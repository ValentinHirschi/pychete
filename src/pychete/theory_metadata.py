from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from html import escape
from typing import TYPE_CHECKING, Any, Iterable, TypeAlias

from symbolica import Expression

from .expr import as_int, is_head, list_expr
from .symbols import (
    SymbolDataKey,
    SymbolRole,
    canonical_string,
    display_string,
    expression_from_canonical,
    latex_string,
    s,
    safe_symbol_name,
    symbol_data,
)

if TYPE_CHECKING:
    from .theory import Theory


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


class FieldChirality(StrEnum):
    """Chirality metadata for fermion fields."""

    NONE = "none"
    LEFT = "left"
    RIGHT = "right"

    @classmethod
    def from_user(cls, value: FieldChirality | str | bool | None) -> FieldChirality:
        """Normalize a user-provided chirality value."""

        if value is None or value is False:
            return cls.NONE
        if value is True:
            raise ValueError("chirality must be false/none, LeftHanded, or RightHanded")
        normalized = str(value).replace("_", "").replace("-", "").lower()
        if normalized in {"none", "false", "0"}:
            return cls.NONE
        if normalized in {"left", "lefthanded"}:
            return cls.LEFT
        if normalized in {"right", "righthanded"}:
            return cls.RIGHT
        try:
            return cls(str(value).lower())
        except ValueError as exc:
            raise ValueError(f"unsupported chirality {value!r}") from exc


class FieldRole(StrEnum):
    """Physics role metadata attached to a registered field."""

    PHYSICAL = "physical"
    GHOST = "ghost"
    ANTI_GHOST = "anti_ghost"
    GOLDSTONE = "goldstone"
    BACKGROUND = "background"

    @classmethod
    def from_user(cls, value: FieldRole | str) -> FieldRole:
        """Normalize a user-provided field-role value."""

        if isinstance(value, cls):
            return value
        normalized = str(value).replace("_", "").replace("-", "").lower()
        aliases = {
            "physical": cls.PHYSICAL,
            "field": cls.PHYSICAL,
            "false": cls.PHYSICAL,
            "none": cls.PHYSICAL,
            "ghost": cls.GHOST,
            "antighost": cls.ANTI_GHOST,
            "ghostbar": cls.ANTI_GHOST,
            "goldstone": cls.GOLDSTONE,
            "goldstoneboson": cls.GOLDSTONE,
            "background": cls.BACKGROUND,
            "backgroundfield": cls.BACKGROUND,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"unsupported field role {value!r}") from exc

    @classmethod
    def from_type(cls, type_expr: Expression) -> FieldRole:
        """Infer a field role from a Matchete-style field type expression."""

        if bool(type_expr == s.Ghost):
            return cls.GHOST
        if bool(type_expr == s.AntiGhost):
            return cls.ANTI_GHOST
        return cls.PHYSICAL


class GroupKind(StrEnum):
    """Whether a registered symmetry group is gauged or global."""

    GAUGE = "gauge"
    GLOBAL = "global"

    @classmethod
    def from_user(cls, value: GroupKind | str) -> GroupKind:
        """Normalize a user-provided group-kind value."""

        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError as exc:
            raise ValueError(f"unsupported group kind {value!r}") from exc


class RepresentationReality(StrEnum):
    """Reality class for a registered group representation.

    Matchete stores this through the Frobenius-Schur indicator: real ``+1``,
    complex ``0``, and pseudoreal ``-1``. ``UNKNOWN`` is used while pychete
    only has explicit Dynkin metadata and no backend-computed indicator yet.
    """

    UNKNOWN = "unknown"
    REAL = "real"
    COMPLEX = "complex"
    PSEUDOREAL = "pseudoreal"

    @classmethod
    def from_user(cls, value: RepresentationReality | str | int | None) -> RepresentationReality:
        """Normalize a user-provided representation-reality value."""

        if value is None:
            return cls.UNKNOWN
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            by_indicator = {1: cls.REAL, 0: cls.COMPLEX, -1: cls.PSEUDOREAL}
            try:
                return by_indicator[value]
            except KeyError as exc:
                raise ValueError(f"unsupported representation Frobenius-Schur indicator {value!r}") from exc
        normalized = str(value).replace("_", "").replace("-", "").lower()
        aliases = {
            "unknown": cls.UNKNOWN,
            "none": cls.UNKNOWN,
            "real": cls.REAL,
            "complex": cls.COMPLEX,
            "pseudoreal": cls.PSEUDOREAL,
            "pseudo": cls.PSEUDOREAL,
            "quaternionic": cls.PSEUDOREAL,
            "1": cls.REAL,
            "0": cls.COMPLEX,
            "-1": cls.PSEUDOREAL,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"unsupported representation reality {value!r}") from exc

    @property
    def indicator(self) -> int | None:
        """Return Matchete's Frobenius-Schur indicator when known."""

        if self is RepresentationReality.REAL:
            return 1
        if self is RepresentationReality.COMPLEX:
            return 0
        if self is RepresentationReality.PSEUDOREAL:
            return -1
        return None


class BuiltinIndexType(StrEnum):
    """Built-in index representations understood by pychete."""

    LORENTZ = "Lorentz"
    FLAVOR = "Flavor"


MassKindInput: TypeAlias = FieldMassKind | str
MassSpec: TypeAlias = tuple[MassKindInput, str] | tuple[MassKindInput, str, Iterable[Expression]]
CouplingSelfConjugate: TypeAlias = bool | tuple[int, ...]
RepresentationLabelInput: TypeAlias = str | Expression
DynkinInput: TypeAlias = Iterable[Expression | int]
JsonValue: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None

_EXPRESSION_DATA_KEY = "__pychete_expression__"
_SYMBOL_ROLE_ORDER = {
    SymbolRole.INDEX_TYPE.value: 0,
    SymbolRole.GROUP.value: 1,
    SymbolRole.REPRESENTATION.value: 2,
    SymbolRole.CG_TENSOR.value: 3,
    SymbolRole.INDEX.value: 4,
    SymbolRole.COUPLING.value: 5,
    SymbolRole.FIELD.value: 6,
    SymbolRole.EXTERNAL.value: 7,
    SymbolRole.LABEL.value: 8,
}


def _local_tag_name(tag: str) -> str:
    return tag.split("::")[-1]


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


def _normalized_restored_symbol_data(role: str, data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    if role == SymbolRole.COUPLING.value:
        indices = normalized.get(SymbolDataKey.INDICES.value, [])
        index_count = len(indices) if isinstance(indices, list) else 0
        normalized.setdefault(SymbolDataKey.SYMMETRIES.value, [])
        normalized.setdefault(SymbolDataKey.DIAGONAL_COUPLING.value, [False for _ in range(index_count)])
        normalized.setdefault(SymbolDataKey.THERMAL_POWER_COUNTING.value, 1)
        normalized.setdefault(SymbolDataKey.UNITARY.value, 0)
    elif role == SymbolRole.FIELD.value:
        type_expr = normalized.get(SymbolDataKey.FIELD_TYPE.value)
        inferred_role = FieldRole.from_type(type_expr) if isinstance(type_expr, Expression) else FieldRole.PHYSICAL
        normalized.setdefault(SymbolDataKey.FIELD_ROLE.value, inferred_role.value)
        normalized.setdefault(SymbolDataKey.PROPAGATING.value, 1)
        normalized.setdefault(SymbolDataKey.ZERO_MODE.value, 0)
    elif role == SymbolRole.GROUP.value:
        group_type = normalized.get(SymbolDataKey.GROUP_TYPE.value)
        normalized.setdefault(
            SymbolDataKey.GROUP_KIND.value,
            GroupKind.GAUGE.value
            if SymbolDataKey.GROUP_COUPLING.value in normalized or SymbolDataKey.GROUP_FIELD.value in normalized
            else GroupKind.GLOBAL.value,
        )
        if isinstance(group_type, Expression):
            normalized.setdefault(SymbolDataKey.GROUP_ABELIAN.value, int(bool(group_type == s.U1)))
    elif role == SymbolRole.REPRESENTATION.value:
        normalized.setdefault(SymbolDataKey.REPRESENTATION_DYNKIN.value, [])
        normalized.setdefault(SymbolDataKey.REPRESENTATION_DIMENSION.value, -1)
        normalized.setdefault(SymbolDataKey.REPRESENTATION_REALITY.value, RepresentationReality.UNKNOWN.value)
    elif role == SymbolRole.CG_TENSOR.value:
        normalized.setdefault(SymbolDataKey.CG_REPRESENTATIONS.value, [])
        normalized.setdefault(SymbolDataKey.CG_SOURCE.value, "")
    return normalized


def field_mass_kind_from_label(label: Expression) -> FieldMassKind:
    value = symbol_data(label, SymbolDataKey.MASS_KIND, FieldMassKind.LIGHT.value)
    return FieldMassKind.from_user(str(value))


def field_type_from_label(label: Expression) -> Expression:
    value = symbol_data(label, SymbolDataKey.FIELD_TYPE)
    if not isinstance(value, Expression):
        raise ValueError(f"Field type is not stored on {canonical_string(label)}")
    return value


def field_role_from_label(label: Expression) -> FieldRole:
    value = symbol_data(label, SymbolDataKey.FIELD_ROLE)
    if value is None:
        return FieldRole.from_type(field_type_from_label(label))
    return FieldRole.from_user(str(value))


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


def field_charges_from_label(label: Expression) -> tuple[Expression, ...]:
    return _expression_list_from_symbol_data(label, SymbolDataKey.CHARGES)


def field_chirality_from_label(label: Expression) -> FieldChirality:
    value = symbol_data(label, SymbolDataKey.CHIRALITY, FieldChirality.NONE.value)
    return FieldChirality.from_user(str(value))


def field_propagating_from_label(label: Expression) -> bool:
    return bool(symbol_data(label, SymbolDataKey.PROPAGATING, 1))


def field_zero_mode_from_label(label: Expression) -> bool:
    return bool(symbol_data(label, SymbolDataKey.ZERO_MODE, 0))


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


def _normalize_coupling_self_conjugate(value: CouplingSelfConjugate | Iterable[int]) -> CouplingSelfConjugate:
    if isinstance(value, bool):
        return value
    if isinstance(value, tuple):
        if not all(isinstance(item, int) for item in value):
            raise ValueError("coupling self_conjugate permutation entries must be integers")
        return value
    return tuple(int(item) for item in value)


def coupling_self_conjugate_from_label(label: Expression) -> CouplingSelfConjugate:
    value = symbol_data(label, SymbolDataKey.SELF_CONJUGATE, 0)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, list):
        return tuple(int(item) for item in value)
    raise ValueError(f"Coupling self-conjugation is not stored as bool or permutation on {canonical_string(label)}")


def coupling_indices_from_label(label: Expression) -> tuple[Expression, ...]:
    return _expression_list_from_symbol_data(label, SymbolDataKey.INDICES)


def coupling_symmetries_from_label(label: Expression) -> tuple[Expression, ...]:
    return _expression_list_from_symbol_data(label, SymbolDataKey.SYMMETRIES)


def coupling_diagonal_flags_from_label(label: Expression) -> tuple[bool, ...]:
    value = symbol_data(label, SymbolDataKey.DIAGONAL_COUPLING, [])
    if not isinstance(value, list):
        raise ValueError(f"diagonal coupling flags are not stored as a list on {canonical_string(label)}")
    if not all(isinstance(item, (bool, int)) for item in value):
        raise ValueError(f"diagonal coupling flags contain non-boolean entries on {canonical_string(label)}")
    return tuple(bool(item) for item in value)


def coupling_thermal_power_counting_from_label(label: Expression) -> int:
    return int(symbol_data(label, SymbolDataKey.THERMAL_POWER_COUNTING, 1))


def coupling_unitary_from_label(label: Expression) -> bool:
    return bool(symbol_data(label, SymbolDataKey.UNITARY, 0))


def representation_group_from_label(label: Expression) -> str | None:
    value = symbol_data(label, SymbolDataKey.REPRESENTATION_GROUP)
    return str(value) if value is not None else None


def representation_dynkin_from_label(label: Expression) -> tuple[Expression, ...]:
    value = symbol_data(label, SymbolDataKey.REPRESENTATION_DYNKIN, [])
    if not isinstance(value, list):
        raise ValueError(f"representation dynkin metadata is not stored as a list on {canonical_string(label)}")
    if not all(isinstance(item, Expression) for item in value):
        raise ValueError(f"representation dynkin metadata contains non-expression entries on {canonical_string(label)}")
    return tuple(value)


def representation_dimension_from_label(label: Expression) -> int | None:
    value = symbol_data(label, SymbolDataKey.REPRESENTATION_DIMENSION, -1)
    dimension = int(value)
    return dimension if dimension >= 0 else None


def representation_reality_from_label(label: Expression) -> RepresentationReality:
    value = symbol_data(label, SymbolDataKey.REPRESENTATION_REALITY, RepresentationReality.UNKNOWN.value)
    return RepresentationReality.from_user(str(value))


def cg_representations_from_label(label: Expression) -> tuple[Expression, ...]:
    return _expression_list_from_symbol_data(label, SymbolDataKey.CG_REPRESENTATIONS)


def cg_tensor_from_label(label: Expression) -> Expression | None:
    value = symbol_data(label, SymbolDataKey.CG_TENSOR)
    if value is None:
        return None
    if not isinstance(value, Expression):
        raise ValueError(f"CG tensor data is not stored as an expression on {canonical_string(label)}")
    return value


def cg_source_from_label(label: Expression) -> str | None:
    value = symbol_data(label, SymbolDataKey.CG_SOURCE)
    if value is None or value == "":
        return None
    return str(value)


def _coupling_name_for_label(theory: Theory, label_text: str) -> str:
    for definition in theory.couplings.values():
        if canonical_string(definition.label) == label_text:
            return definition.name
    label = expression_from_canonical(label_text)
    name = label.get_name().split("::")[-1]
    prefix = f"{SymbolRole.COUPLING.value}_"
    return name.removeprefix(prefix)


def _representation_name_for_label(label: Expression) -> str:
    value = symbol_data(label, SymbolDataKey.LABEL)
    if isinstance(value, str):
        return value
    if bool(label == s.fund):
        return "fund"
    if bool(label == s.adj):
        return "adj"
    return label.get_name().split("::")[-1].removeprefix(f"{SymbolRole.REPRESENTATION.value}_")


def _normalize_dynkin(dynkin: DynkinInput) -> tuple[Expression, ...]:
    return tuple(item if isinstance(item, Expression) else Expression.num(int(item)) for item in dynkin)


def _group_type_from_entry(entry: dict[str, Any]) -> Expression:
    return expression_from_canonical(str(entry["type"]))


def _su_size(group_type: Expression) -> int | None:
    if not is_head(group_type, s.SU) or len(group_type) != 1:
        return None
    return as_int(group_type[0])


def _dynkin_ints(dynkin: tuple[Expression, ...]) -> tuple[int, ...] | None:
    values = tuple(as_int(item) for item in dynkin)
    if any(value is None for value in values):
        return None
    return tuple(int(value) for value in values if value is not None)


def _infer_representation_metadata(
    group_type: Expression,
    label: Expression | None,
    dynkin: tuple[Expression, ...],
) -> tuple[int | None, RepresentationReality]:
    n = _su_size(group_type)
    if n is None:
        return None, RepresentationReality.UNKNOWN
    if label is not None and bool(label == s.fund):
        return n, RepresentationReality.PSEUDOREAL if n == 2 else RepresentationReality.COMPLEX
    if label is not None and bool(label == s.adj):
        return n * n - 1, RepresentationReality.REAL

    dynkin_values = _dynkin_ints(dynkin)
    if dynkin_values is None:
        return None, RepresentationReality.UNKNOWN
    if n == 2 and len(dynkin_values) == 1:
        highest_weight = dynkin_values[0]
        return highest_weight + 1, RepresentationReality.REAL if highest_weight % 2 == 0 else RepresentationReality.PSEUDOREAL

    rank = n - 1
    if len(dynkin_values) != rank:
        return None, RepresentationReality.UNKNOWN
    if dynkin_values == (1, *([0] * (rank - 1))):
        return n, RepresentationReality.COMPLEX
    if dynkin_values == (*([0] * (rank - 1)), 1):
        return n, RepresentationReality.COMPLEX
    if rank > 1 and dynkin_values == (1, *([0] * (rank - 2)), 1):
        return n * n - 1, RepresentationReality.REAL
    return None, RepresentationReality.UNKNOWN


def _normalize_diagonal_coupling(diagonal: bool | Iterable[bool] | None, index_count: int) -> tuple[bool, ...]:
    if diagonal is None:
        return tuple(False for _ in range(index_count))
    flags = (diagonal,) if isinstance(diagonal, bool) else tuple(bool(item) for item in diagonal)
    if len(flags) != index_count:
        raise ValueError("diagonal coupling flags must have the same length as coupling indices")
    return tuple(bool(flag) for flag in flags)


def _field_symbol_tags(field_role: FieldRole, propagating: bool, zero_mode: bool) -> tuple[str, ...]:
    tags = [f"field_role_{field_role.value}", "propagating" if propagating else "non_propagating"]
    if zero_mode:
        tags.append("zero_mode")
    return tuple(tags)


def _group_symbol_tags(group_kind: GroupKind, abelian: bool) -> tuple[str, ...]:
    return (f"group_kind_{group_kind.value}", "abelian" if abelian else "non_abelian")


def _representation_symbol_tags(group: str, reality: RepresentationReality) -> tuple[str, ...]:
    return (f"representation_group_{safe_symbol_name(group)}", f"representation_reality_{reality.value}")


def _cg_tensor_symbol_tags(rank: int) -> tuple[str, ...]:
    return (f"cg_tensor_rank_{rank}",)


def _builtin_cg_tensor_name(kind: str, group: str, representation_name: str | None = None) -> str:
    parts = [kind, group]
    if representation_name is not None:
        parts.append(representation_name)
    return safe_symbol_name("_".join(parts))


def _group_entry(
    *,
    name: str,
    group_type: Expression,
    group_kind: GroupKind,
    coupling: str | None = None,
    field: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": name,
        "kind": group_kind.value,
        "type": canonical_string(group_type),
        "abelian": bool(group_type == s.U1),
    }
    if coupling is not None:
        entry["coupling"] = coupling
    if field is not None:
        entry["field"] = field
    return entry


@dataclass(frozen=True)
class RepresentationDefinition:
    """Registered metadata for a group representation label."""

    name: str
    group: str
    label: Expression
    expr: Expression
    dynkin: tuple[Expression, ...] = ()
    dimension: int | None = None
    reality: RepresentationReality = RepresentationReality.UNKNOWN

    @property
    def dynkin_exprs(self) -> tuple[Expression, ...]:
        """Dynkin coefficients stored on this representation label when available."""

        if symbol_data(self.label, SymbolDataKey.REPRESENTATION_DYNKIN) is not None:
            return representation_dynkin_from_label(self.label)
        return self.dynkin

    @property
    def dimension_value(self) -> int | None:
        """Dimension stored on this representation label when available."""

        if symbol_data(self.label, SymbolDataKey.REPRESENTATION_DIMENSION) is not None:
            return representation_dimension_from_label(self.label)
        return self.dimension

    @property
    def reality_kind(self) -> RepresentationReality:
        """Reality class stored on this representation label when available."""

        if symbol_data(self.label, SymbolDataKey.REPRESENTATION_REALITY) is not None:
            return representation_reality_from_label(self.label)
        return self.reality

    def _repr_latex_(self) -> str:
        return f"${latex_string(self.expr)}$"

    def _repr_html_(self) -> str:
        dynkin = ""
        if self.dynkin_exprs:
            dynkin = " dynkin=(" + ", ".join(escape(display_string(item)) for item in self.dynkin_exprs) + ")"
        dimension = "" if self.dimension_value is None else f" dimension={escape(str(self.dimension_value))}"
        reality = "" if self.reality_kind is RepresentationReality.UNKNOWN else f" reality={escape(self.reality_kind.value)}"
        return f"<code>Representation({escape(display_string(self.expr))}{dynkin}{dimension}{reality})</code>"

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "group": self.group,
            "label": canonical_string(self.label),
            "expr": canonical_string(self.expr),
            "dynkin": [canonical_string(item) for item in self.dynkin_exprs],
            "dimension": self.dimension_value,
            "reality": self.reality_kind.value,
        }


@dataclass(frozen=True)
class CGTensorDefinition:
    """Registered metadata for a Clebsch-Gordan tensor label."""

    name: str
    label: Expression
    representations: tuple[Expression, ...] = ()
    tensor: Expression | None = None
    source: str | None = None

    @property
    def representation_exprs(self) -> tuple[Expression, ...]:
        """Index representations carried by this CG tensor."""

        return cg_representations_from_label(self.label)

    @property
    def tensor_expr(self) -> Expression | None:
        """Backend tensor expression stored on the label, if available."""

        return cg_tensor_from_label(self.label)

    @property
    def source_text(self) -> str | None:
        """Original model/backend source string, if no expression was stored."""

        return cg_source_from_label(self.label)

    def expr(self, *indices: Expression) -> Expression:
        """Build a Symbolica ``CG(label, indices)`` tensor atom."""

        return s.CG(self.label, list_expr(*indices))

    def _repr_latex_(self) -> str:
        return f"${latex_string(self.expr())}$"

    def _repr_html_(self) -> str:
        reps = ", ".join(escape(display_string(rep)) for rep in self.representation_exprs)
        return f"<code>CGTensor({escape(display_string(self.label))}; reps=({reps}))</code>"

    def to_json(self) -> dict[str, Any]:
        tensor = self.tensor_expr
        source = self.source_text
        return {
            "name": self.name,
            "label": canonical_string(self.label),
            "representations": [canonical_string(rep) for rep in self.representation_exprs],
            "tensor": canonical_string(tensor) if tensor is not None else None,
            "source": source,
        }


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
    self_conjugate: CouplingSelfConjugate = False
    symmetries: tuple[Expression, ...] = ()
    diagonal: tuple[bool, ...] = ()
    thermal_power_counting: int = 1
    unitary: bool = False

    def expr(self, *indices: Expression) -> Expression:
        """Build a Symbolica coupling expression with optional indices."""

        if not indices:
            indices = ()
        return s.Coupling(self.label, list_expr(*indices), coupling_eft_order_from_label(self.label))

    @property
    def index_exprs(self) -> tuple[Expression, ...]:
        """Index representations stored on the coupling label."""

        return coupling_indices_from_label(self.label)

    @property
    def self_conjugate_spec(self) -> CouplingSelfConjugate:
        """Whether the coupling is self-conjugate or its conjugation permutation."""

        return coupling_self_conjugate_from_label(self.label)

    @property
    def symmetry_exprs(self) -> tuple[Expression, ...]:
        """Symmetry metadata stored on the coupling label."""

        return coupling_symmetries_from_label(self.label)

    @property
    def diagonal_flags(self) -> tuple[bool, ...]:
        """Flags marking indices that are restricted to diagonal values."""

        return coupling_diagonal_flags_from_label(self.label)

    @property
    def is_unitary(self) -> bool:
        """Whether this coupling is a unitary matrix in flavor space."""

        return coupling_unitary_from_label(self.label)

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
            "symmetries": [canonical_string(i) for i in coupling_symmetries_from_label(self.label)],
            "diagonal": list(coupling_diagonal_flags_from_label(self.label)),
            "thermal_power_counting": coupling_thermal_power_counting_from_label(self.label),
            "unitary": coupling_unitary_from_label(self.label),
        }


@dataclass(frozen=True)
class FieldDefinition:
    """Registered metadata for a field symbol."""

    name: str
    label: Expression
    type: Expression
    indices: tuple[Expression, ...] = ()
    charges: tuple[Expression, ...] = ()
    chirality: FieldChirality = FieldChirality.NONE
    field_role: FieldRole = FieldRole.PHYSICAL
    propagating: bool = True
    zero_mode: bool = False
    self_conjugate: bool = False
    mass_kind: FieldMassKind = FieldMassKind.LIGHT
    mass_label: Expression | None = None
    mass_indices: tuple[Expression, ...] = ()

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

    @property
    def charge_exprs(self) -> tuple[Expression, ...]:
        """Gauge-charge expressions stored on the field label."""

        return field_charges_from_label(self.label)

    @property
    def chirality_kind(self) -> FieldChirality:
        """Chirality stored on the field label."""

        return field_chirality_from_label(self.label)

    @property
    def role(self) -> FieldRole:
        """Physics role stored on the field label."""

        return field_role_from_label(self.label)

    @property
    def is_ghost(self) -> bool:
        """Whether this field is a ghost or anti-ghost."""

        return self.role in {FieldRole.GHOST, FieldRole.ANTI_GHOST}

    @property
    def is_goldstone(self) -> bool:
        """Whether this field is marked as a Goldstone boson."""

        return self.role is FieldRole.GOLDSTONE

    @property
    def is_background(self) -> bool:
        """Whether this field is a non-propagating background field."""

        return self.role is FieldRole.BACKGROUND

    @property
    def is_propagating(self) -> bool:
        """Whether this field participates in fluctuation bases by default."""

        return field_propagating_from_label(self.label)

    @property
    def is_zero_mode(self) -> bool:
        """Whether this field is a Matsubara zero-mode metadata field."""

        return field_zero_mode_from_label(self.label)

    def expr(self, *indices: Expression, derivatives: Iterable[Expression] = ()) -> Expression:
        """Build a Symbolica field expression."""

        return s.Field(self.label, self.type_expr, list_expr(*indices), list_expr(*tuple(derivatives)))

    def mass_expr(self) -> Expression | None:
        """Return the mass coupling expression, if one was registered."""

        return field_mass_expr_from_label(self.label)

    def _repr_latex_(self) -> str:
        return f"${latex_string(self.expr())}$"

    def _repr_html_(self) -> str:
        mass = self.mass_expr()
        mass_part = "" if mass is None else f" mass={escape(display_string(mass))}"
        role_part = "" if self.role is FieldRole.PHYSICAL else f" role={escape(self.role.value)}"
        propagation_part = "" if self.is_propagating else " non_propagating"
        return f"<code>{escape(display_string(self.expr()))}{mass_part}{role_part}{propagation_part}</code>"

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": canonical_string(self.label),
            "type": canonical_string(self.type_expr),
            "indices": [canonical_string(i) for i in field_indices_from_label(self.label)],
            "charges": [canonical_string(i) for i in field_charges_from_label(self.label)],
            "chirality": field_chirality_from_label(self.label).value,
            "field_role": field_role_from_label(self.label).value,
            "propagating": field_propagating_from_label(self.label),
            "zero_mode": field_zero_mode_from_label(self.label),
            "self_conjugate": self.is_self_conjugate,
            "mass_kind": field_mass_kind_from_label(self.label).value,
            "mass_label": canonical_string(mass_label) if (mass_label := field_mass_label_from_label(self.label)) is not None else None,
            "mass_indices": [canonical_string(i) for i in field_mass_indices_from_label(self.label)],
        }


@dataclass(frozen=True)
class ExternalDefinition:
    """Registered metadata for an external symbol imported from input data."""

    name: str
    label: Expression

    def expr(self, *args: Expression) -> Expression:
        """Build this external symbol as an atom or function call."""

        return self.label(*args) if args else self.label

    def _repr_latex_(self) -> str:
        return f"${latex_string(self.expr())}$"

    def _repr_html_(self) -> str:
        return f"<code>{escape(display_string(self.expr()))}</code>"

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": canonical_string(self.label),
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


class CGTensorHandle:
    """Callable handle for constructing a registered Clebsch-Gordan tensor."""

    def __init__(self, theory: Theory, definition: CGTensorDefinition) -> None:
        self.theory = theory
        self.definition = definition

    @property
    def label(self) -> Expression:
        """Symbolica label used internally for this CG tensor."""

        return self.definition.label

    @property
    def name(self) -> str:
        """User-facing CG tensor name."""

        return self.definition.name

    def __call__(self, *indices: Expression) -> Expression:
        """Build this CG tensor with concrete indices."""

        return self.definition.expr(*indices)

    def _repr_latex_(self) -> str:
        return self.definition._repr_latex_()

    def _repr_html_(self) -> str:
        return self.definition._repr_html_()


class ExternalHandle:
    """Callable handle for constructing a registered external symbol."""

    def __init__(self, theory: Theory, definition: ExternalDefinition) -> None:
        self.theory = theory
        self.definition = definition

    @property
    def label(self) -> Expression:
        """Symbolica label used internally for this external symbol."""

        return self.definition.label

    @property
    def name(self) -> str:
        """User-facing external-symbol name."""

        return self.definition.name

    def __call__(self, *args: Expression) -> Expression:
        """Build this external symbol as an atom or function call."""

        return self.definition.expr(*args)

    def _repr_latex_(self) -> str:
        return self.definition._repr_latex_()

    def _repr_html_(self) -> str:
        return self.definition._repr_html_()


__all__ = [
    "BuiltinIndexType",
    "CGTensorDefinition",
    "CGTensorHandle",
    "CouplingDefinition",
    "CouplingHandle",
    "CouplingSelfConjugate",
    "DynkinInput",
    "ExternalDefinition",
    "ExternalHandle",
    "FieldChirality",
    "FieldDefinition",
    "FieldHandle",
    "FieldMassKind",
    "FieldRole",
    "FieldVariation",
    "GroupKind",
    "IndexType",
    "JsonValue",
    "MassKindInput",
    "MassSpec",
    "RepresentationDefinition",
    "RepresentationLabelInput",
    "RepresentationReality",
    "cg_representations_from_label",
    "cg_source_from_label",
    "cg_tensor_from_label",
    "coupling_diagonal_flags_from_label",
    "coupling_eft_order_from_label",
    "coupling_indices_from_label",
    "coupling_self_conjugate_from_label",
    "coupling_symmetries_from_label",
    "coupling_thermal_power_counting_from_label",
    "coupling_unitary_from_label",
    "field_charges_from_label",
    "field_chirality_from_label",
    "field_indices_from_label",
    "field_mass_expr_from_label",
    "field_mass_indices_from_label",
    "field_mass_kind_from_label",
    "field_mass_label_from_label",
    "field_propagating_from_label",
    "field_role_from_label",
    "field_self_conjugate_from_label",
    "field_type_from_label",
    "field_zero_mode_from_label",
    "representation_dimension_from_label",
    "representation_dynkin_from_label",
    "representation_group_from_label",
    "representation_reality_from_label",
]
