from __future__ import annotations

import json
from pathlib import Path

import pytest

from pychete.loaders import load_python_model
from pychete.state import PycheteState
from pychete.validation_fixtures import load_validation_fixture


def _fixture_obj_from_model(path: Path) -> dict[str, object]:
    theory, expressions = load_python_model(path)
    state = PycheteState()
    state.add_theory(theory)
    for name, expression in expressions.items():
        state.add_expression(name, theory, expression)
    return {
        "schema_version": 1,
        "name": "vlf_toy_model_smoke",
        "kind": "model_smoke",
        "source": {
            "generator": "pytest",
            "mathematica_runtime_required": False,
        },
        "state": state.to_json_obj(),
        "expressions": sorted(expressions),
    }


def test_validation_fixture_restores_theory_before_expressions(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(_fixture_obj_from_model(Path("assets/models/VLF_toy_model.py"))), encoding="utf-8")

    fixture = load_validation_fixture(fixture_path)

    theory = fixture.theory()
    assert theory.name == "VLF_toy_model"
    assert {"A", "Psi", "psi", "phi"} <= set(theory.fields)
    theory._validate_registered_expression(fixture.expression("lagrangian"))


def test_validation_fixture_rejects_missing_expression_reference(tmp_path: Path) -> None:
    obj = _fixture_obj_from_model(Path("assets/models/VLF_toy_model.py"))
    obj["expressions"] = ["lagrangian", "off_shell_eft_lagrangian"]
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(obj), encoding="utf-8")

    with pytest.raises(ValueError, match="missing expressions"):
        load_validation_fixture(fixture_path)


def test_default_matching_target_manifest_lists_initial_models() -> None:
    manifest = json.loads(Path("assets/validation/matchete/default_matching_targets.json").read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 1
    assert [model["name"] for model in manifest["models"]] == [
        "VLF_toy_model",
        "Singlet_Scalar_Extension",
        "E_VLL",
        "S1S3LQs",
    ]
    assert all(model["status"] == "pending_fixture" for model in manifest["models"])
