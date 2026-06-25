from __future__ import annotations

import pytest
from symbolica import Expression, Replacement, S

from pychete import (
    MatchingResult,
    NumericProbePlan,
    Theory,
    build_numeric_probe_plan,
    canonical_string,
    deterministic_probe_samples,
    evaluator_probe_equal,
    registered_wilson_matching_condition_targets,
    s,
)
from pychete.backends import vacuum_integrals
from pychete.validation_fixtures import _gap_report
from tests.conftest import assert_expr_equal


def test_evaluator_probe_equal_accepts_symbolically_equivalent_expressions() -> None:
    x, y = S("x", "y")

    result = evaluator_probe_equal(
        (x + y) ** 2,
        x**2 + 2 * x * y + y**2,
        [x, y],
        [
            [1.0, 2.0],
            [-3.5, 0.25],
        ],
    )

    assert result.equal is True
    assert result.max_abs_difference == 0.0


def test_evaluator_probe_equal_rejects_numerically_distinct_expressions() -> None:
    x = S("x")

    result = evaluator_probe_equal(
        x**2,
        x**2 + 1,
        [x],
        [[0.0], [2.0]],
    )

    assert result.equal is False
    assert result.max_abs_difference == 1.0


def test_evaluator_probe_equal_validates_samples_match_parameters() -> None:
    x, y = S("x", "y")

    with pytest.raises(ValueError, match="same length as parameters"):
        evaluator_probe_equal(x + y, y + x, [x, y], [[1.0]])


def test_build_numeric_probe_plan_discovers_symbols_with_symbolica() -> None:
    x, y, z = S("probe_plan_x", "probe_plan_y", "probe_plan_z")
    f = S("probe_plan_f")

    samples = deterministic_probe_samples([x, z], sample_count=2)
    plan = build_numeric_probe_plan(
        [x + y, (x + 1) / (z + 2), z.sin()],
        exclude_symbols=[y],
        sample_count=2,
    )

    assert isinstance(plan, NumericProbePlan)
    assert tuple(canonical_string(parameter) for parameter in plan.parameters) == (
        canonical_string(x),
        canonical_string(z),
    )
    assert plan.samples == samples
    assert plan.parameter_count == 2
    assert plan.sample_count == 2

    function_plan = build_numeric_probe_plan(
        [f(x) + y],
        exclude_symbols=[y],
        parameter_mode="indeterminates",
        sample_count=1,
    )
    assert tuple(canonical_string(parameter) for parameter in function_plan.parameters) == (
        canonical_string(f(x)),
    )


def test_matching_result_comparison_can_use_evaluator_probe_fallback() -> None:
    x = S("comparison_probe_x")
    theory = Theory("comparison_probe")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=x.sin() ** 2 + x.cos() ** 2,
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(1),
    )

    comparison = candidate.compare_to(
        reference,
        names=("on_shell_eft_lagrangian",),
        probe_parameters=[x],
        probe_samples=[[0.0], [0.7]],
    )

    assert comparison.equal is True
    expression = comparison.expressions[0]
    assert expression.canonical_equal is False
    assert expression.numeric_probe is not None
    assert expression.numeric_probe.equal is True


def test_matching_result_comparison_can_transform_expressions_before_comparing() -> None:
    mass = S("comparison_loop_mass")
    theory = Theory("comparison_loop_transform")
    loop_function = vacuum_integrals.loop_function((mass,), (1, 0))
    evaluated = vacuum_integrals.evaluate_loop_functions(loop_function)
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=evaluated,
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=loop_function,
    )

    raw_comparison = candidate.compare_to(reference, names=("on_shell_eft_lagrangian",))
    transformed_comparison = candidate.compare_to(
        reference,
        names=("on_shell_eft_lagrangian",),
        expression_transform=vacuum_integrals.evaluate_loop_functions,
    )

    assert raw_comparison.equal is False
    assert transformed_comparison.equal is True
    assert transformed_comparison.expressions[0].canonical_equal is True


def test_matching_result_comparison_can_restrict_evaluator_probe_names() -> None:
    x = S("comparison_probe_selected_x")
    theory = Theory("comparison_probe_selected")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "selected": x.sin() ** 2 + x.cos() ** 2,
            "unselected": x.sin() ** 2 + x.cos() ** 2 + x,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "selected": Expression.num(1),
            "unselected": x + 1,
        },
    )

    comparison = candidate.compare_to(
        reference,
        names=("selected", "unselected"),
        probe_parameters=[x],
        probe_samples=[[0.0], [0.7]],
        probe_names=("selected",),
    )

    selected, unselected = comparison.expressions
    assert selected.equal is True
    assert selected.numeric_probe is not None
    assert selected.numeric_probe.equal is True
    assert selected.canonical_equal is False
    assert unselected.equal is False
    assert unselected.canonical_equal is False
    assert unselected.numeric_probe is None


def test_gap_report_can_compare_after_loop_function_evaluation() -> None:
    mass = S("gap_report_loop_mass")
    theory = Theory("gap_report_loop_transform")
    loop_function = vacuum_integrals.loop_function((mass,), (1, 0))
    evaluated = vacuum_integrals.evaluate_loop_functions(loop_function)
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"loop": evaluated},
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"loop": loop_function},
    )

    raw_report = _gap_report("candidate", "reference", candidate, reference)
    transformed_report = _gap_report(
        "candidate",
        "reference",
        candidate,
        reference,
        comparison_expression_transform=vacuum_integrals.evaluate_loop_functions,
    )

    assert raw_report.canonical_equal_common_supertrace_names == ()
    assert raw_report.canonical_different_common_supertrace_names == ("loop",)
    assert transformed_report.canonical_equal_common_supertrace_names == ("loop",)
    assert transformed_report.canonical_different_common_supertrace_names == ()


def test_matching_result_comparison_requires_complete_probe_inputs() -> None:
    theory = Theory("comparison_probe_input")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
    )

    with pytest.raises(ValueError, match="provided together"):
        result.compare_to(result, probe_parameters=[])

    with pytest.raises(ValueError, match="probe_names requires"):
        result.compare_to(result, probe_names=("on_shell_eft_lagrangian",))


def test_matching_result_projects_conditions_with_symbolica_coefficients() -> None:
    coefficient_a, coefficient_b, operator_a, x = S(
        "condition_projection_a",
        "condition_projection_b",
        "condition_projection_operator_a",
        "condition_projection_x",
    )
    theory = Theory("condition_projection")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=(
            3 * coefficient_a * operator_a
            + (x + 1) * coefficient_b
            + 7 * coefficient_a * operator_a * coefficient_b
        ),
        matching_conditions={"existing": x},
    )

    projected = result.project_matching_conditions(
        {
            "a_operator": coefficient_a * operator_a,
            "b": coefficient_b,
            "missing": S("condition_projection_missing"),
        },
        drop_zero=True,
    )
    updated = result.with_projected_matching_conditions(
        {
            "a_operator": coefficient_a * operator_a,
            "b": coefficient_b,
        }
    )
    replacement = result.with_projected_matching_conditions(
        [coefficient_a * operator_a],
        merge=False,
    )

    assert set(projected) == {"a_operator", "b"}
    assert canonical_string((projected["a_operator"] - (3 + 7 * coefficient_b)).expand()) == "0"
    assert canonical_string((projected["b"] - (x + 1 + 7 * coefficient_a * operator_a)).expand()) == "0"
    assert set(updated.matching_conditions) == {"existing", "a_operator", "b"}
    assert canonical_string(updated.matching_conditions["existing"]) == canonical_string(x)
    assert updated.metadata["matching_conditions_projected"] is True
    assert updated.metadata["matching_condition_projection_source"] == "on_shell_eft_lagrangian"
    assert updated.metadata["matching_condition_projection_count"] == 2
    assert updated.metadata["matching_condition_projection_expand_source"] is True
    assert tuple(replacement.matching_conditions) == (canonical_string(coefficient_a * operator_a),)


def test_matching_result_can_project_from_unexpanded_source_expression() -> None:
    x = S("condition_projection_unexpanded_x")
    theory = Theory("condition_projection_unexpanded")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    operator = phi() ** 2
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=(x + 1) * operator,
    )

    projected = result.with_projected_matching_conditions(
        {"phi2": operator},
        expand_source=False,
    )

    assert projected.metadata["matching_condition_projection_expand_source"] is False
    assert_expr_equal(projected.matching_conditions["phi2"], x + 1)


def test_matching_result_projects_alpha_equivalent_index_contractions() -> None:
    theory = Theory("condition_projection_indices")
    theory.define_gauge_group("SU2L", s.SU(2), coupling="gL", field="W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=(fund,))
    named_index = theory.index("i", fund)
    dummy_index = theory.dummy_index(1, fund)
    target = higgs(named_index) * s.Bar(higgs(named_index))
    source_operator = higgs(dummy_index) * s.Bar(higgs(dummy_index))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=5 * source_operator,
    )

    projected = result.with_projected_matching_conditions({"HbarH": target}, expand_source=False)
    uncanonized = result.project_matching_conditions(
        {"HbarH": target},
        expand_source=False,
        canonize_indices=False,
    )

    assert projected.metadata["matching_condition_projection_canonize_indices"] is True
    assert_expr_equal(projected.matching_conditions["HbarH"], Expression.num(5))
    assert_expr_equal(uncanonized["HbarH"], Expression.num(0))


def test_matching_result_truncates_projected_coefficients_target_locally() -> None:
    x = S("condition_projection_local_eft_x")
    theory = Theory("condition_projection_local_eft")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    operator = phi() ** 2
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=(x + phi() ** 4) * operator,
    )

    projected = result.with_projected_matching_conditions(
        {"phi2": operator},
        expand_source=False,
        eft_order=4,
    )

    assert projected.metadata["matching_condition_projection_eft_order"] == 4
    assert projected.metadata["matching_condition_projection_heavy_field_dimension"] is False
    assert_expr_equal(projected.matching_conditions["phi2"], x)


def test_matching_result_projects_wilson_conditions_from_operator_metadata() -> None:
    x = S("condition_projection_wilson_x")
    theory = Theory("condition_projection_wilson_operator")
    higgs = theory.define_field("H", s.Scalar, mass=0)
    operator = (s.Bar(higgs()) * higgs()) ** 3
    wilson = theory.define_wilson_coefficient("cH", eft_order=6, basis="SMEFT", operator=operator)
    theory.define_wilson_coefficient("cMissing", basis="SMEFT")
    theory.define_wilson_coefficient("cLEFT", basis="LEFT")
    target = s.Coupling(wilson.label, s.List(), Expression.num(6))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=11 * operator + 3 * target * operator + x * higgs(),
    )

    projected = result.project_matching_conditions([target])
    selector_projected = result.project_matching_conditions("registered_wilsons")
    smeft_targets = registered_wilson_matching_condition_targets(theory, basis="SMEFT")
    all_smeft_targets = registered_wilson_matching_condition_targets(
        theory,
        basis="SMEFT",
        include_without_operator=True,
    )

    assert tuple(projected) == (canonical_string(target),)
    assert canonical_string((projected[canonical_string(target)] - (11 + 3 * target)).expand()) == "0"
    assert tuple(selector_projected) == (canonical_string(target),)
    assert canonical_string((selector_projected[canonical_string(target)] - (11 + 3 * target)).expand()) == "0"
    assert set(smeft_targets) == {canonical_string(target)}
    assert set(all_smeft_targets) == {
        canonical_string(target),
        canonical_string(s.Coupling(theory.external_handle("cMissing").label, s.List(), Expression.num(0))),
    }

    with pytest.raises(ValueError, match="registered_wilsons"):
        result.project_matching_conditions("all_wilsons")


def test_matching_result_projection_normalizes_cd_targets_to_derivative_slots() -> None:
    coefficient = S("condition_projection_cd_coefficient")
    theory = Theory("condition_projection_cd_normalization")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    mu = theory.dummy_index(0)
    source = coefficient * phi(derivatives=[mu]) * s.Bar(phi(derivatives=[mu]))
    target = s.CD(mu, phi()) * s.CD(mu, s.Bar(phi()))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=source,
    )

    raw = result.project_matching_conditions({"kinetic": target}, normalize_derivative_operators=False)
    normalized = result.with_projected_matching_conditions({"kinetic": target})

    assert_expr_equal(raw["kinetic"], Expression.num(0))
    assert_expr_equal(normalized.matching_conditions["kinetic"], coefficient)
    assert normalized.metadata["matching_condition_projection_normalize_derivative_operators"] is True


def test_matching_result_projection_normalizes_additive_cd_targets() -> None:
    coefficient = S("condition_projection_cd_box_coefficient")
    theory = Theory("condition_projection_cd_box")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    mu = theory.dummy_index(0)
    source_operator = (
        phi(derivatives=[mu, mu]) * s.Bar(phi())
        + 2 * phi(derivatives=[mu]) * s.Bar(phi(derivatives=[mu]))
        + phi() * s.Bar(phi(derivatives=[mu, mu]))
    )
    target = s.CD(s.List(mu, mu), phi() * s.Bar(phi()))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    projected = result.project_matching_conditions({"box": target}, expand_source=False)

    assert_expr_equal(projected["box"], coefficient)


def test_matching_result_applies_on_shell_replacements_with_symbolica_rules() -> None:
    theory = Theory("result_on_shell_reduction")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    coupling = theory.define_coupling("c", self_conjugate=True)
    off_shell = coupling() * phi() ** 2 + coupling()
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=off_shell,
        on_shell_eft_lagrangian=off_shell,
    )

    reduced = result.with_on_shell_reduction((Replacement(phi() ** 2, Expression.num(0)),))

    assert reduced.metadata["on_shell_reduced"] is True
    assert reduced.metadata["on_shell_reduction_source"] == "on_shell_eft_lagrangian"
    assert reduced.metadata["on_shell_reduction_replacement_count"] == 1
    assert_expr_equal(reduced.off_shell_eft_lagrangian, off_shell)
    assert_expr_equal(reduced.expression("on_shell_eft_lagrangian_before_reduction"), off_shell)
    assert_expr_equal(reduced.expression("on_shell_eft_lagrangian_after_reduction"), coupling())
    assert_expr_equal(reduced.on_shell_eft_lagrangian, coupling())


def test_matching_result_applies_theory_eom_replacement_before_projection() -> None:
    theory = Theory("result_eom_on_shell_reduction")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    source = theory.define_coupling("J", self_conjugate=True)
    coefficient = theory.define_coupling("c", self_conjugate=True)
    mu = theory.dummy_index(0)
    derivative_target = phi(derivatives=[mu, mu])
    eom_lagrangian = theory.free_lag(phi) + source() * phi()
    off_shell = coefficient() * phi() * derivative_target
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=eom_lagrangian,
        off_shell_eft_lagrangian=off_shell,
        on_shell_eft_lagrangian=off_shell,
    )

    reduced = result.with_on_shell_reduction(
        (theory.eom_replacement_rule(eom_lagrangian, phi, solve_for=derivative_target),)
    ).with_projected_matching_conditions({"c_phi": coefficient() * phi()})

    assert reduced.metadata["on_shell_reduced"] is True
    assert reduced.metadata["matching_conditions_projected"] is True
    assert_expr_equal(reduced.on_shell_eft_lagrangian, coefficient() * phi() * source())
    assert_expr_equal(reduced.matching_conditions["c_phi"], source())


def test_matching_result_truncates_eft_lagrangians_with_symbolica_series() -> None:
    theory = Theory("result_eft_truncation")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    low = phi() ** 4
    high = phi() ** 8
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=low + high,
        on_shell_eft_lagrangian=low + high,
        matching_conditions={"raw": low + high},
        metadata={"stage": "raw_stage"},
    )

    truncated = result.with_eft_truncation(6)

    assert truncated.metadata["stage"] == "raw_stage"
    assert truncated.metadata["eft_result_truncated"] is True
    assert truncated.metadata["eft_result_truncation_order"] == 6
    assert truncated.metadata["eft_result_untruncated_stage"] == "raw_stage"
    assert_expr_equal(truncated.off_shell_eft_lagrangian, low)
    assert_expr_equal(truncated.on_shell_eft_lagrangian, low)
    assert_expr_equal(truncated.matching_conditions["raw"], low)
    assert_expr_equal(truncated.expression("off_shell_eft_lagrangian_before_eft_truncation"), low + high)
    assert_expr_equal(truncated.expression("on_shell_eft_lagrangian_after_eft_truncation"), low)


def test_fixture_gap_report_records_evaluator_probe_equal_supertraces() -> None:
    x = S("fixture_gap_probe_x")
    theory = Theory("fixture_gap_probe")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "probe": x.sin() ** 2 + x.cos() ** 2,
            "unprobed": x.sin() ** 2 + x.cos() ** 2 + x,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "probe": Expression.num(1),
            "unprobed": x + 1,
        },
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        probe_parameters=[x],
        probe_samples=[[0.0], [0.7], [1.3]],
        probe_supertrace_names=("probe",),
    )
    report_obj = report.to_json_obj()

    assert report.common_supertrace_names == ("probe", "unprobed")
    assert report.canonical_equal_common_supertrace_names == ()
    assert report.canonical_different_common_supertrace_names == ("probe", "unprobed")
    assert report.numeric_probe_equal_common_supertrace_names == ("probe",)
    assert report.numeric_probe_different_common_supertrace_names == ()
    assert report.numeric_probe_equal_common_supertrace_count == 1
    assert report.numeric_probe_different_common_supertrace_count == 0
    assert report.accepted_common_supertrace_names == ("probe",)
    assert report.different_after_probe_common_supertrace_names == ("unprobed",)
    assert report.accepted_common_supertrace_count == 1
    assert report.different_after_probe_common_supertrace_count == 1
    assert report_obj["numeric_probe_equal_common_supertrace_names"] == ["probe"]
    assert report_obj["numeric_probe_equal_common_supertrace_count"] == 1
    assert report_obj["accepted_common_supertrace_names"] == ["probe"]
    assert report_obj["different_after_probe_common_supertrace_count"] == 1


def test_fixture_gap_report_can_probe_canonical_different_supertraces_by_preset() -> None:
    x = S("fixture_gap_probe_preset_x")
    theory = Theory("fixture_gap_probe_preset")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "already_equal": x,
            "probe": x.sin() ** 2 + x.cos() ** 2,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "already_equal": x,
            "probe": Expression.num(1),
        },
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        auto_probe_samples=True,
        probe_supertrace_names="canonical_different",
    )

    assert report.canonical_equal_common_supertrace_names == ("already_equal",)
    assert report.canonical_different_common_supertrace_names == ("probe",)
    assert report.numeric_probe_equal_common_supertrace_names == ("probe",)
    assert report.accepted_common_supertrace_names == ("already_equal", "probe")
    assert report.different_after_probe_common_supertrace_names == ()


def test_fixture_gap_report_records_supertrace_word_orders() -> None:
    theory = Theory("fixture_gap_supertrace_order")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "hScalar": Expression.num(0),
            "hScalar[unnormalized]": Expression.num(1),
            "hScalar-lScalar": Expression.num(0),
            "aggregate_stage": Expression.num(0),
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "hScalar": Expression.num(0),
            "hScalar-lScalar-lVector": Expression.num(0),
        },
    )

    report = _gap_report("candidate_fixture", "reference_fixture", candidate, reference)
    report_obj = report.to_json_obj()
    coverage_by_order = {coverage.order: coverage for coverage in report.supertrace_order_coverage}
    json_coverage_by_order = {entry["order"]: entry for entry in report_obj["supertrace_order_coverage"]}

    assert report.candidate_max_supertrace_order == 2
    assert report.reference_max_supertrace_order == 3
    assert report.max_supertrace_order_gap == 1
    assert report.candidate_supertrace_count == 3
    assert "hScalar[unnormalized]" not in report.candidate_supertrace_names
    assert tuple(coverage_by_order) == (1, 2, 3)
    assert coverage_by_order[1].candidate_count == 1
    assert coverage_by_order[1].reference_count == 1
    assert coverage_by_order[1].accepted_common_count == 1
    assert coverage_by_order[2].candidate_count == 1
    assert coverage_by_order[2].reference_count == 0
    assert coverage_by_order[2].candidate_only_names == ("hScalar-lScalar",)
    assert coverage_by_order[3].candidate_count == 0
    assert coverage_by_order[3].reference_count == 1
    assert coverage_by_order[3].missing_reference_count == 1
    assert coverage_by_order[3].reference_only_names == ("hScalar-lScalar-lVector",)
    assert json_coverage_by_order[3]["missing_reference_count"] == 1
    assert json_coverage_by_order[3]["reference_only_names"] == ["hScalar-lScalar-lVector"]
    assert report_obj["candidate_max_supertrace_order"] == 2
    assert report_obj["reference_max_supertrace_order"] == 3
    assert report_obj["max_supertrace_order_gap"] == 1


def test_fixture_gap_report_compares_common_matching_conditions() -> None:
    c_equal, c_diff, x = S("condition_gap_equal", "condition_gap_diff", "condition_gap_x")
    theory = Theory("condition_gap")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            canonical_string(c_equal): x + 1,
            canonical_string(c_diff): x,
            "candidate_only": x,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            canonical_string(c_equal): x + 1,
            canonical_string(c_diff): x + 2,
            "reference_only": x,
        },
    )

    report = _gap_report("candidate_fixture", "reference_fixture", candidate, reference)
    report_obj = report.to_json_obj()

    assert report.common_matching_condition_names == (canonical_string(c_diff), canonical_string(c_equal))
    assert report.canonical_equal_common_matching_condition_names == (canonical_string(c_equal),)
    assert report.canonical_different_common_matching_condition_names == (canonical_string(c_diff),)
    assert report.canonical_equal_common_matching_condition_count == 1
    assert report.canonical_different_common_matching_condition_count == 1
    assert report.accepted_common_matching_condition_names == (canonical_string(c_equal),)
    assert report.different_after_probe_common_matching_condition_names == (canonical_string(c_diff),)
    assert report.accepted_common_matching_condition_count == 1
    assert report.different_after_probe_common_matching_condition_count == 1
    assert report.candidate_only_matching_condition_names == ("candidate_only",)
    assert report.reference_only_matching_condition_names == ("reference_only",)
    assert report_obj["canonical_equal_common_matching_condition_names"] == [canonical_string(c_equal)]
    assert report_obj["canonical_different_common_matching_condition_count"] == 1
    assert report_obj["accepted_common_matching_condition_names"] == [canonical_string(c_equal)]
    assert report_obj["different_after_probe_common_matching_condition_count"] == 1


def test_fixture_gap_report_records_wilson_matching_condition_frontier() -> None:
    x = S("condition_gap_wilson_x")
    theory = Theory("condition_gap_wilson")
    wilson = theory.define_wilson_coefficient("cH", basis="SMEFT")
    coupling = theory.define_coupling("g")
    wilson_name = canonical_string(s.Coupling(wilson.label, s.List(), Expression.num(0)))
    coupling_name = canonical_string(coupling())
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            wilson_name: x,
            coupling_name: x,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            wilson_name: x,
            coupling_name: x + 1,
        },
    )

    report = _gap_report("candidate_fixture", "reference_fixture", candidate, reference)
    report_obj = report.to_json_obj()

    assert report.reference_wilson_matching_condition_names == (wilson_name,)
    assert report.common_wilson_matching_condition_names == (wilson_name,)
    assert report.accepted_common_wilson_matching_condition_names == (wilson_name,)
    assert report.different_after_probe_common_wilson_matching_condition_names == ()
    assert report.reference_wilson_matching_condition_count == 1
    assert report.common_wilson_matching_condition_count == 1
    assert report.accepted_common_wilson_matching_condition_count == 1
    assert report.different_after_probe_common_wilson_matching_condition_count == 0
    assert report_obj["reference_wilson_matching_condition_names"] == [wilson_name]
    assert report_obj["accepted_common_wilson_matching_condition_count"] == 1


def test_fixture_gap_report_can_probe_wilson_matching_conditions_by_preset() -> None:
    x = S("condition_gap_wilson_probe_x")
    theory = Theory("condition_gap_wilson_probe")
    wilson = theory.define_wilson_coefficient("cH", basis="SMEFT")
    coupling = theory.define_coupling("g")
    wilson_name = canonical_string(s.Coupling(wilson.label, s.List(), Expression.num(0)))
    coupling_name = canonical_string(coupling())
    trig_identity = x.sin() ** 2 + x.cos() ** 2
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            wilson_name: trig_identity,
            coupling_name: trig_identity,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            wilson_name: Expression.num(1),
            coupling_name: Expression.num(1),
        },
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        auto_probe_samples=True,
        probe_matching_condition_names="canonical_different_wilson",
    )

    assert report.common_matching_condition_names == (coupling_name, wilson_name)
    assert report.reference_wilson_matching_condition_names == (wilson_name,)
    assert report.numeric_probe_equal_common_matching_condition_names == (wilson_name,)
    assert report.accepted_common_wilson_matching_condition_names == (wilson_name,)
    assert report.accepted_common_matching_condition_names == (wilson_name,)
    assert report.different_after_probe_common_matching_condition_names == (coupling_name,)


def test_fixture_gap_report_rejects_unknown_probe_name_preset_strings() -> None:
    x = S("fixture_gap_bad_probe_preset_x")
    theory = Theory("fixture_gap_bad_probe_preset")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"literal_name": x},
    )

    with pytest.raises(ValueError, match="tuple/list"):
        _gap_report(
            "candidate_fixture",
            "reference_fixture",
            result,
            result,
            auto_probe_samples=True,
            probe_supertrace_names="literal_name",
        )

    with pytest.raises(ValueError, match="only valid for matching conditions"):
        _gap_report(
            "candidate_fixture",
            "reference_fixture",
            result,
            result,
            auto_probe_samples=True,
            probe_supertrace_names="wilson",
        )


def test_fixture_gap_report_records_evaluator_probe_equal_matching_conditions() -> None:
    x = S("fixture_gap_condition_probe_x")
    theory = Theory("fixture_gap_condition_probe")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            "probe_condition": x.sin() ** 2 + x.cos() ** 2,
            "unprobed_condition": x.sin() ** 2 + x.cos() ** 2 + x,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            "probe_condition": Expression.num(1),
            "unprobed_condition": x + 1,
        },
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        auto_probe_samples=True,
        probe_sample_count=3,
        probe_matching_condition_names=("probe_condition",),
    )
    report_obj = report.to_json_obj()

    assert report.common_matching_condition_names == ("probe_condition", "unprobed_condition")
    assert report.canonical_equal_common_matching_condition_names == ()
    assert report.canonical_different_common_matching_condition_names == ("probe_condition", "unprobed_condition")
    assert report.numeric_probe_equal_common_matching_condition_names == ("probe_condition",)
    assert report.numeric_probe_different_common_matching_condition_names == ()
    assert report.numeric_probe_equal_common_matching_condition_count == 1
    assert report.numeric_probe_different_common_matching_condition_count == 0
    assert report.accepted_common_matching_condition_names == ("probe_condition",)
    assert report.different_after_probe_common_matching_condition_names == ("unprobed_condition",)
    assert report.accepted_common_matching_condition_count == 1
    assert report.different_after_probe_common_matching_condition_count == 1
    assert report_obj["numeric_probe_equal_common_matching_condition_names"] == ["probe_condition"]
    assert report_obj["numeric_probe_equal_common_matching_condition_count"] == 1
    assert report_obj["accepted_common_matching_condition_names"] == ["probe_condition"]
    assert report_obj["different_after_probe_common_matching_condition_count"] == 1


def test_fixture_gap_report_auto_probe_handles_function_application_parameters() -> None:
    f, x = S("fixture_gap_function_probe_f", "fixture_gap_function_probe_x")
    theory = Theory("fixture_gap_function_probe")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            "function_condition": f(x),
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            "function_condition": f(x) + 1,
        },
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        auto_probe_samples=True,
        probe_parameter_mode="indeterminates",
        probe_matching_condition_names=("function_condition",),
    )

    assert report.numeric_probe_equal_common_matching_condition_names == ()
    assert report.numeric_probe_different_common_matching_condition_names == ("function_condition",)
    assert report.different_after_probe_common_matching_condition_names == ("function_condition",)


def test_fixture_gap_report_auto_probe_requires_unambiguous_inputs() -> None:
    x = S("fixture_gap_auto_probe_x")
    theory = Theory("fixture_gap_auto_probe")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={"condition": x},
    )

    with pytest.raises(ValueError, match="cannot be combined"):
        _gap_report(
            "candidate_fixture",
            "reference_fixture",
            result,
            result,
            auto_probe_samples=True,
            probe_parameters=[x],
            probe_samples=[[2.0]],
            probe_matching_condition_names=("condition",),
        )

    with pytest.raises(ValueError, match="requires probe_supertrace_names or probe_matching_condition_names"):
        _gap_report(
            "candidate_fixture",
            "reference_fixture",
            result,
            result,
            auto_probe_samples=True,
        )

    with pytest.raises(ValueError, match="requires probe_parameters/probe_samples"):
        _gap_report(
            "candidate_fixture",
            "reference_fixture",
            result,
            result,
            probe_matching_condition_names="common",
        )
