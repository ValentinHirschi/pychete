from __future__ import annotations

from pychete import FieldMassKind, Theory, s
from pychete.functional import functional_derivative_operator, open_cd_expr

from tests.conftest import assert_expr_equal


def test_functional_derivative_operator_preserves_open_derivatives() -> None:
    theory = Theory("open_cd_functional")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    mu = theory.lorentz_index("mu")
    lagrangian = phi(derivatives=[mu]) ** 2 / 2

    derivative = functional_derivative_operator(lagrangian, phi())

    assert_expr_equal(derivative, -s.FuncNCM(open_cd_expr(mu), phi(derivatives=[mu])))
