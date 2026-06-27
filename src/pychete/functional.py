from __future__ import annotations

from collections.abc import Callable, Iterable

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .expr import (
    args,
    bar_field_inner,
    bar_field_pattern,
    bar_field_strength_pattern,
    cd_pattern,
    covariant_derivative_commutator_pattern,
    factors,
    field_pattern,
    field_label,
    field_type,
    field_derivatives,
    field_strength_pattern,
    field_strength_with_derivatives,
    field_with_derivatives,
    is_bar_field,
    is_head,
    is_zero,
    list_items,
    matching_subexpressions,
    product_expr,
    sum_expr,
    terms,
    wilson_term_pattern,
)
from .linear_external import linear_external_function_heads
from .symbols import SymbolRole, canonical_string, s
from .theory import Theory
from .theory_metadata import (
    CouplingSelfConjugate,
    FieldDefinition,
    FieldHandle,
    FieldVariation,
    coupling_self_conjugate_from_label,
    field_self_conjugate_from_label,
)

_MAX_MULTILINEAR_CHAIN_ARITY = 8
_MAX_SCALAR_DERIVATIVE_BILINEAR_CANDIDATES = 128


def hermitian_conjugate(expr: Expression) -> Expression:
    """Return pychete's supported symbolic hermitian conjugate of ``expr``.

    The helper expands conjugation over commutative products, reverses
    non-commutative chains, swaps chiral projectors, and uses field/coupling
    Symbolica metadata to preserve self-conjugate objects.
    """

    return _bar_expr(expr, generated=True).expand()


def apply_cd(indices: tuple[Expression, ...] | list[Expression], expr: Expression) -> Expression:
    out = expr
    for index in indices:
        out = _single_cd(index, out).expand()
    return out


def expand_cd_operators(expr: Expression) -> Expression:
    """Expand explicit ``CD`` wrappers into pychete field-derivative slots.

    Generated matching expressions store covariant/ordinary derivative action
    directly on ``Field(..., derivatives)`` atoms. User-facing operators,
    operator-basis metadata, and fixtures may instead contain explicit
    ``CD(index, body)``
    wrappers. This helper normalizes the latter representation with Symbolica
    replacement rules and :func:`apply_cd`, so product rules and nested
    derivatives use the same native variation machinery as functional
    derivatives.
    """

    cd_pat = cd_pattern()
    if not bool(expr.matches(cd_pat)):
        return expr

    def cd_replacement(match: dict[Expression, Expression]) -> Expression:
        index = match[s.CDIndexWildcard]
        indices = list_items(index) if is_head(index, s.List) else (index,)
        return apply_cd(indices, match[s.CDBodyWildcard])

    out = expr
    for _ in range(16):
        updated = out.replace(cd_pat, cd_replacement).expand()
        if bool(updated == out):
            return updated
        out = updated
    return out


def simplify_trivial_cd_operators(expr: Expression) -> Expression:
    """Remove explicit covariant derivatives acting on zero.

    Generated Wilson-line and CDE expressions can contain intermediate
    ``CD(indices, 0)`` wrappers after commutator expansion. Keep this as a
    Symbolica pattern rewrite so only the trivial derivative operator is
    removed; nonzero ``CD`` bodies remain available for later projection and
    backend simplification.
    """

    cd_pat = cd_pattern()
    if not bool(expr.matches(cd_pat)):
        return expr

    def cd_zero_replacement(match: dict[Expression, Expression]) -> Expression:
        body = match[s.CDBodyWildcard]
        if is_zero(body):
            return Expression.num(0)
        return cd_pat.replace_wildcards(match)

    out = expr
    for _ in range(16):
        updated = out.replace(cd_pat, cd_zero_replacement).expand()
        if bool(updated == out):
            return updated
        out = updated
    return out


def expose_scalar_derivative_commutator_bilinears(
    theory: Theory,
    expr: Expression,
    *,
    include_gauge_coupling: bool = True,
    expand_commutators: bool = True,
    max_candidates: int = _MAX_SCALAR_DERIVATIVE_BILINEAR_CANDIDATES,
) -> Expression:
    """Expose scalar derivative bilinear field-strength components.

    Matchete's Green-basis simplification uses IBP and covariant-derivative
    commutation identities to expose field-strength components hidden inside
    scalar derivative bilinears. This helper implements the local, generic
    scalar cases needed by Wilson-line matching: two two-derivative scalar
    factors and one-sided four-derivative scalar factors. Candidate atoms are
    discovered with Symbolica tag-restricted patterns and component
    coefficients are extracted with native ``Expression.coefficient(...)``
    calls. The field-strength part is represented through formal
    ``CovariantDerivativeCommutator`` products and lowered by the theory's
    registered Symbolica-backed commutator expansion; the helper is not tied
    to a particular operator basis such as SMEFT Warsaw.
    """

    if max_candidates < 0:
        raise ValueError("max_candidates must be non-negative")
    theory._validate_registered_expression(expr)
    field_atoms = _scalar_derivative_field_atoms(expr, derivative_count=2)
    barred_atoms = _scalar_derivative_barred_field_atoms(expr, derivative_count=2)
    one_field_atoms = _scalar_derivative_field_atoms(expr, derivative_count=1)
    one_barred_atoms = _scalar_derivative_barred_field_atoms(expr, derivative_count=1)
    four_field_atoms = _scalar_derivative_field_atoms(expr, derivative_count=4)
    four_barred_atoms = _scalar_derivative_barred_field_atoms(expr, derivative_count=4)
    zero_field_atoms = _scalar_derivative_field_atoms(expr, derivative_count=0)
    zero_barred_atoms = _scalar_derivative_barred_field_atoms(expr, derivative_count=0)
    has_two_derivative_bilinears = bool(field_atoms and barred_atoms)
    has_one_sided_four_derivative_bilinears = bool(
        (four_field_atoms and zero_barred_atoms) or (four_barred_atoms and zero_field_atoms)
    )
    has_mixed_field_strength_bilinears = bool((field_atoms and zero_barred_atoms) or (barred_atoms and zero_field_atoms))
    has_first_derivative_field_strength_bilinears = bool(one_field_atoms and one_barred_atoms)
    if not (
        has_two_derivative_bilinears
        or has_one_sided_four_derivative_bilinears
        or has_mixed_field_strength_bilinears
        or has_first_derivative_field_strength_bilinears
    ):
        return expr

    out = expr
    seen: set[str] = set()
    candidate_count = 0
    for barred in barred_atoms:
        barred_base = bar_field_inner(barred)
        barred_key = canonical_string(field_label(barred_base))
        barred_derivatives = field_derivatives(barred_base)
        canonical_pair = _canonical_distinct_derivative_pair(barred_derivatives)
        if canonical_pair is None:
            continue
        for field in field_atoms:
            if canonical_string(field_label(field)) != barred_key:
                continue
            if _canonical_distinct_derivative_pair(field_derivatives(field)) != canonical_pair:
                continue
            key = "|".join(
                (
                    canonical_string(field_with_derivatives(barred_base, ())),
                    canonical_string(field_with_derivatives(field, ())),
                    canonical_string(canonical_pair[0]),
                    canonical_string(canonical_pair[1]),
                )
            )
            if key in seen:
                continue
            seen.add(key)
            candidate_count += 1
            if candidate_count > max_candidates:
                return out
            out = _expose_scalar_two_derivative_green_bilinear_candidate(
                theory,
                out,
                barred_base,
                field,
                canonical_pair,
                include_gauge_coupling=include_gauge_coupling,
                expand_commutators=expand_commutators,
            )
    for barred in four_barred_atoms:
        barred_base = bar_field_inner(barred)
        barred_key = canonical_string(field_with_derivatives(barred_base, ()))
        for field in zero_field_atoms:
            if canonical_string(field_with_derivatives(field, ())) != barred_key:
                continue
            candidate_count += 1
            if candidate_count > max_candidates:
                return out
            out = _expose_scalar_one_sided_four_derivative_green_bilinear_candidate(
                theory,
                out,
                barred_base,
                field,
                field_derivatives(barred_base),
                four_derivatives_on_bar=True,
                include_gauge_coupling=include_gauge_coupling,
                expand_commutators=expand_commutators,
            )
    for field in four_field_atoms:
        field_key = canonical_string(field_with_derivatives(field, ()))
        for barred in zero_barred_atoms:
            barred_base = bar_field_inner(barred)
            if canonical_string(field_with_derivatives(barred_base, ())) != field_key:
                continue
            candidate_count += 1
            if candidate_count > max_candidates:
                return out
            out = _expose_scalar_one_sided_four_derivative_green_bilinear_candidate(
                theory,
                out,
                barred_base,
                field,
                field_derivatives(field),
                four_derivatives_on_bar=False,
                include_gauge_coupling=include_gauge_coupling,
                expand_commutators=expand_commutators,
            )
    for barred in one_barred_atoms:
        barred_base = bar_field_inner(barred)
        barred_key = canonical_string(field_with_derivatives(barred_base, ()))
        barred_derivatives = field_derivatives(barred_base)
        if len(barred_derivatives) != 1:
            continue
        for field in one_field_atoms:
            if canonical_string(field_with_derivatives(field, ())) != barred_key:
                continue
            field_derivatives_ = field_derivatives(field)
            if len(field_derivatives_) != 1:
                continue
            candidate_count += 1
            if candidate_count > max_candidates:
                return out
            out = _expose_scalar_first_derivative_field_strength_ibp_candidate(
                theory,
                out,
                barred_base,
                field,
                barred_derivatives[0],
                field_derivatives_[0],
                include_gauge_coupling=include_gauge_coupling,
                expand_commutators=expand_commutators,
            )
    for field in field_atoms:
        field_key = canonical_string(field_with_derivatives(field, ()))
        field_derivatives_ = field_derivatives(field)
        for barred in zero_barred_atoms:
            barred_base = bar_field_inner(barred)
            if canonical_string(field_with_derivatives(barred_base, ())) != field_key:
                continue
            candidate_count += 1
            if candidate_count > max_candidates:
                return out
            out = _expose_scalar_mixed_field_strength_green_bilinear_candidate(
                theory,
                out,
                barred_base,
                field,
                field_derivatives_,
                derivatives_on_bar=False,
                include_gauge_coupling=include_gauge_coupling,
                expand_commutators=expand_commutators,
            )
    for barred in barred_atoms:
        barred_base = bar_field_inner(barred)
        barred_key = canonical_string(field_with_derivatives(barred_base, ()))
        barred_derivatives = field_derivatives(barred_base)
        for field in zero_field_atoms:
            if canonical_string(field_with_derivatives(field, ())) != barred_key:
                continue
            candidate_count += 1
            if candidate_count > max_candidates:
                return out
            out = _expose_scalar_mixed_field_strength_green_bilinear_candidate(
                theory,
                out,
                barred_base,
                field,
                barred_derivatives,
                derivatives_on_bar=True,
                include_gauge_coupling=include_gauge_coupling,
                expand_commutators=expand_commutators,
            )
    return out.expand()


def _scalar_derivative_field_atoms(expr: Expression, *, derivative_count: int) -> tuple[Expression, ...]:
    pattern = field_pattern()
    label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    atoms: list[Expression] = []
    seen: set[str] = set()
    for match in expr.match(pattern, label_is_tagged):
        atom = pattern.replace_wildcards(match)
        if not _is_scalar_derivative_field(atom, derivative_count=derivative_count):
            continue
        key = canonical_string(atom)
        if key in seen:
            continue
        seen.add(key)
        atoms.append(atom)
    return tuple(atoms)


def _scalar_derivative_barred_field_atoms(expr: Expression, *, derivative_count: int) -> tuple[Expression, ...]:
    pattern = bar_field_pattern()
    label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    atoms: list[Expression] = []
    seen: set[str] = set()
    for match in expr.match(pattern, label_is_tagged):
        atom = pattern.replace_wildcards(match)
        if not is_bar_field(atom):
            continue
        inner = bar_field_inner(atom)
        if not _is_scalar_derivative_field(inner, derivative_count=derivative_count):
            continue
        key = canonical_string(atom)
        if key in seen:
            continue
        seen.add(key)
        atoms.append(atom)
    return tuple(atoms)


def _is_scalar_derivative_field(atom: Expression, *, derivative_count: int) -> bool:
    if not bool(field_type(atom) == s.Scalar):
        return False
    derivatives = field_derivatives(atom)
    if len(derivatives) != derivative_count:
        return False
    if derivative_count == 2:
        return _canonical_distinct_derivative_pair(derivatives) is not None
    if derivative_count == 1:
        return True
    if derivative_count == 4:
        return _four_derivative_pair_order(derivatives) is not None
    return derivative_count == 0


def _canonical_distinct_derivative_pair(derivatives: tuple[Expression, ...]) -> tuple[Expression, Expression] | None:
    if len(derivatives) != 2:
        return None
    left, right = derivatives
    if bool(left == right):
        return None
    return (right, left) if canonical_string(right) < canonical_string(left) else (left, right)


def _expose_scalar_two_derivative_green_bilinear_candidate(
    theory: Theory,
    expr: Expression,
    barred_base: Expression,
    field_base: Expression,
    derivative_pair: tuple[Expression, Expression],
    *,
    include_gauge_coupling: bool,
    expand_commutators: bool,
) -> Expression:
    first, second = derivative_pair
    components = (
        ((first, second), (first, second), Expression.num(1)),
        ((first, second), (second, first), _half_expr()),
        ((second, first), (first, second), _half_expr()),
        ((second, first), (second, first), Expression.num(1)),
    )
    out = expr
    for barred_derivatives, field_derivatives_, commutator_weight in components:
        source = s.Bar(field_with_derivatives(barred_base, barred_derivatives)) * field_with_derivatives(
            field_base,
            field_derivatives_,
        )
        coefficient = expr.coefficient(source).expand()
        if is_zero(coefficient):
            continue
        replacement = _scalar_green_bilinear_replacement(
            theory,
            barred_base,
            field_base,
            barred_derivatives[0],
            barred_derivatives[1],
            commutator_first=first,
            commutator_second=second,
            commutator_weight=commutator_weight,
            include_gauge_coupling=include_gauge_coupling,
            expand_commutators=expand_commutators,
        )
        out = (out - coefficient * source + coefficient * replacement).expand()
    return out


def _expose_scalar_one_sided_four_derivative_green_bilinear_candidate(
    theory: Theory,
    expr: Expression,
    barred_base: Expression,
    field_base: Expression,
    derivatives: tuple[Expression, ...],
    *,
    four_derivatives_on_bar: bool,
    include_gauge_coupling: bool,
    expand_commutators: bool,
) -> Expression:
    pair_order = _four_derivative_pair_order(derivatives)
    if pair_order is None:
        return expr
    first, second = pair_order
    source = (
        s.Bar(field_with_derivatives(barred_base, derivatives)) * field_with_derivatives(field_base, ())
        if four_derivatives_on_bar
        else s.Bar(field_with_derivatives(barred_base, ())) * field_with_derivatives(field_base, derivatives)
    )
    coefficient = expr.coefficient(source).expand()
    if is_zero(coefficient):
        return expr
    replacement = _scalar_green_bilinear_replacement(
        theory,
        barred_base,
        field_base,
        first,
        second,
        commutator_weight=_four_derivative_commutator_weight(derivatives),
        include_gauge_coupling=include_gauge_coupling,
        expand_commutators=expand_commutators,
    )
    return (expr - coefficient * source + coefficient * replacement).expand()


def _expose_scalar_mixed_field_strength_green_bilinear_candidate(
    theory: Theory,
    expr: Expression,
    barred_base: Expression,
    field_base: Expression,
    derivatives: tuple[Expression, ...],
    *,
    derivatives_on_bar: bool,
    include_gauge_coupling: bool,
    expand_commutators: bool,
) -> Expression:
    if len(derivatives) != 2 or bool(derivatives[0] == derivatives[1]):
        return expr
    zero_barred = s.Bar(field_with_derivatives(barred_base, ()))
    zero_field = field_with_derivatives(field_base, ())
    source = (
        s.Bar(field_with_derivatives(barred_base, derivatives)) * zero_field
        if derivatives_on_bar
        else zero_barred * field_with_derivatives(field_base, derivatives)
    )
    coefficient = expr.coefficient(source).expand()
    if is_zero(coefficient):
        return expr
    field_strength_pair = _matching_field_strength_lorentz_pair(coefficient, derivatives)
    if field_strength_pair is None:
        return expr
    left, right, commutator_weight = field_strength_pair
    commutator_body = zero_barred if derivatives_on_bar else zero_field
    commutator = s.CovariantDerivativeCommutator(left, right, commutator_body)
    replacement = (commutator_weight * commutator * (zero_field if derivatives_on_bar else zero_barred)).expand()
    if expand_commutators:
        replacement = theory.expand_covariant_derivative_commutators(
            replacement,
            include_gauge_coupling=include_gauge_coupling,
        )
    return (expr - coefficient * source + coefficient * replacement).expand()


def _expose_scalar_first_derivative_field_strength_ibp_candidate(
    theory: Theory,
    expr: Expression,
    barred_base: Expression,
    field_base: Expression,
    barred_derivative: Expression,
    field_derivative: Expression,
    *,
    include_gauge_coupling: bool,
    expand_commutators: bool,
) -> Expression:
    if bool(barred_derivative == field_derivative):
        return expr
    zero_barred = s.Bar(field_with_derivatives(barred_base, ()))
    source_field = field_with_derivatives(field_base, (field_derivative,))
    source = s.Bar(field_with_derivatives(barred_base, (barred_derivative,))) * source_field
    coefficient = expr.coefficient(source).expand()
    if is_zero(coefficient):
        return expr
    field_strength_pair = _matching_field_strength_lorentz_pair(coefficient, (barred_derivative, field_derivative))
    if field_strength_pair is None:
        return expr
    left, right, commutator_weight = field_strength_pair
    commutator_replacement = (
        commutator_weight
        * zero_barred
        * s.CovariantDerivativeCommutator(left, right, field_with_derivatives(field_base, ()))
    ).expand()
    if expand_commutators:
        commutator_replacement = theory.expand_covariant_derivative_commutators(
            commutator_replacement,
            include_gauge_coupling=include_gauge_coupling,
        )
    replacement = (
        -apply_cd([barred_derivative], coefficient) * zero_barred * source_field
        - coefficient * commutator_replacement
    ).expand()
    return (expr - coefficient * source + replacement).expand()


def _matching_field_strength_lorentz_pair(
    coefficient: Expression,
    derivatives: tuple[Expression, Expression],
) -> tuple[Expression, Expression, Expression] | None:
    first, second = derivatives
    pattern = field_strength_pattern()
    label_is_tagged = s.FieldStrengthLabelWildcard.req_tag(SymbolRole.FIELD.value)
    for match in coefficient.match(pattern, label_is_tagged):
        atom = pattern.replace_wildcards(match)
        lorentz_indices = list_items(atom[1])
        if len(lorentz_indices) != 2:
            continue
        left, right = lorentz_indices
        if bool(left == first) and bool(right == second):
            return left, right, _half_expr()
        if bool(left == second) and bool(right == first):
            return left, right, -_half_expr()
    return None


def _scalar_green_bilinear_replacement(
    theory: Theory,
    barred_base: Expression,
    field_base: Expression,
    first: Expression,
    second: Expression,
    *,
    commutator_first: Expression | None = None,
    commutator_second: Expression | None = None,
    commutator_weight: Expression,
    include_gauge_coupling: bool,
    expand_commutators: bool,
) -> Expression:
    basis_bilinear = s.Bar(field_with_derivatives(barred_base, (first, first))) * field_with_derivatives(
        field_base,
        (second, second),
    )
    if is_zero(commutator_weight):
        return basis_bilinear
    comm_first = first if commutator_first is None else commutator_first
    comm_second = second if commutator_second is None else commutator_second
    barred_commutator = s.CovariantDerivativeCommutator(
        comm_first,
        comm_second,
        s.Bar(field_with_derivatives(barred_base, ())),
    )
    field_commutator = s.CovariantDerivativeCommutator(comm_first, comm_second, field_with_derivatives(field_base, ()))
    replacement = (basis_bilinear + commutator_weight * barred_commutator * field_commutator).expand()
    if expand_commutators:
        replacement = theory.expand_covariant_derivative_commutators(
            replacement,
            include_gauge_coupling=include_gauge_coupling,
        )
    return replacement


def _four_derivative_pair_order(derivatives: tuple[Expression, ...]) -> tuple[Expression, Expression] | None:
    if len(derivatives) != 4:
        return None
    first = derivatives[0]
    second: Expression | None = None
    counts = {canonical_string(first): 1}
    for derivative in derivatives[1:]:
        key = canonical_string(derivative)
        counts[key] = counts.get(key, 0) + 1
        if second is None and not bool(derivative == first):
            second = derivative
    if second is None or bool(second == first):
        return None
    if counts.get(canonical_string(first), 0) != 2 or counts.get(canonical_string(second), 0) != 2:
        return None
    if len(counts) != 2:
        return None
    return first, second


def _four_derivative_commutator_weight(derivatives: tuple[Expression, ...]) -> Expression:
    pair_order = _four_derivative_pair_order(derivatives)
    if pair_order is None:
        return Expression.num(0)
    first, second = pair_order
    binary = [0 if bool(derivative == first) else 1 for derivative in derivatives]
    inversions = sum(1 for i, left in enumerate(binary) for right in binary[i + 1 :] if left > right)
    swaps_to_grouped_order = min(inversions, 4 - inversions)
    if swaps_to_grouped_order == 0:
        return Expression.num(0)
    if swaps_to_grouped_order == 1:
        return _half_expr()
    return Expression.num(1)


def _half_expr() -> Expression:
    return Expression.num(1) / Expression.num(2)


def _single_cd(index: Expression, expr: Expression) -> Expression:
    varied = expr.replace_multiple(_cd_variation_replacements(index))
    varied = _linearize_variation_wrappers(varied, s.CDVariationParameter)
    return varied.series(s.CDVariationParameter, 0, 1).to_expression().coefficient(s.CDVariationParameter).expand()


def _cd_variation_replacements(index: Expression) -> tuple[Replacement, ...]:
    field_pat = field_pattern()
    bar_pat = bar_field_pattern()
    strength_pat = field_strength_pattern()
    bar_strength_pat = bar_field_strength_pattern()
    commutator_pat = covariant_derivative_commutator_pattern()
    cd_pat = cd_pattern()
    wilson_pat = wilson_term_pattern()

    def field_variation(match: dict[Expression, Expression]) -> Expression:
        matched = field_pat.replace_wildcards(match)
        derivative = s.Field(
            match[s.FieldLabelWildcard],
            match[s.FieldTypeWildcard],
            match[s.FieldIndicesWildcard],
            s.List(*list_items(match[s.FieldDerivativesWildcard]), index),
        )
        return matched + s.CDVariationParameter * derivative

    def bar_variation(match: dict[Expression, Expression]) -> Expression:
        matched = bar_pat.replace_wildcards(match)
        derivative = s.Bar(
            s.Field(
                match[s.FieldLabelWildcard],
                match[s.FieldTypeWildcard],
                match[s.FieldIndicesWildcard],
                s.List(*list_items(match[s.FieldDerivativesWildcard]), index),
            )
        )
        return matched + s.CDVariationParameter * derivative

    def field_strength_variation(match: dict[Expression, Expression]) -> Expression:
        matched = strength_pat.replace_wildcards(match)
        derivative = field_strength_with_derivatives(
            matched,
            (*list_items(match[s.FieldStrengthDerivativesWildcard]), index),
        )
        return matched + s.CDVariationParameter * derivative

    def bar_field_strength_variation(match: dict[Expression, Expression]) -> Expression:
        matched = bar_strength_pat.replace_wildcards(match)
        derivative = s.Bar(
            s.FieldStrength(
                match[s.FieldStrengthLabelWildcard],
                match[s.FieldStrengthLorentzWildcard],
                match[s.FieldStrengthIndicesWildcard],
                s.List(*list_items(match[s.FieldStrengthDerivativesWildcard]), index),
            )
        )
        return matched + s.CDVariationParameter * derivative

    def commutator_variation(match: dict[Expression, Expression]) -> Expression:
        matched = commutator_pat.replace_wildcards(match)
        body_derivative = _single_cd(index, match[s.CovariantCommutatorBodyWildcard])
        derivative = (
            Expression.num(0)
            if is_zero(body_derivative)
            else s.CovariantDerivativeCommutator(
                match[s.CovariantCommutatorLeftWildcard],
                match[s.CovariantCommutatorRightWildcard],
                body_derivative,
            )
        )
        return matched + s.CDVariationParameter * derivative

    def cd_variation(match: dict[Expression, Expression]) -> Expression:
        matched = cd_pat.replace_wildcards(match)
        body_derivative = _single_cd(index, match[s.CDBodyWildcard])
        derivative = Expression.num(0) if is_zero(body_derivative) else s.CD(match[s.CDIndexWildcard], body_derivative)
        return matched + s.CDVariationParameter * derivative

    def wilson_term_variation(match: dict[Expression, Expression]) -> Expression:
        matched = wilson_pat.replace_wildcards(match)
        derivative = s.WilsonTerm(
            match[s.WilsonTermFieldWildcard],
            match[s.WilsonTermLinkIndicesWildcard],
            s.List(*list_items(match[s.WilsonTermDerivativeIndicesWildcard]), index),
        )
        return matched + s.CDVariationParameter * derivative

    field_label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    field_strength_label_is_tagged = s.FieldStrengthLabelWildcard.req_tag(SymbolRole.FIELD.value)
    return (
        Replacement(cd_pat, cd_variation),
        Replacement(wilson_pat, wilson_term_variation),
        Replacement(commutator_pat, commutator_variation),
        Replacement(bar_strength_pat, bar_field_strength_variation, field_strength_label_is_tagged),
        Replacement(strength_pat, field_strength_variation, field_strength_label_is_tagged),
        Replacement(bar_pat, bar_variation, field_label_is_tagged),
        Replacement(field_pat, field_variation, field_label_is_tagged),
    )


def partial_functional_derivative(lagrangian: Expression, target_field: Expression) -> Expression:
    lagrangian = _expand_variation_bars(lagrangian)
    target_replacement = Replacement(target_field, target_field + s.FunctionalVariationParameter)
    bar_protector = Replacement(
        bar_field_pattern(),
        bar_field_pattern(),
        s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value),
    )
    replacements = (
        [target_replacement, bar_protector]
        if bool(target_field.matches(bar_field_pattern(), partial=False))
        else [bar_protector, target_replacement]
    )
    varied = lagrangian.replace_multiple(replacements)
    varied = _linearize_variation_wrappers(varied, s.FunctionalVariationParameter)
    return (
        varied.series(s.FunctionalVariationParameter, 0, 1)
        .to_expression()
        .coefficient(s.FunctionalVariationParameter)
        .expand()
    )


def _expand_variation_bars(expr: Expression) -> Expression:
    body_wildcard = s.CDBodyWildcard
    pattern = s.Bar(body_wildcard)
    out = expr
    for _ in range(16):
        updated = out.replace(pattern, _expanded_bar_replacement)
        if bool(updated == out):
            return updated
        out = updated.expand()
    return out


def _expanded_bar_replacement(match: dict[Expression, Expression]) -> Expression:
    return _bar_expr(match[s.CDBodyWildcard], generated=False)


def _bar_expr(body: Expression, *, generated: bool) -> Expression:
    kind = body.get_type()
    if kind is AtomType.Num:
        return body.conj()
    if kind is AtomType.Add:
        return sum_expr(_bar_expr(term, generated=True) for term in terms(body))
    if kind is AtomType.Mul:
        return product_expr(_bar_expr(factor, generated=True) for factor in factors(body))
    if is_head(body, s.Bar):
        return body[0]
    if is_head(body, s.Field):
        if generated and field_self_conjugate_from_label(field_label(body)):
            return body
        return s.Bar(body)
    if is_bar_field(body):
        return body
    if is_head(body, s.Coupling):
        spec = coupling_self_conjugate_from_label(body[0])
        return _conjugated_coupling(body, spec)
    if bool(body == s.PR):
        return s.PL
    if bool(body == s.PL):
        return s.PR
    if is_head(body, s.Gamma):
        return body
    if is_head(body, s.Proj):
        return s.Proj(s.Bar(body[0]))
    if is_head(body, s.DiracProduct):
        return s.DiracProduct(*(_bar_expr(arg, generated=True) for arg in reversed(args(body))))
    if is_head(body, s.NCM):
        return _chain_expr(*(_bar_expr(arg, generated=True) for arg in reversed(args(body))))
    return s.Bar(body)


def _conjugated_coupling(expr: Expression, spec: CouplingSelfConjugate) -> Expression:
    if spec is True:
        return expr
    if isinstance(spec, tuple):
        indices = list_items(expr[1])
        if len(indices) == len(spec):
            return s.Coupling(expr[0], s.List(*(indices[i - 1] for i in spec)), expr[2])
    return s.Bar(expr)


def _linearize_variation_wrappers(expr: Expression, parameter: Expression) -> Expression:
    expr = _linearize_external_function_variation(expr, parameter)
    return _linearize_noncommutative_variation(expr, parameter)


def _linearize_external_function_variation(expr: Expression, parameter: Expression) -> Expression:
    replacements: list[Replacement] = []
    for index, head in enumerate(linear_external_function_heads(expr)):
        body_wildcard = s.head(f"linear_external_body_{index}_")
        pattern = head(body_wildcard)
        replacements.append(
            Replacement(
                pattern,
                _external_function_variation_replacement(head, pattern, body_wildcard, parameter),
                rhs_cache_size=0,
            )
        )
    return expr.replace_multiple(replacements) if replacements else expr


def _external_function_variation_replacement(
    head: Expression,
    pattern: Expression,
    body_wildcard: Expression,
    parameter: Expression,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_function(match: dict[Expression, Expression]) -> Expression:
        body = match[body_wildcard]
        variation = _coefficient_of_parameter_power(body, parameter, 1)
        if is_zero(variation):
            return pattern.replace_wildcards(match)
        constant = _coefficient_of_parameter_power(body, parameter, 0)
        return (_call_linear_head(head, constant) + parameter * _call_linear_head(head, variation)).expand()

    return replace_function


def _call_linear_head(head: Expression, body: Expression) -> Expression:
    return Expression.num(0) if is_zero(body) else head(body)


def _linearize_noncommutative_variation(expr: Expression, parameter: Expression) -> Expression:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_MULTILINEAR_CHAIN_ARITY + 1):
        wildcards = _chain_wildcards(arity)
        pattern = s.NCM(*wildcards)
        replacements.append(
            Replacement(
                pattern,
                _chain_variation_replacement(pattern, wildcards, parameter),
                rhs_cache_size=0,
            )
        )
    return expr.replace_multiple(replacements)


def _chain_variation_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
    parameter: Expression,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_chain(match: dict[Expression, Expression]) -> Expression:
        return _linearized_chain_variation(pattern, wildcards, match, parameter)

    return replace_chain


def _linearized_chain_variation(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
    match: dict[Expression, Expression],
    parameter: Expression,
) -> Expression:
    operands = tuple(match[wildcard] for wildcard in wildcards)
    constants = tuple(_coefficient_of_parameter_power(operand, parameter, 0) for operand in operands)
    variations = tuple(_coefficient_of_parameter_power(operand, parameter, 1) for operand in operands)
    if all(is_zero(variation) for variation in variations):
        return pattern.replace_wildcards(match)
    base = _chain_expr(*constants)
    linear_terms = []
    for index, variation in enumerate(variations):
        if is_zero(variation):
            continue
        varied_operands = (*constants[:index], variation, *constants[index + 1 :])
        linear_terms.append(_chain_expr(*varied_operands))
    return (base + parameter * sum_expr(linear_terms)).expand()


def _chain_wildcards(arity: int) -> tuple[Expression, ...]:
    return tuple(s.head(f"ncm_operand_{arity}_{index}_") for index in range(arity))


def _coefficient_of_parameter_power(expr: Expression, parameter: Expression, power: int) -> Expression:
    target = Expression.num(1) if power == 0 else parameter**power
    for key, coefficient in expr.coefficient_list(parameter):
        if bool(key == target):
            return coefficient
    return Expression.num(0)


def _chain_expr(*operands: Expression) -> Expression:
    kept = tuple(operand for operand in operands if not is_zero(operand) and not bool(operand == Expression.num(1)))
    if len(kept) != len(operands):
        if any(is_zero(operand) for operand in operands):
            return Expression.num(0)
    if not kept:
        return Expression.num(1)
    if len(kept) == 1:
        return kept[0]
    return s.NCM(*kept)


def _field_derivative_sets(lagrangian: Expression, label: Expression, *, barred: bool) -> set[tuple[Expression, ...]]:
    pattern = bar_field_pattern(label) if barred else field_pattern(label)
    return {list_items(match[s.FieldDerivativesWildcard]) for match in lagrangian.match(pattern)}


def _field_derivative_sets_for_base(
    lagrangian: Expression,
    base: Expression,
    *,
    barred: bool,
) -> set[tuple[Expression, ...]]:
    pattern = _field_pattern_like(base)
    if barred:
        pattern = s.Bar(pattern)
    return {list_items(match[s.FieldDerivativesWildcard]) for match in lagrangian.match(pattern)}


def _field_pattern_like(base: Expression) -> Expression:
    return s.Field(field_label(base), field_type(base), base[2], s.FieldDerivativesWildcard)


def derive_eom(
    theory: Theory,
    lagrangian: Expression,
    field: FieldHandle | FieldDefinition | str | Expression,
    *,
    eft_order: int = 6,
    variation: FieldVariation | str = FieldVariation.AUTO,
) -> Expression:
    theory._validate_registered_expression(lagrangian)
    if isinstance(field, Expression):
        base = bar_field_inner(field) if is_bar_field(field) else field
        if not is_head(base, s.Field):
            raise ValueError(f"Euler-Lagrange variation target must be a Field expression, got {canonical_string(field)}")
        definition: FieldDefinition | None = None
        exact_base: Expression | None = base
        exact_barred = is_bar_field(field)
    else:
        if isinstance(field, str):
            definition = theory.fields[field]
        elif isinstance(field, FieldHandle):
            definition = field.definition
        else:
            definition = field
        exact_base = None
        exact_barred = False

    variation_mode = FieldVariation.from_user(variation)
    if variation_mode is FieldVariation.AUTO:
        if exact_base is not None:
            variation_mode = FieldVariation.BAR if exact_barred else FieldVariation.FIELD
        elif definition is not None:
            variation_mode = FieldVariation.FIELD if definition.is_self_conjugate else FieldVariation.BAR

    if variation_mode is FieldVariation.BAR:
        if exact_base is None:
            assert definition is not None
            derivative_sets = _field_derivative_sets(lagrangian, definition.label, barred=True)
        else:
            derivative_sets = _field_derivative_sets_for_base(lagrangian, exact_base, barred=True)
    else:
        if exact_base is None:
            assert definition is not None
            derivative_sets = _field_derivative_sets(lagrangian, definition.label, barred=False)
        else:
            derivative_sets = _field_derivative_sets_for_base(lagrangian, exact_base, barred=False)
    derivative_sets.add(())

    residual = Expression.num(0)
    if exact_base is None:
        assert definition is not None
        base = definition.expr()
    else:
        base = exact_base
    for derivatives in sorted(derivative_sets, key=lambda d: (len(d), tuple(canonical_string(x) for x in d))):
        target = field_with_derivatives(base, derivatives)
        if variation_mode is FieldVariation.BAR:
            target = s.Bar(target)
        partial = partial_functional_derivative(lagrangian, target)
        if len(derivatives) == 0:
            residual = residual + partial
        else:
            contribution = apply_cd(tuple(reversed(derivatives)), partial)
            residual = residual + ((-1) ** len(derivatives)) * contribution

    return residual.expand()


def eom_replacement_rule(
    theory: Theory,
    lagrangian: Expression,
    field: FieldHandle | FieldDefinition | str | Expression,
    *,
    solve_for: Expression,
    eft_order: int = 6,
    variation: FieldVariation | str = FieldVariation.AUTO,
) -> Replacement:
    """Build a Symbolica replacement rule by isolating ``solve_for`` in an EOM.

    The equation of motion is derived with :func:`derive_eom`, then the
    requested target is isolated with native ``Expression.coefficient(...)``.
    This is intended for on-shell reductions, where the returned
    :class:`symbolica.Replacement` can be passed directly to
    ``MatchingResult.with_on_shell_reduction(...)`` or
    ``OneLoopMatchOptions.on_shell_replacements``.
    """

    theory._validate_registered_expression(solve_for)
    eom = derive_eom(theory, lagrangian, field, eft_order=eft_order, variation=variation)
    coefficient = eom.coefficient(solve_for).expand()
    if is_zero(coefficient):
        raise ValueError(
            "Cannot build EOM replacement rule because the requested target "
            f"{canonical_string(solve_for)} is absent from the EOM"
        )
    remainder = (eom - coefficient * solve_for).expand()
    if bool(remainder.contains(solve_for)):
        raise ValueError(
            "Cannot build a linear EOM replacement rule because the EOM still "
            f"contains {canonical_string(solve_for)} after coefficient extraction"
        )
    return Replacement(solve_for, (-remainder / coefficient).expand())


def eom_replacement_rules_for_expression(
    theory: Theory,
    lagrangian: Expression,
    expression: Expression,
    *,
    fields: Iterable[FieldHandle | FieldDefinition | str | Expression] | None = None,
    eft_order: int = 6,
    variation: FieldVariation | str = FieldVariation.AUTO,
    min_derivative_order: int = 2,
    strict: bool = False,
) -> tuple[Replacement, ...]:
    """Build EOM replacement rules for derivative field atoms in ``expression``.

    Candidate targets are collected with Symbolica pattern matching over
    registered ``Field`` / ``Bar(Field)`` atoms. Each target is isolated through
    :func:`eom_replacement_rule`, so the returned rules remain native
    Symbolica ``Replacement`` objects suitable for ``replace_multiple``.
    """

    if min_derivative_order < 0:
        raise ValueError("min_derivative_order must be non-negative")
    theory._validate_registered_expression(expression)
    allowed_labels = _eom_rule_allowed_field_labels(theory, fields)
    rules: list[Replacement] = []
    failures: list[str] = []
    for target in _eom_rule_targets(
        expression,
        allowed_labels=allowed_labels,
        min_derivative_order=min_derivative_order,
    ):
        field = _eom_rule_base_field(target)
        try:
            rules.append(
                eom_replacement_rule(
                    theory,
                    lagrangian,
                    field,
                    solve_for=target,
                    eft_order=eft_order,
                    variation=variation,
                )
            )
        except ValueError as exc:
            if strict:
                failures.append(str(exc))
    if failures:
        raise ValueError("; ".join(failures))
    return tuple(rules)


def _eom_rule_allowed_field_labels(
    theory: Theory,
    fields: Iterable[FieldHandle | FieldDefinition | str | Expression] | None,
) -> set[str] | None:
    if fields is None:
        return None
    return {canonical_string(_field_label_from_user(theory, field)) for field in fields}


def _field_label_from_user(theory: Theory, field: FieldHandle | FieldDefinition | str | Expression) -> Expression:
    if isinstance(field, str):
        return theory.fields[field].label
    if isinstance(field, FieldHandle):
        return field.definition.label
    if isinstance(field, FieldDefinition):
        return field.label
    base = bar_field_inner(field) if is_bar_field(field) else field
    if not is_head(base, s.Field):
        raise ValueError(f"EOM replacement field filter must be a Field expression, got {canonical_string(field)}")
    return field_label(base)


def _eom_rule_targets(
    expression: Expression,
    *,
    allowed_labels: set[str] | None,
    min_derivative_order: int,
) -> tuple[Expression, ...]:
    label_is_registered_field = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    raw_targets = [
        *matching_subexpressions(expression, bar_field_pattern(), label_is_registered_field),
        *matching_subexpressions(expression, field_pattern(), label_is_registered_field),
    ]
    kept: dict[str, Expression] = {}
    for target in raw_targets:
        base = bar_field_inner(target) if is_bar_field(target) else target
        if allowed_labels is not None and canonical_string(field_label(base)) not in allowed_labels:
            continue
        if len(field_derivatives(base)) < min_derivative_order:
            continue
        kept.setdefault(canonical_string(target), target)
    return tuple(
        sorted(
            kept.values(),
            key=lambda target: (0 if is_bar_field(target) else 1, canonical_string(target)),
        )
    )


def _eom_rule_base_field(target: Expression) -> Expression:
    if is_bar_field(target):
        return s.Bar(field_with_derivatives(bar_field_inner(target), ()))
    return field_with_derivatives(target, ())


def eom_expression(theory: Theory, lagrangian: Expression, field: FieldHandle | FieldDefinition | str, *, eft_order: int = 6) -> Expression:
    definition = theory.fields[field] if isinstance(field, str) else field.definition if isinstance(field, FieldHandle) else field
    return s.EOM(definition.expr(), derive_eom(theory, lagrangian, definition, eft_order=eft_order))
