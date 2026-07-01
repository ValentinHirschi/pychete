from __future__ import annotations

from pathlib import Path

from symbolica import Expression

from pychete import (
    FieldDofClass,
    act_with_open_cds,
    bar_expr,
    bosonic_log_expansion,
    bosonic_propagator_expansion,
    canonical_string,
    close_fermion_loop,
    covariant_loop,
    evaluate_functional_trace,
    evaluate_loop_functions,
    fluctuation_operator_sum,
    functional_trace_template,
    fermionic_propagator_expansion,
    instantiate_functional_trace_template,
    loop_integrate_tadpoles,
    matching_context,
    normalize_hybrid_spinor_wrappers,
    s,
)
from pychete.functional import open_cd_expr
from pychete.expr import derivative_indices_expr, internal_indices_expr, list_expr, lorentz_indices_expr
from pychete.loaders import load_python_model
from pychete.spinor import ncm_expr

from tests.conftest import assert_expr_equal


def _vlf():
    return load_python_model(Path("assets/models/VLF_toy_model.py"))


def _expected_vlf_offshell_dim6(theory) -> Expression:
    phi = theory.field_handle("phi")
    psi = theory.field_handle("psi")
    vector = theory.field_handle("A")
    y = theory.coupling_handle("y")()
    ybar = bar_expr(y)
    mass = theory.coupling_handle("M")()
    light_mass = theory.coupling_handle("m")()
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    rho = theory.dummy_index(2)
    h = s.hbar
    eps = s.DimRegEpsilon
    log = Expression.log(s.MuBar2 / mass**2)
    yy = ybar * y
    yyyy = ybar**2 * y**2

    def fs(left: Expression, right: Expression, *derivatives: Expression) -> Expression:
        return s.FieldStrength(
            vector.label,
            lorentz_indices_expr(left, right),
            internal_indices_expr(),
            derivative_indices_expr(*derivatives),
        )

    light_lagrangian = theory.free_lag("A", "psi", "phi")
    current = ncm_expr(s.Bar(psi()), s.Gamma(mu), s.PL, psi(derivatives=[mu]))
    current_without_derivative = ncm_expr(s.Bar(psi()), s.Gamma(mu), s.PL, psi())
    current_with_phi2 = phi() ** 2 * (
        ncm_expr(s.Bar(psi()), s.Gamma(mu), s.PL, psi(derivatives=[mu]))
        - ncm_expr(s.Bar(psi(derivatives=[mu])), s.Gamma(mu), s.PL, psi())
    )
    tree_operator = Expression.I * yy * current_with_phi2 / (2 * mass**2)
    fs_gamma = (
        -fs(mu, nu) * ncm_expr(s.Bar(psi()), s.Gamma(mu, nu), s.Gamma(rho), s.PL, psi(derivatives=[rho]))
        + fs(mu, nu) * ncm_expr(s.Bar(psi(derivatives=[rho])), s.Gamma(rho), s.Gamma(mu, nu), s.PL, psi())
    )
    higher_derivative = (
        ncm_expr(s.Bar(psi(derivatives=[mu])), s.Gamma(mu), s.PL, psi(derivatives=[nu, nu]))
        - ncm_expr(s.Bar(psi(derivatives=[mu, mu])), s.Gamma(nu), s.PL, psi(derivatives=[nu]))
    )
    box_phi_mu = phi(derivatives=[mu, mu])
    box_phi_nu = phi(derivatives=[nu, nu])

    loop_terms = (
        h * ybar**3 * y**3 * phi() ** 6 / (3 * mass**2)
        + 13 * h * yyyy * phi() ** 3 * box_phi_mu / (18 * mass**2)
        + h * yy * box_phi_mu * box_phi_nu / (3 * mass**2)
        + h * yy * phi() ** 2 * fs(mu, nu) ** 2 / (3 * mass**2)
        - 2 * h * fs(mu, nu, nu) * fs(mu, rho, rho) / (15 * mass**2)
        + h * fs(mu, nu) ** 2 * (-Expression.num(1) / (3 * eps) - log / 3)
        + h * phi() ** 4 * (-yyyy / eps - yyyy * log)
        + h * phi(derivatives=[mu]) ** 2 * (yy / 2 + yy / eps + yy * log)
        + h * phi() ** 2 * (-2 * yy * mass**2 / eps + mass**2 * (-2 * yy - 2 * yy * log))
        + 7 * h * yy * fs(mu, nu, nu) * current_without_derivative / (36 * mass**2)
        + h
        * (
            3 * Expression.I * yy / 4
            + Expression.I * yy / (2 * eps)
            + Expression.I * yy * light_mass**2 / (eps * mass**2)
            + Expression.I * yy * log / 2
            + (3 * Expression.I * yy * light_mass**2 / 2 + Expression.I * yy * light_mass**2 * log) / mass**2
        )
        * current
        + h * (-Expression.I * yyyy / (eps * mass**2) + (-5 * Expression.I * yyyy / 4 - Expression.I * yyyy * log) / mass**2) * current_with_phi2
        + h * yy * fs_gamma / (8 * mass**2)
        + Expression.I * h * yy * higher_derivative / (6 * mass**2)
    )
    return light_lagrangian + tree_operator + loop_terms


def test_vlf_matching_context_matches_matchete_inventory() -> None:
    theory, expressions = _vlf()
    ctx = matching_context(theory, expressions["lagrangian"], eft_order=6)

    assert [dof.name for dof in ctx.dofs_by_class(FieldDofClass.H_FERMION)] == ["Psi", "Conj[Psi]"]
    assert [dof.name for dof in ctx.dofs_by_class(FieldDofClass.L_FERMION)] == ["psi", "Conj[psi]"]
    assert [dof.name for dof in ctx.dofs_by_class(FieldDofClass.L_SCALAR)] == ["phi"]
    assert [dof.name for dof in ctx.dofs_by_class(FieldDofClass.L_VECTOR)] == ["A"]
    assert ctx.masses == (("Psi", theory.coupling_handle("M")()), ("Conj[Psi]", theory.coupling_handle("M")()))
    assert ctx.gauge_couplings == (("A", theory.coupling_handle("e")() ** 2),)
    assert [trace.name for trace in ctx.power_traces] == [
        "hFermion-lScalar",
        "hFermion-lFermion",
        "hFermion-lVector",
        "hFermion-lScalar-lScalar",
        "hFermion-lScalar-lFermion",
        "hFermion-lFermion-lScalar",
        "hFermion-lFermion-lVector",
        "hFermion-lVector-lFermion",
        "hFermion-lScalar-hFermion-lScalar",
        "hFermion-lScalar-hFermion-lFermion",
        "hFermion-lFermion-hFermion-lFermion",
        "hFermion-lFermion-lVector-lFermion",
        "hFermion-lFermion-hFermion-lFermion-hFermion-lFermion",
    ]


def test_vlf_functional_trace_template_exposes_prop_xterm_skeleton() -> None:
    theory, expressions = _vlf()
    ctx = matching_context(theory, expressions["lagrangian"], eft_order=6)
    mass = theory.coupling_handle("M")()

    template = functional_trace_template(ctx, "hFermion-lScalar")
    expected = s.PowerTypeSTr(
        list_expr(s.hFermion, s.lScalar),
        s.FuncNCM(
            s.Prop(mass),
            s.XTerm(s.hFermion, s.lScalar),
            s.Prop(Expression.num(0)),
            s.XTerm(s.lScalar, s.hFermion),
        ),
    )

    assert canonical_string(template) == canonical_string(expected)


def test_vlf_trace_template_instantiation_substitutes_context_xterms() -> None:
    theory, expressions = _vlf()
    ctx = matching_context(theory, expressions["lagrangian"], eft_order=6)
    phi = theory.field_handle("phi")
    y = theory.coupling_handle("y")()

    insertion = fluctuation_operator_sum(ctx, FieldDofClass.H_FERMION, FieldDofClass.L_SCALAR)
    instantiated = instantiate_functional_trace_template(ctx, "hFermion-lScalar")

    assert_expr_equal(
        insertion,
        ctx.fluctuation_operator("Psi", "phi").expression
        + ctx.fluctuation_operator("Conj[Psi]", "phi").expression,
    )
    assert "pychete::XTerm" not in canonical_string(instantiated)
    assert canonical_string(bar_expr(y)) in canonical_string(instantiated)
    assert canonical_string(theory.field_handle("psi")()) in canonical_string(instantiated)

    fermion_instantiated = instantiate_functional_trace_template(ctx, "hFermion-lFermion")
    assert canonical_string(phi()) in canonical_string(fermion_instantiated)


def test_vlf_functional_trace_evaluation_carries_template_and_expression() -> None:
    theory, expressions = _vlf()
    ctx = matching_context(theory, expressions["lagrangian"], eft_order=6)

    evaluation = evaluate_functional_trace(ctx, "hFermion-lScalar")

    assert evaluation.trace.name == "hFermion-lScalar"
    assert canonical_string(evaluation.template) == canonical_string(functional_trace_template(ctx, "hFermion-lScalar"))
    assert canonical_string(evaluation.instantiated_template) == canonical_string(instantiate_functional_trace_template(ctx, "hFermion-lScalar"))
    assert_expr_equal(evaluation.expression, covariant_loop(theory, expressions["lagrangian"], eft_order=6, trace="hFermion-lScalar"))
    assert "pychete::LF(" not in canonical_string(evaluation.evaluated())


def test_vlf_matching_context_contains_xterm_samples() -> None:
    theory, expressions = _vlf()
    ctx = matching_context(theory, expressions["lagrangian"], eft_order=6)
    phi = theory.field_handle("phi")
    y = theory.coupling_handle("y")()
    m = theory.coupling_handle("m")()

    assert ctx.fluctuation_operator("phi", "phi").metadata.eft_order.numerator == 2
    assert_expr_equal(ctx.fluctuation_operator("phi", "phi").expression, m**2)
    assert_expr_equal(
        ctx.fluctuation_operator("Psi", "psi").expression,
        bar_expr(y) * s.FuncNCM(phi(), s.DiracProduct(s.PL)),
    )
    assert_expr_equal(
        ctx.fluctuation_operator("psi", "Psi").expression,
        y * s.FuncNCM(phi(), s.DiracProduct(s.PR)),
    )


def test_vlf_matching_context_retains_conjugate_and_vector_xterms() -> None:
    theory, expressions = _vlf()
    ctx = matching_context(theory, expressions["lagrangian"], eft_order=6)
    phi = theory.field_handle("phi")
    y = theory.coupling_handle("y")()

    assert_expr_equal(
        ctx.fluctuation_operator("Conj[Psi]", "psi").expression,
        bar_expr(y) * phi() * s.DiracProduct(s.PL),
    )
    assert ctx.fluctuation_operator("Psi", "A").metadata.eft_order.numerator == 5
    assert ctx.fluctuation_operator("Psi", "A").metadata.eft_order.denominator == 2
    assert ctx.fluctuation_operator("psi", "A").metadata.eft_order.numerator == 3
    assert ctx.fluctuation_operator("psi", "A").metadata.eft_order.denominator == 2


def test_vlf_one_loop_only_uses_matchete_default_single_mass_logs() -> None:
    theory, expressions = _vlf()
    loop = theory.match(expressions["lagrangian"], eft_order=6, loop_order=(1,))

    assert "field_Psi" not in canonical_string(loop)
    assert "pychete::LF(" not in canonical_string(loop)
    assert "LoopLog" not in canonical_string(loop)
    assert "log" in loop.format_plain()

    evaluated = evaluate_loop_functions(loop)

    assert_expr_equal(evaluated, loop)


def test_vlf_one_loop_phi_six_coefficient_matches_matchete_trace() -> None:
    theory, expressions = _vlf()
    loop = covariant_loop(theory, expressions["lagrangian"], eft_order=6)
    phi = theory.field_handle("phi")
    y = theory.coupling_handle("y")()
    mass = theory.coupling_handle("M")()

    coeff = loop.coefficient(phi() ** 6)

    assert_expr_equal(coeff, s.hbar * bar_expr(y) ** 3 * y**3 / (3 * mass**2))


def test_loop_integrate_tadpoles_produces_internal_lffull() -> None:
    theory, _ = _vlf()
    mass = theory.coupling_handle("M")()

    integrated = loop_integrate_tadpoles(3 * s.Prop(mass) ** 2)

    assert_expr_equal(integrated, 3 * Expression.I * s.LFFull(list_expr(mass), list_expr(Expression.num(2), Expression.num(0))))


def test_hard_region_expansion_templates_match_low_order_formulas() -> None:
    theory, _ = _vlf()
    mass = theory.coupling_handle("M")()
    mu = theory.lorentz_index("mu")
    delta = 2 * s.FuncNCM(s.LoopMom(mu), open_cd_expr(mu)) + s.FuncNCM(open_cd_expr(mu), open_cd_expr(mu))

    assert_expr_equal(
        bosonic_propagator_expansion(mass, max_order=1, momentum_index=mu),
        s.Prop(mass) - s.Prop(mass) ** 2 * delta,
    )
    assert_expr_equal(
        bosonic_log_expansion(mass, max_order=2, momentum_index=mu),
        s.Prop(mass) * delta - s.Prop(mass) ** 2 * delta**2 / 2,
    )
    assert_expr_equal(
        fermionic_propagator_expansion(mass, max_order=0, momentum_index=mu),
        s.FuncNCM(
            s.DiracProduct(s.Gamma(mu)) * s.LoopMom(mu)
            + mass
            + Expression.I * s.FuncNCM(s.DiracProduct(s.Gamma(mu)), open_cd_expr(mu)),
            s.Prop(mass),
        ),
    )


def test_vlf_full_offshell_coefficients_match_matchete_result() -> None:
    theory, expressions = _vlf()
    matched = evaluate_loop_functions(theory.match(expressions["lagrangian"], eft_order=6, loop_order=1))
    phi = theory.field_handle("phi")
    vector = theory.field_handle("A")
    y = theory.coupling_handle("y")()
    ybar = bar_expr(y)
    e = theory.coupling_handle("e")()
    mass = theory.coupling_handle("M")()
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    log = Expression.log(s.MuBar2 / mass**2)
    fs = s.FieldStrength(vector.label, lorentz_indices_expr(mu, nu), internal_indices_expr(), derivative_indices_expr())

    assert_expr_equal(
        matched.coefficient(fs**2),
        -Expression.num(1) / (4 * e**2)
        + s.hbar * (-Expression.num(1) / (3 * s.DimRegEpsilon) - log / 3)
        + s.hbar * ybar * y * phi() ** 2 / (3 * mass**2),
    )
    assert_expr_equal(
        matched.coefficient(phi(derivatives=[mu]) ** 2),
        Expression.num(1) / 2 + s.hbar * (ybar * y / 2 + ybar * y / s.DimRegEpsilon + ybar * y * log),
    )


def test_vlf_full_offshell_dimension_six_expression_matches_matchete_result() -> None:
    theory, expressions = _vlf()

    matched = evaluate_loop_functions(theory.match(expressions["lagrangian"], eft_order=6, loop_order=1))
    expected = _expected_vlf_offshell_dim6(theory)

    assert_expr_equal(matched, expected)


def test_vlf_loop_order_one_is_tree_plus_loop_only() -> None:
    theory, expressions = _vlf()

    tree = theory.match(expressions["lagrangian"], eft_order=6, loop_order=0)
    loop = theory.match(expressions["lagrangian"], eft_order=6, loop_order=(1,))
    combined = theory.match(expressions["lagrangian"], eft_order=6, loop_order=1)

    assert_expr_equal(combined, tree + loop)


def test_vlf_power_trace_zero_and_current_trace_are_available() -> None:
    theory, expressions = _vlf()
    ctx = matching_context(theory, expressions["lagrangian"], eft_order=6)
    phi = theory.field_handle("phi")
    psi = theory.field_handle("psi")
    y = theory.coupling_handle("y")()
    mass = theory.coupling_handle("M")()
    mu = theory.dummy_index(0)

    assert_expr_equal(covariant_loop(theory, expressions["lagrangian"], eft_order=6, trace="hFermion-lScalar-hFermion-lScalar"), Expression.num(0))

    trace = covariant_loop(theory, expressions["lagrangian"], eft_order=6, trace="hFermion-lScalar-hFermion-lFermion")
    current = phi() ** 2 * (
        ncm_expr(s.Bar(psi()), s.Gamma(mu), s.PL, psi(derivatives=[mu]))
        - ncm_expr(s.Bar(psi(derivatives=[mu])), s.Gamma(mu), s.PL, psi())
    )

    assert ctx.power_traces
    assert_expr_equal(trace, -Expression.I * s.hbar * bar_expr(y) ** 2 * y**2 * current / (4 * mass**2))


def test_open_cds_act_on_fields_and_terminal_open_cds_vanish() -> None:
    theory, _ = _vlf()
    phi = theory.field_handle("phi")
    mu = theory.lorentz_index("mu")

    acted = act_with_open_cds(theory, s.FuncNCM(phi(), open_cd_expr(mu), phi()))
    terminal = act_with_open_cds(theory, s.FuncNCM(phi(), open_cd_expr(mu)))

    assert canonical_string(acted) == canonical_string(s.FuncNCM(phi(), phi(derivatives=[mu])))
    assert_expr_equal(terminal, Expression.num(0))


def test_open_cds_evaluate_u1_wilson_line_second_derivative() -> None:
    theory, _ = _vlf()
    psi = theory.fields["psi"]
    vector = theory.fields["A"]
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    acted = act_with_open_cds(theory, s.FuncNCM(open_cd_expr(mu), open_cd_expr(nu), s.WilsonLine(psi.label)))
    expected = -Expression.I * psi.charge_exprs[0] * s.FieldStrength(
        vector.label,
        lorentz_indices_expr(mu, nu),
        internal_indices_expr(),
        derivative_indices_expr(),
    ) / 2

    assert_expr_equal(acted, expected)


def test_close_fermion_loop_accepts_hybrid_spinor_wrappers() -> None:
    theory, _ = _vlf()
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    traced = close_fermion_loop(s.GammaCC(s.DiracProduct(s.Gamma(mu), s.Gamma(nu))))
    transposed = normalize_hybrid_spinor_wrappers(s.Transp(s.DiracProduct(s.Gamma(mu), s.Gamma(nu))))

    assert canonical_string(transposed) == canonical_string(s.DiracProduct(s.Gamma(nu), s.Gamma(mu)))
    assert_expr_equal(traced, 4 * s.Metric(mu, nu))
