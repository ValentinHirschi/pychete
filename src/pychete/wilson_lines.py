from __future__ import annotations

from collections.abc import Sequence
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
    max_derivative_order: int = 2,
) -> Expression:
    """Expand supported ``WilsonTerm`` atoms in ``expr``.

    This is the first current-Matchete-style Wilson-line expansion boundary.
    It handles the coincidence-limit identity term, the vanishing single
    derivative term, and the two-derivative field-strength term. Higher
    derivative ``WilsonTerm`` atoms are intentionally left formal until the
    derivative-sublist/generator-chain expansion is implemented through the
    idenso/spenso-backed algebra path.
    """

    if max_derivative_order < 0:
        raise ValueError("max_derivative_order must be non-negative")
    theory._validate_registered_expression(expr)
    pattern = wilson_term_pattern()
    if not bool(expr.matches(pattern)):
        return expr

    def replace_wilson_term(match: dict[Expression, Expression]) -> Expression:
        derivative_indices = list_items(match[s.WilsonTermDerivativeIndicesWildcard])
        if len(derivative_indices) > max_derivative_order:
            return pattern.replace_wildcards(match)
        return wilson_term_expansion(
            theory,
            match[s.WilsonTermFieldWildcard],
            match[s.WilsonTermLinkIndicesWildcard],
            derivative_indices,
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

    left_label, right_label = _wilson_link_labels(link_indices)
    conjugated = _is_conjugated_field_label(field)
    field_label = _base_field_label(field, conjugated=conjugated)
    derivative_tuple = tuple(derivative_indices)

    if not derivative_tuple:
        return _wilson_identity_factor(field_label, left_label, right_label, conjugated=conjugated)
    if len(derivative_tuple) == 1:
        return Expression.num(0)
    if len(derivative_tuple) != 2:
        return s.WilsonTerm(field, link_indices, list_expr(*derivative_tuple))
    if _is_vector_field_label(field_label):
        return s.WilsonTerm(field, link_indices, list_expr(*derivative_tuple))
    if bool(derivative_tuple[0] == derivative_tuple[1]):
        return Expression.num(0)

    probe = _wilson_probe_field(field_label, right_label)
    probe = s.Bar(probe) if conjugated else probe
    commutator = theory.covariant_derivative_commutator(probe, derivative_tuple[0], derivative_tuple[1])
    matrix_element = _replace_probe_field_by_left_identity(
        commutator,
        field_label,
        left_label,
        conjugated=conjugated,
    )
    return (Expression.num(1) / 2 * matrix_element).expand()


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
