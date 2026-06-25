from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import MatchingResult, Theory, canonical_string, evaluator_probe_equal
from pychete.validation_fixtures import _gap_report


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
    assert tuple(replacement.matching_conditions) == (canonical_string(coefficient_a * operator_a),)


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
    assert report_obj["numeric_probe_equal_common_supertrace_names"] == ["probe"]
    assert report_obj["numeric_probe_equal_common_supertrace_count"] == 1


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
    assert report.candidate_only_matching_condition_names == ("candidate_only",)
    assert report.reference_only_matching_condition_names == ("reference_only",)
    assert report_obj["canonical_equal_common_matching_condition_names"] == [canonical_string(c_equal)]
    assert report_obj["canonical_different_common_matching_condition_count"] == 1
