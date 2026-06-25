from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import MatchingResult, Theory, evaluator_probe_equal
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


def test_fixture_gap_report_records_evaluator_probe_equal_supertraces() -> None:
    x = S("fixture_gap_probe_x")
    theory = Theory("fixture_gap_probe")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"probe": x.sin() ** 2 + x.cos() ** 2},
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"probe": Expression.num(1)},
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        probe_parameters=[x],
        probe_samples=[[0.0], [0.7], [1.3]],
    )
    report_obj = report.to_json_obj()

    assert report.common_supertrace_names == ("probe",)
    assert report.canonical_equal_common_supertrace_names == ()
    assert report.canonical_different_common_supertrace_names == ("probe",)
    assert report.numeric_probe_equal_common_supertrace_names == ("probe",)
    assert report.numeric_probe_different_common_supertrace_names == ()
    assert report.numeric_probe_equal_common_supertrace_count == 1
    assert report.numeric_probe_different_common_supertrace_count == 0
    assert report_obj["numeric_probe_equal_common_supertrace_names"] == ["probe"]
    assert report_obj["numeric_probe_equal_common_supertrace_count"] == 1
