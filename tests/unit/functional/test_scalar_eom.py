from __future__ import annotations

from pychete import Theory, derive_eom, s

from tests.conftest import assert_expr_equal


def test_phi4_scalar_eom_matches_matchete_reference_shape() -> None:
    theory = Theory("phi4")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=("Light", "m"))
    lam = theory.define_coupling("lambda", self_conjugate=True)
    mu = theory.lorentz_index("d")

    lagrangian = theory.free_lag(phi) - s.twenty_fourth * lam() * phi() ** 4
    expected = (
        -phi() * theory.coupling_handle("m")() ** 2
        - phi(derivatives=[mu, mu])
        - s.sixth * lam() * phi() ** 3
    )

    assert_expr_equal(derive_eom(theory, lagrangian, phi), expected)
