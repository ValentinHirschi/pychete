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
class CovariantPropagatorExpansionTerm:
    """One term in a covariant propagator expansion.

    ``denominator_power`` is the power of the scalar propagator denominator
    that must be represented in the loop topology. The numerator data is kept
    split so callers can splice ``open_cd_operands`` into a larger
    non-commutative supertrace chain before acting with open derivatives.
    """

    prefactor: Expression
    loop_momentum_numerator: Expression
    open_cd_operands: tuple[Expression, ...]
    denominator_power: int
    loop_momentum_indices: tuple[Expression, ...] = ()

    @property
    def numerator(self) -> Expression:
        """Return the standalone numerator/operator factor for this term."""

        return self.chain_with()

    def chain_with(self, *right_operands: Expression) -> Expression:
        """Return this expansion term spliced before right-side chain operands."""

        chain = _chain_expr(*self.open_cd_operands, *right_operands)
        return (self.prefactor * self.loop_momentum_numerator * chain).expand()

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{CovariantPropagatorTerm}}\left(P^{{-{self.denominator_power}}}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>CovariantPropagatorTerm(denominator_power={self.denominator_power})</code>"


BosonicCovariantPropagatorExpansionTerm = CovariantPropagatorExpansionTerm


def open_covariant_derivative(indices: Expression | Iterable[Expression]) -> Expression:
    """Return an open covariant-derivative operator for CDE chain algebra."""

    if isinstance(indices, Expression):
        index_list = indices if is_head(indices, s.List) else list_expr(indices)
    else:
        index_list = list_expr(*tuple(indices))
    return s.OpenCD(index_list)


def bosonic_covariant_propagator_expansion_terms(
    indices: Iterable[Expression],
) -> tuple[CovariantPropagatorExpansionTerm, ...]:
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
            CovariantPropagatorExpansionTerm(
                prefactor=Expression.num(1),
                loop_momentum_numerator=Expression.num(1),
                open_cd_operands=(),
                denominator_power=1,
                loop_momentum_indices=(),
            ),
        )

    terms: list[CovariantPropagatorExpansionTerm] = []
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
                CovariantPropagatorExpansionTerm(
                    prefactor=prefactor,
                    loop_momentum_numerator=loop_numerator,
                    open_cd_operands=_interleaved_open_cd_operands(
                        single_indices,
                        pair_indices,
                        pair_distribution,
                    ),
                    denominator_power=denominator_power,
                    loop_momentum_indices=single_indices,
                )
            )
    return tuple(terms)


def fermionic_covariant_propagator_expansion_terms(
    mass: Expression,
    indices: Iterable[Expression],
    *,
    slash_index: Expression,
    derivative_index: Expression,
) -> tuple[CovariantPropagatorExpansionTerm, ...]:
    """Return Matchete-style fermion propagator expansion terms.

    This mirrors Matchete's ``PropFermionExpand`` structure:
    ``(slash(k) + M) Helper[n] + i gamma(mu) OpenCD(mu) Helper[n - 1]``.
    ``slash_index`` and ``derivative_index`` are theory-owned generated
    Lorentz indices supplied by the caller so public expressions keep pychete
    index metadata instead of backend-local placeholders.
    """

    index_tuple = tuple(indices)
    terms: list[CovariantPropagatorExpansionTerm] = []
    for helper in _fermionic_propagator_helper_terms(index_tuple):
        terms.append(
            CovariantPropagatorExpansionTerm(
                prefactor=(mass * helper.prefactor).expand(),
                loop_momentum_numerator=helper.loop_momentum_numerator,
                open_cd_operands=helper.open_cd_operands,
                denominator_power=helper.denominator_power,
                loop_momentum_indices=helper.loop_momentum_indices,
            )
        )
        terms.append(
            CovariantPropagatorExpansionTerm(
                prefactor=helper.prefactor,
                loop_momentum_numerator=(s.LoopMomentum(slash_index) * helper.loop_momentum_numerator).expand(),
                open_cd_operands=(s.DiracProduct(s.Gamma(slash_index)), *helper.open_cd_operands),
                denominator_power=helper.denominator_power,
                loop_momentum_indices=(slash_index, *helper.loop_momentum_indices),
            )
        )
    previous_helper_terms = () if not index_tuple else _fermionic_propagator_helper_terms(index_tuple[:-1])
    for helper in previous_helper_terms:
        terms.append(
            CovariantPropagatorExpansionTerm(
                prefactor=(Expression.I * helper.prefactor).expand(),
                loop_momentum_numerator=helper.loop_momentum_numerator,
                open_cd_operands=(
                    s.DiracProduct(s.Gamma(derivative_index)),
                    open_covariant_derivative(derivative_index),
                    *helper.open_cd_operands,
                ),
                denominator_power=helper.denominator_power,
                loop_momentum_indices=helper.loop_momentum_indices,
            )
        )
    return tuple(term for term in terms if not is_zero(term.prefactor))


def _fermionic_propagator_helper_terms(
    indices: tuple[Expression, ...],
) -> tuple[CovariantPropagatorExpansionTerm, ...]:
    order = len(indices)
    if order == 0:
        return (
            CovariantPropagatorExpansionTerm(
                prefactor=Expression.num(1),
                loop_momentum_numerator=Expression.num(1),
                open_cd_operands=(),
                denominator_power=1,
                loop_momentum_indices=(),
            ),
        )

    terms: list[CovariantPropagatorExpansionTerm] = []
    for pair_count in range(0, order // 2 + 1):
        single_count = order - 2 * pair_count
        single_indices = indices[:single_count]
        pair_indices = indices[single_count : single_count + 2 * pair_count]
        prefactor = (Expression.num(-1) * Expression.I) ** order
        prefactor *= (Expression.num(-1) ** pair_count) * (Expression.num(2) ** single_count)
        loop_numerator = product_expr(s.LoopMomentum(index) for index in single_indices)
        denominator_power = order + 1 - pair_count
        for pair_distribution in _integer_sets(pair_count, single_count + 1):
            terms.append(
                CovariantPropagatorExpansionTerm(
                    prefactor=prefactor,
                    loop_momentum_numerator=loop_numerator,
                    open_cd_operands=_interleaved_fermion_open_cd_operands(
                        single_indices,
                        pair_indices,
                        pair_distribution,
                    ),
                    denominator_power=denominator_power,
                    loop_momentum_indices=single_indices,
                )
            )
    return tuple(terms)


def act_with_open_covariant_derivatives(
    expr: Expression,
    *,
    cyclic: bool = False,
    max_chain_arity: int = _MAX_OPEN_CD_CHAIN_ARITY,
    max_passes: int = 16,
) -> Expression:
    """Apply open CDE covariant derivatives inside bounded ``NCM`` chains.

    This mirrors Matchete's ``ActWithOpenCDs`` semantics for the pychete
    representation: the rightmost ``OpenCD`` in an ``NCM`` chain acts on every
    factor to its right, using :func:`pychete.functional.apply_cd` for the
    actual symbolic derivative. When ``cyclic`` is enabled, the right side is
    interpreted in the closed-supertrace sense and wraps around to the
    beginning of the chain. Bounded-arity Symbolica replacement rules find
    chains natively; Python only orchestrates one matched chain at a time.
    """

    if max_chain_arity < 1:
        raise ValueError("max_chain_arity must be positive")
    if max_passes < 0:
        raise ValueError("max_passes must be non-negative")
    if not bool(expr.matches(s.OpenCD(s.OpenCDIndicesWildcard))):
        return expr

    replacements = _open_cd_chain_replacements(max_chain_arity, cyclic)
    out = expr
    for _ in range(max_passes):
        updated = out.replace_multiple(replacements).expand()
        if bool(updated == out):
            return updated
        out = updated
    return out


@cache
def _open_cd_chain_replacements(max_chain_arity: int, cyclic: bool) -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, max_chain_arity + 1):
        wildcards = _chain_wildcards(arity)
        pattern = s.NCM(*wildcards)
        replacements.append(
            Replacement(
                pattern,
                _open_cd_chain_replacement(pattern, wildcards, cyclic=cyclic),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _open_cd_chain_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
    *,
    cyclic: bool,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_chain(match: dict[Expression, Expression]) -> Expression:
        operands = tuple(match[wildcard] for wildcard in wildcards)
        if not any(_is_open_cd(operand) for operand in operands):
            return pattern.replace_wildcards(match)
        return _act_rightmost_open_cd(operands, cyclic=cyclic)

    return replace_chain


def _act_rightmost_open_cd(operands: tuple[Expression, ...], *, cyclic: bool) -> Expression:
    open_position = max(index for index, operand in enumerate(operands) if _is_open_cd(operand))
    open_cd = operands[open_position]
    remaining = (*operands[:open_position], *operands[open_position + 1 :])
    action_positions = tuple(range(open_position + 1, len(operands)))
    if cyclic:
        action_positions = (*action_positions, *range(0, open_position))
    if not action_positions:
        return Expression.num(0)
    indices = list_items(open_cd[0])
    terms: list[Expression] = []
    for operand_position in action_positions:
        factor = operands[operand_position]
        derivative = apply_cd(indices, factor)
        if is_zero(derivative):
            continue
        remaining_position = operand_position if operand_position < open_position else operand_position - 1
        varied_remaining = (
            *remaining[:remaining_position],
            derivative,
            *remaining[remaining_position + 1 :],
        )
        terms.append(_chain_expr(*varied_remaining))
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


def _interleaved_fermion_open_cd_operands(
    single_indices: tuple[Expression, ...],
    pair_indices: tuple[Expression, ...],
    pair_distribution: tuple[int, ...],
) -> tuple[Expression, ...]:
    pair_position = 0
    operands: list[Expression] = []
    pair_blocks = tuple(
        (
            s.DiracProduct(s.Gamma(pair_indices[index])),
            open_covariant_derivative(pair_indices[index]),
            s.DiracProduct(s.Gamma(pair_indices[index + 1])),
            open_covariant_derivative(pair_indices[index + 1]),
        )
        for index in range(0, len(pair_indices), 2)
    )
    for slot, pair_count in enumerate(pair_distribution):
        for block in pair_blocks[pair_position : pair_position + pair_count]:
            operands.extend(block)
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
    "CovariantPropagatorExpansionTerm",
    "act_with_open_covariant_derivatives",
    "bosonic_covariant_propagator_expansion_terms",
    "fermionic_covariant_propagator_expansion_terms",
    "open_covariant_derivative",
]
