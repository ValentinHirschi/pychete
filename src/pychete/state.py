from __future__ import annotations

import json
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

from symbolica import Expression

from .symbols import canonical_string
from .theory import Theory


@dataclass(frozen=True)
class StateExpression:
    """Named expression stored with the theory that validates it."""

    theory_name: str
    expression: Expression

    def to_json(self) -> dict[str, str]:
        """Return a JSON-serializable representation of this expression."""

        return {
            "theory": self.theory_name,
            "expression": canonical_string(self.expression),
        }


@dataclass
class PycheteState:
    """Checkpoint container for theories and named expressions.

    Theories hold metadata only. Lagrangians and other expressions are stored
    separately under names and point back to the theory that validates their
    symbols.
    """

    theories: dict[str, Theory] = field(default_factory=dict)
    expressions: dict[str, StateExpression] = field(default_factory=dict)
    active_theory: str | None = None
    schema_version: int = 3

    def add_theory(self, theory: Theory, *, active: bool = True) -> Theory:
        """Add a theory to the state and optionally make it active."""

        self.theories[theory.name] = theory
        if active or self.active_theory is None:
            self.active_theory = theory.name
        return theory

    def add_expression(self, name: str, theory: Theory | str, expression: Expression) -> Expression:
        """Store a named expression associated with a theory.

        The expression is validated against the associated theory before it is
        accepted.
        """

        theory_name = theory.name if isinstance(theory, Theory) else theory
        if theory_name not in self.theories:
            raise ValueError(f"Cannot store expression {name!r}: unknown theory {theory_name!r}")
        self.theories[theory_name]._validate_registered_expression(expression)
        self.expressions[name] = StateExpression(theory_name=theory_name, expression=expression)
        return expression

    def get_expression(self, name: str) -> Expression:
        """Return a named expression from the state."""

        return self.expressions[name].expression

    def to_json_obj(self) -> dict[str, Any]:
        """Return a JSON-serializable state checkpoint."""

        return {
            "schema_version": self.schema_version,
            "active_theory": self.active_theory,
            "theories": {
                name: theory.to_json_obj()
                for name, theory in sorted(self.theories.items())
            },
            "expressions": {
                name: state_expression.to_json()
                for name, state_expression in sorted(self.expressions.items())
            },
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize the state checkpoint to a JSON string."""

        return json.dumps(self.to_json_obj(), indent=indent, sort_keys=True) + "\n"

    def write_json(self, path: str | Path) -> None:
        """Write the state checkpoint JSON to ``path``."""

        Path(path).write_text(self.to_json(), encoding="utf-8")

    def save_state(self, path: str | Path) -> None:
        """Alias for ``write_json``."""

        self.write_json(path)

    def _repr_latex_(self) -> str:
        active = "" if self.active_theory is None else rf",\ active={self.active_theory}"
        return rf"$\mathrm{{PycheteState}}\left(n={len(self.theories)},\ e={len(self.expressions)}{active}\right)$"

    def _repr_html_(self) -> str:
        active = "" if self.active_theory is None else f" active={escape(self.active_theory)}"
        return f"<code>PycheteState(n={len(self.theories)} expressions={len(self.expressions)}{active})</code>"

    @property
    def active(self) -> Theory | None:
        """The active theory, if one is selected."""

        if self.active_theory is None:
            return None
        return self.theories[self.active_theory]

    @classmethod
    def from_json_obj(cls, obj: dict[str, Any]) -> PycheteState:
        """Restore a state checkpoint from a JSON object."""

        state = cls(schema_version=int(obj.get("schema_version", 1)))
        state.theories = {
            name: Theory.from_json_obj(theory_obj)
            for name, theory_obj in obj.get("theories", {}).items()
        }
        for name, expression_obj in obj.get("expressions", {}).items():
            if not isinstance(expression_obj, dict):
                raise ValueError(f"Expression entry {name!r} is not a JSON object")
            theory_name = str(expression_obj["theory"])
            if theory_name not in state.theories:
                raise ValueError(f"Expression {name!r} references unknown theory {theory_name!r}")
            expression = state.theories[theory_name]._parse_registered_expression(str(expression_obj["expression"]))
            state.expressions[str(name)] = StateExpression(theory_name=theory_name, expression=expression)
        active_theory = obj.get("active_theory")
        state.active_theory = str(active_theory) if active_theory is not None else None
        return state

    @classmethod
    def from_json(cls, text: str) -> PycheteState:
        """Restore a state checkpoint from a JSON string."""

        return cls.from_json_obj(json.loads(text))

    @classmethod
    def read_json(cls, path: str | Path) -> PycheteState:
        """Read a state checkpoint from a JSON file."""

        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def load_state(path: str | Path) -> PycheteState:
    """Load a pychete state checkpoint from ``path``."""

    return PycheteState.read_json(path)
