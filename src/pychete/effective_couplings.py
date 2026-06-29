from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from html import escape

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .backends import idenso
from .expr import factors, is_head, is_zero, list_items, product_expr, sum_expr, terms
from .green_basis import linear_identity_basis_terms, linear_identity_normal_form_from_identities
from .indices import IndexInfo, collect_indices
from .symbols import SymbolDataKey, canonical_string, display_string, latex_string, s, safe_symbol_name, symbol_data

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
    input_expr = idenso.simplify_pychete_chiral_scalar_projectors(input_expr)
    target_expr = idenso.simplify_pychete_chiral_scalar_projectors(target_expr)
    identity_tuple = tuple(idenso.simplify_pychete_chiral_scalar_projectors(identity) for identity in identity_tuple)
    input_expr = idenso.canonicalize_builtin_epsilon_cg_tensors(input_expr)
    target_expr = idenso.canonicalize_builtin_epsilon_cg_tensors(target_expr)
    identity_tuple = tuple(idenso.canonicalize_builtin_epsilon_cg_tensors(identity) for identity in identity_tuple)
    input_expr = _align_target_operator_indices(input_expr, target_tuple)
    target_expr = _align_target_operator_indices(target_expr, target_tuple)
    identity_tuple = tuple(_align_target_operator_indices(identity, target_tuple) for identity in identity_tuple)
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


def _align_target_operator_indices(
    expr: Expression,
    targets: Sequence[EffectiveCouplingTarget],
) -> Expression:
    replacements = tuple(
        replacement
        for target in targets
        for replacement in _target_operator_alignment_replacements(target)
    )
    if not replacements:
        return expr
    aligned_terms = tuple(_align_target_operator_indices_term(term, targets, replacements) for term in terms(expr.expand()))
    return sum_expr(aligned_terms).expand()


def _align_target_operator_indices_term(
    term: Expression,
    targets: Sequence[EffectiveCouplingTarget],
    replacements: Sequence[Replacement],
) -> Expression:
    aligned = term.replace_multiple(replacements).expand()
    if not bool(aligned == term):
        return aligned
    for target in targets:
        for pattern_operator, alias_operator, alias_sign, wildcards in _target_operator_alignment_operator_patterns(target):
            for match in term.match(pattern_operator):
                index_replacements = _target_operator_index_replacements(match, wildcards)
                relabeled = term.replace_multiple(index_replacements).expand()
                updated = relabeled.replace(
                    alias_operator,
                    Expression.num(alias_sign) * target.operator,
                ).expand()
                if not bool(updated == term):
                    return updated
    return term


def _target_operator_alignment_replacements(target: EffectiveCouplingTarget) -> tuple[Replacement, ...]:
    operator_terms = terms(target.operator.expand())
    if len(operator_terms) != 1:
        return ()
    index_infos = collect_indices(target.operator)
    if not index_infos:
        return ()
    aliases = _epsilon_orientation_aliases(target.operator)
    safe_target_name = safe_symbol_name(target.name)
    replacements: list[Replacement] = []
    for alias_position, (alias_operator, alias_sign) in enumerate(aliases):
        coefficient = Expression.symbol(
            f"pychete::effective_coupling_coefficient_{safe_target_name}_{alias_position}_"
        )
        pattern_operator, _alias_operator, _alias_sign, wildcards = _target_operator_alignment_operator_pattern(
            alias_operator,
            alias_sign,
            index_infos,
            safe_target_name=safe_target_name,
            alias_position=alias_position,
        )
        pattern = coefficient * pattern_operator
        replacements.append(
            Replacement(
                pattern,
                _target_operator_alignment_replacement(pattern, coefficient, target, wildcards, alias_sign),
                partial=False,
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _target_operator_alignment_operator_patterns(
    target: EffectiveCouplingTarget,
) -> tuple[tuple[Expression, Expression, int, tuple[tuple[IndexInfo, Expression], ...]], ...]:
    operator_terms = terms(target.operator.expand())
    if len(operator_terms) != 1:
        return ()
    index_infos = collect_indices(target.operator)
    if not index_infos:
        return ()
    safe_target_name = safe_symbol_name(target.name)
    return tuple(
        _target_operator_alignment_operator_pattern(
            alias_operator,
            alias_sign,
            index_infos,
            safe_target_name=safe_target_name,
            alias_position=alias_position,
        )
        for alias_position, (alias_operator, alias_sign) in enumerate(_epsilon_orientation_aliases(target.operator))
    )


def _target_operator_alignment_operator_pattern(
    alias_operator: Expression,
    alias_sign: int,
    index_infos: Sequence[IndexInfo],
    *,
    safe_target_name: str,
    alias_position: int,
) -> tuple[Expression, Expression, int, tuple[tuple[IndexInfo, Expression], ...]]:
    wildcards = tuple(
        (
            info,
            Expression.symbol(f"pychete::effective_coupling_index_{safe_target_name}_{alias_position}_{position}_"),
        )
        for position, info in enumerate(index_infos)
    )
    pattern_operator = alias_operator
    for info, wildcard in wildcards:
        pattern_operator = pattern_operator.replace(
            info.expr,
            s.Index(wildcard, info.representation),
            allow_new_wildcards_on_rhs=True,
        )
    return pattern_operator, alias_operator, alias_sign, wildcards


def _epsilon_orientation_aliases(expr: Expression) -> tuple[tuple[Expression, int], ...]:
    aliases: dict[str, tuple[Expression, int]] = {canonical_string(expr): (expr, 1)}
    for epsilon in _rank_two_builtin_epsilon_atoms(expr):
        left, right = list_items(epsilon[1])
        swapped = s.CG(epsilon[0], s.List(right, left))
        next_aliases = dict(aliases)
        for alias_expr, alias_sign in aliases.values():
            swapped_alias = alias_expr.replace(epsilon, swapped)
            next_aliases.setdefault(canonical_string(swapped_alias), (swapped_alias, -alias_sign))
        aliases = next_aliases
    return tuple(aliases.values())


def _rank_two_builtin_epsilon_atoms(expr: Expression) -> tuple[Expression, ...]:
    label = s.head("effective_coupling_epsilon_label_")
    left = s.head("effective_coupling_epsilon_left_")
    right = s.head("effective_coupling_epsilon_right_")
    pattern = s.CG(label, s.List(left, right))
    out: list[Expression] = []
    seen: set[str] = set()
    for match in expr.match(pattern):
        matched_label = match[label]
        source = symbol_data(matched_label, SymbolDataKey.CG_SOURCE, "")
        representations = symbol_data(matched_label, SymbolDataKey.CG_REPRESENTATIONS, [])
        if source != "builtin:eps" or not isinstance(representations, list) or len(representations) != 2:
            continue
        atom = pattern.replace_wildcards(match)
        key = canonical_string(atom)
        if key not in seen:
            seen.add(key)
            out.append(atom)
    return tuple(out)


def _target_operator_alignment_replacement(
    pattern: Expression,
    coefficient_wildcard: Expression,
    target: EffectiveCouplingTarget,
    wildcards: Sequence[tuple[IndexInfo, Expression]],
    alias_sign: int,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_term(match: dict[Expression, Expression]) -> Expression:
        coefficient = match[coefficient_wildcard]
        replacements = _target_operator_index_replacements(match, wildcards)
        return (Expression.num(alias_sign) * coefficient.replace_multiple(replacements) * target.operator).expand()

    return replace_term


def _target_operator_index_replacements(
    match: dict[Expression, Expression],
    wildcards: Sequence[tuple[IndexInfo, Expression]],
) -> list[Replacement]:
    replacements: list[Replacement] = []
    for info, wildcard in wildcards:
        matched = match.get(wildcard)
        if matched is None:
            continue
        replacements.append(Replacement(_matched_index_expr(matched, info.representation), info.expr))
    return replacements


def _matched_index_expr(matched: Expression, representation: Expression) -> Expression:
    return matched if is_head(matched, s.Index) else s.Index(matched, representation)


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
