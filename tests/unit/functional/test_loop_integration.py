from __future__ import annotations

from symbolica import Expression, S

from pychete import (
    collect_loop_momenta_to_symmetric_lorentz,
    contract_lorentz_metrics,
    evaluate_sym_gamma_factors,
    evaluate_symmetric_lorentz_indices,
    symmetric_lorentz_gamma_factor,
    symmetric_lorentz_tensor,
    s,
)
from tests.conftest import assert_expr_equal


def test_collect_loop_momenta_to_symmetric_lorentz_uses_symbolica_matches() -> None:
    mu = S("mu")
    nu = S("nu")
    coefficient = S("c")
    expr = coefficient * s.LoopMomentum(mu) * s.LoopMomentum(nu)

    assert_expr_equal(
        collect_loop_momenta_to_symmetric_lorentz(expr),
        coefficient * s.SymmetricLorentzInds(s.List(mu, nu)),
    )


def test_collect_loop_momenta_to_symmetric_lorentz_drops_odd_rank_terms() -> None:
    mu = S("mu")
    nu = S("nu")
    coefficient = S("c")
    survivor = S("survivor")
    expr = survivor + coefficient * s.LoopMomentum(mu) * s.LoopMomentum(nu) * s.LoopMomentum(mu)

    assert_expr_equal(collect_loop_momenta_to_symmetric_lorentz(expr), survivor)


def test_collect_loop_momenta_can_record_massless_denominator_shift() -> None:
    mu = S("mu")
    nu = S("nu")
    coefficient = S("c")
    q2 = S("q2")
    expr = coefficient * s.LoopMomentum(mu) * s.LoopMomentum(nu)

    assert_expr_equal(
        collect_loop_momenta_to_symmetric_lorentz(
            expr,
            include_massless_denominator_shift=True,
            loop_momentum_squared=q2,
        ),
        coefficient
        * s.PropagatorDenominator(q2, Expression.num(0)) ** -1
        * s.SymmetricLorentzInds(s.List(mu, nu)),
    )


def test_contract_lorentz_metrics_replaces_indices_inside_ncm_derivative_slots() -> None:
    mu = s.Index(S("mu"), s.Lorentz)
    nu = s.Index(S("nu"), s.Lorentz)
    rho = s.Index(S("rho"), s.Lorentz)
    field = s.Field(S("phi"), s.Scalar, s.List(), s.List(mu, rho))
    expr = S("c") * s.Metric(mu, nu) * s.NCM(field)

    assert_expr_equal(
        contract_lorentz_metrics(expr),
        S("c") * s.NCM(s.Field(S("phi"), s.Scalar, s.List(), s.List(nu, rho))),
    )


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


def test_evaluate_symmetric_lorentz_indices_can_contract_metric_stage() -> None:
    mu = s.Index(S("mu"), s.Lorentz)
    nu = s.Index(S("nu"), s.Lorentz)
    rho = s.Index(S("rho"), s.Lorentz)
    field = s.Field(S("phi"), s.Scalar, s.List(), s.List(mu, rho))
    expr = s.SymmetricLorentzInds(s.List(mu, nu)) * s.NCM(field)
    gamma = s.SymGammaFactor(Expression.num(1), Expression.num(4))

    assert_expr_equal(
        evaluate_symmetric_lorentz_indices(expr, evaluate_gamma=False, contract_metrics=False),
        s.Metric(mu, nu) * gamma * s.NCM(field),
    )
    assert_expr_equal(
        evaluate_symmetric_lorentz_indices(expr, evaluate_gamma=False),
        gamma * s.NCM(s.Field(S("phi"), s.Scalar, s.List(), s.List(nu, rho))),
    )


def test_evaluate_symmetric_lorentz_indices_preserves_matchete_contraction_order() -> None:
    mu = s.Index(S("mu"), s.Lorentz)
    nu = s.Index(S("nu"), s.Lorentz)
    rho = s.Index(S("rho"), s.Lorentz)
    sigma = s.Index(S("sigma"), s.Lorentz)
    field = s.Field(S("phi"), s.Scalar, s.List(), s.List(mu, nu, rho, sigma))
    expr = s.SymmetricLorentzInds(s.List(mu, nu, rho, sigma)) * s.NCM(field)
    gamma = s.SymGammaFactor(Expression.num(2), Expression.num(4))
    metric_sum = (
        s.Metric(mu, nu) * s.Metric(rho, sigma)
        + s.Metric(mu, rho) * s.Metric(nu, sigma)
        + s.Metric(mu, sigma) * s.Metric(nu, rho)
    )

    assert_expr_equal(
        evaluate_symmetric_lorentz_indices(expr, evaluate_gamma=False),
        (metric_sum * gamma * s.NCM(field)).expand(),
    )
