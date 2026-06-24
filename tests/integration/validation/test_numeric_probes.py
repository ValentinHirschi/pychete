from __future__ import annotations

import pytest
from symbolica import S

from pychete.validation import evaluator_probe_equal


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
