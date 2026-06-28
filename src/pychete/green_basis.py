from __future__ import annotations

from collections.abc import Sequence

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .expr import (
    cg_tensor_pattern,
    covariant_derivative_commutator_pattern,
    factors,
    field_pattern,
    field_strength_pattern,
    is_zero,
    matching_subexpressions,
    product_expr,
    sum_expr,
    terms,
)
from .symbols import canonical_string

_DEFAULT_MAX_GREEN_BASIS_TERMS = 64
_DEFAULT_MAX_GREEN_BASIS_IDENTITIES = 128


def linear_identity_normal_form(
    expr: Expression,
    identities: Sequence[Expression],
    *,
    basis: Sequence[Expression],
    preferred: Sequence[Expression] = (),
    max_basis_terms: int = _DEFAULT_MAX_GREEN_BASIS_TERMS,
    max_identities: int = _DEFAULT_MAX_GREEN_BASIS_IDENTITIES,
) -> Expression:
    """Reduce ``expr`` modulo linear identities in an explicit operator basis.

    Matchete's ``GreensSimplify`` maps operators to a vector space, row-reduces
    identities, and replaces redundant operators by preferred representatives.
    This helper is the bounded pychete boundary for that pattern: callers
    provide an explicit local basis and identities, pychete encodes each basis
    monomial as a temporary Symbolica variable, and Symbolica's native
    ``Expression.solve_linear_system(...)`` solves the linear relations.

    ``preferred`` basis terms are placed at the end of the solver variable
    order, so Symbolica treats them as free variables in underdetermined
    systems where possible. Composite basis monomials are allowed because they
    are encoded before solving and decoded after applying the solution.
    """

    if max_basis_terms < 0:
        raise ValueError("max_basis_terms must be non-negative")
    if max_identities < 0:
        raise ValueError("max_identities must be non-negative")
    basis_terms = _deduplicated_expressions(basis)
    identity_terms = tuple(identity for identity in identities if not is_zero(identity))
    if not basis_terms or not identity_terms:
        return expr
    if len(basis_terms) > max_basis_terms:
        raise ValueError(f"Green-basis reduction received {len(basis_terms)} basis terms")
    if len(identity_terms) > max_identities:
        raise ValueError(f"Green-basis reduction received {len(identity_terms)} identities")

    ordered_basis = _ordered_solver_basis(basis_terms, preferred)
    markers = tuple(
        Expression.symbol(f"pychete::green_basis_marker_{index}") for index, _term in enumerate(ordered_basis)
    )
    imaginary_marker = Expression.symbol("pychete::green_basis_imaginary_unit")
    encode_rules = tuple(
        Replacement(term, marker)
        for term, marker in _sorted_for_encoding(tuple(zip(ordered_basis, markers, strict=True)))
    )
    decode_rules = tuple(Replacement(marker, term) for term, marker in zip(ordered_basis, markers, strict=True))
    encoded_identities = tuple(
        _operator_identity_row(identity.replace_multiple(encode_rules), markers, imaginary_marker=imaginary_marker)
        for identity in identity_terms
    )
    solutions = Expression.solve_linear_system(encoded_identities, markers, warn_if_underdetermined=False)
    solution_rules = tuple(
        Replacement(marker, solution)
        for marker, solution in zip(markers, solutions, strict=True)
        if not is_zero(solution - marker)
    )
    if not solution_rules:
        return expr
    encoded_expr = expr.replace_multiple(encode_rules)
    out = encoded_expr.replace_multiple(solution_rules).replace_multiple(decode_rules)
    return out.replace_multiple((Replacement(imaginary_marker, Expression.I),)).expand()


def linear_identity_basis_terms(
    expressions: Sequence[Expression],
    *,
    max_basis_terms: int = _DEFAULT_MAX_GREEN_BASIS_TERMS,
    operator_patterns: Sequence[Expression] | None = None,
) -> tuple[Expression, ...]:
    """Collect a bounded local operator basis from expressions.

    Matchete first separates coefficients from ``Operator[...]`` objects and
    only maps the operator monomials into the row-reduction vector space. This
    helper performs the corresponding bounded pychete split for local
    Green-basis reductions: expanded additive terms are scanned, scalar
    coefficient factors are discarded, and factors containing registered
    field-like/tensor atoms are kept as the operator monomial.

    The symbolic heavy lifting still happens in Symbolica. This function is
    only local orchestration for building the explicit basis handed to
    :func:`linear_identity_normal_form`.
    """

    if max_basis_terms < 0:
        raise ValueError("max_basis_terms must be non-negative")
    patterns = tuple(operator_patterns) if operator_patterns is not None else _default_operator_patterns()
    out: list[Expression] = []
    seen: set[str] = set()
    for expression in expressions:
        for term in terms(expression.expand()):
            basis_term = _operator_basis_term(term, patterns)
            if basis_term is None or is_zero(basis_term):
                continue
            key = canonical_string(basis_term)
            if key in seen:
                continue
            seen.add(key)
            out.append(basis_term)
            if len(out) > max_basis_terms:
                raise ValueError(f"Green-basis reduction discovered more than {max_basis_terms} basis terms")
    return tuple(out)


def linear_identity_normal_form_from_identities(
    expr: Expression,
    identities: Sequence[Expression],
    *,
    preferred: Sequence[Expression] = (),
    max_basis_terms: int = _DEFAULT_MAX_GREEN_BASIS_TERMS,
    max_identities: int = _DEFAULT_MAX_GREEN_BASIS_IDENTITIES,
    operator_patterns: Sequence[Expression] | None = None,
) -> Expression:
    """Reduce ``expr`` after constructing a local basis from identities.

    This is the next bounded layer toward Matchete's ``GreensSimplify``: the
    caller still chooses the local identity source and preferred
    representatives, but pychete discovers the local operator monomials from
    ``expr`` plus those identities before delegating the solve to Symbolica.
    """

    identity_terms = tuple(identity for identity in identities if not is_zero(identity))
    if not identity_terms:
        return expr
    patterns = tuple(operator_patterns) if operator_patterns is not None else _default_operator_patterns()
    basis = linear_identity_basis_terms(
        (expr, *identity_terms),
        max_basis_terms=max_basis_terms,
        operator_patterns=patterns,
    )
    preferred_terms = _preferred_operator_terms(preferred, patterns)
    return linear_identity_normal_form(
        expr,
        identity_terms,
        basis=basis,
        preferred=preferred_terms,
        max_basis_terms=max_basis_terms,
        max_identities=max_identities,
    )


def _deduplicated_expressions(expressions: Sequence[Expression]) -> tuple[Expression, ...]:
    deduplicated: dict[str, Expression] = {}
    for expression in expressions:
        deduplicated.setdefault(canonical_string(expression), expression)
    return tuple(deduplicated.values())


def _ordered_solver_basis(
    basis: Sequence[Expression],
    preferred: Sequence[Expression],
) -> tuple[Expression, ...]:
    preferred_keys = {canonical_string(term) for term in preferred}
    basis_by_key = {canonical_string(term): term for term in basis}
    missing = preferred_keys - set(basis_by_key)
    if missing:
        raise ValueError(f"preferred Green-basis terms are absent from basis: {sorted(missing)!r}")
    nonpreferred_terms = tuple(term for term in basis if canonical_string(term) not in preferred_keys)
    preferred_terms = tuple(basis_by_key[canonical_string(term)] for term in preferred)
    return (
        *nonpreferred_terms,
        *preferred_terms,
    )


def _sorted_for_encoding(
    replacements: Sequence[tuple[Expression, Expression]],
) -> tuple[tuple[Expression, Expression], ...]:
    return tuple(
        sorted(
            replacements,
            key=lambda replacement: (-replacement[0].get_byte_size(), canonical_string(replacement[0])),
        )
    )


def _operator_identity_row(
    expr: Expression,
    markers: Sequence[Expression],
    *,
    imaginary_marker: Expression,
) -> Expression:
    expanded = expr.expand()
    marker_keys = {canonical_string(marker) for marker in markers}
    row_terms: list[Expression] = []
    leading_coefficient: Expression | None = None
    for term in terms(expanded):
        marker_factor, coefficient = _split_marker_factor(term, marker_keys)
        if marker_factor is None:
            continue
        if leading_coefficient is None:
            leading_coefficient = coefficient
        row_terms.append((coefficient / leading_coefficient) * marker_factor)
    if not row_terms:
        return Expression.num(0)
    return _encode_complex_numeric_coefficients(sum_expr(row_terms), imaginary_marker).expand()


def _split_marker_factor(
    term: Expression,
    marker_keys: set[str],
) -> tuple[Expression | None, Expression]:
    marker: Expression | None = None
    coefficient_factors: list[Expression] = []
    for factor in factors(term):
        if marker is None and canonical_string(factor) in marker_keys:
            marker = factor
        else:
            coefficient_factors.append(factor)
    if marker is None:
        return None, term
    return marker, product_expr(coefficient_factors)


def _encode_complex_numeric_coefficients(expr: Expression, imaginary_marker: Expression) -> Expression:
    encoded_terms: list[Expression] = []
    for term in terms(expr.expand()):
        encoded_terms.append(
            product_expr(_encode_complex_numeric_factor(factor, imaginary_marker) for factor in factors(term))
        )
    return sum_expr(encoded_terms).expand()


def _encode_complex_numeric_factor(factor: Expression, imaginary_marker: Expression) -> Expression:
    if factor.get_type() is not AtomType.Num:
        return factor
    if bool(factor == factor.conj()):
        return factor
    real_part = ((factor + factor.conj()) / Expression.num(2)).expand()
    imaginary_part = ((factor - factor.conj()) / (Expression.num(2) * Expression.I)).expand()
    return (real_part + imaginary_part * imaginary_marker).expand()


def _default_operator_patterns() -> tuple[Expression, ...]:
    return (
        field_pattern(),
        field_strength_pattern(),
        covariant_derivative_commutator_pattern(),
        cg_tensor_pattern(),
    )


def _operator_basis_term(
    term: Expression,
    operator_patterns: Sequence[Expression],
) -> Expression | None:
    operator_factors = tuple(
        factor for factor in factors(term) if _contains_operator_factor(factor, operator_patterns)
    )
    if not operator_factors:
        return None
    return product_expr(operator_factors)


def _contains_operator_factor(
    factor: Expression,
    operator_patterns: Sequence[Expression],
) -> bool:
    return any(matching_subexpressions(factor, pattern) for pattern in operator_patterns)


def _preferred_operator_terms(
    preferred: Sequence[Expression],
    operator_patterns: Sequence[Expression],
) -> tuple[Expression, ...]:
    out: list[Expression] = []
    for expression in preferred:
        expanded_terms = tuple(term for term in terms(expression.expand()) if not is_zero(term))
        if len(expanded_terms) != 1:
            raise ValueError("preferred Green-basis representatives must be single operator terms")
        basis_term = _operator_basis_term(expanded_terms[0], operator_patterns)
        if basis_term is None:
            raise ValueError("preferred Green-basis representative has no operator factors")
        out.append(basis_term)
    return _deduplicated_expressions(out)


__all__ = [
    "linear_identity_basis_terms",
    "linear_identity_normal_form",
    "linear_identity_normal_form_from_identities",
]
