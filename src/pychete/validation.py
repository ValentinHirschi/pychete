from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from symbolica import Expression


NumericValue = int | float | complex


@dataclass(frozen=True)
class NumericProbeResult:
    """Result of a Symbolica evaluator-backed numerical equivalence probe."""

    equal: bool
    max_abs_difference: float
    differences: tuple[complex, ...]


def evaluator_probe_equal(
    lhs: Expression,
    rhs: Expression,
    parameters: Sequence[Expression],
    samples: Sequence[Sequence[NumericValue]],
    *,
    absolute_tolerance: float = 1e-9,
    relative_tolerance: float = 1e-9,
) -> NumericProbeResult:
    """Compare two expressions at sample points using Symbolica evaluators.

    This function intentionally evaluates through
    ``Expression.evaluator_multiple``. It must not be replaced by Python-side
    substitution, because validation probes for one-loop matching should use
    the same Symbolica evaluator technology that production comparisons rely on.
    """

    if not samples:
        raise ValueError("at least one numeric sample is required")
    if any(len(sample) != len(parameters) for sample in samples):
        raise ValueError("every sample must have the same length as parameters")

    evaluator = Expression.evaluator_multiple([lhs, rhs], parameters)
    values = _rows(evaluator.evaluate(samples))
    differences: list[complex] = []
    max_abs_difference = 0.0
    equal = True
    for row in values:
        if len(row) != 2:
            raise ValueError("Symbolica evaluator returned an unexpected row shape")
        lhs_value, rhs_value = row
        difference = lhs_value - rhs_value
        differences.append(difference)
        scale = max(1.0, abs(lhs_value), abs(rhs_value))
        tolerance = absolute_tolerance + relative_tolerance * scale
        abs_difference = abs(difference)
        max_abs_difference = max(max_abs_difference, abs_difference)
        if abs_difference > tolerance:
            equal = False

    return NumericProbeResult(
        equal=equal,
        max_abs_difference=max_abs_difference,
        differences=tuple(differences),
    )


def _rows(values: Any) -> tuple[tuple[complex, ...], ...]:
    if hasattr(values, "tolist"):
        values = values.tolist()
    if not isinstance(values, list):
        raise ValueError("Symbolica evaluator did not return a row list")
    rows: list[tuple[complex, ...]] = []
    for row in values:
        if not isinstance(row, list):
            raise ValueError("Symbolica evaluator did not return a two-dimensional result")
        rows.append(tuple(complex(item) for item in row))
    return tuple(rows)
