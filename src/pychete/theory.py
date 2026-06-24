from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, TypeAlias

from symbolica import Expression, S

from .expr import as_int, is_head, list_expr
from .symbols import SymbolDataKey, SymbolRole, canonical_string, display_string, expression_from_canonical, latex_string, s, safe_symbol_name, symbol_data

if TYPE_CHECKING:
    from .matching import (
        FluctuationBasis,
        FluctuationBasisItem,
        FluctuationOperator,
        HeavyScalarSolution,
        MatchingResult,
        OneLoopSetup,
    )


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
        self.representation_labels: dict[str, Expression] = {}
        self.representations: dict[str, RepresentationDefinition] = {}
        self.cg_tensors: dict[str, CGTensorDefinition] = {}
        self.define_index_type(BuiltinIndexType.LORENTZ)

    def symbol(
        self,
        name: str,
        *,
        role: SymbolRole | str = SymbolRole.LABEL,
        data: dict[str, Any] | None = None,
        tags: Iterable[str] = (),
    ) -> Expression:
        """Return a theory-owned Symbolica symbol with pychete metadata."""

        role_name = role.value if isinstance(role, SymbolRole) else role
        key = f"{role_name}:{name}"
        if key not in self._symbols:
            symbol_name = f"{safe_symbol_name(role_name)}_{safe_symbol_name(name)}"
            symbol_tags = list(dict.fromkeys([SymbolRole.PROJECT.value, role_name, *(_local_tag_name(str(tag)) for tag in tags)]))
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
                tags=symbol_tags,
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
            data = _normalized_restored_symbol_data(role, _decode_symbol_data_value(raw_data))
            raw_tags = entry.get("tags", [])
            tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []
            if role == SymbolRole.FIELD.value:
                field_role = FieldRole.from_user(data.get(SymbolDataKey.FIELD_ROLE.value, FieldRole.PHYSICAL.value))
                tags.extend(
                    _field_symbol_tags(
                        field_role,
                        bool(data.get(SymbolDataKey.PROPAGATING.value, 1)),
                        bool(data.get(SymbolDataKey.ZERO_MODE.value, 0)),
                    )
                )
            elif role == SymbolRole.GROUP.value:
                tags.extend(
                    _group_symbol_tags(
                        GroupKind.from_user(data.get(SymbolDataKey.GROUP_KIND.value, GroupKind.GLOBAL.value)),
                        bool(data.get(SymbolDataKey.GROUP_ABELIAN.value, 0)),
                    )
                )
            elif role == SymbolRole.REPRESENTATION.value:
                group = str(data.get(SymbolDataKey.REPRESENTATION_GROUP.value, "unknown"))
                reality = RepresentationReality.from_user(data.get(SymbolDataKey.REPRESENTATION_REALITY.value, RepresentationReality.UNKNOWN.value))
                tags.extend(_representation_symbol_tags(group, reality))
            elif role == SymbolRole.CG_TENSOR.value:
                reps = data.get(SymbolDataKey.CG_REPRESENTATIONS.value, [])
                rank = len(reps) if isinstance(reps, list) else 0
                tags.extend(_cg_tensor_symbol_tags(rank))
            symbol = self.symbol(name, role=role, data=data, tags=tags)
            if role == SymbolRole.REPRESENTATION.value:
                self.representation_labels[name] = symbol
            expected = entry.get("symbol")
            if expected is not None and canonical_string(symbol) != expected:
                raise ValueError(f"Symbol manifest restored {role}:{name} as {canonical_string(symbol)}, expected {expected}")
            expected_tags = set(str(tag) for tag in entry.get("tags", []))
            actual_tags = set(symbol.get_tags())
            if expected_tags and not expected_tags <= actual_tags:
                raise ValueError(f"Symbol manifest restored {role}:{name} with tags {sorted(actual_tags)}, missing {sorted(expected_tags - actual_tags)}")

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
        self_conjugate: CouplingSelfConjugate | Iterable[int] = False,
        symmetries: Iterable[Expression] = (),
        diagonal: bool | Iterable[bool] | None = None,
        thermal_power_counting: int = 1,
        unitary: bool = False,
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
            Whether the coupling is treated as self-conjugate, or a
            one-based index permutation describing conjugation.
        symmetries:
            Coupling index symmetries, usually built with
            ``s.SymmetricIndices``, ``s.AntisymmetricIndices``,
            ``s.SymmetricPermutation``, or ``s.AntisymmetricPermutation``.
        diagonal:
            Per-index flags for diagonal flavor restrictions.
        thermal_power_counting:
            Thermal power-counting metadata mirrored from Matchete models.
        unitary:
            Whether this coupling is a unitary matrix in flavor space.
        """

        if name in self.couplings:
            return CouplingHandle(self, self.couplings[name])
        indices_tuple = tuple(indices)
        if eft_order < 0:
            raise ValueError("coupling EFT order must be non-negative")
        if any(bool(index == s.Lorentz) for index in indices_tuple):
            raise ValueError("Lorentz cannot be a coupling index representation")
        self_conjugate_spec = _normalize_coupling_self_conjugate(self_conjugate)
        if isinstance(self_conjugate_spec, tuple):
            if len(self_conjugate_spec) != len(indices_tuple):
                raise ValueError("coupling self-conjugation permutation must have the same length as coupling indices")
            if sorted(self_conjugate_spec) != list(range(1, len(indices_tuple) + 1)):
                raise ValueError("coupling self-conjugation permutation must be one-based and complete")
        diagonal_tuple = _normalize_diagonal_coupling(diagonal, len(indices_tuple))
        symmetries_tuple = tuple(symmetries)
        if unitary:
            if len(indices_tuple) != 2 or not bool(indices_tuple[0] == indices_tuple[1]):
                raise ValueError("only matrix couplings with two identical index representations can be unitary")
            if eft_order != 0:
                raise ValueError("unitary couplings must have EFT order 0")
        label = self.symbol(
            name,
            role=SymbolRole.COUPLING,
            data={
                SymbolDataKey.NAME.value: name,
                SymbolDataKey.INDICES.value: list(indices_tuple),
                SymbolDataKey.EFT_ORDER.value: eft_order,
                SymbolDataKey.SELF_CONJUGATE.value: list(self_conjugate_spec) if isinstance(self_conjugate_spec, tuple) else int(self_conjugate_spec),
                SymbolDataKey.SYMMETRIES.value: list(symmetries_tuple),
                SymbolDataKey.DIAGONAL_COUPLING.value: list(diagonal_tuple),
                SymbolDataKey.THERMAL_POWER_COUNTING.value: thermal_power_counting,
                SymbolDataKey.UNITARY.value: int(unitary),
            },
        )
        definition = CouplingDefinition(
            name=name,
            label=label,
            indices=indices_tuple,
            eft_order=eft_order,
            self_conjugate=self_conjugate_spec,
            symmetries=symmetries_tuple,
            diagonal=diagonal_tuple,
            thermal_power_counting=thermal_power_counting,
            unitary=unitary,
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
        chirality: FieldChirality | str | bool | None = FieldChirality.NONE,
        field_role: FieldRole | str | None = None,
        propagating: bool | None = None,
        zero_mode: bool = False,
        self_conjugate: bool = False,
        mass: int | MassSpec | None = None,
    ) -> FieldHandle:
        """Register or return a field.

        ``type_expr`` is usually one of ``s.Scalar``, ``s.Fermion``, or a
        vector type such as ``s.Vector(group_symbol)``. ``charges`` stores
        U(1)-charge expressions such as ``theory.group_charge("U1Y", 1/2)``.
        The ``mass`` argument may be ``0``/``None`` or
        ``(FieldMassKind, coupling_name[, indices])``.
        """

        if name in self.fields:
            return FieldHandle(self, self.fields[name])

        chirality_kind = FieldChirality.from_user(chirality)
        if chirality_kind is not FieldChirality.NONE and (not bool(type_expr == s.Fermion) or self_conjugate):
            raise ValueError("chirality can only be set for non-self-conjugate fermion fields")
        inferred_role = FieldRole.from_type(type_expr)
        role_kind = inferred_role if field_role is None else FieldRole.from_user(field_role)
        if inferred_role in {FieldRole.GHOST, FieldRole.ANTI_GHOST} and role_kind is not inferred_role:
            raise ValueError("ghost field types must use the matching ghost field role")
        if role_kind in {FieldRole.GHOST, FieldRole.ANTI_GHOST} and role_kind is not inferred_role:
            raise ValueError("ghost field roles must use s.Ghost or s.AntiGhost as the field type")
        if role_kind is FieldRole.GOLDSTONE and not bool(type_expr == s.Scalar):
            raise ValueError("Goldstone fields must be scalar fields")
        if zero_mode and bool(type_expr == s.Fermion):
            raise ValueError("fermion fields cannot be marked as zero modes")
        if propagating is None:
            propagating_flag = role_kind is not FieldRole.BACKGROUND
        else:
            propagating_flag = bool(propagating)
            if role_kind is FieldRole.BACKGROUND and propagating_flag:
                raise ValueError("background fields must be non-propagating")
        if not propagating_flag and mass not in (None, 0):
            raise ValueError("non-propagating fields cannot carry mass metadata")

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
            SymbolDataKey.FIELD_ROLE.value: role_kind.value,
            SymbolDataKey.INDICES.value: list(indices_tuple),
            SymbolDataKey.CHARGES.value: list(charges_tuple),
            SymbolDataKey.CHIRALITY.value: chirality_kind.value,
            SymbolDataKey.PROPAGATING.value: int(propagating_flag),
            SymbolDataKey.ZERO_MODE.value: int(zero_mode),
            SymbolDataKey.SELF_CONJUGATE.value: int(self_conjugate),
            SymbolDataKey.MASS_KIND.value: mass_kind.value,
            SymbolDataKey.MASS_INDICES.value: list(mass_indices),
        }
        if mass_label is not None:
            field_data[SymbolDataKey.MASS_LABEL.value] = mass_label
        definition = FieldDefinition(
            name=name,
            label=self.symbol(
                name,
                role=SymbolRole.FIELD,
                data=field_data,
                tags=_field_symbol_tags(role_kind, propagating_flag, zero_mode),
            ),
            type=type_expr,
            indices=indices_tuple,
            charges=charges_tuple,
            chirality=chirality_kind,
            field_role=role_kind,
            propagating=propagating_flag,
            zero_mode=zero_mode,
            self_conjugate=self_conjugate,
            mass_kind=mass_kind,
            mass_label=mass_label,
            mass_indices=mass_indices,
        )
        self.fields[name] = definition
        return FieldHandle(self, definition)

    def field_handle(self, name: str) -> FieldHandle:
        """Return the callable handle for a registered field."""

        return FieldHandle(self, self.fields[name])

    def coupling_handle(self, name: str) -> CouplingHandle:
        """Return the callable handle for a registered coupling."""

        return CouplingHandle(self, self.couplings[name])

    def cg_tensor_handle(self, name: str) -> CGTensorHandle:
        """Return the callable handle for a registered CG tensor."""

        return CGTensorHandle(self, self.cg_tensors[name])

    def define_cg_tensor(
        self,
        name: str,
        representations: Iterable[Expression],
        *,
        tensor: Expression | None = None,
        source: str | None = None,
    ) -> CGTensorHandle:
        """Register a Clebsch-Gordan tensor over group representations.

        The registered label is theory-owned Symbolica data. Calling the
        returned handle creates ``CG(label, List(indices...))`` expressions,
        which can later be lowered to spenso tensor structures by the backend
        adapter.
        """

        if name in self.cg_tensors:
            return CGTensorHandle(self, self.cg_tensors[name])
        representations_tuple = tuple(representations)
        if not representations_tuple:
            raise ValueError("CG tensors must declare at least one representation")
        for representation in representations_tuple:
            self.representation_definition(representation)
        cg_data: dict[str, Any] = {
            SymbolDataKey.NAME.value: name,
            SymbolDataKey.CG_REPRESENTATIONS.value: list(representations_tuple),
            SymbolDataKey.CG_SOURCE.value: source or "",
        }
        if tensor is not None:
            cg_data[SymbolDataKey.CG_TENSOR.value] = tensor
        label = self.symbol(
            name,
            role=SymbolRole.CG_TENSOR,
            data=cg_data,
            tags=_cg_tensor_symbol_tags(len(representations_tuple)),
        )
        definition = CGTensorDefinition(
            name=name,
            label=label,
            representations=representations_tuple,
            tensor=tensor,
            source=source,
        )
        self.cg_tensors[name] = definition
        return CGTensorHandle(self, definition)

    def _builtin_cg_tensor_label(self, kind: str, group: str, representation: Expression | None = None) -> Expression:
        representation_name = None if representation is None else self.representation_definition(representation).name
        return self.cg_tensor_handle(_builtin_cg_tensor_name(kind, group, representation_name)).label

    def _define_builtin_cg_tensors_for_group(self, group: str) -> None:
        fund = self.define_representation(group, "fund")
        adj = self.define_representation(group, "adj")
        self.define_cg_tensor(
            _builtin_cg_tensor_name("gen", group, "fund"),
            [adj, fund, s.Bar(fund)],
            source="builtin:gen",
        )
        self.define_cg_tensor(
            _builtin_cg_tensor_name("gen", group, "adj"),
            [adj, adj, adj],
            source="builtin:gen",
        )
        self.define_cg_tensor(
            _builtin_cg_tensor_name("fStruct", group),
            [adj, adj, adj],
            source="builtin:fStruct",
        )
        self.define_cg_tensor(
            _builtin_cg_tensor_name("dSym", group),
            [adj, adj, adj],
            source="builtin:dSym",
        )
        self.define_cg_tensor(
            _builtin_cg_tensor_name("del", group, "fund"),
            [fund, s.Bar(fund)],
            source="builtin:del",
        )
        self.define_cg_tensor(
            _builtin_cg_tensor_name("del", group, "adj"),
            [adj, adj],
            source="builtin:del",
        )
        fund_dimension = self.representation_dimension(fund)
        if isinstance(fund_dimension, int) and fund_dimension > 1:
            self.define_cg_tensor(
                _builtin_cg_tensor_name("eps", group),
                [fund for _ in range(fund_dimension)],
                source="builtin:eps",
            )

    def define_gauge_group(self, name: str, group_type: Expression, coupling: str, field: str) -> None:
        """Register a gauge group, its coupling, and its vector field."""

        if name in self.groups:
            raise ValueError(f"Group {name!r} is already registered")
        coupling_handle = self.define_coupling(coupling, eft_order=0, self_conjugate=True)
        abelian = bool(group_type == s.U1)
        group_symbol = self.symbol(
            name,
            role=SymbolRole.GROUP,
            data={
                SymbolDataKey.NAME.value: name,
                SymbolDataKey.GROUP_KIND.value: GroupKind.GAUGE.value,
                SymbolDataKey.GROUP_TYPE.value: group_type,
                SymbolDataKey.GROUP_ABELIAN.value: int(abelian),
                SymbolDataKey.GROUP_COUPLING.value: coupling,
                SymbolDataKey.GROUP_FIELD.value: field,
            },
            tags=_group_symbol_tags(GroupKind.GAUGE, abelian),
        )
        vector = self.define_field(field, s.Vector(group_symbol), self_conjugate=True, mass=0)
        self.groups[name] = _group_entry(
            name=name,
            group_type=group_type,
            group_kind=GroupKind.GAUGE,
            coupling=coupling_handle.name,
            field=vector.name,
        )
        if not abelian:
            self._define_builtin_cg_tensors_for_group(name)

    def define_global_group(self, name: str, group_type: Expression) -> Expression:
        """Register a global symmetry group and return its group symbol."""

        if name in self.groups:
            raise ValueError(f"Group {name!r} is already registered")
        abelian = bool(group_type == s.U1)
        group_symbol = self.symbol(
            name,
            role=SymbolRole.GROUP,
            data={
                SymbolDataKey.NAME.value: name,
                SymbolDataKey.GROUP_KIND.value: GroupKind.GLOBAL.value,
                SymbolDataKey.GROUP_TYPE.value: group_type,
                SymbolDataKey.GROUP_ABELIAN.value: int(abelian),
            },
            tags=_group_symbol_tags(GroupKind.GLOBAL, abelian),
        )
        self.groups[name] = _group_entry(
            name=name,
            group_type=group_type,
            group_kind=GroupKind.GLOBAL,
        )
        if not abelian:
            self._define_builtin_cg_tensors_for_group(name)
        return group_symbol

    def define_representation(
        self,
        group: str,
        label: RepresentationLabelInput,
        *,
        dynkin: DynkinInput = (),
        dimension: int | None = None,
        reality: RepresentationReality | str | int | None = RepresentationReality.UNKNOWN,
    ) -> Expression:
        """Register a representation of a gauge or global group.

        ``label`` may be one of the built-in representation labels
        ``"fund"``/``s.fund`` or ``"adj"``/``s.adj``, or a model-specific
        label such as ``"quad"`` from Matchete's ``DefineRepresentation``.
        Model-specific labels become theory-owned Symbolica symbols carrying
        representation tags and data.
        """

        if group not in self.groups:
            raise KeyError(f"Unknown group {group!r}")
        dynkin_tuple = _normalize_dynkin(dynkin)
        if dimension is not None and dimension <= 0:
            raise ValueError("representation dimension must be positive when provided")
        reality_kind = RepresentationReality.from_user(reality)
        label_expr: Expression | None
        if isinstance(label, str):
            label_name = safe_symbol_name(label)
            if label_name == "fund":
                label_expr = s.fund
            elif label_name == "adj":
                label_expr = s.adj
            else:
                label_expr = None
        else:
            label_expr = label
            label_name = _representation_name_for_label(label_expr)

        inferred_dimension, inferred_reality = _infer_representation_metadata(
            _group_type_from_entry(self.groups[group]),
            label_expr,
            dynkin_tuple,
        )
        if dimension is None:
            dimension = inferred_dimension
        if reality_kind is RepresentationReality.UNKNOWN and inferred_reality is not RepresentationReality.UNKNOWN:
            reality_kind = inferred_reality

        if label_expr is None:
            label_expr = self.symbol(
                label_name,
                role=SymbolRole.REPRESENTATION,
                data={
                    SymbolDataKey.NAME.value: label_name,
                    SymbolDataKey.REPRESENTATION_GROUP.value: group,
                    SymbolDataKey.REPRESENTATION_DYNKIN.value: list(dynkin_tuple),
                    SymbolDataKey.REPRESENTATION_DIMENSION.value: dimension if dimension is not None else -1,
                    SymbolDataKey.REPRESENTATION_REALITY.value: reality_kind.value,
                },
                tags=_representation_symbol_tags(group, reality_kind),
            )
            self.representation_labels[label_name] = label_expr
        else:
            role = symbol_data(label_expr, SymbolDataKey.ROLE)
            if role == SymbolRole.REPRESENTATION.value:
                self.representation_labels[label_name] = label_expr

        group_symbol = self.symbol(group, role=SymbolRole.GROUP)
        rep_expr = group_symbol(label_expr)
        key = canonical_string(rep_expr)
        if key in self.representations:
            return self.representations[key].expr

        definition = RepresentationDefinition(
            name=label_name,
            group=group,
            label=label_expr,
            expr=rep_expr,
            dynkin=dynkin_tuple,
            dimension=dimension,
            reality=reality_kind,
        )
        self.representations[key] = definition
        return rep_expr

    def representation_definition(self, representation: Expression) -> RepresentationDefinition:
        """Return metadata for a registered representation expression.

        A syntactic ``Bar(rep)`` wrapper resolves to the same underlying
        definition, allowing model fields with conjugate representation indices
        such as ``Bar@SU3c[fund]`` to reuse the registered metadata.
        """

        key = canonical_string(representation)
        if key in self.representations:
            return self.representations[key]
        if is_head(representation, s.Bar) and len(representation) == 1:
            inner_key = canonical_string(representation[0])
            if inner_key in self.representations:
                return self.representations[inner_key]
        raise KeyError(f"Unknown representation {key!r}")

    def representation_dimension(self, representation: Expression) -> int | None:
        """Return the dimension metadata for a registered representation."""

        return self.representation_definition(representation).dimension_value

    def representation_reality(self, representation: Expression) -> RepresentationReality:
        """Return the reality metadata for a registered representation."""

        return self.representation_definition(representation).reality_kind

    def is_conjugate_representation(self, representation: Expression) -> bool:
        """Return whether ``representation`` is a syntactic ``Bar(rep)`` wrapper."""

        if not is_head(representation, s.Bar) or len(representation) != 1:
            return False
        try:
            self.representation_definition(representation[0])
        except KeyError:
            return False
        return True

    def group_charge(self, group: str, charge: Expression | int | float) -> Expression:
        """Build a U(1)-charge expression for a registered gauge or global group."""

        if group not in self.groups:
            raise KeyError(f"Unknown group {group!r}")
        charge_expr = charge if isinstance(charge, Expression) else Expression.num(charge)
        return self.symbol(group, role=SymbolRole.GROUP)(charge_expr)

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
        for item in field_names_or_handles:
            handle = item if isinstance(item, FieldHandle) else self.field_handle(item)
            definition = handle.definition
            if not definition.is_propagating:
                raise ValueError(f"Free Lagrangians are not defined for non-propagating field {definition.name!r}")
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
                strength = s.FieldStrength(definition.label, list_expr(mu, nu), list_expr(), list_expr())
                out = out - strength**2 / 4
            elif bool(type_expr == s.Fermion):
                mass = self.mass_expr(definition)
                dirac = Expression.I * s.NCM(s.Bar(field_expr), s.Gamma(mu), handle(derivatives=[mu]))
                if mass is not None:
                    dirac = dirac - mass * s.NCM(s.Bar(field_expr), field_expr)
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

    def fluctuation_operator(
        self,
        lagrangian: Expression,
        fields: FluctuationBasis | Iterable[FluctuationBasisItem] | None = None,
    ) -> FluctuationOperator:
        """Extract the algebraic fluctuation-operator Hessian for fields.

        When ``fields`` is omitted, pychete discovers a deterministic
        fluctuation basis from field atoms in ``lagrangian``.
        """

        from .matching import fluctuation_operator

        return fluctuation_operator(self, lagrangian, fields)

    def fluctuation_basis(self, lagrangian: Expression) -> FluctuationBasis:
        """Discover heavy and light fluctuation fields in a Lagrangian."""

        from .matching import fluctuation_basis

        return fluctuation_basis(self, lagrangian)

    def one_loop_setup(
        self,
        lagrangian: Expression,
        *,
        eft_order: int = 6,
        max_trace_order: int = 2,
        include_light_only: bool = False,
    ) -> OneLoopSetup:
        """Prepare native-backed one-loop matching inputs without evaluating loops."""

        from .matching import one_loop_setup

        return one_loop_setup(
            self,
            lagrangian,
            eft_order=eft_order,
            max_trace_order=max_trace_order,
            include_light_only=include_light_only,
        )

    def match(self, lagrangian: Expression, *, eft_order: int = 6, loop_order: int = 0) -> Expression | MatchingResult:
        """Match a Lagrangian through the requested loop order.

        ``loop_order=0`` preserves pychete's existing tree-level heavy-scalar
        matching behavior and returns an expression. ``loop_order=1`` is the
        reserved public entry point for the one-loop matching engine and raises
        ``OneLoopMatchingNotImplementedError`` until that engine is complete.
        """

        from .matching import match_one_loop, match_tree

        if loop_order == 0:
            return match_tree(self, lagrangian, eft_order=eft_order)
        if loop_order == 1:
            return match_one_loop(self, lagrangian, eft_order=eft_order)
        raise ValueError("loop_order must be 0 or 1")

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
            "representations": {name: value.to_json() for name, value in sorted(self.representations.items())},
            "cg_tensors": {name: value.to_json() for name, value in sorted(self.cg_tensors.items())},
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
        theory.groups = {}
        for name, data in obj.get("groups", {}).items():
            group_type = theory._parse_registered_expression(str(data["type"]))
            group_kind = GroupKind.from_user(data.get("kind", GroupKind.GAUGE.value))
            theory.groups[str(name)] = _group_entry(
                name=str(data["name"]),
                group_type=group_type,
                group_kind=group_kind,
                coupling=str(data["coupling"]) if "coupling" in data else None,
                field=str(data["field"]) if "field" in data else None,
            )
        theory.representations = {}
        for _, data in obj.get("representations", {}).items():
            theory.define_representation(
                str(data["group"]),
                theory._parse_registered_expression(str(data["label"])),
                dynkin=[theory._parse_registered_expression(x) for x in data.get("dynkin", [])],
                dimension=data.get("dimension"),
                reality=data.get("reality", RepresentationReality.UNKNOWN.value),
            )
        for name, data in obj.get("cg_tensors", {}).items():
            tensor_text = data.get("tensor")
            theory.define_cg_tensor(
                str(name),
                [theory._parse_registered_expression(x) for x in data.get("representations", [])],
                tensor=theory._parse_registered_expression(str(tensor_text)) if tensor_text is not None else None,
                source=str(data["source"]) if data.get("source") is not None else None,
            )
        for name, data in obj.get("couplings", {}).items():
            self_conjugate_data = data.get("self_conjugate", False)
            if isinstance(self_conjugate_data, list):
                self_conjugate: CouplingSelfConjugate = tuple(int(item) for item in self_conjugate_data)
            else:
                self_conjugate = bool(self_conjugate_data)
            theory.define_coupling(
                name,
                indices=[theory._parse_registered_expression(x) for x in data.get("indices", [])],
                eft_order=int(data.get("eft_order", 0)),
                self_conjugate=self_conjugate,
                symmetries=[theory._parse_registered_expression(x) for x in data.get("symmetries", [])],
                diagonal=[bool(flag) for flag in data.get("diagonal", [])] if "diagonal" in data else None,
                thermal_power_counting=int(data.get("thermal_power_counting", 1)),
                unitary=bool(data.get("unitary", False)),
            )
        for name, data in obj.get("fields", {}).items():
            type_expr = theory._parse_registered_expression(data["type"])
            mass_label = data.get("mass_label")
            mass = None
            if mass_label is not None:
                mass_kind = FieldMassKind.from_user(data.get("mass_kind", FieldMassKind.LIGHT.value))
                mass_indices = [theory._parse_registered_expression(x) for x in data.get("mass_indices", [])]
                mass_name = _coupling_name_for_label(theory, str(mass_label))
                mass = (mass_kind, mass_name, mass_indices)
            theory.define_field(
                name,
                type_expr,
                indices=[theory._parse_registered_expression(x) for x in data.get("indices", [])],
                charges=[theory._parse_registered_expression(x) for x in data.get("charges", [])],
                chirality=FieldChirality.from_user(data.get("chirality", FieldChirality.NONE.value)),
                field_role=FieldRole.from_user(data.get("field_role", FieldRole.from_type(type_expr).value)),
                propagating=bool(data.get("propagating", True)),
                zero_mode=bool(data.get("zero_mode", False)),
                self_conjugate=bool(data.get("self_conjugate", False)),
                mass=mass,
            )
        return theory
