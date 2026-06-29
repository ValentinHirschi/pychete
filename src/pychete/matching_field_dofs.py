from __future__ import annotations

from typing import Any

from symbolica import Expression

from .expr import (
    bar_field_inner,
    bar_field_pattern,
    field_label,
    field_pattern,
    field_strength_pattern,
    is_bar_field,
    is_head,
    list_expr,
)
from .symbols import SymbolRole, canonical_string, s
from .theory import Theory
from .theory_metadata import (
    field_indices_from_label,
    field_propagating_from_label,
    field_self_conjugate_from_label,
    field_type_from_label,
)


def matchete_fluctuation_dof_basis_fields(theory: Theory, lagrangian: Expression) -> tuple[Expression, ...]:
    """Return label-level fluctuation DOFs in Matchete's ``$XFieldDofs`` style.

    Runtime fluctuation matrices currently discover every concrete field atom
    they see. That is useful for exact local diagnostics, but it can duplicate
    algebraically equivalent dummy-index components before supertrace path
    generation. Matchete enumerates one field DOF per field label/conjugation
    and carries component sums through index algebra. This helper exposes that
    cheaper label-level boundary so Wilson-line parity checks can compare the
    same class of paths before expensive tensor reduction.
    """

    theory._validate_registered_expression(lagrangian)
    entries: dict[tuple[str, bool], Expression] = {}
    label_condition = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    for pattern in (bar_field_pattern(), field_pattern()):
        for match in lagrangian.match(pattern, label_condition):
            _add_matchete_dof_basis_field(theory, entries, pattern.replace_wildcards(match))
    strength_condition = s.FieldStrengthLabelWildcard.req_tag(SymbolRole.FIELD.value)
    for match in lagrangian.match(field_strength_pattern(), strength_condition):
        label = match[s.FieldStrengthLabelWildcard]
        _add_matchete_dof_basis_label(theory, entries, label, barred=False)
    return tuple(entries[key] for key in sorted(entries))


def wilson_line_path_component_weight(path: Any) -> int | None:
    """Return the internal-index component weight for a label-level path.

    The weight is the product of known internal dimensions for each distinct
    field label carried by a Wilson-line path. It is intended for canonical
    label-level DOF paths, where repeated appearances of the same field label
    represent one traced internal index line rather than independent component
    choices. If any required dimension is unknown, ``None`` is returned so the
    caller can keep the explicit-component route.
    """

    weight = 1
    seen_labels: set[str] = set()
    for mode in path.propagator_modes:
        label_key = canonical_string(mode.label)
        if label_key in seen_labels:
            continue
        seen_labels.add(label_key)
        dimension = mode.internal_dimension
        if dimension is None:
            return None
        weight *= dimension
    return weight


def _add_matchete_dof_basis_field(
    theory: Theory,
    entries: dict[tuple[str, bool], Expression],
    atom: Expression,
) -> None:
    base = bar_field_inner(atom) if is_bar_field(atom) else atom
    if not is_head(base, s.Field):
        return
    label = field_label(base)
    if not field_propagating_from_label(label):
        return
    if field_self_conjugate_from_label(label):
        _add_matchete_dof_basis_label(theory, entries, label, barred=False)
        return
    _add_matchete_dof_basis_label(theory, entries, label, barred=True)
    _add_matchete_dof_basis_label(theory, entries, label, barred=False)


def _add_matchete_dof_basis_label(
    theory: Theory,
    entries: dict[tuple[str, bool], Expression],
    label: Expression,
    *,
    barred: bool,
) -> None:
    if not field_propagating_from_label(label):
        return
    key = (canonical_string(label), barred)
    entries.setdefault(key, _canonical_dof_field(theory, label, barred=barred))


def _canonical_dof_field(theory: Theory, label: Expression, *, barred: bool) -> Expression:
    indices = tuple(
        theory.dummy_index(slot + 1, representation)
        for slot, representation in enumerate(field_indices_from_label(label))
    )
    field = s.Field(
        label,
        field_type_from_label(label),
        list_expr(*indices),
        s.List(),
    )
    return s.Bar(field) if barred else field
