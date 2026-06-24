from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from symbolica import Expression

from .matching import MatchingResult
from .state import PycheteState
from .theory import Theory


@dataclass(frozen=True)
class ValidationFixture:
    """Mathematica-independent validation fixture loaded from repo assets."""

    name: str
    kind: str
    state: PycheteState
    source: dict[str, Any]
    expression_names: tuple[str, ...]
    matching_result_specs: dict[str, dict[str, Any]] = field(default_factory=dict)
    schema_version: int = 1

    def theory(self, name: str | None = None) -> Theory:
        """Return the requested theory, or the active fixture theory."""

        if name is not None:
            return self.state.theories[name]
        active = self.state.active
        if active is None:
            raise ValueError(f"Validation fixture {self.name!r} has no active theory")
        return active

    def expression(self, name: str) -> Expression:
        """Return a named validation expression."""

        if name not in self.expression_names:
            raise KeyError(f"Validation fixture {self.name!r} has no expression {name!r}")
        return self.state.get_expression(name)

    def matching_result(self, name: str = "default") -> MatchingResult:
        """Return a structured matching result described by this fixture."""

        if name not in self.matching_result_specs:
            raise KeyError(f"Validation fixture {self.name!r} has no matching result {name!r}")
        spec = self.matching_result_specs[name]
        theory = self.theory(str(spec.get("theory"))) if spec.get("theory") is not None else self.theory()
        return MatchingResult(
            theory=theory,
            uv_lagrangian=self.expression(str(spec["uv_lagrangian"])),
            off_shell_eft_lagrangian=self.expression(str(spec["off_shell_eft_lagrangian"])),
            on_shell_eft_lagrangian=self.expression(str(spec["on_shell_eft_lagrangian"])),
            matching_conditions=_expression_map(self, spec.get("matching_conditions", {}), "matching_conditions"),
            fluctuation_operators=_expression_map(self, spec.get("fluctuation_operators", {}), "fluctuation_operators"),
            supertraces=_expression_map(self, spec.get("supertraces", {}), "supertraces"),
            metadata=_metadata(spec.get("metadata", {})),
        )

    @classmethod
    def from_json_obj(cls, obj: dict[str, Any]) -> ValidationFixture:
        """Restore a validation fixture from a JSON object."""

        schema_version = int(obj.get("schema_version", 1))
        if schema_version != 1:
            raise ValueError(f"Unsupported validation fixture schema version {schema_version}")
        state_obj = obj.get("state")
        if not isinstance(state_obj, dict):
            raise ValueError("Validation fixture must contain a state object")
        state = PycheteState.from_json_obj(state_obj)
        raw_expression_names = obj.get("expressions", sorted(state.expressions))
        if not isinstance(raw_expression_names, list) or not all(isinstance(name, str) for name in raw_expression_names):
            raise ValueError("Validation fixture expressions must be a list of names")
        missing = sorted(set(raw_expression_names).difference(state.expressions))
        if missing:
            raise ValueError(f"Validation fixture references missing expressions: {missing}")
        source = obj.get("source", {})
        if not isinstance(source, dict):
            raise ValueError("Validation fixture source metadata must be an object")
        matching_result_specs = _matching_result_specs(obj.get("matching_results", {}), set(state.expressions))
        return cls(
            name=str(obj["name"]),
            kind=str(obj.get("kind", "validation")),
            state=state,
            source=source,
            expression_names=tuple(raw_expression_names),
            matching_result_specs=matching_result_specs,
            schema_version=schema_version,
        )

    @classmethod
    def from_json(cls, text: str) -> ValidationFixture:
        """Restore a validation fixture from a JSON string."""

        return cls.from_json_obj(json.loads(text))

    @classmethod
    def read_json(cls, path: str | Path) -> ValidationFixture:
        """Read a validation fixture from a JSON file."""

        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def load_validation_fixture(path: str | Path) -> ValidationFixture:
    """Load a Mathematica-independent pychete validation fixture."""

    return ValidationFixture.read_json(path)


def _metadata(value: Any) -> dict[str, str | int | float | bool | None]:
    if not isinstance(value, dict):
        raise ValueError("Matching result metadata must be an object")
    out: dict[str, str | int | float | bool | None] = {}
    for key, item in value.items():
        if item is None or isinstance(item, (str, int, float, bool)):
            out[str(key)] = item
        else:
            raise ValueError(f"Matching result metadata value for {key!r} is not JSON-scalar")
    return out


def _expression_map(fixture: ValidationFixture, value: Any, section: str) -> dict[str, Expression]:
    if not isinstance(value, dict):
        raise ValueError(f"Matching result {section} must be an object")
    return {str(label): fixture.expression(str(expression_name)) for label, expression_name in value.items()}


def _matching_result_specs(value: Any, expression_names: set[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        raise ValueError("Validation fixture matching_results must be an object")
    out: dict[str, dict[str, Any]] = {}
    for result_name, raw_spec in value.items():
        if not isinstance(raw_spec, dict):
            raise ValueError(f"Matching result {result_name!r} must be an object")
        spec = dict(raw_spec)
        for required in ("uv_lagrangian", "off_shell_eft_lagrangian", "on_shell_eft_lagrangian"):
            if required not in spec:
                raise ValueError(f"Matching result {result_name!r} is missing {required!r}")
            expression_name = str(spec[required])
            if expression_name not in expression_names:
                raise ValueError(f"Matching result {result_name!r} references missing expression {expression_name!r}")
        for section in ("matching_conditions", "fluctuation_operators", "supertraces"):
            raw_section = spec.get(section, {})
            if not isinstance(raw_section, dict):
                raise ValueError(f"Matching result {result_name!r} {section} must be an object")
            for expression_name in raw_section.values():
                if str(expression_name) not in expression_names:
                    raise ValueError(f"Matching result {result_name!r} references missing expression {expression_name!r}")
        out[str(result_name)] = spec
    return out
