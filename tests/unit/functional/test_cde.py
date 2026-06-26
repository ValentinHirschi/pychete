from __future__ import annotations

import pytest
from symbolica import Expression

from pychete import Theory, s
from pychete.cde import (
    act_with_open_covariant_derivatives,
    bosonic_covariant_propagator_expansion_terms,
    fermionic_covariant_propagator_expansion_terms,
    open_covariant_derivative,
)

from tests.conftest import assert_expr_equal


def test_open_covariant_derivative_acts_on_all_factors_to_its_right() -> None:
    theory = Theory("open_cd_product")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    chi = theory.define_field("chi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")

    expr = s.NCM(open_covariant_derivative(mu), phi(), chi())
    expected = s.NCM(phi(derivatives=[mu]), chi()) + s.NCM(phi(), chi(derivatives=[mu]))

    assert_expr_equal(act_with_open_covariant_derivatives(expr), expected)


def test_open_covariant_derivative_acts_from_the_rightmost_open_operator_first() -> None:
    theory = Theory("open_cd_nested")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    expr = s.NCM(open_covariant_derivative(mu), open_covariant_derivative(nu), phi())

    assert_expr_equal(act_with_open_covariant_derivatives(expr), phi(derivatives=[nu, mu]))


def test_stranded_open_covariant_derivative_chain_vanishes() -> None:
    theory = Theory("open_cd_stranded")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")

    expr = s.NCM(phi(), open_covariant_derivative(mu))

    assert_expr_equal(act_with_open_covariant_derivatives(expr), Expression.num(0))


def test_cyclic_open_covariant_derivative_wraps_in_closed_trace_chains() -> None:
    theory = Theory("open_cd_cyclic")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")

    expr = s.NCM(phi(), open_covariant_derivative(mu))

    assert_expr_equal(act_with_open_covariant_derivatives(expr, cyclic=True), phi(derivatives=[mu]))


def test_open_covariant_derivative_pass_is_guarded_when_operator_absent() -> None:
    theory = Theory("open_cd_absent")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")
    expr = s.NCM(phi(), phi(derivatives=[mu]))

    assert_expr_equal(act_with_open_covariant_derivatives(expr), expr)


def test_open_covariant_derivative_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="max_chain_arity"):
        act_with_open_covariant_derivatives(Expression.num(1), max_chain_arity=0)
    with pytest.raises(ValueError, match="max_passes"):
        act_with_open_covariant_derivatives(Expression.num(1), max_passes=-1)


def test_bosonic_covariant_propagator_expansion_order_zero_is_scalar_propagator() -> None:
    terms = bosonic_covariant_propagator_expansion_terms(())

    assert len(terms) == 1
    assert terms[0].denominator_power == 1
    assert_expr_equal(terms[0].numerator, Expression.num(1))


def test_bosonic_covariant_propagator_expansion_order_two_matches_open_cd_structure() -> None:
    theory = Theory("bosonic_prop_order_two")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    terms = bosonic_covariant_propagator_expansion_terms((mu, nu))

    assert [term.denominator_power for term in terms] == [3, 2]
    assert terms[0].loop_momentum_indices == (mu, nu)
    assert terms[1].loop_momentum_indices == ()
    assert_expr_equal(
        terms[0].numerator,
        -4 * s.LoopMomentum(mu) * s.LoopMomentum(nu) * s.NCM(open_covariant_derivative(mu), open_covariant_derivative(nu)),
    )
    assert_expr_equal(
        terms[1].numerator,
        s.NCM(open_covariant_derivative(mu), open_covariant_derivative(mu)),
    )


def test_bosonic_covariant_propagator_expansion_terms_splice_into_open_cd_chain() -> None:
    theory = Theory("bosonic_prop_splice")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")
    term = bosonic_covariant_propagator_expansion_terms((mu,))[0]

    acted = act_with_open_covariant_derivatives(term.chain_with(phi()))

    assert term.denominator_power == 2
    assert_expr_equal(acted, -2 * Expression.I * s.LoopMomentum(mu) * phi(derivatives=[mu]))


def test_fermionic_covariant_propagator_expansion_order_zero_has_mass_and_slash_terms() -> None:
    theory = Theory("fermionic_prop_order_zero")
    mass = theory.define_coupling("M", mass_dimension=1)
    slash = theory.lorentz_index("slash")
    derivative = theory.lorentz_index("derivative")

    terms = fermionic_covariant_propagator_expansion_terms(
        mass(),
        (),
        slash_index=slash,
        derivative_index=derivative,
    )

    assert [term.denominator_power for term in terms] == [1, 1]
    assert terms[0].loop_momentum_indices == ()
    assert terms[1].loop_momentum_indices == (slash,)
    assert_expr_equal(terms[0].numerator, mass())
    assert_expr_equal(terms[1].numerator, s.LoopMomentum(slash) * s.DiracProduct(s.Gamma(slash)))


def test_fermionic_covariant_propagator_expansion_order_one_adds_p_gamma_term() -> None:
    theory = Theory("fermionic_prop_order_one")
    mass = theory.define_coupling("M", mass_dimension=1)
    mu = theory.lorentz_index("mu")
    slash = theory.lorentz_index("slash")
    derivative = theory.lorentz_index("derivative")

    terms = fermionic_covariant_propagator_expansion_terms(
        mass(),
        (mu,),
        slash_index=slash,
        derivative_index=derivative,
    )

    assert [term.denominator_power for term in terms] == [2, 2, 1]
    assert terms[0].loop_momentum_indices == (mu,)
    assert terms[1].loop_momentum_indices == (slash, mu)
    assert terms[2].loop_momentum_indices == ()
    assert_expr_equal(
        terms[0].numerator,
        -2 * Expression.I * mass() * s.LoopMomentum(mu) * open_covariant_derivative(mu),
    )
    assert_expr_equal(
        terms[1].numerator,
        -2
        * Expression.I
        * s.LoopMomentum(slash)
        * s.LoopMomentum(mu)
        * s.NCM(s.DiracProduct(s.Gamma(slash)), open_covariant_derivative(mu)),
    )
    assert_expr_equal(
        terms[2].numerator,
        Expression.I * s.NCM(s.DiracProduct(s.Gamma(derivative)), open_covariant_derivative(derivative)),
    )


def test_bosonic_covariant_propagator_expansion_interleaves_pair_open_cds() -> None:
    theory = Theory("bosonic_prop_order_three")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    rho = theory.lorentz_index("rho")

    terms = bosonic_covariant_propagator_expansion_terms((mu, nu, rho))
    denominator_three_terms = [term for term in terms if term.denominator_power == 3]

    assert len(denominator_three_terms) == 2
    assert_expr_equal(
        denominator_three_terms[0].numerator,
        -2
        * Expression.I
        * s.LoopMomentum(mu)
        * s.NCM(open_covariant_derivative(mu), open_covariant_derivative(nu), open_covariant_derivative(nu)),
    )
    assert_expr_equal(
        denominator_three_terms[1].numerator,
        -2
        * Expression.I
        * s.LoopMomentum(mu)
        * s.NCM(open_covariant_derivative(nu), open_covariant_derivative(nu), open_covariant_derivative(mu)),
    )
