from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import FieldMassKind, FluctuationSector, FluctuationStatistics, Theory, canonical_string, s

from tests.conftest import assert_expr_equal


def test_fluctuation_operator_uses_symbolica_hessian_for_scalar_basis() -> None:
    theory = Theory("fluctuation_scalar")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True)
    g = theory.define_coupling("g", self_conjugate=True)
    mass = theory.mass_expr(heavy.definition)
    assert mass is not None
    lagrangian = -mass**2 * heavy() ** 2 / 2 - g() * heavy() * phi() ** 2 / 2

    operator = theory.fluctuation_operator(lagrangian, [heavy, phi])

    assert_expr_equal(operator.entry(heavy, heavy), -mass**2)
    assert_expr_equal(operator.entry(heavy, phi), -g() * phi())
    assert_expr_equal(operator.entry(phi, heavy), -g() * phi())
    assert_expr_equal(operator.entry(phi, phi), -g() * heavy())


def test_fluctuation_operator_protects_unselected_barred_fields() -> None:
    theory = Theory("fluctuation_bar_protection")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=False, mass=(FieldMassKind.LIGHT, "m"))
    mass = theory.mass_expr(phi.definition)
    assert mass is not None
    lagrangian = -mass**2 * s.Bar(phi()) * phi()

    operator = theory.fluctuation_operator(lagrangian, [phi])

    assert_expr_equal(operator.entry(phi, phi), Expression.num(0))


def test_fluctuation_operator_can_include_barred_field_basis_entries() -> None:
    theory = Theory("fluctuation_bar_basis")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=False, mass=(FieldMassKind.LIGHT, "m"))
    mass = theory.mass_expr(phi.definition)
    assert mass is not None
    barred_phi = s.Bar(phi())
    lagrangian = -mass**2 * barred_phi * phi()

    operator = theory.fluctuation_operator(lagrangian, [barred_phi, phi])

    assert_expr_equal(operator.entry(barred_phi, phi), -mass**2)
    assert_expr_equal(operator.entry(phi, barred_phi), -mass**2)
    assert operator.to_expression_map()


def test_fluctuation_operator_rejects_duplicate_basis_entries() -> None:
    theory = Theory("fluctuation_duplicate_basis")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True)

    with pytest.raises(ValueError, match="unique"):
        theory.fluctuation_operator(phi() ** 2, [phi, phi])


def test_fluctuation_basis_discovers_fields_with_symbolica_tagged_patterns() -> None:
    theory = Theory("fluctuation_basis_discovery")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    complex_light = theory.define_field("chi", s.Scalar, self_conjugate=False, mass=(FieldMassKind.LIGHT, "m"))
    mu = theory.dummy_index(0)
    unregistered_field = s.Field(S("untagged"), s.Scalar, s.List(), s.List())
    lagrangian = (
        heavy(derivatives=[mu]) ** 2
        + light() ** 2
        + s.Bar(complex_light()) * complex_light()
        + unregistered_field**2
    )

    basis = theory.fluctuation_basis(lagrangian)

    assert tuple(basis) == basis.entries
    heavy_names = {canonical_string(field) for field in basis.heavy}
    light_names = {canonical_string(field) for field in basis.light}
    entry_names = {canonical_string(field) for field in basis.entries}
    assert canonical_string(heavy()) in heavy_names
    assert canonical_string(light()) in light_names
    assert canonical_string(s.Bar(complex_light())) in light_names
    assert canonical_string(complex_light()) in light_names
    assert canonical_string(unregistered_field) not in entry_names


def test_fluctuation_operator_uses_discovered_basis_when_omitted() -> None:
    theory = Theory("fluctuation_auto_basis")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    g = theory.define_coupling("g", self_conjugate=True)
    lagrangian = -g() * heavy() * light() ** 2 / 2

    operator = theory.fluctuation_operator(lagrangian)

    assert {canonical_string(field) for field in operator.basis} == {
        canonical_string(heavy()),
        canonical_string(light()),
    }
    assert_expr_equal(operator.entry(heavy, light), -g() * light())


def test_fluctuation_operator_rejects_basis_from_another_theory() -> None:
    left = Theory("fluctuation_left")
    left_phi = left.define_field("phi", s.Scalar, self_conjugate=True)
    right = Theory("fluctuation_right")
    right_phi = right.define_field("phi", s.Scalar, self_conjugate=True)
    basis = left.fluctuation_basis(left_phi() ** 2)

    with pytest.raises(ValueError, match="belongs to"):
        right.fluctuation_operator(right_phi() ** 2, basis)


def test_fluctuation_basis_modes_carry_statistics_and_mass_metadata() -> None:
    theory = Theory("fluctuation_mode_metadata")
    scalar = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    fermion = theory.define_field("psi", s.Fermion, self_conjugate=False, mass=(FieldMassKind.LIGHT, "m"))
    lagrangian = scalar() ** 2 + s.Bar(fermion()) * fermion()

    basis = theory.fluctuation_basis(lagrangian)
    scalar_mode = basis.mode_for(scalar)
    fermion_mode = basis.mode_for(fermion)
    barred_fermion_mode = basis.mode_for(s.Bar(fermion()))

    assert scalar_mode.mass_kind is FieldMassKind.HEAVY
    assert scalar_mode.statistics is FluctuationStatistics.BOSONIC
    assert scalar_mode.supertrace_sign == 1
    assert scalar_mode.self_conjugate is True
    assert scalar_mode.conjugated is False
    assert fermion_mode.mass_kind is FieldMassKind.LIGHT
    assert fermion_mode.statistics is FluctuationStatistics.FERMIONIC
    assert fermion_mode.supertrace_sign == -1
    assert fermion_mode.conjugated is False
    assert barred_fermion_mode.statistics is FluctuationStatistics.FERMIONIC
    assert barred_fermion_mode.conjugated is True
    assert basis.heavy_modes == (scalar_mode,)
    assert {canonical_string(mode.field) for mode in basis.light_modes} == {
        canonical_string(s.Bar(fermion())),
        canonical_string(fermion()),
    }


def test_fluctuation_operator_extracts_heavy_light_sector_blocks() -> None:
    theory = Theory("fluctuation_sector_blocks")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    g = theory.define_coupling("g", self_conjugate=True)
    lagrangian = -g() * heavy() * light() ** 2 / 2

    operator = theory.fluctuation_operator(lagrangian)
    heavy_light = operator.block(FluctuationSector.HEAVY, FluctuationSector.LIGHT)
    light_heavy = operator.block("light", "heavy")

    assert tuple(mode.field for mode in heavy_light.rows) == (heavy(),)
    assert tuple(mode.field for mode in heavy_light.columns) == (light(),)
    assert_expr_equal(heavy_light.entry(heavy, light), -g() * light())
    assert_expr_equal(light_heavy.entry(light, heavy), -g() * light())
    assert heavy_light.to_expression_map()


def test_fluctuation_operator_all_sector_block_preserves_full_matrix() -> None:
    theory = Theory("fluctuation_sector_all")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    lagrangian = heavy() ** 2 + light() ** 2

    operator = theory.fluctuation_operator(lagrangian)
    full = operator.block("all", "all")

    assert full.rows == operator.modes
    assert full.columns == operator.modes
    assert full.matrix == operator.matrix


def test_fluctuation_operator_rejects_unknown_sector_selector() -> None:
    theory = Theory("fluctuation_bad_sector")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True)
    operator = theory.fluctuation_operator(phi() ** 2)

    with pytest.raises(ValueError, match="fluctuation sector"):
        operator.block("bad", "heavy")


def test_fluctuation_operator_builds_supertrace_plan_from_sector_blocks() -> None:
    theory = Theory("fluctuation_supertrace_plan")
    heavy_scalar = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    heavy_fermion = theory.define_field("Psi", s.Fermion, self_conjugate=False, mass=(FieldMassKind.HEAVY, "MF"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = (
        heavy_scalar() ** 2
        + s.Bar(heavy_fermion()) * heavy_fermion()
        - y() * heavy_scalar() * light() ** 2 / 2
    )

    operator = theory.fluctuation_operator(lagrangian)
    plan = operator.supertrace_plan()

    assert plan.heavy_heavy == operator.block("heavy", "heavy")
    assert plan.heavy_light == operator.block("heavy", "light")
    assert plan.light_heavy == operator.block("light", "heavy")
    assert plan.light_light == operator.block("light", "light")
    assert plan.heavy_mode_count == 3
    assert plan.light_mode_count == 1
    assert plan.heavy_supertrace_sign == -1
    assert len(plan.blocks()) == 4
    assert plan.to_expression_map()


def test_supertrace_plan_builds_weighted_block_trace_with_symbolica_matrix_product() -> None:
    theory = Theory("supertrace_block_trace")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = heavy() ** 2 - y() * heavy() * light() ** 2 / 2

    plan = theory.fluctuation_operator(lagrangian).supertrace_plan()
    heavy_heavy = plan.block_trace("heavy_heavy", plan.heavy_heavy)
    heavy_light_mixing = plan.block_trace("heavy_light_light_heavy", plan.heavy_light, plan.light_heavy)

    assert heavy_heavy.order == 1
    assert heavy_heavy.block_sectors == ((FluctuationSector.HEAVY, FluctuationSector.HEAVY),)
    assert_expr_equal(heavy_heavy.expression, plan.heavy_heavy.entry(heavy, heavy))
    assert heavy_light_mixing.order == 2
    assert heavy_light_mixing.block_sectors == (
        (FluctuationSector.HEAVY, FluctuationSector.LIGHT),
        (FluctuationSector.LIGHT, FluctuationSector.HEAVY),
    )
    assert_expr_equal(heavy_light_mixing.expression, y() ** 2 * light() ** 2)
    assert heavy_light_mixing.to_expression_map()


def test_supertrace_plan_rejects_non_closed_block_trace() -> None:
    theory = Theory("supertrace_bad_block_trace")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    lagrangian = heavy() * light()

    plan = theory.fluctuation_operator(lagrangian).supertrace_plan()

    with pytest.raises(ValueError, match="closed mode chain"):
        plan.block_trace("open", plan.heavy_light)

    with pytest.raises(ValueError, match="matching column and row modes"):
        plan.block_trace("mismatched", plan.heavy_heavy, plan.light_heavy)
