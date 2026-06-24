from __future__ import annotations

from dataclasses import dataclass
from html import escape

from symbolica import Expression, Replacement

from .eft import series_eft
from .expr import (
    bar_field_pattern,
    field_pattern,
    is_zero,
    list_items,
)
from .functional import apply_cd, derive_eom
from .symbols import display_string, latex_string, s
from .theory import FieldDefinition, FieldVariation, Theory


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
