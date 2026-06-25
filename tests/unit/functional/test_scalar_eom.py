from __future__ import annotations

from symbolica import Expression, S

from pychete import FieldMassKind, Theory, hermitian_conjugate, s
from pychete.functional import apply_cd, partial_functional_derivative
from pychete.symbols import canonical_string
from pychete.theory_metadata import EXTERNAL_LINEAR_FUNCTION_TAG

from tests.conftest import assert_expr_equal


def test_phi4_scalar_eom_matches_matchete_reference_shape() -> None:
    theory = Theory("phi4")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    lam = theory.define_coupling("lambda", self_conjugate=True)
    mu = theory.dummy_index(0)

    lagrangian = theory.free_lag(phi) - lam() * phi() ** 4 / 24
    expected = (
        -phi() * theory.coupling_handle("m")() ** 2
        - phi(derivatives=[mu, mu])
        - lam() * phi() ** 3 / 6
    )

    assert_expr_equal(theory.derive_eom(lagrangian, phi), expected)


def test_apply_cd_uses_symbolica_derivative_for_product_and_power_rules() -> None:
    theory = Theory("cd_product_power")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    expr = phi() ** 2 * phi(derivatives=[nu])
    expected = (
        2 * phi() * phi(derivatives=[mu]) * phi(derivatives=[nu])
        + phi() ** 2 * phi(derivatives=[nu, mu])
    )

    assert_expr_equal(apply_cd([mu], expr), expected)


def test_apply_cd_uses_symbolica_derivative_for_fractional_powers() -> None:
    theory = Theory("cd_fractional_power")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")

    half = Expression.num(1) / 2
    expr = phi() ** half
    expected = phi() ** (-half) * phi(derivatives=[mu]) / 2

    assert_expr_equal(apply_cd([mu], expr), expected)


def test_apply_cd_treats_bar_and_nested_cd_as_pattern_atoms() -> None:
    theory = Theory("cd_bar_nested")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    rho = theory.lorentz_index("rho")

    expr = s.Bar(phi()) * s.CD(nu, s.CD(rho, phi()))
    expected = (
        s.Bar(phi(derivatives=[mu])) * s.CD(nu, s.CD(rho, phi()))
        + s.Bar(phi()) * s.CD(nu, s.CD(rho, phi(derivatives=[mu])))
    )

    assert_expr_equal(apply_cd([mu], expr), expected)


def test_apply_cd_ignores_couplings_as_non_field_atoms() -> None:
    theory = Theory("cd_coupling")
    lam = theory.define_coupling("lambda", self_conjugate=True)
    mu = theory.lorentz_index("mu")

    assert_expr_equal(apply_cd([mu], lam()), Expression.num(0))


def test_functional_derivative_uses_field_tag_restricted_matches() -> None:
    theory = Theory("fd_tagged_fields")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    untagged_lookalike = s.Field(S("plain_label"), s.Scalar, s.List(), s.List())

    lagrangian = phi() ** 2 + untagged_lookalike**2

    assert_expr_equal(partial_functional_derivative(lagrangian, phi()), 2 * phi())


def test_functional_derivative_protects_barred_field_atoms_by_pattern() -> None:
    theory = Theory("fd_bar_protection")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    lagrangian = s.Bar(phi()) * phi()

    assert_expr_equal(partial_functional_derivative(lagrangian, phi()), s.Bar(phi()))
    assert_expr_equal(partial_functional_derivative(lagrangian, s.Bar(phi())), phi())


def test_functional_derivative_bar_protector_requires_field_tag() -> None:
    theory = Theory("fd_bar_tag")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    untagged_bar = s.Bar(s.Field(S("plain_phi"), s.Scalar, s.List(), s.List()))
    lagrangian = untagged_bar * phi()

    assert_expr_equal(partial_functional_derivative(lagrangian, phi()), untagged_bar)


def test_functional_derivative_linearizes_tagged_external_transpose_wrapper() -> None:
    theory = Theory("fd_external_transp")
    psi = theory.define_field("psi", s.Fermion, mass=0)
    transpose = theory.define_external("Transp")
    lagrangian = s.NCM(transpose(psi()), s.PR, psi())

    derivative = partial_functional_derivative(lagrangian, psi())

    assert any(tag.split("::")[-1] == EXTERNAL_LINEAR_FUNCTION_TAG for tag in transpose.label.get_tags())
    assert "der(" not in canonical_string(derivative)
    assert "functional_variation_parameter" not in canonical_string(derivative)
    assert_expr_equal(
        derivative,
        s.NCM(transpose(psi()), s.PR) + s.NCM(transpose(Expression.num(1)), s.PR, psi()),
    )


def test_apply_cd_linearizes_tagged_external_transpose_wrapper() -> None:
    theory = Theory("cd_external_transp")
    psi = theory.define_field("psi", s.Fermion, mass=0)
    transpose = theory.define_external("Transp")
    mu = theory.lorentz_index("mu")

    derivative = apply_cd([mu], transpose(psi()))

    assert "der(" not in canonical_string(derivative)
    assert "cd_variation_parameter" not in canonical_string(derivative)
    assert_expr_equal(derivative, transpose(psi(derivatives=[mu])))


def test_hermitian_conjugate_reverses_supported_yukawa_chains() -> None:
    theory = Theory("hc_yukawa")
    light = theory.define_field("psi", s.Fermion, mass=0)
    heavy = theory.define_field("Psi", s.Fermion, mass=0)
    scalar = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    y = theory.define_coupling("y")

    interaction = -y() * scalar() * s.NCM(s.Bar(light()), s.PR, heavy())
    expected = -s.Bar(y()) * scalar() * s.NCM(s.Bar(heavy()), s.PL, light())

    assert_expr_equal(hermitian_conjugate(interaction), expected)
