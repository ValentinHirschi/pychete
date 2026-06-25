from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import cache

from symbolica import Expression, Replacement

from .expr import is_head, is_zero, list_expr, list_items, product_expr, sum_expr
from .functional import apply_cd
from .symbols import s

_MAX_OPEN_CD_CHAIN_ARITY = 8


@dataclass(frozen=True)
class BosonicCovariantPropagatorExpansionTerm:
    """One term in a bosonic CDE propagator expansion.

    ``denominator_power`` is the power of the scalar propagator denominator
    that must be represented in the loop topology. The numerator data is kept
    split so callers can splice ``open_cd_operands`` into a larger
    non-commutative supertrace chain before acting with open derivatives.
    """

    prefactor: Expression
    loop_momentum_numerator: Expression
    open_cd_operands: tuple[Expression, ...]
    denominator_power: int

    @property
    def numerator(self) -> Expression:
        """Return the standalone numerator/operator factor for this term."""

        return self.chain_with()

    def chain_with(self, *right_operands: Expression) -> Expression:
        """Return this expansion term spliced before right-side chain operands."""

        chain = _chain_expr(*self.open_cd_operands, *right_operands)
        return (self.prefactor * self.loop_momentum_numerator * chain).expand()

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{BosonicCDEPropagatorTerm}}\left(P^{{-{self.denominator_power}}}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>BosonicCDEPropagatorTerm(denominator_power={self.denominator_power})</code>"


def open_covariant_derivative(indices: Expression | Iterable[Expression]) -> Expression:
    """Return an open covariant-derivative operator for CDE chain algebra."""

    if isinstance(indices, Expression):
        index_list = indices if is_head(indices, s.List) else list_expr(indices)
    else:
        index_list = list_expr(*tuple(indices))
    return s.OpenCD(index_list)


def bosonic_covariant_propagator_expansion_terms(
    indices: Iterable[Expression],
) -> tuple[BosonicCovariantPropagatorExpansionTerm, ...]:
    """Return Matchete-style bosonic covariant propagator expansion terms.

    The input indices label the CDE expansion order. For order ``n``, this
    mirrors Matchete's ``PropBosonExpand`` numerator structure for
    ``[(q + P)^2 - M^2]^-1``: loop momenta and open covariant derivatives are
    emitted, while the scalar denominator power is carried separately in each
    returned term for later topology construction.
    """

    index_tuple = tuple(indices)
    order = len(index_tuple)
    if order == 0:
        return (
            BosonicCovariantPropagatorExpansionTerm(
                prefactor=Expression.num(1),
                loop_momentum_numerator=Expression.num(1),
                open_cd_operands=(),
                denominator_power=1,
            ),
        )

    terms: list[BosonicCovariantPropagatorExpansionTerm] = []
    for pair_count in range(0, order // 2 + 1):
        single_count = order - 2 * pair_count
        single_indices = index_tuple[:single_count]
        pair_indices = index_tuple[single_count : single_count + pair_count]
        prefactor = (Expression.num(-1) * Expression.I) ** order
        prefactor *= (Expression.num(-1) ** pair_count) * (Expression.num(2) ** single_count)
        loop_numerator = product_expr(s.LoopMomentum(index) for index in single_indices)
        denominator_power = order + 1 - pair_count
        for pair_distribution in _integer_sets(pair_count, single_count + 1):
            terms.append(
                BosonicCovariantPropagatorExpansionTerm(
                    prefactor=prefactor,
                    loop_momentum_numerator=loop_numerator,
                    open_cd_operands=_interleaved_open_cd_operands(
                        single_indices,
                        pair_indices,
                        pair_distribution,
                    ),
                    denominator_power=denominator_power,
                )
            )
    return tuple(terms)


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


@cache
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


def _interleaved_open_cd_operands(
    single_indices: tuple[Expression, ...],
    pair_indices: tuple[Expression, ...],
    pair_distribution: tuple[int, ...],
) -> tuple[Expression, ...]:
    pair_position = 0
    operands: list[Expression] = []
    for slot, pair_count in enumerate(pair_distribution):
        for pair_index in pair_indices[pair_position : pair_position + pair_count]:
            operands.extend((open_covariant_derivative(pair_index), open_covariant_derivative(pair_index)))
        pair_position += pair_count
        if slot < len(single_indices):
            operands.append(open_covariant_derivative(single_indices[slot]))
    return tuple(operands)


@cache
def _integer_sets(total: int, slots: int) -> tuple[tuple[int, ...], ...]:
    if total < 0:
        raise ValueError("total must be non-negative")
    if slots < 1:
        raise ValueError("slots must be positive")
    if slots == 1:
        return ((total,),)
    out: list[tuple[int, ...]] = []
    for first in range(total + 1):
        out.extend((first, *tail) for tail in _integer_sets(total - first, slots - 1))
    return tuple(out)


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


__all__ = [
    "BosonicCovariantPropagatorExpansionTerm",
    "act_with_open_covariant_derivatives",
    "bosonic_covariant_propagator_expansion_terms",
    "open_covariant_derivative",
]
