from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from math import factorial

from symbolica import Expression, S

from .expr import as_int, is_head, list_expr, list_items, product_expr, sum_expr
from .symbols import s


def symmetric_lorentz_gamma_factor(
    pair_count: int,
    *,
    epsilon: Expression | None = None,
    order: int = 1,
) -> Expression:
    """Return Matchete's ``SymGammaFactor[pair_count, 4]`` epsilon series.

    Matchete evaluates
    ``Gamma[d/2] / (2^n Gamma[d/2+n])`` at ``d = 4 - 2 epsilon`` and keeps the
    linear epsilon term because it can multiply loop-function poles. This
    helper exposes the same bounded series for pychete's Wilson-line
    loop-symmetric tensor stage.
    """

    if pair_count < 0:
        raise ValueError("pair_count must be non-negative")
    if order < 0:
        raise ValueError("order must be non-negative")
    if pair_count == 0:
        return Expression.num(1)
    regulator = S("vakint::ε") if epsilon is None else epsilon
    base = Expression.num(1) / (Expression.num(2) ** pair_count * factorial(pair_count + 1))
    if order == 0:
        return base
    linear_coefficient = _harmonic_number(pair_count + 1) - Expression.num(1)
    return (base * (Expression.num(1) + regulator * linear_coefficient)).expand()


def evaluate_sym_gamma_factors(
    expr: Expression,
    *,
    epsilon: Expression | None = None,
    order: int = 1,
) -> Expression:
    """Evaluate formal ``SymGammaFactor`` atoms with the Matchete epsilon series."""

    pair_count = s.head("sym_gamma_pair_count_")
    dimension = s.head("sym_gamma_dimension_")
    pattern = s.SymGammaFactor(pair_count, dimension)
    if not bool(expr.matches(pattern)):
        return expr

    def replace_factor(match: dict[Expression, Expression]) -> Expression:
        n = as_int(match[pair_count])
        dim = as_int(match[dimension])
        if n is None or dim not in (None, 4):
            return pattern.replace_wildcards(match)
        return symmetric_lorentz_gamma_factor(n, epsilon=epsilon, order=order)

    return expr.replace(pattern, replace_factor, rhs_cache_size=0).expand()


def symmetric_lorentz_tensor(
    indices: Iterable[Expression],
    *,
    evaluate_gamma: bool = True,
    epsilon: Expression | None = None,
    gamma_order: int = 1,
) -> Expression:
    """Return Matchete's symmetric loop-momentum tensor for Lorentz indices."""

    reduced_indices = _drop_repeated_index_pairs(tuple(indices))
    rank = len(reduced_indices)
    if rank % 2:
        return Expression.num(0)
    pair_count = rank // 2
    gamma = (
        symmetric_lorentz_gamma_factor(pair_count, epsilon=epsilon, order=gamma_order)
        if evaluate_gamma
        else s.SymGammaFactor(Expression.num(pair_count), Expression.num(4))
    )
    if rank == 0:
        return gamma
    metric_sum = sum_expr(
        product_expr(s.Metric(left, right) for left, right in pairing)
        for pairing in _metric_pairings(reduced_indices)
    )
    return (metric_sum * gamma).expand()


def evaluate_symmetric_lorentz_indices(
    expr: Expression,
    *,
    evaluate_gamma: bool = True,
    epsilon: Expression | None = None,
    gamma_order: int = 1,
) -> Expression:
    """Replace ``SymmetricLorentzInds`` atoms by metric pairings.

    Discovery is delegated to Symbolica wildcard matching. Python only
    enumerates the finite metric pairings for each matched symmetric tensor,
    mirroring Matchete's ``EvaluateSymmetricLorentzInds`` stage.
    """

    pattern = s.SymmetricLorentzInds(s.SymmetricLorentzIndicesWildcard)
    if not bool(expr.matches(pattern)):
        return expr

    def replace_tensor(match: dict[Expression, Expression]) -> Expression:
        payload = match[s.SymmetricLorentzIndicesWildcard]
        indices = list_items(payload) if is_head(payload, s.List) else (payload,)
        return symmetric_lorentz_tensor(
            indices,
            evaluate_gamma=evaluate_gamma,
            epsilon=epsilon,
            gamma_order=gamma_order,
        )

    return expr.replace(pattern, replace_tensor, rhs_cache_size=0).expand()


def _drop_repeated_index_pairs(indices: tuple[Expression, ...]) -> tuple[Expression, ...]:
    remaining: list[Expression] = []
    for index in indices:
        for position, known in enumerate(remaining):
            if bool(index == known):
                del remaining[position]
                break
        else:
            remaining.append(index)
    return tuple(remaining)


def _metric_pairings(indices: Sequence[Expression]) -> Iterator[tuple[tuple[Expression, Expression], ...]]:
    if not indices:
        yield ()
        return
    first = indices[0]
    for position in range(1, len(indices)):
        second = indices[position]
        rest = (*indices[1:position], *indices[position + 1 :])
        for tail in _metric_pairings(rest):
            yield ((first, second), *tail)


def _harmonic_number(n: int) -> Expression:
    if n < 1:
        return Expression.num(0)
    return sum_expr(Expression.num(1) / k for k in range(1, n + 1))


__all__ = [
    "evaluate_sym_gamma_factors",
    "evaluate_symmetric_lorentz_indices",
    "symmetric_lorentz_gamma_factor",
    "symmetric_lorentz_tensor",
]
