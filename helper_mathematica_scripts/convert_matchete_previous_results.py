#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pychete.loaders import parse_matchete_expression
from pychete.loaders.mathematica import _split_top_level, _strip_comments
from pychete.state import PycheteState
from pychete.symbols import canonical_string
from pychete.theory import Theory
from pychete.validation_fixtures import load_validation_fixture


DEFAULT_MODELS = ("VLF_toy_model", "Singlet_Scalar_Extension", "E_VLL", "S1S3LQs")


def _split_rule(text: str) -> tuple[str, str]:
    square = curly = paren = assoc = 0
    in_string = False
    i = 0
    while i < len(text):
        if not in_string and text.startswith("<|", i):
            assoc += 1
            i += 2
            continue
        if not in_string and text.startswith("|>", i):
            assoc -= 1
            i += 2
            continue
        char = text[i]
        if char == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
            i += 1
            continue
        if in_string:
            i += 1
            continue
        if char == "[":
            square += 1
        elif char == "]":
            square -= 1
        elif char == "{":
            curly += 1
        elif char == "}":
            curly -= 1
        elif char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif text.startswith("->", i) and square == 0 and curly == 0 and paren == 0 and assoc == 0:
            return text[:i].strip(), text[i + 2 :].strip()
        i += 1
    raise ValueError(f"Expected a top-level Wolfram rule in: {text[:120]}")


def _string_key(raw: str) -> str:
    key = raw.strip()
    if key.startswith('"') and key.endswith('"'):
        return key[1:-1]
    return key


def _association(text: str) -> dict[str, str]:
    value = _strip_comments(text).strip()
    if value.startswith("<|") and value.endswith("|>"):
        value = value[2:-2]
    return {
        _string_key(key): item
        for part in _split_top_level(value, ",")
        for key, item in [_split_rule(part)]
    }


def _expression_name(prefix: str, label: str) -> str:
    normalized = "".join(char if char.isalnum() else "_" for char in label)
    normalized = "_".join(part for part in normalized.split("_") if part)
    return f"{prefix}_{normalized}"


def _rule_list(text: str) -> list[tuple[str, str]]:
    value = text.strip()
    if value == "None":
        return []
    if not value.startswith("{") or not value.endswith("}"):
        raise ValueError(f"Expected a Wolfram rule list or None, got {value[:120]}")
    return [_split_rule(part) for part in _split_top_level(value[1:-1], ",")]


def _add_matching_conditions(state: PycheteState, theory: Theory, text: str) -> dict[str, str]:
    condition_refs: dict[str, str] = {}
    for i, (lhs_text, rhs_text) in enumerate(_rule_list(text), start=1):
        lhs = parse_matchete_expression(lhs_text, theory)
        rhs = parse_matchete_expression(rhs_text, theory)
        expression_name = f"matchete_matching_condition_{i:03d}"
        condition_refs[canonical_string(lhs)] = expression_name
        state.add_expression(expression_name, theory, rhs)
    return condition_refs


def _build_fixture(model: str, reference_root: Path, fixtures_dir: Path) -> dict[str, object]:
    model_fixture_path = fixtures_dir / f"{model}.model_fixture.json"
    result_path = reference_root / "Validation" / "MatchingResults" / "previous" / f"{model}-EFT.m"
    model_fixture = load_validation_fixture(model_fixture_path)
    theory = model_fixture.theory()
    result = _association(result_path.read_text(encoding="utf-8"))
    supertraces = _association(result["SuperTraces"])

    state = PycheteState()
    state.add_theory(theory)
    stage_names = {
        "uv_lagrangian": "matchete_uv_lagrangian",
        "off_shell_eft_lagrangian": "matchete_off_shell_eft_lagrangian",
        "on_shell_eft_lagrangian": "matchete_on_shell_eft_lagrangian",
    }
    state.add_expression(stage_names["uv_lagrangian"], theory, parse_matchete_expression(result["UV Lagrangian"], theory))
    state.add_expression(
        stage_names["off_shell_eft_lagrangian"],
        theory,
        parse_matchete_expression(result["Off-shell EFT Lagrangian"], theory),
    )
    state.add_expression(
        stage_names["on_shell_eft_lagrangian"],
        theory,
        parse_matchete_expression(result["On-shell EFT Lagrangian"], theory),
    )

    supertrace_refs: dict[str, str] = {}
    for label, expression_text in supertraces.items():
        expression_name = _expression_name("matchete_supertrace", label)
        supertrace_refs[label] = expression_name
        state.add_expression(expression_name, theory, parse_matchete_expression(expression_text, theory))
    matching_condition_refs = _add_matching_conditions(state, theory, result["Matching Conditions"])
    matching_conditions_included = bool(matching_condition_refs)

    return {
        "schema_version": 1,
        "name": f"{model}_matchete_previous_matching",
        "kind": "matching_result",
        "source": {
            "generator": "helper_mathematica_scripts/convert_matchete_previous_results.py",
            "matchete_runtime_required": False,
            "reference_result": str(result_path.relative_to(reference_root)),
            "model_fixture": str(model_fixture_path),
            "matchete_model": _string_key(result["Model"]),
            "matchete_version": _string_key(result["Version"]),
            "matching_conditions_included": matching_conditions_included,
            "matching_condition_count": len(matching_condition_refs),
            "matching_condition_key_format": "canonical pychete expression for the Matchete rule left-hand side",
            "matching_conditions_exclusion": None
            if matching_conditions_included
            else "Matchete stores None for this model's matching conditions.",
        },
        "state": state.to_json_obj(),
        "expressions": sorted(state.expressions),
        "matching_results": {
            "matchete_previous": {
                "theory": theory.name,
                **stage_names,
                "matching_conditions": matching_condition_refs,
                "fluctuation_operators": {},
                "supertraces": supertrace_refs,
                "metadata": {
                    "loop_order": 1,
                    "eft_order": 6,
                    "source": "Matchete previous validation result",
                },
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-root", type=Path, default=Path("Mathematica_reference/Matchete"))
    parser.add_argument("--fixtures-dir", type=Path, default=Path("assets/validation/pychete"))
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    args = parser.parse_args()

    for model in [item.strip() for item in args.models.split(",") if item.strip()]:
        fixture = _build_fixture(model, args.reference_root, args.fixtures_dir)
        out_path = args.fixtures_dir / f"{model}.matching_fixture.json"
        out_path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
