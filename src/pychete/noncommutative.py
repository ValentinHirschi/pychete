from __future__ import annotations

from collections.abc import Callable
from functools import cache

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .expr import (
    bar_field_pattern,
    factors,
    field_pattern,
    field_type,
    is_head,
    is_zero,
    matching_subexpressions,
    product_expr,
    sum_expr,
    terms,
)
from .symbols import s

_MAX_SCALAR_NCM_ARITY = 16


def normalize_ncm_chains(expr: Expression, *, max_passes: int = 8) -> Expression:
    """Flatten nested pychete ``NCM`` chains and hoist scalar coefficients.

    Matchete's noncommutative product flattens nested products before Dirac
    simplification. pychete keeps ``NCM`` explicit, so generated interaction
    insertions can produce operands such as ``a*NCM(x, y)`` inside a larger
    ``NCM`` chain. Symbolica bounded-arity replacement rules find those chains;
    Python only classifies the matched operands and refuses to hoist factors
    that are themselves noncommutative.
    """

    if max_passes < 0:
        raise ValueError("max_passes must be non-negative")
    if not _contains_ncm(expr):
        return expr
    out = expr
    for _ in range(max_passes):
        updated = out.replace_multiple(_normalize_ncm_replacements()).expand()
        if bool(updated == out):
            return updated
        out = updated
    return out


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
    return normalize_ncm_chains(expr).replace_multiple(_scalar_ncm_replacements()).expand()


def distribute_ncm_additions(
    expr: Expression,
    *,
    max_passes: int = 8,
    max_operand_terms: int = 32,
) -> Expression:
    """Distribute additive operands inside pychete ``NCM`` chains.

    Symbolica does not treat pychete's ``NCM`` head as multiplication, so a
    chain such as ``NCM(a + b, OpenCD(mu), x)`` must be linearized explicitly
    before open-derivative and Wilson-line pruning passes can operate on the
    individual source terms. Bounded Symbolica replacement rules find the
    chains; Python only chooses one matched additive operand at a time.
    """

    if max_passes < 0:
        raise ValueError("max_passes must be non-negative")
    if max_operand_terms < 2:
        raise ValueError("max_operand_terms must be at least two")
    if not _contains_ncm(expr):
        return expr
    out = expr
    for _ in range(max_passes):
        updated = out.replace_multiple(_distribute_ncm_replacements(max_operand_terms)).expand()
        if bool(updated == out):
            return updated
        out = updated
    return out


@cache
def _normalize_ncm_replacements() -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_SCALAR_NCM_ARITY + 1):
        wildcards = _ncm_operand_wildcards(arity)
        pattern = s.NCM(*wildcards)
        replacements.append(
            Replacement(
                pattern,
                _normalize_ncm_replacement(pattern, wildcards),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _normalize_ncm_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_chain(match: dict[Expression, Expression]) -> Expression:
        operands = tuple(match[wildcard] for wildcard in wildcards)
        coefficient = Expression.num(1)
        flattened: list[Expression] = []
        changed = False
        for operand in operands:
            operand_coefficient, operand_chain, operand_changed = _normalize_ncm_operand(operand)
            if is_zero(operand_coefficient):
                return Expression.num(0)
            coefficient *= operand_coefficient
            flattened.extend(operand_chain)
            changed = changed or operand_changed
        if not changed:
            return pattern.replace_wildcards(match)
        if not flattened:
            return coefficient
        return coefficient * s.NCM(*flattened)

    return replace_chain


def _normalize_ncm_operand(operand: Expression) -> tuple[Expression, tuple[Expression, ...], bool]:
    if is_zero(operand):
        return Expression.num(0), (), True
    if bool(operand == Expression.num(1)):
        return Expression.num(1), (), True
    if is_head(operand, s.NCM):
        return Expression.num(1), tuple(operand[index] for index in range(len(operand))), True
    ncm_factors: list[Expression] = []
    scalar_factors: list[Expression] = []
    for factor in factors(operand):
        if is_head(factor, s.NCM):
            ncm_factors.append(factor)
        else:
            scalar_factors.append(factor)
    if not ncm_factors:
        return Expression.num(1), (operand,), False
    scalar_coefficient = product_expr(scalar_factors)
    if not _is_commutative_ncm_operand(scalar_coefficient):
        return Expression.num(1), (operand,), False
    flattened = tuple(
        item
        for ncm_factor in ncm_factors
        for item in (ncm_factor[index] for index in range(len(ncm_factor)))
    )
    return scalar_coefficient, flattened, True


@cache
def _scalar_ncm_replacements() -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_SCALAR_NCM_ARITY + 1):
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


@cache
def _distribute_ncm_replacements(max_operand_terms: int) -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_SCALAR_NCM_ARITY + 1):
        wildcards = _ncm_operand_wildcards(arity)
        pattern = s.NCM(*wildcards)
        replacements.append(
            Replacement(
                pattern,
                _distribute_ncm_replacement(pattern, wildcards, max_operand_terms=max_operand_terms),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _distribute_ncm_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
    *,
    max_operand_terms: int,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_chain(match: dict[Expression, Expression]) -> Expression:
        operands = tuple(match[wildcard] for wildcard in wildcards)
        for position, operand in enumerate(operands):
            operand_terms = terms(operand)
            if len(operand_terms) <= 1:
                continue
            if len(operand_terms) > max_operand_terms:
                return pattern.replace_wildcards(match)
            return sum_expr(
                _ncm_from_operands((*operands[:position], term, *operands[position + 1 :]))
                for term in operand_terms
            )
        return pattern.replace_wildcards(match)

    return replace_chain


def _ncm_from_operands(operands: tuple[Expression, ...]) -> Expression:
    kept = tuple(operand for operand in operands if not is_zero(operand) and not bool(operand == Expression.num(1)))
    if len(kept) != len(operands) and any(is_zero(operand) for operand in operands):
        return Expression.num(0)
    if not kept:
        return Expression.num(1)
    if len(kept) == 1:
        return kept[0]
    return s.NCM(*kept)


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


__all__ = ["distribute_ncm_additions", "normalize_ncm_chains", "scalarize_commutative_ncm_chains"]
