from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from fractions import Fraction
from typing import TYPE_CHECKING, Any

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .eft import operator_dimension
from .expr import coupling_pattern, factors, is_zero, product_expr, terms
from .symbols import SymbolDataKey, SymbolRole, canonical_string, s, safe_symbol_name, symbol_data

if TYPE_CHECKING:
    from .theory import Theory


def infer_coupling_mass_dimensions(theory: Theory, lagrangian: Expression) -> dict[str, int | float]:
    """Infer canonical coupling mass dimensions from Lagrangian terms.

    The inference builds linear dimension equations from expanded Lagrangian
    monomials. Coupling powers, including inverse powers, are extracted with
    Symbolica's rational-polynomial representation. Existing coupling
    dimensions, field mass labels, and gauge-group couplings are treated as
    known data; only numerically solved dimensions are returned for remaining
    couplings.
    """

    known = _known_coupling_mass_dimensions(theory)
    unknown_names = tuple(name for name in theory.couplings if name not in known)
    variables = {
        name: Expression.symbol(f"pychete::mass_dimension_{theory.name}_{safe_symbol_name(name)}")
        for name in unknown_names
    }
    equations: list[Expression] = []
    for term in terms(lagrangian.expand()):
        powers = _term_coupling_label_powers(term)
        if powers is None:
            continue
        equation = Expression.num(_operator_scaled_mass_dimension_without_couplings(term) - 8)
        has_unknown = False
        for name, power in sorted(powers.items()):
            if power == 0:
                continue
            if name in known:
                equation += Expression.num(power * _scaled_dimension_value(known[name]))
            elif name in variables:
                equation += Expression.num(power) * variables[name]
                has_unknown = True
        if has_unknown and not is_zero(equation):
            equations.append(equation)

    inferred = dict(known)
    if equations and variables:
        solutions = Expression.solve_linear_system(
            equations,
            tuple(variables.values()),
            warn_if_underdetermined=False,
        )
        for name, solution in zip(variables, solutions, strict=True):
            scaled_dimension = _numeric_fraction(solution)
            if scaled_dimension is None:
                continue
            dimension = scaled_dimension / 2
            inferred[name] = int(dimension) if dimension.denominator == 1 else float(dimension)
    return inferred


def _known_coupling_mass_dimensions(theory: Theory) -> dict[str, int | float]:
    known: dict[str, int | float] = {}
    for name, definition in theory.couplings.items():
        dimension = definition.canonical_mass_dimension
        if dimension is not None:
            known[name] = dimension
    for group in theory.groups.values():
        coupling = group.get("coupling")
        if isinstance(coupling, str):
            known.setdefault(coupling, 0)
    for field in theory.fields.values():
        if field.mass_label is None:
            continue
        name = symbol_data(field.mass_label, SymbolDataKey.LABEL)
        if isinstance(name, str):
            known.setdefault(name, 1)
    return known


def _operator_scaled_mass_dimension_without_couplings(term: Expression) -> int:
    stripped = term.replace_multiple(_strip_coupling_replacements())
    dimension = Fraction(str(operator_dimension(stripped, heavy_field_dimension=False)))
    scaled = 2 * dimension
    if scaled.denominator != 1:
        raise ValueError(f"operator dimension {dimension} cannot be represented in half-integer units")
    return scaled.numerator


def _strip_coupling_replacements() -> tuple[Replacement, Replacement]:
    pattern = coupling_pattern()
    restriction = s.CouplingLabelWildcard.req_tag(SymbolRole.COUPLING.value)
    return (
        Replacement(s.Bar(pattern), Expression.num(1), restriction),
        Replacement(pattern, Expression.num(1), restriction),
    )


def _term_coupling_label_powers(term: Expression) -> dict[str, int] | None:
    variables = _coupling_power_variables(term)
    if not variables:
        return {}
    variable_exprs = tuple(atom for atom, _name in variables)
    try:
        rational = term.to_rational_polynomial(variable_exprs)
    except ValueError:
        stripped = _strip_top_level_numeric_factors(term)
        if bool(stripped == term):
            return None
        try:
            rational = stripped.to_rational_polynomial(variable_exprs)
        except ValueError:
            return None
    numerator_powers = _single_polynomial_power_vector(
        rational.numerator().coefficient_list(variable_exprs),
        len(variable_exprs),
    )
    denominator_powers = _single_polynomial_power_vector(
        rational.denominator().coefficient_list(variable_exprs),
        len(variable_exprs),
    )
    if numerator_powers is None or denominator_powers is None:
        return None
    powers: defaultdict[str, int] = defaultdict(int)
    for numerator_power, denominator_power, (_atom, name) in zip(
        numerator_powers,
        denominator_powers,
        variables,
        strict=True,
    ):
        powers[name] += numerator_power - denominator_power
    return dict(powers)


def _strip_top_level_numeric_factors(expr: Expression) -> Expression:
    return product_expr(factor for factor in factors(expr) if factor.get_type() is not AtomType.Num)


def _coupling_power_variables(expr: Expression) -> tuple[tuple[Expression, str], ...]:
    pattern = coupling_pattern()
    restriction = s.CouplingLabelWildcard.req_tag(SymbolRole.COUPLING.value)
    variables: dict[str, tuple[Expression, str]] = {}
    for match in expr.match(pattern, restriction):
        atom = pattern.replace_wildcards(match)
        label = match[s.CouplingLabelWildcard]
        name = symbol_data(label, SymbolDataKey.LABEL)
        if not isinstance(name, str):
            continue
        variables.setdefault(canonical_string(atom), (atom, name))
        barred = s.Bar(atom)
        if bool(expr.matches(barred)):
            variables.setdefault(canonical_string(barred), (barred, name))
    return tuple(variables.values())


def _single_polynomial_power_vector(
    coefficients: Sequence[tuple[Sequence[int], Any]],
    variable_count: int,
) -> tuple[int, ...] | None:
    nonzero = [
        tuple(int(power) for power in powers)
        for powers, coefficient in coefficients
        if not is_zero(coefficient.to_expression())
    ]
    if len(nonzero) != 1 or len(nonzero[0]) != variable_count:
        return None
    return nonzero[0]


def _scaled_dimension_value(value: int | float) -> int:
    scaled = 2 * (Fraction(value) if isinstance(value, int) else Fraction(str(value)))
    if scaled.denominator != 1:
        raise ValueError(f"dimension {value!r} cannot be represented in half-integer units")
    return scaled.numerator


def _numeric_fraction(expr: Expression) -> Fraction | None:
    if expr.get_type() is not AtomType.Num:
        return None
    try:
        return Fraction(canonical_string(expr))
    except ValueError:
        return Fraction(str(float(expr)))


__all__ = ["infer_coupling_mass_dimensions"]
