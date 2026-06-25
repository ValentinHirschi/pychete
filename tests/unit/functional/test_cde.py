from __future__ import annotations

import pytest
from symbolica import Expression

from pychete import Theory, s
from pychete.cde import act_with_open_covariant_derivatives, open_covariant_derivative

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
