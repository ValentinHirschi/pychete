from __future__ import annotations

import json
from itertools import count
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Iterator, Literal, Mapping, Sequence

from symbolica import Expression, Replacement, S

from .expr import (
    bar_field_inner,
    bar_field_pattern,
    bar_field_strength_inner,
    bar_field_strength_pattern,
    covariant_derivative_commutator_pattern,
    field_derivatives,
    field_label,
    field_pattern,
    field_strength_derivatives,
    field_strength_label,
    field_strength_pattern,
    field_strength_with_derivatives,
    field_with_derivatives,
    is_bar_field,
    is_bar_field_strength,
    is_head,
    is_zero,
    list_expr,
    list_items,
    matching_subexpressions,
    sum_expr,
)
from .symbols import SymbolDataKey, SymbolRole, canonical_string, expression_from_canonical, s, safe_symbol_name, symbol_data

if TYPE_CHECKING:
    from .matching import (
        FluctuationBasis,
        FluctuationBasisItem,
        FluctuationOperator,
        OneLoopSetup,
    )
    from .matching_options import OneLoopMatchOptions
    from .matching_results import MatchingResult
    from .tree_matching import HeavyScalarSolution
from .theory_metadata import (
    BuiltinIndexType,
    CGTensorDefinition,
    CGTensorHandle,
    CouplingDefinition,
    CouplingHandle,
    CouplingSelfConjugate,
    DynkinInput,
    ExternalDefinition,
    ExternalHandle,
    ExternalKind,
    FieldChirality,
    FieldDefinition,
    FieldHandle,
    FieldMassKind,
    FieldRole,
    FieldVariation,
    FreeLagConvention,
    GroupKind,
    IndexType,
    JsonValue,
    MassKindInput,
    MassSpec,
    RepresentationDefinition,
    RepresentationLabelInput,
    RepresentationReality,
    _builtin_cg_tensor_name,
    _cg_tensor_symbol_tags,
    _coupling_name_for_label,
    _decode_symbol_data_value,
    _encode_symbol_data_value,
    _external_symbol_tags,
    _field_symbol_tags,
    _group_entry,
    _group_symbol_tags,
    _group_type_from_entry,
    _infer_representation_metadata,
    _index_type_name,
    _local_tag_name,
    _normalize_coupling_self_conjugate,
    _normalize_diagonal_coupling,
    _normalize_dynkin,
    _normalized_restored_symbol_data,
    _representation_name_for_label,
    _representation_symbol_tags,
    _symbol_data_payload,
    _symbol_manifest_sort_key,
    cg_representations_from_label,
    cg_source_from_label,
    cg_tensor_from_label,
    coupling_diagonal_flags_from_label,
    coupling_eft_order_from_label,
    coupling_indices_from_label,
    coupling_self_conjugate_from_label,
    coupling_symmetries_from_label,
    coupling_thermal_power_counting_from_label,
    coupling_unitary_from_label,
    field_charges_from_label,
    field_chirality_from_label,
    field_indices_from_label,
    field_mass_expr_from_label,
    field_mass_indices_from_label,
    field_mass_kind_from_label,
    field_mass_label_from_label,
    field_propagating_from_label,
    field_role_from_label,
    field_self_conjugate_from_label,
    field_type_from_label,
    field_zero_mode_from_label,
    external_basis_from_label,
    external_eft_order_from_label,
    external_indices_from_label,
    external_kind_from_label,
    external_operator_from_label,
    representation_dimension_from_label,
    representation_dynkin_from_label,
    representation_group_from_label,
    representation_reality_from_label,
)

_COVARIANT_DERIVATIVE_OUTPUT_INDEX_KIND = 0
_COVARIANT_DERIVATIVE_ADJOINT_INDEX_KIND = 1
CovariantDerivativeCommutatorMode = Literal["inversions", "all_distinct"]


def _adjacent_covariant_derivative_inversion(derivatives: tuple[Expression, ...]) -> int | None:
    for index, (left, right) in enumerate(zip(derivatives, derivatives[1:], strict=False)):
        if not is_head(left, s.Index) or not is_head(right, s.Index):
            continue
        if canonical_string(left) > canonical_string(right):
            return index
    return None


def _adjacent_covariant_derivative_distinct_pair(derivatives: tuple[Expression, ...]) -> int | None:
    for index, (left, right) in enumerate(zip(derivatives, derivatives[1:], strict=False)):
        if not is_head(left, s.Index) or not is_head(right, s.Index):
            continue
        if not bool(left == right):
            return index
    return None


def _adjacent_covariant_derivative_distinct_positions(derivatives: tuple[Expression, ...]) -> tuple[int, ...]:
    positions: list[int] = []
    for index, (left, right) in enumerate(zip(derivatives, derivatives[1:], strict=False)):
        if not is_head(left, s.Index) or not is_head(right, s.Index):
            continue
        if not bool(left == right):
            positions.append(index)
    return tuple(positions)


def _adjacent_covariant_derivative_swap_position(
    derivatives: tuple[Expression, ...],
    *,
    mode: CovariantDerivativeCommutatorMode,
) -> int | None:
    if mode == "inversions":
        return _adjacent_covariant_derivative_inversion(derivatives)
    if mode == "all_distinct":
        return _adjacent_covariant_derivative_distinct_pair(derivatives)
    raise ValueError(f"unknown covariant derivative commutator mode {mode!r}")


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
        self.externals: dict[str, ExternalDefinition] = {}
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
            if role_name == SymbolRole.EXTERNAL.value:
                symbol_data_payload[SymbolDataKey.NAME.value] = name
                symbol_data_payload[SymbolDataKey.EXTERNAL_KIND.value] = ExternalKind.GENERIC.value
                symbol_data_payload[SymbolDataKey.INDICES.value] = []
                symbol_data_payload[SymbolDataKey.EFT_ORDER.value] = 0
                symbol_data_payload[SymbolDataKey.BASIS.value] = ""
            if data:
                symbol_data_payload.update(data)
            if role_name == SymbolRole.EXTERNAL.value:
                symbol_tags.extend(
                    _external_symbol_tags(
                        ExternalKind.from_user(symbol_data_payload.get(SymbolDataKey.EXTERNAL_KIND.value)),
                        str(symbol_data_payload.get(SymbolDataKey.BASIS.value) or ""),
                        name=name,
                    )
                )
                symbol_tags = list(dict.fromkeys(symbol_tags))
            self._symbols[key] = s.user(
                self.name,
                symbol_name,
                tags=symbol_tags,
                data=symbol_data_payload,
            )
        if role_name == SymbolRole.EXTERNAL.value and name not in self.externals:
            symbol = self._symbols[key]
            self.externals[name] = ExternalDefinition(
                name=name,
                label=symbol,
                external_kind=external_kind_from_label(symbol),
                indices=external_indices_from_label(symbol),
                eft_order=external_eft_order_from_label(symbol),
                basis=external_basis_from_label(symbol),
                operator=external_operator_from_label(symbol),
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
            elif role == SymbolRole.EXTERNAL.value:
                tags.extend(
                    _external_symbol_tags(
                        ExternalKind.from_user(data.get(SymbolDataKey.EXTERNAL_KIND.value)),
                        str(data.get(SymbolDataKey.BASIS.value) or ""),
                        name=name,
                    )
                )
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
        mass_dimension: int | float | None = None,
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
        mass_dimension:
            Optional canonical mass dimension of the coupling. Store this when
            the dimension is known; leave it unset rather than guessing.
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
        if mass_dimension is not None and (
            isinstance(mass_dimension, bool) or not isinstance(mass_dimension, (int, float))
        ):
            raise ValueError("coupling mass dimension must be numeric")
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
                **({SymbolDataKey.DIMENSION.value: mass_dimension} if mass_dimension is not None else {}),
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
            mass_dimension=mass_dimension,
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
                mass_dimension=1,
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

    def external_handle(self, name: str) -> ExternalHandle:
        """Return the callable handle for a registered external symbol."""

        return ExternalHandle(self, self.externals[name])

    def define_external(
        self,
        name: str,
        *,
        external_kind: ExternalKind | str | None = ExternalKind.GENERIC,
        indices: Iterable[Expression] = (),
        eft_order: int = 0,
        basis: str | None = None,
        operator: Expression | None = None,
    ) -> ExternalHandle:
        """Register or return an external symbol owned by this theory.

        External symbols represent imported names that are intentionally not
        pychete fields, couplings, groups, representations, or CG tensors. The
        primary use is Matchete-derived Wilson-condition labels and helper
        symbols that must still round-trip with Symbolica tags and symbol data.
        ``operator`` may store the EFT operator monomial associated with a
        Wilson-like matching target.
        """

        kind = ExternalKind.from_user(external_kind)
        indices_tuple = tuple(indices)
        basis_value = basis or ""
        if eft_order < 0:
            raise ValueError("external EFT order must be non-negative")
        if name in self.externals:
            definition = self.externals[name]
            requested_generic = (
                kind is ExternalKind.GENERIC
                and not indices_tuple
                and eft_order == 0
                and not basis_value
                and operator is None
            )
            if requested_generic:
                return ExternalHandle(self, definition)
            existing_operator = definition.operator_expr
            existing_matches = (
                definition.kind is kind
                and [canonical_string(index) for index in definition.index_exprs]
                == [canonical_string(index) for index in indices_tuple]
                and definition.order == eft_order
                and (definition.basis_name or "") == basis_value
                and (
                    (existing_operator is None and operator is None)
                    or (
                        existing_operator is not None
                        and operator is not None
                        and canonical_string(existing_operator) == canonical_string(operator)
                    )
                )
            )
            if existing_matches:
                return ExternalHandle(self, definition)
            raise ValueError(
                f"external symbol {name!r} is already registered with incompatible metadata; "
                "register Wilson/external metadata before parsing expressions that use it"
            )
        label = self.symbol(
            name,
            role=SymbolRole.EXTERNAL,
            data={
                SymbolDataKey.NAME.value: name,
                SymbolDataKey.EXTERNAL_KIND.value: kind.value,
                SymbolDataKey.INDICES.value: list(indices_tuple),
                SymbolDataKey.EFT_ORDER.value: eft_order,
                SymbolDataKey.BASIS.value: basis_value,
                **({SymbolDataKey.OPERATOR.value: operator} if operator is not None else {}),
            },
            tags=_external_symbol_tags(kind, basis_value, name=name),
        )
        definition = ExternalDefinition(
            name=name,
            label=label,
            external_kind=kind,
            indices=indices_tuple,
            eft_order=eft_order,
            basis=basis_value or None,
            operator=operator,
        )
        self.externals[name] = definition
        return ExternalHandle(self, definition)

    def define_wilson_coefficient(
        self,
        name: str,
        *,
        indices: Iterable[Expression] = (),
        eft_order: int = 0,
        basis: str | None = None,
        operator: Expression | None = None,
    ) -> ExternalHandle:
        """Register a Wilson-coefficient target as a theory-owned external.

        ``operator`` stores the basis monomial whose coefficient should be
        projected for this Wilson target when matching conditions are extracted
        from an EFT Lagrangian. Raw Wilson coefficients are not assigned to a
        named basis by default; use ``define_wilson_coefficient_from_basis``,
        ``define_wilson_coefficient_from_registered_basis``, or a thin
        basis-specific convenience helper when basis metadata is intended.
        """

        return self.define_external(
            name,
            external_kind=ExternalKind.WILSON_COEFFICIENT,
            indices=indices,
            eft_order=eft_order,
            basis=basis,
            operator=operator,
        )

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
        coupling_handle = self.define_coupling(coupling, eft_order=0, mass_dimension=0, self_conjugate=True)
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

    def _group_symbol_for_charge(self, charge: Expression) -> Expression | None:
        for group_name in self.groups:
            group_symbol = self.symbol(group_name, role=SymbolRole.GROUP)
            if is_head(charge, group_symbol):
                return group_symbol
        return None

    def _abelian_gauge_connection(self, definition: FieldDefinition) -> Expression:
        """Return the scalarized Abelian gauge connection for ``definition``.

        The current matching implementation represents vector components as a
        scalarized field atom. Non-Abelian covariant derivatives therefore stay
        delegated to the upcoming idenso/spenso-backed group-algebra slice.
        """

        terms: list[Expression] = []
        for charge in definition.charge_exprs:
            group_symbol = self._group_symbol_for_charge(charge)
            if group_symbol is None:
                continue
            group_kind = GroupKind.from_user(str(symbol_data(group_symbol, SymbolDataKey.GROUP_KIND, GroupKind.GLOBAL.value)))
            if group_kind is not GroupKind.GAUGE or not bool(
                symbol_data(group_symbol, SymbolDataKey.GROUP_ABELIAN, 0)
            ):
                continue
            if len(charge) != 1:
                raise ValueError(f"Gauge charge {canonical_string(charge)} must carry exactly one charge value")
            coupling_name = symbol_data(group_symbol, SymbolDataKey.GROUP_COUPLING)
            field_name = symbol_data(group_symbol, SymbolDataKey.GROUP_FIELD)
            if not isinstance(coupling_name, str) or not isinstance(field_name, str):
                raise ValueError(f"Gauge group {canonical_string(group_symbol)} is missing coupling/vector metadata")
            if coupling_name not in self.couplings:
                raise KeyError(f"Gauge group {canonical_string(group_symbol)} references unknown coupling {coupling_name!r}")
            if field_name not in self.fields:
                raise KeyError(f"Gauge group {canonical_string(group_symbol)} references unknown vector field {field_name!r}")
            terms.append(charge[0] * self.coupling_handle(coupling_name)() * self.field_handle(field_name)())
        return sum_expr(terms).expand()

    def non_abelian_gauge_generator_insertion(
        self,
        field: Expression,
        field_index: int,
        *,
        output_index: Expression,
        adjoint_index: Expression,
        lorentz_index: Expression | None = None,
        conjugate_field: bool = False,
    ) -> Expression:
        """Build the non-Abelian ``g V T`` insertion for one indexed field.

        ``field`` must be a concrete ``Field`` expression whose
        ``field_index`` slot transforms in a registered non-Abelian gauge
        representation. The returned expression is
        ``g * V(..., adjoint_index) * CG(gen, adjoint, output, input_dual)
        * field(output)`` for unbarred fields. For barred fields, the
        generator acts on the conjugate slot as
        ``CG(gen, adjoint, input, output_dual) * Bar(field(output))`` so the
        resulting fund/dual contractions remain visible to native idenso and
        spenso colour algebra. The conventional covariant-derivative sign and
        factor of ``I`` are left to the caller.
        """

        self._validate_registered_expression(field)
        if not is_head(field, s.Field):
            raise ValueError(f"Expected a Field expression, got {canonical_string(field)}")
        indices = list(list_items(field[2]))
        if field_index < 0 or field_index >= len(indices):
            raise IndexError(f"Field index slot {field_index} is out of range for {canonical_string(field)}")
        input_index = indices[field_index]
        if not is_head(input_index, s.Index) or len(input_index) != 2:
            raise ValueError(f"Field index slot {field_index} is not an Index expression: {canonical_string(input_index)}")
        input_representation = input_index[1]
        representation = self.representation_definition(input_representation)
        group_entry = self.groups.get(representation.group)
        if group_entry is None:
            raise KeyError(f"Representation {canonical_string(input_representation)} belongs to unknown group {representation.group!r}")
        group_kind = GroupKind.from_user(str(group_entry.get("kind", GroupKind.GLOBAL.value)))
        if group_kind is not GroupKind.GAUGE or bool(group_entry.get("abelian", False)):
            raise ValueError(f"Representation {canonical_string(input_representation)} is not a non-Abelian gauge representation")
        group_symbol = self.symbol(representation.group, role=SymbolRole.GROUP)
        coupling_name = symbol_data(group_symbol, SymbolDataKey.GROUP_COUPLING)
        vector_name = symbol_data(group_symbol, SymbolDataKey.GROUP_FIELD)
        if not isinstance(coupling_name, str) or not isinstance(vector_name, str):
            raise ValueError(f"Gauge group {representation.group!r} is missing coupling/vector symbol data")
        generator_name = _builtin_cg_tensor_name("gen", representation.group, representation.name)
        if generator_name not in self.cg_tensors:
            raise KeyError(
                f"Gauge representation {canonical_string(input_representation)} has no registered generator "
                f"CG tensor {generator_name!r}"
            )
        generator = self.cg_tensor_handle(generator_name)
        generator_reps = generator.definition.representation_exprs
        if len(generator_reps) != 3:
            raise ValueError(f"Generator CG tensor {generator.name!r} must have rank 3")
        if not bool(input_representation == generator_reps[1]):
            raise ValueError(
                f"Generator insertion currently expects field index representation "
                f"{canonical_string(generator_reps[1])}, got {canonical_string(input_representation)}"
            )
        adjoint_representation = generator_reps[0]
        if not is_head(adjoint_index, s.Index) or len(adjoint_index) != 2:
            raise ValueError(f"Adjoint index must be an Index expression: {canonical_string(adjoint_index)}")
        if not bool(adjoint_index[1] == adjoint_representation):
            raise ValueError(
                f"Adjoint index has representation {canonical_string(adjoint_index[1])}, "
                f"expected {canonical_string(adjoint_representation)}"
            )
        if not is_head(output_index, s.Index) or len(output_index) != 2:
            raise ValueError(f"Output index must be an Index expression: {canonical_string(output_index)}")
        if not bool(output_index[1] == generator_reps[1]):
            raise ValueError(
                f"Output index has representation {canonical_string(output_index[1])}, "
                f"expected {canonical_string(generator_reps[1])}"
            )
        indices[field_index] = output_index
        transformed_field = s.Field(field[0], field[1], list_expr(*indices), field[3])
        field_factor = s.Bar(transformed_field) if conjugate_field else transformed_field
        generator_factor = self._non_abelian_generator_factor(
            generator,
            generator_reps,
            adjoint_index,
            input_index,
            output_index,
            conjugate_field=conjugate_field,
        )
        vector_indices = (adjoint_index,) if lorentz_index is None else (lorentz_index, adjoint_index)
        return (
            self.coupling_handle(coupling_name)()
            * self.field_handle(vector_name)(*vector_indices)
            * generator_factor
            * field_factor
        )

    def _non_abelian_generator_factor(
        self,
        generator: CGTensorHandle,
        generator_reps: tuple[Expression, ...],
        adjoint_index: Expression,
        input_index: Expression,
        output_index: Expression,
        *,
        conjugate_field: bool,
    ) -> Expression:
        if conjugate_field:
            output_dual_index = s.Index(output_index[0], generator_reps[2])
            return generator(adjoint_index, input_index, output_dual_index)
        input_dual_index = s.Index(input_index[0], generator_reps[2])
        return generator(adjoint_index, output_index, input_dual_index)

    def covariant_derivative_commutator(
        self,
        field: Expression,
        left_index: Expression,
        right_index: Expression,
    ) -> Expression:
        """Return ``[D_left, D_right]`` acting on a field-like atom.

        The convention matches pychete's first-derivative expansion
        ``D = partial - I * connection``. Unbarred fields and field strengths
        therefore receive ``-I`` times the gauge field-strength insertion,
        while barred payloads receive ``+I`` times the corresponding conjugate
        insertion. Abelian charged fields use registered
        charge/coupling/vector metadata, Abelian field-strength bodies lower to
        zero, and non-Abelian indices use registered generator CG tensors. This
        is a structural CDE primitive for later field-strength/basis-reduction
        matching stages.
        """

        self._validate_registered_expression(field)
        conjugate_field = is_bar_field(field) or is_bar_field_strength(field)
        base_atom = self._covariant_derivative_commutator_base_atom(field, conjugate_field=conjugate_field)
        if is_head(base_atom, s.Field):
            return self._covariant_derivative_commutator(
                base_atom,
                left_index,
                right_index,
                conjugate_field=conjugate_field,
                index_counter=count(),
            )
        if is_head(base_atom, s.FieldStrength):
            return self._field_strength_covariant_derivative_commutator(
                base_atom,
                left_index,
                right_index,
                conjugate_field=conjugate_field,
                index_counter=count(),
            )
        raise ValueError(f"Expected a Field, Bar[Field], FieldStrength, or Bar[FieldStrength], got {canonical_string(field)}")

    def _covariant_derivative_commutator(
        self,
        base_field: Expression,
        left_index: Expression,
        right_index: Expression,
        *,
        conjugate_field: bool,
        index_counter: Iterator[int],
        field_strength_derivatives: Iterable[Expression] = (),
        include_gauge_coupling: bool = True,
    ) -> Expression:
        derivative_tuple = tuple(field_strength_derivatives)
        definition = self._field_definition_for_label(field_label(base_field))
        insertion = (
            self._abelian_field_strength_insertions(
                definition,
                base_field,
                left_index,
                right_index,
                conjugate_field=conjugate_field,
                field_strength_derivatives=derivative_tuple,
                include_gauge_coupling=include_gauge_coupling,
            )
            + self._non_abelian_field_strength_insertions(
                base_field,
                left_index,
                right_index,
                conjugate_field=conjugate_field,
                index_counter=index_counter,
                field_strength_derivatives=derivative_tuple,
                include_gauge_coupling=include_gauge_coupling,
            )
        )
        if bool(insertion == Expression.num(0)):
            return insertion
        sign = Expression.I if conjugate_field else -Expression.I
        return (sign * insertion).expand()

    def expand_covariant_derivative_commutators(
        self,
        expr: Expression,
        *,
        include_gauge_coupling: bool = True,
    ) -> Expression:
        """Expand formal covariant-derivative commutators in ``expr``.

        The formal head
        ``CovariantDerivativeCommutator(left, right, Field(...))`` is a compact
        CDE marker for ``[D_left, D_right]``. This method rewrites such markers
        with native Symbolica replacement rules and
        :meth:`covariant_derivative_commutator`, producing registered
        ``FieldStrength`` insertions. Non-field bodies are left as formal
        commutators so later product-rule or basis-reduction stages can handle
        them deliberately. Generated Matchete-style CDE/Wilson-line numerators
        can set ``include_gauge_coupling=False`` because their field-strength
        and Warsaw-basis coupling normalizations are carried separately.
        """

        self._validate_registered_expression(expr)
        pattern = covariant_derivative_commutator_pattern()
        if not bool(expr.matches(pattern)):
            return expr
        index_counter = count()

        def commutator_replacement(match: dict[Expression, Expression]) -> Expression:
            left_index = match[s.CovariantCommutatorLeftWildcard]
            right_index = match[s.CovariantCommutatorRightWildcard]
            body = match[s.CovariantCommutatorBodyWildcard]
            if is_head(body, s.Field) or is_bar_field(body):
                conjugate_field = is_bar_field(body)
                base_field = bar_field_inner(body) if conjugate_field else body
                return self._covariant_derivative_commutator(
                    base_field,
                    left_index,
                    right_index,
                    conjugate_field=conjugate_field,
                    index_counter=index_counter,
                    include_gauge_coupling=include_gauge_coupling,
                )
            if is_head(body, s.FieldStrength) or is_bar_field_strength(body):
                conjugate_field = is_bar_field_strength(body)
                base_strength = bar_field_strength_inner(body) if conjugate_field else body
                return self._field_strength_covariant_derivative_commutator(
                    base_strength,
                    left_index,
                    right_index,
                    conjugate_field=conjugate_field,
                    index_counter=index_counter,
                    include_gauge_coupling=include_gauge_coupling,
                )
            return s.CovariantDerivativeCommutator(left_index, right_index, body)

        return expr.replace(pattern, commutator_replacement, rhs_cache_size=0).expand()

    def covariant_derivative_commutator_identities(self, expr: Expression) -> tuple[Expression, ...]:
        """Return Matchete-style adjacent covariant-derivative commutation identities.

        Matchete's ``IdentitiesCDCommutation`` does not rewrite an operator in
        place; it generates one identity for every adjacent, distinct pair of
        covariant derivative slots on each differentiated field or field
        strength. This helper mirrors that identity source for pychete
        expressions while keeping the symbolic work in Symbolica: field-like
        atoms are discovered with tag-restricted patterns and each linear atom
        contribution is extracted with native ``Expression.coefficient(...)``.

        The returned identities have the form
        ``coefficient * (CommuteCDs(atom, n) - atom)``. Atoms that appear
        nonlinearly in their coefficient are skipped, because replacing a
        single occurrence requires a later operator-class row-reduction
        representation. Use :meth:`emit_covariant_derivative_commutators` when
        an equality-preserving expression rewrite is wanted instead.
        """

        self._validate_registered_expression(expr)
        identities: list[Expression] = []
        seen: set[str] = set()
        for atom, conjugate_field in self._covariant_derivative_identity_atoms(expr):
            coefficient = expr.coefficient(atom).expand()
            if is_zero(coefficient):
                continue
            if not is_zero(coefficient.coefficient(atom)):
                continue
            base_atom = self._covariant_derivative_commutator_base_atom(atom, conjugate_field=conjugate_field)
            derivatives = self._covariant_derivative_atom_derivatives(base_atom)
            for position in _adjacent_covariant_derivative_distinct_positions(derivatives):
                commuted = self._commuted_covariant_derivative_atom_at_position(
                    atom,
                    conjugate_field=conjugate_field,
                    swap_position=position,
                )
                identity = (coefficient * (commuted - atom)).expand()
                if is_zero(identity):
                    continue
                key = canonical_string(identity)
                if key in seen:
                    continue
                seen.add(key)
                identities.append(identity)
        return tuple(identities)

    def covariant_derivative_commutator_normal_form(
        self,
        expr: Expression,
        *,
        basis: Sequence[Expression],
        preferred: Sequence[Expression] = (),
        max_basis_terms: int = 64,
        max_identities: int = 128,
    ) -> Expression:
        """Reduce ``expr`` with local Matchete-style commutator identities.

        This is a bounded Green-basis building block. It generates local
        adjacent-pair identities with
        :meth:`covariant_derivative_commutator_identities`, then delegates the
        linear normal-form solve to Symbolica through
        :func:`pychete.green_basis.linear_identity_normal_form`. The caller
        supplies the explicit local operator ``basis`` and any ``preferred``
        representatives, so pychete does not guess Matchete's full
        operator-class scoring rules in Python.
        """

        from .green_basis import linear_identity_normal_form

        self._validate_registered_expression(expr)
        identities = self.covariant_derivative_commutator_identities(expr)
        return linear_identity_normal_form(
            expr,
            identities,
            basis=basis,
            preferred=preferred,
            max_basis_terms=max_basis_terms,
            max_identities=max_identities,
        )

    def covariant_derivative_commutator_local_normal_form(
        self,
        expr: Expression,
        *,
        preferred: Sequence[Expression] = (),
        max_basis_terms: int = 64,
        max_identities: int = 128,
    ) -> Expression:
        """Reduce ``expr`` with generated commutator identities and a local basis.

        This is the bounded automatic-basis counterpart of
        :meth:`covariant_derivative_commutator_normal_form`. It generates
        Matchete-style adjacent-pair commutator identities for ``expr``,
        collects the local operator monomials appearing in ``expr`` and those
        identities, and delegates the linear solve to Symbolica.

        ``preferred`` still remains explicit; this helper does not try to
        reproduce Matchete's full Green-basis scoring policy in Python.
        """

        from .green_basis import linear_identity_normal_form_from_identities

        self._validate_registered_expression(expr)
        identities = self.covariant_derivative_commutator_identities(expr)
        return linear_identity_normal_form_from_identities(
            expr,
            identities,
            preferred=preferred,
            max_basis_terms=max_basis_terms,
            max_identities=max_identities,
        )

    def _covariant_derivative_identity_atoms(self, expr: Expression) -> tuple[tuple[Expression, bool], ...]:
        field_pat = field_pattern()
        bar_pat = bar_field_pattern()
        strength_pat = field_strength_pattern()
        bar_strength_pat = bar_field_strength_pattern()
        field_label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
        strength_label_is_tagged = s.FieldStrengthLabelWildcard.req_tag(SymbolRole.FIELD.value)

        atoms: list[tuple[Expression, bool]] = []
        seen: set[str] = set()
        for pattern, condition, conjugate_field in (
            (bar_pat, field_label_is_tagged, True),
            (field_pat, field_label_is_tagged, False),
            (bar_strength_pat, strength_label_is_tagged, True),
            (strength_pat, strength_label_is_tagged, False),
        ):
            for atom in matching_subexpressions(expr, pattern, condition):
                if conjugate_field:
                    if not (is_bar_field(atom) or is_bar_field_strength(atom)):
                        continue
                    base_atom = self._covariant_derivative_commutator_base_atom(atom, conjugate_field=True)
                else:
                    base_atom = atom
                derivatives = self._covariant_derivative_atom_derivatives(base_atom)
                if not _adjacent_covariant_derivative_distinct_positions(derivatives):
                    continue
                key = canonical_string(atom)
                if key in seen:
                    continue
                seen.add(key)
                atoms.append((atom, conjugate_field))
        return tuple(atoms)

    def emit_covariant_derivative_commutators(
        self,
        expr: Expression,
        *,
        max_passes: int = 1,
        mode: CovariantDerivativeCommutatorMode = "inversions",
    ) -> Expression:
        """Emit formal commutators by commuting adjacent derivative slots.

        Registered ``Field``/``Bar[Field]`` and
        ``FieldStrength``/``Bar[FieldStrength]`` atoms with adjacent
        covariant derivative indices selected by ``mode`` are rewritten with
        the identity ``D_a D_b X = D_b D_a X + [D_a,D_b] X``. The emitted
        ``CovariantDerivativeCommutator`` markers are intentionally left
        formal; call :meth:`expand_covariant_derivative_commutators` to lower
        field-body markers to ``FieldStrength`` insertions. Prefix derivatives
        are kept as explicit ``CD(...)`` wrappers so existing Symbolica
        replacement passes can apply product rules later without forcing a
        global expansion here.

        The default ``mode="inversions"`` only commutes adjacent indices that
        are out of canonical order, so repeated passes safely canonicalize
        longer derivative lists. ``mode="all_distinct"`` mirrors Matchete's
        ``CommuteCDs`` identity source for adjacent distinct covariant
        derivative pairs and is intentionally limited to one pass to avoid
        immediately commuting the same pair back on the next pass.
        """

        self._validate_registered_expression(expr)
        if max_passes < 0:
            raise ValueError("max_passes must be non-negative")
        if mode not in ("inversions", "all_distinct"):
            raise ValueError(f"unknown covariant derivative commutator mode {mode!r}")
        if mode == "all_distinct" and max_passes > 1:
            raise ValueError('mode="all_distinct" supports only one bounded pass')
        out = expr
        for _ in range(max_passes):
            updated = self._emit_covariant_derivative_commutator_pass(out, mode=mode)
            if bool(updated == out):
                return updated
            out = updated
        return out

    def _emit_covariant_derivative_commutator_pass(
        self,
        expr: Expression,
        *,
        mode: CovariantDerivativeCommutatorMode,
    ) -> Expression:
        field_pat = field_pattern()
        bar_pat = bar_field_pattern()
        strength_pat = field_strength_pattern()
        bar_strength_pat = bar_field_strength_pattern()
        field_label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
        strength_label_is_tagged = s.FieldStrengthLabelWildcard.req_tag(SymbolRole.FIELD.value)
        commutator_pat = covariant_derivative_commutator_pattern()

        if not bool(expr.matches(field_pat, field_label_is_tagged)) and not bool(
            expr.matches(strength_pat, strength_label_is_tagged)
        ):
            return expr

        protect_commutator_replacements: list[Replacement] = []
        restore_commutator_replacements: list[Replacement] = []
        for atom in matching_subexpressions(expr, commutator_pat):
            key = s.CovariantDerivativeProtectedCommutator(Expression.num(len(restore_commutator_replacements)))
            protect_commutator_replacements.append(Replacement(atom, key))
            restore_commutator_replacements.append(Replacement(key, atom))

        out = expr
        if protect_commutator_replacements:
            out = out.replace_multiple(protect_commutator_replacements)
        has_field = bool(out.matches(field_pat, field_label_is_tagged))
        has_strength = bool(out.matches(strength_pat, strength_label_is_tagged))
        if not has_field and not has_strength:
            if restore_commutator_replacements:
                return out.replace_multiple(restore_commutator_replacements)
            return out

        protect_bar_replacements: list[Replacement] = []
        restore_bar_replacements: list[Replacement] = []
        for atom in matching_subexpressions(out, bar_pat, field_label_is_tagged):
            key = s.CovariantDerivativeProtectedBar(Expression.num(len(restore_bar_replacements)))
            protect_bar_replacements.append(Replacement(atom, key))
            restore_bar_replacements.append(
                Replacement(key, self._commuted_covariant_derivative_atom(atom, conjugate_field=True, mode=mode))
            )
        for atom in matching_subexpressions(out, bar_strength_pat, strength_label_is_tagged):
            key = s.CovariantDerivativeProtectedBar(Expression.num(len(restore_bar_replacements)))
            protect_bar_replacements.append(Replacement(atom, key))
            restore_bar_replacements.append(
                Replacement(key, self._commuted_covariant_derivative_atom(atom, conjugate_field=True, mode=mode))
            )

        def field_replacement(match: dict[Expression, Expression]) -> Expression:
            atom = field_pat.replace_wildcards(match)
            return self._commuted_covariant_derivative_atom(atom, conjugate_field=False, mode=mode)

        def strength_replacement(match: dict[Expression, Expression]) -> Expression:
            atom = strength_pat.replace_wildcards(match)
            return self._commuted_covariant_derivative_atom(atom, conjugate_field=False, mode=mode)

        if protect_bar_replacements:
            out = out.replace_multiple(protect_bar_replacements)
        out = out.replace(field_pat, field_replacement, field_label_is_tagged, rhs_cache_size=0)
        out = out.replace(strength_pat, strength_replacement, strength_label_is_tagged, rhs_cache_size=0)
        if restore_bar_replacements:
            out = out.replace_multiple(restore_bar_replacements)
        if restore_commutator_replacements:
            out = out.replace_multiple(restore_commutator_replacements)
        return out

    def _commuted_covariant_derivative_atom(
        self,
        atom: Expression,
        *,
        conjugate_field: bool,
        mode: CovariantDerivativeCommutatorMode,
    ) -> Expression:
        base_atom = self._covariant_derivative_commutator_base_atom(atom, conjugate_field=conjugate_field)
        derivatives = self._covariant_derivative_atom_derivatives(base_atom)
        swap_position = _adjacent_covariant_derivative_swap_position(derivatives, mode=mode)
        if swap_position is None:
            return atom
        return self._commuted_covariant_derivative_atom_at_position(
            atom,
            conjugate_field=conjugate_field,
            swap_position=swap_position,
        )

    def _commuted_covariant_derivative_atom_at_position(
        self,
        atom: Expression,
        *,
        conjugate_field: bool,
        swap_position: int,
    ) -> Expression:
        base_atom = self._covariant_derivative_commutator_base_atom(atom, conjugate_field=conjugate_field)
        derivatives = self._covariant_derivative_atom_derivatives(base_atom)
        if swap_position < 0 or swap_position + 1 >= len(derivatives):
            raise ValueError(f"covariant derivative swap position {swap_position} is out of range")
        left_index = derivatives[swap_position]
        right_index = derivatives[swap_position + 1]
        if not is_head(left_index, s.Index) or not is_head(right_index, s.Index):
            return atom
        if bool(left_index == right_index):
            return atom
        prefix = derivatives[:swap_position]
        suffix = derivatives[swap_position + 2 :]
        swapped_derivatives = (
            *prefix,
            right_index,
            left_index,
            *suffix,
        )
        swapped_payload = self._covariant_derivative_atom_with_derivatives(base_atom, swapped_derivatives)
        swapped_atom = s.Bar(swapped_payload) if conjugate_field else swapped_payload
        commutator_body = self._covariant_derivative_atom_with_derivatives(base_atom, suffix)
        if conjugate_field:
            commutator_body = s.Bar(commutator_body)
        commutator = s.CovariantDerivativeCommutator(left_index, right_index, commutator_body)
        if prefix:
            commutator = s.CD(list_expr(*prefix), commutator)
        return swapped_atom + commutator

    def _covariant_derivative_commutator_base_atom(self, atom: Expression, *, conjugate_field: bool) -> Expression:
        if not conjugate_field:
            return atom
        if is_bar_field(atom):
            return bar_field_inner(atom)
        if is_bar_field_strength(atom):
            return bar_field_strength_inner(atom)
        raise ValueError(f"Expected Bar[Field] or Bar[FieldStrength], got {canonical_string(atom)}")

    def _covariant_derivative_atom_derivatives(self, atom: Expression) -> tuple[Expression, ...]:
        if is_head(atom, s.Field):
            return field_derivatives(atom)
        if is_head(atom, s.FieldStrength):
            return field_strength_derivatives(atom)
        raise ValueError(f"Expected Field or FieldStrength expression, got {canonical_string(atom)}")

    def _covariant_derivative_atom_with_derivatives(
        self,
        atom: Expression,
        derivatives: Iterable[Expression],
    ) -> Expression:
        if is_head(atom, s.Field):
            return field_with_derivatives(atom, derivatives)
        if is_head(atom, s.FieldStrength):
            return field_strength_with_derivatives(atom, derivatives)
        raise ValueError(f"Expected Field or FieldStrength expression, got {canonical_string(atom)}")

    def _field_definition_for_label(self, label: Expression) -> FieldDefinition:
        name = symbol_data(label, SymbolDataKey.NAME)
        if isinstance(name, str) and name in self.fields and bool(self.fields[name].label == label):
            return self.fields[name]
        label_name = symbol_data(label, SymbolDataKey.LABEL)
        if isinstance(label_name, str) and label_name in self.fields and bool(self.fields[label_name].label == label):
            return self.fields[label_name]
        key = canonical_string(label)
        for definition in self.fields.values():
            if canonical_string(definition.label) == key:
                return definition
        raise KeyError(f"Theory {self.name!r} has no field label {key!r}")

    def _abelian_field_strength_insertions(
        self,
        definition: FieldDefinition,
        field: Expression,
        left_index: Expression,
        right_index: Expression,
        *,
        conjugate_field: bool,
        field_strength_derivatives: Iterable[Expression],
        include_gauge_coupling: bool = True,
    ) -> Expression:
        field_factor = s.Bar(field) if conjugate_field else field
        derivative_tuple = tuple(field_strength_derivatives)
        terms: list[Expression] = []
        for charge in definition.charge_exprs:
            group_symbol = self._group_symbol_for_charge(charge)
            if group_symbol is None:
                continue
            group_kind = GroupKind.from_user(
                str(symbol_data(group_symbol, SymbolDataKey.GROUP_KIND, GroupKind.GLOBAL.value))
            )
            if group_kind is not GroupKind.GAUGE or not bool(
                symbol_data(group_symbol, SymbolDataKey.GROUP_ABELIAN, 0)
            ):
                continue
            if len(charge) != 1:
                raise ValueError(f"Gauge charge {canonical_string(charge)} must carry exactly one charge value")
            coupling_name = symbol_data(group_symbol, SymbolDataKey.GROUP_COUPLING)
            vector_name = symbol_data(group_symbol, SymbolDataKey.GROUP_FIELD)
            if not isinstance(coupling_name, str) or not isinstance(vector_name, str):
                raise ValueError(f"Gauge group {canonical_string(group_symbol)} is missing coupling/vector metadata")
            if coupling_name not in self.couplings:
                raise KeyError(
                    f"Gauge group {canonical_string(group_symbol)} references unknown coupling {coupling_name!r}"
                )
            if vector_name not in self.fields:
                raise KeyError(
                    f"Gauge group {canonical_string(group_symbol)} references unknown vector field {vector_name!r}"
                )
            strength = s.FieldStrength(
                self.fields[vector_name].label,
                list_expr(left_index, right_index),
                list_expr(),
                list_expr(*derivative_tuple),
            )
            coupling = self.coupling_handle(coupling_name)() if include_gauge_coupling else Expression.num(1)
            terms.append(charge[0] * coupling * strength * field_factor)
        return sum_expr(terms).expand()

    def _non_abelian_field_strength_insertions(
        self,
        field: Expression,
        left_index: Expression,
        right_index: Expression,
        *,
        conjugate_field: bool,
        index_counter: Iterator[int],
        field_strength_derivatives: Iterable[Expression],
        include_gauge_coupling: bool = True,
    ) -> Expression:
        derivative_tuple = tuple(field_strength_derivatives)
        terms: list[Expression] = []
        field_indices = list(list_items(field[2]))
        for field_index, input_index in enumerate(field_indices):
            if not is_head(input_index, s.Index) or len(input_index) != 2:
                continue
            try:
                representation = self.representation_definition(input_index[1])
            except KeyError:
                continue
            group_entry = self.groups.get(representation.group)
            if group_entry is None:
                continue
            group_kind = GroupKind.from_user(str(group_entry.get("kind", GroupKind.GLOBAL.value)))
            if group_kind is not GroupKind.GAUGE or bool(group_entry.get("abelian", False)):
                continue
            group_symbol = self.symbol(representation.group, role=SymbolRole.GROUP)
            coupling_name = symbol_data(group_symbol, SymbolDataKey.GROUP_COUPLING)
            vector_name = symbol_data(group_symbol, SymbolDataKey.GROUP_FIELD)
            if not isinstance(coupling_name, str) or not isinstance(vector_name, str):
                raise ValueError(f"Gauge group {representation.group!r} is missing coupling/vector symbol data")
            generator_name = _builtin_cg_tensor_name("gen", representation.group, representation.name)
            if generator_name not in self.cg_tensors:
                raise KeyError(
                    f"Gauge representation {canonical_string(input_index[1])} has no registered generator "
                    f"CG tensor {generator_name!r}"
                )
            generator = self.cg_tensor_handle(generator_name)
            generator_reps = generator.definition.representation_exprs
            if len(generator_reps) != 3:
                raise ValueError(f"Generator CG tensor {generator.name!r} must have rank 3")
            if not bool(input_index[1] == generator_reps[1]):
                raise ValueError(
                    f"Generator insertion currently expects field index representation "
                    f"{canonical_string(generator_reps[1])}, got {canonical_string(input_index[1])}"
                )
            index_number = next(index_counter)
            output_index = self._covariant_derivative_generated_index(
                index_number,
                _COVARIANT_DERIVATIVE_OUTPUT_INDEX_KIND,
                generator_reps[1],
                prefix="covariant_commutator",
            )
            adjoint_index = self._covariant_derivative_generated_index(
                index_number,
                _COVARIANT_DERIVATIVE_ADJOINT_INDEX_KIND,
                generator_reps[0],
                prefix="covariant_commutator",
            )
            transformed_indices = list(field_indices)
            transformed_indices[field_index] = output_index
            transformed_field = s.Field(field[0], field[1], list_expr(*transformed_indices), field[3])
            field_factor = s.Bar(transformed_field) if conjugate_field else transformed_field
            strength = s.FieldStrength(
                self.fields[vector_name].label,
                list_expr(left_index, right_index),
                list_expr(adjoint_index),
                list_expr(*derivative_tuple),
            )
            generator_factor = self._non_abelian_generator_factor(
                generator,
                generator_reps,
                adjoint_index,
                input_index,
                output_index,
                conjugate_field=conjugate_field,
            )
            coupling = self.coupling_handle(coupling_name)() if include_gauge_coupling else Expression.num(1)
            terms.append(
                coupling
                * strength
                * generator_factor
                * field_factor
            )
        return sum_expr(terms).expand()

    def _field_strength_covariant_derivative_commutator(
        self,
        base_strength: Expression,
        left_index: Expression,
        right_index: Expression,
        *,
        conjugate_field: bool,
        index_counter: Iterator[int],
        field_strength_derivatives: Iterable[Expression] = (),
        include_gauge_coupling: bool = True,
    ) -> Expression:
        insertion = self._field_strength_adjoint_insertions(
            base_strength,
            left_index,
            right_index,
            conjugate_field=conjugate_field,
            index_counter=index_counter,
            field_strength_derivatives=field_strength_derivatives,
            include_gauge_coupling=include_gauge_coupling,
        )
        if bool(insertion == Expression.num(0)):
            return insertion
        sign = Expression.I if conjugate_field else -Expression.I
        return (sign * insertion).expand()

    def _field_strength_adjoint_insertions(
        self,
        strength: Expression,
        left_index: Expression,
        right_index: Expression,
        *,
        conjugate_field: bool,
        index_counter: Iterator[int],
        field_strength_derivatives: Iterable[Expression],
        include_gauge_coupling: bool = True,
    ) -> Expression:
        derivative_tuple = tuple(field_strength_derivatives)
        definition = self._field_definition_for_label(field_strength_label(strength))
        type_expr = definition.type_expr
        if not is_head(type_expr, s.Vector) or len(type_expr) != 1:
            raise ValueError(f"FieldStrength label {definition.name!r} does not belong to a vector field")
        group_symbol = type_expr[0]
        group_name = symbol_data(group_symbol, SymbolDataKey.NAME)
        if not isinstance(group_name, str):
            raise ValueError(f"Vector field {definition.name!r} has no registered gauge-group name")
        group_entry = self.groups.get(group_name)
        if group_entry is None:
            raise KeyError(f"Theory {self.name!r} has no group {group_name!r}")
        group_kind = GroupKind.from_user(str(group_entry.get("kind", GroupKind.GLOBAL.value)))
        if group_kind is not GroupKind.GAUGE:
            return Expression.num(0)
        if bool(group_entry.get("abelian", False)):
            return Expression.num(0)
        coupling_name = symbol_data(group_symbol, SymbolDataKey.GROUP_COUPLING)
        vector_name = symbol_data(group_symbol, SymbolDataKey.GROUP_FIELD)
        if not isinstance(coupling_name, str) or not isinstance(vector_name, str):
            raise ValueError(f"Gauge group {group_name!r} is missing coupling/vector symbol data")

        terms: list[Expression] = []
        strength_indices = list(list_items(strength[2]))
        for field_index, input_index in enumerate(strength_indices):
            if not is_head(input_index, s.Index) or len(input_index) != 2:
                continue
            try:
                representation = self.representation_definition(input_index[1])
            except KeyError:
                continue
            if representation.group != group_name:
                continue
            generator_name = _builtin_cg_tensor_name("gen", group_name, representation.name)
            if generator_name not in self.cg_tensors:
                raise KeyError(
                    f"Gauge representation {canonical_string(input_index[1])} has no registered generator "
                    f"CG tensor {generator_name!r}"
                )
            generator = self.cg_tensor_handle(generator_name)
            generator_reps = generator.definition.representation_exprs
            if len(generator_reps) != 3:
                raise ValueError(f"Generator CG tensor {generator.name!r} must have rank 3")
            if not bool(input_index[1] == generator_reps[1]):
                raise ValueError(
                    f"Generator insertion currently expects field-strength index representation "
                    f"{canonical_string(generator_reps[1])}, got {canonical_string(input_index[1])}"
                )
            index_number = next(index_counter)
            output_index = self._covariant_derivative_generated_index(
                index_number,
                _COVARIANT_DERIVATIVE_OUTPUT_INDEX_KIND,
                generator_reps[1],
                prefix="covariant_commutator",
            )
            adjoint_index = self._covariant_derivative_generated_index(
                index_number,
                _COVARIANT_DERIVATIVE_ADJOINT_INDEX_KIND,
                generator_reps[0],
                prefix="covariant_commutator",
            )
            transformed_indices = list(strength_indices)
            transformed_indices[field_index] = output_index
            transformed_strength = s.FieldStrength(strength[0], strength[1], list_expr(*transformed_indices), strength[3])
            strength_factor = s.Bar(transformed_strength) if conjugate_field else transformed_strength
            source_strength = s.FieldStrength(
                self.fields[vector_name].label,
                list_expr(left_index, right_index),
                list_expr(adjoint_index),
                list_expr(*derivative_tuple),
            )
            generator_factor = self._non_abelian_generator_factor(
                generator,
                generator_reps,
                adjoint_index,
                input_index,
                output_index,
                conjugate_field=conjugate_field,
            )
            coupling = self.coupling_handle(coupling_name)() if include_gauge_coupling else Expression.num(1)
            terms.append(
                coupling
                * source_strength
                * generator_factor
                * strength_factor
            )
        return sum_expr(terms).expand()

    def _non_abelian_gauge_index_slots(self, definition: FieldDefinition) -> tuple[int, ...]:
        slots: list[int] = []
        for slot, representation_expr in enumerate(definition.indices):
            try:
                representation = self.representation_definition(representation_expr)
            except KeyError:
                continue
            group_entry = self.groups.get(representation.group)
            if group_entry is None:
                continue
            group_kind = GroupKind.from_user(str(group_entry.get("kind", GroupKind.GLOBAL.value)))
            if group_kind is GroupKind.GAUGE and not bool(group_entry.get("abelian", False)):
                slots.append(slot)
        return tuple(slots)

    def _covariant_derivative_generated_index(
        self,
        number: int,
        kind: int,
        representation: Expression,
        *,
        prefix: str = "covariant_derivative",
    ) -> Expression:
        label = self.symbol(
            f"{prefix}_{number}_{kind}",
            role=SymbolRole.INDEX,
            data={
                SymbolDataKey.NAME.value: f"{prefix}_{number}_{kind}",
            },
        )
        return self.index(label, representation)

    def _non_abelian_gauge_generator_insertions(
        self,
        field: Expression,
        *,
        conjugate_field: bool,
        index_counter: Iterator[int],
    ) -> Expression:
        derivatives = list_items(field[3])
        if len(derivatives) != 1:
            return Expression.num(0)
        derivative = derivatives[0]
        terms: list[Expression] = []
        for field_index, input_index in enumerate(list_items(field[2])):
            if not is_head(input_index, s.Index) or len(input_index) != 2:
                continue
            try:
                representation = self.representation_definition(input_index[1])
            except KeyError:
                continue
            group_entry = self.groups.get(representation.group)
            if group_entry is None:
                continue
            group_kind = GroupKind.from_user(str(group_entry.get("kind", GroupKind.GLOBAL.value)))
            if group_kind is not GroupKind.GAUGE or bool(group_entry.get("abelian", False)):
                continue
            generator_name = _builtin_cg_tensor_name("gen", representation.group, representation.name)
            if generator_name not in self.cg_tensors:
                raise KeyError(
                    f"Gauge representation {canonical_string(input_index[1])} has no registered generator "
                    f"CG tensor {generator_name!r}"
                )
            generator_reps = self.cg_tensors[generator_name].representation_exprs
            index_number = next(index_counter)
            output_index = self._covariant_derivative_generated_index(
                index_number,
                _COVARIANT_DERIVATIVE_OUTPUT_INDEX_KIND,
                generator_reps[1],
            )
            adjoint_index = self._covariant_derivative_generated_index(
                index_number,
                _COVARIANT_DERIVATIVE_ADJOINT_INDEX_KIND,
                generator_reps[0],
            )
            terms.append(
                self.non_abelian_gauge_generator_insertion(
                    field,
                    field_index,
                    output_index=output_index,
                    adjoint_index=adjoint_index,
                    lorentz_index=derivative,
                    conjugate_field=conjugate_field,
                )
            )
        return sum_expr(terms).expand()

    def expand_non_abelian_covariant_derivatives(self, expr: Expression) -> Expression:
        """Expand first-order non-Abelian covariant derivatives in ``expr``.

        The expansion is expressed with native Symbolica replacement rules over
        registered ``Field`` atoms. Each first-derivative slot of a field that
        carries a registered non-Abelian gauge representation is rewritten with
        generator insertions built by
        :meth:`non_abelian_gauge_generator_insertion`. Abelian charges are left
        to :meth:`expand_abelian_covariant_derivatives`.
        """

        self._validate_registered_expression(expr)
        index_counter = count()
        protect_bar_replacements: list[Replacement] = []
        restore_bar_replacements: list[Replacement] = []
        field_replacements: list[Replacement] = []
        for definition in self.fields.values():
            if not self._non_abelian_gauge_index_slots(definition):
                continue
            field_pat = field_pattern(definition.label)
            bar_pat = bar_field_pattern(definition.label)

            def field_replacement(
                match: dict[Expression, Expression],
                pattern: Expression = field_pat,
            ) -> Expression:
                atom = pattern.replace_wildcards(match)
                insertion = self._non_abelian_gauge_generator_insertions(
                    atom,
                    conjugate_field=False,
                    index_counter=index_counter,
                )
                if bool(insertion == Expression.num(0)):
                    return atom
                return atom - Expression.I * insertion

            for atom in matching_subexpressions(expr, bar_pat):
                if len(list_items(atom[0][3])) != 1:
                    continue
                insertion = self._non_abelian_gauge_generator_insertions(
                    atom[0],
                    conjugate_field=True,
                    index_counter=index_counter,
                )
                if bool(insertion == Expression.num(0)):
                    continue
                key = s.CovariantDerivativeProtectedBar(Expression.num(len(restore_bar_replacements)))
                protect_bar_replacements.append(Replacement(atom, key))
                restore_bar_replacements.append(Replacement(key, atom + Expression.I * insertion))

            field_replacements.append(Replacement(field_pat, field_replacement, rhs_cache_size=0))
        if not protect_bar_replacements and not field_replacements:
            return expr
        out = expr
        if protect_bar_replacements:
            out = out.replace_multiple(protect_bar_replacements)
        if field_replacements:
            out = out.replace_multiple(field_replacements)
        if restore_bar_replacements:
            out = out.replace_multiple(restore_bar_replacements)
        return out.expand()

    def expand_abelian_covariant_derivatives(self, expr: Expression) -> Expression:
        """Expand first-order Abelian covariant derivatives in ``expr``.

        Matchete-style model input can encode gauge interactions implicitly in
        derivative slots. This helper rewrites first derivatives of fields
        carrying registered Abelian gauge charges as scalarized pychete gauge
        connections, using native Symbolica replacement rules. Non-Abelian
        covariant derivatives are intentionally left untouched for the
        idenso/spenso-backed group-algebra path.
        """

        self._validate_registered_expression(expr)
        protect_bar_replacements: list[Replacement] = []
        restore_bar_replacements: list[Replacement] = []
        field_replacements: list[Replacement] = []
        for definition in self.fields.values():
            connection = self._abelian_gauge_connection(definition)
            if bool(connection == Expression.num(0)):
                continue
            field_pat = field_pattern(definition.label)
            bar_pat = bar_field_pattern(definition.label)

            def field_replacement(
                match: dict[Expression, Expression],
                pattern: Expression = field_pat,
                connection: Expression = connection,
            ) -> Expression:
                atom = pattern.replace_wildcards(match)
                if len(list_items(match[s.FieldDerivativesWildcard])) != 1:
                    return atom
                base = field_with_derivatives(atom, ())
                return atom - Expression.I * connection * base

            for atom in matching_subexpressions(expr, bar_pat):
                if len(list_items(atom[0][3])) != 1:
                    continue
                base = field_with_derivatives(atom[0], ())
                key = s.CovariantDerivativeProtectedBar(Expression.num(len(restore_bar_replacements)))
                protect_bar_replacements.append(Replacement(atom, key))
                restore_bar_replacements.append(Replacement(key, atom + Expression.I * connection * s.Bar(base)))

            field_replacements.append(Replacement(field_pat, field_replacement))
        if not protect_bar_replacements and not field_replacements:
            return expr
        out = expr
        if protect_bar_replacements:
            out = out.replace_multiple(protect_bar_replacements)
        if field_replacements:
            out = out.replace_multiple(field_replacements)
        if restore_bar_replacements:
            out = out.replace_multiple(restore_bar_replacements)
        return out.expand()

    def _vector_gauge_coupling(self, definition: FieldDefinition) -> Expression | None:
        type_expr = definition.type_expr
        if not is_head(type_expr, s.Vector) or len(type_expr) != 1:
            return None
        group_symbol = type_expr[0]
        group_kind = GroupKind.from_user(str(symbol_data(group_symbol, SymbolDataKey.GROUP_KIND, GroupKind.GLOBAL.value)))
        if group_kind is not GroupKind.GAUGE:
            return None
        coupling_name = symbol_data(group_symbol, SymbolDataKey.GROUP_COUPLING)
        if not isinstance(coupling_name, str):
            return None
        if coupling_name not in self.couplings:
            raise KeyError(f"Gauge group {canonical_string(group_symbol)} references unknown coupling {coupling_name!r}")
        return self.coupling_handle(coupling_name)()

    def free_lag(
        self,
        *field_names_or_handles: str | FieldHandle,
        convention: FreeLagConvention | str = FreeLagConvention.PYCHETE,
    ) -> Expression:
        """Build the free Lagrangian for registered fields.

        Each argument may be either a field name or a ``FieldHandle``. The
        returned Symbolica expression is independent of the theory object and
        can be stored or transformed separately. The default pychete convention
        uses canonical gauge kinetic terms and expands Abelian gauge charges
        into scalarized current interactions. The Matchete convention keeps
        covariant-derivative interactions implicit in derivative slots and
        normalizes gauge kinetic terms with Matchete's coupling denominator.
        """

        convention_kind = FreeLagConvention.from_user(convention)
        out = Expression.num(0)
        for item in field_names_or_handles:
            handle = item if isinstance(item, FieldHandle) else self.field_handle(item)
            definition = handle.definition
            if not definition.is_propagating:
                raise ValueError(f"Free Lagrangians are not defined for non-propagating field {definition.name!r}")
            mu = self.dummy_index(0)
            field_indices = self._free_lag_field_indices(definition)
            field_expr = handle(*field_indices)
            type_expr = definition.type_expr
            is_self_conjugate = definition.is_self_conjugate
            if bool(type_expr == s.Scalar):
                mass = self.mass_expr(definition)
                connection = (
                    self._abelian_gauge_connection(definition)
                    if convention_kind is FreeLagConvention.PYCHETE
                    else Expression.num(0)
                )
                if is_self_conjugate:
                    if not bool(connection == Expression.num(0)):
                        raise ValueError("self-conjugate scalar fields cannot carry Abelian gauge charges in free_lag")
                    kinetic = handle(*field_indices, derivatives=[mu]) ** 2 / 2
                    if mass is not None:
                        kinetic = kinetic - mass**2 * field_expr**2 / 2
                else:
                    derived_field = handle(*field_indices, derivatives=[mu])
                    barred_derived_field = s.Bar(derived_field)
                    barred_field = s.Bar(field_expr)
                    kinetic = barred_derived_field * derived_field
                    if not bool(connection == Expression.num(0)):
                        kinetic = (
                            kinetic
                            + Expression.I * connection * barred_field * derived_field
                            - Expression.I * connection * barred_derived_field * field_expr
                            + connection**2 * barred_field * field_expr
                        )
                    if mass is not None:
                        kinetic = kinetic - mass**2 * barred_field * field_expr
                out = out + kinetic
            elif is_head(type_expr, s.Vector):
                nu = self.dummy_index(1)
                strength = s.FieldStrength(definition.label, list_expr(mu, nu), list_expr(), list_expr())
                gauge_coupling = self._vector_gauge_coupling(definition)
                vector_kinetic = -strength**2 / 4
                if convention_kind is FreeLagConvention.MATCHETE and gauge_coupling is not None:
                    vector_kinetic = vector_kinetic / gauge_coupling**2
                out = out + vector_kinetic
                mass = self.mass_expr(definition)
                if mass is not None:
                    out = out - mass**2 * field_expr**2 / 2
            elif bool(type_expr == s.Fermion):
                mass = self.mass_expr(definition)
                connection = (
                    self._abelian_gauge_connection(definition)
                    if convention_kind is FreeLagConvention.PYCHETE
                    else Expression.num(0)
                )
                gamma_mu = s.Gamma(mu)
                if convention_kind is FreeLagConvention.MATCHETE:
                    gamma_mu = s.DiracProduct(gamma_mu)
                dirac = Expression.I * s.NCM(s.Bar(field_expr), gamma_mu, handle(*field_indices, derivatives=[mu]))
                if not bool(connection == Expression.num(0)):
                    dirac = dirac + connection * s.NCM(s.Bar(field_expr), gamma_mu, field_expr)
                if mass is not None:
                    dirac = dirac - mass * s.NCM(s.Bar(field_expr), field_expr)
                out = out + dirac
            else:
                out = out + s.FreeLag(definition.label)
        return out

    def _free_lag_field_indices(self, definition: FieldDefinition) -> tuple[Expression, ...]:
        return tuple(
            self.dummy_index(index, representation)
            for index, representation in enumerate(field_indices_from_label(definition.label))
        )

    def derive_eom(
        self,
        lagrangian: Expression,
        field: FieldHandle | FieldDefinition | str | Expression,
        *,
        eft_order: int = 6,
        variation: FieldVariation | str = FieldVariation.AUTO,
    ) -> Expression:
        """Derive the Euler-Lagrange equation for a field.

        ``lagrangian`` must be a Symbolica expression using symbols registered
        on this theory. ``variation`` controls whether the field, its conjugate,
        or the automatic default is varied. Passing an exact ``Field`` or
        ``Bar(Field)`` expression keeps its concrete index structure in the
        variation target.
        """

        from .functional import derive_eom

        return derive_eom(self, lagrangian, field, eft_order=eft_order, variation=variation)

    def eom_replacement_rule(
        self,
        lagrangian: Expression,
        field: FieldHandle | FieldDefinition | str | Expression,
        *,
        solve_for: Expression,
        eft_order: int = 6,
        variation: FieldVariation | str = FieldVariation.AUTO,
    ) -> Replacement:
        """Return a Symbolica replacement rule from a linear EOM target.

        ``solve_for`` is isolated with native Symbolica coefficient extraction
        from the Euler-Lagrange equation for ``field``. The returned
        ``Replacement`` can be used directly as an on-shell rule in
        ``OneLoopMatchOptions.on_shell_replacements`` or
        ``MatchingResult.with_on_shell_reduction(...)``.
        """

        from .functional import eom_replacement_rule

        return eom_replacement_rule(
            self,
            lagrangian,
            field,
            solve_for=solve_for,
            eft_order=eft_order,
            variation=variation,
        )

    def eom_replacement_rules_for_expression(
        self,
        lagrangian: Expression,
        expression: Expression,
        *,
        fields: Iterable[FieldHandle | FieldDefinition | str | Expression] | None = None,
        eft_order: int = 6,
        variation: FieldVariation | str = FieldVariation.AUTO,
        min_derivative_order: int = 2,
        strict: bool = False,
    ) -> tuple[Replacement, ...]:
        """Return EOM replacement rules for derivative fields in an expression.

        Derivative targets are discovered with Symbolica pattern matching over
        registered ``Field`` and ``Bar(Field)`` atoms. Each target is then
        isolated from the corresponding Euler-Lagrange equation with native
        Symbolica coefficient extraction. By default targets that cannot be
        isolated are skipped; set ``strict=True`` to raise instead.
        """

        from .functional import eom_replacement_rules_for_expression

        return eom_replacement_rules_for_expression(
            self,
            lagrangian,
            expression,
            fields=fields,
            eft_order=eft_order,
            variation=variation,
            min_derivative_order=min_derivative_order,
            strict=strict,
        )

    def abelian_vector_eom_field_redefinition_delta(
        self,
        lagrangian: Expression,
        expression: Expression,
        *,
        fields: Iterable[FieldHandle | FieldDefinition | str | Expression] | None = None,
        strict: bool = False,
    ) -> Expression:
        """Return the Abelian-vector EOM field-redefinition companion.

        This bounded helper covers the scalar-current part of Matchete's vector
        ``EOMSimplify`` shift: after replacing Abelian field-strength
        divergences, it adds the companion generated by shifting charged scalar
        covariant derivatives.  Non-Abelian, fermion-current, and full
        iterative field-redefinition support remain separate work.
        """

        from .functional import abelian_vector_eom_field_redefinition_delta

        return abelian_vector_eom_field_redefinition_delta(
            self,
            lagrangian,
            expression,
            fields=fields,
            strict=strict,
        )

    def expose_abelian_vector_eom_currents(
        self,
        expression: Expression,
        *,
        fields: Iterable[FieldHandle | FieldDefinition | str | Expression] | None = None,
        max_candidates: int = 128,
    ) -> Expression:
        """Expose exact charged-current products as Abelian vector EOM terms.

        This bounded source-side helper rewrites current-current products that
        are exactly recognized by Symbolica coefficient extraction into the
        corresponding Abelian field-strength-divergence representative. It is
        useful before applying the vector field-redefinition consumer, and is
        deliberately conservative while the broader Matchete ``EOMSimplify``
        port is being validated.
        """

        from .functional import expose_abelian_vector_eom_currents

        return expose_abelian_vector_eom_currents(
            self,
            expression,
            fields=fields,
            max_candidates=max_candidates,
        )

    def select_terms_by_dimension_and_derivatives(
        self,
        expression: Expression,
        *,
        dimension: int | float,
        derivative_count: int,
        heavy_field_dimension: bool = True,
        require_formal_eom: bool = False,
    ) -> Expression:
        """Select terms by Matchete-style dimension and derivative count."""

        from .functional import select_terms_by_dimension_and_derivatives

        return select_terms_by_dimension_and_derivatives(
            self,
            expression,
            dimension=dimension,
            derivative_count=derivative_count,
            heavy_field_dimension=heavy_field_dimension,
            require_formal_eom=require_formal_eom,
        )

    def systematic_scalar_eom_field_redefinition_delta(
        self,
        source_lagrangian: Expression,
        *,
        eom_terms_lagrangian: Expression | None = None,
        max_order: int,
        fields: Iterable[FieldHandle | FieldDefinition | str | Expression] | None = None,
        strict: bool = False,
    ) -> Expression:
        """Return the systematic scalar formal-EOM field-redefinition delta."""

        from .functional import systematic_scalar_eom_field_redefinition_delta

        return systematic_scalar_eom_field_redefinition_delta(
            self,
            source_lagrangian,
            eom_terms_lagrangian=eom_terms_lagrangian,
            max_order=max_order,
            fields=fields,
            strict=strict,
        )

    def systematic_abelian_vector_eom_field_redefinition_delta(
        self,
        source_lagrangian: Expression,
        *,
        eom_terms_lagrangian: Expression | None = None,
        max_order: int,
        fields: Iterable[FieldHandle | FieldDefinition | str | Expression] | None = None,
        strict: bool = False,
    ) -> Expression:
        """Return the staged Abelian-vector formal-EOM shift delta."""

        from .functional import systematic_abelian_vector_eom_field_redefinition_delta

        return systematic_abelian_vector_eom_field_redefinition_delta(
            self,
            source_lagrangian,
            eom_terms_lagrangian=eom_terms_lagrangian,
            max_order=max_order,
            fields=fields,
            strict=strict,
        )

    def scalar_eom_field_redefinition_delta(
        self,
        source_lagrangian: Expression,
        eom_terms: Expression,
        *,
        fields: Iterable[FieldHandle | FieldDefinition | str | Expression] | None = None,
        max_order: int | None = None,
        shift_order: int | None = None,
        strict: bool = False,
    ) -> Expression:
        """Return the light-scalar field-redefinition delta for formal EOM terms.

        This is a bounded Matchete ``ScalarShift``/``ShiftLagrangian`` subset:
        ``eom_terms`` must already contain explicit formal ``EOM(Field(...))``
        atoms, and the returned expression is the source variation generated by
        the corresponding scalar field shifts.
        """

        from .functional import scalar_eom_field_redefinition_delta

        return scalar_eom_field_redefinition_delta(
            self,
            source_lagrangian,
            eom_terms,
            fields=fields,
            max_order=max_order,
            shift_order=shift_order,
            strict=strict,
        )

    def solve_heavy_scalar_eoms(self, lagrangian: Expression, *, eft_order: int = 6) -> dict[str, HeavyScalarSolution]:
        """Solve heavy scalar equations of motion order by order.

        Returns a mapping from heavy field names to ``HeavyScalarSolution``
        objects. Solutions are recomputed for the supplied Lagrangian and are
        not cached on the theory.
        """

        from .tree_matching import solve_heavy_scalar_eoms

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
        fluctuation_fields: FluctuationBasis | Iterable[FluctuationBasisItem] | None = None,
        matchete_fluctuation_dof_basis: bool = False,
        wilson_line_weight_paths_by_component_dofs: bool = False,
    ) -> OneLoopSetup:
        """Prepare native-backed one-loop matching inputs without evaluating loops."""

        from .matching import one_loop_setup

        return one_loop_setup(
            self,
            lagrangian,
            eft_order=eft_order,
            max_trace_order=max_trace_order,
            include_light_only=include_light_only,
            fluctuation_fields=fluctuation_fields,
            matchete_fluctuation_dof_basis=matchete_fluctuation_dof_basis,
            wilson_line_weight_paths_by_component_dofs=wilson_line_weight_paths_by_component_dofs,
        )

    def match(
        self,
        lagrangian: Expression,
        *,
        eft_order: int = 6,
        loop_order: int = 0,
        one_loop_options: OneLoopMatchOptions | None = None,
        matching_condition_targets: Mapping[str, Expression] | Iterable[Expression] | str | None = None,
        matching_condition_source: str = "on_shell_eft_lagrangian",
        matching_condition_expand_source: bool = True,
        matching_condition_canonize_indices: bool = True,
        matching_condition_normalize_derivative_operators: bool = True,
        matching_condition_normalize_ibp_scalar_bilinears: bool = False,
        matching_condition_truncate_eft: bool = False,
        matching_condition_drop_zero: bool = False,
        matching_condition_include_coupling_identities: bool = False,
    ) -> Expression | MatchingResult:
        """Match a Lagrangian through the requested loop order.

        ``loop_order=0`` preserves pychete's existing tree-level heavy-scalar
        matching behavior and returns an expression. ``loop_order=1`` returns
        the current internal-analytic, minimal-subtraction one-loop
        ``MatchingResult`` and keeps ``metadata["complete"]`` false until the
        full Matchete-level engine is implemented. Advanced one-loop backend
        choices are provided through ``one_loop_options``. If
        ``matching_condition_targets`` is supplied for ``loop_order=1``, the
        returned result projects those matching conditions from
        ``matching_condition_source`` using native Symbolica coefficient
        extraction. Set ``matching_condition_expand_source=False`` to extract
        from the selected source expression without first expanding the whole
        expression, which can scale better for large factored one-loop
        results. Set ``matching_condition_truncate_eft=True`` to apply the
        requested ``eft_order`` target-locally to each projected contribution
        instead of requiring global result truncation before projection. Pass
        ``"registered_wilsons"`` to project all
        theory-registered Wilson coefficients that have stored operator
        metadata. ``matching_condition_canonize_indices=True`` applies
        Symbolica's native tensor-index canonicalization to the projection
        source and targets before coefficient extraction so alpha-equivalent
        contracted-index relabelings can project. Set
        ``matching_condition_normalize_derivative_operators=True`` to expand
        explicit ``CD(...)`` wrappers into pychete field-derivative slots before
        projection, which aligns user-facing operator metadata with generated
        one-loop sources. Set
        ``matching_condition_normalize_ibp_scalar_bilinears=True`` to allow
        target-local integration-by-parts projection of scalar bilinears such
        as ``A * CD([mu, mu], B)`` against sources already written as
        ``-CD(mu, A) * CD(mu, B)``. Set
        ``matching_condition_include_coupling_identities`` to
        include tree-level identity values for target couplings registered in
        this theory when projecting from a loop-correction expression.
        """

        from .matching import match_one_loop
        from .tree_matching import match_tree

        if loop_order == 0:
            if one_loop_options is not None:
                raise ValueError("one_loop_options requires loop_order=1")
            if matching_condition_targets is not None:
                raise ValueError("matching_condition_targets requires loop_order=1")
            return match_tree(self, lagrangian, eft_order=eft_order)
        if loop_order == 1:
            return match_one_loop(
                self,
                lagrangian,
                eft_order=eft_order,
                one_loop_options=one_loop_options,
                matching_condition_targets=matching_condition_targets,
                matching_condition_source=matching_condition_source,
                matching_condition_expand_source=matching_condition_expand_source,
                matching_condition_canonize_indices=matching_condition_canonize_indices,
                matching_condition_normalize_derivative_operators=(
                    matching_condition_normalize_derivative_operators
                ),
                matching_condition_normalize_ibp_scalar_bilinears=(
                    matching_condition_normalize_ibp_scalar_bilinears
                ),
                matching_condition_truncate_eft=matching_condition_truncate_eft,
                matching_condition_drop_zero=matching_condition_drop_zero,
                matching_condition_include_coupling_identities=(
                    matching_condition_include_coupling_identities
                ),
            )
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
            "externals": {name: value.to_json() for name, value in sorted(self.externals.items())},
            "fields": {name: value.to_json() for name, value in sorted(self.fields.items())},
            "couplings": {name: value.to_json() for name, value in sorted(self.couplings.items())},
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize theory metadata to a JSON string."""

        return json.dumps(self.to_json_obj(), indent=indent, sort_keys=True) + "\n"

    def write_json(self, path: str | Path) -> None:
        """Write theory metadata JSON to ``path``."""

        Path(path).write_text(self.to_json(), encoding="utf-8")

    @staticmethod
    def _symbols_with_checkpoint_cg_tensor_data(obj: dict[str, Any]) -> list[dict[str, Any]] | None:
        entries = obj.get("symbols")
        if entries is None:
            return None
        if not isinstance(entries, list):
            raise ValueError("Theory symbol manifest must be a list")
        tensor_by_name = {
            str(name): str(data["tensor"])
            for name, data in obj.get("cg_tensors", {}).items()
            if isinstance(data, dict) and data.get("tensor") is not None
        }
        if not tensor_by_name:
            return entries

        merged: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Theory symbol manifest entries must be objects")
            next_entry = dict(entry)
            if entry.get("role") == SymbolRole.CG_TENSOR.value and str(entry.get("name")) in tensor_by_name:
                raw_data = entry.get("data", {})
                if not isinstance(raw_data, dict):
                    raise ValueError(f"CG tensor symbol manifest entry {entry.get('name')!r} has non-object data")
                next_data = dict(raw_data)
                next_data.setdefault(
                    SymbolDataKey.CG_TENSOR.value,
                    expression_from_canonical(tensor_by_name[str(entry["name"])]),
                )
                next_entry["data"] = next_data
            merged.append(next_entry)
        return merged

    @classmethod
    def from_json_obj(cls, obj: dict[str, Any]) -> Theory:
        """Restore theory metadata from a JSON object."""

        s.register_builtins()
        theory = cls(obj["theory_name"])
        symbol_entries = cls._symbols_with_checkpoint_cg_tensor_data(obj)
        if symbol_entries is not None:
            theory._restore_symbol_manifest(symbol_entries)
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
                mass_dimension=data.get("mass_dimension"),
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
        for name, data in obj.get("externals", {}).items():
            operator_data = data.get("operator")
            theory.define_external(
                str(name),
                external_kind=str(data.get("external_kind", ExternalKind.GENERIC.value)),
                indices=[theory._parse_registered_expression(x) for x in data.get("indices", [])],
                eft_order=int(data.get("eft_order", 0)),
                basis=str(data["basis"]) if data.get("basis") is not None else None,
                operator=(
                    theory._parse_registered_expression(str(operator_data))
                    if operator_data is not None
                    else None
                ),
            )
        return theory
