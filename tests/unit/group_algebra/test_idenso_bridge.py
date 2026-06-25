from __future__ import annotations

from symbolica import S

from pychete import s
from pychete.group_algebra import chiral_projector_tensor, gamma_tensor, simplify_gamma, spin_metric_tensor

from tests.conftest import assert_expr_equal


def test_idenso_gamma_bridge_simplifies_symbolic_d_contraction() -> None:
    dim = S("D")
    mu = S("mu")
    a = S("a")
    b = S("b")
    c = S("c")

    expr = gamma_tensor(mu, a, b, dim=dim) * gamma_tensor(mu, b, c, dim=dim)

    assert_expr_equal(simplify_gamma(expr), dim * spin_metric_tensor(a, c, dim=dim))


def test_idenso_projector_bridge_exposes_explicit_dimension_identities() -> None:
    a = S("a")
    b = S("b")
    c = S("c")

    expr = chiral_projector_tensor(s.PR, a, b, dim=4) * chiral_projector_tensor(s.PL, b, c, dim=4)

    assert_expr_equal(simplify_gamma(expr), 0)
