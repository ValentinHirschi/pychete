from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from html import escape

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .expr import factors, is_zero, product_expr, sum_expr, terms
from .green_basis import linear_identity_basis_terms, linear_identity_normal_form_from_identities
from .symbols import canonical_string, display_string, latex_string

_DEFAULT_MAX_EFFECTIVE_COUPLING_BASIS_TERMS = 128
_DEFAULT_MAX_EFFECTIVE_COUPLING_IDENTITIES = 256


@dataclass(frozen=True)
class EffectiveCouplingTarget:
    """Target coefficient and operator pair for effective-coupling mapping."""

    name: str
    variable: Expression
    operator: Expression

    def _repr_html_(self) -> str:
        return (
            f"<code>EffectiveCouplingTarget({escape(self.name)}: "
            f"{escape(display_string(self.variable))})</code>"
        )

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{EffectiveCouplingTarget}}\left({latex_string(self.variable)}\right)$"


def map_effective_couplings(
    input_lagrangian: Expression,
    targets: Iterable[EffectiveCouplingTarget],
    *,
    target_lagrangian: Expression | None = None,
    identities: Sequence[Expression] = (),
    allow_incomplete_target: bool = False,
    max_basis_terms: int = _DEFAULT_MAX_EFFECTIVE_COUPLING_BASIS_TERMS,
    max_identities: int = _DEFAULT_MAX_EFFECTIVE_COUPLING_IDENTITIES,
) -> dict[str, Expression]:
    """Solve target effective couplings from an input and target Lagrangian.

    This is the pychete boundary corresponding to Matchete's
    ``MapEffectiveCouplingsInternal`` idea: construct coefficient equalities
    for a target Lagrangian and delegate the linear solve to Symbolica. The
    optional ``identities`` argument represents already discovered Green-basis,
    Fierz, or operator-basis identities. When supplied, input and target
    Lagrangians are first reduced with
    :func:`linear_identity_normal_form_from_identities`, preferring the target
    operator monomials, before coefficient equalities are formed.
    ``allow_incomplete_target`` is a diagnostic mode for partial integration
    tests: equations that contain none of the requested target variables are
    ignored instead of making the solve inconsistent.
    """

    target_tuple = tuple(targets)
    if not target_tuple:
        return {}
    if max_basis_terms < 0:
        raise ValueError("max_basis_terms must be non-negative")
    if max_identities < 0:
        raise ValueError("max_identities must be non-negative")

    target_expr = (
        sum_expr(target.variable * target.operator for target in target_tuple)
        if target_lagrangian is None
        else target_lagrangian
    )
    input_expr = input_lagrangian.expand()
    target_expr = target_expr.expand()
    identity_tuple = tuple(identity for identity in identities if not is_zero(identity))
    if identity_tuple:
        preferred = tuple(target.operator for target in target_tuple)
        input_expr = linear_identity_normal_form_from_identities(
            input_expr,
            identity_tuple,
            preferred=preferred,
            max_basis_terms=max_basis_terms,
            max_identities=max_identities,
        )
        target_expr = linear_identity_normal_form_from_identities(
            target_expr,
            identity_tuple,
            preferred=preferred,
            max_basis_terms=max_basis_terms,
            max_identities=max_identities,
        )

    lagrangian_difference = (input_expr - target_expr).expand()
    basis = linear_identity_basis_terms(
        (lagrangian_difference, *identity_tuple),
        max_basis_terms=max_basis_terms,
    )
    if not basis:
        if is_zero(lagrangian_difference):
            return {target.name: Expression.num(0) for target in target_tuple}
        raise ValueError("effective-coupling mapping found no operator basis terms")

    markers = tuple(
        Expression.symbol(f"pychete::effective_coupling_operator_marker_{index}")
        for index, _basis_term in enumerate(basis)
    )
    encode_rules = tuple(
        Replacement(term, marker)
        for term, marker in _sorted_for_encoding(tuple(zip(basis, markers, strict=True)))
    )
    encoded_difference = lagrangian_difference.replace_multiple(encode_rules).expand()
    imaginary_marker = Expression.symbol("pychete::effective_coupling_imaginary_unit")
    equations = tuple(
        _encode_complex_numeric_coefficients(coefficient.expand(), imaginary_marker)
        for marker_power, coefficient in encoded_difference.coefficient_list(*markers)
        if not bool(marker_power == Expression.num(1)) and not is_zero(coefficient)
    )
    variables = tuple(target.variable for target in target_tuple)
    if allow_incomplete_target:
        equations = tuple(equation for equation in equations if _contains_any_variable(equation, variables))
    if not equations:
        return {target.name: Expression.num(0) for target in target_tuple}
    solutions = Expression.solve_linear_system(
        equations,
        variables,
        warn_if_underdetermined=False,
    )
    decode_rules = (Replacement(imaginary_marker, Expression.I),)
    return {
        target.name: solution.replace_multiple(decode_rules).expand()
        for target, solution in zip(target_tuple, solutions, strict=True)
    }


def _contains_any_variable(expr: Expression, variables: Sequence[Expression]) -> bool:
    return any(bool(expr.matches(variable)) for variable in variables)


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


def _sorted_for_encoding(
    replacements: Sequence[tuple[Expression, Expression]],
) -> tuple[tuple[Expression, Expression], ...]:
    return tuple(
        sorted(
            replacements,
            key=lambda replacement: (-replacement[0].get_byte_size(), canonical_string(replacement[0])),
        )
    )


__all__ = [
    "EffectiveCouplingTarget",
    "map_effective_couplings",
]
