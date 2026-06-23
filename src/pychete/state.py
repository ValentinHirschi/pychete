from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .theory import Theory


@dataclass
class PycheteState:
    theories: dict[str, Theory] = field(default_factory=dict)
    active_theory: str | None = None
    schema_version: int = 1

    def add_theory(self, theory: Theory, *, active: bool = True) -> Theory:
        self.theories[theory.name] = theory
        if active or self.active_theory is None:
            self.active_theory = theory.name
        return theory

    def to_json_obj(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "active_theory": self.active_theory,
            "theories": {
                name: theory.to_json_obj()
                for name, theory in sorted(self.theories.items())
            },
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_json_obj(), indent=indent, sort_keys=True) + "\n"

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    def save_state(self, path: str | Path) -> None:
        self.write_json(path)

    @property
    def active(self) -> Theory | None:
        if self.active_theory is None:
            return None
        return self.theories[self.active_theory]

    @classmethod
    def from_json_obj(cls, obj: dict[str, Any]) -> PycheteState:
        state = cls(schema_version=int(obj.get("schema_version", 1)))
        state.theories = {
            name: Theory.from_json_obj(theory_obj)
            for name, theory_obj in obj.get("theories", {}).items()
        }
        active_theory = obj.get("active_theory")
        state.active_theory = str(active_theory) if active_theory is not None else None
        return state

    @classmethod
    def from_json(cls, text: str) -> PycheteState:
        return cls.from_json_obj(json.loads(text))

    @classmethod
    def read_json(cls, path: str | Path) -> PycheteState:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def load_state(path: str | Path) -> PycheteState:
    return PycheteState.read_json(path)
