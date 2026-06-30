from __future__ import annotations

from enum import StrEnum
from itertools import combinations

from symbolica import Expression, PatternRestriction
from symbolica.core import AtomType

from .expr import args, factors, field_derivatives, field_label, field_type, field_with_derivatives, index_pattern, is_bar_field, is_head, product_expr, sum_expr, terms
from .serialization import canonical_string
from .symbols import s
from .theory import coupling_self_conjugate_from_label, field_self_conjugate_from_label, field_type_from_label


class SpinChainKind(StrEnum):
    """Endpoint classification for a pychete noncommutative spinor chain."""

    SCALAR = "scalar"
    MATRIX = "matrix"
    LEFT_OPEN = "left_open"
    RIGHT_OPEN = "right_open"
    CLOSED = "closed"


_FIELD_HEAD = s.Field.get_name()
_BAR_HEAD = s.Bar.get_name()
_CD_HEAD = s.CD.get_name()
_DIRAC_ATOM_HEADS = frozenset(
    {
        s.DiracProduct.get_name(),
        s.Gamma.get_name(),
        s.PL.get_name(),
        s.PR.get_name(),
    }
)
_DIRAC_MATRIX_ATOM_HEADS = frozenset(
    {
        s.Gamma.get_name(),
        s.PL.get_name(),
        s.PR.get_name(),
    }
)
_NONCOMMUTATIVE_SPIN_HEADS = frozenset({s.DiracProduct.get_name(), s.NCM.get_name()})


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

    kind = expr.get_type()
    return (kind is AtomType.Fn or kind is AtomType.Var) and expr.get_name() in _DIRAC_ATOM_HEADS


def _is_dirac_matrix_atom(expr: Expression) -> bool:
    kind = expr.get_type()
    return (kind is AtomType.Fn or kind is AtomType.Var) and expr.get_name() in _DIRAC_MATRIX_ATOM_HEADS


def is_commutative_spin_factor(expr: Expression) -> bool:
    """Return whether ``expr`` is commutative in canonical spinor expressions."""

    kind = expr.get_type()
    if kind is AtomType.Num:
        return True
    if kind is AtomType.Var:
        return expr.get_name() not in _NONCOMMUTATIVE_SPIN_HEADS

    if kind is AtomType.Add:
        return all(is_commutative_spin_factor(item) for item in args(expr))
    if kind is AtomType.Mul:
        return all(is_commutative_spin_factor(item) for item in factors(expr))
    if kind is AtomType.Pow:
        return is_commutative_spin_factor(expr[0])
    if kind is not AtomType.Fn:
        return True

    head_name = expr.get_name()
    if head_name in _NONCOMMUTATIVE_SPIN_HEADS:
        return False
    if head_name == _FIELD_HEAD:
        return not bool(field_type_from_label(expr[0]) == s.Fermion)
    if head_name == _BAR_HEAD:
        return is_commutative_spin_factor(expr[0])
    if head_name == _CD_HEAD:
        return is_commutative_spin_factor(expr[1])
    return True


def _split_ncm_factor(expr: Expression) -> tuple[Expression, Expression | None]:
    if _is_dirac_matrix_atom(expr):
        return Expression.num(1), expr
    if is_commutative_spin_factor(expr):
        return expr, None
    if expr.get_type() is not AtomType.Mul:
        return Expression.num(1), expr

    commutative: list[Expression] = []
    ordered: list[Expression] = []
    for factor in factors(expr):
        if _is_dirac_matrix_atom(factor) or not is_commutative_spin_factor(factor):
            ordered.append(factor)
        else:
            commutative.append(factor)

    scalar = product_expr(commutative)
    rest = product_expr(ordered) if ordered else None
    return scalar, rest


def _opposite_projector(expr: Expression) -> Expression:
    if bool(expr == s.PR):
        return s.PL
    if bool(expr == s.PL):
        return s.PR
    raise ValueError(f"Expected chiral projector, got {canonical_string(expr)}")


def _is_projector(expr: Expression) -> bool:
    return bool(expr == s.PL) or bool(expr == s.PR)


def _is_lorentz_index(expr: Expression) -> bool:
    return is_head(expr, s.Index) and bool(expr[1] == s.Lorentz)


def _gamma_lorentz_indices(expr: Expression) -> tuple[Expression, ...] | None:
    if not is_head(expr, s.Gamma):
        return None
    indices = tuple(expr[i] for i in range(len(expr)))
    return indices if all(_is_lorentz_index(index) for index in indices) else None


def _dirac_gamma_grade(expr: Expression) -> int:
    indices = _gamma_lorentz_indices(expr)
    return len(indices) if indices is not None else 1


def _projector_moved_through_gamma(projector: Expression, gamma: Expression) -> Expression:
    return _opposite_projector(projector) if _dirac_gamma_grade(gamma) % 2 else projector


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
                items[i : i + 2] = [right, _projector_moved_through_gamma(left, right)]
                changed = True
                continue
            i += 1
    return tuple(items)


def _dirac_product_from_items(items: tuple[Expression, ...]) -> Expression:
    if not items:
        return Expression.num(1)
    return s.DiracProduct(*items)


def _ncm_from_items(items: tuple[Expression, ...]) -> Expression:
    if not items:
        return Expression.num(1)
    if len(items) == 1:
        return items[0]
    return s.NCM(*items)


def _flatten_dirac_product(factor: Expression) -> tuple[Expression, tuple[Expression, ...]]:
    scalar = Expression.num(1)
    items: list[Expression] = []
    for child in tuple(factor[i] for i in range(len(factor))):
        child_scalar, child_rest = _split_ncm_factor(child)
        scalar = scalar * child_scalar
        if child_rest is None:
            continue
        if is_head(child_rest, s.DiracProduct):
            nested_scalar, nested_items = _flatten_dirac_product(child_rest)
            scalar = scalar * nested_scalar
            items.extend(nested_items)
            continue
        items.append(child_rest)
    return scalar, tuple(items)


def _canonicalize_dirac_segments(items: tuple[Expression, ...]) -> tuple[Expression, tuple[Expression, ...]] | None:
    scalar = Expression.num(1)
    output: list[Expression] = []
    segment: list[Expression] = []

    def flush_segment() -> bool:
        if not segment:
            return True
        simplified = _simplify_projectors(segment)
        if simplified is None:
            return False
        output.append(_dirac_product_from_items(simplified))
        segment.clear()
        return True

    for item in items:
        if is_head(item, s.DiracProduct):
            item_scalar, flattened = _flatten_dirac_product(item)
            scalar = scalar * item_scalar
            for flattened_item in flattened:
                if _is_dirac_matrix_atom(flattened_item):
                    segment.append(flattened_item)
                    continue
                if not flush_segment():
                    return None
                output.append(flattened_item)
            continue
        if _is_dirac_matrix_atom(item):
            segment.append(item)
            continue
        if not flush_segment():
            return None
        output.append(item)

    if not flush_segment():
        return None
    return scalar, tuple(output)


def _nested_closed_spinor_line(items: tuple[Expression, ...]) -> tuple[int, int] | None:
    if len(items) < 4 or not is_barred_fermion(items[0]) or not is_fermion_field(items[-1]):
        return None

    for left in range(1, len(items) - 1):
        if not is_barred_fermion(items[left]):
            continue
        for right in range(left + 1, len(items) - 1):
            if is_fermion_field(items[right]):
                return left, right
    return None


def _split_nested_spinor_lines(items: tuple[Expression, ...]) -> Expression:
    nested = _nested_closed_spinor_line(items)
    if nested is None:
        return _ncm_from_items(items)

    left, right = nested
    inner = items[left : right + 1]
    outer = items[:left] + items[right + 1 :]
    return normalize_ncm(_ncm_from_items(outer)) * normalize_ncm(_ncm_from_items(inner))


def _normalize_ncm_match(match: dict[Expression, Expression]) -> Expression:
    raw_factors = _seq_items(match[s.NCMInnerWildcard])
    scalar = Expression.num(1)
    ordered: list[Expression] = []
    for factor in raw_factors:
        if is_head(factor, s.NCM):
            nested = tuple(factor[i] for i in range(len(factor)))
            for item in nested:
                item_scalar, item_rest = _split_ncm_factor(item)
                scalar = scalar * item_scalar
                if item_rest is not None:
                    ordered.append(item_rest)
            continue

        factor_scalar, factor_rest = _split_ncm_factor(factor)
        scalar = scalar * factor_scalar
        if factor_rest is not None:
            ordered.append(factor_rest)

    canonical = _canonicalize_dirac_segments(tuple(ordered))
    if canonical is None:
        return Expression.num(0)
    dirac_scalar, dirac_items = canonical
    return (scalar * dirac_scalar * _split_nested_spinor_lines(dirac_items)).expand()


def normalize_ncm(expr: Expression) -> Expression:
    """Normalize pychete noncommutative products with Symbolica replacements.

    Consecutive Dirac-space matrix atoms are collected into ``DiracProduct``
    segments inside the surrounding spinor ``NCM`` chain.
    """

    pattern = s.NCM(s.NCMInnerWildcard)
    out = expr.replace(s.NCM(), Expression.num(1))
    for _ in range(20):
        new = out.replace(pattern, _normalize_ncm_match).expand()
        if bool(new == out):
            return new
        out = new
    return out


def ncm_expr(*items: Expression) -> Expression:
    """Build and normalize a pychete noncommutative product.

    ``Gamma``, ``PL``, and ``PR`` inputs may be passed directly; normalization
    collects consecutive Dirac-space atoms into ``DiracProduct`` segments.
    """

    return normalize_ncm(s.NCM(*items))


DiracPosition = tuple[int, int]
DiracPairing = tuple[tuple[DiracPosition, DiracPosition], ...]


def _permutation_signature(ranks: tuple[int, ...]) -> int:
    sign = 1
    for i, rank in enumerate(ranks):
        for later in ranks[i + 1 :]:
            if rank > later:
                sign = -sign
    return sign


def _metric(left: Expression, right: Expression) -> Expression:
    return s.Metric(left, right)


def _non_overlapping_pairings(items: tuple[DiracPosition, ...]) -> tuple[DiracPairing, ...]:
    if not items:
        return ((),)

    first = items[0]
    pairings: list[DiracPairing] = []
    for i in range(1, len(items)):
        second = items[i]
        rest = items[1:i] + items[i + 1 :]
        for pairing in _non_overlapping_pairings(rest):
            pairings.append((((first, second),) + pairing))
    return tuple(pairings)


def _position_index(gamma_indices: tuple[tuple[Expression, ...], ...], position: DiracPosition) -> Expression:
    gamma_index, index_position = position
    return gamma_indices[gamma_index][index_position]


def _signature_for_positions(sequence: tuple[DiracPosition, ...], natural: tuple[DiracPosition, ...]) -> int:
    rank = {position: i for i, position in enumerate(natural)}
    return _permutation_signature(tuple(rank[position] for position in sequence))


def _dirac_basis_product(indices: tuple[Expression, ...], trailer: tuple[Expression, ...]) -> Expression:
    items: list[Expression] = []
    if indices:
        gamma = s.Gamma(*indices)
        if bool(gamma == Expression.num(0)):
            return Expression.num(0)
        items.append(gamma)
    items.extend(trailer)
    return _dirac_product_from_items(tuple(items))


def _refine_gamma_basis(gammas: tuple[Expression, ...], trailer: tuple[Expression, ...] = ()) -> Expression:
    gamma_indices = tuple(_gamma_lorentz_indices(gamma) for gamma in gammas)
    if any(indices is None for indices in gamma_indices):
        return _dirac_product_from_items(gammas + trailer)

    groups = tuple(indices for indices in gamma_indices if indices is not None)
    positions = tuple((gamma_index, index_position) for gamma_index, indices in enumerate(groups) for index_position in range(len(indices)))
    out = Expression.num(0)
    for pair_count in range(0, len(positions) + 1, 2):
        for selected in combinations(positions, pair_count):
            selected_set = frozenset(selected)
            antisymmetric_positions = tuple(position for position in positions if position not in selected_set)
            for pairing in _non_overlapping_pairings(tuple(selected)):
                if any(left[0] == right[0] for left, right in pairing):
                    continue
                paired_positions = tuple(position for pair in pairing for position in pair)
                sign = _signature_for_positions(paired_positions + antisymmetric_positions, positions)
                metrics = tuple(_metric(_position_index(groups, left), _position_index(groups, right)) for left, right in pairing)
                indices = tuple(_position_index(groups, position) for position in antisymmetric_positions)
                out = out + sign * product_expr(metrics) * _dirac_basis_product(indices, trailer)
    return out.expand()


def _refine_dirac_product(product: Expression) -> Expression:
    scalar, flattened = _flatten_dirac_product(product)
    simplified = _simplify_projectors(list(flattened))
    if simplified is None:
        return Expression.num(0)
    if not simplified:
        return scalar

    if all(_gamma_lorentz_indices(item) is not None for item in simplified):
        return (scalar * _refine_gamma_basis(simplified)).expand()

    if _is_projector(simplified[-1]) and all(_gamma_lorentz_indices(item) is not None for item in simplified[:-1]):
        return (scalar * _refine_gamma_basis(simplified[:-1], (simplified[-1],))).expand()

    return scalar * _dirac_product_from_items(simplified)


def _refine_dirac_product_match(match: dict[Expression, Expression]) -> Expression:
    return _refine_dirac_product(s.DiracProduct(*_seq_items(match[s.NCMInnerWildcard])))


def _count_index_occurrences(expr: Expression, index: Expression) -> int:
    pattern = index_pattern()
    return sum(1 for match in expr.match(pattern) if bool(pattern.replace_wildcards(match) == index))


def _normalize_dirac_product_gammas(expr: Expression) -> Expression:
    pattern = s.DiracProduct(s.NCMInnerWildcard)

    def normalize(match: dict[Expression, Expression]) -> Expression:
        items = _seq_items(match[s.NCMInnerWildcard])
        normalized_items: list[Expression] = []
        for item in items:
            indices = _gamma_lorentz_indices(item)
            if indices is None:
                normalized_items.append(item)
                continue
            gamma = s.Gamma(*indices)
            if bool(gamma == Expression.num(0)):
                return Expression.num(0)
            if len(indices) > 0:
                normalized_items.append(gamma)
        return _dirac_product_from_items(tuple(normalized_items))

    return expr.replace(pattern, normalize).expand()


def _contract_metric_term(term: Expression) -> Expression:
    out = term
    for _ in range(20):
        term_factors = list(factors(out))
        changed = False
        for i, factor in enumerate(term_factors):
            if not is_head(factor, s.Metric) or len(factor) != 2:
                continue
            left, right = factor[0], factor[1]
            rest = product_expr(term_factors[:i] + term_factors[i + 1 :])
            if bool(left == right) and _is_lorentz_index(left):
                out = s.SpacetimeDimension * rest
                changed = True
                break

            left_count = _count_index_occurrences(rest, left)
            right_count = _count_index_occurrences(rest, right)
            if left_count == 0 and right_count == 0:
                canonical = _metric(left, right)
                if bool(canonical == factor):
                    continue
                term_factors[i] = canonical
                out = product_expr(term_factors)
                changed = True
                break
            if right_count == 0:
                out = rest.replace(left, right)
                changed = True
                break
            out = rest.replace(right, left)
            changed = True
            break
        if not changed:
            return _normalize_dirac_product_gammas(out)
        out = _normalize_dirac_product_gammas(out).expand()
    return out


def _contract_metrics(expr: Expression) -> Expression:
    return sum_expr(_contract_metric_term(term) for term in terms(expr.expand())).expand()


def refine_dirac_products(expr: Expression) -> Expression:
    """Rewrite pychete Dirac products into the antisymmetrized gamma basis.

    This is the pychete analogue of Matchete's ``RefineDiracProducts`` for the
    currently represented Dirac objects: ``Gamma`` matrices, ``PL``/``PR``
    projectors, ``DiracProduct`` segments, and surrounding ``NCM`` chains.
    Products of Lorentz-indexed gamma matrices are expanded into metric terms
    plus antisymmetrized multi-index ``Gamma`` factors. Repeated Lorentz metric
    traces contract to ``s.SpacetimeDimension``.
    """

    normalized = normalize_ncm(expr).replace(s.DiracProduct(), Expression.num(1))
    refined = normalized.replace(s.DiracProduct(s.NCMInnerWildcard), _refine_dirac_product_match).expand()
    return normalize_ncm(_contract_metrics(refined))


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


def _chain_gamma_projector_pair(
    chain: Expression,
) -> tuple[Expression, Expression, Expression, Expression] | None:
    if len(chain) == 3:
        barred, dirac, fermion = (chain[i] for i in range(3))
        if not is_head(dirac, s.DiracProduct) or len(dirac) != 2:
            return None
        gamma, projector = (dirac[i] for i in range(2))
        return barred, gamma, projector, fermion

    if len(chain) == 4:
        barred, gamma, projector, fermion = (chain[i] for i in range(4))
        return barred, gamma, projector, fermion

    return None


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

    has_spin_atom = any(is_dirac_atom(item) or is_fermion_field(item) or is_barred_fermion(item) for item in items)
    if not items or (not has_spin_atom and all(is_commutative_spin_factor(item) for item in items)):
        return SpinChainKind.SCALAR

    left_bar = is_barred_fermion(items[0])
    right_field = is_fermion_field(items[-1])
    if left_bar and right_field:
        return SpinChainKind.CLOSED
    if left_bar:
        return SpinChainKind.RIGHT_OPEN
    if right_field:
        return SpinChainKind.LEFT_OPEN
    return SpinChainKind.MATRIX if has_spin_atom else SpinChainKind.SCALAR


def is_left_open_spin_chain(expr: Expression) -> bool:
    """Return whether ``expr`` is open on the left in Matchete's sense."""

    return spin_chain_kind(expr) in {SpinChainKind.LEFT_OPEN, SpinChainKind.MATRIX}


def is_right_open_spin_chain(expr: Expression) -> bool:
    """Return whether ``expr`` is open on the right in Matchete's sense."""

    return spin_chain_kind(expr) in {SpinChainKind.RIGHT_OPEN, SpinChainKind.MATRIX}


def is_closed_spin_chain(expr: Expression) -> bool:
    """Return whether ``expr`` is a closed fermion spin chain."""

    return spin_chain_kind(expr) is SpinChainKind.CLOSED


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
    pair = _chain_gamma_projector_pair(chain)
    if pair is None:
        return None
    barred, gamma, projector, fermion = pair
    if not is_barred_fermion(barred) or not is_head(gamma, s.Gamma) or not (bool(projector == s.PL) or bool(projector == s.PR)) or not is_fermion_field(fermion):
        return None
    if not bool(gamma[0] == mu):
        return None
    coefficient = product_expr(rest)
    return coefficient, scalar_field, mu, barred, gamma, projector, fermion


def canonicalize_fermion_derivative_bilinears(expr: Expression) -> Expression:
    """Canonize first-derivative closed fermion bilinears to Matchete's raw form."""

    expanded = normalize_ncm(expr)
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

    return normalize_ncm(out)


def ncm_contains_target(match: dict[Expression, Expression], target: Expression) -> int:
    """Pattern restriction helper returning true when an NCM match contains ``target``."""

    def contains(item: Expression) -> bool:
        if bool(item == target):
            return True
        if is_head(item, s.NCM) or is_head(item, s.DiracProduct):
            return any(contains(item[i]) for i in range(len(item)))
        return False

    items = _seq_items(match.get(s.NCMInnerWildcard, Expression.num(0)))
    return 1 if any(contains(item) for item in items) else -1


def ncm_target_restriction(target: Expression) -> PatternRestriction:
    """Build a native Symbolica restriction for NCM chains containing ``target``."""

    return PatternRestriction.req_matches(lambda match: ncm_contains_target(match, target))
