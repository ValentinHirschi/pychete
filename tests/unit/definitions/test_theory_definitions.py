from __future__ import annotations

import json

from pychete import Theory, canonical_string, s
from pychete.symbols import expression_from_canonical


def test_field_and_mass_coupling_definitions_follow_matchete_orders() -> None:
    theory = Theory("defs")
    flavor = theory.define_flavor_index("Flavor", 3)

    heavy = theory.define_field(
        "CapitalPhi",
        s.Scalar,
        indices=[flavor.symbol],
        mass=("Heavy", "MCapitalPhi", [flavor.symbol]),
    )
    light = theory.define_field(
        "psi",
        s.Fermion,
        indices=[flavor.symbol],
        mass=("Light", "mpsi", [flavor.symbol, flavor.symbol]),
    )

    assert theory.fields[heavy.name].heavy is True
    assert theory.couplings["MCapitalPhi"].eft_order == 0
    assert theory.couplings["mpsi"].eft_order == 1
    assert canonical_string(heavy(theory.index("f", flavor.symbol))).startswith("pychete::Field")
    assert canonical_string(light(theory.index("f", flavor.symbol))).startswith("pychete::Field")


def test_pretty_json_checkpoint_contains_full_lagrangian_expression() -> None:
    theory = Theory("json_scalar")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    lagrangian = theory.set_lagrangian(theory.free_lag(phi))

    payload = json.loads(theory.to_json())

    assert payload["schema_version"] == 1
    assert payload["theory_name"] == "json_scalar"
    assert payload["lagrangian"] == canonical_string(lagrangian)
    assert expression_from_canonical(payload["lagrangian"]).format_plain() == payload["lagrangian"]
