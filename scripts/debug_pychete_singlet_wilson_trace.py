#!/usr/bin/env python
"""Dump pychete intermediates for the Singlet hScalar-lScalar frontier.

This development-only helper is the pychete-side counterpart of
``helper_mathematica_scripts/debug_singlet_wilson_trace.wls``.  Runtime
pychete code and pytest must not depend on this script.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from symbolica import Expression

import pychete.matching as matching_module
from pychete.backends import vakint, vacuum_integrals
from pychete.bases.smeft_warsaw import smeft_warsaw_operator
from pychete.expr import (
    bar_field_pattern,
    field_pattern,
    field_derivatives,
    field_strength_pattern,
    is_bar_field,
    bar_field_inner,
    terms,
    wilson_term_pattern,
)
from pychete.matching_options import OneLoopNormalization, one_loop_normalization_factor
from pychete.matching_results import MatchingResult, registered_wilson_matching_condition_targets
from pychete.symbols import canonical_string, s
from pychete.validation_fixtures import load_validation_fixture
from pychete.wilson_lines import contract_wilson_term_derivative_metrics, expand_wilson_terms


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("assets/validation/pychete/debug/singlet_hScalar_lScalar_cHW.pychete.debug.json"),
    )
    parser.add_argument("--trace-name", default="hScalar-lScalar")
    parser.add_argument("--target", default="cHW")
    parser.add_argument("--eft-order", type=int, default=6)
    parser.add_argument("--max-trace-order", type=int, default=2)
    parser.add_argument("--max-total-order", type=int, default=4)
    parser.add_argument("--max-slot-order", type=int, default=4)
    parser.add_argument("--index-prefix", default="diag")
    parser.add_argument("--entry-contains", default="")
    parser.add_argument("--sample-chars", type=int, default=1200)
    parser.add_argument("--include-zero-terms", action="store_true")
    parser.add_argument(
        "--substitute-heavy-scalar-solutions",
        action="store_true",
        help="Apply the public one-loop heavy-scalar EOM substitution stage in aggregate summaries.",
    )
    parser.add_argument(
        "--heavy-scalar-solution-expand",
        action="store_true",
        help="Expand while applying heavy-scalar solution replacement rules.",
    )
    parser.add_argument(
        "--no-filter-by-target",
        action="store_true",
        help="Keep all selected Wilson-line entries instead of applying the conservative target atom filter.",
    )
    parser.add_argument(
        "--skip-runtime-internal-evaluated",
        action="store_true",
        help="Skip the aggregate runtime internal-evaluation summary when only source/stage diagnostics are needed.",
    )
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Stop after Wilson-line source generation and numerator summaries.",
    )
    return parser.parse_args()


def _short(expr: Expression, max_chars: int) -> str:
    rendered = canonical_string(expr)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[:max_chars] + "..."


def _full(expr: Expression) -> str:
    return canonical_string(expr)


def _match_count(expr: Expression, pattern: Expression) -> int:
    return sum(1 for _ in expr.match(pattern))


def _derivative_word(derivatives: tuple[Expression, ...]) -> str:
    if not derivatives:
        return "0"
    labels: dict[str, str] = {}
    out: list[str] = []
    for derivative in derivatives:
        key = canonical_string(derivative)
        if key not in labels:
            labels[key] = chr(ord("a") + len(labels))
        out.append(labels[key])
    return "".join(out)


def _remove_barred_inner_fields(fields: list[Expression], barred: tuple[Expression, ...]) -> list[Expression]:
    remaining = list(fields)
    for barred_atom in barred:
        inner_key = canonical_string(bar_field_inner(barred_atom))
        for index, field in enumerate(remaining):
            if canonical_string(field) == inner_key:
                del remaining[index]
                break
    return remaining


def _field_derivative_signature(term: Expression, label: Expression) -> str:
    bar_pattern = bar_field_pattern(label)
    plain_pattern = field_pattern(label)
    barred = tuple(bar_pattern.replace_wildcards(match) for match in term.match(bar_pattern))
    fields = [plain_pattern.replace_wildcards(match) for match in term.match(plain_pattern)]
    unbarred = _remove_barred_inner_fields(fields, barred)
    bar_words = tuple(_derivative_word(field_derivatives(bar_field_inner(atom))) for atom in barred if is_bar_field(atom))
    field_words = tuple(_derivative_word(field_derivatives(atom)) for atom in unbarred)
    return (
        "bar="
        + (",".join(bar_words) if bar_words else "none")
        + ";field="
        + (",".join(field_words) if field_words else "none")
    )


def _field_derivative_word_histogram(expr: Expression, label: Expression) -> list[dict[str, Any]]:
    expanded = expr.expand()
    if bool(expanded == Expression.num(0)):
        return []
    counts = Counter(_field_derivative_signature(term, label) for term in terms(expanded))
    return [
        {"signature": signature, "count": count}
        for signature, count in sorted(counts.items(), key=lambda item: item[0])
    ]


def _field_derivative_signature_samples(
    expr: Expression,
    label: Expression,
    *,
    sample_chars: int,
) -> list[dict[str, Any]]:
    expanded = expr.expand()
    if bool(expanded == Expression.num(0)):
        return []
    samples: dict[str, str] = {}
    for term in terms(expanded):
        signature = _field_derivative_signature(term, label)
        if signature not in samples:
            samples[signature] = _short(term, sample_chars)
    return [
        {"signature": signature, "sample_input_form": sample}
        for signature, sample in sorted(samples.items(), key=lambda item: item[0])
    ]


def _expr_summary(name: str, expr: Expression, *, sample_chars: int) -> dict[str, Any]:
    expanded = expr.expand()
    try:
        byte_size = expr.get_byte_size()
    except AttributeError:
        byte_size = None
    return {
        "name": name,
        "node_count": len(expr),
        "byte_size": byte_size,
        "term_count": len(terms(expanded)) if bool(expanded != Expression.num(0)) else 0,
        "field_atoms": _match_count(expr, field_pattern()),
        "bar_field_atoms": _match_count(expr, bar_field_pattern()),
        "field_strength_atoms": _match_count(expr, field_strength_pattern()),
        "wilson_terms": _match_count(expr, wilson_term_pattern()),
        "loop_momenta": _match_count(expr, s.LoopMomentum(s.LoopMomentumIndexWildcard)),
        "propagator_denominators": _match_count(
            expr,
            s.PropagatorDenominator(s.PowBaseWildcard, s.PowExponentWildcard),
        ),
        "sample_input_form": _short(expr, sample_chars),
    }


def _stage_snapshot(name: str, expr: Expression, *, h_label: Expression, sample_chars: int) -> dict[str, Any]:
    return {
        "summary": _expr_summary(name, expr, sample_chars=sample_chars),
        "h_derivative_word_histogram": _field_derivative_word_histogram(expr, h_label),
        "h_derivative_signature_samples": _field_derivative_signature_samples(
            expr,
            h_label,
            sample_chars=sample_chars,
        ),
    }


def _pipeline_summary(expr: Expression, *, h_label: Expression, sample_chars: int, name: str) -> dict[str, Any]:
    return {
        "summary": _expr_summary(name, expr, sample_chars=sample_chars),
        "h_derivative_word_histogram": _field_derivative_word_histogram(expr, h_label),
        "h_derivative_signature_samples": _field_derivative_signature_samples(
            expr,
            h_label,
            sample_chars=sample_chars,
        ),
    }


def _empty_pipeline_aggregate() -> dict[str, Expression]:
    return {}


def _add_pipeline_aggregate(
    aggregate: dict[str, Expression],
    stage_expressions: dict[str, Expression],
) -> None:
    for name, expr in stage_expressions.items():
        aggregate[name] = (aggregate.get(name, Expression.num(0)) + expr).expand()


def _pipeline_aggregate_summaries(
    aggregate: dict[str, Expression],
    *,
    h_label: Expression,
    sample_chars: int,
) -> dict[str, dict[str, Any]]:
    return {
        name: _pipeline_summary(expr, h_label=h_label, sample_chars=sample_chars, name=name)
        for name, expr in aggregate.items()
    }


def _prefinal_wilson_line_terms_by_trace(
    setup: Any,
    plan: Any,
    *,
    act_open_derivatives: bool,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    covariant_derivative_commutator_mode: str,
    expand_covariant_derivative_commutators: bool,
    max_wilson_derivative_order: int,
    simplify_pychete_color_algebra: bool,
    term_atom_requirements: Any,
) -> dict[str, tuple[matching_module.WilsonLineTraceExpansionTerm, ...]]:
    paths_by_trace = setup.interaction_wilson_line_trace_paths_by_trace(trace_names=plan.trace_names)
    grouped: dict[str, tuple[matching_module.WilsonLineTraceExpansionTerm, ...]] = {}
    for entry in plan.entries:
        entry_terms: list[matching_module.WilsonLineTraceExpansionTerm] = []
        for path in paths_by_trace[entry.trace_name]:
            if not matching_module._wilson_line_entry_can_satisfy_projection_requirements(
                path,
                entry,
                term_atom_requirements,
            ):
                continue
            filtered_path = matching_module._wilson_line_path_with_projection_filtered_entries(
                path,
                term_atom_requirements,
            )
            entry_terms.extend(
                filtered_path.propagator_expansion_terms(
                    entry.expansion_indices,
                    act_open_derivatives=act_open_derivatives,
                    emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                    emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                    covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                    expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                    max_wilson_derivative_order=max_wilson_derivative_order,
                    simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                )
            )
        grouped[entry.label] = tuple(entry_terms)
    return grouped


def _grouped_entry_orders(
    grouped: dict[str, tuple[matching_module.WilsonLineTraceExpansionTerm, ...]],
    plan_entries_by_label: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        label: {
            "total_order": plan_entries_by_label[label].total_order,
            "slot_orders": list(plan_entries_by_label[label].slot_orders),
        }
        for label, entry_terms in grouped.items()
        if entry_terms
    }


def _term_counts_by_total_order(
    grouped: dict[str, tuple[matching_module.WilsonLineTraceExpansionTerm, ...]],
    plan_entries_by_label: dict[str, Any],
) -> dict[str, int]:
    counts: Counter[int] = Counter()
    for label, entry_terms in grouped.items():
        counts[plan_entries_by_label[label].total_order] += len(entry_terms)
    return {str(order): count for order, count in sorted(counts.items()) if count}


def _aggregate_numerator_summaries_by_total_order(
    grouped: dict[str, tuple[matching_module.WilsonLineTraceExpansionTerm, ...]],
    plan_entries_by_label: dict[str, Any],
    *,
    h_label: Expression,
    sample_chars: int,
) -> dict[str, dict[str, dict[str, Any]]]:
    aggregates: dict[int, dict[str, Expression]] = {}
    for label, entry_terms in grouped.items():
        order = plan_entries_by_label[label].total_order
        order_aggregate = aggregates.setdefault(
            order,
            {
                "pre_wilson_numerator": Expression.num(0),
                "wilson_expanded_numerator": Expression.num(0),
            },
        )
        for term in entry_terms:
            if term.pre_wilson_numerator is not None:
                order_aggregate["pre_wilson_numerator"] = (
                    order_aggregate["pre_wilson_numerator"] + term.pre_wilson_numerator
                ).expand()
            order_aggregate["wilson_expanded_numerator"] = (
                order_aggregate["wilson_expanded_numerator"] + term.numerator
            ).expand()
    return {
        str(order): {
            name: _pipeline_summary(expr, h_label=h_label, sample_chars=sample_chars, name=f"order{order}.{name}")
            for name, expr in order_aggregate.items()
        }
        for order, order_aggregate in sorted(aggregates.items())
    }


def _coefficient_slice_summary(
    expr: Expression,
    coefficient: Expression,
    *,
    h_label: Expression,
    name: str,
    sample_chars: int,
) -> dict[str, Any]:
    coefficient_slice = expr.coefficient(coefficient).expand()
    return {
        "coefficient": _full(coefficient),
        "summary": _expr_summary(name, coefficient_slice, sample_chars=sample_chars),
        "h_derivative_word_histogram": _field_derivative_word_histogram(coefficient_slice, h_label),
    }


def _project_target(
    theory: Any,
    target_name: str,
    target: Expression,
    expr: Expression,
) -> Expression:
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=expr,
    )
    return result.project_matching_conditions(
        {target_name: target},
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
        drop_zero=False,
    )[target_name].expand()


def _registered_or_warsaw_target(theory: Any, target_name: str) -> Expression:
    if target_name in theory.externals:
        handle = theory.external_handle(target_name)
        condition = s.Coupling(
            handle.label,
            s.List(*handle.definition.index_exprs),
            Expression.num(handle.definition.order),
        )
        if canonical_string(condition) in registered_wilson_matching_condition_targets(theory, basis="SMEFT"):
            return condition
    target = smeft_warsaw_operator(theory, target_name)
    if target is None:
        raise ValueError(f"unknown SMEFT Warsaw target {target_name!r}")
    return target


def _apply_heavy_scalar_replacements(
    theory: Any,
    expr: Expression,
    replacement_rules: tuple[Any, ...],
    *,
    expand: bool,
) -> Expression:
    if not replacement_rules:
        return expr
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=expr,
    )
    return result.with_on_shell_reduction(replacement_rules, expand=expand).on_shell_eft_lagrangian


def _projection_map(
    theory: Any,
    target_name: str,
    target: Expression,
    expressions: dict[str, Expression],
) -> dict[str, str]:
    return {
        stage_name: _full(_project_target(theory, target_name, target, expr))
        for stage_name, expr in expressions.items()
    }


def _summary_map(expressions: dict[str, Expression], *, sample_chars: int) -> dict[str, dict[str, Any]]:
    return {
        stage_name: _expr_summary(stage_name, expr, sample_chars=sample_chars)
        for stage_name, expr in expressions.items()
    }


def _h_derivative_histogram_map(
    expressions: dict[str, Expression],
    h_label: Expression,
) -> dict[str, list[dict[str, Any]]]:
    return {
        stage_name: _field_derivative_word_histogram(expr, h_label)
        for stage_name, expr in expressions.items()
    }


def _transform_map_with_errors(
    expressions: dict[str, Expression],
    transform: Any,
) -> tuple[dict[str, Expression], dict[str, str]]:
    transformed: dict[str, Expression] = {}
    errors: dict[str, str] = {}
    for stage_name, expr in expressions.items():
        try:
            transformed[stage_name] = transform(expr)
        except Exception as exc:  # noqa: BLE001 - keep development dumps usable past frontier failures.
            errors[stage_name] = f"{type(exc).__name__}: {exc}"
    return transformed, errors


def _sum_expressions(expressions: tuple[Expression, ...] | list[Expression]) -> Expression:
    total = Expression.num(0)
    for expr in expressions:
        total = (total + expr).expand()
    return total


def _runtime_internal_evaluated_summary(
    theory: Any,
    target_name: str,
    target: Expression,
    normalization_factor: Expression,
    grouped: dict[str, tuple[matching_module.WilsonLineTraceExpansionTerm, ...]],
    plan_entries_by_label: dict[str, Any],
    *,
    h_label: Expression,
    coefficient_targets: dict[str, Expression],
    sample_chars: int,
) -> dict[str, Any]:
    evaluated_by_entry = matching_module._wilson_line_internal_evaluated_terms_by_entry_from_terms(
        theory,
        grouped,
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
    finite_by_entry = {
        entry_label: tuple(vakint.finite_part(term) for term in entry_terms)
        for entry_label, entry_terms in evaluated_by_entry.items()
    }
    normalized_finite_by_entry = {
        entry_label: (normalization_factor * _sum_expressions(tuple(entry_terms))).expand()
        for entry_label, entry_terms in finite_by_entry.items()
    }
    total_finite_before_scalar_bilinears = _sum_expressions(tuple(normalized_finite_by_entry.values()))
    total_finite = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
        theory,
        total_finite_before_scalar_bilinears,
    )
    normalized_finite_by_order: dict[int, Expression] = {}
    for entry_label, expr in normalized_finite_by_entry.items():
        order = plan_entries_by_label[entry_label].total_order
        normalized_finite_by_order[order] = (
            normalized_finite_by_order.get(order, Expression.num(0)) + expr
        ).expand()
    return {
        "controls": {
            "act_open_derivatives": True,
            "emit_covariant_derivative_commutators": False,
            "expand_covariant_derivative_commutators": False,
            "covariant_derivative_commutator_mode": "all_distinct",
            "max_wilson_derivative_order": 4,
            "tensor_reduce": True,
            "tensor_reduce_before_wilson_expand": True,
            "simplify_pychete_color_algebra": True,
            "pre_integral_expose_scalar_derivative_commutator_bilinears": False,
            "post_finite_expose_scalar_derivative_commutator_bilinears": True,
        },
        "term_counts_by_entry": {
            entry_label: len(entry_terms) for entry_label, entry_terms in evaluated_by_entry.items()
        },
        "term_counts_by_total_order": {
            str(order): sum(
                len(evaluated_by_entry[entry_label])
                for entry_label in evaluated_by_entry
                if plan_entries_by_label[entry_label].total_order == order
            )
            for order in sorted({plan_entries_by_label[label].total_order for label in evaluated_by_entry})
        },
        "finite_projection": _full(_project_target(theory, target_name, target, total_finite)),
        "finite_projection_sample_input_form": _short(
            _project_target(theory, target_name, target, total_finite),
            sample_chars,
        ),
        "finite_summary": _expr_summary(
            "runtime_internal_evaluated.finite",
            total_finite,
            sample_chars=sample_chars,
        ),
        "finite_before_scalar_bilinears_summary": _expr_summary(
            "runtime_internal_evaluated.finite_before_scalar_bilinears",
            total_finite_before_scalar_bilinears,
            sample_chars=sample_chars,
        ),
        "finite_h_derivative_word_histogram": _field_derivative_word_histogram(total_finite, h_label),
        "finite_coefficient_slices": {
            coefficient_name: _coefficient_slice_summary(
                total_finite,
                coefficient,
                h_label=h_label,
                name=f"runtime_internal_evaluated.finite.coefficient.{coefficient_name}",
                sample_chars=sample_chars,
            )
            for coefficient_name, coefficient in coefficient_targets.items()
        },
        "finite_projection_by_entry": {
            entry_label: _full(_project_target(theory, target_name, target, expr))
            for entry_label, expr in sorted(normalized_finite_by_entry.items())
        },
        "finite_projection_by_total_order": {
            str(order): _full(_project_target(theory, target_name, target, expr))
            for order, expr in sorted(normalized_finite_by_order.items())
        },
        "finite_summary_by_entry": {
            entry_label: _expr_summary(
                f"runtime_internal_evaluated.finite.{entry_label}",
                expr,
                sample_chars=sample_chars,
            )
            for entry_label, expr in sorted(normalized_finite_by_entry.items())
        },
        "finite_summary_by_total_order": {
            str(order): _expr_summary(
                f"runtime_internal_evaluated.finite.order{order}",
                expr,
                sample_chars=sample_chars,
            )
            for order, expr in sorted(normalized_finite_by_order.items())
        },
    }


def _processed_stage_with_debug(
    theory: Any,
    raw: Expression,
    *,
    use_pre_wilson: bool,
    h_label: Expression,
    sample_chars: int,
) -> tuple[Expression, list[dict[str, Any]]]:
    stage_expressions = _pipeline_stage_expressions(theory, raw, use_pre_wilson=use_pre_wilson)
    processed = stage_expressions[
        ("pre_wilson" if use_pre_wilson else "post_wilson") + ".postprocessed_with_scalar_bilinears"
    ]
    snapshots = [
        _stage_snapshot(name, expr, h_label=h_label, sample_chars=sample_chars)
        for name, expr in stage_expressions.items()
    ]
    return processed, snapshots


def _pipeline_stage_expressions(
    theory: Any,
    raw: Expression,
    *,
    use_pre_wilson: bool,
) -> dict[str, Expression]:
    stage_prefix = "pre_wilson" if use_pre_wilson else "post_wilson"
    stage_expressions: dict[str, Expression] = {f"{stage_prefix}.raw_vakint_integral": raw}
    reduced = vakint.tensor_reduce(raw)
    reduced = vakint.decode_pychete_namespace(theory, reduced)
    stage_expressions[f"{stage_prefix}.tensor_reduced_decoded"] = reduced
    if use_pre_wilson:
        restored = matching_module._restore_theory_owned_generated_lorentz_indices(theory, reduced)
        contracted = contract_wilson_term_derivative_metrics(
            restored,
            max_derivative_order=4,
        )
        stage_expressions[f"{stage_prefix}.formal_metric_contracted"] = contracted
        lowered = expand_wilson_terms(
            theory,
            contracted,
            max_derivative_order=4,
        )
        stage_expressions[f"{stage_prefix}.wilson_terms_expanded"] = lowered
    else:
        lowered = reduced

    postprocessed_without_scalar_bilinears = matching_module._postprocess_wilson_line_tensor_reduced_expression(
        theory,
        lowered,
        emit_covariant_derivative_commutators=True,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=True,
        simplify_pychete_color_algebra=True,
        expose_scalar_derivative_commutator_bilinears_option=False,
    )
    stage_expressions[f"{stage_prefix}.postprocessed_without_scalar_bilinears"] = (
        postprocessed_without_scalar_bilinears
    )
    processed = matching_module._postprocess_wilson_line_tensor_reduced_expression(
        theory,
        lowered,
        emit_covariant_derivative_commutators=True,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=True,
        simplify_pychete_color_algebra=True,
        expose_scalar_derivative_commutator_bilinears_option=True,
    )
    stage_expressions[f"{stage_prefix}.postprocessed_with_scalar_bilinears"] = processed
    return stage_expressions


def _processed_stage(
    theory: Any,
    raw: Expression,
    *,
    use_pre_wilson: bool,
) -> Expression:
    processed, _snapshots = _processed_stage_with_debug(
        theory,
        raw,
        use_pre_wilson=use_pre_wilson,
        h_label=theory.field_handle("H").label,
        sample_chars=900,
    )
    return processed


def _term_row(
    theory: Any,
    target_name: str,
    target: Expression,
    normalization_factor: Expression,
    entry_label: str,
    term_index: int,
    term: matching_module.WilsonLineTraceExpansionTerm,
    *,
    h_label: Expression,
    coefficient_targets: dict[str, Expression],
    sample_chars: int,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "entry_label": entry_label,
        "term_index": term_index,
        "trace_name": term.trace_name,
        "path_index": term.path_index,
        "propagator_powers": list(term.propagator_powers),
        "expansion_slot_lengths": [len(slot) for slot in term.expansion_indices],
        "mass_squareds": [_short(mass, sample_chars) for mass in term.mass_squareds],
        "numerator": _expr_summary("numerator", term.numerator, sample_chars=sample_chars),
        "numerator_h_derivative_word_histogram": _field_derivative_word_histogram(term.numerator, h_label),
        "pre_wilson_numerator": (
            _expr_summary("pre_wilson_numerator", term.pre_wilson_numerator, sample_chars=sample_chars)
            if term.pre_wilson_numerator is not None
            else None
        ),
        "pre_wilson_numerator_h_derivative_word_histogram": (
            _field_derivative_word_histogram(term.pre_wilson_numerator, h_label)
            if term.pre_wilson_numerator is not None
            else None
        ),
    }

    for stage_name, use_pre_wilson in (
        ("post_wilson_tensor_reduced", False),
        ("pre_wilson_tensor_reduced", True),
    ):
        if use_pre_wilson and term.pre_wilson_numerator is None:
            continue
        raw = term.vakint_integral_expression(use_pre_wilson_numerator=use_pre_wilson)
        processed, pipeline_snapshots = _processed_stage_with_debug(
            theory,
            raw,
            use_pre_wilson=use_pre_wilson,
            h_label=h_label,
            sample_chars=sample_chars,
        )
        evaluated = vacuum_integrals.evaluate_one_loop_vakint_expression(
            processed,
            combine_terms=False,
        )
        finite = vakint.finite_part(evaluated)
        normalized = (normalization_factor * evaluated).expand()
        normalized_finite = (normalization_factor * finite).expand()
        projection = _project_target(theory, target_name, target, normalized)
        finite_projection = _project_target(theory, target_name, target, normalized_finite)
        row[stage_name] = {
            "raw_integral": _expr_summary(f"{stage_name}.raw_integral", raw, sample_chars=sample_chars),
            "pipeline_snapshots": pipeline_snapshots,
            "processed_integral": _expr_summary(
                f"{stage_name}.processed_integral",
                processed,
                sample_chars=sample_chars,
            ),
            "evaluated": _expr_summary(f"{stage_name}.evaluated", normalized, sample_chars=sample_chars),
            "finite_minimal_subtraction": _expr_summary(
                f"{stage_name}.finite_minimal_subtraction",
                normalized_finite,
                sample_chars=sample_chars,
            ),
            "finite_h_derivative_word_histogram": _field_derivative_word_histogram(
                normalized_finite,
                h_label,
            ),
            "finite_coefficient_slices": {
                coefficient_name: _coefficient_slice_summary(
                    normalized_finite,
                    coefficient,
                    h_label=h_label,
                    name=f"{stage_name}.finite.coefficient.{coefficient_name}",
                    sample_chars=sample_chars,
                )
                for coefficient_name, coefficient in coefficient_targets.items()
            },
            "target_projection": _full(projection),
            "target_projection_sample_input_form": _short(projection, sample_chars),
            "target_projection_is_zero": bool(projection.expand() == Expression.num(0)),
            "target_projection_finite": _full(finite_projection),
            "target_projection_finite_sample_input_form": _short(finite_projection, sample_chars),
            "target_projection_finite_is_zero": bool(finite_projection.expand() == Expression.num(0)),
        }
    return row


def main() -> int:
    args = _parse_args()
    fixture = load_validation_fixture(args.fixture)
    theory = fixture.theory()
    lagrangian = fixture.expression("lagrangian")
    target = _registered_or_warsaw_target(theory, args.target)
    hbar = theory.external_handle("hbar")() if "hbar" in theory.externals else s.HBar
    normalization_factor = one_loop_normalization_factor(OneLoopNormalization.MATCHETE_EVALUATED_HBAR, hbar=hbar)
    h_label = theory.field_handle("H").label
    heavy_scalar_solutions = (
        matching_module.solve_heavy_scalar_eoms(theory, lagrangian, eft_order=args.eft_order)
        if args.substitute_heavy_scalar_solutions
        else {}
    )
    heavy_scalar_replacement_rules = (
        matching_module.heavy_scalar_solution_replacements(heavy_scalar_solutions, fresh_dummy_indices=True)
        if heavy_scalar_solutions
        else ()
    )
    coefficient_targets: dict[str, Expression] = {}
    if "A" in theory.couplings:
        coefficient_targets["A2"] = theory.coupling_handle("A")() ** 2
    if "A" in theory.couplings and "gL" in theory.couplings:
        coefficient_targets["A2_gL2"] = theory.coupling_handle("A")() ** 2 * theory.coupling_handle("gL")() ** 2
    if "A" in theory.couplings and "gY" in theory.couplings:
        coefficient_targets["A2_gY2"] = theory.coupling_handle("A")() ** 2 * theory.coupling_handle("gY")() ** 2

    setup = theory.one_loop_setup(
        lagrangian,
        eft_order=args.eft_order,
        max_trace_order=args.max_trace_order,
    )
    plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=(args.trace_name,),
        max_total_order=args.max_total_order,
        max_slot_order=args.max_slot_order,
        index_prefix=args.index_prefix,
    )
    requirements = (
        None
        if args.no_filter_by_target
        else matching_module._term_atom_requirements_for_targets(
            theory,
            {args.target: target},
            heavy_scalar_solutions=heavy_scalar_solutions,
        )
    )
    preaction_prefilter_grouped = _prefinal_wilson_line_terms_by_trace(
        setup,
        plan,
        act_open_derivatives=False,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=False,
        max_wilson_derivative_order=4,
        simplify_pychete_color_algebra=False,
        term_atom_requirements=requirements,
    )
    prefinal_grouped = _prefinal_wilson_line_terms_by_trace(
        setup,
        plan,
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=True,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=True,
        max_wilson_derivative_order=4,
        simplify_pychete_color_algebra=True,
        term_atom_requirements=requirements,
    )
    grouped = {
        label: matching_module._filter_wilson_line_terms_by_projection_requirements(entry_terms, requirements)
        for label, entry_terms in prefinal_grouped.items()
    }
    runtime_grouped = setup.interaction_wilson_line_expansion_terms_by_trace(
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

    rows: list[dict[str, Any]] = []
    plan_entries_by_label = {entry.label: entry for entry in plan.entries}
    if args.source_only:
        payload = {
            "schema_version": 1,
            "generator": "debug_pychete_singlet_wilson_trace.py",
            "fixture": str(args.fixture),
            "model": fixture.name,
            "trace_name": args.trace_name,
            "target": args.target,
            "mode": "source_only",
            "plan_entry_count": len(plan.entries),
            "plan_entries": [
                {
                    "label": entry.label,
                    "trace_name": entry.trace_name,
                    "total_order": entry.total_order,
                    "slot_orders": list(entry.slot_orders),
                }
                for entry in plan.entries
            ],
            "filter_terms_by_matching_targets": requirements is not None,
            "preaction_prefilter_nonempty_grouped_entries": {
                label: len(entry_terms) for label, entry_terms in preaction_prefilter_grouped.items() if entry_terms
            },
            "preaction_prefilter_nonempty_grouped_entry_orders": _grouped_entry_orders(
                preaction_prefilter_grouped,
                plan_entries_by_label,
            ),
            "preaction_prefilter_term_counts_by_total_order": _term_counts_by_total_order(
                preaction_prefilter_grouped,
                plan_entries_by_label,
            ),
            "preaction_prefilter_numerator_summaries_by_total_order": (
                _aggregate_numerator_summaries_by_total_order(
                    preaction_prefilter_grouped,
                    plan_entries_by_label,
                    h_label=h_label,
                    sample_chars=args.sample_chars,
                )
            ),
            "prefinal_nonempty_grouped_entries": {
                label: len(entry_terms) for label, entry_terms in prefinal_grouped.items() if entry_terms
            },
            "prefinal_nonempty_grouped_entry_orders": _grouped_entry_orders(
                prefinal_grouped,
                plan_entries_by_label,
            ),
            "prefinal_term_counts_by_total_order": _term_counts_by_total_order(
                prefinal_grouped,
                plan_entries_by_label,
            ),
            "prefinal_numerator_summaries_by_total_order": _aggregate_numerator_summaries_by_total_order(
                prefinal_grouped,
                plan_entries_by_label,
                h_label=h_label,
                sample_chars=args.sample_chars,
            ),
            "postfinal_filter_dropped_term_count_by_entry": {
                label: len(prefinal_grouped[label]) - len(entry_terms)
                for label, entry_terms in grouped.items()
                if len(prefinal_grouped[label]) - len(entry_terms)
            },
            "runtime_internal_nonempty_grouped_entries": {
                label: len(entry_terms) for label, entry_terms in runtime_grouped.items() if entry_terms
            },
            "runtime_internal_nonempty_grouped_entry_orders": _grouped_entry_orders(
                runtime_grouped,
                plan_entries_by_label,
            ),
            "runtime_internal_term_counts_by_total_order": _term_counts_by_total_order(
                runtime_grouped,
                plan_entries_by_label,
            ),
            "nonempty_grouped_entries": {
                label: len(entry_terms) for label, entry_terms in grouped.items() if entry_terms
            },
            "nonempty_grouped_entry_orders": _grouped_entry_orders(grouped, plan_entries_by_label),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(f"Wrote {args.out}")
        return 0
    runtime_internal_evaluated = (
        {"skipped": True, "reason": "--skip-runtime-internal-evaluated"}
        if args.skip_runtime_internal_evaluated
        else _runtime_internal_evaluated_summary(
            theory,
            args.target,
            target,
            normalization_factor,
            runtime_grouped,
            plan_entries_by_label,
            h_label=h_label,
            coefficient_targets=coefficient_targets,
            sample_chars=args.sample_chars,
        )
    )
    totals = {
        "post_wilson_tensor_reduced_unrenormalized": Expression.num(0),
        "post_wilson_tensor_reduced_finite": Expression.num(0),
        "pre_wilson_tensor_reduced_unrenormalized": Expression.num(0),
        "pre_wilson_tensor_reduced_finite": Expression.num(0),
    }
    totals_by_entry: dict[str, dict[str, Expression]] = {}
    totals_by_order: dict[int, dict[str, Expression]] = {}
    pipeline_by_entry: dict[str, dict[str, dict[str, Expression]]] = {}
    pipeline_by_order: dict[int, dict[str, dict[str, Expression]]] = {}
    for entry_label, entry_terms in grouped.items():
        if args.entry_contains and args.entry_contains not in entry_label:
            continue
        entry = plan_entries_by_label[entry_label]
        totals_by_entry[entry_label] = {stage_name: Expression.num(0) for stage_name in totals}
        pipeline_by_entry[entry_label] = {
            "post_wilson_tensor_reduced": _empty_pipeline_aggregate(),
            "pre_wilson_tensor_reduced": _empty_pipeline_aggregate(),
        }
        order_totals = totals_by_order.setdefault(
            entry.total_order,
            {stage_name: Expression.num(0) for stage_name in totals},
        )
        order_pipelines = pipeline_by_order.setdefault(
            entry.total_order,
            {
                "post_wilson_tensor_reduced": _empty_pipeline_aggregate(),
                "pre_wilson_tensor_reduced": _empty_pipeline_aggregate(),
            },
        )
        for term_index, term in enumerate(entry_terms):
            row = _term_row(
                theory,
                args.target,
                target,
                normalization_factor,
                entry_label,
                term_index,
                term,
                h_label=h_label,
                coefficient_targets=coefficient_targets,
                sample_chars=args.sample_chars,
            )
            if (
                args.include_zero_terms
                or args.substitute_heavy_scalar_solutions
                or not row["post_wilson_tensor_reduced"]["target_projection_is_zero"]
                or not row["pre_wilson_tensor_reduced"]["target_projection_is_zero"]
            ):
                rows.append(row)
            for stage_name, use_pre_wilson in (
                ("post_wilson_tensor_reduced", False),
                ("pre_wilson_tensor_reduced", True),
            ):
                if use_pre_wilson and term.pre_wilson_numerator is None:
                    continue
                raw = term.vakint_integral_expression(use_pre_wilson_numerator=use_pre_wilson)
                pipeline_expressions = _pipeline_stage_expressions(theory, raw, use_pre_wilson=use_pre_wilson)
                pipeline_prefix = "pre_wilson" if use_pre_wilson else "post_wilson"
                processed = pipeline_expressions[
                    pipeline_prefix + ".postprocessed_with_scalar_bilinears"
                ]
                _add_pipeline_aggregate(pipeline_by_entry[entry_label][stage_name], pipeline_expressions)
                _add_pipeline_aggregate(order_pipelines[stage_name], pipeline_expressions)
                evaluated = vacuum_integrals.evaluate_one_loop_vakint_expression(
                    processed,
                    combine_terms=False,
                )
                totals[f"{stage_name}_unrenormalized"] = (
                    totals[f"{stage_name}_unrenormalized"] + normalization_factor * evaluated
                ).expand()
                totals[f"{stage_name}_finite"] = (
                    totals[f"{stage_name}_finite"] + normalization_factor * vakint.finite_part(evaluated)
                ).expand()
                totals_by_entry[entry_label][f"{stage_name}_unrenormalized"] = (
                    totals_by_entry[entry_label][f"{stage_name}_unrenormalized"]
                    + normalization_factor * evaluated
                ).expand()
                totals_by_entry[entry_label][f"{stage_name}_finite"] = (
                    totals_by_entry[entry_label][f"{stage_name}_finite"]
                    + normalization_factor * vakint.finite_part(evaluated)
                ).expand()
                order_totals[f"{stage_name}_unrenormalized"] = (
                    order_totals[f"{stage_name}_unrenormalized"] + normalization_factor * evaluated
                ).expand()
                order_totals[f"{stage_name}_finite"] = (
                    order_totals[f"{stage_name}_finite"] + normalization_factor * vakint.finite_part(evaluated)
                ).expand()

    heavy_substituted_totals = {
        stage_name: _apply_heavy_scalar_replacements(
            theory,
            expr,
            heavy_scalar_replacement_rules,
            expand=args.heavy_scalar_solution_expand,
        )
        for stage_name, expr in totals.items()
    }
    heavy_substituted_scalar_green_totals, heavy_substituted_scalar_green_errors = _transform_map_with_errors(
        heavy_substituted_totals,
        lambda expr: matching_module._apply_wilson_line_scalar_green_normal_form(theory, expr),
    )
    heavy_substituted_scalar_commutator_totals, heavy_substituted_scalar_commutator_errors = (
        _transform_map_with_errors(
            heavy_substituted_totals,
            lambda expr: matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
                theory,
                expr,
            ),
        )
    )

    payload = {
        "schema_version": 1,
        "generator": "debug_pychete_singlet_wilson_trace.py",
        "fixture": str(args.fixture),
        "model": fixture.name,
        "trace_name": args.trace_name,
        "target": args.target,
        "plan_entry_count": len(plan.entries),
        "plan_entries": [
            {
                "label": entry.label,
                "trace_name": entry.trace_name,
                "total_order": entry.total_order,
                "slot_orders": list(entry.slot_orders),
            }
            for entry in plan.entries
        ],
        "filter_terms_by_matching_targets": requirements is not None,
        "substitute_heavy_scalar_solutions": args.substitute_heavy_scalar_solutions,
        "heavy_scalar_solution_count": len(heavy_scalar_solutions),
        "heavy_scalar_solution_rule_count": len(heavy_scalar_replacement_rules),
        "heavy_scalar_solution_expand": args.heavy_scalar_solution_expand,
        "preaction_prefilter_nonempty_grouped_entries": {
            label: len(entry_terms) for label, entry_terms in preaction_prefilter_grouped.items() if entry_terms
        },
        "preaction_prefilter_nonempty_grouped_entry_orders": _grouped_entry_orders(
            preaction_prefilter_grouped,
            plan_entries_by_label,
        ),
        "preaction_prefilter_term_counts_by_total_order": _term_counts_by_total_order(
            preaction_prefilter_grouped,
            plan_entries_by_label,
        ),
        "preaction_prefilter_numerator_summaries_by_total_order": _aggregate_numerator_summaries_by_total_order(
            preaction_prefilter_grouped,
            plan_entries_by_label,
            h_label=h_label,
            sample_chars=args.sample_chars,
        ),
        "prefinal_nonempty_grouped_entries": {
            label: len(entry_terms) for label, entry_terms in prefinal_grouped.items() if entry_terms
        },
        "prefinal_nonempty_grouped_entry_orders": _grouped_entry_orders(
            prefinal_grouped,
            plan_entries_by_label,
        ),
        "prefinal_term_counts_by_total_order": _term_counts_by_total_order(
            prefinal_grouped,
            plan_entries_by_label,
        ),
        "prefinal_numerator_summaries_by_total_order": _aggregate_numerator_summaries_by_total_order(
            prefinal_grouped,
            plan_entries_by_label,
            h_label=h_label,
            sample_chars=args.sample_chars,
        ),
        "postfinal_filter_dropped_term_count_by_entry": {
            label: len(prefinal_grouped[label]) - len(entry_terms)
            for label, entry_terms in grouped.items()
            if len(prefinal_grouped[label]) - len(entry_terms)
        },
        "runtime_internal_nonempty_grouped_entries": {
            label: len(entry_terms) for label, entry_terms in runtime_grouped.items() if entry_terms
        },
        "runtime_internal_nonempty_grouped_entry_orders": _grouped_entry_orders(
            runtime_grouped,
            plan_entries_by_label,
        ),
        "runtime_internal_term_counts_by_total_order": _term_counts_by_total_order(
            runtime_grouped,
            plan_entries_by_label,
        ),
        "runtime_internal_evaluated": runtime_internal_evaluated,
        "nonempty_grouped_entries": {label: len(entry_terms) for label, entry_terms in grouped.items() if entry_terms},
        "nonempty_grouped_entry_orders": _grouped_entry_orders(grouped, plan_entries_by_label),
        "normalization": "matchete_evaluated_hbar",
        "normalization_factor": _full(normalization_factor),
        "h_field_label": _full(h_label),
        "coefficient_targets": {
            coefficient_name: _full(coefficient) for coefficient_name, coefficient in coefficient_targets.items()
        },
        "rows": rows,
        "total_projections": _projection_map(theory, args.target, target, totals),
        "total_summaries": _summary_map(totals, sample_chars=args.sample_chars),
        "total_h_derivative_word_histograms": _h_derivative_histogram_map(totals, h_label),
        "heavy_substituted_total_projections": _projection_map(
            theory,
            args.target,
            target,
            heavy_substituted_totals,
        ),
        "heavy_substituted_total_summaries": _summary_map(
            heavy_substituted_totals,
            sample_chars=args.sample_chars,
        ),
        "heavy_substituted_total_h_derivative_word_histograms": _h_derivative_histogram_map(
            heavy_substituted_totals,
            h_label,
        ),
        "heavy_substituted_scalar_green_total_projections": _projection_map(
            theory,
            args.target,
            target,
            heavy_substituted_scalar_green_totals,
        ),
        "heavy_substituted_scalar_green_total_summaries": _summary_map(
            heavy_substituted_scalar_green_totals,
            sample_chars=args.sample_chars,
        ),
        "heavy_substituted_scalar_green_total_h_derivative_word_histograms": _h_derivative_histogram_map(
            heavy_substituted_scalar_green_totals,
            h_label,
        ),
        "heavy_substituted_scalar_green_total_errors": heavy_substituted_scalar_green_errors,
        "heavy_substituted_scalar_commutator_total_projections": _projection_map(
            theory,
            args.target,
            target,
            heavy_substituted_scalar_commutator_totals,
        ),
        "heavy_substituted_scalar_commutator_total_summaries": _summary_map(
            heavy_substituted_scalar_commutator_totals,
            sample_chars=args.sample_chars,
        ),
        "heavy_substituted_scalar_commutator_total_h_derivative_word_histograms": _h_derivative_histogram_map(
            heavy_substituted_scalar_commutator_totals,
            h_label,
        ),
        "heavy_substituted_scalar_commutator_total_errors": heavy_substituted_scalar_commutator_errors,
        "total_coefficient_slices": {
            stage_name: {
                coefficient_name: _coefficient_slice_summary(
                    expr,
                    coefficient,
                    h_label=h_label,
                    name=f"{stage_name}.coefficient.{coefficient_name}",
                    sample_chars=args.sample_chars,
                )
                for coefficient_name, coefficient in coefficient_targets.items()
            }
            for stage_name, expr in totals.items()
        },
        "entry_projections": {
            stage_name: {
                entry_label: _full(_project_target(theory, args.target, target, entry_totals[stage_name]))
                for entry_label, entry_totals in totals_by_entry.items()
            }
            for stage_name in totals
        },
        "entry_summaries": {
            stage_name: {
                entry_label: _expr_summary(
                    f"{stage_name}.{entry_label}",
                    entry_totals[stage_name],
                    sample_chars=args.sample_chars,
                )
                for entry_label, entry_totals in totals_by_entry.items()
            }
            for stage_name in totals
        },
        "entry_h_derivative_word_histograms": {
            stage_name: {
                entry_label: _field_derivative_word_histogram(entry_totals[stage_name], h_label)
                for entry_label, entry_totals in totals_by_entry.items()
            }
            for stage_name in totals
        },
        "entry_pipeline_summaries": {
            stage_name: {
                entry_label: _pipeline_aggregate_summaries(
                    entry_pipelines[stage_name],
                    h_label=h_label,
                    sample_chars=args.sample_chars,
                )
                for entry_label, entry_pipelines in pipeline_by_entry.items()
            }
            for stage_name in ("post_wilson_tensor_reduced", "pre_wilson_tensor_reduced")
        },
        "order_projections": {
            stage_name: {
                str(total_order): _full(_project_target(theory, args.target, target, order_totals[stage_name]))
                for total_order, order_totals in sorted(totals_by_order.items())
            }
            for stage_name in totals
        },
        "order_summaries": {
            stage_name: {
                str(total_order): _expr_summary(
                    f"{stage_name}.order{total_order}",
                    order_totals[stage_name],
                    sample_chars=args.sample_chars,
                )
                for total_order, order_totals in sorted(totals_by_order.items())
            }
            for stage_name in totals
        },
        "order_h_derivative_word_histograms": {
            stage_name: {
                str(total_order): _field_derivative_word_histogram(order_totals[stage_name], h_label)
                for total_order, order_totals in sorted(totals_by_order.items())
            }
            for stage_name in totals
        },
        "order_pipeline_summaries": {
            stage_name: {
                str(total_order): _pipeline_aggregate_summaries(
                    order_pipelines[stage_name],
                    h_label=h_label,
                    sample_chars=args.sample_chars,
                )
                for total_order, order_pipelines in sorted(pipeline_by_order.items())
            }
            for stage_name in ("post_wilson_tensor_reduced", "pre_wilson_tensor_reduced")
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
