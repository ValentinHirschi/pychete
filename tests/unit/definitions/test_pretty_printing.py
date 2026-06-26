from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap

from symbolica import Expression, PrintMode

from pychete import FieldMassKind, PycheteState, Theory, bar_expr, canonical_string, collect_indices, latex_string, load_state, ncm_expr, s
from pychete.matching import HeavyFieldSolution


FORMAT_OPTIONS = {
    "max_line_length": None,
    "color_top_level_sum": False,
    "color_builtin_symbols": False,
    "bracket_level_colors": None,
    "print_ring": False,
    "multiplication_operator": "*",
    "num_exp_as_superscript": False,
}


def _phi4_theory() -> tuple[Theory, Expression]:
    theory = Theory("phi4_pretty")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    lam = theory.define_coupling("lambda")
    lagrangian = theory.free_lag(phi) - lam() * phi() ** 4 / 24
    return theory, lagrangian


def _heavy_scalar_theory() -> tuple[Theory, Expression]:
    theory = Theory("heavy_pretty")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    g = theory.define_coupling("g")
    lagrangian = theory.free_lag(heavy, phi) - g() * heavy() * phi() ** 2 / 2
    return theory, lagrangian


def _format_lagrangian(lagrangian: Expression, mode: PrintMode) -> str:
    if mode is PrintMode.Latex:
        return latex_string(lagrangian)
    return lagrangian.format(mode=mode, **FORMAT_OPTIONS)


def test_phi4_lagrangian_prints_cleanly_in_all_symbolica_modes() -> None:
    _, lagrangian = _phi4_theory()

    assert _format_lagrangian(lagrangian, PrintMode.Symbolica) == (
        "-1/2*phi^2*m^2-1/24*phi^4*lambda+1/2*D[d0](phi)^2"
    )
    assert _format_lagrangian(lagrangian, PrintMode.Latex) == (
        r"-\frac{1}{2} m^{2} \phi^{2}-\frac{1}{24} \lambda \phi^{4}+\frac{1}{2} \left(D_{d0}\phi\right)^{2}"
    )
    assert _format_lagrangian(lagrangian, PrintMode.Mathematica) == (
        r"-1/2*\[Phi]^2*m^2-1/24*\[Phi]^4*\[Lambda]+1/2*CD[{d0}, \[Phi]]^2"
    )
    assert _format_lagrangian(lagrangian, PrintMode.Sympy) == (
        "-1/2*phi**2*m**2-1/24*phi**4*lambda+1/2*D[d0](phi)**2"
    )
    assert _format_lagrangian(lagrangian, PrintMode.Typst) == (
        "-1/2*phi^2*m^2-1/24*phi^4*lambda+1/2*D[d0](phi)^2"
    )


def test_heavy_scalar_lagrangian_prints_cleanly_in_all_symbolica_modes() -> None:
    _, lagrangian = _heavy_scalar_theory()

    assert _format_lagrangian(lagrangian, PrintMode.Symbolica) == (
        "-1/2*S*phi^2*g-1/2*S^2*M^2+1/2*D[d0](S)^2+1/2*D[d0](phi)^2"
    )
    assert _format_lagrangian(lagrangian, PrintMode.Latex) == (
        r"-\frac{1}{2} g S \phi^{2}-\frac{1}{2} M^{2} S^{2}+\frac{1}{2} \left(D_{d0}S\right)^{2}+\frac{1}{2} \left(D_{d0}\phi\right)^{2}"
    )
    assert _format_lagrangian(lagrangian, PrintMode.Mathematica) == (
        r"-1/2*S*\[Phi]^2*g-1/2*S^2*M^2+1/2*CD[{d0}, S]^2+1/2*CD[{d0}, \[Phi]]^2"
    )
    assert _format_lagrangian(lagrangian, PrintMode.Sympy) == (
        "-1/2*S*phi**2*g-1/2*S**2*M**2+1/2*D[d0](S)**2+1/2*D[d0](phi)**2"
    )
    assert _format_lagrangian(lagrangian, PrintMode.Typst) == (
        "-1/2*S*phi^2*g-1/2*S^2*M^2+1/2*D[d0](S)^2+1/2*D[d0](phi)^2"
    )


def test_capitalized_greek_field_names_use_short_internal_labels() -> None:
    theory = Theory("greek_case")
    capital_phi = theory.define_field("Phi", s.Scalar, self_conjugate=True, mass=0)
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    capital_psi = theory.define_field("Psi", s.Fermion, mass=0)
    psi = theory.define_field("psi", s.Fermion, mass=0)

    assert {"Phi", "phi", "Psi", "psi"} <= set(theory.fields)
    assert "Capital" not in canonical_string(capital_phi())
    assert "Capital" not in canonical_string(capital_psi())

    assert capital_phi().format(mode=PrintMode.Symbolica, **FORMAT_OPTIONS) == "Phi"
    assert phi().format(mode=PrintMode.Symbolica, **FORMAT_OPTIONS) == "phi"
    assert capital_psi().format(mode=PrintMode.Symbolica, **FORMAT_OPTIONS) == "Psi"
    assert psi().format(mode=PrintMode.Symbolica, **FORMAT_OPTIONS) == "psi"

    assert capital_phi().format(mode=PrintMode.Latex, **FORMAT_OPTIONS) == r"\Phi"
    assert phi().format(mode=PrintMode.Latex, **FORMAT_OPTIONS) == r"\phi"
    assert capital_phi().format(mode=PrintMode.Mathematica, **FORMAT_OPTIONS) == r"\[CapitalPhi]"
    assert capital_psi().format(mode=PrintMode.Mathematica, **FORMAT_OPTIONS) == r"\[CapitalPsi]"
    assert psi().format(mode=PrintMode.Mathematica, **FORMAT_OPTIONS) == r"\[Psi]"


def test_latex_spinor_derivatives_and_closed_ncm_chains_are_readable() -> None:
    theory = Theory("spinor_latex_pretty")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    psi = theory.define_field("psi", s.Fermion, mass=0)
    mu = theory.lorentz_index("mu")

    assert s.CD(mu, phi()).format(mode=PrintMode.Latex, **FORMAT_OPTIONS) == r"D_{\mu}\phi"
    assert s.Bar(psi(derivatives=[mu])).format(mode=PrintMode.Latex, **FORMAT_OPTIONS) == r"D_{\mu}\bar{\psi}"
    assert s.CD(mu, s.Bar(psi())).format(mode=PrintMode.Latex, **FORMAT_OPTIONS) == r"D_{\mu}\bar{\psi}"
    assert s.Bar(s.CD(mu, psi())).format(mode=PrintMode.Latex, **FORMAT_OPTIONS) == r"D_{\mu}\bar{\psi}"
    assert latex_string(s.CD(mu, phi()) ** 2) == r"\left(D_{\mu}\phi\right)^{2}"
    assert latex_string(s.CD(mu, s.CD(mu, phi()))) == r"D^{2}\phi"
    assert latex_string(phi(derivatives=[mu, mu])) == r"D^{2}\phi"

    closed_chain = ncm_expr(s.Bar(psi()), s.Gamma(mu), psi())
    open_chain = ncm_expr(s.Gamma(mu), psi())
    assert latex_string(closed_chain) == r"\left(\bar{\psi}\,\gamma^{\mu}\,\psi\right)"
    assert latex_string(phi() ** 2 * closed_chain) == (
        r"\phi^{2} \left(\bar{\psi}\,\gamma^{\mu}\,\psi\right)"
    )
    assert latex_string(open_chain) == r"\gamma^{\mu}\,\psi"


def test_latex_products_put_prefactors_before_operators() -> None:
    theory = Theory("prefactor_latex_pretty")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    psi = theory.define_field("psi", s.Fermion, mass=0)
    lam = theory.define_coupling("lambda")
    y = theory.define_coupling("y")
    mass = theory.define_coupling("M")
    mu = theory.lorentz_index("mu")
    closed_chain = ncm_expr(s.Bar(psi()), s.Gamma(mu), psi())

    assert latex_string(phi() ** 4 * lam() / 24) == r"\frac{1}{24} \lambda \phi^{4}"
    assert latex_string(phi() ** 2 * y() * closed_chain / 3) == (
        r"\frac{1}{3} y \phi^{2} \left(\bar{\psi}\,\gamma^{\mu}\,\psi\right)"
    )
    assert latex_string(-phi() ** 2 * y() * closed_chain / (2 * mass() ** 2)) == (
        r"-\frac{1}{2 M^{2}} y \phi^{2} \left(\bar{\psi}\,\gamma^{\mu}\,\psi\right)"
    )


def test_latex_imaginary_mass_suppressed_spinor_term_keeps_operator_out_of_fraction() -> None:
    theory = Theory("imaginary_prefactor_latex_pretty")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    psi = theory.define_field("psi", s.Fermion, mass=0)
    y = theory.define_coupling("y", self_conjugate=False)
    mass = theory.define_coupling("M")
    mu = theory.lorentz_index("mu")
    closed_chain = ncm_expr(s.Bar(psi()), s.Gamma(mu), s.PL, psi())

    expr = -Expression.I * bar_expr(y()) * y() * phi() ** 2 * closed_chain / (2 * mass() ** 2)

    assert latex_string(expr) == (
        r"-\frac{\mathrm{i}}{2 M^{2}} \bar{y} y \phi^{2} "
        r"\left(\bar{\psi}\,\gamma^{\mu}\,P_L\,\psi\right)"
    )


def test_all_builtin_pychete_symbols_have_pretty_print_callbacks() -> None:
    theory = Theory("builtin_pretty")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    lam = theory.define_coupling("lambda")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    builtins = (
        s.List(mu, nu),
        s.InternalIndices(mu, nu),
        s.DerivativeIndices(mu, nu),
        s.LorentzIndices(mu, nu),
        phi(),
        lam(),
        mu,
        s.dummy_index(0),
        s.FieldStrength(phi.label, s.LorentzIndices(mu, nu), s.InternalIndices(), s.DerivativeIndices()),
        s.Bar(phi()),
        s.CD(mu, phi()),
        s.Delta(mu, nu),
        s.Metric(mu, nu),
        s.FlavorSum(mu, phi()),
        s.NCM(s.Bar(phi()), s.Gamma(mu), phi()),
        s.DiracProduct(s.Bar(phi()), phi()),
        s.Gamma(mu),
        s.CG(mu, nu),
        s.EOM(phi(), phi()),
        s.HeavyFieldOrder(phi(), 1),
        s.Scalar,
        s.Fermion,
        s.Vector(s.U1),
        s.Ghost,
        s.AntiGhost,
        s.Lorentz,
        s.U1,
        s.SU(3),
        s.fund,
        s.adj,
        s.PR,
        s.PL,
        s.ConjBodyWildcard,
        s.NCMLeftWildcard,
        s.NCMRightWildcard,
        s.NCMInnerWildcard,
        s.NCMFactorWildcard,
        s.NCMSplitFactorWildcard,
        s.NCMSplitRestWildcard,
        s.NCMGammaIndexWildcard,
        s.FieldLabelWildcard,
        s.FieldTypeWildcard,
        s.FieldIndicesWildcard,
        s.FieldDerivativesWildcard,
        s.IndexLabelWildcard,
        s.IndexRepresentationWildcard,
        s.PowBaseWildcard,
        s.PowExponentWildcard,
        s.CDIndexWildcard,
        s.CDBodyWildcard,
        s.CouplingLabelWildcard,
        s.CouplingIndicesWildcard,
        s.CouplingOrderWildcard,
        s.FieldStrengthLabelWildcard,
        s.FieldStrengthLorentzWildcard,
        s.FieldStrengthIndicesWildcard,
        s.FieldStrengthDerivativesWildcard,
        s.EFTExpansionParameter,
        s.CDVariationParameter,
        s.FunctionalVariationParameter,
    )

    for expr in builtins:
        for mode in (PrintMode.Symbolica, PrintMode.Latex, PrintMode.Mathematica, PrintMode.Sympy, PrintMode.Typst):
            output = expr.format(mode=mode, **FORMAT_OPTIONS)
            assert output
            assert "pychete::" not in output


def test_saved_state_reloads_active_lagrangian_with_pretty_printing(tmp_path: Path) -> None:
    theory, lagrangian = _phi4_theory()
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)
    path = tmp_path / "pychete_state.json"

    state.save_state(path)
    restored = load_state(path)

    assert restored.active_theory == theory.name
    assert restored.active is not None
    restored_lagrangian = restored.get_expression("lagrangian")
    assert _format_lagrangian(restored_lagrangian, PrintMode.Latex) == _format_lagrangian(lagrangian, PrintMode.Latex)


def test_saved_state_cold_load_restores_symbol_manifest_before_parsing(tmp_path: Path) -> None:
    path = tmp_path / "pychete_state.json"
    project_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")

    save_script = textwrap.dedent(
        """
        from pathlib import Path
        import sys

        from pychete import FieldMassKind, PycheteState, Theory, s

        theory = Theory("cold_pretty")
        phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
        lam = theory.define_coupling("lambda")
        lagrangian = theory.free_lag(phi) - lam() * phi() ** 4 / 24
        state = PycheteState()
        state.add_theory(theory)
        state.add_expression("lagrangian", theory, lagrangian)
        state.save_state(Path(sys.argv[1]))
        """
    )
    subprocess.run([sys.executable, "-c", save_script, str(path)], check=True, env=env)

    load_script = textwrap.dedent(
        """
        from pathlib import Path
        import sys

        from symbolica import PrintMode

        from pychete import canonical_string, collect_indices, latex_string, load_state

        format_options = {
            "max_line_length": None,
            "color_top_level_sum": False,
            "color_builtin_symbols": False,
            "bracket_level_colors": None,
            "print_ring": False,
            "multiplication_operator": "*",
            "num_exp_as_superscript": False,
        }

        state = load_state(Path(sys.argv[1]))
        theory = state.active
        assert theory is not None
        lagrangian = state.get_expression("lagrangian")
        assert theory.field_handle("phi").label.get_symbol_data("mass_label") == theory.coupling_handle("m").label
        assert "index:d" not in theory._symbols
        assert "pychete::Index(pychete::dummy_index(0),pychete::Lorentz)" in canonical_string(lagrangian)
        assert any(canonical_string(info.label) == "pychete::dummy_index(0)" for info in collect_indices(lagrangian))
        symbolica = lagrangian.format(mode=PrintMode.Symbolica, **format_options)
        latex = latex_string(lagrangian)
        assert symbolica == "-1/2*phi^2*m^2-1/24*phi^4*lambda+1/2*D[d0](phi)^2"
        assert latex == r"-\\frac{1}{2} m^{2} \\phi^{2}-\\frac{1}{24} \\lambda \\phi^{4}+\\frac{1}{2} \\left(D_{d0}\\phi\\right)^{2}"
        assert "Field(" not in symbolica
        assert "Coupling(" not in symbolica
        """
    )
    subprocess.run([sys.executable, "-c", load_script, str(path)], check=True, env=env)


def test_pychete_objects_expose_jupyter_repr_hooks() -> None:
    theory, lagrangian = _phi4_theory()
    phi = theory.field_handle("phi")
    lam = theory.coupling_handle("lambda")
    index_info = collect_indices(theory.lorentz_index("mu"))[0]
    solution = HeavyFieldSolution(field=phi.definition, orders={1: phi()})
    state = PycheteState()
    state.add_theory(theory)
    state.add_expression("lagrangian", theory, lagrangian)

    objects = (
        theory,
        state,
        phi,
        lam,
        phi.definition,
        lam.definition,
        index_info,
        solution,
    )

    for obj in objects:
        assert obj._repr_latex_()
        assert obj._repr_html_()
