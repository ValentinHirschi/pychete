from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Iterable

from symbolica import Expression, Replacement

from .eft import series_eft
from .expr import (
    bar_field_pattern,
    field_pattern,
    is_zero,
    list_items,
)
from .functional import apply_cd, derive_eom
from .symbols import canonical_string, display_string, latex_string, s
from .theory import FieldDefinition, FieldVariation, Theory


@dataclass(frozen=True)
class MatchingExpressionComparison:
    """Canonical comparison result for one named matching expression."""

    name: str
    equal: bool
    candidate: Expression | None = None
    reference: Expression | None = None

    def _repr_latex_(self) -> str:
        status = r"\checkmark" if self.equal else r"\times"
        return rf"$\mathrm{{{escape(self.name)}}}: {status}$"

    def _repr_html_(self) -> str:
        status = "equal" if self.equal else "different"
        return f"<code>{escape(self.name)}: {status}</code>"


@dataclass(frozen=True)
class MatchingResultComparison:
    """Canonical comparison of two structured matching results."""

    candidate: MatchingResult
    reference: MatchingResult
    expressions: tuple[MatchingExpressionComparison, ...]

    @property
    def equal(self) -> bool:
        """Whether every compared expression is present and canonically equal."""

        return all(item.equal for item in self.expressions)

    @property
    def failed_names(self) -> tuple[str, ...]:
        """Names of expressions that are missing or canonically different."""

        return tuple(item.name for item in self.expressions if not item.equal)

    def assert_equal(self) -> None:
        """Raise ``AssertionError`` if any expression differs."""

        if not self.equal:
            raise AssertionError(f"Matching results differ for: {', '.join(self.failed_names)}")

    def _repr_latex_(self) -> str:
        status = r"\checkmark" if self.equal else r"\times"
        return rf"$\mathrm{{MatchingResultComparison}}\left({status},\ {len(self.expressions)}\right)$"

    def _repr_html_(self) -> str:
        status = "equal" if self.equal else f"different: {', '.join(escape(name) for name in self.failed_names)}"
        return f"<code>MatchingResultComparison({status})</code>"


@dataclass(frozen=True)
class MatchingResult:
    """Structured output of a pychete matching calculation.

    The result stores the major expression stages used by one-loop matching so
    tests and notebooks can inspect individual supertraces, off-shell and
    on-shell EFT Lagrangians, and final matching conditions without relying on
    Matchete's Mathematica data structures.
    """

    theory: Theory
    uv_lagrangian: Expression
    off_shell_eft_lagrangian: Expression
    on_shell_eft_lagrangian: Expression
    matching_conditions: dict[str, Expression] = field(default_factory=dict)
    fluctuation_operators: dict[str, Expression] = field(default_factory=dict)
    supertraces: dict[str, Expression] = field(default_factory=dict)
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    def expression(self, name: str) -> Expression:
        """Return a named expression stage from the matching result."""

        if name == "uv_lagrangian":
            return self.uv_lagrangian
        if name == "off_shell_eft_lagrangian":
            return self.off_shell_eft_lagrangian
        if name == "on_shell_eft_lagrangian":
            return self.on_shell_eft_lagrangian
        for collection in (self.matching_conditions, self.fluctuation_operators, self.supertraces):
            if name in collection:
                return collection[name]
        raise KeyError(f"Matching result has no expression {name!r}")

    def expression_names(self) -> tuple[str, ...]:
        """Return all named expression stages available on the result."""

        return (
            "uv_lagrangian",
            "off_shell_eft_lagrangian",
            "on_shell_eft_lagrangian",
            *self.matching_conditions,
            *self.fluctuation_operators,
            *self.supertraces,
        )

    def validate(self) -> None:
        """Validate every stored expression against the owning theory."""

        for name in self.expression_names():
            self.theory._validate_registered_expression(self.expression(name))

    def compare_to(self, reference: MatchingResult, *, names: Iterable[str] | None = None) -> MatchingResultComparison:
        """Compare this result to a reference result by canonical expressions."""

        if self.theory.name != reference.theory.name:
            raise ValueError(f"Cannot compare matching results from {self.theory.name!r} and {reference.theory.name!r}")
        if names is None:
            comparison_names = tuple(dict.fromkeys((*self.expression_names(), *reference.expression_names())))
        else:
            comparison_names = tuple(names)
        comparisons: list[MatchingExpressionComparison] = []
        for name in comparison_names:
            candidate_expr = _optional_expression(self, name)
            reference_expr = _optional_expression(reference, name)
            equal = (
                candidate_expr is not None
                and reference_expr is not None
                and _canonical_expr(candidate_expr) == _canonical_expr(reference_expr)
            )
            comparisons.append(
                MatchingExpressionComparison(
                    name=name,
                    equal=equal,
                    candidate=candidate_expr,
                    reference=reference_expr,
                )
            )
        return MatchingResultComparison(candidate=self, reference=reference, expressions=tuple(comparisons))

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{MatchingResult}}\left({self.theory.name},\ {len(self.supertraces)}\ \mathrm{{supertraces}}\right)$"

    def _repr_html_(self) -> str:
        return (
            f"<code>MatchingResult(theory={escape(self.theory.name)} "
            f"supertraces={len(self.supertraces)} "
            f"matching_conditions={len(self.matching_conditions)})</code>"
        )


class OneLoopMatchingNotImplementedError(NotImplementedError):
    """Raised while the one-loop matching engine is still under construction."""


def _optional_expression(result: MatchingResult, name: str) -> Expression | None:
    try:
        return result.expression(name)
    except KeyError:
        return None


def _canonical_expr(expr: Expression) -> str:
    return canonical_string(expr.expand())


@dataclass(frozen=True)
class HeavyScalarSolution:
    """Order-by-order solution for a heavy scalar equation of motion."""

    field: FieldDefinition
    orders: dict[int, Expression]
    conjugate_orders: dict[int, Expression] | None = None

    @property
    def inclusive(self) -> Expression:
        """Sum all stored EFT orders for the heavy field."""

        out = Expression.num(0)
        for _, expr in sorted(self.orders.items()):
            out = out + expr
        return out.expand()

    @property
    def inclusive_conjugate(self) -> Expression:
        """Sum all stored EFT orders for the conjugate heavy field."""

        if self.conjugate_orders is None:
            return self.inclusive
        out = Expression.num(0)
        for _, expr in sorted(self.conjugate_orders.items()):
            out = out + expr
        return out.expand()

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{{self.field.name}}}: {latex_string(self.inclusive)}$"

    def _repr_html_(self) -> str:
        return f"<code>{escape(self.field.name)}: {escape(display_string(self.inclusive))}</code>"


def _zero_field_label(expr: Expression, label: Expression, *, conjugate: bool = False) -> Expression:
    pattern = bar_field_pattern(label) if conjugate else field_pattern(label)
    return expr.replace(pattern, Expression.num(0)).expand()


def _mass_squared(field: FieldDefinition) -> Expression:
    mass = field.mass_expr()
    if mass is None:
        raise ValueError(f"Heavy field {field.name} has no mass coupling")
    return mass**2


def _box(theory: Theory, expr: Expression, order: int) -> Expression:
    mu = theory.dummy_index(order)
    return apply_cd((mu, mu), expr)


def _solve_orders_from_source(theory: Theory, source: Expression, mass2: Expression, *, eft_order: int) -> dict[int, Expression]:
    orders: dict[int, Expression] = {}
    max_order = eft_order - 1
    previous_nonzero: Expression | None = None
    for order in range(1, max_order + 1):
        if order == 1:
            value = (source / mass2).expand()
        elif order % 2 == 0:
            value = Expression.num(0)
        else:
            if previous_nonzero is None:
                value = Expression.num(0)
            else:
                value = (-_box(theory, previous_nonzero, order) / mass2).expand()

        orders[order] = value
        if order % 2 == 1 and not is_zero(value):
            previous_nonzero = value
    return orders


def solve_heavy_scalar_eoms(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> dict[str, HeavyScalarSolution]:
    theory._validate_registered_expression(lagrangian)
    lagrangian = lagrangian.expand()
    solutions: dict[str, HeavyScalarSolution] = {}

    for field in theory.fields.values():
        if not field.heavy or not bool(field.type_expr == s.Scalar):
            continue

        mass2 = _mass_squared(field)

        if field.is_self_conjugate:
            eom = derive_eom(theory, lagrangian, field, eft_order=eft_order)
            source = _zero_field_label(eom, field.label)
            solution = HeavyScalarSolution(
                field=field,
                orders=_solve_orders_from_source(theory, source, mass2, eft_order=eft_order),
            )
        else:
            eom = derive_eom(theory, lagrangian, field, eft_order=eft_order, variation=FieldVariation.BAR)
            source = _zero_field_label(eom, field.label)
            conjugate_eom = derive_eom(theory, lagrangian, field, eft_order=eft_order, variation=FieldVariation.FIELD)
            conjugate_source = _zero_field_label(conjugate_eom, field.label, conjugate=True)
            solution = HeavyScalarSolution(
                field=field,
                orders=_solve_orders_from_source(theory, source, mass2, eft_order=eft_order),
                conjugate_orders=_solve_orders_from_source(theory, conjugate_source, mass2, eft_order=eft_order),
            )
        solutions[field.name] = solution

    return solutions


def _replace_heavy_fields(expr: Expression, solutions: dict[str, HeavyScalarSolution]) -> Expression:
    replacements: list[Replacement] = []
    for solution in solutions.values():
        label = solution.field.label

        def bar_solution(match: dict[Expression, Expression], solution: HeavyScalarSolution = solution) -> Expression:
            return apply_cd(list_items(match[s.FieldDerivativesWildcard]), solution.inclusive_conjugate)

        def field_solution(match: dict[Expression, Expression], solution: HeavyScalarSolution = solution) -> Expression:
            return apply_cd(list_items(match[s.FieldDerivativesWildcard]), solution.inclusive)

        replacements.append(Replacement(bar_field_pattern(label), bar_solution))
        replacements.append(Replacement(field_pattern(label), field_solution))
    return expr.replace_multiple(replacements).expand() if replacements else expr.expand()


def match_tree(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> Expression:
    solutions = solve_heavy_scalar_eoms(theory, lagrangian, eft_order=eft_order)
    replaced = _replace_heavy_fields(lagrangian, solutions)
    truncated = series_eft(replaced.expand(), theory, eft_order=eft_order, heavy_field_dimension=False)
    return truncated.expand()


def match_one_loop(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> MatchingResult:
    """Run pychete's one-loop matching pipeline.

    The public API entry point exists so callers cannot accidentally receive a
    tree-level result for a one-loop request. The engine body is intentionally
    not stubbed with fake physics: it must be filled by the Symbolica/idenso/
    spenso/vakint pipeline and validated against the committed Matchete
    fixtures.
    """

    theory._validate_registered_expression(lagrangian)
    raise OneLoopMatchingNotImplementedError(
        "One-loop matching is not implemented yet. The committed default "
        "Matchete matching fixtures are available as acceptance targets under "
        "assets/validation/pychete/*.matching_fixture.json."
    )
