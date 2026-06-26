#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from itertools import count
from pathlib import Path
from typing import Any

from symbolica import Expression

from pychete.dimensions import infer_coupling_mass_dimensions
from pychete.loaders import parse_matchete_expression
from pychete.backends.spenso import cg_tensor_component_expression
from pychete.loaders.mathematica import (
    _clean_name,
    _eval_expression,
    _eval_expression_list,
    _field_type,
    _parse_chirality,
    _parse_call,
    _parse_coupling_self_conjugate,
    _parse_diagonal_coupling,
    _parse_int,
    _parse_int_list,
    _parse_representation_name,
    _preprocess_names,
    _split_top_level,
    _strip_comments,
)
from pychete.state import PycheteState
from pychete.symbols import SymbolRole, s
from pychete.theory import Theory
from pychete.theory_metadata import FieldMassKind, FieldRole, RepresentationReality

_DIMENSION_PROBE_COUNTER = count()


def _entry_name(entry: dict[str, Any]) -> str:
    return _clean_name(str(entry["name_input_form"]))


def _optional_entry_name(entry: dict[str, Any], key: str) -> str | None:
    value = entry.get(key)
    if value is None:
        return None
    return _clean_name(str(value))


def _matchete_group_type(text: str) -> Expression:
    normalized = _preprocess_names(str(text)).strip()
    if normalized == "U1":
        return s.U1
    su_apply = re.fullmatch(r"SU\s*@\s*(\d+)", normalized)
    if su_apply:
        return s.SU(Expression.num(int(su_apply.group(1))))
    alg = re.fullmatch(r'Alg\["A",\s*(\d+)\]', normalized)
    if alg:
        return s.SU(Expression.num(int(alg.group(1)) + 1))
    raise NotImplementedError(f"Unsupported loaded Matchete group type: {text}")


def _matchete_reality(value: str | int | None) -> RepresentationReality:
    if value is None:
        return RepresentationReality.UNKNOWN
    normalized = _clean_name(str(value)).lower()
    if normalized in {"real", "1"}:
        return RepresentationReality.REAL
    if normalized in {"complex", "0"}:
        return RepresentationReality.COMPLEX
    if normalized in {"pseudoreal", "pseudo", "-1"}:
        return RepresentationReality.PSEUDOREAL
    return RepresentationReality.UNKNOWN


def _entry_expressions(entry: dict[str, Any], key: str, theory: Theory) -> tuple[Expression, ...]:
    values = entry.get(key, [])
    if values is None:
        return ()
    if not isinstance(values, list):
        raise TypeError(f"{key} must be a list of InputForm strings")
    return tuple(_eval_expression(str(value), theory, {}) for value in values)


def _entry_expression_list_text(entry: dict[str, Any], key: str, theory: Theory) -> tuple[Expression, ...]:
    value = str(entry.get(key, "{}"))
    return tuple(_eval_expression_list(value, theory))


def _field_type_for_entry(entry: dict[str, Any], theory: Theory) -> Expression:
    raw = str(entry["type_input_form"])
    if _clean_name(raw) == "Vector":
        field_name = _entry_name(entry)
        for group in theory.groups.values():
            if group.get("field") == field_name:
                return s.Vector(theory.symbol(str(group["name"]), role=SymbolRole.GROUP))
        return s.Vector
    return _field_type(raw)


def _field_role_for_entry(entry: dict[str, Any], type_expr: Expression) -> FieldRole:
    raw_role = str(entry.get("field_role", "physical"))
    if raw_role == "goldstone":
        return FieldRole.GOLDSTONE
    if raw_role == "background":
        return FieldRole.BACKGROUND
    if raw_role == "ghost":
        return FieldRole.GHOST
    if raw_role == "anti_ghost":
        return FieldRole.ANTI_GHOST
    return FieldRole.from_type(type_expr)


def _coupling_by_name(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {_entry_name(entry): entry for entry in data.get("couplings", [])}


def _entry_mass_dimension(
    entry: dict[str, Any],
    coupling_dimensions: dict[str, int | float],
) -> int | float | None:
    value = entry.get("mass_dimension")
    if value is not None:
        return value
    return coupling_dimensions.get(_entry_name(entry))


def _mass_spec(entry: dict[str, Any], couplings: dict[str, dict[str, Any]], theory: Theory) -> int | tuple[str, str, tuple[Expression, ...]]:
    raw_mass = str(entry.get("mass_input_form", "0"))
    if raw_mass in {"0", "Null", "None"}:
        return 0
    mass_name = _clean_name(raw_mass)
    mass_kind = FieldMassKind.HEAVY.value if bool(entry.get("heavy", False)) else FieldMassKind.LIGHT.value
    mass_indices = _entry_expressions(couplings[mass_name], "indices_input_form", theory) if mass_name in couplings else ()
    return (mass_kind, mass_name, mass_indices)


def _parse_self_conjugate(raw: str) -> bool | tuple[int, ...]:
    value = _preprocess_names(raw).strip()
    if value.startswith("{") and value.endswith("}"):
        return tuple(_parse_int(part) for part in value[1:-1].split(",") if part.strip())
    return _parse_coupling_self_conjugate(value)


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


def _parse_permutation_key(raw: str) -> tuple[int, ...]:
    value = _preprocess_names(raw).strip()
    if value.startswith("{") and value.endswith("}"):
        return tuple(_parse_int(part) for part in _split_top_level(value[1:-1], ","))
    if value.startswith("List[") and value.endswith("]"):
        return tuple(_parse_int(part) for part in _split_top_level(value[5:-1], ","))
    raise ValueError(f"Unsupported Matchete symmetry permutation key: {raw}")


def _parse_internal_symmetry_association(raw: str) -> tuple[Expression, ...]:
    value = _strip_comments(_preprocess_names(raw)).strip()
    if value.startswith("<|") and value.endswith("|>"):
        body = value[2:-2].strip()
    elif value.startswith("Association[") and value.endswith("]"):
        body = value[len("Association[") : -1].strip()
    else:
        raise ValueError(f"Unsupported Matchete internal symmetry association: {raw}")
    if not body:
        return ()

    symmetries: list[Expression] = []
    for part in _split_top_level(body, ","):
        key_raw, sign_raw = _split_rule(part)
        permutation = _parse_permutation_key(key_raw)
        if permutation == tuple(range(1, len(permutation) + 1)):
            continue
        sign = _parse_int(sign_raw)
        if sign == 1:
            symmetries.append(s.SymmetricPermutation(*permutation))
        elif sign == -1:
            symmetries.append(s.AntisymmetricPermutation(*permutation))
        else:
            raise ValueError(f"Unsupported Matchete symmetry sign {sign_raw!r} for permutation {permutation}")
    return tuple(symmetries)


def _parse_symmetries(raw: str, theory: Theory, warnings: list[str], coupling_name: str) -> tuple[Expression, ...]:
    value = _preprocess_names(raw).strip()
    if value in {"{}", "<||>", "Association[]"}:
        return ()
    if value.startswith("<|") or value.startswith("Association["):
        try:
            return _parse_internal_symmetry_association(value)
        except ValueError as exc:
            warnings.append(f"Skipped internal Matchete symmetry association for coupling {coupling_name}: {exc}")
            return ()
    return tuple(_eval_expression_list(value, theory))


def _mathematica_list_parts(raw: str) -> list[str]:
    value = _strip_comments(_preprocess_names(raw)).strip()
    if value.startswith("{") and value.endswith("}"):
        return _split_top_level(value[1:-1], ",")
    if value.startswith("List[") and value.endswith("]"):
        return _split_top_level(value[5:-1], ",")
    raise ValueError(f"Expected a Wolfram list, got {raw[:120]}")


def _row_major_index(indices: tuple[int, ...], dimensions: tuple[int, ...]) -> int:
    flat = 0
    for index, dimension in zip(indices, dimensions, strict=True):
        flat = flat * dimension + index
    return flat


def _sparse_array_components(raw: str, theory: Theory) -> Expression | None:
    value = _strip_comments(_preprocess_names(raw)).strip()
    if not value.startswith("SparseArray["):
        return None

    head, parts = _parse_call(value)
    if head != "SparseArray" or len(parts) != 4:
        raise ValueError(f"Only four-argument Matchete SparseArray tensors are supported, got {raw[:120]}")

    dimensions = tuple(int(dimension) for dimension in _parse_int_list(parts[1]))
    if not dimensions:
        raise ValueError("SparseArray tensor has no dimensions")
    component_count = 1
    for dimension in dimensions:
        component_count *= dimension

    default = _eval_expression(parts[2], theory, {})
    compressed_parts = _mathematica_list_parts(parts[3])
    if len(compressed_parts) != 3:
        raise ValueError(f"Unsupported SparseArray compressed data shape: {parts[3][:120]}")
    version = _parse_int(compressed_parts[0])
    if version != 1:
        raise ValueError(f"Unsupported SparseArray compressed data version {version}")

    pointer_parts = _mathematica_list_parts(compressed_parts[1])
    if len(pointer_parts) != 2:
        raise ValueError(f"Unsupported SparseArray pointer data shape: {compressed_parts[1][:120]}")
    row_pointers = tuple(_parse_int(part) for part in _mathematica_list_parts(pointer_parts[0]))
    coordinates = tuple(tuple(_parse_int_list(part)) for part in _mathematica_list_parts(pointer_parts[1]))
    values = tuple(_eval_expression(part, theory, {}) for part in _mathematica_list_parts(compressed_parts[2]))

    if len(row_pointers) != dimensions[0] + 1:
        raise ValueError(f"SparseArray row pointer length {len(row_pointers)} is incompatible with {dimensions[0]} rows")
    if len(coordinates) != len(values):
        raise ValueError(f"SparseArray coordinate count {len(coordinates)} does not match value count {len(values)}")
    if row_pointers[-1] != len(values):
        raise ValueError(f"SparseArray row pointer terminates at {row_pointers[-1]}, but has {len(values)} values")

    components = [default for _ in range(component_count)]
    rank = len(dimensions)
    for first_index in range(1, dimensions[0] + 1):
        for position in range(row_pointers[first_index - 1], row_pointers[first_index]):
            full_indices = (first_index, *coordinates[position])
            if len(full_indices) != rank:
                raise ValueError(f"SparseArray coordinate {full_indices} has rank {len(full_indices)}, expected {rank}")
            if any(index < 1 or index > dimension for index, dimension in zip(full_indices, dimensions, strict=True)):
                raise ValueError(f"SparseArray coordinate {full_indices} is outside dimensions {dimensions}")
            components[_row_major_index(tuple(index - 1 for index in full_indices), dimensions)] = values[position]

    return cg_tensor_component_expression(dimensions, components)


def _build_theory_from_model_state(
    data: dict[str, Any],
    *,
    model_name: str,
    warnings: list[str],
    coupling_dimensions: dict[str, int | float] | None = None,
    theory_name: str | None = None,
) -> Theory:
    theory = Theory(theory_name or model_name)
    couplings = _coupling_by_name(data)
    dimensions = coupling_dimensions or {}

    for entry in data.get("flavor_indices", []):
        theory.define_flavor_index(_entry_name(entry), _parse_int(str(entry["dimension_input_form"])))

    for entry in data.get("gauge_groups", []):
        coupling = _optional_entry_name(entry, "coupling_input_form")
        field = _optional_entry_name(entry, "field_input_form")
        if coupling is None or field is None:
            raise ValueError(f"Gauge group {_entry_name(entry)!r} is missing coupling or field metadata")
        theory.define_gauge_group(_entry_name(entry), _matchete_group_type(str(entry["group_input_form"])), coupling, field)

    for entry in data.get("global_groups", []):
        theory.define_global_group(_entry_name(entry), _matchete_group_type(str(entry["group_input_form"])))

    for entry in data.get("representations", []):
        group, label = _parse_representation_name(str(entry["name_input_form"]))
        declared_group = _clean_name(str(entry["group_input_form"]))
        if group != declared_group:
            warnings.append(
                f"Representation {entry['name_input_form']} declares group {declared_group}, "
                f"but its label parses as group {group}; using parsed group."
            )
        if group not in theory.groups:
            warnings.append(f"Skipped representation {entry['name_input_form']} because group {group} is not registered.")
            continue
        theory.define_representation(
            group,
            label,
            dynkin=_entry_expression_list_text(entry, "dynkin_input_form", theory),
            dimension=int(entry["dimension"]) if entry.get("dimension") is not None else None,
            reality=_matchete_reality(entry.get("reality_input_form")),
        )

    for entry in data.get("couplings", []):
        name = _entry_name(entry)
        diagonal = entry.get("diagonal_coupling", None)
        diagonal_flags = tuple(bool(item) for item in diagonal) if isinstance(diagonal, list) else _parse_diagonal_coupling(str(diagonal))
        theory.define_coupling(
            name,
            indices=_entry_expressions(entry, "indices_input_form", theory),
            eft_order=int(entry.get("eft_order", 0)),
            mass_dimension=_entry_mass_dimension(entry, dimensions),
            self_conjugate=_parse_self_conjugate(str(entry.get("self_conjugate_input_form", "False"))),
            symmetries=_parse_symmetries(str(entry.get("symmetries_input_form", "{}")), theory, warnings, name),
            diagonal=diagonal_flags,
            thermal_power_counting=int(entry.get("thermal_power_counting", 1)),
            unitary=bool(entry.get("unitary", False)),
        )

    for entry in data.get("fields", []):
        name = _entry_name(entry)
        if name in theory.fields:
            continue
        type_expr = _field_type_for_entry(entry, theory)
        role = _field_role_for_entry(entry, type_expr)
        theory.define_field(
            name,
            type_expr,
            indices=_entry_expressions(entry, "indices_input_form", theory),
            charges=_entry_expressions(entry, "charges_input_form", theory),
            chirality=_parse_chirality(str(entry.get("chirality_input_form", "False"))),
            field_role=role,
            propagating=bool(entry.get("propagating", role is not FieldRole.BACKGROUND)),
            zero_mode=bool(entry.get("zero_mode", False)),
            self_conjugate=bool(entry.get("self_conjugate", False)),
            mass=_mass_spec(entry, couplings, theory),
        )

    for entry in data.get("cg_tensors", []):
        name = _clean_name(str(entry["name_input_form"]))
        try:
            representations = _entry_expressions(entry, "representations_input_form", theory)
            if name not in theory.cg_tensors:
                source = str(entry.get("tensor_input_form") or "matchete_exported_tensor")
                tensor: Expression | None = None
                try:
                    tensor = _sparse_array_components(source, theory)
                except Exception as exc:  # noqa: BLE001 - keep raw Matchete source if sparse decoding is incomplete.
                    warnings.append(
                        f"Kept CG tensor {entry['name_input_form']} source only; could not decode SparseArray: {exc}"
                    )
                theory.define_cg_tensor(name, representations, tensor=tensor, source=source)
        except Exception as exc:  # noqa: BLE001 - development converter records unsupported Matchete metadata.
            warnings.append(f"Skipped CG tensor {entry['name_input_form']}: {exc}")

    return theory


def _infer_coupling_dimensions_from_lagrangian(data: dict[str, Any], model_name: str) -> dict[str, int | float]:
    if not data.get("lagrangian_input_form"):
        return {}
    probe_name = f"{model_name}_dimension_probe_{next(_DIMENSION_PROBE_COUNTER)}"
    probe_warnings: list[str] = []
    probe_theory = _build_theory_from_model_state(
        data,
        model_name=model_name,
        theory_name=probe_name,
        warnings=probe_warnings,
    )
    lagrangian = parse_matchete_expression(str(data["lagrangian_input_form"]), probe_theory)
    return infer_coupling_mass_dimensions(probe_theory, lagrangian)


def build_fixture_from_model_state(data: dict[str, Any], *, include_lagrangian: bool = True) -> tuple[dict[str, Any], list[str]]:
    if data.get("kind") != "matchete_loaded_model_state":
        raise ValueError("expected kind='matchete_loaded_model_state'")
    if int(data.get("schema_version", 0)) != 1:
        raise ValueError("only matchete_loaded_model_state schema_version=1 is supported")

    warnings: list[str] = []
    model_name = _clean_name(str(data["model"]))
    inferred_dimensions = _infer_coupling_dimensions_from_lagrangian(data, model_name) if include_lagrangian else {}
    theory = _build_theory_from_model_state(
        data,
        model_name=model_name,
        warnings=warnings,
        coupling_dimensions=inferred_dimensions,
    )

    state = PycheteState()
    state.add_theory(theory)
    expressions: list[str] = []
    if include_lagrangian and data.get("lagrangian_input_form"):
        state.add_expression("lagrangian", theory, parse_matchete_expression(str(data["lagrangian_input_form"]), theory))
        expressions.append("lagrangian")

    fixture = {
        "schema_version": 1,
        "name": f"{model_name}_model_definition",
        "kind": "model_definition",
        "source": {
            "generator": "helper_mathematica_scripts/convert_matchete_model_state.py",
            "upstream_generator": data.get("generator"),
            "matchete_runtime_required": False,
            "model": str(data["model"]),
            "warnings": warnings,
        },
        "state": state.to_json_obj(),
        "expressions": expressions,
    }
    return fixture, warnings


def _convert_file(path: Path, out_dir: Path, *, include_lagrangian: bool) -> Path:
    data = json.loads(path.read_text(encoding="utf-8"))
    fixture, warnings = build_fixture_from_model_state(data, include_lagrangian=include_lagrangian)
    model = _clean_name(str(data["model"]))
    out_path = out_dir / f"{model}.model_fixture.json"
    out_path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    for warning in warnings:
        print(f"warning: {warning}")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="RawJSON files from export_matchete_model_state.wls")
    parser.add_argument("--fixtures-dir", type=Path, default=Path("assets/validation/pychete"))
    parser.add_argument("--no-lagrangian", action="store_true", help="Convert metadata only and skip lagrangian parsing")
    args = parser.parse_args()

    args.fixtures_dir.mkdir(parents=True, exist_ok=True)
    for path in args.inputs:
        _convert_file(path, args.fixtures_dir, include_lagrangian=not args.no_lagrangian)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
