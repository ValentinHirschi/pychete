from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from symbolica import Expression, S
import pytest

from pychete import OneLoopIntegralBackend
from pychete.loaders import load_python_model
from pychete.matching import MatchingResult, VakintIntegralStage
from pychete.state import PycheteState
from pychete.symbols import canonical_string
from pychete.validation_fixtures import load_validation_fixture
from tests.conftest import assert_expr_equal


class FakeNamedVakintEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Expression, bool | None]] = []

    def to_canonical(self, expr: Expression, short_form: bool | None = None) -> Expression:
        self.calls.append(("to_canonical", expr, short_form))
        return S("fixture_canonical")(expr)


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
    expected_theory, _expected_expressions = load_python_model(Path("assets/models/VLF_toy_model.py"))

    theory = fixture.theory()
    assert fixture.kind == "model_definition"
    assert fixture.source["generator"] == "helper_mathematica_scripts/convert_matchete_model_state.py"
    assert fixture.source["upstream_generator"] == "export_matchete_model_state.wls"
    assert fixture.source["matchete_runtime_required"] is False
    assert fixture.source["warnings"] == []
    assert theory.to_json_obj() == expected_theory.to_json_obj()
    theory._validate_registered_expression(fixture.expression("lagrangian"))
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


def test_default_model_fixtures_build_order_three_one_loop_preview_without_mathematica() -> None:
    expected = {
        "VLF_toy_model": {"kernels": 25, "contributions": 11, "supertraces": 47},
        "Singlet_Scalar_Extension": {"kernels": 25, "contributions": 11, "supertraces": 47},
        "E_VLL": {"kernels": 25, "contributions": 11, "supertraces": 47},
        "S1S3LQs": {"kernels": 25, "contributions": 11, "supertraces": 47},
    }

    for model, counts in expected.items():
        fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.model_fixture.json"))
        preview = fixture.one_loop_preview(max_trace_order=3)

        assert preview.metadata["stage"] == "interaction_power_type_vakint_result"
        assert preview.metadata["complete"] is False
        assert preview.metadata["uses_interaction_operator"] is True
        assert preview.metadata["fixture"] == fixture.name
        assert preview.metadata["fixture_kind"] == "model_definition"
        assert preview.metadata["lagrangian_expression"] == "lagrangian"
        assert preview.metadata["supertrace_kernel_count"] == counts["kernels"]
        assert preview.metadata["power_type_contribution_count"] == counts["contributions"]
        assert preview.metadata["interaction_power_type_contribution_count"] == counts["contributions"]
        assert preview.metadata["named_supertrace_stage"] == "raw"
        assert len(preview.supertraces) == counts["supertraces"]
        preview.validate()


def test_validation_fixture_preview_can_stage_named_supertraces_with_vakint_engine() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    raw_preview = fixture.one_loop_preview(max_trace_order=1)
    engine = FakeNamedVakintEngine()

    canonical_named_preview = fixture.one_loop_preview(
        max_trace_order=1,
        named_supertrace_stage=VakintIntegralStage.CANONICAL,
        named_supertrace_short_form=True,
        named_supertrace_engine=engine,
    )

    assert canonical_named_preview.metadata["vakint_stage"] == "raw"
    assert canonical_named_preview.metadata["named_supertrace_stage"] == "canonical"
    assert engine.calls == [("to_canonical", raw_preview.expression("hScalar"), True)]
    assert canonical_named_preview.expression("hScalar").format_plain() == (
        S("fixture_canonical")(raw_preview.expression("hScalar")).format_plain()
    )
    assert (
        canonical_named_preview.off_shell_eft_lagrangian.format_plain()
        == raw_preview.off_shell_eft_lagrangian.format_plain()
    )


def test_validation_fixture_preview_can_use_internal_integral_backend_without_mathematica() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))

    preview = fixture.one_loop_preview(
        max_trace_order=1,
        integral_backend=OneLoopIntegralBackend.INTERNAL,
        internal_tensor_reduce=False,
        internal_combine_terms=True,
    )

    assert preview.metadata["stage"] == "interaction_power_type_internal_integral_result"
    assert preview.metadata["integral_backend"] == "pychete_internal"
    assert preview.metadata["tensor_reduce"] is False
    assert preview.metadata["combine_terms"] is True
    assert preview.metadata["fixture"] == fixture.name
    assert "interaction_power_type_internal_integral_sum" in preview.expression_names()
    assert "interaction_power_type_internal_integral_pole_part" in preview.expression_names()
    preview.validate()


def test_validation_fixture_preview_can_use_internal_minimal_subtraction_backend_without_mathematica() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    reference_fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.matching_fixture.json"))
    reference = reference_fixture.matching_result("matchete_previous")

    preview = fixture.one_loop_preview(
        max_trace_order=1,
        integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
        internal_tensor_reduce=False,
        internal_combine_terms=True,
    )
    report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="VLF_toy_model.matchete_previous",
        max_trace_order=1,
        integral_backend="internal_minimal_subtraction",
        internal_tensor_reduce=False,
        internal_combine_terms=True,
    )

    assert preview.metadata["stage"] == "interaction_power_type_internal_minimal_subtraction_result"
    assert preview.metadata["integral_backend"] == "pychete_internal"
    assert preview.metadata["subtraction_scheme"] == "minimal_subtraction_preview"
    assert preview.metadata["poles_subtracted"] is True
    assert preview.metadata["tensor_reduce"] is False
    assert preview.metadata["combine_terms"] is True
    assert preview.metadata["fixture"] == fixture.name
    assert "interaction_power_type_internal_integral_ms_counterterm" in preview.expression_names()
    assert_expr_equal(
        preview.off_shell_eft_lagrangian,
        preview.expression("interaction_power_type_internal_integral_finite_part"),
    )
    assert_expr_equal(
        preview.on_shell_eft_lagrangian,
        preview.expression("interaction_power_type_internal_integral_finite_part"),
    )
    assert report.candidate_stage == "interaction_power_type_internal_minimal_subtraction_result"
    assert "interaction_power_type_internal_integral_ms_counterterm" in report.candidate_supertrace_names
    assert report.reference_stage is None


def test_default_matching_target_gap_reports_track_current_one_loop_coverage() -> None:
    expected = {
        "VLF_toy_model": {
            "reference_supertraces": 13,
            "conditions": 0,
            "candidate_supertraces": 47,
            "common": {
                "hFermion-lFermion",
                "hFermion-lFermion-lScalar",
                "hFermion-lScalar",
                "hFermion-lScalar-lFermion",
                "hFermion-lScalar-lScalar",
            },
            "canonical_equal": set(),
        },
        "Singlet_Scalar_Extension": {
            "reference_supertraces": 24,
            "conditions": 72,
            "candidate_supertraces": 47,
            "common": {
                "hScalar",
                "hScalar-hScalar",
                "hScalar-hScalar-hScalar",
                "hScalar-hScalar-lScalar",
                "hScalar-lScalar",
                "hScalar-lScalar-lScalar",
            },
            "canonical_equal": set(),
        },
        "E_VLL": {
            "reference_supertraces": 50,
            "conditions": 72,
            "candidate_supertraces": 47,
            "common": {
                "hFermion-lFermion",
                "hFermion-lFermion-lFermion",
                "hFermion-lFermion-lScalar",
                "hFermion-lScalar",
                "hFermion-lScalar-lFermion",
                "hFermion-lScalar-lScalar",
            },
            "canonical_equal": {
                "hFermion-lFermion-lFermion",
                "hFermion-lFermion-lScalar",
                "hFermion-lScalar-lFermion",
            },
        },
        "S1S3LQs": {
            "reference_supertraces": 27,
            "conditions": 72,
            "candidate_supertraces": 47,
            "common": {
                "hScalar",
                "hScalar-hScalar",
                "hScalar-hScalar-hScalar",
                "hScalar-hScalar-lFermion",
                "hScalar-lFermion",
                "hScalar-lFermion-lFermion",
                "hScalar-lFermion-lScalar",
                "hScalar-lScalar",
                "hScalar-lScalar-lFermion",
            },
            "canonical_equal": {
                "hScalar-lFermion-lScalar",
                "hScalar-lScalar",
                "hScalar-lScalar-lFermion",
            },
        },
    }

    for model, expected_counts in expected.items():
        model_fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.model_fixture.json"))
        reference_fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.matching_fixture.json"))
        reference = reference_fixture.matching_result("matchete_previous")

        report = model_fixture.one_loop_preview_gap_report(
            reference,
            reference_name=f"{model}.matchete_previous",
            max_trace_order=3,
        )
        report_obj = report.to_json_obj()

        assert report.complete is False
        assert report.candidate_stage == "interaction_power_type_vakint_result"
        assert report.reference_stage is None
        assert report.candidate_supertrace_count == expected_counts["candidate_supertraces"]
        assert report.reference_supertrace_count == expected_counts["reference_supertraces"]
        assert set(report.common_supertrace_names) == expected_counts["common"]
        assert set(report.canonical_equal_common_supertrace_names) == expected_counts["canonical_equal"]
        assert set(report.canonical_different_common_supertrace_names) == (
            expected_counts["common"] - expected_counts["canonical_equal"]
        )
        assert report.canonical_equal_common_supertrace_count == len(expected_counts["canonical_equal"])
        assert report.canonical_different_common_supertrace_count == (
            len(expected_counts["common"]) - len(expected_counts["canonical_equal"])
        )
        assert report.missing_reference_supertrace_count == (
            expected_counts["reference_supertraces"] - len(expected_counts["common"])
        )
        assert len(report.candidate_only_supertrace_names) == (
            expected_counts["candidate_supertraces"] - len(expected_counts["common"])
        )
        assert report.candidate_matching_condition_count == 0
        assert report.reference_matching_condition_count == expected_counts["conditions"]
        assert len(report.common_matching_condition_names) == 0
        assert report.missing_reference_matching_condition_count == expected_counts["conditions"]
        assert set(report.common_expression_names) == expected_counts["common"] | {
            "uv_lagrangian",
            "off_shell_eft_lagrangian",
            "on_shell_eft_lagrangian",
        }
        assert report_obj["complete"] is False
        assert report_obj["common_supertrace_count"] == len(expected_counts["common"])
        assert report_obj["canonical_equal_common_supertrace_count"] == len(expected_counts["canonical_equal"])
        assert report_obj["canonical_different_common_supertrace_count"] == (
            len(expected_counts["common"]) - len(expected_counts["canonical_equal"])
        )
        assert report_obj["missing_reference_supertrace_count"] == (
            expected_counts["reference_supertraces"] - len(expected_counts["common"])
        )
        assert report_obj["missing_reference_matching_condition_count"] == expected_counts["conditions"]


def test_default_matching_target_gap_reports_track_internal_ms_one_loop_coverage() -> None:
    expected = {
        "VLF_toy_model": {
            "reference_supertraces": 13,
            "conditions": 0,
            "common": {
                "hFermion-lFermion",
                "hFermion-lFermion-lScalar",
                "hFermion-lScalar",
                "hFermion-lScalar-lFermion",
                "hFermion-lScalar-lScalar",
            },
            "canonical_equal": set(),
        },
        "Singlet_Scalar_Extension": {
            "reference_supertraces": 24,
            "conditions": 72,
            "common": {
                "hScalar",
                "hScalar-hScalar",
                "hScalar-hScalar-hScalar",
                "hScalar-hScalar-lScalar",
                "hScalar-lScalar",
                "hScalar-lScalar-lScalar",
            },
            "canonical_equal": set(),
        },
        "E_VLL": {
            "reference_supertraces": 50,
            "conditions": 72,
            "common": {
                "hFermion-lFermion",
                "hFermion-lFermion-lFermion",
                "hFermion-lFermion-lScalar",
                "hFermion-lScalar",
                "hFermion-lScalar-lFermion",
                "hFermion-lScalar-lScalar",
            },
            "canonical_equal": {
                "hFermion-lFermion-lFermion",
                "hFermion-lFermion-lScalar",
                "hFermion-lScalar-lFermion",
            },
        },
        "S1S3LQs": {
            "reference_supertraces": 27,
            "conditions": 72,
            "common": {
                "hScalar",
                "hScalar-hScalar",
                "hScalar-hScalar-hScalar",
                "hScalar-hScalar-lFermion",
                "hScalar-lFermion",
                "hScalar-lFermion-lFermion",
                "hScalar-lFermion-lScalar",
                "hScalar-lScalar",
                "hScalar-lScalar-lFermion",
            },
            "canonical_equal": {
                "hScalar-lFermion-lScalar",
                "hScalar-lScalar",
                "hScalar-lScalar-lFermion",
            },
        },
    }

    for model, expected_counts in expected.items():
        model_fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.model_fixture.json"))
        reference_fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.matching_fixture.json"))
        reference = reference_fixture.matching_result("matchete_previous")

        report = model_fixture.one_loop_preview_gap_report(
            reference,
            reference_name=f"{model}.matchete_previous",
            max_trace_order=3,
            integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
            internal_tensor_reduce=False,
            internal_combine_terms=True,
        )
        report_obj = report.to_json_obj()

        assert report.complete is False
        assert report.candidate_stage == "interaction_power_type_internal_minimal_subtraction_result"
        assert report.reference_stage is None
        assert report.candidate_supertrace_count == 50
        assert report.reference_supertrace_count == expected_counts["reference_supertraces"]
        assert set(report.common_supertrace_names) == expected_counts["common"]
        assert set(report.canonical_equal_common_supertrace_names) == expected_counts["canonical_equal"]
        assert set(report.canonical_different_common_supertrace_names) == (
            expected_counts["common"] - expected_counts["canonical_equal"]
        )
        assert report.numeric_probe_equal_common_supertrace_count == 0
        assert report.numeric_probe_different_common_supertrace_count == 0
        assert "interaction_power_type_internal_integral_sum" in report.candidate_only_supertrace_names
        assert "interaction_power_type_internal_integral_ms_counterterm" in report.candidate_only_supertrace_names
        assert report.missing_reference_supertrace_count == (
            expected_counts["reference_supertraces"] - len(expected_counts["common"])
        )
        assert report.candidate_matching_condition_count == 0
        assert report.reference_matching_condition_count == expected_counts["conditions"]
        assert report.missing_reference_matching_condition_count == expected_counts["conditions"]
        assert set(report.common_expression_names) == expected_counts["common"] | {
            "uv_lagrangian",
            "off_shell_eft_lagrangian",
            "on_shell_eft_lagrangian",
        }
        assert report_obj["candidate_supertrace_count"] == 50
        assert report_obj["numeric_probe_equal_common_supertrace_count"] == 0


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
