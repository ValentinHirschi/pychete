from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from math import factorial

from symbolica import Expression, S

from .expr import (
    as_int,
    factors,
    is_head,
    is_zero,
    list_expr,
    list_items,
    pow_parts,
    product_expr,
    sum_expr,
    terms,
)
from .symbols import s


def collect_loop_momenta_to_symmetric_lorentz(
    expr: Expression,
    *,
    include_massless_denominator_shift: bool = False,
    loop_momentum_squared: Expression | None = None,
) -> Expression:
    """Collect explicit loop-momentum vectors into symmetric Lorentz tensors.

    This mirrors the tensor part of Matchete's ``GatherLoopMomenta``/
    ``LoopMoms`` stage. Odd-rank loop-momentum terms vanish. Even-rank terms
    have all explicit ``LoopMomentum(index)`` factors replaced by a single
    ``SymmetricLorentzInds({indices...})`` marker. When
    ``include_massless_denominator_shift`` is set, the term is also multiplied
    by ``PropagatorDenominator(q2, 0)^(-rank/2)``, matching Matchete's
    ``Prop[0]^(-rank/2)`` bookkeeping. Actual scalar topology evaluation is
    still owned by the vacuum-integral backend.
    """

    index = s.head("loop_momentum_collect_index_")
    loop_momentum = s.LoopMomentum(index)
    if not bool(expr.matches(loop_momentum)):
        return expr
    momentum_squared = s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared
    collected_terms: list[Expression] = []
    for term in terms(expr.expand()):
        indices, stripped = _extract_loop_momentum_factors(term)
        if not indices:
            collected_terms.append(term)
            continue
        if len(indices) % 2:
            continue
        if is_zero(stripped):
            continue
        marker = s.SymmetricLorentzInds(list_expr(*indices))
        if include_massless_denominator_shift:
            marker *= s.PropagatorDenominator(momentum_squared, Expression.num(0)) ** (-(len(indices) // 2))
        collected_terms.append((marker * stripped).expand())
    return sum_expr(collected_terms).expand()


def _extract_loop_momentum_factors(term: Expression) -> tuple[tuple[Expression, ...], Expression]:
    indices: list[Expression] = []
    remaining_factors: list[Expression] = []
    for factor in factors(term):
        factor_indices = _loop_momentum_factor_indices(factor)
        if factor_indices:
            indices.extend(factor_indices)
        else:
            remaining_factors.append(factor)
    return tuple(indices), product_expr(remaining_factors).expand()


def _loop_momentum_factor_indices(factor: Expression) -> tuple[Expression, ...]:
    if is_head(factor, s.LoopMomentum) and len(factor) == 1:
        return (factor[0],)
    parts = pow_parts(factor)
    if parts is None:
        return ()
    base, exponent = parts
    power = as_int(exponent)
    if power is None or power < 1:
        return ()
    if not is_head(base, s.LoopMomentum) or len(base) != 1:
        return ()
    return tuple(base[0] for _ in range(power))


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


def contract_lorentz_metrics(expr: Expression) -> Expression:
    """Contract top-level Lorentz metric factors into each additive term.

    This mirrors the local part of Matchete's ``ContractMetricSingleTerm``:
    after extracting each top-level ``Metric(a, b)`` factor from a term,
    substitute one metric index by the other when that index appears in the
    remaining term; otherwise keep the metric factor. The input is not
    expanded before contraction, matching Matchete's ordering when metric
    pairings are still hidden inside a product factor. The substitutions
    themselves are native Symbolica replacements, so this also reaches indices
    inside pychete non-commutative chains and derivative slots.
    """

    metric_left = s.head("contract_lorentz_metric_left_")
    metric_right = s.head("contract_lorentz_metric_right_")
    metric_pattern = s.Metric(metric_left, metric_right)
    if not bool(expr.matches(metric_pattern)):
        return expr
    return sum_expr(_contract_lorentz_metrics_single_term(term) for term in terms(expr)).expand()


def lorentz_dimension(*, epsilon: Expression | None = None) -> Expression:
    """Return the dimensional-regularization Lorentz dimension ``4 - 2 eps``."""

    regulator = S("vakint::ε") if epsilon is None else epsilon
    return (Expression.num(4) - 2 * regulator).expand()


def contract_lorentz_metric_traces(
    expr: Expression,
    *,
    epsilon: Expression | None = None,
) -> Expression:
    """Replace closed Lorentz metric traces by ``d = 4 - 2 epsilon``.

    Matchete keeps the epsilon-suppressed part of ``Metric(mu, mu)`` because it
    can multiply a loop pole and contribute to the finite result. The
    replacement is a native Symbolica wildcard rule; Python only checks whether
    the two matched metric slots are identical.
    """

    metric_left = s.head("contract_lorentz_trace_left_")
    metric_right = s.head("contract_lorentz_trace_right_")
    metric_pattern = s.Metric(metric_left, metric_right)
    if not bool(expr.matches(metric_pattern)):
        return expr
    dimension = lorentz_dimension(epsilon=epsilon)

    def replace_trace(match: dict[Expression, Expression]) -> Expression:
        matched = metric_pattern.replace_wildcards(match)
        if bool(match[metric_left] == match[metric_right]):
            return dimension
        return matched

    return expr.replace(metric_pattern, replace_trace, rhs_cache_size=0).expand()


def _contract_lorentz_metrics_single_term(term: Expression) -> Expression:
    metric_pairs: list[tuple[Expression, Expression]] = []
    remaining_factors: list[Expression] = []
    for factor in factors(term):
        if is_head(factor, s.Metric) and len(factor) == 2:
            metric_pairs.append((factor[0], factor[1]))
        else:
            remaining_factors.append(factor)
    if not metric_pairs:
        return term
    out = product_expr(remaining_factors).expand()
    for left, right in metric_pairs:
        replaced_left = out.replace(left, right, rhs_cache_size=0).expand()
        if bool(replaced_left != out):
            out = replaced_left
            continue
        replaced_right = out.replace(right, left, rhs_cache_size=0).expand()
        if bool(replaced_right != out):
            out = replaced_right
        else:
            out = (out * s.Metric(left, right)).expand()
    return out


def evaluate_symmetric_lorentz_indices(
    expr: Expression,
    *,
    evaluate_gamma: bool = True,
    epsilon: Expression | None = None,
    gamma_order: int = 1,
    contract_metrics: bool = True,
) -> Expression:
    """Replace ``SymmetricLorentzInds`` atoms by metric pairings.

    Discovery is delegated to Symbolica wildcard matching. Python only
    enumerates the finite metric pairings for each matched symmetric tensor.
    By default the result is also passed through Matchete-style single-term
    metric contraction, matching ``EvaluateSymmetricLorentzInds``.
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

    replaced = expr.replace(pattern, replace_tensor, rhs_cache_size=0)
    return contract_lorentz_metrics(replaced) if contract_metrics else replaced.expand()


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
    "collect_loop_momenta_to_symmetric_lorentz",
    "contract_lorentz_metric_traces",
    "contract_lorentz_metrics",
    "evaluate_sym_gamma_factors",
    "evaluate_symmetric_lorentz_indices",
    "lorentz_dimension",
    "symmetric_lorentz_gamma_factor",
    "symmetric_lorentz_tensor",
]
