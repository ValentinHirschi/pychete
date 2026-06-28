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

from symbolica import Expression

import pychete.matching as matching_module
from pychete import (
    MatchingResult,
    OneLoopNormalization,
    canonical_string,
    load_validation_fixture,
    one_loop_normalization_factor,
)
from pychete.backends import vakint as vakint_backend
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
        max_total_order=0,
        max_slot_order=0,
        index_prefix="debug_singlet_eom_boundary",
    )
    heavy_solutions = matching_module.solve_heavy_scalar_eoms(theory, lagrangian, eft_order=6)
    requirements = matching_module._term_atom_requirements_for_targets(
        theory,
        {condition_name: target},
        heavy_scalar_solutions=heavy_solutions,
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
    terms_by_path_lists: dict[str, list[Any]] = {}
    for entry_terms in grouped_terms.values():
        for term in entry_terms:
            terms_by_path_lists.setdefault(f"path{term.path_index}", []).append(term)
    terms_by_path = {
        path: tuple(terms)
        for path, terms in terms_by_path_lists.items()
    }
    evaluated_by_entry = matching_module._wilson_line_internal_evaluated_terms_by_entry_from_terms(
        theory,
        terms_by_path,
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
    selected = sum(
        (term for entry_terms in evaluated_by_entry.values() for term in entry_terms),
        Expression.num(0),
    )
    normalized = (
        one_loop_normalization_factor(
            OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
            hbar=theory.external_handle("hbar")(),
        )
        * selected
    ).expand()
    post_green = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
        theory,
        normalized,
    )
    post_heavy = post_green.replace_multiple(
        matching_module.heavy_scalar_solution_replacements(
            heavy_solutions,
            fresh_dummy_indices=True,
        ),
        repeat=False,
    ).expand()
    post_heavy_green = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
        theory,
        post_heavy,
    )
    stage_expressions = {
        "selected_normalized_evaluated": normalized,
        "selected_normalized_pole_part": vakint_backend.pole_part(normalized),
        "selected_normalized_finite_part": vakint_backend.finite_part(normalized),
        "selected_post_green": post_green,
        "selected_post_heavy": post_heavy,
        "selected_post_heavy_green": post_heavy_green,
    }
    path_stage_expressions = {
        path: (
            one_loop_normalization_factor(
                OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
                hbar=theory.external_handle("hbar")(),
            )
            * sum(evaluated_terms, Expression.num(0))
        ).expand()
        for path, evaluated_terms in evaluated_by_entry.items()
    }
    path_finite_stage_expressions = {
        path: vakint_backend.finite_part(expr)
        for path, expr in path_stage_expressions.items()
    }
    reference_off_shell = reference.project_matching_conditions(
        {condition_name: target},
        source="off_shell_eft_lagrangian",
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )[condition_name]
    matchete_quarter_insertions = _matchete_quarter_insertions(matchete_trace_debug)
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
        "controls": {
            "trace_names": ["hScalar-lScalar-lVector-lScalar"],
            "max_trace_order": 4,
            "max_total_order": 0,
            "max_slot_order": 0,
            "act_open_derivatives": True,
            "tensor_reduce_before_wilson_expand": True,
            "simplify_pychete_color_algebra": True,
            "normalization": "matchete_evaluated_hbar",
        },
        "term_counts_by_entry": {entry: len(terms) for entry, terms in grouped_terms.items()},
        "term_counts_by_path": {path: len(terms) for path, terms in sorted(terms_by_path.items())},
        "evaluated_term_counts_by_entry": {
            entry: sum(len(terms) for terms in evaluated_by_entry.values()) for entry in grouped_terms
        },
        "evaluated_term_counts_by_path": {
            path: len(terms) for path, terms in sorted(evaluated_by_entry.items())
        },
        "matchete_quarter_insertions": matchete_quarter_insertions,
        "matchete_quarter_insertion_count": len(matchete_quarter_insertions),
        "pychete_nonzero_path_count": len(terms_by_path),
        "heavy_scalar_solution_count": len(heavy_solutions),
        "selected_stage_projections": _projection_strings(
            theory,
            condition_name,
            target,
            stage_expressions,
        ),
        "path_stage_projections": _projection_strings(
            theory,
            condition_name,
            target,
            path_stage_expressions,
        ),
        "path_finite_stage_projections": _projection_strings(
            theory,
            condition_name,
            target,
            path_finite_stage_expressions,
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
            "selected_wilson_line_trace_aggregation_or_reduction_before_eom; "
            "pychete selected prop-order-zero normalized source now has the "
            "-2 pole/log weight from eight nonzero Wilson-line paths, each "
            "projecting with the Matchete -1/4 insertion sign. The paired "
            "Matchete insertion dump also records eight -1/4 insertion "
            "checkpoints, while Matchete's saved selected trace/off-shell "
            "checkpoint has -3/2 and the selected prop-order aggregate fields "
            "in this dump are $Failed/$Aborted. The next comparison is "
            "Matchete's reduction/aggregation from insertion checkpoints or "
            "raw selected prop-order data to the saved validation trace, not "
            "source/path coverage or target filtering."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
