from __future__ import annotations

from pathlib import Path

from symbolica import PrintMode

from pychete import FieldMassKind, PycheteState, Theory, load_state, s


FORMAT_OPTIONS = {
    "max_line_length": None,
    "color_top_level_sum": False,
    "color_builtin_symbols": False,
    "bracket_level_colors": None,
    "print_ring": False,
    "multiplication_operator": "*",
    "num_exp_as_superscript": False,
}


def _phi4_theory() -> Theory:
    theory = Theory("phi4_pretty")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    lam = theory.define_coupling("lambda")
    theory.set_lagrangian(theory.free_lag(phi) - s.twenty_fourth * lam() * phi() ** 4)
    return theory


def _heavy_scalar_theory() -> Theory:
    theory = Theory("heavy_pretty")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    g = theory.define_coupling("g")
    theory.set_lagrangian(theory.free_lag(heavy, phi) - s.half * g() * heavy() * phi() ** 2)
    return theory


def _format_lagrangian(theory: Theory, mode: PrintMode) -> str:
    assert theory.lagrangian is not None
    return theory.lagrangian.format(mode=mode, **FORMAT_OPTIONS)


def test_phi4_lagrangian_prints_cleanly_in_all_symbolica_modes() -> None:
    theory = _phi4_theory()

    assert _format_lagrangian(theory, PrintMode.Symbolica) == (
        "-1/2*phi^2*m^2-1/24*phi^4*lambda+1/2*D[d](phi)^2"
    )
    assert _format_lagrangian(theory, PrintMode.Latex) == (
        r"-\frac{1}{2} \phi^{2} m^{2}-\frac{1}{24} \phi^{4} \lambda+\frac{1}{2} D_{d}\left(\phi\right)^{2}"
    )
    assert _format_lagrangian(theory, PrintMode.Mathematica) == (
        r"-1/2*\[Phi]^2*m^2-1/24*\[Phi]^4*\[Lambda]+1/2*CD[{d}, \[Phi]]^2"
    )
    assert _format_lagrangian(theory, PrintMode.Sympy) == (
        "-1/2*phi**2*m**2-1/24*phi**4*lambda+1/2*D[d](phi)**2"
    )
    assert _format_lagrangian(theory, PrintMode.Typst) == (
        "-1/2*phi^2*m^2-1/24*phi^4*lambda+1/2*D[d](phi)^2"
    )


def test_heavy_scalar_lagrangian_prints_cleanly_in_all_symbolica_modes() -> None:
    theory = _heavy_scalar_theory()

    assert _format_lagrangian(theory, PrintMode.Symbolica) == (
        "-1/2*S*phi^2*g-1/2*S^2*M^2+1/2*D[d](S)^2+1/2*D[d](phi)^2"
    )
    assert _format_lagrangian(theory, PrintMode.Latex) == (
        r"-\frac{1}{2} S \phi^{2} g-\frac{1}{2} S^{2} M^{2}+\frac{1}{2} D_{d}\left(S\right)^{2}+\frac{1}{2} D_{d}\left(\phi\right)^{2}"
    )
    assert _format_lagrangian(theory, PrintMode.Mathematica) == (
        r"-1/2*S*\[Phi]^2*g-1/2*S^2*M^2+1/2*CD[{d}, S]^2+1/2*CD[{d}, \[Phi]]^2"
    )
    assert _format_lagrangian(theory, PrintMode.Sympy) == (
        "-1/2*S*phi**2*g-1/2*S**2*M**2+1/2*D[d](S)**2+1/2*D[d](phi)**2"
    )
    assert _format_lagrangian(theory, PrintMode.Typst) == (
        "-1/2*S*phi^2*g-1/2*S^2*M^2+1/2*D[d](S)^2+1/2*D[d](phi)^2"
    )


def test_all_builtin_pychete_symbols_have_pretty_print_callbacks() -> None:
    theory = Theory("builtin_pretty")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    lam = theory.define_coupling("lambda")
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    builtins = (
        s.List(mu, nu),
        phi(),
        lam(),
        mu,
        s.FieldStrength(phi.label, s.List(mu, nu), s.List(), s.List()),
        s.Bar(phi()),
        s.CD(mu, phi()),
        s.Delta(mu, nu),
        s.Metric(mu, nu),
        s.FlavorSum(mu, phi()),
        s.NCM(s.Bar(phi()), s.Gamma(mu), phi()),
        s.DiracProduct(s.Bar(phi()), phi()),
        s.Gamma(mu),
        s.Proj(s.PR),
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
    theory = _phi4_theory()
    state = PycheteState()
    state.add_theory(theory)
    path = tmp_path / "pychete_state.json"

    state.save_state(path)
    restored = load_state(path)

    assert restored.active_theory == theory.name
    assert restored.active is not None
    assert restored.active.lagrangian is not None
    assert _format_lagrangian(restored.active, PrintMode.Latex) == _format_lagrangian(theory, PrintMode.Latex)
