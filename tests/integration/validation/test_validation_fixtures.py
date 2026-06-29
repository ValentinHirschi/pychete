from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from symbolica import Expression, S
import pytest

from pychete import (
    ExternalKind,
    FieldMassKind,
    FreeLagConvention,
    OneLoopIntegralBackend,
    OneLoopMatchOptions,
    OneLoopNormalization,
    OneLoopSetup,
    Theory,
    ValidationFixture,
    abelian_vector_eom_field_redefinition_delta,
    one_loop_normalization_factor,
    registered_wilson_matching_condition_targets,
)
from pychete.backends import spenso as spenso_backend
from pychete.backends import vacuum_integrals
from pychete.backends import vakint as vakint_backend
from pychete import validation_fixtures as validation_fixtures_module
from pychete.bases.smeft_warsaw import SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES
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


def _heavy_scalar_validation_fixture() -> tuple[ValidationFixture, object, object, object]:
    theory = Theory("validation_heavy_scalar_preview")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    coupling = theory.define_coupling("g", self_conjugate=True)
    lagrangian = theory.free_lag(heavy, light) - coupling() * heavy() * light() ** 2 / 2
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    return (
        ValidationFixture(
            name="validation_heavy_scalar_preview",
            kind="unit",
            state=state,
            source={"generator": "pytest"},
            expression_names=("lagrangian",),
        ),
        heavy,
        light,
        coupling,
    )


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


def test_validation_fixture_direct_preview_substitutes_heavy_scalar_solutions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture, heavy, light, coupling = _heavy_scalar_validation_fixture()
    heavy_expr = heavy()

    def fake_result(self: OneLoopSetup, **_kwargs: object) -> MatchingResult:
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=heavy_expr,
            on_shell_eft_lagrangian=heavy_expr,
            metadata={"stage": "fake_preview", "loop_order": 1},
        )

    monkeypatch.setattr(OneLoopSetup, "interaction_power_type_matching_result", fake_result)

    raw = fixture.one_loop_preview(max_trace_order=1, substitute_heavy_scalar_solutions=False)
    reduced = fixture.one_loop_preview(max_trace_order=1, substitute_heavy_scalar_solutions=True)
    heavy_atom = canonical_string(heavy_expr)
    reduced_text = canonical_string(reduced.on_shell_eft_lagrangian)

    assert raw.metadata["heavy_scalar_solutions_substituted"] is False
    assert raw.metadata["heavy_scalar_solution_source"] == "disabled"
    assert raw.metadata["heavy_scalar_solution_fresh_dummy_indices"] is False
    assert reduced.metadata["heavy_scalar_solutions_substituted"] is True
    assert reduced.metadata["heavy_scalar_solution_count"] == 1
    assert reduced.metadata["heavy_scalar_solution_rule_count"] > 0
    assert reduced.metadata["heavy_scalar_solution_source"] == "matching_lagrangian"
    assert reduced.metadata["heavy_scalar_solution_expand"] is False
    assert reduced.metadata["heavy_scalar_solution_fresh_dummy_indices"] is True
    assert heavy_atom in canonical_string(raw.on_shell_eft_lagrangian)
    assert heavy_atom in canonical_string(reduced.expression("on_shell_eft_lagrangian_before_reduction"))
    assert heavy_atom not in reduced_text
    assert canonical_string(light()) in reduced_text
    assert canonical_string(coupling()) in reduced_text


def test_validation_fixture_direct_preview_runs_scalar_eom_exposure_without_commutator_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture, _heavy, _light, coupling = _heavy_scalar_validation_fixture()
    source = Expression.num(3)
    marker = coupling()
    calls: list[tuple[Expression, Expression | None, bool]] = []

    def fake_result(self: OneLoopSetup, **_kwargs: object) -> MatchingResult:
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=source,
            on_shell_eft_lagrangian=source,
            metadata={"stage": "fake_preview", "loop_order": 1},
        )

    def fake_scalar_green_hook(
        _theory: Theory,
        expr: Expression,
        *,
        eom_lagrangian: Expression | None = None,
        eom_fields: object | None = None,
        expose_scalar_eom_terms: bool = False,
    ) -> Expression:
        calls.append((expr, eom_lagrangian, expose_scalar_eom_terms))
        assert eom_fields is None
        return expr + marker

    monkeypatch.setattr(OneLoopSetup, "interaction_power_type_matching_result", fake_result)
    monkeypatch.setattr(
        validation_fixtures_module,
        "_apply_wilson_line_post_integral_scalar_commutator_bilinears",
        fake_scalar_green_hook,
    )

    preview = fixture.one_loop_preview(
        max_trace_order=1,
        wilson_line_expose_scalar_eom_terms=True,
        on_shell_eom_lagrangian="lagrangian",
    )

    assert len(calls) == 1
    assert_expr_equal(calls[0][0], source)
    assert calls[0][1] is not None
    assert_expr_equal(calls[0][1], fixture.expression("lagrangian"))
    assert calls[0][2] is True
    assert_expr_equal(preview.on_shell_eft_lagrangian, source + marker)
    assert preview.metadata["wilson_line_scalar_commutator_bilinears_reduced"] is False
    assert preview.metadata["wilson_line_scalar_eom_terms_reduced"] is True
    assert preview.metadata["wilson_line_scalar_eom_field_redefinition_applied"] is False


def test_validation_fixture_direct_preview_applies_scalar_eom_field_redefinition_after_exposure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("validation_scalar_eom_field_redefinition_preview")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    coefficient = theory.define_coupling("c", self_conjugate=True)
    lagrangian = theory.free_lag(phi)
    exposed = coefficient() * phi() ** 3 * s.EOM(phi())
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    fixture = ValidationFixture(
        name="validation_scalar_eom_field_redefinition_preview",
        kind="unit",
        state=state,
        source={"generator": "pytest"},
        expression_names=("lagrangian",),
    )

    def fake_result(self: OneLoopSetup, **_kwargs: object) -> MatchingResult:
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=Expression.num(0),
            on_shell_eft_lagrangian=Expression.num(0),
            metadata={"stage": "fake_preview", "loop_order": 1},
        )

    def fake_scalar_green_hook(
        _theory: Theory,
        expr: Expression,
        *,
        eom_lagrangian: Expression | None = None,
        eom_fields: object | None = None,
        expose_scalar_eom_terms: bool = False,
    ) -> Expression:
        assert_expr_equal(expr, Expression.num(0))
        assert eom_lagrangian is not None
        assert_expr_equal(eom_lagrangian, lagrangian)
        assert eom_fields == [phi]
        assert expose_scalar_eom_terms is True
        return exposed

    monkeypatch.setattr(OneLoopSetup, "interaction_power_type_matching_result", fake_result)
    monkeypatch.setattr(
        validation_fixtures_module,
        "_apply_wilson_line_post_integral_scalar_commutator_bilinears",
        fake_scalar_green_hook,
    )

    expected_delta = theory.systematic_scalar_eom_field_redefinition_delta(
        lagrangian,
        eom_terms_lagrangian=exposed,
        max_order=6,
        fields=[phi],
        strict=True,
    )
    preview = fixture.one_loop_preview(
        max_trace_order=1,
        wilson_line_expose_scalar_eom_terms=True,
        on_shell_eom_lagrangian="lagrangian",
        on_shell_eom_fields=[phi],
        on_shell_eom_strict=True,
    )

    assert_expr_equal(
        preview.expression("on_shell_eft_lagrangian_after_scalar_commutator_bilinear_exposure"),
        exposed,
    )
    assert_expr_equal(
        preview.expression("on_shell_eft_lagrangian_scalar_eom_field_redefinition_delta"),
        expected_delta,
    )
    assert_expr_equal(preview.on_shell_eft_lagrangian, (exposed + expected_delta).expand())
    assert preview.metadata["wilson_line_scalar_commutator_bilinears_reduced"] is False
    assert preview.metadata["wilson_line_scalar_eom_terms_reduced"] is True
    assert preview.metadata["wilson_line_scalar_eom_field_redefinition_applied"] is True


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


def test_validation_fixture_preview_can_apply_evaluated_matchete_hbar_normalization() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    hbar = S("fixture_evaluated_hbar")
    raw = fixture.one_loop_preview(
        max_trace_order=1,
        integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
    )
    normalized = fixture.one_loop_preview(
        max_trace_order=1,
        integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
        normalization=OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
        hbar=hbar,
    )
    factor = one_loop_normalization_factor(OneLoopNormalization.MATCHETE_EVALUATED_HBAR, hbar=hbar)

    assert normalized.metadata["stage"] == "normalized_interaction_power_type_internal_minimal_subtraction_result"
    assert normalized.metadata["loop_normalization"] == "matchete_evaluated_hbar"
    assert_expr_equal(normalized.expression("interaction_power_type_loop_normalization_factor"), factor)
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


def test_validation_fixture_preview_can_use_bosonic_cde_expansion_without_mathematica() -> None:
    theory = Theory("validation_fixture_cde")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    fixture = ValidationFixture(
        name="validation_fixture_cde",
        kind="model_smoke",
        state=state,
        source={"generator": "pytest", "mathematica_runtime_required": False},
        expression_names=("lagrangian",),
    )
    mu = theory.lorentz_index("mu")
    expansion = {"hScalar-lScalar": ((mu,), ())}
    setup = theory.one_loop_setup(
        lagrangian,
        eft_order=6,
        max_trace_order=2,
    )
    expected = setup.interaction_bosonic_cde_hybrid_matching_result(
        expansion,
        act_open_derivatives=True,
    )

    preview = fixture.one_loop_preview(
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.VAKINT,
        bosonic_cde_expansion_indices_by_trace=expansion,
        bosonic_cde_act_open_derivatives=True,
    )

    assert preview.metadata["stage"] == "interaction_bosonic_cde_hybrid_vakint_result"
    assert preview.metadata["fixture"] == fixture.name
    assert preview.metadata["interaction_bosonic_cde_hybrid"] is True
    assert preview.metadata["bosonic_cde_expansion_enabled"] is True
    assert preview.metadata["bosonic_cde_act_open_derivatives"] is True
    assert_expr_equal(preview.off_shell_eft_lagrangian, expected.off_shell_eft_lagrangian)
    preview.validate()

    generated_plan = setup.interaction_bosonic_cde_expansion_plan(
        trace_names=("hScalar-lScalar",),
        max_total_order=0,
    )
    expected_generated = setup.interaction_bosonic_cde_hybrid_matching_result(generated_plan)
    generated_preview = fixture.one_loop_preview(
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.VAKINT,
        bosonic_cde_trace_names=("hScalar-lScalar",),
        bosonic_cde_max_total_order=0,
    )
    assert generated_preview.metadata["bosonic_cde_expansion_enabled"] is True
    assert generated_preview.metadata["bosonic_cde_expansion_planned"] is True
    assert generated_preview.metadata["interaction_bosonic_cde_hybrid"] is True
    assert generated_preview.metadata["interaction_bosonic_cde_plan_entry_count"] == 1
    assert_expr_equal(generated_preview.off_shell_eft_lagrangian, expected_generated.off_shell_eft_lagrangian)
    generated_preview.validate()


def test_validation_fixture_preview_can_use_wilson_line_expansion_without_mathematica() -> None:
    theory = Theory("validation_fixture_wilson_line")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    z = theory.define_coupling("z", self_conjugate=True)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(light)
        - y() * heavy() * light() ** 2 / 2
        - z() * heavy() ** 2 / 2
    )
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    fixture = ValidationFixture(
        name="validation_fixture_wilson_line",
        kind="model_smoke",
        state=state,
        source={"generator": "pytest", "mathematica_runtime_required": False},
        expression_names=("lagrangian",),
    )
    mu = theory.lorentz_index("mu")
    expansion = {"hScalar-lScalar": ((mu,), ())}
    setup = theory.one_loop_setup(
        lagrangian,
        eft_order=6,
        max_trace_order=2,
    )
    expected = setup.interaction_wilson_line_hybrid_matching_result(
        expansion,
        act_open_derivatives=True,
        max_wilson_derivative_order=3,
    )

    preview = fixture.one_loop_preview(
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.VAKINT,
        wilson_line_expansion_indices_by_trace=expansion,
        wilson_line_act_open_derivatives=True,
        wilson_line_max_derivative_order=3,
    )

    assert preview.metadata["stage"] == "interaction_wilson_line_hybrid_vakint_result"
    assert preview.metadata["fixture"] == fixture.name
    assert preview.metadata["uses_wilson_line_expansion"] is True
    assert preview.metadata["interaction_wilson_line_hybrid"] is True
    assert preview.metadata["wilson_line_expansion_enabled"] is True
    assert preview.metadata["wilson_line_act_open_derivatives"] is True
    assert preview.metadata["wilson_line_max_derivative_order"] == 3
    assert preview.metadata["bosonic_cde_expansion_enabled"] is False
    assert_expr_equal(preview.off_shell_eft_lagrangian, expected.off_shell_eft_lagrangian)
    preview.validate()

    color_simplified_preview = fixture.one_loop_preview(
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.VAKINT,
        wilson_line_expansion_indices_by_trace=expansion,
        wilson_line_act_open_derivatives=True,
        wilson_line_max_derivative_order=3,
        simplify_pychete_color_algebra=True,
    )

    assert color_simplified_preview.metadata["pychete_color_algebra_simplified"] is True
    assert (
        color_simplified_preview.metadata["interaction_wilson_line_pychete_color_algebra_simplified"]
        is True
    )
    assert color_simplified_preview.metadata["native_color_wrappers_decoded"] is True
    assert color_simplified_preview.metadata["su2_field_strength_generator_bilinears_simplified"] is True
    assert color_simplified_preview.metadata["su2_u1_field_strength_generator_bilinears_simplified"] is True
    assert_expr_equal(color_simplified_preview.off_shell_eft_lagrangian, expected.off_shell_eft_lagrangian)

    generated_plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar-lScalar",),
        max_total_order=0,
    )
    expected_generated = setup.interaction_wilson_line_hybrid_matching_result(generated_plan)
    generated_preview = fixture.one_loop_preview(
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.VAKINT,
        wilson_line_trace_names=("hScalar-lScalar",),
        wilson_line_max_total_order=0,
    )
    assert generated_preview.metadata["wilson_line_expansion_enabled"] is True
    assert generated_preview.metadata["wilson_line_expansion_planned"] is True
    assert generated_preview.metadata["interaction_wilson_line_hybrid"] is True
    assert generated_preview.metadata["interaction_wilson_line_plan_entry_count"] == 1
    generated_entry_counts = generated_preview.metadata["interaction_wilson_line_term_count_by_entry"]
    assert sum(generated_entry_counts.values()) == generated_preview.metadata["interaction_wilson_line_term_count"]
    assert (
        generated_preview.metadata["interaction_wilson_line_term_count_by_trace"]["hScalar-lScalar"]
        == generated_preview.metadata["interaction_wilson_line_term_count"]
    )
    assert_expr_equal(generated_preview.off_shell_eft_lagrangian, expected_generated.off_shell_eft_lagrangian)
    generated_preview.validate()

    eps = vakint_backend.epsilon_symbol()
    fake_evaluated = S("single") / eps + S("finite")
    minimal_engine = FakePoleVakintEngine(fake_evaluated)
    single_scale_plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar",),
        max_total_order=0,
    )
    minimal_subtracted = setup.interaction_wilson_line_minimal_subtraction_result(
        single_scale_plan,
        vakint_engine=minimal_engine,
    )
    minimal_term_count = minimal_subtracted.metadata["interaction_wilson_line_term_count"]
    assert minimal_term_count > 0
    assert len(minimal_engine.calls) == minimal_term_count
    assert (
        minimal_subtracted.metadata["interaction_wilson_line_term_count_by_trace"]["hScalar"]
        == minimal_term_count
    )
    assert_expr_equal(minimal_subtracted.off_shell_eft_lagrangian, minimal_term_count * S("finite"))

    unfiltered_for_target = fixture.one_loop_preview(
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.VAKINT,
        wilson_line_trace_names=("hScalar", "hScalar-lScalar"),
        wilson_line_max_total_order=0,
    )
    filtered_for_target = fixture.one_loop_preview(
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.VAKINT,
        wilson_line_trace_names=("hScalar", "hScalar-lScalar"),
        wilson_line_max_total_order=0,
        wilson_line_filter_terms_by_matching_targets=True,
        matching_condition_targets=(light() ** 2,),
    )
    assert filtered_for_target.metadata["wilson_line_terms_filtered_by_matching_targets"] is True
    assert (
        filtered_for_target.metadata["interaction_wilson_line_terms_filtered_by_matching_targets"]
        is True
    )
    assert (
        filtered_for_target.metadata["interaction_wilson_line_term_count"]
        < unfiltered_for_target.metadata["interaction_wilson_line_term_count"]
    )
    filtered_for_target.validate()

    with pytest.raises(ValueError, match="mutually exclusive"):
        fixture.one_loop_preview(
            max_trace_order=2,
            integral_backend=OneLoopIntegralBackend.VAKINT,
            bosonic_cde_expansion_indices_by_trace=expansion,
            wilson_line_expansion_indices_by_trace=expansion,
        )


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


def test_validation_fixture_preview_forwards_wilson_line_scalar_derivative_bilinear_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    captured_hybrid_kwargs: dict[str, object] = {}

    def fake_hybrid(
        self: OneLoopSetup,
        expansion_indices_by_trace: object,
        **kwargs: object,
    ) -> MatchingResult:
        captured_hybrid_kwargs["expansion_indices_by_trace"] = expansion_indices_by_trace
        captured_hybrid_kwargs.update(kwargs)
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=S("fixture_fake_wilson_line_hybrid_vakint_result"),
            on_shell_eft_lagrangian=S("fixture_fake_wilson_line_hybrid_vakint_result"),
            supertraces={
                "interaction_wilson_line_hybrid_vakint_integral_sum": S(
                    "fixture_fake_wilson_line_hybrid_vakint_result"
                ),
            },
            metadata={
                "stage": "fixture_fake_wilson_line_hybrid_vakint",
                "complete": False,
            },
        )

    monkeypatch.setattr(
        OneLoopSetup,
        "interaction_wilson_line_hybrid_matching_result",
        fake_hybrid,
    )

    preview = fixture.one_loop_preview(
        max_trace_order=1,
        integral_backend=OneLoopIntegralBackend.VAKINT,
        wilson_line_expansion_indices_by_trace={"hScalar-lScalar": ((), ())},
        wilson_line_emit_covariant_derivative_commutators=True,
        wilson_line_covariant_derivative_commutator_mode="all_distinct",
        wilson_line_expose_scalar_derivative_commutator_bilinears=True,
    )

    assert preview.metadata["stage"] == "fixture_fake_wilson_line_hybrid_vakint"
    assert preview.metadata["fixture"] == fixture.name
    assert preview.metadata["wilson_line_commutator_emit_mode"] == "all_distinct"
    assert captured_hybrid_kwargs["covariant_derivative_commutator_mode"] == "all_distinct"
    assert preview.metadata["wilson_line_scalar_derivative_commutator_bilinears_exposed"] is True
    assert captured_hybrid_kwargs["expose_scalar_derivative_commutator_bilinears"] is True


def test_validation_fixture_preview_applies_abelian_vector_eom_field_redefinition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("validation_preview_vector_eom_reduction")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 2)],
        self_conjugate=False,
        mass=0,
    )
    coupling = theory.define_coupling("y", self_conjugate=True)
    coefficient = theory.define_coupling("c", self_conjugate=True)
    vector = theory.field_handle("B")
    gauge = theory.coupling_handle("gY")
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    field = phi()
    current = Expression.I * s.Bar(field) * s.CD(mu, field) - Expression.I * s.CD(mu, s.Bar(field)) * field
    divergence = s.FieldStrength(vector.label, s.List(nu, mu), s.List(), s.List(nu))
    source = (coefficient() * current * divergence).expand()
    lagrangian = (
        theory.free_lag(heavy, phi, vector, convention=FreeLagConvention.MATCHETE)
        - coupling() * heavy() * s.Bar(phi()) * phi()
    )
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    fixture = ValidationFixture(
        name="validation_preview_vector_eom_reduction",
        kind="unit",
        state=state,
        source={"generator": "pytest"},
        expression_names=("lagrangian",),
    )

    def fake_power_type_result(self: OneLoopSetup, **_kwargs: object) -> MatchingResult:
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=source,
            on_shell_eft_lagrangian=source,
        )

    monkeypatch.setattr(OneLoopSetup, "interaction_power_type_matching_result", fake_power_type_result)

    preview = fixture.one_loop_preview(
        max_trace_order=1,
        on_shell_eom_lagrangian="lagrangian",
        on_shell_eom_fields=[vector],
        on_shell_eom_strict=True,
        on_shell_eom_abelian_vector_field_redefinition=True,
    )

    assert preview.metadata["on_shell_eom_reduction_requested"] is True
    assert preview.metadata["on_shell_eom_reduction_rule_count"] == 1
    assert preview.metadata["on_shell_eom_abelian_vector_field_redefinition"] is True
    assert preview.metadata["on_shell_eom_abelian_vector_field_redefinition_applied"] is True
    assert "on_shell_eft_lagrangian_abelian_vector_field_redefinition_delta" in preview.supertraces
    assert_expr_equal(preview.on_shell_eft_lagrangian, -4 * coefficient() * gauge() ** 2 * current**2)


def test_validation_fixture_preview_commutator_exposure_without_formal_eom_keeps_vector_replay_inactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("validation_preview_vector_eom_after_scalar_commutator")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 2)],
        self_conjugate=False,
        mass=0,
    )
    coefficient = theory.define_coupling("c", self_conjugate=True)
    vector = theory.field_handle("B")
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    source = coefficient() * s.Bar(phi(derivatives=[mu, nu, nu])) * phi(derivatives=[mu])
    lagrangian = theory.free_lag(phi, vector, convention=FreeLagConvention.MATCHETE)
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    fixture = ValidationFixture(
        name="validation_preview_vector_eom_after_scalar_commutator",
        kind="unit",
        state=state,
        source={"generator": "pytest"},
        expression_names=("lagrangian",),
    )

    def fake_power_type_result(self: OneLoopSetup, **_kwargs: object) -> MatchingResult:
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=source,
            on_shell_eft_lagrangian=source,
        )

    monkeypatch.setattr(OneLoopSetup, "interaction_power_type_matching_result", fake_power_type_result)

    preview = fixture.one_loop_preview(
        max_trace_order=1,
        on_shell_eom_lagrangian="lagrangian",
        on_shell_eom_fields=[vector],
        on_shell_eom_strict=True,
        on_shell_eom_abelian_vector_field_redefinition=True,
        wilson_line_expose_scalar_derivative_commutator_bilinears=True,
    )
    scalar_exposed = preview.supertraces["on_shell_eft_lagrangian_after_scalar_commutator_bilinear_exposure"]
    rules = theory.eom_replacement_rules_for_expression(
        lagrangian,
        scalar_exposed,
        fields=[vector],
        strict=True,
    )
    delta = theory.abelian_vector_eom_field_redefinition_delta(
        lagrangian,
        scalar_exposed,
        fields=[vector],
        strict=True,
    )

    assert len(rules) == 0
    assert_expr_equal(delta, Expression.num(0))
    assert preview.metadata["wilson_line_scalar_commutator_abelian_vector_eom_reduction_rule_count"] == 0
    assert preview.metadata["wilson_line_scalar_commutator_abelian_vector_field_redefinition_applied"] is False
    assert preview.metadata["wilson_line_scalar_commutator_abelian_vector_field_redefinition_staged"] is False
    assert "on_shell_eft_lagrangian_after_scalar_commutator_abelian_vector_eom_reduction" not in preview.supertraces
    assert_expr_equal(preview.on_shell_eft_lagrangian, scalar_exposed)


def test_validation_fixture_preview_stages_vector_eom_redefinition_after_formal_eom_exposure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("validation_preview_staged_vector_eom_after_formal")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 2)],
        self_conjugate=False,
        mass=0,
    )
    coefficient = theory.define_coupling("c", self_conjugate=True)
    vector = theory.field_handle("B")
    mu = theory.dummy_index(0)
    field = phi()
    current = (
        Expression.I * s.Bar(field) * s.CD(mu, field)
        - Expression.I * s.CD(mu, s.Bar(field)) * field
    )
    source = (coefficient() * current * s.EOM(vector(mu))).expand()
    lagrangian = theory.free_lag(phi, vector, convention=FreeLagConvention.MATCHETE)
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    fixture = ValidationFixture(
        name="validation_preview_staged_vector_eom_after_formal",
        kind="unit",
        state=state,
        source={"generator": "pytest"},
        expression_names=("lagrangian",),
    )

    def fake_power_type_result(self: OneLoopSetup, **_kwargs: object) -> MatchingResult:
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=source,
            on_shell_eft_lagrangian=source,
        )

    monkeypatch.setattr(OneLoopSetup, "interaction_power_type_matching_result", fake_power_type_result)

    preview = fixture.one_loop_preview(
        max_trace_order=1,
        on_shell_eom_lagrangian="lagrangian",
        on_shell_eom_fields=[vector],
        on_shell_eom_strict=True,
        on_shell_eom_abelian_vector_field_redefinition=True,
        wilson_line_expose_scalar_eom_terms=True,
    )
    scalar_exposed = preview.supertraces["on_shell_eft_lagrangian_after_scalar_commutator_bilinear_exposure"]
    rules = theory.eom_replacement_rules_for_expression(
        lagrangian,
        scalar_exposed,
        fields=[vector],
        strict=True,
    )
    delta = theory.systematic_abelian_vector_eom_field_redefinition_delta(
        lagrangian,
        eom_terms_lagrangian=scalar_exposed,
        max_order=6,
        fields=[vector],
        strict=True,
    )
    expected = (scalar_exposed.replace_multiple(rules) + delta).expand()

    assert len(rules) == 1
    assert preview.metadata["wilson_line_scalar_eom_terms_reduced"] is True
    assert preview.metadata["wilson_line_scalar_commutator_abelian_vector_eom_reduction_rule_count"] == 1
    assert preview.metadata["wilson_line_scalar_commutator_abelian_vector_field_redefinition_applied"] is True
    assert preview.metadata["wilson_line_scalar_commutator_abelian_vector_field_redefinition_staged"] is True
    assert_expr_equal(
        preview.supertraces["on_shell_eft_lagrangian_scalar_commutator_abelian_vector_field_redefinition_delta"],
        delta,
    )
    assert_expr_equal(preview.on_shell_eft_lagrangian, expected)


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
        project_reference_matching_conditions=True,
        simplify_pychete_color_algebra=True,
        on_shell_eom_lagrangian="lagrangian",
        on_shell_eom_fields=("B",),
        on_shell_eom_min_derivative_order=1,
        on_shell_eom_strict=True,
        on_shell_eom_abelian_vector_field_redefinition=True,
        on_shell_replacement_repeat=True,
        substitute_heavy_scalar_solutions=True,
        include_tree_level_matching=True,
        bosonic_cde_expansion_indices_by_trace={"hScalar": ((S("mu"),),)},
        bosonic_cde_trace_names=("hScalar",),
        bosonic_cde_max_total_order=2,
        bosonic_cde_max_slot_order=1,
        bosonic_cde_index_prefix="forwarded_cde",
        bosonic_cde_act_open_derivatives=True,
        bosonic_cde_emit_covariant_derivative_commutators=True,
        bosonic_cde_emit_covariant_derivative_commutator_passes=2,
        bosonic_cde_expand_covariant_derivative_commutators=True,
        bosonic_cde_filter_terms_by_matching_targets=True,
        matching_condition_projection_expand_source=False,
        matching_condition_projection_canonize_indices=False,
        matching_condition_projection_normalize_derivative_operators=False,
        matching_condition_projection_normalize_ibp_scalar_bilinears=True,
        matching_condition_projection_truncate_eft=True,
        truncate_eft_result=False,
    )

    options = captured["one_loop_options"]
    assert isinstance(options, OneLoopMatchOptions)
    assert options.simplify_pychete_color_algebra is True
    assert_expr_equal(options.on_shell_eom_lagrangian, fixture.expression("lagrangian"))
    assert options.on_shell_eom_fields == ("B",)
    assert options.on_shell_eom_min_derivative_order == 1
    assert options.on_shell_eom_strict is True
    assert options.on_shell_eom_abelian_vector_field_redefinition is True
    assert options.on_shell_replacement_repeat is True
    assert options.substitute_heavy_scalar_solutions is True
    assert options.include_tree_level_matching is True
    assert options.bosonic_cde_expansion_indices_by_trace == {"hScalar": ((S("mu"),),)}
    assert options.bosonic_cde_trace_names == ("hScalar",)
    assert options.bosonic_cde_max_total_order == 2
    assert options.bosonic_cde_max_slot_order == 1
    assert options.bosonic_cde_index_prefix == "forwarded_cde"
    assert options.bosonic_cde_act_open_derivatives is True
    assert options.bosonic_cde_emit_covariant_derivative_commutators is True
    assert options.bosonic_cde_emit_covariant_derivative_commutator_passes == 2
    assert options.bosonic_cde_expand_covariant_derivative_commutators is True
    assert options.bosonic_cde_filter_terms_by_matching_targets is True
    assert options.truncate_eft_result is False
    assert captured["matching_condition_expand_source"] is False
    assert captured["matching_condition_canonize_indices"] is False
    assert captured["matching_condition_normalize_derivative_operators"] is False
    assert captured["matching_condition_normalize_ibp_scalar_bilinears"] is True
    assert captured["matching_condition_truncate_eft"] is True


def test_validation_fixture_gap_report_forwards_heavy_scalar_options_to_direct_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture, _heavy, _light, _coupling = _heavy_scalar_validation_fixture()
    reference = MatchingResult(
        theory=fixture.theory(),
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
    )
    captured: dict[str, object] = {}

    def fake_one_loop_preview(self: ValidationFixture, **kwargs: object) -> MatchingResult:
        captured.update(kwargs)
        return MatchingResult(
            theory=self.theory(),
            uv_lagrangian=Expression.num(0),
            off_shell_eft_lagrangian=Expression.num(0),
            on_shell_eft_lagrangian=Expression.num(0),
        )

    monkeypatch.setattr(ValidationFixture, "one_loop_preview", fake_one_loop_preview)

    fixture.one_loop_preview_gap_report(
        reference,
        reference_name="direct_preview_forwarding",
        on_shell_eom_lagrangian="lagrangian",
        on_shell_eom_fields=("phi",),
        on_shell_eom_min_derivative_order=1,
        on_shell_eom_strict=True,
        on_shell_eom_abelian_vector_field_redefinition=True,
        on_shell_replacement_repeat=True,
        substitute_heavy_scalar_solutions=True,
        heavy_scalar_solution_lagrangian="lagrangian",
        heavy_scalar_solution_expand=True,
    )

    assert_expr_equal(
        captured["on_shell_eom_lagrangian"],
        fixture.expression("lagrangian"),
    )
    assert captured["on_shell_eom_fields"] == ("phi",)
    assert captured["on_shell_eom_min_derivative_order"] == 1
    assert captured["on_shell_eom_strict"] is True
    assert captured["on_shell_eom_abelian_vector_field_redefinition"] is True
    assert captured["on_shell_replacement_repeat"] is True
    assert captured["substitute_heavy_scalar_solutions"] is True
    assert captured["heavy_scalar_solution_expand"] is True
    assert_expr_equal(
        captured["heavy_scalar_solution_lagrangian"],
        fixture.expression("lagrangian"),
    )


def test_validation_fixture_gap_report_forwards_wilson_line_to_public_match_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/VLF_toy_model.model_fixture.json"))
    reference = MatchingResult(
        theory=fixture.theory(),
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
    )
    expansion = {"hScalar": ((S("mu"),),)}
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
        reference_name="public_match_wilson_line_forwarding",
        use_public_match_api=True,
        project_reference_matching_conditions=True,
        wilson_line_expansion_indices_by_trace=expansion,
        wilson_line_trace_names=("hScalar",),
        wilson_line_max_total_order=2,
        wilson_line_max_slot_order=1,
        wilson_line_total_orders_by_trace={"hScalar": (2,)},
        wilson_line_index_prefix="forwarded_wilson",
        wilson_line_act_open_derivatives=True,
        wilson_line_emit_covariant_derivative_commutators=True,
        wilson_line_covariant_derivative_commutator_mode="all_distinct",
        wilson_line_max_derivative_order=3,
        wilson_line_filter_terms_by_matching_targets=True,
        wilson_line_include_unselected_traces=False,
        use_matchete_fluctuation_dof_basis=True,
        wilson_line_weight_paths_by_component_dofs=True,
        wilson_line_expose_scalar_derivative_commutator_bilinears=True,
        wilson_line_expose_scalar_eom_terms=True,
        wilson_line_tensor_reduce_before_wilson_expand=True,
        on_shell_eom_lagrangian=Expression.num(0),
    )

    options = captured["one_loop_options"]
    assert isinstance(options, OneLoopMatchOptions)
    assert options.wilson_line_expansion_indices_by_trace == expansion
    assert options.wilson_line_trace_names == ("hScalar",)
    assert options.wilson_line_max_total_order == 2
    assert options.wilson_line_max_slot_order == 1
    assert options.wilson_line_total_orders_by_trace == {"hScalar": (2,)}
    assert options.wilson_line_index_prefix == "forwarded_wilson"
    assert options.wilson_line_act_open_derivatives is True
    assert options.wilson_line_emit_covariant_derivative_commutators is True
    assert options.wilson_line_covariant_derivative_commutator_mode == "all_distinct"
    assert options.wilson_line_max_derivative_order == 3
    assert options.wilson_line_filter_terms_by_matching_targets is True
    assert options.wilson_line_include_unselected_traces is False
    assert options.use_matchete_fluctuation_dof_basis is True
    assert options.wilson_line_weight_paths_by_component_dofs is True
    assert options.wilson_line_expose_scalar_derivative_commutator_bilinears is True
    assert options.wilson_line_expose_scalar_eom_terms is True
    assert options.wilson_line_tensor_reduce_before_wilson_expand is True
    assert options.bosonic_cde_expansion_indices_by_trace is None


def test_validation_fixture_gap_report_can_filter_direct_wilson_line_terms_by_projected_targets() -> None:
    theory = Theory("validation_fixture_direct_wilson_line_filter")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    z = theory.define_coupling("z", self_conjugate=True)
    wilson = theory.define_wilson_coefficient("cPhi2", operator=light() ** 2)
    target = s.Coupling(wilson.label, s.List(), Expression.num(0))
    target_name = canonical_string(target)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(light)
        - y() * heavy() * light() ** 2 / 2
        - z() * heavy() ** 2 / 2
    )
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    fixture = ValidationFixture(
        name="validation_fixture_direct_wilson_line_filter",
        kind="model_smoke",
        state=state,
        source={"generator": "pytest", "mathematica_runtime_required": False},
        expression_names=("lagrangian",),
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=lagrangian,
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={target_name: Expression.num(0)},
    )

    with pytest.raises(ValueError, match="project_reference_matching_conditions"):
        fixture.one_loop_preview_gap_report(
            reference,
            reference_name="direct_wilson_line_filter_reference",
            wilson_line_filter_terms_by_matching_targets=True,
        )

    report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="direct_wilson_line_filter_reference",
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.VAKINT,
        wilson_line_trace_names=("hScalar", "hScalar-lScalar"),
        wilson_line_max_total_order=0,
        wilson_line_filter_terms_by_matching_targets=True,
        use_matchete_fluctuation_dof_basis=True,
        wilson_line_weight_paths_by_component_dofs=True,
        project_reference_matching_conditions=True,
    )

    assert report.candidate_stage == "interaction_wilson_line_hybrid_vakint_result"
    assert report.matching_condition_projection_registered_wilson_names == (target_name,)
    assert report.candidate_matching_condition_names == (target_name,)
    assert report.reference_matching_condition_names == (target_name,)
    assert report.candidate_metadata["wilson_line_terms_filtered_by_matching_targets"] is True
    assert report.candidate_metadata["interaction_wilson_line_terms_filtered_by_matching_targets"] is True
    assert report.candidate_metadata["matchete_fluctuation_dof_basis"] is True
    assert report.candidate_metadata["interaction_wilson_line_paths_weighted_by_component_dofs"] is True
    assert report.candidate_metadata["interaction_wilson_line_plan_entry_count"] == 2
    candidate_entry_counts = report.candidate_metadata["interaction_wilson_line_term_count_by_entry"]
    assert len(candidate_entry_counts) == 2
    assert sum(candidate_entry_counts.values()) == report.candidate_metadata["interaction_wilson_line_term_count"]
    assert "interaction_wilson_line_term_count_by_trace" in report.to_json_obj()["candidate_metadata"]
    assert report.to_json_obj()["candidate_metadata"]["interaction_wilson_line_plan_entry_count"] == 2


def test_validation_fixture_gap_report_can_filter_public_cde_terms_by_projected_targets() -> None:
    theory = Theory("validation_fixture_public_cde_filter")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    wilson = theory.define_wilson_coefficient("cPhi2", operator=light() ** 2)
    target = s.Coupling(wilson.label, s.List(), Expression.num(0))
    target_name = canonical_string(target)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    fixture = ValidationFixture(
        name="validation_fixture_public_cde_filter",
        kind="model_smoke",
        state=state,
        source={"generator": "pytest", "mathematica_runtime_required": False},
        expression_names=("lagrangian",),
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=lagrangian,
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={target_name: Expression.num(0)},
    )

    with pytest.raises(ValueError, match="use_public_match_api"):
        fixture.one_loop_preview_gap_report(
            reference,
            reference_name="public_cde_filter_reference",
            bosonic_cde_filter_terms_by_matching_targets=True,
        )

    report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="public_cde_filter_reference",
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.VAKINT,
        bosonic_cde_expansion_indices_by_trace={"hScalar-lScalar": ((), ())},
        bosonic_cde_filter_terms_by_matching_targets=True,
        project_reference_matching_conditions=True,
        use_public_match_api=True,
    )

    assert report.candidate_stage == "interaction_bosonic_cde_hybrid_vakint_result"
    assert report.matching_condition_projection_registered_wilson_names == (target_name,)
    assert report.candidate_matching_condition_names == (target_name,)
    assert report.reference_matching_condition_names == (target_name,)


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

    wilson_only_report = fixture.one_loop_preview_gap_report(
        reference,
        project_reference_matching_conditions=True,
        matching_condition_projection_names=("cPhi2",),
        matching_condition_include_coupling_identities=False,
    )
    assert wilson_only_report.common_matching_condition_names == (wilson_name,)
    assert wilson_only_report.candidate_matching_condition_names == (wilson_name,)
    assert wilson_only_report.reference_matching_condition_names == (wilson_name,)
    assert wilson_only_report.matching_condition_projection_registered_wilson_names == (wilson_name,)
    assert wilson_only_report.matching_condition_projection_reference_non_wilson_names == ()

    all_wilsons_report = fixture.one_loop_preview_gap_report(
        reference,
        project_reference_matching_conditions=True,
        matching_condition_projection_names="wilson",
        matching_condition_include_coupling_identities=False,
    )
    assert all_wilsons_report.common_matching_condition_names == (wilson_name,)
    assert all_wilsons_report.matching_condition_projection_registered_wilson_names == (wilson_name,)

    with pytest.raises(ValueError, match="Unknown matching-condition projection name"):
        fixture.one_loop_preview_gap_report(
            reference,
            project_reference_matching_conditions=True,
            matching_condition_projection_names=("missing_target",),
        )


def test_singlet_reference_chd_records_matchete_eom_simplify_delta() -> None:
    reference = load_validation_fixture(
        Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json")
    ).matching_result("matchete_previous")
    theory = reference.theory
    registered_targets = registered_wilson_matching_condition_targets(theory, basis="SMEFT")
    condition_name, target = next(
        (name, target)
        for name, target in registered_targets.items()
        if "external_cHD" in name
    )

    off_shell = reference.project_matching_conditions(
        {condition_name: target},
        source="off_shell_eft_lagrangian",
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )[condition_name]
    on_shell = reference.project_matching_conditions(
        {condition_name: target},
        source="on_shell_eft_lagrangian",
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )[condition_name]
    hbar = theory.external_handle("hbar")()
    source = theory.coupling_handle("A")()
    hypercharge = theory.coupling_handle("gY")()
    mass = theory.coupling_handle("M")()
    epsilon = theory.external_handle("epsilon")()
    mubar_squared = theory.external_handle("mubar2")()
    expected_off_shell = (
        -Expression.num(3) * hbar * source**2 * hypercharge**2 / (2 * epsilon * mass**4)
        - Expression.num(5) * hbar * source**2 * hypercharge**2 / (4 * mass**4)
        - Expression.num(3)
        * hbar
        * source**2
        * hypercharge**2
        * (mubar_squared / mass**2).log()
        / (2 * mass**4)
    )
    expected_delta = (
        -hbar * source**2 * hypercharge**2 / (6 * epsilon * mass**4)
        - Expression.num(17) * hbar * source**2 * hypercharge**2 / (36 * mass**4)
        - hbar * source**2 * hypercharge**2 * (mubar_squared / mass**2).log() / (6 * mass**4)
    )

    assert_expr_equal((off_shell - expected_off_shell).collect_factors(), Expression.num(0))
    assert_expr_equal(((on_shell - off_shell).expand() - expected_delta).collect_factors(), Expression.num(0))
    assert_expr_equal((on_shell - reference.matching_conditions[condition_name]).collect_factors(), Expression.num(0))


def test_singlet_reference_chd_debug_records_matchete_fields_to_shift() -> None:
    debug = json.loads(
        Path("assets/validation/matchete/debug/singlet_eom_cHD.debug.json").read_text(encoding="utf-8")
    )
    fields_to_shift = debug["fields_to_shift_input_form"]
    preparation = debug["fields_to_shift_preparation"]
    higgs_shift = debug["higgs_scalar_shift_summary"]

    assert "{H, 4}" in fields_to_shift
    assert "{B, 4}" not in fields_to_shift
    assert preparation["eom_term_count"] == 6
    for label in ("d", "e", "l", "q", "u", "H"):
        assert label in preparation["eom_field_labels_input_form"]
    assert higgs_shift["available"] is True
    assert higgs_shift["field_type_input_form"] == "Scalar"
    assert higgs_shift["self_conjugate"] is False
    assert higgs_shift["eom_terms_containing_h_count"] == 1
    assert "Matchete`PackageScope`EoM[Field[H" in "".join(higgs_shift["sample_h_eom_terms_input_form"])
    assert "Field[{H, _, 0}" in higgs_shift["rules_input_form"]


def test_singlet_reference_chd_debug_records_field_redefinition_replay_boundary() -> None:
    debug = json.loads(
        Path("assets/validation/matchete/debug/singlet_eom_cHD.debug.json").read_text(encoding="utf-8")
    )
    expected_stage_names = [
        "source",
        "after_renormalize_matter",
        "after_shift_dim5_dev3",
        "after_shift_dim5_dev2",
        "after_shift_dim5_dev1",
        "after_shift_dim6_dev4",
        "after_shift_dim6_dev3",
        "after_shift_dim6_dev2",
        "after_shift_dim6_dev1",
    ]

    for key, source_name in (
        ("field_redefinition_replay_off_shell", "saved_off_shell"),
        ("field_redefinition_replay_supertrace_sum", "saved_supertrace_sum"),
    ):
        replay = debug[key]
        assert replay["source_name"] == source_name
        assert replay["max_order"] == 6
        assert "{H, 4}" in replay["fields_to_shift_input_form"]
        stages = replay["stages"]
        assert [stage["name"] for stage in stages] == expected_stage_names
        assert {stage["delta_from_off_shell_input_form"] for stage in stages} == {"0"}
        assert {stage["delta_from_replay_source_input_form"] for stage in stages} == {"0"}


def test_singlet_reference_chd_debug_records_raw_eom_boundary() -> None:
    debug = json.loads(
        Path("assets/validation/matchete/debug/singlet_eom_cHD.debug.json").read_text(encoding="utf-8")
    )
    boundary = debug["raw_lagrangian_eft_eom_boundary"]

    assert boundary["source_name"] == "raw_lagrangian_eft"
    assert "{H, 4}" in boundary["fields_to_shift_input_form"]
    assert "{B, 4}" not in boundary["fields_to_shift_input_form"]
    stages = {stage["name"]: stage for stage in boundary["stages"]}
    assert list(stages) == [
        "raw_lagrangian_eft",
        "after_internal_simplify",
        "after_perform_systematic_field_redefs",
        "after_greens_simplify",
        "direct_eom_simplify",
    ]
    assert stages["raw_lagrangian_eft"]["delta_from_boundary_source_input_form"] == "0"
    assert stages["raw_lagrangian_eft"]["delta_from_off_shell_input_form"] != "0"
    assert stages["raw_lagrangian_eft"]["delta_from_on_shell_input_form"] != "0"
    assert stages["after_internal_simplify"]["delta_from_off_shell_input_form"] == "0"
    assert stages["after_internal_simplify"]["delta_from_on_shell_input_form"] != "0"
    for stage_name in (
        "after_perform_systematic_field_redefs",
        "after_greens_simplify",
        "direct_eom_simplify",
    ):
        assert stages[stage_name]["delta_from_on_shell_input_form"] == "0"
        assert stages[stage_name]["delta_from_off_shell_input_form"] != "0"


def test_singlet_reference_chd_debug_records_vector_shift_split() -> None:
    debug = json.loads(
        Path("assets/validation/matchete/debug/singlet_eom_cHD.debug.json").read_text(encoding="utf-8")
    )
    split = debug["raw_lagrangian_eft_eom_boundary"]["internal_vector_shift_dim6_dev3_split"]
    summaries = {row["field_input_form"]: row for row in split["field_summaries"]}

    assert split["dim"] == 6
    assert split["devs"] == 3
    assert split["fields_input_form"] == "{B, W}"
    assert set(summaries) == {"B", "W"}
    assert summaries["B"]["selected_term_count"] == 6
    assert summaries["W"]["selected_term_count"] == 6
    assert "6 + 17*\\[Epsilon] + 6*\\[Epsilon]*Log" in summaries["B"]["delta_from_source_input_form"]
    assert "Coupling[gY, {}, 0]^2" in summaries["B"]["delta_from_source_input_form"]
    assert summaries["W"]["delta_from_source_input_form"] == "0"
    assert all("EoM[Field[B" in term for term in summaries["B"]["selected_terms_input_form"])
    assert all("EoM[Field[W" in term for term in summaries["W"]["selected_terms_input_form"])
    assert all("CG[gen[SU2L[fund]]" in term for term in summaries["W"]["selected_terms_input_form"])


def test_singlet_reference_chd_debug_records_inert_gamma_vector_source_split() -> None:
    debug = json.loads(
        Path("assets/validation/matchete/debug/singlet_eom_cHD.debug.json").read_text(encoding="utf-8")
    )
    inert = debug["raw_lagrangian_eft_inert_gamma_eom_boundary"]
    bar_summary = inert["barH_EOMB_DH_normalized_source_coefficient"]
    dbar_summary = inert["DbarH_EOMB_H_normalized_source_coefficient"]

    assert inert["controls"] == {
        "evaluate_gamma_factor": "inert",
        "replacement_input_form": "EvaluateGammaFactor[n_Integer, dim_] := SG[n, dim]",
        "reduction_identities": "dDimensional",
        "devs": 3,
        "dim": 6,
    }
    assert inert["split"]["fields_input_form"] == "{B, W}"
    assert inert["raw_b_selected_term_count"] == 0
    assert inert["raw_w_selected_term_count"] == 0
    assert inert["raw_barH_EOMB_DH_normalized_source_coefficient"] == {
        "term_count": 0,
        "terms_input_form": [],
        "normalized_coefficient_input_form": "0",
    }
    assert inert["raw_DbarH_EOMB_H_normalized_source_coefficient"] == {
        "term_count": 0,
        "terms_input_form": [],
        "normalized_coefficient_input_form": "0",
    }
    assert inert["b_selected_term_count"] == 12
    assert inert["w_selected_term_count"] == 12
    assert bar_summary["term_count"] == 6
    assert dbar_summary["term_count"] == 6
    assert "Matchete`PackageScope`SG[1, 4] - 8*Matchete`PackageScope`SG[2, 4]" in (
        bar_summary["normalized_coefficient_input_form"]
    )
    assert "1 + \\[Epsilon] + \\[Epsilon]*Log" in bar_summary["normalized_coefficient_input_form"]
    assert bar_summary["normalized_coefficient_input_form"].startswith("-(")
    assert dbar_summary["normalized_coefficient_input_form"].startswith("((")
    assert any("*Matchete`PackageScope`SG[1, 4]" in term for term in inert["b_selected_terms_input_form"])
    assert any("8*I" in term and "*Matchete`PackageScope`SG[2, 4]" in term for term in inert["b_selected_terms_input_form"])
    identity_summary = inert["b_operator_identity_summary"]
    assert identity_summary["matched_atomic_count"] == 2
    assert len(identity_summary["class_summaries"]) == 1
    class_summary = identity_summary["class_summaries"][0]
    assert class_summary["op_class_input_form"] == "{{H, Matchete`PackageScope`Conj[H]}, 4}"
    assert class_summary["matched_ids"] == [13, 14]
    assert class_summary["identity_rule_count"] == 27
    assert class_summary["touching_rule_count"] == 2
    operators = {operator["id"]: operator for operator in class_summary["operator_summaries"]}
    assert operators[13]["score_input_form"] == "10000."
    assert operators[14]["score_input_form"] == "10000."
    assert "{B}" in operators[13]["subclass_input_form"]
    assert "{{H, 0}, {Matchete`PackageScope`Conj[H], 1}}" in operators[13]["subclass_input_form"]
    assert "{{H, 1}, {Matchete`PackageScope`Conj[H], 0}}" in operators[14]["subclass_input_form"]
    assert "EoM[Field[B" in operators[13]["operator_form_input_form"]
    assert "EoM[Field[B" in operators[14]["operator_form_input_form"]
    assert all("FieldStrength[B" in rule for rule in class_summary["touching_rules_normal_form_input_form"])


def test_singlet_reference_chd_source_map_is_single_four_slot_supertrace() -> None:
    reference = load_validation_fixture(
        Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json")
    ).matching_result("matchete_previous")
    theory = reference.theory
    registered_targets = registered_wilson_matching_condition_targets(theory, basis="SMEFT")
    condition_name, target = next(
        (name, target)
        for name, target in registered_targets.items()
        if "external_cHD" in name
    )

    contributions = reference.project_matching_conditions_by_source(
        {condition_name: target},
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )
    nonzero = {
        source_name: projected[condition_name]
        for source_name, projected in contributions.items()
        if canonical_string(projected[condition_name].expand()) != "0"
    }
    off_shell = reference.project_matching_conditions(
        {condition_name: target},
        source="off_shell_eft_lagrangian",
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )[condition_name]

    assert tuple(nonzero) == ("hScalar-lScalar-lVector-lScalar",)
    assert_expr_equal(
        (nonzero["hScalar-lScalar-lVector-lScalar"] - off_shell).collect_factors(),
        Expression.num(0),
    )


def test_singlet_model_higgs_eom_rules_are_available_for_reference_laplacians() -> None:
    model = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    reference = load_validation_fixture(
        Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json")
    ).matching_result("matchete_previous")
    theory = reference.theory
    registered_targets = registered_wilson_matching_condition_targets(theory, basis="SMEFT")
    condition_name, target = next(
        (name, target)
        for name, target in registered_targets.items()
        if "external_cHD" in name
    )

    rules = theory.eom_replacement_rules_for_expression(
        model.expression("lagrangian"),
        reference.off_shell_eft_lagrangian,
        fields=[theory.field_handle("H")],
        strict=False,
    )
    reduced_off_shell = reference.off_shell_eft_lagrangian.replace_multiple(rules).expand()
    reduced_result = MatchingResult(
        theory=theory,
        uv_lagrangian=reference.uv_lagrangian,
        off_shell_eft_lagrangian=reduced_off_shell,
        on_shell_eft_lagrangian=reduced_off_shell,
    )
    off_shell = reference.project_matching_conditions(
        {condition_name: target},
        source="off_shell_eft_lagrangian",
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )[condition_name]
    reduced = reduced_result.project_matching_conditions(
        {condition_name: target},
        source="on_shell_eft_lagrangian",
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )[condition_name]

    assert len(rules) == 2
    assert_expr_equal(reduced, off_shell)


def test_singlet_reference_chd_vector_eom_field_redefinition_reaches_matchete_on_shell() -> None:
    model = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    reference = load_validation_fixture(
        Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json")
    ).matching_result("matchete_previous")
    theory = reference.theory
    registered_targets = registered_wilson_matching_condition_targets(theory, basis="SMEFT")
    condition_name, target = next(
        (name, target)
        for name, target in registered_targets.items()
        if "external_cHD" in name
    )
    vector = theory.field_handle("B")
    rules = theory.eom_replacement_rules_for_expression(
        model.expression("lagrangian"),
        reference.off_shell_eft_lagrangian,
        fields=[vector],
        strict=True,
    )
    delta = abelian_vector_eom_field_redefinition_delta(
        theory,
        model.expression("lagrangian"),
        reference.off_shell_eft_lagrangian,
        fields=[vector],
        strict=True,
    )
    reduced = (reference.off_shell_eft_lagrangian.replace_multiple(rules) + delta).expand()
    reduced_result = MatchingResult(
        theory=theory,
        uv_lagrangian=reference.uv_lagrangian,
        off_shell_eft_lagrangian=reduced,
        on_shell_eft_lagrangian=reduced,
    )
    projected = reduced_result.project_matching_conditions(
        {condition_name: target},
        source="on_shell_eft_lagrangian",
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )[condition_name]

    assert len(rules) == 1
    assert not bool(delta == Expression.num(0))
    assert_expr_equal((projected - reference.matching_conditions[condition_name]).collect_factors(), Expression.num(0))


@pytest.mark.slow
@pytest.mark.parametrize(
    (
        "target_name",
        "gauge_couplings",
        "denominator",
        "expected_term_count",
        "expected_nonzero_entries",
    ),
    [
        ("cHW", ("gL", "gL"), 12, 10, ("hScalar-lScalar#wilson14_o4_0",)),
        ("cHB", ("gY", "gY"), 12, 10, ("hScalar-lScalar#wilson14_o4_0",)),
        (
            "cHWB",
            ("gL", "gY"),
            6,
            14,
            ("hScalar-lScalar#wilson5_o2_0", "hScalar-lScalar#wilson14_o4_0"),
        ),
    ],
)
def test_singlet_wilson_line_gap_report_accepts_selected_higgs_gauge_targets_against_matchete_fixture(
    target_name: str,
    gauge_couplings: tuple[str, ...],
    denominator: int,
    expected_term_count: int,
    expected_nonzero_entries: tuple[str, ...],
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    reference_fixture = load_validation_fixture(
        Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json")
    )
    reference = reference_fixture.matching_result("matchete_previous")
    theory = fixture.theory()
    hbar = theory.external_handle("hbar")()
    wilson = theory.external_handle(target_name)
    condition_name = canonical_string(
        s.Coupling(wilson.label, s.List(*wilson.definition.index_exprs), Expression.num(0))
    )

    report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="Singlet_Scalar_Extension.matchete_previous",
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
        normalization=OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
        hbar=hbar,
        wilson_line_trace_names=("hScalar-lScalar",),
        wilson_line_max_total_order=4,
        wilson_line_max_slot_order=4,
        wilson_line_index_prefix=f"singlet_{target_name}_gap",
        wilson_line_act_open_derivatives=True,
        wilson_line_emit_covariant_derivative_commutators=False,
        wilson_line_emit_covariant_derivative_commutator_passes=1,
        wilson_line_covariant_derivative_commutator_mode="all_distinct",
        wilson_line_expand_covariant_derivative_commutators=False,
        wilson_line_max_derivative_order=4,
        wilson_line_filter_terms_by_matching_targets=True,
        use_matchete_fluctuation_dof_basis=True,
        wilson_line_weight_paths_by_component_dofs=False,
        wilson_line_expose_scalar_derivative_commutator_bilinears=True,
        wilson_line_tensor_reduce_before_wilson_expand=True,
        simplify_pychete_color_algebra=True,
        project_reference_matching_conditions=True,
        matching_condition_projection_names=(target_name,),
        matching_condition_projection_source="on_shell_eft_lagrangian",
        matching_condition_projection_expand_source=False,
        matching_condition_projection_truncate_eft=True,
        matching_condition_projection_drop_zero=False,
    )

    expected = reference.theory.external_handle("hbar")() * reference.theory.coupling_handle("A")() ** 2
    for coupling in gauge_couplings:
        expected *= reference.theory.coupling_handle(coupling)()
    expected /= denominator * reference.theory.coupling_handle("M")() ** 4

    assert_expr_equal(reference.matching_conditions[condition_name], expected)
    assert report.candidate_stage == "normalized_interaction_wilson_line_hybrid_internal_minimal_subtraction_result"
    assert report.candidate_matching_condition_count == 1
    assert report.reference_matching_condition_count == 1
    assert report.common_matching_condition_names == (condition_name,)
    assert report.accepted_common_wilson_matching_condition_names == (condition_name,)
    assert report.different_after_probe_common_matching_condition_names == ()
    assert report.matching_condition_projection_registered_wilson_names == (condition_name,)
    assert report.candidate_metadata["interaction_wilson_line_tensor_reduce_before_wilson_expand"] is True
    assert report.candidate_metadata["matchete_fluctuation_dof_basis"] is True
    assert report.candidate_metadata["interaction_wilson_line_paths_weighted_by_component_dofs"] is False
    nonzero_entries = tuple(report.candidate_metadata["interaction_wilson_line_nonzero_plan_entries"])
    assert nonzero_entries == expected_nonzero_entries
    assert sum(report.candidate_metadata["interaction_wilson_line_term_count_by_entry"].values()) == expected_term_count
    assert report.candidate_metadata["interaction_wilson_line_component_weighted_term_count"] == expected_term_count


@pytest.mark.slow
def test_singlet_wilson_line_gap_report_accepts_selected_chd_against_matchete_fixture() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    reference = load_validation_fixture(
        Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json")
    ).matching_result("matchete_previous")
    theory = fixture.theory()
    condition_name, _target = next(
        (name, target)
        for name, target in registered_wilson_matching_condition_targets(theory, basis="SMEFT").items()
        if "external_cHD" in name
    )

    report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="Singlet_Scalar_Extension.matchete_previous",
        max_trace_order=4,
        integral_backend=OneLoopIntegralBackend.INTERNAL,
        normalization=OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
        hbar=theory.external_handle("hbar")(),
        epsilon=theory.external_handle("epsilon")(),
        mu_r_squared=theory.external_handle("mubar2")(),
        use_public_match_api=True,
        wilson_line_trace_names=("hScalar-lScalar", "hScalar-lScalar-lVector-lScalar"),
        wilson_line_max_total_order=4,
        wilson_line_max_slot_order=4,
        wilson_line_total_orders_by_trace={
            "hScalar-lScalar": (0, 2, 4),
            "hScalar-lScalar-lVector-lScalar": (0, 1, 2),
        },
        wilson_line_index_prefix="singlet_cHD_gap",
        wilson_line_act_open_derivatives=True,
        wilson_line_emit_covariant_derivative_commutators=False,
        wilson_line_emit_covariant_derivative_commutator_passes=1,
        wilson_line_covariant_derivative_commutator_mode="all_distinct",
        wilson_line_expand_covariant_derivative_commutators=False,
        wilson_line_max_derivative_order=4,
        wilson_line_filter_terms_by_matching_targets=True,
        wilson_line_include_unselected_traces=False,
        use_matchete_fluctuation_dof_basis=True,
        wilson_line_weight_paths_by_component_dofs=True,
        wilson_line_expose_scalar_derivative_commutator_bilinears=True,
        wilson_line_expose_scalar_eom_terms=True,
        wilson_line_tensor_reduce_before_wilson_expand=True,
        simplify_pychete_color_algebra=True,
        substitute_heavy_scalar_solutions=True,
        on_shell_eom_lagrangian=fixture.expression("lagrangian"),
        on_shell_eom_fields=[theory.field_handle("B")],
        on_shell_eom_abelian_vector_field_redefinition=True,
        project_reference_matching_conditions=True,
        matching_condition_projection_names=("cHD",),
        matching_condition_projection_source="on_shell_eft_lagrangian",
        matching_condition_projection_expand_source=False,
        matching_condition_projection_truncate_eft=True,
        matching_condition_projection_drop_zero=False,
        truncate_eft_result=False,
        expand_loop_scale_logs_for_comparison=True,
    )

    assert report.candidate_stage == "normalized_interaction_wilson_line_internal_integral_result"
    assert report.candidate_matching_condition_count == 1
    assert report.reference_matching_condition_count == 1
    assert report.common_matching_condition_names == (condition_name,)
    assert report.accepted_common_wilson_matching_condition_names == (condition_name,)
    assert report.different_after_probe_common_matching_condition_names == ()
    assert report.matching_condition_projection_registered_wilson_names == (condition_name,)
    assert report.candidate_metadata["matching_condition_projection_source"] == "staged"
    assert report.candidate_metadata["wilson_line_selected_only"] is True
    assert report.candidate_metadata["wilson_line_include_unselected_traces"] is False
    assert report.candidate_metadata["wilson_line_total_orders_by_trace"] == (
        "hScalar-lScalar:0,2,4;hScalar-lScalar-lVector-lScalar:0,1,2"
    )
    assert report.candidate_metadata["interaction_wilson_line_term_count"] == 68
    assert report.candidate_metadata["interaction_wilson_line_component_weighted_term_count"] == 136
    assert report.candidate_metadata["wilson_line_on_shell_projection_source_count"] == 24


@pytest.mark.slow
def test_singlet_wilson_line_filter_keeps_derivative_higgs_sources_staged_for_projection() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    wilson = theory.external_handle("cHD")
    condition_name = canonical_string(
        s.Coupling(wilson.label, s.List(*wilson.definition.index_exprs), Expression.num(0))
    )
    targets = {condition_name: registered_wilson_matching_condition_targets(theory)[condition_name]}

    common_options = dict(
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
        normalization=OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
        hbar=theory.external_handle("hbar")(),
        wilson_line_trace_names=("hScalar-lScalar",),
        wilson_line_max_total_order=0,
        wilson_line_max_slot_order=0,
        wilson_line_act_open_derivatives=True,
        wilson_line_covariant_derivative_commutator_mode="all_distinct",
        wilson_line_max_derivative_order=4,
        wilson_line_filter_terms_by_matching_targets=True,
        wilson_line_expose_scalar_derivative_commutator_bilinears=True,
        wilson_line_tensor_reduce_before_wilson_expand=True,
        simplify_pychete_color_algebra=True,
        matching_condition_targets=targets,
    )
    raw = fixture.one_loop_preview(
        **common_options,
        wilson_line_index_prefix="singlet_cHD_raw_filter",
        substitute_heavy_scalar_solutions=False,
    )
    eom_aware = fixture.one_loop_preview(
        **common_options,
        wilson_line_index_prefix="singlet_cHD_eom_filter",
        substitute_heavy_scalar_solutions=True,
    )

    expected_staged_sources = (
        "wilson_line_on_shell_projection_source[hScalar-lScalar#wilson0_o0_0]",
        "wilson_line_on_shell_projection_source[interaction_power_type_remainder]",
    )
    for preview in (raw, eom_aware):
        staged_sources = preview.staged_projection_sources()

        assert preview.metadata["interaction_wilson_line_term_count"] == 4
        assert preview.metadata["interaction_wilson_line_nonzero_plan_entries"] == (
            "hScalar-lScalar#wilson0_o0_0",
        )
        assert preview.metadata["wilson_line_on_shell_projection_source_count"] == 2
        assert preview.metadata["wilson_line_on_shell_projection_sources"] == ",".join(expected_staged_sources)
        assert preview.metadata["field_derivative_metric_simplified"] is True
        assert preview.metadata["field_strength_metric_simplified"] is True
        assert staged_sources == expected_staged_sources
    assert eom_aware.metadata["heavy_scalar_solutions_substituted"] is True


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


def test_validation_fixture_gap_report_can_expand_loop_scale_logs_for_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    mass = theory.coupling_handle("M")()
    scale = theory.external_handle("mubar2")()
    candidate_expr = (scale.log() - 2 * mass.log()).expand()
    reference_expr = (scale / mass**2).log()
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"scale_log": candidate_expr},
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"scale_log": reference_expr},
    )

    def fake_preview(self: object, **_kwargs: object) -> MatchingResult:
        return candidate

    monkeypatch.setattr(type(fixture), "one_loop_preview", fake_preview)

    raw_report = fixture.one_loop_preview_gap_report(reference, reference_name="scale_log_reference")
    transformed_report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="scale_log_reference",
        mu_r_squared=scale,
        expand_loop_scale_logs_for_comparison=True,
    )

    assert raw_report.canonical_equal_common_supertrace_names == ()
    assert raw_report.canonical_different_common_supertrace_names == ("scale_log",)
    assert transformed_report.canonical_equal_common_supertrace_names == ("scale_log",)
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


def test_validation_fixture_gap_report_resolves_registered_hbar_for_matchete_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
    )
    captured: dict[str, object] = {}

    def fake_preview(self: object, **kwargs: object) -> MatchingResult:
        captured.update(kwargs)
        return candidate

    monkeypatch.setattr(type(fixture), "one_loop_preview", fake_preview)
    fixture.one_loop_preview_gap_report(
        candidate,
        reference_name="hbar_reference",
        normalization=OneLoopNormalization.MATCHETE_HBAR,
    )

    assert_expr_equal(captured["hbar"], theory.external_handle("hbar")())


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
