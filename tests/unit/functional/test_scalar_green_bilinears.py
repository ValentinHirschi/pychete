from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete.backends import idenso
import pychete.matching as matching_module
from pychete.functional import (
    expose_scalar_derivative_commutator_bilinears,
    integrate_by_parts_scalar_laplacians,
    normalize_conjugate_scalar_field_slots,
    scalar_derivative_green_normal_form,
    scalar_derivative_ibp_identities,
    scalar_eom_identities,
    scalar_formal_eom_ibp_identities,
)
from pychete.expr import (
    bar_field_inner,
    bar_field_pattern,
    field_derivatives,
    field_pattern,
    matching_subexpressions,
    terms,
)
from pychete.matching_results import MatchingResult
from pychete.symbols import s
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


def test_wilson_line_scalar_green_hook_can_expose_formal_eom_terms() -> None:
    coefficient = S("wilson_line_scalar_eom_hook_coefficient")
    theory, higgs, _target, i, mu, _nu = _scalar_su2_probe()
    source = s.Bar(higgs(i)) * higgs(i, derivatives=[mu, mu])
    expected = -coefficient * s.Bar(higgs(i)) * s.EOM(higgs(i))

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

    assert_expr_equal(projected["current_divergence"], coefficient)


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
