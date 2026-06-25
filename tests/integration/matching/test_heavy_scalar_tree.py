from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import (
    FieldMassKind,
    MatchingResult,
    OneLoopIntegralBackend,
    OneLoopMatchOptions,
    OneLoopSetup,
    OneLoopNormalization,
    Theory,
    VakintIntegralStage,
    canonical_string,
    one_loop_normalization_factor,
    s,
)
from pychete.backends import spenso as spenso_backend
from pychete.expr import index_pattern
from pychete.tree_matching import HeavyScalarSolution, heavy_scalar_solution_replacements

from tests.conftest import assert_expr_equal


class FakeTensorNetwork:
    def __init__(self, expr: Expression) -> None:
        self.expr = expr


class FakePoleVakintEngine:
    def __init__(self, evaluated: Expression) -> None:
        self.evaluated = evaluated
        self.calls: list[Expression] = []

    def evaluate(self, expr: Expression) -> Expression:
        self.calls.append(expr)
        return self.evaluated


def _heavy_scalar_theory() -> tuple[Theory, object, object, object]:
    theory = Theory("heavy_scalar")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    g = theory.define_coupling("g", self_conjugate=True)
    return theory, heavy, light, g


def test_heavy_scalar_eom_and_fixed_order_solution_match_reference() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    mu = theory.dummy_index(0)
    u3 = theory.dummy_index(3)
    mass = theory.coupling_handle("M")
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2

    eom = theory.derive_eom(lagrangian, heavy)
    expected_eom = -mass() ** 2 * heavy() - heavy(derivatives=[mu, mu]) - g() * phi() ** 2 / 2
    assert_expr_equal(eom, expected_eom)

    solution = theory.solve_heavy_scalar_eoms(lagrangian, eft_order=6)["S"]
    assert_expr_equal(solution.orders[1], -g() * phi() ** 2 / (2 * mass() ** 2))
    assert_expr_equal(solution.orders[2], Expression.num(0))
    assert_expr_equal(
        solution.orders[3],
        g() * (phi(derivatives=[u3]) ** 2 + phi() * phi(derivatives=[u3, u3])) / mass() ** 4,
    )


def test_heavy_scalar_tree_match_through_dimension_six() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    mu = theory.dummy_index(0)
    mass = theory.coupling_handle("M")
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2

    matched = theory.match(lagrangian, eft_order=6)
    expected = (
        phi(derivatives=[mu]) ** 2 / 2
        + g() ** 2 * phi() ** 4 / (8 * mass() ** 2)
        + g() ** 2 * phi() ** 2 * phi(derivatives=[mu]) ** 2 / (2 * mass() ** 4)
    )

    assert_expr_equal(matched, expected)


def test_tree_match_loop_order_zero_preserves_existing_result() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2

    assert_expr_equal(
        theory.match(lagrangian, eft_order=6, loop_order=0),
        theory.match(lagrangian, eft_order=6),
    )


def test_one_loop_match_request_returns_incomplete_internal_minimal_subtraction_result() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2

    result = theory.match(lagrangian, eft_order=6, loop_order=1)

    assert isinstance(result, MatchingResult)
    assert result.metadata["loop_order"] == 1
    assert result.metadata["complete"] is False
    assert result.metadata["stage"] == "interaction_power_type_internal_minimal_subtraction_result"
    assert result.metadata["subtraction_scheme"] == "minimal_subtraction_preview"
    assert result.metadata["poles_subtracted"] is True
    assert result.metadata["integral_backend"] == "pychete_internal"
    assert result.metadata["tensor_reduce"] is False
    assert result.metadata["combine_terms"] is True
    assert result.metadata["uses_interaction_operator"] is True
    assert "interaction_power_type_internal_integral_sum" in result.supertraces
    assert "interaction_power_type_internal_integral_ms_counterterm" in result.supertraces
    assert_expr_equal(
        result.off_shell_eft_lagrangian,
        result.expression("interaction_power_type_internal_integral_finite_part"),
    )
    assert_expr_equal(
        result.on_shell_eft_lagrangian,
        result.expression("interaction_power_type_internal_integral_finite_part"),
    )
    result.validate()


def test_one_loop_match_can_project_requested_matching_conditions() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    unused = theory.define_coupling("unused", self_conjugate=True)
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    target = g() ** 2 * phi() ** 2
    wilson = theory.define_wilson_coefficient("cPhi2", operator=target)
    wilson_name = canonical_string(s.Coupling(wilson.label, s.List(), Expression.num(0)))

    result = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        matching_condition_targets={
            "g2_phi2": target,
            "unused": unused(),
        },
        matching_condition_expand_source=False,
        matching_condition_truncate_eft=True,
        matching_condition_drop_zero=True,
    )

    assert isinstance(result, MatchingResult)
    expected = result.on_shell_eft_lagrangian.coefficient(target).expand()
    assert set(result.matching_conditions) == {"g2_phi2"}
    assert_expr_equal(result.matching_conditions["g2_phi2"], expected)
    assert canonical_string(expected) != "0"
    assert result.metadata["matching_conditions_projected"] is True
    assert result.metadata["matching_condition_projection_source"] == "on_shell_eft_lagrangian"
    assert result.metadata["matching_condition_projection_expand_source"] is False
    assert result.metadata["matching_condition_projection_eft_order"] == 6
    assert result.metadata["matching_condition_projection_count"] == 1
    assert result.metadata["matching_condition_projection_coupling_identities"] is False

    with_identity = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        matching_condition_targets={
            "g2_phi2": target,
            "unused": unused(),
        },
        matching_condition_drop_zero=True,
        matching_condition_include_coupling_identities=True,
    )

    assert isinstance(with_identity, MatchingResult)
    assert set(with_identity.matching_conditions) == {"g2_phi2", "unused"}
    assert_expr_equal(with_identity.matching_conditions["unused"], unused())
    assert with_identity.metadata["matching_condition_projection_coupling_identities"] is True

    registered_wilson_projection = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        matching_condition_targets="registered_wilsons",
        matching_condition_drop_zero=True,
    )

    assert isinstance(registered_wilson_projection, MatchingResult)
    assert set(registered_wilson_projection.matching_conditions) == {wilson_name}
    assert_expr_equal(registered_wilson_projection.matching_conditions[wilson_name], expected)


def test_one_loop_match_substitutes_heavy_scalar_solution_before_projection() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    cubic = theory.define_coupling("a", self_conjugate=True)
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2 - cubic() * heavy() ** 3 / 6
    raw_options = OneLoopMatchOptions(
        max_trace_order=2,
        tensor_reduce=False,
        substitute_heavy_scalar_solutions=False,
    )
    options = OneLoopMatchOptions(
        max_trace_order=2,
        tensor_reduce=False,
        substitute_heavy_scalar_solutions=True,
    )

    raw = theory.match(lagrangian, eft_order=6, loop_order=1, one_loop_options=raw_options)
    reduced = theory.match(lagrangian, eft_order=6, loop_order=1, one_loop_options=options)
    heavy_atom = canonical_string(heavy())

    assert isinstance(raw, MatchingResult)
    assert isinstance(reduced, MatchingResult)
    assert raw.metadata["heavy_scalar_solutions_substituted"] is False
    assert raw.metadata["heavy_scalar_solution_source"] == "disabled"
    assert raw.metadata["heavy_scalar_solution_fresh_dummy_indices"] is False
    assert reduced.metadata["heavy_scalar_solutions_substituted"] is True
    assert reduced.metadata["heavy_scalar_solution_count"] == 1
    assert reduced.metadata["heavy_scalar_solution_rule_count"] == 4
    assert reduced.metadata["heavy_scalar_solution_source"] == "matching_lagrangian"
    assert reduced.metadata["heavy_scalar_solution_expand"] is False
    assert reduced.metadata["heavy_scalar_solution_fresh_dummy_indices"] is True
    assert heavy_atom in canonical_string(raw.on_shell_eft_lagrangian)
    assert heavy_atom in canonical_string(reduced.expression("on_shell_eft_lagrangian_before_reduction"))
    assert heavy_atom not in canonical_string(reduced.on_shell_eft_lagrangian)


def test_heavy_scalar_solution_power_rules_use_fresh_dummy_indices() -> None:
    theory = Theory("heavy_scalar_fresh_dummies")
    theory.define_gauge_group("SU2L", s.SU(2), coupling="gL", field="W")
    fund = theory.define_representation("SU2L", "fund")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    higgs = theory.define_field("H", s.Scalar, indices=(fund,))
    index = theory.dummy_index(1, fund)
    solution = HeavyScalarSolution(
        field=heavy.definition,
        orders={1: higgs(index) * s.Bar(higgs(index))},
    )
    rules = heavy_scalar_solution_replacements({"S": solution}, fresh_dummy_indices=True)
    replaced = (heavy() ** 2).replace_multiple(rules).expand()
    index_pat = index_pattern()
    counts: dict[str, int] = {}

    for match in replaced.match(index_pat):
        key = canonical_string(index_pat.replace_wildcards(match))
        counts[key] = counts.get(key, 0) + 1

    assert len(counts) == 2
    assert set(counts.values()) == {2}


def test_one_loop_match_applies_on_shell_reduction_before_condition_projection() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    target = g() ** 2 * phi() ** 2

    result = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            tensor_reduce=False,
            combine_terms=True,
            on_shell_replacements={target: Expression.num(0)},
        ),
        matching_condition_targets={"g2_phi2": target},
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["on_shell_reduced"] is True
    assert result.metadata["on_shell_reduction_replacement_count"] == 1
    assert result.metadata["matching_conditions_projected"] is True
    assert_expr_equal(result.off_shell_eft_lagrangian, result.expression("on_shell_eft_lagrangian_before_reduction"))
    assert_expr_equal(result.on_shell_eft_lagrangian, Expression.num(0))
    assert_expr_equal(result.expression("on_shell_eft_lagrangian_after_reduction"), Expression.num(0))
    assert_expr_equal(result.matching_conditions["g2_phi2"], Expression.num(0))


def test_one_loop_match_generates_eom_replacements_before_condition_projection() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    source = theory.define_coupling("J", self_conjugate=True)
    coefficient = theory.define_coupling("c", self_conjugate=True)
    mu = theory.dummy_index(0)
    derivative_target = phi(derivatives=[mu, mu])
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    eom_lagrangian = theory.free_lag(phi) + source() * phi()
    engine = FakePoleVakintEngine(coefficient() * phi() * derivative_target)

    result = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.VAKINT,
            vakint_stage=VakintIntegralStage.EVALUATED,
            vakint_engine=engine,
            on_shell_eom_lagrangian=eom_lagrangian,
            on_shell_eom_fields=[phi],
            on_shell_eom_strict=True,
        ),
        matching_condition_targets={"c_phi": coefficient() * phi()},
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["on_shell_reduced"] is True
    assert result.metadata["on_shell_eom_reduction_requested"] is True
    assert result.metadata["on_shell_eom_reduction_rule_count"] == 1
    assert result.metadata["matching_conditions_projected"] is True
    assert_expr_equal(result.off_shell_eft_lagrangian, coefficient() * phi() * derivative_target)
    assert_expr_equal(result.on_shell_eft_lagrangian, coefficient() * phi() * source())
    assert_expr_equal(result.matching_conditions["c_phi"], source())


def test_one_loop_match_truncates_eft_result_before_condition_projection() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    coefficient = theory.define_coupling("c", self_conjugate=True)
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    low = coefficient() * phi() ** 4
    high = coefficient() * phi() ** 8
    engine = FakePoleVakintEngine(low + high)

    result = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.VAKINT,
            vakint_stage=VakintIntegralStage.EVALUATED,
            vakint_engine=engine,
        ),
        matching_condition_targets={
            "low": low,
            "high": high,
        },
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["eft_result_truncated"] is True
    assert result.metadata["eft_result_truncation_order"] == 6
    assert result.metadata["stage"] == "interaction_power_type_vakint_result"
    assert_expr_equal(result.expression("on_shell_eft_lagrangian_before_eft_truncation"), low + high)
    assert_expr_equal(result.on_shell_eft_lagrangian, low)
    assert_expr_equal(result.matching_conditions["low"], Expression.num(1))
    assert_expr_equal(result.matching_conditions["high"], Expression.num(0))

    opt_out_engine = FakePoleVakintEngine(low + high)
    untruncated = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.VAKINT,
            vakint_stage=VakintIntegralStage.EVALUATED,
            vakint_engine=opt_out_engine,
            truncate_eft_result=False,
        ),
        matching_condition_targets={
            "low": low,
            "high": high,
        },
    )

    assert isinstance(untruncated, MatchingResult)
    assert untruncated.metadata["eft_result_truncated"] is False
    assert_expr_equal(untruncated.on_shell_eft_lagrangian, low + high)
    assert_expr_equal(untruncated.matching_conditions["high"], Expression.num(1))


def test_one_loop_match_options_select_backend_and_trace_order() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2

    result = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            tensor_reduce=False,
            combine_terms=True,
        ),
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["stage"] == "interaction_power_type_internal_integral_result"
    assert result.metadata["max_trace_order"] == 1
    assert result.metadata["integral_backend"] == "pychete_internal"
    assert result.metadata["tensor_reduce"] is False
    assert result.metadata["combine_terms"] is True


def test_one_loop_match_options_route_public_match_through_spenso(monkeypatch: pytest.MonkeyPatch) -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    calls: list[tuple[Expression, object | None, object | None, int | None, object | None]] = []

    def fake_evaluate_tensor_network(
        expr: Expression,
        *,
        library: object | None = None,
        function_library: object | None = None,
        n_steps: int | None = None,
        mode: object | None = None,
    ) -> FakeTensorNetwork:
        calls.append((expr, library, function_library, n_steps, mode))
        return FakeTensorNetwork(expr)

    def fake_tensor_network_result_scalar(network: FakeTensorNetwork) -> Expression:
        return S("tensor")(network.expr)

    monkeypatch.setattr(spenso_backend, "evaluate_tensor_network", fake_evaluate_tensor_network)
    monkeypatch.setattr(spenso_backend, "tensor_network_result_scalar", fake_tensor_network_result_scalar)

    result = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            tensor_reduce=False,
            evaluate_tensor_networks=True,
            tensor_network_library="library",
            tensor_network_function_library="functions",
            tensor_network_n_steps=5,
            tensor_network_mode="mode",
        ),
    )

    assert isinstance(result, MatchingResult)
    assert calls
    assert calls[0][1:] == ("library", "functions", 5, "mode")
    assert len(calls) == result.metadata["supertrace_kernel_count"]
    assert result.metadata["tensor_networks_evaluated"] is True
    assert result.metadata["tensor_network_cg_component_source"] == "library"
    assert result.metadata["tensor_network_native_hep_cg_builtins"] is False


def test_one_loop_match_option_simplifies_pychete_color_algebra(monkeypatch: pytest.MonkeyPatch) -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    calls: list[dict[str, object]] = []

    def fake_simplify_index_algebra(self: OneLoopSetup, **kwargs: object) -> OneLoopSetup:
        calls.append(kwargs)
        return self

    monkeypatch.setattr(OneLoopSetup, "simplify_index_algebra", fake_simplify_index_algebra)

    result = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            tensor_reduce=False,
            simplify_pychete_color_algebra=True,
        ),
    )

    assert isinstance(result, MatchingResult)
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
    assert result.metadata["pychete_color_algebra_simplified"] is True
    assert result.metadata["native_color_wrappers_decoded"] is True


def test_one_loop_match_options_apply_vakint_normalization() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    raw = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.VAKINT,
        ),
    )
    normalized = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.VAKINT,
            normalization=OneLoopNormalization.MATCHETE_HBAR,
        ),
    )
    factor = one_loop_normalization_factor(OneLoopNormalization.MATCHETE_HBAR)

    assert isinstance(raw, MatchingResult)
    assert isinstance(normalized, MatchingResult)
    assert normalized.metadata["stage"] == "interaction_power_type_normalized_vakint_result"
    assert normalized.metadata["loop_normalization"] == "matchete_hbar"
    assert normalized.metadata["loop_normalization_applied"] is True
    assert_expr_equal(normalized.expression("interaction_power_type_loop_normalization_factor"), factor)
    assert_expr_equal(
        normalized.expression("interaction_power_type_vakint_integral_sum_unnormalized"),
        raw.expression("interaction_power_type_vakint_integral_sum"),
    )
    assert_expr_equal(normalized.off_shell_eft_lagrangian, factor * raw.off_shell_eft_lagrangian)

    custom_factor = S("custom_internal_loop_factor")
    raw_internal = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.INTERNAL,
        ),
    )
    normalized_internal = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            normalization=custom_factor,
        ),
    )

    assert isinstance(raw_internal, MatchingResult)
    assert isinstance(normalized_internal, MatchingResult)
    assert normalized_internal.metadata["stage"] == "normalized_interaction_power_type_internal_integral_result"
    assert normalized_internal.metadata["unnormalized_stage"] == raw_internal.metadata["stage"]
    assert normalized_internal.metadata["loop_normalization"] == "custom"
    assert normalized_internal.metadata["loop_normalization_applied"] is True
    assert_expr_equal(
        normalized_internal.expression("interaction_power_type_loop_normalization_factor"),
        custom_factor,
    )
    assert_expr_equal(
        normalized_internal.expression("interaction_power_type_unnormalized_eft_lagrangian"),
        raw_internal.off_shell_eft_lagrangian,
    )
    assert_expr_equal(
        normalized_internal.expression("interaction_power_type_normalized_internal_integral_finite_part"),
        custom_factor * raw_internal.expression("interaction_power_type_internal_integral_finite_part"),
    )
    assert_expr_equal(
        normalized_internal.off_shell_eft_lagrangian,
        custom_factor * raw_internal.off_shell_eft_lagrangian,
    )


def test_one_loop_match_options_select_vakint_minimal_subtraction_backend() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    eps = S("eps")
    engine = FakePoleVakintEngine(S("double") / eps**2 + S("single") / eps + S("finite"))

    result = theory.match(
        lagrangian,
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=1,
            integral_backend=OneLoopIntegralBackend.VAKINT_MINIMAL_SUBTRACTION,
            vakint_engine=engine,
            max_pole_order=2,
            epsilon=eps,
        ),
    )

    assert isinstance(result, MatchingResult)
    assert engine.calls
    assert result.metadata["stage"] == "interaction_power_type_minimal_subtraction_result"
    assert result.metadata["subtraction_scheme"] == "minimal_subtraction_preview"
    assert result.metadata["poles_subtracted"] is True
    assert result.metadata["vakint_stage"] == "evaluated"
    assert result.metadata["max_pole_order"] == 2
    assert result.metadata["uses_interaction_operator"] is True
    assert_expr_equal(result.off_shell_eft_lagrangian, S("finite"))
    assert_expr_equal(result.on_shell_eft_lagrangian, S("finite"))
    assert_expr_equal(
        result.expression("interaction_power_type_vakint_pole_part"),
        S("double") / eps**2 + S("single") / eps,
    )
    assert_expr_equal(
        result.expression("interaction_power_type_vakint_ms_counterterm"),
        -S("double") / eps**2 - S("single") / eps,
    )
    assert_expr_equal(result.expression("interaction_power_type_vakint_finite_part"), S("finite"))


def test_tree_match_rejects_matching_condition_targets() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2

    with pytest.raises(ValueError, match="loop_order=1"):
        theory.match(lagrangian, matching_condition_targets={"phi": phi()})

    with pytest.raises(ValueError, match="loop_order=1"):
        theory.match(lagrangian, one_loop_options=OneLoopMatchOptions())


def test_one_theory_can_match_two_lagrangians_without_cross_talk() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    h = theory.define_coupling("h", self_conjugate=True)
    mass = theory.coupling_handle("M")
    lagrangian_g = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    lagrangian_h = theory.free_lag(heavy, phi) - h() * heavy() * phi() ** 3

    solution_g = theory.solve_heavy_scalar_eoms(lagrangian_g, eft_order=6)["S"]
    solution_h = theory.solve_heavy_scalar_eoms(lagrangian_h, eft_order=6)["S"]
    assert_expr_equal(solution_g.orders[1], -g() * phi() ** 2 / (2 * mass() ** 2))
    assert_expr_equal(solution_h.orders[1], -h() * phi() ** 3 / mass() ** 2)

    matched_g = theory.match(lagrangian_g, eft_order=6)
    matched_h = theory.match(lagrangian_h, eft_order=6)
    matched_g_text = canonical_string(matched_g)
    matched_h_text = canonical_string(matched_h)

    assert "heavy_scalar::coupling_g" in matched_g_text
    assert "heavy_scalar::coupling_h" not in matched_g_text
    assert "heavy_scalar::coupling_h" in matched_h_text
    assert "heavy_scalar::coupling_g" not in matched_h_text


def test_tree_match_supports_several_independent_diagonal_heavy_scalars() -> None:
    theory = Theory("two_heavy_scalars")
    s_field = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "MS"))
    t_field = theory.define_field("T", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "MT"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    g_s = theory.define_coupling("gS", self_conjugate=True)
    g_t = theory.define_coupling("gT", self_conjugate=True)
    mu = theory.dummy_index(0)
    m_s = theory.coupling_handle("MS")
    m_t = theory.coupling_handle("MT")

    lagrangian = (
        theory.free_lag(s_field, t_field, phi)
        - g_s() * s_field() * phi() ** 2 / 2
        - g_t() * t_field() * phi() ** 2 / 2
    )

    matched = theory.match(lagrangian, eft_order=6)
    expected = (
        phi(derivatives=[mu]) ** 2 / 2
        + g_s() ** 2 * phi() ** 4 / (8 * m_s() ** 2)
        + g_s() ** 2 * phi() ** 2 * phi(derivatives=[mu]) ** 2 / (2 * m_s() ** 4)
        + g_t() ** 2 * phi() ** 4 / (8 * m_t() ** 2)
        + g_t() ** 2 * phi() ** 2 * phi(derivatives=[mu]) ** 2 / (2 * m_t() ** 4)
    )

    assert_expr_equal(matched, expected)


def test_complex_heavy_scalar_tree_match_solves_field_and_conjugate() -> None:
    theory = Theory("complex_heavy")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=False, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    y = theory.define_coupling("y")
    yb = theory.define_coupling("yb")
    mass = theory.coupling_handle("M")
    mu = theory.dummy_index(0)
    u3 = theory.dummy_index(3)
    lagrangian = (
        theory.free_lag(heavy, phi)
        - y() * s.Bar(heavy()) * phi() ** 2
        - yb() * heavy() * phi() ** 2
    )

    solution = theory.solve_heavy_scalar_eoms(lagrangian, eft_order=6)["S"]
    assert_expr_equal(solution.orders[1], -y() * phi() ** 2 / mass() ** 2)
    assert_expr_equal(solution.conjugate_orders[1], -yb() * phi() ** 2 / mass() ** 2)
    assert_expr_equal(
        solution.orders[3],
        2 * y() * (phi(derivatives=[u3]) ** 2 + phi() * phi(derivatives=[u3, u3])) / mass() ** 4,
    )

    matched = theory.match(lagrangian, eft_order=6)
    expected = (
        phi(derivatives=[mu]) ** 2 / 2
        + y() * yb() * phi() ** 4 / mass() ** 2
        + 4 * y() * yb() * phi() ** 2 * phi(derivatives=[mu]) ** 2 / mass() ** 4
    )
    assert_expr_equal(matched, expected)
