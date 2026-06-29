from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from html import escape
from itertools import product
from typing import Any, Iterable, Iterator, Mapping, Sequence, TypeAlias

from symbolica import Expression, Matrix, Replacement

from .cde import (
    CovariantPropagatorExpansionTerm,
    act_with_open_covariant_derivatives,
    bosonic_covariant_propagator_expansion_terms,
    fermionic_covariant_propagator_expansion_terms,
    open_covariant_derivative,
)
from .eft import series_eft
from .expr import (
    bar_field_pattern,
    bar_field_inner,
    factors,
    field_derivatives,
    field_label,
    field_pattern,
    field_strength_pattern,
    field_type,
    field_with_derivatives,
    is_bar_field,
    is_head,
    is_zero,
    list_expr,
    list_items,
    product_expr,
    sum_expr,
    terms,
)
from .functional import (
    abelian_vector_eom_field_redefinition_delta,
    derive_eom,
    eom_replacement_rules_for_expression,
    expose_scalar_derivative_commutator_bilinears,
    partial_functional_derivative,
    simplify_trivial_cd_operators,
)
from .indices import collect_indices, relabel_dummy_indices
from .logging import get_logger, progress
from .matching_expansion_plans import (
    BosonicCDEExpansionPlan,
    BosonicCDEExpansionPlanEntry,
    BosonicCDEExpansionRequest,
    WilsonLineExpansionPlan,
    WilsonLineExpansionPlanEntry,
    WilsonLineExpansionRequest,
    cde_expansion_request_metadata as _cde_expansion_request_metadata,
    cde_expansion_trace_names as _cde_expansion_trace_names,
    cde_plan_entry_label as _cde_plan_entry_label,
    cde_plan_expansion_indices as _cde_plan_expansion_indices,
    normalize_expansion_indices as _normalize_cde_expansion_indices,
    slot_order_allocations as _cde_slot_order_allocations,
    wilson_line_expansion_request_metadata as _wilson_line_expansion_request_metadata,
    wilson_line_expansion_trace_names as _wilson_line_expansion_trace_names,
    wilson_line_plan_entry_label as _wilson_line_plan_entry_label,
    wilson_line_plan_expansion_indices as _wilson_line_plan_expansion_indices,
    wilson_line_trace_name_from_entry_label as _wilson_line_trace_name_from_entry_label,
)
from .matching_field_dofs import (
    matchete_fluctuation_dof_basis_fields,
    wilson_line_path_component_weight,
)
from .matching_integrals import (
    cde_vakint_integral_terms_at_stage as _cde_vakint_integral_terms_at_stage,
    combine_propagator_power_shifts as _combine_propagator_power_shifts,
    contains_pychete_dirac_factor as _contains_pychete_dirac_factor,
    contains_registered_fermion_field as _contains_registered_fermion_field,
    extract_propagator_denominator_power_shifts as _extract_propagator_denominator_power_shifts,
    finite_named_supertraces as _finite_named_supertraces,
    named_internal_supertraces as _named_internal_supertraces,
    named_vakint_supertraces as _named_vakint_supertraces,
    postprocess_pre_wilson_line_tensor_reduced_expression as _postprocess_pre_wilson_line_tensor_reduced_expression,
    postprocess_wilson_line_numerator as _postprocess_wilson_line_numerator,
    postprocess_wilson_line_tensor_reduced_expression as _postprocess_wilson_line_tensor_reduced_expression,
    postprocess_wilson_line_vakint_stage_expression as _postprocess_wilson_line_vakint_stage_expression,
    propagator_denominator_factor_data as _propagator_denominator_factor_data,
    restore_theory_owned_generated_lorentz_indices as _restore_theory_owned_generated_lorentz_indices,
    sum_wilson_line_internal_terms as _sum_wilson_line_internal_terms,
    theory_owned_generated_lorentz_index as _theory_owned_generated_lorentz_index,
    vakint_expression_at_stage as _vakint_expression_at_stage,
    vakint_integral_terms_at_stage as _vakint_integral_terms_at_stage,
    wilson_line_internal_evaluated_entry_expressions_by_entry_from_terms as _wilson_line_internal_evaluated_entry_expressions_by_entry_from_terms,
    wilson_line_internal_evaluated_terms_by_entry_from_terms as _wilson_line_internal_evaluated_terms_by_entry_from_terms,
    wilson_line_internal_evaluated_terms_from_terms as _wilson_line_internal_evaluated_terms_from_terms,
    wilson_line_internal_expression_map_by_entry as _wilson_line_internal_expression_map_by_entry,
    wilson_line_internal_integral_sum_from_terms as _wilson_line_internal_integral_sum_from_terms,
    wilson_line_matchete_order_numerator_to_vakint_integral as _wilson_line_matchete_order_numerator_to_vakint_integral,
    wilson_line_matchete_order_pre_wilson_integral_expression as _wilson_line_matchete_order_pre_wilson_integral_expression,
)
from .matching_options import (
    OneLoopIntegralBackend,
    OneLoopMatchOptions,
    OneLoopNormalization,
    OneLoopNormalizationInput,
    VakintIntegralStage,
    WilsonLineInternalEvaluationMode,
    one_loop_normalization_label,
)
from .matching_projection_filters import (
    ProjectionAtomRequirementGroups,
    filter_cde_terms_by_projection_requirements as _filter_cde_terms_by_projection_requirements,
    filter_wilson_line_terms_by_projection_requirements as _filter_wilson_line_terms_by_projection_requirements,
    term_atom_requirements_for_targets as _term_atom_requirements_for_targets,
    wilson_line_entry_can_satisfy_projection_requirements as _wilson_line_entry_can_satisfy_projection_requirements,
    wilson_line_path_with_projection_filtered_entries as _wilson_line_path_with_projection_filtered_entries,
)
from .matching_results import (
    LOOP_ONLY_OFF_SHELL_PROJECTION_SOURCE,
    LOOP_ONLY_ON_SHELL_PROJECTION_SOURCE,
    TREE_LEVEL_OFF_SHELL_PROJECTION_SOURCE,
    TREE_LEVEL_ON_SHELL_PROJECTION_SOURCE,
    MatchingExpressionComparison,
    MatchingResult,
    MatchingResultComparison,
)
from .noncommutative import distribute_ncm_additions, scalarize_commutative_ncm_chains
from .symbols import SymbolDataKey, SymbolRole, canonical_string, display_string, latex_string, s, safe_symbol_name, symbol_data
from .theory import CovariantDerivativeCommutatorMode, Theory
from .theory_metadata import (
    FieldChirality,
    FieldDefinition,
    FieldHandle,
    FieldMassKind,
    FieldRole,
    FieldVariation,
    GroupKind,
    field_chirality_from_label,
    field_mass_expr_from_label,
    field_mass_kind_from_label,
    field_indices_from_label,
    field_propagating_from_label,
    field_role_from_label,
    field_self_conjugate_from_label,
    field_type_from_label,
)
from .tree_matching import (
    HeavyScalarSolution,
    heavy_scalar_solution_replacements,
    match_tree,
    replace_heavy_scalar_solutions_eft_limited,
    solve_heavy_scalar_eoms,
)
from .wilson_line_eom import (
    _apply_on_shell_eom_reduction_to_expression,
    _apply_wilson_line_abelian_vector_eom_field_redefinition,
    _apply_wilson_line_post_integral_scalar_commutator_bilinears,
    _apply_wilson_line_scalar_eom_field_redefinition,
    _apply_wilson_line_scalar_green_normal_form,
)

FluctuationBasisItem: TypeAlias = FieldHandle | FieldDefinition | str | Expression
_LOGGER = get_logger("matching")


class FluctuationStatistics(StrEnum):
    """Statistics class used for fluctuation supertrace bookkeeping."""

    BOSONIC = "bosonic"
    FERMIONIC = "fermionic"


class FluctuationSector(StrEnum):
    """Sector selector for fluctuation operator blocks."""

    ALL = "all"
    HEAVY = "heavy"
    LIGHT = "light"

    @classmethod
    def from_user(cls, value: FluctuationSector | str) -> FluctuationSector:
        """Normalize a user-provided fluctuation-sector selector."""

        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError("fluctuation sector must be 'all', 'heavy', or 'light'") from exc


@dataclass(frozen=True)
class FluctuationMode:
    """Metadata for one field entry in a fluctuation basis."""

    theory: Theory
    field: Expression
    base_field: Expression
    field_type: Expression
    field_role: FieldRole
    mass_kind: FieldMassKind
    statistics: FluctuationStatistics
    self_conjugate: bool
    conjugated: bool

    @property
    def label(self) -> Expression:
        """Symbolica field label carrying this mode's metadata."""

        return field_label(self.base_field)

    @property
    def is_heavy(self) -> bool:
        """Whether this fluctuation mode belongs to the heavy sector."""

        return self.mass_kind is FieldMassKind.HEAVY

    @property
    def is_light(self) -> bool:
        """Whether this fluctuation mode belongs to the light sector."""

        return self.mass_kind is FieldMassKind.LIGHT

    @property
    def supertrace_sign(self) -> int:
        """Return the boson/fermion sign for supertrace contributions."""

        return -1 if self.statistics is FluctuationStatistics.FERMIONIC else 1

    @property
    def chirality(self) -> FieldChirality:
        """Chirality metadata stored on this mode's field label."""

        return field_chirality_from_label(self.label)

    @property
    def conjugate_mode_count(self) -> int:
        """Number of basis modes generated by this field's reality convention."""

        return 1 if self.self_conjugate else 2

    @property
    def spin_lorentz_dimension(self) -> int | None:
        """Known spin/Lorentz component count, leaving vectors backend-dependent."""

        return _mode_spin_lorentz_dimension(self.field_type, self.chirality, self.field_role)

    @property
    def chiral_supertrace_factor(self) -> Expression:
        """Matchete-style half-factor compensating chiral fermion projectors."""

        if (
            self.statistics is FluctuationStatistics.FERMIONIC
            and self.chirality in {FieldChirality.LEFT, FieldChirality.RIGHT}
        ):
            return Expression.num(1) / 2
        return Expression.num(1)

    @property
    def index_representations(self) -> tuple[Expression, ...]:
        """Index representations carried by this fluctuation mode."""

        return field_indices_from_label(self.label)

    @property
    def index_dimensions(self) -> tuple[int | None, ...]:
        """Dimensions of this mode's index representations when known."""

        return tuple(
            _mode_index_representation_dimension(self.theory, representation)
            for representation in self.index_representations
        )

    @property
    def internal_dimension(self) -> int | None:
        """Product of known internal index dimensions, or ``None`` if unknown."""

        dimension = 1
        for index_dimension in self.index_dimensions:
            if index_dimension is None:
                return None
            dimension *= index_dimension
        return dimension

    @property
    def known_component_count(self) -> int | None:
        """Product of known internal and spin/Lorentz dimensions."""

        internal_dimension = self.internal_dimension
        spin_lorentz_dimension = self.spin_lorentz_dimension
        if internal_dimension is None or spin_lorentz_dimension is None:
            return None
        return internal_dimension * spin_lorentz_dimension

    @property
    def supertrace_weight(self) -> int | None:
        """Signed internal multiplicity for this mode when fully known."""

        internal_dimension = self.internal_dimension
        if internal_dimension is None:
            return None
        return self.supertrace_sign * internal_dimension

    @property
    def mass(self) -> Expression | None:
        """Mass coupling reconstructed from Symbolica field-label data."""

        return field_mass_expr_from_label(self.label)

    @property
    def mass_squared(self) -> Expression | None:
        """Squared mass coupling for propagator denominators, if present."""

        mass = self.mass
        if mass is None:
            return None
        return mass**2

    @property
    def supertrace_category(self) -> str:
        """Matchete-style heavy/light and spin category used for trace names."""

        return _mode_supertrace_category(self)

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{FluctuationMode}}\left({latex_string(self.field)}\right)$"

    def _repr_html_(self) -> str:
        dimension = self.internal_dimension
        dimension_part = "" if dimension is None else f" dim={dimension}"
        return (
            f"<code>FluctuationMode({escape(display_string(self.field))} "
            f"{self.mass_kind.value} {self.field_role.value} {self.statistics.value}{dimension_part})</code>"
        )


@dataclass(frozen=True)
class FluctuationPropagator:
    """Propagator metadata for one fluctuation mode.

    This stage intentionally stores only the Symbolica expressions needed to
    build propagator denominators later. The mass is recovered from symbol data
    on the field label, so state loading and custom field symbols keep the same
    metadata path as all other theory definitions.
    """

    theory: Theory
    mode: FluctuationMode
    mass: Expression | None
    mass_squared: Expression | None

    @property
    def field(self) -> Expression:
        """Return the fluctuation field expression this propagator belongs to."""

        return self.mode.field

    @property
    def is_heavy(self) -> bool:
        """Whether this propagator belongs to a heavy fluctuation."""

        return self.mode.is_heavy

    @property
    def is_light(self) -> bool:
        """Whether this propagator belongs to a light fluctuation."""

        return self.mode.is_light

    def denominator(self, *, loop_momentum_squared: Expression | None = None) -> Expression:
        """Return a neutral Symbolica propagator-denominator expression."""

        momentum_squared = s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared
        mass_squared = Expression.num(0) if self.mass_squared is None else self.mass_squared
        return s.PropagatorDenominator(momentum_squared, mass_squared)

    def to_expression_map(self, *, prefix: str = "fluctuation_propagator") -> dict[str, Expression]:
        """Return mass and denominator expressions attached to this propagator."""

        entries: dict[str, Expression] = {}
        key = canonical_string(self.field)
        if self.mass is not None:
            entries[f"{prefix}[{key},mass]"] = self.mass
        if self.mass_squared is not None:
            entries[f"{prefix}[{key},mass_squared]"] = self.mass_squared
        entries[f"{prefix}[{key},denominator]"] = self.denominator()
        return entries

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{FluctuationPropagator}}\left({latex_string(self.field)}\right)$"

    def _repr_html_(self) -> str:
        mass = "" if self.mass is None else f" mass={escape(display_string(self.mass))}"
        return f"<code>FluctuationPropagator({escape(display_string(self.field))}{mass})</code>"


@dataclass(frozen=True)
class PropagatorPlan:
    """Structured propagator metadata prepared for one-loop expansion."""

    theory: Theory
    propagators: tuple[FluctuationPropagator, ...]

    @property
    def heavy(self) -> tuple[FluctuationPropagator, ...]:
        """Return propagators for heavy fluctuation modes."""

        return tuple(propagator for propagator in self.propagators if propagator.is_heavy)

    @property
    def light(self) -> tuple[FluctuationPropagator, ...]:
        """Return propagators for light fluctuation modes."""

        return tuple(propagator for propagator in self.propagators if propagator.is_light)

    def to_expression_map(self, *, prefix: str = "propagator_plan") -> dict[str, Expression]:
        """Return deterministic mass expressions for all planned propagators."""

        entries: dict[str, Expression] = {}
        for propagator in self.propagators:
            entries.update(propagator.to_expression_map(prefix=prefix))
        return entries

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{PropagatorPlan}}\left(H={len(self.heavy)},\ L={len(self.light)}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>PropagatorPlan(heavy={len(self.heavy)} light={len(self.light)})</code>"


@dataclass(frozen=True)
class FluctuationBasis:
    """Discovered fluctuation fields split into heavy and light sectors."""

    theory: Theory
    modes: tuple[FluctuationMode, ...]

    @property
    def entries(self) -> tuple[Expression, ...]:
        """Return all basis field expressions in deterministic order."""

        return tuple(mode.field for mode in self.modes)

    @property
    def heavy(self) -> tuple[Expression, ...]:
        """Return heavy-sector field expressions in this basis."""

        return tuple(mode.field for mode in self.modes if mode.is_heavy)

    @property
    def light(self) -> tuple[Expression, ...]:
        """Return light-sector field expressions in this basis."""

        return tuple(mode.field for mode in self.modes if mode.is_light)

    @property
    def heavy_modes(self) -> tuple[FluctuationMode, ...]:
        """Return heavy-sector modes in this basis."""

        return tuple(mode for mode in self.modes if mode.is_heavy)

    @property
    def light_modes(self) -> tuple[FluctuationMode, ...]:
        """Return light-sector modes in this basis."""

        return tuple(mode for mode in self.modes if mode.is_light)

    def __iter__(self) -> Iterator[Expression]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def mode_for(self, field: FluctuationBasisItem) -> FluctuationMode:
        """Return metadata for one field expression in this basis."""

        requested = _fluctuation_basis_expression(self.theory, field)
        key = canonical_string(requested)
        for mode in self.modes:
            if canonical_string(mode.field) == key:
                return mode
        raise KeyError(f"Fluctuation basis has no field {key!r}")

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{FluctuationBasis}}\left(H={len(self.heavy)},\ L={len(self.light)}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>FluctuationBasis(heavy={len(self.heavy)} light={len(self.light)})</code>"


@dataclass(frozen=True)
class FluctuationOperatorBlock:
    """Rectangular block of a fluctuation operator matrix."""

    theory: Theory
    row_sector: FluctuationSector
    column_sector: FluctuationSector
    rows: tuple[FluctuationMode, ...]
    columns: tuple[FluctuationMode, ...]
    matrix: tuple[tuple[Expression, ...], ...]
    row_category: str | None = None
    column_category: str | None = None

    def entry(self, row: FluctuationBasisItem, column: FluctuationBasisItem) -> Expression:
        """Return one block entry identified by row and column fields."""

        row_index = _mode_index(self.rows, _fluctuation_basis_expression(self.theory, row))
        column_index = _mode_index(self.columns, _fluctuation_basis_expression(self.theory, column))
        return self.matrix[row_index][column_index]

    def to_expression_map(self, *, prefix: str = "fluctuation_operator_block") -> dict[str, Expression]:
        """Return deterministic named expressions for this block."""

        entries: dict[str, Expression] = {}
        row_label = self.row_category or self.row_sector.value
        column_label = self.column_category or self.column_sector.value
        for row in self.rows:
            for column in self.columns:
                key = (
                    f"{prefix}[{row_label},{column_label},"
                    f"{canonical_string(row.field)},{canonical_string(column.field)}]"
                )
                entries[key] = self.entry(row.field, column.field)
        return entries

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{FluctuationOperatorBlock}}\left({len(self.rows)}\times {len(self.columns)}\right)$"

    def _repr_html_(self) -> str:
        return (
            f"<code>FluctuationOperatorBlock({self.row_sector.value},{self.column_sector.value} "
            f"{len(self.rows)}x{len(self.columns)})</code>"
        )


@dataclass(frozen=True)
class SupertraceBlockTrace:
    """Weighted matrix-product trace over fluctuation-operator blocks."""

    theory: Theory
    name: str
    blocks: tuple[FluctuationOperatorBlock, ...]
    modes: tuple[FluctuationMode, ...]
    expression: Expression
    cyclic_key: tuple[str, ...] | None = None

    @property
    def order(self) -> int:
        """Number of block factors in this trace kernel."""

        return len(self.blocks)

    @property
    def block_sectors(self) -> tuple[tuple[FluctuationSector, FluctuationSector], ...]:
        """Return the ordered sector path represented by this trace kernel."""

        return tuple((block.row_sector, block.column_sector) for block in self.blocks)

    @property
    def cyclic_sector_key(self) -> tuple[str, ...]:
        """Return a canonical cyclic key for this closed sector path."""

        labels = (
            self.cyclic_key
            if self.cyclic_key is not None
            else tuple(block.row_sector.value for block in self.blocks)
        )
        return _cyclic_sector_key(labels)

    @property
    def cyclic_path_labels(self) -> tuple[str, ...]:
        """Return labels used to determine cyclic trace multiplicity."""

        return (
            self.cyclic_key
            if self.cyclic_key is not None
            else tuple(block.row_sector.value for block in self.blocks)
        )

    @property
    def power_type_log_prefactor(self) -> Expression:
        """Return the power-series prefactor after cyclic de-duplication."""

        if self.order == 0:
            return Expression.num(1)
        orbit_size = _cyclic_orbit_size(self.cyclic_path_labels)
        return Expression.num(-orbit_size) / (2 * Expression.num(self.order))

    def propagator_mass_squared_chain(self, *, include_light: bool = True) -> tuple[tuple[Expression, ...], ...]:
        """Return mass-squared slots aligned with the row modes of each block."""

        return tuple(
            tuple(
                _fluctuation_mass_squared(mode)
                for mode in block.rows
                if include_light or mode.is_heavy
            )
            for block in self.blocks
        )

    def propagator_denominator_chain(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        include_light: bool = True,
    ) -> tuple[tuple[Expression, ...], ...]:
        """Return denominator slots aligned with the row modes of each block."""

        return tuple(
            tuple(
                s.PropagatorDenominator(
                    s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared,
                    mass_squared,
                )
                for mass_squared in slot
            )
            for slot in self.propagator_mass_squared_chain(include_light=include_light)
        )

    def propagator_expression(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        include_light: bool = True,
    ) -> Expression:
        """Return this trace kernel decorated with propagator denominator slots."""

        chain = self.propagator_denominator_chain(
            loop_momentum_squared=loop_momentum_squared,
            include_light=include_light,
        )
        return s.SupertraceKernel(self.expression, list_expr(*(list_expr(*slot) for slot in chain)))

    def vakint_integral_expression(self, *, include_light: bool = True) -> Expression:
        """Return this trace kernel lowered to vakint's one-loop topology form."""

        from .backends import vakint

        return vakint.one_loop_vacuum_integral(
            self.expression,
            _flatten_expression_slots(self.propagator_mass_squared_chain(include_light=include_light)),
        )

    def to_expression_map(self, *, prefix: str = "supertrace_block_trace") -> dict[str, Expression]:
        """Return this trace kernel as a deterministic named expression."""

        return {f"{prefix}[{self.name}]": self.expression}

    def simplify_index_algebra(
        self,
        *,
        expand: bool = True,
        gamma: bool = True,
        color: bool = True,
        pychete_color: bool = False,
        metrics: bool = True,
        dots: bool = False,
    ) -> SupertraceBlockTrace:
        """Return this trace kernel after native idenso index simplification."""

        from .backends import idenso

        expression = idenso.simplify_index_algebra(
            self.expression,
            expand=expand,
            gamma=gamma,
            color=color,
            metrics=metrics,
            dots=dots,
        )
        if pychete_color:
            expression = idenso.simplify_pychete_color_algebra(self.theory, expression)
        return replace(
            self,
            expression=expression,
        )

    def canonicalize_integrals(
        self,
        *,
        short_form: bool | None = None,
        engine: Any | None = None,
    ) -> SupertraceBlockTrace:
        """Return this trace kernel after native vakint canonicalization."""

        from .backends import vakint

        return replace(
            self,
            expression=vakint.decode_pychete_namespace(
                self.theory,
                vakint.to_canonical(self.expression, short_form=short_form, engine=engine),
            ),
        )

    def tensor_reduce_integrals(self, *, engine: Any | None = None) -> SupertraceBlockTrace:
        """Return this trace kernel after native vakint tensor reduction."""

        from .backends import vakint

        return replace(
            self,
            expression=vakint.decode_pychete_namespace(
                self.theory,
                vakint.tensor_reduce(self.expression, engine=engine),
            ),
        )

    def evaluate_integrals(self, *, engine: Any | None = None) -> SupertraceBlockTrace:
        """Return this trace kernel after native vakint integral evaluation."""

        from .backends import vakint

        return replace(
            self,
            expression=vakint.decode_pychete_namespace(
                self.theory,
                vakint.evaluate(self.expression, engine=engine),
            ),
        )

    def evaluate_tensor_network(
        self,
        *,
        library: Any | None = None,
        cg_components_by_name: Mapping[str, Sequence[Expression | int | float | complex]] | None = None,
        builtin_cg_components: bool = False,
        native_hep_cg_builtins: bool = False,
        symbolic_cg_components: bool = False,
        function_library: Any | None = None,
        n_steps: int | None = None,
        mode: Any | None = None,
    ) -> SupertraceBlockTrace:
        """Return this trace kernel after native spenso tensor evaluation."""

        from .backends import spenso

        network = spenso.evaluate_pychete_tensor_network(
            self.theory,
            self.expression,
            library=library,
            cg_components_by_name=cg_components_by_name,
            builtin_cg_components=builtin_cg_components,
            native_hep_cg_builtins=native_hep_cg_builtins,
            symbolic_cg_components=symbolic_cg_components,
            function_library=function_library,
            n_steps=n_steps,
            mode=mode,
        )
        return replace(self, expression=spenso.tensor_network_result_scalar(network))

    def wilson_line_trace_paths(self) -> tuple[WilsonLineTracePath, ...]:
        """Return entry-level Wilson-line paths for this trace.

        Matchete's current supertrace route interleaves interaction insertions
        with propagators and a closing Wilson line before acting with open
        derivatives. This method exposes the same ordered path structure
        without changing the existing power-type result pipeline.
        """

        paths: list[WilsonLineTracePath] = []
        for path_index, entry_path in enumerate(_supertrace_block_entry_paths(self.blocks)):
            if not entry_path.next_modes:
                continue
            link_indices = _wilson_line_link_indices(self.theory, self.name, path_index)
            paths.append(
                WilsonLineTracePath(
                    theory=self.theory,
                    trace_name=self.name,
                    path_index=path_index,
                    sign=entry_path.sign,
                    prefactor=self.power_type_log_prefactor * Expression.num(entry_path.sign),
                    entries=entry_path.entries,
                    propagator_modes=entry_path.next_modes,
                    propagation_target_modes=entry_path.propagation_target_modes,
                    closing_mode=entry_path.next_modes[-1],
                    link_indices=link_indices,
                )
            )
        return tuple(paths)

    def bosonic_cde_expansion_terms(
        self,
        expansion_indices: Sequence[Sequence[Expression]],
        *,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
    ) -> tuple[BosonicCDETraceExpansionTerm, ...]:
        """Return CDE-expanded bosonic propagator terms for this ordered trace.

        ``expansion_indices`` contains one Lorentz-index sequence per
        propagator slot after each block in the closed trace. The returned
        terms preserve ordered block entries, splice in the corresponding
        ``OpenCD`` operands, and keep topology powers explicit for the existing
        vakint/internal integral backends. Optional commutator emission and
        lowering act only on the generated numerator after open CDE derivatives
        have had a chance to act, keeping this post-processing local to the
        selected trace/order entry.
        """

        if len(expansion_indices) != len(self.blocks):
            raise ValueError("expansion_indices must contain one entry per trace block")
        propagator_expansions = tuple(
            bosonic_covariant_propagator_expansion_terms(indices)
            for indices in expansion_indices
        )
        terms: list[BosonicCDETraceExpansionTerm] = []
        for entry_path in _supertrace_block_entry_paths(self.blocks):
            for choices in product(*propagator_expansions):
                prefactor = self.power_type_log_prefactor * Expression.num(entry_path.sign)
                loop_numerator = Expression.num(1)
                operands: list[Expression] = []
                masses: list[Expression] = []
                powers: list[int] = []
                for slot_index, (entry, next_mode, expansion) in enumerate(
                    zip(
                        entry_path.entries,
                        entry_path.next_modes,
                        choices,
                        strict=True,
                    )
                ):
                    prefactor *= expansion.prefactor
                    loop_numerator *= expansion.loop_momentum_numerator
                    operands.append(_fresh_cde_trace_entry_dummy_indices(entry, slot_index))
                    operands.extend(expansion.open_cd_operands)
                    masses.append(_fluctuation_mass_squared(next_mode))
                    powers.append(expansion.denominator_power)
                numerator = (prefactor * loop_numerator * _ncm_chain(*operands)).expand()
                if act_open_derivatives:
                    numerator = act_with_open_covariant_derivatives(numerator, cyclic=True)
                numerator = _postprocess_bosonic_cde_numerator(
                    self.theory,
                    numerator,
                    emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                    emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                    expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                )
                numerator = scalarize_commutative_ncm_chains(numerator)
                if is_zero(numerator):
                    continue
                terms.append(
                    BosonicCDETraceExpansionTerm(
                        theory=self.theory,
                        trace_name=self.name,
                        numerator=numerator,
                        mass_squareds=tuple(masses),
                        propagator_powers=tuple(powers),
                    )
                )
        return tuple(terms)

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{SupertraceBlockTrace}}\left({escape(self.name)},\ {self.order}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>SupertraceBlockTrace({escape(self.name)} order={self.order})</code>"


@dataclass(frozen=True)
class WilsonLineTracePath:
    """Entry-level supertrace path with an explicit closing Wilson line."""

    theory: Theory
    trace_name: str
    path_index: int
    sign: int
    prefactor: Expression
    entries: tuple[Expression, ...]
    propagator_modes: tuple[FluctuationMode, ...]
    propagation_target_modes: tuple[FluctuationMode, ...]
    closing_mode: FluctuationMode
    link_indices: tuple[Expression, Expression]

    @property
    def order(self) -> int:
        """Number of interaction insertions in this path."""

        return len(self.entries)

    @property
    def closing_field_label(self) -> Expression:
        """Field label carried by the closing Wilson line."""

        label = self.closing_mode.label
        return s.Bar(label) if self.closing_mode.conjugated else label

    def mass_squareds(self, *, include_light: bool = True) -> tuple[Expression, ...]:
        """Return propagator mass-squared slots in Wilson-line path order."""

        return tuple(
            _fluctuation_mass_squared(mode)
            for mode in self.propagator_modes
            if include_light or mode.is_heavy
        )

    def wilson_line_expression(self) -> Expression:
        """Return the unexpanded closing ``WilsonLine`` placeholder."""

        return s.WilsonLine(self.closing_field_label, list_expr(*self.link_indices))

    def wilson_term_expression(
        self,
        derivative_indices: Sequence[Expression] = (),
    ) -> Expression:
        """Return a ``WilsonTerm`` placeholder with explicit derivative slots."""

        return s.WilsonTerm(
            self.closing_field_label,
            list_expr(*self.link_indices),
            list_expr(*derivative_indices),
        )

    def template_expression(
        self,
        *,
        use_wilson_term: bool = False,
        derivative_indices: Sequence[Expression] = (),
    ) -> Expression:
        """Return the prefactor-weighted ordered insertion template."""

        closing = (
            self.wilson_term_expression(derivative_indices)
            if use_wilson_term
            else self.wilson_line_expression()
        )
        return (self.prefactor * _ncm_chain(*self.entries, closing)).expand()

    def kernel_expression(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        include_light: bool = True,
        use_wilson_term: bool = False,
        derivative_indices: Sequence[Expression] = (),
    ) -> Expression:
        """Return this path as a ``SupertraceKernel`` with propagator slots."""

        momentum_squared = s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared
        denominators = tuple(
            s.PropagatorDenominator(momentum_squared, mass_squared)
            for mass_squared in self.mass_squareds(include_light=include_light)
        )
        return s.SupertraceKernel(
            self.template_expression(
                use_wilson_term=use_wilson_term,
                derivative_indices=derivative_indices,
            ),
            list_expr(*(list_expr(denominator) for denominator in denominators)),
        )

    def wilson_term_expanded_template_expression(
        self,
        derivative_indices: Sequence[Expression] = (),
    ) -> Expression:
        """Return the ordered insertion template after supported Wilson expansion."""

        from .wilson_lines import expand_wilson_terms

        return expand_wilson_terms(
            self.theory,
            self.template_expression(
                use_wilson_term=True,
                derivative_indices=derivative_indices,
            ),
        )

    def wilson_term_expanded_kernel_expression(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        include_light: bool = True,
        derivative_indices: Sequence[Expression] = (),
    ) -> Expression:
        """Return the path kernel after supported Wilson expansion."""

        from .wilson_lines import expand_wilson_terms

        return expand_wilson_terms(
            self.theory,
            self.kernel_expression(
                loop_momentum_squared=loop_momentum_squared,
                include_light=include_light,
                use_wilson_term=True,
                derivative_indices=derivative_indices,
            ),
        )

    def propagator_expansion_terms(
        self,
        expansion_indices: Sequence[Sequence[Expression]],
        *,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        simplify_pychete_color_algebra: bool = False,
    ) -> tuple[WilsonLineTraceExpansionTerm, ...]:
        """Return Matchete-style propagator-expanded terms for this path.

        ``expansion_indices`` contains one Lorentz-index sequence per
        propagator slot in this ordered Wilson-line path. The implementation
        reuses the tested covariant propagator expansion primitive, but the
        public object is Wilson-line based: open derivative operators act on
        the ordered insertion chain and the closing ``WilsonTerm`` before the
        supported Wilson-term expansion is applied.
        """

        if len(expansion_indices) != len(self.entries):
            raise ValueError("expansion_indices must contain one entry per Wilson-line path slot")
        terms: list[WilsonLineTraceExpansionTerm] = []
        for raw_term in self.raw_propagator_expansion_terms(expansion_indices):
            term = _postprocess_wilson_line_raw_expansion_term(
                raw_term,
                act_open_derivatives=act_open_derivatives,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                max_wilson_derivative_order=max_wilson_derivative_order,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            )
            if term is not None:
                terms.append(term)
        return tuple(terms)

    def raw_propagator_expansion_terms(
        self,
        expansion_indices: Sequence[Sequence[Expression]],
    ) -> tuple[_WilsonLineRawExpansionTerm, ...]:
        """Return unacted formal Wilson-line terms before open-CD/Wilson cleanup."""

        if len(expansion_indices) != len(self.entries):
            raise ValueError("expansion_indices must contain one entry per Wilson-line path slot")
        normalized_indices = _normalize_cde_expansion_indices(expansion_indices)
        propagator_expansions = tuple(
            _wilson_line_propagator_expansion_terms(
                self.theory,
                mode,
                indices,
                trace_name=self.trace_name,
                path_index=self.path_index,
                slot_index=slot_index,
            )
            for slot_index, (mode, indices) in enumerate(
                zip(self.propagator_modes, normalized_indices, strict=True)
            )
        )
        terms: list[_WilsonLineRawExpansionTerm] = []
        fresh_entries = tuple(
            _fresh_trace_entry_dummy_indices(entry, slot_index)
            for slot_index, entry in enumerate(self.entries)
        )
        for choices in product(*propagator_expansions):
            prefactor = self.prefactor
            loop_numerator = Expression.num(1)
            loop_momentum_indices: list[Expression] = []
            operands: list[Expression] = []
            masses: list[Expression] = []
            powers: list[int] = []
            for slot_index, (entry, mode, expansion) in enumerate(
                zip(self.entries, self.propagator_modes, choices, strict=True)
            ):
                target_slot_index = (slot_index + 1) % self.order
                prefactor *= expansion.prefactor
                loop_numerator *= expansion.loop_momentum_numerator
                loop_momentum_indices.extend(expansion.loop_momentum_indices)
                operands.append(fresh_entries[slot_index])
                propagation_pairing = (
                    _fresh_fluctuation_propagation_pairing(
                        mode,
                        self.propagation_target_modes[slot_index],
                        slot_index,
                        target_slot_index,
                    )
                )
                propagation_pairing *= _internal_vector_propagator_lorentz_pairing(
                    mode,
                    fresh_entries[slot_index],
                    fresh_entries[target_slot_index],
                    target_slot_index=target_slot_index,
                )
                operands.append(propagation_pairing)
                operands.extend(expansion.open_cd_operands)
                masses.append(_fluctuation_mass_squared(mode))
                powers.append(expansion.denominator_power)
            operands.append(self.wilson_term_expression())
            numerator = (prefactor * loop_numerator * _ncm_chain(*operands)).expand()
            numerator = distribute_ncm_additions(numerator)
            terms.append(
                _WilsonLineRawExpansionTerm(
                    theory=self.theory,
                    trace_name=self.trace_name,
                    path_index=self.path_index,
                    expansion_indices=normalized_indices,
                    numerator_before_open_cd=numerator,
                    mass_squareds=tuple(masses),
                    propagator_powers=tuple(powers),
                    loop_momentum_indices=tuple(loop_momentum_indices),
                    close_fermion_loop=(
                        bool(self.propagator_modes)
                        and self.propagator_modes[0].statistics is FluctuationStatistics.FERMIONIC
                    ),
                )
            )
        return tuple(terms)

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{WilsonLineTracePath}}\left({escape(self.trace_name)},\ {self.path_index}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>WilsonLineTracePath({escape(self.trace_name)} path={self.path_index})</code>"


def _fresh_trace_entry_dummy_indices(entry: Expression, slot_index: int) -> Expression:
    """Make dummy contractions local to one ordered trace insertion."""

    return relabel_dummy_indices(entry, start=200_000 + 1_000 * slot_index)


def _remove_wilson_line_loop_momentum_symmetry_vanishing_terms(
    expr: Expression,
    loop_momentum_indices: Sequence[Expression],
) -> Expression:
    """Drop loop-symmetry-vanishing Wilson terms with pychete Xterm momenta.

    Matchete's Xterm substitutions already contain the ``OpenCD - I LoopMom``
    split when ``RemoveSymmetryVanishingWilsonTerms`` sees the expression.
    pychete keeps the momentum part of differential Xterms as
    ``DifferentialOperator(...)`` until the backend lowering stage. Include
    those uncontracted differential slots in the loop-momentum rank used for
    the Wilson-term symmetry rule, without lowering the expression early.
    """

    from .wilson_lines import remove_loop_momentum_symmetry_vanishing_wilson_terms

    base_indices = tuple(loop_momentum_indices)
    loop_momentum_pattern = s.LoopMomentum(s.LoopMomentumIndexWildcard)
    if (
        not base_indices
        and not bool(expr.matches(loop_momentum_pattern))
        and not bool(expr.matches(s.DifferentialOperator(s.FieldDerivativesWildcard)))
    ):
        return expr
    return sum_expr(
        remove_loop_momentum_symmetry_vanishing_wilson_terms(
            term,
            _term_loop_symmetry_indices(term, base_indices),
        )
        for term in terms(expr)
    ).expand()


def _term_loop_symmetry_indices(
    term: Expression,
    fallback_loop_momentum_indices: tuple[Expression, ...],
) -> tuple[Expression, ...]:
    actual_loop_indices = _explicit_loop_momentum_indices(term)
    return (
        (*actual_loop_indices, *_differential_operator_free_loop_indices(term))
        if actual_loop_indices
        else (*fallback_loop_momentum_indices, *_differential_operator_free_loop_indices(term))
    )


def _explicit_loop_momentum_indices(expr: Expression) -> tuple[Expression, ...]:
    pattern = s.LoopMomentum(s.LoopMomentumIndexWildcard)
    if not bool(expr.matches(pattern)):
        return ()
    return tuple(match[s.LoopMomentumIndexWildcard] for match in expr.match(pattern))


def _differential_operator_free_loop_indices(expr: Expression) -> tuple[Expression, ...]:
    pattern = s.DifferentialOperator(s.FieldDerivativesWildcard)
    if not bool(expr.matches(pattern)):
        return ()
    indices: list[Expression] = []
    for match in expr.match(pattern):
        derivatives = list_items(match[s.FieldDerivativesWildcard])
        if _contracted_derivative_pair_power(derivatives) is None:
            indices.extend(derivatives)
    return tuple(indices)


def _fresh_fluctuation_propagation_pairing(
    column_mode: FluctuationMode,
    target_row_mode: FluctuationMode,
    column_slot_index: int,
    target_slot_index: int,
) -> Expression:
    """Return the field-space identity carried by one explicit propagator slot."""

    propagated_field = column_mode.field if column_mode.self_conjugate else _conjugate_fluctuation_field(column_mode.field)
    source = _slot_local_fluctuation_field(propagated_field, column_slot_index)
    target = _slot_local_fluctuation_field(target_row_mode.field, target_slot_index)
    return _fluctuation_field_pairing(source, target)


def _internal_vector_propagator_lorentz_pairing(
    mode: FluctuationMode,
    source_entry: Expression,
    target_entry: Expression,
    *,
    target_slot_index: int,
) -> Expression:
    """Return the implicit Lorentz metric for non-closing vector propagators."""

    if target_slot_index == 0 or not _is_vector_field_type(mode.field_type):
        return Expression.num(1)
    source_index = _single_lorentz_index_in_expression(source_entry)
    target_index = _single_lorentz_index_in_expression(target_entry)
    if source_index is None or target_index is None:
        return Expression.num(1)
    return s.Metric(source_index, target_index)


def _single_lorentz_index_in_expression(expr: Expression) -> Expression | None:
    indices = tuple(info.expr for info in collect_indices(expr) if bool(info.representation == s.Lorentz))
    if len(indices) != 1:
        return None
    return indices[0]


def _slot_local_fluctuation_field(field: Expression, slot_index: int) -> Expression:
    conjugated = is_bar_field(field)
    base = bar_field_inner(field) if conjugated else field
    if not is_head(base, s.Field):
        return field
    indices = tuple(
        s.Index(s.dummy_index(200_000 + 1_000 * slot_index + offset), index[1])
        if is_head(index, s.Index)
        else index
        for offset, index in enumerate(list_items(base[2]))
    )
    relabeled = s.Field(base[0], base[1], list_expr(*indices), base[3])
    return s.Bar(relabeled) if conjugated else relabeled


def _fluctuation_field_pairing(source: Expression, target: Expression) -> Expression:
    source_base = bar_field_inner(source) if is_bar_field(source) else source
    target_base = bar_field_inner(target) if is_bar_field(target) else target
    source_conjugated = is_bar_field(source)
    target_conjugated = is_bar_field(target)
    if source_conjugated != target_conjugated:
        raise ValueError(
            "Propagation pairing requires aligned fluctuation orientations, got "
            f"{canonical_string(source)} and {canonical_string(target)}"
        )
    if not bool(field_label(source_base) == field_label(target_base)):
        raise ValueError(
            "Propagation pairing requires matching field labels, got "
            f"{canonical_string(source_base)} and {canonical_string(target_base)}"
        )
    source_indices = list_items(source_base[2])
    target_indices = list_items(target_base[2])
    if len(source_indices) != len(target_indices):
        raise ValueError("Propagation pairing field-index ranks do not match")
    factors: list[Expression] = []
    for source_index, target_index in zip(source_indices, target_indices, strict=True):
        if not is_head(source_index, s.Index) or not is_head(target_index, s.Index):
            raise ValueError("Propagation pairing requires concrete Index field slots")
        if source_conjugated:
            factors.append(s.Delta(s.Index(source_index[0], s.Bar(source_index[1])), target_index))
        else:
            factors.append(s.Delta(source_index, s.Index(target_index[0], s.Bar(target_index[1]))))
    return product_expr(factors)


def _fresh_cde_trace_entry_dummy_indices(entry: Expression, slot_index: int) -> Expression:
    """Make dummy contractions local to one ordered legacy CDE trace insertion."""

    return _fresh_trace_entry_dummy_indices(entry, slot_index)


@dataclass(frozen=True)
class _WilsonLineRawExpansionTerm:
    """Formal Wilson-line numerator before open-CD action and Wilson expansion."""

    theory: Theory
    trace_name: str
    path_index: int
    expansion_indices: tuple[tuple[Expression, ...], ...]
    numerator_before_open_cd: Expression
    mass_squareds: tuple[Expression, ...]
    propagator_powers: tuple[int, ...]
    loop_momentum_indices: tuple[Expression, ...]
    close_fermion_loop: bool = False
    component_weight: int = 1


def _postprocess_wilson_line_raw_expansion_term(
    raw_term: _WilsonLineRawExpansionTerm,
    *,
    act_open_derivatives: bool,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode,
    expand_covariant_derivative_commutators: bool,
    max_wilson_derivative_order: int,
    simplify_pychete_color_algebra: bool,
) -> WilsonLineTraceExpansionTerm | None:
    """Apply Matchete-order open-CD, Wilson, and backend cleanup to a raw term."""

    from .wilson_lines import expand_wilson_terms

    numerator = raw_term.numerator_before_open_cd
    if act_open_derivatives:
        # Explicit Wilson-line chains already close on the final WilsonTerm;
        # Matchete's ActWithOpenCDs acts only on factors to the right here.
        numerator = act_with_open_covariant_derivatives(numerator)
        numerator = distribute_ncm_additions(numerator)
    numerator = _remove_wilson_line_loop_momentum_symmetry_vanishing_terms(
        numerator,
        raw_term.loop_momentum_indices,
    )
    pre_wilson_numerator = numerator
    numerator = expand_wilson_terms(
        raw_term.theory,
        numerator,
        max_derivative_order=max_wilson_derivative_order,
    )
    numerator = _postprocess_bosonic_cde_numerator(
        raw_term.theory,
        numerator,
        emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
        emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
        expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
        covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
    )
    numerator = _postprocess_wilson_line_numerator(
        numerator,
        close_fermion_loop=raw_term.close_fermion_loop,
    )
    if simplify_pychete_color_algebra:
        from .backends import idenso

        numerator = idenso.simplify_pychete_color_algebra(raw_term.theory, numerator)
    if is_zero(numerator):
        return None
    return WilsonLineTraceExpansionTerm(
        theory=raw_term.theory,
        trace_name=raw_term.trace_name,
        path_index=raw_term.path_index,
        expansion_indices=raw_term.expansion_indices,
        numerator=numerator,
        mass_squareds=raw_term.mass_squareds,
        propagator_powers=raw_term.propagator_powers,
        pre_wilson_numerator=pre_wilson_numerator,
        component_weight=raw_term.component_weight,
    )


@dataclass(frozen=True)
class WilsonLineTraceExpansionTerm:
    """One Wilson-line propagator-expanded supertrace-kernel term."""

    theory: Theory
    trace_name: str
    path_index: int
    expansion_indices: tuple[tuple[Expression, ...], ...]
    numerator: Expression
    mass_squareds: tuple[Expression, ...]
    propagator_powers: tuple[int, ...]
    pre_wilson_numerator: Expression | None = None
    component_weight: int = 1

    def kernel_expression(self, *, loop_momentum_squared: Expression | None = None) -> Expression:
        """Return this term as a pychete ``SupertraceKernel`` expression."""

        momentum_squared = s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared
        denominators = tuple(
            s.PropagatorDenominator(momentum_squared, mass_squared) ** power
            for mass_squared, power in zip(self.mass_squareds, self.propagator_powers, strict=True)
        )
        return s.SupertraceKernel(self.numerator, list_expr(*(list_expr(denominator) for denominator in denominators)))

    def vakint_integral_expression(self, *, use_pre_wilson_numerator: bool = False) -> Expression:
        """Lower this term to the existing one-loop vakint topology representation."""

        from .backends import vakint

        numerator = (
            self.pre_wilson_numerator
            if use_pre_wilson_numerator and self.pre_wilson_numerator is not None
            else self.numerator
        )
        return vakint.one_loop_vacuum_integral(
            numerator,
            self.mass_squareds,
            powers=self.propagator_powers,
        )

    def _repr_latex_(self) -> str:
        return (
            rf"$\mathrm{{WilsonLineTraceExpansionTerm}}\left("
            rf"{escape(self.trace_name)},\ {self.path_index}\right)$"
        )

    def _repr_html_(self) -> str:
        return (
            f"<code>WilsonLineTraceExpansionTerm({escape(self.trace_name)} "
            f"path={self.path_index} powers={self.propagator_powers} "
            f"weight={self.component_weight})</code>"
        )


@dataclass(frozen=True)
class BosonicCDETraceExpansionTerm:
    """One CDE-expanded supertrace-kernel term with explicit topology powers."""

    theory: Theory
    trace_name: str
    numerator: Expression
    mass_squareds: tuple[Expression, ...]
    propagator_powers: tuple[int, ...]

    def kernel_expression(self, *, loop_momentum_squared: Expression | None = None) -> Expression:
        """Return this term as a pychete ``SupertraceKernel`` expression."""

        momentum_squared = s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared
        denominators = tuple(
            s.PropagatorDenominator(momentum_squared, mass_squared) ** power
            for mass_squared, power in zip(self.mass_squareds, self.propagator_powers, strict=True)
        )
        return s.SupertraceKernel(self.numerator, list_expr(*(list_expr(denominator) for denominator in denominators)))

    def vakint_integral_expression(self) -> Expression:
        """Lower this term to the existing one-loop vakint topology representation."""

        from .backends import vakint

        return vakint.one_loop_vacuum_integral(
            self.numerator,
            self.mass_squareds,
            powers=self.propagator_powers,
        )

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{BosonicCDETraceExpansionTerm}}\left({escape(self.trace_name)}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>BosonicCDETraceExpansionTerm({escape(self.trace_name)} powers={self.propagator_powers})</code>"


@dataclass(frozen=True)
class PowerTypeSupertraceContribution:
    """Power-type one-loop supertrace contribution before final reduction."""

    theory: Theory
    trace: SupertraceBlockTrace
    eft_order: int
    heavy_field_dimension: bool = False

    @property
    def name(self) -> str:
        """Contribution name inherited from the underlying block trace."""

        return self.trace.name

    @property
    def order(self) -> int:
        """Power-trace order of this contribution."""

        return self.trace.order

    @property
    def prefactor(self) -> Expression:
        """Power-type logarithmic prefactor after the grading sign in ``trace``."""

        return self.trace.power_type_log_prefactor

    @property
    def numerator_expression(self) -> Expression:
        """Return the prefactor-weighted trace numerator."""

        from .backends import idenso

        return idenso.simplify_pychete_dirac_algebra((self.prefactor * self.trace.expression).expand())

    @property
    def eft_numerator_expression(self) -> Expression:
        """Return the prefactor-weighted numerator truncated by EFT order."""

        return series_eft(
            self.numerator_expression,
            self.theory,
            eft_order=self.eft_order,
            heavy_field_dimension=self.heavy_field_dimension,
        )

    def vakint_integral_expression(self, *, include_light: bool = True) -> Expression:
        """Return the EFT-truncated contribution lowered to vakint topology form."""

        from .backends import vakint

        return vakint.one_loop_vacuum_integral(
            self.eft_numerator_expression,
            _flatten_expression_slots(self.trace.propagator_mass_squared_chain(include_light=include_light)),
        )

    def to_expression_map(self, *, prefix: str = "power_type_supertrace") -> dict[str, Expression]:
        """Return deterministic expressions for this power-type contribution."""

        return {
            f"{prefix}[{self.name},numerator]": self.numerator_expression,
            f"{prefix}[{self.name},eft_numerator]": self.eft_numerator_expression,
            f"{prefix}[{self.name},vakint_integral]": self.vakint_integral_expression(),
        }

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{PowerTypeSupertraceContribution}}\left({escape(self.name)},\ {self.order}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>PowerTypeSupertraceContribution({escape(self.name)} order={self.order})</code>"


@dataclass(frozen=True)
class SupertracePlan:
    """Structured block data prepared for future supertrace generation."""

    theory: Theory
    operator: FluctuationOperator
    heavy_heavy: FluctuationOperatorBlock
    heavy_light: FluctuationOperatorBlock
    light_heavy: FluctuationOperatorBlock
    light_light: FluctuationOperatorBlock

    @property
    def heavy_mode_count(self) -> int:
        """Number of heavy fluctuation modes in the plan."""

        return len(self.heavy_heavy.rows)

    @property
    def light_mode_count(self) -> int:
        """Number of light fluctuation modes in the plan."""

        return len(self.light_light.rows)

    @property
    def heavy_supertrace_sign(self) -> int:
        """Sum of boson/fermion signs over heavy modes."""

        return sum(mode.supertrace_sign for mode in self.heavy_heavy.rows)

    @property
    def supertrace_category_labels(self) -> tuple[str, ...]:
        """Heavy/light spin categories present in this plan."""

        return _supertrace_category_labels(self.operator.modes)

    def blocks(self) -> tuple[FluctuationOperatorBlock, ...]:
        """Return the four heavy/light blocks in deterministic order."""

        return (self.heavy_heavy, self.heavy_light, self.light_heavy, self.light_light)

    def block_trace(
        self,
        name: str,
        *blocks: FluctuationOperatorBlock,
        cyclic_key: tuple[str, ...] | None = None,
    ) -> SupertraceBlockTrace:
        """Build a weighted closed-block trace kernel with Symbolica matrices."""

        if not blocks:
            raise ValueError("at least one fluctuation block is required")
        normalized_blocks = tuple(blocks)
        if any(block.theory.name != self.theory.name for block in normalized_blocks):
            raise ValueError(f"Supertrace blocks must belong to theory {self.theory.name!r}")
        _validate_closed_block_chain(normalized_blocks)
        return SupertraceBlockTrace(
            theory=self.theory,
            name=name,
            blocks=normalized_blocks,
            modes=normalized_blocks[0].rows,
            expression=_supertrace_block_product(normalized_blocks),
            cyclic_key=cyclic_key,
        )

    def category_block(self, row_category: str, column_category: str) -> FluctuationOperatorBlock:
        """Return a block restricted to Matchete-style supertrace categories."""

        row_sector = _supertrace_category_sector(row_category)
        column_sector = _supertrace_category_sector(column_category)
        source_block = self._sector_block(row_sector, column_sector)
        row_indices = _category_indices(source_block.rows, row_category)
        column_indices = _category_indices(source_block.columns, column_category)
        return FluctuationOperatorBlock(
            theory=self.theory,
            row_sector=row_sector,
            column_sector=column_sector,
            rows=tuple(source_block.rows[index] for index in row_indices),
            columns=tuple(source_block.columns[index] for index in column_indices),
            matrix=tuple(
                tuple(
                    source_block.matrix[row][column]
                    for column in column_indices
                )
                for row in row_indices
            ),
            row_category=row_category,
            column_category=column_category,
        )

    def _sector_block(
        self,
        row_sector: FluctuationSector,
        column_sector: FluctuationSector,
    ) -> FluctuationOperatorBlock:
        for block in self.blocks():
            if block.row_sector is row_sector and block.column_sector is column_sector:
                return block
        raise KeyError(f"Supertrace plan has no {row_sector.value}-{column_sector.value} block")

    def closed_block_traces(self, order: int, *, include_light_only: bool = False) -> tuple[SupertraceBlockTrace, ...]:
        """Generate all closed heavy/light sector trace kernels of an order."""

        if order < 1:
            raise ValueError("closed block trace order must be at least 1")
        traces: list[SupertraceBlockTrace] = []
        sectors = (FluctuationSector.HEAVY, FluctuationSector.LIGHT)
        block_by_sectors = {
            (block.row_sector, block.column_sector): block
            for block in self.blocks()
        }
        for path in product(sectors, repeat=order):
            closed_path = (*path, path[0])
            if not include_light_only and all(sector is FluctuationSector.LIGHT for sector in closed_path):
                continue
            blocks = tuple(
                block_by_sectors[(closed_path[index], closed_path[index + 1])]
                for index in range(order)
            )
            traces.append(self.block_trace(_sector_path_name(closed_path), *blocks))
        return tuple(traces)

    def closed_category_traces(self, order: int, *, include_light_only: bool = False) -> tuple[SupertraceBlockTrace, ...]:
        """Generate closed trace kernels split by heavy/light spin categories."""

        if order < 1:
            raise ValueError("closed category trace order must be at least 1")
        traces: list[SupertraceBlockTrace] = []
        labels = self.supertrace_category_labels
        for path in product(labels, repeat=order):
            light_only = all(_supertrace_category_sector(label) is FluctuationSector.LIGHT for label in path)
            if not include_light_only and light_only:
                continue
            closed_path = (*path, path[0])
            blocks = tuple(
                self.category_block(closed_path[index], closed_path[index + 1])
                for index in range(order)
            )
            traces.append(self.block_trace("-".join(path), *blocks, cyclic_key=path))
        return tuple(traces)

    def to_expression_map(self, *, prefix: str = "supertrace_input") -> dict[str, Expression]:
        """Return deterministic named expressions for all planned blocks."""

        entries: dict[str, Expression] = {}
        for block in self.blocks():
            entries.update(block.to_expression_map(prefix=prefix))
        return entries

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{SupertracePlan}}\left(H={self.heavy_mode_count},\ L={self.light_mode_count}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>SupertracePlan(heavy={self.heavy_mode_count} light={self.light_mode_count})</code>"


@dataclass(frozen=True)
class OneLoopSetup:
    """Prepared one-loop matching inputs before propagator expansion."""

    theory: Theory
    uv_lagrangian: Expression
    eft_order: int
    fluctuation_operator: FluctuationOperator
    supertrace_plan: SupertracePlan
    block_traces: tuple[SupertraceBlockTrace, ...]
    matchete_fluctuation_dof_basis: bool = False
    wilson_line_weight_paths_by_component_dofs: bool = False

    @property
    def max_trace_order(self) -> int:
        """Largest generated block-trace order."""

        if not self.block_traces:
            return 0
        return max(trace.order for trace in self.block_traces)

    @property
    def supertrace_kernel_count(self) -> int:
        """Number of generated supertrace block kernels."""

        return len(self.block_traces)

    @property
    def power_type_contribution_count(self) -> int:
        """Number of cyclically unique power-type supertrace contributions."""

        return len(self.power_type_contributions())

    @property
    def interaction_power_type_contribution_count(self) -> int:
        """Number of cyclically unique interaction-power contributions."""

        return len(self.interaction_power_type_contributions())

    def supertrace_expression_map(self, *, prefix: str = "supertrace_kernel") -> dict[str, Expression]:
        """Return deterministic named expressions for generated trace kernels."""

        entries: dict[str, Expression] = {}
        for trace in self.block_traces:
            entries.update(trace.to_expression_map(prefix=prefix))
        return entries

    def supertrace_propagator_expression_map(
        self,
        *,
        prefix: str = "supertrace_propagator_kernel",
        loop_momentum_squared: Expression | None = None,
        include_light: bool = True,
    ) -> dict[str, Expression]:
        """Return generated trace kernels decorated with propagator denominators."""

        return {
            f"{prefix}[{trace.name}]": trace.propagator_expression(
                loop_momentum_squared=loop_momentum_squared,
                include_light=include_light,
            )
            for trace in self.block_traces
        }

    def interaction_supertrace_plan(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> SupertracePlan:
        """Return a supertrace plan built from interaction-only operator blocks."""

        return self.fluctuation_operator.interaction_supertrace_plan(
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
        )

    def interaction_block_traces(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
    ) -> tuple[SupertraceBlockTrace, ...]:
        """Generate closed traces from interaction-only fluctuation blocks."""

        plan = self.interaction_supertrace_plan(
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
        )
        traces: list[SupertraceBlockTrace] = []
        for order in range(1, self.max_trace_order + 1):
            traces.extend(plan.closed_category_traces(order, include_light_only=include_light_only))
        return tuple(traces)

    def interaction_supertrace_expression_map(
        self,
        *,
        prefix: str = "interaction_supertrace_kernel",
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> dict[str, Expression]:
        """Return deterministic traces built from interaction-only blocks."""

        entries: dict[str, Expression] = {}
        for trace in self.interaction_block_traces(
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
        ):
            entries.update(trace.to_expression_map(prefix=prefix))
        return entries

    def interaction_bosonic_cde_expansion_plan(
        self,
        *,
        trace_names: Sequence[str] | None = None,
        max_total_order: int,
        max_slot_order: int | None = None,
        index_prefix: str = "cde",
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> BosonicCDEExpansionPlan:
        """Generate deterministic CDE derivative-order entries for interaction traces.

        The planner enumerates weak compositions of the total derivative order
        over each selected trace's propagator slots. It only allocates
        theory-owned Lorentz-index labels; the symbolic CDE expansion and
        subsequent vakint lowering stay in the native expression path used by
        ``interaction_bosonic_cde_expansion_terms``.
        """

        if max_total_order < 0:
            raise ValueError("max_total_order must be non-negative")
        if max_slot_order is not None and max_slot_order < 0:
            raise ValueError("max_slot_order must be non-negative")
        selected_trace_names = None if trace_names is None else tuple(dict.fromkeys(trace_names))
        traces = self._interaction_bosonic_cde_trace_map(
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            trace_names=selected_trace_names,
        )
        selected_trace_names = tuple(traces) if selected_trace_names is None else selected_trace_names
        entries: list[BosonicCDEExpansionPlanEntry] = []
        for trace_name in selected_trace_names:
            if trace_name not in traces:
                raise KeyError(f"One-loop setup has no interaction trace {trace_name!r}")
            trace = traces[trace_name]
            for total_order in range(max_total_order + 1):
                for slot_orders in _cde_slot_order_allocations(
                    total_order,
                    len(trace.blocks),
                    max_slot_order=max_slot_order,
                ):
                    entry_index = len(entries)
                    label = _cde_plan_entry_label(trace_name, entry_index, slot_orders)
                    entries.append(
                        BosonicCDEExpansionPlanEntry(
                            trace_name=trace_name,
                            expansion_indices=_cde_plan_expansion_indices(
                                self.theory,
                                trace_name=trace_name,
                                entry_index=entry_index,
                                slot_orders=slot_orders,
                                index_prefix=index_prefix,
                            ),
                            total_order=total_order,
                            slot_orders=slot_orders,
                            label=label,
                        )
                    )
        return BosonicCDEExpansionPlan(
            theory=self.theory,
            entries=tuple(entries),
            trace_names=selected_trace_names,
            max_total_order=max_total_order,
            max_slot_order=max_slot_order,
        )

    def interaction_wilson_line_trace_paths(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        trace_names: Sequence[str] | None = None,
    ) -> tuple[WilsonLineTracePath, ...]:
        """Return entry-level interaction traces with explicit Wilson lines."""

        if trace_names is None:
            traces = _cyclically_unique_traces(
                self.interaction_block_traces(
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                    include_light_only=include_light_only,
                )
            )
        else:
            traces = tuple(
                self.fluctuation_operator.interaction_category_trace(
                    _category_path_from_trace_name(name),
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                )
                for name in _selected_power_type_trace_names(
                    self.fluctuation_operator.modes,
                    max_trace_order=self.max_trace_order,
                    trace_names=tuple(dict.fromkeys(trace_names)),
                    include_light_only=include_light_only,
                )
            )
        return tuple(
            path
            for trace in traces
            for path in trace.wilson_line_trace_paths()
        )

    def interaction_wilson_line_trace_paths_by_trace(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        trace_names: Sequence[str] | None = None,
    ) -> dict[str, tuple[WilsonLineTracePath, ...]]:
        """Return Wilson-line interaction paths grouped by trace name."""

        grouped: dict[str, list[WilsonLineTracePath]] = {}
        for path in self.interaction_wilson_line_trace_paths(
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            trace_names=trace_names,
        ):
            grouped.setdefault(path.trace_name, []).append(path)
        return {trace_name: tuple(paths) for trace_name, paths in grouped.items()}

    def interaction_wilson_line_expansion_plan(
        self,
        *,
        trace_names: Sequence[str] | None = None,
        max_total_order: int,
        max_slot_order: int | None = None,
        index_prefix: str = "wilson_line",
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
    ) -> WilsonLineExpansionPlan:
        """Generate deterministic Wilson-line derivative-order entries for selected traces."""

        if max_total_order < 0:
            raise ValueError("max_total_order must be non-negative")
        if max_slot_order is not None and max_slot_order < 0:
            raise ValueError("max_slot_order must be non-negative")
        selected_trace_names = None if trace_names is None else tuple(dict.fromkeys(trace_names))
        paths_by_trace = self.interaction_wilson_line_trace_paths_by_trace(
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            trace_names=selected_trace_names,
        )
        selected_trace_names = tuple(paths_by_trace) if selected_trace_names is None else selected_trace_names
        entries: list[WilsonLineExpansionPlanEntry] = []
        for trace_name in selected_trace_names:
            if trace_name not in paths_by_trace:
                raise KeyError(f"One-loop setup has no Wilson-line interaction trace {trace_name!r}")
            slot_count = paths_by_trace[trace_name][0].order
            for total_order in range(max_total_order + 1):
                for slot_orders in _cde_slot_order_allocations(
                    total_order,
                    slot_count,
                    max_slot_order=max_slot_order,
                ):
                    entry_index = len(entries)
                    label = _wilson_line_plan_entry_label(trace_name, entry_index, slot_orders)
                    entries.append(
                        WilsonLineExpansionPlanEntry(
                            trace_name=trace_name,
                            expansion_indices=_wilson_line_plan_expansion_indices(
                                self.theory,
                                trace_name=trace_name,
                                entry_index=entry_index,
                                slot_orders=slot_orders,
                                index_prefix=index_prefix,
                            ),
                            total_order=total_order,
                            slot_orders=slot_orders,
                            label=label,
                        )
                    )
        return WilsonLineExpansionPlan(
            theory=self.theory,
            entries=tuple(entries),
            trace_names=selected_trace_names,
            max_total_order=max_total_order,
            max_slot_order=max_slot_order,
        )

    def _interaction_wilson_line_plan_entries(
        self,
        expansion_request: WilsonLineExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
    ) -> tuple[WilsonLineExpansionPlanEntry, ...]:
        if isinstance(expansion_request, WilsonLineExpansionPlan):
            entries = expansion_request.entries
        else:
            entries = tuple(
                WilsonLineExpansionPlanEntry(
                    trace_name=trace_name,
                    expansion_indices=_normalize_cde_expansion_indices(expansion_indices),
                    total_order=sum(len(indices) for indices in expansion_indices),
                    slot_orders=tuple(len(indices) for indices in expansion_indices),
                    label=trace_name,
                )
                for trace_name, expansion_indices in expansion_request.items()
            )
        paths_by_trace = self.interaction_wilson_line_trace_paths_by_trace(
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            trace_names=tuple(entry.trace_name for entry in entries),
        )
        missing = tuple(entry.trace_name for entry in entries if entry.trace_name not in paths_by_trace)
        if missing:
            raise KeyError(f"One-loop setup has no Wilson-line interaction trace {missing[0]!r}")
        return entries

    def interaction_wilson_line_kernel_expression_map(
        self,
        *,
        prefix: str = "interaction_wilson_line_kernel",
        loop_momentum_squared: Expression | None = None,
        include_light: bool = True,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
    ) -> dict[str, Expression]:
        """Return interaction Wilson-line path kernels as named expressions."""

        return {
            f"{prefix}[{path.trace_name},{path.path_index}]": path.kernel_expression(
                loop_momentum_squared=loop_momentum_squared,
                include_light=include_light,
            )
            for path in self.interaction_wilson_line_trace_paths(
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                include_light_only=include_light_only,
            )
        }

    def interaction_wilson_line_expansion_terms_by_trace(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        simplify_pychete_color_algebra: bool = False,
        collect_path_sums: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> dict[str, tuple[WilsonLineTraceExpansionTerm, ...]]:
        """Return Wilson-line propagator-expanded terms grouped by trace name."""

        grouped: dict[str, tuple[WilsonLineTraceExpansionTerm, ...]] = {}
        plan_entries = self._interaction_wilson_line_plan_entries(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
        )
        paths_by_trace = self.interaction_wilson_line_trace_paths_by_trace(
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            trace_names=tuple(entry.trace_name for entry in plan_entries),
        )
        path_term_cache: dict[
            tuple[str, tuple[tuple[str, ...], ...], str],
            tuple[WilsonLineTracePath, tuple[WilsonLineTraceExpansionTerm, ...]],
        ] = {}
        path_cache_hits = 0
        for entry in plan_entries:
            if collect_path_sums:
                grouped[entry.label] = _filter_wilson_line_terms_by_projection_requirements(
                    _collected_wilson_line_terms_for_entry(
                        entry,
                        paths_by_trace[entry.trace_name],
                        weight_paths_by_component_dofs=self.wilson_line_weight_paths_by_component_dofs,
                        act_open_derivatives=act_open_derivatives,
                        emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                        emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                        covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                        expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                        max_wilson_derivative_order=max_wilson_derivative_order,
                        simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                        term_atom_requirements=term_atom_requirements,
                    ),
                    term_atom_requirements,
                )
                continue
            terms: list[WilsonLineTraceExpansionTerm] = []
            for path in paths_by_trace[entry.trace_name]:
                if not _wilson_line_entry_can_satisfy_projection_requirements(
                    path,
                    entry,
                    term_atom_requirements,
                ):
                    continue
                path = _wilson_line_path_with_projection_filtered_entries(path, term_atom_requirements)
                cache_key = _wilson_line_path_term_cache_key(path, entry)
                cached = path_term_cache.get(cache_key) if cache_key is not None else None
                if cached is None:
                    path_terms = path.propagator_expansion_terms(
                        entry.expansion_indices,
                        act_open_derivatives=act_open_derivatives,
                        emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                        emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                        covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                        expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                        max_wilson_derivative_order=max_wilson_derivative_order,
                        simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                    )
                    if cache_key is not None:
                        path_term_cache[cache_key] = (path, path_terms)
                else:
                    source_path, source_terms = cached
                    path_terms = _clone_wilson_line_terms_for_path(source_terms, source_path, path)
                    path_cache_hits += 1
                if self.wilson_line_weight_paths_by_component_dofs:
                    path_terms = _component_weighted_wilson_line_terms(
                        path,
                        path_terms,
                    )
                terms.extend(path_terms)
            grouped[entry.label] = _filter_wilson_line_terms_by_projection_requirements(
                terms,
                term_atom_requirements,
            )
        if path_cache_hits:
            _LOGGER.debug("reused %s cached Wilson-line path-template expansions", path_cache_hits)
        return grouped

    def interaction_wilson_line_expansion_terms(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        simplify_pychete_color_algebra: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> tuple[WilsonLineTraceExpansionTerm, ...]:
        """Return selected Wilson-line propagator-expanded terms in deterministic order."""

        grouped = self.interaction_wilson_line_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            term_atom_requirements=term_atom_requirements,
        )
        return tuple(term for terms in grouped.values() for term in terms)

    def interaction_wilson_line_expansion_kernel_expression_map(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        prefix: str = "interaction_wilson_line_expansion_kernel",
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        simplify_pychete_color_algebra: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> dict[str, Expression]:
        """Return selected Wilson-line propagator-expanded terms as kernels."""

        grouped_terms = self.interaction_wilson_line_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            term_atom_requirements=term_atom_requirements,
        )
        return _wilson_line_kernel_expression_map_from_terms(
            grouped_terms,
            prefix=prefix,
            loop_momentum_squared=loop_momentum_squared,
        )

    def interaction_wilson_line_expansion_vakint_integral_expression_map(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        prefix: str = "interaction_wilson_line_expansion_vakint_integral",
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        simplify_pychete_color_algebra: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> dict[str, Expression]:
        """Return selected Wilson-line propagator-expanded terms as vakint topologies."""

        grouped_terms = self.interaction_wilson_line_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            term_atom_requirements=term_atom_requirements,
        )
        return _wilson_line_vakint_integral_expression_map_from_terms(grouped_terms, prefix=prefix)

    def interaction_wilson_line_vakint_integral_sum(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        epsilon: Expression | None = None,
        short_form: bool | None = None,
        engine: Any | None = None,
        simplify_pychete_color_algebra: bool = False,
        expose_scalar_derivative_commutator_bilinears: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> Expression:
        """Return the summed selected Wilson-line-expanded interaction topologies."""

        grouped_terms = self.interaction_wilson_line_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            term_atom_requirements=term_atom_requirements,
        )
        terms = _flatten_wilson_line_terms(grouped_terms)
        raw_terms = tuple(term.vakint_integral_expression() for term in terms)
        if VakintIntegralStage.from_user(stage) is VakintIntegralStage.RAW:
            return _wilson_line_raw_integral_sum_from_expressions(raw_terms)
        vakint_sum = _vakint_integral_terms_at_stage(
            raw_terms,
            theory=self.theory,
            stage=VakintIntegralStage.from_user(stage),
            short_form=short_form,
            engine=engine,
            label="Wilson-line",
        )
        return _postprocess_wilson_line_vakint_stage_expression(
            self.theory,
            vakint_sum,
            stage=VakintIntegralStage.from_user(stage),
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            expose_scalar_derivative_commutator_bilinears=expose_scalar_derivative_commutator_bilinears,
            epsilon=epsilon,
        )

    def interaction_wilson_line_internal_integral_sum(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        tensor_reduce_before_wilson_expand: bool = False,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
        simplify_pychete_color_algebra: bool = False,
        expose_scalar_derivative_commutator_bilinears: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> Expression:
        """Evaluate selected Wilson-line-expanded integrals with pychete."""

        grouped_terms = self.interaction_wilson_line_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            term_atom_requirements=term_atom_requirements,
        )
        return _wilson_line_internal_integral_sum_from_terms(
            self.theory,
            _flatten_wilson_line_terms(grouped_terms),
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            tensor_reduce_before_wilson_expand=tensor_reduce_before_wilson_expand,
            max_wilson_derivative_order=max_wilson_derivative_order,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            expose_scalar_derivative_commutator_bilinears=expose_scalar_derivative_commutator_bilinears,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
        )

    def interaction_wilson_line_matching_result(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
        simplify_pychete_color_algebra: bool = False,
        expose_scalar_derivative_commutator_bilinears: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the selected Wilson-line-expanded interaction one-loop result."""

        selected_vakint_stage = VakintIntegralStage.from_user(vakint_stage)
        selected_named_stage = VakintIntegralStage.from_user(named_supertrace_stage)
        grouped_terms = self.interaction_wilson_line_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            term_atom_requirements=term_atom_requirements,
        )
        terms = _flatten_wilson_line_terms(grouped_terms)
        raw_named_integrals = _wilson_line_vakint_integral_expression_map_from_terms(grouped_terms)
        raw_integral_expressions = tuple(raw_named_integrals.values())
        if selected_vakint_stage is VakintIntegralStage.RAW:
            vakint_sum = _wilson_line_raw_integral_sum_from_expressions(raw_integral_expressions)
        else:
            vakint_sum = _vakint_integral_terms_at_stage(
                raw_integral_expressions,
                theory=self.theory,
                stage=selected_vakint_stage,
                short_form=vakint_short_form,
                engine=vakint_engine,
                label="Wilson-line",
            )
            vakint_sum = _postprocess_wilson_line_vakint_stage_expression(
                self.theory,
                vakint_sum,
                stage=selected_vakint_stage,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=False,
                epsilon=epsilon,
            )
        named_integrals = {
            name: _postprocess_wilson_line_vakint_stage_expression(
                self.theory,
                _vakint_expression_at_stage(
                    expr,
                    theory=self.theory,
                    stage=selected_named_stage,
                    short_form=named_supertrace_short_form,
                    engine=named_supertrace_engine,
                ),
                stage=selected_named_stage,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=False,
                epsilon=epsilon,
            )
            for name, expr in raw_named_integrals.items()
        }
        supertraces = {
            **_wilson_line_kernel_expression_map_from_terms(
                grouped_terms,
                loop_momentum_squared=loop_momentum_squared,
            ),
            **named_integrals,
            "interaction_wilson_line_vakint_integral_sum": vakint_sum,
            f"interaction_wilson_line_vakint_integral_sum[{selected_vakint_stage.value}]": vakint_sum,
        }
        if selected_vakint_stage is VakintIntegralStage.EVALUATED:
            from .backends import vakint

            supertraces["interaction_wilson_line_vakint_pole_part"] = vakint.pole_part(
                vakint_sum,
                max_pole_order=max_pole_order,
                epsilon=epsilon,
            )
            finite_part = vakint.finite_part(
                vakint_sum,
                epsilon=epsilon,
            )
            if expose_scalar_derivative_commutator_bilinears:
                supertraces[
                    "interaction_wilson_line_vakint_finite_part_before_scalar_commutator_bilinears"
                ] = finite_part
                finite_part = _apply_wilson_line_post_integral_scalar_commutator_bilinears(
                    self.theory,
                    finite_part,
                )
            supertraces["interaction_wilson_line_vakint_finite_part"] = finite_part
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=vakint_sum,
            on_shell_eft_lagrangian=vakint_sum,
            fluctuation_operators={
                **self.fluctuation_operator.to_expression_map(),
                **self.fluctuation_operator.interaction_expression_map(),
            },
            supertraces=supertraces,
            metadata={
                "stage": "interaction_wilson_line_vakint_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                **_wilson_line_expansion_request_metadata(expansion_indices_by_trace),
                **_wilson_line_expansion_term_metadata(grouped_terms),
                "interaction_wilson_line_term_count": len(terms),
                "interaction_wilson_line_paths_weighted_by_component_dofs": (
                    self.wilson_line_weight_paths_by_component_dofs
                ),
                "matchete_fluctuation_dof_basis": self.matchete_fluctuation_dof_basis,
                "interaction_wilson_line_terms_filtered_by_matching_targets": term_atom_requirements is not None,
                "interaction_wilson_line_pychete_color_algebra_simplified": simplify_pychete_color_algebra,
                "interaction_wilson_line_scalar_derivative_commutator_bilinears_exposed": (
                    expose_scalar_derivative_commutator_bilinears
                ),
                "interaction_wilson_line_act_open_derivatives": act_open_derivatives,
                "interaction_wilson_line_commutators_emitted": emit_covariant_derivative_commutators,
                "interaction_wilson_line_commutator_emit_passes": (
                    emit_covariant_derivative_commutator_passes
                    if emit_covariant_derivative_commutators
                    else None
                ),
                "interaction_wilson_line_commutator_emit_mode": (
                    covariant_derivative_commutator_mode
                    if emit_covariant_derivative_commutators
                    else None
                ),
                "interaction_wilson_line_commutators_expanded": expand_covariant_derivative_commutators,
                "interaction_wilson_line_max_derivative_order": max_wilson_derivative_order,
                "on_shell_reduced": False,
                "vakint_stage": selected_vakint_stage.value,
                "named_supertrace_stage": selected_named_stage.value,
                "interaction_wilson_line_vakint_termwise_stage": selected_vakint_stage is not VakintIntegralStage.RAW,
                "uses_interaction_operator": True,
                "uses_wilson_line_expansion": True,
            },
        )

    def interaction_wilson_line_internal_matching_result(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        tensor_reduce_before_wilson_expand: bool = False,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
        simplify_pychete_color_algebra: bool = False,
        expose_scalar_derivative_commutator_bilinears: bool = False,
        internal_evaluation_mode: WilsonLineInternalEvaluationMode | str = WilsonLineInternalEvaluationMode.TERMWISE,
        collect_path_sums: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the Wilson-line-expanded interaction result evaluated internally."""

        from .backends import vakint

        grouped_terms = self.interaction_wilson_line_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            collect_path_sums=collect_path_sums,
            term_atom_requirements=term_atom_requirements,
        )
        terms = _flatten_wilson_line_terms(grouped_terms)
        raw_vakint_integrals = _wilson_line_vakint_integral_expression_map_from_terms(grouped_terms)
        raw_vakint_sum = _wilson_line_raw_integral_sum_from_expressions(raw_vakint_integrals.values())
        selected_internal_evaluation_mode = WilsonLineInternalEvaluationMode.from_user(internal_evaluation_mode)
        evaluated_terms_by_entry: dict[str, tuple[Expression, ...]]
        if selected_internal_evaluation_mode is WilsonLineInternalEvaluationMode.ENTRYWISE:
            evaluated_entry_expressions = _wilson_line_internal_evaluated_entry_expressions_by_entry_from_terms(
                self.theory,
                grouped_terms,
                tensor_reduce=tensor_reduce,
                tensor_reduce_engine=tensor_reduce_engine,
                tensor_reduce_before_wilson_expand=tensor_reduce_before_wilson_expand,
                max_wilson_derivative_order=max_wilson_derivative_order,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
            )
            evaluated_terms_by_entry = {
                entry_label: (entry_expression,)
                for entry_label, entry_expression in evaluated_entry_expressions.items()
            }
        else:
            evaluated_terms_by_entry = _wilson_line_internal_evaluated_terms_by_entry_from_terms(
                self.theory,
                grouped_terms,
                tensor_reduce=tensor_reduce,
                tensor_reduce_engine=tensor_reduce_engine,
                tensor_reduce_before_wilson_expand=tensor_reduce_before_wilson_expand,
                max_wilson_derivative_order=max_wilson_derivative_order,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=expose_scalar_derivative_commutator_bilinears,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
            )
        evaluated_terms = _flatten_expression_slots(evaluated_terms_by_entry.values())
        evaluated_by_entry = _wilson_line_internal_expression_map_by_entry(
            evaluated_terms_by_entry,
            "interaction_wilson_line_internal_integral_sum",
            combine_terms=combine_terms,
        )
        evaluated = _sum_wilson_line_internal_terms(evaluated_terms, combine_terms=combine_terms)
        pole_terms_by_entry = {
            entry_label: tuple(
                vakint.pole_part(term, max_pole_order=max_pole_order, epsilon=epsilon)
                for term in entry_terms
            )
            for entry_label, entry_terms in evaluated_terms_by_entry.items()
        }
        pole_by_entry = _wilson_line_internal_expression_map_by_entry(
            pole_terms_by_entry,
            "interaction_wilson_line_internal_integral_pole_part",
            combine_terms=combine_terms,
        )
        pole = _sum_wilson_line_internal_terms(
            _flatten_expression_slots(pole_terms_by_entry.values()),
            combine_terms=combine_terms,
        )
        finite_terms_by_entry = {
            entry_label: tuple(vakint.finite_part(term, epsilon=epsilon) for term in entry_terms)
            for entry_label, entry_terms in evaluated_terms_by_entry.items()
        }
        finite_by_entry = _wilson_line_internal_expression_map_by_entry(
            finite_terms_by_entry,
            "interaction_wilson_line_internal_integral_finite_part",
            combine_terms=combine_terms,
        )
        finite = _sum_wilson_line_internal_terms(
            _flatten_expression_slots(finite_terms_by_entry.values()),
            combine_terms=combine_terms,
        )
        through_finite_terms_by_entry = {
            entry_label: tuple(
                vakint.through_finite_part(
                    term,
                    max_pole_order=max_pole_order,
                    epsilon=epsilon,
                )
                for term in entry_terms
            )
            for entry_label, entry_terms in evaluated_terms_by_entry.items()
        }
        through_finite_by_entry = _wilson_line_internal_expression_map_by_entry(
            through_finite_terms_by_entry,
            "interaction_wilson_line_internal_integral_through_finite_part",
            combine_terms=combine_terms,
        )
        through_finite = _sum_wilson_line_internal_terms(
            _flatten_expression_slots(through_finite_terms_by_entry.values()),
            combine_terms=combine_terms,
        )
        scalar_bilinear_supertraces: dict[str, Expression] = {}
        if expose_scalar_derivative_commutator_bilinears:
            finite_before_scalar_bilinears = finite
            through_finite_before_scalar_bilinears = through_finite
            finite = _apply_wilson_line_post_integral_scalar_commutator_bilinears(self.theory, finite)
            through_finite = _apply_wilson_line_post_integral_scalar_commutator_bilinears(
                self.theory,
                through_finite,
            )
            scalar_bilinear_supertraces = {
                "interaction_wilson_line_internal_integral_finite_part_before_scalar_commutator_bilinears": (
                    finite_before_scalar_bilinears
                ),
                "interaction_wilson_line_internal_integral_through_finite_part_before_scalar_commutator_bilinears": (
                    through_finite_before_scalar_bilinears
                ),
            }
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=evaluated,
            on_shell_eft_lagrangian=evaluated,
            fluctuation_operators={
                **self.fluctuation_operator.to_expression_map(),
                **self.fluctuation_operator.interaction_expression_map(),
            },
            supertraces={
                **_wilson_line_kernel_expression_map_from_terms(
                    grouped_terms,
                    loop_momentum_squared=loop_momentum_squared,
                ),
                **raw_vakint_integrals,
                **evaluated_by_entry,
                **pole_by_entry,
                **finite_by_entry,
                **through_finite_by_entry,
                **scalar_bilinear_supertraces,
                "interaction_wilson_line_vakint_integral_sum": raw_vakint_sum,
                "interaction_wilson_line_internal_integral_sum": evaluated,
                "interaction_wilson_line_internal_integral_pole_part": pole,
                "interaction_wilson_line_internal_integral_finite_part": finite,
                "interaction_wilson_line_internal_integral_through_finite_part": through_finite,
            },
            metadata={
                "stage": "interaction_wilson_line_internal_integral_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                **_wilson_line_expansion_request_metadata(expansion_indices_by_trace),
                **_wilson_line_expansion_term_metadata(grouped_terms),
                "interaction_wilson_line_term_count": len(terms),
                "interaction_wilson_line_paths_weighted_by_component_dofs": (
                    self.wilson_line_weight_paths_by_component_dofs
                ),
                "matchete_fluctuation_dof_basis": self.matchete_fluctuation_dof_basis,
                "interaction_wilson_line_terms_filtered_by_matching_targets": term_atom_requirements is not None,
                "interaction_wilson_line_pychete_color_algebra_simplified": simplify_pychete_color_algebra,
                "interaction_wilson_line_scalar_derivative_commutator_bilinears_exposed": (
                    expose_scalar_derivative_commutator_bilinears
                ),
                "interaction_wilson_line_act_open_derivatives": act_open_derivatives,
                "interaction_wilson_line_commutators_emitted": emit_covariant_derivative_commutators,
                "interaction_wilson_line_commutator_emit_passes": (
                    emit_covariant_derivative_commutator_passes
                    if emit_covariant_derivative_commutators
                    else None
                ),
                "interaction_wilson_line_commutator_emit_mode": (
                    covariant_derivative_commutator_mode
                    if emit_covariant_derivative_commutators
                    else None
                ),
                "interaction_wilson_line_commutators_expanded": expand_covariant_derivative_commutators,
                "interaction_wilson_line_max_derivative_order": max_wilson_derivative_order,
                "on_shell_reduced": False,
                "integral_backend": "pychete_internal",
                "tensor_reduce": tensor_reduce,
                "interaction_wilson_line_tensor_reduce_before_wilson_expand": (
                    tensor_reduce_before_wilson_expand
                ),
                "interaction_wilson_line_internal_evaluation_mode": selected_internal_evaluation_mode.value,
                "interaction_wilson_line_path_sums_collected": collect_path_sums,
                "interaction_wilson_line_internal_termwise_evaluation": (
                    selected_internal_evaluation_mode is WilsonLineInternalEvaluationMode.TERMWISE
                ),
                "combine_terms": combine_terms,
                "uses_interaction_operator": True,
                "uses_wilson_line_expansion": True,
                "max_pole_order": max_pole_order,
            },
        )

    def interaction_wilson_line_internal_minimal_subtraction_result(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        tensor_reduce_before_wilson_expand: bool = False,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
        simplify_pychete_color_algebra: bool = False,
        expose_scalar_derivative_commutator_bilinears: bool = False,
        internal_evaluation_mode: WilsonLineInternalEvaluationMode | str = WilsonLineInternalEvaluationMode.TERMWISE,
        collect_path_sums: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the internal Wilson-line result after minimal-subtraction pole removal."""

        from .backends import vakint

        grouped_terms = self.interaction_wilson_line_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            collect_path_sums=collect_path_sums,
            term_atom_requirements=term_atom_requirements,
        )
        terms = _flatten_wilson_line_terms(grouped_terms)
        raw_vakint_integrals = _wilson_line_vakint_integral_expression_map_from_terms(grouped_terms)
        raw_vakint_sum = _wilson_line_raw_integral_sum_from_expressions(raw_vakint_integrals.values())
        selected_internal_evaluation_mode = WilsonLineInternalEvaluationMode.from_user(internal_evaluation_mode)
        evaluated_terms_by_entry: dict[str, tuple[Expression, ...]]
        if selected_internal_evaluation_mode is WilsonLineInternalEvaluationMode.ENTRYWISE:
            evaluated_entry_expressions = _wilson_line_internal_evaluated_entry_expressions_by_entry_from_terms(
                self.theory,
                grouped_terms,
                tensor_reduce=tensor_reduce,
                tensor_reduce_engine=tensor_reduce_engine,
                tensor_reduce_before_wilson_expand=tensor_reduce_before_wilson_expand,
                max_wilson_derivative_order=max_wilson_derivative_order,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
            )
            evaluated_terms_by_entry = {
                entry_label: (entry_expression,)
                for entry_label, entry_expression in evaluated_entry_expressions.items()
            }
        else:
            evaluated_terms_by_entry = _wilson_line_internal_evaluated_terms_by_entry_from_terms(
                self.theory,
                grouped_terms,
                tensor_reduce=tensor_reduce,
                tensor_reduce_engine=tensor_reduce_engine,
                tensor_reduce_before_wilson_expand=tensor_reduce_before_wilson_expand,
                max_wilson_derivative_order=max_wilson_derivative_order,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=expose_scalar_derivative_commutator_bilinears,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
            )
        evaluated_terms = _flatten_expression_slots(evaluated_terms_by_entry.values())
        evaluated_by_entry = _wilson_line_internal_expression_map_by_entry(
            evaluated_terms_by_entry,
            "interaction_wilson_line_internal_integral_sum",
            combine_terms=combine_terms,
        )
        evaluated = _sum_wilson_line_internal_terms(evaluated_terms, combine_terms=combine_terms)
        pole_terms_by_entry = {
            entry_label: tuple(
                vakint.pole_part(term, max_pole_order=max_pole_order, epsilon=epsilon)
                for term in entry_terms
            )
            for entry_label, entry_terms in evaluated_terms_by_entry.items()
        }
        pole_by_entry = _wilson_line_internal_expression_map_by_entry(
            pole_terms_by_entry,
            "interaction_wilson_line_internal_integral_pole_part",
            combine_terms=combine_terms,
        )
        pole = _sum_wilson_line_internal_terms(
            _flatten_expression_slots(pole_terms_by_entry.values()),
            combine_terms=combine_terms,
        )
        finite_terms_by_entry = {
            entry_label: tuple(vakint.finite_part(term, epsilon=epsilon) for term in entry_terms)
            for entry_label, entry_terms in evaluated_terms_by_entry.items()
        }
        finite_by_entry = _wilson_line_internal_expression_map_by_entry(
            finite_terms_by_entry,
            "interaction_wilson_line_internal_integral_finite_part",
            combine_terms=combine_terms,
        )
        finite = _sum_wilson_line_internal_terms(
            _flatten_expression_slots(finite_terms_by_entry.values()),
            combine_terms=combine_terms,
        )
        through_finite_terms_by_entry = {
            entry_label: tuple(
                vakint.through_finite_part(
                    term,
                    max_pole_order=max_pole_order,
                    epsilon=epsilon,
                )
                for term in entry_terms
            )
            for entry_label, entry_terms in evaluated_terms_by_entry.items()
        }
        through_finite_by_entry = _wilson_line_internal_expression_map_by_entry(
            through_finite_terms_by_entry,
            "interaction_wilson_line_internal_integral_through_finite_part",
            combine_terms=combine_terms,
        )
        through_finite = _sum_wilson_line_internal_terms(
            _flatten_expression_slots(through_finite_terms_by_entry.values()),
            combine_terms=combine_terms,
        )
        scalar_bilinear_supertraces: dict[str, Expression] = {}
        if expose_scalar_derivative_commutator_bilinears:
            finite_before_scalar_bilinears = finite
            through_finite_before_scalar_bilinears = through_finite
            finite = _apply_wilson_line_post_integral_scalar_commutator_bilinears(self.theory, finite)
            through_finite = _apply_wilson_line_post_integral_scalar_commutator_bilinears(
                self.theory,
                through_finite,
            )
            scalar_bilinear_supertraces = {
                "interaction_wilson_line_internal_integral_finite_part_before_scalar_commutator_bilinears": (
                    finite_before_scalar_bilinears
                ),
                "interaction_wilson_line_internal_integral_through_finite_part_before_scalar_commutator_bilinears": (
                    through_finite_before_scalar_bilinears
                ),
            }
        counterterm = -pole
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=finite,
            on_shell_eft_lagrangian=finite,
            fluctuation_operators={
                **self.fluctuation_operator.to_expression_map(),
                **self.fluctuation_operator.interaction_expression_map(),
            },
            supertraces={
                **_wilson_line_kernel_expression_map_from_terms(
                    grouped_terms,
                    loop_momentum_squared=loop_momentum_squared,
                ),
                **raw_vakint_integrals,
                **evaluated_by_entry,
                **pole_by_entry,
                **finite_by_entry,
                **through_finite_by_entry,
                **scalar_bilinear_supertraces,
                "interaction_wilson_line_vakint_integral_sum": raw_vakint_sum,
                "interaction_wilson_line_internal_integral_sum": evaluated,
                "interaction_wilson_line_internal_integral_pole_part": pole,
                "interaction_wilson_line_internal_integral_finite_part": finite,
                "interaction_wilson_line_internal_integral_through_finite_part": through_finite,
                "interaction_wilson_line_internal_integral_ms_counterterm": counterterm,
            },
            metadata={
                "stage": "interaction_wilson_line_internal_minimal_subtraction_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                **_wilson_line_expansion_request_metadata(expansion_indices_by_trace),
                **_wilson_line_expansion_term_metadata(grouped_terms),
                "interaction_wilson_line_term_count": len(terms),
                "interaction_wilson_line_paths_weighted_by_component_dofs": (
                    self.wilson_line_weight_paths_by_component_dofs
                ),
                "matchete_fluctuation_dof_basis": self.matchete_fluctuation_dof_basis,
                "interaction_wilson_line_terms_filtered_by_matching_targets": term_atom_requirements is not None,
                "interaction_wilson_line_pychete_color_algebra_simplified": simplify_pychete_color_algebra,
                "interaction_wilson_line_scalar_derivative_commutator_bilinears_exposed": (
                    expose_scalar_derivative_commutator_bilinears
                ),
                "interaction_wilson_line_act_open_derivatives": act_open_derivatives,
                "interaction_wilson_line_commutators_emitted": emit_covariant_derivative_commutators,
                "interaction_wilson_line_commutator_emit_passes": (
                    emit_covariant_derivative_commutator_passes
                    if emit_covariant_derivative_commutators
                    else None
                ),
                "interaction_wilson_line_commutator_emit_mode": (
                    covariant_derivative_commutator_mode
                    if emit_covariant_derivative_commutators
                    else None
                ),
                "interaction_wilson_line_commutators_expanded": expand_covariant_derivative_commutators,
                "interaction_wilson_line_max_derivative_order": max_wilson_derivative_order,
                "on_shell_reduced": False,
                "integral_backend": "pychete_internal",
                "tensor_reduce": tensor_reduce,
                "interaction_wilson_line_tensor_reduce_before_wilson_expand": (
                    tensor_reduce_before_wilson_expand
                ),
                "interaction_wilson_line_internal_evaluation_mode": selected_internal_evaluation_mode.value,
                "interaction_wilson_line_path_sums_collected": collect_path_sums,
                "interaction_wilson_line_internal_termwise_evaluation": (
                    selected_internal_evaluation_mode is WilsonLineInternalEvaluationMode.TERMWISE
                ),
                "interaction_wilson_line_internal_termwise_minimal_subtraction": (
                    selected_internal_evaluation_mode is WilsonLineInternalEvaluationMode.TERMWISE
                ),
                "combine_terms": combine_terms,
                "uses_interaction_operator": True,
                "uses_wilson_line_expansion": True,
                "max_pole_order": max_pole_order,
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
            },
        )

    def interaction_wilson_line_minimal_subtraction_result(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
        simplify_pychete_color_algebra: bool = False,
        expose_scalar_derivative_commutator_bilinears: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the finite native-vakint Wilson-line result after pole subtraction."""

        from .backends import vakint

        grouped_terms = self.interaction_wilson_line_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            term_atom_requirements=term_atom_requirements,
        )
        terms = _flatten_wilson_line_terms(grouped_terms)
        raw_named_integrals = _wilson_line_vakint_integral_expression_map_from_terms(grouped_terms)
        evaluated = _vakint_integral_terms_at_stage(
            tuple(raw_named_integrals.values()),
            theory=self.theory,
            stage=VakintIntegralStage.EVALUATED,
            engine=vakint_engine,
            label="Wilson-line",
        )
        evaluated = _postprocess_wilson_line_vakint_stage_expression(
            self.theory,
            evaluated,
            stage=VakintIntegralStage.EVALUATED,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            expose_scalar_derivative_commutator_bilinears=False,
            epsilon=epsilon,
        )
        selected_named_stage = VakintIntegralStage.from_user(named_supertrace_stage)
        pole = vakint.pole_part(evaluated, max_pole_order=max_pole_order, epsilon=epsilon)
        finite = vakint.finite_part(evaluated, epsilon=epsilon)
        scalar_bilinear_supertraces: dict[str, Expression] = {}
        if expose_scalar_derivative_commutator_bilinears:
            finite_before_scalar_bilinears = finite
            finite = _apply_wilson_line_post_integral_scalar_commutator_bilinears(self.theory, finite)
            scalar_bilinear_supertraces = {
                "interaction_wilson_line_vakint_finite_part_before_scalar_commutator_bilinears": (
                    finite_before_scalar_bilinears
                ),
            }
        counterterm = (-pole).expand()
        named_integrals = {
            name: _postprocess_wilson_line_vakint_stage_expression(
                self.theory,
                _vakint_expression_at_stage(
                    expr,
                    theory=self.theory,
                    stage=selected_named_stage,
                    short_form=named_supertrace_short_form,
                    engine=named_supertrace_engine,
                ),
                stage=selected_named_stage,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=False,
                epsilon=epsilon,
            )
            for name, expr in raw_named_integrals.items()
        }
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=finite,
            on_shell_eft_lagrangian=finite,
            fluctuation_operators={
                **self.fluctuation_operator.to_expression_map(),
                **self.fluctuation_operator.interaction_expression_map(),
            },
            supertraces={
                **_wilson_line_kernel_expression_map_from_terms(
                    grouped_terms,
                    loop_momentum_squared=loop_momentum_squared,
                ),
                **named_integrals,
                **scalar_bilinear_supertraces,
                "interaction_wilson_line_vakint_integral_sum": evaluated,
                "interaction_wilson_line_vakint_integral_sum[evaluated]": evaluated,
                "interaction_wilson_line_vakint_pole_part": pole,
                "interaction_wilson_line_vakint_ms_counterterm": counterterm,
                "interaction_wilson_line_vakint_finite_part": finite,
            },
            metadata={
                "stage": "interaction_wilson_line_minimal_subtraction_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                **_wilson_line_expansion_request_metadata(expansion_indices_by_trace),
                **_wilson_line_expansion_term_metadata(grouped_terms),
                "interaction_wilson_line_term_count": len(terms),
                "interaction_wilson_line_paths_weighted_by_component_dofs": (
                    self.wilson_line_weight_paths_by_component_dofs
                ),
                "matchete_fluctuation_dof_basis": self.matchete_fluctuation_dof_basis,
                "interaction_wilson_line_terms_filtered_by_matching_targets": term_atom_requirements is not None,
                "interaction_wilson_line_pychete_color_algebra_simplified": simplify_pychete_color_algebra,
                "interaction_wilson_line_scalar_derivative_commutator_bilinears_exposed": (
                    expose_scalar_derivative_commutator_bilinears
                ),
                "interaction_wilson_line_act_open_derivatives": act_open_derivatives,
                "interaction_wilson_line_commutators_emitted": emit_covariant_derivative_commutators,
                "interaction_wilson_line_commutator_emit_passes": (
                    emit_covariant_derivative_commutator_passes
                    if emit_covariant_derivative_commutators
                    else None
                ),
                "interaction_wilson_line_commutator_emit_mode": (
                    covariant_derivative_commutator_mode
                    if emit_covariant_derivative_commutators
                    else None
                ),
                "interaction_wilson_line_commutators_expanded": expand_covariant_derivative_commutators,
                "interaction_wilson_line_max_derivative_order": max_wilson_derivative_order,
                "on_shell_reduced": False,
                "vakint_stage": VakintIntegralStage.EVALUATED.value,
                "named_supertrace_stage": selected_named_stage.value,
                "interaction_wilson_line_vakint_termwise_stage": True,
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
                "max_pole_order": max_pole_order,
                "uses_interaction_operator": True,
                "uses_wilson_line_expansion": True,
            },
        )

    def interaction_wilson_line_hybrid_matching_result(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
        simplify_pychete_color_algebra: bool = False,
        expose_scalar_derivative_commutator_bilinears: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return interaction-power traces with selected traces replaced by Wilson-line output."""

        selected_trace_names = _wilson_line_expansion_trace_names(expansion_indices_by_trace)
        interaction_remainder = self.interaction_power_type_matching_result(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=selected_trace_names,
            vakint_stage=vakint_stage,
            vakint_short_form=vakint_short_form,
            vakint_engine=vakint_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            named_supertrace_stage=named_supertrace_stage,
            named_supertrace_short_form=named_supertrace_short_form,
            named_supertrace_engine=named_supertrace_engine,
        )
        wilson_line_result = self.interaction_wilson_line_matching_result(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            vakint_stage=vakint_stage,
            vakint_short_form=vakint_short_form,
            vakint_engine=vakint_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            named_supertrace_stage=named_supertrace_stage,
            named_supertrace_short_form=named_supertrace_short_form,
            named_supertrace_engine=named_supertrace_engine,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            expose_scalar_derivative_commutator_bilinears=expose_scalar_derivative_commutator_bilinears,
            term_atom_requirements=term_atom_requirements,
        )
        result = _combine_interaction_expansion_hybrid_results(
            interaction_remainder,
            wilson_line_result,
            stage="interaction_wilson_line_hybrid_vakint_result",
            selected_trace_names=selected_trace_names,
            aggregate_expression_names=(
                "interaction_wilson_line_hybrid_vakint_integral_sum",
                f"interaction_wilson_line_hybrid_vakint_integral_sum[{VakintIntegralStage.from_user(vakint_stage).value}]",
            ),
            metadata_prefix="interaction_wilson_line",
            expansion_flag_name="uses_wilson_line_expansion",
            hybrid_flag_name="interaction_wilson_line_hybrid",
        )
        if VakintIntegralStage.from_user(vakint_stage) is VakintIntegralStage.EVALUATED:
            from .backends import vakint

            result = replace(
                result,
                supertraces={
                    **result.supertraces,
                    "interaction_wilson_line_hybrid_vakint_pole_part": vakint.pole_part(
                        result.off_shell_eft_lagrangian,
                        max_pole_order=max_pole_order,
                        epsilon=epsilon,
                    ),
                    "interaction_wilson_line_hybrid_vakint_finite_part": vakint.finite_part(
                        result.off_shell_eft_lagrangian,
                        epsilon=epsilon,
                    ),
                },
            )
        return result

    def interaction_wilson_line_hybrid_internal_matching_result(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        tensor_reduce_before_wilson_expand: bool = False,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
        simplify_pychete_color_algebra: bool = False,
        expose_scalar_derivative_commutator_bilinears: bool = False,
        internal_evaluation_mode: WilsonLineInternalEvaluationMode | str = WilsonLineInternalEvaluationMode.TERMWISE,
        collect_path_sums: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the hybrid Wilson-line/interaction result evaluated internally."""

        selected_trace_names = _wilson_line_expansion_trace_names(expansion_indices_by_trace)
        interaction_remainder = self.interaction_power_type_internal_matching_result(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=selected_trace_names,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
        )
        wilson_line_result = self.interaction_wilson_line_internal_matching_result(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            tensor_reduce_before_wilson_expand=tensor_reduce_before_wilson_expand,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            expose_scalar_derivative_commutator_bilinears=expose_scalar_derivative_commutator_bilinears,
            internal_evaluation_mode=internal_evaluation_mode,
            collect_path_sums=collect_path_sums,
            term_atom_requirements=term_atom_requirements,
        )
        result = _combine_interaction_expansion_hybrid_results(
            interaction_remainder,
            wilson_line_result,
            stage="interaction_wilson_line_hybrid_internal_integral_result",
            selected_trace_names=selected_trace_names,
            aggregate_expression_names=("interaction_wilson_line_hybrid_internal_integral_sum",),
            metadata_prefix="interaction_wilson_line",
            expansion_flag_name="uses_wilson_line_expansion",
            hybrid_flag_name="interaction_wilson_line_hybrid",
        )
        pole = (
            interaction_remainder.expression("interaction_power_type_internal_integral_pole_part")
            + wilson_line_result.expression("interaction_wilson_line_internal_integral_pole_part")
        )
        finite = (
            interaction_remainder.expression("interaction_power_type_internal_integral_finite_part")
            + wilson_line_result.expression("interaction_wilson_line_internal_integral_finite_part")
        )
        through_finite = (
            interaction_remainder.expression("interaction_power_type_internal_integral_through_finite_part")
            + wilson_line_result.expression("interaction_wilson_line_internal_integral_through_finite_part")
        )
        return replace(
            result,
            supertraces={
                **result.supertraces,
                "interaction_wilson_line_hybrid_internal_integral_pole_part": pole,
                "interaction_wilson_line_hybrid_internal_integral_finite_part": finite,
                "interaction_wilson_line_hybrid_internal_integral_through_finite_part": through_finite,
            },
        )

    def interaction_wilson_line_hybrid_internal_minimal_subtraction_result(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        tensor_reduce_before_wilson_expand: bool = False,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
        simplify_pychete_color_algebra: bool = False,
        expose_scalar_derivative_commutator_bilinears: bool = False,
        internal_evaluation_mode: WilsonLineInternalEvaluationMode | str = WilsonLineInternalEvaluationMode.TERMWISE,
        collect_path_sums: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the hybrid internal Wilson-line result after pole removal."""

        unrenormalized = self.interaction_wilson_line_hybrid_internal_matching_result(
            expansion_indices_by_trace,
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            tensor_reduce_before_wilson_expand=tensor_reduce_before_wilson_expand,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            expose_scalar_derivative_commutator_bilinears=expose_scalar_derivative_commutator_bilinears,
            internal_evaluation_mode=internal_evaluation_mode,
            collect_path_sums=collect_path_sums,
            term_atom_requirements=term_atom_requirements,
        )
        pole = unrenormalized.expression("interaction_wilson_line_hybrid_internal_integral_pole_part")
        finite = unrenormalized.expression("interaction_wilson_line_hybrid_internal_integral_finite_part")
        counterterm = -pole
        return replace(
            unrenormalized,
            off_shell_eft_lagrangian=finite,
            on_shell_eft_lagrangian=finite,
            supertraces={
                **unrenormalized.supertraces,
                "interaction_wilson_line_hybrid_internal_integral_ms_counterterm": counterterm,
            },
            metadata={
                **unrenormalized.metadata,
                "stage": "interaction_wilson_line_hybrid_internal_minimal_subtraction_result",
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
                "on_shell_reduced": False,
            },
        )

    def interaction_wilson_line_hybrid_minimal_subtraction_result(
        self,
        expansion_indices_by_trace: WilsonLineExpansionRequest,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        include_light_only: bool = False,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
        expand_covariant_derivative_commutators: bool = False,
        max_wilson_derivative_order: int = 4,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
        simplify_pychete_color_algebra: bool = False,
        expose_scalar_derivative_commutator_bilinears: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the finite native-vakint hybrid Wilson-line result."""

        from .backends import vakint

        selected_trace_names = _wilson_line_expansion_trace_names(expansion_indices_by_trace)
        interaction_remainder = self.interaction_power_type_minimal_subtraction_result(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=selected_trace_names,
            vakint_engine=vakint_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            named_supertrace_stage=named_supertrace_stage,
            named_supertrace_short_form=named_supertrace_short_form,
            named_supertrace_engine=named_supertrace_engine,
        )
        wilson_line_result = self.interaction_wilson_line_minimal_subtraction_result(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            include_light_only=include_light_only,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            vakint_engine=vakint_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            named_supertrace_stage=named_supertrace_stage,
            named_supertrace_short_form=named_supertrace_short_form,
            named_supertrace_engine=named_supertrace_engine,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
            expose_scalar_derivative_commutator_bilinears=expose_scalar_derivative_commutator_bilinears,
            term_atom_requirements=term_atom_requirements,
        )
        result = _combine_interaction_expansion_hybrid_results(
            interaction_remainder,
            wilson_line_result,
            stage="interaction_wilson_line_hybrid_minimal_subtraction_result",
            selected_trace_names=selected_trace_names,
            aggregate_expression_names=("interaction_wilson_line_hybrid_vakint_finite_part",),
            metadata_prefix="interaction_wilson_line",
            expansion_flag_name="uses_wilson_line_expansion",
            hybrid_flag_name="interaction_wilson_line_hybrid",
        )
        pole = vakint.pole_part(
            (
                interaction_remainder.expression("interaction_power_type_vakint_integral_sum[evaluated]")
                + wilson_line_result.expression("interaction_wilson_line_vakint_integral_sum[evaluated]")
            ).expand(),
            max_pole_order=max_pole_order,
            epsilon=epsilon,
        )
        return replace(
            result,
            supertraces={
                **result.supertraces,
                "interaction_wilson_line_hybrid_vakint_pole_part": pole,
                "interaction_wilson_line_hybrid_vakint_ms_counterterm": (-pole).expand(),
            },
            metadata={
                **result.metadata,
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
            },
        )

    def _interaction_bosonic_cde_trace_map(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        trace_names: Sequence[str] | None = None,
    ) -> dict[str, SupertraceBlockTrace]:
        if trace_names is not None:
            return {
                name: self.fluctuation_operator.interaction_category_trace(
                    _category_path_from_trace_name(name),
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                )
                for name in _selected_power_type_trace_names(
                    self.fluctuation_operator.modes,
                    max_trace_order=self.max_trace_order,
                    trace_names=trace_names,
                    include_light_only=False,
                )
            }
        return {
            trace.name: trace
            for trace in self.interaction_power_type_traces(
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
            )
        }

    def _interaction_bosonic_cde_plan_entries(
        self,
        expansion_request: BosonicCDEExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> tuple[BosonicCDEExpansionPlanEntry, ...]:
        if isinstance(expansion_request, BosonicCDEExpansionPlan):
            entries = expansion_request.entries
        else:
            entries = tuple(
                BosonicCDEExpansionPlanEntry(
                    trace_name=trace_name,
                    expansion_indices=_normalize_cde_expansion_indices(expansion_indices),
                    total_order=sum(len(indices) for indices in expansion_indices),
                    slot_orders=tuple(len(indices) for indices in expansion_indices),
                    label=trace_name,
                )
                for trace_name, expansion_indices in expansion_request.items()
            )
        _selected_power_type_trace_names(
            self.fluctuation_operator.modes,
            max_trace_order=self.max_trace_order,
            trace_names=tuple(entry.trace_name for entry in entries),
            include_light_only=False,
        )
        return entries

    def interaction_bosonic_cde_kernel_expression_map(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        prefix: str = "interaction_bosonic_cde_kernel",
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> dict[str, Expression]:
        """Return selected interaction traces after bosonic CDE propagator expansion.

        The default one-loop matching path remains unchanged. This method
        exposes the next CDE integration stage for tests and diagnostics by
        expanding only the requested trace names with explicitly supplied
        expansion-index sequences.
        """

        entries: dict[str, Expression] = {}
        for trace_name, terms in self.interaction_bosonic_cde_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        ).items():
            for index, term in enumerate(terms):
                entries[f"{prefix}[{trace_name},{index}]"] = term.kernel_expression(
                    loop_momentum_squared=loop_momentum_squared,
                )
        return entries

    def interaction_bosonic_cde_expansion_terms_by_trace(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> dict[str, tuple[BosonicCDETraceExpansionTerm, ...]]:
        """Return selected CDE-expanded interaction terms grouped by trace or plan label."""

        grouped: dict[str, tuple[BosonicCDETraceExpansionTerm, ...]] = {}
        plan_entries = self._interaction_bosonic_cde_plan_entries(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
        )
        traces = self._interaction_bosonic_cde_trace_map(
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            trace_names=tuple(entry.trace_name for entry in plan_entries),
        )
        for entry in plan_entries:
            terms = traces[entry.trace_name].bosonic_cde_expansion_terms(
                entry.expansion_indices,
                act_open_derivatives=act_open_derivatives,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            )
            grouped[entry.label] = _filter_cde_terms_by_projection_requirements(
                terms,
                term_atom_requirements,
            )
        return grouped

    def interaction_bosonic_cde_expansion_terms(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> tuple[BosonicCDETraceExpansionTerm, ...]:
        """Return selected CDE-expanded interaction terms in deterministic order."""

        grouped = self.interaction_bosonic_cde_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        )
        return tuple(term for terms in grouped.values() for term in terms)

    def interaction_bosonic_cde_vakint_integral_expression_map(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        prefix: str = "interaction_bosonic_cde_vakint_integral",
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> dict[str, Expression]:
        """Return selected CDE-expanded interaction traces as vakint topologies."""

        entries: dict[str, Expression] = {}
        for trace_name, terms in self.interaction_bosonic_cde_expansion_terms_by_trace(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        ).items():
            for index, term in enumerate(terms):
                entries[f"{prefix}[{trace_name},{index}]"] = term.vakint_integral_expression()
        return entries

    def interaction_bosonic_cde_vakint_integral_sum(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        short_form: bool | None = None,
        engine: Any | None = None,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> Expression:
        """Return the summed selected CDE-expanded interaction topologies."""

        terms = self.interaction_bosonic_cde_expansion_terms(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        )
        return _cde_vakint_integral_terms_at_stage(
            tuple(term.vakint_integral_expression() for term in terms),
            theory=self.theory,
            stage=VakintIntegralStage.from_user(stage),
            short_form=short_form,
            engine=engine,
        )

    def interaction_bosonic_cde_internal_integral_sum(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> Expression:
        """Evaluate selected CDE-expanded interaction integrals with pychete."""

        from .backends import vakint, vacuum_integrals

        terms = self.interaction_bosonic_cde_expansion_terms(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        )
        evaluated_terms: list[Expression] = []
        with progress(
            f"evaluating {len(terms)} CDE-expanded scalar vacuum integrals termwise",
            logger=_LOGGER,
        ):
            for term in terms:
                raw = term.vakint_integral_expression()
                if tensor_reduce:
                    raw = vakint.tensor_reduce(raw, engine=tensor_reduce_engine)
                    raw = vakint.decode_pychete_namespace(self.theory, raw)
                evaluated_terms.append(
                    vacuum_integrals.evaluate_one_loop_vakint_expression(
                        raw,
                        epsilon=epsilon,
                        mu_r_squared=mu_r_squared,
                        combine_terms=False,
                    )
                )
        evaluated = sum_expr(evaluated_terms).expand()
        return evaluated.together() if combine_terms else evaluated

    def operator_propagator_denominator_chain(
        self,
        trace: SupertraceBlockTrace | str,
        *,
        loop_momentum_squared: Expression | None = None,
        include_light: bool = True,
        require_registered_mass: bool = True,
    ) -> tuple[tuple[Expression, ...], ...]:
        """Return inverse-operator denominators aligned with one trace path."""

        selected_trace = self._trace(trace)
        chain: list[tuple[Expression, ...]] = []
        for block in selected_trace.blocks:
            denominators: list[Expression] = []
            for mode in block.rows:
                if not include_light and mode.is_light:
                    continue
                denominator = self.fluctuation_operator.propagator_denominator_for_mode(
                    mode.field,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                )
                if denominator is None:
                    raise ValueError(
                        "Could not recognize a free propagator denominator for "
                        f"{canonical_string(mode.field)} in trace {selected_trace.name!r}"
                    )
                denominators.append(denominator)
            chain.append(tuple(denominators))
        return tuple(chain)

    def operator_propagator_mass_squared_chain(
        self,
        trace: SupertraceBlockTrace | str,
        *,
        loop_momentum_squared: Expression | None = None,
        include_light: bool = True,
        require_registered_mass: bool = True,
    ) -> tuple[tuple[Expression, ...], ...]:
        """Return mass-squared slots extracted from inverse-operator denominators."""

        return tuple(
            tuple(_propagator_denominator_mass_squared(denominator) for denominator in slot)
            for slot in self.operator_propagator_denominator_chain(
                trace,
                loop_momentum_squared=loop_momentum_squared,
                include_light=include_light,
                require_registered_mass=require_registered_mass,
            )
        )

    def operator_propagator_expression(
        self,
        trace: SupertraceBlockTrace | str,
        *,
        loop_momentum_squared: Expression | None = None,
        include_light: bool = True,
        require_registered_mass: bool = True,
    ) -> Expression:
        """Return one trace kernel decorated with inverse-operator denominators."""

        selected_trace = self._trace(trace)
        chain = self.operator_propagator_denominator_chain(
            selected_trace,
            loop_momentum_squared=loop_momentum_squared,
            include_light=include_light,
            require_registered_mass=require_registered_mass,
        )
        return s.SupertraceKernel(selected_trace.expression, list_expr(*(list_expr(*slot) for slot in chain)))

    def supertrace_operator_propagator_expression_map(
        self,
        *,
        prefix: str = "supertrace_operator_propagator_kernel",
        loop_momentum_squared: Expression | None = None,
        include_light: bool = True,
        require_registered_mass: bool = True,
        skip_unrecognized: bool = True,
    ) -> dict[str, Expression]:
        """Return generated traces decorated with inverse-operator denominators."""

        entries: dict[str, Expression] = {}
        for trace in self.block_traces:
            try:
                entries[f"{prefix}[{trace.name}]"] = self.operator_propagator_expression(
                    trace,
                    loop_momentum_squared=loop_momentum_squared,
                    include_light=include_light,
                    require_registered_mass=require_registered_mass,
                )
            except ValueError:
                if not skip_unrecognized:
                    raise
        return entries

    def operator_vakint_integral_expression(
        self,
        trace: SupertraceBlockTrace | str,
        *,
        include_light: bool = True,
        require_registered_mass: bool = True,
    ) -> Expression:
        """Lower one trace to vakint using inverse-operator mass slots."""

        from .backends import vakint

        selected_trace = self._trace(trace)
        return vakint.one_loop_vacuum_integral(
            selected_trace.expression,
            _flatten_expression_slots(
                self.operator_propagator_mass_squared_chain(
                    selected_trace,
                    include_light=include_light,
                    require_registered_mass=require_registered_mass,
                )
            ),
        )

    def operator_vakint_integral_expression_map(
        self,
        *,
        prefix: str = "operator_vakint_integral",
        include_light: bool = True,
        require_registered_mass: bool = True,
        skip_unrecognized: bool = True,
    ) -> dict[str, Expression]:
        """Return vakint topologies built from inverse-operator denominators."""

        entries: dict[str, Expression] = {}
        for trace in self.block_traces:
            try:
                entries[f"{prefix}[{trace.name}]"] = self.operator_vakint_integral_expression(
                    trace,
                    include_light=include_light,
                    require_registered_mass=require_registered_mass,
                )
            except ValueError:
                if not skip_unrecognized:
                    raise
        return entries

    def power_type_traces(self) -> tuple[SupertraceBlockTrace, ...]:
        """Return cyclically unique traces used for power-type contributions."""

        return _cyclically_unique_traces(self.block_traces)

    def interaction_power_type_traces(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> tuple[SupertraceBlockTrace, ...]:
        """Return cyclically unique interaction-only traces."""

        return _cyclically_unique_traces(
            self.interaction_block_traces(
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
            )
        )

    def power_type_contributions(
        self,
        *,
        heavy_field_dimension: bool = False,
    ) -> tuple[PowerTypeSupertraceContribution, ...]:
        """Return EFT-truncated power-type contribution objects."""

        return tuple(
            PowerTypeSupertraceContribution(
                theory=self.theory,
                trace=trace,
                eft_order=self.eft_order,
                heavy_field_dimension=heavy_field_dimension,
            )
            for trace in self.power_type_traces()
        )

    def interaction_power_type_contributions(
        self,
        *,
        heavy_field_dimension: bool = False,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
    ) -> tuple[PowerTypeSupertraceContribution, ...]:
        """Return EFT-truncated interaction-power contribution objects."""

        excluded = set(exclude_trace_names)
        return tuple(
            PowerTypeSupertraceContribution(
                theory=self.theory,
                trace=trace,
                eft_order=self.eft_order,
                heavy_field_dimension=heavy_field_dimension,
            )
            for trace in self.interaction_power_type_traces(
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
            )
            if trace.name not in excluded
        )

    def power_type_expression_map(self, *, prefix: str = "power_type_supertrace") -> dict[str, Expression]:
        """Return deterministic expressions for power-type contributions."""

        entries: dict[str, Expression] = {}
        for contribution in self.power_type_contributions():
            entries.update(contribution.to_expression_map(prefix=prefix))
        return entries

    def interaction_power_type_expression_map(
        self,
        *,
        prefix: str = "interaction_power_type_supertrace",
        heavy_field_dimension: bool = False,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
    ) -> dict[str, Expression]:
        """Return deterministic expressions for interaction-power contributions."""

        entries: dict[str, Expression] = {}
        for contribution in self.interaction_power_type_contributions(
            heavy_field_dimension=heavy_field_dimension,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=exclude_trace_names,
        ):
            entries.update(contribution.to_expression_map(prefix=prefix))
        return entries

    def power_type_eft_lagrangian(self, *, heavy_field_dimension: bool = False) -> Expression:
        """Return the summed EFT-truncated power-type off-shell Lagrangian contribution."""

        return sum_expr(
            contribution.eft_numerator_expression
            for contribution in self.power_type_contributions(heavy_field_dimension=heavy_field_dimension)
        ).expand()

    def interaction_power_type_eft_lagrangian(
        self,
        *,
        heavy_field_dimension: bool = False,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
    ) -> Expression:
        """Return the summed interaction-power off-shell contribution."""

        return sum_expr(
            contribution.eft_numerator_expression
            for contribution in self.interaction_power_type_contributions(
                heavy_field_dimension=heavy_field_dimension,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                exclude_trace_names=exclude_trace_names,
            )
        ).expand()

    def power_type_vakint_integral_sum(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        short_form: bool | None = None,
        engine: Any | None = None,
    ) -> Expression:
        """Return the summed power-type contribution at a native vakint stage."""

        raw = sum_expr(
            contribution.vakint_integral_expression(include_light=include_light)
            for contribution in self.power_type_contributions(heavy_field_dimension=heavy_field_dimension)
        ).expand()
        selected = VakintIntegralStage.from_user(stage)
        if selected is VakintIntegralStage.RAW:
            return raw
        from .backends import vakint

        if selected is VakintIntegralStage.CANONICAL:
            return vakint.decode_pychete_namespace(
                self.theory,
                vakint.to_canonical(raw, short_form=short_form, engine=engine),
            )
        if selected is VakintIntegralStage.TENSOR_REDUCED:
            return vakint.decode_pychete_namespace(self.theory, vakint.tensor_reduce(raw, engine=engine))
        return vakint.decode_pychete_namespace(self.theory, vakint.evaluate(raw, engine=engine))

    def power_type_internal_integral_sum(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
    ) -> Expression:
        """Evaluate power-type vacuum integrals with pychete.

        Native vakint remains responsible for optional topology-independent
        tensor reduction. The scalar one-loop topology evaluation, including
        single-scale, massless, and mixed-mass analytic cases, is then
        performed by pychete's internal backend. Set
        ``combine_terms`` to route the evaluated expression through
        Symbolica's native ``together()`` common-denominator pass.
        """

        _LOGGER.info("assembling power-type vakint integral sum for %s", self.theory.name)
        raw = self.power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
        )
        if tensor_reduce:
            from .backends import vakint

            with progress("tensor-reducing power-type one-loop integrals", logger=_LOGGER):
                raw = vakint.tensor_reduce(raw, engine=tensor_reduce_engine)
            raw = vakint.decode_pychete_namespace(self.theory, raw)
        from .backends import vacuum_integrals

        with progress("evaluating power-type scalar vacuum integrals", logger=_LOGGER):
            return vacuum_integrals.evaluate_one_loop_vakint_expression(
                raw,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
                combine_terms=combine_terms,
            )

    def power_type_internal_matching_result(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
    ) -> MatchingResult:
        """Return the power-type result evaluated by pychete's internal integral backend."""

        from .backends import vakint

        contributions = self.power_type_contributions(heavy_field_dimension=heavy_field_dimension)
        numerator_sum = sum_expr(contribution.eft_numerator_expression for contribution in contributions).expand()
        raw_vakint_sum = self.power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
        )
        evaluated = self.power_type_internal_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
        )
        pole = vakint.pole_part(evaluated, max_pole_order=max_pole_order, epsilon=epsilon)
        finite = vakint.finite_part(evaluated, epsilon=epsilon)
        through_finite = vakint.through_finite_part(
            evaluated,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
        )
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=evaluated,
            on_shell_eft_lagrangian=evaluated,
            fluctuation_operators=self.fluctuation_operator.to_expression_map(),
            supertraces={
                **_named_internal_supertraces(
                    contributions,
                    include_light=include_light,
                    tensor_reduce=tensor_reduce,
                    tensor_reduce_engine=tensor_reduce_engine,
                    epsilon=epsilon,
                    mu_r_squared=mu_r_squared,
                    combine_terms=combine_terms,
                ),
                **self.power_type_expression_map(prefix="power_type_supertrace"),
                "power_type_eft_lagrangian": numerator_sum,
                "power_type_vakint_integral_sum": raw_vakint_sum,
                "power_type_internal_integral_sum": evaluated,
                "power_type_internal_integral_pole_part": pole,
                "power_type_internal_integral_finite_part": finite,
                "power_type_internal_integral_through_finite_part": through_finite,
            },
            metadata={
                "stage": "power_type_internal_integral_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                "power_type_contribution_count": self.power_type_contribution_count,
                "on_shell_reduced": False,
                "integral_backend": "pychete_internal",
                "tensor_reduce": tensor_reduce,
                "combine_terms": combine_terms,
                "max_pole_order": max_pole_order,
            },
        )

    def power_type_internal_minimal_subtraction_result(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
    ) -> MatchingResult:
        """Return the internal-backend finite power-type result after pole subtraction."""

        unrenormalized = self.power_type_internal_matching_result(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
        )
        pole = unrenormalized.expression("power_type_internal_integral_pole_part")
        finite = unrenormalized.expression("power_type_internal_integral_finite_part")
        counterterm = (-pole).expand()
        finite_named_supertraces = _finite_named_supertraces(
            unrenormalized.supertraces,
            (
                contribution.name
                for contribution in self.power_type_contributions(
                    heavy_field_dimension=heavy_field_dimension,
                )
            ),
            epsilon=epsilon,
        )
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=finite,
            on_shell_eft_lagrangian=finite,
            matching_conditions=unrenormalized.matching_conditions,
            fluctuation_operators=unrenormalized.fluctuation_operators,
            supertraces={
                **unrenormalized.supertraces,
                **finite_named_supertraces,
                "power_type_internal_integral_ms_counterterm": counterterm,
            },
            metadata={
                **unrenormalized.metadata,
                "stage": "power_type_internal_minimal_subtraction_result",
                "complete": False,
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
                "on_shell_reduced": False,
            },
        )

    def interaction_power_type_vakint_integral_sum(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
        stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        short_form: bool | None = None,
        engine: Any | None = None,
    ) -> Expression:
        """Return the summed interaction-power contribution at a vakint stage."""

        raw = sum_expr(
            contribution.vakint_integral_expression(include_light=include_light)
            for contribution in self.interaction_power_type_contributions(
                heavy_field_dimension=heavy_field_dimension,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                exclude_trace_names=exclude_trace_names,
            )
        ).expand()
        selected = VakintIntegralStage.from_user(stage)
        if selected is VakintIntegralStage.RAW:
            return raw
        from .backends import vakint

        if selected is VakintIntegralStage.CANONICAL:
            with progress("canonicalizing interaction-power vakint integrals", logger=_LOGGER):
                return vakint.decode_pychete_namespace(
                    self.theory,
                    vakint.to_canonical(raw, short_form=short_form, engine=engine),
                )
        if selected is VakintIntegralStage.TENSOR_REDUCED:
            with progress("tensor-reducing interaction-power vakint integrals", logger=_LOGGER):
                return vakint.decode_pychete_namespace(self.theory, vakint.tensor_reduce(raw, engine=engine))
        with progress("evaluating interaction-power vakint integrals", logger=_LOGGER):
            return vakint.decode_pychete_namespace(self.theory, vakint.evaluate(raw, engine=engine))

    def interaction_power_type_internal_integral_sum(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
    ) -> Expression:
        """Evaluate interaction-power vacuum integrals with pychete.

        This is the internal analytic counterpart to
        ``interaction_power_type_vakint_integral_sum(stage="evaluated")`` for
        one-loop scalar topologies after optional vakint tensor reduction. Set
        ``combine_terms`` to route the evaluated expression through Symbolica's
        native ``together()`` common-denominator pass.
        """

        _LOGGER.info("assembling interaction-power vakint integral sum for %s", self.theory.name)
        raw = self.interaction_power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=exclude_trace_names,
        )
        if tensor_reduce:
            from .backends import vakint

            with progress("tensor-reducing interaction-power one-loop integrals", logger=_LOGGER):
                raw = vakint.tensor_reduce(raw, engine=tensor_reduce_engine)
            raw = vakint.decode_pychete_namespace(self.theory, raw)
        from .backends import vacuum_integrals

        with progress("evaluating interaction-power scalar vacuum integrals", logger=_LOGGER):
            return vacuum_integrals.evaluate_one_loop_vakint_expression(
                raw,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
                combine_terms=combine_terms,
            )

    def interaction_power_type_vakint_epsilon_coefficient(
        self,
        power: int,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
        stage: VakintIntegralStage | str = VakintIntegralStage.EVALUATED,
        short_form: bool | None = None,
        engine: Any | None = None,
        epsilon: Expression | None = None,
    ) -> Expression:
        """Return one epsilon coefficient of the interaction-power vakint aggregate."""

        from .backends import vakint

        expr = self.interaction_power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=exclude_trace_names,
            stage=stage,
            short_form=short_form,
            engine=engine,
        )
        return vakint.epsilon_coefficient(expr, power, epsilon=epsilon)

    def interaction_power_type_vakint_pole_part(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
        stage: VakintIntegralStage | str = VakintIntegralStage.EVALUATED,
        short_form: bool | None = None,
        engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
    ) -> Expression:
        """Return the negative-power epsilon poles of the interaction-power aggregate."""

        from .backends import vakint

        expr = self.interaction_power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=exclude_trace_names,
            stage=stage,
            short_form=short_form,
            engine=engine,
        )
        return vakint.pole_part(expr, max_pole_order=max_pole_order, epsilon=epsilon)

    def interaction_power_type_vakint_finite_part(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
        stage: VakintIntegralStage | str = VakintIntegralStage.EVALUATED,
        short_form: bool | None = None,
        engine: Any | None = None,
        epsilon: Expression | None = None,
    ) -> Expression:
        """Return the epsilon^0 coefficient of the interaction-power vakint aggregate."""

        from .backends import vakint

        expr = self.interaction_power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=exclude_trace_names,
            stage=stage,
            short_form=short_form,
            engine=engine,
        )
        return vakint.finite_part(expr, epsilon=epsilon)

    def interaction_bosonic_cde_matching_result(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the selected CDE-expanded interaction one-loop result."""

        selected_vakint_stage = VakintIntegralStage.from_user(vakint_stage)
        selected_named_stage = VakintIntegralStage.from_user(named_supertrace_stage)
        vakint_sum = self.interaction_bosonic_cde_vakint_integral_sum(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            stage=selected_vakint_stage,
            short_form=vakint_short_form,
            engine=vakint_engine,
            term_atom_requirements=term_atom_requirements,
        )
        raw_named_integrals = self.interaction_bosonic_cde_vakint_integral_expression_map(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        )
        named_integrals = {
            name: _vakint_expression_at_stage(
                expr,
                theory=self.theory,
                stage=selected_named_stage,
                short_form=named_supertrace_short_form,
                engine=named_supertrace_engine,
            )
            for name, expr in raw_named_integrals.items()
        }
        terms = self.interaction_bosonic_cde_expansion_terms(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        )
        supertraces = {
            **self.interaction_bosonic_cde_kernel_expression_map(
                expansion_indices_by_trace,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                act_open_derivatives=act_open_derivatives,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                term_atom_requirements=term_atom_requirements,
            ),
            **named_integrals,
            "interaction_bosonic_cde_vakint_integral_sum": vakint_sum,
            f"interaction_bosonic_cde_vakint_integral_sum[{selected_vakint_stage.value}]": vakint_sum,
        }
        if selected_vakint_stage is VakintIntegralStage.EVALUATED:
            from .backends import vakint

            supertraces["interaction_bosonic_cde_vakint_pole_part"] = vakint.pole_part(
                vakint_sum,
                max_pole_order=max_pole_order,
                epsilon=epsilon,
            )
            supertraces["interaction_bosonic_cde_vakint_finite_part"] = vakint.finite_part(vakint_sum, epsilon=epsilon)
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=vakint_sum,
            on_shell_eft_lagrangian=vakint_sum,
            fluctuation_operators={
                **self.fluctuation_operator.to_expression_map(),
                **self.fluctuation_operator.interaction_expression_map(),
            },
            supertraces=supertraces,
            metadata={
                "stage": "interaction_bosonic_cde_vakint_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                **_cde_expansion_request_metadata(expansion_indices_by_trace),
                "interaction_bosonic_cde_term_count": len(terms),
                "interaction_bosonic_cde_act_open_derivatives": act_open_derivatives,
                "interaction_bosonic_cde_commutators_emitted": emit_covariant_derivative_commutators,
                "interaction_bosonic_cde_commutator_emit_passes": (
                    emit_covariant_derivative_commutator_passes
                    if emit_covariant_derivative_commutators
                    else 0
                ),
                "interaction_bosonic_cde_commutators_expanded": expand_covariant_derivative_commutators,
                "on_shell_reduced": False,
                "vakint_stage": selected_vakint_stage.value,
                "named_supertrace_stage": selected_named_stage.value,
                "interaction_bosonic_cde_vakint_termwise_stage": selected_vakint_stage is not VakintIntegralStage.RAW,
                "uses_interaction_operator": True,
                "uses_bosonic_cde_expansion": True,
            },
        )

    def interaction_bosonic_cde_internal_matching_result(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the CDE-expanded interaction result evaluated internally."""

        from .backends import vakint

        terms = self.interaction_bosonic_cde_expansion_terms(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        )
        raw_vakint_sum = self.interaction_bosonic_cde_vakint_integral_sum(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        )
        evaluated = self.interaction_bosonic_cde_internal_integral_sum(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
            term_atom_requirements=term_atom_requirements,
        )
        pole = vakint.pole_part(evaluated, max_pole_order=max_pole_order, epsilon=epsilon)
        finite = vakint.finite_part(evaluated, epsilon=epsilon)
        through_finite = vakint.through_finite_part(
            evaluated,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
        )
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=evaluated,
            on_shell_eft_lagrangian=evaluated,
            fluctuation_operators={
                **self.fluctuation_operator.to_expression_map(),
                **self.fluctuation_operator.interaction_expression_map(),
            },
            supertraces={
                **self.interaction_bosonic_cde_kernel_expression_map(
                    expansion_indices_by_trace,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                    act_open_derivatives=act_open_derivatives,
                    emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                    emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                    expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                    term_atom_requirements=term_atom_requirements,
                ),
                **self.interaction_bosonic_cde_vakint_integral_expression_map(
                    expansion_indices_by_trace,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                    act_open_derivatives=act_open_derivatives,
                    emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                    emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                    expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                    term_atom_requirements=term_atom_requirements,
                ),
                "interaction_bosonic_cde_vakint_integral_sum": raw_vakint_sum,
                "interaction_bosonic_cde_internal_integral_sum": evaluated,
                "interaction_bosonic_cde_internal_integral_pole_part": pole,
                "interaction_bosonic_cde_internal_integral_finite_part": finite,
                "interaction_bosonic_cde_internal_integral_through_finite_part": through_finite,
            },
            metadata={
                "stage": "interaction_bosonic_cde_internal_integral_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                **_cde_expansion_request_metadata(expansion_indices_by_trace),
                "interaction_bosonic_cde_term_count": len(terms),
                "interaction_bosonic_cde_act_open_derivatives": act_open_derivatives,
                "interaction_bosonic_cde_commutators_emitted": emit_covariant_derivative_commutators,
                "interaction_bosonic_cde_commutator_emit_passes": (
                    emit_covariant_derivative_commutator_passes
                    if emit_covariant_derivative_commutators
                    else 0
                ),
                "interaction_bosonic_cde_commutators_expanded": expand_covariant_derivative_commutators,
                "on_shell_reduced": False,
                "integral_backend": "pychete_internal",
                "tensor_reduce": tensor_reduce,
                "interaction_bosonic_cde_internal_termwise_evaluation": True,
                "combine_terms": combine_terms,
                "uses_interaction_operator": True,
                "uses_bosonic_cde_expansion": True,
                "max_pole_order": max_pole_order,
            },
        )

    def interaction_bosonic_cde_internal_minimal_subtraction_result(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the internal CDE result after minimal-subtraction pole removal."""

        unrenormalized = self.interaction_bosonic_cde_internal_matching_result(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
            term_atom_requirements=term_atom_requirements,
        )
        pole = unrenormalized.expression("interaction_bosonic_cde_internal_integral_pole_part")
        finite = unrenormalized.expression("interaction_bosonic_cde_internal_integral_finite_part")
        counterterm = (-pole).expand()
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=finite,
            on_shell_eft_lagrangian=finite,
            matching_conditions=unrenormalized.matching_conditions,
            fluctuation_operators=unrenormalized.fluctuation_operators,
            supertraces={
                **unrenormalized.supertraces,
                "interaction_bosonic_cde_internal_integral_ms_counterterm": counterterm,
            },
            metadata={
                **unrenormalized.metadata,
                "stage": "interaction_bosonic_cde_internal_minimal_subtraction_result",
                "complete": False,
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
                "on_shell_reduced": False,
            },
        )

    def interaction_bosonic_cde_minimal_subtraction_result(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the finite native-vakint CDE result after pole subtraction."""

        from .backends import vakint

        evaluated = self.interaction_bosonic_cde_vakint_integral_sum(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            stage=VakintIntegralStage.EVALUATED,
            engine=vakint_engine,
            term_atom_requirements=term_atom_requirements,
        )
        selected_named_stage = VakintIntegralStage.from_user(named_supertrace_stage)
        pole = vakint.pole_part(evaluated, max_pole_order=max_pole_order, epsilon=epsilon)
        finite = vakint.finite_part(evaluated, epsilon=epsilon)
        counterterm = (-pole).expand()
        terms = self.interaction_bosonic_cde_expansion_terms(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        )
        raw_named_integrals = self.interaction_bosonic_cde_vakint_integral_expression_map(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            term_atom_requirements=term_atom_requirements,
        )
        named_integrals = {
            name: _vakint_expression_at_stage(
                expr,
                theory=self.theory,
                stage=selected_named_stage,
                short_form=named_supertrace_short_form,
                engine=named_supertrace_engine,
            )
            for name, expr in raw_named_integrals.items()
        }
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=finite,
            on_shell_eft_lagrangian=finite,
            fluctuation_operators={
                **self.fluctuation_operator.to_expression_map(),
                **self.fluctuation_operator.interaction_expression_map(),
            },
            supertraces={
                **self.interaction_bosonic_cde_kernel_expression_map(
                    expansion_indices_by_trace,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                    act_open_derivatives=act_open_derivatives,
                    emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                    emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                    expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                    term_atom_requirements=term_atom_requirements,
                ),
                **named_integrals,
                "interaction_bosonic_cde_vakint_integral_sum": evaluated,
                "interaction_bosonic_cde_vakint_integral_sum[evaluated]": evaluated,
                "interaction_bosonic_cde_vakint_pole_part": pole,
                "interaction_bosonic_cde_vakint_ms_counterterm": counterterm,
                "interaction_bosonic_cde_vakint_finite_part": finite,
            },
            metadata={
                "stage": "interaction_bosonic_cde_minimal_subtraction_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                **_cde_expansion_request_metadata(expansion_indices_by_trace),
                "interaction_bosonic_cde_term_count": len(terms),
                "interaction_bosonic_cde_act_open_derivatives": act_open_derivatives,
                "interaction_bosonic_cde_commutators_emitted": emit_covariant_derivative_commutators,
                "interaction_bosonic_cde_commutator_emit_passes": (
                    emit_covariant_derivative_commutator_passes
                    if emit_covariant_derivative_commutators
                    else 0
                ),
                "interaction_bosonic_cde_commutators_expanded": expand_covariant_derivative_commutators,
                "on_shell_reduced": False,
                "vakint_stage": VakintIntegralStage.EVALUATED.value,
                "named_supertrace_stage": selected_named_stage.value,
                "interaction_bosonic_cde_vakint_termwise_stage": True,
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
                "max_pole_order": max_pole_order,
                "uses_interaction_operator": True,
                "uses_bosonic_cde_expansion": True,
            },
        )

    def interaction_bosonic_cde_hybrid_matching_result(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return interaction-power traces with selected traces replaced by CDE output."""

        selected_trace_names = _cde_expansion_trace_names(expansion_indices_by_trace)
        interaction_remainder = self.interaction_power_type_matching_result(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=selected_trace_names,
            vakint_stage=vakint_stage,
            vakint_short_form=vakint_short_form,
            vakint_engine=vakint_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            named_supertrace_stage=named_supertrace_stage,
            named_supertrace_short_form=named_supertrace_short_form,
            named_supertrace_engine=named_supertrace_engine,
        )
        cde_result = self.interaction_bosonic_cde_matching_result(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            vakint_stage=vakint_stage,
            vakint_short_form=vakint_short_form,
            vakint_engine=vakint_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            named_supertrace_stage=named_supertrace_stage,
            named_supertrace_short_form=named_supertrace_short_form,
            named_supertrace_engine=named_supertrace_engine,
            term_atom_requirements=term_atom_requirements,
        )
        result = _combine_bosonic_cde_hybrid_results(
            interaction_remainder,
            cde_result,
            stage="interaction_bosonic_cde_hybrid_vakint_result",
            selected_trace_names=selected_trace_names,
            aggregate_expression_names=(
                "interaction_bosonic_cde_hybrid_vakint_integral_sum",
                f"interaction_bosonic_cde_hybrid_vakint_integral_sum[{VakintIntegralStage.from_user(vakint_stage).value}]",
            ),
        )
        if VakintIntegralStage.from_user(vakint_stage) is VakintIntegralStage.EVALUATED:
            from .backends import vakint

            result = replace(
                result,
                supertraces={
                    **result.supertraces,
                    "interaction_bosonic_cde_hybrid_vakint_pole_part": vakint.pole_part(
                        result.off_shell_eft_lagrangian,
                        max_pole_order=max_pole_order,
                        epsilon=epsilon,
                    ),
                    "interaction_bosonic_cde_hybrid_vakint_finite_part": vakint.finite_part(
                        result.off_shell_eft_lagrangian,
                        epsilon=epsilon,
                    ),
                },
            )
        return result

    def interaction_bosonic_cde_hybrid_internal_matching_result(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the hybrid CDE/interaction result evaluated internally."""

        from .backends import vakint

        selected_trace_names = _cde_expansion_trace_names(expansion_indices_by_trace)
        interaction_remainder = self.interaction_power_type_internal_matching_result(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=selected_trace_names,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
        )
        cde_result = self.interaction_bosonic_cde_internal_matching_result(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
            term_atom_requirements=term_atom_requirements,
        )
        result = _combine_bosonic_cde_hybrid_results(
            interaction_remainder,
            cde_result,
            stage="interaction_bosonic_cde_hybrid_internal_integral_result",
            selected_trace_names=selected_trace_names,
            aggregate_expression_names=("interaction_bosonic_cde_hybrid_internal_integral_sum",),
        )
        return replace(
            result,
            supertraces={
                **result.supertraces,
                "interaction_bosonic_cde_hybrid_internal_integral_pole_part": vakint.pole_part(
                    result.off_shell_eft_lagrangian,
                    max_pole_order=max_pole_order,
                    epsilon=epsilon,
                ),
                "interaction_bosonic_cde_hybrid_internal_integral_finite_part": vakint.finite_part(
                    result.off_shell_eft_lagrangian,
                    epsilon=epsilon,
                ),
            },
        )

    def interaction_bosonic_cde_hybrid_internal_minimal_subtraction_result(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the hybrid internal result after minimal-subtraction pole removal."""

        unrenormalized = self.interaction_bosonic_cde_hybrid_internal_matching_result(
            expansion_indices_by_trace,
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
            term_atom_requirements=term_atom_requirements,
        )
        pole = unrenormalized.expression("interaction_bosonic_cde_hybrid_internal_integral_pole_part")
        finite = unrenormalized.expression("interaction_bosonic_cde_hybrid_internal_integral_finite_part")
        counterterm = (-pole).expand()
        return replace(
            unrenormalized,
            off_shell_eft_lagrangian=finite,
            on_shell_eft_lagrangian=finite,
            supertraces={
                **unrenormalized.supertraces,
                "interaction_bosonic_cde_hybrid_internal_integral_ms_counterterm": counterterm,
            },
            metadata={
                **unrenormalized.metadata,
                "stage": "interaction_bosonic_cde_hybrid_internal_minimal_subtraction_result",
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
                "on_shell_reduced": False,
            },
        )

    def interaction_bosonic_cde_hybrid_minimal_subtraction_result(
        self,
        expansion_indices_by_trace: BosonicCDEExpansionRequest,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        act_open_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
        term_atom_requirements: ProjectionAtomRequirementGroups | None = None,
    ) -> MatchingResult:
        """Return the finite native-vakint hybrid result after pole subtraction."""

        from .backends import vakint

        selected_trace_names = _cde_expansion_trace_names(expansion_indices_by_trace)
        interaction_remainder = self.interaction_power_type_minimal_subtraction_result(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=selected_trace_names,
            vakint_engine=vakint_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            named_supertrace_stage=named_supertrace_stage,
            named_supertrace_short_form=named_supertrace_short_form,
            named_supertrace_engine=named_supertrace_engine,
        )
        cde_result = self.interaction_bosonic_cde_minimal_subtraction_result(
            expansion_indices_by_trace,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            vakint_engine=vakint_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            named_supertrace_stage=named_supertrace_stage,
            named_supertrace_short_form=named_supertrace_short_form,
            named_supertrace_engine=named_supertrace_engine,
            term_atom_requirements=term_atom_requirements,
        )
        result = _combine_bosonic_cde_hybrid_results(
            interaction_remainder,
            cde_result,
            stage="interaction_bosonic_cde_hybrid_minimal_subtraction_result",
            selected_trace_names=selected_trace_names,
            aggregate_expression_names=("interaction_bosonic_cde_hybrid_vakint_finite_part",),
        )
        pole = vakint.pole_part(
            (
                interaction_remainder.expression("interaction_power_type_vakint_integral_sum[evaluated]")
                + cde_result.expression("interaction_bosonic_cde_vakint_integral_sum[evaluated]")
            ).expand(),
            max_pole_order=max_pole_order,
            epsilon=epsilon,
        )
        return replace(
            result,
            supertraces={
                **result.supertraces,
                "interaction_bosonic_cde_hybrid_vakint_pole_part": pole,
                "interaction_bosonic_cde_hybrid_vakint_ms_counterterm": (-pole).expand(),
            },
            metadata={
                **result.metadata,
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
            },
        )

    def interaction_power_type_matching_result(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
    ) -> MatchingResult:
        """Return the current interaction-power one-loop preview result."""

        excluded_trace_names = tuple(exclude_trace_names)
        contributions = self.interaction_power_type_contributions(
            heavy_field_dimension=heavy_field_dimension,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=excluded_trace_names,
        )
        numerator_sum = sum_expr(contribution.eft_numerator_expression for contribution in contributions).expand()
        selected_vakint_stage = VakintIntegralStage.from_user(vakint_stage)
        vakint_sum = self.interaction_power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=excluded_trace_names,
            stage=selected_vakint_stage,
            short_form=vakint_short_form,
            engine=vakint_engine,
        )
        selected_named_stage = VakintIntegralStage.from_user(named_supertrace_stage)
        supertraces = {
            **_named_vakint_supertraces(
                contributions,
                include_light=include_light,
                stage=selected_named_stage,
                short_form=named_supertrace_short_form,
                engine=named_supertrace_engine,
            ),
            **self.interaction_power_type_expression_map(
                prefix="interaction_power_type_supertrace",
                heavy_field_dimension=heavy_field_dimension,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                exclude_trace_names=excluded_trace_names,
            ),
            "interaction_power_type_eft_lagrangian": numerator_sum,
            "interaction_power_type_vakint_integral_sum": vakint_sum,
            f"interaction_power_type_vakint_integral_sum[{selected_vakint_stage.value}]": vakint_sum,
        }
        if selected_vakint_stage is VakintIntegralStage.EVALUATED:
            from .backends import vakint

            supertraces["interaction_power_type_vakint_pole_part"] = vakint.pole_part(
                vakint_sum,
                max_pole_order=max_pole_order,
                epsilon=epsilon,
            )
            supertraces["interaction_power_type_vakint_finite_part"] = vakint.finite_part(vakint_sum, epsilon=epsilon)
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=vakint_sum,
            on_shell_eft_lagrangian=vakint_sum,
            fluctuation_operators={
                **self.fluctuation_operator.to_expression_map(),
                **self.fluctuation_operator.interaction_expression_map(),
            },
            supertraces=supertraces,
            metadata={
                "stage": "interaction_power_type_vakint_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                "power_type_contribution_count": self.power_type_contribution_count,
                "interaction_power_type_contribution_count": len(contributions),
                "interaction_power_type_excluded_trace_names": ",".join(excluded_trace_names),
                "on_shell_reduced": False,
                "vakint_stage": selected_vakint_stage.value,
                "named_supertrace_stage": selected_named_stage.value,
                "uses_interaction_operator": True,
            },
        )

    def interaction_power_type_internal_matching_result(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
    ) -> MatchingResult:
        """Return the interaction-power result evaluated by pychete's internal integral backend."""

        from .backends import vakint

        excluded_trace_names = tuple(exclude_trace_names)
        contributions = self.interaction_power_type_contributions(
            heavy_field_dimension=heavy_field_dimension,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=excluded_trace_names,
        )
        numerator_sum = sum_expr(contribution.eft_numerator_expression for contribution in contributions).expand()
        raw_vakint_sum = self.interaction_power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=excluded_trace_names,
        )
        evaluated = self.interaction_power_type_internal_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=excluded_trace_names,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
        )
        pole = vakint.pole_part(evaluated, max_pole_order=max_pole_order, epsilon=epsilon)
        finite = vakint.finite_part(evaluated, epsilon=epsilon)
        through_finite = vakint.through_finite_part(
            evaluated,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
        )
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=evaluated,
            on_shell_eft_lagrangian=evaluated,
            fluctuation_operators={
                **self.fluctuation_operator.to_expression_map(),
                **self.fluctuation_operator.interaction_expression_map(),
            },
            supertraces={
                **_named_internal_supertraces(
                    contributions,
                    include_light=include_light,
                    tensor_reduce=tensor_reduce,
                    tensor_reduce_engine=tensor_reduce_engine,
                    epsilon=epsilon,
                    mu_r_squared=mu_r_squared,
                    combine_terms=combine_terms,
                ),
                **self.interaction_power_type_expression_map(
                    prefix="interaction_power_type_supertrace",
                    heavy_field_dimension=heavy_field_dimension,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                    exclude_trace_names=excluded_trace_names,
                ),
                "interaction_power_type_eft_lagrangian": numerator_sum,
                "interaction_power_type_vakint_integral_sum": raw_vakint_sum,
                "interaction_power_type_internal_integral_sum": evaluated,
                "interaction_power_type_internal_integral_pole_part": pole,
                "interaction_power_type_internal_integral_finite_part": finite,
                "interaction_power_type_internal_integral_through_finite_part": through_finite,
            },
            metadata={
                "stage": "interaction_power_type_internal_integral_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                "power_type_contribution_count": self.power_type_contribution_count,
                "interaction_power_type_contribution_count": len(contributions),
                "interaction_power_type_excluded_trace_names": ",".join(excluded_trace_names),
                "on_shell_reduced": False,
                "integral_backend": "pychete_internal",
                "tensor_reduce": tensor_reduce,
                "combine_terms": combine_terms,
                "uses_interaction_operator": True,
                "max_pole_order": max_pole_order,
            },
        )

    def interaction_power_type_internal_minimal_subtraction_result(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
        tensor_reduce: bool = True,
        tensor_reduce_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        combine_terms: bool = False,
    ) -> MatchingResult:
        """Return the internal-backend finite result after pole subtraction.

        This is the minimal-subtraction-style counterpart of
        ``interaction_power_type_internal_matching_result``. It keeps the
        internally evaluated aggregate, pole part, finite part, and counterterm
        in ``supertraces`` while using the epsilon^0 coefficient as the current
        EFT Lagrangian preview.
        """

        excluded_trace_names = tuple(exclude_trace_names)
        unrenormalized = self.interaction_power_type_internal_matching_result(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=excluded_trace_names,
            tensor_reduce=tensor_reduce,
            tensor_reduce_engine=tensor_reduce_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
        )
        pole = unrenormalized.expression("interaction_power_type_internal_integral_pole_part")
        finite = unrenormalized.expression("interaction_power_type_internal_integral_finite_part")
        through_finite = unrenormalized.expression("interaction_power_type_internal_integral_through_finite_part")
        counterterm = (-pole).expand()
        finite_named_supertraces = _finite_named_supertraces(
            unrenormalized.supertraces,
            (
                contribution.name
                for contribution in self.interaction_power_type_contributions(
                    heavy_field_dimension=heavy_field_dimension,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                    exclude_trace_names=excluded_trace_names,
                )
            ),
            epsilon=epsilon,
        )
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=finite,
            on_shell_eft_lagrangian=finite,
            matching_conditions=unrenormalized.matching_conditions,
            fluctuation_operators=unrenormalized.fluctuation_operators,
            supertraces={
                **unrenormalized.supertraces,
                **finite_named_supertraces,
                "interaction_power_type_internal_integral_through_finite_part": through_finite,
                "interaction_power_type_internal_integral_ms_counterterm": counterterm,
            },
            metadata={
                **unrenormalized.metadata,
                "stage": "interaction_power_type_internal_minimal_subtraction_result",
                "complete": False,
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
                "on_shell_reduced": False,
            },
        )

    def interaction_power_type_normalized_matching_result(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        normalization: OneLoopNormalizationInput = OneLoopNormalization.MATCHETE_HBAR,
        hbar: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
    ) -> MatchingResult:
        """Return an interaction-power result with an explicit loop factor applied."""

        excluded_trace_names = tuple(exclude_trace_names)
        unnormalized = self.interaction_power_type_matching_result(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=excluded_trace_names,
            vakint_stage=vakint_stage,
            vakint_short_form=vakint_short_form,
            vakint_engine=vakint_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            named_supertrace_stage=named_supertrace_stage,
            named_supertrace_short_form=named_supertrace_short_form,
            named_supertrace_engine=named_supertrace_engine,
        )
        return unnormalized.with_loop_normalization(
            normalization,
            hbar=hbar,
            stage="interaction_power_type_normalized_vakint_result",
            unnormalized_expression_name="interaction_power_type_vakint_integral_sum",
        )

    def interaction_power_type_minimal_subtraction_result(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        exclude_trace_names: Iterable[str] = (),
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
    ) -> MatchingResult:
        """Return the finite interaction-power result after pole subtraction."""

        from .backends import vakint

        excluded_trace_names = tuple(exclude_trace_names)
        contributions = self.interaction_power_type_contributions(
            heavy_field_dimension=heavy_field_dimension,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=excluded_trace_names,
        )
        numerator_sum = sum_expr(contribution.eft_numerator_expression for contribution in contributions).expand()
        evaluated = self.interaction_power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
            exclude_trace_names=excluded_trace_names,
            stage=VakintIntegralStage.EVALUATED,
            engine=vakint_engine,
        )
        selected_named_stage = VakintIntegralStage.from_user(named_supertrace_stage)
        pole = vakint.pole_part(evaluated, max_pole_order=max_pole_order, epsilon=epsilon)
        finite = vakint.finite_part(evaluated, epsilon=epsilon)
        counterterm = (-pole).expand()
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=finite,
            on_shell_eft_lagrangian=finite,
            fluctuation_operators={
                **self.fluctuation_operator.to_expression_map(),
                **self.fluctuation_operator.interaction_expression_map(),
            },
            supertraces={
                **_named_vakint_supertraces(
                    contributions,
                    include_light=include_light,
                    stage=selected_named_stage,
                    short_form=named_supertrace_short_form,
                    engine=named_supertrace_engine,
                ),
                **self.interaction_power_type_expression_map(
                    prefix="interaction_power_type_supertrace",
                    heavy_field_dimension=heavy_field_dimension,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                    exclude_trace_names=excluded_trace_names,
                ),
                "interaction_power_type_eft_lagrangian": numerator_sum,
                "interaction_power_type_vakint_integral_sum": evaluated,
                "interaction_power_type_vakint_integral_sum[evaluated]": evaluated,
                "interaction_power_type_vakint_pole_part": pole,
                "interaction_power_type_vakint_ms_counterterm": counterterm,
                "interaction_power_type_vakint_finite_part": finite,
            },
            metadata={
                "stage": "interaction_power_type_minimal_subtraction_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                "power_type_contribution_count": self.power_type_contribution_count,
                "interaction_power_type_contribution_count": len(contributions),
                "interaction_power_type_excluded_trace_names": ",".join(excluded_trace_names),
                "on_shell_reduced": False,
                "vakint_stage": VakintIntegralStage.EVALUATED.value,
                "named_supertrace_stage": selected_named_stage.value,
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
                "max_pole_order": max_pole_order,
                "uses_interaction_operator": True,
            },
        )

    def power_type_vakint_epsilon_coefficient(
        self,
        power: int,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        stage: VakintIntegralStage | str = VakintIntegralStage.EVALUATED,
        short_form: bool | None = None,
        engine: Any | None = None,
        epsilon: Expression | None = None,
    ) -> Expression:
        """Return one epsilon coefficient of the aggregate vakint expression."""

        from .backends import vakint

        expr = self.power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            stage=stage,
            short_form=short_form,
            engine=engine,
        )
        return vakint.epsilon_coefficient(expr, power, epsilon=epsilon)

    def power_type_vakint_pole_part(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        stage: VakintIntegralStage | str = VakintIntegralStage.EVALUATED,
        short_form: bool | None = None,
        engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
    ) -> Expression:
        """Return the negative-power epsilon poles of the aggregate vakint expression."""

        from .backends import vakint

        expr = self.power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            stage=stage,
            short_form=short_form,
            engine=engine,
        )
        return vakint.pole_part(expr, max_pole_order=max_pole_order, epsilon=epsilon)

    def power_type_vakint_finite_part(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        stage: VakintIntegralStage | str = VakintIntegralStage.EVALUATED,
        short_form: bool | None = None,
        engine: Any | None = None,
        epsilon: Expression | None = None,
    ) -> Expression:
        """Return the epsilon^0 coefficient of the aggregate vakint expression."""

        from .backends import vakint

        expr = self.power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            stage=stage,
            short_form=short_form,
            engine=engine,
        )
        return vakint.finite_part(expr, epsilon=epsilon)

    def power_type_matching_result(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
    ) -> MatchingResult:
        """Return the current incomplete one-loop result for power-type terms.

        The returned EFT Lagrangians are the aggregate power-type contribution
        after lowering to the selected native vakint stage. Metadata keeps the
        result explicitly incomplete until the full Matchete-level matching
        pipeline, on-shell reduction, and generic operator-basis condition
        extraction land.
        """

        contributions = self.power_type_contributions(heavy_field_dimension=heavy_field_dimension)
        numerator_sum = sum_expr(contribution.eft_numerator_expression for contribution in contributions).expand()
        selected_vakint_stage = VakintIntegralStage.from_user(vakint_stage)
        vakint_sum = self.power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            stage=selected_vakint_stage,
            short_form=vakint_short_form,
            engine=vakint_engine,
        )
        selected_named_stage = VakintIntegralStage.from_user(named_supertrace_stage)
        supertraces = {
            **_named_vakint_supertraces(
                contributions,
                include_light=include_light,
                stage=selected_named_stage,
                short_form=named_supertrace_short_form,
                engine=named_supertrace_engine,
            ),
            **self.power_type_expression_map(prefix="power_type_supertrace"),
            "power_type_eft_lagrangian": numerator_sum,
            "power_type_vakint_integral_sum": vakint_sum,
            f"power_type_vakint_integral_sum[{selected_vakint_stage.value}]": vakint_sum,
        }
        if selected_vakint_stage is VakintIntegralStage.EVALUATED:
            from .backends import vakint

            supertraces["power_type_vakint_pole_part"] = vakint.pole_part(
                vakint_sum,
                max_pole_order=max_pole_order,
                epsilon=epsilon,
            )
            supertraces["power_type_vakint_finite_part"] = vakint.finite_part(vakint_sum, epsilon=epsilon)
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=vakint_sum,
            on_shell_eft_lagrangian=vakint_sum,
            fluctuation_operators=self.fluctuation_operator.to_expression_map(),
            supertraces=supertraces,
            metadata={
                "stage": "power_type_vakint_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                "power_type_contribution_count": self.power_type_contribution_count,
                "on_shell_reduced": False,
                "vakint_stage": selected_vakint_stage.value,
                "named_supertrace_stage": selected_named_stage.value,
            },
        )

    def power_type_matching_preview(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
    ) -> MatchingResult:
        """Return the current incomplete power-type matching result.

        This compatibility alias keeps the older preview method name while the
        result now uses the vakint-staged aggregate as the EFT Lagrangian.
        """

        return self.power_type_matching_result(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            vakint_stage=vakint_stage,
            vakint_short_form=vakint_short_form,
            vakint_engine=vakint_engine,
            max_pole_order=max_pole_order,
            epsilon=epsilon,
            named_supertrace_stage=named_supertrace_stage,
            named_supertrace_short_form=named_supertrace_short_form,
            named_supertrace_engine=named_supertrace_engine,
        )

    def power_type_minimal_subtraction_result(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        vakint_engine: Any | None = None,
        max_pole_order: int = 1,
        epsilon: Expression | None = None,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
    ) -> MatchingResult:
        """Return the current finite-part result after pole subtraction.

        This is a minimal-subtraction-style preview over the evaluated vakint
        aggregate. It removes the negative-power epsilon pole part and uses the
        epsilon^0 coefficient as the EFT Lagrangian, while preserving both the
        raw pole and counterterm in ``supertraces`` for inspection.
        """

        from .backends import vakint

        contributions = self.power_type_contributions(heavy_field_dimension=heavy_field_dimension)
        numerator_sum = sum_expr(contribution.eft_numerator_expression for contribution in contributions).expand()
        evaluated = self.power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            stage=VakintIntegralStage.EVALUATED,
            engine=vakint_engine,
        )
        selected_named_stage = VakintIntegralStage.from_user(named_supertrace_stage)
        pole = vakint.pole_part(evaluated, max_pole_order=max_pole_order, epsilon=epsilon)
        finite = vakint.finite_part(evaluated, epsilon=epsilon)
        counterterm = (-pole).expand()
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=finite,
            on_shell_eft_lagrangian=finite,
            fluctuation_operators=self.fluctuation_operator.to_expression_map(),
            supertraces={
                **_named_vakint_supertraces(
                    contributions,
                    include_light=include_light,
                    stage=selected_named_stage,
                    short_form=named_supertrace_short_form,
                    engine=named_supertrace_engine,
                ),
                **self.power_type_expression_map(prefix="power_type_supertrace"),
                "power_type_eft_lagrangian": numerator_sum,
                "power_type_vakint_integral_sum": evaluated,
                "power_type_vakint_integral_sum[evaluated]": evaluated,
                "power_type_vakint_pole_part": pole,
                "power_type_vakint_ms_counterterm": counterterm,
                "power_type_vakint_finite_part": finite,
            },
            metadata={
                "stage": "power_type_minimal_subtraction_result",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                "power_type_contribution_count": self.power_type_contribution_count,
                "on_shell_reduced": False,
                "vakint_stage": VakintIntegralStage.EVALUATED.value,
                "named_supertrace_stage": selected_named_stage.value,
                "subtraction_scheme": "minimal_subtraction_preview",
                "poles_subtracted": True,
                "max_pole_order": max_pole_order,
            },
        )

    def vakint_integral_expression_map(
        self,
        *,
        prefix: str = "vakint_integral",
        include_light: bool = True,
    ) -> dict[str, Expression]:
        """Return generated trace kernels lowered to vakint topology expressions."""

        return {
            f"{prefix}[{trace.name}]": trace.vakint_integral_expression(include_light=include_light)
            for trace in self.block_traces
        }

    def canonicalize_vakint_integral_expression_map(
        self,
        *,
        prefix: str = "vakint_integral",
        short_form: bool | None = None,
        engine: Any | None = None,
        include_light: bool = True,
    ) -> dict[str, Expression]:
        """Canonicalize generated vakint integral expressions with native vakint."""

        from .backends import vakint

        return {
            name: vakint.decode_pychete_namespace(
                self.theory,
                vakint.to_canonical(expr, short_form=short_form, engine=engine),
            )
            for name, expr in self.vakint_integral_expression_map(
                prefix=prefix,
                include_light=include_light,
            ).items()
        }

    def tensor_reduce_vakint_integral_expression_map(
        self,
        *,
        prefix: str = "vakint_integral",
        engine: Any | None = None,
        include_light: bool = True,
    ) -> dict[str, Expression]:
        """Tensor-reduce generated vakint integral expressions with native vakint."""

        from .backends import vakint

        return {
            name: vakint.decode_pychete_namespace(
                self.theory,
                vakint.tensor_reduce(expr, engine=engine),
            )
            for name, expr in self.vakint_integral_expression_map(
                prefix=prefix,
                include_light=include_light,
            ).items()
        }

    def evaluate_vakint_integral_expression_map(
        self,
        *,
        prefix: str = "vakint_integral",
        engine: Any | None = None,
        include_light: bool = True,
    ) -> dict[str, Expression]:
        """Evaluate generated vakint integral expressions with native vakint."""

        from .backends import vakint

        return {
            name: vakint.decode_pychete_namespace(
                self.theory,
                vakint.evaluate(expr, engine=engine),
            )
            for name, expr in self.vakint_integral_expression_map(
                prefix=prefix,
                include_light=include_light,
            ).items()
        }

    @property
    def propagator_count(self) -> int:
        """Number of heavy propagators planned by default."""

        return len(self.propagator_plan().propagators)

    def propagator_plan(self, *, include_light: bool = False) -> PropagatorPlan:
        """Return propagator metadata for heavy modes, optionally including light modes."""

        modes = self.fluctuation_operator.modes
        selected_modes = modes if include_light else tuple(mode for mode in modes if mode.is_heavy)
        return PropagatorPlan(
            theory=self.theory,
            propagators=tuple(_fluctuation_propagator(mode) for mode in selected_modes),
        )

    def simplify_index_algebra(
        self,
        *,
        expand: bool = True,
        gamma: bool = True,
        color: bool = True,
        pychete_color: bool = False,
        metrics: bool = True,
        dots: bool = False,
    ) -> OneLoopSetup:
        """Return a setup with generated kernels simplified through idenso."""

        return replace(
            self,
            block_traces=tuple(
                trace.simplify_index_algebra(
                    expand=expand,
                    gamma=gamma,
                    color=color,
                    pychete_color=pychete_color,
                    metrics=metrics,
                    dots=dots,
                )
                for trace in self.block_traces
            ),
        )

    def canonicalize_integrals(
        self,
        *,
        short_form: bool | None = None,
        engine: Any | None = None,
    ) -> OneLoopSetup:
        """Return a setup with generated kernels canonicalized by vakint."""

        return replace(
            self,
            block_traces=tuple(
                trace.canonicalize_integrals(short_form=short_form, engine=engine)
                for trace in self.block_traces
            ),
        )

    def tensor_reduce_integrals(self, *, engine: Any | None = None) -> OneLoopSetup:
        """Return a setup with generated kernels tensor-reduced by vakint."""

        return replace(
            self,
            block_traces=tuple(
                trace.tensor_reduce_integrals(engine=engine)
                for trace in self.block_traces
            ),
        )

    def evaluate_integrals(self, *, engine: Any | None = None) -> OneLoopSetup:
        """Return a setup with generated kernels evaluated by vakint."""

        return replace(
            self,
            block_traces=tuple(
                trace.evaluate_integrals(engine=engine)
                for trace in self.block_traces
            ),
        )

    def evaluate_tensor_networks(
        self,
        *,
        library: Any | None = None,
        cg_components_by_name: Mapping[str, Sequence[Expression | int | float | complex]] | None = None,
        builtin_cg_components: bool = False,
        native_hep_cg_builtins: bool = False,
        symbolic_cg_components: bool = False,
        function_library: Any | None = None,
        n_steps: int | None = None,
        mode: Any | None = None,
    ) -> OneLoopSetup:
        """Return a setup with generated kernels evaluated through spenso."""

        return replace(
            self,
            block_traces=tuple(
                trace.evaluate_tensor_network(
                    library=library,
                    cg_components_by_name=cg_components_by_name,
                    builtin_cg_components=builtin_cg_components,
                    native_hep_cg_builtins=native_hep_cg_builtins,
                    symbolic_cg_components=symbolic_cg_components,
                    function_library=function_library,
                    n_steps=n_steps,
                    mode=mode,
                )
                for trace in self.block_traces
            ),
        )

    def to_expression_map(self, *, prefix: str = "one_loop_setup") -> dict[str, Expression]:
        """Return deterministic expressions produced by this setup stage."""

        entries = {
            f"{prefix}[uv_lagrangian]": self.uv_lagrangian,
            **self.fluctuation_operator.to_expression_map(prefix=f"{prefix}.fluctuation_operator"),
            **self.fluctuation_operator.momentum_expression_map(
                prefix=f"{prefix}.fluctuation_operator_momentum",
            ),
            **self.fluctuation_operator.interaction_expression_map(
                prefix=f"{prefix}.fluctuation_operator_interaction",
            ),
            **self.fluctuation_operator.propagator_denominator_expression_map(
                prefix=f"{prefix}.fluctuation_operator_denominator",
            ),
            **self.propagator_plan().to_expression_map(prefix=f"{prefix}.propagator"),
            **self.supertrace_expression_map(prefix=f"{prefix}.supertrace_kernel"),
            **self.interaction_supertrace_expression_map(prefix=f"{prefix}.interaction_supertrace_kernel"),
            **self.interaction_wilson_line_kernel_expression_map(
                prefix=f"{prefix}.interaction_wilson_line_kernel",
            ),
            **self.supertrace_propagator_expression_map(prefix=f"{prefix}.supertrace_propagator_kernel"),
            **self.supertrace_operator_propagator_expression_map(
                prefix=f"{prefix}.supertrace_operator_propagator_kernel",
            ),
            **self.vakint_integral_expression_map(prefix=f"{prefix}.vakint_integral"),
            **self.operator_vakint_integral_expression_map(prefix=f"{prefix}.operator_vakint_integral"),
            **self.power_type_expression_map(prefix=f"{prefix}.power_type_supertrace"),
            **self.interaction_power_type_expression_map(prefix=f"{prefix}.interaction_power_type_supertrace"),
            f"{prefix}[power_type_eft_lagrangian]": self.power_type_eft_lagrangian(),
            f"{prefix}[power_type_vakint_integral_sum]": self.power_type_vakint_integral_sum(),
            f"{prefix}[interaction_power_type_eft_lagrangian]": self.interaction_power_type_eft_lagrangian(),
            f"{prefix}[interaction_power_type_vakint_integral_sum]": self.interaction_power_type_vakint_integral_sum(),
        }
        return entries

    def _trace(self, trace: SupertraceBlockTrace | str) -> SupertraceBlockTrace:
        if isinstance(trace, SupertraceBlockTrace):
            return trace
        for candidate in self.block_traces:
            if candidate.name == trace:
                return candidate
        raise KeyError(f"One-loop setup has no trace {trace!r}")

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{OneLoopSetup}}\left({self.theory.name},\ {self.supertrace_kernel_count}\right)$"

    def _repr_html_(self) -> str:
        return (
            f"<code>OneLoopSetup(theory={escape(self.theory.name)} "
            f"kernels={self.supertrace_kernel_count} max_order={self.max_trace_order})</code>"
        )


@dataclass(frozen=True)
class FluctuationOperator:
    """Quadratic fluctuation operator extracted from a Lagrangian."""

    theory: Theory
    basis: tuple[Expression, ...]
    matrix: tuple[tuple[Expression, ...], ...]
    modes: tuple[FluctuationMode, ...] = ()
    differential_matrix: tuple[tuple[Expression, ...], ...] = ()

    def entry(self, row: FluctuationBasisItem, column: FluctuationBasisItem) -> Expression:
        """Return one matrix entry identified by its row and column fields."""

        row_index = self._basis_index(_fluctuation_basis_expression(self.theory, row))
        column_index = self._basis_index(_fluctuation_basis_expression(self.theory, column))
        return self.matrix[row_index][column_index]

    def differential_entry(self, row: FluctuationBasisItem, column: FluctuationBasisItem) -> Expression:
        """Return one Euler-Lagrange differential-operator matrix entry."""

        if not self.differential_matrix:
            return self.entry(row, column)
        row_index = self._basis_index(_fluctuation_basis_expression(self.theory, row))
        column_index = self._basis_index(_fluctuation_basis_expression(self.theory, column))
        return self.differential_matrix[row_index][column_index]

    def momentum_entry(
        self,
        row: FluctuationBasisItem,
        column: FluctuationBasisItem,
        *,
        loop_momentum_squared: Expression | None = None,
    ) -> Expression:
        """Return one differential entry lowered to loop-momentum powers."""

        return _lower_differential_operators_to_momentum(
            self.differential_entry(row, column),
            loop_momentum_squared=loop_momentum_squared,
        )

    def momentum_expression_map(
        self,
        *,
        prefix: str = "fluctuation_operator_momentum",
        loop_momentum_squared: Expression | None = None,
    ) -> dict[str, Expression]:
        """Return deterministic momentum-lowered operator entries."""

        entries: dict[str, Expression] = {}
        for row in self.basis:
            for column in self.basis:
                key = f"{prefix}[{canonical_string(row)},{canonical_string(column)}]"
                entries[key] = self.momentum_entry(
                    row,
                    column,
                    loop_momentum_squared=loop_momentum_squared,
                )
        return entries

    def propagator_denominator_entry(
        self,
        row: FluctuationBasisItem,
        column: FluctuationBasisItem,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> Expression | None:
        """Return a recognized scalar propagator denominator for one entry."""

        row_expr = _fluctuation_basis_expression(self.theory, row)
        column_expr = _fluctuation_basis_expression(self.theory, column)
        row_mode = self.mode_for(row_expr)
        momentum_entry = self.momentum_entry(
            row_expr,
            column_expr,
            loop_momentum_squared=loop_momentum_squared,
        )
        denominator = _momentum_entry_propagator_denominator(
            momentum_entry,
            loop_momentum_squared=loop_momentum_squared,
        )
        if denominator is None and row_mode.statistics is FluctuationStatistics.FERMIONIC:
            denominator = _fermion_momentum_entry_propagator_denominator(
                momentum_entry,
                loop_momentum_squared=loop_momentum_squared,
            )
        if denominator is None and row_mode.statistics is FluctuationStatistics.FERMIONIC:
            free_part = _fermion_registered_free_inverse_part(
                momentum_entry,
                loop_momentum_squared=loop_momentum_squared,
            )
            if free_part is not None:
                denominator = _fermion_momentum_entry_propagator_denominator(
                    free_part,
                    loop_momentum_squared=loop_momentum_squared,
                )
        if denominator is None or not require_registered_mass:
            return denominator
        if not _same_field_label(row_expr, column_expr):
            return None
        expected_mass_squared = _fluctuation_mass_squared(self.mode_for(column_expr))
        if is_zero((denominator[1] - expected_mass_squared).expand()):
            return denominator
        if row_mode.statistics is FluctuationStatistics.FERMIONIC:
            free_part = _fermion_registered_free_inverse_part(
                momentum_entry,
                expected_mass_squared=expected_mass_squared,
                loop_momentum_squared=loop_momentum_squared,
            )
            if free_part is not None:
                return s.PropagatorDenominator(
                    s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared,
                    expected_mass_squared,
                )
        return None

    def propagator_denominator_for_mode(
        self,
        field: FluctuationBasisItem,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> Expression | None:
        """Return the free propagator denominator attached to one basis mode."""

        mode = self.mode_for(field)
        columns: tuple[Expression, ...]
        if mode.self_conjugate:
            columns = (mode.field,)
        else:
            columns = (_conjugate_fluctuation_field(mode.field), mode.field)
        for column in columns:
            try:
                denominator = self.propagator_denominator_entry(
                    mode.field,
                    column,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                )
            except KeyError:
                continue
            if denominator is not None:
                return denominator
            if require_registered_mass:
                entry = self.momentum_entry(
                    mode.field,
                    column,
                    loop_momentum_squared=loop_momentum_squared,
                )
                expected_mass_squared = _fluctuation_mass_squared(self.mode_for(column))
                if _has_registered_free_inverse_part(
                    entry,
                    expected_mass_squared,
                    loop_momentum_squared=loop_momentum_squared,
                ):
                    return s.PropagatorDenominator(
                        s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared,
                        expected_mass_squared,
                    )
        return None

    def propagator_denominator_expression_map(
        self,
        *,
        prefix: str = "fluctuation_operator_denominator",
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> dict[str, Expression]:
        """Return recognized propagator denominators for operator entries."""

        entries: dict[str, Expression] = {}
        for row in self.basis:
            for column in self.basis:
                denominator = self.propagator_denominator_entry(
                    row,
                    column,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                )
                if denominator is None:
                    continue
                key = f"{prefix}[{canonical_string(row)},{canonical_string(column)}]"
                entries[key] = denominator
        return entries

    def free_inverse_entry(
        self,
        row: FluctuationBasisItem,
        column: FluctuationBasisItem,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> Expression:
        """Return the free inverse-propagator part of one momentum entry."""

        row_expr = _fluctuation_basis_expression(self.theory, row)
        column_expr = _fluctuation_basis_expression(self.theory, column)
        row_mode = self.mode_for(row_expr)
        if canonical_string(column_expr) not in _free_inverse_column_keys(row_mode):
            return Expression.num(0)
        momentum_entry = self.momentum_entry(
            row_expr,
            column_expr,
            loop_momentum_squared=loop_momentum_squared,
        )
        if row_mode.statistics is FluctuationStatistics.FERMIONIC:
            expected_mass_squared = (
                _fluctuation_mass_squared(self.mode_for(column_expr))
                if require_registered_mass
                else None
            )
            free_part = _fermion_registered_free_inverse_part(
                momentum_entry,
                expected_mass_squared=expected_mass_squared,
                loop_momentum_squared=loop_momentum_squared,
            )
            return Expression.num(0) if free_part is None else free_part
        denominator = self.propagator_denominator_for_mode(
            row_expr,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
        )
        if denominator is None:
            return Expression.num(0)
        return _propagator_denominator_inverse_expression(denominator)

    def interaction_entry(
        self,
        row: FluctuationBasisItem,
        column: FluctuationBasisItem,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> Expression:
        """Return one fluctuation-operator entry with free propagation removed."""

        momentum_entry = self.momentum_entry(
            row,
            column,
            loop_momentum_squared=loop_momentum_squared,
        )
        free_entry = self.free_inverse_entry(
            row,
            column,
            loop_momentum_squared=loop_momentum_squared,
            require_registered_mass=require_registered_mass,
        )
        return (momentum_entry - free_entry).expand()

    def interaction_expression_map(
        self,
        *,
        prefix: str = "fluctuation_operator_interaction",
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> dict[str, Expression]:
        """Return deterministic interaction-only fluctuation-operator entries."""

        entries: dict[str, Expression] = {}
        for row in self.basis:
            for column in self.basis:
                key = f"{prefix}[{canonical_string(row)},{canonical_string(column)}]"
                entries[key] = self.interaction_entry(
                    row,
                    column,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                )
        return entries

    def interaction_block(
        self,
        row_sector: FluctuationSector | str,
        column_sector: FluctuationSector | str,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> FluctuationOperatorBlock:
        """Return a sector block built from interaction-only operator entries."""

        if not self.modes:
            raise ValueError("This fluctuation operator does not carry basis mode metadata")
        row_selector = FluctuationSector.from_user(row_sector)
        column_selector = FluctuationSector.from_user(column_sector)
        row_indices = _sector_indices(self.modes, row_selector)
        column_indices = _sector_indices(self.modes, column_selector)
        return FluctuationOperatorBlock(
            theory=self.theory,
            row_sector=row_selector,
            column_sector=column_selector,
            rows=tuple(self.modes[index] for index in row_indices),
            columns=tuple(self.modes[index] for index in column_indices),
            matrix=tuple(
                tuple(
                    self.interaction_entry(
                        self.modes[row].field,
                        self.modes[column].field,
                        loop_momentum_squared=loop_momentum_squared,
                        require_registered_mass=require_registered_mass,
                    )
                    for column in column_indices
                )
                for row in row_indices
            ),
        )

    def interaction_category_block(
        self,
        row_category: str,
        column_category: str,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> FluctuationOperatorBlock:
        """Return an interaction-only block restricted to exact supertrace categories."""

        if not self.modes:
            raise ValueError("This fluctuation operator does not carry basis mode metadata")
        row_sector = _supertrace_category_sector(row_category)
        column_sector = _supertrace_category_sector(column_category)
        row_indices = _category_indices(self.modes, row_category)
        column_indices = _category_indices(self.modes, column_category)
        return FluctuationOperatorBlock(
            theory=self.theory,
            row_sector=row_sector,
            column_sector=column_sector,
            rows=tuple(self.modes[index] for index in row_indices),
            columns=tuple(self.modes[index] for index in column_indices),
            matrix=tuple(
                tuple(
                    self.interaction_entry(
                        self.modes[row].field,
                        self.modes[column].field,
                        loop_momentum_squared=loop_momentum_squared,
                        require_registered_mass=require_registered_mass,
                    )
                    for column in column_indices
                )
                for row in row_indices
            ),
            row_category=row_category,
            column_category=column_category,
        )

    def interaction_category_trace(
        self,
        category_path: Sequence[str],
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> SupertraceBlockTrace:
        """Return one selected interaction-only category trace without building the full plan."""

        if not category_path:
            raise ValueError("category_path must not be empty")
        path = tuple(category_path)
        closed_path = (*path, path[0])
        block_cache: dict[tuple[str, str], FluctuationOperatorBlock] = {}
        blocks: list[FluctuationOperatorBlock] = []
        for index in range(len(path)):
            key = (closed_path[index], closed_path[index + 1])
            if key not in block_cache:
                block_cache[key] = self.interaction_category_block(
                    key[0],
                    key[1],
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                )
            blocks.append(block_cache[key])
        block_tuple = tuple(blocks)
        _validate_closed_block_chain(block_tuple)
        return SupertraceBlockTrace(
            theory=self.theory,
            name="-".join(path),
            blocks=block_tuple,
            modes=block_tuple[0].rows,
            expression=_supertrace_block_product(block_tuple),
            cyclic_key=path,
        )

    def interaction_supertrace_plan(
        self,
        *,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
    ) -> SupertracePlan:
        """Prepare heavy/light blocks with free inverse propagation removed."""

        return SupertracePlan(
            theory=self.theory,
            operator=self,
            heavy_heavy=self.interaction_block(
                FluctuationSector.HEAVY,
                FluctuationSector.HEAVY,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
            ),
            heavy_light=self.interaction_block(
                FluctuationSector.HEAVY,
                FluctuationSector.LIGHT,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
            ),
            light_heavy=self.interaction_block(
                FluctuationSector.LIGHT,
                FluctuationSector.HEAVY,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
            ),
            light_light=self.interaction_block(
                FluctuationSector.LIGHT,
                FluctuationSector.LIGHT,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
            ),
        )

    def to_expression_map(self, *, prefix: str = "fluctuation_operator") -> dict[str, Expression]:
        """Return deterministic named entries suitable for ``MatchingResult``."""

        entries: dict[str, Expression] = {}
        for row in self.basis:
            for column in self.basis:
                key = f"{prefix}[{canonical_string(row)},{canonical_string(column)}]"
                entries[key] = self.entry(row, column)
                if self.differential_matrix:
                    differential_key = f"{prefix}_differential[{canonical_string(row)},{canonical_string(column)}]"
                    entries[differential_key] = self.differential_entry(row, column)
        return entries

    def _basis_index(self, field: Expression) -> int:
        key = canonical_string(field)
        for index, basis_field in enumerate(self.basis):
            if canonical_string(basis_field) == key:
                return index
        raise KeyError(f"Fluctuation basis has no field {key!r}")

    def mode_for(self, field: FluctuationBasisItem) -> FluctuationMode:
        """Return metadata for one field expression in this operator basis."""

        if not self.modes:
            raise ValueError("This fluctuation operator does not carry basis mode metadata")
        requested = _fluctuation_basis_expression(self.theory, field)
        return self.modes[_mode_index(self.modes, requested)]

    def block(
        self,
        row_sector: FluctuationSector | str,
        column_sector: FluctuationSector | str,
    ) -> FluctuationOperatorBlock:
        """Return a heavy/light sector block of the fluctuation matrix."""

        if not self.modes:
            raise ValueError("This fluctuation operator does not carry basis mode metadata")
        row_selector = FluctuationSector.from_user(row_sector)
        column_selector = FluctuationSector.from_user(column_sector)
        row_indices = _sector_indices(self.modes, row_selector)
        column_indices = _sector_indices(self.modes, column_selector)
        return FluctuationOperatorBlock(
            theory=self.theory,
            row_sector=row_selector,
            column_sector=column_selector,
            rows=tuple(self.modes[index] for index in row_indices),
            columns=tuple(self.modes[index] for index in column_indices),
            matrix=tuple(tuple(self.matrix[row][column] for column in column_indices) for row in row_indices),
        )

    def supertrace_plan(self) -> SupertracePlan:
        """Prepare heavy/light block data for future supertrace generation."""

        return SupertracePlan(
            theory=self.theory,
            operator=self,
            heavy_heavy=self.block(FluctuationSector.HEAVY, FluctuationSector.HEAVY),
            heavy_light=self.block(FluctuationSector.HEAVY, FluctuationSector.LIGHT),
            light_heavy=self.block(FluctuationSector.LIGHT, FluctuationSector.HEAVY),
            light_light=self.block(FluctuationSector.LIGHT, FluctuationSector.LIGHT),
        )

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{FluctuationOperator}}\left({len(self.basis)}\times {len(self.basis)}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>FluctuationOperator({len(self.basis)}x{len(self.basis)})</code>"


class OneLoopMatchingNotImplementedError(NotImplementedError):
    """Raised while the one-loop matching engine is still under construction."""


def fluctuation_operator(
    theory: Theory,
    lagrangian: Expression,
    fields: FluctuationBasis | Iterable[FluctuationBasisItem] | None = None,
) -> FluctuationOperator:
    """Extract the Symbolica Hessian over a fluctuation basis.

    The algebraic matrix is the exact-field Hessian used by current supertrace
    previews. The differential matrix is assembled from Euler-Lagrange
    functional derivatives and keeps derivative slots as
    ``DifferentialOperator`` expressions for later backend lowering.
    """

    theory._validate_registered_expression(lagrangian)
    basis_info = _normalize_fluctuation_basis(theory, lagrangian, fields)
    basis = basis_info.entries
    if not basis:
        raise ValueError("at least one fluctuation field is required")
    _validate_unique_fluctuation_basis(basis)
    with progress(
        f"building fluctuation operator for {theory.name} ({len(basis)} modes)",
        logger=_LOGGER,
        level="DEBUG",
    ):
        matrix = tuple(
            tuple(
                partial_functional_derivative(
                    partial_functional_derivative(lagrangian, row),
                    column,
                ).expand()
                for column in basis
            )
            for row in basis
        )
        differential_matrix = tuple(
            tuple(
                _fluctuation_differential_entry(theory, lagrangian, row, column)
                for column in basis
            )
            for row in basis
        )
    return FluctuationOperator(
        theory=theory,
        basis=basis,
        matrix=matrix,
        modes=basis_info.modes,
        differential_matrix=differential_matrix,
    )


def fluctuation_basis(theory: Theory, lagrangian: Expression) -> FluctuationBasis:
    """Discover fluctuation fields in a Lagrangian with Symbolica patterns."""

    theory._validate_registered_expression(lagrangian)
    fields = _discover_fluctuation_basis(lagrangian)
    _LOGGER.debug("discovered %d fluctuation fields for %s", len(fields), theory.name)
    return FluctuationBasis(theory=theory, modes=tuple(_fluctuation_mode(theory, field) for field in fields))


def matchete_fluctuation_dof_basis(theory: Theory, lagrangian: Expression) -> FluctuationBasis:
    """Return a label-level fluctuation basis matching Matchete's DOF classing."""

    fields = matchete_fluctuation_dof_basis_fields(theory, lagrangian)
    return FluctuationBasis(theory=theory, modes=tuple(_fluctuation_mode(theory, field) for field in fields))


def one_loop_setup(
    theory: Theory,
    lagrangian: Expression,
    *,
    eft_order: int = 6,
    max_trace_order: int = 2,
    include_light_only: bool = False,
    fluctuation_fields: FluctuationBasis | Iterable[FluctuationBasisItem] | None = None,
    matchete_fluctuation_dof_basis: bool = False,
    wilson_line_weight_paths_by_component_dofs: bool = False,
) -> OneLoopSetup:
    """Prepare the current native-backed one-loop matching input stages."""

    if max_trace_order < 1:
        raise ValueError("max_trace_order must be at least 1")
    theory._validate_registered_expression(lagrangian)
    if wilson_line_weight_paths_by_component_dofs and not matchete_fluctuation_dof_basis:
        raise ValueError(
            "wilson_line_weight_paths_by_component_dofs requires matchete_fluctuation_dof_basis"
        )
    if matchete_fluctuation_dof_basis and fluctuation_fields is None:
        fluctuation_fields = matchete_fluctuation_dof_basis_fields(theory, lagrangian)
    with progress(
        (
            f"preparing one-loop setup for {theory.name} "
            f"(eft_order={eft_order}, max_trace_order={max_trace_order})"
        ),
        logger=_LOGGER,
    ):
        operator = fluctuation_operator(theory, lagrangian, fluctuation_fields)
        plan = operator.supertrace_plan()
        block_traces = tuple(
            trace
            for order in range(1, max_trace_order + 1)
            for trace in plan.closed_category_traces(order, include_light_only=include_light_only)
        )
        setup = OneLoopSetup(
            theory=theory,
            uv_lagrangian=lagrangian,
            eft_order=eft_order,
            fluctuation_operator=operator,
            supertrace_plan=plan,
            block_traces=block_traces,
            matchete_fluctuation_dof_basis=matchete_fluctuation_dof_basis,
            wilson_line_weight_paths_by_component_dofs=wilson_line_weight_paths_by_component_dofs,
        )
    _LOGGER.info(
        "one-loop setup for %s contains %d fluctuation modes and %d trace kernels",
        theory.name,
        len(operator.basis),
        setup.supertrace_kernel_count,
    )
    return setup


def _fluctuation_basis_expression(theory: Theory, field: FluctuationBasisItem) -> Expression:
    if isinstance(field, FieldHandle):
        return field()
    if isinstance(field, FieldDefinition):
        return field.expr()
    if isinstance(field, str):
        return theory.field_handle(field)()
    return field


def _normalize_fluctuation_basis(
    theory: Theory,
    lagrangian: Expression,
    fields: FluctuationBasis | Iterable[FluctuationBasisItem] | None,
) -> FluctuationBasis:
    if fields is None:
        return fluctuation_basis(theory, lagrangian)
    if isinstance(fields, FluctuationBasis):
        if fields.theory.name != theory.name:
            raise ValueError(f"Fluctuation basis belongs to {fields.theory.name!r}, not {theory.name!r}")
        return fields
    basis = tuple(_fluctuation_basis_expression(theory, field) for field in fields)
    return FluctuationBasis(theory=theory, modes=tuple(_fluctuation_mode(theory, field) for field in basis))


def _fluctuation_differential_entry(
    theory: Theory,
    lagrangian: Expression,
    row: Expression,
    column: Expression,
) -> Expression:
    entry = _fluctuation_differential_entry_from_lagrangian(theory, lagrangian, row, column)
    implicit_entry = _implicit_abelian_scalar_vector_differential_entry(
        theory,
        lagrangian,
        row,
        column,
        explicit_entry=entry,
    )
    if not is_zero(implicit_entry):
        entry = entry + implicit_entry
    return entry.expand()


def _fluctuation_differential_entry_from_lagrangian(
    theory: Theory,
    lagrangian: Expression,
    row: Expression,
    column: Expression,
) -> Expression:
    row_variation = FieldVariation.BAR if is_bar_field(row) else FieldVariation.FIELD
    eom = derive_eom(theory, lagrangian, row, variation=row_variation)
    return _fluctuation_differential_entry_from_eom(theory, lagrangian, eom, row, column)


def _fluctuation_differential_entry_from_eom(
    theory: Theory,
    lagrangian: Expression,
    eom: Expression,
    row: Expression,
    column: Expression,
) -> Expression:

    column_base = bar_field_inner(column) if is_bar_field(column) else column
    column_barred = is_bar_field(column)
    derivative_sets = _field_derivative_sets_in_expression(
        eom,
        field_label(column_base),
        barred=column_barred,
    )
    derivative_sets.add(())

    terms: list[Expression] = []
    for derivatives in sorted(derivative_sets, key=_derivative_set_sort_key):
        target = field_with_derivatives(column_base, derivatives)
        if column_barred:
            target = s.Bar(target)
        coefficient = partial_functional_derivative(eom, target)
        if not is_zero(coefficient):
            terms.append(_differential_operator_term(coefficient, derivatives))
    terms.extend(_field_strength_differential_terms(theory, lagrangian, row, column))
    return sum_expr(terms).expand()


def _implicit_abelian_scalar_vector_differential_entry(
    theory: Theory,
    lagrangian: Expression,
    row: Expression,
    column: Expression,
    *,
    explicit_entry: Expression,
) -> Expression:
    """Return Matchete-style scalar-vector X-terms from implicit Abelian CDs."""

    if not is_zero(explicit_entry):
        return Expression.num(0)
    scalar, vector = _scalar_vector_fluctuation_pair(row, column)
    if scalar is None or vector is None:
        return Expression.num(0)
    scalar_base = bar_field_inner(scalar) if is_bar_field(scalar) else scalar
    if not bool(field_type(scalar_base) == s.Scalar):
        return Expression.num(0)
    if field_self_conjugate_from_label(field_label(scalar_base)):
        return Expression.num(0)
    if not _lagrangian_has_first_derivative_scalar_kinetic(lagrangian, scalar_base):
        return Expression.num(0)
    try:
        scalar_definition = _field_definition_from_label(theory, field_label(scalar_base))
        vector_definition = _field_definition_from_label(theory, field_label(vector))
    except KeyError:
        return Expression.num(0)
    charge_connection = _abelian_connection_factor_for_vector(theory, scalar_definition, vector_definition)
    if is_zero(charge_connection):
        return Expression.num(0)
    derivative = _implicit_scalar_kinetic_derivative_index(lagrangian, scalar_base, theory=theory)
    scalar_derivative = field_with_derivatives(scalar_base, (derivative,))
    interaction_lagrangian = (
        Expression.I * charge_connection * vector * s.Bar(scalar_base) * scalar_derivative
        - Expression.I * charge_connection * vector * s.Bar(scalar_derivative) * scalar_base
    ).expand()
    entry = _fluctuation_differential_entry_from_lagrangian(theory, interaction_lagrangian, row, column)
    entry = _matchete_implicit_scalar_vector_derivative_signs(entry, field_label(scalar_base))
    open_cd_entry = _implicit_abelian_scalar_vector_open_cd_entry(entry, field_label(scalar_base))
    return (entry + open_cd_entry).expand()


def _matchete_implicit_scalar_vector_derivative_signs(entry: Expression, scalar_label: Expression) -> Expression:
    """Align implicit scalar-vector derivative atoms with Matchete ``Xterm`` signs."""

    derivative_terms: list[Expression] = []
    seen_fields: set[str] = set()
    for pattern in (field_pattern(scalar_label), bar_field_pattern(scalar_label)):
        for match in entry.match(pattern):
            field_atom = pattern.replace_wildcards(match)
            base_field = bar_field_inner(field_atom) if is_bar_field(field_atom) else field_atom
            if len(field_derivatives(base_field)) != 1:
                continue
            field_key = canonical_string(field_atom)
            if field_key in seen_fields:
                continue
            seen_fields.add(field_key)
            coefficient = entry.coefficient(field_atom).expand()
            if is_zero(coefficient):
                continue
            derivative_terms.append(coefficient * field_atom)
    if not derivative_terms:
        return entry
    return (entry - 2 * sum_expr(derivative_terms)).expand()


def _implicit_abelian_scalar_vector_open_cd_entry(entry: Expression, scalar_label: Expression) -> Expression:
    """Return Matchete-style scalar-vector ``OpenCD`` branches.

    Matchete's scalar-vector ``Xterm[..., 1, 1, 1]`` branch is tied to the
    same first-order operator coefficient that produces the ``LoopMom`` branch
    after ``OpenCD -> OpenCD - I LoopMom``. In pychete's differential
    representation, ``C * DifferentialOperator(mu)`` lowers to
    ``I*C*LoopMomentum(mu)``, so the corresponding open branch is
    ``-C*NCM(field, OpenCD(mu))`` with the matched scalar field kept inside the
    noncommutative chain.
    """

    operator_pattern = s.DifferentialOperator(s.FieldDerivativesWildcard)
    seen_operators: set[str] = set()
    terms_out: list[Expression] = []
    for match in entry.match(operator_pattern):
        derivatives = list_items(match[s.FieldDerivativesWildcard])
        if len(derivatives) != 1:
            continue
        operator = operator_pattern.replace_wildcards(match)
        operator_key = canonical_string(operator)
        if operator_key in seen_operators:
            continue
        seen_operators.add(operator_key)
        coefficient = entry.coefficient(operator).expand()
        terms_out.append(
            _implicit_abelian_scalar_vector_open_cd_terms_from_coefficient(
                coefficient,
                scalar_label,
                derivatives[0],
            )
        )
    return sum_expr(terms_out).expand()


def _implicit_abelian_scalar_vector_open_cd_terms_from_coefficient(
    coefficient: Expression,
    scalar_label: Expression,
    derivative: Expression,
) -> Expression:
    open_cd = open_covariant_derivative(derivative)
    terms_out: list[Expression] = []
    seen_fields: set[str] = set()
    for pattern in (field_pattern(scalar_label), bar_field_pattern(scalar_label)):
        for match in coefficient.match(pattern):
            field_atom = pattern.replace_wildcards(match)
            base_field = bar_field_inner(field_atom) if is_bar_field(field_atom) else field_atom
            if field_derivatives(base_field):
                continue
            field_key = canonical_string(field_atom)
            if field_key in seen_fields:
                continue
            seen_fields.add(field_key)
            scalar_coefficient = coefficient.coefficient(field_atom).expand()
            if is_zero(scalar_coefficient):
                continue
            terms_out.append(-scalar_coefficient * s.NCM(field_atom, open_cd))
    return sum_expr(terms_out).expand()


def _scalar_vector_fluctuation_pair(row: Expression, column: Expression) -> tuple[Expression | None, Expression | None]:
    row_base = bar_field_inner(row) if is_bar_field(row) else row
    column_base = bar_field_inner(column) if is_bar_field(column) else column
    if not is_head(row_base, s.Field) or not is_head(column_base, s.Field):
        return None, None
    row_is_scalar = bool(field_type(row_base) == s.Scalar)
    column_is_scalar = bool(field_type(column_base) == s.Scalar)
    row_is_vector = _is_vector_field_label(field_label(row_base))
    column_is_vector = _is_vector_field_label(field_label(column_base))
    if row_is_scalar and column_is_vector:
        return row, column_base
    if row_is_vector and column_is_scalar:
        return column, row_base
    return None, None


def _lagrangian_has_first_derivative_scalar_kinetic(lagrangian: Expression, scalar_base: Expression) -> bool:
    label = field_label(scalar_base)
    plain_derivatives = _field_derivative_sets_in_expression(lagrangian, label, barred=False)
    barred_derivatives = _field_derivative_sets_in_expression(lagrangian, label, barred=True)
    return any(len(derivatives) == 1 for derivatives in plain_derivatives) and any(
        len(derivatives) == 1 for derivatives in barred_derivatives
    )


def _implicit_scalar_kinetic_derivative_index(
    lagrangian: Expression,
    scalar_base: Expression,
    *,
    theory: Theory,
) -> Expression:
    label = field_label(scalar_base)
    plain_derivatives = sorted(
        (
            derivatives
            for derivatives in _field_derivative_sets_in_expression(lagrangian, label, barred=False)
            if len(derivatives) == 1
        ),
        key=_derivative_set_sort_key,
    )
    if plain_derivatives:
        return plain_derivatives[0][0]
    return theory.dummy_index(0)


def _abelian_connection_factor_for_vector(
    theory: Theory,
    scalar_definition: FieldDefinition,
    vector_definition: FieldDefinition,
) -> Expression:
    terms: list[Expression] = []
    for charge in scalar_definition.charge_exprs:
        group_symbol = theory._group_symbol_for_charge(charge)
        if group_symbol is None:
            continue
        group_kind = GroupKind.from_user(str(symbol_data(group_symbol, SymbolDataKey.GROUP_KIND, GroupKind.GLOBAL.value)))
        if group_kind is not GroupKind.GAUGE or not bool(symbol_data(group_symbol, SymbolDataKey.GROUP_ABELIAN, 0)):
            continue
        if len(charge) != 1:
            raise ValueError(f"Gauge charge {canonical_string(charge)} must carry exactly one charge value")
        field_name = symbol_data(group_symbol, SymbolDataKey.GROUP_FIELD)
        if not isinstance(field_name, str):
            continue
        if theory.fields.get(field_name) != vector_definition:
            continue
        coupling_name = symbol_data(group_symbol, SymbolDataKey.GROUP_COUPLING)
        if not isinstance(coupling_name, str):
            raise ValueError(f"Gauge group {canonical_string(group_symbol)} is missing coupling metadata")
        terms.append(charge[0] * theory.coupling_handle(coupling_name)())
    return sum_expr(terms).expand()


def _field_strength_differential_terms(
    theory: Theory,
    lagrangian: Expression,
    row: Expression,
    column: Expression,
) -> tuple[Expression, ...]:
    row_base = bar_field_inner(row) if is_bar_field(row) else row
    column_base = bar_field_inner(column) if is_bar_field(column) else column
    row_label = field_label(row_base)
    column_label = field_label(column_base)
    if not _is_vector_field_label(row_label) or not _is_vector_field_label(column_label):
        return ()
    row_strengths = _matching_field_strength_atoms(lagrangian, row_label, list_items(row_base[2]))
    column_strengths = _matching_field_strength_atoms(lagrangian, column_label, list_items(column_base[2]))
    terms: list[Expression] = []
    for row_strength, row_lorentz in row_strengths:
        for column_strength, column_lorentz in column_strengths:
            if not _same_expression_sequence(row_lorentz, column_lorentz):
                continue
            coefficient = _field_strength_bilinear_coefficient(lagrangian, row_strength, column_strength)
            if is_zero(coefficient):
                continue
            multiplicity = 4 if bool(row_strength == column_strength) else 2
            terms.append(
                multiplicity
                * coefficient
                * s.DifferentialOperator(list_expr(row_lorentz[0], row_lorentz[0]))
            )
    return tuple(terms)


def _is_vector_field_label(label: Expression) -> bool:
    field_type = field_type_from_label(label)
    return bool(field_type == s.Vector) or is_head(field_type, s.Vector)


def _matching_field_strength_atoms(
    lagrangian: Expression,
    label: Expression,
    gauge_indices: tuple[Expression, ...],
) -> tuple[tuple[Expression, tuple[Expression, ...]], ...]:
    pattern = field_strength_pattern(label)
    seen: set[str] = set()
    strengths: list[tuple[Expression, tuple[Expression, ...]]] = []
    for match in lagrangian.match(pattern):
        strength = pattern.replace_wildcards(match)
        key = canonical_string(strength)
        if key in seen:
            continue
        seen.add(key)
        if not _same_expression_sequence(gauge_indices, list_items(match[s.FieldStrengthIndicesWildcard])):
            continue
        if list_items(match[s.FieldStrengthDerivativesWildcard]):
            continue
        lorentz_indices = list_items(match[s.FieldStrengthLorentzWildcard])
        if len(lorentz_indices) != 2:
            continue
        strengths.append((strength, lorentz_indices))
    return tuple(strengths)


def _field_strength_bilinear_coefficient(
    lagrangian: Expression,
    left: Expression,
    right: Expression,
) -> Expression:
    product = left**2 if bool(left == right) else left * right
    return lagrangian.coefficient(product).expand()


def _field_derivative_sets_in_expression(
    expr: Expression,
    label: Expression,
    *,
    barred: bool,
) -> set[tuple[Expression, ...]]:
    pattern = bar_field_pattern(label) if barred else field_pattern(label)
    return {list_items(match[s.FieldDerivativesWildcard]) for match in expr.match(pattern)}


def _derivative_set_sort_key(derivatives: tuple[Expression, ...]) -> tuple[int, tuple[str, ...]]:
    return (len(derivatives), tuple(canonical_string(index) for index in derivatives))


def _differential_operator_term(coefficient: Expression, derivatives: tuple[Expression, ...]) -> Expression:
    if not derivatives:
        return coefficient
    return coefficient * s.DifferentialOperator(list_expr(*derivatives))


def _lower_differential_operators_to_momentum(
    expr: Expression,
    *,
    loop_momentum_squared: Expression | None = None,
) -> Expression:
    momentum_squared = s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared
    pattern = s.DifferentialOperator(s.FieldDerivativesWildcard)

    def lower_operator(match: dict[Expression, Expression]) -> Expression:
        matched = pattern.replace_wildcards(match)
        derivatives = list_items(match[s.FieldDerivativesWildcard])
        power = _contracted_derivative_pair_power(derivatives)
        if power is None:
            return _open_derivative_momentum_product(derivatives)
        if power == 0:
            return Expression.num(1)
        return (-momentum_squared) ** power

    return expr.replace(pattern, lower_operator).expand()


def _open_derivative_momentum_product(derivatives: tuple[Expression, ...]) -> Expression:
    if not derivatives:
        return Expression.num(1)
    return product_expr(Expression.I * s.LoopMomentum(index) for index in derivatives)


def _momentum_entry_propagator_denominator(
    expr: Expression,
    *,
    loop_momentum_squared: Expression | None = None,
) -> Expression | None:
    momentum_squared = s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared
    momentum_coefficient = _coefficient_of_momentum_power(expr, momentum_squared, 1)
    if momentum_coefficient is None:
        return None
    if not bool(momentum_coefficient == Expression.num(1)):
        return None
    if _has_unsupported_momentum_powers(expr, momentum_squared):
        return None
    constant = _coefficient_of_momentum_power(expr, momentum_squared, 0)
    mass_squared = Expression.num(0) if constant is None else (-constant).expand()
    return s.PropagatorDenominator(momentum_squared, mass_squared)


def _fermion_momentum_entry_propagator_denominator(
    expr: Expression,
    *,
    loop_momentum_squared: Expression | None = None,
) -> Expression | None:
    momentum_squared = s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared
    marker = s.FermionSlashMomentumMarker
    marked = expr.replace_multiple(_fermion_slash_momentum_replacements(marker)).expand()
    momentum_coefficient = _coefficient_of_momentum_power(marked, marker, 1)
    if momentum_coefficient is None:
        return None
    if not (bool(momentum_coefficient == Expression.num(1)) or bool(momentum_coefficient == -Expression.num(1))):
        return None
    if _has_unsupported_momentum_powers(marked, marker):
        return None
    constant = _coefficient_of_momentum_power(marked, marker, 0)
    mass = Expression.num(0) if constant is None else constant.expand()
    return s.PropagatorDenominator(momentum_squared, (mass**2).expand())


def _fermion_slash_momentum_replacements(marker: Expression) -> tuple[Replacement, ...]:
    index = s.LoopMomentumIndexWildcard
    return (
        Replacement(s.Gamma(index) * s.LoopMomentum(index), marker),
        Replacement(s.DiracProduct(s.Gamma(index)) * s.LoopMomentum(index), marker),
    )


def _fermion_registered_free_inverse_part(
    expr: Expression,
    *,
    expected_mass_squared: Expression | None = None,
    loop_momentum_squared: Expression | None = None,
) -> Expression | None:
    free_part = _field_independent_part(expr)
    denominator = _fermion_momentum_entry_propagator_denominator(
        free_part,
        loop_momentum_squared=loop_momentum_squared,
    )
    if denominator is None:
        return None
    if expected_mass_squared is not None and not is_zero((denominator[1] - expected_mass_squared).expand()):
        return None
    return free_part.expand()


def _propagator_denominator_mass_squared(denominator: Expression) -> Expression:
    if not is_head(denominator, s.PropagatorDenominator):
        raise ValueError(f"Expected PropagatorDenominator, got {canonical_string(denominator)}")
    return denominator[1]


def _propagator_denominator_inverse_expression(denominator: Expression) -> Expression:
    if not is_head(denominator, s.PropagatorDenominator):
        raise ValueError(f"Expected PropagatorDenominator, got {canonical_string(denominator)}")
    return (denominator[0] - denominator[1]).expand()


def _conjugate_fluctuation_field(field: Expression) -> Expression:
    return bar_field_inner(field) if is_bar_field(field) else s.Bar(field)


def _free_inverse_column_keys(mode: FluctuationMode) -> set[str]:
    if mode.self_conjugate:
        return {canonical_string(mode.field)}
    return {canonical_string(_conjugate_fluctuation_field(mode.field))}


def _coefficient_of_momentum_power(expr: Expression, momentum_squared: Expression, power: int) -> Expression | None:
    if power == 0:
        target = Expression.num(1)
    elif power == 1:
        target = momentum_squared
    else:
        target = momentum_squared**power
    for key, coefficient in expr.coefficient_list(momentum_squared):
        if bool(key == target):
            return coefficient.expand()
    return None


def _has_unsupported_momentum_powers(expr: Expression, momentum_squared: Expression) -> bool:
    for key, coefficient in expr.coefficient_list(momentum_squared):
        if is_zero(coefficient):
            continue
        if bool(key == Expression.num(1)) or bool(key == momentum_squared):
            continue
        return True
    return False


def _has_registered_free_inverse_part(
    expr: Expression,
    expected_mass_squared: Expression,
    *,
    loop_momentum_squared: Expression | None = None,
) -> bool:
    momentum_squared = s.LoopMomentumSquared if loop_momentum_squared is None else loop_momentum_squared
    if _has_unsupported_momentum_powers(expr, momentum_squared):
        return False
    momentum_coefficient = _coefficient_of_momentum_power(expr, momentum_squared, 1)
    if momentum_coefficient is None:
        return False
    free_momentum_coefficient = _field_independent_part(momentum_coefficient)
    if not bool(free_momentum_coefficient == Expression.num(1)):
        return False
    constant = _coefficient_of_momentum_power(expr, momentum_squared, 0)
    free_constant = Expression.num(0) if constant is None else _field_independent_part(constant)
    return is_zero((free_constant + expected_mass_squared).expand())


def _field_independent_part(expr: Expression) -> Expression:
    field_label_is_tagged = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    field_strength_label_is_tagged = s.FieldStrengthLabelWildcard.req_tag(SymbolRole.FIELD.value)
    return expr.replace_multiple(
        (
            Replacement(bar_field_pattern(), Expression.num(0), field_label_is_tagged),
            Replacement(field_pattern(), Expression.num(0), field_label_is_tagged),
            Replacement(field_strength_pattern(), Expression.num(0), field_strength_label_is_tagged),
        )
    ).expand()


def _contracted_derivative_pair_power(derivatives: tuple[Expression, ...]) -> int | None:
    if len(derivatives) % 2 != 0:
        return None
    for left, right in zip(derivatives[::2], derivatives[1::2], strict=True):
        if not bool(left == right):
            return None
    return len(derivatives) // 2


def _same_expression_sequence(left: tuple[Expression, ...], right: tuple[Expression, ...]) -> bool:
    return len(left) == len(right) and all(bool(left_item == right_item) for left_item, right_item in zip(left, right))


def _same_field_label(left: Expression, right: Expression) -> bool:
    left_base = bar_field_inner(left) if is_bar_field(left) else left
    right_base = bar_field_inner(right) if is_bar_field(right) else right
    return bool(field_label(left_base) == field_label(right_base))


def _field_definition_from_label(theory: Theory, label: Expression) -> FieldDefinition:
    key = canonical_string(label)
    for definition in theory.fields.values():
        if canonical_string(definition.label) == key:
            return definition
    raise KeyError(f"Theory {theory.name!r} has no field label {key!r}")


def _validate_unique_fluctuation_basis(basis: tuple[Expression, ...]) -> None:
    keys = [canonical_string(field) for field in basis]
    if len(set(keys)) != len(keys):
        raise ValueError("fluctuation basis fields must be unique")


def _discover_fluctuation_basis(lagrangian: Expression) -> tuple[Expression, ...]:
    cond = s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value)
    entries: dict[str, Expression] = {}
    for pattern in (bar_field_pattern(), field_pattern()):
        for match in lagrangian.match(pattern, cond):
            _add_discovered_fluctuation(entries, pattern.replace_wildcards(match))
    strength_pattern = field_strength_pattern()
    for match in lagrangian.match(strength_pattern, s.FieldStrengthLabelWildcard.req_tag(SymbolRole.FIELD.value)):
        _add_discovered_fluctuation(entries, _field_strength_fluctuation_field(match))
    return tuple(entries[key] for key in sorted(entries))


def _field_strength_fluctuation_field(match: dict[Expression, Expression]) -> Expression:
    label = match[s.FieldStrengthLabelWildcard]
    return s.Field(
        label,
        field_type_from_label(label),
        match[s.FieldStrengthIndicesWildcard],
        s.List(),
    )


def _add_discovered_fluctuation(entries: dict[str, Expression], expr: Expression) -> None:
    field = bar_field_inner(expr) if is_bar_field(expr) else expr
    base = field_with_derivatives(field, ())
    if not field_propagating_from_label(field_label(base)):
        return
    if field_self_conjugate_from_label(field_label(base)):
        _add_basis_entry(entries, base)
        return
    _add_basis_entry(entries, s.Bar(base))
    _add_basis_entry(entries, base)


def _add_basis_entry(entries: dict[str, Expression], field: Expression) -> None:
    entries.setdefault(canonical_string(field), field)


def _fluctuation_mode(theory: Theory, field: Expression) -> FluctuationMode:
    base = bar_field_inner(field) if is_bar_field(field) else field
    label = field_label(base)
    if not field_propagating_from_label(label):
        raise ValueError(f"Non-propagating field {canonical_string(field)!r} cannot be used as a fluctuation mode")
    field_type = field_type_from_label(label)
    field_role = field_role_from_label(label)
    return FluctuationMode(
        theory=theory,
        field=field,
        base_field=base,
        field_type=field_type,
        field_role=field_role,
        mass_kind=field_mass_kind_from_label(label),
        statistics=_fluctuation_statistics(field_type, field_role),
        self_conjugate=field_self_conjugate_from_label(label),
        conjugated=is_bar_field(field),
    )


def _fluctuation_propagator(mode: FluctuationMode) -> FluctuationPropagator:
    mass = mode.mass
    if mode.is_heavy and mass is None:
        raise ValueError(f"Heavy fluctuation field {canonical_string(mode.field)!r} has no mass symbol data")
    mass_squared = None if mass is None else mass**2
    return FluctuationPropagator(
        theory=mode.theory,
        mode=mode,
        mass=mass,
        mass_squared=mass_squared,
    )


def _fluctuation_mass_squared(mode: FluctuationMode) -> Expression:
    return Expression.num(0) if mode.mass_squared is None else mode.mass_squared


def _postprocess_bosonic_cde_numerator(
    theory: Theory,
    numerator: Expression,
    *,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    expand_covariant_derivative_commutators: bool,
    covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
) -> Expression:
    if emit_covariant_derivative_commutators:
        numerator = theory.emit_covariant_derivative_commutators(
            numerator,
            max_passes=emit_covariant_derivative_commutator_passes,
            mode=covariant_derivative_commutator_mode,
        )
    if expand_covariant_derivative_commutators:
        numerator = theory.expand_covariant_derivative_commutators(
            numerator,
            include_gauge_coupling=False,
        )
    return simplify_trivial_cd_operators(numerator)


def _wilson_line_propagator_expansion_terms(
    theory: Theory,
    mode: FluctuationMode,
    indices: Sequence[Expression],
    *,
    trace_name: str,
    path_index: int,
    slot_index: int,
) -> tuple[CovariantPropagatorExpansionTerm, ...]:
    if mode.statistics is not FluctuationStatistics.FERMIONIC:
        terms = bosonic_covariant_propagator_expansion_terms(indices)
        if not _is_vector_field_type(mode.field_type):
            return terms
        return tuple(
            CovariantPropagatorExpansionTerm(
                prefactor=-term.prefactor,
                loop_momentum_numerator=term.loop_momentum_numerator,
                open_cd_operands=term.open_cd_operands,
                denominator_power=term.denominator_power,
                loop_momentum_indices=term.loop_momentum_indices,
            )
            for term in terms
        )
    prefix = safe_symbol_name(f"{trace_name}_{path_index}_{slot_index}")
    return fermionic_covariant_propagator_expansion_terms(
        Expression.num(0) if mode.mass is None else mode.mass,
        indices,
        slash_index=theory.lorentz_index(f"{prefix}_slash"),
        derivative_index=theory.lorentz_index(f"{prefix}_derivative"),
    )


def _is_vector_field_type(field_type: Expression) -> bool:
    return bool(field_type == s.Vector) or is_head(field_type, s.Vector)


def _wilson_line_link_indices(theory: Theory, trace_name: str, path_index: int) -> tuple[Expression, Expression]:
    trace_key = safe_symbol_name(trace_name)
    return (
        theory.symbol(f"wilson_line_{trace_key}_{path_index}_left", role=SymbolRole.INDEX),
        theory.symbol(f"wilson_line_{trace_key}_{path_index}_right", role=SymbolRole.INDEX),
    )


def _wilson_line_expansion_term_metadata(
    grouped_terms: Mapping[str, Sequence[WilsonLineTraceExpansionTerm]],
) -> dict[str, Any]:
    count_by_entry: dict[str, int] = {}
    count_by_trace: dict[str, int] = {}
    count_by_entry_path: dict[str, dict[str, int]] = {}
    weighted_count_by_entry: dict[str, int] = {}
    weighted_count_by_entry_path: dict[str, dict[str, int]] = {}
    nonzero_entries: list[str] = []
    weighted_term_count = 0
    for entry_label, terms in grouped_terms.items():
        term_count = len(terms)
        trace_name = terms[0].trace_name if terms else _wilson_line_trace_name_from_entry_label(entry_label)
        count_by_entry[entry_label] = term_count
        count_by_trace[trace_name] = count_by_trace.get(trace_name, 0) + term_count
        if term_count:
            nonzero_entries.append(entry_label)
        path_counts: dict[str, int] = {}
        weighted_path_counts: dict[str, int] = {}
        weighted_entry_count = 0
        for term in terms:
            path_key = str(term.path_index)
            path_counts[path_key] = path_counts.get(path_key, 0) + 1
            weighted_path_counts[path_key] = weighted_path_counts.get(path_key, 0) + term.component_weight
            weighted_entry_count += term.component_weight
        weighted_term_count += weighted_entry_count
        count_by_entry_path[entry_label] = dict(sorted(path_counts.items(), key=lambda item: int(item[0])))
        weighted_count_by_entry[entry_label] = weighted_entry_count
        weighted_count_by_entry_path[entry_label] = dict(
            sorted(weighted_path_counts.items(), key=lambda item: int(item[0]))
        )
    return {
        "interaction_wilson_line_term_count_by_entry": count_by_entry,
        "interaction_wilson_line_term_count_by_trace": dict(sorted(count_by_trace.items())),
        "interaction_wilson_line_term_count_by_entry_path": count_by_entry_path,
        "interaction_wilson_line_component_weighted_term_count": weighted_term_count,
        "interaction_wilson_line_component_weighted_term_count_by_entry": weighted_count_by_entry,
        "interaction_wilson_line_component_weighted_term_count_by_entry_path": weighted_count_by_entry_path,
        "interaction_wilson_line_nonzero_plan_entries": tuple(nonzero_entries),
        "interaction_wilson_line_empty_plan_entry_count": sum(1 for count in count_by_entry.values() if count == 0),
    }


def _metadata_wilson_line_total_orders_by_trace(value: Mapping[str, Sequence[int]] | None) -> str | None:
    if value is None:
        return None
    return ";".join(
        f"{trace_name}:{','.join(str(order) for order in value[trace_name])}" for trace_name in sorted(value)
    )


def _activate_wilson_line_internal_through_finite_source(result: MatchingResult) -> MatchingResult:
    """Use Matchete's epsilon-expanded Wilson-line source for public follow-up stages."""

    source_names = (
        "interaction_wilson_line_normalized_hybrid_internal_integral_through_finite_part",
        "interaction_wilson_line_normalized_internal_integral_through_finite_part",
        "interaction_wilson_line_hybrid_internal_integral_through_finite_part",
        "interaction_wilson_line_internal_integral_through_finite_part",
    )
    for source_name in source_names:
        if source_name not in result.supertraces:
            continue
        through_finite = result.supertraces[source_name]
        return replace(
            result,
            off_shell_eft_lagrangian=through_finite,
            on_shell_eft_lagrangian=through_finite,
            supertraces={
                **result.supertraces,
                "off_shell_eft_lagrangian_before_wilson_line_internal_through_finite_activation": (
                    result.off_shell_eft_lagrangian
                ),
                "on_shell_eft_lagrangian_before_wilson_line_internal_through_finite_activation": (
                    result.on_shell_eft_lagrangian
                ),
                "off_shell_eft_lagrangian_after_wilson_line_internal_through_finite_activation": through_finite,
                "on_shell_eft_lagrangian_after_wilson_line_internal_through_finite_activation": through_finite,
            },
            metadata={
                **result.metadata,
                "wilson_line_internal_through_finite_source_activated": True,
                "wilson_line_internal_through_finite_source": source_name,
            },
        )
    return replace(
        result,
        metadata={
            **result.metadata,
            "wilson_line_internal_through_finite_source_activated": False,
            "wilson_line_internal_through_finite_source": None,
        },
    )


def _component_weighted_wilson_line_terms(
    path: WilsonLineTracePath,
    terms: Sequence[WilsonLineTraceExpansionTerm],
) -> tuple[WilsonLineTraceExpansionTerm, ...]:
    """Scale label-level Wilson-line terms by Matchete-style component multiplicity."""

    if not terms:
        return ()
    weight = wilson_line_path_component_weight(path)
    if weight is None:
        raise ValueError(
            "Cannot apply Wilson-line component-DOF path weighting because at least "
            f"one internal dimension in path {path.trace_name}[{path.path_index}] is unknown"
        )
    if weight == 1:
        return tuple(terms)
    factor = Expression.num(weight)
    return tuple(
        replace(
            term,
            numerator=factor * term.numerator,
            pre_wilson_numerator=(
                None
                if term.pre_wilson_numerator is None
                else factor * term.pre_wilson_numerator
            ),
            component_weight=term.component_weight * weight,
        )
        for term in terms
    )


def _collected_wilson_line_terms_for_entry(
    entry: WilsonLineExpansionPlanEntry,
    paths: Sequence[WilsonLineTracePath],
    *,
    weight_paths_by_component_dofs: bool,
    act_open_derivatives: bool,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode,
    expand_covariant_derivative_commutators: bool,
    max_wilson_derivative_order: int,
    simplify_pychete_color_algebra: bool,
    term_atom_requirements: ProjectionAtomRequirementGroups | None,
) -> tuple[WilsonLineTraceExpansionTerm, ...]:
    """Generate terms by collecting equivalent raw Wilson-line path sums first."""

    groups: dict[
        tuple[tuple[str, ...], tuple[int, ...], tuple[str, ...], bool],
        list[_WilsonLineRawExpansionTerm],
    ] = {}
    for path in paths:
        if not _wilson_line_entry_can_satisfy_projection_requirements(path, entry, term_atom_requirements):
            continue
        filtered_path = _wilson_line_path_with_projection_filtered_entries(path, term_atom_requirements)
        raw_terms = filtered_path.raw_propagator_expansion_terms(entry.expansion_indices)
        if weight_paths_by_component_dofs:
            raw_terms = _component_weighted_raw_wilson_line_terms(filtered_path, raw_terms)
        for raw_term in raw_terms:
            key = _raw_wilson_line_collection_key(raw_term)
            groups.setdefault(key, []).append(raw_term)

    terms: list[WilsonLineTraceExpansionTerm] = []
    for raw_terms in groups.values():
        collected = _collect_raw_wilson_line_terms(raw_terms)
        term = _postprocess_wilson_line_raw_expansion_term(
            collected,
            act_open_derivatives=act_open_derivatives,
            emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
            covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
            expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
            max_wilson_derivative_order=max_wilson_derivative_order,
            simplify_pychete_color_algebra=simplify_pychete_color_algebra,
        )
        if term is not None:
            terms.append(term)
    return tuple(terms)


def _component_weighted_raw_wilson_line_terms(
    path: WilsonLineTracePath,
    terms: Sequence[_WilsonLineRawExpansionTerm],
) -> tuple[_WilsonLineRawExpansionTerm, ...]:
    if not terms:
        return ()
    weight = wilson_line_path_component_weight(path)
    if weight is None:
        raise ValueError(
            "Cannot apply Wilson-line component-DOF path weighting because at least "
            f"one internal dimension in path {path.trace_name}[{path.path_index}] is unknown"
        )
    if weight == 1:
        return tuple(terms)
    factor = Expression.num(weight)
    return tuple(
        replace(
            term,
            numerator_before_open_cd=factor * term.numerator_before_open_cd,
            component_weight=term.component_weight * weight,
        )
        for term in terms
    )


def _raw_wilson_line_collection_key(
    term: _WilsonLineRawExpansionTerm,
) -> tuple[tuple[str, ...], tuple[int, ...], tuple[str, ...], bool]:
    return (
        tuple(canonical_string(mass_squared) for mass_squared in term.mass_squareds),
        term.propagator_powers,
        tuple(canonical_string(index) for index in term.loop_momentum_indices),
        term.close_fermion_loop,
    )


def _collect_raw_wilson_line_terms(
    terms: Sequence[_WilsonLineRawExpansionTerm],
) -> _WilsonLineRawExpansionTerm:
    if not terms:
        raise ValueError("Cannot collect an empty Wilson-line raw-term group")
    first = terms[0]
    return replace(
        first,
        path_index=-1,
        numerator_before_open_cd=sum_expr(term.numerator_before_open_cd for term in terms).expand(),
        component_weight=sum(term.component_weight for term in terms),
    )


def _wilson_line_path_term_cache_key(
    path: WilsonLineTracePath,
    entry: WilsonLineExpansionPlanEntry,
) -> tuple[str, tuple[tuple[str, ...], ...], str] | None:
    """Return a conservative cache key for bosonic Wilson-line path templates."""

    if any(mode.statistics is FluctuationStatistics.FERMIONIC for mode in path.propagator_modes):
        return None
    path_key_parts = (
        canonical_string(path.prefactor),
        canonical_string(path.closing_field_label),
        tuple(canonical_string(path_entry) for path_entry in path.entries),
        tuple(canonical_string(mode.field) for mode in path.propagator_modes),
        tuple(canonical_string(mode.field) for mode in path.propagation_target_modes),
    )
    return (
        path.trace_name,
        tuple(tuple(canonical_string(index) for index in slot) for slot in entry.expansion_indices),
        repr(path_key_parts),
    )


def _clone_wilson_line_terms_for_path(
    terms: Sequence[WilsonLineTraceExpansionTerm],
    source_path: WilsonLineTracePath,
    target_path: WilsonLineTracePath,
) -> tuple[WilsonLineTraceExpansionTerm, ...]:
    """Clone cached bosonic Wilson-line terms onto another equivalent path."""

    replacements = [
        Replacement(source_index, target_index)
        for source_index, target_index in zip(source_path.link_indices, target_path.link_indices, strict=True)
        if not bool(source_index == target_index)
    ]

    def remap(expr: Expression | None) -> Expression | None:
        if expr is None or not replacements:
            return expr
        return expr.replace_multiple(replacements)

    def remap_required(expr: Expression) -> Expression:
        if not replacements:
            return expr
        return expr.replace_multiple(replacements)

    return tuple(
        replace(
            term,
            path_index=target_path.path_index,
            numerator=remap_required(term.numerator),
            pre_wilson_numerator=remap(term.pre_wilson_numerator),
        )
        for term in terms
    )


def _combine_bosonic_cde_hybrid_results(
    interaction_remainder: MatchingResult,
    cde_result: MatchingResult,
    *,
    stage: str,
    selected_trace_names: tuple[str, ...],
    aggregate_expression_names: Iterable[str],
) -> MatchingResult:
    return _combine_interaction_expansion_hybrid_results(
        interaction_remainder,
        cde_result,
        stage=stage,
        selected_trace_names=selected_trace_names,
        aggregate_expression_names=aggregate_expression_names,
        metadata_prefix="interaction_bosonic_cde",
        expansion_flag_name="uses_bosonic_cde_expansion",
        hybrid_flag_name="interaction_bosonic_cde_hybrid",
    )


def _combine_interaction_expansion_hybrid_results(
    interaction_remainder: MatchingResult,
    expansion_result: MatchingResult,
    *,
    stage: str,
    selected_trace_names: tuple[str, ...],
    aggregate_expression_names: Iterable[str],
    metadata_prefix: str,
    expansion_flag_name: str,
    hybrid_flag_name: str,
) -> MatchingResult:
    off_shell = (interaction_remainder.off_shell_eft_lagrangian + expansion_result.off_shell_eft_lagrangian).expand()
    on_shell = (interaction_remainder.on_shell_eft_lagrangian + expansion_result.on_shell_eft_lagrangian).expand()
    aggregate_supertraces = {name: off_shell for name in aggregate_expression_names}
    return MatchingResult(
        theory=expansion_result.theory,
        uv_lagrangian=expansion_result.uv_lagrangian,
        off_shell_eft_lagrangian=off_shell,
        on_shell_eft_lagrangian=on_shell,
        matching_conditions={
            **interaction_remainder.matching_conditions,
            **expansion_result.matching_conditions,
        },
        fluctuation_operators={
            **interaction_remainder.fluctuation_operators,
            **expansion_result.fluctuation_operators,
        },
        supertraces={
            **interaction_remainder.supertraces,
            **expansion_result.supertraces,
            **aggregate_supertraces,
        },
        metadata={
            **interaction_remainder.metadata,
            **expansion_result.metadata,
            "stage": stage,
            "complete": False,
            "on_shell_reduced": False,
            "uses_interaction_operator": True,
            expansion_flag_name: True,
            "uses_interaction_power_remainder": True,
            hybrid_flag_name: True,
            f"{metadata_prefix}_replaced_trace_names": ",".join(selected_trace_names),
            f"{metadata_prefix}_replaced_trace_count": len(selected_trace_names),
            "interaction_power_type_component_stage": interaction_remainder.metadata.get("stage"),
            f"{metadata_prefix}_component_stage": expansion_result.metadata.get("stage"),
            "interaction_power_type_remainder_contribution_count": interaction_remainder.metadata.get(
                "interaction_power_type_contribution_count"
            ),
        },
    )


def _flatten_expression_slots(slots: Iterable[Iterable[Expression]]) -> tuple[Expression, ...]:
    return tuple(item for slot in slots for item in slot)


def _flatten_wilson_line_terms(
    grouped_terms: Mapping[str, Sequence[WilsonLineTraceExpansionTerm]],
) -> tuple[WilsonLineTraceExpansionTerm, ...]:
    return tuple(term for terms in grouped_terms.values() for term in terms)


def _wilson_line_kernel_expression_map_from_terms(
    grouped_terms: Mapping[str, Sequence[WilsonLineTraceExpansionTerm]],
    *,
    prefix: str = "interaction_wilson_line_expansion_kernel",
    loop_momentum_squared: Expression | None = None,
) -> dict[str, Expression]:
    entries: dict[str, Expression] = {}
    for trace_name, terms in grouped_terms.items():
        for term_index, term in enumerate(terms):
            entries[f"{prefix}[{trace_name},{term.path_index},{term_index}]"] = term.kernel_expression(
                loop_momentum_squared=loop_momentum_squared,
            )
    return entries


def _wilson_line_vakint_integral_expression_map_from_terms(
    grouped_terms: Mapping[str, Sequence[WilsonLineTraceExpansionTerm]],
    *,
    prefix: str = "interaction_wilson_line_expansion_vakint_integral",
) -> dict[str, Expression]:
    entries: dict[str, Expression] = {}
    for trace_name, terms in grouped_terms.items():
        for term_index, term in enumerate(terms):
            entries[f"{prefix}[{trace_name},{term.path_index},{term_index}]"] = term.vakint_integral_expression()
    return entries


def _wilson_line_raw_integral_sum_from_expressions(expressions: Iterable[Expression]) -> Expression:
    return sum_expr(expressions).expand()


def _fluctuation_statistics(field_type: Expression, field_role: FieldRole) -> FluctuationStatistics:
    grassmann_roles = {FieldRole.GHOST, FieldRole.ANTI_GHOST}
    if bool(field_type == s.Fermion) or field_role in grassmann_roles:
        return FluctuationStatistics.FERMIONIC
    return FluctuationStatistics.BOSONIC


def _mode_spin_lorentz_dimension(
    field_type: Expression,
    chirality: FieldChirality,
    field_role: FieldRole,
) -> int | None:
    if field_role in {FieldRole.GHOST, FieldRole.ANTI_GHOST}:
        return 1
    if bool(field_type == s.Scalar):
        return 1
    if bool(field_type == s.Fermion):
        return 2 if chirality in {FieldChirality.LEFT, FieldChirality.RIGHT} else 4
    if bool(field_type == s.Vector) or is_head(field_type, s.Vector):
        return None
    return None


def _mode_index_representation_dimension(theory: Theory, representation: Expression) -> int | None:
    try:
        return theory.representation_dimension(representation)
    except KeyError:
        dimension = symbol_data(representation, SymbolDataKey.DIMENSION)
        if dimension is None:
            return None
        dimension_value = int(dimension)
        return dimension_value if dimension_value >= 0 else None


def _mode_index(modes: tuple[FluctuationMode, ...], field: Expression) -> int:
    key = canonical_string(field)
    for index, mode in enumerate(modes):
        if canonical_string(mode.field) == key:
            return index
    raise KeyError(f"Fluctuation basis has no field {key!r}")


def _supertrace_category_labels(modes: tuple[FluctuationMode, ...]) -> tuple[str, ...]:
    labels: dict[str, None] = {}
    for mode in sorted(modes, key=_mode_supertrace_category_sort_key):
        labels.setdefault(mode.supertrace_category, None)
    return tuple(labels)


def _mode_supertrace_category_sort_key(mode: FluctuationMode) -> tuple[int, int, str]:
    sector_order = 0 if mode.is_heavy else 1
    return (sector_order, _mode_supertrace_type_order(mode), canonical_string(mode.field))


def _mode_supertrace_type_order(mode: FluctuationMode) -> int:
    type_name = _mode_supertrace_type_name(mode)
    order = {
        "Scalar": 0,
        "Fermion": 1,
        "Vector": 2,
        "Ghost": 3,
        "AntiGhost": 4,
    }
    return order.get(type_name, 99)


def _mode_supertrace_category(mode: FluctuationMode) -> str:
    prefix = "h" if mode.is_heavy else "l"
    return f"{prefix}{_mode_supertrace_type_name(mode)}"


def _mode_supertrace_type_name(mode: FluctuationMode) -> str:
    field_type = mode.field_type
    if bool(field_type == s.Scalar):
        return "Scalar"
    if bool(field_type == s.Fermion):
        return "Fermion"
    if bool(field_type == s.Ghost):
        return "Ghost"
    if bool(field_type == s.AntiGhost):
        return "AntiGhost"
    if bool(field_type == s.Vector) or is_head(field_type, s.Vector):
        return "Vector"
    return "Unknown"


def _supertrace_category_sector(label: str) -> FluctuationSector:
    if label.startswith("h"):
        return FluctuationSector.HEAVY
    if label.startswith("l"):
        return FluctuationSector.LIGHT
    raise ValueError(f"Unknown supertrace category label {label!r}")


def _category_indices(modes: tuple[FluctuationMode, ...], label: str) -> tuple[int, ...]:
    indices = tuple(index for index, mode in enumerate(modes) if mode.supertrace_category == label)
    if not indices:
        raise ValueError(f"Fluctuation basis has no {label!r} modes")
    return indices


def _cyclically_unique_traces(traces: Iterable[SupertraceBlockTrace]) -> tuple[SupertraceBlockTrace, ...]:
    unique: list[SupertraceBlockTrace] = []
    seen: set[tuple[str, ...]] = set()
    for trace in traces:
        if trace.cyclic_sector_key in seen:
            continue
        seen.add(trace.cyclic_sector_key)
        unique.append(trace)
    return tuple(unique)


def _selected_power_type_trace_names(
    modes: tuple[FluctuationMode, ...],
    *,
    max_trace_order: int,
    trace_names: Sequence[str],
    include_light_only: bool = False,
) -> tuple[str, ...]:
    requested = tuple(dict.fromkeys(trace_names))
    if not requested:
        return ()
    valid_names = _power_type_trace_names(
        modes,
        max_trace_order=max_trace_order,
        include_light_only=include_light_only,
    )
    valid_name_set = set(valid_names)
    for name in requested:
        if name not in valid_name_set:
            raise KeyError(f"One-loop setup has no interaction trace {name!r}")
    return requested


def _power_type_trace_names(
    modes: tuple[FluctuationMode, ...],
    *,
    max_trace_order: int,
    include_light_only: bool = False,
) -> tuple[str, ...]:
    names: list[str] = []
    seen: set[tuple[str, ...]] = set()
    labels = _supertrace_category_labels(modes)
    for order in range(1, max_trace_order + 1):
        for path in product(labels, repeat=order):
            light_only = all(_supertrace_category_sector(label) is FluctuationSector.LIGHT for label in path)
            if not include_light_only and light_only:
                continue
            key = _cyclic_sector_key(path)
            if key in seen:
                continue
            seen.add(key)
            names.append("-".join(path))
    return tuple(names)


def _category_path_from_trace_name(name: str) -> tuple[str, ...]:
    path = tuple(part for part in name.split("-") if part)
    if not path:
        raise ValueError("interaction trace name must not be empty")
    return path


def _sector_indices(modes: tuple[FluctuationMode, ...], sector: FluctuationSector) -> tuple[int, ...]:
    if sector is FluctuationSector.ALL:
        return tuple(range(len(modes)))
    if sector is FluctuationSector.HEAVY:
        return tuple(index for index, mode in enumerate(modes) if mode.is_heavy)
    return tuple(index for index, mode in enumerate(modes) if mode.is_light)


def _validate_closed_block_chain(blocks: tuple[FluctuationOperatorBlock, ...]) -> None:
    for left, right in zip(blocks, blocks[1:], strict=False):
        if _mode_keys(left.columns) != _mode_keys(right.rows):
            raise ValueError("adjacent fluctuation blocks must have matching column and row modes")
    if _mode_keys(blocks[0].rows) != _mode_keys(blocks[-1].columns):
        raise ValueError("fluctuation block trace must form a closed mode chain")


def _mode_keys(modes: tuple[FluctuationMode, ...]) -> tuple[str, ...]:
    return tuple(canonical_string(mode.field) for mode in modes)


def _propagated_mode_key(mode: FluctuationMode) -> str:
    """Return the row-mode key reached after this mode's free propagator."""

    if mode.self_conjugate:
        return canonical_string(mode.field)
    return canonical_string(_conjugate_fluctuation_field(mode.field))


def _mode_index_by_key(modes: tuple[FluctuationMode, ...]) -> dict[str, int]:
    return {canonical_string(mode.field): index for index, mode in enumerate(modes)}


def _sector_path_name(path: tuple[FluctuationSector, ...]) -> str:
    return "-".join(sector.value for sector in path)


def _cyclic_sector_key(sectors: tuple[str, ...]) -> tuple[str, ...]:
    if not sectors:
        return ()
    rotations = tuple(sectors[index:] + sectors[:index] for index in range(len(sectors)))
    return min(rotations)


def _cyclic_orbit_size(labels: tuple[str, ...]) -> int:
    if not labels:
        return 0
    return len({labels[index:] + labels[:index] for index in range(len(labels))})


@dataclass(frozen=True)
class _SupertraceBlockEntryPath:
    sign: int
    entries: tuple[Expression, ...]
    next_modes: tuple[FluctuationMode, ...]
    propagation_target_modes: tuple[FluctuationMode, ...]


def _supertrace_block_entry_paths(blocks: tuple[FluctuationOperatorBlock, ...]) -> tuple[_SupertraceBlockEntryPath, ...]:
    if not blocks:
        return ()
    row_index_by_block = tuple(_mode_index_by_key(block.rows) for block in blocks)
    paths: list[_SupertraceBlockEntryPath] = []

    def visit(
        block_index: int,
        row_index: int,
        first_row_key: str,
        first_row_mode: FluctuationMode,
        first_sign: int,
        entries: tuple[Expression, ...],
        next_modes: tuple[FluctuationMode, ...],
        propagation_target_modes: tuple[FluctuationMode, ...],
    ) -> None:
        block = blocks[block_index]
        for column_index, column_mode in enumerate(block.columns):
            propagated_key = _propagated_mode_key(column_mode)
            next_entries = (*entries, block.matrix[row_index][column_index])
            next_path_modes = (*next_modes, column_mode)
            if block_index == len(blocks) - 1:
                if propagated_key != first_row_key:
                    continue
                paths.append(
                    _SupertraceBlockEntryPath(
                        sign=first_sign,
                        entries=next_entries,
                        next_modes=next_path_modes,
                        propagation_target_modes=(*propagation_target_modes, first_row_mode),
                    )
                )
                continue
            next_row_index = row_index_by_block[block_index + 1].get(propagated_key)
            if next_row_index is None:
                continue
            next_row_mode = blocks[block_index + 1].rows[next_row_index]
            visit(
                block_index + 1,
                next_row_index,
                first_row_key,
                first_row_mode,
                first_sign,
                next_entries,
                next_path_modes,
                (*propagation_target_modes, next_row_mode),
            )

    for row_index, mode in enumerate(blocks[0].rows):
        visit(
            0,
            row_index,
            canonical_string(mode.field),
            mode,
            mode.supertrace_sign,
            (),
            (),
            (),
        )
    return tuple(paths)


def _ncm_chain(*operands: Expression) -> Expression:
    kept = tuple(operand for operand in operands if not is_zero(operand) and not bool(operand == Expression.num(1)))
    if len(kept) != len(operands) and any(is_zero(operand) for operand in operands):
        return Expression.num(0)
    if not kept:
        return Expression.num(1)
    if len(kept) == 1:
        return kept[0]
    return s.NCM(*kept)


def _supertrace_block_product(blocks: tuple[FluctuationOperatorBlock, ...]) -> Expression:
    trace_modes = blocks[0].rows
    if not trace_modes or any(not block.rows or not block.columns for block in blocks):
        return Expression.num(0)
    try:
        return _supertrace_block_product_matrix(blocks)
    except ValueError as exc:
        if "rational polynomial" not in str(exc):
            raise
        return _supertrace_block_product_expression(blocks)


def _supertrace_block_product_matrix(blocks: tuple[FluctuationOperatorBlock, ...]) -> Expression:
    trace_modes = blocks[0].rows
    product = _block_matrix(blocks[0])
    for block, next_block in zip(blocks, blocks[1:], strict=False):
        product = product @ _propagation_matrix(block.columns, next_block.rows)
        product = product @ _block_matrix(next_block)
    product = product @ _propagation_matrix(blocks[-1].columns, blocks[0].rows)
    out = Expression.num(0)
    for index, mode in enumerate(trace_modes):
        out = out + Expression.num(mode.supertrace_sign) * product[index, index].to_expression()
    return out.expand()


def _propagation_matrix(columns: tuple[FluctuationMode, ...], rows: tuple[FluctuationMode, ...]) -> Matrix:
    row_key_to_indices: dict[str, list[int]] = {}
    for row_index, mode in enumerate(rows):
        row_key_to_indices.setdefault(canonical_string(mode.field), []).append(row_index)
    matrix: list[list[Expression]] = []
    for column in columns:
        matrix_row = [Expression.num(0) for _ in rows]
        for row_index in row_key_to_indices.get(_propagated_mode_key(column), ()):
            matrix_row[row_index] = Expression.num(1)
        matrix.append(matrix_row)
    return Matrix.from_nested(tuple(tuple(row) for row in matrix))


def _supertrace_block_product_expression(blocks: tuple[FluctuationOperatorBlock, ...]) -> Expression:
    return sum_expr(
        Expression.num(path.sign) * product_expr(path.entries)
        for path in _supertrace_block_entry_paths(blocks)
    ).expand()


def _block_matrix(block: FluctuationOperatorBlock) -> Matrix:
    return Matrix.from_nested(block.matrix)


def match_one_loop(
    theory: Theory,
    lagrangian: Expression,
    *,
    eft_order: int = 6,
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
) -> MatchingResult:
    """Run the current internal-analytic one-loop matching pipeline.

    This returns an explicitly incomplete minimal-subtraction preview built
    from the interaction-only fluctuation operator and pychete's internal
    analytic scalar vacuum-integral backend unless ``one_loop_options`` selects
    a different preview backend. The result metadata carries ``complete=False``
    until the remaining Matchete-level matching stages are implemented and
    validated. Requested matching conditions are projected from the selected
    result expression stage with native Symbolica coefficient extraction.
    """

    theory._validate_registered_expression(lagrangian)
    options = one_loop_options or OneLoopMatchOptions()
    selected_backend = OneLoopIntegralBackend.from_user(options.integral_backend)
    normalization_label = one_loop_normalization_label(options.normalization)
    _LOGGER.info(
        (
            "running one-loop match for %s "
            "(backend=%s, normalization=%s, eft_order=%s, max_trace_order=%s)"
        ),
        theory.name,
        selected_backend.value,
        normalization_label,
        eft_order,
        options.max_trace_order,
    )
    matching_lagrangian = lagrangian
    if options.expand_abelian_covariant_derivatives:
        matching_lagrangian = theory.expand_abelian_covariant_derivatives(matching_lagrangian)
    if options.expand_non_abelian_covariant_derivatives:
        matching_lagrangian = theory.expand_non_abelian_covariant_derivatives(matching_lagrangian)
    if options.emit_covariant_derivative_commutators:
        matching_lagrangian = theory.emit_covariant_derivative_commutators(
            matching_lagrangian,
            max_passes=options.emit_covariant_derivative_commutator_passes,
        )
    if options.expand_covariant_derivative_commutators:
        matching_lagrangian = theory.expand_covariant_derivative_commutators(matching_lagrangian)
    heavy_scalar_solutions: dict[str, HeavyScalarSolution] | None = None
    if options.substitute_heavy_scalar_solutions:
        solution_lagrangian = (
            options.heavy_scalar_solution_lagrangian
            if options.heavy_scalar_solution_lagrangian is not None
            else matching_lagrangian
        )
        theory._validate_registered_expression(solution_lagrangian)
        heavy_scalar_solutions = solve_heavy_scalar_eoms(theory, solution_lagrangian, eft_order=eft_order)
    if options.wilson_line_weight_paths_by_component_dofs and not options.use_matchete_fluctuation_dof_basis:
        raise ValueError(
            "wilson_line_weight_paths_by_component_dofs requires "
            "use_matchete_fluctuation_dof_basis in the public one-loop route"
        )
    setup_fluctuation_fields: FluctuationBasis | Iterable[FluctuationBasisItem] | None = None
    if options.use_matchete_fluctuation_dof_basis:
        _LOGGER.info("using Matchete-style label-level fluctuation DOF basis for %s", theory.name)
        setup_fluctuation_fields = matchete_fluctuation_dof_basis_fields(theory, matching_lagrangian)
    setup = one_loop_setup(
        theory,
        matching_lagrangian,
        eft_order=eft_order,
        max_trace_order=options.max_trace_order,
        include_light_only=options.include_light_only,
        fluctuation_fields=setup_fluctuation_fields,
        matchete_fluctuation_dof_basis=options.use_matchete_fluctuation_dof_basis,
        wilson_line_weight_paths_by_component_dofs=options.wilson_line_weight_paths_by_component_dofs,
    )
    if options.simplify_pychete_color_algebra:
        _LOGGER.info("simplifying one-loop pychete colour algebra for %s", theory.name)
        setup = setup.simplify_index_algebra(
            expand=False,
            gamma=False,
            color=False,
            pychete_color=True,
            metrics=False,
            dots=False,
        )
    tensor_network_cg_component_source: str | None = None
    if options.evaluate_tensor_networks:
        _LOGGER.info("evaluating one-loop tensor networks for %s", theory.name)
        tensor_network_cg_component_source = _one_loop_tensor_network_component_source(theory, options)
        setup = setup.evaluate_tensor_networks(
            library=options.tensor_network_library,
            cg_components_by_name=options.tensor_network_cg_components_by_name,
            builtin_cg_components=options.tensor_network_builtin_cg_components,
            native_hep_cg_builtins=options.tensor_network_native_hep_cg_builtins,
            symbolic_cg_components=options.tensor_network_symbolic_cg_components,
            function_library=options.tensor_network_function_library,
            n_steps=options.tensor_network_n_steps,
            mode=options.tensor_network_mode,
        )
    _LOGGER.info("building one-loop result for %s with %s backend", theory.name, selected_backend.value)
    cde_expansion_indices_by_trace: Any = options.bosonic_cde_expansion_indices_by_trace
    if cde_expansion_indices_by_trace is None and options.bosonic_cde_max_total_order is not None:
        cde_expansion_indices_by_trace = setup.interaction_bosonic_cde_expansion_plan(
            trace_names=options.bosonic_cde_trace_names,
            max_total_order=options.bosonic_cde_max_total_order,
            max_slot_order=options.bosonic_cde_max_slot_order,
            index_prefix=options.bosonic_cde_index_prefix,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
        )
    wilson_line_expansion_indices_by_trace: Any = options.wilson_line_expansion_indices_by_trace
    if wilson_line_expansion_indices_by_trace is None and options.wilson_line_max_total_order is not None:
        wilson_line_expansion_indices_by_trace = setup.interaction_wilson_line_expansion_plan(
            trace_names=options.wilson_line_trace_names,
            max_total_order=options.wilson_line_max_total_order,
            max_slot_order=options.wilson_line_max_slot_order,
            index_prefix=options.wilson_line_index_prefix,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
            include_light_only=options.include_light_only,
        )
    wilson_line_plan_filters_requested = bool(
        options.wilson_line_total_orders is not None
        or options.wilson_line_total_orders_by_trace is not None
        or options.wilson_line_entry_labels is not None
    )
    if wilson_line_plan_filters_requested:
        if not isinstance(wilson_line_expansion_indices_by_trace, WilsonLineExpansionPlan):
            raise ValueError(
                "wilson_line_total_orders, wilson_line_total_orders_by_trace, and wilson_line_entry_labels require "
                "a generated WilsonLineExpansionPlan"
            )
        wilson_line_expansion_indices_by_trace = wilson_line_expansion_indices_by_trace.filtered(
            total_orders=options.wilson_line_total_orders,
            total_orders_by_trace=options.wilson_line_total_orders_by_trace,
            labels=options.wilson_line_entry_labels,
        )
    if cde_expansion_indices_by_trace is not None and wilson_line_expansion_indices_by_trace is not None:
        raise ValueError("CDE and Wilson-line expansion options are mutually exclusive")
    cde_term_atom_requirements = (
        _term_atom_requirements_for_targets(theory, matching_condition_targets)
        if options.bosonic_cde_filter_terms_by_matching_targets and cde_expansion_indices_by_trace is not None
        else None
    )
    wilson_line_term_atom_requirements = (
        _term_atom_requirements_for_targets(
            theory,
            matching_condition_targets,
            heavy_scalar_solutions=heavy_scalar_solutions,
        )
        if options.wilson_line_filter_terms_by_matching_targets and wilson_line_expansion_indices_by_trace is not None
        else None
    )
    wilson_line_builder_expose_scalar_derivative_commutator_bilinears = bool(
        options.wilson_line_expose_scalar_derivative_commutator_bilinears
        and not options.wilson_line_expose_scalar_eom_terms
    )
    wilson_line_internal_tensor_reduce = bool(options.tensor_reduce or options.wilson_line_expose_scalar_eom_terms)
    wilson_line_include_unselected_traces = options.wilson_line_include_unselected_traces
    if wilson_line_expansion_indices_by_trace is not None and selected_backend is OneLoopIntegralBackend.INTERNAL:
        if wilson_line_include_unselected_traces:
            result = setup.interaction_wilson_line_hybrid_internal_matching_result(
                wilson_line_expansion_indices_by_trace,
                heavy_field_dimension=options.heavy_field_dimension,
                include_light=options.include_light,
                loop_momentum_squared=options.loop_momentum_squared,
                require_registered_mass=options.require_registered_mass,
                include_light_only=options.include_light_only,
                act_open_derivatives=options.wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=options.wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    options.wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    options.wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=(
                    options.wilson_line_expand_covariant_derivative_commutators
                ),
                max_wilson_derivative_order=options.wilson_line_max_derivative_order,
                tensor_reduce=wilson_line_internal_tensor_reduce,
                tensor_reduce_engine=options.tensor_reduce_engine,
                tensor_reduce_before_wilson_expand=(
                    options.wilson_line_tensor_reduce_before_wilson_expand
                ),
                max_pole_order=options.max_pole_order,
                epsilon=options.epsilon,
                mu_r_squared=options.mu_r_squared,
                combine_terms=options.combine_terms,
                simplify_pychete_color_algebra=options.simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_builder_expose_scalar_derivative_commutator_bilinears
                ),
                internal_evaluation_mode=options.wilson_line_internal_evaluation_mode,
                collect_path_sums=options.wilson_line_collect_path_sums,
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
        else:
            result = setup.interaction_wilson_line_internal_matching_result(
                wilson_line_expansion_indices_by_trace,
                loop_momentum_squared=options.loop_momentum_squared,
                require_registered_mass=options.require_registered_mass,
                include_light_only=options.include_light_only,
                act_open_derivatives=options.wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=options.wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    options.wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    options.wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=(
                    options.wilson_line_expand_covariant_derivative_commutators
                ),
                max_wilson_derivative_order=options.wilson_line_max_derivative_order,
                tensor_reduce=wilson_line_internal_tensor_reduce,
                tensor_reduce_engine=options.tensor_reduce_engine,
                tensor_reduce_before_wilson_expand=(
                    options.wilson_line_tensor_reduce_before_wilson_expand
                ),
                max_pole_order=options.max_pole_order,
                epsilon=options.epsilon,
                mu_r_squared=options.mu_r_squared,
                combine_terms=options.combine_terms,
                simplify_pychete_color_algebra=options.simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_builder_expose_scalar_derivative_commutator_bilinears
                ),
                internal_evaluation_mode=options.wilson_line_internal_evaluation_mode,
                collect_path_sums=options.wilson_line_collect_path_sums,
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
    elif (
        wilson_line_expansion_indices_by_trace is not None
        and selected_backend is OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION
    ):
        if wilson_line_include_unselected_traces:
            result = setup.interaction_wilson_line_hybrid_internal_minimal_subtraction_result(
                wilson_line_expansion_indices_by_trace,
                heavy_field_dimension=options.heavy_field_dimension,
                include_light=options.include_light,
                loop_momentum_squared=options.loop_momentum_squared,
                require_registered_mass=options.require_registered_mass,
                include_light_only=options.include_light_only,
                act_open_derivatives=options.wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=options.wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    options.wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    options.wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=(
                    options.wilson_line_expand_covariant_derivative_commutators
                ),
                max_wilson_derivative_order=options.wilson_line_max_derivative_order,
                tensor_reduce=wilson_line_internal_tensor_reduce,
                tensor_reduce_engine=options.tensor_reduce_engine,
                tensor_reduce_before_wilson_expand=(
                    options.wilson_line_tensor_reduce_before_wilson_expand
                ),
                max_pole_order=options.max_pole_order,
                epsilon=options.epsilon,
                mu_r_squared=options.mu_r_squared,
                combine_terms=options.combine_terms,
                simplify_pychete_color_algebra=options.simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_builder_expose_scalar_derivative_commutator_bilinears
                ),
                internal_evaluation_mode=options.wilson_line_internal_evaluation_mode,
                collect_path_sums=options.wilson_line_collect_path_sums,
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
        else:
            result = setup.interaction_wilson_line_internal_minimal_subtraction_result(
                wilson_line_expansion_indices_by_trace,
                loop_momentum_squared=options.loop_momentum_squared,
                require_registered_mass=options.require_registered_mass,
                include_light_only=options.include_light_only,
                act_open_derivatives=options.wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=options.wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    options.wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    options.wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=(
                    options.wilson_line_expand_covariant_derivative_commutators
                ),
                max_wilson_derivative_order=options.wilson_line_max_derivative_order,
                tensor_reduce=wilson_line_internal_tensor_reduce,
                tensor_reduce_engine=options.tensor_reduce_engine,
                tensor_reduce_before_wilson_expand=(
                    options.wilson_line_tensor_reduce_before_wilson_expand
                ),
                max_pole_order=options.max_pole_order,
                epsilon=options.epsilon,
                mu_r_squared=options.mu_r_squared,
                combine_terms=options.combine_terms,
                simplify_pychete_color_algebra=options.simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_builder_expose_scalar_derivative_commutator_bilinears
                ),
                internal_evaluation_mode=options.wilson_line_internal_evaluation_mode,
                collect_path_sums=options.wilson_line_collect_path_sums,
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
    elif (
        wilson_line_expansion_indices_by_trace is not None
        and selected_backend is OneLoopIntegralBackend.VAKINT_MINIMAL_SUBTRACTION
    ):
        if wilson_line_include_unselected_traces:
            result = setup.interaction_wilson_line_hybrid_minimal_subtraction_result(
                wilson_line_expansion_indices_by_trace,
                heavy_field_dimension=options.heavy_field_dimension,
                include_light=options.include_light,
                loop_momentum_squared=options.loop_momentum_squared,
                require_registered_mass=options.require_registered_mass,
                include_light_only=options.include_light_only,
                act_open_derivatives=options.wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=options.wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    options.wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    options.wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=(
                    options.wilson_line_expand_covariant_derivative_commutators
                ),
                max_wilson_derivative_order=options.wilson_line_max_derivative_order,
                vakint_engine=options.vakint_engine,
                max_pole_order=options.max_pole_order,
                epsilon=options.epsilon,
                named_supertrace_stage=options.named_supertrace_stage,
                named_supertrace_short_form=options.named_supertrace_short_form,
                named_supertrace_engine=options.named_supertrace_engine,
                simplify_pychete_color_algebra=options.simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_builder_expose_scalar_derivative_commutator_bilinears
                ),
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
        else:
            result = setup.interaction_wilson_line_minimal_subtraction_result(
                wilson_line_expansion_indices_by_trace,
                loop_momentum_squared=options.loop_momentum_squared,
                require_registered_mass=options.require_registered_mass,
                include_light_only=options.include_light_only,
                act_open_derivatives=options.wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=options.wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    options.wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    options.wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=(
                    options.wilson_line_expand_covariant_derivative_commutators
                ),
                max_wilson_derivative_order=options.wilson_line_max_derivative_order,
                vakint_engine=options.vakint_engine,
                max_pole_order=options.max_pole_order,
                epsilon=options.epsilon,
                named_supertrace_stage=options.named_supertrace_stage,
                named_supertrace_short_form=options.named_supertrace_short_form,
                named_supertrace_engine=options.named_supertrace_engine,
                simplify_pychete_color_algebra=options.simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_builder_expose_scalar_derivative_commutator_bilinears
                ),
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
    elif wilson_line_expansion_indices_by_trace is not None:
        if wilson_line_include_unselected_traces:
            result = setup.interaction_wilson_line_hybrid_matching_result(
                wilson_line_expansion_indices_by_trace,
                heavy_field_dimension=options.heavy_field_dimension,
                include_light=options.include_light,
                loop_momentum_squared=options.loop_momentum_squared,
                require_registered_mass=options.require_registered_mass,
                include_light_only=options.include_light_only,
                act_open_derivatives=options.wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=options.wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    options.wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    options.wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=(
                    options.wilson_line_expand_covariant_derivative_commutators
                ),
                max_wilson_derivative_order=options.wilson_line_max_derivative_order,
                vakint_stage=options.vakint_stage,
                vakint_short_form=options.vakint_short_form,
                vakint_engine=options.vakint_engine,
                max_pole_order=options.max_pole_order,
                epsilon=options.epsilon,
                named_supertrace_stage=options.named_supertrace_stage,
                named_supertrace_short_form=options.named_supertrace_short_form,
                named_supertrace_engine=options.named_supertrace_engine,
                simplify_pychete_color_algebra=options.simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_builder_expose_scalar_derivative_commutator_bilinears
                ),
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
        else:
            result = setup.interaction_wilson_line_matching_result(
                wilson_line_expansion_indices_by_trace,
                loop_momentum_squared=options.loop_momentum_squared,
                require_registered_mass=options.require_registered_mass,
                include_light_only=options.include_light_only,
                act_open_derivatives=options.wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=options.wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    options.wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    options.wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=(
                    options.wilson_line_expand_covariant_derivative_commutators
                ),
                max_wilson_derivative_order=options.wilson_line_max_derivative_order,
                vakint_stage=options.vakint_stage,
                vakint_short_form=options.vakint_short_form,
                vakint_engine=options.vakint_engine,
                max_pole_order=options.max_pole_order,
                epsilon=options.epsilon,
                named_supertrace_stage=options.named_supertrace_stage,
                named_supertrace_short_form=options.named_supertrace_short_form,
                named_supertrace_engine=options.named_supertrace_engine,
                simplify_pychete_color_algebra=options.simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_builder_expose_scalar_derivative_commutator_bilinears
                ),
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
    elif cde_expansion_indices_by_trace is not None and selected_backend is OneLoopIntegralBackend.INTERNAL:
        result = setup.interaction_bosonic_cde_hybrid_internal_matching_result(
            cde_expansion_indices_by_trace,
            heavy_field_dimension=options.heavy_field_dimension,
            include_light=options.include_light,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
            act_open_derivatives=options.bosonic_cde_act_open_derivatives,
            emit_covariant_derivative_commutators=options.bosonic_cde_emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=options.bosonic_cde_emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=options.bosonic_cde_expand_covariant_derivative_commutators,
            tensor_reduce=options.tensor_reduce,
            tensor_reduce_engine=options.tensor_reduce_engine,
            max_pole_order=options.max_pole_order,
            epsilon=options.epsilon,
            mu_r_squared=options.mu_r_squared,
            combine_terms=options.combine_terms,
            term_atom_requirements=cde_term_atom_requirements,
        )
    elif (
        cde_expansion_indices_by_trace is not None
        and selected_backend is OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION
    ):
        result = setup.interaction_bosonic_cde_hybrid_internal_minimal_subtraction_result(
            cde_expansion_indices_by_trace,
            heavy_field_dimension=options.heavy_field_dimension,
            include_light=options.include_light,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
            act_open_derivatives=options.bosonic_cde_act_open_derivatives,
            emit_covariant_derivative_commutators=options.bosonic_cde_emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=options.bosonic_cde_emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=options.bosonic_cde_expand_covariant_derivative_commutators,
            tensor_reduce=options.tensor_reduce,
            tensor_reduce_engine=options.tensor_reduce_engine,
            max_pole_order=options.max_pole_order,
            epsilon=options.epsilon,
            mu_r_squared=options.mu_r_squared,
            combine_terms=options.combine_terms,
            term_atom_requirements=cde_term_atom_requirements,
        )
    elif (
        cde_expansion_indices_by_trace is not None
        and selected_backend is OneLoopIntegralBackend.VAKINT_MINIMAL_SUBTRACTION
    ):
        result = setup.interaction_bosonic_cde_hybrid_minimal_subtraction_result(
            cde_expansion_indices_by_trace,
            heavy_field_dimension=options.heavy_field_dimension,
            include_light=options.include_light,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
            act_open_derivatives=options.bosonic_cde_act_open_derivatives,
            emit_covariant_derivative_commutators=options.bosonic_cde_emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=options.bosonic_cde_emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=options.bosonic_cde_expand_covariant_derivative_commutators,
            vakint_engine=options.vakint_engine,
            max_pole_order=options.max_pole_order,
            epsilon=options.epsilon,
            named_supertrace_stage=options.named_supertrace_stage,
            named_supertrace_short_form=options.named_supertrace_short_form,
            named_supertrace_engine=options.named_supertrace_engine,
            term_atom_requirements=cde_term_atom_requirements,
        )
    elif cde_expansion_indices_by_trace is not None:
        result = setup.interaction_bosonic_cde_hybrid_matching_result(
            cde_expansion_indices_by_trace,
            heavy_field_dimension=options.heavy_field_dimension,
            include_light=options.include_light,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
            act_open_derivatives=options.bosonic_cde_act_open_derivatives,
            emit_covariant_derivative_commutators=options.bosonic_cde_emit_covariant_derivative_commutators,
            emit_covariant_derivative_commutator_passes=options.bosonic_cde_emit_covariant_derivative_commutator_passes,
            expand_covariant_derivative_commutators=options.bosonic_cde_expand_covariant_derivative_commutators,
            vakint_stage=options.vakint_stage,
            vakint_short_form=options.vakint_short_form,
            vakint_engine=options.vakint_engine,
            max_pole_order=options.max_pole_order,
            epsilon=options.epsilon,
            named_supertrace_stage=options.named_supertrace_stage,
            named_supertrace_short_form=options.named_supertrace_short_form,
            named_supertrace_engine=options.named_supertrace_engine,
            term_atom_requirements=cde_term_atom_requirements,
        )
    elif selected_backend is OneLoopIntegralBackend.INTERNAL:
        result = setup.interaction_power_type_internal_matching_result(
            heavy_field_dimension=options.heavy_field_dimension,
            include_light=options.include_light,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
            tensor_reduce=options.tensor_reduce,
            tensor_reduce_engine=options.tensor_reduce_engine,
            max_pole_order=options.max_pole_order,
            epsilon=options.epsilon,
            mu_r_squared=options.mu_r_squared,
            combine_terms=options.combine_terms,
        )
    elif selected_backend is OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION:
        result = setup.interaction_power_type_internal_minimal_subtraction_result(
            heavy_field_dimension=options.heavy_field_dimension,
            include_light=options.include_light,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
            tensor_reduce=options.tensor_reduce,
            tensor_reduce_engine=options.tensor_reduce_engine,
            max_pole_order=options.max_pole_order,
            epsilon=options.epsilon,
            mu_r_squared=options.mu_r_squared,
            combine_terms=options.combine_terms,
        )
    elif selected_backend is OneLoopIntegralBackend.VAKINT_MINIMAL_SUBTRACTION:
        result = setup.interaction_power_type_minimal_subtraction_result(
            heavy_field_dimension=options.heavy_field_dimension,
            include_light=options.include_light,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
            vakint_engine=options.vakint_engine,
            max_pole_order=options.max_pole_order,
            epsilon=options.epsilon,
            named_supertrace_stage=options.named_supertrace_stage,
            named_supertrace_short_form=options.named_supertrace_short_form,
            named_supertrace_engine=options.named_supertrace_engine,
        )
    elif normalization_label != OneLoopNormalization.PREVIEW.value:
        result = setup.interaction_power_type_normalized_matching_result(
            heavy_field_dimension=options.heavy_field_dimension,
            include_light=options.include_light,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
            vakint_stage=options.vakint_stage,
            vakint_short_form=options.vakint_short_form,
            vakint_engine=options.vakint_engine,
            max_pole_order=options.max_pole_order,
            epsilon=options.epsilon,
            normalization=options.normalization,
            hbar=options.hbar,
            named_supertrace_stage=options.named_supertrace_stage,
            named_supertrace_short_form=options.named_supertrace_short_form,
            named_supertrace_engine=options.named_supertrace_engine,
        )
    else:
        result = setup.interaction_power_type_matching_result(
            heavy_field_dimension=options.heavy_field_dimension,
            include_light=options.include_light,
            loop_momentum_squared=options.loop_momentum_squared,
            require_registered_mass=options.require_registered_mass,
            vakint_stage=options.vakint_stage,
            vakint_short_form=options.vakint_short_form,
            vakint_engine=options.vakint_engine,
            max_pole_order=options.max_pole_order,
            epsilon=options.epsilon,
            named_supertrace_stage=options.named_supertrace_stage,
            named_supertrace_short_form=options.named_supertrace_short_form,
            named_supertrace_engine=options.named_supertrace_engine,
        )
    if (
        normalization_label != OneLoopNormalization.PREVIEW.value
        and result.metadata.get("loop_normalization_applied") is not True
    ):
        result = result.with_loop_normalization(options.normalization, hbar=options.hbar)
    if wilson_line_expansion_indices_by_trace is not None and selected_backend is OneLoopIntegralBackend.INTERNAL:
        result = _activate_wilson_line_internal_through_finite_source(result)
    if options.include_tree_level_matching:
        tree_level = match_tree(theory, matching_lagrangian, eft_order=eft_order)
        result = replace(
            result,
            off_shell_eft_lagrangian=(tree_level + result.off_shell_eft_lagrangian).expand(),
            on_shell_eft_lagrangian=(tree_level + result.on_shell_eft_lagrangian).expand(),
            supertraces={
                **result.supertraces,
                "tree_level_eft_lagrangian": tree_level,
                "loop_only_off_shell_eft_lagrangian": result.off_shell_eft_lagrangian,
                "loop_only_on_shell_eft_lagrangian": result.on_shell_eft_lagrangian,
                LOOP_ONLY_OFF_SHELL_PROJECTION_SOURCE: result.off_shell_eft_lagrangian,
                LOOP_ONLY_ON_SHELL_PROJECTION_SOURCE: result.on_shell_eft_lagrangian,
                TREE_LEVEL_OFF_SHELL_PROJECTION_SOURCE: tree_level,
                TREE_LEVEL_ON_SHELL_PROJECTION_SOURCE: tree_level,
            },
            metadata={
                **result.metadata,
                "tree_level_matching_included": True,
                "tree_level_matching_source": "matching_lagrangian",
            },
        )
    else:
        result = replace(
            result,
            metadata={
                **result.metadata,
                "tree_level_matching_included": False,
                "tree_level_matching_source": "disabled",
            },
        )
    result = replace(
        result,
        metadata={
            **result.metadata,
            "tensor_networks_evaluated": options.evaluate_tensor_networks,
            "tensor_network_cg_component_source": tensor_network_cg_component_source,
            "tensor_network_native_hep_cg_builtins": options.tensor_network_native_hep_cg_builtins,
            "abelian_covariant_derivatives_expanded": options.expand_abelian_covariant_derivatives,
            "non_abelian_covariant_derivatives_expanded": options.expand_non_abelian_covariant_derivatives,
            "covariant_derivative_commutators_emitted": options.emit_covariant_derivative_commutators,
            "covariant_derivative_commutator_emit_passes": (
                options.emit_covariant_derivative_commutator_passes
                if options.emit_covariant_derivative_commutators
                else 0
            ),
            "covariant_derivative_commutators_expanded": options.expand_covariant_derivative_commutators,
            "bosonic_cde_expansion_enabled": cde_expansion_indices_by_trace is not None,
            "bosonic_cde_expansion_planned": isinstance(cde_expansion_indices_by_trace, BosonicCDEExpansionPlan),
            "bosonic_cde_trace_names": (
                ",".join(cde_expansion_indices_by_trace.trace_names)
                if isinstance(cde_expansion_indices_by_trace, BosonicCDEExpansionPlan)
                else ",".join(options.bosonic_cde_expansion_indices_by_trace or ())
            ),
            "bosonic_cde_max_total_order": options.bosonic_cde_max_total_order,
            "bosonic_cde_max_slot_order": options.bosonic_cde_max_slot_order,
            "bosonic_cde_index_prefix": options.bosonic_cde_index_prefix,
            "bosonic_cde_act_open_derivatives": options.bosonic_cde_act_open_derivatives,
            "bosonic_cde_commutators_emitted": options.bosonic_cde_emit_covariant_derivative_commutators,
            "bosonic_cde_commutator_emit_passes": (
                options.bosonic_cde_emit_covariant_derivative_commutator_passes
                if options.bosonic_cde_emit_covariant_derivative_commutators
                else 0
            ),
            "bosonic_cde_commutators_expanded": options.bosonic_cde_expand_covariant_derivative_commutators,
            "bosonic_cde_terms_filtered_by_matching_targets": (
                cde_term_atom_requirements is not None
            ),
            "wilson_line_expansion_enabled": wilson_line_expansion_indices_by_trace is not None,
            "wilson_line_expansion_planned": isinstance(wilson_line_expansion_indices_by_trace, WilsonLineExpansionPlan),
            "wilson_line_trace_names": (
                ",".join(wilson_line_expansion_indices_by_trace.trace_names)
                if isinstance(wilson_line_expansion_indices_by_trace, WilsonLineExpansionPlan)
                else ",".join(options.wilson_line_expansion_indices_by_trace or ())
            ),
            "wilson_line_max_total_order": options.wilson_line_max_total_order,
            "wilson_line_max_slot_order": options.wilson_line_max_slot_order,
            "wilson_line_total_orders": (
                ",".join(str(order) for order in options.wilson_line_total_orders)
                if options.wilson_line_total_orders is not None
                else None
            ),
            "wilson_line_total_orders_by_trace": _metadata_wilson_line_total_orders_by_trace(
                options.wilson_line_total_orders_by_trace
            ),
            "wilson_line_entry_labels": (
                ",".join(options.wilson_line_entry_labels)
                if options.wilson_line_entry_labels is not None
                else None
            ),
            "wilson_line_plan_filters_applied": wilson_line_plan_filters_requested,
            "wilson_line_index_prefix": options.wilson_line_index_prefix,
            "wilson_line_act_open_derivatives": options.wilson_line_act_open_derivatives,
            "wilson_line_commutators_emitted": options.wilson_line_emit_covariant_derivative_commutators,
            "wilson_line_commutator_emit_passes": (
                options.wilson_line_emit_covariant_derivative_commutator_passes
                if options.wilson_line_emit_covariant_derivative_commutators
                else 0
            ),
            "wilson_line_commutator_emit_mode": (
                options.wilson_line_covariant_derivative_commutator_mode
                if options.wilson_line_emit_covariant_derivative_commutators
                else None
            ),
            "wilson_line_commutators_expanded": options.wilson_line_expand_covariant_derivative_commutators,
            "wilson_line_max_derivative_order": options.wilson_line_max_derivative_order,
            "wilson_line_tensor_reduce_before_wilson_expand": (
                options.wilson_line_tensor_reduce_before_wilson_expand
            ),
            "wilson_line_terms_filtered_by_matching_targets": (
                wilson_line_term_atom_requirements is not None
            ),
            "wilson_line_include_unselected_traces": wilson_line_include_unselected_traces,
            "wilson_line_selected_only": (
                wilson_line_expansion_indices_by_trace is not None
                and not wilson_line_include_unselected_traces
            ),
            "wilson_line_scalar_derivative_commutator_bilinears_exposed": (
                options.wilson_line_expose_scalar_derivative_commutator_bilinears
            ),
            "wilson_line_scalar_eom_terms_exposed": options.wilson_line_expose_scalar_eom_terms,
            "use_matchete_fluctuation_dof_basis": options.use_matchete_fluctuation_dof_basis,
            "wilson_line_weight_paths_by_component_dofs": (
                options.wilson_line_weight_paths_by_component_dofs
            ),
            "pychete_color_algebra_simplified": options.simplify_pychete_color_algebra,
        },
    )
    result = _simplify_result_field_strength_metrics(result)
    if options.simplify_pychete_color_algebra:
        result = _decode_result_native_color_wrappers(theory, result)
    skip_heavy_scalar_solutions_for_wilson_line_scalar_eom = bool(
        options.substitute_heavy_scalar_solutions
        and options.wilson_line_expose_scalar_eom_terms
    )
    if options.substitute_heavy_scalar_solutions and not skip_heavy_scalar_solutions_for_wilson_line_scalar_eom:
        result = _apply_heavy_scalar_solution_reduction_to_one_loop_result(
            theory,
            result,
            heavy_scalar_solutions or {},
            options,
            eft_order=eft_order,
            matching_condition_targets=matching_condition_targets,
            matching_condition_truncate_eft=matching_condition_truncate_eft,
            deferred_to_wilson_line_scalar_eom=False,
        )
    elif options.substitute_heavy_scalar_solutions:
        solutions = heavy_scalar_solutions or {}
        replacement_rules = heavy_scalar_solution_replacements(solutions, fresh_dummy_indices=True)
        if replacement_rules:
            _LOGGER.info(
                "skipping %d heavy scalar solution substitution rule(s) for %s at the Wilson-line scalar/EOM boundary",
                len(replacement_rules),
                theory.name,
            )
        result = replace(
            result,
            metadata={
                **result.metadata,
                "heavy_scalar_solutions_substituted": False,
                "heavy_scalar_solution_count": len(solutions),
                "heavy_scalar_solution_rule_count": len(replacement_rules),
                "heavy_scalar_solution_source": (
                    "option" if options.heavy_scalar_solution_lagrangian is not None else "matching_lagrangian"
                ),
                "heavy_scalar_solution_expand": options.heavy_scalar_solution_expand,
                "heavy_scalar_solution_fresh_dummy_indices": False,
                "heavy_scalar_solution_eft_limited": False,
                "heavy_scalar_solution_deferred_to_wilson_line_scalar_eom": False,
                "heavy_scalar_solution_skipped_for_wilson_line_scalar_eom": True,
                "heavy_scalar_solution_skip_reason": "wilson_line_scalar_eom_internal_simplify_boundary",
            },
        )
    elif not options.substitute_heavy_scalar_solutions:
        result = replace(
            result,
            metadata={
                **result.metadata,
                "heavy_scalar_solutions_substituted": False,
                "heavy_scalar_solution_count": 0,
                "heavy_scalar_solution_rule_count": 0,
                "heavy_scalar_solution_source": "disabled",
                "heavy_scalar_solution_expand": False,
                "heavy_scalar_solution_fresh_dummy_indices": False,
                "heavy_scalar_solution_eft_limited": False,
                "heavy_scalar_solution_deferred_to_wilson_line_scalar_eom": False,
                "heavy_scalar_solution_skipped_for_wilson_line_scalar_eom": False,
                "heavy_scalar_solution_skip_reason": None,
            },
        )
    if options.on_shell_replacements is not None:
        result = result.with_on_shell_reduction(
            options.on_shell_replacements,
            repeat=options.on_shell_replacement_repeat,
        )
    defer_on_shell_eom_to_wilson_line_scalar_eom = bool(
        options.on_shell_eom_lagrangian is not None
        and options.wilson_line_expose_scalar_eom_terms
    )
    if options.on_shell_eom_lagrangian is not None and not defer_on_shell_eom_to_wilson_line_scalar_eom:
        eom_source = result.on_shell_eft_lagrangian
        eom_rules = eom_replacement_rules_for_expression(
            theory,
            options.on_shell_eom_lagrangian,
            eom_source,
            fields=options.on_shell_eom_fields,
            eft_order=eft_order,
            min_derivative_order=options.on_shell_eom_min_derivative_order,
            strict=options.on_shell_eom_strict,
        )
        vector_field_redefinition_delta = Expression.num(0)
        if options.on_shell_eom_abelian_vector_field_redefinition:
            vector_field_redefinition_delta = abelian_vector_eom_field_redefinition_delta(
                theory,
                options.on_shell_eom_lagrangian,
                eom_source,
                fields=options.on_shell_eom_fields,
                strict=options.on_shell_eom_strict,
            )
        if eom_rules:
            result = result.with_on_shell_reduction(
                eom_rules,
                repeat=options.on_shell_replacement_repeat,
            )
        if not is_zero(vector_field_redefinition_delta):
            before_field_redefinition = result.on_shell_eft_lagrangian
            after_field_redefinition = (before_field_redefinition + vector_field_redefinition_delta).expand()
            result = replace(
                result,
                on_shell_eft_lagrangian=after_field_redefinition,
                supertraces={
                    **result.supertraces,
                    "on_shell_eft_lagrangian_before_abelian_vector_field_redefinition": (
                        before_field_redefinition
                    ),
                    "on_shell_eft_lagrangian_after_abelian_vector_field_redefinition": (
                        after_field_redefinition
                    ),
                    "on_shell_eft_lagrangian_abelian_vector_field_redefinition_delta": (
                        vector_field_redefinition_delta
                    ),
                },
            )
            result = _sync_loop_on_shell_projection_source_with_final(result)
        result = replace(
            result,
            metadata={
                **result.metadata,
                "on_shell_eom_reduction_requested": True,
                "on_shell_eom_reduction_rule_count": len(eom_rules),
                "on_shell_eom_min_derivative_order": options.on_shell_eom_min_derivative_order,
                "on_shell_eom_strict": options.on_shell_eom_strict,
                "on_shell_eom_abelian_vector_field_redefinition": (
                    options.on_shell_eom_abelian_vector_field_redefinition
                ),
                "on_shell_eom_abelian_vector_field_redefinition_applied": (
                    not is_zero(vector_field_redefinition_delta)
                ),
            },
        )
    elif defer_on_shell_eom_to_wilson_line_scalar_eom:
        result = replace(
            result,
            metadata={
                **result.metadata,
                "on_shell_eom_reduction_requested": True,
                "on_shell_eom_reduction_rule_count": 0,
                "on_shell_eom_min_derivative_order": options.on_shell_eom_min_derivative_order,
                "on_shell_eom_strict": options.on_shell_eom_strict,
                "on_shell_eom_abelian_vector_field_redefinition": (
                    options.on_shell_eom_abelian_vector_field_redefinition
                ),
                "on_shell_eom_abelian_vector_field_redefinition_applied": False,
                "on_shell_eom_reduction_deferred_to_wilson_line_scalar_eom": True,
            },
        )
    if options.wilson_line_expose_scalar_derivative_commutator_bilinears or options.wilson_line_expose_scalar_eom_terms:
        before_scalar_exposure = result.on_shell_eft_lagrangian
        scalar_exposed_on_shell = _apply_wilson_line_post_integral_scalar_commutator_bilinears(
            theory,
            before_scalar_exposure,
            eom_lagrangian=options.on_shell_eom_lagrangian,
            eom_fields=options.on_shell_eom_fields,
            expose_scalar_eom_terms=options.wilson_line_expose_scalar_eom_terms,
        )
        reduced_on_shell = scalar_exposed_on_shell
        scalar_commutator_vector_eom_rule_count = 0
        scalar_commutator_vector_field_redefinition_delta = Expression.num(0)
        staged_scalar_eom_vector_field_redefinition = bool(options.wilson_line_expose_scalar_eom_terms)
        if (
            options.on_shell_eom_lagrangian is not None
            and options.on_shell_eom_abelian_vector_field_redefinition
        ):
            (
                reduced_on_shell,
                scalar_commutator_vector_eom_rule_count,
                scalar_commutator_vector_field_redefinition_delta,
            ) = _apply_on_shell_eom_reduction_to_expression(
                theory,
                scalar_exposed_on_shell,
                eom_lagrangian=options.on_shell_eom_lagrangian,
                fields=options.on_shell_eom_fields,
                eft_order=eft_order,
                min_derivative_order=options.on_shell_eom_min_derivative_order,
                strict=options.on_shell_eom_strict,
                abelian_vector_field_redefinition=not staged_scalar_eom_vector_field_redefinition,
                repeat=options.on_shell_replacement_repeat,
            )
            if staged_scalar_eom_vector_field_redefinition:
                (
                    reduced_on_shell,
                    scalar_commutator_vector_field_redefinition_delta,
                ) = _apply_wilson_line_abelian_vector_eom_field_redefinition(
                    theory,
                    reduced_on_shell,
                    source_lagrangian=options.on_shell_eom_lagrangian,
                    eom_terms_lagrangian=scalar_exposed_on_shell,
                    max_order=eft_order,
                    fields=options.on_shell_eom_fields,
                    strict=options.on_shell_eom_strict,
                )
        after_scalar_eom_field_redefinition = reduced_on_shell
        scalar_eom_field_redefinition_delta = Expression.num(0)
        if options.wilson_line_expose_scalar_eom_terms:
            assert options.on_shell_eom_lagrangian is not None
            scalar_source_lagrangian = (options.on_shell_eom_lagrangian + reduced_on_shell).expand()
            (
                after_scalar_eom_field_redefinition,
                scalar_eom_field_redefinition_delta,
            ) = _apply_wilson_line_scalar_eom_field_redefinition(
                theory,
                reduced_on_shell,
                source_lagrangian=scalar_source_lagrangian,
                max_order=eft_order,
                fields=options.on_shell_eom_fields,
                strict=options.on_shell_eom_strict,
            )
        scalar_supertraces = {
            **result.supertraces,
            "on_shell_eft_lagrangian_before_scalar_commutator_bilinear_exposure": (
                before_scalar_exposure
            ),
            "on_shell_eft_lagrangian_after_scalar_commutator_bilinear_exposure": scalar_exposed_on_shell,
        }
        if scalar_commutator_vector_eom_rule_count or not is_zero(scalar_commutator_vector_field_redefinition_delta):
            scalar_supertraces = {
                **scalar_supertraces,
                "on_shell_eft_lagrangian_after_scalar_commutator_abelian_vector_eom_reduction": (
                    reduced_on_shell
                ),
                "on_shell_eft_lagrangian_scalar_commutator_abelian_vector_field_redefinition_delta": (
                    scalar_commutator_vector_field_redefinition_delta
                ),
            }
        if options.wilson_line_expose_scalar_eom_terms:
            scalar_supertraces = {
                **scalar_supertraces,
                "on_shell_eft_lagrangian_scalar_eom_field_redefinition_delta": (
                    scalar_eom_field_redefinition_delta
                ),
                "on_shell_eft_lagrangian_after_scalar_eom_field_redefinition": (
                    after_scalar_eom_field_redefinition
                ),
            }
        result = replace(
            result,
            on_shell_eft_lagrangian=after_scalar_eom_field_redefinition,
            supertraces=scalar_supertraces,
            metadata={
                **result.metadata,
                "wilson_line_scalar_commutator_bilinears_reduced": (
                    options.wilson_line_expose_scalar_derivative_commutator_bilinears
                ),
                "wilson_line_scalar_eom_terms_reduced": options.wilson_line_expose_scalar_eom_terms,
                "wilson_line_scalar_eom_field_redefinition_applied": (
                    not is_zero(scalar_eom_field_redefinition_delta)
                ),
                "wilson_line_scalar_commutator_abelian_vector_eom_reduction_rule_count": (
                    scalar_commutator_vector_eom_rule_count
                ),
                "wilson_line_scalar_commutator_abelian_vector_field_redefinition_applied": (
                    not is_zero(scalar_commutator_vector_field_redefinition_delta)
                ),
                "wilson_line_scalar_commutator_abelian_vector_field_redefinition_staged": (
                    staged_scalar_eom_vector_field_redefinition
                    and not is_zero(scalar_commutator_vector_field_redefinition_delta)
                ),
            },
        )
        result = _sync_loop_on_shell_projection_source_with_final(result)
    if options.truncate_eft_result:
        result = result.with_eft_truncation(
            eft_order,
            heavy_field_dimension=options.heavy_field_dimension,
        )
    else:
        result = replace(
            result,
            metadata={
                **result.metadata,
                "eft_result_truncated": False,
                "eft_result_truncation_order": eft_order,
            },
        )
    if matching_condition_targets is None:
        _log_one_loop_result(result)
        return result
    staged_sources = result.staged_projection_sources(matching_condition_source)
    if staged_sources:
        projected = result.with_projected_matching_conditions_from_sources(
            matching_condition_targets,
            staged_sources,
            expand_source=matching_condition_expand_source,
            canonize_indices=matching_condition_canonize_indices,
            normalize_derivative_operators=matching_condition_normalize_derivative_operators,
            normalize_ibp_scalar_bilinears=matching_condition_normalize_ibp_scalar_bilinears,
            drop_zero=matching_condition_drop_zero,
            include_coupling_identities=matching_condition_include_coupling_identities,
            eft_order=eft_order if matching_condition_truncate_eft else None,
            heavy_field_dimension=options.heavy_field_dimension,
        )
    else:
        projected = result.with_projected_matching_conditions(
            matching_condition_targets,
            source=matching_condition_source,
            expand_source=matching_condition_expand_source,
            canonize_indices=matching_condition_canonize_indices,
            normalize_derivative_operators=matching_condition_normalize_derivative_operators,
            normalize_ibp_scalar_bilinears=matching_condition_normalize_ibp_scalar_bilinears,
            drop_zero=matching_condition_drop_zero,
            include_coupling_identities=matching_condition_include_coupling_identities,
            eft_order=eft_order if matching_condition_truncate_eft else None,
            heavy_field_dimension=options.heavy_field_dimension,
        )
    _log_one_loop_result(projected)
    return projected


def _simplify_result_field_strength_metrics(result: MatchingResult) -> MatchingResult:
    from .backends import idenso as idenso_backend

    simplified_off_shell = idenso_backend.simplify_pychete_field_strength_metrics(result.off_shell_eft_lagrangian)
    simplified_on_shell = idenso_backend.simplify_pychete_field_strength_metrics(result.on_shell_eft_lagrangian)
    simplified_matching_conditions = {
        name: idenso_backend.simplify_pychete_field_strength_metrics(expression)
        for name, expression in result.matching_conditions.items()
    }
    simplified_supertraces = {
        name: idenso_backend.simplify_pychete_field_strength_metrics(expression)
        for name, expression in result.supertraces.items()
    }
    return replace(
        result,
        off_shell_eft_lagrangian=simplified_off_shell,
        on_shell_eft_lagrangian=simplified_on_shell,
        matching_conditions=simplified_matching_conditions,
        supertraces=simplified_supertraces,
        metadata={
            **result.metadata,
            "field_strength_metric_simplified": True,
        },
    )


def _apply_heavy_scalar_solution_reduction_to_one_loop_result(
    theory: Theory,
    result: MatchingResult,
    solutions: dict[str, HeavyScalarSolution],
    options: OneLoopMatchOptions,
    *,
    eft_order: int,
    matching_condition_targets: Mapping[str, Expression] | Iterable[Expression] | str | None,
    matching_condition_truncate_eft: bool,
    deferred_to_wilson_line_scalar_eom: bool,
) -> MatchingResult:
    replacement_rules = heavy_scalar_solution_replacements(solutions, fresh_dummy_indices=True)
    if replacement_rules:
        stage = "after Wilson-line scalar/EOM exposure" if deferred_to_wilson_line_scalar_eom else "before EOM exposure"
        _LOGGER.info(
            "substituting %d heavy scalar solution(s) in one-loop result for %s (%s)",
            len(solutions),
            theory.name,
            stage,
        )
        if matching_condition_targets is not None and matching_condition_truncate_eft:
            before_reduction = result.on_shell_eft_lagrangian
            reduced = replace_heavy_scalar_solutions_eft_limited(
                before_reduction,
                solutions,
                theory,
                eft_order=eft_order,
                fresh_dummy_indices=True,
            )
            supertraces = {
                **result.supertraces,
                "on_shell_eft_lagrangian_before_reduction": before_reduction,
                "on_shell_eft_lagrangian_after_reduction": reduced,
            }
            for stage_name in (
                LOOP_ONLY_ON_SHELL_PROJECTION_SOURCE,
                TREE_LEVEL_ON_SHELL_PROJECTION_SOURCE,
            ):
                if stage_name not in result.supertraces:
                    continue
                supertraces[stage_name] = replace_heavy_scalar_solutions_eft_limited(
                    result.supertraces[stage_name],
                    solutions,
                    theory,
                    eft_order=eft_order,
                    fresh_dummy_indices=True,
                )
            result = replace(
                result,
                on_shell_eft_lagrangian=reduced,
                supertraces=supertraces,
                metadata={
                    **result.metadata,
                    "on_shell_reduced": True,
                    "on_shell_reduction_source": "on_shell_eft_lagrangian",
                    "on_shell_reduction_replacement_count": len(replacement_rules),
                    "on_shell_reduction_repeat": False,
                    "heavy_scalar_solution_eft_limited": True,
                },
            )
            result = _sync_loop_on_shell_projection_source_with_final(result)
        else:
            result = result.with_on_shell_reduction(
                replacement_rules,
                expand=options.heavy_scalar_solution_expand,
            )
    return replace(
        result,
        metadata={
            **result.metadata,
            "heavy_scalar_solutions_substituted": bool(replacement_rules),
            "heavy_scalar_solution_count": len(solutions),
            "heavy_scalar_solution_rule_count": len(replacement_rules),
            "heavy_scalar_solution_source": (
                "option" if options.heavy_scalar_solution_lagrangian is not None else "matching_lagrangian"
            ),
            "heavy_scalar_solution_expand": options.heavy_scalar_solution_expand,
            "heavy_scalar_solution_fresh_dummy_indices": True,
            "heavy_scalar_solution_eft_limited": bool(
                replacement_rules
                and matching_condition_targets is not None
                and matching_condition_truncate_eft
            ),
            "heavy_scalar_solution_deferred_to_wilson_line_scalar_eom": deferred_to_wilson_line_scalar_eom,
            "heavy_scalar_solution_skipped_for_wilson_line_scalar_eom": False,
            "heavy_scalar_solution_skip_reason": None,
        },
    )


def _decode_result_native_color_wrappers(theory: Theory, result: MatchingResult) -> MatchingResult:
    from .backends import idenso as idenso_backend

    def decode_and_simplify(expression: Expression) -> Expression:
        return idenso_backend.decode_native_color_wrappers_and_simplify_field_strengths(theory, expression)

    decoded_off_shell = decode_and_simplify(result.off_shell_eft_lagrangian)
    decoded_on_shell = decode_and_simplify(result.on_shell_eft_lagrangian)
    decoded_matching_conditions = {
        name: decode_and_simplify(expression) for name, expression in result.matching_conditions.items()
    }
    decoded_supertraces = {name: decode_and_simplify(expression) for name, expression in result.supertraces.items()}
    return replace(
        result,
        off_shell_eft_lagrangian=decoded_off_shell,
        on_shell_eft_lagrangian=decoded_on_shell,
        matching_conditions=decoded_matching_conditions,
        supertraces=decoded_supertraces,
        metadata={
            **result.metadata,
            "native_color_wrappers_decoded": True,
            "post_decode_field_strength_metric_simplified": True,
            "su2_field_strength_generator_bilinears_simplified": True,
            "su2_u1_field_strength_generator_bilinears_simplified": True,
        },
    )


def _log_one_loop_result(result: MatchingResult) -> None:
    _LOGGER.info(
        "one-loop result for %s contains %d supertraces and %d matching conditions",
        result.theory.name,
        len(result.supertraces),
        len(result.matching_conditions),
    )


def _sync_loop_on_shell_projection_source_with_final(result: MatchingResult) -> MatchingResult:
    """Keep staged loop/tree on-shell projection sources additive.

    Replacement-rule reductions use ``MatchingResult.with_on_shell_reduction``,
    which updates staged projection sources directly. Wilson-line scalar/EOM
    exposure and vector field redefinitions are computed as transformed final
    on-shell expressions, so when a tree source is present the loop projection
    source must be refreshed to preserve
    ``loop_only_on_shell_projection_source + tree_level_on_shell_projection_source
    == on_shell_eft_lagrangian``.
    """

    if (
        LOOP_ONLY_ON_SHELL_PROJECTION_SOURCE not in result.supertraces
        or TREE_LEVEL_ON_SHELL_PROJECTION_SOURCE not in result.supertraces
    ):
        return result
    tree_source = result.supertraces[TREE_LEVEL_ON_SHELL_PROJECTION_SOURCE]
    loop_source = (result.on_shell_eft_lagrangian - tree_source).expand()
    return replace(
        result,
        supertraces={
            **result.supertraces,
            LOOP_ONLY_ON_SHELL_PROJECTION_SOURCE: loop_source,
        },
        metadata={
            **result.metadata,
            "on_shell_staged_projection_sources_synchronized": True,
        },
    )


def _one_loop_tensor_network_component_source(theory: Theory, options: OneLoopMatchOptions) -> str | None:
    if options.tensor_network_cg_components_by_name is not None:
        return "explicit"
    if options.tensor_network_builtin_cg_components:
        return "builtin"
    if options.tensor_network_symbolic_cg_components:
        return "symbolic"
    from .backends import spenso

    if spenso.has_stored_cg_tensor_components(theory):
        return "stored"
    if options.tensor_network_native_hep_cg_builtins:
        return "native_hep"
    if options.tensor_network_library is not None:
        return "library"
    return None
