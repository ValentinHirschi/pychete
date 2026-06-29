from __future__ import annotations

import pytest

from pychete.matching_expansion_plans import WilsonLineExpansionPlan, WilsonLineExpansionPlanEntry
from pychete.theory import Theory


@pytest.mark.unit
@pytest.mark.matching
def test_wilson_line_plan_filters_total_orders_by_trace() -> None:
    theory = Theory("wilson_line_plan_filter")
    mu = theory.lorentz_index("mu")
    entries = (
        WilsonLineExpansionPlanEntry("traceA", ((mu,),), 0, (0,), "traceA#w0"),
        WilsonLineExpansionPlanEntry("traceA", ((mu,),), 2, (2,), "traceA#w2"),
        WilsonLineExpansionPlanEntry("traceB", ((mu,),), 1, (1,), "traceB#w1"),
        WilsonLineExpansionPlanEntry("traceB", ((mu,),), 3, (3,), "traceB#w3"),
        WilsonLineExpansionPlanEntry("traceC", ((mu,),), 4, (4,), "traceC#w4"),
    )
    plan = WilsonLineExpansionPlan(
        theory=theory,
        entries=entries,
        trace_names=("traceA", "traceB", "traceC"),
        max_total_order=4,
        max_slot_order=4,
    )

    filtered = plan.filtered(total_orders_by_trace={"traceA": (2,), "traceB": (1,)})

    assert [entry.label for entry in filtered.entries] == ["traceA#w2", "traceB#w1", "traceC#w4"]
    assert filtered.trace_names == ("traceA", "traceB", "traceC")


@pytest.mark.unit
@pytest.mark.matching
def test_wilson_line_plan_rejects_negative_per_trace_total_order() -> None:
    theory = Theory("wilson_line_plan_filter_negative")
    mu = theory.lorentz_index("mu")
    plan = WilsonLineExpansionPlan(
        theory=theory,
        entries=(WilsonLineExpansionPlanEntry("traceA", ((mu,),), 0, (0,), "traceA#w0"),),
        trace_names=("traceA",),
        max_total_order=0,
        max_slot_order=0,
    )

    with pytest.raises(ValueError, match="per-trace total-order filters must be non-negative"):
        plan.filtered(total_orders_by_trace={"traceA": (-1,)})
