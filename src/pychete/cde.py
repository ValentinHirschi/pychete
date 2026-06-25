from __future__ import annotations

from collections.abc import Callable, Iterable

from symbolica import Expression, Replacement

from .expr import is_head, is_zero, list_expr, list_items, sum_expr
from .functional import apply_cd
from .symbols import s

_MAX_OPEN_CD_CHAIN_ARITY = 8


def open_covariant_derivative(indices: Expression | Iterable[Expression]) -> Expression:
    """Return an open covariant-derivative operator for CDE chain algebra."""

    if isinstance(indices, Expression):
        index_list = indices if is_head(indices, s.List) else list_expr(indices)
    else:
        index_list = list_expr(*tuple(indices))
    return s.OpenCD(index_list)


def act_with_open_covariant_derivatives(
    expr: Expression,
    *,
    max_chain_arity: int = _MAX_OPEN_CD_CHAIN_ARITY,
    max_passes: int = 16,
) -> Expression:
    """Apply open CDE covariant derivatives inside bounded ``NCM`` chains.

    This mirrors Matchete's ``ActWithOpenCDs`` semantics for the pychete
    representation: the rightmost ``OpenCD`` in an ``NCM`` chain acts on every
    factor to its right, using :func:`pychete.functional.apply_cd` for the
    actual symbolic derivative. Bounded-arity Symbolica replacement rules find
    chains natively; Python only orchestrates one matched chain at a time.
    """

    if max_chain_arity < 1:
        raise ValueError("max_chain_arity must be positive")
    if max_passes < 0:
        raise ValueError("max_passes must be non-negative")
    if not bool(expr.matches(s.OpenCD(s.OpenCDIndicesWildcard))):
        return expr

    replacements = _open_cd_chain_replacements(max_chain_arity)
    out = expr
    for _ in range(max_passes):
        updated = out.replace_multiple(replacements).expand()
        if bool(updated == out):
            return updated
        out = updated
    return out


def _open_cd_chain_replacements(max_chain_arity: int) -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, max_chain_arity + 1):
        wildcards = _chain_wildcards(arity)
        pattern = s.NCM(*wildcards)
        replacements.append(Replacement(pattern, _open_cd_chain_replacement(pattern, wildcards), rhs_cache_size=0))
    return tuple(replacements)


def _open_cd_chain_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_chain(match: dict[Expression, Expression]) -> Expression:
        operands = tuple(match[wildcard] for wildcard in wildcards)
        if not any(_is_open_cd(operand) for operand in operands):
            return pattern.replace_wildcards(match)
        return _act_rightmost_open_cd(operands)

    return replace_chain


def _act_rightmost_open_cd(operands: tuple[Expression, ...]) -> Expression:
    open_position = max(index for index, operand in enumerate(operands) if _is_open_cd(operand))
    open_cd = operands[open_position]
    suffix = operands[open_position + 1 :]
    if not suffix:
        return Expression.num(0)
    indices = list_items(open_cd[0])
    terms: list[Expression] = []
    for relative_position, factor in enumerate(suffix):
        derivative = apply_cd(indices, factor)
        if is_zero(derivative):
            continue
        varied_suffix = (*suffix[:relative_position], derivative, *suffix[relative_position + 1 :])
        terms.append(_chain_expr(*operands[:open_position], *varied_suffix))
    return sum_expr(terms).expand()


def _is_open_cd(expr: Expression) -> bool:
    return is_head(expr, s.OpenCD)


def _chain_wildcards(arity: int) -> tuple[Expression, ...]:
    return tuple(s.head(f"open_cd_ncm_operand_{arity}_{index}_") for index in range(arity))


def _chain_expr(*operands: Expression) -> Expression:
    kept = tuple(operand for operand in operands if not is_zero(operand) and not bool(operand == Expression.num(1)))
    if len(kept) != len(operands) and any(is_zero(operand) for operand in operands):
        return Expression.num(0)
    if not kept:
        return Expression.num(1)
    if len(kept) == 1:
        return kept[0]
    return s.NCM(*kept)


__all__ = ["act_with_open_covariant_derivatives", "open_covariant_derivative"]
