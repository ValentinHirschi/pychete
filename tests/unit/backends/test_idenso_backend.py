from __future__ import annotations

from symbolica import Expression, S
from symbolica.community import idenso as native_idenso

from pychete.backends import idenso
from pychete.group_algebra import simplify_color, simplify_gamma, simplify_metrics
from pychete.symbols import canonical_string, s


def _same(lhs, rhs) -> bool:
    return canonical_string(lhs) == canonical_string(rhs)


def test_idenso_backend_delegates_core_simplifiers() -> None:
    x = S("x")

    assert _same(idenso.simplify_gamma(x), native_idenso.simplify_gamma(x))
    assert _same(idenso.simplify_color(x), native_idenso.simplify_color(x))
    assert _same(idenso.simplify_metrics(x), native_idenso.simplify_metrics(x))
    assert _same(idenso.to_dots(x), native_idenso.to_dots(x))


def test_idenso_backend_exposes_index_helpers() -> None:
    x = S("x")
    header = S("wrapped")

    assert idenso.list_dangling(x) == native_idenso.list_dangling(x)
    assert _same(idenso.wrap_indices(x, header), native_idenso.wrap_indices(x, header))
    assert _same(idenso.wrap_dummies(x, header), native_idenso.wrap_dummies(x, header))
    assert _same(idenso.cook_indices(x), native_idenso.cook_indices(x))


def test_existing_group_algebra_shim_uses_idenso_backend() -> None:
    x = S("x")

    assert _same(simplify_gamma(x), idenso.simplify_gamma(x))
    assert _same(simplify_color(x), idenso.simplify_color(x))
    assert _same(simplify_metrics(x), idenso.simplify_metrics(x))


def test_idenso_pipeline_is_native_noop_for_plain_symbol() -> None:
    x = S("x")

    assert _same(idenso.simplify_index_algebra(x, dots=True), x)


def test_idenso_pipeline_simplifies_pychete_projectors_through_native_bridge() -> None:
    expr = s.PR**3 + s.PL**2 + s.PR * s.PL + S("x") * s.PL * s.PR

    simplified = idenso.simplify_index_algebra(expr, expand=False, color=False, metrics=False)

    assert _same(simplified, s.PR + s.PL)
    assert _same(idenso.simplify_pychete_dirac_projectors(s.PR**2), s.PR)
    assert _same(idenso.simplify_pychete_dirac_projectors(s.PL**2), s.PL)
    assert _same(idenso.simplify_pychete_dirac_projectors(s.PR * s.PL), Expression.num(0))
