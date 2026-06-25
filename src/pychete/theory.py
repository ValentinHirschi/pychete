from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Mapping

from symbolica import Expression, S

from .expr import is_head, list_expr
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
    representation_dimension_from_label,
    representation_dynkin_from_label,
    representation_group_from_label,
    representation_reality_from_label,
)


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
    ) -> ExternalHandle:
        """Register or return an external symbol owned by this theory.

        External symbols represent imported names that are intentionally not
        pychete fields, couplings, groups, representations, or CG tensors. The
        primary use is Matchete-derived Wilson-condition labels and helper
        symbols that must still round-trip with Symbolica tags and symbol data.
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
            )
            if requested_generic:
                return ExternalHandle(self, definition)
            existing_matches = (
                definition.kind is kind
                and [canonical_string(index) for index in definition.index_exprs]
                == [canonical_string(index) for index in indices_tuple]
                and definition.order == eft_order
                and (definition.basis_name or "") == basis_value
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
        )
        self.externals[name] = definition
        return ExternalHandle(self, definition)

    def define_wilson_coefficient(
        self,
        name: str,
        *,
        indices: Iterable[Expression] = (),
        eft_order: int = 0,
        basis: str = "SMEFT",
    ) -> ExternalHandle:
        """Register a Wilson-coefficient target as a theory-owned external."""

        return self.define_external(
            name,
            external_kind=ExternalKind.WILSON_COEFFICIENT,
            indices=indices,
            eft_order=eft_order,
            basis=basis,
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

    def match(
        self,
        lagrangian: Expression,
        *,
        eft_order: int = 6,
        loop_order: int = 0,
        one_loop_options: OneLoopMatchOptions | None = None,
        matching_condition_targets: Mapping[str, Expression] | Iterable[Expression] | None = None,
        matching_condition_source: str = "on_shell_eft_lagrangian",
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
        extraction. Set ``matching_condition_include_coupling_identities`` to
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
            theory.define_external(
                str(name),
                external_kind=str(data.get("external_kind", ExternalKind.GENERIC.value)),
                indices=[theory._parse_registered_expression(x) for x in data.get("indices", [])],
                eft_order=int(data.get("eft_order", 0)),
                basis=str(data["basis"]) if data.get("basis") is not None else None,
            )
        return theory
