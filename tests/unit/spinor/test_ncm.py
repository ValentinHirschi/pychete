from __future__ import annotations

from pychete import FieldMassKind, SpinChainKind, Theory, bar_expr, ncm_expr, normalize_ncm, s, spin_chain_kind
from pychete.spinor import is_commutative_spin_factor

from tests.conftest import assert_expr_equal


def test_ncm_extracts_commutative_scalar_from_spin_chain() -> None:
    theory = Theory("ncm_scalar")
    psi = theory.define_field("psi", s.Fermion, mass=0)
    heavy = theory.define_field("Psi", s.Fermion, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)

    expr = normalize_ncm(s.NCM(s.Bar(psi()), phi(), s.PR, heavy()))

    assert_expr_equal(expr, phi() * ncm_expr(s.Bar(psi()), s.PR, heavy()))
    assert spin_chain_kind(expr) is SpinChainKind.CLOSED


def test_bar_expr_reverses_ncm_chain_and_swaps_projectors() -> None:
    theory = Theory("ncm_bar")
    psi = theory.define_field("psi", s.Fermion, mass=0)
    heavy = theory.define_field("Psi", s.Fermion, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    y = theory.define_coupling("y")

    expr = -y() * phi() * ncm_expr(s.Bar(psi()), s.PR, heavy())
    expected = -bar_expr(y()) * phi() * ncm_expr(s.Bar(heavy()), s.PL, psi())

    assert_expr_equal(bar_expr(expr), expected)


def test_projector_rules_and_open_spin_chain_classification() -> None:
    theory = Theory("ncm_projectors")
    psi = theory.define_field("psi", s.Fermion, mass=0)
    mu = theory.lorentz_index("mu")

    assert_expr_equal(ncm_expr(s.Bar(psi()), s.PR, s.PL, psi()), 0)
    assert_expr_equal(
        ncm_expr(s.Bar(psi()), s.PR, s.Gamma(mu), s.PL, psi()),
        ncm_expr(s.Bar(psi()), s.Gamma(mu), s.PL, psi()),
    )
    assert spin_chain_kind(ncm_expr(s.PL, psi())) is SpinChainKind.LEFT_OPEN
    assert spin_chain_kind(ncm_expr(s.Bar(psi()), s.PR)) is SpinChainKind.RIGHT_OPEN
    assert spin_chain_kind(ncm_expr(s.Gamma(mu), s.PL)) is SpinChainKind.MATRIX


def test_commutative_spin_factor_defaults_to_true_except_spinor_space_objects() -> None:
    theory = Theory("ncm_commutative_hot_path")
    psi = theory.define_field("psi", s.Fermion, mass=0)
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    ordinary = theory.symbol("ordinary", role="external")
    mu = theory.lorentz_index("mu")

    assert not is_commutative_spin_factor(psi())
    assert not is_commutative_spin_factor(s.Bar(psi()))
    assert not is_commutative_spin_factor(s.CD(mu, psi()))
    assert not is_commutative_spin_factor(s.Gamma(mu))
    assert not is_commutative_spin_factor(s.PR)
    assert not is_commutative_spin_factor(ncm_expr(s.Bar(psi()), psi()))

    assert is_commutative_spin_factor(phi())
    assert is_commutative_spin_factor(s.Bar(phi()))
    assert is_commutative_spin_factor(s.CD(mu, phi()))
    assert is_commutative_spin_factor(ordinary(psi()))
