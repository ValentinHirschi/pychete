from __future__ import annotations

from pychete import Theory, s
from pychete.cde import open_covariant_derivative
from pychete.noncommutative import (
    distribute_ncm_additions,
    hoist_commutative_ncm_operands,
    normalize_ncm_chains,
    scalarize_commutative_ncm_chains,
)

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


def test_hoist_commutative_ncm_operands_moves_known_scalars_out_of_mixed_chain() -> None:
    theory = Theory("hoist_ncm_known_scalars")
    scalar = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    left = theory.define_field("psiL", s.Fermion, mass=0)
    right = theory.define_field("psiR", s.Fermion, mass=0)
    coupling = theory.define_coupling("y")
    theory.define_index_type("Flavor")
    i = theory.index("i", "Flavor")
    j = theory.index("j", "Flavor")

    expr = s.NCM(
        -coupling() * s.Bar(scalar()),
        s.Bar(left()),
        s.Delta(i, j),
        s.PR,
        right(),
    )
    expected = -coupling() * s.Bar(scalar()) * s.Delta(i, j) * s.NCM(s.Bar(left()), s.PR, right())

    assert_expr_equal(hoist_commutative_ncm_operands(expr), expected)


def test_hoist_commutative_ncm_operands_preserves_plain_symbol_placeholders() -> None:
    left = s.head("abstract_left")
    right = s.head("abstract_right")

    expr = s.NCM(left, s.PR, right)

    assert_expr_equal(hoist_commutative_ncm_operands(expr), expr)


def test_distribute_ncm_additions_linearizes_additive_operands_before_open_cd() -> None:
    theory = Theory("distribute_ncm_additive_operands")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    chi = theory.define_field("chi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")

    expr = s.NCM(phi() + chi(), open_covariant_derivative(mu), phi())
    expected = s.NCM(phi(), open_covariant_derivative(mu), phi()) + s.NCM(
        chi(),
        open_covariant_derivative(mu),
        phi(),
    )

    assert_expr_equal(distribute_ncm_additions(expr), expected)


def test_distribute_ncm_additions_respects_operand_term_guard() -> None:
    theory = Theory("distribute_ncm_additive_guard")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    chi = theory.define_field("chi", s.Scalar, self_conjugate=True, mass=0)
    eta = theory.define_field("eta", s.Scalar, self_conjugate=True, mass=0)

    expr = s.NCM(phi() + chi() + eta(), phi())

    assert_expr_equal(distribute_ncm_additions(expr, max_operand_terms=2), expr)


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
