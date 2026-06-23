from __future__ import annotations

import json

from pychete import Theory, s
from pychete.state import PycheteState


def test_state_checkpoint_has_active_theory_and_theory_mapping() -> None:
    state = PycheteState()
    theory = Theory("state_model")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    theory.set_lagrangian(theory.free_lag(phi))
    state.add_theory(theory)

    payload = json.loads(state.to_json())

    assert payload["schema_version"] == 2
    assert payload["active_theory"] == "state_model"
    assert "state_model" in payload["theories"]
    assert payload["theories"]["state_model"]["lagrangian"] is not None
