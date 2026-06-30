from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from html import escape
from typing import Callable

from symbolica import Expression, Replacement

from .eft import series_eft
from .expr import (
    bar_field_pattern,
    field_pattern,
    is_zero,
    list_items,
)
from .functional import apply_cd, derive_eom
from .spinor import bar_expr, canonicalize_fermion_derivative_bilinears, ncm_expr, normalize_ncm
from .printing import display_string, latex_string
from .symbols import s
from .theory import FieldDefinition, FieldVariation, Theory


def _normalize_matching_expression(expr: Expression) -> Expression:
    return normalize_ncm(expr)


class HeavyFieldFamily(StrEnum):
    """Heavy-field family handled by tree-level matching."""

    SCALAR = "scalar"
    FERMION = "fermion"
    VECTOR = "vector"


@dataclass(frozen=True)
class HeavyFieldSolution:
    """Order-by-order solution for a heavy-field equation of motion."""

    field: FieldDefinition
    orders: dict[int, Expression]
    conjugate_orders: dict[int, Expression] | None = None
    family: HeavyFieldFamily = HeavyFieldFamily.SCALAR

    @property
    def inclusive(self) -> Expression:
        """Sum all stored EFT orders for the heavy field."""

        return self._sum_orders(self.orders)

    @property
    def inclusive_conjugate(self) -> Expression:
        """Sum all stored EFT orders for the conjugate heavy field."""

        if self.conjugate_orders is None:
            return self.inclusive
        return self._sum_orders(self.conjugate_orders)

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{{self.field.name}}}: {latex_string(self.inclusive)}$"

    def _repr_html_(self) -> str:
        return f"<code>{escape(self.field.name)}: {escape(display_string(self.inclusive))}</code>"

    def _sum_orders(self, orders: dict[int, Expression]) -> Expression:
        out = Expression.num(0)
        for _, expr in sorted(orders.items()):
            out = out + expr
        return _normalize_matching_expression(out)


@dataclass(frozen=True)
class _HeavyFieldEquations:
    source: Expression
    conjugate_source: Expression | None = None


@dataclass(frozen=True)
class _HeavyFieldSolverSpec:
    family: HeavyFieldFamily
    field_type: Expression
    build_equations: Callable[[Theory, Expression, FieldDefinition, int], _HeavyFieldEquations]
    solve_orders: Callable[[Theory, FieldDefinition, Expression, int], dict[int, Expression]]
    solve_conjugate_orders: Callable[
        [Theory, FieldDefinition, _HeavyFieldEquations, dict[int, Expression], int],
        dict[int, Expression] | None,
    ]


def _zero_field_label(expr: Expression, label: Expression, *, conjugate: bool = False) -> Expression:
    pattern = bar_field_pattern(label) if conjugate else field_pattern(label)
    return _normalize_matching_expression(expr.replace(pattern, Expression.num(0)))


def _mass_squared(field: FieldDefinition) -> Expression:
    mass = field.mass_expr()
    if mass is None:
        raise ValueError(f"Heavy field {field.name} has no mass coupling")
    return mass**2


def _mass(field: FieldDefinition) -> Expression:
    mass = field.mass_expr()
    if mass is None:
        raise ValueError(f"Heavy field {field.name} has no mass coupling")
    return mass


def _box(theory: Theory, expr: Expression, order: int) -> Expression:
    mu = theory.dummy_index(order)
    return apply_cd((mu, mu), expr)


def _solve_scalar_orders_from_source(theory: Theory, source: Expression, mass2: Expression, *, eft_order: int) -> dict[int, Expression]:
    orders: dict[int, Expression] = {}
    max_order = eft_order - 1
    previous_nonzero: Expression | None = None
    for order in range(1, max_order + 1):
        if order == 1:
            value = _normalize_matching_expression(source / mass2)
        elif order % 2 == 0:
            value = Expression.num(0)
        else:
            if previous_nonzero is None:
                value = Expression.num(0)
            else:
                value = _normalize_matching_expression(-_box(theory, previous_nonzero, order) / mass2)

        orders[order] = value
        if order % 2 == 1 and not is_zero(value):
            previous_nonzero = value
    return orders


def _prepare_heavy_lagrangian(theory: Theory, lagrangian: Expression) -> Expression:
    theory._validate_registered_expression(lagrangian)
    return _normalize_matching_expression(lagrangian)


def _matching_heavy_fields(theory: Theory, field_type: Expression) -> tuple[FieldDefinition, ...]:
    return tuple(field for field in theory.fields.values() if field.heavy and bool(field.type_expr == field_type))


def _solve_heavy_fields_with_spec(
    theory: Theory,
    lagrangian: Expression,
    spec: _HeavyFieldSolverSpec,
    *,
    eft_order: int,
) -> dict[str, HeavyFieldSolution]:
    solutions: dict[str, HeavyFieldSolution] = {}
    for field in _matching_heavy_fields(theory, spec.field_type):
        equations = spec.build_equations(theory, lagrangian, field, eft_order)
        orders = spec.solve_orders(theory, field, equations.source, eft_order)
        conjugate_orders = spec.solve_conjugate_orders(theory, field, equations, orders, eft_order)
        solutions[field.name] = HeavyFieldSolution(
            field=field,
            orders=orders,
            conjugate_orders=conjugate_orders,
            family=spec.family,
        )
    return solutions


def _build_scalar_equations(theory: Theory, lagrangian: Expression, field: FieldDefinition, eft_order: int) -> _HeavyFieldEquations:
    if field.is_self_conjugate:
        eom = derive_eom(theory, lagrangian, field, eft_order=eft_order)
        return _HeavyFieldEquations(source=_zero_field_label(eom, field.label))

    eom = derive_eom(theory, lagrangian, field, eft_order=eft_order, variation=FieldVariation.BAR)
    source = _zero_field_label(eom, field.label)
    conjugate_eom = derive_eom(theory, lagrangian, field, eft_order=eft_order, variation=FieldVariation.FIELD)
    conjugate_source = _zero_field_label(conjugate_eom, field.label, conjugate=True)
    return _HeavyFieldEquations(source=source, conjugate_source=conjugate_source)


def _solve_scalar_orders(theory: Theory, field: FieldDefinition, source: Expression, eft_order: int) -> dict[int, Expression]:
    return _solve_scalar_orders_from_source(theory, source, _mass_squared(field), eft_order=eft_order)


def _solve_scalar_conjugate_orders(
    theory: Theory,
    field: FieldDefinition,
    equations: _HeavyFieldEquations,
    _orders: dict[int, Expression],
    eft_order: int,
) -> dict[int, Expression] | None:
    if equations.conjugate_source is None:
        return None
    return _solve_scalar_orders(theory, field, equations.conjugate_source, eft_order)


def _slash_d(theory: Theory, expr: Expression, order: int) -> Expression:
    mu = theory.dummy_index(order)
    return ncm_expr(s.Gamma(mu), apply_cd((mu,), expr))


def _build_fermion_equations(theory: Theory, lagrangian: Expression, field: FieldDefinition, eft_order: int) -> _HeavyFieldEquations:
    eom = derive_eom(theory, lagrangian, field, eft_order=eft_order, variation=FieldVariation.BAR)
    return _HeavyFieldEquations(source=_zero_field_label(eom, field.label))


def _solve_fermion_orders_from_source(theory: Theory, source: Expression, mass: Expression, *, eft_order: int) -> dict[int, Expression]:
    orders: dict[int, Expression] = {}
    max_order = max(1, eft_order - 4)
    for order in range(1, max_order + 1):
        if order == 1:
            value = source / mass
        else:
            value = Expression.I * _slash_d(theory, orders[order - 1], order) / mass
        orders[order] = _normalize_matching_expression(value)
    return orders


def _solve_fermion_orders(theory: Theory, field: FieldDefinition, source: Expression, eft_order: int) -> dict[int, Expression]:
    return _solve_fermion_orders_from_source(theory, source, _mass(field), eft_order=eft_order)


def _solve_fermion_conjugate_orders(
    _theory: Theory,
    _field: FieldDefinition,
    _equations: _HeavyFieldEquations,
    orders: dict[int, Expression],
    _eft_order: int,
) -> dict[int, Expression]:
    return {order: bar_expr(expr) for order, expr in orders.items()}


_HEAVY_SCALAR_SOLVER = _HeavyFieldSolverSpec(
    family=HeavyFieldFamily.SCALAR,
    field_type=s.Scalar,
    build_equations=_build_scalar_equations,
    solve_orders=_solve_scalar_orders,
    solve_conjugate_orders=_solve_scalar_conjugate_orders,
)
_HEAVY_FERMION_SOLVER = _HeavyFieldSolverSpec(
    family=HeavyFieldFamily.FERMION,
    field_type=s.Fermion,
    build_equations=_build_fermion_equations,
    solve_orders=_solve_fermion_orders,
    solve_conjugate_orders=_solve_fermion_conjugate_orders,
)
_HEAVY_FIELD_SOLVERS = (_HEAVY_SCALAR_SOLVER, _HEAVY_FERMION_SOLVER)


def _solve_matching_heavy_field_eoms(
    theory: Theory,
    lagrangian: Expression,
    *,
    eft_order: int,
    families: tuple[HeavyFieldFamily, ...] | None = None,
) -> dict[str, HeavyFieldSolution]:
    prepared = _prepare_heavy_lagrangian(theory, lagrangian)
    solutions: dict[str, HeavyFieldSolution] = {}
    selected_families = set(families) if families is not None else None
    for spec in _HEAVY_FIELD_SOLVERS:
        if selected_families is not None and spec.family not in selected_families:
            continue
        solutions.update(_solve_heavy_fields_with_spec(theory, prepared, spec, eft_order=eft_order))
    return solutions


def solve_heavy_field_eoms(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> dict[str, HeavyFieldSolution]:
    """Solve all supported heavy-field equations of motion order by order."""

    return _solve_matching_heavy_field_eoms(theory, lagrangian, eft_order=eft_order)


def solve_heavy_scalar_eoms(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> dict[str, HeavyFieldSolution]:
    """Solve heavy scalar equations of motion order by order."""

    return _solve_matching_heavy_field_eoms(theory, lagrangian, eft_order=eft_order, families=(HeavyFieldFamily.SCALAR,))


def solve_heavy_fermion_eoms(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> dict[str, HeavyFieldSolution]:
    """Solve diagonal heavy Dirac-fermion equations of motion order by order."""

    return _solve_matching_heavy_field_eoms(theory, lagrangian, eft_order=eft_order, families=(HeavyFieldFamily.FERMION,))


def _replace_heavy_fields(expr: Expression, solutions: dict[str, HeavyFieldSolution]) -> Expression:
    replacements: list[Replacement] = []
    for solution in solutions.values():
        label = solution.field.label

        def bar_solution(match: dict[Expression, Expression], solution: HeavyFieldSolution = solution) -> Expression:
            return apply_cd(list_items(match[s.FieldDerivativesWildcard]), solution.inclusive_conjugate)

        def field_solution(match: dict[Expression, Expression], solution: HeavyFieldSolution = solution) -> Expression:
            return apply_cd(list_items(match[s.FieldDerivativesWildcard]), solution.inclusive)

        replacements.append(Replacement(bar_field_pattern(label), bar_solution))
        replacements.append(Replacement(field_pattern(label), field_solution))
    return _normalize_matching_expression(expr.replace_multiple(replacements)) if replacements else _normalize_matching_expression(expr)


def match_tree(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> Expression:
    solutions = solve_heavy_field_eoms(theory, lagrangian, eft_order=eft_order)
    replaced = _replace_heavy_fields(lagrangian, solutions)
    truncated = series_eft(replaced.expand(), theory, eft_order=eft_order, heavy_field_dimension=False)
    return canonicalize_fermion_derivative_bilinears(_normalize_matching_expression(truncated))
