from __future__ import annotations

from pychete import Theory, s
from pychete.cde import open_covariant_derivative
from pychete.noncommutative import normalize_ncm_chains, scalarize_commutative_ncm_chains

from tests.conftest import assert_expr_equal


def test_scalarize_commutative_ncm_chains_multiplies_scalar_operands() -> None:
    theory = Theory("scalarize_ncm_scalar_operands")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    chi = theory.define_field("chi", s.Scalar, self_conjugate=True, mass=0)
    y = theory.define_coupling("y", self_conjugate=True)

    expr = s.NCM(-y() * phi(), chi())

    assert_expr_equal(scalarize_commutative_ncm_chains(expr), -y() * phi() * chi())
    assert_expr_equal(scalarize_commutative_ncm_chains(s.NCM(phi() + chi())), phi() + chi())


def test_normalize_ncm_chains_flattens_nested_chains_and_hoists_scalars() -> None:
    theory = Theory("normalize_ncm_nested")
    psi = theory.define_field("psi", s.Fermion, mass=0)
    y = theory.define_coupling("y")

    expr = s.NCM(
        -y() * s.NCM(s.Bar(psi()), s.PR),
        -s.Bar(y()) * s.NCM(s.PL, psi()),
        s.NCM(s.PR, s.PL),
    )
    expected = y() * s.Bar(y()) * s.NCM(s.Bar(psi()), s.PR, s.PL, psi(), s.PR, s.PL)

    assert_expr_equal(normalize_ncm_chains(expr), expected)


def test_scalarize_commutative_ncm_chains_preserves_fermion_chains() -> None:
    theory = Theory("scalarize_ncm_preserve_fermions")
    left = theory.define_field("psiL", s.Fermion, mass=0)
    right = theory.define_field("psiR", s.Fermion, mass=0)

    chain = s.NCM(s.Bar(left()), right())

    assert_expr_equal(scalarize_commutative_ncm_chains(chain), chain)


def test_scalarize_commutative_ncm_chains_preserves_open_cd_chains() -> None:
    theory = Theory("scalarize_ncm_preserve_open_cd")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")

    chain = s.NCM(open_covariant_derivative(mu), phi())

    assert_expr_equal(scalarize_commutative_ncm_chains(chain), chain)
