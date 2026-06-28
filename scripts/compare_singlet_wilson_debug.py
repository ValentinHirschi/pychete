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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matchete", type=Path, default=DEFAULT_MATCHETE)
    parser.add_argument("--pychete", type=Path, default=DEFAULT_PYCHETE)
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


def _print_pychete_summary(data: dict[str, Any], *, sample_chars: int) -> None:
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
    _print_matchete_summary(matchete)
    print()
    _print_pychete_summary(pychete, sample_chars=args.sample_chars)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
