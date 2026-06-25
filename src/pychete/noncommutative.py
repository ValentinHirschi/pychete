from __future__ import annotations

from collections.abc import Callable
from functools import cache

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .expr import (
    bar_field_pattern,
    field_pattern,
    field_type,
    is_head,
    matching_subexpressions,
    product_expr,
)
from .symbols import s

_MAX_SCALAR_NCM_ARITY = 16


def scalarize_commutative_ncm_chains(expr: Expression) -> Expression:
    """Replace all-commutative ``NCM`` chains by ordinary products.

    The pass is intentionally conservative: chains containing fermion fields,
    Dirac/gamma/projector objects, open CDE derivatives, or nested
    non-commutative products are left untouched. Symbolica performs the actual
    matching and replacement over bounded arities; Python only classifies the
    compact matched operands.
    """

    if not _contains_ncm(expr):
        return expr
    return expr.replace_multiple(_scalar_ncm_replacements()).expand()


@cache
def _scalar_ncm_replacements() -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(2, _MAX_SCALAR_NCM_ARITY + 1):
        wildcards = _ncm_operand_wildcards(arity)
        pattern = s.NCM(*wildcards)
        replacements.append(
            Replacement(
                pattern,
                _scalar_ncm_replacement(pattern, wildcards),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _scalar_ncm_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_chain(match: dict[Expression, Expression]) -> Expression:
        operands = tuple(match[wildcard] for wildcard in wildcards)
        if not all(_is_commutative_ncm_operand(operand) for operand in operands):
            return pattern.replace_wildcards(match)
        return product_expr(operands)

    return replace_chain


def _is_commutative_ncm_operand(expr: Expression) -> bool:
    if _contains_noncommutative_marker(expr):
        return False
    for field in matching_subexpressions(expr, field_pattern()):
        if bool(field_type(field) == s.Fermion):
            return False
    for barred_field in matching_subexpressions(expr, bar_field_pattern()):
        if bool(field_type(barred_field[0]) == s.Fermion):
            return False
    return True


def _contains_noncommutative_marker(expr: Expression) -> bool:
    if bool(expr == s.PR) or bool(expr == s.PL):
        return True
    if expr.contains(s.PR) or expr.contains(s.PL):
        return True
    for pattern in _noncommutative_marker_patterns():
        if bool(expr.matches(pattern)):
            return True
    return False


@cache
def _noncommutative_marker_patterns() -> tuple[Expression, ...]:
    return (
        *tuple(
            s.NCM(*_ncm_operand_wildcards(arity))
            for arity in range(1, _MAX_SCALAR_NCM_ARITY + 1)
        ),
        *tuple(
            s.DiracProduct(*_ncm_operand_wildcards(arity))
            for arity in range(1, _MAX_SCALAR_NCM_ARITY + 1)
        ),
        s.Gamma(s.CDIndexWildcard),
        s.Sigma(s.CDIndexWildcard, s.CDBodyWildcard),
        s.Proj(s.CDBodyWildcard),
        s.OpenCD(s.OpenCDIndicesWildcard),
    )


def _contains_ncm(expr: Expression) -> bool:
    if expr.get_type() is AtomType.Fn and is_head(expr, s.NCM):
        return True
    return any(
        bool(expr.matches(s.NCM(*_ncm_operand_wildcards(arity))))
        for arity in range(2, _MAX_SCALAR_NCM_ARITY + 1)
    )


@cache
def _ncm_operand_wildcards(arity: int) -> tuple[Expression, ...]:
    return tuple(s.head(f"scalar_ncm_operand_{arity}_{index}_") for index in range(arity))


__all__ = ["scalarize_commutative_ncm_chains"]
