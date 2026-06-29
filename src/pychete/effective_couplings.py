from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from html import escape

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .backends import idenso
from .expr import as_int, factors, is_head, is_zero, list_items, product_expr, sum_expr, terms
from .green_basis import linear_identity_basis_terms, linear_identity_normal_form_from_identities
from .indices import IndexInfo, collect_indices
from .symbols import SymbolDataKey, canonical_string, display_string, latex_string, s, safe_symbol_name, symbol_data
from .theory_metadata import FieldChirality, field_chirality_from_label

_DEFAULT_MAX_EFFECTIVE_COUPLING_BASIS_TERMS = 128
_DEFAULT_MAX_EFFECTIVE_COUPLING_IDENTITIES = 256
_CoefficientTransform = Callable[[Expression], Expression]


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
    auto_identities = (
        *_target_operator_chiral_fierz_identities(target_tuple),
        *_target_operator_color_fierz_identities(target_tuple),
    )
    identity_tuple = tuple(identity for identity in (*identities, *auto_identities) if not is_zero(identity))
    input_expr = idenso.simplify_pychete_chiral_projectors(input_expr)
    target_expr = idenso.simplify_pychete_chiral_projectors(target_expr)
    identity_tuple = tuple(idenso.simplify_pychete_chiral_projectors(identity) for identity in identity_tuple)
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
    ) + _target_operator_group_fierz_alignment_replacements(targets)
    fallback_patterns = tuple(
        pattern
        for target in targets
        for pattern in _target_operator_alignment_operator_patterns(target)
    ) + _target_operator_group_fierz_alignment_operator_patterns(targets)
    if not replacements:
        return expr
    aligned_terms = tuple(
        _align_target_operator_indices_term(term, replacements, fallback_patterns)
        for term in terms(expr.expand())
    )
    return sum_expr(aligned_terms).expand()


def _align_target_operator_indices_term(
    term: Expression,
    replacements: Sequence[Replacement],
    fallback_patterns: Sequence[
        tuple[Expression, Expression, Expression, int, tuple[tuple[IndexInfo, Expression], ...], _CoefficientTransform]
    ],
) -> Expression:
    aligned = term.replace_multiple(replacements).expand()
    if not bool(aligned == term):
        return aligned
    for (
        pattern_operator,
        alias_operator,
        replacement_operator,
        alias_sign,
        wildcards,
        coefficient_transform,
    ) in fallback_patterns:
        for match in term.match(pattern_operator):
            index_replacements = _target_operator_index_replacements(match, wildcards)
            relabeled = term.replace_multiple(index_replacements).expand()
            coefficient = relabeled.coefficient(alias_operator).expand()
            if is_zero(coefficient):
                continue
            if not is_zero((relabeled - coefficient * alias_operator).expand()):
                continue
            updated = (
                Expression.num(alias_sign)
                * coefficient_transform(coefficient)
                * replacement_operator
            ).expand()
            if not bool(updated == term):
                return updated
    return term


@dataclass(frozen=True)
class _VectorCurrentPatternMatch:
    expr: Expression
    left: Expression
    right: Expression
    label: Expression
    mu: Expression


@dataclass(frozen=True)
class _GeneratorCurrentMatch:
    current: _VectorCurrentPatternMatch
    generator: Expression
    adjoint_index: Expression
    left_color: Expression
    right_color: Expression
    color_position: int
    dimension: int


@dataclass(frozen=True)
class _PureVectorTarget:
    operator: Expression
    currents: tuple[_VectorCurrentPatternMatch, _VectorCurrentPatternMatch]


@dataclass(frozen=True)
class _ColorOctetTarget:
    operator: Expression
    generators: tuple[_GeneratorCurrentMatch, _GeneratorCurrentMatch]


def _target_operator_chiral_fierz_identities(
    targets: Sequence[EffectiveCouplingTarget],
) -> tuple[Expression, ...]:
    identities: list[Expression] = []
    seen: set[str] = set()
    for target in targets:
        for identity in _chiral_fierz_identities_for_operator(target.operator):
            key = canonical_string(identity)
            if key in seen:
                continue
            seen.add(key)
            identities.append(identity)
    return tuple(identities)


def _target_operator_color_fierz_identities(
    targets: Sequence[EffectiveCouplingTarget],
) -> tuple[Expression, ...]:
    pure_targets = _pure_vector_targets(targets)
    octet_targets = _color_octet_targets(targets)
    identities: list[Expression] = []
    seen: set[str] = set()
    for octet in octet_targets:
        singlet = _matching_pure_vector_target(octet, pure_targets)
        if singlet is None:
            continue
        crossed = _crossed_color_vector_operator(octet)
        dimension = octet.generators[0].dimension
        for identity in (
            (crossed - singlet.operator / Expression.num(dimension) - Expression.num(2) * octet.operator).expand(),
            *_chiral_fierz_identities_for_operator(crossed),
        ):
            key = canonical_string(identity)
            if key in seen:
                continue
            seen.add(key)
            identities.append(identity)
    return tuple(identities)


def _target_operator_group_fierz_alignment_replacements(
    targets: Sequence[EffectiveCouplingTarget],
) -> tuple[Replacement, ...]:
    aliases: list[tuple[Expression, Expression, int, _CoefficientTransform]] = []
    seen: set[str] = set()
    for crossed in _target_operator_color_fierz_crossed_vectors(targets):
        for alias in (crossed, *tuple(channel for channel, _operator in _chiral_fierz_channels_for_operator(crossed))):
            key = canonical_string(alias)
            if key in seen:
                continue
            seen.add(key)
            aliases.append((alias, alias, 1, _identity_coefficient_transform))
    replacements: list[Replacement] = []
    for alias_position, (alias_operator, replacement_operator, alias_sign, coefficient_transform) in enumerate(aliases):
        index_infos = collect_indices(alias_operator * replacement_operator)
        if not index_infos:
            continue
        coefficient = Expression.symbol(
            f"pychete::effective_coupling_coefficient_group_fierz_{alias_position}_"
        )
        pattern_operator, _alias_operator, _replacement_operator, _alias_sign, wildcards, _coefficient_transform = (
            _target_operator_alignment_operator_pattern(
                alias_operator,
                replacement_operator,
                alias_sign,
                coefficient_transform,
                index_infos,
                safe_target_name="group_fierz",
                alias_position=alias_position,
            )
        )
        replacements.append(
            Replacement(
                coefficient * pattern_operator,
                _target_operator_alignment_replacement(
                    coefficient * pattern_operator,
                    coefficient,
                    replacement_operator,
                    wildcards,
                    alias_sign,
                    coefficient_transform,
                ),
                partial=False,
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _target_operator_group_fierz_alignment_operator_patterns(
    targets: Sequence[EffectiveCouplingTarget],
) -> tuple[
    tuple[Expression, Expression, Expression, int, tuple[tuple[IndexInfo, Expression], ...], _CoefficientTransform],
    ...,
]:
    patterns: list[
        tuple[Expression, Expression, Expression, int, tuple[tuple[IndexInfo, Expression], ...], _CoefficientTransform]
    ] = []
    seen: set[str] = set()
    for alias_position, crossed in enumerate(_target_operator_color_fierz_crossed_vectors(targets)):
        aliases = (crossed, *tuple(channel for channel, _operator in _chiral_fierz_channels_for_operator(crossed)))
        for alias_offset, alias_operator in enumerate(aliases):
            key = canonical_string(alias_operator)
            if key in seen:
                continue
            seen.add(key)
            patterns.append(
                _target_operator_alignment_operator_pattern(
                    alias_operator,
                    alias_operator,
                    1,
                    _identity_coefficient_transform,
                    collect_indices(alias_operator),
                    safe_target_name="group_fierz_fallback",
                    alias_position=alias_position * 8 + alias_offset,
                )
            )
    return tuple(patterns)


def _target_operator_color_fierz_crossed_vectors(
    targets: Sequence[EffectiveCouplingTarget],
) -> tuple[Expression, ...]:
    pure_targets = _pure_vector_targets(targets)
    out: list[Expression] = []
    seen: set[str] = set()
    for target in targets:
        octet = _color_octet_target(target.operator)
        if octet is None or _matching_pure_vector_target(octet, pure_targets) is None:
            continue
        crossed = _crossed_color_vector_operator(octet)
        key = canonical_string(crossed)
        if key in seen:
            continue
        seen.add(key)
        out.append(crossed)
    return tuple(out)


def _pure_vector_targets(
    targets: Sequence[EffectiveCouplingTarget],
) -> tuple[_PureVectorTarget, ...]:
    out: list[_PureVectorTarget] = []
    for target in targets:
        candidate = _pure_vector_target(target.operator)
        if candidate is not None:
            out.append(candidate)
    return tuple(out)


def _color_octet_targets(
    targets: Sequence[EffectiveCouplingTarget],
) -> tuple[_ColorOctetTarget, ...]:
    out: list[_ColorOctetTarget] = []
    for target in targets:
        candidate = _color_octet_target(target.operator)
        if candidate is not None:
            out.append(candidate)
    return tuple(out)


def _chiral_fierz_identities_for_operator(operator: Expression) -> tuple[Expression, ...]:
    return tuple(
        (scalar_channel + operator_term / Expression.num(2)).expand()
        for scalar_channel, operator_term in _chiral_fierz_channels_for_operator(operator)
    )


def _chiral_fierz_channels_for_operator(operator: Expression) -> tuple[tuple[Expression, Expression], ...]:
    channels: list[tuple[Expression, Expression]] = []
    for operator_term in terms(operator.expand()):
        currents = _vector_current_matches(operator_term)
        if len(currents) != 2:
            continue
        first, second = currents
        noncurrent_remainder = operator_term.replace_multiple(
            (
                Replacement(first.expr, Expression.num(1)),
                Replacement(second.expr, Expression.num(1)),
            )
        ).expand()
        if not bool(noncurrent_remainder == Expression.num(1)):
            continue
        if not bool(first.mu == second.mu):
            continue
        first_chirality = field_chirality_from_label(first.label)
        second_chirality = field_chirality_from_label(second.label)
        if not _opposite_nonzero_chiralities(first_chirality, second_chirality):
            continue
        scalar_channel = s.NCM(s.Bar(first.left), second.right) * s.NCM(s.Bar(second.left), first.right)
        channels.append((scalar_channel.expand(), operator_term))
    return tuple(channels)


def _vector_current_matches(expr: Expression) -> tuple[_VectorCurrentPatternMatch, ...]:
    left_label = s.head("effective_coupling_vector_left_label_")
    left_indices = s.head("effective_coupling_vector_left_indices_")
    left_derivatives = s.head("effective_coupling_vector_left_derivatives_")
    right_label = s.head("effective_coupling_vector_right_label_")
    right_indices = s.head("effective_coupling_vector_right_indices_")
    right_derivatives = s.head("effective_coupling_vector_right_derivatives_")
    mu = s.head("effective_coupling_vector_mu_")
    left = s.Field(left_label, s.Fermion, left_indices, left_derivatives)
    right = s.Field(right_label, s.Fermion, right_indices, right_derivatives)
    pattern = s.NCM(s.Bar(left), s.Gamma(mu), right)
    out: list[_VectorCurrentPatternMatch] = []
    seen: set[str] = set()
    for match in expr.match(pattern):
        if not bool(match[left_label] == match[right_label]):
            continue
        if not bool(match[left_derivatives] == s.List()) or not bool(match[right_derivatives] == s.List()):
            continue
        current = pattern.replace_wildcards(match)
        key = canonical_string(current)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            _VectorCurrentPatternMatch(
                expr=current,
                left=left.replace_wildcards(match),
                right=right.replace_wildcards(match),
                label=match[left_label],
                mu=match[mu],
            )
        )
    return tuple(out)


def _opposite_nonzero_chiralities(left: FieldChirality, right: FieldChirality) -> bool:
    return {left, right} == {FieldChirality.LEFT, FieldChirality.RIGHT}


def _pure_vector_target(operator: Expression) -> _PureVectorTarget | None:
    operator_terms = terms(operator.expand())
    if len(operator_terms) != 1:
        return None
    operator_term = operator_terms[0]
    currents = _vector_current_matches(operator_term)
    if len(currents) != 2:
        return None
    remainder = _remove_current_factors(operator_term, currents)
    if not bool(remainder == Expression.num(1)):
        return None
    return _PureVectorTarget(operator=operator_term, currents=(currents[0], currents[1]))


def _color_octet_target(operator: Expression) -> _ColorOctetTarget | None:
    operator_terms = terms(operator.expand())
    if len(operator_terms) != 1:
        return None
    operator_term = operator_terms[0]
    currents = _vector_current_matches(operator_term)
    if len(currents) != 2:
        return None
    remainder = _remove_current_factors(operator_term, currents)
    generators = _generator_current_matches(remainder, currents)
    if len(generators) != 2:
        return None
    first, second = generators
    if not bool(first.adjoint_index == second.adjoint_index):
        return None
    if first.dimension <= 0 or first.dimension != second.dimension:
        return None
    return _ColorOctetTarget(operator=operator_term, generators=(first, second))


def _remove_current_factors(
    expr: Expression,
    currents: Sequence[_VectorCurrentPatternMatch],
) -> Expression:
    return expr.replace_multiple(tuple(Replacement(current.expr, Expression.num(1)) for current in currents)).expand()


def _generator_current_matches(
    expr: Expression,
    currents: Sequence[_VectorCurrentPatternMatch],
) -> tuple[_GeneratorCurrentMatch, ...]:
    generators = _builtin_generator_atoms(expr)
    out: list[_GeneratorCurrentMatch] = []
    used_current_keys: set[str] = set()
    for generator in generators:
        indices = list_items(generator[1])
        adjoint_index, left_color, right_color = indices
        dimension = _generator_fundamental_dimension(generator)
        if dimension <= 0:
            dimension = _index_representation_dimension(left_color)
        if dimension <= 0:
            continue
        for current in currents:
            current_key = canonical_string(current.expr)
            if current_key in used_current_keys:
                continue
            color_position = _current_color_position(current, left_color, right_color)
            if color_position is None:
                continue
            used_current_keys.add(current_key)
            out.append(
                _GeneratorCurrentMatch(
                    current=current,
                    generator=generator,
                    adjoint_index=adjoint_index,
                    left_color=left_color,
                    right_color=right_color,
                    color_position=color_position,
                    dimension=dimension,
                )
            )
            break
    return tuple(out)


def _builtin_generator_atoms(expr: Expression) -> tuple[Expression, ...]:
    label = s.head("effective_coupling_generator_label_")
    adjoint = s.head("effective_coupling_generator_adjoint_")
    left = s.head("effective_coupling_generator_left_")
    right = s.head("effective_coupling_generator_right_")
    pattern = s.CG(label, s.List(adjoint, left, right))
    out: list[Expression] = []
    seen: set[str] = set()
    for match in expr.match(pattern):
        matched_label = match[label]
        source = symbol_data(matched_label, SymbolDataKey.CG_SOURCE, "")
        representations = symbol_data(matched_label, SymbolDataKey.CG_REPRESENTATIONS, [])
        if source != "builtin:gen" or not isinstance(representations, list) or len(representations) != 3:
            continue
        atom = pattern.replace_wildcards(match)
        key = canonical_string(atom)
        if key in seen:
            continue
        seen.add(key)
        out.append(atom)
    return tuple(out)


def _generator_fundamental_dimension(generator: Expression) -> int:
    representations = symbol_data(generator[0], SymbolDataKey.CG_REPRESENTATIONS, [])
    if not isinstance(representations, list) or len(representations) < 2:
        return -1
    dimension = symbol_data(representations[1], SymbolDataKey.DIMENSION, -1)
    try:
        return int(dimension)
    except (TypeError, ValueError):
        return -1


def _index_representation_dimension(index: Expression) -> int:
    if not is_head(index, s.Index):
        return -1
    representation = index[1]
    dimension = symbol_data(representation, SymbolDataKey.DIMENSION, -1)
    try:
        dimension_int = int(dimension)
    except (TypeError, ValueError):
        dimension_int = -1
    if dimension_int > 0:
        return dimension_int
    group_symbol = Expression.symbol(representation.get_name())
    group_type = symbol_data(group_symbol, SymbolDataKey.GROUP_TYPE)
    if group_type is not None and is_head(group_type, s.SU):
        group_size = as_int(group_type[0])
        return group_size if group_size is not None else -1
    return -1


def _current_color_position(
    current: _VectorCurrentPatternMatch,
    left_color: Expression,
    right_color: Expression,
) -> int | None:
    left_indices = list_items(current.left[2])
    right_indices = list_items(current.right[2])
    for position, (left_index, right_index) in enumerate(zip(left_indices, right_indices, strict=False)):
        if bool(left_index == left_color) and bool(right_index == right_color):
            return position
    return None


def _matching_pure_vector_target(
    octet: _ColorOctetTarget,
    pure_targets: Sequence[_PureVectorTarget],
) -> _PureVectorTarget | None:
    for pure in pure_targets:
        if _pure_target_matches_octet(pure, octet):
            return pure
    return None


def _pure_target_matches_octet(pure: _PureVectorTarget, octet: _ColorOctetTarget) -> bool:
    pure_by_label = _unique_currents_by_label(pure.currents)
    octet_by_label = _unique_generators_by_current_label(octet.generators)
    if pure_by_label is None or octet_by_label is None or set(pure_by_label) != set(octet_by_label):
        return False
    for label_key, octet_generator in octet_by_label.items():
        pure_current = pure_by_label[label_key]
        pure_position = _singlet_current_color_position(pure_current, octet_generator.left_color)
        if pure_position is None:
            return False
        if not _currents_match_ignoring_color(
            pure_current,
            pure_position,
            octet_generator.current,
            octet_generator.color_position,
        ):
            return False
    return True


def _unique_currents_by_label(
    currents: Sequence[_VectorCurrentPatternMatch],
) -> dict[str, _VectorCurrentPatternMatch] | None:
    out: dict[str, _VectorCurrentPatternMatch] = {}
    for current in currents:
        key = canonical_string(current.label)
        if key in out:
            return None
        out[key] = current
    return out


def _unique_generators_by_current_label(
    generators: Sequence[_GeneratorCurrentMatch],
) -> dict[str, _GeneratorCurrentMatch] | None:
    out: dict[str, _GeneratorCurrentMatch] = {}
    for generator in generators:
        key = canonical_string(generator.current.label)
        if key in out:
            return None
        out[key] = generator
    return out


def _singlet_current_color_position(
    current: _VectorCurrentPatternMatch,
    reference_color: Expression,
) -> int | None:
    left_indices = list_items(current.left[2])
    right_indices = list_items(current.right[2])
    reference_representation = reference_color[1] if is_head(reference_color, s.Index) else None
    for position, (left_index, right_index) in enumerate(zip(left_indices, right_indices, strict=False)):
        if not bool(left_index == right_index):
            continue
        if reference_representation is not None and (
            not is_head(left_index, s.Index) or not bool(left_index[1] == reference_representation)
        ):
            continue
        return position
    return None


def _currents_match_ignoring_color(
    left: _VectorCurrentPatternMatch,
    left_color_position: int,
    right: _VectorCurrentPatternMatch,
    right_color_position: int,
) -> bool:
    if not bool(left.mu == right.mu) or not bool(left.label == right.label):
        return False
    return _indices_without_position(left.left, left_color_position) == _indices_without_position(
        right.left,
        right_color_position,
    ) and _indices_without_position(left.right, left_color_position) == _indices_without_position(
        right.right,
        right_color_position,
    )


def _indices_without_position(field: Expression, position_to_drop: int) -> tuple[str, ...]:
    return tuple(
        canonical_string(index)
        for position, index in enumerate(list_items(field[2]))
        if position != position_to_drop
    )


def _crossed_color_vector_operator(octet: _ColorOctetTarget) -> Expression:
    first, second = octet.generators
    crossed_second = second.current.expr.replace_multiple(
        (
            Replacement(second.left_color, first.right_color),
            Replacement(second.right_color, first.left_color),
        )
    )
    return (first.current.expr * crossed_second).expand()


def _target_operator_alignment_replacements(target: EffectiveCouplingTarget) -> tuple[Replacement, ...]:
    operator_terms = terms(target.operator.expand())
    if len(operator_terms) != 1:
        return ()
    index_infos = collect_indices(target.operator)
    if not index_infos:
        return ()
    safe_target_name = safe_symbol_name(target.name)
    replacements: list[Replacement] = []
    for alias_position, (alias_operator, replacement_operator, alias_sign, coefficient_transform) in enumerate(
        _target_operator_alignment_aliases(target)
    ):
        coefficient = Expression.symbol(
            f"pychete::effective_coupling_coefficient_{safe_target_name}_{alias_position}_"
        )
        pattern_operator, _alias_operator, _replacement_operator, _alias_sign, wildcards, _coefficient_transform = (
            _target_operator_alignment_operator_pattern(
                alias_operator,
                replacement_operator,
                alias_sign,
                coefficient_transform,
                index_infos,
                safe_target_name=safe_target_name,
                alias_position=alias_position,
            )
        )
        pattern = coefficient * pattern_operator
        replacements.append(
            Replacement(
                pattern,
                _target_operator_alignment_replacement(
                    pattern,
                    coefficient,
                    replacement_operator,
                    wildcards,
                    alias_sign,
                    coefficient_transform,
                ),
                partial=False,
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _target_operator_alignment_operator_patterns(
    target: EffectiveCouplingTarget,
) -> tuple[
    tuple[Expression, Expression, Expression, int, tuple[tuple[IndexInfo, Expression], ...], _CoefficientTransform],
    ...,
]:
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
            replacement_operator,
            alias_sign,
            coefficient_transform,
            index_infos,
            safe_target_name=safe_target_name,
            alias_position=alias_position,
        )
        for alias_position, (alias_operator, replacement_operator, alias_sign, coefficient_transform) in enumerate(
            _target_operator_alignment_aliases(target)
        )
    )


def _target_operator_alignment_aliases(
    target: EffectiveCouplingTarget,
) -> tuple[tuple[Expression, Expression, int, _CoefficientTransform], ...]:
    out: list[tuple[Expression, Expression, int, _CoefficientTransform]] = []
    seen: set[str] = set()
    target_alias_operator = _normalize_alignment_alias_operator(target.operator)
    for alias_operator, alias_sign in _epsilon_orientation_aliases(target_alias_operator):
        key = f"{canonical_string(alias_operator)}->{canonical_string(target.operator)}:{alias_sign}:direct"
        if key in seen:
            continue
        seen.add(key)
        out.append((alias_operator, target.operator, alias_sign, _identity_coefficient_transform))
    chiral_fierz_channels = _chiral_fierz_channels_for_operator(target.operator)
    if not chiral_fierz_channels:
        hermitian_operator = _normalize_alignment_alias_operator(_hermitian_conjugate_coefficient(target.operator))
        for alias_operator, alias_sign in _epsilon_orientation_aliases(hermitian_operator):
            key = f"{canonical_string(alias_operator)}->{canonical_string(target.operator)}:{alias_sign}:hc"
            if key in seen:
                continue
            seen.add(key)
            out.append((alias_operator, target.operator, alias_sign, _hermitian_conjugate_coefficient))
    for scalar_channel, _operator_term in chiral_fierz_channels:
        for alias_operator, alias_sign in _epsilon_orientation_aliases(scalar_channel):
            key = f"{canonical_string(alias_operator)}->{canonical_string(scalar_channel)}:{alias_sign}:direct"
            if key in seen:
                continue
            seen.add(key)
            out.append((alias_operator, scalar_channel, alias_sign, _identity_coefficient_transform))
    return tuple(out)


def _normalize_alignment_alias_operator(expr: Expression) -> Expression:
    from .functional import expand_cd_operators

    return idenso.canonicalize_builtin_epsilon_cg_tensors(
        idenso.simplify_pychete_chiral_projectors(expand_cd_operators(expr))
    )


def _target_operator_alignment_operator_pattern(
    alias_operator: Expression,
    replacement_operator: Expression,
    alias_sign: int,
    coefficient_transform: _CoefficientTransform,
    index_infos: Sequence[IndexInfo],
    *,
    safe_target_name: str,
    alias_position: int,
) -> tuple[Expression, Expression, Expression, int, tuple[tuple[IndexInfo, Expression], ...], _CoefficientTransform]:
    alias_prefactor, alias_body = _numeric_prefactor_and_body(alias_operator)
    wildcards = tuple(
        (
            info,
            Expression.symbol(f"pychete::effective_coupling_index_{safe_target_name}_{alias_position}_{position}_"),
        )
        for position, info in enumerate(index_infos)
    )
    pattern_operator = alias_body
    for info, wildcard in wildcards:
        pattern_operator = pattern_operator.replace(
            info.expr,
            s.Index(wildcard, info.representation),
            allow_new_wildcards_on_rhs=True,
        )
    return (
        pattern_operator,
        alias_body,
        replacement_operator,
        alias_sign,
        wildcards,
        _prefactor_adjusted_coefficient_transform(alias_prefactor, coefficient_transform),
    )


def _numeric_prefactor_and_body(expr: Expression) -> tuple[Expression, Expression]:
    prefactors: list[Expression] = []
    body_factors: list[Expression] = []
    for factor in factors(expr):
        if factor.get_type() is AtomType.Num:
            prefactors.append(factor)
        else:
            body_factors.append(factor)
    return product_expr(prefactors), product_expr(body_factors)


def _prefactor_adjusted_coefficient_transform(
    prefactor: Expression,
    transform: _CoefficientTransform,
) -> _CoefficientTransform:
    def adjusted(coefficient: Expression) -> Expression:
        return transform((coefficient / prefactor).expand())

    return adjusted


def _identity_coefficient_transform(expr: Expression) -> Expression:
    return expr


def _hermitian_conjugate_coefficient(expr: Expression) -> Expression:
    from .functional import hermitian_conjugate

    return hermitian_conjugate(expr)


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
    replacement_operator: Expression,
    wildcards: Sequence[tuple[IndexInfo, Expression]],
    alias_sign: int,
    coefficient_transform: _CoefficientTransform,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_term(match: dict[Expression, Expression]) -> Expression:
        coefficient = match[coefficient_wildcard]
        replacements = _target_operator_index_replacements(match, wildcards)
        aligned_coefficient = coefficient_transform(coefficient.replace_multiple(replacements))
        return (Expression.num(alias_sign) * aligned_coefficient * replacement_operator).expand()

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
