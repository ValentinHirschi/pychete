from __future__ import annotations

from pathlib import Path

from symbolica import Expression

from pychete import FieldVariation, bar_expr, s
from pychete.functional import partial_functional_derivative
from pychete.loaders import load_python_model
from pychete.spinor import ncm_expr

from tests.conftest import assert_expr_equal


def test_heavy_fermion_eom_keeps_open_ncm_chains() -> None:
    theory, expressions = load_python_model(Path("assets/models/VLF_toy_model.py"))
    psi = theory.field_handle("psi")
    heavy = theory.field_handle("Psi")
    phi = theory.field_handle("phi")
    y = theory.coupling_handle("y")
    mass = theory.coupling_handle("M")
    mu = theory.dummy_index(0)

    eom = theory.derive_eom(expressions["lagrangian"], heavy, variation=FieldVariation.BAR)
    expected = (
        -mass() * heavy()
        - phi() * bar_expr(y()) * ncm_expr(s.PL, psi())
        + Expression.I * ncm_expr(s.Gamma(mu), heavy(derivatives=[mu]))
    )

    assert_expr_equal(eom, expected)


def test_fermion_functional_derivative_tracks_grassmann_sign_inside_ncm() -> None:
    theory, _ = load_python_model(Path("assets/models/VLF_toy_model.py"))
    psi = theory.field_handle("psi")
    heavy = theory.field_handle("Psi")

    chain = ncm_expr(s.Bar(psi()), s.PR, heavy())

    assert_expr_equal(partial_functional_derivative(chain, heavy()), -ncm_expr(s.Bar(psi()), s.PR))
