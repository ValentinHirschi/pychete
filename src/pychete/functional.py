from __future__ import annotations

from collections.abc import Callable

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .expr import (
    args,
    bar_field_inner,
    bar_field_pattern,
    cd_pattern,
    factors,
    field_pattern,
    field_label,
    field_type,
    field_with_derivatives,
    is_bar_field,
    is_head,
    is_zero,
    list_items,
    product_expr,
    sum_expr,
    terms,
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


def _single_cd(index: Expression, expr: Expression) -> Expression:
    varied = expr.replace_multiple(_cd_variation_replacements(index))
    varied = _linearize_variation_wrappers(varied, s.CDVariationParameter)
    return varied.series(s.CDVariationParameter, 0, 1).to_expression().coefficient(s.CDVariationParameter).expand()


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


def eom_expression(theory: Theory, lagrangian: Expression, field: FieldHandle | FieldDefinition | str, *, eft_order: int = 6) -> Expression:
    definition = theory.fields[field] if isinstance(field, str) else field.definition if isinstance(field, FieldHandle) else field
    return s.EOM(definition.expr(), derive_eom(theory, lagrangian, definition, eft_order=eft_order))
