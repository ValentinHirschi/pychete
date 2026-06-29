from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from itertools import count
from typing import Any

from symbolica import Expression, PatternRestriction, Replacement
from symbolica.core import AtomType

from .common import import_backend
from ..expr import (
    args,
    as_int,
    cg_tensor_pattern,
    factors,
    field_strength_pattern,
    field_strength_with_derivatives,
    field_with_derivatives,
    is_head,
    list_items,
    product_expr,
    sum_expr,
    terms,
)
from ..symbols import SymbolDataKey, SymbolRole, canonical_string, expression_from_canonical, s, symbol_data
from ..theory_metadata import FieldChirality, GroupKind, field_chirality_from_label

_MAX_NATIVE_PROJECTOR_POWER = 16
_MAX_NATIVE_DIRAC_WORD_ARITY = 8
_MAX_NCM_POWER_EXPANSION_TOTAL_ARITY = 16
_MAX_NATIVE_COLOR_CHAIN_ARITY = 16


def native_module():
    """Return the native idenso Python module."""

    return import_backend("symbolica.community.idenso")


def cook_function(expr: Expression) -> Expression:
    """Delegate function-symbol flattening to idenso."""

    return native_module().cook_function(expr)


def cook_indices(expr: Expression) -> Expression:
    """Delegate index-symbol flattening to idenso."""

    return native_module().cook_indices(expr)


def dirac_adjoint(expr: Expression) -> Expression:
    """Delegate Dirac-adjoint construction to idenso."""

    return native_module().dirac_adjoint(expr)


def expand_bis(expr: Expression) -> Expression:
    """Delegate bispinor-index expansion to idenso."""

    return native_module().expand_bis(expr)


def expand_color(expr: Expression) -> Expression:
    """Delegate colour-index expansion to idenso."""

    return native_module().expand_color(expr)


def expand_metrics(expr: Expression) -> Expression:
    """Delegate metric-index expansion to idenso."""

    return native_module().expand_metrics(expr)


def expand_mink(expr: Expression) -> Expression:
    """Delegate Minkowski-index expansion to idenso."""

    return native_module().expand_mink(expr)


def expand_mink_bis(expr: Expression) -> Expression:
    """Delegate combined Minkowski and bispinor expansion to idenso."""

    return native_module().expand_mink_bis(expr)


def list_dangling(expr: Expression) -> list[Expression]:
    """Return native idenso dangling-index detection."""

    return native_module().list_dangling(expr)


def simplify_color(expr: Expression) -> Expression:
    """Delegate colour algebra simplification to idenso."""

    return native_module().simplify_color(expr)


@cache
def _delta_pattern() -> Expression:
    return s.Delta(s.head("pychete_any_delta_left_"), s.head("pychete_any_delta_right_"))


@cache
def _native_color_wrapper_patterns() -> tuple[Expression, ...]:
    left = s.head("native_color_wrapper_left_")
    right = s.head("native_color_wrapper_right_")
    first = s.head("native_color_wrapper_first_")
    second = s.head("native_color_wrapper_second_")
    third = s.head("native_color_wrapper_third_")
    chain_left = s.head("native_color_wrapper_chain_left_")
    chain_right = s.head("native_color_wrapper_chain_right_")
    generator = _native_color_symbol("t")
    return (
        _native_color_symbol("g")(left, right),
        generator(first, second, third),
        _native_color_symbol("f")(first, second, third),
        *tuple(
            _native_color_symbol("chain")(
                chain_left,
                chain_right,
                *(
                    generator(
                        s.head(f"native_color_wrapper_chain_adjoint_{arity}_{index}_"),
                        s.head(f"native_color_wrapper_chain_in_{arity}_{index}_"),
                        s.head(f"native_color_wrapper_chain_out_{arity}_{index}_"),
                    )
                    for index in range(arity)
                ),
            )
            for arity in range(1, _MAX_NATIVE_COLOR_CHAIN_ARITY + 1)
        ),
    )


def _contains_delta(expr: Expression) -> bool:
    return bool(expr.matches(_delta_pattern()))


def _contains_cg_tensor(expr: Expression) -> bool:
    return bool(expr.matches(cg_tensor_pattern()))


def _contains_field_strength(expr: Expression) -> bool:
    return bool(expr.matches(field_strength_pattern()))


def _contains_native_color_wrapper(expr: Expression) -> bool:
    if any(expr.contains(_native_color_symbol(name)) for name in ("TR", "CA", "CF", "Nc", "NA")):
        return True
    return any(bool(expr.matches(pattern)) for pattern in _native_color_wrapper_patterns())


def simplify_pychete_color_algebra(
    theory: Any,
    expr: Expression,
    *,
    decode_metrics: bool = True,
    substitute_group_constants: bool = True,
) -> Expression:
    """Simplify registered pychete ``CG`` colour tensors through idenso.

    pychete stores generators and structure constants as theory-owned
    ``CG(label, indices)`` atoms. This adapter lowers compatible built-in
    SU(N) fundamental/adjoint tensors to spenso's native HEP tensor heads,
    delegates the algebra to idenso's Rust-backed ``simplify_color`` routine,
    then decodes simple native metrics and tensor chains back to registered
    pychete CG tensors when the originating group is unambiguous.
    """

    has_delta = _contains_delta(expr)
    has_cg = _contains_cg_tensor(expr)
    if not has_delta and not has_cg:
        return expr
    from . import spenso

    normalized = contract_pychete_deltas(theory, expr) if has_delta else expr
    if not _contains_cg_tensor(normalized):
        return normalized.expand() if has_delta else normalized
    normalized = _replace_adjoint_generators_with_structure_constants(theory, normalized)
    groups = _cg_groups_in_expression(theory, normalized)
    if not groups:
        return normalized.expand()
    lowered = spenso.lower_native_hep_cg_tensors_to_spenso(theory, normalized)
    simplified = simplify_color(lowered).expand()
    if substitute_group_constants:
        simplified = _substitute_native_color_constants(theory, simplified, groups)
    if decode_metrics:
        simplified = _decode_native_color_metrics(theory, simplified, groups)
    simplified = _decode_native_color_tensors(theory, simplified, groups)
    return simplified.expand()


def canonicalize_builtin_epsilon_cg_tensors(expr: Expression) -> Expression:
    """Canonicalize registered rank-two builtin epsilon CG tensors.

    The SU(2) invariant epsilon tensor is antisymmetric. Matchete normalizes
    these CG tensors before basis projection, so ``eps(j, i)`` must be
    available as ``-eps(i, j)`` when a registered operator basis uses the
    opposite slot order. Selection is driven by Symbolica metadata on the CG
    label, not by Wilson-coefficient names.
    """

    if not _contains_cg_tensor(expr):
        return expr
    return expr.replace_multiple(_builtin_epsilon_cg_replacements()).expand()


def decode_native_color_wrappers(
    theory: Any,
    expr: Expression,
    *,
    decode_metrics: bool = True,
    substitute_group_constants: bool = True,
) -> Expression:
    """Decode native spenso/idenso colour wrappers into pychete CG tensors.

    This is intentionally decode-only: it does not call native idenso
    simplifiers over the full expression. Use it for public matching results
    that may contain generated pychete CDE/Lorentz structures alongside native
    colour wrappers.
    """

    if not _contains_native_color_wrapper(expr):
        return expr
    groups = tuple(theory.groups)
    decoded = expr
    if substitute_group_constants:
        decoded = _substitute_native_color_constants(theory, decoded, groups)
    if decode_metrics:
        decoded = _decode_native_color_metrics(theory, decoded, groups)
    return _decode_native_color_tensors(theory, decoded, groups).expand()


@cache
def _pychete_delta_cg_contraction_replacements() -> tuple[Replacement, ...]:
    left_label = s.head("pychete_delta_cg_left_")
    right_label = s.head("pychete_delta_cg_right_")
    representation = s.head("pychete_delta_cg_representation_")
    cg_label = s.head("pychete_delta_cg_label_")
    cg_indices = s.head("pychete_delta_cg_indices_")

    left = s.Index(left_label, representation)
    right_dual = s.Index(right_label, s.Bar(representation))
    left_dual = s.Index(left_label, s.Bar(representation))
    right = s.Index(right_label, representation)
    cg = s.CG(cg_label, cg_indices)
    direct_pattern = s.Delta(left, right_dual) * cg
    conjugate_pattern = s.Delta(left_dual, right) * cg

    def direct_contract(match: dict[Expression, Expression]) -> Expression:
        matched = direct_pattern.replace_wildcards(match)
        contracted = _contract_delta_match_into_cg(
            match,
            cg_label=cg_label,
            cg_indices=cg_indices,
            first_label=left_label,
            second_label=right_label,
            representation=representation,
            direct=True,
        )
        return matched if contracted is None else contracted

    def conjugate_contract(match: dict[Expression, Expression]) -> Expression:
        matched = conjugate_pattern.replace_wildcards(match)
        contracted = _contract_delta_match_into_cg(
            match,
            cg_label=cg_label,
            cg_indices=cg_indices,
            first_label=left_label,
            second_label=right_label,
            representation=representation,
            direct=False,
        )
        return matched if contracted is None else contracted

    return (
        Replacement(
            direct_pattern,
            direct_contract,
            cg_label.req_tag(SymbolRole.CG_TENSOR.value)
            & _delta_cg_contractible_restriction(
                cg_label=cg_label,
                cg_indices=cg_indices,
                first_label=left_label,
                second_label=right_label,
                representation=representation,
                direct=True,
            ),
        ),
        Replacement(
            conjugate_pattern,
            conjugate_contract,
            cg_label.req_tag(SymbolRole.CG_TENSOR.value)
            & _delta_cg_contractible_restriction(
                cg_label=cg_label,
                cg_indices=cg_indices,
                first_label=left_label,
                second_label=right_label,
                representation=representation,
                direct=False,
            ),
        ),
    )


def _delta_cg_contractible_restriction(
    *,
    cg_label: Expression,
    cg_indices: Expression,
    first_label: Expression,
    second_label: Expression,
    representation: Expression,
    direct: bool,
) -> PatternRestriction:
    required = (cg_label, cg_indices, first_label, second_label, representation)

    def contractible(match: dict[Expression, Expression]) -> int:
        if any(wildcard not in match for wildcard in required):
            return 0
        return (
            1
            if _contract_delta_match_into_cg(
                match,
                cg_label=cg_label,
                cg_indices=cg_indices,
                first_label=first_label,
                second_label=second_label,
                representation=representation,
                direct=direct,
            )
            is not None
            else -1
        )

    return PatternRestriction.req_matches(contractible)


def _contract_delta_match_into_cg(
    match: dict[Expression, Expression],
    *,
    cg_label: Expression,
    cg_indices: Expression,
    first_label: Expression,
    second_label: Expression,
    representation: Expression,
    direct: bool,
) -> Expression | None:
    rep = match[representation]
    if direct:
        replacements = (
            (match[second_label], match[first_label], rep),
            (match[first_label], match[second_label], s.Bar(rep)),
        )
    else:
        replacements = (
            (match[first_label], match[second_label], rep),
            (match[second_label], match[first_label], s.Bar(rep)),
        )
    for source_label, target_label, index_representation in replacements:
        updated_indices, changed = _replace_cg_index_label(
            match[cg_indices],
            source_label=source_label,
            target_label=target_label,
            representation=index_representation,
        )
        if changed:
            return s.CG(match[cg_label], updated_indices)
    return None


def _replace_cg_index_label(
    indices_expr: Expression,
    *,
    source_label: Expression,
    target_label: Expression,
    representation: Expression,
) -> tuple[Expression, bool]:
    indices = list_items(indices_expr)
    updated: list[Expression] = []
    changed = False
    for index in indices:
        if is_head(index, s.Index) and bool(index[0] == source_label) and bool(index[1] == representation):
            updated.append(s.Index(target_label, representation))
            changed = True
        else:
            updated.append(index)
    return s.List(*updated), changed


def simplify_gamma(expr: Expression) -> Expression:
    """Delegate gamma-matrix algebra simplification to idenso."""

    return native_module().simplify_gamma(expr)


def simplify_pychete_dirac_projectors(expr: Expression) -> Expression:
    """Simplify pychete projector-only Dirac words through native idenso.

    pychete's public expressions use compact ``s.PR`` and ``s.PL`` symbols,
    while idenso's gamma simplifier expects explicit spenso projector tensors
    with bispinor endpoints. This adapter lowers projector-only words to native
    spenso tensors, delegates simplification to ``idenso.simplify_gamma``, and
    decodes the simple scalar/projector result back to pychete symbols.
    """

    replacements: tuple[tuple[Expression, Expression], ...] = (
        (s.PR * s.PR, _native_projector_word((s.PR, s.PR))),
        (s.PL * s.PL, _native_projector_word((s.PL, s.PL))),
        (s.PR * s.PL, _native_projector_word((s.PR, s.PL))),
        (s.PL * s.PR, _native_projector_word((s.PL, s.PR))),
    )
    out = expr
    for projector, power_replacement in (
        (s.PR, _projector_power_replacement(s.PR)),
        (s.PL, _projector_power_replacement(s.PL)),
    ):
        out = out.replace(projector ** s.PowExponentWildcard, power_replacement)
    for pattern, replacement in replacements:
        out = out.replace(pattern, replacement, repeat=True)
    return out.expand()


def simplify_pychete_dirac_algebra(expr: Expression) -> Expression:
    """Simplify compact pychete Dirac words by delegating to native idenso."""

    out = expand_pychete_ncm_powers(expr)
    out = simplify_pychete_dirac_projectors(out)
    out = out.replace_multiple(_dirac_product_replacements())
    out = out.replace_multiple(_ncm_dirac_word_replacements())
    out = simplify_pychete_open_dirac_chains(out)
    out = simplify_pychete_chiral_scalar_projectors(out)
    out = out.replace_multiple(_mixed_ncm_dirac_subword_replacements())
    return simplify_pychete_dirac_projectors(out).expand()


def trace_pychete_closed_dirac_chains(expr: Expression) -> Expression:
    """Trace closed compact pychete Dirac words through native idenso.

    This is intended for scalar supertrace numerators whose ``NCM`` operands
    are entirely pychete gamma/projector factors or ``DiracProduct`` wrappers.
    Chains containing field endpoints or any other non-Dirac operand are left
    unchanged so open spinor lines are not accidentally closed.
    """

    out = expand_pychete_ncm_powers(expr)
    return out.replace_multiple(_closed_ncm_dirac_trace_replacements()).expand()


def expand_pychete_ncm_powers(expr: Expression) -> Expression:
    """Expand bounded positive integer powers of pychete ``NCM`` chains.

    Symbolica multiplication is commutative, while pychete encodes
    noncommutative chains explicitly with the ``NCM`` head. Generated matrix
    products can still produce powers such as ``NCM(a, b)^2``. Expand those
    powers to ``NCM(a, b, a, b)`` before Dirac/idenso simplification. Symbolic,
    non-positive, or oversized powers are left unchanged.
    """

    return expr.replace_multiple(_ncm_power_replacements()).expand()


def simplify_pychete_open_dirac_chains(expr: Expression) -> Expression:
    """Simplify Dirac words between registered pychete fermion endpoints.

    The endpoint selection is done with Symbolica patterns restricted to
    theory-created field labels. Only the Dirac middle word is lowered to
    native spenso tensors and simplified by idenso; pychete field endpoints
    remain in the public expression representation.
    """

    return expr.replace_multiple(_open_fermion_ncm_dirac_chain_replacements()).expand()


def simplify_pychete_chiral_scalar_projectors(expr: Expression) -> Expression:
    """Normalize scalar chiral projectors in registered open fermion chains.

    Matchete's target SMEFT scalar four-fermion operators omit explicit
    projectors because the fermion fields carry chirality metadata. Generated
    and converted pychete sources can still contain compact
    ``NCM(Bar(psi), DiracProduct(PR|PL), chi)`` chains. This pass uses
    Symbolica replacement rules and field-label symbol data to remove
    projectors that match the right endpoint chirality, or to return zero for
    the opposite chirality. Non-chiral endpoints are left unchanged.
    """

    return expr.replace_multiple(_chiral_scalar_projector_replacements()).expand()


def simplify_metrics(expr: Expression) -> Expression:
    """Delegate metric algebra simplification to idenso."""

    return native_module().simplify_metrics(expr)


def simplify_pychete_loop_momentum_metrics(expr: Expression) -> Expression:
    """Simplify pychete metric/delta contractions of loop-momentum factors."""

    return expr.replace_multiple(_loop_momentum_metric_replacements(), repeat=True).expand()


def simplify_pychete_field_strength_metrics(expr: Expression) -> Expression:
    """Simplify metric contractions and Lorentz antisymmetry of field strengths."""

    result = expr.replace_multiple(_field_strength_lorentz_index_alias_replacements())
    result = result.replace_multiple(_field_strength_metric_index_alias_replacements())
    result = result.replace_multiple(_field_strength_metric_trace_replacements(), repeat=True)
    result = result.replace_multiple(_field_strength_metric_slot_replacements(), repeat=True)
    return result.replace_multiple(_field_strength_lorentz_antisymmetry_replacements()).expand()


def simplify_pychete_field_derivative_metrics(expr: Expression) -> Expression:
    """Contract pychete metrics into field and field-strength derivative slots.

    Vakint tensor reduction emits metric tensors for loop-momentum numerators.
    In Wilson-line expressions those metrics can contract covariant-derivative
    slots on ``Field``/``FieldStrength`` atoms. Keep this normalization as a
    Symbolica replacement pass so only local metric-slot contractions are
    performed here; commutator expansion remains owned by ``Theory``.
    """

    out = expr
    replacements = _field_derivative_metric_slot_replacements()
    for _ in range(16):
        updated = out.replace_multiple(replacements).expand()
        if bool(updated == out):
            return updated
        out = updated
    return out


def simplify_su2_field_strength_generator_bilinears(theory: Any, expr: Expression) -> Expression:
    """Project symmetric SU(2) field-strength generator bilinears to singlets.

    Wilson-line and legacy CDE commutator expansions can generate fundamental
    bilinears of the form
    ``Bar(phi_j) phi_i T^A_{i k} T^B_{k j} F^A F^B``. For SU(2), a symmetric
    adjoint field-strength pair projects onto the singlet with a coefficient
    fixed by native idenso colour traces. This helper keeps the match in
    Symbolica replacement rules and delegates the group coefficient to idenso
    instead of hard-coding generator algebra in projection code.
    """

    result = expr
    for group in theory.groups:
        coefficient = _su2_field_strength_generator_bilinear_coefficient(theory, group)
        if coefficient is None:
            continue
        replacements = _su2_field_strength_generator_bilinear_replacements(theory, group, coefficient)
        if not replacements:
            continue
        result = _replace_candidate_terms(
            result,
            replacements,
            candidate=_su2_field_strength_generator_bilinear_candidate(theory, group),
            repeat=False,
        )
    return result


def simplify_su2_u1_field_strength_generator_bilinears(theory: Any, expr: Expression) -> Expression:
    """Canonicalize mixed SU(2)-U(1) fundamental field-strength bilinears.

    Generated sources can emit terms proportional to
    ``phi_i Bar(phi_j) T^A_{i j} F^A B``. Registered operator-basis metadata may
    choose the conjugate-first orientation
    ``Bar(phi_i) T^A_{i j} phi_j F^A B``. This helper rewrites the generated
    source orientation into that generic registered-target orientation with
    Symbolica replacement rules; the U(1) charge and coupling factors remain
    in the surrounding coefficient.
    """

    result = expr
    for su2_group in theory.groups:
        if _su_group_size(theory, su2_group) != 2:
            continue
        su2_symbol = theory.symbol(su2_group, role=SymbolRole.GROUP)
        su2_kind = GroupKind.from_user(
            str(symbol_data(su2_symbol, SymbolDataKey.GROUP_KIND, GroupKind.GLOBAL.value))
        )
        if su2_kind is not GroupKind.GAUGE or bool(
            symbol_data(su2_symbol, SymbolDataKey.GROUP_ABELIAN, 0)
        ):
            continue
        for u1_group in theory.groups:
            u1_symbol = theory.symbol(u1_group, role=SymbolRole.GROUP)
            u1_kind = GroupKind.from_user(
                str(symbol_data(u1_symbol, SymbolDataKey.GROUP_KIND, GroupKind.GLOBAL.value))
            )
            if u1_kind is not GroupKind.GAUGE or not bool(
                symbol_data(u1_symbol, SymbolDataKey.GROUP_ABELIAN, 0)
            ):
                continue
            replacements = _su2_u1_field_strength_generator_bilinear_replacements(
                theory,
                su2_group,
                u1_group,
            )
            if not replacements:
                continue
            result = _replace_candidate_terms(
                result,
                replacements,
                candidate=_su2_u1_field_strength_generator_bilinear_candidate(
                    theory,
                    su2_group,
                    u1_group,
                ),
                repeat=False,
            ).expand()
    return result


def simplify_pychete_field_strength_group_algebra(theory: Any, expr: Expression) -> Expression:
    """Simplify pychete field-strength metric and supported group bilinears.

    This is the public backend boundary for generated CDE/Wilson-line results
    that already use pychete ``FieldStrength``/``CG`` atoms. Lorentz metric
    identities are applied first, then the supported SU(2) and mixed SU(2)-U(1)
    field-strength generator bilinears are normalized with Symbolica
    replacement rules backed by idenso colour traces.
    """

    has_delta = _contains_delta(expr)
    has_cg = _contains_cg_tensor(expr)
    has_field_strength = _contains_field_strength(expr)
    if not has_delta and not has_cg and not has_field_strength:
        return expr
    result = simplify_pychete_field_derivative_metrics(expr) if has_field_strength else expr
    if has_delta:
        result = contract_pychete_deltas(theory, result)
    if has_field_strength:
        result = simplify_pychete_field_strength_metrics(result)
    if has_field_strength and has_cg:
        result = simplify_su2_field_strength_generator_bilinears(theory, result)
        result = simplify_su2_u1_field_strength_generator_bilinears(theory, result)
    return contract_pychete_deltas(theory, result) if _contains_delta(result) else result


def _replace_candidate_terms(
    expr: Expression,
    replacements: tuple[Replacement, ...],
    *,
    candidate: Callable[[Expression], bool],
    repeat: bool,
) -> Expression:
    changed = False
    updated_terms: list[Expression] = []
    for term in terms(expr):
        if not candidate(term):
            updated_terms.append(term)
            continue
        updated = term.replace_multiple(replacements, repeat=repeat).expand()
        changed = changed or not bool(updated == term)
        updated_terms.append(updated)
    return sum_expr(updated_terms).expand() if changed else expr


def _su2_field_strength_generator_bilinear_candidate(theory: Any, group: str) -> Callable[[Expression], bool]:
    group_symbol = theory.symbol(group, role=SymbolRole.GROUP)
    vector_name = symbol_data(group_symbol, SymbolDataKey.GROUP_FIELD)
    generator_name = f"gen_{group}_fund"
    if not isinstance(vector_name, str) or vector_name not in theory.fields or generator_name not in theory.cg_tensors:
        return lambda _term: False
    generator_pattern = cg_tensor_pattern(theory.cg_tensors[generator_name].label)
    strength_pattern = field_strength_pattern(theory.fields[vector_name].label)

    def candidate(term: Expression) -> bool:
        return _has_at_least_matches(term, generator_pattern, 2) and _has_at_least_matches(term, strength_pattern, 2)

    return candidate


def _su2_u1_field_strength_generator_bilinear_candidate(
    theory: Any,
    su2_group: str,
    u1_group: str,
) -> Callable[[Expression], bool]:
    su2_symbol = theory.symbol(su2_group, role=SymbolRole.GROUP)
    u1_symbol = theory.symbol(u1_group, role=SymbolRole.GROUP)
    su2_vector_name = symbol_data(su2_symbol, SymbolDataKey.GROUP_FIELD)
    u1_vector_name = symbol_data(u1_symbol, SymbolDataKey.GROUP_FIELD)
    generator_name = f"gen_{su2_group}_fund"
    if (
        not isinstance(su2_vector_name, str)
        or su2_vector_name not in theory.fields
        or not isinstance(u1_vector_name, str)
        or u1_vector_name not in theory.fields
        or generator_name not in theory.cg_tensors
    ):
        return lambda _term: False
    generator_pattern = cg_tensor_pattern(theory.cg_tensors[generator_name].label)
    su2_strength_pattern = field_strength_pattern(theory.fields[su2_vector_name].label)
    u1_strength_pattern = field_strength_pattern(theory.fields[u1_vector_name].label)

    def candidate(term: Expression) -> bool:
        return (
            _has_at_least_matches(term, generator_pattern, 1)
            and _has_at_least_matches(term, su2_strength_pattern, 1)
            and _has_at_least_matches(term, u1_strength_pattern, 1)
        )

    return candidate


def _has_at_least_matches(expr: Expression, pattern: Expression, minimum: int) -> bool:
    count = 0
    for _match in expr.match(pattern):
        count += 1
        if count >= minimum:
            return True
    return False


def contract_pychete_deltas_into_cg_tensors(expr: Expression) -> Expression:
    """Contract explicit pychete ``Delta`` factors into registered ``CG`` tensors.

    Wilson-line transporters emit the public ``Delta(Index(...), Index(...))``
    head, while the native colour bridge lowers registered ``CG`` tensors.
    Normalize the transporter deltas into neighboring CG index labels before
    handing the expression to the native-backed colour and field-strength
    projectors.
    """

    if not _contains_delta(expr) or not _contains_cg_tensor(expr):
        return expr
    out = expr
    replacements = _pychete_delta_cg_contraction_replacements()
    for _ in range(8):
        updated = out.replace_multiple(replacements).expand()
        if bool(updated == out):
            return updated
        out = updated
    return out


def contract_pychete_deltas(theory: Any, expr: Expression) -> Expression:
    """Contract explicit pychete ``Delta`` heads using registered index metadata.

    This mirrors the Matchete ``ContractDelta`` stage for non-flavour group
    indices: deltas are first pushed into neighbouring CG tensors, then
    remaining explicit deltas are used as native replacement rules over the
    rest of each product. Closed registered-representation traces reduce to
    the stored representation dimension.
    """

    if not _contains_delta(expr):
        return expr
    out = contract_pychete_deltas_into_cg_tensors(expr)
    replacements = (
        *_pychete_delta_identity_replacements(),
        *_pychete_delta_field_slot_replacements(),
        *_pychete_delta_contraction_replacements(theory),
    )
    for _ in range(8):
        updated = out.replace_multiple(replacements).expand()
        if bool(updated == out):
            return updated
        out = updated
    return out


@cache
def _pychete_delta_identity_replacements() -> tuple[Replacement, ...]:
    label = s.head("pychete_delta_identity_label_")
    representation = s.head("pychete_delta_identity_representation_")
    rest = s.head("pychete_delta_identity_rest_")
    direct = s.Delta(
        s.Index(label, representation),
        s.Index(label, s.Bar(representation)),
    )
    conjugate = s.Delta(
        s.Index(label, s.Bar(representation)),
        s.Index(label, representation),
    )
    replacements: list[Replacement] = []
    for delta in (direct, conjugate):
        replacements.append(Replacement(delta * rest, rest, rhs_cache_size=0))
        replacements.append(Replacement(delta, Expression.num(1), rhs_cache_size=0))
    return tuple(replacements)


@cache
def _pychete_delta_field_slot_replacements() -> tuple[Replacement, ...]:
    first_label = s.head("pychete_delta_field_first_label_")
    second_label = s.head("pychete_delta_field_second_label_")
    representation = s.head("pychete_delta_field_representation_")
    label = s.head("pychete_delta_field_label_")
    type_expr = s.head("pychete_delta_field_type_")
    derivatives = s.head("pychete_delta_field_derivatives_")
    label_is_field = label.req_tag(SymbolRole.FIELD.value)
    same_rep = s.Delta(
        s.Index(first_label, representation),
        s.Index(second_label, representation),
    )
    direct_pair = s.Delta(
        s.Index(first_label, representation),
        s.Index(second_label, s.Bar(representation)),
    )
    conjugate_pair = s.Delta(
        s.Index(first_label, s.Bar(representation)),
        s.Index(second_label, representation),
    )

    def field_replacement(
        *,
        index_wildcards: tuple[Expression, ...],
        position: int,
        source_label: Expression,
        target_label: Expression,
        barred: bool,
    ) -> Callable[[dict[Expression, Expression]], Expression]:
        def replace(match: dict[Expression, Expression]) -> Expression:
            updated = list(index_wildcards)
            updated[position] = s.Index(match[target_label], match[representation])
            field = s.Field(
                match[label],
                match[type_expr],
                s.List(*(match[item] if item in match else item for item in updated)),
                match[derivatives],
            )
            return s.Bar(field) if barred else field

        return replace

    replacements: list[Replacement] = []
    for delta in (same_rep, direct_pair, conjugate_pair):
        for arity in range(1, 9):
            for position in range(arity):
                for source_label, target_label in (
                    (first_label, second_label),
                    (second_label, first_label),
                ):
                    index_wildcards = tuple(
                        s.head(f"pychete_delta_field_index_{arity}_{position}_{index}_")
                        for index in range(arity)
                    )
                    pattern_indices = list(index_wildcards)
                    pattern_indices[position] = s.Index(source_label, representation)
                    field = s.Field(label, type_expr, s.List(*pattern_indices), derivatives)
                    replacements.append(
                        Replacement(
                            delta * field,
                            field_replacement(
                                index_wildcards=tuple(pattern_indices),
                                position=position,
                                source_label=source_label,
                                target_label=target_label,
                                barred=False,
                            ),
                            label_is_field,
                            rhs_cache_size=0,
                        )
                    )
                    replacements.append(
                        Replacement(
                            delta * s.Bar(field),
                            field_replacement(
                                index_wildcards=tuple(pattern_indices),
                                position=position,
                                source_label=source_label,
                                target_label=target_label,
                                barred=True,
                            ),
                            label_is_field,
                            rhs_cache_size=0,
                        )
                    )
    return tuple(replacements)


def _pychete_delta_contraction_replacements(theory: Any) -> tuple[Replacement, ...]:
    first_label = s.head("pychete_delta_first_label_")
    second_label = s.head("pychete_delta_second_label_")
    representation = s.head("pychete_delta_representation_")
    rest = s.head("pychete_delta_rest_")

    same_rep = s.Delta(
        s.Index(first_label, representation),
        s.Index(second_label, representation),
    )
    direct_pair = s.Delta(
        s.Index(first_label, representation),
        s.Index(second_label, s.Bar(representation)),
    )
    conjugate_pair = s.Delta(
        s.Index(first_label, s.Bar(representation)),
        s.Index(second_label, representation),
    )

    def delta_replacement(delta_pattern: Expression) -> Callable[[dict[Expression, Expression]], Expression]:
        def replace(match: dict[Expression, Expression]) -> Expression:
            matched = delta_pattern.replace_wildcards(match)
            dimension = _closed_delta_dimension(theory, match, first_label, second_label, representation)
            return matched if dimension is None else dimension

        return replace

    def product_replacement(delta_pattern: Expression) -> Callable[[dict[Expression, Expression]], Expression]:
        product_pattern = delta_pattern * rest

        def replace(match: dict[Expression, Expression]) -> Expression:
            matched = product_pattern.replace_wildcards(match)
            rest_expr = match[rest]
            contracted = _contract_delta_product_rest(
                theory,
                rest_expr,
                match,
                first_label=first_label,
                second_label=second_label,
                representation=representation,
            )
            if contracted is not None:
                return contracted
            dimension = _closed_delta_dimension(theory, match, first_label, second_label, representation)
            return matched if dimension is None else (dimension * rest_expr).expand()

        return replace

    replacements: list[Replacement] = []
    for delta_pattern in (same_rep, direct_pair, conjugate_pair):
        replacements.append(Replacement(delta_pattern * rest, product_replacement(delta_pattern), rhs_cache_size=0))
        replacements.append(Replacement(delta_pattern, delta_replacement(delta_pattern), rhs_cache_size=0))
    return tuple(replacements)


def _contract_delta_product_rest(
    theory: Any,
    rest: Expression,
    match: dict[Expression, Expression],
    *,
    first_label: Expression,
    second_label: Expression,
    representation: Expression,
) -> Expression | None:
    rep = match[representation]
    if _registered_representation_dimension(theory, rep) is None:
        return None
    first = match[first_label]
    second = match[second_label]
    substitutions = (
        (s.Index(first, rep), s.Index(second, rep)),
        (s.Index(second, rep), s.Index(first, rep)),
        (s.Index(first, s.Bar(rep)), s.Index(second, s.Bar(rep))),
        (s.Index(second, s.Bar(rep)), s.Index(first, s.Bar(rep))),
    )
    for source, target in substitutions:
        updated = rest.replace(source, target)
        if not bool(updated == rest):
            return updated
    return None


def _closed_delta_dimension(
    theory: Any,
    match: dict[Expression, Expression],
    first_label: Expression,
    second_label: Expression,
    representation: Expression,
) -> Expression | None:
    first = match[first_label]
    second = match[second_label]
    if not bool(first == second) and not (_is_dummy_index_label(first) and _is_dummy_index_label(second)):
        return None
    dimension = _registered_representation_dimension(theory, match[representation])
    return None if dimension is None else Expression.num(dimension)


def _registered_representation_dimension(theory: Any, representation: Expression) -> int | None:
    try:
        return theory.representation_dimension(representation)
    except (AttributeError, KeyError):
        return None


def _is_dummy_index_label(label: Expression) -> bool:
    return is_head(label, s.dummy_index)


def decode_native_color_wrappers_and_simplify_field_strengths(theory: Any, expr: Expression) -> Expression:
    """Decode native idenso/spenso colour wrappers and simplify generated gauge bilinears."""

    decoded = decode_native_color_wrappers(theory, expr)
    return simplify_pychete_field_strength_group_algebra(theory, decoded)


def to_dots(expr: Expression) -> Expression:
    """Delegate contracted-vector dot-product conversion to idenso."""

    return native_module().to_dots(expr)


def wrap_dummies(expr: Expression, header: Expression) -> Expression:
    """Wrap only dummy indices through idenso's native routine."""

    return native_module().wrap_dummies(expr, header)


def wrap_indices(expr: Expression, header: Expression) -> Expression:
    """Wrap all abstract indices through idenso's native routine."""

    return native_module().wrap_indices(expr, header)


def simplify_index_algebra(
    expr: Expression,
    *,
    expand: bool = True,
    gamma: bool = True,
    color: bool = True,
    metrics: bool = True,
    dots: bool = False,
) -> Expression:
    """Run a native idenso simplification pipeline for index algebra."""

    result = simplify_pychete_dirac_algebra(expr)
    if expand:
        result = expand_mink_bis(result)
        result = expand_color(result)
        result = expand_metrics(result)
    if gamma:
        result = simplify_gamma(result)
    if color:
        result = simplify_color(result)
    if metrics:
        result = simplify_pychete_field_derivative_metrics(result)
        result = simplify_pychete_loop_momentum_metrics(result)
        result = simplify_pychete_field_strength_metrics(result)
        result = simplify_metrics(result)
        result = simplify_pychete_field_derivative_metrics(result)
        result = simplify_pychete_loop_momentum_metrics(result)
        result = simplify_pychete_field_strength_metrics(result)
    if dots:
        result = to_dots(result)
    return simplify_pychete_dirac_algebra(result)


@cache
def _loop_momentum_metric_replacements() -> tuple[Replacement, ...]:
    first = s.head("loop_momentum_metric_first_")
    second = s.head("loop_momentum_metric_second_")
    metric_heads = (s.Metric, s.Delta)
    replacements: list[Replacement] = [Replacement(s.LoopMomentum(first) * s.LoopMomentum(first), s.LoopMomentumSquared)]
    for metric_head in metric_heads:
        metric = metric_head(first, second)
        replacements.extend(
            (
                Replacement(metric * s.LoopMomentum(first), s.LoopMomentum(second)),
                Replacement(metric * s.LoopMomentum(second), s.LoopMomentum(first)),
            )
        )
    return tuple(replacements)


def _normalize_generated_lorentz_index(index: Expression) -> Expression:
    if not is_head(index, s.Index) or len(index) != 2 or not bool(index[1] == s.Lorentz):
        return index
    normalized = _generated_backend_index_alias(index[0])
    if normalized is None:
        return index
    return s.Index(normalized, s.Lorentz)


@cache
def _field_strength_lorentz_index_alias_replacements() -> tuple[Replacement, ...]:
    label = s.head("field_strength_lorentz_alias_label_")
    indices = s.head("field_strength_lorentz_alias_indices_")
    derivatives = s.head("field_strength_lorentz_alias_derivatives_")
    first = s.head("field_strength_lorentz_alias_first_")
    second = s.head("field_strength_lorentz_alias_second_")
    strength = s.FieldStrength(label, s.List(first, second), indices, derivatives)

    def normalize(match: dict[Expression, Expression]) -> Expression:
        first_index = _normalize_generated_lorentz_index(match[first])
        second_index = _normalize_generated_lorentz_index(match[second])
        return s.FieldStrength(match[label], s.List(first_index, second_index), match[indices], match[derivatives])

    return (Replacement(strength, normalize, label.req_tag(SymbolRole.FIELD.value), rhs_cache_size=0),)


@cache
def _field_strength_metric_index_alias_replacements() -> tuple[Replacement, ...]:
    label = s.head("field_strength_metric_alias_label_")
    indices = s.head("field_strength_metric_alias_indices_")
    derivatives = s.head("field_strength_metric_alias_derivatives_")
    first = s.head("field_strength_metric_alias_first_")
    second = s.head("field_strength_metric_alias_second_")
    metric_left = s.head("field_strength_metric_alias_metric_left_")
    metric_right = s.head("field_strength_metric_alias_metric_right_")
    strength = s.FieldStrength(label, s.List(first, second), indices, derivatives)

    def normalize_metric(
        match: dict[Expression, Expression],
        *,
        metric_head: Expression,
    ) -> Expression:
        left = _normalize_generated_lorentz_index(match[metric_left])
        right = _normalize_generated_lorentz_index(match[metric_right])
        return metric_head(left, right) * strength.replace_wildcards(match)

    def normalize_metric_for(metric_head: Expression) -> Callable[[dict[Expression, Expression]], Expression]:
        def normalize(match: dict[Expression, Expression]) -> Expression:
            return normalize_metric(match, metric_head=metric_head)

        return normalize

    replacements: list[Replacement] = []
    for metric_head in (s.Metric, s.Delta):
        replacements.append(
            Replacement(
                metric_head(metric_left, metric_right) * strength,
                normalize_metric_for(metric_head),
                label.req_tag(SymbolRole.FIELD.value),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _generated_backend_index_alias(label: Expression) -> Expression | None:
    try:
        full_name = label.get_name()
    except TypeError:
        return None
    local_name = full_name.rsplit("::", maxsplit=1)[-1]
    for prefix in ("index_wilson_line_", "index_cde_"):
        if local_name.startswith(prefix):
            return Expression.symbol(f"pychete::{local_name.removeprefix('index_')}")
    for prefix in ("wilson_line_", "cde_"):
        if local_name.startswith(prefix):
            return Expression.symbol(f"pychete::{local_name}")
    return None


@cache
def _field_strength_metric_trace_replacements() -> tuple[Replacement, ...]:
    label = s.head("field_strength_metric_trace_label_")
    indices = s.head("field_strength_metric_trace_indices_")
    derivatives = s.head("field_strength_metric_trace_derivatives_")
    first = s.head("field_strength_metric_trace_first_")
    second = s.head("field_strength_metric_trace_second_")
    label_is_field = label.req_tag(SymbolRole.FIELD.value)
    replacements: list[Replacement] = []
    for metric_head in (s.Metric, s.Delta):
        metric = metric_head(first, second)
        direct = s.FieldStrength(label, s.List(first, second), indices, derivatives)
        swapped = s.FieldStrength(label, s.List(second, first), indices, derivatives)
        replacements.extend(
            (
                Replacement(metric * direct, Expression.num(0), label_is_field),
                Replacement(metric * swapped, Expression.num(0), label_is_field),
            )
        )
    return tuple(replacements)


@cache
def _field_strength_metric_slot_replacements() -> tuple[Replacement, ...]:
    label = s.head("field_strength_metric_slot_label_")
    indices = s.head("field_strength_metric_slot_indices_")
    derivatives = s.head("field_strength_metric_slot_derivatives_")
    first = s.head("field_strength_metric_slot_first_")
    second = s.head("field_strength_metric_slot_second_")
    replacement = s.head("field_strength_metric_slot_replacement_")
    label_is_field = label.req_tag(SymbolRole.FIELD.value)
    strength = s.FieldStrength(label, s.List(first, second), indices, derivatives)

    def replace_first(match: dict[Expression, Expression]) -> Expression:
        return s.FieldStrength(
            match[label],
            s.List(match[replacement], match[second]),
            match[indices],
            match[derivatives],
        )

    def replace_second(match: dict[Expression, Expression]) -> Expression:
        return s.FieldStrength(
            match[label],
            s.List(match[first], match[replacement]),
            match[indices],
            match[derivatives],
        )

    replacements: list[Replacement] = []
    for metric_head in (s.Metric, s.Delta):
        replacements.extend(
            (
                Replacement(metric_head(first, replacement) * strength, replace_first, label_is_field),
                Replacement(metric_head(replacement, first) * strength, replace_first, label_is_field),
                Replacement(metric_head(second, replacement) * strength, replace_second, label_is_field),
                Replacement(metric_head(replacement, second) * strength, replace_second, label_is_field),
            )
        )
    return tuple(replacements)


@cache
def _field_strength_lorentz_antisymmetry_replacements() -> tuple[Replacement, ...]:
    label = s.head("field_strength_lorentz_label_")
    indices = s.head("field_strength_lorentz_indices_")
    derivatives = s.head("field_strength_lorentz_derivatives_")
    first = s.head("field_strength_lorentz_first_")
    second = s.head("field_strength_lorentz_second_")
    strength = s.FieldStrength(label, s.List(first, second), indices, derivatives)

    def canonicalize(match: dict[Expression, Expression]) -> Expression:
        first_index = match[first]
        second_index = match[second]
        if bool(first_index == second_index):
            return Expression.num(0)
        field_strength = strength.replace_wildcards(match)
        if canonical_string(second_index) < canonical_string(first_index):
            return -s.FieldStrength(
                match[label],
                s.List(second_index, first_index),
                match[indices],
                match[derivatives],
            )
        return field_strength

    return (
        Replacement(
            strength,
            canonicalize,
            label.req_tag(SymbolRole.FIELD.value),
            rhs_cache_size=0,
        ),
    )


@cache
def _field_derivative_metric_slot_replacements() -> tuple[Replacement, ...]:
    label = s.head("field_derivative_metric_label_")
    type_expr = s.head("field_derivative_metric_type_")
    indices = s.head("field_derivative_metric_indices_")
    strength_lorentz = s.head("field_derivative_metric_strength_lorentz_")
    metric_left = s.head("field_derivative_metric_left_")
    metric_right = s.head("field_derivative_metric_right_")
    label_is_field = label.req_tag(SymbolRole.FIELD.value)

    def contract_field_like(
        match: dict[Expression, Expression],
        *,
        body: Expression,
        derivative_wildcards: tuple[Expression, ...],
        metric_head: Expression,
        constructor: Callable[[Expression, tuple[Expression, ...]], Expression],
    ) -> Expression:
        updated_derivatives = _contract_metric_into_derivative_slots(
            tuple(match[wildcard] for wildcard in derivative_wildcards),
            match[metric_left],
            match[metric_right],
        )
        if updated_derivatives is None:
            return metric_head(match[metric_left], match[metric_right]) * body.replace_wildcards(match)
        return constructor(body.replace_wildcards(match), updated_derivatives)

    def bar_field_with_derivatives(matched: Expression, updated: tuple[Expression, ...]) -> Expression:
        return s.Bar(field_with_derivatives(matched, updated))

    def bar_strength_with_derivatives(matched: Expression, updated: tuple[Expression, ...]) -> Expression:
        return s.Bar(field_strength_with_derivatives(matched, updated))

    def make_contract_replacement(
        *,
        body: Expression,
        derivative_wildcards: tuple[Expression, ...],
        metric_head: Expression,
        constructor: Callable[[Expression, tuple[Expression, ...]], Expression],
    ) -> Callable[[dict[Expression, Expression]], Expression]:
        def replacement(match: dict[Expression, Expression]) -> Expression:
            return contract_field_like(
                match,
                body=body,
                derivative_wildcards=derivative_wildcards,
                metric_head=metric_head,
                constructor=constructor,
            )

        return replacement

    replacements: list[Replacement] = []
    for arity in range(1, 9):
        derivative_wildcards = tuple(
            s.head(f"field_derivative_metric_derivative_{arity}_{index}_") for index in range(arity)
        )
        field = s.Field(label, type_expr, indices, s.List(*derivative_wildcards))
        strength = s.FieldStrength(label, strength_lorentz, indices, s.List(*derivative_wildcards))
        for metric_head in (s.Metric, s.Delta):
            metric = metric_head(metric_left, metric_right)
            replacements.extend(
                (
                    Replacement(
                        metric * field,
                        make_contract_replacement(
                            body=field,
                            derivative_wildcards=derivative_wildcards,
                            metric_head=metric_head,
                            constructor=field_with_derivatives,
                        ),
                        label_is_field,
                        rhs_cache_size=0,
                    ),
                    Replacement(
                        metric * s.Bar(field),
                        make_contract_replacement(
                            body=field,
                            derivative_wildcards=derivative_wildcards,
                            metric_head=metric_head,
                            constructor=bar_field_with_derivatives,
                        ),
                        label_is_field,
                        rhs_cache_size=0,
                    ),
                    Replacement(
                        metric * strength,
                        make_contract_replacement(
                            body=strength,
                            derivative_wildcards=derivative_wildcards,
                            metric_head=metric_head,
                            constructor=field_strength_with_derivatives,
                        ),
                        label_is_field,
                        rhs_cache_size=0,
                    ),
                    Replacement(
                        metric * s.Bar(strength),
                        make_contract_replacement(
                            body=strength,
                            derivative_wildcards=derivative_wildcards,
                            metric_head=metric_head,
                            constructor=bar_strength_with_derivatives,
                        ),
                        label_is_field,
                        rhs_cache_size=0,
                    ),
                )
            )
    return tuple(replacements)


def _contract_metric_into_derivative_slots(
    derivatives: tuple[Expression, ...],
    metric_left: Expression,
    metric_right: Expression,
) -> tuple[Expression, ...] | None:
    derivative_items = tuple(derivatives)
    normalized_items = tuple(_normalize_generated_lorentz_index(index) for index in derivative_items)
    left = _normalize_generated_lorentz_index(metric_left)
    right = _normalize_generated_lorentz_index(metric_right)
    if any(bool(index == left) for index in normalized_items):
        return tuple(
            metric_right if bool(index == left) else original
            for original, index in zip(derivative_items, normalized_items, strict=True)
        )
    if any(bool(index == right) for index in normalized_items):
        return tuple(
            metric_left if bool(index == right) else original
            for original, index in zip(derivative_items, normalized_items, strict=True)
        )
    return None


def _projector_power_replacement(
    projector: Expression,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_power(match: dict[Expression, Expression]) -> Expression:
        exponent = as_int(match[s.PowExponentWildcard])
        if exponent is None or exponent < 1 or exponent > _MAX_NATIVE_PROJECTOR_POWER:
            return projector ** match[s.PowExponentWildcard]
        return _native_projector_word((projector,) * exponent)

    return replace_power


def _native_projector_word(projectors: tuple[Expression, ...]) -> Expression:
    if not projectors:
        return Expression.num(1)
    native_expr = Expression.num(1)
    for index, projector in enumerate(projectors, start=1):
        native_expr *= _native_projector_tensor(projector)(index, index + 1)
    return _decode_simple_native_projector_result(native_module().simplify_gamma(native_expr))


@cache
def _dirac_product_replacements() -> tuple[Replacement, ...]:
    return _dirac_word_replacements(s.DiracProduct, "product")


@cache
def _ncm_dirac_word_replacements() -> tuple[Replacement, ...]:
    return _dirac_word_replacements(s.NCM, "ncm")


@cache
def _mixed_ncm_dirac_subword_replacements() -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_NATIVE_DIRAC_WORD_ARITY + 1):
        wildcards = _dirac_word_wildcards("mixed_ncm", arity)
        pattern = s.NCM(*wildcards)
        replacements.append(
            Replacement(
                pattern,
                _mixed_ncm_dirac_subword_replacement(pattern, wildcards),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


@cache
def _closed_ncm_dirac_trace_replacements() -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_NATIVE_DIRAC_WORD_ARITY + 1):
        wildcards = _dirac_word_wildcards("closed_ncm_trace", arity)
        pattern = s.NCM(*wildcards)
        replacements.append(
            Replacement(
                pattern,
                _closed_ncm_dirac_trace_replacement(pattern, wildcards),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


@cache
def _ncm_power_replacements() -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_NATIVE_DIRAC_WORD_ARITY + 1):
        wildcards = _dirac_word_wildcards("ncm_power", arity)
        pattern = s.NCM(*wildcards) ** s.PowExponentWildcard
        replacements.append(
            Replacement(
                pattern,
                _ncm_power_replacement(pattern, wildcards),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


@cache
def _open_fermion_ncm_dirac_chain_replacements() -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_NATIVE_DIRAC_WORD_ARITY + 1):
        middle_wildcards = _dirac_word_wildcards("open_ncm", arity)
        left_label = s.head(f"dirac_open_{arity}_left_label_")
        left_indices = s.head(f"dirac_open_{arity}_left_indices_")
        left_derivatives = s.head(f"dirac_open_{arity}_left_derivatives_")
        right_label = s.head(f"dirac_open_{arity}_right_label_")
        right_indices = s.head(f"dirac_open_{arity}_right_indices_")
        right_derivatives = s.head(f"dirac_open_{arity}_right_derivatives_")
        left_endpoint = s.Bar(s.Field(left_label, s.Fermion, left_indices, left_derivatives))
        right_endpoint = s.Field(right_label, s.Fermion, right_indices, right_derivatives)
        pattern = s.NCM(left_endpoint, *middle_wildcards, right_endpoint)
        field_labels_are_registered = left_label.req_tag(SymbolRole.FIELD.value) & right_label.req_tag(
            SymbolRole.FIELD.value
        )
        replacements.append(
            Replacement(
                pattern,
                _open_fermion_ncm_dirac_chain_replacement(pattern, left_endpoint, middle_wildcards, right_endpoint),
                field_labels_are_registered,
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


@cache
def _chiral_scalar_projector_replacements() -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    left_label = s.head("chiral_projector_left_label_")
    left_indices = s.head("chiral_projector_left_indices_")
    left_derivatives = s.head("chiral_projector_left_derivatives_")
    right_label = s.head("chiral_projector_right_label_")
    right_indices = s.head("chiral_projector_right_indices_")
    right_derivatives = s.head("chiral_projector_right_derivatives_")
    left_endpoint = s.Bar(s.Field(left_label, s.Fermion, left_indices, left_derivatives))
    right_endpoint = s.Field(right_label, s.Fermion, right_indices, right_derivatives)
    field_labels_are_registered = left_label.req_tag(SymbolRole.FIELD.value) & right_label.req_tag(
        SymbolRole.FIELD.value
    )
    for projector in (s.PR, s.PL):
        for projector_expr in (projector, s.DiracProduct(projector)):
            pattern = s.NCM(left_endpoint, projector_expr, right_endpoint)
            replacements.append(
                Replacement(
                    pattern,
                    _chiral_scalar_projector_replacement(pattern, projector, left_endpoint, right_endpoint),
                    field_labels_are_registered,
                    rhs_cache_size=0,
                )
            )
    return tuple(replacements)


def _dirac_word_replacements(head: Expression, kind: str) -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_NATIVE_DIRAC_WORD_ARITY + 1):
        wildcards = _dirac_word_wildcards(kind, arity)
        pattern = head(*wildcards)
        replacements.append(
            Replacement(
                pattern,
                _dirac_word_replacement(pattern, wildcards),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _chiral_scalar_projector_replacement(
    pattern: Expression,
    projector: Expression,
    left_endpoint: Expression,
    right_endpoint: Expression,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_projector(match: dict[Expression, Expression]) -> Expression:
        right_label = match[s.head("chiral_projector_right_label_")]
        chirality = field_chirality_from_label(right_label)
        if chirality is FieldChirality.NONE:
            return pattern.replace_wildcards(match)
        if _projector_matches_right_chirality(projector, chirality):
            return s.NCM(
                left_endpoint.replace_wildcards(match),
                right_endpoint.replace_wildcards(match),
            )
        return Expression.num(0)

    return replace_projector


def _projector_matches_right_chirality(projector: Expression, chirality: FieldChirality) -> bool:
    return (bool(projector == s.PR) and chirality is FieldChirality.RIGHT) or (
        bool(projector == s.PL) and chirality is FieldChirality.LEFT
    )


def _open_fermion_ncm_dirac_chain_replacement(
    pattern: Expression,
    left_endpoint: Expression,
    middle_wildcards: tuple[Expression, ...],
    right_endpoint: Expression,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_open_chain(match: dict[Expression, Expression]) -> Expression:
        matched = pattern.replace_wildcards(match)
        factors_to_simplify = _flatten_pychete_dirac_factors(tuple(match[wildcard] for wildcard in middle_wildcards))
        if factors_to_simplify is None:
            return matched
        simplified = _native_dirac_word(factors_to_simplify)
        split = None if simplified is None else _split_mixed_ncm_dirac_result(simplified)
        if split is None:
            return matched
        scalar, replacement_operands = split
        if bool(scalar == Expression.num(0)):
            return Expression.num(0)
        return _ncm_with_commutative_coefficient(
            scalar,
            (
                left_endpoint.replace_wildcards(match),
                *replacement_operands,
                right_endpoint.replace_wildcards(match),
            ),
        )

    return replace_open_chain


def _ncm_power_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_power(match: dict[Expression, Expression]) -> Expression:
        matched = pattern.replace_wildcards(match)
        exponent = as_int(match[s.PowExponentWildcard])
        if (
            exponent is None
            or exponent <= 0
            or exponent * len(wildcards) > _MAX_NCM_POWER_EXPANSION_TOTAL_ARITY
        ):
            return matched
        operands = tuple(match[wildcard] for wildcard in wildcards)
        return s.NCM(*(operands * exponent))

    return replace_power


def _dirac_word_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_word(match: dict[Expression, Expression]) -> Expression:
        matched = pattern.replace_wildcards(match)
        factors_to_simplify = _flatten_pychete_dirac_factors(tuple(match[wildcard] for wildcard in wildcards))
        if factors_to_simplify is None:
            return matched
        simplified = _native_dirac_word(factors_to_simplify)
        return matched if simplified is None else simplified

    return replace_word


def _mixed_ncm_dirac_subword_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_mixed_chain(match: dict[Expression, Expression]) -> Expression:
        matched = pattern.replace_wildcards(match)
        simplified = _simplify_mixed_ncm_dirac_subwords(tuple(match[wildcard] for wildcard in wildcards))
        return matched if simplified is None else simplified

    return replace_mixed_chain


def _closed_ncm_dirac_trace_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_closed_chain(match: dict[Expression, Expression]) -> Expression:
        matched = pattern.replace_wildcards(match)
        factors_to_trace = _flatten_pychete_dirac_factors(tuple(match[wildcard] for wildcard in wildcards))
        if factors_to_trace is None:
            return matched
        traced = _native_closed_dirac_word(factors_to_trace)
        return matched if traced is None else traced

    return replace_closed_chain


def _dirac_word_wildcards(kind: str, arity: int) -> tuple[Expression, ...]:
    return tuple(s.head(f"dirac_{kind}_{arity}_{index}_") for index in range(arity))


def _simplify_mixed_ncm_dirac_subwords(operands: tuple[Expression, ...]) -> Expression | None:
    output_operands: list[Expression] = []
    coefficient = Expression.num(1)
    changed = False
    run_operands: list[Expression] = []
    run_factors: list[Expression] = []

    def flush_run() -> bool:
        nonlocal coefficient, changed, run_operands, run_factors
        if not run_operands:
            return True
        if len(run_factors) < 2:
            output_operands.extend(run_operands)
            run_operands = []
            run_factors = []
            return True
        simplified = _native_dirac_word(tuple(run_factors))
        split = None if simplified is None else _split_mixed_ncm_dirac_result(simplified)
        if split is None:
            output_operands.extend(run_operands)
        else:
            scalar, replacement_operands = split
            if bool(scalar == Expression.num(0)):
                return False
            coefficient = (coefficient * scalar).expand()
            output_operands.extend(replacement_operands)
            changed = True
        run_operands = []
        run_factors = []
        return True

    for operand in operands:
        factors_to_simplify = _flatten_pychete_dirac_factors((operand,))
        if factors_to_simplify is None:
            if not flush_run():
                return Expression.num(0)
            output_operands.append(operand)
            continue
        run_operands.append(operand)
        run_factors.extend(factors_to_simplify)
    if not flush_run():
        return Expression.num(0)
    if not changed:
        return None
    return _ncm_with_commutative_coefficient(coefficient, tuple(output_operands))


def _split_mixed_ncm_dirac_result(expr: Expression) -> tuple[Expression, tuple[Expression, ...]] | None:
    if bool(expr == Expression.num(0)):
        return Expression.num(0), ()
    if bool(expr == Expression.num(1)):
        return Expression.num(1), ()
    if expr.get_type() is AtomType.Num:
        return expr, ()
    if _flatten_pychete_dirac_factors((expr,)) is not None:
        return Expression.num(1), (expr,)
    if expr.get_type() is not AtomType.Mul:
        return None

    coefficient = Expression.num(1)
    nonnumeric: list[Expression] = []
    for factor in factors(expr):
        if factor.get_type() is AtomType.Num:
            coefficient = (coefficient * factor).expand()
        else:
            nonnumeric.append(factor)
    if len(nonnumeric) > 1:
        return None
    if not nonnumeric:
        return coefficient, ()
    if _flatten_pychete_dirac_factors((nonnumeric[0],)) is None:
        return None
    return coefficient, (nonnumeric[0],)


def _ncm_with_commutative_coefficient(coefficient: Expression, operands: tuple[Expression, ...]) -> Expression:
    if bool(coefficient == Expression.num(0)):
        return Expression.num(0)
    if not operands:
        return coefficient
    body = operands[0] if len(operands) == 1 else s.NCM(*operands)
    return body if bool(coefficient == Expression.num(1)) else (coefficient * body).expand()


def _flatten_pychete_dirac_factors(operands: tuple[Expression, ...]) -> tuple[Expression, ...] | None:
    flattened: list[Expression] = []
    for operand in operands:
        if is_head(operand, s.DiracProduct):
            nested = _flatten_pychete_dirac_factors(args(operand))
            if nested is None:
                return None
            flattened.extend(nested)
            continue
        if not _is_pychete_dirac_factor(operand):
            return None
        flattened.append(operand)
    return tuple(flattened)


def _is_pychete_dirac_factor(expr: Expression) -> bool:
    return bool(expr == s.PR) or bool(expr == s.PL) or (is_head(expr, s.Gamma) and len(expr) == 1)


def _native_dirac_word(pychete_factors: tuple[Expression, ...]) -> Expression | None:
    if not pychete_factors:
        return Expression.num(1)
    native_expr = Expression.num(1)
    for index, factor in enumerate(pychete_factors, start=1):
        native_factor = _native_dirac_factor(factor, index, index + 1)
        if native_factor is None:
            return None
        native_expr *= native_factor
    return _decode_simple_native_dirac_result(native_module().simplify_gamma(native_expr))


def _native_closed_dirac_word(pychete_factors: tuple[Expression, ...]) -> Expression | None:
    if not pychete_factors:
        return Expression.num(4)
    native_expr = Expression.num(1)
    last = len(pychete_factors)
    for index, factor in enumerate(pychete_factors, start=1):
        right = 1 if index == last else index + 1
        native_factor = _native_dirac_factor(factor, index, right)
        if native_factor is None:
            return None
        native_expr *= native_factor
    return _decode_simple_native_dirac_result(native_module().simplify_gamma(native_expr))


def _native_dirac_factor(factor: Expression, left: int, right: int) -> Expression | None:
    if bool(factor == s.PR) or bool(factor == s.PL):
        return _native_projector_tensor(factor)(left, right)
    if is_head(factor, s.Gamma) and len(factor) == 1:
        return _native_gamma_tensor()(left, right, factor[0])
    return None


@cache
def _native_hep_tensor(name: str) -> Callable[..., Expression]:
    from symbolica import S
    from symbolica.community.spenso import TensorLibrary

    return TensorLibrary.hep_lib()[S(name)]


def _native_projector_tensor(projector: Expression) -> Callable[..., Expression]:
    if bool(projector == s.PR):
        return _native_hep_tensor("spenso::projp")
    if bool(projector == s.PL):
        return _native_hep_tensor("spenso::projm")
    raise ValueError(f"Unsupported pychete Dirac projector {projector}")


def _native_gamma_tensor() -> Callable[..., Expression]:
    return _native_hep_tensor("spenso::gamma")


def _decode_simple_native_projector_result(expr: Expression) -> Expression:
    decoded = _decode_simple_native_dirac_result(expr)
    return expr if decoded is None else decoded


def _decode_simple_native_dirac_result(expr: Expression) -> Expression | None:
    if bool(expr == Expression.num(0)):
        return Expression.num(0)
    chain = _decode_native_dirac_chain(expr)
    if chain is not None:
        return chain
    if _is_native_spinor_metric(expr):
        return Expression.num(1)
    metric = _decode_native_lorentz_metric(expr)
    if metric is not None:
        return metric
    kind = expr.get_type()
    if kind is AtomType.Num:
        return expr
    if kind is AtomType.Add:
        decoded_terms = tuple(_decode_simple_native_dirac_result(term) for term in args(expr))
        if any(term is None for term in decoded_terms):
            return None
        return sum_expr(term for term in decoded_terms if term is not None)
    if kind is AtomType.Mul:
        decoded_factors = tuple(_decode_simple_native_dirac_result(factor) for factor in factors(expr))
        if any(factor is None for factor in decoded_factors):
            return None
        return product_expr(factor for factor in decoded_factors if factor is not None)
    return None


def _cg_groups_in_expression(theory: Any, expr: Expression) -> tuple[str, ...]:
    pattern = cg_tensor_pattern()
    groups: list[str] = []
    for match in expr.match(pattern, s.CGTensorLabelWildcard.req_tag(SymbolRole.CG_TENSOR.value)):
        atom = pattern.replace_wildcards(match)
        definition = _cg_tensor_definition_for_label(theory, atom[0])
        if definition is None:
            continue
        for representation in definition.representation_exprs:
            group = theory.representation_definition(representation).group
            if group not in groups:
                groups.append(group)
    return tuple(groups)


def _cg_tensor_definition_for_label(theory: Any, label: Expression) -> Any | None:
    label_text = canonical_string(label)
    for definition in theory.cg_tensors.values():
        if canonical_string(definition.label) == label_text:
            return definition
    return None


@cache
def _builtin_epsilon_cg_replacements() -> tuple[Replacement, ...]:
    label = s.head("builtin_epsilon_cg_label_")
    left = s.head("builtin_epsilon_cg_left_")
    right = s.head("builtin_epsilon_cg_right_")
    pattern = s.CG(label, s.List(left, right))
    registered_cg_label = label.req_tag(SymbolRole.CG_TENSOR.value)

    def canonicalize(match: dict[Expression, Expression]) -> Expression:
        if not _is_rank_two_builtin_epsilon_label(match[label]):
            return pattern.replace_wildcards(match)
        left_index = match[left]
        right_index = match[right]
        if canonical_string(left_index) <= canonical_string(right_index):
            return pattern.replace_wildcards(match)
        return -s.CG(match[label], s.List(right_index, left_index))

    return (Replacement(pattern, canonicalize, registered_cg_label, rhs_cache_size=0),)


def _is_rank_two_builtin_epsilon_label(label: Expression) -> bool:
    source = symbol_data(label, SymbolDataKey.CG_SOURCE, "")
    representations = symbol_data(label, SymbolDataKey.CG_REPRESENTATIONS, [])
    return source == "builtin:eps" and isinstance(representations, list) and len(representations) == 2


def _replace_adjoint_generators_with_structure_constants(theory: Any, expr: Expression) -> Expression:
    pattern = cg_tensor_pattern()

    def replace(match: dict[Expression, Expression]) -> Expression:
        atom = pattern.replace_wildcards(match)
        definition = _cg_tensor_definition_for_label(theory, atom[0])
        if definition is None or definition.source_text != "builtin:gen":
            return atom
        if len(definition.representation_exprs) != 3:
            return atom
        representations = tuple(theory.representation_definition(rep) for rep in definition.representation_exprs)
        group = representations[0].group
        if not all(representation.group == group and representation.name == "adj" for representation in representations):
            return atom
        fstruct_name = f"fStruct_{group}"
        if fstruct_name not in theory.cg_tensors:
            return atom
        return -Expression.I * theory.cg_tensor_handle(fstruct_name)(*list_items(atom[1]))

    return expr.replace_multiple(
        [
            Replacement(
                pattern,
                replace,
                s.CGTensorLabelWildcard.req_tag(SymbolRole.CG_TENSOR.value),
                rhs_cache_size=0,
            )
        ]
    ).expand()


def _substitute_native_color_constants(theory: Any, expr: Expression, groups: tuple[str, ...]) -> Expression:
    replacements: list[Replacement] = [Replacement(_native_color_symbol("TR"), Expression.num(1) / Expression.num(2))]
    sizes: tuple[int, ...] = tuple(
        dict.fromkeys(size for group in groups if (size := _su_group_size(theory, group)) is not None)
    )
    if len(sizes) == 1:
        n = sizes[0]
        replacements.extend(
            [
                Replacement(_native_color_symbol("CA"), Expression.num(n)),
                Replacement(_native_color_symbol("CF"), Expression.num(n * n - 1) / Expression.num(2 * n)),
                Replacement(_native_color_symbol("Nc"), Expression.num(n)),
                Replacement(_native_color_symbol("NA"), Expression.num(n * n - 1)),
            ]
        )
    return expr.replace_multiple(replacements).expand()


def _decode_native_color_metrics(theory: Any, expr: Expression, groups: tuple[str, ...]) -> Expression:
    left = s.head("native_color_metric_left_")
    right = s.head("native_color_metric_right_")
    pattern = _native_color_symbol("g")(left, right)

    def decode(match: dict[Expression, Expression]) -> Expression:
        original = pattern.replace_wildcards(match)
        decoded = _decode_native_color_metric(theory, match[left], match[right], groups)
        return original if decoded is None else decoded

    return expr.replace_multiple([Replacement(pattern, decode, rhs_cache_size=0)]).expand()


def _decode_native_color_metric(
    theory: Any,
    left: Expression,
    right: Expression,
    groups: tuple[str, ...],
) -> Expression | None:
    left_slot = _decode_native_color_slot(left)
    right_slot = _decode_native_color_slot(right)
    if left_slot is None or right_slot is None:
        return None
    group = _native_color_metric_group(theory, left_slot, right_slot, groups)
    if group is None:
        return None
    group_symbol = theory.symbol(group, role=SymbolRole.GROUP)
    if left_slot.kind == "adj" and right_slot.kind == "adj":
        adj = group_symbol(s.adj)
        delta_name = f"del_{group}_adj"
        if delta_name not in theory.cg_tensors:
            return None
        left_index = theory.index(left_slot.label, adj)
        right_index = theory.index(right_slot.label, adj)
        if canonical_string(right_index) < canonical_string(left_index):
            left_index, right_index = right_index, left_index
        return theory.cg_tensor_handle(delta_name)(left_index, right_index)
    if left_slot.kind == "fund" and right_slot.kind == "fund" and left_slot.dual != right_slot.dual:
        fund = group_symbol(s.fund)
        delta_name = f"del_{group}_fund"
        if delta_name not in theory.cg_tensors:
            return None
        if left_slot.dual:
            return theory.cg_tensor_handle(delta_name)(
                theory.index(right_slot.label, fund),
                theory.index(left_slot.label, s.Bar(fund)),
            )
        return theory.cg_tensor_handle(delta_name)(
            theory.index(left_slot.label, fund),
            theory.index(right_slot.label, s.Bar(fund)),
        )
    return None


def _decode_native_color_tensors(theory: Any, expr: Expression, groups: tuple[str, ...]) -> Expression:
    adjoint = s.head("native_color_tensor_adjoint_")
    left = s.head("native_color_tensor_left_")
    right = s.head("native_color_tensor_right_")
    first = s.head("native_color_tensor_first_")
    second = s.head("native_color_tensor_second_")
    third = s.head("native_color_tensor_third_")
    generator = _native_color_symbol("t")
    structure_constant = _native_color_symbol("f")

    def decode_generator(match: dict[Expression, Expression]) -> Expression:
        original = generator(adjoint, left, right).replace_wildcards(match)
        decoded = _decode_native_color_generator(theory, match[adjoint], match[left], match[right], groups)
        return original if decoded is None else decoded

    def decode_structure_constant(match: dict[Expression, Expression]) -> Expression:
        original = structure_constant(first, second, third).replace_wildcards(match)
        decoded = _decode_native_color_structure_constant(
            theory,
            match[first],
            match[second],
            match[third],
            groups,
        )
        return original if decoded is None else decoded

    decoded_chains = _decode_native_color_chains(theory, expr, groups)
    return decoded_chains.replace_multiple(
        [
            Replacement(generator(adjoint, left, right), decode_generator, rhs_cache_size=0),
            Replacement(structure_constant(first, second, third), decode_structure_constant, rhs_cache_size=0),
        ]
    ).expand()


def _decode_native_color_chains(theory: Any, expr: Expression, groups: tuple[str, ...]) -> Expression:
    chain = _native_color_symbol("chain")
    generator = _native_color_symbol("t")
    in_slot = _native_color_symbol("in")
    out_slot = _native_color_symbol("out")
    left = s.head("native_color_chain_left_")
    right = s.head("native_color_chain_right_")
    occurrence = count()
    replacements: list[Replacement] = []

    for arity in range(1, _MAX_NATIVE_COLOR_CHAIN_ARITY + 1):
        adjoints = tuple(s.head(f"native_color_chain_adjoint_{arity}_{i}_") for i in range(arity))
        pattern = chain(left, right, *(generator(adjoint, in_slot, out_slot) for adjoint in adjoints))

        def decode(
            match: dict[Expression, Expression],
            *,
            adjoints: tuple[Expression, ...] = adjoints,
            pattern: Expression = pattern,
        ) -> Expression:
            original = pattern.replace_wildcards(match)
            decoded = _decode_native_color_chain(
                theory,
                match[left],
                match[right],
                tuple(match[adjoint] for adjoint in adjoints),
                groups,
                occurrence=next(occurrence),
            )
            return original if decoded is None else decoded

        replacements.append(Replacement(pattern, decode, rhs_cache_size=0))
    return expr.replace_multiple(replacements).expand()


def _decode_native_color_chain(
    theory: Any,
    left: Expression,
    right: Expression,
    adjoints: tuple[Expression, ...],
    groups: tuple[str, ...],
    *,
    occurrence: int,
) -> Expression | None:
    if len(adjoints) == 1:
        return _decode_native_color_generator(theory, adjoints[0], left, right, groups)
    left_slot = _decode_native_color_slot(left)
    right_slot = _decode_native_color_slot(right)
    adjoint_slots = tuple(_decode_native_color_slot(adjoint) for adjoint in adjoints)
    if left_slot is None or right_slot is None or any(slot is None for slot in adjoint_slots):
        return None
    concrete_adjoint_slots = tuple(slot for slot in adjoint_slots if slot is not None)
    if left_slot.kind != "fund" or right_slot.kind != "fund" or left_slot.dual or not right_slot.dual:
        return None
    if any(slot.kind != "adj" for slot in concrete_adjoint_slots):
        return None
    group = _native_color_chain_group(theory, left_slot, right_slot, concrete_adjoint_slots, groups)
    if group is None:
        return None
    generator_name = f"gen_{group}_fund"
    if generator_name not in theory.cg_tensors:
        return None
    group_symbol = theory.symbol(group, role=SymbolRole.GROUP)
    adjoint_representation = group_symbol(s.adj)
    fund = group_symbol(s.fund)
    generator_handle = theory.cg_tensor_handle(generator_name)
    internal = tuple(
        theory.index(
            theory.symbol(f"native_color_chain_{occurrence}_{i}", role=SymbolRole.INDEX),
            fund,
        )
        for i in range(len(concrete_adjoint_slots) - 1)
    )
    outputs = (theory.index(left_slot.label, fund), *internal)
    inputs = (
        *(theory.index(index[0], s.Bar(fund)) for index in internal),
        theory.index(right_slot.label, s.Bar(fund)),
    )
    return product_expr(
        generator_handle(theory.index(slot.label, adjoint_representation), output, input_)
        for slot, output, input_ in zip(concrete_adjoint_slots, outputs, inputs, strict=True)
    )


def _decode_native_color_generator(
    theory: Any,
    adjoint: Expression,
    left: Expression,
    right: Expression,
    groups: tuple[str, ...],
) -> Expression | None:
    adjoint_slot = _decode_native_color_slot(adjoint)
    left_slot = _decode_native_color_slot(left)
    right_slot = _decode_native_color_slot(right)
    if adjoint_slot is None or left_slot is None or right_slot is None:
        return None
    if adjoint_slot.kind != "adj" or left_slot.kind != "fund" or right_slot.kind != "fund":
        return None
    if left_slot.dual == right_slot.dual or left_slot.dimension != right_slot.dimension:
        return None
    group = _native_color_generator_group(theory, adjoint_slot, left_slot, right_slot, groups)
    if group is None:
        return None
    generator_name = f"gen_{group}_fund"
    if generator_name not in theory.cg_tensors:
        return None
    group_symbol = theory.symbol(group, role=SymbolRole.GROUP)
    adjoint_representation = group_symbol(s.adj)
    fund = group_symbol(s.fund)
    adjoint_index = theory.index(adjoint_slot.label, adjoint_representation)
    if left_slot.dual:
        output_index = theory.index(right_slot.label, fund)
        input_index = theory.index(left_slot.label, s.Bar(fund))
    else:
        output_index = theory.index(left_slot.label, fund)
        input_index = theory.index(right_slot.label, s.Bar(fund))
    return theory.cg_tensor_handle(generator_name)(adjoint_index, output_index, input_index)


def _decode_native_color_structure_constant(
    theory: Any,
    first: Expression,
    second: Expression,
    third: Expression,
    groups: tuple[str, ...],
) -> Expression | None:
    slots = tuple(_decode_native_color_slot(index) for index in (first, second, third))
    if any(slot is None or slot.kind != "adj" for slot in slots):
        return None
    adjoint_slots = tuple(slot for slot in slots if slot is not None)
    group = _native_color_adjoint_group(theory, adjoint_slots, groups)
    if group is None:
        return None
    fstruct_name = f"fStruct_{group}"
    if fstruct_name not in theory.cg_tensors:
        return None
    sign, canonical_slots = _canonicalize_antisymmetric_color_slots(adjoint_slots)
    group_symbol = theory.symbol(group, role=SymbolRole.GROUP)
    adjoint_representation = group_symbol(s.adj)
    decoded = theory.cg_tensor_handle(fstruct_name)(
        *(theory.index(slot.label, adjoint_representation) for slot in canonical_slots)
    )
    return decoded if sign == 1 else -decoded


def _canonicalize_antisymmetric_color_slots(
    slots: tuple["_NativeColorSlot", ...],
) -> tuple[int, tuple["_NativeColorSlot", ...]]:
    order = tuple(sorted(range(len(slots)), key=lambda index: canonical_string(slots[index].label)))
    inversions = sum(
        1
        for left_position, left in enumerate(order)
        for right in order[left_position + 1 :]
        if left > right
    )
    sign = -1 if inversions % 2 else 1
    return sign, tuple(slots[index] for index in order)


def _native_color_generator_group(
    theory: Any,
    adjoint: "_NativeColorSlot",
    left: "_NativeColorSlot",
    right: "_NativeColorSlot",
    groups: tuple[str, ...],
) -> str | None:
    candidates = [
        group
        for group in groups
        if _native_color_group_dimension(theory, group, "adj") == adjoint.dimension
        and _native_color_group_dimension(theory, group, "fund") == left.dimension
        and _native_color_group_dimension(theory, group, "fund") == right.dimension
    ]
    return candidates[0] if len(candidates) == 1 else None


def _native_color_adjoint_group(
    theory: Any,
    slots: tuple["_NativeColorSlot", ...],
    groups: tuple[str, ...],
) -> str | None:
    dimensions = {slot.dimension for slot in slots}
    if len(dimensions) != 1:
        return None
    dimension = next(iter(dimensions))
    candidates = [
        group
        for group in groups
        if _native_color_group_dimension(theory, group, "adj") == dimension
    ]
    return candidates[0] if len(candidates) == 1 else None


def _native_color_metric_group(
    theory: Any,
    left: "_NativeColorSlot",
    right: "_NativeColorSlot",
    groups: tuple[str, ...],
) -> str | None:
    if left.kind != right.kind or left.dimension != right.dimension:
        return None
    candidates = [
        group
        for group in groups
        if _native_color_group_dimension(theory, group, left.kind) == left.dimension
    ]
    return candidates[0] if len(candidates) == 1 else None


def _native_color_chain_group(
    theory: Any,
    left: "_NativeColorSlot",
    right: "_NativeColorSlot",
    adjoints: tuple["_NativeColorSlot", ...],
    groups: tuple[str, ...],
) -> str | None:
    if left.dimension != right.dimension:
        return None
    candidates = [
        group
        for group in groups
        if _native_color_group_dimension(theory, group, "fund") == left.dimension
        and all(_native_color_group_dimension(theory, group, "adj") == adjoint.dimension for adjoint in adjoints)
    ]
    return candidates[0] if len(candidates) == 1 else None


@dataclass(frozen=True)
class _NativeColorSlot:
    kind: str
    dimension: int
    label: Expression
    dual: bool


def _decode_native_color_slot(expr: Expression) -> _NativeColorSlot | None:
    dual = False
    body = expr
    if is_head(body, _native_color_symbol("dind")) and len(body) == 1:
        dual = True
        body = body[0]
    if is_head(body, _native_color_symbol("cof")) and len(body) == 2:
        dimension = as_int(body[0])
        return None if dimension is None else _NativeColorSlot("fund", dimension, body[1], dual)
    if is_head(body, _native_color_symbol("coad")) and len(body) == 2:
        dimension = as_int(body[0])
        return None if dimension is None else _NativeColorSlot("adj", dimension, body[1], dual)
    return None


def _native_color_group_dimension(theory: Any, group: str, kind: str) -> int | None:
    n = _su_group_size(theory, group)
    if n is None:
        return None
    return n if kind == "fund" else n * n - 1


def _su_group_size(theory: Any, group: str) -> int | None:
    group_entry = theory.groups.get(group)
    if group_entry is None:
        return None
    group_type = expression_from_canonical(str(group_entry["type"]))
    if not is_head(group_type, s.SU) or len(group_type) != 1:
        return None
    n = as_int(group_type[0])
    if n is None or n <= 1:
        return None
    return n


def _su2_field_strength_generator_bilinear_coefficient(theory: Any, group: str) -> Expression | None:
    if _su_group_size(theory, group) != 2:
        return None
    group_symbol = theory.symbol(group, role=SymbolRole.GROUP)
    group_kind = GroupKind.from_user(str(symbol_data(group_symbol, SymbolDataKey.GROUP_KIND, GroupKind.GLOBAL.value)))
    if group_kind is not GroupKind.GAUGE or bool(symbol_data(group_symbol, SymbolDataKey.GROUP_ABELIAN, 0)):
        return None
    vector_name = symbol_data(group_symbol, SymbolDataKey.GROUP_FIELD)
    if not isinstance(vector_name, str) or vector_name not in theory.fields:
        return None
    generator_name = f"gen_{group}_fund"
    delta_fund_name = f"del_{group}_fund"
    delta_adj_name = f"del_{group}_adj"
    if generator_name not in theory.cg_tensors or delta_fund_name not in theory.cg_tensors or delta_adj_name not in theory.cg_tensors:
        return None
    adj_dim = _native_color_group_dimension(theory, group, "adj")
    fund_dim = _native_color_group_dimension(theory, group, "fund")
    if adj_dim is None or fund_dim is None:
        return None
    adj = group_symbol(s.adj)
    fund = group_symbol(s.fund)
    adjoint_a = s.Index(Expression.symbol(f"pychete::{group}_su2_project_A"), adj)
    adjoint_b = s.Index(Expression.symbol(f"pychete::{group}_su2_project_B"), adj)
    fund_i = s.Index(Expression.symbol(f"pychete::{group}_su2_project_i"), fund)
    fund_k = s.Index(Expression.symbol(f"pychete::{group}_su2_project_k"), fund)
    fund_i_dual = s.Index(fund_i[0], s.Bar(fund))
    fund_k_dual = s.Index(fund_k[0], s.Bar(fund))
    generator = theory.cg_tensor_handle(generator_name)
    delta_fund = theory.cg_tensor_handle(delta_fund_name)
    delta_adj = theory.cg_tensor_handle(delta_adj_name)
    contracted_trace = (
        delta_adj(adjoint_a, adjoint_b)
        * generator(adjoint_a, fund_i, fund_k_dual)
        * generator(adjoint_b, fund_k, fund_i_dual)
    )
    traced = simplify_pychete_color_algebra(theory, contracted_trace)
    trace_coefficient = traced.coefficient(delta_fund(fund_i, fund_i_dual)).expand()
    if not bool(trace_coefficient == Expression.num(0)):
        return (trace_coefficient / Expression.num(adj_dim)).expand()
    if tuple(traced.match(cg_tensor_pattern(), s.CGTensorLabelWildcard.req_tag(SymbolRole.CG_TENSOR.value))):
        return None
    return (traced / Expression.num(adj_dim * fund_dim)).expand()


def _su2_field_strength_generator_bilinear_replacements(
    theory: Any,
    group: str,
    coefficient: Expression,
) -> tuple[Replacement, ...]:
    group_symbol = theory.symbol(group, role=SymbolRole.GROUP)
    vector_name = symbol_data(group_symbol, SymbolDataKey.GROUP_FIELD)
    if not isinstance(vector_name, str) or vector_name not in theory.fields:
        return ()
    generator_name = f"gen_{group}_fund"
    if generator_name not in theory.cg_tensors:
        return ()
    vector_label = theory.fields[vector_name].label
    generator_label = theory.cg_tensors[generator_name].label
    fund = group_symbol(s.fund)
    adj = group_symbol(s.adj)

    field_label = s.head(f"su2_fs_gen_{group}_field_label_")
    field_index_label = s.head(f"su2_fs_gen_{group}_field_index_")
    bar_index_label = s.head(f"su2_fs_gen_{group}_bar_index_")
    internal_index_label = s.head(f"su2_fs_gen_{group}_internal_index_")
    adjoint_left_label = s.head(f"su2_fs_gen_{group}_adjoint_left_")
    adjoint_right_label = s.head(f"su2_fs_gen_{group}_adjoint_right_")
    lorentz_indices = s.head(f"su2_fs_gen_{group}_lorentz_")

    field_index = s.Index(field_index_label, fund)
    bar_index = s.Index(bar_index_label, fund)
    bar_dual_index = s.Index(bar_index_label, s.Bar(fund))
    internal_index = s.Index(internal_index_label, fund)
    internal_dual_index = s.Index(internal_index_label, s.Bar(fund))
    adjoint_left = s.Index(adjoint_left_label, adj)
    adjoint_right = s.Index(adjoint_right_label, adj)

    field = s.Field(field_label, s.Scalar, s.List(field_index), s.List())
    barred_field = s.Bar(s.Field(field_label, s.Scalar, s.List(bar_index), s.List()))
    left_strength = s.FieldStrength(vector_label, lorentz_indices, s.List(adjoint_left), s.List())
    right_strength = s.FieldStrength(vector_label, lorentz_indices, s.List(adjoint_right), s.List())
    left_generator = s.CG(generator_label, s.List(adjoint_left, field_index, internal_dual_index))
    right_generator = s.CG(generator_label, s.List(adjoint_right, internal_index, bar_dual_index))
    reversed_left_generator = s.CG(generator_label, s.List(adjoint_left, internal_index, bar_dual_index))
    reversed_right_generator = s.CG(generator_label, s.List(adjoint_right, field_index, internal_dual_index))
    patterns = (
        field * barred_field * left_generator * right_generator * left_strength * right_strength,
        field * barred_field * reversed_left_generator * reversed_right_generator * left_strength * right_strength,
    )

    def project_for_pattern(pattern: Expression) -> Callable[[dict[Expression, Expression]], Expression]:
        def project(match: dict[Expression, Expression]) -> Expression:
            matched = pattern.replace_wildcards(match)
            label = match[field_label]
            if not _is_single_fund_scalar_field_label(theory, label, fund):
                return matched
            singlet_index = s.Index(match[field_index_label], fund)
            adjoint_index = s.Index(match[adjoint_left_label], adj)
            singlet_field = s.Field(label, s.Scalar, s.List(singlet_index), s.List())
            singlet_bar = s.Bar(s.Field(label, s.Scalar, s.List(singlet_index), s.List()))
            singlet_strength = s.FieldStrength(vector_label, match[lorentz_indices], s.List(adjoint_index), s.List())
            return (coefficient * singlet_field * singlet_bar * singlet_strength * singlet_strength).expand()

        return project

    return tuple(
        Replacement(
            pattern,
            project_for_pattern(pattern),
            field_label.req_tag(SymbolRole.FIELD.value),
            rhs_cache_size=0,
        )
        for pattern in patterns
    )


def _su2_u1_field_strength_generator_bilinear_replacements(
    theory: Any,
    su2_group: str,
    u1_group: str,
) -> tuple[Replacement, ...]:
    su2_symbol = theory.symbol(su2_group, role=SymbolRole.GROUP)
    u1_symbol = theory.symbol(u1_group, role=SymbolRole.GROUP)
    su2_vector_name = symbol_data(su2_symbol, SymbolDataKey.GROUP_FIELD)
    u1_vector_name = symbol_data(u1_symbol, SymbolDataKey.GROUP_FIELD)
    if not isinstance(su2_vector_name, str) or su2_vector_name not in theory.fields:
        return ()
    if not isinstance(u1_vector_name, str) or u1_vector_name not in theory.fields:
        return ()
    generator_name = f"gen_{su2_group}_fund"
    if generator_name not in theory.cg_tensors:
        return ()
    su2_vector_label = theory.fields[su2_vector_name].label
    u1_vector_label = theory.fields[u1_vector_name].label
    generator_label = theory.cg_tensors[generator_name].label
    fund = su2_symbol(s.fund)
    adj = su2_symbol(s.adj)

    field_label = s.head(f"su2_u1_fs_gen_{su2_group}_{u1_group}_field_label_")
    field_index_label = s.head(f"su2_u1_fs_gen_{su2_group}_{u1_group}_field_index_")
    bar_index_label = s.head(f"su2_u1_fs_gen_{su2_group}_{u1_group}_bar_index_")
    adjoint_label = s.head(f"su2_u1_fs_gen_{su2_group}_{u1_group}_adjoint_")
    lorentz_indices = s.head(f"su2_u1_fs_gen_{su2_group}_{u1_group}_lorentz_")

    field_index = s.Index(field_index_label, fund)
    bar_index = s.Index(bar_index_label, fund)
    bar_dual_index = s.Index(bar_index_label, s.Bar(fund))
    adjoint_index = s.Index(adjoint_label, adj)

    field = s.Field(field_label, s.Scalar, s.List(field_index), s.List())
    barred_field = s.Bar(s.Field(field_label, s.Scalar, s.List(bar_index), s.List()))
    generator = s.CG(generator_label, s.List(adjoint_index, field_index, bar_dual_index))
    su2_strength = s.FieldStrength(su2_vector_label, lorentz_indices, s.List(adjoint_index), s.List())
    u1_strength = s.FieldStrength(u1_vector_label, lorentz_indices, s.List(), s.List())
    pattern = field * barred_field * generator * su2_strength * u1_strength

    def project(match: dict[Expression, Expression], *, pattern: Expression = pattern) -> Expression:
        matched = pattern.replace_wildcards(match)
        label = match[field_label]
        if not _is_single_fund_scalar_field_label_with_abelian_charge(theory, label, fund, u1_symbol):
            return matched
        source_field_index = s.Index(match[field_index_label], fund)
        source_field_dual_index = s.Index(match[field_index_label], s.Bar(fund))
        source_bar_index = s.Index(match[bar_index_label], fund)
        source_adjoint_index = s.Index(match[adjoint_label], adj)
        canonical_field = s.Field(label, s.Scalar, s.List(source_field_index), s.List())
        canonical_bar = s.Bar(s.Field(label, s.Scalar, s.List(source_bar_index), s.List()))
        canonical_generator = s.CG(
            generator_label,
            s.List(source_adjoint_index, source_bar_index, source_field_dual_index),
        )
        canonical_su2_strength = s.FieldStrength(
            su2_vector_label,
            match[lorentz_indices],
            s.List(source_adjoint_index),
            s.List(),
        )
        canonical_u1_strength = s.FieldStrength(u1_vector_label, match[lorentz_indices], s.List(), s.List())
        return (
            canonical_bar
            * canonical_generator
            * canonical_field
            * canonical_su2_strength
            * canonical_u1_strength
        ).expand()

    return (
        Replacement(
            pattern,
            project,
            field_label.req_tag(SymbolRole.FIELD.value),
            rhs_cache_size=0,
        ),
    )


def _is_single_fund_scalar_field_label(theory: Any, label: Expression, fund: Expression) -> bool:
    label_key = canonical_string(label)
    for definition in theory.fields.values():
        if canonical_string(definition.label) != label_key:
            continue
        return (
            bool(definition.type_expr == s.Scalar)
            and len(definition.indices) == 1
            and bool(definition.indices[0] == fund)
        )
    return False


def _is_single_fund_scalar_field_label_with_abelian_charge(
    theory: Any,
    label: Expression,
    fund: Expression,
    group_symbol: Expression,
) -> bool:
    label_key = canonical_string(label)
    for definition in theory.fields.values():
        if canonical_string(definition.label) != label_key:
            continue
        if (
            not bool(definition.type_expr == s.Scalar)
            or len(definition.indices) != 1
            or not bool(definition.indices[0] == fund)
        ):
            return False
        return any(is_head(charge, group_symbol) for charge in definition.charge_exprs)
    return False


@cache
def _native_color_symbol(name: str) -> Expression:
    return Expression.symbol(f"spenso::{name}")


def _decode_native_dirac_chain(expr: Expression) -> Expression | None:
    if (
        expr.get_type() is not AtomType.Fn
        or expr.get_name() != "spenso::chain"
        or len(expr) < 3
    ):
        return None
    decoded_factors = tuple(_decode_native_dirac_factor(factor) for factor in args(expr)[2:])
    if any(factor is None for factor in decoded_factors):
        return None
    return _pychete_dirac_word(tuple(factor for factor in decoded_factors if factor is not None))


def _decode_native_dirac_factor(expr: Expression) -> Expression | None:
    if is_head(expr, Expression.symbol("spenso::projp")) and len(expr) == 2:
        return s.PR
    if is_head(expr, Expression.symbol("spenso::projm")) and len(expr) == 2:
        return s.PL
    if is_head(expr, Expression.symbol("spenso::gamma")) and len(expr) == 3:
        return s.Gamma(_decode_native_lorentz_index(expr[2]))
    return None


def _decode_native_lorentz_index(expr: Expression) -> Expression:
    if is_head(expr, Expression.symbol("spenso::mink")) and len(expr) == 2:
        return expr[1]
    return expr


def _decode_native_lorentz_metric(expr: Expression) -> Expression | None:
    if (
        not is_head(expr, Expression.symbol("spenso::g"))
        or len(expr) != 2
        or not _is_native_minkowski_index(expr[0])
        or not _is_native_minkowski_index(expr[1])
    ):
        return None
    return s.Metric(_decode_native_lorentz_index(expr[0]), _decode_native_lorentz_index(expr[1]))


def _is_native_spinor_metric(expr: Expression) -> bool:
    return (
        is_head(expr, Expression.symbol("spenso::g"))
        and len(expr) == 2
        and _is_native_bis_index(expr[0])
        and _is_native_bis_index(expr[1])
    )


def _is_native_bis_index(expr: Expression) -> bool:
    return is_head(expr, Expression.symbol("spenso::bis")) and len(expr) == 2


def _is_native_minkowski_index(expr: Expression) -> bool:
    return is_head(expr, Expression.symbol("spenso::mink")) and len(expr) == 2


def _pychete_dirac_word(dirac_factors: tuple[Expression, ...]) -> Expression:
    if not dirac_factors:
        return Expression.num(1)
    if len(dirac_factors) == 1:
        return dirac_factors[0]
    return s.DiracProduct(*dirac_factors)


__all__ = [
    "canonicalize_builtin_epsilon_cg_tensors",
    "cook_function",
    "cook_indices",
    "contract_pychete_deltas_into_cg_tensors",
    "contract_pychete_deltas",
    "decode_native_color_wrappers",
    "decode_native_color_wrappers_and_simplify_field_strengths",
    "dirac_adjoint",
    "expand_bis",
    "expand_color",
    "expand_metrics",
    "expand_mink",
    "expand_mink_bis",
    "list_dangling",
    "native_module",
    "simplify_color",
    "simplify_gamma",
    "simplify_index_algebra",
    "simplify_metrics",
    "simplify_su2_field_strength_generator_bilinears",
    "simplify_su2_u1_field_strength_generator_bilinears",
    "simplify_pychete_field_strength_group_algebra",
    "expand_pychete_ncm_powers",
    "simplify_pychete_color_algebra",
    "simplify_pychete_chiral_scalar_projectors",
    "simplify_pychete_dirac_algebra",
    "trace_pychete_closed_dirac_chains",
    "simplify_pychete_field_derivative_metrics",
    "simplify_pychete_field_strength_metrics",
    "simplify_pychete_open_dirac_chains",
    "simplify_pychete_dirac_projectors",
    "simplify_pychete_loop_momentum_metrics",
    "to_dots",
    "wrap_dummies",
    "wrap_indices",
]
