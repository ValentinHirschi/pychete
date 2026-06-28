from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import FieldMassKind, FreeLagConvention, Theory, hermitian_conjugate, s
from pychete.functional import (
    abelian_vector_eom_field_redefinition_delta,
    apply_cd,
    expand_cd_operators,
    expose_scalar_derivative_commutator_bilinears,
    partial_functional_derivative,
    scalar_eom_field_redefinition_delta,
)
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


def test_eom_replacement_rule_isolates_requested_derivative_with_symbolica_coefficient() -> None:
    theory = Theory("phi4_eom_rule")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    lam = theory.define_coupling("lambda", self_conjugate=True)
    mu = theory.dummy_index(0)
    source = theory.define_coupling("J", self_conjugate=True)

    lagrangian = theory.free_lag(phi) - lam() * phi() ** 4 / 24 + source() * phi()
    target = phi(derivatives=[mu, mu])
    rule = theory.eom_replacement_rule(lagrangian, phi, solve_for=target)

    reduced = (target + phi() * target).replace_multiple((rule,))
    expected_rhs = -theory.coupling_handle("m")() ** 2 * phi() - lam() * phi() ** 3 / 6 + source()

    assert_expr_equal(reduced, expected_rhs + phi() * expected_rhs)


def test_eom_replacement_rule_rejects_absent_targets() -> None:
    theory = Theory("phi4_eom_rule_absent")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    chi = theory.define_field("chi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.dummy_index(0)

    lagrangian = theory.free_lag(phi)

    with pytest.raises(ValueError, match="absent from the EOM"):
        theory.eom_replacement_rule(lagrangian, phi, solve_for=chi(derivatives=[mu, mu]))


def test_eom_replacement_rules_for_expression_collects_derivative_targets_with_symbolica_match() -> None:
    theory = Theory("phi4_eom_rules_for_expr")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    chi = theory.define_field("chi", s.Scalar, self_conjugate=True, mass=0)
    source = theory.define_coupling("J", self_conjugate=True)
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)

    lagrangian = theory.free_lag(phi, chi) + source() * phi()
    target = phi(derivatives=[mu, mu])
    ignored = chi(derivatives=[nu, nu])
    expression = phi() * target + chi() * ignored

    rules = theory.eom_replacement_rules_for_expression(
        lagrangian,
        expression,
        fields=[phi],
        min_derivative_order=2,
        strict=True,
    )

    assert len(rules) == 1
    assert_expr_equal(expression.replace_multiple(rules), phi() * (source() - theory.coupling_handle("m")() ** 2 * phi()) + chi() * ignored)


def test_indexed_complex_scalar_eom_uses_conjugate_variation_and_declared_indices() -> None:
    theory = Theory("indexed_complex_scalar_eom")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    source = theory.define_coupling("J", indices=[fund], self_conjugate=False)
    internal = theory.dummy_index(0, fund)
    mu = theory.dummy_index(0)
    lagrangian = theory.free_lag(higgs) + source(internal) * s.Bar(higgs(internal))
    target = higgs(internal, derivatives=[mu, mu])
    expected_eom = -target + source(internal)

    assert_expr_equal(theory.derive_eom(lagrangian, higgs), expected_eom)
    assert_expr_equal(theory.derive_eom(lagrangian, higgs(internal)), expected_eom)

    rule = theory.eom_replacement_rule(lagrangian, higgs(internal), solve_for=target)
    reduced = (s.Bar(higgs(internal)) * target).replace_multiple((rule,))

    assert_expr_equal(reduced, s.Bar(higgs(internal)) * source(internal))

    rules = theory.eom_replacement_rules_for_expression(
        lagrangian,
        s.Bar(higgs(internal)) * target,
        fields=[higgs],
        strict=True,
    )

    assert len(rules) == 1
    assert_expr_equal((s.Bar(higgs(internal)) * target).replace_multiple(rules), s.Bar(higgs(internal)) * source(internal))


def test_eom_replacement_rules_collect_abelian_vector_divergence_targets() -> None:
    coefficient = S("abelian_vector_eom_coefficient")
    theory = Theory("abelian_vector_eom_rules")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 2)],
        self_conjugate=False,
        mass=0,
    )
    vector = theory.field_handle("B")
    coupling = theory.coupling_handle("gY")
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    field = phi()
    current = Expression.I * s.Bar(field) * s.CD(mu, field) - Expression.I * s.CD(mu, s.Bar(field)) * field
    divergence = s.FieldStrength(vector.label, s.List(nu, mu), s.List(), s.List(nu))
    lagrangian = theory.free_lag(phi, vector, convention=FreeLagConvention.MATCHETE)
    source = (coefficient * current * divergence).expand()

    rules = theory.eom_replacement_rules_for_expression(
        lagrangian,
        source,
        fields=[vector],
        strict=True,
    )
    reduced = source.replace_multiple(rules).expand()

    assert len(rules) == 1
    assert_expr_equal(reduced, -2 * coefficient * coupling() ** 2 * current**2)


def test_eom_replacement_rules_collect_opposite_abelian_vector_divergence_sign() -> None:
    coefficient = S("abelian_vector_eom_opposite_coefficient")
    theory = Theory("abelian_vector_eom_opposite_rules")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 2)],
        self_conjugate=False,
        mass=0,
    )
    vector = theory.field_handle("B")
    coupling = theory.coupling_handle("gY")
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    field = phi()
    current = Expression.I * s.Bar(field) * s.CD(mu, field) - Expression.I * s.CD(mu, s.Bar(field)) * field
    divergence = s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List(nu))
    lagrangian = theory.free_lag(phi, vector, convention=FreeLagConvention.MATCHETE)
    source = (coefficient * current * divergence).expand()

    rules = theory.eom_replacement_rules_for_expression(
        lagrangian,
        source,
        fields=[vector],
        strict=True,
    )
    reduced = source.replace_multiple(rules).expand()

    assert len(rules) == 1
    assert_expr_equal(reduced, 2 * coefficient * coupling() ** 2 * current**2)


def test_abelian_vector_eom_field_redefinition_delta_matches_scalar_current_shift() -> None:
    coefficient = S("abelian_vector_field_redefinition_coefficient")
    theory = Theory("abelian_vector_field_redefinition_delta")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 2)],
        self_conjugate=False,
        mass=0,
    )
    vector = theory.field_handle("B")
    coupling = theory.coupling_handle("gY")
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    field = phi()
    current = Expression.I * s.Bar(field) * s.CD(mu, field) - Expression.I * s.CD(mu, s.Bar(field)) * field
    divergence = s.FieldStrength(vector.label, s.List(nu, mu), s.List(), s.List(nu))
    lagrangian = theory.free_lag(phi, vector, convention=FreeLagConvention.MATCHETE)
    source = (coefficient * current * divergence).expand()

    delta = abelian_vector_eom_field_redefinition_delta(
        theory,
        lagrangian,
        source,
        fields=[vector],
        strict=True,
    )

    assert_expr_equal(delta, -2 * coefficient * coupling() ** 2 * current**2)


def test_scalar_eom_field_redefinition_delta_consumes_formal_complex_scalar_eoms() -> None:
    theory = Theory("formal_complex_scalar_eom_shift")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=False, mass=0)
    coefficient = theory.define_coupling("scalar_eom_shift_coefficient", self_conjugate=True)
    field = phi()
    source = theory.free_lag(phi)
    eom_terms = (
        -coefficient() * s.Bar(field) * s.EOM(field) / 2
        - coefficient() * s.EOM(s.Bar(field)) * field / 2
    ).expand()
    expected_shift = -coefficient() * field / 2
    expected = (
        theory.derive_eom(source, s.Bar(field)) * expected_shift
        + theory.derive_eom(source, field) * hermitian_conjugate(expected_shift)
    ).expand()

    delta = scalar_eom_field_redefinition_delta(
        theory,
        source,
        eom_terms,
        fields=[phi],
        strict=True,
    )

    assert_expr_equal(delta, expected)
    assert_expr_equal(theory.scalar_eom_field_redefinition_delta(source, eom_terms, fields=[phi]), expected)


def test_scalar_eom_field_redefinition_delta_scopes_source_by_eft_order() -> None:
    theory = Theory("formal_scalar_eom_shift_scoped")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    coefficient = theory.define_coupling("scalar_eom_shift_scoped_coefficient", self_conjugate=True)
    high = theory.define_coupling("scalar_eom_shift_high_source", mass_dimension=-2, self_conjugate=True)
    field = phi()
    source = theory.free_lag(phi) + high() * field**6
    eom_terms = coefficient() * field * s.EOM(field)
    expected = (theory.derive_eom(theory.free_lag(phi), field) * coefficient() * field).expand()

    delta = scalar_eom_field_redefinition_delta(
        theory,
        source,
        eom_terms,
        fields=[phi],
        max_order=6,
        shift_order=2,
        strict=True,
    )

    assert_expr_equal(delta, expected)


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


def test_apply_cd_differentiates_field_strength_atoms_with_symbolica_patterns() -> None:
    theory = Theory("cd_field_strength")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    vector = theory.field_handle("B")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    rho = theory.lorentz_index("rho")
    sigma = theory.lorentz_index("sigma")
    strength = s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List(rho))
    expected = s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List(rho, sigma))

    assert_expr_equal(apply_cd([sigma], strength), expected)
    assert_expr_equal(apply_cd([sigma], s.Bar(strength)), s.Bar(expected))


def test_apply_cd_propagates_formal_commutator_derivatives() -> None:
    theory = Theory("cd_formal_commutator")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    rho = theory.lorentz_index("rho")

    commutator = s.CovariantDerivativeCommutator(mu, nu, phi())
    expected = s.CovariantDerivativeCommutator(mu, nu, phi(derivatives=[rho]))

    assert_expr_equal(apply_cd([rho], commutator), expected)


def test_expand_cd_operators_differentiates_lowered_commutator_field_strength_insertions() -> None:
    theory = Theory("cd_lowered_commutator")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field("phi", s.Scalar, charges=[theory.group_charge("U1Y", 1)], mass=0)
    vector = theory.field_handle("B")
    coupling = theory.coupling_handle("gY")
    a = theory.lorentz_index("a")
    b = theory.lorentz_index("b")
    c = theory.lorentz_index("c")
    strength = s.FieldStrength(vector.label, s.List(c, b), s.List(), s.List())
    derived_strength = s.FieldStrength(vector.label, s.List(c, b), s.List(), s.List(a))
    expr = s.CD(s.List(a), s.CovariantDerivativeCommutator(c, b, phi()))

    lowered = theory.expand_covariant_derivative_commutators(expr)
    expanded = expand_cd_operators(lowered)
    expected = -Expression.I * coupling() * (derived_strength * phi() + strength * phi(derivatives=[a]))

    assert_expr_equal(expanded, expected)


def test_expose_scalar_derivative_commutator_bilinears_keeps_residual_terms() -> None:
    theory = Theory("scalar_commutator_bilinear_decomposition")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=False, mass=0)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    bar_ab = s.Bar(phi(derivatives=[mu, nu]))
    bar_ba = s.Bar(phi(derivatives=[nu, mu]))
    field_ab = phi(derivatives=[mu, nu])
    field_ba = phi(derivatives=[nu, mu])
    expr = 3 * bar_ab * field_ab - 5 * bar_ab * field_ba + 7 * bar_ba * field_ab + 11 * bar_ba * field_ba
    commutator_bilinear = (
        s.CovariantDerivativeCommutator(mu, nu, s.Bar(phi()))
        * s.CovariantDerivativeCommutator(mu, nu, phi())
    )
    expected = (
        -2 * s.Bar(phi(derivatives=[mu, mu])) * phi(derivatives=[nu, nu])
        + 18 * s.Bar(phi(derivatives=[nu, nu])) * phi(derivatives=[mu, mu])
        + 15 * commutator_bilinear
    ).expand()

    exposed = expose_scalar_derivative_commutator_bilinears(
        theory,
        expr,
        expand_commutators=False,
    )

    assert_expr_equal(exposed, expected)


def test_expose_scalar_derivative_commutator_bilinears_can_lower_to_field_strengths() -> None:
    theory = Theory("scalar_commutator_bilinear_lowered")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        self_conjugate=False,
        mass=0,
    )
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    expr = (
        (s.Bar(phi(derivatives=[mu, nu])) - s.Bar(phi(derivatives=[nu, mu])))
        * (phi(derivatives=[mu, nu]) - phi(derivatives=[nu, mu]))
    ).expand()
    expected = (
        theory.covariant_derivative_commutator(s.Bar(phi()), mu, nu)
        * theory.covariant_derivative_commutator(phi(), mu, nu)
    ).expand()

    exposed = expose_scalar_derivative_commutator_bilinears(theory, expr)

    assert_expr_equal(exposed, expected)


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


def test_functional_derivative_matches_indexed_field_by_label_with_local_delta_contraction() -> None:
    theory = Theory("fd_indexed_delta")
    theory.define_global_group("SU2", s.SU(Expression.num(2)))
    fund = theory.define_representation("SU2", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    singlet = theory.define_field("S", s.Scalar, self_conjugate=True, mass=0)
    source_index = theory.index("i", fund)
    target_index = theory.index("j", fund)
    target_dual = theory.index("j", s.Bar(fund))
    lagrangian = singlet() * higgs(source_index) * s.Bar(higgs(source_index))

    barred_derivative = partial_functional_derivative(lagrangian, s.Bar(higgs(target_index)))
    field_derivative = partial_functional_derivative(lagrangian, higgs(target_index))

    assert_expr_equal(
        barred_derivative,
        singlet() * higgs(target_index),
    )
    assert_expr_equal(
        field_derivative,
        singlet() * s.Bar(higgs(target_index)),
    )
    assert_expr_equal(
        partial_functional_derivative(lagrangian, s.Bar(higgs(source_index))),
        singlet() * higgs(source_index),
    )
    assert_expr_equal(
        partial_functional_derivative(lagrangian, higgs(source_index)),
        singlet() * s.Bar(higgs(source_index)),
    )
    assert_expr_equal(
        partial_functional_derivative(lagrangian, higgs(target_dual)),
        Expression.num(0),
    )


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
