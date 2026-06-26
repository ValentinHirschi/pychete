from __future__ import annotations

from collections.abc import Iterator, Sequence
from functools import cache
from itertools import combinations, count, permutations
from typing import TYPE_CHECKING

from symbolica import Expression

from .expr import is_head, list_expr, list_items, product_expr, wilson_term_pattern
from .noncommutative import scalarize_commutative_ncm_chains
from .symbols import s
from .theory_metadata import field_indices_from_label, field_type_from_label

if TYPE_CHECKING:
    from .theory import Theory


def expand_wilson_terms(
    theory: Theory,
    expr: Expression,
    *,
    max_derivative_order: int = 4,
) -> Expression:
    """Expand supported ``WilsonTerm`` atoms in ``expr``.

    This is the first current-Matchete-style Wilson-line expansion boundary.
    It handles the coincidence-limit identity term, the vanishing single
    derivative term, and Matchete-style derivative-sublist expansions up to
    ``max_derivative_order``. Larger ``WilsonTerm`` atoms are intentionally
    left formal so users can opt into higher combinatoric cost deliberately.
    """

    if max_derivative_order < 0:
        raise ValueError("max_derivative_order must be non-negative")
    theory._validate_registered_expression(expr)
    pattern = wilson_term_pattern()
    if not bool(expr.matches(pattern)):
        return expr
    index_counter = count()

    def replace_wilson_term(match: dict[Expression, Expression]) -> Expression:
        derivative_indices = list_items(match[s.WilsonTermDerivativeIndicesWildcard])
        if len(derivative_indices) > max_derivative_order:
            return pattern.replace_wildcards(match)
        return _wilson_term_expansion(
            theory,
            match[s.WilsonTermFieldWildcard],
            match[s.WilsonTermLinkIndicesWildcard],
            derivative_indices,
            index_counter=index_counter,
        )

    return scalarize_commutative_ncm_chains(
        expr.replace(pattern, replace_wilson_term, rhs_cache_size=0).expand()
    )


def wilson_term_expansion(
    theory: Theory,
    field: Expression,
    link_indices: Expression,
    derivative_indices: Sequence[Expression],
) -> Expression:
    """Return the supported coincidence-limit expansion of one ``WilsonTerm``."""

    return _wilson_term_expansion(
        theory,
        field,
        link_indices,
        derivative_indices,
        index_counter=count(),
    )


def _wilson_term_expansion(
    theory: Theory,
    field: Expression,
    link_indices: Expression,
    derivative_indices: Sequence[Expression],
    *,
    index_counter: Iterator[int],
) -> Expression:
    left_label, right_label = _wilson_link_labels(link_indices)
    conjugated = _is_conjugated_field_label(field)
    field_label = _base_field_label(field, conjugated=conjugated)
    derivative_tuple = tuple(derivative_indices)

    if not derivative_tuple:
        return _wilson_identity_factor(field_label, left_label, right_label, conjugated=conjugated)
    if len(derivative_tuple) == 1:
        return Expression.num(0)
    if _is_vector_field_label(field_label):
        return s.WilsonTerm(field, link_indices, list_expr(*derivative_tuple))
    terms: list[Expression] = []
    for partition in _wilson_derivative_partitions(derivative_tuple):
        term = _wilson_partition_expansion(
            theory,
            field_label,
            left_label,
            right_label,
            partition,
            conjugated=conjugated,
            index_counter=index_counter,
        )
        if not bool(term == Expression.num(0)):
            terms.append(term)
    if not terms:
        return Expression.num(0)
    return sum(terms, Expression.num(0)).expand()


def _wilson_link_labels(link_indices: Expression) -> tuple[Expression, Expression]:
    items = list_items(link_indices)
    if len(items) != 2:
        raise ValueError("WilsonTerm link-indices argument must contain exactly two endpoints")
    return (_endpoint_label(items[0]), _endpoint_label(items[1]))


def _endpoint_label(endpoint: Expression) -> Expression:
    if is_head(endpoint, s.Index):
        if len(endpoint) != 2:
            raise ValueError("Index endpoint must have label and representation")
        return endpoint[0]
    return endpoint


def _is_conjugated_field_label(field: Expression) -> bool:
    return is_head(field, s.Bar) and len(field) == 1


def _base_field_label(field: Expression, *, conjugated: bool) -> Expression:
    return field[0] if conjugated else field


def _wilson_probe_field(field_label: Expression, right_label: Expression) -> Expression:
    return s.Field(
        field_label,
        field_type_from_label(field_label),
        list_expr(*_endpoint_field_indices(field_label, right_label)),
        list_expr(),
    )


def _endpoint_field_indices(field_label: Expression, endpoint_label: Expression) -> tuple[Expression, ...]:
    return tuple(s.Index(endpoint_label, representation) for representation in field_indices_from_label(field_label))


def _wilson_identity_factor(
    field_label: Expression,
    left_label: Expression,
    right_label: Expression,
    *,
    conjugated: bool,
) -> Expression:
    return _wilson_identity_from_actual_indices(
        field_label,
        left_label,
        _endpoint_field_indices(field_label, right_label),
        right_label=right_label,
        conjugated=conjugated,
    )


def _wilson_identity_from_actual_indices(
    field_label: Expression,
    left_label: Expression,
    actual_indices: Sequence[Expression],
    *,
    right_label: Expression | None = None,
    conjugated: bool,
) -> Expression:
    field_representations = field_indices_from_label(field_label)
    if len(actual_indices) != len(field_representations):
        raise ValueError("WilsonTerm field-index payload does not match registered field metadata")
    factors = [_wilson_vector_lorentz_identity(field_label, left_label, right_label)]
    for representation, actual_index in zip(field_representations, actual_indices, strict=True):
        if not is_head(actual_index, s.Index) or len(actual_index) != 2:
            raise ValueError("WilsonTerm endpoint expansion requires concrete Index arguments")
        if conjugated:
            left_index = s.Index(left_label, s.Bar(representation))
            right_index = s.Index(actual_index[0], representation)
        else:
            left_index = s.Index(left_label, representation)
            right_index = s.Index(actual_index[0], s.Bar(representation))
        factors.append(s.Delta(left_index, right_index))
    return product_expr(factors)


def _wilson_vector_lorentz_identity(
    field_label: Expression,
    left_label: Expression,
    right_label: Expression | None,
) -> Expression:
    if right_label is None:
        return Expression.num(1)
    field_type = field_type_from_label(field_label)
    if is_head(field_type, s.Vector):
        return s.Metric(s.Index(left_label, s.Lorentz), s.Index(right_label, s.Lorentz))
    return Expression.num(1)


def _is_vector_field_label(field_label: Expression) -> bool:
    return is_head(field_type_from_label(field_label), s.Vector)


def _wilson_partition_expansion(
    theory: Theory,
    field_label: Expression,
    left_label: Expression,
    right_label: Expression,
    partition: tuple[tuple[Expression, ...], ...],
    *,
    conjugated: bool,
    index_counter: Iterator[int],
) -> Expression:
    out = _wilson_probe_field(field_label, right_label)
    out = s.Bar(out) if conjugated else out
    for block in reversed(partition):
        out = _apply_wilson_derivative_block(
            theory,
            out,
            field_label,
            block,
            conjugated=conjugated,
            index_counter=index_counter,
        )
        if bool(out == Expression.num(0)):
            return out
    return _replace_probe_field_by_left_identity(
        out,
        field_label,
        left_label,
        conjugated=conjugated,
    )


def _apply_wilson_derivative_block(
    theory: Theory,
    expr: Expression,
    field_label: Expression,
    block: tuple[Expression, ...],
    *,
    conjugated: bool,
    index_counter: Iterator[int],
) -> Expression:
    pattern = s.Field(
        field_label,
        field_type_from_label(field_label),
        s.FieldIndicesWildcard,
        s.List(),
    )
    if conjugated:
        pattern = s.Bar(pattern)

    def replace_field(match: dict[Expression, Expression]) -> Expression:
        atom = pattern.replace_wildcards(match)
        if conjugated:
            atom = atom[0]
        return _wilson_derivative_block_action(
            theory,
            atom,
            block,
            conjugated=conjugated,
            index_counter=index_counter,
        )

    return expr.replace(pattern, replace_field, rhs_cache_size=0).expand()


def _wilson_derivative_block_action(
    theory: Theory,
    base_field: Expression,
    block: tuple[Expression, ...],
    *,
    conjugated: bool,
    index_counter: Iterator[int],
) -> Expression:
    if len(block) < 2:
        return Expression.num(0)
    if len(block) == 2 and bool(block[0] == block[1]):
        return Expression.num(0)

    leading_permutations = tuple(permutations(block[:-1]))
    if not leading_permutations:
        return Expression.num(0)
    prefactor = Expression.num(len(block) - 1) / (Expression.num(len(block)) * Expression.num(len(leading_permutations)))
    terms: list[Expression] = []
    for perm in leading_permutations:
        left_index = perm[-1]
        right_index = block[-1]
        field_strength_derivatives = perm[:-1]
        terms.append(
            prefactor
            * theory._covariant_derivative_commutator(
                base_field,
                left_index,
                right_index,
                conjugate_field=conjugated,
                index_counter=index_counter,
                field_strength_derivatives=field_strength_derivatives,
            )
        )
    return sum(terms, Expression.num(0)).expand()


@cache
def _wilson_derivative_partitions(indices: tuple[Expression, ...]) -> tuple[tuple[tuple[Expression, ...], ...], ...]:
    length = len(indices)
    if length < 2:
        return ()
    if length < 4:
        return ((indices,),)
    out: list[tuple[tuple[Expression, ...], ...]] = []
    positions = tuple(range(length - 1))
    for subset_size in range(2, length - 1):
        for subset in combinations(positions, subset_size):
            subset_set = set(subset)
            first = tuple(indices[position] for position in subset)
            rest = tuple(indices[position] for position in range(length) if position not in subset_set)
            for prefix in _wilson_derivative_partitions(first):
                out.append((*prefix, rest))
    out.append((indices,))
    return tuple(out)


def _replace_probe_field_by_left_identity(
    expr: Expression,
    field_label: Expression,
    left_label: Expression,
    *,
    conjugated: bool,
) -> Expression:
    pattern = s.Field(
        field_label,
        field_type_from_label(field_label),
        s.FieldIndicesWildcard,
        s.List(),
    )
    if conjugated:
        pattern = s.Bar(pattern)

    def replace_probe(match: dict[Expression, Expression]) -> Expression:
        return _wilson_identity_from_actual_indices(
            field_label,
            left_label,
            list_items(match[s.FieldIndicesWildcard]),
            conjugated=conjugated,
        )

    return expr.replace(pattern, replace_probe, rhs_cache_size=0).expand()


__all__ = ["expand_wilson_terms", "wilson_term_expansion"]
