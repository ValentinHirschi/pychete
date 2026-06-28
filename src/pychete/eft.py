from __future__ import annotations

from collections.abc import Callable
from functools import cache
from itertools import product

from symbolica import Expression, Replacement

from .expr import (
    as_int,
    bar_field_inner,
    bar_field_pattern,
    cd_pattern,
    coupling_pattern,
    field_derivatives,
    field_label,
    field_pattern,
    field_strength_pattern,
    field_type,
    is_bar_field,
    is_head,
    is_zero,
    list_items,
    matching_subexpressions,
    sum_expr,
)
from .linear_external import linear_external_function_heads
from .symbols import SymbolRole, canonical_string, s
from .theory import Theory
from .theory_metadata import FieldMassKind, field_mass_kind_from_label

_MAX_NCM_EFT_ARITY = 8


def type_dimension(type_expr: Expression) -> int | float:
    scaled = _scaled_type_dimension(type_expr)
    return scaled // 2 if scaled % 2 == 0 else scaled / 2


def _scaled_type_dimension(type_expr: Expression) -> int:
    return 3 if bool(type_expr == s.Fermion) else 2


def _coupling_order(expr: Expression) -> int:
    order = as_int(expr[2])
    if order is None:
        raise ValueError(f"Coupling EFT order is not an integer: {canonical_string(expr)}")
    return order


def _coupling_scaled_order(expr: Expression) -> int:
    return 2 * _coupling_order(expr)


def _marker_power(scaled_dimension: int) -> Expression:
    if scaled_dimension == 0:
        return Expression.num(1)
    if scaled_dimension == 1:
        return s.EFTExpansionParameter
    return s.EFTExpansionParameter**scaled_dimension


def _unscale_dimension(scaled_dimension: int) -> int | float:
    return scaled_dimension // 2 if scaled_dimension % 2 == 0 else scaled_dimension / 2


def _is_heavy_field_label(theory: Theory | None, label: Expression) -> bool:
    return field_mass_kind_from_label(label) is FieldMassKind.HEAVY


def _field_scaled_dimension(expr: Expression, theory: Theory | None, *, heavy_field_dimension: bool) -> int:
    dim = 2 * len(field_derivatives(expr)) + _scaled_type_dimension(field_type(expr))
    if heavy_field_dimension and _is_heavy_field_label(theory, field_label(expr)):
        dim += 2
    return dim


def _field_strength_scaled_dimension(expr: Expression) -> int:
    return 2 * len(list_items(expr[3])) + 4


def _cd_scaled_dimension(expr: Expression, theory: Theory | None, *, heavy_field_dimension: bool) -> int:
    indices = list_items(expr[0]) if is_head(expr[0], s.List) else (expr[0],)
    return _scaled_operator_dimension(expr[1], theory, heavy_field_dimension=heavy_field_dimension) + 2 * len(indices)


def _eom_scaled_dimension(expr: Expression, theory: Theory | None, *, heavy_field_dimension: bool) -> int:
    body = expr[0]
    base = bar_field_inner(body) if is_bar_field(body) else body
    if not is_head(base, s.Field):
        return 0
    derivative_shift = 2 if bool(field_type(base) == s.Fermion) else 4
    return _field_scaled_dimension(base, theory, heavy_field_dimension=heavy_field_dimension) + derivative_shift


def _eft_weight_replacements(theory: Theory | None, *, heavy_field_dimension: bool) -> tuple[Replacement, ...]:
    cd_pat = cd_pattern()
    bar_pat = bar_field_pattern()
    field_strength_pat = field_strength_pattern()
    field_pat = field_pattern()
    coupling_pat = coupling_pattern()

    def weighted(atom: Expression, scaled_dimension: int) -> Expression:
        return atom if scaled_dimension == 0 else atom * _marker_power(scaled_dimension)

    def cd_weight(match: dict[Expression, Expression]) -> Expression:
        atom = cd_pat.replace_wildcards(match)
        return weighted(atom, _cd_scaled_dimension(atom, theory, heavy_field_dimension=heavy_field_dimension))

    def bar_weight(match: dict[Expression, Expression]) -> Expression:
        atom = bar_pat.replace_wildcards(match)
        return weighted(atom, _field_scaled_dimension(bar_field_inner(atom), theory, heavy_field_dimension=heavy_field_dimension))

    def field_strength_weight(match: dict[Expression, Expression]) -> Expression:
        atom = field_strength_pat.replace_wildcards(match)
        return weighted(atom, _field_strength_scaled_dimension(atom))

    def field_weight(match: dict[Expression, Expression]) -> Expression:
        atom = field_pat.replace_wildcards(match)
        return weighted(atom, _field_scaled_dimension(atom, theory, heavy_field_dimension=heavy_field_dimension))

    def coupling_weight(match: dict[Expression, Expression]) -> Expression:
        atom = coupling_pat.replace_wildcards(match)
        return weighted(atom, _coupling_scaled_order(atom))

    field_label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    coupling_label_is_tagged = s.CouplingLabelWildcard.req_tag(SymbolRole.COUPLING.value)
    return (
        Replacement(cd_pat, cd_weight),
        Replacement(bar_pat, bar_weight, field_label_is_tagged),
        Replacement(field_strength_pat, field_strength_weight, s.FieldStrengthLabelWildcard.req_tag(SymbolRole.FIELD.value)),
        Replacement(field_pat, field_weight, field_label_is_tagged),
        Replacement(coupling_pat, coupling_weight, coupling_label_is_tagged),
    )


def _encode_eom_atoms_for_eft_weighting(
    expr: Expression,
    theory: Theory | None,
    *,
    heavy_field_dimension: bool,
) -> tuple[Expression, tuple[Replacement, ...], tuple[Replacement, ...]]:
    label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    atoms = (
        *matching_subexpressions(expr, s.EOM(field_pattern()), label_is_tagged),
        *matching_subexpressions(expr, s.EOM(bar_field_pattern()), label_is_tagged),
    )
    if not atoms:
        return expr, (), ()

    encode: list[Replacement] = []
    weight: list[Replacement] = []
    decode: list[Replacement] = []
    for index, atom in enumerate(sorted(set(atoms), key=canonical_string)):
        temp = s.head(f"eft_eom_atom_{index}")
        encode.append(Replacement(atom, temp))
        weight.append(
            Replacement(
                temp,
                temp * _marker_power(_eom_scaled_dimension(atom, theory, heavy_field_dimension=heavy_field_dimension)),
            )
        )
        decode.append(Replacement(temp, atom))
    return expr.replace_multiple(encode), tuple(weight), tuple(decode)


def _eft_weighted_expression(
    expr: Expression,
    theory: Theory | None,
    *,
    heavy_field_dimension: bool,
) -> Expression:
    encoded, eom_weight_replacements, eom_decode_replacements = _encode_eom_atoms_for_eft_weighting(
        expr,
        theory,
        heavy_field_dimension=heavy_field_dimension,
    )
    weighted = encoded.replace_multiple(
        (
            *eom_weight_replacements,
            *_eft_weight_replacements(theory, heavy_field_dimension=heavy_field_dimension),
        )
    )
    weighted = _extract_linear_external_eft_markers(weighted)
    weighted = _extract_ncm_eft_markers(weighted).expand()
    if eom_decode_replacements:
        weighted = weighted.replace_multiple(eom_decode_replacements).expand()
    return weighted


def _extract_linear_external_eft_markers(expr: Expression) -> Expression:
    replacements = _linear_external_eft_marker_replacements(expr)
    if not replacements:
        return expr
    out = expr
    for _ in range(8):
        updated = out.replace_multiple(replacements)
        if bool(updated == out):
            return updated
        out = updated.expand()
    return out


def _linear_external_eft_marker_replacements(expr: Expression) -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for index, head in enumerate(linear_external_function_heads(expr)):
        body_wildcard = s.head(f"eft_linear_external_body_{index}_")
        pattern = head(body_wildcard)
        replacements.append(
            Replacement(
                pattern,
                _linear_external_eft_marker_replacement(pattern, body_wildcard),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _linear_external_eft_marker_replacement(
    pattern: Expression,
    body_wildcard: Expression,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_function(match: dict[Expression, Expression]) -> Expression:
        terms = _marker_terms(match[body_wildcard])
        if len(terms) == 1 and terms[0][0] == 0:
            return pattern.replace_wildcards(match)
        expanded_terms = []
        for marker_power, coefficient in terms:
            if is_zero(coefficient):
                continue
            function_call = pattern.replace_wildcards({body_wildcard: coefficient})
            expanded_terms.append((_marker_power(marker_power) * function_call).expand())
        return sum_expr(expanded_terms).expand()

    return replace_function


def _extract_ncm_eft_markers(expr: Expression) -> Expression:
    return expr.replace_multiple(_ncm_eft_marker_replacements())


@cache
def _ncm_eft_marker_replacements() -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_NCM_EFT_ARITY + 1):
        wildcards = tuple(s.head(f"eft_ncm_operand_{arity}_{index}_") for index in range(arity))
        pattern = s.NCM(*wildcards)
        replacements.append(
            Replacement(
                pattern,
                _ncm_eft_marker_replacement(pattern, wildcards),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _ncm_eft_marker_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_ncm(match: dict[Expression, Expression]) -> Expression:
        operand_terms = tuple(_marker_terms(match[wildcard]) for wildcard in wildcards)
        if all(len(terms) == 1 and terms[0][0] == 0 for terms in operand_terms):
            return pattern.replace_wildcards(match)
        expanded_terms: list[Expression] = []
        for combination in product(*operand_terms):
            marker_power = sum(power for power, _coefficient in combination)
            coefficients = tuple(coefficient for _power, coefficient in combination)
            chain = _ncm_expr(*coefficients)
            if is_zero(chain):
                continue
            expanded_terms.append((_marker_power(marker_power) * chain).expand())
        return sum_expr(expanded_terms).expand()

    return replace_ncm


def _marker_terms(expr: Expression) -> tuple[tuple[int, Expression], ...]:
    terms: list[tuple[int, Expression]] = []
    for key, coefficient in expr.coefficient_list(s.EFTExpansionParameter):
        dimension = _marker_key_scaled_dimension(key)
        if dimension is None:
            terms.append((0, (key * coefficient).expand()))
        else:
            terms.append((dimension, coefficient))
    return tuple(terms) if terms else ((0, Expression.num(0)),)


def _ncm_expr(*operands: Expression) -> Expression:
    kept = tuple(operand for operand in operands if not is_zero(operand) and not bool(operand == Expression.num(1)))
    if len(kept) != len(operands) and any(is_zero(operand) for operand in operands):
        return Expression.num(0)
    if not kept:
        return Expression.num(1)
    if len(kept) == 1:
        return kept[0]
    return s.NCM(*kept)


def _marker_key_scaled_dimension(key: Expression) -> int | None:
    if bool(key == Expression.num(1)):
        return 0
    if bool(key == s.EFTExpansionParameter):
        return 1

    pattern = s.EFTExpansionParameter ** s.PowExponentWildcard
    for match in key.match(pattern):
        n = as_int(match[s.PowExponentWildcard])
        if n is not None:
            return n
    return None


def _scaled_operator_dimension(expr: Expression, theory: Theory | None, *, heavy_field_dimension: bool) -> int:
    weighted = _eft_weighted_expression(expr, theory, heavy_field_dimension=heavy_field_dimension).expand()
    dimensions = [
        dimension
        for key, _ in weighted.coefficient_list(s.EFTExpansionParameter)
        if (dimension := _marker_key_scaled_dimension(key)) is not None
    ]
    return min(dimensions, default=0)


def _select_weighted_eft_terms(weighted: Expression, scaled_order: int, *, exact: bool) -> Expression:
    selected = (
        coefficient
        for key, coefficient in weighted.coefficient_list(s.EFTExpansionParameter)
        if (dimension := _marker_key_scaled_dimension(key)) is not None
        and ((dimension == scaled_order) if exact else (dimension <= scaled_order))
    )
    return sum_expr(selected).expand()


def operator_dimension(expr: Expression, theory: Theory | None = None, *, heavy_field_dimension: bool = True) -> float:
    """Return the minimum EFT operator dimension appearing in ``expr``."""

    return _unscale_dimension(_scaled_operator_dimension(expr, theory, heavy_field_dimension=heavy_field_dimension))


def series_eft(
    expr: Expression,
    theory: Theory | None = None,
    *,
    eft_order: int | tuple[int, ...],
    heavy_field_dimension: bool = True,
) -> Expression:
    """Truncate or select terms by EFT order.

    Passing an integer keeps terms below that order. Passing a one-item tuple,
    such as ``(6,)``, selects exactly that EFT order.
    """

    if isinstance(eft_order, tuple):
        if len(eft_order) != 1:
            raise ValueError("exact EFT order must be passed as a one-item tuple")
        exact = True
        order = eft_order[0]
    else:
        exact = False
        order = eft_order
    scaled_order = 2 * order
    weighted = _eft_weighted_expression(expr, theory, heavy_field_dimension=heavy_field_dimension).expand()
    return _select_weighted_eft_terms(weighted, scaled_order, exact=exact)
