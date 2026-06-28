from __future__ import annotations

from symbolica import Expression, S

from pychete import (
    evaluate_sym_gamma_factors,
    evaluate_symmetric_lorentz_indices,
    symmetric_lorentz_gamma_factor,
    symmetric_lorentz_tensor,
    s,
)
from tests.conftest import assert_expr_equal


def test_symmetric_lorentz_gamma_factor_keeps_linear_epsilon_term() -> None:
    epsilon = S("eps")

    assert_expr_equal(
        symmetric_lorentz_gamma_factor(1, epsilon=epsilon),
        Expression.num(1) / 4 + epsilon / 8,
    )
    assert_expr_equal(
        symmetric_lorentz_gamma_factor(2, epsilon=epsilon),
        Expression.num(1) / 24 + 5 * epsilon / 144,
    )


def test_evaluate_sym_gamma_factors_uses_symbolica_replacement() -> None:
    epsilon = S("eps")
    coefficient = S("c")
    expr = coefficient * s.SymGammaFactor(Expression.num(2), Expression.num(4))

    assert_expr_equal(
        evaluate_sym_gamma_factors(expr, epsilon=epsilon),
        coefficient * (Expression.num(1) / 24 + 5 * epsilon / 144),
    )


def test_symmetric_lorentz_tensor_evaluates_metric_pairings() -> None:
    mu = S("mu")
    nu = S("nu")
    rho = S("rho")
    sigma = S("sigma")

    rank_two = symmetric_lorentz_tensor((mu, nu), evaluate_gamma=False)
    assert_expr_equal(rank_two, s.Metric(mu, nu) * s.SymGammaFactor(Expression.num(1), Expression.num(4)))

    rank_four = symmetric_lorentz_tensor((mu, nu, rho, sigma), evaluate_gamma=False)
    expected = (
        s.Metric(mu, nu) * s.Metric(rho, sigma)
        + s.Metric(mu, rho) * s.Metric(nu, sigma)
        + s.Metric(mu, sigma) * s.Metric(nu, rho)
    ) * s.SymGammaFactor(Expression.num(2), Expression.num(4))
    assert_expr_equal(rank_four, expected)


def test_evaluate_symmetric_lorentz_indices_handles_repeated_pairs_and_odd_rank() -> None:
    mu = S("mu")
    nu = S("nu")
    rho = S("rho")
    epsilon = S("eps")

    repeated = s.SymmetricLorentzInds(s.List(mu, mu, nu, rho))
    odd = s.SymmetricLorentzInds(s.List(mu, nu, rho))

    assert_expr_equal(
        evaluate_symmetric_lorentz_indices(repeated, epsilon=epsilon),
        s.Metric(nu, rho) * (Expression.num(1) / 4 + epsilon / 8),
    )
    assert_expr_equal(evaluate_symmetric_lorentz_indices(odd, epsilon=epsilon), Expression.num(0))
