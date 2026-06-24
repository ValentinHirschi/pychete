from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete.backends import vakint, vacuum_integrals
from tests.conftest import assert_expr_equal


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


@pytest.mark.parametrize(
    "expression, message",
    [
        (
            vakint.one_loop_vacuum_integral(S("num"), (Expression.num(0),), powers=(1,)),
            "nonzero masses",
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
