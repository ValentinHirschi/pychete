from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, TypeAlias

from symbolica import Expression, S

from .expr import derivative_indices_expr, internal_indices_expr, is_head, lorentz_indices_expr
from .symbols import SymbolDataKey, SymbolRole, canonical_string, display_string, expression_from_canonical, latex_string, s, safe_symbol_name, symbol_data

if TYPE_CHECKING:
    from .matching import HeavyFermionSolution, HeavyScalarSolution


class FieldMassKind(StrEnum):
    """Mass hierarchy used for EFT counting and heavy-field matching."""

    HEAVY = "heavy"
    LIGHT = "light"

    @classmethod
    def from_user(cls, value: FieldMassKind | str) -> FieldMassKind:
        """Normalize a user-provided mass-kind value."""

        normalized = str(value).lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"unsupported mass kind {value!r}") from exc


class FieldVariation(StrEnum):
    """Choice of field variable for Euler-Lagrange variation."""

    AUTO = "auto"
    FIELD = "field"
    BAR = "bar"

    @classmethod
    def from_user(cls, value: FieldVariation | str) -> FieldVariation:
        """Normalize a user-provided variation mode."""

        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError("variation must be FieldVariation.AUTO, FieldVariation.FIELD, or FieldVariation.BAR") from exc


class BuiltinIndexType(StrEnum):
    """Built-in index representations understood by pychete."""

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
    value = symbol_data(label, SymbolDataKey.MASS_KIND, FieldMassKind.LIGHT.value)
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


def field_charges_from_label(label: Expression) -> tuple[Expression, ...]:
    return _expression_list_from_symbol_data(label, SymbolDataKey.CHARGES)


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
    return s.Coupling(mass_label, internal_indices_expr(*field_mass_indices_from_label(label)), order)


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
    """Metadata for an index representation within a theory."""

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
    """Registered metadata for a coupling symbol."""

    name: str
    label: Expression
    indices: tuple[Expression, ...] = ()
    eft_order: int = 0
    self_conjugate: bool = False

    def expr(self, *indices: Expression) -> Expression:
        """Build a Symbolica coupling expression with optional indices."""

        if not indices:
            indices = ()
        return s.Coupling(self.label, internal_indices_expr(*indices), coupling_eft_order_from_label(self.label))

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
class GaugeCharge:
    """Charge assignment of a field under a registered gauge group."""

    group: str
    value: Expression
    expr: Expression

    def to_json(self) -> dict[str, Any]:
        return {
            "group": self.group,
            "value": canonical_string(self.value),
            "expr": canonical_string(self.expr),
        }


@dataclass(frozen=True)
class FieldDefinition:
    """Registered metadata for a field symbol."""

    name: str
    label: Expression
    type: Expression
    indices: tuple[Expression, ...] = ()
    self_conjugate: bool = False
    mass_kind: FieldMassKind = FieldMassKind.LIGHT
    mass_label: Expression | None = None
    mass_indices: tuple[Expression, ...] = ()
    charges: tuple[Expression, ...] = ()

    @property
    def heavy(self) -> bool:
        """Whether this field is treated as heavy in EFT counting."""

        return field_mass_kind_from_label(self.label) is FieldMassKind.HEAVY

    @property
    def type_expr(self) -> Expression:
        """Symbolica expression encoding the field type."""

        return field_type_from_label(self.label)

    @property
    def is_self_conjugate(self) -> bool:
        """Whether the field equals its conjugate."""

        return field_self_conjugate_from_label(self.label)

    def expr(self, *indices: Expression, derivatives: Iterable[Expression] = ()) -> Expression:
        """Build a Symbolica field expression."""

        return s.Field(self.label, self.type_expr, internal_indices_expr(*indices), derivative_indices_expr(*tuple(derivatives)))

    def mass_expr(self) -> Expression | None:
        """Return the mass coupling expression, if one was registered."""

        return field_mass_expr_from_label(self.label)

    @property
    def charge_exprs(self) -> tuple[Expression, ...]:
        """Gauge-charge expressions stored for this field."""

        return field_charges_from_label(self.label)

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
            "charges": [canonical_string(charge) for charge in field_charges_from_label(self.label)],
        }


class FieldHandle:
    """Callable handle for constructing expressions of a registered field."""

    def __init__(self, theory: Theory, definition: FieldDefinition) -> None:
        self.theory = theory
        self.definition = definition

    @property
    def label(self) -> Expression:
        """Symbolica label used internally for this field."""

        return self.definition.label

    @property
    def name(self) -> str:
        """User-facing field name."""

        return self.definition.name

    def __call__(self, *indices: Expression, derivatives: Iterable[Expression] = ()) -> Expression:
        """Build this field with optional indices and derivatives."""

        return self.definition.expr(*indices, derivatives=derivatives)

    def _repr_latex_(self) -> str:
        return self.definition._repr_latex_()

    def _repr_html_(self) -> str:
        return self.definition._repr_html_()


class CouplingHandle:
    """Callable handle for constructing expressions of a registered coupling."""

    def __init__(self, theory: Theory, definition: CouplingDefinition) -> None:
        self.theory = theory
        self.definition = definition

    @property
    def label(self) -> Expression:
        """Symbolica label used internally for this coupling."""

        return self.definition.label

    @property
    def name(self) -> str:
        """User-facing coupling name."""

        return self.definition.name

    def __call__(self, *indices: Expression) -> Expression:
        """Build this coupling with optional indices."""

        return self.definition.expr(*indices)

    def _repr_latex_(self) -> str:
        return self.definition._repr_latex_()

    def _repr_html_(self) -> str:
        return self.definition._repr_html_()


class Theory:
    """Metadata context for fields, couplings, groups, and index types.

    A theory owns the symbols needed to interpret Symbolica expressions, but it
    does not own a Lagrangian. Pass Lagrangian expressions explicitly to methods
    such as :meth:`derive_eom`, :meth:`solve_heavy_scalar_eoms`, and
    :meth:`match`.
    """

    schema_version = 2

    def __init__(self, name: str) -> None:
        s.register_builtins()
        self.name = safe_symbol_name(name)
        self._symbols: dict[str, Expression] = {}
        self.index_types: dict[str, IndexType] = {}
        self.fields: dict[str, FieldDefinition] = {}
        self.couplings: dict[str, CouplingDefinition] = {}
        self.groups: dict[str, dict[str, Any]] = {}
        self.define_index_type(BuiltinIndexType.LORENTZ)

    def symbol(self, name: str, *, role: SymbolRole | str = SymbolRole.LABEL, data: dict[str, Any] | None = None) -> Expression:
        """Return a theory-owned Symbolica symbol with pychete metadata."""

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
        """Return JSON-serializable metadata for theory-owned symbols."""

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
                if canonical in builtin_symbols:
                    continue
                raise ValueError(f"Unregistered pychete builtin symbol in expression: {canonical}")
            if not canonical.startswith(theory_namespace):
                role = symbol_data(symbol, SymbolDataKey.ROLE)
                owner = symbol_data(symbol, SymbolDataKey.THEORY)
                if role is not None or owner is not None:
                    raise ValueError(f"Pychete expression references symbol from a different theory: {canonical}")
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
        """Register or return an index representation.

        ``Lorentz`` is always available as a built-in representation. Other
        names create theory-owned index-type symbols and may carry an optional
        dimension.
        """

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
        """Register or return a flavor index representation."""

        return self.define_index_type(name, dimension)

    def index(
        self,
        label: str | Expression,
        representation: BuiltinIndexType | str | Expression = BuiltinIndexType.LORENTZ,
    ) -> Expression:
        """Build an ``Index(label, representation)`` expression.

        String labels are converted to plain Symbolica symbols. Explicit
        Symbolica expressions may be passed for advanced labels such as
        ``s.dummy_index(0)``.
        """

        label_expr = label if isinstance(label, Expression) else S(safe_symbol_name(label))
        if isinstance(representation, Expression):
            rep_expr = representation
        else:
            rep_expr = self.define_index_type(representation).symbol
        return s.Index(label_expr, rep_expr)

    def lorentz_index(self, label: str) -> Expression:
        """Build a Lorentz index with the given label."""

        return self.index(label, s.Lorentz)

    def dummy_index(
        self,
        number: int,
        representation: BuiltinIndexType | str | Expression = BuiltinIndexType.LORENTZ,
    ) -> Expression:
        """Build a default dummy index for deterministic generated sums."""

        if isinstance(representation, Expression):
            rep_expr = representation
        else:
            rep_expr = self.define_index_type(representation).symbol
        return s.Index(s.dummy_index(number), rep_expr)

    def define_coupling(
        self,
        name: str,
        *,
        indices: Iterable[Expression] = (),
        eft_order: int = 0,
        self_conjugate: bool = False,
    ) -> CouplingHandle:
        """Register or return a coupling.

        Parameters
        ----------
        name:
            User-facing coupling name.
        indices:
            Optional index representations carried by the coupling.
        eft_order:
            EFT order assigned to the coupling for truncation.
        self_conjugate:
            Whether the coupling is treated as self-conjugate.
        """

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
        charges: Iterable[Expression] = (),
        self_conjugate: bool = False,
        mass: int | MassSpec | None = None,
    ) -> FieldHandle:
        """Register or return a field.

        ``type_expr`` is usually one of ``s.Scalar``, ``s.Fermion``, or a
        vector type such as ``s.Vector(group_symbol)``. The ``mass`` argument
        may be ``0``/``None`` or ``(FieldMassKind, coupling_name[, indices])``.
        """

        if name in self.fields:
            return FieldHandle(self, self.fields[name])

        mass_kind = FieldMassKind.LIGHT
        mass_label: Expression | None = None
        mass_indices: tuple[Expression, ...] = ()
        if mass not in (None, 0):
            if not isinstance(mass, tuple) or len(mass) < 2:
                raise ValueError("mass must be 0/None or (FieldMassKind.HEAVY|FieldMassKind.LIGHT, label[, indices])")
            mass_kind = FieldMassKind.from_user(mass[0])
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
        charges_tuple = tuple(charges)
        field_data: dict[str, Any] = {
            SymbolDataKey.NAME.value: name,
            SymbolDataKey.FIELD_TYPE.value: type_expr,
            SymbolDataKey.INDICES.value: list(indices_tuple),
            SymbolDataKey.CHARGES.value: list(charges_tuple),
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
            charges=charges_tuple,
        )
        self.fields[name] = definition
        return FieldHandle(self, definition)

    def field_handle(self, name: str) -> FieldHandle:
        """Return the callable handle for a registered field."""

        return FieldHandle(self, self.fields[name])

    def coupling_handle(self, name: str) -> CouplingHandle:
        """Return the callable handle for a registered coupling."""

        return CouplingHandle(self, self.couplings[name])

    def define_gauge_group(self, name: str, group_type: Expression, coupling: str, field: str) -> None:
        """Register a gauge group, its coupling, and its vector field."""

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
            "symbol": canonical_string(group_symbol),
            "type": canonical_string(group_type),
            "coupling": coupling_handle.name,
            "field": vector.name,
        }

    def gauge_charge(self, group: str, value: int | Expression) -> GaugeCharge:
        """Build a charge expression for a registered gauge group."""

        if group not in self.groups:
            raise KeyError(f"Unknown gauge group {group!r}")
        group_symbol = self.symbol(group, role=SymbolRole.GROUP)
        value_expr = value if isinstance(value, Expression) else Expression.num(value)
        return GaugeCharge(group=group, value=value_expr, expr=group_symbol(value_expr))

    def mass_expr(self, field_def: FieldDefinition) -> Expression | None:
        """Return the mass expression associated with a field definition."""

        return field_def.mass_expr()

    def free_lag(self, *field_names_or_handles: str | FieldHandle) -> Expression:
        """Build the free Lagrangian for registered fields.

        Each argument may be either a field name or a ``FieldHandle``. The
        returned Symbolica expression is independent of the theory object and
        can be stored or transformed separately.
        """

        out = Expression.num(0)
        from .spinor import ncm_expr

        for item in field_names_or_handles:
            handle = item if isinstance(item, FieldHandle) else self.field_handle(item)
            definition = handle.definition
            mu = self.dummy_index(0)
            field_expr = handle()
            type_expr = definition.type_expr
            is_self_conjugate = definition.is_self_conjugate
            if bool(type_expr == s.Scalar):
                mass = self.mass_expr(definition)
                if is_self_conjugate:
                    kinetic = handle(derivatives=[mu]) ** 2 / 2
                    if mass is not None:
                        kinetic = kinetic - mass**2 * field_expr**2 / 2
                else:
                    kinetic = s.Bar(handle(derivatives=[mu])) * handle(derivatives=[mu])
                    if mass is not None:
                        kinetic = kinetic - mass**2 * s.Bar(field_expr) * field_expr
                out = out + kinetic
            elif is_head(type_expr, s.Vector):
                nu = self.dummy_index(1)
                strength = s.FieldStrength(definition.label, lorentz_indices_expr(mu, nu), internal_indices_expr(), derivative_indices_expr())
                group_symbol = type_expr[0]
                coupling_name = symbol_data(group_symbol, SymbolDataKey.GROUP_COUPLING)
                if isinstance(coupling_name, str) and coupling_name in self.couplings:
                    gauge_coupling = self.coupling_handle(coupling_name)()
                    out = out - strength**2 / (4 * gauge_coupling**2)
                else:
                    out = out - strength**2 / 4
            elif bool(type_expr == s.Fermion):
                mass = self.mass_expr(definition)
                dirac = Expression.I * ncm_expr(s.Bar(field_expr), s.Gamma(mu), handle(derivatives=[mu]))
                if mass is not None:
                    dirac = dirac - mass * ncm_expr(s.Bar(field_expr), field_expr)
                out = out + dirac
            else:
                out = out + s.FreeLag(definition.label)
        return out

    def derive_eom(
        self,
        lagrangian: Expression,
        field: FieldHandle | FieldDefinition | str,
        *,
        eft_order: int = 6,
        variation: FieldVariation | str = FieldVariation.AUTO,
    ) -> Expression:
        """Derive the Euler-Lagrange equation for a field.

        ``lagrangian`` must be a Symbolica expression using symbols registered
        on this theory. ``variation`` controls whether the field, its conjugate,
        or the automatic default is varied.
        """

        from .functional import derive_eom

        return derive_eom(self, lagrangian, field, eft_order=eft_order, variation=variation)

    def solve_heavy_scalar_eoms(self, lagrangian: Expression, *, eft_order: int = 6) -> dict[str, HeavyScalarSolution]:
        """Solve heavy scalar equations of motion order by order.

        Returns a mapping from heavy field names to ``HeavyScalarSolution``
        objects. Solutions are recomputed for the supplied Lagrangian and are
        not cached on the theory.
        """

        from .matching import solve_heavy_scalar_eoms

        return solve_heavy_scalar_eoms(self, lagrangian, eft_order=eft_order)

    def solve_heavy_fermion_eoms(self, lagrangian: Expression, *, eft_order: int = 6) -> dict[str, HeavyFermionSolution]:
        """Solve heavy Dirac-fermion equations of motion order by order.

        The current implementation supports diagonal heavy Dirac fields with
        Matchete-style free kinetic and mass terms.
        """

        from .matching import solve_heavy_fermion_eoms

        return solve_heavy_fermion_eoms(self, lagrangian, eft_order=eft_order)

    def match(self, lagrangian: Expression, *, eft_order: int = 6, loop_order: int = 0) -> Expression:
        """Integrate out heavy fields at the requested loop order.

        The result is a matched light-field Lagrangian truncated through
        ``eft_order``. Only tree-level matching, ``loop_order=0``, is currently
        implemented.
        """

        if loop_order != 0:
            raise NotImplementedError("pychete currently implements only tree-level matching with loop_order=0")

        from .matching import match_tree

        return match_tree(self, lagrangian, eft_order=eft_order)

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{Theory}}\left({self.name}\right)$"

    def _repr_html_(self) -> str:
        return f"<div><strong>Theory {escape(self.name)}</strong></div>"

    def to_json_obj(self) -> dict[str, Any]:
        """Return a JSON-serializable checkpoint for theory metadata."""

        return {
            "schema_version": self.schema_version,
            "theory_name": self.name,
            "symbols": self.symbol_manifest(),
            "index_types": {name: value.to_json() for name, value in sorted(self.index_types.items())},
            "groups": self.groups,
            "fields": {name: value.to_json() for name, value in sorted(self.fields.items())},
            "couplings": {name: value.to_json() for name, value in sorted(self.couplings.items())},
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize theory metadata to a JSON string."""

        return json.dumps(self.to_json_obj(), indent=indent, sort_keys=True) + "\n"

    def write_json(self, path: str | Path) -> None:
        """Write theory metadata JSON to ``path``."""

        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_json_obj(cls, obj: dict[str, Any]) -> Theory:
        """Restore theory metadata from a JSON object."""

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
        theory.groups = {
            str(name): dict(data)
            for name, data in obj.get("groups", {}).items()
            if isinstance(data, dict)
        }
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
                charges=[theory._parse_registered_expression(x) for x in data.get("charges", [])],
                self_conjugate=bool(data.get("self_conjugate", False)),
                mass=mass,
            )
        return theory
