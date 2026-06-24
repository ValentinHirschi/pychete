from __future__ import annotations

import json
from pathlib import Path

import pytest

from pychete import Theory, canonical_string, collect_indices, load_state, s
from pychete.state import PycheteState


def test_state_checkpoint_has_active_theory_and_theory_mapping() -> None:
    state = PycheteState()
    theory = Theory("state_model")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    lagrangian = theory.free_lag(phi)
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)

    payload = json.loads(state.to_json())

    assert payload["schema_version"] == 3
    assert payload["active_theory"] == "state_model"
    assert "state_model" in payload["theories"]
    assert "lagrangian" not in payload["theories"]["state_model"]
    assert payload["expressions"]["lagrangian"] == {
        "theory": "state_model",
        "expression": canonical_string(lagrangian),
    }


def test_state_checkpoint_round_trips_plain_index_labels(tmp_path: Path) -> None:
    state = PycheteState()
    theory = Theory("state_indices")
    flavor = theory.define_flavor_index("Flavor", 3)
    phi = theory.define_field("phi", s.Scalar, indices=[flavor.symbol], self_conjugate=True, mass=0)
    a = theory.index("a", flavor.symbol)
    mu = theory.lorentz_index("mu")
    lagrangian = phi(a, derivatives=[mu]) * phi(a, derivatives=[mu])
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    path = tmp_path / "pychete_state.json"

    state.save_state(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    theory_payload = payload["theories"]["state_indices"]
    expression_payload = payload["expressions"]["lagrangian"]["expression"]

    assert all(entry["role"] != "index" for entry in theory_payload["symbols"])
    assert "pychete::Index(python::a,state_indices::index_type_Flavor)" in expression_payload
    assert "pychete::Index(python::mu,pychete::Lorentz)" in expression_payload
    assert "state_indices::index_a" not in expression_payload
    assert "state_indices::index_mu" not in expression_payload
    assert "pychete::index_a" not in expression_payload
    assert "pychete::index_mu" not in expression_payload

    restored = load_state(path)
    restored_theory = restored.active
    restored_lagrangian = restored.get_expression("lagrangian")

    assert restored_theory is not None
    assert restored.expressions["lagrangian"].theory_name == "state_indices"
    assert "index:a" not in restored_theory._symbols
    assert "index:mu" not in restored_theory._symbols
    assert canonical_string(restored_lagrangian) == canonical_string(lagrangian)
    assert {canonical_string(info.label) for info in collect_indices(restored_lagrangian)} == {
        "python::a",
        "python::mu",
    }


def test_state_rejects_expression_against_wrong_theory() -> None:
    left = Theory("left_state")
    left_phi = left.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    right = Theory("right_state")
    right.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    lagrangian = left.free_lag(left_phi)
    state = PycheteState()
    state.add_theory(left)
    state.add_theory(right, active=False)

    with pytest.raises(ValueError, match="different theory"):
        state.add_expression("wrong", right, lagrangian)


def test_state_loading_rejects_expression_with_wrong_theory_metadata() -> None:
    left = Theory("left_load")
    left_phi = left.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    right = Theory("right_load")
    right.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    state = PycheteState()
    state.add_theory(left)
    state.add_theory(right, active=False)
    state.add_expression("lagrangian", left, left.free_lag(left_phi))
    payload = state.to_json_obj()
    payload["expressions"]["lagrangian"]["theory"] = "right_load"

    with pytest.raises(ValueError, match="different theory"):
        PycheteState.from_json_obj(payload)
