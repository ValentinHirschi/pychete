from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Iterable, Iterator, Mapping, Sequence, TypeAlias

from symbolica import Expression

from .symbols import SymbolDataKey, SymbolRole, s, safe_symbol_name
from .theory import Theory


@dataclass(frozen=True)
class BosonicCDEExpansionPlanEntry:
    """One generated CDE expansion request for a selected interaction trace."""

    trace_name: str
    expansion_indices: tuple[tuple[Expression, ...], ...]
    total_order: int
    slot_orders: tuple[int, ...]
    label: str

    def as_explicit_map(self) -> dict[str, tuple[tuple[Expression, ...], ...]]:
        """Return this entry as the legacy single-trace explicit expansion map."""

        return {self.trace_name: self.expansion_indices}

    def _repr_latex_(self) -> str:
        orders = ",".join(str(order) for order in self.slot_orders)
        return rf"$\mathrm{{BosonicCDEExpansionPlanEntry}}\left({escape(self.trace_name)},\ [{orders}]\right)$"

    def _repr_html_(self) -> str:
        return (
            f"<code>BosonicCDEExpansionPlanEntry({escape(self.trace_name)} "
            f"orders={self.slot_orders} total={self.total_order})</code>"
        )


@dataclass(frozen=True)
class BosonicCDEExpansionPlan:
    """Generated CDE expansion plan for selected interaction-supertrace families."""

    theory: Theory
    entries: tuple[BosonicCDEExpansionPlanEntry, ...]
    trace_names: tuple[str, ...]
    max_total_order: int
    max_slot_order: int | None = None

    @property
    def entry_count(self) -> int:
        """Number of generated trace-slot expansion entries."""

        return len(self.entries)

    @property
    def trace_count(self) -> int:
        """Number of selected trace families represented by the plan."""

        return len(self.trace_names)

    def by_trace(self) -> dict[str, tuple[BosonicCDEExpansionPlanEntry, ...]]:
        """Return generated entries grouped by source trace name."""

        grouped: dict[str, list[BosonicCDEExpansionPlanEntry]] = {trace_name: [] for trace_name in self.trace_names}
        for entry in self.entries:
            grouped.setdefault(entry.trace_name, []).append(entry)
        return {trace_name: tuple(entries) for trace_name, entries in grouped.items()}

    def explicit_maps(self) -> tuple[dict[str, tuple[tuple[Expression, ...], ...]], ...]:
        """Return legacy one-entry expansion maps for each generated plan entry."""

        return tuple(entry.as_explicit_map() for entry in self.entries)

    def __iter__(self) -> Iterator[BosonicCDEExpansionPlanEntry]:
        """Iterate over generated plan entries in deterministic evaluation order."""

        return iter(self.entries)

    def __len__(self) -> int:
        """Return ``entry_count`` for convenient notebook inspection."""

        return self.entry_count

    def _repr_latex_(self) -> str:
        max_slot = r"\infty" if self.max_slot_order is None else str(self.max_slot_order)
        return (
            rf"$\mathrm{{BosonicCDEExpansionPlan}}\left({self.trace_count}\ \mathrm{{traces}},\ "
            rf"{self.entry_count}\ \mathrm{{entries}},\ N={self.max_total_order},\ n_\max={max_slot}\right)$"
        )

    def _repr_html_(self) -> str:
        max_slot = "unbounded" if self.max_slot_order is None else str(self.max_slot_order)
        return (
            f"<code>BosonicCDEExpansionPlan(traces={self.trace_count} entries={self.entry_count} "
            f"max_total_order={self.max_total_order} max_slot_order={max_slot})</code>"
        )


@dataclass(frozen=True)
class WilsonLineExpansionPlanEntry:
    """One generated Wilson-line expansion request for a selected interaction trace."""

    trace_name: str
    expansion_indices: tuple[tuple[Expression, ...], ...]
    total_order: int
    slot_orders: tuple[int, ...]
    label: str

    def as_explicit_map(self) -> dict[str, tuple[tuple[Expression, ...], ...]]:
        """Return this entry as a single-trace explicit expansion map."""

        return {self.trace_name: self.expansion_indices}

    def _repr_latex_(self) -> str:
        orders = ",".join(str(order) for order in self.slot_orders)
        return rf"$\mathrm{{WilsonLineExpansionPlanEntry}}\left({escape(self.trace_name)},\ [{orders}]\right)$"

    def _repr_html_(self) -> str:
        return (
            f"<code>WilsonLineExpansionPlanEntry({escape(self.trace_name)} "
            f"orders={self.slot_orders} total={self.total_order})</code>"
        )


@dataclass(frozen=True)
class WilsonLineExpansionPlan:
    """Generated Wilson-line expansion plan for selected interaction traces."""

    theory: Theory
    entries: tuple[WilsonLineExpansionPlanEntry, ...]
    trace_names: tuple[str, ...]
    max_total_order: int
    max_slot_order: int | None = None

    @property
    def entry_count(self) -> int:
        """Number of generated trace-slot expansion entries."""

        return len(self.entries)

    @property
    def trace_count(self) -> int:
        """Number of selected trace families represented by the plan."""

        return len(self.trace_names)

    def by_trace(self) -> dict[str, tuple[WilsonLineExpansionPlanEntry, ...]]:
        """Return generated entries grouped by source trace name."""

        grouped: dict[str, list[WilsonLineExpansionPlanEntry]] = {trace_name: [] for trace_name in self.trace_names}
        for entry in self.entries:
            grouped.setdefault(entry.trace_name, []).append(entry)
        return {trace_name: tuple(entries) for trace_name, entries in grouped.items()}

    def explicit_maps(self) -> tuple[dict[str, tuple[tuple[Expression, ...], ...]], ...]:
        """Return one-entry expansion maps for each generated plan entry."""

        return tuple(entry.as_explicit_map() for entry in self.entries)

    def filtered(
        self,
        *,
        total_orders: Iterable[int] | None = None,
        labels: Iterable[str] | None = None,
    ) -> WilsonLineExpansionPlan:
        """Return a plan containing only entries matching the requested metadata."""

        allowed_orders = None if total_orders is None else frozenset(total_orders)
        allowed_labels = None if labels is None else frozenset(labels)
        if allowed_orders is not None and any(order < 0 for order in allowed_orders):
            raise ValueError("Wilson-line total-order filters must be non-negative")
        entries = tuple(
            entry
            for entry in self.entries
            if (allowed_orders is None or entry.total_order in allowed_orders)
            and (allowed_labels is None or entry.label in allowed_labels)
        )
        if not entries:
            raise ValueError("Wilson-line plan filters removed every generated entry")
        trace_names = tuple(dict.fromkeys(entry.trace_name for entry in entries))
        return WilsonLineExpansionPlan(
            theory=self.theory,
            entries=entries,
            trace_names=trace_names,
            max_total_order=self.max_total_order,
            max_slot_order=self.max_slot_order,
        )

    def __iter__(self) -> Iterator[WilsonLineExpansionPlanEntry]:
        """Iterate over generated plan entries in deterministic evaluation order."""

        return iter(self.entries)

    def __len__(self) -> int:
        """Return ``entry_count`` for convenient notebook inspection."""

        return self.entry_count

    def _repr_latex_(self) -> str:
        max_slot = r"\infty" if self.max_slot_order is None else str(self.max_slot_order)
        return (
            rf"$\mathrm{{WilsonLineExpansionPlan}}\left({self.trace_count}\ \mathrm{{traces}},\ "
            rf"{self.entry_count}\ \mathrm{{entries}},\ N={self.max_total_order},\ n_\max={max_slot}\right)$"
        )

    def _repr_html_(self) -> str:
        max_slot = "unbounded" if self.max_slot_order is None else str(self.max_slot_order)
        return (
            f"<code>WilsonLineExpansionPlan(traces={self.trace_count} entries={self.entry_count} "
            f"max_total_order={self.max_total_order} max_slot_order={max_slot})</code>"
        )


BosonicCDEExpansionRequest: TypeAlias = (
    Mapping[str, Sequence[Sequence[Expression]]] | BosonicCDEExpansionPlan
)
WilsonLineExpansionRequest: TypeAlias = (
    Mapping[str, Sequence[Sequence[Expression]]] | WilsonLineExpansionPlan
)


def normalize_expansion_indices(
    expansion_indices: Sequence[Sequence[Expression]],
) -> tuple[tuple[Expression, ...], ...]:
    return tuple(tuple(indices) for indices in expansion_indices)


def slot_order_allocations(
    total_order: int,
    slot_count: int,
    *,
    max_slot_order: int | None,
) -> tuple[tuple[int, ...], ...]:
    if total_order < 0:
        raise ValueError("total_order must be non-negative")
    if slot_count < 1:
        raise ValueError("slot_count must be positive")
    if slot_count == 1:
        if max_slot_order is not None and total_order > max_slot_order:
            return ()
        return ((total_order,),)
    allocations: list[tuple[int, ...]] = []
    first_max = total_order if max_slot_order is None else min(total_order, max_slot_order)
    for first_order in range(first_max + 1):
        for tail in slot_order_allocations(
            total_order - first_order,
            slot_count - 1,
            max_slot_order=max_slot_order,
        ):
            allocations.append((first_order, *tail))
    return tuple(allocations)


def cde_plan_expansion_indices(
    theory: Theory,
    *,
    trace_name: str,
    entry_index: int,
    slot_orders: tuple[int, ...],
    index_prefix: str,
) -> tuple[tuple[Expression, ...], ...]:
    trace_key = safe_symbol_name(trace_name)
    prefix_key = safe_symbol_name(index_prefix)
    return _plan_expansion_indices(
        theory,
        trace_key=trace_key,
        prefix_key=prefix_key,
        entry_index=entry_index,
        slot_orders=slot_orders,
        tags=("cde", "cde_plan"),
    )


def cde_plan_entry_label(trace_name: str, entry_index: int, slot_orders: tuple[int, ...]) -> str:
    order_label = "_".join(str(order) for order in slot_orders)
    return f"{trace_name}#cde{entry_index}_o{order_label}"


def wilson_line_plan_expansion_indices(
    theory: Theory,
    *,
    trace_name: str,
    entry_index: int,
    slot_orders: tuple[int, ...],
    index_prefix: str,
) -> tuple[tuple[Expression, ...], ...]:
    trace_key = safe_symbol_name(trace_name)
    prefix_key = safe_symbol_name(index_prefix)
    return _plan_expansion_indices(
        theory,
        trace_key=trace_key,
        prefix_key=prefix_key,
        entry_index=entry_index,
        slot_orders=slot_orders,
        tags=("wilson_line", "wilson_line_plan"),
    )


def wilson_line_plan_entry_label(trace_name: str, entry_index: int, slot_orders: tuple[int, ...]) -> str:
    order_label = "_".join(str(order) for order in slot_orders)
    return f"{trace_name}#wilson{entry_index}_o{order_label}"


def wilson_line_trace_name_from_entry_label(entry_label: str) -> str:
    return entry_label.split("#wilson", 1)[0]


def cde_expansion_request_metadata(expansion_request: BosonicCDEExpansionRequest) -> dict[str, Any]:
    if isinstance(expansion_request, BosonicCDEExpansionPlan):
        return {
            "interaction_bosonic_cde_trace_count": expansion_request.trace_count,
            "interaction_bosonic_cde_plan_entry_count": expansion_request.entry_count,
            "interaction_bosonic_cde_planned": True,
            "interaction_bosonic_cde_plan_trace_names": expansion_request.trace_names,
            "interaction_bosonic_cde_plan_max_total_order": expansion_request.max_total_order,
            "interaction_bosonic_cde_plan_max_slot_order": expansion_request.max_slot_order,
        }
    return {
        "interaction_bosonic_cde_trace_count": len(expansion_request),
        "interaction_bosonic_cde_plan_entry_count": len(expansion_request),
        "interaction_bosonic_cde_planned": False,
        "interaction_bosonic_cde_plan_trace_names": tuple(expansion_request),
        "interaction_bosonic_cde_plan_max_total_order": None,
        "interaction_bosonic_cde_plan_max_slot_order": None,
    }


def cde_expansion_trace_names(expansion_request: BosonicCDEExpansionRequest) -> tuple[str, ...]:
    if isinstance(expansion_request, BosonicCDEExpansionPlan):
        return expansion_request.trace_names
    return tuple(expansion_request)


def wilson_line_expansion_request_metadata(expansion_request: WilsonLineExpansionRequest) -> dict[str, Any]:
    if isinstance(expansion_request, WilsonLineExpansionPlan):
        return {
            "interaction_wilson_line_trace_count": expansion_request.trace_count,
            "interaction_wilson_line_trace_names": expansion_request.trace_names,
            "interaction_wilson_line_plan_entry_count": expansion_request.entry_count,
            "interaction_wilson_line_planned": True,
            "interaction_wilson_line_plan_trace_names": expansion_request.trace_names,
            "interaction_wilson_line_plan_max_total_order": expansion_request.max_total_order,
            "interaction_wilson_line_plan_max_slot_order": expansion_request.max_slot_order,
        }
    return {
        "interaction_wilson_line_trace_count": len(expansion_request),
        "interaction_wilson_line_plan_entry_count": len(expansion_request),
        "interaction_wilson_line_planned": False,
        "interaction_wilson_line_plan_trace_names": tuple(expansion_request),
        "interaction_wilson_line_plan_max_total_order": None,
        "interaction_wilson_line_plan_max_slot_order": None,
        "interaction_wilson_line_trace_names": tuple(expansion_request),
    }


def wilson_line_expansion_trace_names(expansion_request: WilsonLineExpansionRequest) -> tuple[str, ...]:
    if isinstance(expansion_request, WilsonLineExpansionPlan):
        return expansion_request.trace_names
    return tuple(expansion_request)


def generated_slot_order_tuples(
    slot_count: int,
    *,
    max_total_order: int,
    max_slot_order: int | None,
) -> tuple[tuple[int, ...], ...]:
    """Return deterministic derivative-order allocations for generated plans."""

    return tuple(
        allocation
        for total_order in range(max_total_order + 1)
        for allocation in slot_order_allocations(
            total_order,
            slot_count,
            max_slot_order=max_slot_order,
        )
    )


def _plan_expansion_indices(
    theory: Theory,
    *,
    trace_key: str,
    prefix_key: str,
    entry_index: int,
    slot_orders: tuple[int, ...],
    tags: tuple[str, str],
) -> tuple[tuple[Expression, ...], ...]:
    slots: list[tuple[Expression, ...]] = []
    for slot_index, slot_order in enumerate(slot_orders):
        indices: list[Expression] = []
        for derivative_index in range(slot_order):
            label = f"{prefix_key}_{trace_key}_{entry_index}_{slot_index}_{derivative_index}"
            label_symbol = theory.symbol(
                label,
                role=SymbolRole.INDEX,
                data={SymbolDataKey.NAME.value: label},
                tags=tags,
            )
            indices.append(theory.index(label_symbol, s.Lorentz))
        slots.append(tuple(indices))
    return tuple(slots)


__all__ = [
    "BosonicCDEExpansionPlan",
    "BosonicCDEExpansionPlanEntry",
    "BosonicCDEExpansionRequest",
    "WilsonLineExpansionPlan",
    "WilsonLineExpansionPlanEntry",
    "WilsonLineExpansionRequest",
    "cde_expansion_request_metadata",
    "cde_expansion_trace_names",
    "cde_plan_entry_label",
    "cde_plan_expansion_indices",
    "generated_slot_order_tuples",
    "normalize_expansion_indices",
    "slot_order_allocations",
    "wilson_line_expansion_request_metadata",
    "wilson_line_expansion_trace_names",
    "wilson_line_plan_entry_label",
    "wilson_line_plan_expansion_indices",
    "wilson_line_trace_name_from_entry_label",
]
