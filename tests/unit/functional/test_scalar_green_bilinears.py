from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete.backends import idenso
import pychete.matching as matching_module
from pychete.functional import (
    expose_scalar_derivative_commutator_bilinears,
    expose_vector_field_strength_divergences_as_formal_eom,
    integrate_by_parts_scalar_laplacians,
    matchete_vector_eom_scalar_bilinear_normal_form,
    normalize_conjugate_scalar_field_slots,
    scalar_derivative_green_normal_form,
    scalar_derivative_green_normal_form_by_operator_class,
    scalar_derivative_ibp_identities,
    scalar_eom_identities,
    scalar_formal_eom_ibp_identities,
    vector_formal_eom_ibp_identities,
    vector_eom_identities,
)
from pychete.expr import (
    bar_field_inner,
    bar_field_pattern,
    field_derivatives,
    field_pattern,
    field_strength_derivatives,
    field_strength_pattern,
    matching_subexpressions,
    terms,
)
from pychete.matching_results import MatchingResult
from pychete.symbols import SymbolRole, s
from pychete.theory import Theory
from pychete.theory_metadata import FieldHandle
from tests.conftest import assert_expr_equal


def _scalar_su2_probe() -> tuple[Theory, FieldHandle, Expression, Expression, Expression, Expression]:
    theory = Theory("scalar_green_bilinear_probe")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    weak = theory.field_handle("W")
    i = theory.index("i", fund)
    a = theory.index("A", adj)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    target = (
        s.Bar(higgs(i))
        * higgs(i)
        * s.FieldStrength(weak.label, s.List(mu, nu), s.List(a), s.List()) ** 2
        / theory.coupling_handle("gL")() ** 2
    )
    return theory, higgs, target, i, mu, nu


def _scalar_u1_probe() -> tuple[Theory, FieldHandle, Expression, Expression, Expression, Expression]:
    theory = Theory("scalar_green_mixed_field_strength_probe")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        self_conjugate=False,
        mass=0,
    )
    vector = theory.field_handle("B")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    strength = s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List())
    target = s.Bar(phi()) * phi() * strength**2
    return theory, phi, strength, target, mu, nu


@pytest.mark.parametrize(
    ("name", "derivatives", "expected_weight"),
    (
        ("Dbar_abab_H", ("mu", "nu", "mu", "nu"), Expression.num(1) / Expression.num(8)),
        ("Dbar_aabb_H", ("mu", "mu", "nu", "nu"), Expression.num(0)),
        ("Dbar_abba_H", ("mu", "nu", "nu", "mu"), Expression.num(1) / Expression.num(4)),
    ),
)
def test_scalar_green_bilinear_exposes_one_sided_four_derivative_field_strength_component(
    name: str,
    derivatives: tuple[str, str, str, str],
    expected_weight: Expression,
) -> None:
    theory, higgs, target, i, mu, nu = _scalar_su2_probe()
    derivative_lookup = {"mu": mu, "nu": nu}
    derivative_tuple = tuple(derivative_lookup[label] for label in derivatives)
    source = s.Bar(higgs(i, derivatives=derivative_tuple)) * higgs(i)

    coefficient = _project_c_hw_like_coefficient(theory, source, target)

    assert name
    assert_expr_equal(coefficient, expected_weight * theory.coupling_handle("gL")() ** 2)


def test_scalar_green_bilinear_normalizes_dual_index_conjugate_scalar_slots() -> None:
    theory, higgs, _target, i, mu, _nu = _scalar_su2_probe()
    dual_i = theory.index("i", s.Bar(i[1]))
    source = higgs(dual_i, derivatives=[mu]) * higgs(i)

    normalized = normalize_conjugate_scalar_field_slots(theory, source)

    assert_expr_equal(normalized, s.Bar(higgs(i, derivatives=[mu])) * higgs(i))


def test_scalar_green_bilinear_exposes_dual_index_conjugate_one_sided_four_derivative_component() -> None:
    theory, higgs, target, i, mu, nu = _scalar_su2_probe()
    dual_i = theory.index("i", s.Bar(i[1]))
    source = higgs(dual_i, derivatives=[mu, nu, nu, mu]) * higgs(i)

    coefficient = _project_c_hw_like_coefficient(theory, source, target)

    assert_expr_equal(coefficient, theory.coupling_handle("gL")() ** 2 / 4)


@pytest.mark.parametrize(
    ("field_derivatives", "expected_weight"),
    (
        (("mu", "nu"), Expression.num(1) / Expression.num(4)),
        (("nu", "mu"), Expression.num(1) / Expression.num(8)),
    ),
)
def test_scalar_green_bilinear_exposes_two_derivative_field_strength_component(
    field_derivatives: tuple[str, str],
    expected_weight: Expression,
) -> None:
    theory, higgs, target, i, mu, nu = _scalar_su2_probe()
    derivative_lookup = {"mu": mu, "nu": nu}
    field_derivative_tuple = tuple(derivative_lookup[label] for label in field_derivatives)
    source = s.Bar(higgs(i, derivatives=[mu, nu])) * higgs(i, derivatives=field_derivative_tuple)

    coefficient = _project_c_hw_like_coefficient(theory, source, target)

    assert_expr_equal(coefficient, expected_weight * theory.coupling_handle("gL")() ** 2)


def test_scalar_green_bilinear_preserves_antisymmetric_commutator_component() -> None:
    theory, higgs, target, i, mu, nu = _scalar_su2_probe()
    source = (
        (s.Bar(higgs(i, derivatives=[mu, nu])) - s.Bar(higgs(i, derivatives=[nu, mu])))
        * (higgs(i, derivatives=[mu, nu]) - higgs(i, derivatives=[nu, mu]))
    ).expand()

    coefficient = _project_c_hw_like_coefficient(theory, source, target)

    assert_expr_equal(coefficient, theory.coupling_handle("gL")() ** 2 / 4)


@pytest.mark.parametrize(
    ("derivatives", "expected_weight"),
    (
        (("mu", "nu"), Expression.num(1) / Expression.num(2)),
        (("nu", "mu"), -Expression.num(1) / Expression.num(2)),
    ),
)
def test_scalar_green_bilinear_exposes_mixed_field_strength_derivative_component(
    derivatives: tuple[str, str],
    expected_weight: Expression,
) -> None:
    theory, phi, strength, target, mu, nu = _scalar_u1_probe()
    derivative_lookup = {"mu": mu, "nu": nu}
    source = (
        Expression.I
        * strength
        * s.Bar(phi())
        * phi(derivatives=tuple(derivative_lookup[label] for label in derivatives))
    )

    coefficient = _project_mixed_field_strength_coefficient(theory, source, target)

    assert_expr_equal(coefficient, expected_weight)


def test_scalar_green_bilinear_exposes_conjugate_mixed_field_strength_derivative_component() -> None:
    theory, phi, strength, target, mu, nu = _scalar_u1_probe()
    source = Expression.I * strength * s.Bar(phi(derivatives=[mu, nu])) * phi()

    coefficient = _project_mixed_field_strength_coefficient(theory, source, target)

    assert_expr_equal(coefficient, -Expression.num(1) / Expression.num(2))


def test_scalar_laplacian_ibp_exposes_derivative_current_component() -> None:
    coefficient = S("scalar_laplacian_ibp_current_coefficient")
    theory, higgs, _target, i, mu, _nu = _scalar_su2_probe()
    j = theory.index("j", theory.fields["H"].indices[0])
    source = s.Bar(higgs(i)) * higgs(i) * s.Bar(higgs(j)) * higgs(j, derivatives=[mu, mu])
    target = higgs(i) * s.Bar(higgs(j)) * higgs(j, derivatives=[mu]) * s.Bar(higgs(i, derivatives=[mu]))

    reduced = integrate_by_parts_scalar_laplacians(theory, coefficient * source)
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=reduced,
    )

    projected = result.project_matching_conditions({"current": target}, expand_source=False)

    assert_expr_equal(projected["current"], -coefficient)


def test_scalar_laplacian_ibp_drops_bare_total_derivative() -> None:
    theory, higgs, _target, i, mu, _nu = _scalar_su2_probe()
    source = higgs(i, derivatives=[mu, mu])

    reduced = integrate_by_parts_scalar_laplacians(theory, source)

    assert_expr_equal(reduced, Expression.num(0))


def test_scalar_derivative_ibp_identities_generate_outer_derivative_identity() -> None:
    coefficient = S("scalar_derivative_ibp_identity_coefficient")
    theory, higgs, _target, i, mu, nu = _scalar_su2_probe()
    source = s.Bar(higgs(i)) * higgs(i, derivatives=[mu, nu])
    expected = (
        coefficient * source
        + coefficient * s.Bar(higgs(i, derivatives=[mu])) * higgs(i, derivatives=[nu])
    )

    identities = scalar_derivative_ibp_identities(theory, coefficient * source)

    assert len(identities) == 1
    assert_expr_equal(identities[0], expected)


def test_scalar_derivative_green_normal_form_applies_ibp_identity() -> None:
    coefficient = S("scalar_derivative_green_ibp_coefficient")
    theory, higgs, _target, i, mu, nu = _scalar_su2_probe()
    source = s.Bar(higgs(i)) * higgs(i, derivatives=[mu, nu])
    expected = -coefficient * s.Bar(higgs(i, derivatives=[mu])) * higgs(i, derivatives=[nu])

    reduced = scalar_derivative_green_normal_form(
        theory,
        coefficient * source,
        include_commutators=False,
        max_rounds=1,
    )

    assert_expr_equal(reduced, expected)


def test_scalar_derivative_green_normal_form_can_prefer_commuted_representatives() -> None:
    coefficient = S("scalar_derivative_green_commutator_coefficient")
    theory, higgs, _target, i, mu, nu = _scalar_su2_probe()
    source = s.Bar(higgs(i)) * higgs(i, derivatives=[mu, nu])
    swapped = s.Bar(higgs(i)) * higgs(i, derivatives=[nu, mu])
    commutator = s.Bar(higgs(i)) * s.CovariantDerivativeCommutator(mu, nu, higgs(i))

    reduced = scalar_derivative_green_normal_form(
        theory,
        coefficient * source,
        include_ibp=False,
        preferred=(swapped, commutator),
    )

    assert_expr_equal(reduced, coefficient * swapped + coefficient * commutator)


def test_scalar_derivative_green_normal_form_closes_local_ibp_neighborhood() -> None:
    coefficient = S("scalar_derivative_green_closure_coefficient")
    theory, higgs, _target, i, mu, nu = _scalar_su2_probe()
    source = s.Bar(higgs(i)) * higgs(i, derivatives=[mu, nu])
    preferred = s.Bar(higgs(i, derivatives=[mu, nu])) * higgs(i)

    reduced = scalar_derivative_green_normal_form(
        theory,
        coefficient * source,
        preferred=(preferred,),
        include_commutators=False,
        max_rounds=2,
    )

    assert_expr_equal(reduced, coefficient * preferred)


def test_scalar_derivative_green_normal_form_auto_prefers_balanced_four_derivative_bilinear() -> None:
    coefficient = S("scalar_derivative_green_auto_score_coefficient")
    theory, higgs, _target, i, mu, nu = _scalar_su2_probe()
    source = s.Bar(higgs(i)) * higgs(i, derivatives=[mu, nu, mu, nu])
    expected = coefficient * s.Bar(higgs(i, derivatives=[mu, nu])) * higgs(i, derivatives=[mu, nu])

    reduced = scalar_derivative_green_normal_form(theory, coefficient * source)

    assert_expr_equal(reduced, expected)


def test_scalar_eom_identities_expose_laplacian_as_formal_eom() -> None:
    coefficient = S("scalar_eom_identity_coefficient")
    theory, higgs, _target, i, mu, _nu = _scalar_su2_probe()
    source = s.Bar(higgs(i)) * higgs(i, derivatives=[mu, mu])
    expected = coefficient * s.Bar(higgs(i)) * (s.EOM(higgs(i)) + higgs(i, derivatives=[mu, mu]))

    identities = scalar_eom_identities(
        theory,
        theory.free_lag(higgs),
        coefficient * source,
        fields=[higgs],
    )

    assert len(identities) == 1
    assert_expr_equal(identities[0], expected)


def test_scalar_derivative_green_normal_form_can_prefer_formal_eom_representative() -> None:
    coefficient = S("scalar_derivative_green_eom_coefficient")
    theory, higgs, _target, i, mu, _nu = _scalar_su2_probe()
    source = s.Bar(higgs(i)) * higgs(i, derivatives=[mu, mu])
    expected = -coefficient * s.Bar(higgs(i)) * s.EOM(higgs(i))

    reduced = scalar_derivative_green_normal_form(
        theory,
        coefficient * source,
        include_ibp=False,
        include_commutators=False,
        include_eom=True,
        eom_lagrangian=theory.free_lag(higgs),
        eom_fields=[higgs],
        max_rounds=1,
    )

    assert_expr_equal(reduced, expected)


@pytest.mark.parametrize(
    ("orientation", "identity_eom_sign", "reduced_eom_sign"),
    (
        ("standard", -Expression.num(1), Expression.num(1)),
        ("opposite", Expression.num(1), -Expression.num(1)),
    ),
)
def test_vector_eom_identities_expose_field_strength_divergence_as_formal_eom(
    orientation: str,
    identity_eom_sign: Expression,
    reduced_eom_sign: Expression,
) -> None:
    coefficient = S(f"vector_eom_identity_{orientation}_coefficient")
    theory, phi, _strength, _target, mu, nu = _scalar_u1_probe()
    vector = theory.field_handle("B")
    if orientation == "standard":
        divergence = s.FieldStrength(vector.label, s.List(nu, mu), s.List(), s.List(nu))
    else:
        divergence = s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List(nu))
    prefactor = coefficient * s.Bar(phi()) * phi(derivatives=[mu])
    formal_eom = s.EOM(vector(mu))

    identities = vector_eom_identities(theory, prefactor * divergence, fields=[vector])

    assert len(identities) == 1
    assert_expr_equal(identities[0], prefactor * (divergence + identity_eom_sign * formal_eom))

    reduced = scalar_derivative_green_normal_form(
        theory,
        prefactor * divergence,
        include_ibp=False,
        include_commutators=False,
        include_eom=True,
        eom_lagrangian=theory.free_lag(phi, vector),
        eom_fields=[vector],
        max_rounds=1,
    )

    assert_expr_equal(reduced, reduced_eom_sign * prefactor * formal_eom)


def test_expose_vector_field_strength_divergences_as_formal_eom_uses_standard_form_signs() -> None:
    coefficient = S("vector_eom_direct_standard_form_coefficient")
    theory, phi, _strength, _target, mu, nu = _scalar_u1_probe()
    vector = theory.field_handle("B")
    standard_divergence = s.FieldStrength(vector.label, s.List(nu, mu), s.List(), s.List(nu))
    opposite_divergence = s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List(nu))
    prefactor = coefficient * s.Bar(phi()) * phi(derivatives=[mu])

    exposed = expose_vector_field_strength_divergences_as_formal_eom(
        theory,
        prefactor * standard_divergence + prefactor * opposite_divergence,
        fields=[vector],
    )

    assert_expr_equal(exposed, Expression.num(0))


def test_matchete_vector_eom_scalar_bilinear_normal_form_uses_antisymmetric_pair() -> None:
    left_coefficient = S("vector_eom_left_orientation_coefficient")
    right_coefficient = S("vector_eom_right_orientation_coefficient")
    theory, phi, _strength, _target, mu, _nu = _scalar_u1_probe()
    vector = theory.field_handle("B")
    formal_eom = s.EOM(vector(mu))
    derivative_on_bar = s.Bar(phi(derivatives=[mu])) * formal_eom * phi()
    derivative_on_field = s.Bar(phi()) * formal_eom * phi(derivatives=[mu])

    reduced = matchete_vector_eom_scalar_bilinear_normal_form(
        theory,
        left_coefficient * derivative_on_bar + right_coefficient * derivative_on_field,
        fields=[vector],
    )

    expected = (
        (left_coefficient - right_coefficient)
        * (derivative_on_bar - derivative_on_field)
        / 2
    ).expand()
    assert_expr_equal(reduced, expected)


def test_matchete_vector_eom_scalar_bilinear_normal_form_leaves_nonabelian_vector_eoms_formal() -> None:
    coefficient = S("nonabelian_vector_eom_orientation_coefficient")
    theory, phi, _target, index, mu, _nu = _scalar_su2_probe()
    weak = theory.field_handle("W")
    adjoint = theory.define_representation("SU2L", "adj")
    adjoint_index = theory.index("A", adjoint)
    formal_eom = s.EOM(weak(adjoint_index, mu))
    source = coefficient * s.Bar(phi(index)) * formal_eom * phi(index, derivatives=[mu])

    reduced = matchete_vector_eom_scalar_bilinear_normal_form(theory, source, fields=[weak])

    assert_expr_equal(reduced, source)


def test_scalar_derivative_green_standard_form_eom_ignores_interaction_terms() -> None:
    coefficient = S("scalar_derivative_green_standard_eom_coefficient")
    theory, higgs, _target, i, mu, _nu = _scalar_su2_probe()
    quartic = theory.define_coupling("lambda_H", self_conjugate=True)
    eom_lagrangian = (
        theory.free_lag(higgs)
        - quartic() * (s.Bar(higgs(i)) * higgs(i)) ** 2
    )
    source = s.Bar(higgs(i)) * higgs(i, derivatives=[mu, mu])
    expected = -coefficient * s.Bar(higgs(i)) * s.EOM(higgs(i))

    reduced = scalar_derivative_green_normal_form(
        theory,
        coefficient * source,
        include_ibp=False,
        include_commutators=False,
        include_eom=True,
        eom_lagrangian=eom_lagrangian,
        eom_fields=[higgs],
        eom_standard_form_only=True,
        max_rounds=1,
    )

    assert_expr_equal(reduced, expected)


def test_scalar_derivative_green_normal_form_by_operator_class_keeps_basis_local() -> None:
    coefficient = S("scalar_derivative_green_classwise_coefficient")
    theory, higgs, _target, i, mu, nu = _scalar_su2_probe()
    singlet = theory.define_field("S", s.Scalar, self_conjugate=False, mass=0)
    source = (
        coefficient * s.Bar(higgs(i)) * higgs(i, derivatives=[mu, nu])
        + coefficient * s.Bar(singlet()) * singlet(derivatives=[mu, nu])
    )
    expected = (
        -coefficient * s.Bar(higgs(i, derivatives=[mu])) * higgs(i, derivatives=[nu])
        - coefficient * s.Bar(singlet(derivatives=[mu])) * singlet(derivatives=[nu])
    )

    with pytest.raises(ValueError, match="Green-basis reduction discovered more than 3 basis terms"):
        scalar_derivative_green_normal_form(
            theory,
            source,
            include_commutators=False,
            max_basis_terms=3,
            max_rounds=1,
        )

    reduced = scalar_derivative_green_normal_form_by_operator_class(
        theory,
        source,
        include_commutators=False,
        max_basis_terms=3,
        max_rounds=1,
    )

    assert_expr_equal(reduced, expected)


def test_scalar_formal_eom_ibp_identity_matches_matchete_scalar_eom_splitter() -> None:
    coefficient = S("scalar_formal_eom_ibp_coefficient")
    theory, higgs, _target, i, _mu, _nu = _scalar_su2_probe()
    source = coefficient * s.Bar(higgs(i)) * s.EOM(higgs(i))

    identities = scalar_formal_eom_ibp_identities(theory, source, fields=[higgs])

    assert len(identities) == 1
    identity = identities[0]
    derivative_atoms = [
        atom
        for atom in matching_subexpressions(identity, field_pattern(higgs.definition.label))
        if len(field_derivatives(atom)) == 1
    ]
    laplacian_atoms = [
        atom
        for atom in matching_subexpressions(identity, field_pattern(higgs.definition.label))
        if len(field_derivatives(atom)) == 2
    ]
    assert derivative_atoms
    assert laplacian_atoms
    assert not bool(identity.matches(s.EOM(s.CDBodyWildcard)))


def test_scalar_derivative_green_normal_form_uses_formal_eom_ibp_splitter_identity() -> None:
    coefficient = S("scalar_derivative_green_formal_eom_ibp_coefficient")
    theory, higgs, _target, i, _mu, _nu = _scalar_su2_probe()
    source = s.Bar(higgs(i)) * s.EOM(higgs(i))
    splitter_identity = scalar_formal_eom_ibp_identities(theory, coefficient * source, fields=[higgs])[0]
    preferred = next(
        (
            field_atoms[0] * bar_atoms[0]
            for term in terms(splitter_identity.expand())
            if (
                field_atoms := [
                    atom
                    for atom in matching_subexpressions(term, field_pattern(higgs.definition.label))
                    if len(field_derivatives(atom)) == 1
                ]
            )
            and (
                bar_atoms := [
                    atom
                    for atom in matching_subexpressions(term, bar_field_pattern(higgs.definition.label))
                    if len(field_derivatives(bar_field_inner(atom))) == 1
                ]
            )
        ),
        None,
    )
    assert preferred is not None

    reduced = scalar_derivative_green_normal_form(
        theory,
        coefficient * source,
        preferred=(preferred,),
        include_eom=True,
        eom_lagrangian=theory.free_lag(higgs),
        eom_fields=[higgs],
        max_rounds=3,
    )

    assert_expr_equal(reduced, coefficient * preferred)


def test_vector_formal_eom_ibp_identity_matches_matchete_vector_eom_splitter() -> None:
    coefficient = S("vector_formal_eom_ibp_coefficient")
    theory, phi, _strength, _target, mu, _nu = _scalar_u1_probe()
    vector = theory.field_handle("B")
    source = coefficient * s.Bar(phi()) * phi() * s.EOM(vector(mu))

    identities = vector_formal_eom_ibp_identities(theory, source, fields=[vector])

    assert len(identities) == 1
    identity = identities[0]
    strength_atoms = matching_subexpressions(identity, field_strength_pattern(vector.definition.label))
    divergence_atoms = [atom for atom in strength_atoms if field_strength_derivatives(atom)]
    assert strength_atoms
    assert divergence_atoms
    assert not bool(identity.matches(s.EOM(s.CDBodyWildcard)))


def test_scalar_derivative_green_normal_form_uses_vector_formal_eom_ibp_splitter_identity() -> None:
    coefficient = S("scalar_derivative_green_vector_formal_eom_ibp_coefficient")
    theory, phi, _strength, _target, mu, _nu = _scalar_u1_probe()
    vector = theory.field_handle("B")
    rho = theory.index(theory.symbol("vector_formal_eom_ibp_0_mu", role=SymbolRole.INDEX), s.Lorentz)
    source = coefficient * s.Bar(phi()) * phi() * s.EOM(vector(mu))
    preferred = (
        s.Bar(phi(derivatives=[rho])) * phi() * s.FieldStrength(vector.label, s.List(rho, mu), s.List(), s.List()),
        s.Bar(phi()) * phi(derivatives=[rho]) * s.FieldStrength(vector.label, s.List(rho, mu), s.List(), s.List()),
    )
    expected = -coefficient * sum(preferred, Expression.num(0))

    reduced = scalar_derivative_green_normal_form(
        theory,
        source,
        preferred=preferred,
        include_ibp=False,
        include_commutators=False,
        include_eom=True,
        eom_lagrangian=theory.free_lag(phi, vector),
        eom_fields=[vector],
        max_rounds=3,
    )

    assert_expr_equal(reduced, expected)


def test_wilson_line_scalar_green_hook_can_expose_formal_eom_terms() -> None:
    coefficient = S("wilson_line_scalar_eom_hook_coefficient")
    theory, higgs, _target, i, mu, _nu = _scalar_su2_probe()
    source = s.Bar(higgs(i)) * higgs(i, derivatives=[mu, mu])
    expected = -coefficient * higgs(i) * s.EOM(s.Bar(higgs(i)))

    reduced = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
        theory,
        coefficient * source,
        eom_lagrangian=theory.free_lag(higgs),
        expose_scalar_eom_terms=True,
    )

    assert_expr_equal(reduced, expected)


def test_wilson_line_scalar_green_hook_can_expose_formal_vector_eom_terms() -> None:
    coefficient = S("wilson_line_vector_eom_hook_coefficient")
    theory, phi, _strength, _target, mu, nu = _scalar_u1_probe()
    vector = theory.field_handle("B")
    source = coefficient * s.Bar(phi()) * phi(derivatives=[mu]) * s.FieldStrength(
        vector.label,
        s.List(nu, mu),
        s.List(),
        s.List(nu),
    )
    expected = (
        coefficient
        * (
            s.Bar(phi()) * phi(derivatives=[mu]) * s.EOM(vector(mu))
            - s.Bar(phi(derivatives=[mu])) * phi() * s.EOM(vector(mu))
        )
        / 2
    ).expand()

    reduced = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
        theory,
        source,
        eom_lagrangian=theory.free_lag(phi, vector),
        expose_scalar_eom_terms=True,
    )

    assert_expr_equal(reduced, expected)


def test_wilson_line_scalar_green_hook_exposes_generated_vector_divergence_as_formal_eom() -> None:
    coefficient = S("wilson_line_generated_vector_eom_hook_coefficient")
    theory, phi, _strength, _target, mu, nu = _scalar_u1_probe()
    vector = theory.field_handle("B")
    source = (
        coefficient
        * Expression.I
        * s.Bar(phi())
        * phi(derivatives=[mu])
        * s.CD(nu, s.FieldStrength(vector.label, s.List(nu, mu), s.List(), s.List()))
    )
    divergence = s.FieldStrength(vector.label, s.List(nu, mu), s.List(), s.List(nu))
    divergence_target = Expression.I * s.Bar(phi()) * phi(derivatives=[mu]) * divergence
    formal_target = Expression.I * s.Bar(phi()) * phi(derivatives=[mu]) * s.EOM(vector(mu))

    reduced = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
        theory,
        source,
        eom_lagrangian=theory.free_lag(phi, vector),
        expose_scalar_eom_terms=True,
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=reduced,
    )
    projected = result.project_matching_conditions(
        {
            "formal_vector_eom": formal_target,
            "divergence": divergence_target,
        },
        expand_source=False,
        drop_zero=False,
    )

    assert_expr_equal(projected["formal_vector_eom"], coefficient / 2)
    assert_expr_equal(projected["divergence"], Expression.num(0))


def test_wilson_line_scalar_green_hook_closes_four_derivative_formal_eom_neighborhood() -> None:
    coefficient = S("wilson_line_scalar_eom_hook_four_derivative_coefficient")
    theory, higgs, _target, i, mu, nu = _scalar_su2_probe()
    source = s.Bar(higgs(i, derivatives=[mu, mu, nu, nu])) * higgs(i)
    expected = coefficient * s.EOM(higgs(i)) * s.EOM(s.Bar(higgs(i)))

    reduced = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
        theory,
        coefficient * source,
        eom_lagrangian=theory.free_lag(higgs),
        expose_scalar_eom_terms=True,
    )

    assert_expr_equal(reduced, expected)


@pytest.mark.parametrize(
    ("barred_derivative", "field_derivative", "expected_weight"),
    (
        ("mu", "nu", -Expression.num(1) / Expression.num(2)),
        ("nu", "mu", Expression.num(1) / Expression.num(2)),
    ),
)
def test_scalar_green_bilinear_ibp_exposes_first_derivative_field_strength_component(
    barred_derivative: str,
    field_derivative: str,
    expected_weight: Expression,
) -> None:
    theory, phi, strength, target, mu, nu = _scalar_u1_probe()
    derivative_lookup = {"mu": mu, "nu": nu}
    source = (
        Expression.I
        * strength
        * s.Bar(phi(derivatives=[derivative_lookup[barred_derivative]]))
        * phi(derivatives=[derivative_lookup[field_derivative]])
    )

    coefficient = _project_mixed_field_strength_coefficient(theory, source, target)

    assert_expr_equal(coefficient, expected_weight)


def test_scalar_green_bilinear_exposes_three_plus_one_field_strength_divergence_component() -> None:
    coefficient = S("scalar_green_three_plus_one_coefficient")
    theory, phi, _strength, _target, mu, nu = _scalar_u1_probe()
    vector = theory.field_handle("B")
    source = coefficient * s.Bar(phi(derivatives=[mu, nu, nu])) * phi(derivatives=[mu])
    divergence = s.FieldStrength(vector.label, s.List(nu, mu), s.List(), s.List(nu))
    target = Expression.I * s.Bar(phi()) * phi(derivatives=[mu]) * divergence
    expected = -coefficient * s.Bar(phi(derivatives=[nu, nu])) * phi(derivatives=[mu, mu])

    normalized = expose_scalar_derivative_commutator_bilinears(
        theory,
        source,
        include_gauge_coupling=False,
        expand_commutators=True,
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=normalized.expand(),
    )

    projected = result.project_matching_conditions({"current_divergence": target}, expand_source=False)

    assert_expr_equal(projected["current_divergence"], Expression.num(0))
    assert_expr_equal(normalized, expected)


def test_scalar_green_bilinear_keeps_unmatched_three_plus_one_ordering_bounded() -> None:
    coefficient = S("scalar_green_unmatched_three_plus_one_coefficient")
    theory, phi, _strength, _target, mu, nu = _scalar_u1_probe()
    vector = theory.field_handle("B")
    source = coefficient * s.Bar(phi(derivatives=[nu, nu, mu])) * phi(derivatives=[mu])
    divergence = s.FieldStrength(vector.label, s.List(nu, mu), s.List(), s.List(nu))
    target = Expression.I * s.Bar(phi()) * phi(derivatives=[mu]) * divergence

    normalized = expose_scalar_derivative_commutator_bilinears(
        theory,
        source,
        include_gauge_coupling=False,
        expand_commutators=True,
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=normalized.expand(),
    )

    projected = result.project_matching_conditions({"current_divergence": target}, expand_source=False)

    assert_expr_equal(projected["current_divergence"], Expression.num(0))


def _project_c_hw_like_coefficient(theory: Theory, source: Expression, target: Expression) -> Expression:
    normalized = expose_scalar_derivative_commutator_bilinears(
        theory,
        source,
        include_gauge_coupling=False,
        expand_commutators=True,
    )
    normalized = idenso.simplify_pychete_field_strength_group_algebra(theory, normalized)
    normalized = idenso.simplify_pychete_color_algebra(theory, normalized)
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=normalized.expand(),
    )
    return result.project_matching_conditions({"cHW_like": target}, expand_source=False)["cHW_like"].expand()


def _project_mixed_field_strength_coefficient(theory: Theory, source: Expression, target: Expression) -> Expression:
    normalized = expose_scalar_derivative_commutator_bilinears(
        theory,
        source,
        include_gauge_coupling=False,
        expand_commutators=True,
    )
    normalized = idenso.simplify_pychete_field_strength_group_algebra(theory, normalized)
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=normalized.expand(),
    )
    return result.project_matching_conditions({"field_strength_like": target}, expand_source=False)[
        "field_strength_like"
    ].expand()
