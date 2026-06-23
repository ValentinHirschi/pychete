from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from html import escape
from pathlib import Path
from typing import Any, Iterable, TypeAlias

from symbolica import Expression

from .expr import is_head, list_expr
from .symbols import SymbolDataKey, SymbolRole, canonical_string, display_string, expression_from_canonical, latex_string, s, safe_symbol_name, symbol_data


class FieldMassKind(StrEnum):
    HEAVY = "heavy"
    LIGHT = "light"
    MASSLESS = "massless"

    @classmethod
    def from_user(cls, value: FieldMassKind | str) -> FieldMassKind:
        normalized = str(value).lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"unsupported mass kind {value!r}") from exc


class BuiltinIndexType(StrEnum):
    LORENTZ = "Lorentz"
    FLAVOR = "Flavor"


MassKindInput: TypeAlias = FieldMassKind | str
MassSpec: TypeAlias = tuple[MassKindInput, str] | tuple[MassKindInput, str, Iterable[Expression]]
JsonValue: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None

_EXPRESSION_DATA_KEY = "__pychete_expression__"
_SYMBOL_ROLE_ORDER = {
    SymbolRole.INDEX_TYPE.value: 0,
    SymbolRole.GROUP.value: 1,
    SymbolRole.INDEX.value: 2,
    SymbolRole.COUPLING.value: 3,
    SymbolRole.FIELD.value: 4,
    SymbolRole.EXTERNAL.value: 5,
    SymbolRole.LABEL.value: 6,
}


def _index_type_name(name: BuiltinIndexType | str) -> str:
    return name.value if isinstance(name, BuiltinIndexType) else name


def _encode_symbol_data_value(value: Any) -> JsonValue:
    if isinstance(value, Expression):
        return {_EXPRESSION_DATA_KEY: canonical_string(value)}
    if isinstance(value, list):
        return [_encode_symbol_data_value(item) for item in value]
    if isinstance(value, tuple):
        return [_encode_symbol_data_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _encode_symbol_data_value(item) for key, item in value.items()}
    if isinstance(value, StrEnum):
        return value.value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Cannot serialize Symbolica symbol data value {value!r}")


def _decode_symbol_data_value(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {_EXPRESSION_DATA_KEY}:
            return expression_from_canonical(str(value[_EXPRESSION_DATA_KEY]))
        return {str(key): _decode_symbol_data_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode_symbol_data_value(item) for item in value]
    return value


def _symbol_data_payload(label: Expression) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {}
    for key in SymbolDataKey:
        try:
            payload[key.value] = _encode_symbol_data_value(label.get_symbol_data(key.value))
        except KeyError:
            continue
    return payload


def _symbol_manifest_sort_key(entry: dict[str, Any]) -> tuple[int, str, str]:
    role = str(entry.get("role", ""))
    return (_SYMBOL_ROLE_ORDER.get(role, 100), role, str(entry.get("name", "")))


def field_mass_kind_from_label(label: Expression) -> FieldMassKind:
    value = symbol_data(label, SymbolDataKey.MASS_KIND, FieldMassKind.MASSLESS.value)
    return FieldMassKind.from_user(str(value))


def field_type_from_label(label: Expression) -> Expression:
    value = symbol_data(label, SymbolDataKey.FIELD_TYPE)
    if not isinstance(value, Expression):
        raise ValueError(f"Field type is not stored on {canonical_string(label)}")
    return value


def field_self_conjugate_from_label(label: Expression) -> bool:
    return bool(symbol_data(label, SymbolDataKey.SELF_CONJUGATE, 0))


def _expression_list_from_symbol_data(label: Expression, key: SymbolDataKey) -> tuple[Expression, ...]:
    value = symbol_data(label, key, [])
    if not isinstance(value, list):
        raise ValueError(f"{key.value} is not stored as a list on {canonical_string(label)}")
    if not all(isinstance(item, Expression) for item in value):
        raise ValueError(f"{key.value} contains non-expression entries on {canonical_string(label)}")
    return tuple(value)


def field_indices_from_label(label: Expression) -> tuple[Expression, ...]:
    return _expression_list_from_symbol_data(label, SymbolDataKey.INDICES)


def field_mass_indices_from_label(label: Expression) -> tuple[Expression, ...]:
    return _expression_list_from_symbol_data(label, SymbolDataKey.MASS_INDICES)


def field_mass_label_from_label(label: Expression) -> Expression | None:
    value = symbol_data(label, SymbolDataKey.MASS_LABEL)
    if value is None:
        return None
    if not isinstance(value, Expression):
        raise ValueError(f"Field mass label is not stored as an expression on {canonical_string(label)}")
    return value


def field_mass_expr_from_label(label: Expression) -> Expression | None:
    mass_label = field_mass_label_from_label(label)
    if mass_label is None:
        return None
    order = 0 if field_mass_kind_from_label(label) is FieldMassKind.HEAVY else 1
    return s.Coupling(mass_label, list_expr(*field_mass_indices_from_label(label)), order)


def coupling_eft_order_from_label(label: Expression) -> int:
    return int(symbol_data(label, SymbolDataKey.EFT_ORDER, 0))


def coupling_self_conjugate_from_label(label: Expression) -> bool:
    return bool(symbol_data(label, SymbolDataKey.SELF_CONJUGATE, 0))


def coupling_indices_from_label(label: Expression) -> tuple[Expression, ...]:
    return _expression_list_from_symbol_data(label, SymbolDataKey.INDICES)


def _coupling_name_for_label(theory: Theory, label_text: str) -> str:
    for definition in theory.couplings.values():
        if canonical_string(definition.label) == label_text:
            return definition.name
    label = expression_from_canonical(label_text)
    name = label.get_name().split("::")[-1]
    prefix = f"{SymbolRole.COUPLING.value}_"
    return name.removeprefix(prefix)


@dataclass(frozen=True)
class IndexType:
    name: str
    symbol: Expression
    dimension: int | None = None

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{IndexType}}\left({latex_string(self.symbol)}\right)$"

    def _repr_html_(self) -> str:
        dim = "" if self.dimension is None else f" dimension={escape(str(self.dimension))}"
        return f"<code>IndexType({escape(display_string(self.symbol))}{dim})</code>"

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
        return s.Coupling(self.label, list_expr(*indices), coupling_eft_order_from_label(self.label))

    def _repr_latex_(self) -> str:
        return f"${latex_string(self.expr())}$"

    def _repr_html_(self) -> str:
        return f"<code>{escape(display_string(self.expr()))}</code>"

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": canonical_string(self.label),
            "indices": [canonical_string(i) for i in coupling_indices_from_label(self.label)],
            "eft_order": coupling_eft_order_from_label(self.label),
            "self_conjugate": coupling_self_conjugate_from_label(self.label),
        }


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    label: Expression
    type: Expression
    indices: tuple[Expression, ...] = ()
    self_conjugate: bool = False
    mass_kind: FieldMassKind = FieldMassKind.MASSLESS
    mass_label: Expression | None = None
    mass_indices: tuple[Expression, ...] = ()

    @property
    def heavy(self) -> bool:
        return field_mass_kind_from_label(self.label) is FieldMassKind.HEAVY

    @property
    def type_expr(self) -> Expression:
        return field_type_from_label(self.label)

    @property
    def is_self_conjugate(self) -> bool:
        return field_self_conjugate_from_label(self.label)

    def expr(self, *indices: Expression, derivatives: Iterable[Expression] = ()) -> Expression:
        return s.Field(self.label, self.type_expr, list_expr(*indices), list_expr(*tuple(derivatives)))

    def mass_expr(self) -> Expression | None:
        return field_mass_expr_from_label(self.label)

    def _repr_latex_(self) -> str:
        return f"${latex_string(self.expr())}$"

    def _repr_html_(self) -> str:
        mass = self.mass_expr()
        mass_part = "" if mass is None else f" mass={escape(display_string(mass))}"
        return f"<code>{escape(display_string(self.expr()))}{mass_part}</code>"

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": canonical_string(self.label),
            "type": canonical_string(self.type_expr),
            "indices": [canonical_string(i) for i in field_indices_from_label(self.label)],
            "self_conjugate": self.is_self_conjugate,
            "mass_kind": field_mass_kind_from_label(self.label).value,
            "mass_label": canonical_string(mass_label) if (mass_label := field_mass_label_from_label(self.label)) is not None else None,
            "mass_indices": [canonical_string(i) for i in field_mass_indices_from_label(self.label)],
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

    def _repr_latex_(self) -> str:
        return self.definition._repr_latex_()

    def _repr_html_(self) -> str:
        return self.definition._repr_html_()


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

    def _repr_latex_(self) -> str:
        return self.definition._repr_latex_()

    def _repr_html_(self) -> str:
        return self.definition._repr_html_()


class Theory:
    """Stateful top-level object for pychete definitions and current Lagrangian."""

    schema_version = 2

    def __init__(self, name: str) -> None:
        s.register_builtins()
        self.name = safe_symbol_name(name)
        self._symbols: dict[str, Expression] = {}
        self.index_types: dict[str, IndexType] = {}
        self.fields: dict[str, FieldDefinition] = {}
        self.couplings: dict[str, CouplingDefinition] = {}
        self.groups: dict[str, dict[str, Any]] = {}
        self.lagrangian: Expression | None = None
        self.analysis = AnalysisState()
        self.define_index_type(BuiltinIndexType.LORENTZ)

    def symbol(self, name: str, *, role: SymbolRole | str = SymbolRole.LABEL, data: dict[str, Any] | None = None) -> Expression:
        role_name = role.value if isinstance(role, SymbolRole) else role
        key = f"{role_name}:{name}"
        if key not in self._symbols:
            symbol_name = f"{safe_symbol_name(role_name)}_{safe_symbol_name(name)}"
            symbol_data_payload: dict[str, Any] = {
                SymbolDataKey.THEORY.value: self.name,
                SymbolDataKey.ROLE.value: role_name,
                SymbolDataKey.LABEL.value: name,
            }
            if data:
                symbol_data_payload.update(data)
            self._symbols[key] = s.user(
                self.name,
                symbol_name,
                tags=[SymbolRole.PROJECT.value, role_name],
                data=symbol_data_payload,
            )
        return self._symbols[key]

    def symbol_manifest(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for key, expr in self._symbols.items():
            role_name, name = key.split(":", 1)
            entries.append(
                {
                    "name": name,
                    "role": role_name,
                    "symbol": canonical_string(expr),
                    "tags": expr.get_tags(),
                    "data": _symbol_data_payload(expr),
                }
            )
        return sorted(entries, key=_symbol_manifest_sort_key)

    def _restore_symbol_manifest(self, entries: Iterable[dict[str, Any]]) -> None:
        s.register_builtins()
        for entry in sorted(entries, key=_symbol_manifest_sort_key):
            name = str(entry["name"])
            role = str(entry["role"])
            raw_data = entry.get("data", {})
            if not isinstance(raw_data, dict):
                raise ValueError(f"Symbol manifest entry for {role}:{name} has non-object data")
            data = _decode_symbol_data_value(raw_data)
            symbol = self.symbol(name, role=role, data=data)
            expected = entry.get("symbol")
            if expected is not None and canonical_string(symbol) != expected:
                raise ValueError(f"Symbol manifest restored {role}:{name} as {canonical_string(symbol)}, expected {expected}")
            expected_tags = set(str(tag) for tag in entry.get("tags", []))
            actual_tags = set(symbol.get_tags())
            if expected_tags and actual_tags != expected_tags:
                raise ValueError(f"Symbol manifest restored {role}:{name} with tags {sorted(actual_tags)}, expected {sorted(expected_tags)}")

    def _parse_registered_expression(self, text: str) -> Expression:
        expr = expression_from_canonical(text)
        self._validate_registered_expression(expr)
        return expr

    def _validate_registered_expression(self, expr: Expression) -> None:
        builtin_symbols = s.builtin_symbols_by_canonical_name()
        builtin_namespace = f"{s.namespace}::"
        theory_namespace = f"{self.name}::"
        for symbol in expr.get_all_symbols():
            canonical = canonical_string(symbol)
            if canonical.startswith(builtin_namespace):
                if canonical not in builtin_symbols:
                    raise ValueError(f"Unregistered pychete builtin symbol in expression: {canonical}")
                continue
            if not canonical.startswith(theory_namespace):
                continue
            role = symbol_data(symbol, SymbolDataKey.ROLE)
            label = symbol_data(symbol, SymbolDataKey.LABEL)
            owner = symbol_data(symbol, SymbolDataKey.THEORY)
            if not isinstance(role, str) or label is None or owner != self.name:
                raise ValueError(f"Unregistered pychete theory symbol in expression: {canonical}")
            key = f"{role}:{label}"
            if key not in self._symbols or not bool(symbol == self._symbols[key]):
                raise ValueError(f"Pychete expression references symbol outside the restored registry: {canonical}")

    def define_index_type(self, name: BuiltinIndexType | str, dimension: int | None = None) -> IndexType:
        name_key = _index_type_name(name)
        if name_key in self.index_types:
            return self.index_types[name_key]
        sym = (
            s.Lorentz
            if name_key == BuiltinIndexType.LORENTZ.value
            else self.symbol(
                name_key,
                role=SymbolRole.INDEX_TYPE,
                data={
                    SymbolDataKey.NAME.value: name_key,
                    SymbolDataKey.DIMENSION.value: dimension if dimension is not None else -1,
                },
            )
        )
        index_type = IndexType(name=name_key, symbol=sym, dimension=dimension)
        self.index_types[name_key] = index_type
        return index_type

    def define_flavor_index(self, name: BuiltinIndexType | str = BuiltinIndexType.FLAVOR, dimension: int | None = None) -> IndexType:
        return self.define_index_type(name, dimension)

    def index(
        self,
        label: str | Expression,
        representation: BuiltinIndexType | str | Expression = BuiltinIndexType.LORENTZ,
    ) -> Expression:
        label_expr = label if isinstance(label, Expression) else self.symbol(label, role=SymbolRole.INDEX)
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
        indices_tuple = tuple(indices)
        label = self.symbol(
            name,
            role=SymbolRole.COUPLING,
            data={
                SymbolDataKey.NAME.value: name,
                SymbolDataKey.INDICES.value: list(indices_tuple),
                SymbolDataKey.EFT_ORDER.value: eft_order,
                SymbolDataKey.SELF_CONJUGATE.value: int(self_conjugate),
            },
        )
        definition = CouplingDefinition(
            name=name,
            label=label,
            indices=indices_tuple,
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
        mass: int | MassSpec | None = None,
    ) -> FieldHandle:
        if name in self.fields:
            return FieldHandle(self, self.fields[name])

        mass_kind = FieldMassKind.MASSLESS
        mass_label: Expression | None = None
        mass_indices: tuple[Expression, ...] = ()
        if mass not in (None, 0):
            if not isinstance(mass, tuple) or len(mass) < 2:
                raise ValueError("mass must be 0/None or (FieldMassKind.HEAVY|FieldMassKind.LIGHT, label[, indices])")
            mass_kind = FieldMassKind.from_user(mass[0])
            if mass_kind is FieldMassKind.MASSLESS:
                raise ValueError("mass kind for a massive field must be FieldMassKind.HEAVY or FieldMassKind.LIGHT")
            mass_name = mass[1]
            mass_indices = tuple(mass[2]) if len(mass) > 2 else ()
            order = 0 if mass_kind is FieldMassKind.HEAVY else 1
            mass_handle = self.define_coupling(
                str(mass_name),
                indices=mass_indices,
                eft_order=order,
                self_conjugate=True,
            )
            mass_label = mass_handle.label

        indices_tuple = tuple(indices)
        field_data: dict[str, Any] = {
            SymbolDataKey.NAME.value: name,
            SymbolDataKey.FIELD_TYPE.value: type_expr,
            SymbolDataKey.INDICES.value: list(indices_tuple),
            SymbolDataKey.SELF_CONJUGATE.value: int(self_conjugate),
            SymbolDataKey.MASS_KIND.value: mass_kind.value,
            SymbolDataKey.MASS_INDICES.value: list(mass_indices),
        }
        if mass_label is not None:
            field_data[SymbolDataKey.MASS_LABEL.value] = mass_label
        definition = FieldDefinition(
            name=name,
            label=self.symbol(name, role=SymbolRole.FIELD, data=field_data),
            type=type_expr,
            indices=indices_tuple,
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
        group_symbol = self.symbol(
            name,
            role=SymbolRole.GROUP,
            data={
                SymbolDataKey.NAME.value: name,
                SymbolDataKey.GROUP_TYPE.value: group_type,
                SymbolDataKey.GROUP_COUPLING.value: coupling,
                SymbolDataKey.GROUP_FIELD.value: field,
            },
        )
        vector = self.define_field(field, s.Vector(group_symbol), self_conjugate=True, mass=0)
        self.groups[name] = {
            "name": name,
            "type": canonical_string(group_type),
            "coupling": coupling_handle.name,
            "field": vector.name,
        }

    def mass_expr(self, field_def: FieldDefinition) -> Expression | None:
        return field_def.mass_expr()

    def free_lag(self, *field_names_or_handles: str | FieldHandle) -> Expression:
        out = s.zero
        for item in field_names_or_handles:
            handle = item if isinstance(item, FieldHandle) else self.field_handle(item)
            definition = handle.definition
            mu = self.lorentz_index("d")
            field_expr = handle()
            type_expr = definition.type_expr
            is_self_conjugate = definition.is_self_conjugate
            if bool(type_expr == s.Scalar):
                mass = self.mass_expr(definition)
                if is_self_conjugate:
                    kinetic = s.half * handle(derivatives=[mu]) ** 2
                    if mass is not None:
                        kinetic = kinetic - s.half * mass**2 * field_expr**2
                else:
                    kinetic = s.Bar(handle(derivatives=[mu])) * handle(derivatives=[mu])
                    if mass is not None:
                        kinetic = kinetic - mass**2 * s.Bar(field_expr) * field_expr
                out = out + kinetic
            elif is_head(type_expr, s.Vector):
                nu = self.lorentz_index("e")
                strength = s.FieldStrength(definition.label, list_expr(mu, nu), list_expr(), list_expr())
                out = out - s.twenty_fourth * 6 * strength**2
            elif bool(type_expr == s.Fermion):
                mass = self.mass_expr(definition)
                dirac = s.I * s.NCM(s.Bar(field_expr), s.Gamma(mu), handle(derivatives=[mu]))
                if mass is not None:
                    dirac = dirac - mass * s.NCM(s.Bar(field_expr), field_expr)
                out = out + dirac
            else:
                out = out + s.FreeLag(definition.label)
        return out

    def set_lagrangian(self, lagrangian: Expression) -> Expression:
        self._validate_registered_expression(lagrangian)
        self.lagrangian = lagrangian.expand()
        self.analysis = AnalysisState(lagrangian=self.lagrangian)
        return self.lagrangian

    def _repr_latex_(self) -> str:
        if self.lagrangian is not None:
            return f"${latex_string(self.lagrangian)}$"
        return rf"$\mathrm{{Theory}}\left({self.name}\right)$"

    def _repr_html_(self) -> str:
        if self.lagrangian is not None:
            return f"<div><strong>Theory {escape(self.name)}</strong><br><code>{escape(display_string(self.lagrangian))}</code></div>"
        return f"<div><strong>Theory {escape(self.name)}</strong></div>"

    def to_json_obj(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "theory_name": self.name,
            "symbols": self.symbol_manifest(),
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
        s.register_builtins()
        theory = cls(obj["theory_name"])
        if "symbols" in obj:
            theory._restore_symbol_manifest(obj["symbols"])
        for name, data in obj.get("index_types", {}).items():
            if name != BuiltinIndexType.LORENTZ.value:
                theory.define_index_type(name, data.get("dimension"))
        for name, data in obj.get("couplings", {}).items():
            theory.define_coupling(
                name,
                indices=[theory._parse_registered_expression(x) for x in data.get("indices", [])],
                eft_order=int(data.get("eft_order", 0)),
                self_conjugate=bool(data.get("self_conjugate", False)),
            )
        for name, data in obj.get("fields", {}).items():
            mass_label = data.get("mass_label")
            mass = None
            if mass_label is not None:
                mass_kind = FieldMassKind.from_user(data.get("mass_kind", FieldMassKind.LIGHT.value))
                mass_indices = [theory._parse_registered_expression(x) for x in data.get("mass_indices", [])]
                mass_name = _coupling_name_for_label(theory, str(mass_label))
                mass = (mass_kind, mass_name, mass_indices)
            theory.define_field(
                name,
                theory._parse_registered_expression(data["type"]),
                indices=[theory._parse_registered_expression(x) for x in data.get("indices", [])],
                self_conjugate=bool(data.get("self_conjugate", False)),
                mass=mass,
            )
        if obj.get("lagrangian"):
            theory.set_lagrangian(theory._parse_registered_expression(obj["lagrangian"]))
        return theory
