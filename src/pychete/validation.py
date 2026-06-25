from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Literal, Sequence

from symbolica import Expression

from .symbols import canonical_string, display_string


NumericValue = int | float | complex
ProbeParameterMode = Literal["symbols", "indeterminates"]


@dataclass(frozen=True)
class NumericProbeResult:
    """Result of a Symbolica evaluator-backed numerical equivalence probe."""

    equal: bool
    max_abs_difference: float
    differences: tuple[complex, ...]


@dataclass(frozen=True)
class NumericProbePlan:
    """Deterministic Symbolica evaluator inputs for numerical equivalence probes."""

    parameters: tuple[Expression, ...]
    samples: tuple[tuple[NumericValue, ...], ...]

    @property
    def parameter_count(self) -> int:
        """Number of Symbolica parameters supplied to the evaluator."""

        return len(self.parameters)

    @property
    def sample_count(self) -> int:
        """Number of deterministic sample points in this plan."""

        return len(self.samples)

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{NumericProbePlan}}\left({self.parameter_count},\ {self.sample_count}\right)$"

    def _repr_html_(self) -> str:
        parameters = ", ".join(escape(display_string(parameter)) for parameter in self.parameters)
        return (
            f"<code>NumericProbePlan(parameters=[{parameters}], "
            f"samples={self.sample_count})</code>"
        )


def deterministic_probe_samples(
    parameters: Sequence[Expression],
    *,
    sample_count: int = 3,
) -> tuple[tuple[NumericValue, ...], ...]:
    """Return stable nonzero sample points for Symbolica evaluator probes.

    The points are deterministic and positive, avoiding the most common
    singular sample values such as 0 and 1. They are not a proof of equality;
    they are intended as a reproducible fallback when canonical Symbolica
    equality is too strict for a selected validation expression.
    """

    if sample_count < 1:
        raise ValueError("sample_count must be positive")
    parameter_count = len(parameters)
    return tuple(
        tuple(
            float((sample_index + 2) * (parameter_index + 3) + 1) / float(parameter_index + 2)
            for parameter_index in range(parameter_count)
        )
        for sample_index in range(sample_count)
    )


def build_numeric_probe_plan(
    expressions: Sequence[Expression],
    *,
    exclude_symbols: Sequence[Expression] = (),
    parameter_mode: ProbeParameterMode = "symbols",
    sample_count: int = 3,
) -> NumericProbePlan:
    """Build deterministic evaluator inputs from symbols appearing in expressions.

    The default ``parameter_mode="symbols"`` uses native
    ``Expression.get_all_symbols(False)`` so built-in numerical functions such
    as ``sin(x)`` are evaluated normally through Symbolica's evaluator. Use
    ``parameter_mode="indeterminates"`` for pychete expressions with custom
    symbolic function atoms such as ``Coupling(...)``: this delegates to
    ``Expression.get_all_indeterminates(enter_functions=False)`` so those
    applications become evaluator parameters.
    """

    if parameter_mode not in {"symbols", "indeterminates"}:
        raise ValueError("parameter_mode must be 'symbols' or 'indeterminates'")
    excluded = {canonical_string(symbol) for symbol in exclude_symbols}
    by_name: dict[str, Expression] = {}
    for expr in expressions:
        if parameter_mode == "symbols":
            discovered = expr.get_all_symbols(include_function_symbols=False)
        else:
            discovered = expr.get_all_indeterminates(enter_functions=False)
        for symbol in discovered:
            name = canonical_string(symbol)
            if name in excluded:
                continue
            by_name.setdefault(name, symbol)
    parameters = tuple(symbol for _, symbol in sorted(by_name.items()))
    return NumericProbePlan(
        parameters=parameters,
        samples=deterministic_probe_samples(parameters, sample_count=sample_count),
    )


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
