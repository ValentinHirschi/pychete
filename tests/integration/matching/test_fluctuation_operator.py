from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import FieldMassKind, Theory, canonical_string, s

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
