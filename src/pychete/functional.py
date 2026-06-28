from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

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
    field_strength_derivatives,
    field_strength_label,
    field_strength_pattern,
    field_strength_with_derivatives,
    field_with_derivatives,
    is_bar_field,
    is_head,
    is_zero,
    list_expr,
    list_items,
    matching_subexpressions,
    product_expr,
    sum_expr,
    terms,
    wilson_term_pattern,
)
from .linear_external import linear_external_function_heads
from .symbols import SymbolDataKey, SymbolRole, canonical_string, s, symbol_data
from .theory import Theory
from .theory_metadata import (
    CouplingSelfConjugate,
    FieldDefinition,
    FieldHandle,
    FieldVariation,
    GroupKind,
    coupling_self_conjugate_from_label,
    field_indices_from_label,
    field_self_conjugate_from_label,
)

_MAX_MULTILINEAR_CHAIN_ARITY = 8
_MAX_SCALAR_DERIVATIVE_BILINEAR_CANDIDATES = 128
_DEFAULT_SCALAR_GREEN_MAX_BASIS_TERMS = 96
_DEFAULT_SCALAR_GREEN_MAX_IDENTITIES = 192
_DEFAULT_SCALAR_GREEN_MAX_ROUNDS = 2


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
    expr = normalize_conjugate_scalar_field_slots(theory, expr)
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


def integrate_by_parts_scalar_laplacians(
    theory: Theory,
    expr: Expression,
    *,
    max_candidates: int = _MAX_SCALAR_DERIVATIVE_BILINEAR_CANDIDATES,
) -> Expression:
    """Integrate scalar Laplacian factors by parts in a bounded Green-basis pass.

    Matchete's ``IdentitiesIBP`` generates total-derivative identities for
    operators containing differentiated fields.  This helper implements the
    local scalar-Laplacian member of that identity family,
    ``A * D_mu D_mu phi -> -D_mu(A) * D_mu phi``, using Symbolica pattern
    discovery and native coefficient extraction.  It is deliberately opt-in:
    callers decide where this Green-basis normalization is appropriate.
    """

    if max_candidates < 0:
        raise ValueError("max_candidates must be non-negative")
    theory._validate_registered_expression(expr)
    out = normalize_conjugate_scalar_field_slots(theory, expr)
    atoms = (*_scalar_laplacian_field_atoms(out), *_scalar_laplacian_barred_field_atoms(out))
    seen: set[str] = set()
    candidate_count = 0
    for atom in atoms:
        key = canonical_string(atom)
        if key in seen:
            continue
        seen.add(key)
        candidate_count += 1
        if candidate_count > max_candidates:
            return out.expand()
        out = _integrate_scalar_laplacian_atom_by_parts(out, atom)
    return out.expand()


def scalar_derivative_ibp_identities(
    theory: Theory,
    expr: Expression,
    *,
    max_identities: int = _DEFAULT_SCALAR_GREEN_MAX_IDENTITIES,
) -> tuple[Expression, ...]:
    """Return local scalar-field IBP identities for Green-basis reduction.

    This is the scalar subset of Matchete's ``IdentitiesIBP`` identity source.
    For every linear differentiated scalar ``Field`` or ``Bar(Field)`` atom it
    constructs the total-derivative identity
    ``D_mu(coefficient * D_rest(phi)) == 0``, i.e.
    ``coefficient * D_mu D_rest(phi) + D_mu(coefficient) * D_rest(phi)``.
    Field atoms are discovered with Symbolica tag-restricted patterns and the
    coefficient is extracted with native ``Expression.coefficient(...)``.
    """

    if max_identities < 0:
        raise ValueError("max_identities must be non-negative")
    theory._validate_registered_expression(expr)
    normalized = normalize_conjugate_scalar_field_slots(theory, expr)
    identities: list[Expression] = []
    seen: set[str] = set()
    for atom in _scalar_derivative_ibp_atoms(normalized):
        coefficient = normalized.coefficient(atom).expand()
        if is_zero(coefficient):
            continue
        if not is_zero(coefficient.coefficient(atom)):
            continue
        identity = _scalar_derivative_ibp_identity_for_atom(coefficient, atom)
        if is_zero(identity):
            continue
        key = canonical_string(identity)
        if key in seen:
            continue
        seen.add(key)
        identities.append(identity)
        if len(identities) > max_identities:
            raise ValueError(f"scalar Green-basis IBP generated more than {max_identities} identities")
    return tuple(identities)


def scalar_derivative_green_normal_form(
    theory: Theory,
    expr: Expression,
    *,
    preferred: Iterable[Expression] = (),
    include_ibp: bool = True,
    include_commutators: bool = True,
    max_basis_terms: int = _DEFAULT_SCALAR_GREEN_MAX_BASIS_TERMS,
    max_identities: int = _DEFAULT_SCALAR_GREEN_MAX_IDENTITIES,
    max_rounds: int = _DEFAULT_SCALAR_GREEN_MAX_ROUNDS,
) -> Expression:
    """Reduce scalar derivative operators with local IBP and commutator identities.

    The helper is a bounded pychete analogue of the scalar-derivative part of
    Matchete's ``GreensSimplify``. It builds a local identity neighborhood from
    scalar ``IdentitiesIBP`` and covariant-derivative commutation identities,
    optionally closes that neighborhood over newly discovered local operator
    basis terms for a few rounds, and then delegates row reduction to
    Symbolica via :func:`pychete.green_basis.linear_identity_normal_form_from_identities`.

    If ``preferred`` is not supplied, a scalar-only local ordering mirrors the
    clear scalar pieces of Matchete's ``OpScore``: field-strength-like
    representatives are preferred to raw derivatives, repeated derivative
    slots and explicit ``CD`` wrappers are penalized, and derivatives are
    favored when they are distributed across scalar factors. This does not try
    to reproduce Matchete's full fermion/CG/Fierz scoring policy in Python.
    """

    if max_basis_terms < 0:
        raise ValueError("max_basis_terms must be non-negative")
    if max_identities < 0:
        raise ValueError("max_identities must be non-negative")
    if max_rounds < 0:
        raise ValueError("max_rounds must be non-negative")
    theory._validate_registered_expression(expr)
    normalized = normalize_conjugate_scalar_field_slots(theory, expr)
    identities = _scalar_derivative_green_identities(
        theory,
        normalized,
        include_ibp=include_ibp,
        include_commutators=include_commutators,
        max_basis_terms=max_basis_terms,
        max_identities=max_identities,
        max_rounds=max_rounds,
    )
    if not identities:
        return normalized

    from .green_basis import linear_identity_basis_terms, linear_identity_normal_form

    basis = linear_identity_basis_terms(
        (normalized, *identities),
        max_basis_terms=max_basis_terms,
    )
    preferred_terms = tuple(preferred) or _scalar_derivative_green_preferred_terms(basis)
    return linear_identity_normal_form(
        normalized,
        identities,
        basis=basis,
        preferred=preferred_terms,
        max_basis_terms=max_basis_terms,
        max_identities=max_identities,
    )


def normalize_conjugate_scalar_field_slots(theory: Theory, expr: Expression) -> Expression:
    """Rewrite dual-index scalar fields as explicit ``Bar(Field(...))`` atoms.

    Matchete model conversion can encode a conjugate scalar component either as
    ``Bar(Field(...))`` or as a field carrying the dual representation index,
    e.g. ``Field(H, [Bar(fund)])``.  The Green-bilinear and commutator passes
    operate on the explicit ``Bar(Field(...))`` representation, so normalize
    the dual-index form with a Symbolica field-pattern replacement before those
    passes run.
    """

    theory._validate_registered_expression(expr)
    pattern = field_pattern()
    label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)

    def normalize_match(match: dict[Expression, Expression]) -> Expression:
        atom = pattern.replace_wildcards(match)
        return _explicit_bar_scalar_field(atom) or atom

    return expr.replace(pattern, normalize_match, label_is_tagged, rhs_cache_size=0)


def _explicit_bar_scalar_field(atom: Expression) -> Expression | None:
    if not bool(field_type(atom) == s.Scalar):
        return None
    label = field_label(atom)
    if field_self_conjugate_from_label(label):
        return None
    expected_representations = field_indices_from_label(label)
    actual_indices = list_items(atom[2])
    if not expected_representations or len(actual_indices) != len(expected_representations):
        return None
    base_indices: list[Expression] = []
    for actual_index, expected_representation in zip(actual_indices, expected_representations, strict=True):
        if not is_head(actual_index, s.Index):
            return None
        if not bool(actual_index[1] == s.Bar(expected_representation)):
            return None
        base_indices.append(s.Index(actual_index[0], expected_representation))
    base = s.Field(label, field_type(atom), list_expr(*base_indices), atom[3])
    return s.Bar(base)


def _scalar_derivative_green_identities(
    theory: Theory,
    expr: Expression,
    *,
    include_ibp: bool,
    include_commutators: bool,
    max_basis_terms: int,
    max_identities: int,
    max_rounds: int,
) -> tuple[Expression, ...]:
    if not include_ibp and not include_commutators:
        return ()

    from .green_basis import linear_identity_basis_terms

    identities: list[Expression] = []
    seen_identities: set[str] = set()
    processed_sources: set[str] = set()
    frontier: tuple[Expression, ...] = (expr,)
    for _ in range(max(1, max_rounds)):
        new_sources: list[Expression] = []
        for source in frontier:
            source_key = canonical_string(source)
            if source_key in processed_sources:
                continue
            processed_sources.add(source_key)
            for identity in _scalar_derivative_identity_sources(
                theory,
                source,
                include_ibp=include_ibp,
                include_commutators=include_commutators,
                max_identities=max_identities,
            ):
                identity_key = canonical_string(identity)
                if identity_key in seen_identities:
                    continue
                seen_identities.add(identity_key)
                identities.append(identity)
                if len(identities) > max_identities:
                    raise ValueError(f"scalar Green-basis reduction generated more than {max_identities} identities")
        if not identities:
            break
        basis_terms = linear_identity_basis_terms(
            (expr, *identities),
            max_basis_terms=max_basis_terms,
        )
        for basis_term in basis_terms:
            key = canonical_string(basis_term)
            if key not in processed_sources:
                new_sources.append(basis_term)
        if not new_sources:
            break
        frontier = tuple(new_sources)
    return tuple(identities)


def _scalar_derivative_identity_sources(
    theory: Theory,
    expr: Expression,
    *,
    include_ibp: bool,
    include_commutators: bool,
    max_identities: int,
) -> tuple[Expression, ...]:
    identities: list[Expression] = []
    if include_ibp:
        identities.extend(scalar_derivative_ibp_identities(theory, expr, max_identities=max_identities))
    if include_commutators:
        identities.extend(theory.covariant_derivative_commutator_identities(expr))
    if len(identities) > max_identities:
        raise ValueError(f"scalar Green-basis reduction generated more than {max_identities} identities")
    return tuple(identities)


def _scalar_derivative_green_preferred_terms(
    basis: Sequence[Expression],
) -> tuple[Expression, ...]:
    return tuple(
        sorted(
            basis,
            key=lambda term: (_scalar_derivative_green_score(term), canonical_string(term)),
        )
    )


def _scalar_derivative_green_score(term: Expression) -> int:
    eom_score = 1_000_000 * len(matching_subexpressions(term, s.EOM(s.CDBodyWildcard)))
    field_strength_score = 10_000 * (
        len(matching_subexpressions(term, field_strength_pattern()))
        + len(matching_subexpressions(term, bar_field_strength_pattern()))
        + len(matching_subexpressions(term, covariant_derivative_commutator_pattern()))
    )
    explicit_cd_penalty = 1_000 * len(matching_subexpressions(term, cd_pattern()))
    derivative_lengths = _scalar_green_derivative_lengths(term)
    repeated_derivative_penalty = 100 * sum(1 for derivatives in derivative_lengths if _has_repeated_derivative(derivatives))
    derivative_balance_penalty = 10 * sum(len(derivatives) * len(derivatives) for derivatives in derivative_lengths)
    derivative_count_penalty = sum(len(derivatives) for derivatives in derivative_lengths)
    return (
        eom_score
        + field_strength_score
        - explicit_cd_penalty
        - repeated_derivative_penalty
        - derivative_balance_penalty
        - derivative_count_penalty
    )


def _scalar_green_derivative_lengths(term: Expression) -> tuple[tuple[Expression, ...], ...]:
    field_label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    derivative_lengths: list[tuple[Expression, ...]] = []
    for atom in matching_subexpressions(term, bar_field_pattern(), field_label_is_tagged):
        if is_bar_field(atom) and bool(field_type(bar_field_inner(atom)) == s.Scalar):
            derivative_lengths.append(field_derivatives(bar_field_inner(atom)))
    for atom in matching_subexpressions(term, field_pattern(), field_label_is_tagged):
        if bool(field_type(atom) == s.Scalar):
            derivative_lengths.append(field_derivatives(atom))
    return tuple(derivative_lengths)


def _has_repeated_derivative(derivatives: Sequence[Expression]) -> bool:
    seen: set[str] = set()
    for derivative in derivatives:
        key = canonical_string(derivative)
        if key in seen:
            return True
        seen.add(key)
    return False


def _scalar_derivative_ibp_atoms(expr: Expression) -> tuple[Expression, ...]:
    field_pat = field_pattern()
    bar_pat = bar_field_pattern()
    field_label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    atoms: list[Expression] = []
    seen: set[str] = set()
    for pattern in (bar_pat, field_pat):
        for atom in matching_subexpressions(expr, pattern, field_label_is_tagged):
            if is_bar_field(atom):
                base_atom = bar_field_inner(atom)
            else:
                base_atom = atom
            if not _is_scalar_derivative_ibp_field(base_atom):
                continue
            key = canonical_string(atom)
            if key in seen:
                continue
            seen.add(key)
            atoms.append(atom)
    return tuple(atoms)


def _is_scalar_derivative_ibp_field(atom: Expression) -> bool:
    if not bool(field_type(atom) == s.Scalar):
        return False
    derivatives = field_derivatives(atom)
    return bool(derivatives) and all(is_head(derivative, s.Index) for derivative in derivatives)


def _scalar_derivative_ibp_identity_for_atom(coefficient: Expression, atom: Expression) -> Expression:
    base_atom = bar_field_inner(atom) if is_bar_field(atom) else atom
    derivatives = field_derivatives(base_atom)
    if not derivatives:
        return Expression.num(0)
    outer_derivative = derivatives[0]
    reduced_base = field_with_derivatives(base_atom, derivatives[1:])
    reduced_atom = s.Bar(reduced_base) if is_bar_field(atom) else reduced_base
    return (coefficient * atom + apply_cd([outer_derivative], coefficient) * reduced_atom).expand()


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


def _scalar_laplacian_field_atoms(expr: Expression) -> tuple[Expression, ...]:
    pattern = field_pattern()
    label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    atoms: list[Expression] = []
    seen: set[str] = set()
    for match in expr.match(pattern, label_is_tagged):
        atom = pattern.replace_wildcards(match)
        if not _is_scalar_laplacian_field(atom):
            continue
        key = canonical_string(atom)
        if key in seen:
            continue
        seen.add(key)
        atoms.append(atom)
    return tuple(atoms)


def _scalar_laplacian_barred_field_atoms(expr: Expression) -> tuple[Expression, ...]:
    pattern = bar_field_pattern()
    label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    atoms: list[Expression] = []
    seen: set[str] = set()
    for match in expr.match(pattern, label_is_tagged):
        atom = pattern.replace_wildcards(match)
        if not is_bar_field(atom):
            continue
        if not _is_scalar_laplacian_field(bar_field_inner(atom)):
            continue
        key = canonical_string(atom)
        if key in seen:
            continue
        seen.add(key)
        atoms.append(atom)
    return tuple(atoms)


def _is_scalar_laplacian_field(atom: Expression) -> bool:
    if not bool(field_type(atom) == s.Scalar):
        return False
    derivatives = field_derivatives(atom)
    return len(derivatives) == 2 and bool(derivatives[0] == derivatives[1])


def _integrate_scalar_laplacian_atom_by_parts(expr: Expression, atom: Expression) -> Expression:
    base_atom = bar_field_inner(atom) if is_bar_field(atom) else atom
    derivatives = field_derivatives(base_atom)
    if len(derivatives) != 2 or not bool(derivatives[0] == derivatives[1]):
        return expr
    derivative = derivatives[0]
    coefficient = expr.coefficient(atom).expand()
    if is_zero(coefficient):
        return expr
    reduced_base = field_with_derivatives(base_atom, (derivative,))
    reduced_atom = s.Bar(reduced_base) if is_bar_field(atom) else reduced_base
    replacement = (-apply_cd([derivative], coefficient) * reduced_atom).expand()
    return (expr - coefficient * atom + replacement).expand()


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
        definition = theory._field_definition_for_label(field_label(base))
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
            if definition is not None and not definition.is_self_conjugate:
                variation_mode = FieldVariation.FIELD if exact_barred else FieldVariation.BAR
            else:
                variation_mode = FieldVariation.FIELD
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
        base = definition.expr(*_default_field_indices(theory, definition))
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
    for target, open_index, sign in _abelian_vector_eom_rule_targets(expression, allowed_labels=allowed_labels):
        try:
            replacement = _abelian_vector_eom_replacement(
                theory,
                lagrangian,
                target,
                open_index=open_index,
                sign=sign,
            )
            if replacement is not None:
                rules.append(replacement)
        except ValueError as exc:
            if strict:
                failures.append(str(exc))
    if failures:
        raise ValueError("; ".join(failures))
    return tuple(rules)


def abelian_vector_eom_field_redefinition_delta(
    theory: Theory,
    lagrangian: Expression,
    expression: Expression,
    *,
    fields: Iterable[FieldHandle | FieldDefinition | str | Expression] | None = None,
    strict: bool = False,
) -> Expression:
    """Return the bounded Abelian-vector companion to EOM replacements.

    Matchete's vector field redefinition shifts both the Abelian field strength
    and the charged covariant derivatives.  The ordinary
    :func:`eom_replacement_rules_for_expression` path accounts for replacing
    ``D_nu F_{nu mu}`` itself.  This helper adds the matching charged-current
    companion induced by shifting scalar covariant derivatives, using the same
    Symbolica pattern discovery and native coefficient extraction as the
    replacement-rule path.

    This is intentionally a first bounded subset of ``EOMSimplify``: Abelian
    gauge vectors and charged scalar currents only.
    """

    theory._validate_registered_expression(expression)
    allowed_labels = _eom_rule_allowed_field_labels(theory, fields)
    deltas: list[Expression] = []
    failures: list[str] = []
    for target, open_index, sign in _abelian_vector_eom_rule_targets(expression, allowed_labels=allowed_labels):
        try:
            replacement = _abelian_vector_eom_replacement(
                theory,
                lagrangian,
                target,
                open_index=open_index,
                sign=sign,
            )
            if replacement is None:
                continue
            coefficient = expression.coefficient(target).expand()
            if is_zero(coefficient):
                continue
            replacement_value = target.replace_multiple([replacement]).expand()
            deltas.append((coefficient * replacement_value).expand())
        except ValueError as exc:
            if strict:
                failures.append(str(exc))
    if failures:
        raise ValueError("; ".join(failures))
    return sum_expr(deltas).expand()


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


def _default_field_indices(theory: Theory, definition: FieldDefinition) -> tuple[Expression, ...]:
    return tuple(
        theory.dummy_index(index, representation)
        for index, representation in enumerate(field_indices_from_label(definition.label))
    )


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


def _abelian_vector_eom_rule_targets(
    expression: Expression,
    *,
    allowed_labels: set[str] | None,
) -> tuple[tuple[Expression, Expression, Expression], ...]:
    pattern = field_strength_pattern()
    label_is_registered_field = s.FieldStrengthLabelWildcard.req_tag(SymbolRole.FIELD.value)
    targets: dict[str, tuple[Expression, Expression, Expression]] = {}
    for atom in matching_subexpressions(expression, pattern, label_is_registered_field):
        if allowed_labels is not None and canonical_string(field_strength_label(atom)) not in allowed_labels:
            continue
        lorentz = list_items(atom[1])
        internal = list_items(atom[2])
        derivatives = field_strength_derivatives(atom)
        if len(lorentz) != 2 or internal or len(derivatives) != 1:
            continue
        derivative = derivatives[0]
        left, right = lorentz
        if bool(derivative == left):
            open_index = right
            sign = -Expression.num(1)
        elif bool(derivative == right):
            open_index = left
            sign = Expression.num(1)
        else:
            continue
        targets.setdefault(canonical_string(atom), (atom, open_index, sign))
    return tuple(targets.values())


def _abelian_vector_eom_replacement(
    theory: Theory,
    lagrangian: Expression,
    target: Expression,
    *,
    open_index: Expression,
    sign: Expression,
) -> Replacement | None:
    definition = theory._field_definition_for_label(field_strength_label(target))
    type_expr = definition.type_expr
    if not is_head(type_expr, s.Vector) or len(type_expr) != 1:
        return None
    group_symbol = type_expr[0]
    group_kind = GroupKind.from_user(str(symbol_data(group_symbol, SymbolDataKey.GROUP_KIND, GroupKind.GLOBAL.value)))
    if group_kind is not GroupKind.GAUGE or not bool(symbol_data(group_symbol, SymbolDataKey.GROUP_ABELIAN, 0)):
        return None
    coupling_name = symbol_data(group_symbol, SymbolDataKey.GROUP_COUPLING)
    if not isinstance(coupling_name, str) or coupling_name not in theory.couplings:
        return None
    current = _abelian_vector_scalar_current_sum(theory, lagrangian, group_symbol, open_index)
    if is_zero(current):
        return None
    coupling = theory.coupling_handle(coupling_name)()
    return Replacement(target, (sign * coupling**2 * current).expand())


def _abelian_vector_scalar_current_sum(
    theory: Theory,
    lagrangian: Expression,
    group_symbol: Expression,
    open_index: Expression,
) -> Expression:
    currents: list[Expression] = []
    for definition in theory.fields.values():
        if not bool(definition.type_expr == s.Scalar) or definition.is_self_conjugate:
            continue
        if not _expression_contains_field_label(lagrangian, definition.label):
            continue
        indices = _default_field_indices(theory, definition)
        field = definition.expr(*indices)
        for charge in definition.charge_exprs:
            charge_group = theory._group_symbol_for_charge(charge)
            if charge_group is None or not bool(charge_group == group_symbol):
                continue
            if len(charge) != 1:
                continue
            currents.append((charge[0] * scalar_abelian_gauge_current(open_index, field)).expand())
    return sum_expr(currents).expand()


def scalar_abelian_gauge_current(mu: Expression, field: Expression) -> Expression:
    """Return the scalar current used by Abelian vector EOM reductions."""

    return (Expression.I * s.Bar(field) * s.CD(mu, field) - Expression.I * s.CD(mu, s.Bar(field)) * field).expand()


def _expression_contains_field_label(expr: Expression, label: Expression) -> bool:
    label_key = canonical_string(label)
    for atom in matching_subexpressions(expr, field_pattern(label)):
        if canonical_string(field_label(atom)) == label_key:
            return True
    for atom in matching_subexpressions(expr, bar_field_pattern(label)):
        if is_bar_field(atom) and canonical_string(field_label(bar_field_inner(atom))) == label_key:
            return True
    return False


def eom_expression(theory: Theory, lagrangian: Expression, field: FieldHandle | FieldDefinition | str, *, eft_order: int = 6) -> Expression:
    definition = theory.fields[field] if isinstance(field, str) else field.definition if isinstance(field, FieldHandle) else field
    return s.EOM(definition.expr(), derive_eom(theory, lagrangian, definition, eft_order=eft_order))
