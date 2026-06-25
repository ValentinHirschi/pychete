from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import Theory
from pychete.backends import vakint, vacuum_integrals
from pychete.symbols import canonical_string, s
from tests.conftest import assert_expr_equal

_DECODE_THEORY = Theory("vacuum_integrals_decode")


def _decode_native_constants(expr: Expression) -> Expression:
    return vakint.decode_pychete_namespace(_DECODE_THEORY, expr)


def _loop_function_topology(masses: tuple[Expression, ...], powers: tuple[int, ...]) -> Expression:
    alpha = powers[-1]
    mass_squareds = tuple(mass**2 for mass in masses)
    prop_powers = tuple(powers[:-1])
    if alpha:
        mass_squareds += (Expression.num(0),)
        prop_powers += (alpha,)
    return vakint.one_loop_vacuum_integral(Expression.num(1), mass_squareds, powers=prop_powers)


def _expected_loop_function_value(masses: tuple[Expression, ...], powers: tuple[int, ...]) -> Expression:
    topology_value = vacuum_integrals.evaluate_one_loop_vakint_expression(_loop_function_topology(masses, powers))
    return vakint.finite_part((topology_value / vacuum_integrals.imaginary_unit_symbol()).expand())


def test_loop_function_placeholder_lowers_to_vakint_topology() -> None:
    m1 = S("M1")
    m2 = S("M2")
    loop_function = vacuum_integrals.loop_function((m1, m2), (1, 2, -1))
    expected = _loop_function_topology((m1, m2), (1, 2, -1))

    assert_expr_equal(vacuum_integrals.loop_function_to_vakint_integral(loop_function), expected)


def test_canonize_loop_function_combines_duplicate_masses_and_orders_powers() -> None:
    m1 = S("M1")
    m2 = S("M2")
    dropped = S("Mdropped")
    loop_function = s.LoopFunction(
        s.List(m2, m1, m2, dropped),
        s.List(Expression.num(1), Expression.num(3), Expression.num(2), Expression.num(0), Expression.num(-1)),
    )
    expected = vacuum_integrals.loop_function((m1, m2), (3, 3, -1))

    assert_expr_equal(vacuum_integrals.canonize_loop_function(loop_function), expected)


def test_canonize_loop_functions_replaces_all_atoms_with_symbolica_matcher() -> None:
    m1 = S("M1")
    m2 = S("M2")
    coefficient = S("coeff")
    expression = coefficient * s.LoopFunction(
        s.List(m2, m1, m2),
        s.List(Expression.num(1), Expression.num(2), Expression.num(3), Expression.num(0)),
    )
    expected = coefficient * vacuum_integrals.loop_function((m2, m1), (4, 2, 0))

    assert_expr_equal(vacuum_integrals.canonize_loop_functions(expression), expected)


def test_canonize_loop_function_sets_scaleless_massless_remnants_to_zero() -> None:
    mass = S("M")
    loop_function = s.LoopFunction(s.List(mass), s.List(Expression.num(0), Expression.num(2)))

    assert_expr_equal(vacuum_integrals.canonize_loop_function(loop_function), Expression.num(0))
    assert_expr_equal(vacuum_integrals.canonize_loop_functions(3 * loop_function), Expression.num(0))


def test_evaluate_loop_functions_accepts_noncanonical_loop_function_atoms() -> None:
    m1 = S("M1")
    m2 = S("M2")
    loop_function = s.LoopFunction(
        s.List(m2, m1, m2),
        s.List(Expression.num(1), Expression.num(2), Expression.num(3), Expression.num(0)),
    )
    canonical_loop_function = vacuum_integrals.loop_function((m2, m1), (4, 2, 0))

    assert_expr_equal(
        vacuum_integrals.evaluate_loop_functions(loop_function),
        vacuum_integrals.evaluate_loop_functions(canonical_loop_function),
    )


def test_loop_function_pole_part_extracts_full_loop_pole_piece() -> None:
    mass = S("M")
    loop_function = vacuum_integrals.loop_function((mass,), (2, 2))
    expected = vakint.pole_part(
        (
            vacuum_integrals.evaluate_one_loop_vakint_expression(
                vacuum_integrals.loop_function_to_vakint_integral(loop_function)
            )
            / vacuum_integrals.imaginary_unit_symbol()
        ).expand()
    )

    assert_expr_equal(vacuum_integrals.loop_function_pole_part(loop_function), expected)


def test_reduce_loop_function_first_power_matches_matchete_pole_treatment_identity() -> None:
    a = S("a")
    b = S("b")
    loop_function = vacuum_integrals.loop_function((a, b), (2, 1, 1))
    reduced = vacuum_integrals.reduce_loop_function_first_power(loop_function)

    assert "LoopFunction" in canonical_string(reduced)
    assert_expr_equal(
        vacuum_integrals.evaluate_loop_functions(loop_function - reduced, combine_terms=True),
        Expression.num(0),
    )


def test_reduce_loop_functions_first_power_replaces_atoms_expression_wide() -> None:
    a = S("a")
    b = S("b")
    coefficient = S("coeff")
    loop_function = vacuum_integrals.loop_function((a, b), (3, 1, 0))
    expression = coefficient * loop_function
    reduced = vacuum_integrals.reduce_loop_functions_first_power(expression)

    assert canonical_string(reduced) != canonical_string(expression)
    assert_expr_equal(
        vacuum_integrals.evaluate_loop_functions(expression - reduced, combine_terms=True),
        Expression.num(0),
    )


def test_reduce_loop_function_first_power_leaves_already_reduced_atoms_unchanged() -> None:
    a = S("a")
    b = S("b")
    loop_function = vacuum_integrals.loop_function((a, b), (1, 1, 0))

    assert_expr_equal(vacuum_integrals.reduce_loop_function_first_power(loop_function), loop_function)


def test_reduce_loop_function_ibp_applies_positive_massless_power_relation() -> None:
    a = S("a")
    b = S("b")
    loop_function = vacuum_integrals.loop_function((a, b), (1, 1, 1))
    reduced = vacuum_integrals.reduce_loop_function_ibp(loop_function)
    expected = (
        vacuum_integrals.loop_function((a, b), (1, 1, 0)) / a**2
        - vacuum_integrals.loop_function((b,), (1, 0)) / (a**2 * b**2)
    )

    assert_expr_equal(reduced, expected)
    assert_expr_equal(
        vacuum_integrals.evaluate_loop_functions(loop_function - reduced, combine_terms=True).replace(
            (a**2).log(),
            2 * a.log(),
        ),
        Expression.num(0),
    )


def test_reduce_loop_function_ibp_applies_negative_massless_power_relation() -> None:
    a = S("a")
    b = S("b")
    loop_function = vacuum_integrals.loop_function((a, b), (1, 1, -1))
    reduced = vacuum_integrals.reduce_loop_function_ibp(loop_function)
    expected = vacuum_integrals.loop_function((b,), (1, 0)) + a**2 * vacuum_integrals.loop_function((a, b), (1, 1, 0))

    assert_expr_equal(reduced, expected)
    assert_expr_equal(
        vacuum_integrals.evaluate_loop_functions(loop_function - reduced, combine_terms=True),
        Expression.num(0),
    )


def test_reduce_loop_functions_ibp_replaces_atoms_expression_wide() -> None:
    a = S("a")
    b = S("b")
    coefficient = S("coeff")
    expression = coefficient * vacuum_integrals.loop_function((a, b), (2, 1, 1))
    reduced = vacuum_integrals.reduce_loop_functions_ibp(expression)

    assert canonical_string(reduced) != canonical_string(expression)
    assert_expr_equal(
        vacuum_integrals.evaluate_loop_functions(expression - reduced, combine_terms=True),
        Expression.num(0),
    )


def test_simplify_loop_functions_matches_matchete_simple_sum_cases() -> None:
    m1 = S("M1")
    m3 = S("M3")
    expression_1 = (
        vacuum_integrals.loop_function((m1, m3), (1, 1, 1))
        + vacuum_integrals.loop_function((m1, m3), (2, 1, 0))
        - vacuum_integrals.loop_function((m3, m1), (2, 1, 0))
    )
    expected_1 = 2 * vacuum_integrals.loop_function((m1, m3), (2, 1, 0))
    expression_2 = (
        vacuum_integrals.loop_function((m1, m3), (1, 1, 1))
        - vacuum_integrals.loop_function((m1, m3), (2, 1, 0))
        + vacuum_integrals.loop_function((m3, m1), (2, 1, 0))
    )
    expected_2 = 2 * vacuum_integrals.loop_function((m1, m3), (1, 2, 0))

    assert_expr_equal(vacuum_integrals.simplify_loop_functions(expression_1), expected_1)
    assert_expr_equal(vacuum_integrals.simplify_loop_functions(expression_2), expected_2)


def test_simplify_loop_functions_matches_matchete_full_reduction_case() -> None:
    md = S("Md")
    mq = S("Mq")
    expression = (
        vacuum_integrals.loop_function((md, mq), (2, 2, 0))
        + vacuum_integrals.loop_function((md, mq), (3, 1, 0))
        - vacuum_integrals.loop_function((md, mq), (3, 2, -1))
        - vacuum_integrals.loop_function((md, mq), (4, 1, -1))
        + vacuum_integrals.loop_function((mq, md), (3, 1, 0))
        - vacuum_integrals.loop_function((mq, md), (3, 2, -1))
        - vacuum_integrals.loop_function((mq, md), (4, 1, -1))
    )
    expected = Expression.num(1) / (96 * Expression.PI**2 * md**2 * mq**2)

    assert_expr_equal(vacuum_integrals.simplify_loop_functions(expression, combine_terms=True), expected)


def test_simplify_loop_functions_matches_matchete_partial_reduction_case() -> None:
    mq = S("Mq")
    mu = S("Mu")
    expression = (
        -vacuum_integrals.loop_function((mq, mu), (2, 2, 0))
        - vacuum_integrals.loop_function((mq, mu), (3, 1, 0))
        + vacuum_integrals.loop_function((mq, mu), (3, 2, -1))
        + vacuum_integrals.loop_function((mq, mu), (4, 1, -1))
        + vacuum_integrals.loop_function((mu, mq), (3, 1, 0))
        + vacuum_integrals.loop_function((mu, mq), (3, 2, -1))
        - 3 * vacuum_integrals.loop_function((mu, mq), (4, 1, -1))
        + 2 * vacuum_integrals.loop_function((mu, mq), (5, 1, -2))
    )
    expected = -2 * vacuum_integrals.loop_function((mq, mu), (4, 1, -1)) + 2 * vacuum_integrals.loop_function(
        (mq, mu),
        (5, 1, -2),
    )
    simplified = vacuum_integrals.simplify_loop_functions(expression)

    assert_expr_equal(simplified, expected)
    assert_expr_equal(
        vacuum_integrals.evaluate_loop_functions(expression - simplified, combine_terms=True),
        Expression.num(0),
    )


def test_evaluate_loop_functions_uses_internal_finite_loop_function_convention() -> None:
    m1 = S("M1")
    m2 = S("M2")
    numerator = S("num")
    loop_function = vacuum_integrals.loop_function((m1, m2), (1, 1, 0))
    expression = numerator * loop_function
    expected = numerator * _expected_loop_function_value((m1, m2), (1, 1, 0))

    assert_expr_equal(vacuum_integrals.evaluate_loop_functions(expression), expected)


def test_evaluate_loop_functions_handles_massless_power_after_tensor_reduction() -> None:
    mass = S("M")
    loop_function = vacuum_integrals.loop_function((mass,), (2, -2))
    expected = _expected_loop_function_value((mass,), (2, -2))

    assert_expr_equal(vacuum_integrals.evaluate_loop_functions(loop_function), expected)


def test_loop_function_validation_rejects_invalid_power_data() -> None:
    mass = S("M")

    with pytest.raises(ValueError, match="one massive power"):
        vacuum_integrals.loop_function((mass,), (1,))
    with pytest.raises(ValueError, match="powers must be integers"):
        vacuum_integrals.evaluate_loop_functions(s.LoopFunction(s.List(mass), s.List(S("n"), Expression.num(0))))
    with pytest.raises(ValueError, match="nonnegative"):
        vacuum_integrals.loop_function_to_vakint_integral(vacuum_integrals.loop_function((mass,), (-1, 0)))


def test_internal_single_scale_tadpoles_match_vakint_finite_order_evaluation() -> None:
    mass = S("M")
    numerator = S("num")
    engine = vakint.create_engine(
        verify_numerator_identification=False,
        number_of_terms_in_epsilon_expansion=2,
    )

    for power in range(1, 6):
        integral = vakint.one_loop_vacuum_integral(numerator, (mass**2,), powers=(power,))
        vakint_result = _decode_native_constants(vakint.evaluate(integral, engine=engine))
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
        vakint_result = _decode_native_constants(vakint.evaluate(integral, engine=engine))
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

    native_result = _decode_native_constants(vakint.evaluate(expression, engine=engine))
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


def test_internal_single_scale_vakint_expression_collects_powered_duplicate_props() -> None:
    mass_squared = S("muvsq")
    numerator = S("num")
    first = vakint.propagator(1, mass_squared, power=2)
    duplicate = vakint.propagator(8, mass_squared, power=1)
    expression = numerator * vakint.symbol("topo")(first**3 * duplicate**2)
    expected = vacuum_integrals.evaluate_one_loop_single_scale_vacuum_integral_from_mass_squared(
        numerator,
        mass_squared,
        power=8,
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


def test_absorb_vakint_scalar_loop_momentum_numerators_lowers_to_massless_power() -> None:
    mass = S("m")
    coeff = S("c")
    index = S("mu")
    expression = coeff * vakint.loop_momentum(1, index) ** 2 * vakint.one_loop_vacuum_topology((mass**2,))
    expected = coeff * vakint.one_loop_vacuum_integral(
        Expression.num(1),
        (mass**2, Expression.num(0)),
        powers=(1, -1),
    )

    absorbed = vacuum_integrals.absorb_vakint_scalar_loop_momentum_numerators(expression)

    assert "vakint::k(1,python::mu)^2" not in canonical_string(absorbed)
    assert_expr_equal(
        vacuum_integrals.evaluate_one_loop_vakint_expression(absorbed),
        vacuum_integrals.evaluate_one_loop_vakint_expression(expected),
    )


def test_absorb_vakint_scalar_loop_momentum_numerators_handles_multiple_factors() -> None:
    mass = S("m")
    expression = (
        vakint.loop_momentum(1, S("mu")) ** 2
        * vakint.loop_momentum(1, S("nu")) ** 2
        * vakint.one_loop_vacuum_topology((mass**2,))
    )
    expected = vakint.one_loop_vacuum_integral(
        Expression.num(1),
        (mass**2, Expression.num(0)),
        powers=(1, -2),
    )

    absorbed = vacuum_integrals.absorb_vakint_scalar_loop_momentum_numerators(expression)

    assert "vakint::k(1,python::mu)^2" not in canonical_string(absorbed)
    assert "vakint::k(1,python::nu)^2" not in canonical_string(absorbed)
    assert_expr_equal(
        vacuum_integrals.evaluate_one_loop_vakint_expression(absorbed),
        vacuum_integrals.evaluate_one_loop_vakint_expression(expected),
    )


def test_internal_vakint_expression_absorbs_tensor_reduced_scalar_loop_momentum() -> None:
    mass = S("m")
    expression = vakint.loop_momentum(1, S("mu")) ** 2 * vakint.one_loop_vacuum_topology((mass**2,))
    expected = vacuum_integrals.evaluate_one_loop_vakint_expression(
        vakint.one_loop_vacuum_integral(Expression.num(1), (mass**2, Expression.num(0)), powers=(1, -1))
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


def test_internal_vakint_expression_matches_matchete_mass_function_simple_sum_cases() -> None:
    m1 = S("M1")
    m3 = S("M3")
    expression_1 = (
        _loop_function_topology((m1, m3), (1, 1, 1))
        + _loop_function_topology((m1, m3), (2, 1, 0))
        - _loop_function_topology((m3, m1), (2, 1, 0))
    )
    expected_1 = 2 * _loop_function_topology((m1, m3), (2, 1, 0))
    expression_2 = (
        _loop_function_topology((m1, m3), (1, 1, 1))
        - _loop_function_topology((m1, m3), (2, 1, 0))
        + _loop_function_topology((m3, m1), (2, 1, 0))
    )
    expected_2 = 2 * _loop_function_topology((m1, m3), (1, 2, 0))

    for expression, expected in ((expression_1, expected_1), (expression_2, expected_2)):
        assert_expr_equal(
            vacuum_integrals.evaluate_one_loop_vakint_expression(expression, combine_terms=True),
            vacuum_integrals.evaluate_one_loop_vakint_expression(expected, combine_terms=True),
        )


def test_internal_vakint_expression_matches_matchete_mass_function_partial_reduction_case() -> None:
    mq = S("Mq")
    mu = S("Mu")
    expression = (
        -_loop_function_topology((mq, mu), (2, 2, 0))
        - _loop_function_topology((mq, mu), (3, 1, 0))
        + _loop_function_topology((mq, mu), (3, 2, -1))
        + _loop_function_topology((mq, mu), (4, 1, -1))
        + _loop_function_topology((mu, mq), (3, 1, 0))
        + _loop_function_topology((mu, mq), (3, 2, -1))
        - 3 * _loop_function_topology((mu, mq), (4, 1, -1))
        + 2 * _loop_function_topology((mu, mq), (5, 1, -2))
    )
    expected = -2 * _loop_function_topology((mq, mu), (4, 1, -1)) + 2 * _loop_function_topology(
        (mq, mu),
        (5, 1, -2),
    )

    assert_expr_equal(
        vacuum_integrals.evaluate_one_loop_vakint_expression(expression, combine_terms=True),
        vacuum_integrals.evaluate_one_loop_vakint_expression(expected, combine_terms=True),
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
            "at least one propagator",
        ),
    ],
)
def test_internal_single_scale_vakint_expression_rejects_unsupported_topologies(
    expression: Expression,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        vacuum_integrals.evaluate_one_loop_single_scale_vakint_expression(expression)
