from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

from symbolica import Expression

from .expr import list_expr
from .symbols import canonical_string, expression_from_canonical, s, safe_symbol_name

FieldKind = Literal["heavy", "light", "massless"]


@dataclass(frozen=True)
class IndexType:
    name: str
    symbol: Expression
    dimension: int | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "symbol": canonical_string(self.symbol),
            "dimension": self.dimension,
        }


@dataclass(frozen=True)
class CouplingDefinition:
    name: str
    label: Expression
    indices: tuple[Expression, ...] = ()
    eft_order: int = 0
    self_conjugate: bool = False

    def expr(self, *indices: Expression) -> Expression:
        if not indices:
            indices = ()
        return s.Coupling(self.label, list_expr(*indices), self.eft_order)

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": canonical_string(self.label),
            "indices": [canonical_string(i) for i in self.indices],
            "eft_order": self.eft_order,
            "self_conjugate": self.self_conjugate,
        }


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    label: Expression
    type: Expression
    indices: tuple[Expression, ...] = ()
    self_conjugate: bool = False
    mass_kind: FieldKind = "massless"
    mass_label: Expression | None = None
    mass_indices: tuple[Expression, ...] = ()

    @property
    def heavy(self) -> bool:
        return self.mass_kind == "heavy"

    def expr(self, *indices: Expression, derivatives: Iterable[Expression] = ()) -> Expression:
        return s.Field(self.label, self.type, list_expr(*indices), list_expr(*tuple(derivatives)))

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": canonical_string(self.label),
            "type": canonical_string(self.type),
            "indices": [canonical_string(i) for i in self.indices],
            "self_conjugate": self.self_conjugate,
            "mass_kind": self.mass_kind,
            "mass_label": canonical_string(self.mass_label) if self.mass_label is not None else None,
            "mass_indices": [canonical_string(i) for i in self.mass_indices],
        }


@dataclass
class AnalysisState:
    lagrangian: Expression | None = None
    eoms: dict[str, Expression] = field(default_factory=dict)
    heavy_scalar_solutions: dict[str, dict[int, Expression]] = field(default_factory=dict)


class FieldHandle:
    def __init__(self, theory: Theory, definition: FieldDefinition) -> None:
        self.theory = theory
        self.definition = definition

    @property
    def label(self) -> Expression:
        return self.definition.label

    @property
    def name(self) -> str:
        return self.definition.name

    def __call__(self, *indices: Expression, derivatives: Iterable[Expression] = ()) -> Expression:
        return self.definition.expr(*indices, derivatives=derivatives)


class CouplingHandle:
    def __init__(self, theory: Theory, definition: CouplingDefinition) -> None:
        self.theory = theory
        self.definition = definition

    @property
    def label(self) -> Expression:
        return self.definition.label

    @property
    def name(self) -> str:
        return self.definition.name

    def __call__(self, *indices: Expression) -> Expression:
        return self.definition.expr(*indices)


class Theory:
    """Stateful top-level object for pychete definitions and current Lagrangian."""

    schema_version = 1

    def __init__(self, name: str) -> None:
        self.name = safe_symbol_name(name)
        self._symbols: dict[str, Expression] = {}
        self.index_types: dict[str, IndexType] = {}
        self.fields: dict[str, FieldDefinition] = {}
        self.couplings: dict[str, CouplingDefinition] = {}
        self.groups: dict[str, dict[str, Any]] = {}
        self.lagrangian: Expression | None = None
        self.analysis = AnalysisState()
        self.define_index_type("Lorentz")

    def symbol(self, name: str, *, role: str = "label") -> Expression:
        key = f"{role}:{name}"
        if key not in self._symbols:
            symbol_name = f"{safe_symbol_name(role)}_{safe_symbol_name(name)}"
            self._symbols[key] = s.user(
                self.name,
                symbol_name,
                tags=["pychete", role],
                data={"theory": self.name, "role": role, "label": name},
            )
        return self._symbols[key]

    def define_index_type(self, name: str, dimension: int | None = None) -> IndexType:
        if name in self.index_types:
            return self.index_types[name]
        sym = s.Lorentz if name == "Lorentz" else self.symbol(name, role="index_type")
        index_type = IndexType(name=name, symbol=sym, dimension=dimension)
        self.index_types[name] = index_type
        return index_type

    def define_flavor_index(self, name: str = "Flavor", dimension: int | None = None) -> IndexType:
        return self.define_index_type(name, dimension)

    def index(self, label: str | Expression, representation: str | Expression = "Lorentz") -> Expression:
        label_expr = label if isinstance(label, Expression) else self.symbol(label, role="index")
        if isinstance(representation, Expression):
            rep_expr = representation
        else:
            rep_expr = self.define_index_type(representation).symbol
        return s.Index(label_expr, rep_expr)

    def lorentz_index(self, label: str) -> Expression:
        return self.index(label, s.Lorentz)

    def define_coupling(
        self,
        name: str,
        *,
        indices: Iterable[Expression] = (),
        eft_order: int = 0,
        self_conjugate: bool = False,
    ) -> CouplingHandle:
        if name in self.couplings:
            return CouplingHandle(self, self.couplings[name])
        label = self.symbol(name, role="coupling")
        definition = CouplingDefinition(
            name=name,
            label=label,
            indices=tuple(indices),
            eft_order=eft_order,
            self_conjugate=self_conjugate,
        )
        self.couplings[name] = definition
        return CouplingHandle(self, definition)

    def define_field(
        self,
        name: str,
        type_expr: Expression,
        *,
        indices: Iterable[Expression] = (),
        self_conjugate: bool = False,
        mass: int | tuple[str, str] | tuple[str, str, Iterable[Expression]] | None = None,
    ) -> FieldHandle:
        if name in self.fields:
            return FieldHandle(self, self.fields[name])

        mass_kind: FieldKind = "massless"
        mass_label: Expression | None = None
        mass_indices: tuple[Expression, ...] = ()
        if mass not in (None, 0):
            if not isinstance(mass, tuple) or len(mass) < 2:
                raise ValueError("mass must be 0/None or ('Heavy'|'Light', label[, indices])")
            kind = str(mass[0]).lower()
            if kind not in {"heavy", "light"}:
                raise ValueError(f"unsupported mass kind {mass[0]!r}")
            mass_kind = "heavy" if kind == "heavy" else "light"
            mass_name = mass[1]
            mass_indices = tuple(mass[2]) if len(mass) > 2 else ()
            order = 0 if mass_kind == "heavy" else 1
            mass_handle = self.define_coupling(
                str(mass_name),
                indices=mass_indices,
                eft_order=order,
                self_conjugate=True,
            )
            mass_label = mass_handle.label

        definition = FieldDefinition(
            name=name,
            label=self.symbol(name, role="field"),
            type=type_expr,
            indices=tuple(indices),
            self_conjugate=self_conjugate,
            mass_kind=mass_kind,
            mass_label=mass_label,
            mass_indices=mass_indices,
        )
        self.fields[name] = definition
        self.analysis = AnalysisState()
        return FieldHandle(self, definition)

    def field_handle(self, name: str) -> FieldHandle:
        return FieldHandle(self, self.fields[name])

    def coupling_handle(self, name: str) -> CouplingHandle:
        return CouplingHandle(self, self.couplings[name])

    def define_gauge_group(self, name: str, group_type: Expression, coupling: str, field: str) -> None:
        coupling_handle = self.define_coupling(coupling, eft_order=0, self_conjugate=True)
        vector = self.define_field(field, s.Vector(self.symbol(name, role="group")), self_conjugate=True, mass=0)
        self.groups[name] = {
            "name": name,
            "type": canonical_string(group_type),
            "coupling": coupling_handle.name,
            "field": vector.name,
        }

    def mass_expr(self, field_def: FieldDefinition) -> Expression | None:
        if field_def.mass_label is None:
            return None
        return s.Coupling(field_def.mass_label, list_expr(), 0 if field_def.heavy else 1)

    def free_lag(self, *field_names_or_handles: str | FieldHandle) -> Expression:
        out = s.zero
        for item in field_names_or_handles:
            handle = item if isinstance(item, FieldHandle) else self.field_handle(item)
            definition = handle.definition
            mu = self.lorentz_index("d")
            field_expr = handle()
            if canonical_string(definition.type) == canonical_string(s.Scalar):
                mass = self.mass_expr(definition)
                if definition.self_conjugate:
                    kinetic = s.half * handle(derivatives=[mu]) ** 2
                    if mass is not None:
                        kinetic = kinetic - s.half * mass**2 * field_expr**2
                else:
                    kinetic = s.Bar(handle(derivatives=[mu])) * handle(derivatives=[mu])
                    if mass is not None:
                        kinetic = kinetic - mass**2 * s.Bar(field_expr) * field_expr
                out = out + kinetic
            elif canonical_string(definition.type).startswith(canonical_string(s.Vector)):
                nu = self.lorentz_index("e")
                strength = s.FieldStrength(definition.label, list_expr(mu, nu), list_expr(), list_expr())
                out = out - s.twenty_fourth * 6 * strength**2
            elif canonical_string(definition.type) == canonical_string(s.Fermion):
                mass = self.mass_expr(definition)
                dirac = s.I * s.NCM(s.Bar(field_expr), s.Gamma(mu), handle(derivatives=[mu]))
                if mass is not None:
                    dirac = dirac - mass * s.NCM(s.Bar(field_expr), field_expr)
                out = out + dirac
            else:
                out = out + s.head("FreeLag")(definition.label)
        return out

    def set_lagrangian(self, lagrangian: Expression) -> Expression:
        self.lagrangian = lagrangian.expand()
        self.analysis = AnalysisState(lagrangian=self.lagrangian)
        return self.lagrangian

    def to_json_obj(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "theory_name": self.name,
            "index_types": {name: value.to_json() for name, value in sorted(self.index_types.items())},
            "groups": self.groups,
            "fields": {name: value.to_json() for name, value in sorted(self.fields.items())},
            "couplings": {name: value.to_json() for name, value in sorted(self.couplings.items())},
            "lagrangian": canonical_string(self.lagrangian) if self.lagrangian is not None else None,
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_json_obj(), indent=indent, sort_keys=True) + "\n"

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_json_obj(cls, obj: dict[str, Any]) -> Theory:
        theory = cls(obj["theory_name"])
        for name, data in obj.get("index_types", {}).items():
            if name != "Lorentz":
                theory.define_index_type(name, data.get("dimension"))
        for name, data in obj.get("couplings", {}).items():
            theory.define_coupling(
                name,
                indices=[expression_from_canonical(x) for x in data.get("indices", [])],
                eft_order=int(data.get("eft_order", 0)),
                self_conjugate=bool(data.get("self_conjugate", False)),
            )
        for name, data in obj.get("fields", {}).items():
            mass_label = data.get("mass_label")
            mass = None
            if mass_label is not None:
                mass = ("Heavy" if data.get("mass_kind") == "heavy" else "Light", name + "_mass")
            theory.define_field(
                name,
                expression_from_canonical(data["type"]),
                indices=[expression_from_canonical(x) for x in data.get("indices", [])],
                self_conjugate=bool(data.get("self_conjugate", False)),
                mass=mass,
            )
        if obj.get("lagrangian"):
            theory.set_lagrangian(expression_from_canonical(obj["lagrangian"]))
        return theory
