from __future__ import annotations

from pathlib import Path

from symbolica import Expression

from pychete import HeavyFieldFamily, bar_expr, canonical_string, s
from pychete.loaders import load_matchete_model, load_python_model
from pychete.spinor import ncm_expr

from tests.conftest import assert_expr_equal


def _expected_vlf_tree_result(path: str):
    theory, expressions = load_python_model(Path(path))
    psi = theory.field_handle("psi")
    phi = theory.field_handle("phi")
    y = theory.coupling_handle("y")
    mass = theory.coupling_handle("M")
    mu = theory.dummy_index(0)
    light_lagrangian = theory.free_lag("A", "psi", "phi")
    tree_operator = (
        Expression.I
        * phi() ** 2
        * y()
        * bar_expr(y())
        * (
            ncm_expr(s.Bar(psi()), s.Gamma(mu), s.PL, psi(derivatives=[mu]))
            - ncm_expr(s.Bar(psi(derivatives=[mu])), s.Gamma(mu), s.PL, psi())
        )
        / (2 * mass() ** 2)
    )
    return theory, expressions, light_lagrangian + tree_operator


def test_vlf_python_asset_matches_raw_offshell_tree_result_through_dimension_six() -> None:
    theory, expressions, expected = _expected_vlf_tree_result("assets/models/VLF_toy_model.py")
    solution = theory.solve_heavy_field_eoms(expressions["lagrangian"], eft_order=6)["Psi"]
    assert solution.family is HeavyFieldFamily.FERMION

    matched = theory.match(expressions["lagrangian"], eft_order=6, loop_order=0)

    assert "field_Psi" not in canonical_string(matched)
    assert_expr_equal(matched, expected)


def test_vlf_mathematica_asset_matches_python_asset_tree_result() -> None:
    mathematica_theory, mathematica_expressions = load_matchete_model(Path("assets/models/VLF_toy_model.m"))
    python_theory, python_expressions, expected = _expected_vlf_tree_result("assets/models/VLF_toy_model.py")

    mathematica_matched = mathematica_theory.match(mathematica_expressions["lagrangian"], eft_order=6, loop_order=0)
    python_matched = python_theory.match(python_expressions["lagrangian"], eft_order=6, loop_order=0)

    assert "field_Psi" not in canonical_string(mathematica_matched)
    assert_expr_equal(mathematica_matched, expected)
    assert_expr_equal(python_matched, expected)


def test_matching_rejects_nonzero_loop_order_for_now() -> None:
    theory, expressions, _ = _expected_vlf_tree_result("assets/models/VLF_toy_model.py")

    try:
        theory.match(expressions["lagrangian"], eft_order=6, loop_order=1)
    except NotImplementedError as exc:
        assert "loop_order=0" in str(exc)
    else:
        raise AssertionError("expected nonzero loop order to be rejected")
