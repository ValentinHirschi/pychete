from __future__ import annotations

import json
from pathlib import Path

import pytest

from pychete.loaders import load_python_model
from pychete.matching import MatchingResult
from pychete.state import PycheteState
from pychete.symbols import canonical_string
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
        "matching_results": {
            "default": {
                "theory": theory.name,
                "uv_lagrangian": "lagrangian",
                "off_shell_eft_lagrangian": "lagrangian",
                "on_shell_eft_lagrangian": "lagrangian",
                "matching_conditions": {
                    "toy_condition": "lagrangian",
                },
                "fluctuation_operators": {
                    "toy_operator": "lagrangian",
                },
                "supertraces": {
                    "toy_supertrace": "lagrangian",
                },
                "metadata": {
                    "loop_order": 1,
                    "fixture": True,
                },
            },
        },
    }


def test_validation_fixture_restores_theory_before_expressions(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(_fixture_obj_from_model(Path("assets/models/VLF_toy_model.py"))), encoding="utf-8")

    fixture = load_validation_fixture(fixture_path)

    theory = fixture.theory()
    assert theory.name == "VLF_toy_model"
    assert {"A", "Psi", "psi", "phi"} <= set(theory.fields)
    theory._validate_registered_expression(fixture.expression("lagrangian"))


def test_committed_vlf_model_fixture_is_mathematica_independent() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    expected_theory, expected_expressions = load_python_model(Path("assets/models/VLF_toy_model.py"))

    theory = fixture.theory()
    assert fixture.kind == "model_definition"
    assert fixture.source["matchete_runtime_required"] is False
    assert theory.to_json_obj() == expected_theory.to_json_obj()
    assert canonical_string(fixture.expression("lagrangian")) == canonical_string(expected_expressions["lagrangian"])
    assert canonical_string(theory.fields["Psi"].charge_exprs[0]) == "VLF_toy_model::group_U1e(1)"


def test_validation_fixture_restores_structured_matching_result(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(_fixture_obj_from_model(Path("assets/models/VLF_toy_model.py"))), encoding="utf-8")

    result = load_validation_fixture(fixture_path).matching_result()

    assert isinstance(result, MatchingResult)
    assert result.theory.name == "VLF_toy_model"
    assert result.metadata["loop_order"] == 1
    assert result.expression("toy_supertrace").format_plain() == result.uv_lagrangian.format_plain()
    result.validate()


def test_validation_fixture_rejects_missing_expression_reference(tmp_path: Path) -> None:
    obj = _fixture_obj_from_model(Path("assets/models/VLF_toy_model.py"))
    obj["expressions"] = ["lagrangian", "off_shell_eft_lagrangian"]
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(obj), encoding="utf-8")

    with pytest.raises(ValueError, match="missing expressions"):
        load_validation_fixture(fixture_path)


def test_validation_fixture_rejects_missing_matching_result_expression(tmp_path: Path) -> None:
    obj = _fixture_obj_from_model(Path("assets/models/VLF_toy_model.py"))
    matching_results = obj["matching_results"]
    assert isinstance(matching_results, dict)
    default = matching_results["default"]
    assert isinstance(default, dict)
    default["supertraces"] = {"broken": "missing_supertrace"}
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(obj), encoding="utf-8")

    with pytest.raises(ValueError, match="missing expression"):
        load_validation_fixture(fixture_path)


def test_default_matching_target_manifest_lists_initial_models() -> None:
    manifest = json.loads(Path("assets/validation/matchete/default_matching_targets.json").read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 1
    models = manifest["models"]
    assert [model["name"] for model in manifest["models"]] == [
        "VLF_toy_model",
        "Singlet_Scalar_Extension",
        "E_VLL",
        "S1S3LQs",
    ]
    assert all(model["status"] == "pending_matching_fixture" for model in models)
    for model in models:
        assert Path(model["model_asset"]).is_file()
        assert Path(model["model_fixture"]).is_file()
        for parent_asset in model["parent_assets"]:
            assert Path(parent_asset).is_file()


def test_default_model_definition_fixtures_load_without_mathematica() -> None:
    expected_fields = {
        "VLF_toy_model": {"A", "Psi", "psi", "phi"},
        "Singlet_Scalar_Extension": {"B", "G", "H", "W", "phi", "q", "u", "d", "l", "e"},
        "E_VLL": {"B", "EE", "G", "H", "W", "q", "u", "d", "l", "e"},
        "S1S3LQs": {"B", "G", "H", "S1", "S3", "W", "q", "u", "d", "l", "e"},
    }

    for model, fields in expected_fields.items():
        fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.model_fixture.json"))
        theory = fixture.theory()
        assert fixture.kind == "model_definition"
        assert fixture.source["matchete_runtime_required"] is False
        assert theory.name == model
        assert fields <= set(theory.fields)
        theory.symbol_manifest()
