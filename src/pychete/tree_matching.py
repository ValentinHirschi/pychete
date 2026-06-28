from __future__ import annotations

from dataclasses import dataclass
from html import escape
from itertools import count, product
from typing import Callable

from symbolica import Expression, Replacement

from .eft import operator_dimension, series_eft
from .expr import as_int, bar_field_pattern, field_pattern, is_zero, list_items, product_expr, terms
from .functional import apply_cd, derive_eom
from .indices import relabel_dummy_indices
from .symbols import display_string, latex_string, s
from .theory import Theory
from .theory_metadata import FieldDefinition, FieldVariation


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
    """Solve heavy scalar equations of motion order by order."""

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
    replacements = heavy_scalar_solution_replacements(solutions)
    return expr.replace_multiple(replacements).expand() if replacements else expr.expand()


def heavy_scalar_solution_replacements(
    solutions: dict[str, HeavyScalarSolution],
    *,
    fresh_dummy_indices: bool = False,
    max_order: int | None = None,
) -> tuple[Replacement, ...]:
    """Return Symbolica replacement rules for solved heavy scalar fields."""

    replacements: list[Replacement] = []
    fresh_counter = count()
    for solution in solutions.values():
        label = solution.field.label
        field_pat = field_pattern(label)
        bar_field_pat = bar_field_pattern(label)

        def fresh_solution_expr(expr: Expression) -> Expression:
            if not fresh_dummy_indices:
                return expr
            return relabel_dummy_indices(expr, start=100_000 + 1_000 * next(fresh_counter))

        def solution_order_terms(
            *,
            solution: HeavyScalarSolution,
            conjugate: bool,
        ) -> tuple[tuple[int, Expression], ...]:
            orders = (
                solution.conjugate_orders
                if conjugate and solution.conjugate_orders is not None
                else solution.orders
            )
            return tuple(
                (order, expr)
                for order, expr in sorted(orders.items())
                if max_order is None or order <= max_order
            )

        def solution_expr(
            match: dict[Expression, Expression],
            *,
            solution: HeavyScalarSolution,
            conjugate: bool,
            fresh_solution_expr: Callable[[Expression], Expression] = fresh_solution_expr,
        ) -> Expression:
            derivatives = list_items(match[s.FieldDerivativesWildcard])
            return sum(
                (
                    apply_cd(derivatives, fresh_solution_expr(expr))
                    for _order, expr in solution_order_terms(solution=solution, conjugate=conjugate)
                ),
                Expression.num(0),
            ).expand()

        def power_solution(
            match: dict[Expression, Expression],
            *,
            solution: HeavyScalarSolution,
            conjugate: bool,
            pattern: Expression,
            solution_expr: Callable[..., Expression] = solution_expr,
        ) -> Expression:
            exponent = as_int(match[s.PowExponentWildcard])
            if exponent is None or exponent <= 0:
                return (pattern ** s.PowExponentWildcard).replace_wildcards(match)
            derivatives = list_items(match[s.FieldDerivativesWildcard])
            order_terms = solution_order_terms(solution=solution, conjugate=conjugate)
            expanded_terms: list[Expression] = []
            for combination in product(order_terms, repeat=exponent):
                if max_order is not None and sum(order for order, _expr in combination) > max_order:
                    continue
                expanded_terms.append(
                    product_expr(
                        apply_cd(derivatives, fresh_solution_expr(expr))
                        for _order, expr in combination
                    )
                )
            return sum(expanded_terms, Expression.num(0)).expand()

        def bar_solution(
            match: dict[Expression, Expression],
            solution: HeavyScalarSolution = solution,
            solution_expr: Callable[..., Expression] = solution_expr,
        ) -> Expression:
            return solution_expr(match, solution=solution, conjugate=True)

        def field_solution(
            match: dict[Expression, Expression],
            solution: HeavyScalarSolution = solution,
            solution_expr: Callable[..., Expression] = solution_expr,
        ) -> Expression:
            return solution_expr(match, solution=solution, conjugate=False)

        if fresh_dummy_indices or max_order is not None:
            def bar_power_solution(
                match: dict[Expression, Expression],
                solution: HeavyScalarSolution = solution,
                pattern: Expression = bar_field_pat,
                power_solution: Callable[..., Expression] = power_solution,
            ) -> Expression:
                return power_solution(
                    match,
                    solution=solution,
                    conjugate=True,
                    pattern=pattern,
                )

            def field_power_solution(
                match: dict[Expression, Expression],
                solution: HeavyScalarSolution = solution,
                pattern: Expression = field_pat,
                power_solution: Callable[..., Expression] = power_solution,
            ) -> Expression:
                return power_solution(
                    match,
                    solution=solution,
                    conjugate=False,
                    pattern=pattern,
                )

            replacements.append(
                Replacement(
                    bar_field_pat ** s.PowExponentWildcard,
                    bar_power_solution,
                )
            )
            replacements.append(
                Replacement(
                    field_pat ** s.PowExponentWildcard,
                    field_power_solution,
                )
            )
        replacements.append(Replacement(bar_field_pat, bar_solution))
        replacements.append(Replacement(field_pat, field_solution))
    return tuple(replacements)


def replace_heavy_scalar_solutions_eft_limited(
    expr: Expression,
    solutions: dict[str, HeavyScalarSolution],
    theory: Theory,
    *,
    eft_order: int,
    fresh_dummy_indices: bool = False,
) -> Expression:
    """Replace heavy scalars with a per-term EFT-order cap.

    This is a bounded one-loop projection helper.  It avoids expanding high
    derivative orders of a heavy-scalar solution in source terms whose existing
    EFT dimension already leaves no room for those solution orders to
    contribute to the requested target order.  Symbolica still performs the
    actual replacement; Python only chooses a conservative order cap per
    additive source term.
    """

    if not solutions:
        return expr.expand()
    replaced_terms = []
    for term in terms(expr.expand()):
        max_order = _max_heavy_scalar_solution_order_for_term(
            theory,
            term,
            eft_order=eft_order,
        )
        replacements = heavy_scalar_solution_replacements(
            solutions,
            fresh_dummy_indices=fresh_dummy_indices,
            max_order=max_order,
        )
        replaced_terms.append(term.replace_multiple(replacements, repeat=False))
    return sum(replaced_terms, Expression.num(0)).expand()


def _max_heavy_scalar_solution_order_for_term(
    theory: Theory,
    term: Expression,
    *,
    eft_order: int,
) -> int:
    dimension = operator_dimension(term, theory, heavy_field_dimension=True)
    remaining = eft_order - dimension
    return max(1, int(2 * remaining - 1))


def replace_heavy_scalar_solutions(expr: Expression, solutions: dict[str, HeavyScalarSolution]) -> Expression:
    """Replace heavy scalar fields in ``expr`` by solved EFT-order solutions."""

    return _replace_heavy_fields(expr, solutions)


def match_tree(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> Expression:
    """Run tree-level heavy-scalar matching."""

    solutions = solve_heavy_scalar_eoms(theory, lagrangian, eft_order=eft_order)
    replaced = _replace_heavy_fields(lagrangian, solutions)
    truncated = series_eft(replaced.expand(), theory, eft_order=eft_order, heavy_field_dimension=False)
    return truncated.expand()


__all__ = [
    "HeavyScalarSolution",
    "heavy_scalar_solution_replacements",
    "match_tree",
    "replace_heavy_scalar_solutions_eft_limited",
    "replace_heavy_scalar_solutions",
    "solve_heavy_scalar_eoms",
]
