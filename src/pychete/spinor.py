from __future__ import annotations

from enum import StrEnum

from symbolica import Expression, PatternRestriction
from symbolica.core import AtomType

from .expr import args, factors, field_derivatives, field_label, field_type, field_with_derivatives, is_bar_field, is_head, product_expr, terms
from .symbols import canonical_string, s
from .theory import coupling_self_conjugate_from_label, field_self_conjugate_from_label, field_type_from_label


class SpinChainKind(StrEnum):
    """Endpoint classification for a pychete noncommutative spinor chain."""

    SCALAR = "scalar"
    MATRIX = "matrix"
    LEFT_OPEN = "left_open"
    RIGHT_OPEN = "right_open"
    CLOSED = "closed"


def _seq_items(expr: Expression) -> tuple[Expression, ...]:
    if expr.get_type() is AtomType.Fn and expr.get_name() == "symbolica::arg":
        return tuple(expr[i] for i in range(len(expr)))
    return (expr,)


def _is_field(expr: Expression) -> bool:
    return is_head(expr, s.Field)


def is_fermion_field(expr: Expression) -> bool:
    """Return whether ``expr`` is a pychete fermion ``Field`` expression."""

    return _is_field(expr) and bool(field_type_from_label(expr[0]) == s.Fermion)


def is_barred_fermion(expr: Expression) -> bool:
    """Return whether ``expr`` is ``Bar`` applied to a fermion ``Field``."""

    return is_bar_field(expr) and is_fermion_field(expr[0])


def is_dirac_atom(expr: Expression) -> bool:
    """Return whether ``expr`` is a Dirac-space atom used in NCM chains."""

    return bool(expr == s.PR) or bool(expr == s.PL) or is_head(expr, s.Gamma) or is_head(expr, s.Proj) or is_head(expr, s.DiracProduct)


def _is_commutative_field(expr: Expression) -> bool:
    return _is_field(expr) and not bool(field_type_from_label(expr[0]) == s.Fermion)


def is_commutative_spin_factor(expr: Expression) -> bool:
    """Return whether an expression can be pulled out of a spinor ``NCM`` chain."""

    kind = expr.get_type()
    if kind is AtomType.Num:
        return True
    if bool(expr == s.PR) or bool(expr == s.PL):
        return False
    if kind is AtomType.Var:
        return True
    if is_head(expr, s.NCM) or is_head(expr, s.DiracProduct) or is_head(expr, s.Gamma) or is_head(expr, s.Proj):
        return False
    if is_bar_field(expr):
        return not is_fermion_field(expr[0])
    if is_head(expr, s.Bar):
        return is_commutative_spin_factor(expr[0])
    if _is_commutative_field(expr):
        return True
    if is_head(expr, s.Coupling) or is_head(expr, s.FieldStrength) or is_head(expr, s.Delta) or is_head(expr, s.Metric) or is_head(expr, s.CG):
        return True
    if is_head(expr, s.CD):
        return is_commutative_spin_factor(expr[1])
    if kind is AtomType.Add:
        return all(is_commutative_spin_factor(item) for item in args(expr))
    if kind is AtomType.Mul:
        return all(is_commutative_spin_factor(item) for item in factors(expr))
    if kind is AtomType.Pow:
        return is_commutative_spin_factor(expr[0])
    return False


def _split_commutative_factor(expr: Expression) -> tuple[Expression, Expression | None]:
    if is_commutative_spin_factor(expr):
        return expr, None
    if expr.get_type() is not AtomType.Mul:
        return Expression.num(1), expr

    commutative: list[Expression] = []
    ordered: list[Expression] = []
    for factor in factors(expr):
        if is_commutative_spin_factor(factor):
            commutative.append(factor)
        else:
            ordered.append(factor)

    scalar = product_expr(commutative)
    rest = product_expr(ordered) if ordered else None
    return scalar, rest


def _opposite_projector(expr: Expression) -> Expression:
    if bool(expr == s.PR):
        return s.PL
    if bool(expr == s.PL):
        return s.PR
    raise ValueError(f"Expected chiral projector, got {canonical_string(expr)}")


def _simplify_projectors(items: list[Expression]) -> tuple[Expression, ...] | None:
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(items) - 1:
            left = items[i]
            right = items[i + 1]
            if (bool(left == s.PL) and bool(right == s.PL)) or (bool(left == s.PR) and bool(right == s.PR)):
                del items[i + 1]
                changed = True
                continue
            if (bool(left == s.PL) and bool(right == s.PR)) or (bool(left == s.PR) and bool(right == s.PL)):
                return None
            if (bool(left == s.PL) or bool(left == s.PR)) and is_head(right, s.Gamma):
                items[i : i + 2] = [right, _opposite_projector(left)]
                changed = True
                continue
            i += 1
    return tuple(items)


def _ncm_from_items(items: tuple[Expression, ...]) -> Expression:
    if not items:
        return Expression.num(1)
    if len(items) == 1:
        return items[0]
    return s.NCM(*items)


def _normalize_ncm_match(match: dict[Expression, Expression]) -> Expression:
    raw_factors = _seq_items(match[s.NCMInnerWildcard])
    scalar = Expression.num(1)
    ordered: list[Expression] = []
    for factor in raw_factors:
        if is_head(factor, s.NCM) or is_head(factor, s.DiracProduct):
            nested = tuple(factor[i] for i in range(len(factor)))
            for item in nested:
                item_scalar, item_rest = _split_commutative_factor(item)
                scalar = scalar * item_scalar
                if item_rest is not None:
                    ordered.append(item_rest)
            continue

        factor_scalar, factor_rest = _split_commutative_factor(factor)
        scalar = scalar * factor_scalar
        if factor_rest is not None:
            ordered.append(factor_rest)

    simplified = _simplify_projectors(ordered)
    if simplified is None:
        return Expression.num(0)
    return (scalar * _ncm_from_items(simplified)).expand()


def normalize_ncm(expr: Expression) -> Expression:
    """Normalize pychete noncommutative products with Symbolica replacements."""

    pattern = s.NCM(s.NCMInnerWildcard)
    out = expr.replace(s.NCM(), Expression.num(1))
    for _ in range(20):
        new = out.replace(pattern, _normalize_ncm_match).expand()
        if bool(new == out):
            return new
        out = new
    return out


def ncm_expr(*items: Expression) -> Expression:
    """Build and normalize a pychete noncommutative product."""

    return normalize_ncm(s.NCM(*items))


def _bar_atom(body: Expression) -> Expression:
    if bool(body == s.PR):
        return s.PL
    if bool(body == s.PL):
        return s.PR
    if is_head(body, s.Gamma):
        return body
    if is_head(body, s.NCM) or is_head(body, s.DiracProduct):
        return ncm_expr(*(bar_expr(item) for item in reversed(tuple(body[i] for i in range(len(body))))))
    if is_head(body, s.Bar):
        return body[0]
    if is_head(body, s.Field):
        return body if field_self_conjugate_from_label(body[0]) else s.Bar(body)
    if is_head(body, s.Coupling):
        return body if coupling_self_conjugate_from_label(body[0]) else s.Bar(body)
    if is_head(body, s.CD):
        return s.CD(body[0], bar_expr(body[1]))
    if is_head(body, s.FieldStrength):
        return body
    if body.get_type() is AtomType.Num:
        return body
    return s.Bar(body)


def _bar_conj_match(match: dict[Expression, Expression]) -> Expression:
    return _bar_atom(match[s.ConjBodyWildcard])


def bar_expr(expr: Expression) -> Expression:
    """Return the pychete Hermitian conjugate of an expression.

    Symbolica's native ``conj`` distributes over the commutative envelope. This
    helper then converts the remaining conjugated pychete atoms, including
    reversed ``NCM`` chains, back into the canonical pychete representation.
    """

    out = expr.conj()
    conj_pattern = s.SymbolicaConj(s.ConjBodyWildcard)
    for _ in range(20):
        new = out.replace(conj_pattern, _bar_conj_match).expand()
        new = normalize_ncm(new)
        if bool(new == out):
            return new
        out = new
    return out


def spin_chain_kind(expr: Expression) -> SpinChainKind:
    """Classify the endpoint structure of a pychete spinor chain."""

    normalized = normalize_ncm(expr)
    if normalized.get_type() is AtomType.Mul:
        candidates = tuple(factor for factor in factors(normalized) if not is_commutative_spin_factor(factor))
        if len(candidates) == 1:
            normalized = candidates[0]

    if is_head(normalized, s.NCM):
        items = tuple(normalized[i] for i in range(len(normalized)))
    elif is_fermion_field(normalized) or is_barred_fermion(normalized) or is_dirac_atom(normalized):
        items = (normalized,)
    else:
        noncommutative = tuple(factor for factor in factors(normalized) if not is_commutative_spin_factor(factor))
        items = noncommutative or (normalized,)

    if not items or all(is_commutative_spin_factor(item) for item in items):
        return SpinChainKind.SCALAR

    left_bar = is_barred_fermion(items[0])
    right_field = is_fermion_field(items[-1])
    has_spin_atom = any(is_dirac_atom(item) or is_fermion_field(item) or is_barred_fermion(item) for item in items)
    if left_bar and right_field:
        return SpinChainKind.CLOSED
    if left_bar:
        return SpinChainKind.RIGHT_OPEN
    if right_field:
        return SpinChainKind.LEFT_OPEN
    return SpinChainKind.MATRIX if has_spin_atom else SpinChainKind.SCALAR


def _is_plain_scalar_field(expr: Expression) -> bool:
    return is_head(expr, s.Field) and bool(field_type(expr) == s.Scalar) and field_derivatives(expr) == ()


def _field_power_base_and_exponent(expr: Expression) -> tuple[Expression, int] | None:
    if expr.get_type() is AtomType.Pow and _is_plain_scalar_field(expr[0]):
        try:
            exponent = int(expr[1])
        except (TypeError, ValueError):
            return None
        return expr[0], exponent
    if _is_plain_scalar_field(expr):
        return expr, 1
    return None


def _same_field_without_derivatives(left: Expression, right: Expression) -> bool:
    return is_head(left, s.Field) and is_head(right, s.Field) and bool(field_label(left) == field_label(right)) and bool(field_type(left) == field_type(right)) and bool(left[2] == right[2])


def _term_zero(expr: Expression) -> bool:
    return bool(expr.expand() == Expression.num(0))


def _parse_current_derivative_term(term: Expression) -> tuple[Expression, Expression, Expression, Expression, Expression, Expression, Expression] | None:
    scalar_field: Expression | None = None
    derivative_field: Expression | None = None
    chain: Expression | None = None
    rest: list[Expression] = []

    for factor in factors(term):
        if is_head(factor, s.NCM):
            chain = factor if chain is None else None
            if chain is None:
                return None
            continue
        power = _field_power_base_and_exponent(factor)
        if power is not None and power[1] == 1:
            scalar_field = power[0] if scalar_field is None else scalar_field
            if not bool(scalar_field == power[0]):
                rest.append(factor)
            continue
        if is_head(factor, s.Field) and bool(field_type(factor) == s.Scalar) and len(field_derivatives(factor)) == 1:
            derivative_field = factor if derivative_field is None else derivative_field
            if derivative_field is not factor:
                return None
            continue
        rest.append(factor)

    if scalar_field is None or derivative_field is None or chain is None:
        return None
    if not _same_field_without_derivatives(scalar_field, derivative_field):
        return None
    mu = field_derivatives(derivative_field)[0]
    if len(chain) != 4:
        return None
    barred, gamma, projector, fermion = (chain[i] for i in range(4))
    if not is_barred_fermion(barred) or not is_head(gamma, s.Gamma) or not (bool(projector == s.PL) or bool(projector == s.PR)) or not is_fermion_field(fermion):
        return None
    if not bool(gamma[0] == mu):
        return None
    coefficient = product_expr(rest)
    return coefficient, scalar_field, mu, barred, gamma, projector, fermion


def canonicalize_fermion_derivative_bilinears(expr: Expression) -> Expression:
    """Canonize first-derivative closed fermion bilinears to Matchete's raw form."""

    expanded = normalize_ncm(expr.expand())
    term_list = list(terms(expanded))
    used = [False] * len(term_list)
    out = Expression.num(0)

    for i, term in enumerate(term_list):
        if used[i]:
            continue
        parsed = _parse_current_derivative_term(term)
        if parsed is None:
            out = out + term
            used[i] = True
            continue

        coefficient, scalar_field, mu, barred, gamma, projector, fermion = parsed
        derivative_fermion = field_with_derivatives(fermion, (*field_derivatives(fermion), mu))
        companion = normalize_ncm(coefficient * scalar_field**2 * ncm_expr(barred, gamma, projector, derivative_fermion))
        companion_index: int | None = None
        for j in range(i + 1, len(term_list)):
            if not used[j] and _term_zero(term_list[j] - companion):
                companion_index = j
                break

        if companion_index is None:
            out = out + term
            used[i] = True
            continue

        barred_derivative = s.Bar(field_with_derivatives(barred[0], (*field_derivatives(barred[0]), mu)))
        raw = coefficient * scalar_field**2 * (
            ncm_expr(barred, gamma, projector, derivative_fermion)
            - ncm_expr(barred_derivative, gamma, projector, fermion)
        ) / 2
        out = out + raw
        used[i] = True
        used[companion_index] = True

    return normalize_ncm(out.expand())


def ncm_contains_target(match: dict[Expression, Expression], target: Expression) -> int:
    """Pattern restriction helper returning true when an NCM match contains ``target``."""

    items = _seq_items(match.get(s.NCMInnerWildcard, Expression.num(0)))
    return 1 if any(bool(item == target) for item in items) else -1


def ncm_target_restriction(target: Expression) -> PatternRestriction:
    """Build a native Symbolica restriction for NCM chains containing ``target``."""

    return PatternRestriction.req_matches(lambda match: ncm_contains_target(match, target))
