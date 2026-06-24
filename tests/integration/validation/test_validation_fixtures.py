from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from symbolica import Expression
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
    assert all(model["status"] == "matching_fixture_committed" for model in models)
    for model in models:
        assert Path(model["model_asset"]).is_file()
        assert Path(model["model_fixture"]).is_file()
        if matching_fixture := model.get("matching_fixture"):
            assert Path(matching_fixture).is_file()
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
        assert "lagrangian" in fixture.expression_names
        theory._validate_registered_expression(fixture.expression("lagrangian"))
        if fixture.source.get("parent_assets"):
            assert fixture.source["parent_lagrangian_included"] is False
        theory.symbol_manifest()


def test_committed_default_matching_fixtures_load_structured_results_without_mathematica() -> None:
    expected = {
        "VLF_toy_model": {"supertraces": 13, "conditions": 0},
        "Singlet_Scalar_Extension": {"supertraces": 24, "conditions": 72},
        "E_VLL": {"supertraces": 50, "conditions": 72},
        "S1S3LQs": {"supertraces": 27, "conditions": 72},
    }

    for model, counts in expected.items():
        fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.matching_fixture.json"))
        result = fixture.matching_result("matchete_previous")

        assert fixture.kind == "matching_result"
        assert fixture.source["matchete_runtime_required"] is False
        assert fixture.source["matching_condition_count"] == counts["conditions"]
        assert result.theory.name == model
        assert result.metadata["loop_order"] == 1
        assert result.metadata["eft_order"] == 6
        assert len(result.supertraces) == counts["supertraces"]
        assert len(result.matching_conditions) == counts["conditions"]
        result.compare_to(result).assert_equal()
        result.validate()


def test_default_model_fixtures_build_first_one_loop_setup_kernel_without_mathematica() -> None:
    for model in ("VLF_toy_model", "Singlet_Scalar_Extension", "E_VLL", "S1S3LQs"):
        fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.model_fixture.json"))
        theory = fixture.theory()
        setup = theory.one_loop_setup(fixture.expression("lagrangian"), eft_order=6, max_trace_order=1)

        assert setup.supertrace_kernel_count == 1
        assert tuple(trace.name for trace in setup.block_traces) == ("heavy-heavy",)
        assert setup.fluctuation_operator.modes
        theory._validate_registered_expression(setup.block_traces[0].expression)


def test_matching_result_comparison_reports_canonical_differences() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.matching_fixture.json"))
    reference = fixture.matching_result("matchete_previous")
    candidate = replace(
        reference,
        on_shell_eft_lagrangian=reference.on_shell_eft_lagrangian + Expression.num(1),
    )

    comparison = candidate.compare_to(reference, names=("on_shell_eft_lagrangian",))

    assert comparison.equal is False
    assert comparison.failed_names == ("on_shell_eft_lagrangian",)
    with pytest.raises(AssertionError, match="on_shell_eft_lagrangian"):
        comparison.assert_equal()
