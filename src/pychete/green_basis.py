from __future__ import annotations

from collections.abc import Sequence

from symbolica import Expression, Replacement

from .expr import is_zero
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
    encode_rules = tuple(
        Replacement(term, marker)
        for term, marker in _sorted_for_encoding(tuple(zip(ordered_basis, markers, strict=True)))
    )
    decode_rules = tuple(Replacement(marker, term) for term, marker in zip(ordered_basis, markers, strict=True))
    encoded_identities = tuple(identity.replace_multiple(encode_rules).expand() for identity in identity_terms)
    solutions = Expression.solve_linear_system(encoded_identities, markers, warn_if_underdetermined=False)
    solution_rules = tuple(
        Replacement(marker, solution)
        for marker, solution in zip(markers, solutions, strict=True)
        if not is_zero(solution - marker)
    )
    if not solution_rules:
        return expr
    encoded_expr = expr.replace_multiple(encode_rules)
    return encoded_expr.replace_multiple(solution_rules).replace_multiple(decode_rules).expand()


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


__all__ = ["linear_identity_normal_form"]
