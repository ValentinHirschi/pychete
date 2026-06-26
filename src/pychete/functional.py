from __future__ import annotations

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .expr import (
    bar_field_pattern,
    cd_pattern,
    derivative_indices_expr,
    field_pattern,
    field_with_derivatives,
    is_zero,
    list_items,
)
from .symbols import SymbolRole, canonical_string, s
from .spinor import is_barred_fermion, is_fermion_field, ncm_expr, ncm_target_restriction, normalize_ncm
from .theory import FieldDefinition, FieldHandle, FieldVariation, Theory


def _normalize_functional_expression(expr: Expression) -> Expression:
    return normalize_ncm(expr)


def apply_cd(indices: tuple[Expression, ...] | list[Expression], expr: Expression) -> Expression:
    out = expr
    for index in indices:
        out = _normalize_functional_expression(_single_cd(index, out))
    return out


def _single_cd(index: Expression, expr: Expression) -> Expression:
    varied = normalize_ncm(expr.replace_multiple(_cd_variation_replacements(index)))
    return _normalize_functional_expression(varied.series(s.CDVariationParameter, 0, 1).to_expression().coefficient(s.CDVariationParameter))


def _cd_variation_replacements(index: Expression) -> tuple[Replacement, ...]:
    field_pat = field_pattern()
    bar_pat = bar_field_pattern()
    cd_pat = cd_pattern()

    def field_variation(match: dict[Expression, Expression]) -> Expression:
        matched = field_pat.replace_wildcards(match)
        derivative = s.Field(
            match[s.FieldLabelWildcard],
            match[s.FieldTypeWildcard],
            match[s.FieldIndicesWildcard],
            derivative_indices_expr(*list_items(match[s.FieldDerivativesWildcard]), index),
        )
        return matched + s.CDVariationParameter * derivative

    def bar_variation(match: dict[Expression, Expression]) -> Expression:
        matched = bar_pat.replace_wildcards(match)
        derivative = s.Bar(
            s.Field(
                match[s.FieldLabelWildcard],
                match[s.FieldTypeWildcard],
                match[s.FieldIndicesWildcard],
                derivative_indices_expr(*list_items(match[s.FieldDerivativesWildcard]), index),
            )
        )
        return matched + s.CDVariationParameter * derivative

    def cd_variation(match: dict[Expression, Expression]) -> Expression:
        matched = cd_pat.replace_wildcards(match)
        body_derivative = _single_cd(index, match[s.CDBodyWildcard])
        derivative = Expression.num(0) if is_zero(body_derivative) else s.CD(match[s.CDIndexWildcard], body_derivative)
        return matched + s.CDVariationParameter * derivative

    field_label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    return (
        Replacement(cd_pat, cd_variation),
        Replacement(bar_pat, bar_variation, field_label_is_tagged),
        Replacement(field_pat, field_variation, field_label_is_tagged),
    )


def partial_functional_derivative(lagrangian: Expression, target_field: Expression) -> Expression:
    ncm_pat = s.NCM(s.NCMInnerWildcard)

    def is_fermionic_target(expr: Expression) -> bool:
        return is_fermion_field(expr) or is_barred_fermion(expr)

    def ncm_items(match: dict[Expression, Expression]) -> tuple[Expression, ...]:
        matched = match[s.NCMInnerWildcard]
        if matched.get_type() is AtomType.Fn and matched.get_name() == "symbolica::arg":
            return tuple(matched[i] for i in range(len(matched)))
        return (matched,)

    def ncm_variation(match: dict[Expression, Expression]) -> Expression:
        items = ncm_items(match)
        derivative = Expression.num(0)
        for index, item in enumerate(items):
            if not bool(item == target_field):
                continue
            preceding_fermions = sum(
                1
                for previous in items[:index]
                if is_fermion_field(previous) or is_barred_fermion(previous)
            )
            sign = -1 if preceding_fermions % 2 else 1
            derivative = derivative + sign * ncm_expr(*(items[:index] + items[index + 1 :]))
        return ncm_expr(*items) + s.FunctionalVariationParameter * derivative

    target_replacement = Replacement(target_field, target_field + s.FunctionalVariationParameter)
    bar_protector = Replacement(
        bar_field_pattern(),
        bar_field_pattern(),
        s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value),
    )
    ncm_replacement = Replacement(ncm_pat, ncm_variation, ncm_target_restriction(target_field))
    replacements = (
        [ncm_replacement, target_replacement, bar_protector]
        if bool(target_field.matches(bar_field_pattern(), partial=False))
        else [ncm_replacement, bar_protector, target_replacement]
        if is_fermionic_target(target_field)
        else [bar_protector, target_replacement]
    )
    varied = normalize_ncm(lagrangian.replace_multiple(replacements))
    return _normalize_functional_expression(
        varied.series(s.FunctionalVariationParameter, 0, 1)
        .to_expression()
        .coefficient(s.FunctionalVariationParameter)
    )


def _field_derivative_sets(lagrangian: Expression, label: Expression, *, barred: bool) -> set[tuple[Expression, ...]]:
    pattern = bar_field_pattern(label) if barred else field_pattern(label)
    return {list_items(match[s.FieldDerivativesWildcard]) for match in lagrangian.match(pattern)}


def derive_eom(
    theory: Theory,
    lagrangian: Expression,
    field: FieldHandle | FieldDefinition | str,
    *,
    eft_order: int = 6,
    variation: FieldVariation | str = FieldVariation.AUTO,
) -> Expression:
    theory._validate_registered_expression(lagrangian)
    if isinstance(field, str):
        definition = theory.fields[field]
    elif isinstance(field, FieldHandle):
        definition = field.definition
    else:
        definition = field

    variation_mode = FieldVariation.from_user(variation)
    if variation_mode is FieldVariation.AUTO:
        variation_mode = FieldVariation.FIELD if definition.is_self_conjugate else FieldVariation.BAR

    if variation_mode is FieldVariation.BAR:
        derivative_sets = _field_derivative_sets(lagrangian, definition.label, barred=True)
    else:
        derivative_sets = _field_derivative_sets(lagrangian, definition.label, barred=False)
    derivative_sets.add(())

    residual = Expression.num(0)
    base = definition.expr()
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

    return _normalize_functional_expression(residual)


def eom_expression(theory: Theory, lagrangian: Expression, field: FieldHandle | FieldDefinition | str, *, eft_order: int = 6) -> Expression:
    definition = theory.fields[field] if isinstance(field, str) else field.definition if isinstance(field, FieldHandle) else field
    return s.EOM(definition.expr(), derive_eom(theory, lagrangian, definition, eft_order=eft_order))
