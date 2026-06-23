from __future__ import annotations

from dataclasses import dataclass

from symbolica import Expression

from .eft import series_eft
from .expr import (
    collect_bar_field_atoms,
    collect_field_atoms,
    expr_key,
    bar_field_inner,
    field_derivatives,
    field_label,
    is_head,
    replace_many,
    transform,
)
from .functional import apply_cd, derive_eom
from .symbols import canonical_string, s
from .theory import FieldDefinition, Theory


@dataclass(frozen=True)
class HeavyScalarSolution:
    field: FieldDefinition
    orders: dict[int, Expression]
    conjugate_orders: dict[int, Expression] | None = None

    @property
    def inclusive(self) -> Expression:
        out = s.zero
        for _, expr in sorted(self.orders.items()):
            out = out + expr
        return out.expand()

    @property
    def inclusive_conjugate(self) -> Expression:
        if self.conjugate_orders is None:
            return self.inclusive
        out = s.zero
        for _, expr in sorted(self.conjugate_orders.items()):
            out = out + expr
        return out.expand()


def _zero_field_label(expr: Expression, label: Expression, *, conjugate: bool = False) -> Expression:
    label_key = expr_key(label)

    def visitor(sub: Expression) -> Expression | None:
        if not conjugate and is_head(sub, s.Field) and expr_key(field_label(sub)) == label_key:
            return s.zero
        if conjugate and is_head(sub, s.Bar) and is_head(sub[0], s.Field) and expr_key(field_label(sub[0])) == label_key:
            return s.zero
        return None

    return transform(expr, visitor).expand()


def _mass_squared(theory: Theory, field: FieldDefinition) -> Expression:
    mass = theory.mass_expr(field)
    if mass is None:
        raise ValueError(f"Heavy field {field.name} has no mass coupling")
    return mass**2


def _box(theory: Theory, expr: Expression, order: int) -> Expression:
    mu = theory.lorentz_index(f"u{order}")
    return apply_cd((mu, mu), expr)


def _solve_orders_from_source(theory: Theory, source: Expression, mass2: Expression, *, eft_order: int) -> dict[int, Expression]:
    orders: dict[int, Expression] = {}
    max_order = eft_order - 1
    previous_nonzero: Expression | None = None
    for order in range(1, max_order + 1):
        if order == 1:
            value = (source / mass2).expand()
        elif order % 2 == 0:
            value = s.zero
        else:
            if previous_nonzero is None:
                value = s.zero
            else:
                value = (-_box(theory, previous_nonzero, order) / mass2).expand()

        orders[order] = value
        if order % 2 == 1 and canonical_string(value.expand()) != "0":
            previous_nonzero = value
    return orders


def solve_heavy_scalar_eoms(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> dict[str, HeavyScalarSolution]:
    lagrangian = theory.set_lagrangian(lagrangian)
    solutions: dict[str, HeavyScalarSolution] = {}

    for field in theory.fields.values():
        if not field.heavy or canonical_string(field.type) != canonical_string(s.Scalar):
            continue

        mass2 = _mass_squared(theory, field)

        if field.self_conjugate:
            eom = derive_eom(theory, lagrangian, field, eft_order=eft_order)
            source = _zero_field_label(eom, field.label)
            solution = HeavyScalarSolution(
                field=field,
                orders=_solve_orders_from_source(theory, source, mass2, eft_order=eft_order),
            )
        else:
            eom = derive_eom(theory, lagrangian, field, eft_order=eft_order, variation="bar")
            source = _zero_field_label(eom, field.label)
            conjugate_eom = derive_eom(theory, lagrangian, field, eft_order=eft_order, variation="field")
            conjugate_source = _zero_field_label(conjugate_eom, field.label, conjugate=True)
            solution = HeavyScalarSolution(
                field=field,
                orders=_solve_orders_from_source(theory, source, mass2, eft_order=eft_order),
                conjugate_orders=_solve_orders_from_source(theory, conjugate_source, mass2, eft_order=eft_order),
            )
        theory.analysis.heavy_scalar_solutions[field.name] = solution.orders
        solutions[field.name] = solution

    return solutions


def _replace_heavy_fields(theory: Theory, expr: Expression, solutions: dict[str, HeavyScalarSolution]) -> Expression:
    replacements: list[tuple[Expression, Expression]] = []
    field_solution_by_label = {
        expr_key(solution.field.label): solution
        for solution in solutions.values()
    }
    for atom in collect_bar_field_atoms(expr):
        inner = bar_field_inner(atom)
        solution = field_solution_by_label.get(expr_key(field_label(inner)))
        if solution is None:
            continue
        replacement = apply_cd(field_derivatives(inner), solution.inclusive_conjugate)
        replacements.append((atom, replacement))
    for atom in collect_field_atoms(expr):
        solution = field_solution_by_label.get(expr_key(field_label(atom)))
        if solution is None:
            continue
        replacement = apply_cd(field_derivatives(atom), solution.inclusive)
        replacements.append((atom, replacement))
    return replace_many(expr, replacements).expand()


def match_tree(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> Expression:
    solutions = solve_heavy_scalar_eoms(theory, lagrangian, eft_order=eft_order)
    replaced = _replace_heavy_fields(theory, lagrangian, solutions)
    truncated = series_eft(replaced.expand(), theory, eft_order=eft_order, heavy_field_dimension=False)
    return truncated.expand()
