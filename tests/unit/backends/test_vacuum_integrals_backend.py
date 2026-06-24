from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete.backends import vakint, vacuum_integrals
from tests.conftest import assert_expr_equal


def _loop_function_topology(masses: tuple[Expression, ...], powers: tuple[int, ...]) -> Expression:
    alpha = powers[-1]
    mass_squareds = tuple(mass**2 for mass in masses)
    prop_powers = tuple(powers[:-1])
    if alpha:
        mass_squareds += (Expression.num(0),)
        prop_powers += (alpha,)
    return vakint.one_loop_vacuum_integral(Expression.num(1), mass_squareds, powers=prop_powers)


def test_internal_single_scale_tadpoles_match_vakint_finite_order_evaluation() -> None:
    mass = S("M")
    numerator = S("num")
    engine = vakint.create_engine(
        verify_numerator_identification=False,
        number_of_terms_in_epsilon_expansion=2,
    )

    for power in range(1, 6):
        integral = vakint.one_loop_vacuum_integral(numerator, (mass**2,), powers=(power,))
        vakint_result = vakint.evaluate(integral, engine=engine)
        internal_result = vacuum_integrals.evaluate_one_loop_single_scale_vacuum_integral(
            numerator,
            mass,
            power=power,
        )

        assert_expr_equal(internal_result, vakint_result)


def test_internal_single_scale_mass_squared_tadpoles_match_vakint_finite_order_evaluation() -> None:
    mass_squared = S("muvsq")
    numerator = S("num")
    engine = vakint.create_engine(
        verify_numerator_identification=False,
        number_of_terms_in_epsilon_expansion=2,
    )

    for power in range(1, 5):
        integral = vakint.one_loop_vacuum_integral(numerator, (mass_squared,), powers=(power,))
        vakint_result = vakint.evaluate(integral, engine=engine)
        internal_result = vacuum_integrals.evaluate_one_loop_single_scale_vacuum_integral_from_mass_squared(
            numerator,
            mass_squared,
            power=power,
        )

        assert_expr_equal(internal_result, vakint_result)


def test_internal_single_scale_vakint_expression_evaluator_matches_native_vakint() -> None:
    mass = S("M")
    numerator = S("num")
    coeff = S("coeff")
    expression = (
        vakint.one_loop_vacuum_integral(numerator, (mass**2,), powers=(1,))
        + vakint.one_loop_vacuum_integral(coeff, (mass**2,), powers=(3,))
    )
    engine = vakint.create_engine(
        verify_numerator_identification=False,
        number_of_terms_in_epsilon_expansion=2,
    )

    native_result = vakint.evaluate(expression, engine=engine)
    internal_result = vacuum_integrals.evaluate_one_loop_single_scale_vakint_expression(expression)

    assert_expr_equal(internal_result, native_result)


def test_internal_single_scale_vakint_expression_combines_equal_mass_powers() -> None:
    mass_squared = S("muvsq")
    numerator = S("num")
    expression = vakint.one_loop_vacuum_integral(
        numerator,
        (mass_squared, mass_squared),
        powers=(1, 2),
    )
    expected = vacuum_integrals.evaluate_one_loop_single_scale_vacuum_integral_from_mass_squared(
        numerator,
        mass_squared,
        power=3,
    )

    assert_expr_equal(vacuum_integrals.evaluate_one_loop_single_scale_vakint_expression(expression), expected)


def test_internal_vakint_expression_evaluates_two_mass_scalar_topology() -> None:
    m1 = S("M1")
    m2 = S("M2")
    numerator = S("num")
    expression = vakint.one_loop_vacuum_integral(numerator, (m1**2, m2**2), powers=(1, 1))
    eps = vacuum_integrals.epsilon_symbol()
    mu = vacuum_integrals.mu_r_squared_symbol()
    normalization = vacuum_integrals.imaginary_unit_symbol() * numerator / (16 * Expression.PI**2)
    expected = (
        normalization
        * m1**2
        * (Expression.num(1) / eps + 1 + mu.log() - 2 * m1.log())
        / (m1**2 - m2**2)
        + normalization
        * m2**2
        * (Expression.num(1) / eps + 1 + mu.log() - 2 * m2.log())
        / (m2**2 - m1**2)
    )

    assert_expr_equal(vacuum_integrals.evaluate_one_loop_vakint_expression(expression), expected)


def test_internal_vakint_expression_evaluates_massless_massive_scalar_topology() -> None:
    mass = S("M")
    numerator = S("num")
    expression = vakint.one_loop_vacuum_integral(numerator, (Expression.num(0), mass**2), powers=(1, 1))
    eps = vacuum_integrals.epsilon_symbol()
    mu = vacuum_integrals.mu_r_squared_symbol()
    expected = (
        vacuum_integrals.imaginary_unit_symbol()
        * numerator
        / (16 * Expression.PI**2)
        * (Expression.num(1) / eps + 1 + mu.log() - 2 * mass.log())
    )

    assert_expr_equal(vacuum_integrals.evaluate_one_loop_vakint_expression(expression), expected)


def test_internal_vakint_expression_sets_scaleless_massless_topologies_to_zero() -> None:
    expression = vakint.one_loop_vacuum_integral(S("num"), (Expression.num(0),), powers=(2,))

    assert_expr_equal(vacuum_integrals.evaluate_one_loop_vakint_expression(expression), Expression.num(0))


def test_internal_vakint_expression_matches_matchete_massive_with_massless_denominator_case() -> None:
    mass = S("m")
    expression = vakint.one_loop_vacuum_integral(Expression.num(1), (mass**2, Expression.num(0)), powers=(2, 2))
    eps = vacuum_integrals.epsilon_symbol()
    mu = vacuum_integrals.mu_r_squared_symbol()
    expected = (
        -vacuum_integrals.imaginary_unit_symbol()
        / (16 * Expression.PI**2 * mass**4)
        * (Expression.num(1) / eps + mu.log() - 2 * mass.log() + 2)
    )

    assert_expr_equal(vacuum_integrals.evaluate_one_loop_vakint_expression(expression), expected)


def test_internal_vakint_expression_matches_matchete_massive_with_momentum_numerator_case() -> None:
    mass = S("m")
    expression = vakint.one_loop_vacuum_integral(Expression.num(1), (mass**2, Expression.num(0)), powers=(2, -2))
    eps = vacuum_integrals.epsilon_symbol()
    mu = vacuum_integrals.mu_r_squared_symbol()
    expected = (
        vacuum_integrals.imaginary_unit_symbol()
        * mass**4
        / (16 * Expression.PI**2)
        * (3 / eps + 3 * (mu.log() - 2 * mass.log()) + 2)
    )

    assert_expr_equal(vacuum_integrals.evaluate_one_loop_vakint_expression(expression), expected)


def test_internal_vakint_expression_combines_matchete_mass_function_full_reduction_case() -> None:
    md = S("Md")
    mq = S("Mq")
    expression = (
        _loop_function_topology((md, mq), (2, 2, 0))
        + _loop_function_topology((md, mq), (3, 1, 0))
        - _loop_function_topology((md, mq), (3, 2, -1))
        - _loop_function_topology((md, mq), (4, 1, -1))
        + _loop_function_topology((mq, md), (3, 1, 0))
        - _loop_function_topology((mq, md), (3, 2, -1))
        - _loop_function_topology((mq, md), (4, 1, -1))
    )
    expected = (
        vacuum_integrals.imaginary_unit_symbol()
        / (16 * Expression.PI**2)
        / (6 * md**2 * mq**2)
    )

    assert_expr_equal(
        vacuum_integrals.evaluate_one_loop_vakint_expression(expression, combine_terms=True),
        expected,
    )


@pytest.mark.parametrize(
    "expression, message",
    [
        (
            vakint.one_loop_vacuum_integral(S("num"), (Expression.num(0),), powers=(1,)),
            "massless propagators",
        ),
        (
            vakint.one_loop_vacuum_integral(S("num"), (S("M1") ** 2, S("M2") ** 2), powers=(1, 1)),
            "mixed-mass topologies",
        ),
        (
            vakint.one_loop_vacuum_integral(S("num"), (S("M") ** 2,), powers=(0,)),
            "positive integers",
        ),
    ],
)
def test_internal_single_scale_vakint_expression_rejects_unsupported_topologies(
    expression: Expression,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        vacuum_integrals.evaluate_one_loop_single_scale_vakint_expression(expression)
