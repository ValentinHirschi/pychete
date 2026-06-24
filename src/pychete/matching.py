from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from html import escape
from itertools import product
from typing import Iterable, Iterator, Sequence, TypeAlias

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
    list_items,
)
from .functional import apply_cd, derive_eom
from .symbols import SymbolRole, canonical_string, display_string, latex_string, s
from .theory import (
    FieldDefinition,
    FieldHandle,
    FieldMassKind,
    FieldVariation,
    Theory,
    field_mass_kind_from_label,
    field_self_conjugate_from_label,
    field_type_from_label,
)
from .validation import NumericProbeResult, NumericValue, evaluator_probe_equal

FluctuationBasisItem: TypeAlias = FieldHandle | FieldDefinition | str | Expression


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
    mass_kind: FieldMassKind
    statistics: FluctuationStatistics
    self_conjugate: bool
    conjugated: bool

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

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{FluctuationMode}}\left({latex_string(self.field)}\right)$"

    def _repr_html_(self) -> str:
        return (
            f"<code>FluctuationMode({escape(display_string(self.field))} "
            f"{self.mass_kind.value} {self.statistics.value})</code>"
        )


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

    def to_expression_map(self, *, prefix: str = "supertrace_block_trace") -> dict[str, Expression]:
        """Return this trace kernel as a deterministic named expression."""

        return {f"{prefix}[{self.name}]": self.expression}

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{SupertraceBlockTrace}}\left({escape(self.name)},\ {self.order}\right)$"

    def _repr_html_(self) -> str:
        return f"<code>SupertraceBlockTrace({escape(self.name)} order={self.order})</code>"


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
    field_type = field_type_from_label(label)
    return FluctuationMode(
        theory=theory,
        field=field,
        base_field=base,
        field_type=field_type,
        mass_kind=field_mass_kind_from_label(label),
        statistics=_fluctuation_statistics(field_type),
        self_conjugate=field_self_conjugate_from_label(label),
        conjugated=is_bar_field(field),
    )


def _fluctuation_statistics(field_type: Expression) -> FluctuationStatistics:
    return FluctuationStatistics.FERMIONIC if bool(field_type == s.Fermion) else FluctuationStatistics.BOSONIC


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


def _supertrace_block_product(blocks: tuple[FluctuationOperatorBlock, ...]) -> Expression:
    trace_modes = blocks[0].rows
    if not trace_modes or any(not block.rows or not block.columns for block in blocks):
        return Expression.num(0)
    product = _block_matrix(blocks[0])
    for block in blocks[1:]:
        product = product @ _block_matrix(block)
    out = Expression.num(0)
    for index, mode in enumerate(trace_modes):
        out = out + Expression.num(mode.supertrace_sign) * product[index, index].to_expression()
    return out.expand()


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
