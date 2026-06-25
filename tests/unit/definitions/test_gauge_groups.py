from __future__ import annotations

import json

from pychete import FieldMassKind, Theory, canonical_string, s
from pychete.expr import derivative_indices_expr, internal_indices_expr, lorentz_indices_expr

from tests.conftest import assert_expr_equal


def test_abelian_charge_metadata_is_stored_on_field_symbols() -> None:
    theory = Theory("u1_charges")
    theory.define_gauge_group("U1e", s.U1, "e", "A")
    charge = theory.gauge_charge("U1e", 1)
    psi = theory.define_field("psi", s.Fermion, charges=[charge.expr], mass=(FieldMassKind.HEAVY, "M"))

    assert psi.definition.charge_exprs == (charge.expr,)
    assert psi.label.get_symbol_data("charges") == [charge.expr]
    assert canonical_string(charge.expr) == "u1_charges::group_U1e(1)"


def test_gauge_group_and_charges_round_trip_through_json() -> None:
    theory = Theory("u1_json")
    theory.define_gauge_group("U1e", s.U1, "e", "A")
    charge = theory.gauge_charge("U1e", 1)
    theory.define_field("psi", s.Fermion, charges=[charge.expr], mass=0)

    restored = Theory.from_json_obj(json.loads(theory.to_json()))
    restored_charge = restored.gauge_charge("U1e", 1)

    assert restored.groups == theory.groups
    assert restored.fields["psi"].charge_exprs == (restored_charge.expr,)


def test_u1_vector_free_lagrangian_has_gauge_coupling_normalization() -> None:
    theory = Theory("u1_free")
    theory.define_gauge_group("U1e", s.U1, "e", "A")
    vector = theory.field_handle("A")
    e = theory.coupling_handle("e")
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    strength = s.FieldStrength(vector.label, lorentz_indices_expr(mu, nu), internal_indices_expr(), derivative_indices_expr())

    assert_expr_equal(theory.free_lag("A"), -strength**2 / (4 * e() ** 2))
