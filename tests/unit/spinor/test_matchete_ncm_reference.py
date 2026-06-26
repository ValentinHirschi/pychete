"""Pychete ports of in-scope Matchete ``Validation/Tests/NCM.wl`` tests.

Covered TestIDs:
``Extract scalar from spin chain``, ``Extract derivative scalar from spin
chain``, ``Contraction of spinors 1-3``, ``LOpenSpinChainQ 1-5, 7, 9``,
``ROpenSpinChainQ 1-5, 7, 9``, ``ClosedSpinChainQ 1-4``, and the current-scope
no-op parts of ``CanonizeSpinorLines: nothing 1, 2, 4``.

The remaining active Matchete NCM tests require charge conjugation,
transpose-canonical ordering, Majorana/GammaCC handling, explicit
``CanonizeSpinorLines`` diagnostics, or FermionTrace/CDE machinery that pychete
does not currently implement.
"""

from __future__ import annotations

from symbolica import Expression

from pychete import (
    Theory,
    is_closed_spin_chain,
    is_left_open_spin_chain,
    is_right_open_spin_chain,
    ncm_expr,
    normalize_ncm,
    s,
)

from tests.conftest import assert_expr_equal


def _ncm_reference_theory():
    theory = Theory("matchete_ncm_reference")
    psi_m = theory.define_field("psiM", s.Fermion, self_conjugate=True, mass=0)
    psi_d = theory.define_field("psiD", s.Fermion, mass=0)
    psi_l = theory.define_field("psiL", s.Fermion, mass=0)
    psi_r = theory.define_field("psiR", s.Fermion, mass=0)
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    coupling_m = theory.define_coupling("m")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    gamma5 = s.Gamma(Expression.num(5))
    return theory, psi_m, psi_d, psi_l, psi_r, phi, coupling_m, mu, nu, gamma5


def test_matchete_ncm_extract_scalar_from_spin_chain() -> None:
    _, _, _, psi_l, psi_r, phi, _, _, _, _ = _ncm_reference_theory()

    expr = ncm_expr(s.Bar(psi_l()), phi(), psi_r())

    assert_expr_equal(expr, phi() * ncm_expr(s.Bar(psi_l()), psi_r()))


def test_matchete_ncm_extract_derivative_scalar_from_spin_chain() -> None:
    _, psi_m, _, psi_l, _, phi, _, mu, _, _ = _ncm_reference_theory()

    expr = ncm_expr(s.Bar(psi_l()), s.Gamma(mu), Expression.I * s.CD(mu, phi()), psi_l())

    assert_expr_equal(expr, Expression.I * s.CD(mu, phi()) * ncm_expr(s.Bar(psi_l()), s.Gamma(mu), psi_l()))
    assert not is_left_open_spin_chain(s.Bar(psi_m(derivatives=[mu])))


def test_matchete_ncm_contraction_of_spinors_1() -> None:
    _, psi_m, psi_d, _, _, _, _, mu, _, _ = _ncm_reference_theory()

    expr = normalize_ncm(
        s.NCM(
            s.Bar(psi_d()),
            s.NCM(s.Gamma(mu), s.Bar(psi_m()), s.Gamma(mu), psi_m()),
            psi_d(),
        )
    )
    expected = ncm_expr(s.Bar(psi_d()), s.Gamma(mu), psi_d()) * ncm_expr(s.Bar(psi_m()), s.Gamma(mu), psi_m())

    assert_expr_equal(expr, expected)


def test_matchete_ncm_contraction_of_spinors_2() -> None:
    _, psi_m, psi_d, _, _, _, _, mu, _, gamma5 = _ncm_reference_theory()

    expr = normalize_ncm(
        s.NCM(
            s.Bar(psi_d()),
            s.NCM(s.Gamma(mu), gamma5, s.Bar(psi_m()), s.Gamma(mu), psi_m()),
            psi_d(),
        )
    )
    expected = ncm_expr(s.Bar(psi_d()), s.Gamma(mu), gamma5, psi_d()) * ncm_expr(s.Bar(psi_m()), s.Gamma(mu), psi_m())

    assert_expr_equal(expr, expected)


def test_matchete_ncm_contraction_of_spinors_3() -> None:
    _, psi_m, _, psi_l, psi_r, _, coupling_m, mu, _, _ = _ncm_reference_theory()

    expr = normalize_ncm(
        s.NCM(
            s.Bar(psi_l()),
            coupling_m() * s.NCM(s.Bar(psi_m()), s.Gamma(mu), psi_m()),
            psi_r(),
        )
    )
    expected = coupling_m() * ncm_expr(s.Bar(psi_l()), psi_r()) * ncm_expr(s.Bar(psi_m()), s.Gamma(mu), psi_m())

    assert_expr_equal(expr, expected)


def test_matchete_ncm_lopen_spin_chain_predicates() -> None:
    _, psi_m, _, _, _, _, _, mu, _, _ = _ncm_reference_theory()

    assert not is_left_open_spin_chain(ncm_expr(s.Bar(psi_m()), s.Gamma(mu), psi_m()))
    assert is_left_open_spin_chain(ncm_expr(s.Gamma(mu), psi_m()))
    assert not is_left_open_spin_chain(ncm_expr(s.Bar(psi_m()), s.Gamma(mu)))
    assert is_left_open_spin_chain(s.Gamma(mu))
    assert is_left_open_spin_chain(psi_m())
    assert not is_left_open_spin_chain(s.Bar(psi_m()))
    assert not is_left_open_spin_chain(s.Bar(psi_m(derivatives=[mu])))


def test_matchete_ncm_ropen_spin_chain_predicates() -> None:
    _, psi_m, _, _, _, _, _, mu, _, gamma5 = _ncm_reference_theory()

    assert not is_right_open_spin_chain(ncm_expr(s.Bar(psi_m()), s.Gamma(mu), psi_m()))
    assert not is_right_open_spin_chain(ncm_expr(s.Gamma(mu), psi_m()))
    assert is_right_open_spin_chain(ncm_expr(s.Bar(psi_m()), s.Gamma(mu)))
    assert is_right_open_spin_chain(ncm_expr(s.Gamma(mu), gamma5))
    assert not is_right_open_spin_chain(psi_m())
    assert is_right_open_spin_chain(s.Bar(psi_m()))
    assert is_right_open_spin_chain(s.Bar(psi_m(derivatives=[mu])))


def test_matchete_ncm_closed_spin_chain_predicates() -> None:
    _, psi_m, _, _, _, phi, _, mu, _, _ = _ncm_reference_theory()

    assert is_closed_spin_chain(ncm_expr(s.Bar(psi_m()), s.Gamma(mu), psi_m()))
    assert not is_closed_spin_chain(ncm_expr(s.Bar(psi_m()), s.Gamma(mu)))
    assert not is_closed_spin_chain(psi_m())
    assert not is_closed_spin_chain(phi())


def test_matchete_ncm_canonize_spinor_lines_nothing_cases_in_current_scope() -> None:
    _, psi_m, _, psi_l, psi_r, _, _, mu, nu, _ = _ncm_reference_theory()

    closed = ncm_expr(s.Bar(psi_l()), s.Gamma(mu, nu), psi_r())
    reversed_open = ncm_expr(psi_m(), s.Bar(psi_r()))
    left_open = ncm_expr(s.Gamma(mu, nu), s.PL, psi_m())

    assert_expr_equal(normalize_ncm(closed), closed)
    assert_expr_equal(normalize_ncm(reversed_open), reversed_open)
    assert_expr_equal(normalize_ncm(left_open), left_open)
