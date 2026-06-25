from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from symbolica import Expression, S
import pytest

from pychete import (
    ExternalKind,
    OneLoopIntegralBackend,
    OneLoopMatchOptions,
    OneLoopNormalization,
    OneLoopSetup,
    SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES,
    Theory,
    ValidationFixture,
    one_loop_normalization_factor,
    registered_wilson_matching_condition_targets,
)
from pychete.backends import spenso as spenso_backend
from pychete.backends import vacuum_integrals
from pychete.backends import vakint as vakint_backend
from pychete.loaders import load_python_model
from pychete.matching import MatchingResult, VakintIntegralStage
from pychete.state import PycheteState
from pychete.symbols import canonical_string, s
from pychete.validation_fixtures import load_validation_fixture
from tests.conftest import assert_expr_equal


class FakeNamedVakintEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Expression, bool | None]] = []

    def to_canonical(self, expr: Expression, short_form: bool | None = None) -> Expression:
        self.calls.append(("to_canonical", expr, short_form))
        return S("fixture_canonical")(expr)


class FakePoleVakintEngine:
    def __init__(self, evaluated: Expression) -> None:
        self.evaluated = evaluated
        self.calls: list[Expression] = []

    def evaluate(self, expr: Expression) -> Expression:
        self.calls.append(expr)
        return self.evaluated


class FakeTensorNetwork:
    def __init__(self, expr: Expression) -> None:
        self.expr = expr


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


def test_committed_matching_fixtures_store_smeft_wilson_metadata() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json"))
    theory = fixture.theory()
    result = fixture.matching_result("matchete_previous")
    targets = {target.name: target for target in result.matching_condition_targets()}
    chd = theory.external_handle("cHd")
    chd_indices = chd.definition.index_exprs
    chd_name = canonical_string(s.Coupling(chd.label, s.List(*chd_indices), Expression.num(0)))
    wilsons_with_operators = {
        name
        for name, external in theory.externals.items()
        if external.kind is ExternalKind.WILSON_COEFFICIENT and external.operator_expr is not None
    }

    assert wilsons_with_operators == set(SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES)
    assert set(registered_wilson_matching_condition_targets(theory)) == {
        target.name for target in result.matching_condition_targets() if target.is_wilson_coefficient
    }
    assert theory.external_handle("cHB").definition.kind is ExternalKind.WILSON_COEFFICIENT
    assert theory.external_handle("cHB").definition.basis_name == "SMEFT"
    assert theory.external_handle("cHB").definition.index_exprs == ()
    assert theory.external_handle("cHB").definition.operator_expr is not None
    assert "field_B" in canonical_string(theory.external_handle("cHB").definition.operator_expr)
    assert theory.external_handle("cHd").definition.kind is ExternalKind.WILSON_COEFFICIENT
    assert theory.external_handle("cHd").definition.basis_name == "SMEFT"
    assert len(theory.external_handle("cHd").definition.index_exprs) == 2
    assert theory.external_handle("cHd").definition.operator_expr is not None
    assert "field_d" in canonical_string(theory.external_handle("cHd").definition.operator_expr)
    assert theory.external_handle("ceW").definition.operator_expr is not None
    assert "pychete::Sigma" in canonical_string(theory.external_handle("ceW").definition.operator_expr)
    assert theory.external_handle("Delta").definition.kind is ExternalKind.GENERIC
    assert "gL" not in theory.externals
    assert targets[chd_name].is_wilson_coefficient is True
    assert targets[chd_name].basis == "SMEFT"
    assert targets[chd_name].external_kind is ExternalKind.WILSON_COEFFICIENT
    assert len(targets[chd_name].indices) == 2
    assert targets[chd_name].eft_order == 0
    assert targets[chd_name].operator is not None
    assert targets[chd_name].projection_expression == targets[chd_name].operator


def test_committed_model_fixtures_store_matching_smeft_wilson_metadata() -> None:
    for model in ("Singlet_Scalar_Extension", "E_VLL", "S1S3LQs"):
        model_fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.model_fixture.json"))
        matching_fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.matching_fixture.json"))
        model_theory = model_fixture.theory()
        matching_theory = matching_fixture.theory()
        model_wilsons = {
            name
            for name, external in model_theory.externals.items()
            if external.kind is ExternalKind.WILSON_COEFFICIENT
        }

        assert model_wilsons == set(SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES)
        assert model_fixture.source["smeft_wilson_metadata"]["source"] == "matching_fixture_symbol_metadata"
        assert model_fixture.source["smeft_wilson_metadata"]["wilson_count"] == 64
        for name in model_wilsons:
            assert model_theory.external_handle(name).definition.to_json() == (
                matching_theory.external_handle(name).definition.to_json()
            )
            assert model_theory.external_handle(name).definition.operator_expr is not None


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
        fixture_path = Path(f"assets/validation/pychete/{model}.matching_fixture.json")
        fixture_json = fixture_path.read_text(encoding="utf-8")
        fixture = load_validation_fixture(fixture_path)
        result = fixture.matching_result("matchete_previous")
        canonical_payload = "\n".join(
            canonical_string(expression)
            for expression in (
                result.off_shell_eft_lagrangian,
                result.on_shell_eft_lagrangian,
                *result.matching_conditions.values(),
                *result.supertraces.values(),
            )
        )

        assert fixture.kind == "matching_result"
        assert fixture.source["matchete_runtime_required"] is False
        assert fixture.source["matching_condition_count"] == counts["conditions"]
        assert "external_LF" not in fixture_json
        assert "external_LF" not in canonical_payload
        if model == "S1S3LQs":
            assert "pychete::LoopFunction" in fixture_json
            assert "pychete::LoopFunction" in canonical_payload
        assert result.theory.name == model
        assert result.metadata["loop_order"] == 1
        assert result.metadata["eft_order"] == 6
        assert len(result.supertraces) == counts["supertraces"]
        assert len(result.matching_conditions) == counts["conditions"]
        result.compare_to(result).assert_equal()
        result.validate()


def test_default_model_fixtures_build_order_three_one_loop_preview_without_mathematica() -> None:
    expected = {
        "VLF_toy_model": {"kernels": 45, "contributions": 18, "supertraces": 75},
        "Singlet_Scalar_Extension": {"kernels": 45, "contributions": 18, "supertraces": 75},
        "E_VLL": {"kernels": 45, "contributions": 18, "supertraces": 75},
        "S1S3LQs": {"kernels": 45, "contributions": 18, "supertraces": 75},
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
        assert preview.metadata["tensor_networks_evaluated"] is False
        assert len(preview.supertraces) == counts["supertraces"]
        if model == "S1S3LQs":
            for trace_name in ("hScalar-lFermion-lScalar", "hScalar-lScalar-lFermion"):
                trace_text = canonical_string(preview.expression(trace_name))
                assert "pychete::eft_order_parameter" not in trace_text
                assert "der(" not in trace_text
        preview.validate()


def test_validation_fixture_preview_can_evaluate_tensor_networks_with_stored_cg_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/S1S3LQs.model_fixture.json"))
    calls: list[tuple[Expression, object | None]] = []

    def fake_evaluate_tensor_network(
        expr: Expression,
        *,
        library: object | None = None,
        function_library: object | None = None,
        n_steps: int | None = None,
        mode: object | None = None,
    ) -> FakeTensorNetwork:
        calls.append((expr, library))
        return FakeTensorNetwork(expr)

    def fake_tensor_network_result_scalar(network: FakeTensorNetwork) -> Expression:
        return S("tensor")(network.expr)

    monkeypatch.setattr(spenso_backend, "evaluate_tensor_network", fake_evaluate_tensor_network)
    monkeypatch.setattr(spenso_backend, "tensor_network_result_scalar", fake_tensor_network_result_scalar)

    preview = fixture.one_loop_preview(max_trace_order=1, evaluate_tensor_networks=True)

    assert preview.metadata["tensor_networks_evaluated"] is True
    assert preview.metadata["tensor_network_cg_component_source"] == "stored"
    assert preview.metadata["tensor_network_native_hep_cg_builtins"] is False
    assert calls
    assert len(calls) == preview.metadata["supertrace_kernel_count"]
    assert all(type(library).__name__ == "TensorLibrary" for _expr, library in calls)
    assert all("pychete::CG" not in canonical_string(expr) for expr, _library in calls)


def test_validation_fixture_preview_can_simplify_pychete_color_algebra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/S1S3LQs.model_fixture.json"))
    calls: list[dict[str, object]] = []

    def fake_simplify_index_algebra(self: OneLoopSetup, **kwargs: object) -> OneLoopSetup:
        calls.append(kwargs)
        return self

    monkeypatch.setattr(OneLoopSetup, "simplify_index_algebra", fake_simplify_index_algebra)

    preview = fixture.one_loop_preview(max_trace_order=1, simplify_pychete_color_algebra=True)

    assert calls == [
        {
            "expand": False,
            "gamma": False,
            "color": False,
            "pychete_color": True,
            "metrics": False,
            "dots": False,
        }
    ]
    assert preview.metadata["pychete_color_algebra_simplified"] is True


def test_public_one_loop_match_can_evaluate_fixture_tensor_networks_with_stored_cg_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/S1S3LQs.model_fixture.json"))
    calls: list[tuple[Expression, object | None]] = []

    def fake_evaluate_tensor_network(
        expr: Expression,
        *,
        library: object | None = None,
        function_library: object | None = None,
        n_steps: int | None = None,
        mode: object | None = None,
    ) -> FakeTensorNetwork:
        calls.append((expr, library))
        return FakeTensorNetwork(expr)

    def fake_tensor_network_result_scalar(network: FakeTensorNetwork) -> Expression:
        return S("tensor")(network.expr)

    monkeypatch.setattr(spenso_backend, "evaluate_tensor_network", fake_evaluate_tensor_network)
    monkeypatch.setattr(spenso_backend, "tensor_network_result_scalar", fake_tensor_network_result_scalar)

    result = fixture.theory().match(
        fixture.expression("lagrangian"),
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            evaluate_tensor_networks=True,
        ),
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["tensor_networks_evaluated"] is True
    assert result.metadata["tensor_network_cg_component_source"] == "stored"
    assert result.metadata["tensor_network_native_hep_cg_builtins"] is False
    assert calls
    assert len(calls) == result.metadata["supertrace_kernel_count"]
    assert all(type(library).__name__ == "TensorLibrary" for _expr, library in calls)
    assert all("pychete::CG" not in canonical_string(expr) for expr, _library in calls)


def test_validation_fixture_preview_can_apply_vakint_normalization_without_mathematica() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    raw = fixture.one_loop_preview(max_trace_order=1)
    normalized = fixture.one_loop_preview(
        max_trace_order=1,
        normalization=OneLoopNormalization.MATCHETE_HBAR,
    )
    factor = one_loop_normalization_factor(OneLoopNormalization.MATCHETE_HBAR)

    assert normalized.metadata["stage"] == "interaction_power_type_normalized_vakint_result"
    assert normalized.metadata["loop_normalization"] == "matchete_hbar"
    assert normalized.metadata["fixture"] == fixture.name
    assert normalized.metadata["fixture_kind"] == fixture.kind
    assert_expr_equal(normalized.expression("interaction_power_type_loop_normalization_factor"), factor)
    assert_expr_equal(
        normalized.expression("interaction_power_type_vakint_integral_sum_unnormalized"),
        raw.expression("interaction_power_type_vakint_integral_sum"),
    )
    assert_expr_equal(normalized.expression("hFermion[unnormalized]"), raw.expression("hFermion"))
    assert_expr_equal(normalized.expression("hFermion"), factor * raw.expression("hFermion"))
    assert_expr_equal(normalized.on_shell_eft_lagrangian, factor * raw.on_shell_eft_lagrangian)


def test_validation_fixture_preview_can_apply_internal_normalization_without_mathematica() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    factor = S("fixture_internal_loop_factor")
    raw = fixture.one_loop_preview(
        max_trace_order=1,
        integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
    )
    normalized = fixture.one_loop_preview(
        max_trace_order=1,
        integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
        normalization=factor,
    )

    assert normalized.metadata["stage"] == "normalized_interaction_power_type_internal_minimal_subtraction_result"
    assert normalized.metadata["unnormalized_stage"] == raw.metadata["stage"]
    assert normalized.metadata["loop_normalization"] == "custom"
    assert normalized.metadata["loop_normalization_applied"] is True
    assert normalized.metadata["fixture"] == fixture.name
    assert normalized.metadata["fixture_kind"] == fixture.kind
    assert_expr_equal(normalized.expression("interaction_power_type_loop_normalization_factor"), factor)
    assert_expr_equal(
        normalized.expression("interaction_power_type_unnormalized_eft_lagrangian"),
        raw.off_shell_eft_lagrangian,
    )
    assert_expr_equal(
        normalized.expression("interaction_power_type_normalized_internal_integral_finite_part"),
        factor * raw.expression("interaction_power_type_internal_integral_finite_part"),
    )
    assert_expr_equal(normalized.expression("hFermion[unnormalized]"), raw.expression("hFermion"))
    assert_expr_equal(normalized.expression("hFermion"), factor * raw.expression("hFermion"))
    assert_expr_equal(normalized.on_shell_eft_lagrangian, factor * raw.on_shell_eft_lagrangian)


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


def test_validation_fixture_preview_accepts_custom_internal_series_symbols_without_mathematica() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    eps = S("fixture_custom_eps")
    mu = S("fixture_custom_mubar2")

    preview = fixture.one_loop_preview(
        max_trace_order=1,
        integral_backend=OneLoopIntegralBackend.INTERNAL,
        internal_tensor_reduce=False,
        internal_combine_terms=True,
        epsilon=eps,
        mu_r_squared=mu,
    )
    evaluated = canonical_string(preview.expression("interaction_power_type_internal_integral_sum"))
    pole = canonical_string(preview.expression("interaction_power_type_internal_integral_pole_part"))
    finite = canonical_string(preview.expression("interaction_power_type_internal_integral_finite_part"))

    assert "fixture_custom_eps" in evaluated
    assert "fixture_custom_mubar2" in evaluated
    assert "fixture_custom_eps" in pole
    assert "fixture_custom_mubar2" not in pole
    assert "fixture_custom_eps" not in finite
    assert "fixture_custom_mubar2" in finite


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


def test_validation_fixture_preview_can_use_vakint_minimal_subtraction_backend_without_mathematica() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    eps = vakint_backend.epsilon_symbol()
    engine = FakePoleVakintEngine(S("pole") / eps + S("finite"))

    preview = fixture.one_loop_preview(
        max_trace_order=1,
        integral_backend=OneLoopIntegralBackend.VAKINT_MINIMAL_SUBTRACTION,
        vakint_engine=engine,
        internal_max_pole_order=1,
    )

    assert engine.calls
    assert preview.metadata["stage"] == "interaction_power_type_minimal_subtraction_result"
    assert preview.metadata["subtraction_scheme"] == "minimal_subtraction_preview"
    assert preview.metadata["poles_subtracted"] is True
    assert preview.metadata["fixture"] == fixture.name
    assert preview.metadata["fixture_kind"] == fixture.kind
    assert_expr_equal(preview.off_shell_eft_lagrangian, S("finite"))
    assert_expr_equal(preview.on_shell_eft_lagrangian, S("finite"))
    assert "interaction_power_type_vakint_ms_counterterm" in preview.expression_names()


def test_default_matching_target_projected_matching_condition_frontier_without_mathematica() -> None:
    expected = {
        "VLF_toy_model": {
            "conditions": 0,
            "accepted": 0,
            "different_after_probe": 0,
            "wilson": 0,
            "accepted_wilson": 0,
            "different_wilson": 0,
            "projection_registered_wilson": 0,
            "projection_reference_non_wilson": 0,
            "projection_reference_wilson_fallback": 0,
        },
        "Singlet_Scalar_Extension": {
            "conditions": 72,
            "accepted": 42,
            "different_after_probe": 30,
            "wilson": 64,
            "accepted_wilson": 39,
            "different_wilson": 25,
            "projection_registered_wilson": 64,
            "projection_reference_non_wilson": 8,
            "projection_reference_wilson_fallback": 0,
        },
        "E_VLL": {
            "conditions": 72,
            "accepted": 27,
            "different_after_probe": 45,
            "wilson": 64,
            "accepted_wilson": 25,
            "different_wilson": 39,
            "projection_registered_wilson": 64,
            "projection_reference_non_wilson": 8,
            "projection_reference_wilson_fallback": 0,
        },
        "S1S3LQs": {
            "conditions": 72,
            "accepted": 12,
            "different_after_probe": 60,
            "wilson": 64,
            "accepted_wilson": 12,
            "different_wilson": 52,
            "projection_registered_wilson": 64,
            "projection_reference_non_wilson": 8,
            "projection_reference_wilson_fallback": 0,
        },
    }

    for model, expected_counts in expected.items():
        fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.model_fixture.json"))
        reference_fixture = load_validation_fixture(Path(f"assets/validation/pychete/{model}.matching_fixture.json"))
        reference = reference_fixture.matching_result("matchete_previous")

        report = fixture.one_loop_preview_gap_report(
            reference,
            reference_name=f"{model}.matchete_previous",
            max_trace_order=1,
            project_reference_matching_conditions=True,
        )
        report_obj = report.to_json_obj()

        assert report.candidate_matching_condition_count == expected_counts["conditions"]
        assert report.reference_matching_condition_count == expected_counts["conditions"]
        assert len(report.common_matching_condition_names) == expected_counts["conditions"]
        assert report.missing_reference_matching_condition_count == 0
        assert report.accepted_common_matching_condition_count == expected_counts["accepted"]
        assert report.canonical_equal_common_matching_condition_count == expected_counts["accepted"]
        assert report.numeric_probe_equal_common_matching_condition_count == 0
        assert report.different_after_probe_common_matching_condition_count == expected_counts["different_after_probe"]
        assert report.reference_wilson_matching_condition_count == expected_counts["wilson"]
        assert report.common_wilson_matching_condition_count == expected_counts["wilson"]
        assert report.accepted_common_wilson_matching_condition_count == expected_counts["accepted_wilson"]
        assert (
            report.matching_condition_projection_registered_wilson_count
            == expected_counts["projection_registered_wilson"]
        )
        assert (
            report.matching_condition_projection_reference_non_wilson_count
            == expected_counts["projection_reference_non_wilson"]
        )
        assert (
            report.matching_condition_projection_reference_wilson_fallback_count
            == expected_counts["projection_reference_wilson_fallback"]
        )
        assert (
            report.different_after_probe_common_wilson_matching_condition_count
            == expected_counts["different_wilson"]
        )
        assert report_obj["common_matching_condition_count"] == expected_counts["conditions"]
        assert report_obj["missing_reference_matching_condition_count"] == 0
        assert report_obj["accepted_common_matching_condition_count"] == expected_counts["accepted"]
        assert report_obj["reference_wilson_matching_condition_count"] == expected_counts["wilson"]
        assert report_obj["common_wilson_matching_condition_count"] == expected_counts["wilson"]
        assert report_obj["accepted_common_wilson_matching_condition_count"] == expected_counts["accepted_wilson"]
        assert (
            report_obj["matching_condition_projection_registered_wilson_count"]
            == expected_counts["projection_registered_wilson"]
        )
        assert (
            report_obj["matching_condition_projection_reference_non_wilson_count"]
            == expected_counts["projection_reference_non_wilson"]
        )
        assert (
            report_obj["matching_condition_projection_reference_wilson_fallback_count"]
            == expected_counts["projection_reference_wilson_fallback"]
        )
        assert (
            report_obj["different_after_probe_common_matching_condition_count"]
            == expected_counts["different_after_probe"]
        )
        assert (
            report_obj["different_after_probe_common_wilson_matching_condition_count"]
            == expected_counts["different_wilson"]
        )


def test_validation_fixture_gap_report_can_project_conditions_through_public_match_api() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    reference_fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json"))
    reference = reference_fixture.matching_result("matchete_previous")

    report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="Singlet_Scalar_Extension.matchete_previous",
        max_trace_order=1,
        integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
        internal_tensor_reduce=False,
        internal_combine_terms=True,
        project_reference_matching_conditions=True,
        use_public_match_api=True,
    )

    assert report.candidate_stage == "interaction_power_type_internal_minimal_subtraction_result"
    assert report.candidate_matching_condition_count == 72
    assert report.reference_matching_condition_count == 72
    assert len(report.common_matching_condition_names) == 72
    assert report.missing_reference_matching_condition_count == 0
    assert report.matching_condition_projection_registered_wilson_count == 64
    assert report.matching_condition_projection_reference_non_wilson_count == 8
    assert report.matching_condition_projection_reference_wilson_fallback_count == 0
    assert report.accepted_common_matching_condition_count == 42
    assert report.different_after_probe_common_matching_condition_count == 30
    assert "pychete::Coupling(Singlet_Scalar_Extension::coupling_gL,pychete::List(),0)" in (
        report.accepted_common_matching_condition_names
    )
    assert "pychete::Coupling(Singlet_Scalar_Extension::external_cHB,pychete::List(),0)" in (
        report.different_after_probe_common_matching_condition_names
    )


def test_validation_fixture_gap_report_forwards_pychete_color_to_public_match_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    reference = MatchingResult(
        theory=fixture.theory(),
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
    )
    captured: dict[str, object] = {}

    def fake_match(self: Theory, *_args: object, **kwargs: object) -> MatchingResult:
        captured.update(kwargs)
        return MatchingResult(
            theory=self,
            uv_lagrangian=Expression.num(0),
            off_shell_eft_lagrangian=Expression.num(0),
            on_shell_eft_lagrangian=Expression.num(0),
        )

    monkeypatch.setattr(Theory, "match", fake_match)

    fixture.one_loop_preview_gap_report(
        reference,
        reference_name="public_match_forwarding",
        use_public_match_api=True,
        simplify_pychete_color_algebra=True,
        substitute_heavy_scalar_solutions=True,
        matching_condition_projection_expand_source=False,
    )

    options = captured["one_loop_options"]
    assert isinstance(options, OneLoopMatchOptions)
    assert options.simplify_pychete_color_algebra is True
    assert options.substitute_heavy_scalar_solutions is True
    assert captured["matching_condition_expand_source"] is False


def test_validation_fixture_gap_report_projects_registered_wilsons_before_reference_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("registered_projection_fixture")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    coupling = theory.define_coupling("g", self_conjugate=True)
    operator = phi() ** 2
    wilson = theory.define_wilson_coefficient("cPhi2", operator=operator)
    wilson_target = s.Coupling(wilson.label, s.List(), Expression.num(0))
    wilson_name = canonical_string(wilson_target)
    coupling_name = canonical_string(coupling())
    projected_lagrangian = 3 * operator + 5 * coupling()
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, Expression.num(0))
    fixture = ValidationFixture(
        name="registered_projection_fixture",
        kind="unit_validation",
        state=state,
        source={"generator": "pytest"},
        expression_names=("lagrangian",),
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            wilson_name: Expression.num(3),
            coupling_name: Expression.num(5),
        },
    )

    def fake_one_loop_preview(self: ValidationFixture, **_kwargs: object) -> MatchingResult:
        return MatchingResult(
            theory=theory,
            uv_lagrangian=Expression.num(0),
            off_shell_eft_lagrangian=projected_lagrangian,
            on_shell_eft_lagrangian=projected_lagrangian,
        )

    monkeypatch.setattr(ValidationFixture, "one_loop_preview", fake_one_loop_preview)

    report = fixture.one_loop_preview_gap_report(
        reference,
        project_reference_matching_conditions=True,
        matching_condition_include_coupling_identities=False,
    )
    report_obj = report.to_json_obj()

    assert set(report.common_matching_condition_names) == {wilson_name, coupling_name}
    assert set(report.accepted_common_matching_condition_names) == {wilson_name, coupling_name}
    assert report.matching_condition_projection_registered_wilson_names == (wilson_name,)
    assert report.matching_condition_projection_reference_non_wilson_names == (coupling_name,)
    assert report.matching_condition_projection_reference_wilson_fallback_names == ()
    assert report_obj["matching_condition_projection_registered_wilson_count"] == 1
    assert report_obj["matching_condition_projection_reference_non_wilson_count"] == 1
    assert report_obj["matching_condition_projection_reference_wilson_fallback_count"] == 0


def test_default_matching_condition_probe_accepts_fixture_function_indeterminates() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    reference_fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json"))
    reference = reference_fixture.matching_result("matchete_previous")
    base_report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="Singlet_Scalar_Extension.matchete_previous",
        max_trace_order=1,
        project_reference_matching_conditions=True,
    )
    probe_name = base_report.canonical_different_common_matching_condition_names[0]

    probed_report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="Singlet_Scalar_Extension.matchete_previous",
        max_trace_order=1,
        project_reference_matching_conditions=True,
        auto_probe_samples=True,
        probe_parameter_mode="indeterminates",
        probe_sample_count=1,
        probe_matching_condition_names=(probe_name,),
    )

    assert probed_report.numeric_probe_equal_common_matching_condition_names == ()
    assert probed_report.numeric_probe_different_common_matching_condition_names == (probe_name,)
    assert probed_report.accepted_common_matching_condition_count == base_report.accepted_common_matching_condition_count
    assert probed_report.different_after_probe_common_matching_condition_count == (
        base_report.different_after_probe_common_matching_condition_count
    )


def test_default_matching_condition_probe_can_select_canonical_different_wilson_targets() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    reference_fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json"))
    reference = reference_fixture.matching_result("matchete_previous")
    base_report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="Singlet_Scalar_Extension.matchete_previous",
        max_trace_order=1,
        project_reference_matching_conditions=True,
    )

    probed_report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="Singlet_Scalar_Extension.matchete_previous",
        max_trace_order=1,
        project_reference_matching_conditions=True,
        auto_probe_samples=True,
        probe_parameter_mode="indeterminates",
        probe_sample_count=1,
        probe_matching_condition_names="canonical_different_wilson",
    )

    probed_names = set(probed_report.numeric_probe_equal_common_matching_condition_names) | set(
        probed_report.numeric_probe_different_common_matching_condition_names
    )
    base_different_wilson = set(base_report.different_after_probe_common_wilson_matching_condition_names)

    assert probed_names == base_different_wilson
    assert probed_report.accepted_common_wilson_matching_condition_count >= (
        base_report.accepted_common_wilson_matching_condition_count
    )
    assert probed_report.different_after_probe_common_wilson_matching_condition_count <= (
        base_report.different_after_probe_common_wilson_matching_condition_count
    )
    assert set(probed_report.numeric_probe_equal_common_matching_condition_names).issubset(
        base_different_wilson
    )


def test_validation_fixture_gap_report_can_use_reference_trace_order(monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    theory = fixture.theory()
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "hScalar": Expression.num(0),
            "hScalar-lScalar-lVector-lScalar": Expression.num(0),
        },
    )
    requested_orders: list[int] = []

    def fake_one_loop_preview(self: object, **kwargs: object) -> MatchingResult:
        requested_orders.append(int(kwargs["max_trace_order"]))
        return MatchingResult(
            theory=theory,
            uv_lagrangian=Expression.num(0),
            off_shell_eft_lagrangian=Expression.num(0),
            on_shell_eft_lagrangian=Expression.num(0),
            supertraces={"hScalar": Expression.num(0)},
        )

    monkeypatch.setattr(type(fixture), "one_loop_preview", fake_one_loop_preview)

    report = fixture.one_loop_preview_gap_report(reference, max_trace_order="reference")

    assert requested_orders == [4]
    assert report.candidate_max_supertrace_order == 1
    assert report.reference_max_supertrace_order == 4
    assert report.max_supertrace_order_gap == 3


def test_default_matching_target_gap_reports_track_current_one_loop_coverage() -> None:
    expected = {
        "VLF_toy_model": {
            "reference_supertraces": 13,
            "reference_max_order": 6,
            "conditions": 0,
            "candidate_supertraces": 75,
            "common": {
                "hFermion-lFermion",
                "hFermion-lFermion-lScalar",
                "hFermion-lFermion-lVector",
                "hFermion-lScalar",
                "hFermion-lScalar-lFermion",
                "hFermion-lScalar-lScalar",
                "hFermion-lVector",
                "hFermion-lVector-lFermion",
            },
            "canonical_equal": set(),
        },
        "Singlet_Scalar_Extension": {
            "reference_supertraces": 24,
            "reference_max_order": 6,
            "conditions": 72,
            "candidate_supertraces": 75,
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
            "reference_max_order": 6,
            "conditions": 72,
            "candidate_supertraces": 75,
            "common": {
                "hFermion-lFermion",
                "hFermion-lFermion-lFermion",
                "hFermion-lFermion-lScalar",
                "hFermion-lFermion-lVector",
                "hFermion-lScalar",
                "hFermion-lScalar-lFermion",
                "hFermion-lScalar-lScalar",
                "hFermion-lScalar-lVector",
                "hFermion-lVector",
                "hFermion-lVector-lFermion",
                "hFermion-lVector-lScalar",
            },
            "canonical_equal": {
                "hFermion-lFermion-lFermion",
            },
        },
        "S1S3LQs": {
            "reference_supertraces": 27,
            "reference_max_order": 5,
            "conditions": 72,
            "candidate_supertraces": 75,
            "common": {
                "hScalar",
                "hScalar-hScalar",
                "hScalar-hScalar-hScalar",
                "hScalar-hScalar-lFermion",
                "hScalar-hScalar-lVector",
                "hScalar-lFermion",
                "hScalar-lFermion-lFermion",
                "hScalar-lFermion-lScalar",
                "hScalar-lFermion-lVector",
                "hScalar-lScalar",
                "hScalar-lScalar-lFermion",
                "hScalar-lScalar-lVector",
                "hScalar-lVector",
                "hScalar-lVector-lFermion",
                "hScalar-lVector-lScalar",
                "hScalar-lVector-lVector",
            },
            "canonical_equal": {
                "hScalar-hScalar-lVector",
                "hScalar-lScalar-lVector",
                "hScalar-lVector-lScalar",
                "hScalar-lVector-lVector",
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
        order_coverage = {coverage.order: coverage for coverage in report.supertrace_order_coverage}
        json_order_coverage = {entry["order"]: entry for entry in report_obj["supertrace_order_coverage"]}
        highest_reference_order = expected_counts["reference_max_order"]

        assert report.complete is False
        assert report.candidate_stage == "interaction_power_type_vakint_result"
        assert report.reference_stage is None
        assert report.candidate_supertrace_count == expected_counts["candidate_supertraces"]
        assert report.reference_supertrace_count == expected_counts["reference_supertraces"]
        assert report.candidate_max_supertrace_order == 3
        assert report.reference_max_supertrace_order == expected_counts["reference_max_order"]
        assert report.max_supertrace_order_gap == expected_counts["reference_max_order"] - 3
        assert highest_reference_order in order_coverage
        assert order_coverage[highest_reference_order].candidate_count == 0
        assert order_coverage[highest_reference_order].common_count == 0
        assert order_coverage[highest_reference_order].reference_count > 0
        assert order_coverage[highest_reference_order].missing_reference_count == (
            order_coverage[highest_reference_order].reference_count
        )
        assert order_coverage[highest_reference_order].accepted_common_count == 0
        assert json_order_coverage[highest_reference_order]["candidate_count"] == 0
        assert json_order_coverage[highest_reference_order]["missing_reference_count"] == (
            json_order_coverage[highest_reference_order]["reference_count"]
        )
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
        assert report_obj["candidate_max_supertrace_order"] == 3
        assert report_obj["reference_max_supertrace_order"] == expected_counts["reference_max_order"]
        assert report_obj["max_supertrace_order_gap"] == expected_counts["reference_max_order"] - 3
        assert report_obj["common_supertrace_count"] == len(expected_counts["common"])
        assert report_obj["canonical_equal_common_supertrace_count"] == len(expected_counts["canonical_equal"])
        assert report_obj["canonical_different_common_supertrace_count"] == (
            len(expected_counts["common"]) - len(expected_counts["canonical_equal"])
        )
        assert report_obj["missing_reference_supertrace_count"] == (
            expected_counts["reference_supertraces"] - len(expected_counts["common"])
        )
        assert report_obj["missing_reference_matching_condition_count"] == expected_counts["conditions"]


def test_validation_fixture_gap_report_can_evaluate_loop_functions_for_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    mass = S("fixture_gap_report_loop_mass")
    loop_function = vacuum_integrals.loop_function((mass,), (1, 0))
    evaluated = vacuum_integrals.evaluate_loop_functions(loop_function)
    candidate = MatchingResult(
        theory=fixture.theory(),
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"loop": evaluated},
    )
    reference = MatchingResult(
        theory=fixture.theory(),
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"loop": loop_function},
    )

    def fake_preview(self: object, **_kwargs: object) -> MatchingResult:
        return candidate

    monkeypatch.setattr(type(fixture), "one_loop_preview", fake_preview)

    raw_report = fixture.one_loop_preview_gap_report(reference, reference_name="loop_reference")
    transformed_report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="loop_reference",
        evaluate_loop_functions_for_comparison=True,
    )

    assert raw_report.canonical_equal_common_supertrace_names == ()
    assert raw_report.canonical_different_common_supertrace_names == ("loop",)
    assert transformed_report.canonical_equal_common_supertrace_names == ("loop",)
    assert transformed_report.canonical_different_common_supertrace_names == ()


def test_validation_fixture_gap_report_forwards_internal_scale_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    theory = fixture.theory()
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
    )
    captured: dict[str, object] = {}
    eps = S("fixture_gap_report_eps")
    mu = S("fixture_gap_report_mubar2")
    momentum = S("fixture_gap_report_q2")

    def fake_preview(self: object, **kwargs: object) -> MatchingResult:
        captured.update(kwargs)
        return candidate

    monkeypatch.setattr(type(fixture), "one_loop_preview", fake_preview)
    fixture.one_loop_preview_gap_report(
        candidate,
        reference_name="scale_reference",
        epsilon=eps,
        mu_r_squared=mu,
        loop_momentum_squared=momentum,
        require_registered_mass=False,
        simplify_pychete_color_algebra=True,
    )

    assert captured["epsilon"] is eps
    assert captured["mu_r_squared"] is mu
    assert captured["loop_momentum_squared"] is momentum
    assert captured["require_registered_mass"] is False
    assert captured["simplify_pychete_color_algebra"] is True


def test_validation_fixture_gap_report_can_simplify_loop_functions_for_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    m1 = S("fixture_gap_report_lf_m1")
    m3 = S("fixture_gap_report_lf_m3")
    loop_sum = (
        vacuum_integrals.loop_function((m1, m3), (1, 1, 1))
        + vacuum_integrals.loop_function((m1, m3), (2, 1, 0))
        - vacuum_integrals.loop_function((m3, m1), (2, 1, 0))
    )
    simplified = 2 * vacuum_integrals.loop_function((m1, m3), (2, 1, 0))
    candidate = MatchingResult(
        theory=fixture.theory(),
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"loop_sum": loop_sum},
    )
    reference = MatchingResult(
        theory=fixture.theory(),
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"loop_sum": simplified},
    )

    def fake_preview(self: object, **_kwargs: object) -> MatchingResult:
        return candidate

    monkeypatch.setattr(type(fixture), "one_loop_preview", fake_preview)

    raw_report = fixture.one_loop_preview_gap_report(reference, reference_name="loop_sum_reference")
    simplified_report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="loop_sum_reference",
        simplify_loop_functions_for_comparison=True,
    )

    assert raw_report.canonical_equal_common_supertrace_names == ()
    assert raw_report.canonical_different_common_supertrace_names == ("loop_sum",)
    assert simplified_report.canonical_equal_common_supertrace_names == ("loop_sum",)
    assert simplified_report.canonical_different_common_supertrace_names == ()


def test_default_matching_target_gap_reports_track_internal_ms_one_loop_coverage() -> None:
    # S1S3LQs remains covered by the raw order-three report above. After
    # exact indexed light-side interactions are retained, its internal-MS
    # evaluation is too expensive for this smoke test until the backend has
    # stronger expression filtering/reduction.
    expected = {
        "VLF_toy_model": {
            "reference_supertraces": 13,
            "conditions": 0,
            "common": {
                "hFermion-lFermion",
                "hFermion-lFermion-lScalar",
                "hFermion-lFermion-lVector",
                "hFermion-lScalar",
                "hFermion-lScalar-lFermion",
                "hFermion-lScalar-lScalar",
                "hFermion-lVector",
                "hFermion-lVector-lFermion",
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
                "hFermion-lFermion-lVector",
                "hFermion-lScalar",
                "hFermion-lScalar-lFermion",
                "hFermion-lScalar-lScalar",
                "hFermion-lScalar-lVector",
                "hFermion-lVector",
                "hFermion-lVector-lFermion",
                "hFermion-lVector-lScalar",
            },
            "canonical_equal": {
                "hFermion-lFermion-lFermion",
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
        assert report.candidate_supertrace_count == 78
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
        assert report_obj["candidate_supertrace_count"] == 78
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
