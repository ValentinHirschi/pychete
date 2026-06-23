from __future__ import annotations

from pychete import FieldMassKind, Theory, derive_eom, match_tree, solve_heavy_scalar_eoms, s

from tests.conftest import assert_expr_equal


def _heavy_scalar_theory() -> tuple[Theory, object, object, object]:
    theory = Theory("heavy_scalar")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    g = theory.define_coupling("g", self_conjugate=True)
    return theory, heavy, light, g


def test_heavy_scalar_eom_and_fixed_order_solution_match_reference() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    mu = theory.lorentz_index("d")
    u3 = theory.lorentz_index("u3")
    mass = theory.coupling_handle("M")
    lagrangian = theory.free_lag(heavy, phi) - s.half * g() * heavy() * phi() ** 2

    eom = derive_eom(theory, lagrangian, heavy)
    expected_eom = -mass() ** 2 * heavy() - heavy(derivatives=[mu, mu]) - s.half * g() * phi() ** 2
    assert_expr_equal(eom, expected_eom)

    solution = solve_heavy_scalar_eoms(theory, lagrangian, eft_order=6)["S"]
    assert_expr_equal(solution.orders[1], -s.half * g() * phi() ** 2 / mass() ** 2)
    assert_expr_equal(solution.orders[2], s.zero)
    assert_expr_equal(
        solution.orders[3],
        g() * (phi(derivatives=[u3]) ** 2 + phi() * phi(derivatives=[u3, u3])) / mass() ** 4,
    )


def test_heavy_scalar_tree_match_through_dimension_six() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    mu = theory.lorentz_index("d")
    mass = theory.coupling_handle("M")
    lagrangian = theory.free_lag(heavy, phi) - s.half * g() * heavy() * phi() ** 2

    matched = match_tree(theory, lagrangian, eft_order=6)
    expected = (
        s.half * phi(derivatives=[mu]) ** 2
        + (s.half / 4) * g() ** 2 * phi() ** 4 / mass() ** 2
        + s.half * g() ** 2 * phi() ** 2 * phi(derivatives=[mu]) ** 2 / mass() ** 4
    )

    assert_expr_equal(matched, expected)


def test_tree_match_supports_several_independent_diagonal_heavy_scalars() -> None:
    theory = Theory("two_heavy_scalars")
    s_field = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "MS"))
    t_field = theory.define_field("T", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "MT"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    g_s = theory.define_coupling("gS", self_conjugate=True)
    g_t = theory.define_coupling("gT", self_conjugate=True)
    mu = theory.lorentz_index("d")
    m_s = theory.coupling_handle("MS")
    m_t = theory.coupling_handle("MT")

    lagrangian = (
        theory.free_lag(s_field, t_field, phi)
        - s.half * g_s() * s_field() * phi() ** 2
        - s.half * g_t() * t_field() * phi() ** 2
    )

    matched = match_tree(theory, lagrangian, eft_order=6)
    expected = (
        s.half * phi(derivatives=[mu]) ** 2
        + (s.half / 4) * g_s() ** 2 * phi() ** 4 / m_s() ** 2
        + s.half * g_s() ** 2 * phi() ** 2 * phi(derivatives=[mu]) ** 2 / m_s() ** 4
        + (s.half / 4) * g_t() ** 2 * phi() ** 4 / m_t() ** 2
        + s.half * g_t() ** 2 * phi() ** 2 * phi(derivatives=[mu]) ** 2 / m_t() ** 4
    )

    assert_expr_equal(matched, expected)


def test_complex_heavy_scalar_tree_match_solves_field_and_conjugate() -> None:
    theory = Theory("complex_heavy")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=False, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    y = theory.define_coupling("y")
    yb = theory.define_coupling("yb")
    mass = theory.coupling_handle("M")
    mu = theory.lorentz_index("d")
    u3 = theory.lorentz_index("u3")
    lagrangian = (
        theory.free_lag(heavy, phi)
        - y() * s.Bar(heavy()) * phi() ** 2
        - yb() * heavy() * phi() ** 2
    )

    solution = solve_heavy_scalar_eoms(theory, lagrangian, eft_order=6)["S"]
    assert_expr_equal(solution.orders[1], -y() * phi() ** 2 / mass() ** 2)
    assert_expr_equal(solution.conjugate_orders[1], -yb() * phi() ** 2 / mass() ** 2)
    assert_expr_equal(
        solution.orders[3],
        2 * y() * (phi(derivatives=[u3]) ** 2 + phi() * phi(derivatives=[u3, u3])) / mass() ** 4,
    )

    matched = match_tree(theory, lagrangian, eft_order=6)
    expected = (
        s.half * phi(derivatives=[mu]) ** 2
        + y() * yb() * phi() ** 4 / mass() ** 2
        + 4 * y() * yb() * phi() ** 2 * phi(derivatives=[mu]) ** 2 / mass() ** 4
    )
    assert_expr_equal(matched, expected)
