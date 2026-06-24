from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from symbolica import Expression

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
        return cls(
            name=str(obj["name"]),
            kind=str(obj.get("kind", "validation")),
            state=state,
            source=source,
            expression_names=tuple(raw_expression_names),
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
