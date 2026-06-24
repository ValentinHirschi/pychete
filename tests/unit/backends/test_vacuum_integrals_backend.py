from __future__ import annotations

from symbolica import S

from pychete.backends import vakint, vacuum_integrals
from tests.conftest import assert_expr_equal


def test_internal_single_scale_tadpole_matches_vakint_finite_order_evaluation() -> None:
    mass = S("M")
    numerator = S("num")
    integral = vakint.one_loop_vacuum_integral(numerator, (mass**2,))
    engine = vakint.create_engine(
        verify_numerator_identification=False,
        number_of_terms_in_epsilon_expansion=2,
    )

    vakint_result = vakint.evaluate(integral, engine=engine)
    internal_result = vacuum_integrals.evaluate_one_loop_single_scale_vacuum_integral(numerator, mass)

    assert_expr_equal(internal_result, vakint_result)
