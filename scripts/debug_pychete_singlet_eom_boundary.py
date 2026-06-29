#!/usr/bin/env python
"""Dump pychete-side Singlet cHD EOMSimplify boundary probes.

This development-only helper pairs with
``helper_mathematica_scripts/debug_singlet_eom_simplify.wls``.  It consumes
committed pychete/Matchete-independent fixtures and writes a compact JSON
summary for the current Singlet ``cHD`` frontier. Runtime pychete code and
pytest must not depend on this script.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from symbolica import Expression, Replacement

import pychete.matching as matching_module
from pychete import (
    MatchingResult,
    OneLoopNormalization,
    canonical_string,
    load_validation_fixture,
    one_loop_normalization_factor,
    s,
)
from pychete.backends import vakint as vakint_backend
from pychete.expr import (
    field_derivatives,
    field_with_derivatives,
    field_pattern,
    field_strength_derivatives,
    field_strength_label,
    field_strength_pattern,
    is_head,
    is_zero,
    list_items,
    matching_subexpressions,
    terms,
)
from pychete.functional import expose_abelian_vector_eom_currents, scalar_eom_identities
from pychete.matching_results import registered_wilson_matching_condition_targets

_MATHEMATICA_XTERM_PATTERN = re.compile(
    r"Xterm\[\{([^}]*)\},\s*\{[^}]*\},\s*(\d+),\s*(\d+),\s*(\d+)\]"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"),
    )
    parser.add_argument(
        "--reference-fixture",
        type=Path,
        default=Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json"),
    )
    parser.add_argument(
        "--matchete-eom-debug",
        type=Path,
        default=Path("assets/validation/matchete/debug/singlet_eom_cHD.debug.json"),
    )
    parser.add_argument(
        "--matchete-trace-debug",
        type=Path,
        default=Path(
            "assets/validation/matchete/debug/"
            "singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.full.debug.json"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json"),
    )
    parser.add_argument("--max-total-order", type=int, default=2)
    parser.add_argument("--max-slot-order", type=int, default=2)
    parser.add_argument("--index-prefix", default="debug_singlet_eom_boundary")
    parser.add_argument(
        "--include-green-heavy-stages",
        action="store_true",
        help="Also project post-Green and post-heavy selected-trace stages; slower.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def _project(theory: Any, condition_name: str, target: Expression, expr: Expression) -> Expression:
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=expr,
    )
    return result.project_matching_conditions(
        {condition_name: target},
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
        drop_zero=False,
    )[condition_name]


def _project_source_operator_coefficients(
    theory: Any,
    targets: dict[str, Expression],
    expr: Expression,
) -> dict[str, Expression]:
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=expr,
        on_shell_eft_lagrangian=expr,
    )
    return result.project_matching_conditions(
        targets,
        source="off_shell_eft_lagrangian",
        expand_source=False,
        normalize_derivative_operators=False,
        eft_order=None,
        drop_zero=False,
    )


def _source_vector_eom_operator_targets(
    theory: Any,
    *,
    vector_field: str,
    index_prefix: str,
) -> dict[str, Expression]:
    higgs = theory.field_handle("H")
    vector = theory.field_handle(vector_field)
    fund = theory.fields["H"].indices[0]
    i = theory.index(theory.symbol(f"{index_prefix}_higgs_i"), fund)
    mu = theory.index(theory.symbol(f"{index_prefix}_mu"), s.Lorentz)
    higgs_field = higgs(i)
    derivative_higgs = field_with_derivatives(higgs_field, (mu,))
    vector_eom = s.EOM(vector(mu))
    return {
        "barH_EOMB_DH": s.Bar(higgs_field) * vector_eom * derivative_higgs,
        "DbarH_EOMB_H": s.Bar(derivative_higgs) * vector_eom * higgs_field,
        "H_EOMB_DH_unbarred": higgs_field * vector_eom * derivative_higgs,
        "DH_EOMB_H_unbarred": derivative_higgs * vector_eom * higgs_field,
    }


def _projection_strings(
    theory: Any,
    condition_name: str,
    target: Expression,
    expressions: dict[str, Expression],
) -> dict[str, str]:
    return {
        name: canonical_string(_project(theory, condition_name, target, expr))
        for name, expr in expressions.items()
    }


def _sum_expressions(expressions: list[Expression]) -> Expression:
    total = Expression.num(0)
    for expr in expressions:
        total = (total + expr).expand()
    return total


def _projection_sum(
    theory: Any,
    condition_name: str,
    target: Expression,
    expressions: list[Expression],
) -> Expression:
    return _sum_expressions([
        _project(theory, condition_name, target, expr)
        for expr in expressions
    ])


def _projected_stage_order_map(
    theory: Any,
    condition_name: str,
    target: Expression,
    expressions_by_stage_and_order: dict[str, dict[int, list[Expression]]],
) -> dict[str, dict[int, Expression]]:
    projected: dict[str, dict[int, Expression]] = {}
    for stage_name, expressions_by_order in expressions_by_stage_and_order.items():
        projected[stage_name] = {}
        for order, expressions in sorted(expressions_by_order.items()):
            print(
                f"Projecting {stage_name} total_order={order} chunks={len(expressions)}",
                flush=True,
            )
            projected[stage_name][order] = _projection_sum(theory, condition_name, target, expressions)
    return projected


def _field_strength_divergence_count(theory: Any, expr: Expression, *, field_name: str) -> int:
    label = theory.field_handle(field_name).label
    count = 0
    for atom in matching_subexpressions(expr, field_strength_pattern()):
        if not bool(field_strength_label(atom) == label):
            continue
        lorentz = list_items(atom[1])
        derivatives = field_strength_derivatives(atom)
        if len(lorentz) != 2 or len(derivatives) != 1:
            continue
        if bool(derivatives[0] == lorentz[0]) or bool(derivatives[0] == lorentz[1]):
            count += 1
    return count


def _formal_eom_count(expr: Expression) -> int:
    return len(matching_subexpressions(expr, s.EOM(s.CDBodyWildcard)))


def _formal_vector_eom_count(theory: Any, expr: Expression, *, field_name: str) -> int:
    label = theory.field_handle(field_name).label
    count = 0
    for atom in matching_subexpressions(expr, s.EOM(field_pattern(label))):
        body = atom[0]
        if field_derivatives(body):
            continue
        if any(is_head(index, s.Index) and bool(index[1] == s.Lorentz) for index in list_items(body[2])):
            count += 1
    return count


def _formal_vector_eom_term_samples(
    theory: Any,
    expr: Expression,
    *,
    field_name: str,
    max_samples: int = 3,
) -> list[str]:
    label = theory.field_handle(field_name).label
    samples: list[str] = []
    for term in terms(expr.expand()):
        if is_zero(term):
            continue
        if not any(matching_subexpressions(term, s.EOM(field_pattern(label)))):
            continue
        samples.append(canonical_string(term))
        if len(samples) >= max_samples:
            break
    return samples


def _eom_exposure_probe(
    theory: Any,
    lagrangian: Expression,
    entry_expressions: dict[str, Expression],
    *,
    condition_name: str,
    target: Expression,
    vector_field: str,
    scalar_field: str,
    heavy_replacements: tuple[Replacement, ...] = (),
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    by_entry: dict[str, dict[str, Any]] = {}
    scalar_eom_exposed_vector_delta_projections: list[Expression] = []
    scalar_eom_exposed_heavy_vector_delta_projections: list[Expression] = []
    for entry_label, expr in entry_expressions.items():
        vector_exposed = expose_abelian_vector_eom_currents(
            theory,
            expr,
            fields=[vector_field],
        )
        vector_delta = theory.abelian_vector_eom_field_redefinition_delta(
            lagrangian,
            expr,
            fields=[vector_field],
            strict=True,
        )
        vector_exposed_delta = theory.abelian_vector_eom_field_redefinition_delta(
            lagrangian,
            vector_exposed,
            fields=[vector_field],
            strict=True,
        )
        scalar_identities = scalar_eom_identities(
            theory,
            lagrangian,
            expr,
            fields=[scalar_field],
            max_identities=512,
        )
        scalar_eom_exposure_error: str | None = None
        try:
            scalar_eom_exposed = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
                theory,
                expr,
                eom_lagrangian=lagrangian,
                expose_scalar_eom_terms=True,
            )
        except ValueError as exc:
            scalar_eom_exposed = expr
            scalar_eom_exposure_error = str(exc)
        scalar_eom_source_lagrangian = (lagrangian + scalar_eom_exposed).expand()
        scalar_eom_delta_error: str | None = None
        try:
            _, scalar_eom_field_redefinition_delta = (
                matching_module._apply_wilson_line_scalar_eom_field_redefinition(
                    theory,
                    scalar_eom_exposed,
                    source_lagrangian=scalar_eom_source_lagrangian,
                    max_order=6,
                    fields=[scalar_field],
                    strict=True,
                )
            )
        except ValueError as exc:
            scalar_eom_field_redefinition_delta = Expression.num(0)
            scalar_eom_delta_error = str(exc)
        scalar_eom_exposed_vector_delta_error: str | None = None
        try:
            scalar_eom_exposed_vector_delta = theory.abelian_vector_eom_field_redefinition_delta(
                lagrangian,
                scalar_eom_exposed,
                fields=[vector_field],
                strict=True,
            )
        except ValueError as exc:
            scalar_eom_exposed_vector_delta = Expression.num(0)
            scalar_eom_exposed_vector_delta_error = str(exc)
        scalar_eom_exposed_vector_delta_projection = _project(
            theory,
            condition_name,
            target,
            scalar_eom_exposed_vector_delta,
        )
        scalar_eom_exposed_vector_delta_projections.append(scalar_eom_exposed_vector_delta_projection)
        formal_vector_count = _formal_vector_eom_count(
            theory,
            scalar_eom_exposed,
            field_name=vector_field,
        )
        heavy_vector_delta = Expression.num(0)
        heavy_vector_delta_error: str | None = None
        if heavy_replacements and formal_vector_count:
            try:
                scalar_eom_exposed_heavy = scalar_eom_exposed.replace_multiple(
                    heavy_replacements,
                    repeat=False,
                ).expand()
                heavy_vector_delta = theory.abelian_vector_eom_field_redefinition_delta(
                    lagrangian,
                    scalar_eom_exposed_heavy,
                    fields=[vector_field],
                    strict=True,
                )
            except ValueError as exc:
                heavy_vector_delta = Expression.num(0)
                heavy_vector_delta_error = str(exc)
        heavy_vector_delta_projection = _project(
            theory,
            condition_name,
            target,
            heavy_vector_delta,
        )
        scalar_eom_exposed_heavy_vector_delta_projections.append(heavy_vector_delta_projection)
        by_entry[entry_label] = {
            "byte_count": expr.get_byte_size(),
            "field_strength_count": len(matching_subexpressions(expr, field_strength_pattern())),
            "formal_vector_eom_count": _formal_vector_eom_count(
                theory,
                expr,
                field_name=vector_field,
            ),
            "vector_field_strength_divergence_count": _field_strength_divergence_count(
                theory,
                expr,
                field_name=vector_field,
            ),
            "vector_eom_current_exposed_byte_count": vector_exposed.get_byte_size(),
            "vector_eom_current_exposed_field_strength_divergence_count": (
                _field_strength_divergence_count(
                    theory,
                    vector_exposed,
                    field_name=vector_field,
                )
            ),
            "scalar_eom_identity_count": len(scalar_identities),
            "scalar_eom_exposure_error": scalar_eom_exposure_error,
            "scalar_eom_exposed_byte_count": scalar_eom_exposed.get_byte_size(),
            "scalar_eom_exposed_formal_eom_count": _formal_eom_count(scalar_eom_exposed),
            "scalar_eom_exposed_formal_vector_eom_count": formal_vector_count,
            "scalar_eom_exposed_formal_vector_eom_term_samples": _formal_vector_eom_term_samples(
                theory,
                scalar_eom_exposed,
                field_name=vector_field,
            ),
            "scalar_eom_exposed_vector_field_strength_divergence_count": (
                _field_strength_divergence_count(
                    theory,
                    scalar_eom_exposed,
                    field_name=vector_field,
                )
            ),
            "scalar_eom_field_redefinition_delta_is_zero": bool(
                scalar_eom_field_redefinition_delta == Expression.num(0)
            ),
            "scalar_eom_field_redefinition_delta_byte_count": (
                scalar_eom_field_redefinition_delta.get_byte_size()
            ),
            "scalar_eom_field_redefinition_delta_error": scalar_eom_delta_error,
            "scalar_eom_exposed_vector_field_redefinition_delta_is_zero": bool(
                scalar_eom_exposed_vector_delta == Expression.num(0)
            ),
            "scalar_eom_exposed_vector_field_redefinition_delta_byte_count": (
                scalar_eom_exposed_vector_delta.get_byte_size()
            ),
            "scalar_eom_exposed_vector_field_redefinition_delta_error": (
                scalar_eom_exposed_vector_delta_error
            ),
            "scalar_eom_exposed_vector_field_redefinition_delta_projection": canonical_string(
                scalar_eom_exposed_vector_delta_projection
            ),
            "scalar_eom_exposed_vector_field_redefinition_delta_projection_is_zero": bool(
                scalar_eom_exposed_vector_delta_projection == Expression.num(0)
            ),
            "scalar_eom_exposed_heavy_vector_field_redefinition_delta_is_zero": bool(
                heavy_vector_delta == Expression.num(0)
            ),
            "scalar_eom_exposed_heavy_vector_field_redefinition_delta_byte_count": (
                heavy_vector_delta.get_byte_size()
            ),
            "scalar_eom_exposed_heavy_vector_field_redefinition_delta_error": heavy_vector_delta_error,
            "scalar_eom_exposed_heavy_vector_field_redefinition_delta_projection": canonical_string(
                heavy_vector_delta_projection
            ),
            "scalar_eom_exposed_heavy_vector_field_redefinition_delta_projection_is_zero": bool(
                heavy_vector_delta_projection == Expression.num(0)
            ),
            "vector_field_redefinition_delta_is_zero": bool(vector_delta == Expression.num(0)),
            "vector_field_redefinition_delta_byte_count": vector_delta.get_byte_size(),
            "vector_eom_current_exposed_delta_is_zero": bool(vector_exposed_delta == Expression.num(0)),
            "vector_eom_current_exposed_delta_byte_count": vector_exposed_delta.get_byte_size(),
        }
    summary = {
        "entry_count": len(by_entry),
        "field_strength_count": sum(row["field_strength_count"] for row in by_entry.values()),
        "formal_vector_eom_count": sum(row["formal_vector_eom_count"] for row in by_entry.values()),
        "vector_field_strength_divergence_count": sum(
            row["vector_field_strength_divergence_count"] for row in by_entry.values()
        ),
        "vector_eom_current_exposed_field_strength_divergence_count": sum(
            row["vector_eom_current_exposed_field_strength_divergence_count"] for row in by_entry.values()
        ),
        "scalar_eom_identity_count": sum(row["scalar_eom_identity_count"] for row in by_entry.values()),
        "scalar_eom_exposed_formal_eom_count": sum(
            row["scalar_eom_exposed_formal_eom_count"] for row in by_entry.values()
        ),
        "scalar_eom_exposed_formal_vector_eom_count": sum(
            row["scalar_eom_exposed_formal_vector_eom_count"] for row in by_entry.values()
        ),
        "scalar_eom_exposed_vector_field_strength_divergence_count": sum(
            row["scalar_eom_exposed_vector_field_strength_divergence_count"] for row in by_entry.values()
        ),
        "scalar_eom_exposure_error_count": sum(
            row["scalar_eom_exposure_error"] is not None for row in by_entry.values()
        ),
        "nonzero_scalar_eom_field_redefinition_delta_entry_count": sum(
            not row["scalar_eom_field_redefinition_delta_is_zero"] for row in by_entry.values()
        ),
        "scalar_eom_field_redefinition_delta_error_count": sum(
            row["scalar_eom_field_redefinition_delta_error"] is not None for row in by_entry.values()
        ),
        "nonzero_scalar_eom_exposed_vector_field_redefinition_delta_entry_count": sum(
            not row["scalar_eom_exposed_vector_field_redefinition_delta_is_zero"] for row in by_entry.values()
        ),
        "scalar_eom_exposed_vector_field_redefinition_delta_error_count": sum(
            row["scalar_eom_exposed_vector_field_redefinition_delta_error"] is not None
            for row in by_entry.values()
        ),
        "nonzero_scalar_eom_exposed_vector_field_redefinition_delta_projection_entry_count": sum(
            not row["scalar_eom_exposed_vector_field_redefinition_delta_projection_is_zero"]
            for row in by_entry.values()
        ),
        "scalar_eom_exposed_vector_field_redefinition_delta_projection_sum": canonical_string(
            _sum_expressions(scalar_eom_exposed_vector_delta_projections)
        ),
        "nonzero_scalar_eom_exposed_heavy_vector_field_redefinition_delta_entry_count": sum(
            not row["scalar_eom_exposed_heavy_vector_field_redefinition_delta_is_zero"]
            for row in by_entry.values()
        ),
        "scalar_eom_exposed_heavy_vector_field_redefinition_delta_error_count": sum(
            row["scalar_eom_exposed_heavy_vector_field_redefinition_delta_error"] is not None
            for row in by_entry.values()
        ),
        "nonzero_scalar_eom_exposed_heavy_vector_field_redefinition_delta_projection_entry_count": sum(
            not row["scalar_eom_exposed_heavy_vector_field_redefinition_delta_projection_is_zero"]
            for row in by_entry.values()
        ),
        "scalar_eom_exposed_heavy_vector_field_redefinition_delta_projection_sum": canonical_string(
            _sum_expressions(scalar_eom_exposed_heavy_vector_delta_projections)
        ),
        "nonzero_vector_field_redefinition_delta_entry_count": sum(
            not row["vector_field_redefinition_delta_is_zero"] for row in by_entry.values()
        ),
        "nonzero_vector_eom_current_exposed_delta_entry_count": sum(
            not row["vector_eom_current_exposed_delta_is_zero"] for row in by_entry.values()
        ),
    }
    return by_entry, summary


def _source_trace_vector_eom_probe(
    theory: Any,
    lagrangian: Expression,
    setup: Any,
    requirements: Any,
    normalization: Expression,
    *,
    condition_name: str,
    target: Expression,
    vector_field: str,
    trace_name: str,
    max_total_order: int,
    max_slot_order: int,
    index_prefix: str,
) -> dict[str, Any]:
    plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=(trace_name,),
        max_total_order=max_total_order,
        max_slot_order=max_slot_order,
        index_prefix=index_prefix,
    )
    grouped_terms = setup.interaction_wilson_line_expansion_terms_by_trace(
        plan,
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=False,
        max_wilson_derivative_order=4,
        simplify_pychete_color_algebra=True,
        term_atom_requirements=requirements,
    )
    evaluated_by_entry = matching_module._wilson_line_internal_evaluated_terms_by_entry_from_terms(
        theory,
        grouped_terms,
        tensor_reduce=True,
        tensor_reduce_engine=None,
        tensor_reduce_before_wilson_expand=True,
        max_wilson_derivative_order=4,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=False,
        simplify_pychete_color_algebra=True,
        expose_scalar_derivative_commutator_bilinears=False,
        epsilon=None,
        mu_r_squared=None,
    )
    plan_entries_by_label = {entry.label: entry for entry in plan.entries}
    by_entry: dict[str, dict[str, Any]] = {}
    projections: list[Expression] = []
    source_operator_targets = _source_vector_eom_operator_targets(
        theory,
        vector_field=vector_field,
        index_prefix=f"{index_prefix}_source_projection",
    )
    source_operator_projection_sums: dict[str, list[Expression]] = {
        name: [] for name in source_operator_targets
    }
    for entry_label, evaluated_terms in sorted(evaluated_by_entry.items()):
        if not evaluated_terms:
            continue
        normalized = (normalization * sum(evaluated_terms, Expression.num(0))).expand()
        pole_finite = (
            vakint_backend.pole_part(normalized)
            + vakint_backend.finite_part(normalized)
        ).expand()
        scalar_eom_exposed = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
            theory,
            pole_finite,
            eom_lagrangian=lagrangian,
            expose_scalar_eom_terms=True,
        )
        vector_delta = theory.abelian_vector_eom_field_redefinition_delta(
            lagrangian,
            scalar_eom_exposed,
            fields=[vector_field],
            strict=True,
        )
        projection = _project(theory, condition_name, target, vector_delta)
        projections.append(projection)
        source_operator_projections = _project_source_operator_coefficients(
            theory,
            source_operator_targets,
            scalar_eom_exposed,
        )
        for name, projected in source_operator_projections.items():
            source_operator_projection_sums[name].append(projected)
        by_entry[entry_label] = {
            "total_order": plan_entries_by_label[entry_label].total_order,
            "slot_orders": list(plan_entries_by_label[entry_label].slot_orders),
            "evaluated_term_count": len(evaluated_terms),
            "pole_finite_byte_count": pole_finite.get_byte_size(),
            "scalar_eom_exposed_byte_count": scalar_eom_exposed.get_byte_size(),
            "scalar_eom_exposed_formal_vector_eom_count": _formal_vector_eom_count(
                theory,
                scalar_eom_exposed,
                field_name=vector_field,
            ),
            "scalar_eom_exposed_formal_vector_eom_term_samples": (
                _formal_vector_eom_term_samples(
                    theory,
                    scalar_eom_exposed,
                    field_name=vector_field,
                )
            ),
            "vector_field_redefinition_delta_is_zero": bool(vector_delta == Expression.num(0)),
            "vector_field_redefinition_delta_byte_count": vector_delta.get_byte_size(),
            "vector_field_redefinition_delta_projection": canonical_string(projection),
            "vector_field_redefinition_delta_projection_is_zero": bool(
                projection == Expression.num(0)
            ),
            "formal_vector_eom_source_operator_projections": {
                name: canonical_string(projected)
                for name, projected in source_operator_projections.items()
            },
            "nonzero_formal_vector_eom_source_operator_projection_names": [
                name
                for name, projected in source_operator_projections.items()
                if not is_zero(projected)
            ],
        }
    return {
        "controls": {
            "trace_name": trace_name,
            "max_total_order": max_total_order,
            "max_slot_order": max_slot_order,
            "index_prefix": index_prefix,
            "act_open_derivatives": True,
            "tensor_reduce_before_wilson_expand": True,
            "filter_terms_by_matching_targets": requirements is not None,
        },
        "term_counts_by_entry": {entry: len(terms) for entry, terms in grouped_terms.items()},
        "term_counts_by_total_order": {
            str(order): sum(
                len(grouped_terms[entry.label])
                for entry in plan.entries
                if entry.total_order == order
            )
            for order in sorted({entry.total_order for entry in plan.entries})
        },
        "evaluated_term_counts_by_entry": {
            entry: len(evaluated_by_entry.get(entry, ())) for entry in grouped_terms
        },
        "by_entry": by_entry,
        "summary": {
            "entry_count": len(by_entry),
            "nonzero_vector_field_redefinition_delta_entry_count": sum(
                not row["vector_field_redefinition_delta_is_zero"]
                for row in by_entry.values()
            ),
            "nonzero_vector_field_redefinition_delta_projection_entry_count": sum(
                not row["vector_field_redefinition_delta_projection_is_zero"]
                for row in by_entry.values()
            ),
            "scalar_eom_exposed_formal_vector_eom_count": sum(
                row["scalar_eom_exposed_formal_vector_eom_count"]
                for row in by_entry.values()
            ),
            "vector_field_redefinition_delta_projection_sum": canonical_string(
                _sum_expressions(projections)
            ),
            "formal_vector_eom_source_operator_projection_sums": {
                name: canonical_string(_sum_expressions(values))
                for name, values in source_operator_projection_sums.items()
            },
            "nonzero_formal_vector_eom_source_operator_projection_names": [
                name
                for name, values in source_operator_projection_sums.items()
                if not is_zero(_sum_expressions(values))
            ],
        },
    }


def _matchete_internal_dim6_dev3_delta(matchete_eom_debug: dict[str, Any]) -> dict[str, Any]:
    stages = (
        matchete_eom_debug.get("raw_lagrangian_eft_eom_boundary", {})
        .get("internal_field_redefinition_replay", {})
        .get("stages", [])
    )
    if not isinstance(stages, list):
        return {}
    for index, stage in enumerate(stages):
        if isinstance(stage, dict) and stage.get("name") == "after_shift_dim6_dev3":
            selection = stage.get("selection_before_shift")
            return {
                "stage_index": index,
                "stage_name": stage.get("name"),
                "delta_from_replay_source_input_form": stage.get("delta_from_replay_source_input_form"),
                "coefficient_input_form": stage.get("coefficient_input_form"),
                "selection_selected_term_count": (
                    selection.get("selected_term_count") if isinstance(selection, dict) else None
                ),
                "selection_selected_eom_field_labels_input_form": (
                    selection.get("selected_eom_field_labels_input_form") if isinstance(selection, dict) else None
                ),
                "selection_selected_eom_terms_input_form": (
                    selection.get("selected_eom_terms_input_form") if isinstance(selection, dict) else None
                ),
            }
    return {}


def _projection_strings_from_order_map(
    projected_by_stage_and_order: dict[str, dict[int, Expression]],
) -> dict[str, str]:
    return {
        stage_name: canonical_string(_sum_expressions(list(projections_by_order.values())))
        for stage_name, projections_by_order in projected_by_stage_and_order.items()
    }


def _projection_order_strings_from_order_map(
    projected_by_stage_and_order: dict[str, dict[int, Expression]],
) -> dict[str, dict[str, str]]:
    return {
        stage_name: {
            str(order): canonical_string(expr)
            for order, expr in sorted(projections_by_order.items())
        }
        for stage_name, projections_by_order in projected_by_stage_and_order.items()
    }


def _matchete_xterm_signatures(replacement: str) -> list[dict[str, Any]]:
    return [
        {
            "fields": fields.replace("Matchete`PackageScope`", "").replace("\\[Phi]", "phi"),
            "base_order": int(base_order),
            "momentum_order": int(momentum_order),
            "open_cd_order": int(open_cd_order),
        }
        for fields, base_order, momentum_order, open_cd_order in _MATHEMATICA_XTERM_PATTERN.findall(replacement)
    ]


def _matchete_quarter_insertions(debug: dict[str, Any]) -> list[dict[str, Any]]:
    insertions = debug.get("insertions", ())
    if not isinstance(insertions, list):
        return []
    rows: list[dict[str, Any]] = []
    for insertion in insertions:
        if not isinstance(insertion, dict):
            continue
        coefficient = str(insertion.get("validation_simplified_target_coefficient_input_form", ""))
        if not coefficient.startswith("-1/4*"):
            continue
        replacement = str(insertion.get("replacement_input_form", ""))
        rows.append(
            {
                "index": insertion.get("index"),
                "xterm_signatures": _matchete_xterm_signatures(replacement),
                "target_coefficient_input_form": coefficient,
            }
        )
    return rows


def main() -> int:
    args = _parse_args()
    fixture = load_validation_fixture(args.fixture)
    reference = load_validation_fixture(args.reference_fixture).matching_result("matchete_previous")
    matchete_eom_debug = _load_json(args.matchete_eom_debug)
    matchete_trace_debug = _load_json(args.matchete_trace_debug)
    theory = fixture.theory()
    lagrangian = fixture.expression("lagrangian")
    condition_name, target = next(
        (name, target)
        for name, target in registered_wilson_matching_condition_targets(theory, basis="SMEFT").items()
        if "external_cHD" in name
    )
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=4)
    plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar-lScalar-lVector-lScalar",),
        max_total_order=args.max_total_order,
        max_slot_order=args.max_slot_order,
        index_prefix=args.index_prefix,
    )
    heavy_solutions = matching_module.solve_heavy_scalar_eoms(theory, lagrangian, eft_order=6)
    requirements = matching_module._term_atom_requirements_for_targets(
        theory,
        {condition_name: target},
        heavy_scalar_solutions=heavy_solutions,
    )
    plan_entries_by_label = {entry.label: entry for entry in plan.entries}
    grouped_terms: dict[str, tuple[Any, ...]] = {}
    evaluated_by_entry: dict[str, tuple[Expression, ...]] = {}
    terms_by_path_lists: dict[str, list[Any]] = {}
    for order in sorted({entry.total_order for entry in plan.entries}):
        order_entries = tuple(entry for entry in plan.entries if entry.total_order == order)
        order_plan = matching_module.WilsonLineExpansionPlan(
            theory=plan.theory,
            entries=order_entries,
            trace_names=plan.trace_names,
            max_total_order=plan.max_total_order,
            max_slot_order=plan.max_slot_order,
        )
        print(f"Generating Wilson-line terms for total_order={order}", flush=True)
        order_grouped = setup.interaction_wilson_line_expansion_terms_by_trace(
            order_plan,
            act_open_derivatives=True,
            emit_covariant_derivative_commutators=False,
            emit_covariant_derivative_commutator_passes=1,
            covariant_derivative_commutator_mode="all_distinct",
            expand_covariant_derivative_commutators=False,
            max_wilson_derivative_order=4,
            simplify_pychete_color_algebra=True,
            term_atom_requirements=requirements,
        )
        grouped_terms.update(order_grouped)
        for entry_terms in order_grouped.values():
            for term in entry_terms:
                terms_by_path_lists.setdefault(f"path{term.path_index}", []).append(term)
        print(
            "Evaluating Wilson-line terms for total_order="
            f"{order} terms={sum(len(terms) for terms in order_grouped.values())}",
            flush=True,
        )
        evaluated_by_entry.update(
            matching_module._wilson_line_internal_evaluated_terms_by_entry_from_terms(
                theory,
                order_grouped,
                tensor_reduce=True,
                tensor_reduce_engine=None,
                tensor_reduce_before_wilson_expand=True,
                max_wilson_derivative_order=4,
                emit_covariant_derivative_commutators=False,
                emit_covariant_derivative_commutator_passes=1,
                covariant_derivative_commutator_mode="all_distinct",
                expand_covariant_derivative_commutators=False,
                simplify_pychete_color_algebra=True,
                expose_scalar_derivative_commutator_bilinears=False,
                epsilon=None,
                mu_r_squared=None,
            )
        )
    terms_by_path = {
        path: tuple(terms)
        for path, terms in terms_by_path_lists.items()
    }
    normalization = one_loop_normalization_factor(
        OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
        hbar=theory.external_handle("hbar")(),
    )
    stage_names = [
        "selected_normalized_evaluated",
        "selected_normalized_pole_part",
        "selected_normalized_finite_part",
    ]
    heavy_replacements = matching_module.heavy_scalar_solution_replacements(
        heavy_solutions,
        fresh_dummy_indices=True,
    )
    if args.include_green_heavy_stages:
        stage_names.extend([
            "selected_post_green",
            "selected_post_heavy",
            "selected_post_heavy_green",
        ])
    stage_expression_parts_by_order: dict[str, dict[int, list[Expression]]] = {
        stage_name: {} for stage_name in stage_names
    }
    pole_finite_expression_by_entry: dict[str, Expression] = {}
    for entry_label, evaluated_terms in evaluated_by_entry.items():
        if not evaluated_terms:
            continue
        normalized = (normalization * sum(evaluated_terms, Expression.num(0))).expand()
        pole_finite_expression_by_entry[entry_label] = (
            vakint_backend.pole_part(normalized) + vakint_backend.finite_part(normalized)
        ).expand()
        entry_stage_expressions = {
            "selected_normalized_evaluated": normalized,
            "selected_normalized_pole_part": vakint_backend.pole_part(normalized),
            "selected_normalized_finite_part": vakint_backend.finite_part(normalized),
        }
        if args.include_green_heavy_stages:
            post_green = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
                theory,
                normalized,
            )
            post_heavy = post_green.replace_multiple(
                heavy_replacements,
                repeat=False,
            ).expand()
            post_heavy_green = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
                theory,
                post_heavy,
            )
            entry_stage_expressions.update({
                "selected_post_green": post_green,
                "selected_post_heavy": post_heavy,
                "selected_post_heavy_green": post_heavy_green,
            })
        order = plan_entries_by_label[entry_label].total_order
        for stage_name, expr in entry_stage_expressions.items():
            stage_expression_parts_by_order[stage_name].setdefault(order, []).append(expr)
    projected_by_stage_and_order = _projected_stage_order_map(
        theory,
        condition_name,
        target,
        stage_expression_parts_by_order,
    )
    reference_off_shell = reference.project_matching_conditions(
        {condition_name: target},
        source="off_shell_eft_lagrangian",
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )[condition_name]
    matchete_quarter_insertions = _matchete_quarter_insertions(matchete_trace_debug)
    eom_probe_by_entry, eom_probe_summary = _eom_exposure_probe(
        theory,
        lagrangian,
        pole_finite_expression_by_entry,
        condition_name=condition_name,
        target=target,
        vector_field="B",
        scalar_field="H",
        heavy_replacements=heavy_replacements,
    )
    source_trace_vector_eom_probe = _source_trace_vector_eom_probe(
        theory,
        lagrangian,
        setup,
        requirements,
        normalization,
        condition_name=condition_name,
        target=target,
        vector_field="B",
        trace_name="hScalar-lScalar",
        max_total_order=4,
        max_slot_order=4,
        index_prefix=f"{args.index_prefix}_source_trace_eom",
    )
    payload = {
        "schema_version": 1,
        "generator": "scripts/debug_pychete_singlet_eom_boundary.py",
        "model": fixture.name,
        "target": "cHD",
        "condition_name": condition_name,
        "matchete_debug_files": {
            "eom": str(args.matchete_eom_debug),
            "trace": str(args.matchete_trace_debug),
        },
        "matchete_internal_dim6_dev3_delta": _matchete_internal_dim6_dev3_delta(matchete_eom_debug),
        "controls": {
            "trace_names": ["hScalar-lScalar-lVector-lScalar"],
            "max_trace_order": 4,
            "max_total_order": args.max_total_order,
            "max_slot_order": args.max_slot_order,
            "act_open_derivatives": True,
            "tensor_reduce_before_wilson_expand": True,
            "simplify_pychete_color_algebra": True,
            "normalization": "matchete_evaluated_hbar",
            "include_green_heavy_stages": args.include_green_heavy_stages,
        },
        "term_counts_by_entry": {entry: len(terms) for entry, terms in grouped_terms.items()},
        "term_counts_by_total_order": {
            str(order): sum(
                len(grouped_terms[entry.label])
                for entry in plan.entries
                if entry.total_order == order
            )
            for order in sorted({entry.total_order for entry in plan.entries})
        },
        "term_counts_by_path": {path: len(terms) for path, terms in sorted(terms_by_path.items())},
        "evaluated_term_counts_by_entry": {
            entry: len(evaluated_by_entry.get(entry, ())) for entry in grouped_terms
        },
        "evaluated_term_counts_by_total_order": {
            str(order): sum(
                len(evaluated_by_entry.get(entry.label, ()))
                for entry in plan.entries
                if entry.total_order == order
            )
            for order in sorted({entry.total_order for entry in plan.entries})
        },
        "evaluated_term_counts_by_path": {},
        "eom_exposure_probe_by_entry": eom_probe_by_entry,
        "eom_exposure_probe_summary": eom_probe_summary,
        "source_trace_vector_eom_probe": source_trace_vector_eom_probe,
        "matchete_quarter_insertions": matchete_quarter_insertions,
        "matchete_quarter_insertion_count": len(matchete_quarter_insertions),
        "pychete_nonzero_path_count": len(terms_by_path),
        "heavy_scalar_solution_count": len(heavy_solutions),
        "selected_stage_projections": _projection_strings_from_order_map(projected_by_stage_and_order),
        "selected_stage_projections_by_total_order": _projection_order_strings_from_order_map(
            projected_by_stage_and_order
        ),
        "reference_projections": {
            "matchete_trace_off_shell_input_form": matchete_trace_debug[
                "previous_validation_trace_target_coefficient_input_form"
            ],
            "matchete_eom_off_shell_input_form": matchete_eom_debug[
                "off_shell_coefficient_input_form"
            ],
            "matchete_eom_on_shell_input_form": matchete_eom_debug[
                "on_shell_coefficient_input_form"
            ],
            "pychete_reference_off_shell": canonical_string(reference_off_shell),
            "pychete_reference_on_shell": canonical_string(reference.matching_conditions[condition_name]),
        },
        "first_differing_boundary": (
            "selected_wilson_line_trace_generation_now_matches_the_Matchete_"
            "propagation_order_0_1_2_selected_trace_checkpoint. Projections are "
            "computed entry/order-locally before summing to avoid the known "
            "large aggregate projection cost. The current narrowed mismatch is "
            "the representative-conversion boundary before field redefinition: "
            "Matchete's InternalSimplify exposes EOM-proportional structures "
            "that feed PerformSystematicFieldRedefs. The refreshed Matchete "
            "replay locates the first nonzero cHD delta at dim6/dev3 vector "
            "EOM selection over B/W. A follow-up source-trace probe shows that "
            "the relevant two-Higgs B-vector EOM source is generated by the "
            "hScalar-lScalar order-four Wilson-line trace, not by the "
            "hScalar-lScalar-lVector-lScalar four-slot trace alone. pychete "
            "now exposes that bounded hScalar-lScalar B-vector EOM source and "
            "gets a nonzero cHD projection from its Abelian vector field "
            "redefinition, but the coefficient is still short of Matchete's "
            "after_shift_dim6_dev3 delta. The next boundary is therefore the "
            "Matchete InternalSimplify scalar Green/EoMSplitter coefficient "
            "parity for the hScalar-lScalar two-Higgs source, plus the later "
            "non-Abelian W-vector EOM treatment if needed."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
