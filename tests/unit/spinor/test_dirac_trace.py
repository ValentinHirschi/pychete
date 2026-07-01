from __future__ import annotations

from symbolica import Expression, S
from symbolica.core import SymbolAttribute

from pychete import Theory, dirac_trace, ncm_expr, s

from tests.conftest import assert_expr_equal


def test_lc_tensor_uses_native_symbolica_antisymmetry() -> None:
    theory = Theory("dirac_trace_lc_symmetry")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    assert SymbolAttribute.Antisymmetric in s.LCTensor.get_attributes()
    assert_expr_equal(s.LCTensor(nu, mu), -s.LCTensor(mu, nu))
    assert_expr_equal(s.LCTensor(mu, mu), 0)


def test_dirac_trace_multiplies_scalar_terms_by_spin_dimension() -> None:
    theory = Theory("dirac_trace_scalar")
    c = theory.define_coupling("c")

    assert_expr_equal(dirac_trace(c()), 4 * c())


def test_dirac_trace_two_gammas() -> None:
    theory = Theory("dirac_trace_pair")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    expr = dirac_trace(ncm_expr(s.Gamma(mu), s.Gamma(nu)))

    assert_expr_equal(expr, 4 * s.Metric(mu, nu))


def test_dirac_trace_repeated_lorentz_pair_keeps_spacetime_dimension() -> None:
    theory = Theory("dirac_trace_repeated_pair")
    mu = theory.lorentz_index("mu")

    expr = dirac_trace(s.DiracProduct(s.Gamma(mu), s.Gamma(mu)))

    assert_expr_equal(expr, 4 * s.SpacetimeDimension)


def test_dirac_trace_can_substitute_dimension() -> None:
    theory = Theory("dirac_trace_dimension")
    mu = theory.lorentz_index("mu")
    eps = S("eps")

    expr = dirac_trace(s.DiracProduct(s.Gamma(mu), s.Gamma(mu)), dimension=4 - 2 * eps)

    assert_expr_equal(expr, 4 * (4 - 2 * eps))


def test_dirac_trace_four_gammas() -> None:
    theory = Theory("dirac_trace_four")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    rho = theory.lorentz_index("rho")
    sigma = theory.lorentz_index("sigma")

    expr = dirac_trace(s.DiracProduct(s.Gamma(mu), s.Gamma(nu), s.Gamma(rho), s.Gamma(sigma)))
    expected = 4 * (
        s.Metric(mu, nu) * s.Metric(rho, sigma)
        - s.Metric(mu, rho) * s.Metric(nu, sigma)
        + s.Metric(mu, sigma) * s.Metric(nu, rho)
    )

    assert_expr_equal(expr, expected)


def test_dirac_trace_with_multi_index_gamma() -> None:
    theory = Theory("dirac_trace_multi_index")
    alpha = theory.lorentz_index("alpha")
    beta = theory.lorentz_index("beta")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    expr = dirac_trace(s.DiracProduct(s.Gamma(alpha), s.Gamma(beta), s.Gamma(mu, nu)))
    expected = 4 * s.Metric(alpha, nu) * s.Metric(beta, mu) - 4 * s.Metric(alpha, mu) * s.Metric(beta, nu)

    assert_expr_equal(expr, expected)


def test_dirac_trace_with_right_projector_matches_matchete_reference_shape() -> None:
    theory = Theory("dirac_trace_projector")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    rho = theory.lorentz_index("rho")
    sigma = theory.lorentz_index("sigma")

    expr = dirac_trace(s.DiracProduct(s.Gamma(mu), s.Gamma(nu), s.Gamma(rho), s.Gamma(sigma), s.PR))
    expected = (
        2 * s.Metric(mu, sigma) * s.Metric(nu, rho)
        - 2 * s.Metric(mu, rho) * s.Metric(nu, sigma)
        + 2 * s.Metric(mu, nu) * s.Metric(rho, sigma)
        - 2 * Expression.I * s.LCTensor(mu, nu, rho, sigma)
    )

    assert_expr_equal(expr, expected)


def test_dirac_trace_uses_standalone_gamma5_symbol() -> None:
    theory = Theory("dirac_trace_gamma5")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    rho = theory.lorentz_index("rho")
    sigma = theory.lorentz_index("sigma")

    expr = dirac_trace(s.DiracProduct(s.Gamma(mu), s.Gamma(nu), s.Gamma(rho), s.Gamma(sigma), s.Gamma5))

    assert_expr_equal(expr, -4 * Expression.I * s.LCTensor(mu, nu, rho, sigma))


def test_dirac_trace_leaves_multiple_dirac_products_unchanged() -> None:
    theory = Theory("dirac_trace_multiple_products")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    expr = s.DiracProduct(s.Gamma(mu)) * s.DiracProduct(s.Gamma(nu))

    assert_expr_equal(dirac_trace(expr), expr)
