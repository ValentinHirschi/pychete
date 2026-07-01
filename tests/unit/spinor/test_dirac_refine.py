from __future__ import annotations

from symbolica.core import SymbolAttribute

from pychete import Theory, ncm_expr, refine_dirac_products, s

from tests.conftest import assert_expr_equal


def test_dirac_basis_heads_use_native_symbolica_symmetries() -> None:
    theory = Theory("dirac_native_symmetry")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    assert SymbolAttribute.Symmetric in s.Metric.get_attributes()
    assert SymbolAttribute.Antisymmetric in s.LCTensor.get_attributes()
    assert SymbolAttribute.Antisymmetric in s.Gamma.get_attributes()
    assert bool(s.Metric(nu, mu) == s.Metric(mu, nu))
    assert_expr_equal(s.LCTensor(nu, mu), -s.LCTensor(mu, nu))
    assert_expr_equal(s.Gamma(nu, mu), -s.Gamma(mu, nu))
    assert_expr_equal(s.Gamma(mu, mu), 0)
    assert not bool(s.Gamma5 == s.Gamma(5))


def test_refine_dirac_products_expands_two_gammas_to_metric_plus_antisymmetric_basis() -> None:
    theory = Theory("dirac_refine_pair")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    expr = refine_dirac_products(ncm_expr(s.Gamma(mu), s.Gamma(nu)))

    assert_expr_equal(expr, s.Metric(mu, nu) + s.DiracProduct(s.Gamma(mu, nu)))


def test_refine_dirac_products_contracts_repeated_lorentz_gamma_pair() -> None:
    theory = Theory("dirac_refine_repeated_pair")
    mu = theory.lorentz_index("mu")

    expr = refine_dirac_products(ncm_expr(s.Gamma(mu), s.Gamma(mu)))

    assert_expr_equal(expr, s.SpacetimeDimension)


def test_refine_dirac_products_contracts_separated_repeated_lorentz_indices() -> None:
    theory = Theory("dirac_refine_separated_repeated")
    mu = theory.lorentz_index("mu")
    alpha = theory.lorentz_index("alpha")

    expr = refine_dirac_products(s.DiracProduct(s.Gamma(mu), s.Gamma(alpha), s.Gamma(mu)))

    assert_expr_equal(expr, (2 - s.SpacetimeDimension) * s.DiracProduct(s.Gamma(alpha)))


def test_refine_dirac_products_refines_multi_index_gamma_times_single_gamma() -> None:
    theory = Theory("dirac_refine_multi_index")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    rho = theory.lorentz_index("rho")

    expr = refine_dirac_products(s.DiracProduct(s.Gamma(mu, nu), s.Gamma(rho)))
    expected = (
        s.DiracProduct(s.Gamma(mu, nu, rho))
        + s.Metric(nu, rho) * s.DiracProduct(s.Gamma(mu))
        - s.Metric(mu, rho) * s.DiracProduct(s.Gamma(nu))
    )

    assert_expr_equal(expr, expected)


def test_refine_dirac_products_keeps_trailing_projector_attached_to_each_basis_term() -> None:
    theory = Theory("dirac_refine_projector")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    expr = refine_dirac_products(s.DiracProduct(s.Gamma(mu), s.Gamma(nu), s.PL))
    expected = s.Metric(mu, nu) * s.DiracProduct(s.PL) + s.DiracProduct(s.Gamma(mu, nu), s.PL)

    assert_expr_equal(expr, expected)


def test_refine_dirac_products_distributes_inside_closed_ncm_chain() -> None:
    theory = Theory("dirac_refine_closed_ncm")
    psi = theory.define_field("psi", s.Fermion, mass=0)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    expr = refine_dirac_products(ncm_expr(s.Bar(psi()), s.Gamma(mu), s.Gamma(nu), psi()))
    expected = s.Metric(mu, nu) * ncm_expr(s.Bar(psi()), psi()) + ncm_expr(s.Bar(psi()), s.Gamma(mu, nu), psi())

    assert_expr_equal(expr, expected)


def test_refine_dirac_products_leaves_non_lorentz_gamma_atoms_unmatched() -> None:
    expr = refine_dirac_products(s.DiracProduct(s.Gamma5, s.Gamma5))

    assert_expr_equal(expr, s.DiracProduct(s.Gamma5, s.Gamma5))


def test_refine_dirac_products_treats_empty_gamma_as_identity() -> None:
    expr = refine_dirac_products(s.DiracProduct(s.Gamma()))

    assert_expr_equal(expr, 1)
