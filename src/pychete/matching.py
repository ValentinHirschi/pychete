from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from html import escape
from itertools import product
from typing import Any, Iterable, Iterator, Mapping, Sequence, TypeAlias

from symbolica import Expression, Matrix, Replacement

from .eft import series_eft
from .expr import (
    bar_field_pattern,
    bar_field_inner,
    field_label,
    field_pattern,
    field_with_derivatives,
    is_bar_field,
    is_zero,
    list_expr,
    list_items,
    sum_expr,
)
from .functional import apply_cd, derive_eom
from .symbols import SymbolRole, canonical_string, display_string, latex_string, s
from .theory import (
    FieldDefinition,
    FieldHandle,
    FieldMassKind,
    FieldRole,
    FieldVariation,
    Theory,
    field_mass_expr_from_label,
    field_mass_kind_from_label,
    field_propagating_from_label,
    field_role_from_label,
    field_self_conjugate_from_label,
    field_type_from_label,
)
from .validation import NumericProbeResult, NumericValue, evaluator_probe_equal

FluctuationBasisItem: TypeAlias = FieldHandle | FieldDefinition | str | Expression
ExpressionMatrix: TypeAlias = tuple[tuple[Expression, ...], ...]


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


class VakintIntegralStage(StrEnum):
    """Native vakint processing stage for lowered one-loop integral expressions."""

    RAW = "raw"
    CANONICAL = "canonical"
    TENSOR_REDUCED = "tensor_reduced"
    EVALUATED = "evaluated"

    @classmethod
    def from_user(cls, value: VakintIntegralStage | str) -> VakintIntegralStage:
        """Normalize a user-provided vakint integral stage selector."""

        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError("vakint integral stage must be 'raw', 'canonical', 'tensor_reduced', or 'evaluated'") from exc


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

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{FluctuationMode}}\left({latex_string(self.field)}\right)$"

    def _repr_html_(self) -> str:
        return (
            f"<code>FluctuationMode({escape(display_string(self.field))} "
            f"{self.mass_kind.value} {self.field_role.value} {self.statistics.value})</code>"
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

    def entry(self, row: FluctuationBasisItem, column: FluctuationBasisItem) -> Expression:
        """Return one block entry identified by row and column fields."""

        row_index = _mode_index(self.rows, _fluctuation_basis_expression(self.theory, row))
        column_index = _mode_index(self.columns, _fluctuation_basis_expression(self.theory, column))
        return self.matrix[row_index][column_index]

    def to_expression_map(self, *, prefix: str = "fluctuation_operator_block") -> dict[str, Expression]:
        """Return deterministic named expressions for this block."""

        entries: dict[str, Expression] = {}
        for row in self.rows:
            for column in self.columns:
                key = (
                    f"{prefix}[{self.row_sector.value},{self.column_sector.value},"
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

        return _cyclic_sector_key(tuple(block.row_sector.value for block in self.blocks))

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
        metrics: bool = True,
        dots: bool = False,
    ) -> SupertraceBlockTrace:
        """Return this trace kernel after native idenso index simplification."""

        from .backends import idenso

        return replace(
            self,
            expression=idenso.simplify_index_algebra(
                self.expression,
                expand=expand,
                gamma=gamma,
                color=color,
                metrics=metrics,
                dots=dots,
            ),
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
            expression=vakint.to_canonical(self.expression, short_form=short_form, engine=engine),
        )

    def tensor_reduce_integrals(self, *, engine: Any | None = None) -> SupertraceBlockTrace:
        """Return this trace kernel after native vakint tensor reduction."""

        from .backends import vakint

        return replace(self, expression=vakint.tensor_reduce(self.expression, engine=engine))

    def evaluate_integrals(self, *, engine: Any | None = None) -> SupertraceBlockTrace:
        """Return this trace kernel after native vakint integral evaluation."""

        from .backends import vakint

        return replace(self, expression=vakint.evaluate(self.expression, engine=engine))

    def evaluate_tensor_network(
        self,
        *,
        library: Any | None = None,
        cg_components_by_name: Mapping[str, Sequence[Expression | int | float | complex]] | None = None,
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
            symbolic_cg_components=symbolic_cg_components,
            function_library=function_library,
            n_steps=n_steps,
            mode=mode,
        )
        return replace(self, expression=spenso.tensor_network_result_scalar(network))

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{SupertraceBlockTrace}}\left({escape(self.name)},\ {self.order}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>SupertraceBlockTrace({escape(self.name)} order={self.order})</code>"


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

        return -Expression.num(1) / 2

    @property
    def numerator_expression(self) -> Expression:
        """Return the prefactor-weighted trace numerator."""

        return (self.prefactor * self.trace.expression).expand()

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

    def blocks(self) -> tuple[FluctuationOperatorBlock, ...]:
        """Return the four heavy/light blocks in deterministic order."""

        return (self.heavy_heavy, self.heavy_light, self.light_heavy, self.light_light)

    def block_trace(self, name: str, *blocks: FluctuationOperatorBlock) -> SupertraceBlockTrace:
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
        )

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

    def power_type_traces(self) -> tuple[SupertraceBlockTrace, ...]:
        """Return cyclically unique traces used for power-type contributions."""

        traces: list[SupertraceBlockTrace] = []
        seen: set[tuple[str, ...]] = set()
        for trace in self.block_traces:
            if trace.cyclic_sector_key in seen:
                continue
            seen.add(trace.cyclic_sector_key)
            traces.append(trace)
        return tuple(traces)

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

    def power_type_expression_map(self, *, prefix: str = "power_type_supertrace") -> dict[str, Expression]:
        """Return deterministic expressions for power-type contributions."""

        entries: dict[str, Expression] = {}
        for contribution in self.power_type_contributions():
            entries.update(contribution.to_expression_map(prefix=prefix))
        return entries

    def power_type_eft_lagrangian(self, *, heavy_field_dimension: bool = False) -> Expression:
        """Return the summed EFT-truncated power-type off-shell Lagrangian contribution."""

        return sum_expr(
            contribution.eft_numerator_expression
            for contribution in self.power_type_contributions(heavy_field_dimension=heavy_field_dimension)
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
            return vakint.to_canonical(raw, short_form=short_form, engine=engine)
        if selected is VakintIntegralStage.TENSOR_REDUCED:
            return vakint.tensor_reduce(raw, engine=engine)
        return vakint.evaluate(raw, engine=engine)

    def power_type_matching_preview(
        self,
        *,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
    ) -> MatchingResult:
        """Return an explicitly incomplete matching-result preview for power-type terms."""

        off_shell = self.power_type_eft_lagrangian(heavy_field_dimension=heavy_field_dimension)
        selected_vakint_stage = VakintIntegralStage.from_user(vakint_stage)
        vakint_sum = self.power_type_vakint_integral_sum(
            heavy_field_dimension=heavy_field_dimension,
            include_light=include_light,
            stage=selected_vakint_stage,
            short_form=vakint_short_form,
            engine=vakint_engine,
        )
        supertraces = {
            **self.power_type_expression_map(prefix="power_type_supertrace"),
            "power_type_eft_lagrangian": off_shell,
            "power_type_vakint_integral_sum": vakint_sum,
            f"power_type_vakint_integral_sum[{selected_vakint_stage.value}]": vakint_sum,
        }
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=off_shell,
            on_shell_eft_lagrangian=off_shell,
            fluctuation_operators=self.fluctuation_operator.to_expression_map(),
            supertraces=supertraces,
            metadata={
                "stage": "power_type_preview",
                "complete": False,
                "loop_order": 1,
                "eft_order": self.eft_order,
                "max_trace_order": self.max_trace_order,
                "supertrace_kernel_count": self.supertrace_kernel_count,
                "power_type_contribution_count": self.power_type_contribution_count,
                "on_shell_reduced": False,
                "vakint_stage": selected_vakint_stage.value,
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
            name: vakint.to_canonical(expr, short_form=short_form, engine=engine)
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
            name: vakint.tensor_reduce(expr, engine=engine)
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
            name: vakint.evaluate(expr, engine=engine)
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
            **self.propagator_plan().to_expression_map(prefix=f"{prefix}.propagator"),
            **self.supertrace_expression_map(prefix=f"{prefix}.supertrace_kernel"),
            **self.supertrace_propagator_expression_map(prefix=f"{prefix}.supertrace_propagator_kernel"),
            **self.vakint_integral_expression_map(prefix=f"{prefix}.vakint_integral"),
            **self.power_type_expression_map(prefix=f"{prefix}.power_type_supertrace"),
            f"{prefix}[power_type_eft_lagrangian]": self.power_type_eft_lagrangian(),
            f"{prefix}[power_type_vakint_integral_sum]": self.power_type_vakint_integral_sum(),
        }
        return entries

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

    def entry(self, row: FluctuationBasisItem, column: FluctuationBasisItem) -> Expression:
        """Return one matrix entry identified by its row and column fields."""

        row_index = self._basis_index(_fluctuation_basis_expression(self.theory, row))
        column_index = self._basis_index(_fluctuation_basis_expression(self.theory, column))
        return self.matrix[row_index][column_index]

    def to_expression_map(self, *, prefix: str = "fluctuation_operator") -> dict[str, Expression]:
        """Return deterministic named entries suitable for ``MatchingResult``."""

        entries: dict[str, Expression] = {}
        for row in self.basis:
            for column in self.basis:
                key = f"{prefix}[{canonical_string(row)},{canonical_string(column)}]"
                entries[key] = self.entry(row, column)
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


@dataclass(frozen=True)
class MatchingExpressionComparison:
    """Comparison result for one named matching expression."""

    name: str
    equal: bool
    candidate: Expression | None = None
    reference: Expression | None = None
    canonical_equal: bool = False
    numeric_probe: NumericProbeResult | None = None

    def _repr_latex_(self) -> str:
        status = r"\checkmark" if self.equal else r"\times"
        return rf"$\mathrm{{{escape(self.name)}}}: {status}$"

    def _repr_html_(self) -> str:
        if self.canonical_equal:
            status = "canonically equal"
        elif self.numeric_probe is not None and self.numeric_probe.equal:
            status = "numeric-probe equal"
        elif self.numeric_probe is not None:
            status = f"different, max_abs_difference={self.numeric_probe.max_abs_difference:g}"
        else:
            status = "different"
        return f"<code>{escape(self.name)}: {status}</code>"


@dataclass(frozen=True)
class MatchingResultComparison:
    """Canonical comparison of two structured matching results."""

    candidate: MatchingResult
    reference: MatchingResult
    expressions: tuple[MatchingExpressionComparison, ...]

    @property
    def equal(self) -> bool:
        """Whether every compared expression is present and canonically equal."""

        return all(item.equal for item in self.expressions)

    @property
    def failed_names(self) -> tuple[str, ...]:
        """Names of expressions that are missing or canonically different."""

        return tuple(item.name for item in self.expressions if not item.equal)

    def assert_equal(self) -> None:
        """Raise ``AssertionError`` if any expression differs."""

        if not self.equal:
            raise AssertionError(f"Matching results differ for: {', '.join(self.failed_names)}")

    def _repr_latex_(self) -> str:
        status = r"\checkmark" if self.equal else r"\times"
        return rf"$\mathrm{{MatchingResultComparison}}\left({status},\ {len(self.expressions)}\right)$"

    def _repr_html_(self) -> str:
        status = "equal" if self.equal else f"different: {', '.join(escape(name) for name in self.failed_names)}"
        return f"<code>MatchingResultComparison({status})</code>"


@dataclass(frozen=True)
class MatchingResult:
    """Structured output of a pychete matching calculation.

    The result stores the major expression stages used by one-loop matching so
    tests and notebooks can inspect individual supertraces, off-shell and
    on-shell EFT Lagrangians, and final matching conditions without relying on
    Matchete's Mathematica data structures.
    """

    theory: Theory
    uv_lagrangian: Expression
    off_shell_eft_lagrangian: Expression
    on_shell_eft_lagrangian: Expression
    matching_conditions: dict[str, Expression] = field(default_factory=dict)
    fluctuation_operators: dict[str, Expression] = field(default_factory=dict)
    supertraces: dict[str, Expression] = field(default_factory=dict)
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    def expression(self, name: str) -> Expression:
        """Return a named expression stage from the matching result."""

        if name == "uv_lagrangian":
            return self.uv_lagrangian
        if name == "off_shell_eft_lagrangian":
            return self.off_shell_eft_lagrangian
        if name == "on_shell_eft_lagrangian":
            return self.on_shell_eft_lagrangian
        for collection in (self.matching_conditions, self.fluctuation_operators, self.supertraces):
            if name in collection:
                return collection[name]
        raise KeyError(f"Matching result has no expression {name!r}")

    def expression_names(self) -> tuple[str, ...]:
        """Return all named expression stages available on the result."""

        return (
            "uv_lagrangian",
            "off_shell_eft_lagrangian",
            "on_shell_eft_lagrangian",
            *self.matching_conditions,
            *self.fluctuation_operators,
            *self.supertraces,
        )

    def validate(self) -> None:
        """Validate every stored expression against the owning theory."""

        for name in self.expression_names():
            self.theory._validate_registered_expression(self.expression(name))

    def compare_to(
        self,
        reference: MatchingResult,
        *,
        names: Iterable[str] | None = None,
        probe_parameters: Sequence[Expression] | None = None,
        probe_samples: Sequence[Sequence[NumericValue]] | None = None,
        absolute_tolerance: float = 1e-9,
        relative_tolerance: float = 1e-9,
    ) -> MatchingResultComparison:
        """Compare this result to a reference result.

        Canonical Symbolica equality is the primary comparison. If
        ``probe_parameters`` and ``probe_samples`` are provided, expressions
        that are not canonically equal are additionally tested with
        Symbolica's evaluator-backed numeric probes.
        """

        if self.theory.name != reference.theory.name:
            raise ValueError(f"Cannot compare matching results from {self.theory.name!r} and {reference.theory.name!r}")
        if (probe_parameters is None) != (probe_samples is None):
            raise ValueError("probe_parameters and probe_samples must be provided together")
        if names is None:
            comparison_names = tuple(dict.fromkeys((*self.expression_names(), *reference.expression_names())))
        else:
            comparison_names = tuple(names)
        comparisons: list[MatchingExpressionComparison] = []
        for name in comparison_names:
            candidate_expr = _optional_expression(self, name)
            reference_expr = _optional_expression(reference, name)
            canonical_equal = (
                candidate_expr is not None
                and reference_expr is not None
                and _canonical_expr(candidate_expr) == _canonical_expr(reference_expr)
            )
            numeric_probe: NumericProbeResult | None = None
            equal = canonical_equal
            if (
                not canonical_equal
                and candidate_expr is not None
                and reference_expr is not None
                and probe_parameters is not None
                and probe_samples is not None
            ):
                numeric_probe = evaluator_probe_equal(
                    candidate_expr,
                    reference_expr,
                    probe_parameters,
                    probe_samples,
                    absolute_tolerance=absolute_tolerance,
                    relative_tolerance=relative_tolerance,
                )
                equal = numeric_probe.equal
            comparisons.append(
                MatchingExpressionComparison(
                    name=name,
                    equal=equal,
                    candidate=candidate_expr,
                    reference=reference_expr,
                    canonical_equal=canonical_equal,
                    numeric_probe=numeric_probe,
                )
            )
        return MatchingResultComparison(candidate=self, reference=reference, expressions=tuple(comparisons))

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{MatchingResult}}\left({self.theory.name},\ {len(self.supertraces)}\ \mathrm{{supertraces}}\right)$"

    def _repr_html_(self) -> str:
        return (
            f"<code>MatchingResult(theory={escape(self.theory.name)} "
            f"supertraces={len(self.supertraces)} "
            f"matching_conditions={len(self.matching_conditions)})</code>"
        )


class OneLoopMatchingNotImplementedError(NotImplementedError):
    """Raised while the one-loop matching engine is still under construction."""


def fluctuation_operator(
    theory: Theory,
    lagrangian: Expression,
    fields: FluctuationBasis | Iterable[FluctuationBasisItem] | None = None,
) -> FluctuationOperator:
    """Extract the Symbolica Hessian over a fluctuation basis.

    The current implementation computes the algebraic Hessian with respect to
    exact field expressions in ``fields``. If ``fields`` is omitted, pychete
    discovers a basis from tagged field atoms in ``lagrangian``. Derivative-
    valued field expressions may be supplied explicitly as independent basis
    entries; full differential operator assembly is a later one-loop matching
    stage.
    """

    theory._validate_registered_expression(lagrangian)
    basis_info = _normalize_fluctuation_basis(theory, lagrangian, fields)
    basis = basis_info.entries
    if not basis:
        raise ValueError("at least one fluctuation field is required")
    _validate_unique_fluctuation_basis(basis)
    variables = tuple(_fluctuation_variable(index) for index, _ in enumerate(basis))
    encoded = _encode_fluctuation_basis(lagrangian, basis, variables)
    matrix = tuple(
        tuple(
            _decode_fluctuation_basis(
                encoded.derivative(row_variable).derivative(column_variable),
                basis,
                variables,
            ).expand()
            for column_variable in variables
        )
        for row_variable in variables
    )
    return FluctuationOperator(theory=theory, basis=basis, matrix=matrix, modes=basis_info.modes)


def fluctuation_basis(theory: Theory, lagrangian: Expression) -> FluctuationBasis:
    """Discover fluctuation fields in a Lagrangian with Symbolica patterns."""

    theory._validate_registered_expression(lagrangian)
    fields = _discover_fluctuation_basis(lagrangian)
    return FluctuationBasis(theory=theory, modes=tuple(_fluctuation_mode(theory, field) for field in fields))


def one_loop_setup(
    theory: Theory,
    lagrangian: Expression,
    *,
    eft_order: int = 6,
    max_trace_order: int = 2,
    include_light_only: bool = False,
) -> OneLoopSetup:
    """Prepare the current native-backed one-loop matching input stages."""

    if max_trace_order < 1:
        raise ValueError("max_trace_order must be at least 1")
    theory._validate_registered_expression(lagrangian)
    operator = fluctuation_operator(theory, lagrangian)
    plan = operator.supertrace_plan()
    block_traces = tuple(
        trace
        for order in range(1, max_trace_order + 1)
        for trace in plan.closed_block_traces(order, include_light_only=include_light_only)
    )
    return OneLoopSetup(
        theory=theory,
        uv_lagrangian=lagrangian,
        eft_order=eft_order,
        fluctuation_operator=operator,
        supertrace_plan=plan,
        block_traces=block_traces,
    )


def _optional_expression(result: MatchingResult, name: str) -> Expression | None:
    try:
        return result.expression(name)
    except KeyError:
        return None


def _canonical_expr(expr: Expression) -> str:
    return canonical_string(expr.expand())


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
    return tuple(entries[key] for key in sorted(entries))


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


def _flatten_expression_slots(slots: Iterable[Iterable[Expression]]) -> tuple[Expression, ...]:
    return tuple(item for slot in slots for item in slot)


def _fluctuation_statistics(field_type: Expression, field_role: FieldRole) -> FluctuationStatistics:
    grassmann_roles = {FieldRole.GHOST, FieldRole.ANTI_GHOST}
    if bool(field_type == s.Fermion) or field_role in grassmann_roles:
        return FluctuationStatistics.FERMIONIC
    return FluctuationStatistics.BOSONIC


def _mode_index(modes: tuple[FluctuationMode, ...], field: Expression) -> int:
    key = canonical_string(field)
    for index, mode in enumerate(modes):
        if canonical_string(mode.field) == key:
            return index
    raise KeyError(f"Fluctuation basis has no field {key!r}")


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


def _sector_path_name(path: tuple[FluctuationSector, ...]) -> str:
    return "-".join(sector.value for sector in path)


def _cyclic_sector_key(sectors: tuple[str, ...]) -> tuple[str, ...]:
    if not sectors:
        return ()
    rotations = tuple(sectors[index:] + sectors[:index] for index in range(len(sectors)))
    return min(rotations)


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
    for block in blocks[1:]:
        product = product @ _block_matrix(block)
    out = Expression.num(0)
    for index, mode in enumerate(trace_modes):
        out = out + Expression.num(mode.supertrace_sign) * product[index, index].to_expression()
    return out.expand()


def _supertrace_block_product_expression(blocks: tuple[FluctuationOperatorBlock, ...]) -> Expression:
    product_matrix = blocks[0].matrix
    for block in blocks[1:]:
        product_matrix = _expression_matrix_multiply(product_matrix, block.matrix)
    return sum_expr(
        Expression.num(mode.supertrace_sign) * product_matrix[index][index]
        for index, mode in enumerate(blocks[0].rows)
    ).expand()


def _expression_matrix_multiply(left: ExpressionMatrix, right: ExpressionMatrix) -> ExpressionMatrix:
    if not left or not right:
        return ()
    row_count = len(left)
    inner_count = len(right)
    column_count = len(right[0])
    return tuple(
        tuple(
            sum_expr(left[row][inner] * right[inner][column] for inner in range(inner_count)).expand()
            for column in range(column_count)
        )
        for row in range(row_count)
    )


def _block_matrix(block: FluctuationOperatorBlock) -> Matrix:
    return Matrix.from_nested(block.matrix)


def _fluctuation_variable(index: int) -> Expression:
    return s.user(
        "pychete_internal",
        f"fluctuation_{index}",
        tags=[SymbolRole.PROJECT.value, "fluctuation_variable"],
        data={"role": "fluctuation_variable", "index": index},
    )


def _encode_fluctuation_basis(
    lagrangian: Expression,
    basis: tuple[Expression, ...],
    variables: tuple[Expression, ...],
) -> Expression:
    barred_replacements: list[Replacement] = []
    unbarred_replacements: list[Replacement] = []
    for field, variable in zip(basis, variables, strict=True):
        replacement = Replacement(field, variable)
        if is_bar_field(field):
            barred_replacements.append(replacement)
        else:
            unbarred_replacements.append(replacement)
    bar_protector = Replacement(
        bar_field_pattern(),
        bar_field_pattern(),
        s.FieldLabelWildcard.req_tag(SymbolRole.FIELD.value),
    )
    return lagrangian.replace_multiple([*barred_replacements, bar_protector, *unbarred_replacements])


def _decode_fluctuation_basis(
    expr: Expression,
    basis: tuple[Expression, ...],
    variables: tuple[Expression, ...],
) -> Expression:
    replacements = [Replacement(variable, field) for field, variable in zip(basis, variables, strict=True)]
    return expr.replace_multiple(replacements)


@dataclass(frozen=True)
class HeavyScalarSolution:
    """Order-by-order solution for a heavy scalar equation of motion."""

    field: FieldDefinition
    orders: dict[int, Expression]
    conjugate_orders: dict[int, Expression] | None = None

    @property
    def inclusive(self) -> Expression:
        """Sum all stored EFT orders for the heavy field."""

        out = Expression.num(0)
        for _, expr in sorted(self.orders.items()):
            out = out + expr
        return out.expand()

    @property
    def inclusive_conjugate(self) -> Expression:
        """Sum all stored EFT orders for the conjugate heavy field."""

        if self.conjugate_orders is None:
            return self.inclusive
        out = Expression.num(0)
        for _, expr in sorted(self.conjugate_orders.items()):
            out = out + expr
        return out.expand()

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{{self.field.name}}}: {latex_string(self.inclusive)}$"

    def _repr_html_(self) -> str:
        return f"<code>{escape(self.field.name)}: {escape(display_string(self.inclusive))}</code>"


def _zero_field_label(expr: Expression, label: Expression, *, conjugate: bool = False) -> Expression:
    pattern = bar_field_pattern(label) if conjugate else field_pattern(label)
    return expr.replace(pattern, Expression.num(0)).expand()


def _mass_squared(field: FieldDefinition) -> Expression:
    mass = field.mass_expr()
    if mass is None:
        raise ValueError(f"Heavy field {field.name} has no mass coupling")
    return mass**2


def _box(theory: Theory, expr: Expression, order: int) -> Expression:
    mu = theory.dummy_index(order)
    return apply_cd((mu, mu), expr)


def _solve_orders_from_source(theory: Theory, source: Expression, mass2: Expression, *, eft_order: int) -> dict[int, Expression]:
    orders: dict[int, Expression] = {}
    max_order = eft_order - 1
    previous_nonzero: Expression | None = None
    for order in range(1, max_order + 1):
        if order == 1:
            value = (source / mass2).expand()
        elif order % 2 == 0:
            value = Expression.num(0)
        else:
            if previous_nonzero is None:
                value = Expression.num(0)
            else:
                value = (-_box(theory, previous_nonzero, order) / mass2).expand()

        orders[order] = value
        if order % 2 == 1 and not is_zero(value):
            previous_nonzero = value
    return orders


def solve_heavy_scalar_eoms(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> dict[str, HeavyScalarSolution]:
    theory._validate_registered_expression(lagrangian)
    lagrangian = lagrangian.expand()
    solutions: dict[str, HeavyScalarSolution] = {}

    for field in theory.fields.values():
        if not field.heavy or not bool(field.type_expr == s.Scalar):
            continue

        mass2 = _mass_squared(field)

        if field.is_self_conjugate:
            eom = derive_eom(theory, lagrangian, field, eft_order=eft_order)
            source = _zero_field_label(eom, field.label)
            solution = HeavyScalarSolution(
                field=field,
                orders=_solve_orders_from_source(theory, source, mass2, eft_order=eft_order),
            )
        else:
            eom = derive_eom(theory, lagrangian, field, eft_order=eft_order, variation=FieldVariation.BAR)
            source = _zero_field_label(eom, field.label)
            conjugate_eom = derive_eom(theory, lagrangian, field, eft_order=eft_order, variation=FieldVariation.FIELD)
            conjugate_source = _zero_field_label(conjugate_eom, field.label, conjugate=True)
            solution = HeavyScalarSolution(
                field=field,
                orders=_solve_orders_from_source(theory, source, mass2, eft_order=eft_order),
                conjugate_orders=_solve_orders_from_source(theory, conjugate_source, mass2, eft_order=eft_order),
            )
        solutions[field.name] = solution

    return solutions


def _replace_heavy_fields(expr: Expression, solutions: dict[str, HeavyScalarSolution]) -> Expression:
    replacements: list[Replacement] = []
    for solution in solutions.values():
        label = solution.field.label

        def bar_solution(match: dict[Expression, Expression], solution: HeavyScalarSolution = solution) -> Expression:
            return apply_cd(list_items(match[s.FieldDerivativesWildcard]), solution.inclusive_conjugate)

        def field_solution(match: dict[Expression, Expression], solution: HeavyScalarSolution = solution) -> Expression:
            return apply_cd(list_items(match[s.FieldDerivativesWildcard]), solution.inclusive)

        replacements.append(Replacement(bar_field_pattern(label), bar_solution))
        replacements.append(Replacement(field_pattern(label), field_solution))
    return expr.replace_multiple(replacements).expand() if replacements else expr.expand()


def match_tree(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> Expression:
    solutions = solve_heavy_scalar_eoms(theory, lagrangian, eft_order=eft_order)
    replaced = _replace_heavy_fields(lagrangian, solutions)
    truncated = series_eft(replaced.expand(), theory, eft_order=eft_order, heavy_field_dimension=False)
    return truncated.expand()


def match_one_loop(theory: Theory, lagrangian: Expression, *, eft_order: int = 6) -> MatchingResult:
    """Run pychete's one-loop matching pipeline.

    The public API entry point exists so callers cannot accidentally receive a
    tree-level result for a one-loop request. The engine body is intentionally
    not stubbed with fake physics: it must be filled by the Symbolica/idenso/
    spenso/vakint pipeline and validated against the committed Matchete
    fixtures.
    """

    theory._validate_registered_expression(lagrangian)
    raise OneLoopMatchingNotImplementedError(
        "One-loop matching is not implemented yet. The committed default "
        "Matchete matching fixtures are available as acceptance targets under "
        "assets/validation/pychete/*.matching_fixture.json."
    )
