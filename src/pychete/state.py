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
