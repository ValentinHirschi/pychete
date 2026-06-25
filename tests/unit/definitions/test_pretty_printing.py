from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap

from symbolica import Expression, PrintMode

from pychete import FieldMassKind, MatchingResult, PycheteState, Theory, canonical_string, collect_indices, load_state, s
from pychete.backends import vacuum_integrals
from pychete.matching import HeavyScalarSolution


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
    return lagrangian.format(mode=mode, **FORMAT_OPTIONS)


def test_phi4_lagrangian_prints_cleanly_in_all_symbolica_modes() -> None:
    _, lagrangian = _phi4_theory()

    assert _format_lagrangian(lagrangian, PrintMode.Symbolica) == (
        "-1/2*phi^2*m^2-1/24*phi^4*lambda+1/2*D[d0](phi)^2"
    )
    assert _format_lagrangian(lagrangian, PrintMode.Latex) == (
        r"-\frac{1}{2} \phi^{2} m^{2}-\frac{1}{24} \phi^{4} \lambda+\frac{1}{2} D_{d0}\left(\phi\right)^{2}"
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
        r"-\frac{1}{2} S \phi^{2} g-\frac{1}{2} S^{2} M^{2}+\frac{1}{2} D_{d0}\left(S\right)^{2}+\frac{1}{2} D_{d0}\left(\phi\right)^{2}"
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


def test_supertrace_denominator_heads_print_cleanly_in_all_symbolica_modes() -> None:
    denominator = s.PropagatorDenominator(s.LoopMomentumSquared, Expression.num(2))
    kernel = s.SupertraceKernel(Expression.num(3), s.List(s.List(denominator)))
    momentum = s.LoopMomentum(s.dummy_index(0))
    open_cd = s.OpenCD(s.List(s.dummy_index(0)))

    assert _format_lagrangian(momentum, PrintMode.Symbolica) == "q[d0]"
    assert _format_lagrangian(momentum, PrintMode.Latex) == "q_{d0}"
    assert _format_lagrangian(momentum, PrintMode.Mathematica) == "q[d0]"
    assert _format_lagrangian(momentum, PrintMode.Sympy) == "q[d0]"
    assert _format_lagrangian(momentum, PrintMode.Typst) == "q_d0"
    assert _format_lagrangian(denominator, PrintMode.Symbolica) == "prop_den(q2, 2)"
    assert _format_lagrangian(denominator, PrintMode.Latex) == r"\mathcal{D}\left(q^2, 2\right)"
    assert _format_lagrangian(denominator, PrintMode.Mathematica) == "PropagatorDenominator[q2, 2]"
    assert _format_lagrangian(denominator, PrintMode.Sympy) == "prop_den(q2, 2)"
    assert _format_lagrangian(denominator, PrintMode.Typst) == "prop_den(q^2, 2)"
    assert _format_lagrangian(kernel, PrintMode.Symbolica) == "supertrace_kernel(3, {{prop_den(q2, 2)}})"
    assert _format_lagrangian(open_cd, PrintMode.Symbolica) == "OpenCD({d0})"
    assert _format_lagrangian(open_cd, PrintMode.Latex) == r"\mathsf{D}^{open}\left({d0}\right)"
    assert _format_lagrangian(open_cd, PrintMode.Mathematica) == "OpenCD[{d0}]"
    assert _format_lagrangian(open_cd, PrintMode.Sympy) == "OpenCD({d0})"
    assert _format_lagrangian(open_cd, PrintMode.Typst) == "OpenCD({d0})"


def test_loop_hbar_symbol_prints_cleanly_in_all_symbolica_modes() -> None:
    assert _format_lagrangian(s.HBar, PrintMode.Symbolica) == "hbar"
    assert _format_lagrangian(s.HBar, PrintMode.Latex) == r"\hbar"
    assert _format_lagrangian(s.HBar, PrintMode.Mathematica) == r"\[HBar]"
    assert _format_lagrangian(s.HBar, PrintMode.Sympy) == "hbar"
    assert _format_lagrangian(s.HBar, PrintMode.Typst) == "hbar"


def test_loop_function_prints_cleanly_in_all_symbolica_modes() -> None:
    loop_function = vacuum_integrals.loop_function((Expression.symbol("M1"), Expression.symbol("M2")), (1, 2, -1))

    assert _format_lagrangian(loop_function, PrintMode.Symbolica) == "LF({M1, M2}, {1, 2, -1})"
    assert _format_lagrangian(loop_function, PrintMode.Latex) == (
        r"\mathrm{LF}_{{1, 2, -1}}\left({M1, M2}\right)"
    )
    assert _format_lagrangian(loop_function, PrintMode.Mathematica) == "LF[{M1, M2}, {1, 2, -1}]"
    assert _format_lagrangian(loop_function, PrintMode.Sympy) == "LF({M1, M2}, {1, 2, -1})"
    assert _format_lagrangian(loop_function, PrintMode.Typst) == 'LF({"M1", "M2"}, {1, 2, -1})'


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
        s.dummy_index(0),
        s.FieldStrength(phi.label, s.List(mu, nu), s.List(), s.List()),
        s.Bar(phi()),
        s.CD(mu, phi()),
        s.CovariantDerivativeCommutator(mu, nu, phi()),
        s.Delta(mu, nu),
        s.Metric(mu, nu),
        s.FlavorSum(mu, phi()),
        s.NCM(s.Bar(phi()), s.Gamma(mu), phi()),
        s.DiracProduct(s.Bar(phi()), phi()),
        s.Gamma(mu),
        s.Sigma(mu, nu),
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
        s.CovariantCommutatorLeftWildcard,
        s.CovariantCommutatorRightWildcard,
        s.CovariantCommutatorBodyWildcard,
        s.CouplingLabelWildcard,
        s.CouplingIndicesWildcard,
        s.CouplingOrderWildcard,
        s.CGTensorLabelWildcard,
        s.CGTensorIndicesWildcard,
        s.FieldStrengthLabelWildcard,
        s.FieldStrengthLorentzWildcard,
        s.FieldStrengthIndicesWildcard,
        s.FieldStrengthDerivativesWildcard,
        vacuum_integrals.loop_function((Expression.symbol("M1"), Expression.symbol("M2")), (1, 1, 0)),
        s.LoopFunctionMassesWildcard,
        s.LoopFunctionPowersWildcard,
        s.EFTExpansionParameter,
        s.CDVariationParameter,
        s.FunctionalVariationParameter,
        s.HBar,
        s.CovariantDerivativeProtectedCommutator(0),
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

        from pychete import canonical_string, collect_indices, load_state

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
        latex = lagrangian.format(mode=PrintMode.Latex, **format_options)
        assert symbolica == "-1/2*phi^2*m^2-1/24*phi^4*lambda+1/2*D[d0](phi)^2"
        assert latex == r"-\\frac{1}{2} \\phi^{2} m^{2}-\\frac{1}{24} \\phi^{4} \\lambda+\\frac{1}{2} D_{d0}\\left(\\phi\\right)^{2}"
        assert "Field(" not in symbolica
        assert "Coupling(" not in symbolica
        """
    )
    subprocess.run([sys.executable, "-c", load_script, str(path)], check=True, env=env)


def test_pychete_objects_expose_jupyter_repr_hooks() -> None:
    theory, lagrangian = _heavy_scalar_theory()
    phi = theory.field_handle("S")
    lam = theory.coupling_handle("g")
    index_info = collect_indices(theory.lorentz_index("mu"))[0]
    solution = HeavyScalarSolution(field=phi.definition, orders={1: phi()})
    matching_result = MatchingResult(
        theory=theory,
        uv_lagrangian=lagrangian,
        off_shell_eft_lagrangian=lagrangian,
        on_shell_eft_lagrangian=lagrangian,
    )
    fluctuation_basis = theory.fluctuation_basis(lagrangian)
    fluctuation_mode = fluctuation_basis.mode_for(phi)
    fluctuation_operator = theory.fluctuation_operator(lagrangian, [phi])
    fluctuation_block = fluctuation_operator.block("all", "all")
    supertrace_plan = fluctuation_operator.supertrace_plan()
    supertrace_block_trace = supertrace_plan.block_trace("all", fluctuation_block)
    one_loop_setup = theory.one_loop_setup(lagrangian)
    propagator_plan = one_loop_setup.propagator_plan(include_light=True)
    power_type_contribution = one_loop_setup.power_type_contributions()[0]
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
        fluctuation_basis,
        fluctuation_mode,
        fluctuation_operator,
        fluctuation_block,
        supertrace_plan,
        supertrace_block_trace,
        one_loop_setup,
        propagator_plan,
        *propagator_plan.propagators,
        power_type_contribution,
        matching_result,
    )

    for obj in objects:
        assert obj._repr_latex_()
        assert obj._repr_html_()
