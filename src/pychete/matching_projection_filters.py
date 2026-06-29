from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Sequence, TypeAlias

from symbolica import Expression

from .expr import (
    bar_field_pattern,
    field_pattern,
    field_strength_pattern,
    is_head,
    is_zero,
    sum_expr,
    terms,
)
from .matching_results import (
    MatchingConditionTargetInput,
    _projection_aliases_for_target,
    _projection_atom_counts,
    _projection_atom_requirement_groups_for_expressions,
    _resolve_matching_condition_targets,
    matching_condition_targets as structured_matching_condition_targets,
)
from .symbols import SymbolDataKey, SymbolRole, canonical_string, s, symbol_data
from .theory import Theory
from .theory_metadata import (
    GroupKind,
    field_charges_from_label,
    field_indices_from_label,
    field_type_from_label,
)
from .tree_matching import HeavyScalarSolution

ProjectionAtomRequirement: TypeAlias = tuple[str, str, int]
ProjectionAtomRequirementGroups: TypeAlias = tuple[tuple[ProjectionAtomRequirement, ...], ...]


def filter_cde_terms_by_projection_requirements(
    terms_in: Sequence[Any],
    requirements: ProjectionAtomRequirementGroups | None,
) -> tuple[Any, ...]:
    if not requirements:
        return tuple(terms_in)
    return tuple(term for term in terms_in if _cde_term_matches_projection_requirements(term, requirements))


def filter_wilson_line_terms_by_projection_requirements(
    terms_in: Sequence[Any],
    requirements: ProjectionAtomRequirementGroups | None,
) -> tuple[Any, ...]:
    if not requirements:
        return tuple(terms_in)
    return tuple(term for term in terms_in if _wilson_line_term_matches_projection_requirements(term, requirements))


def wilson_line_path_with_projection_filtered_entries(
    path: Any,
    requirements: ProjectionAtomRequirementGroups | None,
) -> Any:
    if not requirements or not _projection_requirements_are_field_strength_local(requirements):
        return path
    filtered_entries = tuple(
        _filter_wilson_line_entry_expression_by_projection_requirements(path.theory, entry, requirements)
        for entry in path.entries
    )
    if all(bool(filtered == original) for filtered, original in zip(filtered_entries, path.entries, strict=True)):
        return path
    return replace(path, entries=filtered_entries)


def wilson_line_entry_can_satisfy_projection_requirements(
    path: Any,
    entry: Any,
    requirements: ProjectionAtomRequirementGroups | None,
) -> bool:
    if requirements is None:
        return True
    if not requirements:
        return True
    static_counts = _projection_atom_counts(_ncm_chain(*path.entries))
    possible_generated_strength_labels = wilson_line_path_generated_field_strength_labels(path)
    max_generated_field_strengths = entry.total_order // 2
    for group in requirements:
        if wilson_line_atom_counts_can_satisfy_requirement_group(
            static_counts,
            group,
            possible_generated_strength_labels=possible_generated_strength_labels,
            max_generated_field_strengths=max_generated_field_strengths,
        ):
            return True
    return False


def term_atom_requirements_for_targets(
    theory: Theory,
    targets: MatchingConditionTargetInput | None,
    *,
    heavy_scalar_solutions: Mapping[str, HeavyScalarSolution] | None = None,
) -> ProjectionAtomRequirementGroups | None:
    if targets is None:
        return None
    resolved = _resolve_matching_condition_targets(theory, targets)
    projection_expressions: list[Expression] = []
    for target in structured_matching_condition_targets(resolved):
        projection_expression = target.projection_expression
        if projection_expression is None:
            continue
        projection_expressions.append(projection_expression)
        projection_expressions.extend(
            alias
            for alias, _weight in _projection_aliases_for_target(
                theory,
                target,
                projection_expression,
                normalize_ibp_scalar_bilinears=False,
                include_eom_projection_aliases=True,
            )
        )
    requirements = _projection_atom_requirement_groups_for_expressions(projection_expressions)
    if requirements and heavy_scalar_solutions:
        requirements = _projection_atom_requirements_with_heavy_scalar_solution_relaxations(
            requirements,
            heavy_scalar_solutions,
        )
    return requirements or None


def wilson_line_atom_counts_can_satisfy_requirement_group(
    counts: Mapping[tuple[str, str], int],
    group: Sequence[ProjectionAtomRequirement],
    *,
    possible_generated_strength_labels: frozenset[str],
    max_generated_field_strengths: int,
) -> bool:
    for kind, label, required_count in group:
        available = counts.get((kind, label), 0)
        if kind == "field_strength" and label in possible_generated_strength_labels:
            available += max_generated_field_strengths
        if available < required_count:
            return False
    return True


def wilson_line_path_generated_field_strength_labels(path: Any) -> frozenset[str]:
    """Return field-strength labels that this Wilson-line path can generate.

    The generated-term filter still uses Symbolica pattern counts on actual
    numerators. This pre-generation check is deliberately conservative: it
    only rules out a requested field-strength label when none of the
    registered fields carried by the ordered path can produce that gauge
    strength through covariant-derivative commutators.
    """

    labels: set[str] = set()
    field_pat = field_pattern()
    bar_pat = bar_field_pattern()
    field_label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    for entry in path.entries:
        for match in entry.match(field_pat, field_label_is_tagged):
            labels.update(field_generated_field_strength_labels(path.theory, match[s.FieldLabelWildcard]))
        for match in entry.match(bar_pat, field_label_is_tagged):
            labels.update(field_generated_field_strength_labels(path.theory, match[s.FieldLabelWildcard]))
    closing_label = path.closing_field_label[0] if is_head(path.closing_field_label, s.Bar) else path.closing_field_label
    labels.update(field_generated_field_strength_labels(path.theory, closing_label))
    return frozenset(labels)


def wilson_line_term_generated_field_strength_labels(term: Any) -> frozenset[str]:
    labels: set[str] = set()
    for expr in (term.pre_wilson_numerator, term.numerator):
        if expr is None:
            continue
        labels.update(expression_generated_field_strength_labels(term.theory, expr))
    return frozenset(labels)


def expression_generated_field_strength_labels(theory: Theory, expr: Expression) -> frozenset[str]:
    labels: set[str] = set()
    field_label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    for pattern in (field_pattern(), bar_field_pattern()):
        for match in expr.match(pattern, field_label_is_tagged):
            labels.update(field_generated_field_strength_labels(theory, match[s.FieldLabelWildcard]))
    return frozenset(labels)


def field_generated_field_strength_labels(theory: Theory, label: Expression) -> frozenset[str]:
    labels: set[str] = set()
    for charge in field_charges_from_label(label):
        group_symbol = theory._group_symbol_for_charge(charge)
        if group_symbol is None:
            continue
        group_kind = GroupKind.from_user(
            str(symbol_data(group_symbol, SymbolDataKey.GROUP_KIND, GroupKind.GLOBAL.value))
        )
        if group_kind is not GroupKind.GAUGE or not bool(symbol_data(group_symbol, SymbolDataKey.GROUP_ABELIAN, 0)):
            continue
        labels.update(_group_vector_field_label_key(theory, group_symbol))

    representations = list(field_indices_from_label(label))
    field_type = field_type_from_label(label)
    if is_head(field_type, s.Vector) and len(field_type) == 1:
        representations.append(field_type[0](s.adj))
    for representation_expr in representations:
        try:
            representation = theory.representation_definition(representation_expr)
        except KeyError:
            continue
        group_entry = theory.groups.get(representation.group)
        if group_entry is None:
            continue
        group_kind = GroupKind.from_user(str(group_entry.get("kind", GroupKind.GLOBAL.value)))
        if group_kind is not GroupKind.GAUGE or bool(group_entry.get("abelian", False)):
            continue
        group_symbol = theory.symbol(representation.group, role=SymbolRole.GROUP)
        labels.update(_group_vector_field_label_key(theory, group_symbol))
    return frozenset(labels)


def _projection_requirements_are_field_strength_local(
    requirements: ProjectionAtomRequirementGroups,
) -> bool:
    return all(any(kind == "field_strength" for kind, _label, _count in group) for group in requirements)


def _filter_wilson_line_entry_expression_by_projection_requirements(
    theory: Theory,
    entry: Expression,
    requirements: ProjectionAtomRequirementGroups,
) -> Expression:
    kept: list[Expression] = []
    for term in terms(entry.expand()):
        if _wilson_line_entry_term_can_contribute_to_projection_requirements(theory, term, requirements):
            kept.append(term)
    return sum_expr(kept).expand()


def _wilson_line_entry_term_can_contribute_to_projection_requirements(
    theory: Theory,
    term: Expression,
    requirements: ProjectionAtomRequirementGroups,
) -> bool:
    field_labels = _projection_field_labels_in_expression(term)
    strength_labels = _projection_field_strength_labels_in_expression(term)
    if not field_labels and not strength_labels:
        return True
    for group in requirements:
        required_fields = {label for kind, label, _count in group if kind == "field"}
        required_strengths = {label for kind, label, _count in group if kind == "field_strength"}
        if not strength_labels.issubset(required_strengths):
            continue
        if all(
            label in required_fields
            or bool(field_generated_field_strength_labels(theory, label_expr) & required_strengths)
            for label, label_expr in field_labels.items()
        ):
            return True
    return False


def _projection_field_labels_in_expression(expr: Expression) -> dict[str, Expression]:
    label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    labels: dict[str, Expression] = {}
    for match in expr.match(field_pattern(), label_is_tagged):
        label = match[s.FieldLabelWildcard]
        labels.setdefault(canonical_string(label), label)
    return labels


def _projection_field_strength_labels_in_expression(expr: Expression) -> set[str]:
    label_is_tagged = s.FieldStrengthLabelWildcard.req_tag(SymbolRole.FIELD.value)
    return {
        canonical_string(match[s.FieldStrengthLabelWildcard])
        for match in expr.match(field_strength_pattern(), label_is_tagged)
    }


def _cde_term_matches_projection_requirements(
    term: Any,
    requirements: ProjectionAtomRequirementGroups,
) -> bool:
    return _term_numerator_matches_projection_requirements(term.numerator, requirements)


def _term_numerator_matches_projection_requirements(
    numerator: Expression,
    requirements: ProjectionAtomRequirementGroups,
) -> bool:
    counts = _projection_atom_counts(numerator)
    for group in requirements:
        if all(counts[(kind, label)] >= required_count for kind, label, required_count in group):
            return True
    return False


def _wilson_line_term_matches_projection_requirements(
    term: Any,
    requirements: ProjectionAtomRequirementGroups,
) -> bool:
    counts = _projection_atom_counts(term.numerator)
    possible_generated_strength_labels = wilson_line_term_generated_field_strength_labels(term)
    max_generated_field_strengths = sum(len(indices) for indices in term.expansion_indices) // 2
    for group in requirements:
        if wilson_line_atom_counts_can_satisfy_requirement_group(
            counts,
            group,
            possible_generated_strength_labels=possible_generated_strength_labels,
            max_generated_field_strengths=max_generated_field_strengths,
        ):
            return True
    return False


def _projection_atom_requirements_with_heavy_scalar_solution_relaxations(
    requirements: ProjectionAtomRequirementGroups,
    heavy_scalar_solutions: Mapping[str, HeavyScalarSolution],
) -> ProjectionAtomRequirementGroups:
    """Return requirements that also keep terms made relevant by heavy EOMs.

    Matchete applies ``ReplaceHeavyEOM`` after evaluating matching-mode
    supertraces. Wilson-line target filtering therefore has to keep terms that
    are short of the final operator's light fields only because they still
    contain a heavy scalar that will be replaced by its EOM solution.
    """

    relaxed: list[tuple[ProjectionAtomRequirement, ...]] = list(requirements)
    seen = set(relaxed)
    for group in requirements:
        for solution in heavy_scalar_solutions.values():
            heavy_key = ("field", canonical_string(solution.field.label))
            for contribution in _heavy_scalar_solution_projection_atom_contribution_groups(solution):
                max_substitutions = _max_heavy_scalar_filter_substitutions(group, contribution)
                for count in range(1, max_substitutions + 1):
                    relaxed_group = _relax_projection_atom_requirement_group(
                        group,
                        heavy_key=heavy_key,
                        contribution=contribution,
                        count=count,
                    )
                    if relaxed_group is None or relaxed_group in seen:
                        continue
                    seen.add(relaxed_group)
                    relaxed.append(relaxed_group)
    return tuple(relaxed)


def _heavy_scalar_solution_projection_atom_contribution_groups(
    solution: HeavyScalarSolution,
) -> tuple[Mapping[tuple[str, str], int], ...]:
    contribution_groups: list[Mapping[tuple[str, str], int]] = []
    seen: set[tuple[tuple[tuple[str, str], int], ...]] = set()
    expressions = (solution.inclusive, solution.inclusive_conjugate)
    for expr in expressions:
        for term in terms(expr.expand()):
            counts = _projection_atom_counts(term)
            if not counts:
                continue
            key = tuple(sorted(counts.items()))
            if key in seen:
                continue
            seen.add(key)
            contribution_groups.append(counts)
    return tuple(contribution_groups)


def _max_heavy_scalar_filter_substitutions(
    group: Sequence[ProjectionAtomRequirement],
    contribution: Mapping[tuple[str, str], int],
) -> int:
    max_substitutions = 0
    for kind, label, required_count in group:
        contribution_count = contribution.get((kind, label), 0)
        if contribution_count <= 0:
            continue
        max_substitutions = max(
            max_substitutions,
            (required_count + contribution_count - 1) // contribution_count,
        )
    return max_substitutions


def _relax_projection_atom_requirement_group(
    group: Sequence[ProjectionAtomRequirement],
    *,
    heavy_key: tuple[str, str],
    contribution: Mapping[tuple[str, str], int],
    count: int,
) -> tuple[ProjectionAtomRequirement, ...] | None:
    remaining = {(kind, label): required_count for kind, label, required_count in group}
    changed = False
    for key, contribution_count in contribution.items():
        required_count = remaining.get(key)
        if required_count is None:
            continue
        relaxed_count = max(0, required_count - count * contribution_count)
        if relaxed_count != required_count:
            changed = True
        if relaxed_count:
            remaining[key] = relaxed_count
        else:
            remaining.pop(key, None)
    if not changed:
        return None
    remaining[heavy_key] = remaining.get(heavy_key, 0) + count
    return tuple((kind, label, required_count) for (kind, label), required_count in sorted(remaining.items()))


def _group_vector_field_label_key(theory: Theory, group_symbol: Expression) -> tuple[str, ...]:
    vector_name = symbol_data(group_symbol, SymbolDataKey.GROUP_FIELD)
    if not isinstance(vector_name, str) or vector_name not in theory.fields:
        return ()
    return (canonical_string(theory.fields[vector_name].label),)


def _ncm_chain(*operands: Expression) -> Expression:
    kept = tuple(operand for operand in operands if not is_zero(operand) and not bool(operand == Expression.num(1)))
    if len(kept) != len(operands) and any(is_zero(operand) for operand in operands):
        return Expression.num(0)
    if not kept:
        return Expression.num(1)
    if len(kept) == 1:
        return kept[0]
    return s.NCM(*kept)


__all__ = [
    "ProjectionAtomRequirement",
    "ProjectionAtomRequirementGroups",
    "expression_generated_field_strength_labels",
    "field_generated_field_strength_labels",
    "filter_cde_terms_by_projection_requirements",
    "filter_wilson_line_terms_by_projection_requirements",
    "term_atom_requirements_for_targets",
    "wilson_line_atom_counts_can_satisfy_requirement_group",
    "wilson_line_entry_can_satisfy_projection_requirements",
    "wilson_line_path_generated_field_strength_labels",
    "wilson_line_path_with_projection_filtered_entries",
    "wilson_line_term_generated_field_strength_labels",
]
