#!/usr/bin/env python
"""Dump pychete intermediates for the Singlet hScalar-lScalar -> cHW frontier.

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
from pychete.matching_results import MatchingResult
from pychete.symbols import canonical_string, s
from pychete.validation_fixtures import load_validation_fixture


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


def _project_chw(theory: Any, target: Expression, expr: Expression) -> Expression:
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=expr,
    )
    return result.project_matching_conditions(
        {"cHW": target},
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
        drop_zero=False,
    )["cHW"].expand()


def _processed_stage(
    theory: Any,
    raw: Expression,
    *,
    use_pre_wilson: bool,
) -> Expression:
    reduced = vakint.tensor_reduce(raw)
    reduced = vakint.decode_pychete_namespace(theory, reduced)
    if use_pre_wilson:
        return matching_module._postprocess_pre_wilson_line_tensor_reduced_expression(
            theory,
            reduced,
            max_wilson_derivative_order=4,
            emit_covariant_derivative_commutators=True,
            emit_covariant_derivative_commutator_passes=1,
            covariant_derivative_commutator_mode="all_distinct",
            expand_covariant_derivative_commutators=True,
            simplify_pychete_color_algebra=True,
            expose_scalar_derivative_commutator_bilinears_option=True,
        )
    return matching_module._postprocess_wilson_line_tensor_reduced_expression(
        theory,
        reduced,
        emit_covariant_derivative_commutators=True,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=True,
        simplify_pychete_color_algebra=True,
        expose_scalar_derivative_commutator_bilinears_option=True,
    )


def _term_row(
    theory: Any,
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
        "pre_wilson_numerator": (
            _expr_summary("pre_wilson_numerator", term.pre_wilson_numerator, sample_chars=sample_chars)
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
        processed = _processed_stage(theory, raw, use_pre_wilson=use_pre_wilson)
        evaluated = vacuum_integrals.evaluate_one_loop_vakint_expression(
            processed,
            combine_terms=False,
        )
        finite = vakint.finite_part(evaluated)
        normalized = (normalization_factor * evaluated).expand()
        normalized_finite = (normalization_factor * finite).expand()
        projection = _project_chw(theory, target, normalized)
        finite_projection = _project_chw(theory, target, normalized_finite)
        row[stage_name] = {
            "raw_integral": _expr_summary(f"{stage_name}.raw_integral", raw, sample_chars=sample_chars),
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
            "cHW_projection": _full(projection),
            "cHW_projection_sample_input_form": _short(projection, sample_chars),
            "cHW_projection_is_zero": bool(projection.expand() == Expression.num(0)),
            "cHW_projection_finite": _full(finite_projection),
            "cHW_projection_finite_sample_input_form": _short(finite_projection, sample_chars),
            "cHW_projection_finite_is_zero": bool(finite_projection.expand() == Expression.num(0)),
        }
    return row


def main() -> int:
    args = _parse_args()
    fixture = load_validation_fixture(args.fixture)
    theory = fixture.theory()
    lagrangian = fixture.expression("lagrangian")
    target = smeft_warsaw_operator(theory, args.target)
    if target is None:
        raise ValueError(f"unknown SMEFT Warsaw target {args.target!r}")
    hbar = theory.external_handle("hbar")() if "hbar" in theory.externals else s.HBar
    normalization_factor = one_loop_normalization_factor(OneLoopNormalization.MATCHETE_EVALUATED_HBAR, hbar=hbar)
    h_label = theory.field_handle("H").label
    coefficient_targets: dict[str, Expression] = {}
    if "A" in theory.couplings:
        coefficient_targets["A2"] = theory.coupling_handle("A")() ** 2
    if "A" in theory.couplings and "gL" in theory.couplings:
        coefficient_targets["A2_gL2"] = theory.coupling_handle("A")() ** 2 * theory.coupling_handle("gL")() ** 2

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
    requirements = matching_module._term_atom_requirements_for_targets(theory, {"cHW": target})
    grouped = setup.interaction_wilson_line_expansion_terms_by_trace(
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

    rows: list[dict[str, Any]] = []
    totals = {
        "post_wilson_tensor_reduced_unrenormalized": Expression.num(0),
        "post_wilson_tensor_reduced_finite": Expression.num(0),
        "pre_wilson_tensor_reduced_unrenormalized": Expression.num(0),
        "pre_wilson_tensor_reduced_finite": Expression.num(0),
    }
    for entry_label, entry_terms in grouped.items():
        if args.entry_contains and args.entry_contains not in entry_label:
            continue
        for term_index, term in enumerate(entry_terms):
            row = _term_row(
                theory,
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
                or not row["post_wilson_tensor_reduced"]["cHW_projection_is_zero"]
                or not row["pre_wilson_tensor_reduced"]["cHW_projection_is_zero"]
            ):
                rows.append(row)
            for stage_name, use_pre_wilson in (
                ("post_wilson_tensor_reduced", False),
                ("pre_wilson_tensor_reduced", True),
            ):
                if use_pre_wilson and term.pre_wilson_numerator is None:
                    continue
                raw = term.vakint_integral_expression(use_pre_wilson_numerator=use_pre_wilson)
                processed = _processed_stage(theory, raw, use_pre_wilson=use_pre_wilson)
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

    payload = {
        "schema_version": 1,
        "generator": "debug_pychete_singlet_wilson_trace.py",
        "fixture": str(args.fixture),
        "model": fixture.name,
        "trace_name": args.trace_name,
        "target": args.target,
        "plan_entry_count": len(plan.entries),
        "nonempty_grouped_entries": {label: len(entry_terms) for label, entry_terms in grouped.items() if entry_terms},
        "normalization": "matchete_evaluated_hbar",
        "normalization_factor": _full(normalization_factor),
        "h_field_label": _full(h_label),
        "coefficient_targets": {
            coefficient_name: _full(coefficient) for coefficient_name, coefficient in coefficient_targets.items()
        },
        "rows": rows,
        "total_projections": {
            stage_name: _full(_project_chw(theory, target, expr))
            for stage_name, expr in totals.items()
        },
        "total_summaries": {
            stage_name: _expr_summary(stage_name, expr, sample_chars=args.sample_chars)
            for stage_name, expr in totals.items()
        },
        "total_h_derivative_word_histograms": {
            stage_name: _field_derivative_word_histogram(expr, h_label)
            for stage_name, expr in totals.items()
        },
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
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
