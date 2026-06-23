from __future__ import annotations

from pychete import Theory, series_eft, s

from tests.conftest import assert_expr_equal


def test_series_eft_counts_light_masses_and_scalar_fields() -> None:
    theory = Theory("eft")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=("Light", "m"))
    m = theory.coupling_handle("m")

    expr = m() ** 2 * phi() ** 4 + m() ** 2 * phi() ** 6

    assert_expr_equal(series_eft(expr, theory, eft_order=6), m() ** 2 * phi() ** 4)


def test_series_eft_counts_inverse_light_masses() -> None:
    theory = Theory("eft_inverse")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=("Light", "m"))
    m = theory.coupling_handle("m")

    expr = phi() ** 6 / m() ** 2 + phi() ** 8 / m() ** 2 + phi() ** 10 / m() ** 2
    expected = phi() ** 6 / m() ** 2 + phi() ** 8 / m() ** 2

    assert_expr_equal(series_eft(expr, theory, eft_order=6), expected)
