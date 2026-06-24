from __future__ import annotations

from symbolica import Expression

from pychete import FieldMassKind, MatchingResult, Theory, canonical_string, s

from tests.conftest import assert_expr_equal


def _heavy_scalar_theory() -> tuple[Theory, object, object, object]:
    theory = Theory("heavy_scalar")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    g = theory.define_coupling("g", self_conjugate=True)
    return theory, heavy, light, g


def test_heavy_scalar_eom_and_fixed_order_solution_match_reference() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    mu = theory.dummy_index(0)
    u3 = theory.dummy_index(3)
    mass = theory.coupling_handle("M")
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2

    eom = theory.derive_eom(lagrangian, heavy)
    expected_eom = -mass() ** 2 * heavy() - heavy(derivatives=[mu, mu]) - g() * phi() ** 2 / 2
    assert_expr_equal(eom, expected_eom)

    solution = theory.solve_heavy_scalar_eoms(lagrangian, eft_order=6)["S"]
    assert_expr_equal(solution.orders[1], -g() * phi() ** 2 / (2 * mass() ** 2))
    assert_expr_equal(solution.orders[2], Expression.num(0))
    assert_expr_equal(
        solution.orders[3],
        g() * (phi(derivatives=[u3]) ** 2 + phi() * phi(derivatives=[u3, u3])) / mass() ** 4,
    )


def test_heavy_scalar_tree_match_through_dimension_six() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    mu = theory.dummy_index(0)
    mass = theory.coupling_handle("M")
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2

    matched = theory.match(lagrangian, eft_order=6)
    expected = (
        phi(derivatives=[mu]) ** 2 / 2
        + g() ** 2 * phi() ** 4 / (8 * mass() ** 2)
        + g() ** 2 * phi() ** 2 * phi(derivatives=[mu]) ** 2 / (2 * mass() ** 4)
    )

    assert_expr_equal(matched, expected)


def test_tree_match_loop_order_zero_preserves_existing_result() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2

    assert_expr_equal(
        theory.match(lagrangian, eft_order=6, loop_order=0),
        theory.match(lagrangian, eft_order=6),
    )


def test_one_loop_match_request_returns_incomplete_internal_integral_result() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2

    result = theory.match(lagrangian, eft_order=6, loop_order=1)

    assert isinstance(result, MatchingResult)
    assert result.metadata["loop_order"] == 1
    assert result.metadata["complete"] is False
    assert result.metadata["stage"] == "interaction_power_type_internal_integral_result"
    assert result.metadata["integral_backend"] == "pychete_internal"
    assert result.metadata["tensor_reduce"] is False
    assert result.metadata["combine_terms"] is True
    assert result.metadata["uses_interaction_operator"] is True
    assert "interaction_power_type_internal_integral_sum" in result.supertraces
    assert_expr_equal(result.off_shell_eft_lagrangian, result.expression("interaction_power_type_internal_integral_sum"))
    result.validate()


def test_one_theory_can_match_two_lagrangians_without_cross_talk() -> None:
    theory, heavy, phi, g = _heavy_scalar_theory()
    h = theory.define_coupling("h", self_conjugate=True)
    mass = theory.coupling_handle("M")
    lagrangian_g = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    lagrangian_h = theory.free_lag(heavy, phi) - h() * heavy() * phi() ** 3

    solution_g = theory.solve_heavy_scalar_eoms(lagrangian_g, eft_order=6)["S"]
    solution_h = theory.solve_heavy_scalar_eoms(lagrangian_h, eft_order=6)["S"]
    assert_expr_equal(solution_g.orders[1], -g() * phi() ** 2 / (2 * mass() ** 2))
    assert_expr_equal(solution_h.orders[1], -h() * phi() ** 3 / mass() ** 2)

    matched_g = theory.match(lagrangian_g, eft_order=6)
    matched_h = theory.match(lagrangian_h, eft_order=6)
    matched_g_text = canonical_string(matched_g)
    matched_h_text = canonical_string(matched_h)

    assert "heavy_scalar::coupling_g" in matched_g_text
    assert "heavy_scalar::coupling_h" not in matched_g_text
    assert "heavy_scalar::coupling_h" in matched_h_text
    assert "heavy_scalar::coupling_g" not in matched_h_text


def test_tree_match_supports_several_independent_diagonal_heavy_scalars() -> None:
    theory = Theory("two_heavy_scalars")
    s_field = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "MS"))
    t_field = theory.define_field("T", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "MT"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    g_s = theory.define_coupling("gS", self_conjugate=True)
    g_t = theory.define_coupling("gT", self_conjugate=True)
    mu = theory.dummy_index(0)
    m_s = theory.coupling_handle("MS")
    m_t = theory.coupling_handle("MT")

    lagrangian = (
        theory.free_lag(s_field, t_field, phi)
        - g_s() * s_field() * phi() ** 2 / 2
        - g_t() * t_field() * phi() ** 2 / 2
    )

    matched = theory.match(lagrangian, eft_order=6)
    expected = (
        phi(derivatives=[mu]) ** 2 / 2
        + g_s() ** 2 * phi() ** 4 / (8 * m_s() ** 2)
        + g_s() ** 2 * phi() ** 2 * phi(derivatives=[mu]) ** 2 / (2 * m_s() ** 4)
        + g_t() ** 2 * phi() ** 4 / (8 * m_t() ** 2)
        + g_t() ** 2 * phi() ** 2 * phi(derivatives=[mu]) ** 2 / (2 * m_t() ** 4)
    )

    assert_expr_equal(matched, expected)


def test_complex_heavy_scalar_tree_match_solves_field_and_conjugate() -> None:
    theory = Theory("complex_heavy")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=False, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    y = theory.define_coupling("y")
    yb = theory.define_coupling("yb")
    mass = theory.coupling_handle("M")
    mu = theory.dummy_index(0)
    u3 = theory.dummy_index(3)
    lagrangian = (
        theory.free_lag(heavy, phi)
        - y() * s.Bar(heavy()) * phi() ** 2
        - yb() * heavy() * phi() ** 2
    )

    solution = theory.solve_heavy_scalar_eoms(lagrangian, eft_order=6)["S"]
    assert_expr_equal(solution.orders[1], -y() * phi() ** 2 / mass() ** 2)
    assert_expr_equal(solution.conjugate_orders[1], -yb() * phi() ** 2 / mass() ** 2)
    assert_expr_equal(
        solution.orders[3],
        2 * y() * (phi(derivatives=[u3]) ** 2 + phi() * phi(derivatives=[u3, u3])) / mass() ** 4,
    )

    matched = theory.match(lagrangian, eft_order=6)
    expected = (
        phi(derivatives=[mu]) ** 2 / 2
        + y() * yb() * phi() ** 4 / mass() ** 2
        + 4 * y() * yb() * phi() ** 2 * phi(derivatives=[mu]) ** 2 / mass() ** 4
    )
    assert_expr_equal(matched, expected)
