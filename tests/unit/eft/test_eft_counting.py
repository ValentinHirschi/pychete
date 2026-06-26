from __future__ import annotations

from symbolica import Expression

from pychete import (
    FieldMassKind,
    SymbolRole,
    Theory,
    canonical_string,
    infer_coupling_mass_dimensions,
    operator_dimension,
    series_eft,
    s,
)
from pychete.expr import list_expr

from tests.conftest import assert_expr_equal


def test_series_eft_counts_light_masses_and_scalar_fields() -> None:
    theory = Theory("eft")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    m = theory.coupling_handle("m")

    expr = m() ** 2 * phi() ** 4 + m() ** 2 * phi() ** 6

    assert_expr_equal(series_eft(expr, theory, eft_order=6), m() ** 2 * phi() ** 4)


def test_series_eft_counts_inverse_light_masses() -> None:
    theory = Theory("eft_inverse")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    m = theory.coupling_handle("m")

    expr = phi() ** 6 / m() ** 2 + phi() ** 8 / m() ** 2 + phi() ** 10 / m() ** 2
    expected = phi() ** 6 / m() ** 2 + phi() ** 8 / m() ** 2

    assert_expr_equal(series_eft(expr, theory, eft_order=6), expected)


def test_series_eft_uses_symbolica_marker_coefficients_for_exact_and_inclusive_orders() -> None:
    theory = Theory("eft_exact")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    m = theory.coupling_handle("m")

    dim_three = m() * phi() ** 2
    dim_six = m() ** 2 * phi() ** 4
    dim_eight = phi() ** 8
    expr = dim_three + dim_six + dim_eight

    assert_expr_equal(series_eft(expr, theory, eft_order=6), dim_three + dim_six)
    assert_expr_equal(series_eft(expr, theory, eft_order=(6,)), dim_six)


def test_series_eft_extracts_marker_powers_from_noncommutative_chains() -> None:
    theory = Theory("eft_ncm")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    psi = theory.define_field("psi", s.Fermion, self_conjugate=False, mass=0)
    chain = phi() * s.NCM(s.Bar(psi()), s.PR, psi())
    higher = phi() ** 4 * s.NCM(s.Bar(psi()), s.PL, psi())
    expr = chain + higher

    assert_expr_equal(series_eft(expr, theory, eft_order=3), Expression.num(0))
    assert_expr_equal(series_eft(expr, theory, eft_order=4), chain)
    assert_expr_equal(series_eft(expr, theory, eft_order=(4,)), chain)
    assert "eft_order_parameter" not in canonical_string(series_eft(expr, theory, eft_order=6))


def test_series_eft_extracts_marker_powers_from_linear_external_wrappers_in_chains() -> None:
    theory = Theory("eft_ncm_transp")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    psi = theory.define_field("psi", s.Fermion, self_conjugate=False, mass=0)
    transpose = theory.define_external("Transp")
    chain = phi() * s.NCM(transpose(psi()), s.PR, psi())
    higher = phi() ** 4 * s.NCM(transpose(psi()), s.PL, psi())
    expr = chain + higher

    assert_expr_equal(series_eft(expr, theory, eft_order=3), Expression.num(0))
    assert_expr_equal(series_eft(expr, theory, eft_order=4), chain)
    assert_expr_equal(series_eft(expr, theory, eft_order=(4,)), chain)
    assert "eft_order_parameter" not in canonical_string(series_eft(expr, theory, eft_order=6))


def test_operator_dimension_uses_pattern_weighted_atoms() -> None:
    theory = Theory("eft_weighted_atoms")
    heavy = theory.define_field("heavy", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    psi = theory.define_field("psi", s.Fermion, self_conjugate=False, mass=0)
    vector = theory.define_field("A", s.Vector(theory.symbol("G", role=SymbolRole.GROUP)), self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    strength = s.FieldStrength(vector.label, list_expr(mu, nu), list_expr(), list_expr())

    assert operator_dimension(heavy(), theory) == 2
    assert operator_dimension(heavy(), theory, heavy_field_dimension=False) == 1
    assert operator_dimension(s.CD(mu, heavy()), theory, heavy_field_dimension=False) == 2
    assert operator_dimension(s.CD(list_expr(mu, mu), heavy()), theory, heavy_field_dimension=False) == 3
    assert operator_dimension(s.Bar(psi()), theory) == 1.5
    assert operator_dimension(strength, theory) == 2


def test_infer_coupling_mass_dimensions_uses_symbolica_rational_powers() -> None:
    theory = Theory("eft_infer_coupling_dimensions")
    theory.define_gauge_group("U1X", s.U1, "g", "B")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    psi = theory.define_field("psi", s.Fermion, self_conjugate=False, mass=0)
    cubic = theory.define_coupling("A", self_conjugate=True)
    quartic = theory.define_coupling("kappa", self_conjugate=True)
    heavy_cubic = theory.define_coupling("muphi", self_conjugate=True)
    yukawa = theory.define_coupling("y")
    inverse_mass = theory.define_coupling("rho", self_conjugate=True)
    heavy_mass = theory.coupling_handle("M")
    light_mass = theory.coupling_handle("m")

    lagrangian = (
        -cubic() * heavy() * phi() ** 2
        - quartic() * heavy() ** 2 * phi() ** 2 / 2
        - heavy_cubic() * heavy() ** 3 / 6
        - yukawa() * phi() * s.NCM(s.Bar(psi()), s.PR, psi())
        - inverse_mass() * phi() ** 4 / heavy_mass()
    )

    dimensions = infer_coupling_mass_dimensions(theory, lagrangian)

    assert dimensions["A"] == 1
    assert dimensions["kappa"] == 0
    assert dimensions["muphi"] == 1
    assert dimensions["y"] == 0
    assert dimensions["rho"] == 1
    assert dimensions["M"] == 1
    assert dimensions["m"] == 1
    assert dimensions["g"] == 0
