#!/usr/bin/env python
"""Compare Matchete and pychete Singlet Wilson-line debug dumps.

This development helper reads the JSON artifacts produced by
``helper_mathematica_scripts/debug_singlet_wilson_trace.wls`` and
``scripts/debug_pychete_singlet_wilson_trace.py``.  It intentionally has no
runtime role in pychete and no dependency on Mathematica.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_MATCHETE = Path("assets/validation/matchete/debug/singlet_hScalar_lScalar_cHW.debug.json")
DEFAULT_PYCHETE = Path("assets/validation/pychete/debug/singlet_hScalar_lScalar_cHW.pychete.fullrows.debug.json")
DEFAULT_MATCHETE_PROP_ORDERS = {
    0: Path("assets/validation/matchete/debug/singlet_hScalar_lScalar_cHW.prop0.debug.json"),
    2: Path("assets/validation/matchete/debug/singlet_hScalar_lScalar_cHW.prop2.debug.json"),
    4: DEFAULT_MATCHETE,
    6: Path("assets/validation/matchete/debug/singlet_hScalar_lScalar_cHW.prop6.debug.json"),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matchete", type=Path, default=DEFAULT_MATCHETE)
    parser.add_argument("--pychete", type=Path, default=DEFAULT_PYCHETE)
    parser.add_argument(
        "--matchete-prop-order",
        action="append",
        metavar="ORDER=PATH",
        help="Additional or replacement Matchete prop-order dump to summarize.",
    )
    parser.add_argument(
        "--no-default-prop-orders",
        action="store_true",
        help="Only summarize prop-order dumps passed through --matchete-prop-order.",
    )
    parser.add_argument("--sample-chars", type=int, default=180)
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON in {path}")
    return data


def _signature_counts(histogram: list[dict[str, Any]] | None) -> str:
    if not histogram:
        return "<none>"
    return ", ".join(f"{item['signature']}:{item['count']}" for item in histogram)


def _short(value: str, max_chars: int) -> str:
    return value if len(value) <= max_chars else value[: max_chars - 3] + "..."


def _stage_by_name(stages: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((stage for stage in stages if stage.get("name") == name), None)


def _parse_prop_order_spec(spec: str) -> tuple[int, Path]:
    if "=" not in spec:
        raise ValueError(f"expected ORDER=PATH for --matchete-prop-order, got {spec!r}")
    order, path = spec.split("=", 1)
    return int(order), Path(path)


def _prop_order_paths(args: argparse.Namespace) -> dict[int, Path]:
    paths: dict[int, Path] = {} if args.no_default_prop_orders else dict(DEFAULT_MATCHETE_PROP_ORDERS)
    for spec in args.matchete_prop_order or ():
        order, path = _parse_prop_order_spec(spec)
        paths[order] = path
    return paths


def _stage_terms_and_hist(stage: dict[str, Any] | None) -> str:
    if stage is None:
        return "<missing>"
    return f"terms={stage.get('term_count')} " + _signature_counts(stage.get("h_derivative_word_histogram"))


def _validation_stage_line(stage: dict[str, Any] | None) -> str:
    if stage is None:
        return "<missing>"
    status = " aborted" if stage.get("aborted_or_failed") else ""
    return f"{stage.get('name')}{status}: " + _stage_terms_and_hist(stage)


def _print_validation_stage_summaries(
    title: str,
    stages: list[dict[str, Any]] | None,
    *,
    indent: str,
) -> None:
    if not stages:
        return
    print(f"{indent}{title}")
    wanted = {
        "validation_input",
        "validation_contract_cgs",
        "validation_match_reduce",
        "validation_greens_simplify",
    }
    for stage in stages:
        if not isinstance(stage, dict) or stage.get("name") not in wanted:
            continue
        print(f"{indent}  " + _validation_stage_line(stage))


def _print_matchete_prop_order_summary(paths: dict[int, Path]) -> None:
    if not paths:
        return
    print("Matchete prop-order sweep")
    previous_chw: str | None = None
    for order, path in sorted(paths.items()):
        if not path.exists():
            print(f"  order {order}: missing {path}")
            continue
        data = _load_json(path)
        if previous_chw is None:
            previous_chw = str(data.get("previous_validation_cHW_condition_input_form", ""))
        raw = data.get("raw_insertion_sum_summary")
        prefactored = data.get("power_prefactor_times_raw_sum_summary")
        selected = data.get("selected_prop_order_validation_simplified_summary")
        selected_input = str(data.get("selected_prop_order_validation_simplified_input_form", ""))
        selected_status = "$Aborted" if selected_input.startswith("$Aborted") else "ok"
        print(f"  order {order}: insertions={data.get('insertion_count')} selected_status={selected_status}")
        print(f"    raw: {_stage_terms_and_hist(raw if isinstance(raw, dict) else None)}")
        print(f"    prefactored: {_stage_terms_and_hist(prefactored if isinstance(prefactored, dict) else None)}")
        print(f"    selected_validation: {_stage_terms_and_hist(selected if isinstance(selected, dict) else None)}")
        stage_summaries = data.get("selected_prop_order_validation_stage_summaries")
        _print_validation_stage_summaries(
            "selected validation checkpoints:",
            stage_summaries if isinstance(stage_summaries, list) else None,
            indent="    ",
        )
    if previous_chw:
        print(f"  saved validation cHW: {previous_chw}")


def _print_matchete_summary(data: dict[str, Any]) -> None:
    wanted = (
        "contracted_metric",
        "wilson_expanded",
        "loop_integrated",
        "post_index_group_cleanup",
        "eps_expanded_relabelled",
        "evaluate_str_reference",
    )
    print("Matchete stages")
    for insertion in data.get("insertions", []):
        print(f"  insertion {insertion.get('index')}")
        stages = insertion.get("stages", [])
        if not isinstance(stages, list):
            continue
        for name in wanted:
            stage = _stage_by_name(stages, name)
            if stage is None:
                continue
            print(
                "    "
                + f"{name}: terms={stage.get('term_count')} "
                + _signature_counts(stage.get("h_derivative_word_histogram"))
            )
        validation_stages = insertion.get("validation_simplification_stage_summaries")
        _print_validation_stage_summaries(
            "prefactored EvaluateSTr validation checkpoints:",
            validation_stages if isinstance(validation_stages, list) else None,
            indent="    ",
        )


def _nonzero_pychete_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("rows", [])
    if not isinstance(rows, list):
        return []
    selected: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        pre = row.get("pre_wilson_tensor_reduced", {})
        post = row.get("post_wilson_tensor_reduced", {})
        pre_nonzero = isinstance(pre, dict) and not pre.get("cHW_projection_finite_is_zero", True)
        post_nonzero = isinstance(post, dict) and not post.get("cHW_projection_finite_is_zero", True)
        if pre_nonzero or post_nonzero:
            selected.append(row)
    return selected


def _print_pychete_stage_summary(row: dict[str, Any], stage_key: str, *, sample_chars: int) -> None:
    stage = row.get(stage_key)
    if not isinstance(stage, dict):
        return
    projection = stage.get("cHW_projection_finite_sample_input_form", "")
    print(f"    {stage_key}: cHW_finite={_short(str(projection), sample_chars)}")
    snapshots = stage.get("pipeline_snapshots", [])
    if not isinstance(snapshots, list):
        return
    wanted_suffixes = (
        "tensor_reduced_decoded",
        "formal_metric_contracted",
        "wilson_terms_expanded",
        "postprocessed_without_scalar_bilinears",
        "postprocessed_with_scalar_bilinears",
    )
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            continue
        summary = snapshot.get("summary", {})
        if not isinstance(summary, dict):
            continue
        name = str(summary.get("name", ""))
        if not name.endswith(wanted_suffixes):
            continue
        print(
            "      "
            + f"{name}: terms={summary.get('term_count')} "
            + _signature_counts(snapshot.get("h_derivative_word_histogram"))
        )


def _print_pychete_order_pipeline_summaries(data: dict[str, Any]) -> None:
    order_pipelines = data.get("order_pipeline_summaries")
    if not isinstance(order_pipelines, dict) or not order_pipelines:
        return
    print("pychete aggregate pipeline snapshots by total order")
    for stage_name in ("pre_wilson_tensor_reduced", "post_wilson_tensor_reduced"):
        stage_orders = order_pipelines.get(stage_name)
        if not isinstance(stage_orders, dict):
            continue
        for order, snapshots in sorted(stage_orders.items(), key=lambda item: int(item[0])):
            if not isinstance(snapshots, dict) or not snapshots:
                continue
            print(f"  {stage_name} order {order}")
            for snapshot_name, snapshot in snapshots.items():
                if not isinstance(snapshot, dict):
                    continue
                summary = snapshot.get("summary", {})
                if not isinstance(summary, dict):
                    continue
                print(
                    "    "
                    + f"{snapshot_name}: terms={summary.get('term_count')} "
                    + _signature_counts(snapshot.get("h_derivative_word_histogram"))
                )
    print()


def _print_pychete_grouped_candidate_block(data: dict[str, Any], *, prefix: str, title: str) -> None:
    entry_orders = data.get(f"{prefix}_nonempty_grouped_entry_orders", {})
    entries = data.get(f"{prefix}_nonempty_grouped_entries", {})
    if not isinstance(entries, dict) or not entries:
        return
    print(title)
    for label, count in entries.items():
        order = entry_orders.get(label, {}) if isinstance(entry_orders, dict) else {}
        print(
            "  "
            + f"{label}: terms={count} "
            + f"order={order.get('total_order', '<unknown>')} "
            + f"slots={order.get('slot_orders', '<unknown>')}"
        )
    counts_by_order = data.get(f"{prefix}_term_counts_by_total_order", {})
    if isinstance(counts_by_order, dict) and counts_by_order:
        rendered = ", ".join(
            f"o{order}={count}" for order, count in sorted(counts_by_order.items(), key=lambda item: int(item[0]))
        )
        print(f"  totals by order: {rendered}")
    if prefix == "prefinal":
        dropped = data.get("postfinal_filter_dropped_term_count_by_entry", {})
        if isinstance(dropped, dict) and dropped:
            print("  dropped by final projection filter:")
            for label, count in dropped.items():
                print(f"    {label}: {count}")
    numerator_summaries = data.get(f"{prefix}_numerator_summaries_by_total_order", {})
    if isinstance(numerator_summaries, dict) and numerator_summaries:
        print("  candidate numerator summaries:")
        for order, summaries in sorted(numerator_summaries.items(), key=lambda item: int(item[0])):
            if not isinstance(summaries, dict):
                continue
            rendered_parts: list[str] = []
            for name in ("pre_wilson_numerator", "wilson_expanded_numerator"):
                snapshot = summaries.get(name, {})
                summary = snapshot.get("summary", {}) if isinstance(snapshot, dict) else {}
                if isinstance(summary, dict):
                    rendered_parts.append(
                        f"{name}=terms:{summary.get('term_count')} "
                        + _signature_counts(snapshot.get("h_derivative_word_histogram"))
                    )
            print(f"    order {order}: " + "; ".join(rendered_parts))
    print()


def _print_pychete_summary(data: dict[str, Any], *, sample_chars: int) -> None:
    print(
        "pychete selection: "
        + f"filter_by_target={data.get('filter_terms_by_matching_targets', '<unknown>')} "
        + f"plan_entries={data.get('plan_entry_count', '<unknown>')}"
    )
    _print_pychete_grouped_candidate_block(
        data,
        prefix="preaction_prefilter",
        title="pychete pre-action prefilter entries",
    )
    _print_pychete_grouped_candidate_block(
        data,
        prefix="prefinal",
        title="pychete pre-final post-action candidate entries",
    )
    entry_orders = data.get("nonempty_grouped_entry_orders", {})
    nonempty_entries = data.get("nonempty_grouped_entries", {})
    if isinstance(nonempty_entries, dict) and nonempty_entries:
        print("pychete nonempty selected entries")
        for label, count in nonempty_entries.items():
            order = entry_orders.get(label, {}) if isinstance(entry_orders, dict) else {}
            print(
                "  "
                + f"{label}: terms={count} "
                + f"order={order.get('total_order', '<unknown>')} "
                + f"slots={order.get('slot_orders', '<unknown>')}"
            )
        print()
    total_projections = data.get("total_projections", {})
    if isinstance(total_projections, dict) and total_projections:
        print("pychete selected-total projections")
        for name in (
            "post_wilson_tensor_reduced_finite",
            "pre_wilson_tensor_reduced_finite",
            "post_wilson_tensor_reduced_unrenormalized",
            "pre_wilson_tensor_reduced_unrenormalized",
        ):
            if name in total_projections:
                print(f"  {name}: {_short(str(total_projections[name]), sample_chars)}")
        print()
    order_projections = data.get("order_projections", {})
    if isinstance(order_projections, dict) and order_projections:
        print("pychete selected projections by total order")
        for stage_name in (
            "post_wilson_tensor_reduced_finite",
            "pre_wilson_tensor_reduced_finite",
        ):
            stage_projection = order_projections.get(stage_name, {})
            if not isinstance(stage_projection, dict) or not stage_projection:
                continue
            rendered = ", ".join(
                f"o{order}={_short(str(value), sample_chars)}"
                for order, value in sorted(stage_projection.items(), key=lambda item: int(item[0]))
            )
            print(f"  {stage_name}: {rendered}")
        print()
    _print_pychete_order_pipeline_summaries(data)
    print("pychete nonzero rows")
    rows = _nonzero_pychete_rows(data)
    if not rows:
        print("  <none>")
        return
    for row in rows:
        print(
            "  "
            + f"{row.get('entry_label')} term={row.get('term_index')} "
            + f"powers={row.get('propagator_powers')} slots={row.get('expansion_slot_lengths')}"
        )
        _print_pychete_stage_summary(row, "pre_wilson_tensor_reduced", sample_chars=sample_chars)
        _print_pychete_stage_summary(row, "post_wilson_tensor_reduced", sample_chars=sample_chars)


def main() -> int:
    args = _parse_args()
    matchete = _load_json(args.matchete)
    pychete = _load_json(args.pychete)
    print(f"Matchete dump: {args.matchete}")
    print(f"pychete dump:  {args.pychete}")
    print()
    _print_matchete_prop_order_summary(_prop_order_paths(args))
    print()
    _print_matchete_summary(matchete)
    print()
    _print_pychete_summary(pychete, sample_chars=args.sample_chars)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
