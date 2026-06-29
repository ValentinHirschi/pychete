from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest
from symbolica import Expression, S

from pychete import (
    BosonicCDEExpansionPlan,
    BosonicCDEExpansionPlanEntry,
    BosonicCDETraceExpansionTerm,
    FieldChirality,
    FieldMassKind,
    FieldRole,
    FluctuationSector,
    FluctuationStatistics,
    FreeLagConvention,
    MatchingResult,
    OneLoopIntegralBackend,
    OneLoopMatchOptions,
    OneLoopNormalization,
    PowerTypeSupertraceContribution,
    SupertraceBlockTrace,
    SymbolRole,
    Theory,
    VakintIntegralStage,
    WilsonLineInternalEvaluationMode,
    WilsonLineTraceExpansionTerm,
    WilsonLineTracePath,
    WilsonLineExpansionPlan,
    WilsonLineExpansionPlanEntry,
    canonical_string,
    contract_wilson_term_derivative_metrics,
    dummy_indices,
    expand_wilson_terms,
    load_validation_fixture,
    one_loop_normalization_factor,
    remove_loop_momentum_symmetry_vanishing_wilson_terms,
    remove_symmetry_vanishing_wilson_terms,
    s,
)
import pychete.matching as matching_module
import pychete.matching_results as matching_results_module
from pychete.backends import idenso as idenso_backend
from pychete.backends import spenso as spenso_backend
from pychete.backends import vacuum_integrals as vacuum_integrals_backend
from pychete.backends import vakint as vakint_backend
from pychete.bases.smeft_warsaw import define_smeft_wilson_coefficient, smeft_warsaw_operator
from pychete.expr import field_pattern, terms as expression_terms
from pychete.matching import _lower_differential_operators_to_momentum

from tests.conftest import assert_expr_equal


class FakeKernelVakintEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Expression, bool | None]] = []

    def to_canonical(self, expr: Expression, short_form: bool | None = None) -> Expression:
        self.calls.append(("to_canonical", expr, short_form))
        return S("canonical")(expr)

    def tensor_reduce(self, expr: Expression) -> Expression:
        self.calls.append(("tensor_reduce", expr, None))
        return S("reduced")(expr)

    def evaluate(self, expr: Expression) -> Expression:
        self.calls.append(("evaluate", expr, None))
        return S("evaluated")(expr)


class FakeScalarLoopMomentumVakintEngine(FakeKernelVakintEngine):
    def tensor_reduce(self, expr: Expression) -> Expression:
        self.calls.append(("tensor_reduce", expr, None))
        return vakint_backend.loop_momentum(1, S("mu")) ** 2 * expr


class FakeTensorNetwork:
    def __init__(self, expr: Expression) -> None:
        self.expr = expr


class FakePoleVakintEngine:
    def __init__(self, evaluated: Expression) -> None:
        self.evaluated = evaluated
        self.calls: list[tuple[str, Expression]] = []

    def evaluate(self, expr: Expression) -> Expression:
        self.calls.append(("evaluate", expr))
        return self.evaluated


def test_fluctuation_operator_uses_symbolica_hessian_for_scalar_basis() -> None:
    theory = Theory("fluctuation_scalar")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True)
    g = theory.define_coupling("g", self_conjugate=True)
    mass = theory.mass_expr(heavy.definition)
    assert mass is not None
    lagrangian = -mass**2 * heavy() ** 2 / 2 - g() * heavy() * phi() ** 2 / 2

    operator = theory.fluctuation_operator(lagrangian, [heavy, phi])

    assert_expr_equal(operator.entry(heavy, heavy), -mass**2)
    assert_expr_equal(operator.entry(heavy, phi), -g() * phi())
    assert_expr_equal(operator.entry(phi, heavy), -g() * phi())
    assert_expr_equal(operator.entry(phi, phi), -g() * heavy())


def test_fluctuation_operator_exposes_euler_lagrange_differential_entries() -> None:
    theory = Theory("fluctuation_differential_scalar")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    mass = theory.mass_expr(heavy.definition)
    assert mass is not None
    mu = theory.dummy_index(0)
    lagrangian = theory.free_lag(heavy)

    operator = theory.fluctuation_operator(lagrangian)

    assert_expr_equal(operator.entry(heavy, heavy), -mass**2)
    assert_expr_equal(
        operator.differential_entry(heavy, heavy),
        -mass**2 - s.DifferentialOperator(s.List(mu, mu)),
    )
    expression_map = operator.to_expression_map()
    assert_expr_equal(
        expression_map[f"fluctuation_operator_differential[{canonical_string(heavy())},{canonical_string(heavy())}]"],
        operator.differential_entry(heavy, heavy),
    )
    assert_expr_equal(operator.momentum_entry(heavy, heavy), s.LoopMomentumSquared - mass**2)
    momentum_map = operator.momentum_expression_map()
    assert_expr_equal(
        momentum_map[f"fluctuation_operator_momentum[{canonical_string(heavy())},{canonical_string(heavy())}]"],
        operator.momentum_entry(heavy, heavy),
    )
    assert_expr_equal(
        operator.propagator_denominator_entry(heavy, heavy),
        s.PropagatorDenominator(s.LoopMomentumSquared, mass**2),
    )
    denominator_map = operator.propagator_denominator_expression_map()
    assert_expr_equal(
        denominator_map[f"fluctuation_operator_denominator[{canonical_string(heavy())},{canonical_string(heavy())}]"],
        operator.propagator_denominator_entry(heavy, heavy),
    )


def test_fluctuation_operator_differential_entries_handle_barred_complex_scalars() -> None:
    theory = Theory("fluctuation_differential_complex")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=False, mass=(FieldMassKind.LIGHT, "m"))
    mass = theory.mass_expr(phi.definition)
    assert mass is not None
    mu = theory.dummy_index(0)
    lagrangian = theory.free_lag(phi)
    barred_phi = s.Bar(phi())

    operator = theory.fluctuation_operator(lagrangian, [barred_phi, phi])
    expected = -mass**2 - s.DifferentialOperator(s.List(mu, mu))

    assert_expr_equal(operator.entry(barred_phi, phi), -mass**2)
    assert_expr_equal(operator.entry(phi, barred_phi), -mass**2)
    assert_expr_equal(operator.differential_entry(barred_phi, phi), expected)
    assert_expr_equal(operator.differential_entry(phi, barred_phi), expected)
    assert_expr_equal(operator.momentum_entry(barred_phi, phi), s.LoopMomentumSquared - mass**2)
    assert_expr_equal(operator.momentum_entry(phi, barred_phi), s.LoopMomentumSquared - mass**2)
    assert_expr_equal(
        operator.propagator_denominator_entry(barred_phi, phi),
        s.PropagatorDenominator(s.LoopMomentumSquared, mass**2),
    )
    assert_expr_equal(
        operator.propagator_denominator_entry(phi, barred_phi),
        s.PropagatorDenominator(s.LoopMomentumSquared, mass**2),
    )
    assert_expr_equal(
        operator.propagator_denominator_for_mode(barred_phi),
        s.PropagatorDenominator(s.LoopMomentumSquared, mass**2),
    )
    assert_expr_equal(
        operator.propagator_denominator_for_mode(phi),
        s.PropagatorDenominator(s.LoopMomentumSquared, mass**2),
    )


def test_charged_scalar_free_lag_generates_gauge_interactions() -> None:
    theory = Theory("fluctuation_charged_scalar_free")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        self_conjugate=False,
        mass=(FieldMassKind.LIGHT, "m"),
    )
    vector = theory.field_handle("B")
    coupling = theory.coupling_handle("gY")
    lagrangian = theory.free_lag(phi, vector)

    operator = theory.fluctuation_operator(lagrangian, [s.Bar(phi()), phi(), vector()])
    denominator = s.PropagatorDenominator(s.LoopMomentumSquared, Expression.num(0))

    assert_expr_equal(operator.free_inverse_entry(vector, vector), s.LoopMomentumSquared)
    assert_expr_equal(operator.propagator_denominator_for_mode(vector()), denominator)
    assert_expr_equal(operator.interaction_entry(vector, vector), 2 * coupling() ** 2 * phi() * s.Bar(phi()))


def test_matchete_implicit_abelian_scalar_kinetic_generates_scalar_vector_xterms() -> None:
    theory = Theory("fluctuation_matchete_implicit_scalar_vector")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        self_conjugate=False,
        mass=(FieldMassKind.LIGHT, "m"),
    )
    vector = theory.field_handle("B")
    coupling = theory.coupling_handle("gY")
    mu = theory.dummy_index(0)
    lagrangian = theory.free_lag(phi, vector, convention=FreeLagConvention.MATCHETE)

    operator = theory.fluctuation_operator(lagrangian, [s.Bar(phi()), phi(), vector()])

    assert_expr_equal(
        operator.differential_entry(s.Bar(phi()), vector()),
        Expression.I * phi() * coupling() * s.DifferentialOperator(s.List(mu))
        - 2 * Expression.I * phi(derivatives=[mu]) * coupling()
        - Expression.I * coupling() * s.NCM(phi(), s.OpenCD(s.List(mu))),
    )
    assert_expr_equal(
        operator.differential_entry(vector(), phi()),
        Expression.I * coupling() * s.Bar(phi()) * s.DifferentialOperator(s.List(mu))
        + Expression.I * coupling() * s.Bar(phi(derivatives=[mu]))
        - Expression.I * coupling() * s.NCM(s.Bar(phi()), s.OpenCD(s.List(mu))),
    )
    assert_expr_equal(
        operator.differential_entry(phi(), vector()),
        -Expression.I * coupling() * s.Bar(phi()) * s.DifferentialOperator(s.List(mu))
        + 2 * Expression.I * coupling() * s.Bar(phi(derivatives=[mu]))
        + Expression.I * coupling() * s.NCM(s.Bar(phi()), s.OpenCD(s.List(mu))),
    )
    assert_expr_equal(
        operator.differential_entry(vector(), s.Bar(phi())),
        -Expression.I * phi() * coupling() * s.DifferentialOperator(s.List(mu))
        - Expression.I * phi(derivatives=[mu]) * coupling()
        + Expression.I * coupling() * s.NCM(phi(), s.OpenCD(s.List(mu))),
    )
    assert_expr_equal(
        operator.differential_entry(s.Bar(phi()), vector()).coefficient(vector()).expand(),
        Expression.num(0),
    )


def test_one_loop_match_option_expands_abelian_covariant_derivatives_before_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("match_expand_abelian_covariant_derivatives")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        self_conjugate=False,
        mass=0,
    )
    vector = theory.field_handle("B")
    coupling = theory.coupling_handle("gY")
    captured: dict[str, Expression] = {}

    class FakeSetup:
        def interaction_power_type_internal_matching_result(self, **_kwargs: object) -> MatchingResult:
            return MatchingResult(
                theory=theory,
                uv_lagrangian=captured["lagrangian"],
                off_shell_eft_lagrangian=captured["lagrangian"],
                on_shell_eft_lagrangian=captured["lagrangian"],
                metadata={"stage": "fake_internal"},
            )

    def fake_one_loop_setup(
        _theory: Theory,
        lagrangian: Expression,
        **_kwargs: object,
    ) -> FakeSetup:
        captured["lagrangian"] = lagrangian
        return FakeSetup()

    monkeypatch.setattr(matching_module, "one_loop_setup", fake_one_loop_setup)

    lagrangian = theory.free_lag(phi, vector, convention=FreeLagConvention.MATCHETE)
    result = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            expand_abelian_covariant_derivatives=True,
            truncate_eft_result=False,
        ),
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["abelian_covariant_derivatives_expanded"] is True
    assert_expr_equal(
        captured["lagrangian"].coefficient(coupling() ** 2 * vector() ** 2 * phi() * s.Bar(phi())).expand(),
        Expression.num(1),
    )


def test_one_loop_match_option_expands_non_abelian_covariant_derivatives_before_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("match_expand_nonabelian_covariant_derivatives")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], mass=0)
    mu = theory.dummy_index(0)
    index = theory.index("i", fund)
    captured: dict[str, Expression] = {}

    class FakeSetup:
        def interaction_power_type_internal_matching_result(self, **_kwargs: object) -> MatchingResult:
            return MatchingResult(
                theory=theory,
                uv_lagrangian=captured["lagrangian"],
                off_shell_eft_lagrangian=captured["lagrangian"],
                on_shell_eft_lagrangian=captured["lagrangian"],
                metadata={"stage": "fake_internal"},
            )

    def fake_one_loop_setup(
        _theory: Theory,
        lagrangian: Expression,
        **_kwargs: object,
    ) -> FakeSetup:
        captured["lagrangian"] = lagrangian
        return FakeSetup()

    monkeypatch.setattr(matching_module, "one_loop_setup", fake_one_loop_setup)

    derived = higgs(index, derivatives=[mu])
    result = theory.match(
        s.Bar(derived) * derived,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            expand_non_abelian_covariant_derivatives=True,
            truncate_eft_result=False,
        ),
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["non_abelian_covariant_derivatives_expanded"] is True
    expanded = canonical_string(captured["lagrangian"])
    assert "cg_tensor_gen_SU2L_fund" in expanded
    assert "index_covariant_derivative" in expanded


def test_one_loop_match_option_expands_covariant_derivative_commutators_before_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("match_expand_covariant_commutators")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        mass=0,
    )
    mu = theory.index("mu")
    nu = theory.index("nu")
    captured: dict[str, Expression] = {}

    class FakeSetup:
        def interaction_power_type_internal_matching_result(self, **_kwargs: object) -> MatchingResult:
            return MatchingResult(
                theory=theory,
                uv_lagrangian=captured["lagrangian"],
                off_shell_eft_lagrangian=captured["lagrangian"],
                on_shell_eft_lagrangian=captured["lagrangian"],
                metadata={"stage": "fake_internal"},
            )

    def fake_one_loop_setup(
        _theory: Theory,
        lagrangian: Expression,
        **_kwargs: object,
    ) -> FakeSetup:
        captured["lagrangian"] = lagrangian
        return FakeSetup()

    monkeypatch.setattr(matching_module, "one_loop_setup", fake_one_loop_setup)

    formal = s.CovariantDerivativeCommutator(mu, nu, phi())
    result = theory.match(
        formal,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            expand_covariant_derivative_commutators=True,
            truncate_eft_result=False,
        ),
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["covariant_derivative_commutators_expanded"] is True
    assert_expr_equal(captured["lagrangian"], theory.covariant_derivative_commutator(phi(), mu, nu))
    assert_expr_equal(
        theory.expand_covariant_derivative_commutators(
            s.CovariantDerivativeCommutator(mu, nu, s.Bar(phi()))
        ),
        theory.covariant_derivative_commutator(s.Bar(phi()), mu, nu),
    )
    assert "pychete::FieldStrength" in canonical_string(
        theory.covariant_derivative_commutator(s.Bar(phi()), mu, nu)
    )


def test_one_loop_match_option_emits_and_expands_covariant_derivative_commutators_before_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("match_emit_covariant_commutators")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        mass=0,
    )
    b = theory.index("b")
    c = theory.index("c")
    captured: dict[str, Expression] = {}

    class FakeSetup:
        def interaction_power_type_internal_matching_result(self, **_kwargs: object) -> MatchingResult:
            return MatchingResult(
                theory=theory,
                uv_lagrangian=captured["lagrangian"],
                off_shell_eft_lagrangian=captured["lagrangian"],
                on_shell_eft_lagrangian=captured["lagrangian"],
                metadata={"stage": "fake_internal"},
            )

    def fake_one_loop_setup(
        _theory: Theory,
        lagrangian: Expression,
        **_kwargs: object,
    ) -> FakeSetup:
        captured["lagrangian"] = lagrangian
        return FakeSetup()

    monkeypatch.setattr(matching_module, "one_loop_setup", fake_one_loop_setup)

    result = theory.match(
        phi(derivatives=[c, b]),
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            emit_covariant_derivative_commutators=True,
            expand_covariant_derivative_commutators=True,
            truncate_eft_result=False,
        ),
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["covariant_derivative_commutators_emitted"] is True
    assert result.metadata["covariant_derivative_commutator_emit_passes"] == 1
    assert result.metadata["covariant_derivative_commutators_expanded"] is True
    assert_expr_equal(
        captured["lagrangian"],
        phi(derivatives=[b, c]) + theory.covariant_derivative_commutator(phi(), c, b),
    )


def test_charged_fermion_free_lag_subtracts_only_registered_free_inverse() -> None:
    theory = Theory("fluctuation_charged_fermion_free")
    theory.define_gauge_group("U1e", s.U1, "e", "A")
    psi = theory.define_field(
        "psi",
        s.Fermion,
        charges=[theory.group_charge("U1e", 1)],
        mass=(FieldMassKind.HEAVY, "M"),
    )
    vector = theory.field_handle("A")
    coupling = theory.coupling_handle("e")
    mass = theory.mass_expr(psi.definition)
    assert mass is not None
    mu = theory.dummy_index(0)
    lagrangian = theory.free_lag(psi, vector)
    barred_psi = s.Bar(psi())

    operator = theory.fluctuation_operator(lagrangian, [barred_psi, psi(), vector()])
    denominator = s.PropagatorDenominator(s.LoopMomentumSquared, mass**2)
    current = coupling() * vector() * s.Gamma(mu)

    assert_expr_equal(operator.propagator_denominator_entry(barred_psi, psi()), denominator)
    assert_expr_equal(operator.propagator_denominator_entry(psi(), barred_psi), denominator)
    assert_expr_equal(operator.propagator_denominator_for_mode(psi()), denominator)
    assert_expr_equal(operator.free_inverse_entry(barred_psi, psi()), -mass - s.Gamma(mu) * s.LoopMomentum(mu))
    assert_expr_equal(operator.free_inverse_entry(psi(), barred_psi), -mass + s.Gamma(mu) * s.LoopMomentum(mu))
    assert_expr_equal(operator.interaction_entry(barred_psi, psi()), current)
    assert_expr_equal(operator.interaction_entry(psi(), barred_psi), current)


def test_fluctuation_operator_denominator_extraction_rejects_interaction_masses() -> None:
    theory = Theory("fluctuation_denominator_interaction")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = theory.free_lag(phi) - y() * heavy() * phi() ** 2 / 2

    operator = theory.fluctuation_operator(lagrangian)

    assert_expr_equal(operator.momentum_entry(phi, phi), s.LoopMomentumSquared - y() * heavy())
    assert operator.propagator_denominator_entry(phi, phi) is None
    assert_expr_equal(
        operator.propagator_denominator_for_mode(phi),
        s.PropagatorDenominator(s.LoopMomentumSquared, Expression.num(0)),
    )
    assert_expr_equal(
        operator.propagator_denominator_entry(phi, phi, require_registered_mass=False),
        s.PropagatorDenominator(s.LoopMomentumSquared, y() * heavy()),
    )


def test_fluctuation_operator_protects_unselected_barred_fields() -> None:
    theory = Theory("fluctuation_bar_protection")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=False, mass=(FieldMassKind.LIGHT, "m"))
    mass = theory.mass_expr(phi.definition)
    assert mass is not None
    lagrangian = -mass**2 * s.Bar(phi()) * phi()

    operator = theory.fluctuation_operator(lagrangian, [phi])

    assert_expr_equal(operator.entry(phi, phi), Expression.num(0))


def test_fluctuation_operator_can_include_barred_field_basis_entries() -> None:
    theory = Theory("fluctuation_bar_basis")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=False, mass=(FieldMassKind.LIGHT, "m"))
    mass = theory.mass_expr(phi.definition)
    assert mass is not None
    barred_phi = s.Bar(phi())
    lagrangian = -mass**2 * barred_phi * phi()

    operator = theory.fluctuation_operator(lagrangian, [barred_phi, phi])

    assert_expr_equal(operator.entry(barred_phi, phi), -mass**2)
    assert_expr_equal(operator.entry(phi, barred_phi), -mass**2)
    assert operator.to_expression_map()


def test_fluctuation_operator_linearizes_noncommutative_fermion_chains_without_formal_derivatives() -> None:
    theory = Theory("fluctuation_ncm_fermions")
    heavy = theory.define_field("Psi", s.Fermion, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("psi", s.Fermion, mass=0)
    scalar = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y")
    mass = theory.mass_expr(heavy.definition)
    assert mass is not None
    mu = theory.dummy_index(0)
    interaction = -y() * scalar() * s.NCM(s.Bar(light()), s.PR, heavy())
    lagrangian = theory.free_lag(heavy, light, scalar) + interaction + s.Bar(interaction)
    basis = (s.Bar(heavy()), heavy(), s.Bar(light()), light(), scalar())

    operator = theory.fluctuation_operator(lagrangian, basis)

    for row in basis:
        for column in basis:
            for entry in (
                operator.entry(row, column),
                operator.differential_entry(row, column),
                operator.momentum_entry(row, column),
                operator.interaction_entry(row, column),
            ):
                assert "der(" not in canonical_string(entry)
    assert_expr_equal(operator.entry(heavy, s.Bar(light())), -y() * scalar() * s.PR)
    assert_expr_equal(operator.entry(s.Bar(heavy()), light), -s.Bar(y()) * scalar() * s.PL)
    assert_expr_equal(operator.entry(heavy, scalar), -y() * s.NCM(s.Bar(light()), s.PR))
    assert_expr_equal(operator.entry(scalar, s.Bar(heavy())), -s.Bar(y()) * s.NCM(s.PL, light()))
    assert_expr_equal(
        operator.differential_entry(heavy, s.Bar(heavy())),
        -mass - Expression.I * s.Gamma(mu) * s.DifferentialOperator(s.List(mu)),
    )
    assert_expr_equal(
        operator.momentum_entry(heavy, s.Bar(heavy())),
        s.Gamma(mu) * s.LoopMomentum(mu) - mass,
    )
    heavy_denominator = s.PropagatorDenominator(s.LoopMomentumSquared, mass**2)
    light_denominator = s.PropagatorDenominator(s.LoopMomentumSquared, Expression.num(0))
    assert_expr_equal(operator.propagator_denominator_entry(heavy, s.Bar(heavy())), heavy_denominator)
    assert_expr_equal(operator.propagator_denominator_entry(s.Bar(heavy()), heavy()), heavy_denominator)
    assert_expr_equal(operator.propagator_denominator_for_mode(heavy()), heavy_denominator)
    assert_expr_equal(operator.propagator_denominator_entry(light, s.Bar(light())), light_denominator)
    assert_expr_equal(operator.propagator_denominator_for_mode(light()), light_denominator)
    assert_expr_equal(
        operator.free_inverse_entry(heavy, s.Bar(heavy())),
        operator.momentum_entry(heavy, s.Bar(heavy())),
    )
    assert_expr_equal(operator.interaction_entry(heavy, s.Bar(heavy())), Expression.num(0))
    assert_expr_equal(operator.interaction_entry(s.Bar(heavy()), heavy()), Expression.num(0))


def test_open_differential_operators_lower_to_loop_momentum_numerators() -> None:
    theory = Theory("open_derivative_lowering")
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    operator = s.DifferentialOperator(s.List(mu, nu))

    lowered = _lower_differential_operators_to_momentum(operator)

    assert_expr_equal(lowered, -s.LoopMomentum(mu) * s.LoopMomentum(nu))


def test_fluctuation_operator_differential_entries_keep_indexed_yukawa_modes() -> None:
    theory = Theory("fluctuation_indexed_yukawa_modes")
    flavor = theory.define_index_type("Flavor", dimension=2)
    i = theory.dummy_index(0, flavor.symbol)
    heavy = theory.define_field("Psi", s.Fermion, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("psi", s.Fermion, indices=[flavor.symbol], mass=0)
    scalar = theory.define_field("phi", s.Scalar, indices=[flavor.symbol], self_conjugate=False, mass=0)
    y = theory.define_coupling("y", indices=[flavor.symbol])
    heavy_field = heavy()
    light_i = light(i)
    scalar_i = scalar(i)
    interaction = -y(i) * scalar_i * s.NCM(s.Bar(light_i), s.PR, heavy_field)
    lagrangian = interaction + s.Bar(interaction)
    basis = (s.Bar(heavy_field), heavy_field, s.Bar(light_i), light_i, s.Bar(scalar_i), scalar_i)

    operator = theory.fluctuation_operator(lagrangian, basis)
    light_to_heavy = -y(i) * scalar_i * s.PR
    conjugate_light_to_heavy = -s.Bar(y(i)) * s.Bar(scalar_i) * s.PL

    assert_expr_equal(operator.entry(s.Bar(light_i), heavy_field), light_to_heavy)
    assert_expr_equal(operator.differential_entry(s.Bar(light_i), heavy_field), light_to_heavy)
    assert_expr_equal(operator.interaction_entry(s.Bar(light_i), heavy_field), light_to_heavy)
    assert_expr_equal(operator.entry(light_i, s.Bar(heavy_field)), conjugate_light_to_heavy)
    assert_expr_equal(operator.differential_entry(light_i, s.Bar(heavy_field)), conjugate_light_to_heavy)
    assert_expr_equal(operator.interaction_entry(light_i, s.Bar(heavy_field)), conjugate_light_to_heavy)


def test_fluctuation_operator_rejects_duplicate_basis_entries() -> None:
    theory = Theory("fluctuation_duplicate_basis")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True)

    with pytest.raises(ValueError, match="unique"):
        theory.fluctuation_operator(phi() ** 2, [phi, phi])


def test_fluctuation_basis_discovers_fields_with_symbolica_tagged_patterns() -> None:
    theory = Theory("fluctuation_basis_discovery")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    complex_light = theory.define_field("chi", s.Scalar, self_conjugate=False, mass=(FieldMassKind.LIGHT, "m"))
    mu = theory.dummy_index(0)
    unregistered_field = s.Field(S("untagged"), s.Scalar, s.List(), s.List())
    lagrangian = (
        heavy(derivatives=[mu]) ** 2
        + light() ** 2
        + s.Bar(complex_light()) * complex_light()
        + unregistered_field**2
    )

    basis = theory.fluctuation_basis(lagrangian)

    assert tuple(basis) == basis.entries
    heavy_names = {canonical_string(field) for field in basis.heavy}
    light_names = {canonical_string(field) for field in basis.light}
    entry_names = {canonical_string(field) for field in basis.entries}
    assert canonical_string(heavy()) in heavy_names
    assert canonical_string(light()) in light_names
    assert canonical_string(s.Bar(complex_light())) in light_names
    assert canonical_string(complex_light()) in light_names
    assert canonical_string(unregistered_field) not in entry_names


def test_fluctuation_operator_uses_discovered_basis_when_omitted() -> None:
    theory = Theory("fluctuation_auto_basis")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    g = theory.define_coupling("g", self_conjugate=True)
    lagrangian = -g() * heavy() * light() ** 2 / 2

    operator = theory.fluctuation_operator(lagrangian)

    assert {canonical_string(field) for field in operator.basis} == {
        canonical_string(heavy()),
        canonical_string(light()),
    }
    assert_expr_equal(operator.entry(heavy, light), -g() * light())


def test_fluctuation_operator_rejects_basis_from_another_theory() -> None:
    left = Theory("fluctuation_left")
    left_phi = left.define_field("phi", s.Scalar, self_conjugate=True)
    right = Theory("fluctuation_right")
    right_phi = right.define_field("phi", s.Scalar, self_conjugate=True)
    basis = left.fluctuation_basis(left_phi() ** 2)

    with pytest.raises(ValueError, match="belongs to"):
        right.fluctuation_operator(right_phi() ** 2, basis)


def test_fluctuation_basis_modes_carry_statistics_and_mass_metadata() -> None:
    theory = Theory("fluctuation_mode_metadata")
    scalar = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    fermion = theory.define_field("psi", s.Fermion, self_conjugate=False, mass=(FieldMassKind.LIGHT, "m"))
    lagrangian = scalar() ** 2 + s.Bar(fermion()) * fermion()

    basis = theory.fluctuation_basis(lagrangian)
    scalar_mode = basis.mode_for(scalar)
    fermion_mode = basis.mode_for(fermion)
    barred_fermion_mode = basis.mode_for(s.Bar(fermion()))

    assert scalar_mode.mass_kind is FieldMassKind.HEAVY
    assert scalar_mode.statistics is FluctuationStatistics.BOSONIC
    assert scalar_mode.supertrace_sign == 1
    assert scalar_mode.index_representations == ()
    assert scalar_mode.index_dimensions == ()
    assert scalar_mode.internal_dimension == 1
    assert scalar_mode.spin_lorentz_dimension == 1
    assert scalar_mode.conjugate_mode_count == 1
    assert scalar_mode.known_component_count == 1
    assert scalar_mode.supertrace_weight == 1
    assert_expr_equal(scalar_mode.chiral_supertrace_factor, Expression.num(1))
    assert scalar_mode.self_conjugate is True
    assert scalar_mode.conjugated is False
    assert fermion_mode.mass_kind is FieldMassKind.LIGHT
    assert fermion_mode.statistics is FluctuationStatistics.FERMIONIC
    assert fermion_mode.supertrace_sign == -1
    assert fermion_mode.chirality is FieldChirality.NONE
    assert fermion_mode.spin_lorentz_dimension == 4
    assert fermion_mode.conjugate_mode_count == 2
    assert fermion_mode.known_component_count == 4
    assert fermion_mode.internal_dimension == 1
    assert fermion_mode.supertrace_weight == -1
    assert_expr_equal(fermion_mode.chiral_supertrace_factor, Expression.num(1))
    assert fermion_mode.conjugated is False
    assert barred_fermion_mode.statistics is FluctuationStatistics.FERMIONIC
    assert barred_fermion_mode.conjugated is True
    assert basis.heavy_modes == (scalar_mode,)
    assert {canonical_string(mode.field) for mode in basis.light_modes} == {
        canonical_string(s.Bar(fermion())),
        canonical_string(fermion()),
    }


def test_fluctuation_modes_carry_internal_representation_dimensions() -> None:
    theory = Theory("fluctuation_mode_dimensions")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    theory.define_global_group("SU2L", s.SU(Expression.num(2)))
    su3_fund = theory.define_representation("SU3c", "fund")
    su2_fund = theory.define_representation("SU2L", "fund")
    flavor = theory.define_flavor_index("Flavor", 3)
    quark = theory.define_field(
        "Q",
        s.Fermion,
        indices=[su3_fund, su2_fund, flavor.symbol],
        mass=(FieldMassKind.LIGHT, "mQ"),
    )
    unknown = theory.define_index_type("Unknown")
    hidden = theory.define_field("X", s.Scalar, indices=[unknown.symbol], self_conjugate=True, mass=0)
    lagrangian = s.Bar(quark()) * quark() + hidden() ** 2

    basis = theory.fluctuation_basis(lagrangian)
    quark_mode = basis.mode_for(quark)
    barred_quark_mode = basis.mode_for(s.Bar(quark()))
    hidden_mode = basis.mode_for(hidden)

    assert quark_mode.index_representations == (su3_fund, su2_fund, flavor.symbol)
    assert quark_mode.index_dimensions == (3, 2, 3)
    assert quark_mode.internal_dimension == 18
    assert quark_mode.supertrace_weight == -18
    assert barred_quark_mode.index_dimensions == quark_mode.index_dimensions
    assert barred_quark_mode.internal_dimension == 18
    assert barred_quark_mode.supertrace_weight == -18
    assert hidden_mode.index_dimensions == (None,)
    assert hidden_mode.internal_dimension is None
    assert hidden_mode.supertrace_weight is None


def test_fluctuation_modes_expose_spin_lorentz_and_reality_conventions() -> None:
    theory = Theory("fluctuation_mode_spin_lorentz")
    theory.define_gauge_group("U1X", s.U1, "gX", "X")
    vector = theory.field_handle("X")
    left = theory.define_field(
        "L",
        s.Fermion,
        chirality=FieldChirality.LEFT,
        mass=(FieldMassKind.LIGHT, "mL"),
    )
    dirac = theory.define_field("D", s.Fermion, mass=(FieldMassKind.LIGHT, "mD"))
    complex_scalar = theory.define_field("Phi", s.Scalar, self_conjugate=False, mass=0)
    ghost = theory.define_field("c", s.Ghost, mass=(FieldMassKind.LIGHT, "mc"))
    lagrangian = (
        vector() ** 2
        + s.Bar(left()) * left()
        + s.Bar(dirac()) * dirac()
        + s.Bar(complex_scalar()) * complex_scalar()
        + s.Bar(ghost()) * ghost()
    )

    basis = theory.fluctuation_basis(lagrangian)
    vector_mode = basis.mode_for(vector)
    left_mode = basis.mode_for(left)
    dirac_mode = basis.mode_for(dirac)
    scalar_mode = basis.mode_for(complex_scalar)
    barred_scalar_mode = basis.mode_for(s.Bar(complex_scalar()))
    ghost_mode = basis.mode_for(ghost)

    assert vector_mode.spin_lorentz_dimension is None
    assert vector_mode.known_component_count is None
    assert vector_mode.conjugate_mode_count == 1
    assert left_mode.chirality is FieldChirality.LEFT
    assert left_mode.spin_lorentz_dimension == 2
    assert left_mode.known_component_count == 2
    assert_expr_equal(left_mode.chiral_supertrace_factor, Expression.num(1) / 2)
    assert dirac_mode.chirality is FieldChirality.NONE
    assert dirac_mode.spin_lorentz_dimension == 4
    assert dirac_mode.known_component_count == 4
    assert_expr_equal(dirac_mode.chiral_supertrace_factor, Expression.num(1))
    assert scalar_mode.conjugate_mode_count == 2
    assert barred_scalar_mode.conjugate_mode_count == 2
    assert scalar_mode.spin_lorentz_dimension == 1
    assert ghost_mode.spin_lorentz_dimension == 1
    assert ghost_mode.statistics is FluctuationStatistics.FERMIONIC


def test_fluctuation_basis_discovers_vector_modes_from_field_strength_atoms() -> None:
    theory = Theory("fluctuation_basis_field_strength_vector")
    theory.define_gauge_group("U1X", s.U1, "gX", "X")
    vector = theory.field_handle("X")
    lagrangian = theory.free_lag(vector)

    basis = theory.fluctuation_basis(lagrangian)
    mode = basis.mode_for(vector)

    assert len(basis.entries) == 1
    assert_expr_equal(basis.entries[0], vector())
    assert mode.statistics is FluctuationStatistics.BOSONIC
    assert mode.supertrace_category == "lVector"


def test_fluctuation_operator_recognizes_free_vector_field_strength_kinetic_term() -> None:
    theory = Theory("fluctuation_operator_field_strength_vector")
    theory.define_gauge_group("U1X", s.U1, "gX", "X")
    vector = theory.field_handle("X")
    mu = theory.dummy_index(0)
    lagrangian = theory.free_lag(vector)

    operator = theory.fluctuation_operator(lagrangian)
    denominator = s.PropagatorDenominator(s.LoopMomentumSquared, Expression.num(0))

    assert_expr_equal(operator.entry(vector, vector), Expression.num(0))
    assert_expr_equal(operator.differential_entry(vector, vector), -s.DifferentialOperator(s.List(mu, mu)))
    assert_expr_equal(operator.momentum_entry(vector, vector), s.LoopMomentumSquared)
    assert_expr_equal(operator.propagator_denominator_entry(vector, vector), denominator)
    assert_expr_equal(operator.propagator_denominator_for_mode(vector), denominator)
    assert_expr_equal(operator.free_inverse_entry(vector, vector), s.LoopMomentumSquared)
    assert_expr_equal(operator.interaction_entry(vector, vector), Expression.num(0))


def test_fluctuation_operator_keeps_vector_kinetic_interactions_after_free_subtraction() -> None:
    theory = Theory("fluctuation_operator_vector_kinetic_interaction")
    theory.define_gauge_group("U1X", s.U1, "gX", "X")
    vector = theory.field_handle("X")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    c = theory.define_coupling("c", self_conjugate=True)
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    strength = s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List())
    lagrangian = theory.free_lag(vector) - c() * heavy() * strength**2

    operator = theory.fluctuation_operator(lagrangian, [vector])
    denominator = s.PropagatorDenominator(s.LoopMomentumSquared, Expression.num(0))

    assert_expr_equal(
        operator.differential_entry(vector, vector),
        (-1 - 4 * c() * heavy()) * s.DifferentialOperator(s.List(mu, mu)),
    )
    assert_expr_equal(operator.momentum_entry(vector, vector), (1 + 4 * c() * heavy()) * s.LoopMomentumSquared)
    assert operator.propagator_denominator_entry(vector, vector) is None
    assert_expr_equal(operator.propagator_denominator_for_mode(vector), denominator)
    assert_expr_equal(operator.free_inverse_entry(vector, vector), s.LoopMomentumSquared)
    assert_expr_equal(operator.interaction_entry(vector, vector), 4 * c() * heavy() * s.LoopMomentumSquared)


def test_fluctuation_operator_extracts_vector_field_strength_kinetic_mixing() -> None:
    theory = Theory("fluctuation_operator_vector_kinetic_mixing")
    theory.define_gauge_group("U1X", s.U1, "gX", "X")
    theory.define_gauge_group("U1Y", s.U1, "gY", "Y")
    x_vector = theory.field_handle("X")
    y_vector = theory.field_handle("Y")
    chi = theory.define_coupling("chi", self_conjugate=True)
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    x_strength = s.FieldStrength(x_vector.label, s.List(mu, nu), s.List(), s.List())
    y_strength = s.FieldStrength(y_vector.label, s.List(mu, nu), s.List(), s.List())
    lagrangian = theory.free_lag(x_vector, y_vector) - chi() * x_strength * y_strength / 2

    operator = theory.fluctuation_operator(lagrangian, [x_vector, y_vector])

    assert_expr_equal(operator.differential_entry(x_vector, y_vector), -chi() * s.DifferentialOperator(s.List(mu, mu)))
    assert_expr_equal(operator.differential_entry(y_vector, x_vector), -chi() * s.DifferentialOperator(s.List(mu, mu)))
    assert_expr_equal(operator.momentum_entry(x_vector, y_vector), chi() * s.LoopMomentumSquared)
    assert_expr_equal(operator.momentum_entry(y_vector, x_vector), chi() * s.LoopMomentumSquared)
    assert operator.propagator_denominator_entry(x_vector, y_vector) is None
    assert_expr_equal(operator.free_inverse_entry(x_vector, y_vector), Expression.num(0))
    assert_expr_equal(operator.interaction_entry(x_vector, y_vector), chi() * s.LoopMomentumSquared)
    assert_expr_equal(operator.interaction_entry(y_vector, x_vector), chi() * s.LoopMomentumSquared)


def test_fluctuation_operator_recognizes_massive_vector_free_denominator() -> None:
    theory = Theory("fluctuation_operator_massive_vector")
    group = theory.define_global_group("GV", s.U1)
    vector = theory.define_field("V", s.Vector(group), self_conjugate=True, mass=(FieldMassKind.HEAVY, "MV"))
    mass = theory.mass_expr(vector.definition)
    assert mass is not None
    mu = theory.dummy_index(0)
    lagrangian = theory.free_lag(vector)

    operator = theory.fluctuation_operator(lagrangian)
    denominator = s.PropagatorDenominator(s.LoopMomentumSquared, mass**2)

    assert_expr_equal(operator.entry(vector, vector), -mass**2)
    assert_expr_equal(operator.differential_entry(vector, vector), -mass**2 - s.DifferentialOperator(s.List(mu, mu)))
    assert_expr_equal(operator.momentum_entry(vector, vector), s.LoopMomentumSquared - mass**2)
    assert_expr_equal(operator.propagator_denominator_entry(vector, vector), denominator)
    assert_expr_equal(operator.propagator_denominator_for_mode(vector), denominator)
    assert_expr_equal(operator.free_inverse_entry(vector, vector), s.LoopMomentumSquared - mass**2)
    assert_expr_equal(operator.interaction_entry(vector, vector), Expression.num(0))


def test_one_loop_setup_builds_operator_derived_vector_propagator_insertions() -> None:
    theory = Theory("one_loop_setup_vector_operator_denominators")
    theory.define_gauge_group("U1X", s.U1, "gX", "X")
    vector = theory.field_handle("X")
    lagrangian = theory.free_lag(vector)
    setup = theory.one_loop_setup(lagrangian, max_trace_order=1, include_light_only=True)
    trace = next(trace for trace in setup.block_traces if trace.name == "lVector")
    denominator = s.PropagatorDenominator(s.LoopMomentumSquared, Expression.num(0))

    assert setup.operator_propagator_denominator_chain(trace) == ((denominator,),)
    assert setup.operator_propagator_mass_squared_chain(trace) == ((Expression.num(0),),)
    assert_expr_equal(
        setup.operator_propagator_expression(trace),
        s.SupertraceKernel(trace.expression, s.List(s.List(denominator))),
    )
    assert_expr_equal(
        setup.operator_vakint_integral_expression(trace),
        vakint_backend.one_loop_vacuum_integral(trace.expression, (Expression.num(0),)),
    )


def test_one_loop_setup_builds_operator_derived_massive_vector_propagator_insertions() -> None:
    theory = Theory("one_loop_setup_massive_vector_operator_denominators")
    group = theory.define_global_group("GV", s.U1)
    vector = theory.define_field("V", s.Vector(group), self_conjugate=True, mass=(FieldMassKind.HEAVY, "MV"))
    mass = theory.mass_expr(vector.definition)
    assert mass is not None
    lagrangian = theory.free_lag(vector)
    setup = theory.one_loop_setup(lagrangian, max_trace_order=1)
    trace = next(trace for trace in setup.block_traces if trace.name == "hVector")
    denominator = s.PropagatorDenominator(s.LoopMomentumSquared, mass**2)

    assert setup.operator_propagator_denominator_chain(trace) == ((denominator,),)
    assert setup.operator_propagator_mass_squared_chain(trace) == ((mass**2,),)
    assert_expr_equal(
        setup.operator_vakint_integral_expression(trace),
        vakint_backend.one_loop_vacuum_integral(trace.expression, (mass**2,)),
    )


def test_fluctuation_basis_skips_background_fields_and_grades_ghosts_as_fermionic() -> None:
    theory = Theory("fluctuation_field_roles")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    background = theory.define_field("v", s.Scalar, field_role=FieldRole.BACKGROUND, self_conjugate=True, mass=0)
    ghost = theory.define_field("c", s.Ghost, mass=(FieldMassKind.HEAVY, "Mc"))

    lagrangian = heavy() ** 2 + background() ** 2 + s.Bar(ghost()) * ghost()
    basis = theory.fluctuation_basis(lagrangian)

    assert canonical_string(background()) not in {canonical_string(entry) for entry in basis.entries}
    ghost_mode = basis.mode_for(ghost)
    barred_ghost_mode = basis.mode_for(s.Bar(ghost()))
    assert ghost_mode.field_role is FieldRole.GHOST
    assert ghost_mode.statistics is FluctuationStatistics.FERMIONIC
    assert barred_ghost_mode.statistics is FluctuationStatistics.FERMIONIC
    assert ghost_mode.supertrace_sign == -1

    with pytest.raises(ValueError, match="Non-propagating"):
        theory.fluctuation_operator(lagrangian, fields=[background])


def test_fluctuation_operator_extracts_heavy_light_sector_blocks() -> None:
    theory = Theory("fluctuation_sector_blocks")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    g = theory.define_coupling("g", self_conjugate=True)
    lagrangian = -g() * heavy() * light() ** 2 / 2

    operator = theory.fluctuation_operator(lagrangian)
    heavy_light = operator.block(FluctuationSector.HEAVY, FluctuationSector.LIGHT)
    light_heavy = operator.block("light", "heavy")

    assert tuple(mode.field for mode in heavy_light.rows) == (heavy(),)
    assert tuple(mode.field for mode in heavy_light.columns) == (light(),)
    assert_expr_equal(heavy_light.entry(heavy, light), -g() * light())
    assert_expr_equal(light_heavy.entry(light, heavy), -g() * light())
    assert heavy_light.to_expression_map()


def test_fluctuation_operator_all_sector_block_preserves_full_matrix() -> None:
    theory = Theory("fluctuation_sector_all")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    lagrangian = heavy() ** 2 + light() ** 2

    operator = theory.fluctuation_operator(lagrangian)
    full = operator.block("all", "all")

    assert full.rows == operator.modes
    assert full.columns == operator.modes
    assert full.matrix == operator.matrix


def test_fluctuation_operator_rejects_unknown_sector_selector() -> None:
    theory = Theory("fluctuation_bad_sector")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True)
    operator = theory.fluctuation_operator(phi() ** 2)

    with pytest.raises(ValueError, match="fluctuation sector"):
        operator.block("bad", "heavy")


def test_fluctuation_operator_builds_supertrace_plan_from_sector_blocks() -> None:
    theory = Theory("fluctuation_supertrace_plan")
    heavy_scalar = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    heavy_fermion = theory.define_field("Psi", s.Fermion, self_conjugate=False, mass=(FieldMassKind.HEAVY, "MF"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = (
        heavy_scalar() ** 2
        + s.Bar(heavy_fermion()) * heavy_fermion()
        - y() * heavy_scalar() * light() ** 2 / 2
    )

    operator = theory.fluctuation_operator(lagrangian)
    plan = operator.supertrace_plan()

    assert plan.heavy_heavy == operator.block("heavy", "heavy")
    assert plan.heavy_light == operator.block("heavy", "light")
    assert plan.light_heavy == operator.block("light", "heavy")
    assert plan.light_light == operator.block("light", "light")
    assert plan.heavy_mode_count == 3
    assert plan.light_mode_count == 1
    assert plan.heavy_supertrace_sign == -1
    assert len(plan.blocks()) == 4
    assert plan.to_expression_map()


def test_supertrace_plan_builds_weighted_block_trace_with_symbolica_matrix_product() -> None:
    theory = Theory("supertrace_block_trace")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = heavy() ** 2 - y() * heavy() * light() ** 2 / 2

    plan = theory.fluctuation_operator(lagrangian).supertrace_plan()
    heavy_heavy = plan.block_trace("heavy_heavy", plan.heavy_heavy)
    heavy_light_mixing = plan.block_trace("heavy_light_light_heavy", plan.heavy_light, plan.light_heavy)

    assert heavy_heavy.order == 1
    assert heavy_heavy.block_sectors == ((FluctuationSector.HEAVY, FluctuationSector.HEAVY),)
    assert_expr_equal(heavy_heavy.expression, plan.heavy_heavy.entry(heavy, heavy))
    assert heavy_light_mixing.order == 2
    assert heavy_light_mixing.block_sectors == (
        (FluctuationSector.HEAVY, FluctuationSector.LIGHT),
        (FluctuationSector.LIGHT, FluctuationSector.HEAVY),
    )
    assert_expr_equal(heavy_light_mixing.expression, y() ** 2 * light() ** 2)
    assert heavy_light_mixing.to_expression_map()


def test_supertrace_plan_falls_back_for_non_polynomial_matrix_entries() -> None:
    theory = Theory("supertrace_expression_matrix_fallback")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    coefficient = S("external::F")
    lagrangian = coefficient(light()) * heavy() ** 2 / 2

    plan = theory.fluctuation_operator(lagrangian).supertrace_plan()
    trace = plan.block_trace("heavy_heavy", plan.heavy_heavy)

    assert_expr_equal(trace.expression, coefficient(light()))


def test_supertrace_plan_rejects_non_closed_block_trace() -> None:
    theory = Theory("supertrace_bad_block_trace")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    lagrangian = heavy() * light()

    plan = theory.fluctuation_operator(lagrangian).supertrace_plan()

    with pytest.raises(ValueError, match="closed mode chain"):
        plan.block_trace("open", plan.heavy_light)

    with pytest.raises(ValueError, match="matching column and row modes"):
        plan.block_trace("mismatched", plan.heavy_heavy, plan.light_heavy)


def test_supertrace_plan_generates_closed_block_traces_by_order() -> None:
    theory = Theory("supertrace_closed_paths")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = heavy() ** 2 + light() ** 2 - y() * heavy() * light() ** 2 / 2

    plan = theory.fluctuation_operator(lagrangian).supertrace_plan()
    order_one = plan.closed_block_traces(1)
    order_one_with_light = plan.closed_block_traces(1, include_light_only=True)
    order_two = {trace.name: trace for trace in plan.closed_block_traces(2)}
    category_order_one = plan.closed_category_traces(1)
    category_order_two = {trace.name: trace for trace in plan.closed_category_traces(2)}

    assert tuple(trace.name for trace in order_one) == ("heavy-heavy",)
    assert tuple(trace.name for trace in order_one_with_light) == ("heavy-heavy", "light-light")
    assert set(order_two) == {
        "heavy-heavy-heavy",
        "heavy-light-heavy",
        "light-heavy-light",
    }
    assert order_two["heavy-light-heavy"].cyclic_sector_key == order_two["light-heavy-light"].cyclic_sector_key
    assert_expr_equal(order_two["heavy-heavy-heavy"].expression, Expression.num(4))
    assert_expr_equal(order_two["heavy-light-heavy"].expression, y() ** 2 * light() ** 2)
    assert_expr_equal(order_two["light-heavy-light"].expression, y() ** 2 * light() ** 2)
    assert tuple(trace.name for trace in category_order_one) == ("hScalar",)
    assert set(category_order_two) == {"hScalar-hScalar", "hScalar-lScalar", "lScalar-hScalar"}
    assert category_order_two["hScalar-lScalar"].cyclic_sector_key == (
        "hScalar",
        "lScalar",
    )
    assert category_order_two["lScalar-hScalar"].cyclic_sector_key == (
        "hScalar",
        "lScalar",
    )
    assert_expr_equal(category_order_two["hScalar-lScalar"].expression, y() ** 2 * light() ** 2)

    with pytest.raises(ValueError, match="at least 1"):
        plan.closed_block_traces(0)


def test_supertrace_plan_splits_matching_traces_by_mode_category() -> None:
    theory = Theory("supertrace_category_paths")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light_scalar = theory.define_field("phi", s.Scalar, self_conjugate=True)
    light_fermion = theory.define_field("psi", s.Fermion, self_conjugate=False, mass=0)
    y = theory.define_coupling("y", self_conjugate=True)
    z = theory.define_coupling("z", self_conjugate=True)
    lagrangian = (
        heavy() ** 2
        + light_scalar() ** 2
        + s.Bar(light_fermion()) * light_fermion()
        - y() * heavy() * light_scalar() ** 2 / 2
        - z() * heavy() * s.Bar(light_fermion()) * light_fermion()
    )

    plan = theory.fluctuation_operator(lagrangian).supertrace_plan()
    category_traces = {trace.name: trace for trace in plan.closed_category_traces(2)}
    setup = theory.one_loop_setup(lagrangian, max_trace_order=2)

    assert plan.supertrace_category_labels == ("hScalar", "lScalar", "lFermion")
    assert set(category_traces) == {
        "hScalar-hScalar",
        "hScalar-lScalar",
        "hScalar-lFermion",
        "lScalar-hScalar",
        "lFermion-hScalar",
    }
    assert tuple(trace.name for trace in setup.power_type_traces()) == (
        "hScalar",
        "hScalar-hScalar",
        "hScalar-lScalar",
        "hScalar-lFermion",
    )
    assert_expr_equal(category_traces["hScalar-lScalar"].expression, y() ** 2 * light_scalar() ** 2)
    assert_expr_equal(
        category_traces["hScalar-lFermion"].expression,
        2 * z() ** 2 * s.Bar(light_fermion()) * light_fermion(),
    )


def test_theory_one_loop_setup_prepares_current_matching_pipeline_inputs() -> None:
    theory = Theory("one_loop_setup")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = heavy() ** 2 + light() ** 2 - y() * heavy() * light() ** 2 / 2

    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    trace_names = tuple(trace.name for trace in setup.block_traces)
    trace_map = setup.supertrace_expression_map()

    assert setup.theory is theory
    assert setup.uv_lagrangian == lagrangian
    assert setup.eft_order == 6
    assert setup.max_trace_order == 2
    assert setup.supertrace_kernel_count == 4
    assert setup.power_type_contribution_count == 3
    assert trace_names == (
        "hScalar",
        "hScalar-hScalar",
        "hScalar-lScalar",
        "lScalar-hScalar",
    )
    assert setup.fluctuation_operator.basis == (heavy(), light())
    assert setup.supertrace_plan.heavy_mode_count == 1
    assert_expr_equal(trace_map["supertrace_kernel[hScalar-lScalar]"], y() ** 2 * light() ** 2)
    assert tuple(trace.name for trace in setup.power_type_traces()) == (
        "hScalar",
        "hScalar-hScalar",
        "hScalar-lScalar",
    )
    power_map = setup.power_type_expression_map()
    assert_expr_equal(
        power_map["power_type_supertrace[hScalar-lScalar,numerator]"],
        -y() ** 2 * light() ** 2 / 2,
    )
    assert_expr_equal(
        power_map["power_type_supertrace[hScalar-lScalar,eft_numerator]"],
        -y() ** 2 * light() ** 2 / 2,
    )
    assert_expr_equal(
        setup.power_type_eft_lagrangian(),
        -Expression.num(2) - y() ** 2 * light() ** 2 / 2,
    )
    setup_map = setup.to_expression_map()
    assert setup_map
    assert any("fluctuation_operator_momentum" in key for key in setup_map)
    assert_expr_equal(
        setup_map["one_loop_setup[power_type_eft_lagrangian]"],
        setup.power_type_eft_lagrangian(),
    )
    preview = setup.power_type_matching_preview()
    assert isinstance(preview, MatchingResult)
    assert preview.theory is theory
    assert preview.metadata["stage"] == "power_type_vakint_result"
    assert preview.metadata["complete"] is False
    assert preview.metadata["loop_order"] == 1
    assert preview.metadata["eft_order"] == 6
    assert preview.metadata["max_trace_order"] == 2
    assert preview.metadata["power_type_contribution_count"] == 3
    assert_expr_equal(preview.off_shell_eft_lagrangian, setup.power_type_vakint_integral_sum())
    assert_expr_equal(preview.on_shell_eft_lagrangian, setup.power_type_vakint_integral_sum())
    assert_expr_equal(preview.expression("power_type_eft_lagrangian"), setup.power_type_eft_lagrangian())
    assert_expr_equal(
        preview.expression("power_type_supertrace[hScalar-lScalar,eft_numerator]"),
        -y() ** 2 * light() ** 2 / 2,
    )
    assert preview.fluctuation_operators == setup.fluctuation_operator.to_expression_map()
    preview.validate()

    with pytest.raises(ValueError, match="max_trace_order"):
        theory.one_loop_setup(lagrangian, max_trace_order=0)


def test_one_loop_setup_propagator_plan_recovers_masses_from_symbol_data() -> None:
    theory = Theory("one_loop_setup_propagators")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    heavy_mass = theory.mass_expr(heavy.definition)
    light_mass = theory.mass_expr(light.definition)
    assert heavy_mass is not None
    assert light_mass is not None
    lagrangian = -heavy_mass**2 * heavy() ** 2 / 2 - light_mass**2 * light() ** 2 / 2 - y() * heavy() * light() ** 2 / 2

    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    heavy_plan = setup.propagator_plan()
    full_plan = setup.propagator_plan(include_light=True)

    assert setup.propagator_count == 1
    assert len(heavy_plan.propagators) == 1
    assert len(heavy_plan.heavy) == 1
    assert len(heavy_plan.light) == 0
    assert len(full_plan.propagators) == 2
    assert len(full_plan.heavy) == 1
    assert len(full_plan.light) == 1
    heavy_propagator = heavy_plan.propagators[0]
    light_propagator = full_plan.light[0]
    heavy_mode = setup.fluctuation_operator.mode_for(heavy)
    light_mode = setup.fluctuation_operator.mode_for(light)
    assert heavy_propagator.mass is not None
    assert heavy_propagator.mass_squared is not None
    assert light_propagator.mass is not None
    assert light_propagator.mass_squared is not None
    assert heavy_mode.mass is not None
    assert light_mode.mass_squared is not None
    heavy_denominator = s.PropagatorDenominator(s.LoopMomentumSquared, heavy_mass**2)
    light_denominator = s.PropagatorDenominator(s.LoopMomentumSquared, light_mass**2)
    assert heavy_propagator.field == heavy()
    assert_expr_equal(heavy_propagator.mass, heavy_mass)
    assert_expr_equal(heavy_propagator.mass_squared, heavy_mass**2)
    assert_expr_equal(heavy_propagator.denominator(), heavy_denominator)
    assert_expr_equal(light_propagator.mass, light_mass)
    assert_expr_equal(light_propagator.mass_squared, light_mass**2)
    assert_expr_equal(light_propagator.denominator(), light_denominator)
    assert_expr_equal(heavy_mode.mass, heavy_mass)
    assert_expr_equal(light_mode.mass_squared, light_mass**2)
    trace = next(trace for trace in setup.block_traces if trace.name == "hScalar-lScalar")
    mass_chain = trace.propagator_mass_squared_chain()
    chain = trace.propagator_denominator_chain()
    assert len(mass_chain) == 2
    assert len(mass_chain[0]) == 1
    assert len(mass_chain[1]) == 1
    assert_expr_equal(mass_chain[0][0], heavy_mass**2)
    assert_expr_equal(mass_chain[1][0], light_mass**2)
    assert len(chain) == 2
    assert len(chain[0]) == 1
    assert len(chain[1]) == 1
    assert_expr_equal(chain[0][0], heavy_denominator)
    assert_expr_equal(chain[1][0], light_denominator)
    assert_expr_equal(
        trace.propagator_expression(),
        s.SupertraceKernel(trace.expression, s.List(s.List(heavy_denominator), s.List(light_denominator))),
    )
    decorated = setup.supertrace_propagator_expression_map()
    assert_expr_equal(
        decorated["supertrace_propagator_kernel[hScalar-lScalar]"],
        trace.propagator_expression(),
    )
    vakint_integral = vakint_backend.one_loop_vacuum_integral(trace.expression, (heavy_mass**2, light_mass**2))
    assert_expr_equal(trace.vakint_integral_expression(), vakint_integral)
    assert_expr_equal(
        setup.vakint_integral_expression_map()["vakint_integral[hScalar-lScalar]"],
        vakint_integral,
    )
    repeated_heavy_trace = next(trace for trace in setup.block_traces if trace.name == "hScalar-hScalar")
    repeated_heavy_integral = vakint_backend.one_loop_vacuum_integral(
        repeated_heavy_trace.expression,
        (heavy_mass**2,),
        powers=(2,),
    )
    assert_expr_equal(repeated_heavy_trace.vakint_integral_expression(), repeated_heavy_integral)
    assert_expr_equal(
        setup.vakint_integral_expression_map()["vakint_integral[hScalar-hScalar]"],
        repeated_heavy_integral,
    )
    canonical_engine = FakeKernelVakintEngine()
    with pytest.raises(ValueError, match="mixed-mass topologies"):
        setup.canonicalize_vakint_integral_expression_map(short_form=True, engine=canonical_engine)
    reduction_engine = FakeKernelVakintEngine()
    reduced = setup.tensor_reduce_vakint_integral_expression_map(engine=reduction_engine)
    assert len(reduction_engine.calls) == setup.supertrace_kernel_count
    assert ("tensor_reduce", vakint_integral, None) in reduction_engine.calls
    assert_expr_equal(reduced["vakint_integral[hScalar-lScalar]"], S("reduced")(vakint_integral))
    evaluation_engine = FakeKernelVakintEngine()
    with pytest.raises(ValueError, match="mixed-mass topologies"):
        setup.evaluate_vakint_integral_expression_map(engine=evaluation_engine)
    contribution = next(item for item in setup.power_type_contributions() if item.name == "hScalar-lScalar")
    assert_expr_equal(contribution.prefactor, -Expression.num(1) / 2)
    assert_expr_equal(contribution.numerator_expression, -trace.expression / 2)
    assert_expr_equal(contribution.eft_numerator_expression, -trace.expression / 2)
    assert_expr_equal(
        contribution.vakint_integral_expression(),
        vakint_backend.one_loop_vacuum_integral(-trace.expression / 2, (heavy_mass**2, light_mass**2)),
    )
    expected_power_type_vakint_sum = (
        vakint_backend.one_loop_vacuum_integral(heavy_mass**2 / 2, (heavy_mass**2,))
        + vakint_backend.one_loop_vacuum_integral(-(heavy_mass**2) ** 2 / 4, (heavy_mass**2, heavy_mass**2))
        + vakint_backend.one_loop_vacuum_integral(
            -y() ** 2 * light() ** 2 / 2,
            (heavy_mass**2, light_mass**2),
        )
    ).expand()
    assert_expr_equal(setup.power_type_vakint_integral_sum(), expected_power_type_vakint_sum)
    canonical_power_engine = FakeKernelVakintEngine()
    with pytest.raises(ValueError, match="mixed-mass topologies"):
        setup.power_type_vakint_integral_sum(
            stage=VakintIntegralStage.CANONICAL,
            short_form=True,
            engine=canonical_power_engine,
        )
    reduced_power_engine = FakeKernelVakintEngine()
    reduced_power_sum = setup.power_type_vakint_integral_sum(
        stage=VakintIntegralStage.TENSOR_REDUCED,
        engine=reduced_power_engine,
    )
    assert reduced_power_engine.calls == [("tensor_reduce", expected_power_type_vakint_sum, None)]
    assert_expr_equal(reduced_power_sum, S("reduced")(expected_power_type_vakint_sum))
    evaluated_power_engine = FakeKernelVakintEngine()
    with pytest.raises(ValueError, match="mixed-mass topologies"):
        setup.power_type_vakint_integral_sum(
            stage=VakintIntegralStage.EVALUATED,
            engine=evaluated_power_engine,
        )
    expected_power_type_internal = vacuum_integrals_backend.evaluate_one_loop_vakint_expression(
        expected_power_type_vakint_sum,
        combine_terms=True,
    )
    internal_power_result = setup.power_type_internal_matching_result(
        tensor_reduce=False,
        combine_terms=True,
    )
    expected_power_type_pole = vakint_backend.pole_part(expected_power_type_internal)
    expected_power_type_finite = vakint_backend.finite_part(expected_power_type_internal)
    assert internal_power_result.metadata["stage"] == "power_type_internal_integral_result"
    assert internal_power_result.metadata["integral_backend"] == "pychete_internal"
    assert internal_power_result.metadata["tensor_reduce"] is False
    assert internal_power_result.metadata["combine_terms"] is True
    assert_expr_equal(internal_power_result.off_shell_eft_lagrangian, expected_power_type_internal)
    assert_expr_equal(internal_power_result.on_shell_eft_lagrangian, expected_power_type_internal)
    assert_expr_equal(
        internal_power_result.expression("power_type_internal_integral_sum"),
        expected_power_type_internal,
    )
    assert_expr_equal(
        internal_power_result.expression("power_type_internal_integral_pole_part"),
        expected_power_type_pole,
    )
    assert_expr_equal(
        internal_power_result.expression("power_type_internal_integral_finite_part"),
        expected_power_type_finite,
    )
    internal_power_subtracted = setup.power_type_internal_minimal_subtraction_result(
        tensor_reduce=False,
        combine_terms=True,
    )
    assert internal_power_subtracted.metadata["stage"] == "power_type_internal_minimal_subtraction_result"
    assert internal_power_subtracted.metadata["subtraction_scheme"] == "minimal_subtraction_preview"
    assert internal_power_subtracted.metadata["poles_subtracted"] is True
    assert internal_power_subtracted.metadata["integral_backend"] == "pychete_internal"
    assert_expr_equal(internal_power_subtracted.off_shell_eft_lagrangian, expected_power_type_finite)
    assert_expr_equal(internal_power_subtracted.on_shell_eft_lagrangian, expected_power_type_finite)
    assert_expr_equal(
        internal_power_subtracted.expression("power_type_internal_integral_ms_counterterm"),
        -expected_power_type_pole,
    )
    assert_expr_equal(
        internal_power_subtracted.expression("power_type_internal_integral_finite_part"),
        expected_power_type_finite,
    )
    with pytest.raises(ValueError, match="vakint integral stage"):
        setup.power_type_vakint_integral_sum(stage="bad-stage")
    assert_expr_equal(
        setup.power_type_matching_preview().expression("power_type_vakint_integral_sum"),
        expected_power_type_vakint_sum,
    )
    assert_expr_equal(
        setup.power_type_matching_result().off_shell_eft_lagrangian,
        expected_power_type_vakint_sum,
    )
    assert_expr_equal(
        setup.power_type_matching_result().expression("power_type_eft_lagrangian"),
        setup.power_type_eft_lagrangian(),
    )
    preview_engine = FakeKernelVakintEngine()
    with pytest.raises(ValueError, match="mixed-mass topologies"):
        setup.power_type_matching_preview(
            vakint_stage=VakintIntegralStage.CANONICAL,
            vakint_short_form=True,
            vakint_engine=preview_engine,
        )
    assert "propagator_plan" in next(iter(full_plan.to_expression_map()))
    assert any(key.startswith("one_loop_setup.propagator[") for key in setup.to_expression_map())
    assert any(key.startswith("one_loop_setup.supertrace_propagator_kernel[") for key in setup.to_expression_map())
    assert any(key.startswith("one_loop_setup.vakint_integral[") for key in setup.to_expression_map())
    assert any(key.startswith("one_loop_setup.power_type_supertrace[") for key in setup.to_expression_map())
    assert any(key == "one_loop_setup[power_type_vakint_integral_sum]" for key in setup.to_expression_map())


def test_one_loop_setup_builds_operator_derived_propagator_insertions() -> None:
    theory = Theory("one_loop_setup_operator_denominators")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    heavy_mass = theory.mass_expr(heavy.definition)
    light_mass = theory.mass_expr(light.definition)
    assert heavy_mass is not None
    assert light_mass is not None
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    trace = next(trace for trace in setup.block_traces if trace.name == "hScalar-lScalar")
    heavy_denominator = s.PropagatorDenominator(s.LoopMomentumSquared, heavy_mass**2)
    light_denominator = s.PropagatorDenominator(s.LoopMomentumSquared, light_mass**2)
    expected_chain = ((heavy_denominator,), (light_denominator,))
    expected_mass_chain = ((heavy_mass**2,), (light_mass**2,))
    expected_kernel = s.SupertraceKernel(trace.expression, s.List(s.List(heavy_denominator), s.List(light_denominator)))
    expected_vakint = vakint_backend.one_loop_vacuum_integral(trace.expression, (heavy_mass**2, light_mass**2))

    assert setup.operator_propagator_denominator_chain(trace) == expected_chain
    assert setup.operator_propagator_mass_squared_chain("hScalar-lScalar") == expected_mass_chain
    assert_expr_equal(setup.operator_propagator_expression(trace), expected_kernel)
    assert_expr_equal(setup.operator_vakint_integral_expression("hScalar-lScalar"), expected_vakint)
    operator_decorated = setup.supertrace_operator_propagator_expression_map(skip_unrecognized=False)
    operator_integrals = setup.operator_vakint_integral_expression_map(skip_unrecognized=False)
    assert_expr_equal(
        operator_decorated["supertrace_operator_propagator_kernel[hScalar-lScalar]"],
        expected_kernel,
    )
    assert_expr_equal(operator_integrals["operator_vakint_integral[hScalar-lScalar]"], expected_vakint)
    setup_map = setup.to_expression_map()
    assert any(key.startswith("one_loop_setup.supertrace_operator_propagator_kernel[") for key in setup_map)
    assert any(key.startswith("one_loop_setup.operator_vakint_integral[") for key in setup_map)


def test_one_loop_setup_builds_operator_derived_fermion_propagator_insertions() -> None:
    theory = Theory("one_loop_setup_operator_fermion_denominators")
    heavy = theory.define_field("Psi", s.Fermion, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("psi", s.Fermion, mass=0)
    scalar = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    y = theory.define_coupling("y")
    heavy_mass = theory.mass_expr(heavy.definition)
    assert heavy_mass is not None
    interaction = -y() * scalar() * s.NCM(s.Bar(light()), s.PR, heavy())
    lagrangian = theory.free_lag(heavy, light, scalar) + interaction + s.Bar(interaction)
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    trace = next(trace for trace in setup.block_traces if trace.name == "hFermion-lFermion")
    heavy_denominator = s.PropagatorDenominator(s.LoopMomentumSquared, heavy_mass**2)
    light_denominator = s.PropagatorDenominator(s.LoopMomentumSquared, Expression.num(0))
    expected_chain = ((heavy_denominator, heavy_denominator), (light_denominator, light_denominator))
    expected_mass_chain = ((heavy_mass**2, heavy_mass**2), (Expression.num(0), Expression.num(0)))

    assert setup.operator_propagator_denominator_chain(trace) == expected_chain
    assert setup.operator_propagator_mass_squared_chain(trace) == expected_mass_chain
    assert_expr_equal(
        setup.operator_propagator_expression(trace),
        s.SupertraceKernel(
            trace.expression,
            s.List(
                s.List(heavy_denominator, heavy_denominator),
                s.List(light_denominator, light_denominator),
            ),
        ),
    )


def test_one_loop_setup_builds_interaction_only_fluctuation_traces() -> None:
    theory = Theory("one_loop_setup_interaction_operator")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    heavy_mass = theory.mass_expr(heavy.definition)
    light_mass = theory.mass_expr(light.definition)
    assert heavy_mass is not None
    assert light_mass is not None
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    operator = setup.fluctuation_operator

    assert_expr_equal(operator.free_inverse_entry(heavy, heavy), s.LoopMomentumSquared - heavy_mass**2)
    assert_expr_equal(operator.free_inverse_entry(light, light), s.LoopMomentumSquared - light_mass**2)
    assert_expr_equal(operator.free_inverse_entry(heavy, light), Expression.num(0))
    assert_expr_equal(operator.interaction_entry(heavy, heavy), Expression.num(0))
    assert_expr_equal(operator.interaction_entry(light, light), -y() * heavy())
    assert_expr_equal(operator.interaction_entry(heavy, light), -y() * light())
    assert_expr_equal(operator.interaction_entry(light, heavy), -y() * light())

    interaction_map = operator.interaction_expression_map()
    assert_expr_equal(
        interaction_map[f"fluctuation_operator_interaction[{canonical_string(heavy())},{canonical_string(heavy())}]"],
        Expression.num(0),
    )
    interaction_plan = setup.interaction_supertrace_plan()
    assert_expr_equal(interaction_plan.heavy_heavy.entry(heavy, heavy), Expression.num(0))
    assert_expr_equal(interaction_plan.light_light.entry(light, light), -y() * heavy())
    interaction_traces = {trace.name: trace for trace in setup.interaction_block_traces()}
    assert_expr_equal(interaction_traces["hScalar"].expression, Expression.num(0))
    assert_expr_equal(interaction_traces["hScalar-hScalar"].expression, Expression.num(0))
    assert_expr_equal(interaction_traces["hScalar-lScalar"].expression, y() ** 2 * light() ** 2)
    interaction_supertraces = setup.interaction_supertrace_expression_map()
    assert_expr_equal(interaction_supertraces["interaction_supertrace_kernel[hScalar]"], Expression.num(0))
    assert setup.interaction_power_type_contribution_count == 3
    assert tuple(trace.name for trace in setup.interaction_power_type_traces()) == (
        "hScalar",
        "hScalar-hScalar",
        "hScalar-lScalar",
    )
    interaction_power_map = setup.interaction_power_type_expression_map()
    assert_expr_equal(
        interaction_power_map["interaction_power_type_supertrace[hScalar,eft_numerator]"],
        Expression.num(0),
    )
    assert_expr_equal(
        interaction_power_map["interaction_power_type_supertrace[hScalar-lScalar,eft_numerator]"],
        -y() ** 2 * light() ** 2 / 2,
    )
    assert_expr_equal(setup.interaction_power_type_eft_lagrangian(), -y() ** 2 * light() ** 2 / 2)
    expected_interaction_vakint = vakint_backend.one_loop_vacuum_integral(
        -y() ** 2 * light() ** 2 / 2,
        (heavy_mass**2, light_mass**2),
    )
    assert_expr_equal(setup.interaction_power_type_vakint_integral_sum(), expected_interaction_vakint)
    assert_expr_equal(
        setup.interaction_power_type_internal_integral_sum(tensor_reduce=False),
        vacuum_integrals_backend.evaluate_one_loop_vakint_expression(expected_interaction_vakint),
    )
    canonical_engine = FakeKernelVakintEngine()
    with pytest.raises(ValueError, match="mixed-mass topologies"):
        setup.interaction_power_type_vakint_integral_sum(
            stage=VakintIntegralStage.CANONICAL,
            short_form=True,
            engine=canonical_engine,
        )
    interaction_result = setup.interaction_power_type_matching_result()
    assert interaction_result.metadata["stage"] == "interaction_power_type_vakint_result"
    assert interaction_result.metadata["uses_interaction_operator"] is True
    assert interaction_result.metadata["power_type_contribution_count"] == 3
    assert interaction_result.metadata["interaction_power_type_contribution_count"] == 3
    assert interaction_result.metadata["named_supertrace_stage"] == "raw"
    assert_expr_equal(interaction_result.off_shell_eft_lagrangian, expected_interaction_vakint)
    assert_expr_equal(
        interaction_result.expression("interaction_power_type_eft_lagrangian"),
        -y() ** 2 * light() ** 2 / 2,
    )
    assert_expr_equal(interaction_result.expression("hScalar-lScalar"), expected_interaction_vakint)
    named_engine = FakeKernelVakintEngine()
    named_reduced_result = setup.interaction_power_type_matching_result(
        named_supertrace_stage=VakintIntegralStage.TENSOR_REDUCED,
        named_supertrace_engine=named_engine,
    )
    expected_named_calls = [
        ("tensor_reduce", contribution.vakint_integral_expression(), None)
        for contribution in setup.interaction_power_type_contributions()
    ]
    assert named_engine.calls == expected_named_calls
    assert named_reduced_result.metadata["vakint_stage"] == "raw"
    assert named_reduced_result.metadata["named_supertrace_stage"] == "tensor_reduced"
    assert_expr_equal(named_reduced_result.off_shell_eft_lagrangian, expected_interaction_vakint)
    assert_expr_equal(
        named_reduced_result.expression("hScalar-lScalar"),
        S("reduced")(expected_interaction_vakint),
    )
    internal_result = setup.interaction_power_type_internal_matching_result(
        tensor_reduce=False,
        combine_terms=True,
    )
    expected_internal = vacuum_integrals_backend.evaluate_one_loop_vakint_expression(
        expected_interaction_vakint,
        combine_terms=True,
    )
    assert internal_result.metadata["stage"] == "interaction_power_type_internal_integral_result"
    assert internal_result.metadata["integral_backend"] == "pychete_internal"
    assert internal_result.metadata["tensor_reduce"] is False
    assert internal_result.metadata["combine_terms"] is True
    assert_expr_equal(internal_result.off_shell_eft_lagrangian, expected_internal)
    assert_expr_equal(internal_result.expression("hScalar-lScalar"), expected_internal)
    assert_expr_equal(internal_result.expression("interaction_power_type_vakint_integral_sum"), expected_interaction_vakint)
    assert_expr_equal(internal_result.expression("interaction_power_type_internal_integral_sum"), expected_internal)
    assert_expr_equal(
        internal_result.expression("interaction_power_type_internal_integral_pole_part"),
        vakint_backend.pole_part(expected_internal),
    )
    assert_expr_equal(
        internal_result.expression("interaction_power_type_internal_integral_finite_part"),
        vakint_backend.finite_part(expected_internal),
    )
    internal_subtracted = setup.interaction_power_type_internal_minimal_subtraction_result(
        tensor_reduce=False,
        combine_terms=True,
    )
    expected_internal_pole = vakint_backend.pole_part(expected_internal)
    expected_internal_finite = vakint_backend.finite_part(expected_internal)
    assert internal_subtracted.metadata["stage"] == "interaction_power_type_internal_minimal_subtraction_result"
    assert internal_subtracted.metadata["subtraction_scheme"] == "minimal_subtraction_preview"
    assert internal_subtracted.metadata["poles_subtracted"] is True
    assert internal_subtracted.metadata["integral_backend"] == "pychete_internal"
    assert internal_subtracted.metadata["tensor_reduce"] is False
    assert internal_subtracted.metadata["combine_terms"] is True
    assert_expr_equal(internal_subtracted.off_shell_eft_lagrangian, expected_internal_finite)
    assert_expr_equal(internal_subtracted.on_shell_eft_lagrangian, expected_internal_finite)
    assert_expr_equal(internal_subtracted.expression("hScalar-lScalar"), expected_internal_finite)
    assert_expr_equal(
        internal_subtracted.expression("interaction_power_type_internal_integral_sum"),
        expected_internal,
    )
    assert_expr_equal(
        internal_subtracted.expression("interaction_power_type_internal_integral_pole_part"),
        expected_internal_pole,
    )
    assert_expr_equal(
        internal_subtracted.expression("interaction_power_type_internal_integral_ms_counterterm"),
        -expected_internal_pole,
    )
    assert_expr_equal(
        internal_subtracted.expression("interaction_power_type_internal_integral_finite_part"),
        expected_internal_finite,
    )
    matchete_hbar_factor = one_loop_normalization_factor(OneLoopNormalization.MATCHETE_HBAR)
    external_hbar = S("matching_normalization_external_hbar")
    assert_expr_equal(one_loop_normalization_factor(None), Expression.num(1))
    assert_expr_equal(matchete_hbar_factor, Expression.I * s.HBar)
    assert_expr_equal(
        one_loop_normalization_factor(OneLoopNormalization.MATCHETE_HBAR, hbar=external_hbar),
        Expression.I * external_hbar,
    )
    assert_expr_equal(
        one_loop_normalization_factor(OneLoopNormalization.MATCHETE_EVALUATED_HBAR, hbar=external_hbar),
        16 * Expression.PI**2 * Expression.I * external_hbar,
    )
    assert_expr_equal(
        (
            one_loop_normalization_factor(OneLoopNormalization.MATCHETE_EVALUATED_HBAR, hbar=external_hbar)
            * (-Expression.I / (192 * Expression.PI**2))
        ).expand(),
        external_hbar / 12,
    )
    assert_expr_equal(
        one_loop_normalization_factor(OneLoopNormalization.MATCHETE_LOOP_FACTOR),
        Expression.I / (16 * Expression.PI**2),
    )
    normalized_interaction_result = setup.interaction_power_type_normalized_matching_result(
        normalization=OneLoopNormalization.MATCHETE_HBAR,
    )
    assert normalized_interaction_result.metadata["stage"] == "interaction_power_type_normalized_vakint_result"
    assert normalized_interaction_result.metadata["loop_normalization"] == "matchete_hbar"
    assert normalized_interaction_result.metadata["loop_normalization_applied"] is True
    assert normalized_interaction_result.metadata["uses_interaction_operator"] is True
    assert_expr_equal(
        normalized_interaction_result.expression("interaction_power_type_loop_normalization_factor"),
        matchete_hbar_factor,
    )
    assert_expr_equal(
        normalized_interaction_result.expression("interaction_power_type_vakint_integral_sum_unnormalized"),
        expected_interaction_vakint,
    )
    assert_expr_equal(
        normalized_interaction_result.expression("hScalar-lScalar[unnormalized]"),
        expected_interaction_vakint,
    )
    assert_expr_equal(
        normalized_interaction_result.expression("hScalar-lScalar"),
        matchete_hbar_factor * expected_interaction_vakint,
    )
    assert_expr_equal(
        normalized_interaction_result.off_shell_eft_lagrangian,
        matchete_hbar_factor * expected_interaction_vakint,
    )
    assert_expr_equal(
        normalized_interaction_result.expression("interaction_power_type_normalized_eft_lagrangian"),
        matchete_hbar_factor * expected_interaction_vakint,
    )
    setup_map = setup.to_expression_map()
    assert_expr_equal(
        setup_map[f"one_loop_setup.fluctuation_operator_interaction[{canonical_string(light())},{canonical_string(light())}]"],
        -y() * heavy(),
    )
    assert_expr_equal(
        setup_map["one_loop_setup.interaction_supertrace_kernel[hScalar-lScalar]"],
        y() ** 2 * light() ** 2,
    )
    assert_expr_equal(
        setup_map["one_loop_setup.interaction_power_type_supertrace[hScalar-lScalar,eft_numerator]"],
        -y() ** 2 * light() ** 2 / 2,
    )
    assert_expr_equal(
        setup_map["one_loop_setup[interaction_power_type_vakint_integral_sum]"],
        expected_interaction_vakint,
    )


def test_power_type_prefactor_keeps_periodic_cyclic_trace_factor() -> None:
    theory = Theory("one_loop_setup_periodic_trace_prefactor")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() ** 2 * light() / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=3)
    contributions = {contribution.name: contribution for contribution in setup.interaction_power_type_contributions()}

    assert_expr_equal(contributions["hScalar"].prefactor, -Expression.num(1) / 2)
    assert_expr_equal(contributions["hScalar-hScalar"].prefactor, -Expression.num(1) / 4)
    assert_expr_equal(contributions["hScalar-hScalar-hScalar"].prefactor, -Expression.num(1) / 6)
    assert_expr_equal(contributions["hScalar-hScalar"].numerator_expression, -y() ** 2 * light() ** 2 / 4)
    assert_expr_equal(contributions["hScalar-hScalar-hScalar"].numerator_expression, y() ** 3 * light() ** 3 / 6)


def test_one_loop_setup_exposes_explicit_wilson_line_trace_paths() -> None:
    theory = Theory("one_loop_setup_wilson_line_paths")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    heavy_mass = theory.mass_expr(heavy.definition)
    light_mass = theory.mass_expr(light.definition)
    assert heavy_mass is not None
    assert light_mass is not None
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2

    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    paths_by_trace = setup.interaction_wilson_line_trace_paths_by_trace()
    path = paths_by_trace["hScalar-lScalar"][0]

    assert isinstance(path, WilsonLineTracePath)
    assert path.trace_name == "hScalar-lScalar"
    assert path.path_index == 0
    assert path.order == 2
    assert path.sign == 1
    assert path.closing_mode.is_heavy is True
    assert_expr_equal(path.prefactor, -Expression.num(1) / 2)
    assert tuple(canonical_string(mass) for mass in path.mass_squareds()) == (
        canonical_string(light_mass**2),
        canonical_string(heavy_mass**2),
    )
    assert canonical_string(path.wilson_line_expression()).startswith("pychete::WilsonLine")
    assert canonical_string(path.wilson_term_expression([theory.index("mu")])).startswith("pychete::WilsonTerm")
    assert "pychete::WilsonLine" in canonical_string(path.template_expression())
    kernel = path.kernel_expression()
    assert canonical_string(kernel).startswith("pychete::SupertraceKernel")

    expression_map = setup.interaction_wilson_line_kernel_expression_map()
    assert_expr_equal(expression_map["interaction_wilson_line_kernel[hScalar-lScalar,0]"], kernel)
    setup_map = setup.to_expression_map()
    assert_expr_equal(setup_map["one_loop_setup.interaction_wilson_line_kernel[hScalar-lScalar,0]"], kernel)
    assert "pychete::WilsonTerm" not in canonical_string(path.wilson_term_expanded_template_expression())
    assert "pychete::WilsonTerm" not in canonical_string(path.wilson_term_expanded_kernel_expression())


def test_wilson_line_path_expands_propagator_terms_without_cde_result_object() -> None:
    theory = Theory("one_loop_setup_wilson_line_expansion_terms")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    heavy_mass = theory.mass_expr(heavy.definition)
    light_mass = theory.mass_expr(light.definition)
    assert heavy_mass is not None
    assert light_mass is not None
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    path = setup.interaction_wilson_line_trace_paths_by_trace()["hScalar-lScalar"][0]
    expansion = {"hScalar-lScalar": ((), ())}

    terms = path.propagator_expansion_terms(expansion["hScalar-lScalar"])
    grouped = setup.interaction_wilson_line_expansion_terms_by_trace(expansion)
    kernels = setup.interaction_wilson_line_expansion_kernel_expression_map(expansion)
    integrals = setup.interaction_wilson_line_expansion_vakint_integral_expression_map(expansion)
    generated_plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar-lScalar",),
        max_total_order=0,
    )
    generated_grouped = setup.interaction_wilson_line_expansion_terms_by_trace(generated_plan)
    generated_kernels = setup.interaction_wilson_line_expansion_kernel_expression_map(generated_plan)

    expected_numerator = -y() ** 2 * light() ** 2 / 2
    expected_kernel = s.SupertraceKernel(
        expected_numerator,
        s.List(
            s.List(s.PropagatorDenominator(s.LoopMomentumSquared, light_mass**2)),
            s.List(s.PropagatorDenominator(s.LoopMomentumSquared, heavy_mass**2)),
        ),
    )
    expected_integral = vakint_backend.one_loop_vacuum_integral(
        expected_numerator,
        (light_mass**2, heavy_mass**2),
        powers=(1, 1),
    )

    assert len(terms) == 1
    assert isinstance(terms[0], WilsonLineTraceExpansionTerm)
    assert not isinstance(terms[0], BosonicCDETraceExpansionTerm)
    assert tuple(grouped) == ("hScalar-lScalar",)
    assert len(grouped["hScalar-lScalar"]) == 1
    assert grouped["hScalar-lScalar"][0].path_index == terms[0].path_index
    assert_expr_equal(grouped["hScalar-lScalar"][0].kernel_expression(), expected_kernel)
    assert tuple(kernels) == ("interaction_wilson_line_expansion_kernel[hScalar-lScalar,0,0]",)
    assert tuple(integrals) == ("interaction_wilson_line_expansion_vakint_integral[hScalar-lScalar,0,0]",)
    assert isinstance(generated_plan, WilsonLineExpansionPlan)
    assert generated_plan.trace_names == ("hScalar-lScalar",)
    assert generated_plan.trace_count == 1
    assert generated_plan.entry_count == 1
    assert isinstance(generated_plan.entries[0], WilsonLineExpansionPlanEntry)
    assert generated_plan.entries[0].slot_orders == (0, 0)
    assert tuple(generated_grouped) == ("hScalar-lScalar#wilson0_o0_0",)
    assert generated_grouped["hScalar-lScalar#wilson0_o0_0"][0].path_index == terms[0].path_index
    assert_expr_equal(terms[0].kernel_expression(), expected_kernel)
    assert_expr_equal(kernels["interaction_wilson_line_expansion_kernel[hScalar-lScalar,0,0]"], expected_kernel)
    assert_expr_equal(
        generated_kernels["interaction_wilson_line_expansion_kernel[hScalar-lScalar#wilson0_o0_0,0,0]"],
        expected_kernel,
    )
    assert_expr_equal(
        integrals["interaction_wilson_line_expansion_vakint_integral[hScalar-lScalar,0,0]"],
        expected_integral,
    )
    assert "pychete::WilsonTerm" not in canonical_string(terms[0].numerator)


def test_wilson_line_complex_scalar_paths_follow_conjugate_propagators() -> None:
    theory = Theory("one_loop_setup_wilson_line_complex_scalar_pairing")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("H", s.Scalar, self_conjugate=False, mass=0)
    coupling = theory.define_coupling("A", self_conjugate=True)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(light)
        - coupling() * heavy() * s.Bar(light()) * light()
    )

    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    trace = next(trace for trace in setup.interaction_power_type_traces() if trace.name == "hScalar-lScalar")
    terms = setup.interaction_wilson_line_expansion_terms({"hScalar-lScalar": ((), ())})
    numerator_sum = sum((term.numerator for term in terms), Expression.num(0)).expand()

    assert len(terms) == 2
    assert_expr_equal(trace.expression, 2 * coupling() ** 2 * s.Bar(light()) * light())
    assert_expr_equal(numerator_sum, -coupling() ** 2 * s.Bar(light()) * light())
    assert_expr_equal(numerator_sum.coefficient(coupling() ** 2 * light() ** 2).expand(), Expression.num(0))
    assert_expr_equal(
        numerator_sum.coefficient(coupling() ** 2 * s.Bar(light()) ** 2).expand(),
        Expression.num(0),
    )


def test_wilson_line_expansion_can_simplify_generated_color_algebra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("one_loop_setup_wilson_line_generated_color_simplification")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    expansion = {"hScalar-lScalar": ((), ())}
    calls: list[tuple[Theory, Expression]] = []
    marker = S("generated_wilson_line_color_simplified")

    def fake_simplify_pychete_color_algebra(
        call_theory: Theory,
        expr: Expression,
        **_: object,
    ) -> Expression:
        calls.append((call_theory, expr))
        return (expr + marker).expand()

    monkeypatch.setattr(idenso_backend, "simplify_pychete_color_algebra", fake_simplify_pychete_color_algebra)

    raw_terms = setup.interaction_wilson_line_expansion_terms(expansion)
    simplified_terms = setup.interaction_wilson_line_expansion_terms(
        expansion,
        simplify_pychete_color_algebra=True,
    )

    assert calls == [(theory, raw_terms[0].numerator)]
    assert "generated_wilson_line_color_simplified" not in canonical_string(raw_terms[0].numerator)
    assert "generated_wilson_line_color_simplified" in canonical_string(simplified_terms[0].numerator)


def test_wilson_line_open_derivatives_act_right_without_cyclic_wrap() -> None:
    theory = Theory("one_loop_setup_wilson_line_right_acting_open_cd")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field(
        "H",
        s.Scalar,
        charges=[theory.group_charge("U1Y", Expression.num(1))],
        self_conjugate=False,
        mass=0,
    )
    vector = theory.field_handle("B")
    coupling = theory.define_coupling("A", self_conjugate=True, mass_dimension=1)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(light)
        + theory.free_lag(vector)
        - coupling() * heavy() * s.Bar(light()) * light()
    )
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    a = theory.index("a")
    b = theory.index("b")
    c = theory.index("c")
    d = theory.index("d")

    pure_heavy_terms = setup.interaction_wilson_line_expansion_terms(
        {"hScalar": ((a, b, c, d),)},
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=True,
        emit_covariant_derivative_commutator_passes=4,
        expand_covariant_derivative_commutators=True,
    )
    mixed_terms = setup.interaction_wilson_line_expansion_terms(
        {"hScalar-lScalar": ((a, b, c, d), ())},
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=True,
        emit_covariant_derivative_commutator_passes=4,
        expand_covariant_derivative_commutators=True,
    )
    rendered = "\n".join(canonical_string(term.numerator) for term in mixed_terms)

    assert pure_heavy_terms == ()
    assert len(mixed_terms) == 10
    assert "pychete::FieldStrength" in rendered
    assert "pychete::OpenCD" not in rendered
    assert "coupling_gY" not in rendered


def test_wilson_line_vector_slots_use_matchete_propagator_sign() -> None:
    theory = Theory("one_loop_setup_wilson_line_vector_prop_sign")
    group = theory.symbol("G", role=SymbolRole.GROUP)
    vector = theory.define_field("V", s.Vector(group), self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    vector_mass = theory.mass_expr(vector.definition)
    light_mass = theory.mass_expr(light.definition)
    assert vector_mass is not None
    assert light_mass is not None
    lagrangian = theory.free_lag(vector) + theory.free_lag(light) - y() * vector() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    expansion = {"hVector-lScalar": ((), ())}
    terms = setup.interaction_wilson_line_expansion_terms(expansion)
    left = theory.index(theory.symbol("wilson_line_hVector_lScalar_0_left", role=SymbolRole.INDEX))
    right = theory.index(theory.symbol("wilson_line_hVector_lScalar_0_right", role=SymbolRole.INDEX))

    assert len(terms) == 1
    assert terms[0].propagator_powers == (1, 1)
    assert_expr_equal(
        terms[0].numerator,
        y() ** 2 * light() ** 2 * s.Metric(left, right) / 2,
    )
    assert_expr_equal(
        terms[0].kernel_expression(),
        s.SupertraceKernel(
            y() ** 2 * light() ** 2 * s.Metric(left, right) / 2,
            s.List(
                s.List(s.PropagatorDenominator(s.LoopMomentumSquared, light_mass**2)),
                s.List(s.PropagatorDenominator(s.LoopMomentumSquared, vector_mass**2)),
            ),
        ),
    )


def test_public_wilson_line_can_filter_terms_by_matching_targets() -> None:
    theory = Theory("one_loop_setup_wilson_line_filter_targets")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    z = theory.define_coupling("z", self_conjugate=True)
    wilson = theory.define_wilson_coefficient("cPhi2", operator=light() ** 2)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(light)
        - y() * heavy() * light() ** 2 / 2
        - z() * heavy() ** 2 / 2
    )
    common_options = dict(
        integral_backend=OneLoopIntegralBackend.VAKINT,
        max_trace_order=2,
        wilson_line_trace_names=("hScalar", "hScalar-lScalar"),
        wilson_line_max_total_order=0,
        truncate_eft_result=False,
    )
    unfiltered = theory.match(
        lagrangian,
        loop_order=1,
        matching_condition_targets="registered_wilsons",
        matching_condition_expand_source=False,
        one_loop_options=OneLoopMatchOptions(**common_options),
    )
    filtered = theory.match(
        lagrangian,
        loop_order=1,
        matching_condition_targets="registered_wilsons",
        matching_condition_expand_source=False,
        one_loop_options=OneLoopMatchOptions(
            **common_options,
            wilson_line_filter_terms_by_matching_targets=True,
        ),
    )
    target = canonical_string(s.Coupling(wilson.label, s.List(), Expression.num(0)))

    assert unfiltered.metadata["wilson_line_terms_filtered_by_matching_targets"] is False
    assert filtered.metadata["wilson_line_terms_filtered_by_matching_targets"] is True
    assert unfiltered.metadata["interaction_wilson_line_term_count"] == 2
    assert filtered.metadata["interaction_wilson_line_term_count"] == 1
    assert set(filtered.matching_conditions) == {target}
    assert not bool(filtered.matching_conditions[target].expand() == Expression.num(0))


def test_wilson_line_target_filter_skips_impossible_entries_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("one_loop_setup_wilson_line_filter_impossible_strength")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    define_smeft_wilson_coefficient(theory, "cHW")
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar-lScalar",),
        max_total_order=4,
        max_slot_order=4,
    )
    requirements = matching_module._term_atom_requirements_for_targets(theory, "registered_wilsons")
    assert requirements is not None

    def fail_generation(*_args: object, **_kwargs: object) -> tuple[WilsonLineTraceExpansionTerm, ...]:
        raise AssertionError("impossible target-local entries should be skipped before term generation")

    monkeypatch.setattr(
        matching_module.WilsonLineTracePath,
        "propagator_expansion_terms",
        fail_generation,
    )

    grouped = setup.interaction_wilson_line_expansion_terms_by_trace(
        plan,
        term_atom_requirements=requirements,
    )

    assert grouped
    assert all(terms == () for terms in grouped.values())


def test_singlet_wilson_line_target_prefilter_matches_matchete_order_four_insertions() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    target = smeft_warsaw_operator(theory, "cHW")
    assert target is not None
    setup = theory.one_loop_setup(
        fixture.expression("lagrangian"),
        eft_order=6,
        max_trace_order=2,
    )
    plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar-lScalar",),
        max_total_order=4,
        max_slot_order=4,
        index_prefix="singlet_prefilter",
    )
    requirements = matching_module._term_atom_requirements_for_targets(theory, {"cHW": target})
    assert requirements is not None
    phi_pattern = field_pattern(theory.field_handle("phi").label)
    grouped_terms = setup.interaction_wilson_line_expansion_terms_by_trace(
        plan,
        act_open_derivatives=False,
        max_wilson_derivative_order=4,
        term_atom_requirements=requirements,
    )

    counts_by_slot_order: dict[tuple[int, ...], int] = {}
    expanded_counts_by_slot_order: dict[tuple[int, ...], int] = {}
    phi_atom_count = 0
    for entry in plan.entries:
        if entry.total_order != 4:
            continue
        entry_terms = tuple(grouped_terms[entry.label])
        counts_by_slot_order[entry.slot_orders] = len(entry_terms)
        expanded_count = 0
        for term in entry_terms:
            pre_wilson_numerator = term.pre_wilson_numerator
            assert pre_wilson_numerator is not None
            expanded_count += len(expression_terms(pre_wilson_numerator.expand()))
            phi_atom_count += sum(1 for _match in pre_wilson_numerator.match(phi_pattern))
        expanded_counts_by_slot_order[entry.slot_orders] = expanded_count

    expected_counts = {
        (0, 4): 10,
        (1, 3): 6,
        (2, 2): 8,
        (3, 1): 6,
        (4, 0): 10,
    }
    assert counts_by_slot_order == expected_counts
    assert expanded_counts_by_slot_order == expected_counts
    assert sum(counts_by_slot_order.values()) == 40
    assert phi_atom_count == 0


def test_singlet_four_slot_scalar_vector_trace_has_implicit_abelian_xterms() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    setup = theory.one_loop_setup(
        fixture.expression("lagrangian"),
        eft_order=6,
        max_trace_order=4,
        include_light_only=True,
    )
    plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar-lScalar-lVector-lScalar",),
        max_total_order=0,
        max_slot_order=0,
        index_prefix="singlet_hslvls",
    )

    grouped_terms = setup.interaction_wilson_line_expansion_terms_by_trace(
        plan,
        act_open_derivatives=False,
        max_wilson_derivative_order=4,
        simplify_pychete_color_algebra=True,
    )
    collected_grouped_terms = setup.interaction_wilson_line_expansion_terms_by_trace(
        plan,
        act_open_derivatives=False,
        max_wilson_derivative_order=4,
        simplify_pychete_color_algebra=True,
        collect_path_sums=True,
    )
    generated_terms = tuple(term for entry_terms in grouped_terms.values() for term in entry_terms)
    collected_terms = tuple(term for entry_terms in collected_grouped_terms.values() for term in entry_terms)
    numerator_sum = sum((term.numerator for term in generated_terms), Expression.num(0)).expand()
    collected_numerator_sum = sum((term.numerator for term in collected_terms), Expression.num(0)).expand()

    assert len(generated_terms) == 16
    assert len(collected_terms) == 1
    assert_expr_equal(collected_numerator_sum, numerator_sum)
    assert all(bool(term.numerator.matches(s.OpenCD(s.OpenCDIndicesWildcard))) for term in generated_terms)
    assert not bool(numerator_sum.coefficient(theory.coupling_handle("gY")() ** 2).expand() == Expression.num(0))

    acted_terms = tuple(
        term
        for entry_terms in setup.interaction_wilson_line_expansion_terms_by_trace(
            plan,
            act_open_derivatives=True,
            max_wilson_derivative_order=4,
            simplify_pychete_color_algebra=True,
        ).values()
        for term in entry_terms
    )
    acted_collected_terms = tuple(
        term
        for entry_terms in setup.interaction_wilson_line_expansion_terms_by_trace(
            plan,
            act_open_derivatives=True,
            max_wilson_derivative_order=4,
            simplify_pychete_color_algebra=True,
            collect_path_sums=True,
        ).values()
        for term in entry_terms
    )
    acted_numerator_sum = sum((term.numerator for term in acted_terms), Expression.num(0)).expand()
    acted_collected_numerator_sum = sum(
        (term.numerator for term in acted_collected_terms),
        Expression.num(0),
    ).expand()
    assert len(acted_terms) == 16
    assert len(acted_collected_terms) == 1
    assert_expr_equal(acted_collected_numerator_sum, acted_numerator_sum)
    assert all(not bool(term.numerator.matches(s.OpenCD(s.OpenCDIndicesWildcard))) for term in acted_terms)


def test_wilson_line_expansion_drops_odd_loop_rank_after_open_derivatives() -> None:
    theory = Theory("one_loop_setup_wilson_line_odd_loop_rank")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    mu = theory.lorentz_index("mu")
    expansion = {"hScalar-lScalar": ((mu,), ())}

    terms = setup.interaction_wilson_line_expansion_terms(
        expansion,
        act_open_derivatives=True,
    )
    kernels = setup.interaction_wilson_line_expansion_kernel_expression_map(
        expansion,
        act_open_derivatives=True,
    )

    assert terms == ()
    assert kernels == {}


def test_wilson_line_tensor_reduced_postprocess_contracts_derivative_metrics() -> None:
    theory = Theory("one_loop_setup_wilson_line_tensor_reduced_derivatives")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    higgs = theory.define_field(
        "H",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        mass=0,
    )
    a = theory.index("a")
    b = theory.index("b")
    c = theory.index("c")
    source = s.Metric(a, c) * higgs() * s.Bar(higgs(derivatives=[c, b, a]))

    processed = matching_module._postprocess_wilson_line_tensor_reduced_expression(
        theory,
        source,
        emit_covariant_derivative_commutators=True,
        emit_covariant_derivative_commutator_passes=2,
        expand_covariant_derivative_commutators=True,
        simplify_pychete_color_algebra=False,
    )

    rendered = canonical_string(processed)
    assert "pychete::Metric" not in rendered
    assert "pychete::FieldStrength" in rendered


def test_wilson_term_metric_contraction_updates_formal_derivative_slots() -> None:
    theory = Theory("one_loop_setup_wilson_line_formal_metric_contraction")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    nu = theory.index("nu")
    rho = theory.index("rho")
    sigma = theory.index("sigma")
    term = s.WilsonTerm(phi.label, s.List(left, right), s.List(mu, rho))
    source = s.Metric(mu, nu) * s.Delta(rho, sigma) * term

    contracted = contract_wilson_term_derivative_metrics(source, max_derivative_order=4)

    assert_expr_equal(
        contracted,
        s.WilsonTerm(phi.label, s.List(left, right), s.List(nu, sigma)),
    )


def test_wilson_term_metric_contraction_leaves_nonmatching_metrics_bounded() -> None:
    theory = Theory("one_loop_setup_wilson_line_formal_metric_nonmatch")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    nu = theory.index("nu")
    rho = theory.index("rho")
    sigma = theory.index("sigma")
    source = s.Metric(rho, sigma) * s.WilsonTerm(phi.label, s.List(left, right), s.List(mu, nu))

    contracted = contract_wilson_term_derivative_metrics(source, max_derivative_order=4)

    assert_expr_equal(contracted, source)


def test_wilson_line_internal_evaluation_can_tensor_reduce_before_wilson_expansion() -> None:
    theory = Theory("one_loop_setup_wilson_line_pre_wilson_tensor_reduce")
    theory.define_gauge_group("SU2L", s.SU(2), "g2", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    mass = theory.define_coupling("M", self_conjugate=True, mass_dimension=1)
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    nu = theory.index("nu")
    rho = theory.index("rho")
    formal_numerator = (
        s.LoopMomentum(mu)
        * s.LoopMomentum(nu)
        * s.WilsonTerm(higgs.label, s.List(left, right), s.List(mu, rho))
    )
    term = WilsonLineTraceExpansionTerm(
        theory=theory,
        trace_name="probe",
        path_index=0,
        expansion_indices=((mu, nu),),
        numerator=Expression.num(0),
        mass_squareds=(mass() ** 2,),
        propagator_powers=(3,),
        pre_wilson_numerator=formal_numerator,
    )

    evaluated = matching_module._wilson_line_internal_evaluated_terms_from_terms(
        theory,
        (term,),
        tensor_reduce=True,
        tensor_reduce_engine=None,
        tensor_reduce_before_wilson_expand=True,
        max_wilson_derivative_order=4,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="inversions",
        expand_covariant_derivative_commutators=False,
        simplify_pychete_color_algebra=False,
        expose_scalar_derivative_commutator_bilinears=False,
        epsilon=None,
        mu_r_squared=None,
    )

    rendered = canonical_string(evaluated[0])
    assert rendered != "0"
    assert "pychete::WilsonTerm" not in rendered
    assert "pychete::Metric" not in rendered
    assert "pychete::FieldStrength" in rendered

    evaluated_by_entry = matching_module._wilson_line_internal_evaluated_entry_expressions_by_entry_from_terms(
        theory,
        {"probe#wilson0": (term,)},
        tensor_reduce=True,
        tensor_reduce_engine=None,
        tensor_reduce_before_wilson_expand=True,
        max_wilson_derivative_order=4,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="inversions",
        expand_covariant_derivative_commutators=False,
        simplify_pychete_color_algebra=False,
        epsilon=None,
        mu_r_squared=None,
    )

    assert_expr_equal(evaluated_by_entry["probe#wilson0"], evaluated[0])


def test_one_loop_match_can_use_selected_wilson_line_expansion_route() -> None:
    theory = Theory("one_loop_match_wilson_line_expansion")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    heavy_mass = theory.mass_expr(heavy.definition)
    light_mass = theory.mass_expr(light.definition)
    assert heavy_mass is not None
    assert light_mass is not None
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    expansion = {"hScalar-lScalar": ((), ())}
    expected_numerator = -y() ** 2 * light() ** 2 / 2
    expected_selected_integral = vakint_backend.one_loop_vacuum_integral(
        expected_numerator,
        (light_mass**2, heavy_mass**2),
        powers=(1, 1),
    )
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    expected_remainder = setup.interaction_power_type_vakint_integral_sum(
        exclude_trace_names=("hScalar-lScalar",),
    )
    expected_integral = (expected_remainder + expected_selected_integral).expand()

    result = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.VAKINT,
            wilson_line_expansion_indices_by_trace=expansion,
            wilson_line_emit_covariant_derivative_commutators=True,
            wilson_line_emit_covariant_derivative_commutator_passes=1,
            wilson_line_covariant_derivative_commutator_mode="all_distinct",
            wilson_line_expand_covariant_derivative_commutators=True,
            truncate_eft_result=False,
        ),
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["stage"] == "interaction_wilson_line_hybrid_vakint_result"
    assert result.metadata["uses_wilson_line_expansion"] is True
    assert result.metadata["uses_interaction_power_remainder"] is True
    assert result.metadata["interaction_wilson_line_hybrid"] is True
    assert result.metadata["wilson_line_expansion_enabled"] is True
    assert result.metadata["wilson_line_commutators_emitted"] is True
    assert result.metadata["wilson_line_commutator_emit_passes"] == 1
    assert result.metadata["wilson_line_commutator_emit_mode"] == "all_distinct"
    assert result.metadata["wilson_line_commutators_expanded"] is True
    assert result.metadata["bosonic_cde_expansion_enabled"] is False
    assert result.metadata["interaction_wilson_line_commutators_emitted"] is True
    assert result.metadata["interaction_wilson_line_commutator_emit_passes"] == 1
    assert result.metadata["interaction_wilson_line_commutator_emit_mode"] == "all_distinct"
    assert result.metadata["interaction_wilson_line_commutators_expanded"] is True
    assert result.metadata["interaction_wilson_line_term_count"] == 1
    assert result.metadata["interaction_wilson_line_trace_names"] == ("hScalar-lScalar",)
    assert result.metadata["interaction_wilson_line_replaced_trace_names"] == "hScalar-lScalar"
    assert_expr_equal(result.off_shell_eft_lagrangian, expected_integral)
    assert_expr_equal(result.expression("interaction_wilson_line_vakint_integral_sum"), expected_selected_integral)
    assert_expr_equal(result.expression("interaction_wilson_line_hybrid_vakint_integral_sum"), expected_integral)

    color_simplified_result = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.VAKINT,
            wilson_line_expansion_indices_by_trace=expansion,
            truncate_eft_result=False,
            simplify_pychete_color_algebra=True,
        ),
    )

    assert color_simplified_result.metadata["pychete_color_algebra_simplified"] is True
    assert (
        color_simplified_result.metadata["interaction_wilson_line_pychete_color_algebra_simplified"]
        is True
    )
    assert_expr_equal(
        color_simplified_result.expression("interaction_wilson_line_vakint_integral_sum"),
        expected_selected_integral,
    )

    generated_result = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.VAKINT,
            wilson_line_trace_names=("hScalar-lScalar",),
            wilson_line_max_total_order=0,
            truncate_eft_result=False,
        ),
    )

    assert isinstance(generated_result, MatchingResult)
    assert generated_result.metadata["stage"] == "interaction_wilson_line_hybrid_vakint_result"
    assert generated_result.metadata["wilson_line_expansion_enabled"] is True
    assert generated_result.metadata["wilson_line_expansion_planned"] is True
    assert generated_result.metadata["wilson_line_trace_names"] == "hScalar-lScalar"
    assert generated_result.metadata["interaction_wilson_line_planned"] is True
    assert generated_result.metadata["interaction_wilson_line_plan_entry_count"] == 1
    assert_expr_equal(generated_result.off_shell_eft_lagrangian, expected_integral)


def test_wilson_line_hybrid_internal_reuses_component_laurent_parts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("one_loop_setup_wilson_line_hybrid_component_laurent")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light)
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    remainder_expr = S("remainder_expr")
    wilson_expr = S("wilson_expr")
    remainder_pole = S("remainder_pole")
    wilson_pole = S("wilson_pole")
    remainder_finite = S("remainder_finite")
    wilson_finite = S("wilson_finite")
    captured_wilson_line_kwargs: dict[str, object] = {}

    def fake_remainder(*_args: object, **_kwargs: object) -> MatchingResult:
        return MatchingResult(
            theory=theory,
            uv_lagrangian=lagrangian,
            off_shell_eft_lagrangian=remainder_expr,
            on_shell_eft_lagrangian=remainder_expr,
            supertraces={
                "interaction_power_type_internal_integral_pole_part": remainder_pole,
                "interaction_power_type_internal_integral_finite_part": remainder_finite,
            },
            metadata={
                "stage": "fake_remainder",
                "interaction_power_type_contribution_count": 1,
            },
        )

    def fake_wilson_line(*_args: object, **kwargs: object) -> MatchingResult:
        captured_wilson_line_kwargs.update(kwargs)
        return MatchingResult(
            theory=theory,
            uv_lagrangian=lagrangian,
            off_shell_eft_lagrangian=wilson_expr,
            on_shell_eft_lagrangian=wilson_expr,
            supertraces={
                "interaction_wilson_line_internal_integral_pole_part": wilson_pole,
                "interaction_wilson_line_internal_integral_finite_part": wilson_finite,
            },
            metadata={
                "stage": "fake_wilson_line",
                "interaction_wilson_line_term_count": 1,
            },
        )

    def fail_aggregate_pole_part(*_args: object, **_kwargs: object) -> Expression:
        raise AssertionError("hybrid internal result should reuse component pole parts")

    def fail_aggregate_finite_part(*_args: object, **_kwargs: object) -> Expression:
        raise AssertionError("hybrid internal result should reuse component finite parts")

    monkeypatch.setattr(
        matching_module.OneLoopSetup,
        "interaction_power_type_internal_matching_result",
        fake_remainder,
    )
    monkeypatch.setattr(
        matching_module.OneLoopSetup,
        "interaction_wilson_line_internal_matching_result",
        fake_wilson_line,
    )
    monkeypatch.setattr(vakint_backend, "pole_part", fail_aggregate_pole_part)
    monkeypatch.setattr(vakint_backend, "finite_part", fail_aggregate_finite_part)

    result = setup.interaction_wilson_line_hybrid_internal_matching_result(
        {"hScalar-lScalar": ((), ())},
        expose_scalar_derivative_commutator_bilinears=True,
    )

    assert captured_wilson_line_kwargs["expose_scalar_derivative_commutator_bilinears"] is True
    assert_expr_equal(
        result.expression("interaction_wilson_line_hybrid_internal_integral_pole_part"),
        remainder_pole + wilson_pole,
    )
    assert_expr_equal(
        result.expression("interaction_wilson_line_hybrid_internal_integral_finite_part"),
        remainder_finite + wilson_finite,
    )


def test_one_loop_match_forwards_wilson_line_scalar_derivative_bilinear_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("one_loop_match_wilson_line_scalar_derivative_option")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light)
    captured_hybrid_kwargs: dict[str, object] = {}

    def fake_hybrid(
        self: matching_module.OneLoopSetup,
        expansion_indices_by_trace: object,
        **kwargs: object,
    ) -> MatchingResult:
        captured_hybrid_kwargs["expansion_indices_by_trace"] = expansion_indices_by_trace
        captured_hybrid_kwargs.update(kwargs)
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=S("fake_wilson_line_hybrid_internal_result"),
            on_shell_eft_lagrangian=S("fake_wilson_line_hybrid_internal_result"),
            supertraces={
                "interaction_wilson_line_hybrid_internal_integral_sum": S(
                    "fake_wilson_line_hybrid_internal_result"
                ),
            },
            metadata={
                "stage": "fake_wilson_line_hybrid_internal",
                "complete": False,
            },
        )

    monkeypatch.setattr(
        matching_module.OneLoopSetup,
        "interaction_wilson_line_hybrid_internal_matching_result",
        fake_hybrid,
    )

    result = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            wilson_line_expansion_indices_by_trace={"hScalar-lScalar": ((), ())},
            wilson_line_expose_scalar_derivative_commutator_bilinears=True,
            truncate_eft_result=False,
        ),
    )

    assert result.metadata["stage"] == "fake_wilson_line_hybrid_internal"
    assert captured_hybrid_kwargs["expose_scalar_derivative_commutator_bilinears"] is True
    assert result.metadata["wilson_line_scalar_derivative_commutator_bilinears_exposed"] is True


def test_one_loop_match_forwards_wilson_line_scalar_derivative_bilinear_option_to_vakint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("one_loop_match_wilson_line_scalar_derivative_vakint_option")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light)
    captured_hybrid_kwargs: dict[str, object] = {}

    def fake_hybrid(
        self: matching_module.OneLoopSetup,
        expansion_indices_by_trace: object,
        **kwargs: object,
    ) -> MatchingResult:
        captured_hybrid_kwargs["expansion_indices_by_trace"] = expansion_indices_by_trace
        captured_hybrid_kwargs.update(kwargs)
        return MatchingResult(
            theory=self.theory,
            uv_lagrangian=self.uv_lagrangian,
            off_shell_eft_lagrangian=S("fake_wilson_line_hybrid_vakint_result"),
            on_shell_eft_lagrangian=S("fake_wilson_line_hybrid_vakint_result"),
            supertraces={
                "interaction_wilson_line_hybrid_vakint_integral_sum": S(
                    "fake_wilson_line_hybrid_vakint_result"
                ),
            },
            metadata={
                "stage": "fake_wilson_line_hybrid_vakint",
                "complete": False,
            },
        )

    monkeypatch.setattr(
        matching_module.OneLoopSetup,
        "interaction_wilson_line_hybrid_matching_result",
        fake_hybrid,
    )

    result = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.VAKINT,
            vakint_stage=VakintIntegralStage.EVALUATED,
            wilson_line_expansion_indices_by_trace={"hScalar-lScalar": ((), ())},
            wilson_line_expose_scalar_derivative_commutator_bilinears=True,
            truncate_eft_result=False,
        ),
    )

    assert result.metadata["stage"] == "fake_wilson_line_hybrid_vakint"
    assert captured_hybrid_kwargs["expose_scalar_derivative_commutator_bilinears"] is True
    assert result.metadata["wilson_line_scalar_derivative_commutator_bilinears_exposed"] is True


def test_wilson_line_vakint_stage_postprocess_exposes_scalar_derivative_bilinears() -> None:
    theory = Theory("wilson_line_vakint_stage_scalar_bilinear_postprocess")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        self_conjugate=False,
        mass=0,
    )
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    expr = (
        (s.Bar(phi(derivatives=[mu, nu])) - s.Bar(phi(derivatives=[nu, mu])))
        * (phi(derivatives=[mu, nu]) - phi(derivatives=[nu, mu]))
    ).expand()
    formal_commutator_bilinear = (
        s.CovariantDerivativeCommutator(mu, nu, s.Bar(phi()))
        * s.CovariantDerivativeCommutator(mu, nu, phi())
    )
    expected = theory.expand_covariant_derivative_commutators(
        formal_commutator_bilinear,
        include_gauge_coupling=False,
    ).expand()

    raw = matching_module._postprocess_wilson_line_vakint_stage_expression(
        theory,
        expr,
        stage=VakintIntegralStage.RAW,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        expand_covariant_derivative_commutators=False,
        simplify_pychete_color_algebra=False,
        expose_scalar_derivative_commutator_bilinears=True,
    )
    evaluated = matching_module._postprocess_wilson_line_vakint_stage_expression(
        theory,
        expr,
        stage=VakintIntegralStage.EVALUATED,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        expand_covariant_derivative_commutators=False,
        simplify_pychete_color_algebra=False,
        expose_scalar_derivative_commutator_bilinears=True,
    )

    assert_expr_equal(raw, expr)
    assert_expr_equal(evaluated, expected)


def test_wilson_line_internal_results_expose_entrywise_laurent_sums() -> None:
    theory = Theory("one_loop_setup_wilson_line_entrywise_laurent")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    z = theory.define_coupling("z", self_conjugate=True)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(light)
        - y() * heavy() * light() ** 2 / 2
        - z() * heavy() ** 2 / 2
    )
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar-lScalar",),
        max_total_order=0,
    )
    entry_label = plan.entries[0].label

    result = setup.interaction_wilson_line_internal_matching_result(plan, tensor_reduce=False)
    assert result.metadata["interaction_wilson_line_term_count_by_entry"][entry_label] > 0
    assert_expr_equal(
        result.expression(f"interaction_wilson_line_internal_integral_sum[{entry_label}]"),
        result.expression("interaction_wilson_line_internal_integral_sum"),
    )
    assert_expr_equal(
        result.expression(f"interaction_wilson_line_internal_integral_pole_part[{entry_label}]"),
        result.expression("interaction_wilson_line_internal_integral_pole_part"),
    )
    assert_expr_equal(
        result.expression(f"interaction_wilson_line_internal_integral_finite_part[{entry_label}]"),
        result.expression("interaction_wilson_line_internal_integral_finite_part"),
    )

    subtracted = setup.interaction_wilson_line_internal_minimal_subtraction_result(plan, tensor_reduce=False)
    assert_expr_equal(
        subtracted.expression(f"interaction_wilson_line_internal_integral_finite_part[{entry_label}]"),
        subtracted.off_shell_eft_lagrangian,
    )


def test_one_loop_match_rejects_simultaneous_wilson_line_and_cde_expansion_options() -> None:
    theory = Theory("one_loop_match_wilson_line_cde_conflict")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    expansion = {"hScalar-lScalar": ((), ())}

    with pytest.raises(ValueError, match="mutually exclusive"):
        theory.match(
            lagrangian,
            loop_order=1,
            one_loop_options=OneLoopMatchOptions(
                bosonic_cde_expansion_indices_by_trace=expansion,
                wilson_line_expansion_indices_by_trace=expansion,
            ),
        )


def test_expand_wilson_terms_returns_registered_identity_transporter() -> None:
    theory = Theory("wilson_term_identity")
    theory.define_gauge_group("SU2L", s.SU(2), "g2", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")

    identity = expand_wilson_terms(theory, s.WilsonTerm(higgs.label, s.List(left, right), s.List()))
    expected_identity = s.Delta(theory.index(left, fund), theory.index(right, s.Bar(fund)))
    one_derivative = expand_wilson_terms(theory, s.WilsonTerm(higgs.label, s.List(left, right), s.List(mu)))

    assert_expr_equal(identity, expected_identity)
    assert_expr_equal(one_derivative, Expression.num(0))


def test_expand_wilson_terms_returns_non_abelian_vector_identity_transporter() -> None:
    theory = Theory("wilson_term_vector_identity")
    theory.define_gauge_group("SU2L", s.SU(2), "g2", "W")
    adj = theory.define_representation("SU2L", "adj")
    vector = theory.field_handle("W")
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)

    identity = expand_wilson_terms(theory, s.WilsonTerm(vector.label, s.List(left, right), s.List()))
    expected = (
        s.Metric(theory.index(left), theory.index(right))
        * s.Delta(theory.index(left, adj), theory.index(right, s.Bar(adj)))
    )

    assert_expr_equal(identity, expected)


def test_remove_symmetry_vanishing_wilson_terms_uses_loop_symmetry_markers() -> None:
    theory = Theory("wilson_term_symmetric_lorentz_vanish")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    nu = theory.index("nu")
    rho = theory.index("rho")
    symmetric_marker = s.SymmetricLorentzInds(s.List(mu, nu))
    vanishing = symmetric_marker * s.WilsonTerm(phi.label, s.List(left, right), s.List(mu, nu))
    repeated = s.WilsonTerm(phi.label, s.List(left, right), s.List(mu, mu))
    survivor = symmetric_marker * s.WilsonTerm(phi.label, s.List(left, right), s.List(mu, rho))
    matchete_subset_survivor = symmetric_marker * s.WilsonTerm(
        phi.label,
        s.List(left, right),
        s.List(mu, nu, rho, rho),
    )
    empty_wilson_survivor = symmetric_marker * s.WilsonTerm(phi.label, s.List(left, right), s.List())

    assert_expr_equal(remove_symmetry_vanishing_wilson_terms(vanishing), Expression.num(0))
    assert_expr_equal(remove_symmetry_vanishing_wilson_terms(repeated), Expression.num(0))
    assert_expr_equal(remove_symmetry_vanishing_wilson_terms(vanishing + survivor), survivor)
    assert_expr_equal(remove_symmetry_vanishing_wilson_terms(matchete_subset_survivor), matchete_subset_survivor)
    assert_expr_equal(remove_symmetry_vanishing_wilson_terms(empty_wilson_survivor), empty_wilson_survivor)
    assert_expr_equal(expand_wilson_terms(theory, vanishing), Expression.num(0))


def test_loop_momentum_symmetry_cleanup_preserves_backend_numerators() -> None:
    theory = Theory("wilson_term_loop_momentum_symmetry")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    nu = theory.index("nu")
    rho = theory.index("rho")
    sigma = theory.index("sigma")
    numerator = s.LoopMomentum(mu) * s.LoopMomentum(nu)
    vanishing = numerator * s.WilsonTerm(phi.label, s.List(left, right), s.List(mu, nu))
    survivor = numerator * s.WilsonTerm(phi.label, s.List(left, right), s.List(mu, rho))
    four_derivative_survivor = numerator * s.WilsonTerm(
        phi.label,
        s.List(left, right),
        s.List(mu, nu, rho, sigma),
    )
    rank_four_numerator = s.LoopMomentum(mu) * s.LoopMomentum(nu) * s.LoopMomentum(rho) * s.LoopMomentum(sigma)
    rank_four_vanishing = rank_four_numerator * s.WilsonTerm(
        phi.label,
        s.List(left, right),
        s.List(mu, nu),
    )
    rank_four_survivor = rank_four_numerator * s.WilsonTerm(
        phi.label,
        s.List(left, right),
        s.List(mu, rho, sigma, theory.index("lambda")),
    )
    rank_four_empty_wilson_survivor = rank_four_numerator * s.WilsonTerm(
        phi.label,
        s.List(left, right),
        s.List(),
    )
    odd = s.LoopMomentum(mu) * s.WilsonTerm(phi.label, s.List(left, right), s.List(mu))

    assert_expr_equal(
        remove_loop_momentum_symmetry_vanishing_wilson_terms(vanishing, (mu, nu)),
        Expression.num(0),
    )
    assert_expr_equal(
        remove_loop_momentum_symmetry_vanishing_wilson_terms(survivor, (mu, nu)),
        survivor,
    )
    assert "SymmetricLorentzInds" not in canonical_string(
        remove_loop_momentum_symmetry_vanishing_wilson_terms(survivor, (mu, nu))
    )
    assert_expr_equal(
        remove_loop_momentum_symmetry_vanishing_wilson_terms(four_derivative_survivor, (mu, nu)),
        four_derivative_survivor,
    )
    assert_expr_equal(
        remove_loop_momentum_symmetry_vanishing_wilson_terms(rank_four_vanishing, (mu, nu, rho, sigma)),
        Expression.num(0),
    )
    assert_expr_equal(
        remove_loop_momentum_symmetry_vanishing_wilson_terms(rank_four_survivor, (mu, nu, rho, sigma)),
        rank_four_survivor,
    )
    assert_expr_equal(
        remove_loop_momentum_symmetry_vanishing_wilson_terms(
            rank_four_empty_wilson_survivor,
            (mu, nu, rho, sigma),
        ),
        rank_four_empty_wilson_survivor,
    )
    assert_expr_equal(remove_loop_momentum_symmetry_vanishing_wilson_terms(odd, (mu,)), Expression.num(0))


def test_wilson_line_loop_symmetry_pruning_counts_open_differential_operator_rank() -> None:
    theory = Theory("wilson_line_open_differential_operator_loop_rank")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    expr = s.DifferentialOperator(s.List(mu)) * s.WilsonTerm(
        phi.label,
        s.List(left, right),
        s.List(),
    )

    assert_expr_equal(
        matching_module._remove_wilson_line_loop_momentum_symmetry_vanishing_terms(expr, ()),
        Expression.num(0),
    )


def test_expand_wilson_terms_lowers_abelian_two_derivative_term() -> None:
    theory = Theory("wilson_term_abelian_two_derivative")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 2)],
        self_conjugate=False,
        mass=0,
    )
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    nu = theory.index("nu")
    strength = s.FieldStrength(theory.field_handle("B").label, s.List(mu, nu), s.List(), s.List())

    expanded = expand_wilson_terms(theory, s.WilsonTerm(phi.label, s.List(left, right), s.List(mu, nu)))
    conjugate_expanded = expand_wilson_terms(
        theory,
        s.WilsonTerm(s.Bar(phi.label), s.List(left, right), s.List(mu, nu)),
    )

    assert_expr_equal(expanded, -Expression.I * strength)
    assert_expr_equal(conjugate_expanded, Expression.I * strength)


def test_expand_wilson_terms_uses_derivative_sublist_partition_for_three_derivatives() -> None:
    theory = Theory("wilson_term_abelian_three_derivative")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 2)],
        self_conjugate=False,
        mass=0,
    )
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    a = theory.index("a")
    b = theory.index("b")
    c = theory.index("c")
    vector = theory.field_handle("B").label
    expected = (
        -Expression.I
        * Expression.num(2)
        / 3
        * (
            s.FieldStrength(vector, s.List(b, c), s.List(), s.List(a))
            + s.FieldStrength(vector, s.List(a, c), s.List(), s.List(b))
        )
    )

    expanded = expand_wilson_terms(theory, s.WilsonTerm(phi.label, s.List(left, right), s.List(a, b, c)))

    assert_expr_equal(expanded, expected)


def test_expand_wilson_terms_leaves_terms_above_requested_derivative_order_formal() -> None:
    theory = Theory("wilson_term_requested_order_cap")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        self_conjugate=False,
        mass=0,
    )
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    indices = [theory.index(name) for name in ("a", "b", "c")]
    term = s.WilsonTerm(phi.label, s.List(left, right), s.List(*indices))

    expanded = expand_wilson_terms(theory, term, max_derivative_order=2)

    assert_expr_equal(expanded, term)


def test_expand_wilson_terms_uses_multi_block_derivative_partitions() -> None:
    theory = Theory("wilson_term_abelian_four_derivative")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    phi = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        self_conjugate=False,
        mass=0,
    )
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    a = theory.index("a")
    b = theory.index("b")
    c = theory.index("c")
    d = theory.index("d")
    vector = theory.field_handle("B").label

    def strength(first: Expression, second: Expression, *derivatives: Expression) -> Expression:
        return s.FieldStrength(vector, s.List(first, second), s.List(), s.List(*derivatives))

    pair_partitions = (
        strength(a, b) * strength(c, d)
        + strength(a, c) * strength(b, d)
        + strength(b, c) * strength(a, d)
    )
    full_block = (
        strength(c, d, a, b)
        + strength(b, d, a, c)
        + strength(c, d, b, a)
        + strength(a, d, b, c)
        + strength(b, d, c, a)
        + strength(a, d, c, b)
    )
    expected = -pair_partitions / 4 - Expression.I * full_block / 8

    expanded = expand_wilson_terms(theory, s.WilsonTerm(phi.label, s.List(left, right), s.List(a, b, c, d)))

    assert_expr_equal(expanded, expected)


def test_expand_wilson_terms_lowers_non_abelian_vector_two_derivative_term() -> None:
    theory = Theory("wilson_term_non_abelian_vector_two_derivative")
    theory.define_gauge_group("SU2L", s.SU(2), "g2", "W")
    adj = theory.define_representation("SU2L", "adj")
    vector = theory.field_handle("W")
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    nu = theory.index("nu")

    expanded = expand_wilson_terms(theory, s.WilsonTerm(vector.label, s.List(left, right), s.List(mu, nu)))

    output_label = theory.symbol("covariant_commutator_0_0", role=SymbolRole.INDEX)
    adjoint_label = theory.symbol("covariant_commutator_0_1", role=SymbolRole.INDEX)
    output = theory.index(output_label, adj)
    adjoint = theory.index(adjoint_label, adj)
    strength = s.FieldStrength(vector.label, s.List(mu, nu), s.List(adjoint), s.List())
    generator = theory.cg_tensor_handle("gen_SU2L_adj")
    expected = (
        -Expression.I
        / 2
        * strength
        * generator(adjoint, output, theory.index(right, adj))
        * s.Delta(theory.index(left, adj), theory.index(output_label, s.Bar(adj)))
        * s.Metric(theory.index(left), theory.index(right))
    )

    assert_expr_equal(expanded, expected)


def test_expand_wilson_terms_lowers_abelian_vector_derivative_term_to_zero() -> None:
    theory = Theory("wilson_term_abelian_vector_derivative")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    vector = theory.field_handle("B")
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    nu = theory.index("nu")

    expanded = expand_wilson_terms(theory, s.WilsonTerm(vector.label, s.List(left, right), s.List(mu, nu)))

    assert_expr_equal(expanded, Expression.num(0))


def test_expand_wilson_terms_lowers_non_abelian_two_derivative_term() -> None:
    theory = Theory("wilson_term_non_abelian_two_derivative")
    theory.define_gauge_group("SU2L", s.SU(2), "g2", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    nu = theory.index("nu")

    expanded = expand_wilson_terms(theory, s.WilsonTerm(higgs.label, s.List(left, right), s.List(mu, nu)))

    output_label = theory.symbol("covariant_commutator_0_0", role=SymbolRole.INDEX)
    adjoint_label = theory.symbol("covariant_commutator_0_1", role=SymbolRole.INDEX)
    output = theory.index(output_label, fund)
    adjoint = theory.index(adjoint_label, adj)
    strength = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adjoint), s.List())
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    expected = (
        -Expression.I
        / 2
        * strength
        * generator(adjoint, output, theory.index(right, s.Bar(fund)))
        * s.Delta(theory.index(left, fund), theory.index(output_label, s.Bar(fund)))
    )

    assert_expr_equal(expanded, expected)


def test_expand_wilson_terms_lowers_conjugate_non_abelian_two_derivative_term() -> None:
    theory = Theory("wilson_term_conjugate_non_abelian_two_derivative")
    theory.define_gauge_group("SU2L", s.SU(2), "g2", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    left = theory.symbol("wilson_left", role=SymbolRole.INDEX)
    right = theory.symbol("wilson_right", role=SymbolRole.INDEX)
    mu = theory.index("mu")
    nu = theory.index("nu")

    expanded = expand_wilson_terms(theory, s.WilsonTerm(s.Bar(higgs.label), s.List(left, right), s.List(mu, nu)))

    output_label = theory.symbol("covariant_commutator_0_0", role=SymbolRole.INDEX)
    adjoint_label = theory.symbol("covariant_commutator_0_1", role=SymbolRole.INDEX)
    output = theory.index(output_label, fund)
    adjoint = theory.index(adjoint_label, adj)
    strength = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adjoint), s.List())
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    expected = (
        Expression.I
        / 2
        * strength
        * generator(adjoint, theory.index(right, fund), theory.index(output_label, s.Bar(fund)))
        * s.Delta(theory.index(left, s.Bar(fund)), output)
    )

    assert_expr_equal(expanded, expected)


def test_interaction_bosonic_cde_expansion_maps_selected_trace_to_kernel_and_vakint() -> None:
    theory = Theory("one_loop_setup_interaction_bosonic_cde")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    heavy_mass = theory.mass_expr(heavy.definition)
    light_mass = theory.mass_expr(light.definition)
    assert heavy_mass is not None
    assert light_mass is not None
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    trace = next(trace for trace in setup.interaction_power_type_traces() if trace.name == "hScalar-lScalar")
    mu = theory.lorentz_index("mu")
    expansion = {"hScalar-lScalar": ((mu,), ())}
    first_entry = -y() * light()
    second_entry = -y() * light()
    numerator = Expression.I * s.LoopMomentum(mu) * s.NCM(
        first_entry,
        s.OpenCD(s.List(mu)),
        second_entry,
    )
    expected_kernel = s.SupertraceKernel(
        numerator,
        s.List(
            s.List(s.PropagatorDenominator(s.LoopMomentumSquared, light_mass**2) ** 2),
            s.List(s.PropagatorDenominator(s.LoopMomentumSquared, heavy_mass**2)),
        ),
    )
    expected_integral = vakint_backend.one_loop_vacuum_integral(
        numerator,
        (light_mass**2, heavy_mass**2),
        powers=(2, 1),
    )

    terms = trace.bosonic_cde_expansion_terms(expansion["hScalar-lScalar"])
    kernels = setup.interaction_bosonic_cde_kernel_expression_map(expansion)
    integrals = setup.interaction_bosonic_cde_vakint_integral_expression_map(expansion)
    acted_integrals = setup.interaction_bosonic_cde_vakint_integral_expression_map(
        expansion,
        act_open_derivatives=True,
    )
    acted_result = setup.interaction_bosonic_cde_matching_result(
        expansion,
        act_open_derivatives=True,
    )

    assert len(terms) == 1
    assert isinstance(terms[0], BosonicCDETraceExpansionTerm)
    assert tuple(kernels) == ("interaction_bosonic_cde_kernel[hScalar-lScalar,0]",)
    assert tuple(integrals) == ("interaction_bosonic_cde_vakint_integral[hScalar-lScalar,0]",)
    assert_expr_equal(terms[0].kernel_expression(), expected_kernel)
    assert_expr_equal(kernels["interaction_bosonic_cde_kernel[hScalar-lScalar,0]"], expected_kernel)
    assert_expr_equal(integrals["interaction_bosonic_cde_vakint_integral[hScalar-lScalar,0]"], expected_integral)
    cde_reduction_engine = FakeKernelVakintEngine()
    setup.interaction_bosonic_cde_vakint_integral_sum(
        expansion,
        stage=VakintIntegralStage.TENSOR_REDUCED,
        engine=cde_reduction_engine,
    )
    cde_engine_expr = cde_reduction_engine.calls[0][1]
    cde_index_wildcard = S("cde_backend_loop_index_")
    cde_loop_momentum_matches = tuple(cde_engine_expr.match(vakint_backend.symbol("k")(1, cde_index_wildcard)))
    assert cde_loop_momentum_matches
    cde_index_match = cde_loop_momentum_matches[0]
    cde_safe_index = cde_index_match[cde_index_wildcard]
    assert all(
        "pychete::Index" not in canonical_string(match[cde_index_wildcard])
        for match in cde_loop_momentum_matches
    )
    assert_expr_equal(
        vakint_backend.decode_pychete_namespace(
            theory,
            vakint_backend.symbol("g")(cde_safe_index, cde_safe_index),
        ),
        s.Metric(mu, mu),
    )

    acted_numerator = 2 * Expression.I * s.LoopMomentum(mu) * y() ** 2 * light() * light(derivatives=[mu])
    expected_acted_integral = vakint_backend.one_loop_vacuum_integral(
        acted_numerator,
        (light_mass**2, heavy_mass**2),
        powers=(2, 1),
    )
    assert_expr_equal(
        acted_integrals["interaction_bosonic_cde_vakint_integral[hScalar-lScalar,0]"],
        expected_acted_integral,
    )
    assert acted_result.metadata["stage"] == "interaction_bosonic_cde_vakint_result"
    assert acted_result.metadata["uses_bosonic_cde_expansion"] is True
    assert acted_result.metadata["interaction_bosonic_cde_term_count"] == 1
    assert acted_result.metadata["interaction_bosonic_cde_act_open_derivatives"] is True
    assert_expr_equal(acted_result.off_shell_eft_lagrangian, expected_acted_integral)
    assert_expr_equal(
        acted_result.expression("interaction_bosonic_cde_vakint_integral_sum"),
        expected_acted_integral,
    )

    zero_order_expansion = {"hScalar-lScalar": ((), ())}
    zero_order_integral = setup.interaction_bosonic_cde_vakint_integral_sum(zero_order_expansion)
    internal_result = setup.interaction_bosonic_cde_internal_matching_result(
        zero_order_expansion,
        tensor_reduce=False,
        combine_terms=True,
    )
    expected_internal = vacuum_integrals_backend.evaluate_one_loop_vakint_expression(
        zero_order_integral,
        combine_terms=True,
    )
    assert internal_result.metadata["stage"] == "interaction_bosonic_cde_internal_integral_result"
    assert internal_result.metadata["integral_backend"] == "pychete_internal"
    assert internal_result.metadata["uses_bosonic_cde_expansion"] is True
    assert_expr_equal(internal_result.off_shell_eft_lagrangian, expected_internal)

    matched = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.VAKINT,
            bosonic_cde_expansion_indices_by_trace=expansion,
            bosonic_cde_act_open_derivatives=True,
            truncate_eft_result=False,
        ),
    )
    assert isinstance(matched, MatchingResult)
    assert matched.metadata["stage"] == "interaction_bosonic_cde_hybrid_vakint_result"
    assert matched.metadata["interaction_bosonic_cde_hybrid"] is True
    assert matched.metadata["uses_interaction_power_remainder"] is True
    assert matched.metadata["bosonic_cde_expansion_enabled"] is True
    assert matched.metadata["bosonic_cde_act_open_derivatives"] is True
    assert_expr_equal(matched.off_shell_eft_lagrangian, expected_acted_integral)

    plan = setup.interaction_bosonic_cde_expansion_plan(
        trace_names=("hScalar-lScalar",),
        max_total_order=1,
        index_prefix="pytest_cde",
    )
    assert isinstance(plan, BosonicCDEExpansionPlan)
    assert all(isinstance(entry, BosonicCDEExpansionPlanEntry) for entry in plan)
    assert plan.trace_names == ("hScalar-lScalar",)
    assert tuple(entry.slot_orders for entry in plan.entries) == ((0, 0), (0, 1), (1, 0))
    assert len(plan) == 3
    assert plan.entry_count == 3
    assert plan.trace_count == 1
    assert tuple(plan.by_trace()) == ("hScalar-lScalar",)
    generated_index_label = plan.entries[1].expansion_indices[1][0][0]
    assert any(tag.endswith(f"::{SymbolRole.INDEX.value}") for tag in generated_index_label.get_tags())
    plan_integral_sum = setup.interaction_bosonic_cde_vakint_integral_sum(plan)
    expected_plan_integral_sum = Expression.num(0)
    for entry in plan:
        expected_plan_integral_sum += setup.interaction_bosonic_cde_vakint_integral_sum(entry.as_explicit_map())
    assert_expr_equal(plan_integral_sum, expected_plan_integral_sum.expand())
    plan_integrals = setup.interaction_bosonic_cde_vakint_integral_expression_map(plan)
    assert tuple(plan_integrals) == (
        "interaction_bosonic_cde_vakint_integral[hScalar-lScalar#cde0_o0_0,0]",
        "interaction_bosonic_cde_vakint_integral[hScalar-lScalar#cde1_o0_1,0]",
        "interaction_bosonic_cde_vakint_integral[hScalar-lScalar#cde2_o1_0,0]",
    )
    plan_raw_terms = tuple(plan_integrals.values())
    plan_reduction_engine = FakeKernelVakintEngine()
    plan_reduced_sum = setup.interaction_bosonic_cde_vakint_integral_sum(
        plan,
        stage=VakintIntegralStage.TENSOR_REDUCED,
        engine=plan_reduction_engine,
    )
    expected_plan_reduced_sum = Expression.num(0)
    for raw in plan_raw_terms:
        expected_plan_reduced_sum += S("reduced")(raw)
    expected_plan_reduced_sum = expected_plan_reduced_sum.expand()
    assert [name for name, _expr, _short in plan_reduction_engine.calls] == ["tensor_reduce"] * len(plan_raw_terms)
    assert tuple(expr for _name, expr, _short in plan_reduction_engine.calls) == plan_raw_terms
    assert_expr_equal(plan_reduced_sum, expected_plan_reduced_sum)
    termwise_result_engine = FakeKernelVakintEngine()
    termwise_result = setup.interaction_bosonic_cde_matching_result(
        plan,
        vakint_stage=VakintIntegralStage.TENSOR_REDUCED,
        vakint_engine=termwise_result_engine,
    )
    assert termwise_result.metadata["interaction_bosonic_cde_vakint_termwise_stage"] is True
    assert [name for name, _expr, _short in termwise_result_engine.calls] == ["tensor_reduce"] * len(plan_raw_terms)
    assert_expr_equal(termwise_result.off_shell_eft_lagrangian, expected_plan_reduced_sum)
    planned_match = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.VAKINT,
            bosonic_cde_trace_names=("hScalar-lScalar",),
            bosonic_cde_max_total_order=1,
            bosonic_cde_index_prefix="pytest_cde",
            truncate_eft_result=False,
        ),
    )
    assert isinstance(planned_match, MatchingResult)
    assert planned_match.metadata["bosonic_cde_expansion_enabled"] is True
    assert planned_match.metadata["bosonic_cde_expansion_planned"] is True
    assert planned_match.metadata["interaction_bosonic_cde_hybrid"] is True
    assert planned_match.metadata["interaction_bosonic_cde_trace_count"] == 1
    assert planned_match.metadata["interaction_bosonic_cde_plan_entry_count"] == 3
    assert planned_match.metadata["interaction_bosonic_cde_term_count"] == 3
    assert_expr_equal(planned_match.off_shell_eft_lagrangian, plan_integral_sum)
    with pytest.raises(ValueError, match="one entry per trace block"):
        trace.bosonic_cde_expansion_terms(((mu,),))
    with pytest.raises(KeyError, match="missing"):
        setup.interaction_bosonic_cde_kernel_expression_map({"missing": ((),)})


def test_selected_bosonic_cde_builds_only_requested_interaction_category_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("one_loop_setup_selected_bosonic_cde_blocks")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() ** 3 / 6 - y() * heavy() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=3)
    category_block_calls: list[tuple[str, str]] = []
    original_category_block = matching_module.FluctuationOperator.interaction_category_block

    def fail_full_interaction_block(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("selected CDE trace construction should not build full sector blocks")

    def record_category_block(
        operator: matching_module.FluctuationOperator,
        row_category: str,
        column_category: str,
        **kwargs: object,
    ) -> matching_module.FluctuationOperatorBlock:
        category_block_calls.append((row_category, column_category))
        return original_category_block(operator, row_category, column_category, **kwargs)

    monkeypatch.setattr(matching_module.FluctuationOperator, "interaction_block", fail_full_interaction_block)
    monkeypatch.setattr(matching_module.FluctuationOperator, "interaction_category_block", record_category_block)

    plan = setup.interaction_bosonic_cde_expansion_plan(
        trace_names=("hScalar-hScalar-hScalar",),
        max_total_order=0,
    )

    assert plan.trace_names == ("hScalar-hScalar-hScalar",)
    assert category_block_calls == [("hScalar", "hScalar")]


def test_public_bosonic_cde_matching_projects_scalar_ncm_chains() -> None:
    theory = Theory("one_loop_setup_interaction_bosonic_cde_projection")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = theory.free_lag(heavy) + theory.free_lag(light) - y() * heavy() * light() ** 2 / 2

    result = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            bosonic_cde_trace_names=("hScalar-lScalar",),
            bosonic_cde_max_total_order=0,
            tensor_reduce=False,
            combine_terms=True,
            truncate_eft_result=False,
        ),
        matching_condition_targets={"phi2": light() ** 2},
        matching_condition_expand_source=False,
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["stage"] == "interaction_bosonic_cde_hybrid_internal_integral_result"
    assert result.metadata["interaction_bosonic_cde_hybrid"] is True
    assert result.metadata["matching_conditions_projected"] is True
    assert result.metadata["matching_condition_projection_expand_source"] is False
    assert "pychete::NCM(" not in canonical_string(result.off_shell_eft_lagrangian)
    assert canonical_string(result.matching_conditions["phi2"]) != "0"
    expected_phi2 = result.off_shell_eft_lagrangian.collect_factors().coefficient(light() ** 2).expand()
    assert (result.matching_conditions["phi2"] - expected_phi2).together().format_plain() == "0"


def test_public_bosonic_cde_matching_preserves_unselected_interaction_traces() -> None:
    theory = Theory("one_loop_setup_interaction_bosonic_cde_hybrid")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    kappa = theory.define_coupling("kappa", self_conjugate=True)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(light)
        - kappa() * heavy() ** 3 / 6
        - y() * heavy() * light() ** 2 / 2
    )
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    expansion = {"hScalar-lScalar": ((), ())}
    selected_trace_names = ("hScalar-lScalar",)
    remainder = setup.interaction_power_type_vakint_integral_sum(exclude_trace_names=selected_trace_names)
    cde_replacement = setup.interaction_bosonic_cde_vakint_integral_sum(expansion)

    assert canonical_string(remainder) != "0"
    result = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.VAKINT,
            bosonic_cde_expansion_indices_by_trace=expansion,
            truncate_eft_result=False,
        ),
    )

    assert isinstance(result, MatchingResult)
    assert result.metadata["stage"] == "interaction_bosonic_cde_hybrid_vakint_result"
    assert result.metadata["interaction_bosonic_cde_replaced_trace_names"] == ",".join(selected_trace_names)
    assert result.metadata["interaction_power_type_remainder_contribution_count"] == (
        setup.interaction_power_type_contribution_count - 1
    )
    assert "hScalar-lScalar" not in result.supertraces
    assert "interaction_bosonic_cde_vakint_integral[hScalar-lScalar,0]" in result.supertraces
    assert_expr_equal(result.off_shell_eft_lagrangian, (remainder + cde_replacement).expand())


def test_single_block_bosonic_cde_acts_open_derivatives_cyclically() -> None:
    theory = Theory("one_loop_setup_single_block_cyclic_cde")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    vector = theory.field_handle("W")
    kappa = theory.define_coupling("kappa", self_conjugate=True)
    i = theory.dummy_index(1, fund)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(higgs)
        + theory.free_lag(vector)
        - kappa() * heavy() ** 2 * s.Bar(higgs(i)) * higgs(i) / 2
    )
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=1)
    b = theory.index("b")
    c = theory.index("c")
    expansion = {"hScalar": ((b, c),)}

    raw_terms = setup.interaction_bosonic_cde_expansion_terms(expansion)
    acted_terms = setup.interaction_bosonic_cde_expansion_terms(expansion, act_open_derivatives=True)
    lowered_terms = setup.interaction_bosonic_cde_expansion_terms(
        expansion,
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=True,
        emit_covariant_derivative_commutator_passes=2,
        expand_covariant_derivative_commutators=True,
    )

    assert len(raw_terms) == len(acted_terms) == len(lowered_terms) == 2
    assert any("OpenCD" in canonical_string(term.numerator) for term in raw_terms)
    assert all("OpenCD" not in canonical_string(term.numerator) for term in acted_terms)
    assert any("FieldStrength" in canonical_string(term.numerator) for term in lowered_terms)
    assert any("cg_tensor_gen_SU2L_fund" in canonical_string(term.numerator) for term in lowered_terms)


def test_bosonic_cde_internal_tensor_reduction_decodes_native_vakint_tensors() -> None:
    theory = Theory("one_loop_setup_bosonic_cde_decode_vakint_tensors")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    vector = theory.field_handle("W")
    kappa = theory.define_coupling("kappa", self_conjugate=True)
    i = theory.dummy_index(1, fund)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(higgs)
        + theory.free_lag(vector)
        - kappa() * heavy() ** 2 * s.Bar(higgs(i)) * higgs(i) / 2
    )
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=1)
    result = setup.interaction_bosonic_cde_hybrid_internal_matching_result(
        {"hScalar": ((theory.index("b"), theory.index("c")),)},
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=True,
        emit_covariant_derivative_commutator_passes=2,
        expand_covariant_derivative_commutators=True,
        tensor_reduce=True,
        combine_terms=False,
    )
    rendered = canonical_string(result.off_shell_eft_lagrangian)

    assert result.metadata["stage"] == "interaction_bosonic_cde_hybrid_internal_integral_result"
    assert "vakint::g" not in rendered
    assert "vakint::CG" not in rendered
    assert "pychete::Metric" in rendered
    assert "pychete::CG" in rendered
    assert "pychete::FieldStrength" in rendered


def test_public_bosonic_cde_simplifies_metric_traced_field_strengths() -> None:
    theory = Theory("one_loop_setup_bosonic_cde_simplify_field_strength_metrics")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    vector = theory.field_handle("W")
    kappa = theory.define_coupling("kappa", self_conjugate=True)
    i = theory.dummy_index(1, fund)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(higgs)
        + theory.free_lag(vector)
        - kappa() * heavy() ** 2 * s.Bar(higgs(i)) * higgs(i) / 2
    )
    result = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            max_trace_order=1,
            bosonic_cde_expansion_indices_by_trace={
                "hScalar": ((theory.index("b"), theory.index("c")),),
            },
            bosonic_cde_act_open_derivatives=True,
            bosonic_cde_emit_covariant_derivative_commutators=True,
            bosonic_cde_emit_covariant_derivative_commutator_passes=2,
            bosonic_cde_expand_covariant_derivative_commutators=True,
            tensor_reduce=True,
            combine_terms=False,
            truncate_eft_result=False,
        ),
    )
    rendered = canonical_string(result.on_shell_eft_lagrangian)

    assert result.metadata["field_strength_metric_simplified"] is True
    assert "pychete::FieldStrength" not in rendered
    assert "vakint::g" not in rendered
    assert "vakint::CG" not in rendered


def test_public_bosonic_cde_decodes_order_four_covariant_derivatives() -> None:
    theory = Theory("one_loop_setup_bosonic_cde_decode_order_four_cd")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    fund = theory.define_representation("SU2L", "fund")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    higgs = theory.define_field(
        "H",
        s.Scalar,
        indices=[fund],
        charges=[theory.group_charge("U1Y", Expression.num(1) / Expression.num(2))],
        self_conjugate=False,
        mass=0,
    )
    vector = theory.field_handle("W")
    kappa = theory.define_coupling("kappa", self_conjugate=True)
    wilson_handles = {
        name: define_smeft_wilson_coefficient(theory, name)
        for name in ("cHW", "cHB", "cHWB")
    }
    i = theory.dummy_index(1, fund)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(higgs)
        + theory.free_lag(vector)
        + theory.free_lag(theory.field_handle("B"))
        - kappa() * heavy() ** 2 * s.Bar(higgs(i)) * higgs(i) / 2
    )
    result = theory.match(
        lagrangian,
        loop_order=1,
        matching_condition_targets="registered_wilsons",
        matching_condition_expand_source=False,
        matching_condition_truncate_eft=True,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            max_trace_order=1,
            bosonic_cde_trace_names=("hScalar",),
            bosonic_cde_max_total_order=4,
            bosonic_cde_max_slot_order=4,
            bosonic_cde_act_open_derivatives=True,
            bosonic_cde_emit_covariant_derivative_commutators=True,
            bosonic_cde_emit_covariant_derivative_commutator_passes=4,
            bosonic_cde_expand_covariant_derivative_commutators=True,
            tensor_reduce=True,
            combine_terms=False,
            truncate_eft_result=False,
            simplify_pychete_color_algebra=True,
        ),
    )
    rendered = canonical_string(result.on_shell_eft_lagrangian)

    assert result.metadata["field_strength_metric_simplified"] is True
    assert result.metadata["native_color_wrappers_decoded"] is True
    assert result.metadata["su2_field_strength_generator_bilinears_simplified"] is True
    assert result.metadata["su2_u1_field_strength_generator_bilinears_simplified"] is True
    assert result.metadata["matching_conditions_projected"] is True
    assert "vakint::CD" not in rendered
    assert "vakint::List" not in rendered
    assert "vakint::𝑖" not in rendered
    assert "spenso::" not in rendered
    assert "pychete::CD" in rendered
    assert "pychete::FieldStrength" in rendered
    expected_targets = {
        name: canonical_string(s.Coupling(handle.label, s.List(), Expression.num(0)))
        for name, handle in wilson_handles.items()
    }
    assert set(result.matching_conditions) == set(expected_targets.values())
    for target in expected_targets.values():
        assert not bool(result.matching_conditions[target].expand() == Expression.num(0))


def test_public_bosonic_cde_can_filter_terms_by_matching_targets() -> None:
    theory = Theory("one_loop_setup_bosonic_cde_filter_targets")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    fund = theory.define_representation("SU2L", "fund")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    higgs = theory.define_field(
        "H",
        s.Scalar,
        indices=[fund],
        charges=[theory.group_charge("U1Y", Expression.num(1) / Expression.num(2))],
        self_conjugate=False,
        mass=0,
    )
    vector = theory.field_handle("W")
    kappa = theory.define_coupling("kappa", self_conjugate=True)
    wilson = define_smeft_wilson_coefficient(theory, "cHW")
    i = theory.dummy_index(1, fund)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(higgs)
        + theory.free_lag(vector)
        + theory.free_lag(theory.field_handle("B"))
        - kappa() * heavy() ** 2 * s.Bar(higgs(i)) * higgs(i) / 2
    )
    common_options = dict(
        integral_backend=OneLoopIntegralBackend.INTERNAL,
        max_trace_order=1,
        bosonic_cde_trace_names=("hScalar",),
        bosonic_cde_max_total_order=4,
        bosonic_cde_max_slot_order=4,
        bosonic_cde_act_open_derivatives=True,
        bosonic_cde_emit_covariant_derivative_commutators=True,
        bosonic_cde_emit_covariant_derivative_commutator_passes=4,
        bosonic_cde_expand_covariant_derivative_commutators=True,
        tensor_reduce=True,
        combine_terms=False,
        truncate_eft_result=False,
        simplify_pychete_color_algebra=True,
    )
    unfiltered = theory.match(
        lagrangian,
        loop_order=1,
        matching_condition_targets="registered_wilsons",
        matching_condition_expand_source=False,
        matching_condition_truncate_eft=True,
        one_loop_options=OneLoopMatchOptions(**common_options),
    )
    filtered = theory.match(
        lagrangian,
        loop_order=1,
        matching_condition_targets="registered_wilsons",
        matching_condition_expand_source=False,
        matching_condition_truncate_eft=True,
        one_loop_options=OneLoopMatchOptions(
            **common_options,
            bosonic_cde_filter_terms_by_matching_targets=True,
        ),
    )
    target = canonical_string(s.Coupling(wilson.label, s.List(), Expression.num(0)))

    assert unfiltered.metadata["bosonic_cde_terms_filtered_by_matching_targets"] is False
    assert filtered.metadata["bosonic_cde_terms_filtered_by_matching_targets"] is True
    assert unfiltered.metadata["interaction_bosonic_cde_term_count"] == 12
    assert filtered.metadata["interaction_bosonic_cde_term_count"] == 8
    assert set(filtered.matching_conditions) == {target}
    assert not bool(filtered.matching_conditions[target].expand() == Expression.num(0))


def test_projection_atom_filter_counts_powered_field_strength_targets() -> None:
    theory = Theory("one_loop_setup_bosonic_cde_filter_field_strength_powers")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    target = smeft_warsaw_operator(theory, "cHW")
    assert target is not None
    w_label = canonical_string(theory.field_handle("W").label)
    requirement_groups = matching_results_module._projection_atom_requirement_groups_for_expressions((target,))

    assert ("field_strength", w_label, 2) in requirement_groups[0]

    coefficient_one = S("field_strength_power_filter_one")
    coefficient_two = S("field_strength_power_filter_two")
    i = theory.dummy_index(1, fund)
    adjoint = theory.index("A", theory.symbol("SU2L", role=SymbolRole.GROUP)(s.adj))
    mu = theory.index("mu")
    nu = theory.index("nu")
    higgs_bilinear = s.Bar(higgs(i)) * higgs(i)
    strength = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adjoint), s.List())
    source = coefficient_one * higgs_bilinear * strength + coefficient_two * higgs_bilinear * strength**2
    filtered = matching_results_module._ProjectionCoefficientExtractor(source)._filtered_source(target)
    rendered = canonical_string(filtered)

    compact_strength_power = matching_results_module._expand_indexed_projection_atom_powers(
        strength**2,
        include_field_strength=False,
    )

    assert_expr_equal(compact_strength_power, strength**2)
    assert matching_results_module._projection_atom_counts(strength**2)[("field_strength", w_label)] == 2
    assert "field_strength_power_filter_one" not in rendered
    assert "field_strength_power_filter_two" in rendered


def test_matching_projection_handles_compact_alpha_equivalent_field_strength_powers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("one_loop_setup_bosonic_cde_project_compact_field_strength_powers")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    target = smeft_warsaw_operator(theory, "cHW")
    assert target is not None
    coefficient = S("compact_field_strength_power_projection_coefficient")
    source_higgs_index = theory.index("source_higgs", fund)
    source_adjoint = theory.index(
        "source_adjoint",
        theory.symbol("SU2L", role=SymbolRole.GROUP)(s.adj),
    )
    source_mu = theory.index("source_mu")
    source_nu = theory.index("source_nu")
    source_operator = (
        s.Bar(higgs(source_higgs_index))
        * higgs(source_higgs_index)
        * s.FieldStrength(
            theory.field_handle("W").label,
            s.List(source_mu, source_nu),
            s.List(source_adjoint),
            s.List(),
        )
        ** 2
        / theory.coupling_handle("gL")() ** 2
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    def fail_canonize_tensor_terms(
        expr: Expression,
        index_specs: Sequence[tuple[Expression, Expression]],
    ) -> Expression:
        raise AssertionError("wildcard projection should handle compact field-strength powers")

    monkeypatch.setattr(matching_results_module, "_canonize_tensor_terms", fail_canonize_tensor_terms)

    projected = result.project_matching_conditions({"cHW": target}, expand_source=False)

    assert_expr_equal(projected["cHW"], coefficient)


def test_matching_projection_normalizes_field_strength_target_denominators_before_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("one_loop_setup_bosonic_cde_project_field_strength_denominator")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    target = smeft_warsaw_operator(theory, "cHW")
    assert target is not None
    coefficient = S("field_strength_denominator_projection_coefficient")
    source_higgs_index = theory.index("source_higgs", fund)
    source_adjoint = theory.index("source_adjoint", theory.symbol("SU2L", role=SymbolRole.GROUP)(s.adj))
    source_mu = theory.index("source_mu")
    source_nu = theory.index("source_nu")
    source_operator = (
        s.Bar(higgs(source_higgs_index))
        * higgs(source_higgs_index)
        * s.FieldStrength(
            theory.field_handle("W").label,
            s.List(source_mu, source_nu),
            s.List(source_adjoint),
            s.List(),
        )
        ** 2
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    def fail_collected_source(*_args: object, **_kwargs: object) -> Expression:
        raise AssertionError("field-strength denominator projection should not collect source")

    def fail_factored_source(*_args: object, **_kwargs: object) -> Expression:
        raise AssertionError("field-strength denominator projection should not factor source")

    monkeypatch.setattr(
        matching_results_module._ProjectionCoefficientExtractor,
        "_collected_source",
        fail_collected_source,
    )
    monkeypatch.setattr(
        matching_results_module._ProjectionCoefficientExtractor,
        "_factored_source",
        fail_factored_source,
    )

    projected = result.project_matching_conditions({"cHW": target}, expand_source=False)

    assert_expr_equal(projected["cHW"], coefficient * theory.coupling_handle("gL")() ** 2)


def test_matching_projection_normalizes_negative_powers_in_canonized_exact_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("one_loop_setup_project_canonized_negative_power")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    target = smeft_warsaw_operator(theory, "cHW")
    assert target is not None
    coefficient = S("canonized_negative_power_projection_coefficient")
    source_higgs_index = theory.index("source_higgs", fund)
    source_adjoint = theory.index("source_adjoint", adj)
    source_mu = theory.index("source_mu")
    source_nu = theory.index("source_nu")
    source_operator = (
        s.Bar(higgs(source_higgs_index))
        * higgs(source_higgs_index)
        * s.FieldStrength(
            theory.field_handle("W").label,
            s.List(source_mu, source_nu),
            s.List(source_adjoint),
            s.List(),
        )
        ** 2
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    def disable_target_local_wildcard(*_args: object, **_kwargs: object) -> Expression | None:
        return None

    def fail_generic_projection(*_args: object, **_kwargs: object) -> Expression:
        raise AssertionError("canonized exact projection should handle negative target powers")

    monkeypatch.setattr(
        matching_results_module,
        "_target_local_wildcard_projection_coefficient",
        disable_target_local_wildcard,
    )
    monkeypatch.setattr(
        matching_results_module,
        "_source_is_small_enough_for_generic_projection",
        lambda _source: False,
    )
    monkeypatch.setattr(matching_results_module, "_matching_projection_coefficient", fail_generic_projection)

    projected = result.project_matching_conditions({"cHW": target}, expand_source=False)

    assert_expr_equal(projected["cHW"], coefficient * theory.coupling_handle("gL")() ** 2)


def test_matching_projection_simplifies_target_local_field_strength_group_structures() -> None:
    theory = Theory("one_loop_setup_project_field_strength_group_local")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    target = smeft_warsaw_operator(theory, "cHW")
    assert target is not None
    coefficient = S("field_strength_group_projection_coefficient")
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    higgs_left = theory.index("higgs_left", fund)
    higgs_right = theory.index("higgs_right", fund)
    internal_left = theory.index("internal_left", fund)
    internal_right = theory.index("internal_right", fund)
    internal_left_dual = theory.index("internal_left", s.Bar(fund))
    internal_right_dual = theory.index("internal_right", s.Bar(fund))
    higgs_right_dual = theory.index("higgs_right", s.Bar(fund))
    adjoint_left = theory.index("adjoint_left", adj)
    adjoint_right = theory.index("adjoint_right", adj)
    metric_left = s.Index(S(f"{theory.name}::index_wilson_line_projection_left"), s.Lorentz)
    metric_right = s.Index(S(f"{theory.name}::index_wilson_line_projection_right"), s.Lorentz)
    shared_lorentz = s.Index(S("pychete::wilson_line_projection_shared"), s.Lorentz)
    left_strength = s.FieldStrength(
        theory.field_handle("W").label,
        s.List(shared_lorentz, metric_right),
        s.List(adjoint_left),
        s.List(),
    )
    right_strength = s.FieldStrength(
        theory.field_handle("W").label,
        s.List(shared_lorentz, metric_left),
        s.List(adjoint_right),
        s.List(),
    )
    source_operator = (
        higgs(higgs_left)
        * s.Bar(higgs(higgs_right))
        * s.Delta(internal_left, internal_right_dual)
        * generator(adjoint_left, higgs_left, internal_left_dual)
        * generator(adjoint_right, internal_right, higgs_right_dual)
        * s.Metric(metric_left, metric_right)
        * left_strength
        * right_strength
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    projected = result.project_matching_conditions({"cHW": target}, expand_source=False)

    assert_expr_equal(
        projected["cHW"],
        coefficient * theory.coupling_handle("gL")() ** 2 / Expression.num(4),
    )


def test_public_bosonic_cde_projects_two_insertion_higgs_derivative_operator() -> None:
    theory = Theory("one_loop_setup_bosonic_cde_projects_chd")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    kappa = theory.define_coupling("kappa", self_conjugate=True)
    wilson = define_smeft_wilson_coefficient(theory, "cHD")
    i = theory.dummy_index(1, fund)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(higgs)
        - kappa() * heavy() ** 2 * s.Bar(higgs(i)) * higgs(i) / 2
    )
    result = theory.match(
        lagrangian,
        loop_order=1,
        matching_condition_targets="registered_wilsons",
        matching_condition_expand_source=False,
        matching_condition_truncate_eft=True,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            max_trace_order=2,
            bosonic_cde_trace_names=("hScalar-hScalar",),
            bosonic_cde_max_total_order=2,
            bosonic_cde_max_slot_order=2,
            bosonic_cde_act_open_derivatives=True,
            tensor_reduce=True,
            combine_terms=False,
            truncate_eft_result=False,
        ),
    )
    target = canonical_string(s.Coupling(wilson.label, s.List(), Expression.num(0)))

    assert result.metadata["interaction_bosonic_cde_internal_termwise_evaluation"] is True
    assert result.metadata["matching_conditions_projected"] is True
    assert set(result.matching_conditions) == {target}
    assert not bool(result.matching_conditions[target].expand() == Expression.num(0))


def test_public_bosonic_cde_projects_three_insertion_higgs_potential_operator() -> None:
    theory = Theory("one_loop_setup_bosonic_cde_projects_ch")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    kappa = theory.define_coupling("kappa", self_conjugate=True)
    wilson = define_smeft_wilson_coefficient(theory, "cH")
    i = theory.dummy_index(1, fund)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(higgs)
        - kappa() * heavy() ** 2 * s.Bar(higgs(i)) * higgs(i) / 2
    )
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=3)
    terms = setup.interaction_bosonic_cde_expansion_terms({"hScalar-hScalar-hScalar": ((), (), ())})

    assert len(terms) == 1
    assert len({canonical_string(index.label) for index in dummy_indices(terms[0].numerator)}) == 3

    result = theory.match(
        lagrangian,
        loop_order=1,
        matching_condition_targets="registered_wilsons",
        matching_condition_expand_source=False,
        matching_condition_truncate_eft=True,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL,
            max_trace_order=3,
            bosonic_cde_trace_names=("hScalar-hScalar-hScalar",),
            bosonic_cde_max_total_order=0,
            bosonic_cde_max_slot_order=0,
            bosonic_cde_act_open_derivatives=True,
            tensor_reduce=True,
            combine_terms=False,
            truncate_eft_result=False,
        ),
    )
    target = canonical_string(s.Coupling(wilson.label, s.List(), Expression.num(0)))

    assert result.metadata["interaction_bosonic_cde_internal_termwise_evaluation"] is True
    assert result.metadata["matching_conditions_projected"] is True
    assert result.metadata["matching_condition_projection_canonize_indices"] is True
    assert set(result.matching_conditions) == {target}
    assert not bool(result.matching_conditions[target].expand() == Expression.num(0))


@pytest.mark.slow
def test_public_bosonic_cde_heavy_solution_projects_ch_muphi_component() -> None:
    theory = Theory("one_loop_setup_bosonic_cde_heavy_solution_projects_ch")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    heavy = theory.define_field("S", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    source = theory.define_coupling("A", self_conjugate=True)
    kappa = theory.define_coupling("kappa", self_conjugate=True)
    muphi = theory.define_coupling("muphi", self_conjugate=True)
    hbar = theory.define_external("hbar")
    wilson = define_smeft_wilson_coefficient(theory, "cH")
    i = theory.dummy_index(1, fund)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(higgs)
        - source() * heavy() * s.Bar(higgs(i)) * higgs(i)
        - kappa() * heavy() ** 2 * s.Bar(higgs(i)) * higgs(i) / 2
        - muphi() * heavy() ** 3 / 6
    )
    target = canonical_string(s.Coupling(wilson.label, s.List(), Expression.num(0)))

    result = theory.match(
        lagrangian,
        loop_order=1,
        matching_condition_targets="registered_wilsons",
        matching_condition_expand_source=False,
        matching_condition_truncate_eft=True,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
            normalization=OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
            hbar=hbar(),
            max_trace_order=3,
            bosonic_cde_trace_names=("hScalar-hScalar-hScalar",),
            bosonic_cde_max_total_order=0,
            bosonic_cde_max_slot_order=0,
            tensor_reduce=True,
            combine_terms=False,
            truncate_eft_result=False,
            substitute_heavy_scalar_solutions=True,
        ),
    )
    coefficient = result.matching_conditions[target].coefficient(
        hbar() * source() * kappa() ** 2 * muphi()
    ).expand()

    assert result.metadata["heavy_scalar_solutions_substituted"] is True
    assert result.metadata["matching_condition_projection_canonize_indices"] is True
    assert_expr_equal(coefficient, -Expression.num(1) / (4 * theory.coupling_handle("M")() ** 4))


def test_planned_bosonic_cde_can_emit_and_lower_covariant_derivative_commutators() -> None:
    theory = Theory("one_loop_setup_interaction_bosonic_cde_commutator")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field(
        "phi",
        s.Scalar,
        charges=[theory.group_charge("U1Y", 1)],
        self_conjugate=False,
        mass=(FieldMassKind.LIGHT, "m"),
    )
    vector = theory.field_handle("B")
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = (
        theory.free_lag(heavy)
        + theory.free_lag(light)
        + theory.free_lag(vector)
        - y() * heavy() * s.Bar(light()) * light()
    )
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    b = theory.index("b")
    c = theory.index("c")
    expansion = {"hScalar-lScalar": ((b, c), ())}

    base_terms = setup.interaction_bosonic_cde_expansion_terms(
        expansion,
        act_open_derivatives=True,
    )
    emitted_terms = setup.interaction_bosonic_cde_expansion_terms(
        expansion,
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=True,
    )
    lowered_terms = setup.interaction_bosonic_cde_expansion_terms(
        expansion,
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=True,
        expand_covariant_derivative_commutators=True,
    )

    assert len(base_terms) == len(emitted_terms) == len(lowered_terms) == 4
    for base, emitted, lowered in zip(base_terms, emitted_terms, lowered_terms, strict=True):
        assert_expr_equal(
            emitted.numerator,
            theory.emit_covariant_derivative_commutators(base.numerator),
        )
        assert_expr_equal(
            lowered.numerator,
            theory.expand_covariant_derivative_commutators(
                emitted.numerator,
                include_gauge_coupling=False,
            ),
        )
    assert any("CovariantDerivativeCommutator" in canonical_string(term.numerator) for term in emitted_terms)
    assert all("CovariantDerivativeCommutator" not in canonical_string(term.numerator) for term in lowered_terms)

    planned_match = theory.match(
        lagrangian,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            integral_backend=OneLoopIntegralBackend.VAKINT,
            bosonic_cde_trace_names=("hScalar-lScalar",),
            bosonic_cde_max_total_order=2,
            bosonic_cde_max_slot_order=2,
            bosonic_cde_act_open_derivatives=True,
            bosonic_cde_emit_covariant_derivative_commutators=True,
            bosonic_cde_emit_covariant_derivative_commutator_passes=2,
            bosonic_cde_expand_covariant_derivative_commutators=True,
            truncate_eft_result=False,
        ),
    )
    assert planned_match.metadata["bosonic_cde_expansion_planned"] is True
    assert planned_match.metadata["bosonic_cde_commutators_emitted"] is True
    assert planned_match.metadata["bosonic_cde_commutator_emit_passes"] == 2
    assert planned_match.metadata["bosonic_cde_commutators_expanded"] is True
    assert planned_match.metadata["interaction_bosonic_cde_commutators_emitted"] is True
    assert planned_match.metadata["interaction_bosonic_cde_commutators_expanded"] is True


def test_one_loop_setup_extracts_evaluated_vakint_poles_with_symbolica_coefficients() -> None:
    theory = Theory("one_loop_setup_poles")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    y = theory.define_coupling("y", self_conjugate=True)
    heavy_mass = theory.mass_expr(heavy.definition)
    assert heavy_mass is not None
    lagrangian = theory.free_lag(heavy) - y() * heavy() ** 3 / 6
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    expected_raw = setup.power_type_vakint_integral_sum()
    expected_interaction_raw = setup.interaction_power_type_vakint_integral_sum()
    eps = vakint_backend.epsilon_symbol()
    evaluated_series = S("double") / eps**2 + S("single") / eps + S("finite") + S("higher") * eps

    coefficient_engine = FakePoleVakintEngine(evaluated_series)
    pole_coefficient = setup.power_type_vakint_epsilon_coefficient(-1, engine=coefficient_engine)
    assert coefficient_engine.calls == [("evaluate", expected_raw)]
    assert_expr_equal(pole_coefficient, S("single"))

    pole_engine = FakePoleVakintEngine(evaluated_series)
    assert_expr_equal(
        setup.power_type_vakint_pole_part(engine=pole_engine, max_pole_order=2),
        S("double") / eps**2 + S("single") / eps,
    )
    assert pole_engine.calls == [("evaluate", expected_raw)]

    finite_engine = FakePoleVakintEngine(evaluated_series)
    assert_expr_equal(setup.power_type_vakint_finite_part(engine=finite_engine), S("finite"))
    assert finite_engine.calls == [("evaluate", expected_raw)]

    result_engine = FakePoleVakintEngine(evaluated_series)
    result = setup.power_type_matching_result(
        vakint_stage=VakintIntegralStage.EVALUATED,
        vakint_engine=result_engine,
        max_pole_order=2,
    )
    assert result_engine.calls == [("evaluate", expected_raw)]
    assert result.metadata["vakint_stage"] == "evaluated"
    assert_expr_equal(result.off_shell_eft_lagrangian, evaluated_series)
    assert_expr_equal(result.expression("power_type_vakint_pole_part"), S("double") / eps**2 + S("single") / eps)
    assert_expr_equal(result.expression("power_type_vakint_finite_part"), S("finite"))

    subtraction_engine = FakePoleVakintEngine(evaluated_series)
    subtracted = setup.power_type_minimal_subtraction_result(
        vakint_engine=subtraction_engine,
        max_pole_order=2,
    )
    assert subtraction_engine.calls == [("evaluate", expected_raw)]
    assert subtracted.metadata["stage"] == "power_type_minimal_subtraction_result"
    assert subtracted.metadata["complete"] is False
    assert subtracted.metadata["subtraction_scheme"] == "minimal_subtraction_preview"
    assert subtracted.metadata["poles_subtracted"] is True
    assert subtracted.metadata["max_pole_order"] == 2
    assert_expr_equal(subtracted.off_shell_eft_lagrangian, S("finite"))
    assert_expr_equal(subtracted.on_shell_eft_lagrangian, S("finite"))
    assert_expr_equal(subtracted.expression("power_type_vakint_pole_part"), S("double") / eps**2 + S("single") / eps)
    assert_expr_equal(subtracted.expression("power_type_vakint_ms_counterterm"), -S("double") / eps**2 - S("single") / eps)
    assert_expr_equal(subtracted.expression("power_type_vakint_finite_part"), S("finite"))

    interaction_coefficient_engine = FakePoleVakintEngine(evaluated_series)
    interaction_pole_coefficient = setup.interaction_power_type_vakint_epsilon_coefficient(
        -1,
        engine=interaction_coefficient_engine,
    )
    assert interaction_coefficient_engine.calls == [("evaluate", expected_interaction_raw)]
    assert_expr_equal(interaction_pole_coefficient, S("single"))

    interaction_pole_engine = FakePoleVakintEngine(evaluated_series)
    assert_expr_equal(
        setup.interaction_power_type_vakint_pole_part(engine=interaction_pole_engine, max_pole_order=2),
        S("double") / eps**2 + S("single") / eps,
    )
    assert interaction_pole_engine.calls == [("evaluate", expected_interaction_raw)]

    interaction_finite_engine = FakePoleVakintEngine(evaluated_series)
    assert_expr_equal(setup.interaction_power_type_vakint_finite_part(engine=interaction_finite_engine), S("finite"))
    assert interaction_finite_engine.calls == [("evaluate", expected_interaction_raw)]

    interaction_result_engine = FakePoleVakintEngine(evaluated_series)
    interaction_result = setup.interaction_power_type_matching_result(
        vakint_stage=VakintIntegralStage.EVALUATED,
        vakint_engine=interaction_result_engine,
        max_pole_order=2,
    )
    assert interaction_result_engine.calls == [("evaluate", expected_interaction_raw)]
    assert interaction_result.metadata["vakint_stage"] == "evaluated"
    assert interaction_result.metadata["uses_interaction_operator"] is True
    assert_expr_equal(interaction_result.off_shell_eft_lagrangian, evaluated_series)
    assert_expr_equal(
        interaction_result.expression("interaction_power_type_vakint_pole_part"),
        S("double") / eps**2 + S("single") / eps,
    )
    assert_expr_equal(interaction_result.expression("interaction_power_type_vakint_finite_part"), S("finite"))

    interaction_subtraction_engine = FakePoleVakintEngine(evaluated_series)
    interaction_subtracted = setup.interaction_power_type_minimal_subtraction_result(
        vakint_engine=interaction_subtraction_engine,
        max_pole_order=2,
    )
    assert interaction_subtraction_engine.calls == [("evaluate", expected_interaction_raw)]
    assert interaction_subtracted.metadata["stage"] == "interaction_power_type_minimal_subtraction_result"
    assert interaction_subtracted.metadata["complete"] is False
    assert interaction_subtracted.metadata["subtraction_scheme"] == "minimal_subtraction_preview"
    assert interaction_subtracted.metadata["poles_subtracted"] is True
    assert interaction_subtracted.metadata["uses_interaction_operator"] is True
    assert interaction_subtracted.metadata["max_pole_order"] == 2
    assert_expr_equal(interaction_subtracted.off_shell_eft_lagrangian, S("finite"))
    assert_expr_equal(interaction_subtracted.on_shell_eft_lagrangian, S("finite"))
    assert_expr_equal(
        interaction_subtracted.expression("interaction_power_type_vakint_pole_part"),
        S("double") / eps**2 + S("single") / eps,
    )
    assert_expr_equal(
        interaction_subtracted.expression("interaction_power_type_vakint_ms_counterterm"),
        -S("double") / eps**2 - S("single") / eps,
    )
    assert_expr_equal(interaction_subtracted.expression("interaction_power_type_vakint_finite_part"), S("finite"))

    normalized_result_engine = FakePoleVakintEngine(evaluated_series)
    loop_factor = one_loop_normalization_factor(OneLoopNormalization.MATCHETE_LOOP_FACTOR)
    normalized_evaluated = setup.interaction_power_type_normalized_matching_result(
        vakint_stage=VakintIntegralStage.EVALUATED,
        vakint_engine=normalized_result_engine,
        max_pole_order=2,
        normalization=OneLoopNormalization.MATCHETE_LOOP_FACTOR,
    )
    assert normalized_result_engine.calls == [("evaluate", expected_interaction_raw)]
    assert normalized_evaluated.metadata["stage"] == "interaction_power_type_normalized_vakint_result"
    assert normalized_evaluated.metadata["loop_normalization"] == "matchete_loop_factor"
    assert_expr_equal(normalized_evaluated.off_shell_eft_lagrangian, loop_factor * evaluated_series)
    assert_expr_equal(
        normalized_evaluated.expression("interaction_power_type_normalized_vakint_pole_part"),
        loop_factor * (S("double") / eps**2 + S("single") / eps),
    )
    assert_expr_equal(normalized_evaluated.expression("interaction_power_type_normalized_vakint_finite_part"), loop_factor * S("finite"))


def test_one_loop_setup_can_evaluate_single_scale_integrals_internally() -> None:
    theory = Theory("one_loop_setup_internal_integrals")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = theory.free_lag(heavy) - y() * heavy() ** 3 / 6
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)

    raw_power = setup.power_type_vakint_integral_sum()
    raw_interaction = setup.interaction_power_type_vakint_integral_sum()
    assert_expr_equal(
        setup.power_type_internal_integral_sum(tensor_reduce=False),
        vacuum_integrals_backend.evaluate_one_loop_single_scale_vakint_expression(raw_power),
    )
    assert_expr_equal(
        setup.interaction_power_type_internal_integral_sum(tensor_reduce=False),
        vacuum_integrals_backend.evaluate_one_loop_single_scale_vakint_expression(raw_interaction),
    )
    assert_expr_equal(
        setup.interaction_power_type_internal_integral_sum(tensor_reduce=False, combine_terms=True),
        vacuum_integrals_backend.evaluate_one_loop_single_scale_vakint_expression(
            raw_interaction,
            combine_terms=True,
        ),
    )

    tensor_reduce_engine = FakeKernelVakintEngine()
    assert_expr_equal(
        setup.interaction_power_type_internal_integral_sum(tensor_reduce_engine=tensor_reduce_engine),
        vacuum_integrals_backend.evaluate_one_loop_single_scale_vakint_expression(S("reduced")(raw_interaction)),
    )
    assert tensor_reduce_engine.calls == [("tensor_reduce", raw_interaction, None)]


def test_one_loop_internal_integral_evaluation_absorbs_tensor_reduced_scalar_loop_momentum() -> None:
    theory = Theory("one_loop_setup_internal_scalar_loop_momentum")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = theory.free_lag(heavy) - y() * heavy() ** 3 / 6
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    raw_interaction = setup.interaction_power_type_vakint_integral_sum()
    tensor_reduce_engine = FakeScalarLoopMomentumVakintEngine()

    result = setup.interaction_power_type_internal_integral_sum(tensor_reduce_engine=tensor_reduce_engine)

    assert tensor_reduce_engine.calls == [("tensor_reduce", raw_interaction, None)]
    assert "vakint::k(" not in canonical_string(result)


def test_one_loop_setup_simplifies_generated_kernels_through_idenso(monkeypatch: pytest.MonkeyPatch) -> None:
    theory = Theory("one_loop_setup_idenso")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = heavy() ** 2 + light() ** 2 - y() * heavy() * light() ** 2 / 2
    calls: list[tuple[Expression, bool, bool, bool, bool, bool]] = []

    def fake_simplify_index_algebra(
        expr: Expression,
        *,
        expand: bool = True,
        gamma: bool = True,
        color: bool = True,
        metrics: bool = True,
        dots: bool = False,
    ) -> Expression:
        calls.append((expr, expand, gamma, color, metrics, dots))
        return (expr + 1).expand()

    monkeypatch.setattr(idenso_backend, "simplify_index_algebra", fake_simplify_index_algebra)

    setup = theory.one_loop_setup(lagrangian, max_trace_order=1)
    simplified = setup.simplify_index_algebra(expand=False, dots=True)

    assert simplified is not setup
    assert simplified.fluctuation_operator is setup.fluctuation_operator
    assert simplified.supertrace_plan is setup.supertrace_plan
    assert tuple(trace.name for trace in simplified.block_traces) == tuple(trace.name for trace in setup.block_traces)
    assert len(calls) == setup.supertrace_kernel_count
    assert calls[0][1:] == (False, True, True, True, True)
    for original, simplified_trace in zip(setup.block_traces, simplified.block_traces, strict=True):
        assert_expr_equal(simplified_trace.expression, original.expression + 1)


def test_supertrace_block_trace_contracts_loop_momentum_metrics_through_idenso_bridge() -> None:
    theory = Theory("one_loop_setup_loop_momentum_metrics")
    mu = s.Index(s.dummy_index(0), s.Lorentz)
    nu = s.Index(s.dummy_index(1), s.Lorentz)
    trace = SupertraceBlockTrace(
        theory=theory,
        name="metric_q_q",
        blocks=(),
        modes=(),
        expression=S("x") * s.Metric(mu, nu) * s.LoopMomentum(mu) * s.LoopMomentum(nu),
    )

    simplified = trace.simplify_index_algebra(expand=False, gamma=False, color=False, dots=False)

    assert_expr_equal(simplified.expression, S("x") * s.LoopMomentumSquared)


def test_supertrace_block_trace_can_simplify_pychete_color_cg_tensors() -> None:
    theory = Theory("one_loop_setup_pychete_color")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    delta_adj = theory.cg_tensor_handle("del_SU2L_adj")
    adj_a = theory.index("A", adj)
    adj_b = theory.index("B", adj)
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    i_dual = theory.index("i", s.Bar(fund))
    j_dual = theory.index("j", s.Bar(fund))
    trace = SupertraceBlockTrace(
        theory=theory,
        name="su2_generator_trace",
        blocks=(),
        modes=(),
        expression=generator(adj_a, i, j_dual) * generator(adj_b, j, i_dual),
    )

    simplified = trace.simplify_index_algebra(
        expand=False,
        gamma=False,
        color=False,
        pychete_color=True,
        metrics=False,
    )

    assert_expr_equal(simplified.expression, delta_adj(adj_a, adj_b) / 2)
    assert "spenso::" not in canonical_string(simplified.expression)


def test_one_loop_setup_simplifies_projector_words_before_vakint_lowering() -> None:
    theory = Theory("one_loop_setup_vlf_projectors")
    heavy = theory.define_field("Psi", s.Fermion, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("psi", s.Fermion, mass=0)
    scalar = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y")
    interaction = -y() * scalar() * s.NCM(s.Bar(light()), s.PR, heavy())
    lagrangian = theory.free_lag(heavy, light, scalar) + interaction + s.Bar(interaction)
    setup = theory.one_loop_setup(lagrangian, max_trace_order=2)

    result = setup.interaction_power_type_matching_result()
    numerator = result.expression("interaction_power_type_supertrace[hFermion-lFermion,eft_numerator]")
    open_chain_numerator = result.expression("interaction_power_type_supertrace[hFermion-lScalar,eft_numerator]")

    assert "pychete::eft_order_parameter" not in canonical_string(numerator)
    assert "pychete::PR^2" not in canonical_string(numerator)
    assert "pychete::PL^2" not in canonical_string(numerator)
    assert_expr_equal(numerator, Expression.num(0))
    assert "pychete::NCM(" in canonical_string(open_chain_numerator)
    assert canonical_string(s.NCM(s.Bar(light()), s.PR) ** 2) not in canonical_string(open_chain_numerator)
    assert canonical_string(s.NCM(s.PL, light()) ** 2) not in canonical_string(open_chain_numerator)
    assert_expr_equal(
        open_chain_numerator,
        y() * s.Bar(y()) * s.NCM(s.PL, light()) * s.NCM(s.Bar(light()), s.PR),
    )


def test_wilson_line_expansion_normalizes_nested_fermion_ncm_chains() -> None:
    theory = Theory("wilson_line_nested_fermion_ncm")
    heavy = theory.define_field("Psi", s.Fermion, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("psi", s.Fermion, mass=0)
    scalar = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y")
    mass = theory.mass_expr(heavy.definition)
    assert mass is not None
    interaction = -y() * scalar() * s.NCM(s.Bar(light()), s.PR, heavy())
    lagrangian = theory.free_lag(heavy, light, scalar) + interaction + s.Bar(interaction)
    setup = theory.one_loop_setup(lagrangian, max_trace_order=2)

    terms = setup.interaction_wilson_line_expansion_terms({"hFermion-lScalar": ((), ())})
    numerators = tuple(term.numerator for term in terms)

    assert len(numerators) == 1
    assert all("pychete::NCM(" in canonical_string(numerator) for numerator in numerators)
    assert all("pychete::NCM(pychete::NCM" not in canonical_string(numerator) for numerator in numerators)
    assert_expr_equal(
        sum(numerators, Expression.num(0)).expand(),
        mass * y() * s.Bar(y()) * s.NCM(s.PL, light(), s.Bar(light()), s.PR) / 2,
    )


def test_wilson_line_fermion_slots_preserve_even_slash_numerators() -> None:
    theory = Theory("wilson_line_fermion_even_slash")
    heavy = theory.define_field("Psi", s.Fermion, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("psi", s.Fermion, mass=0)
    scalar = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y")
    interaction = -y() * scalar() * s.NCM(s.Bar(light()), s.PR, heavy())
    lagrangian = theory.free_lag(heavy, light, scalar) + interaction + s.Bar(interaction)
    setup = theory.one_loop_setup(lagrangian, max_trace_order=2)

    terms = setup.interaction_wilson_line_expansion_terms({"hFermion-lFermion": ((), ())})

    assert len(terms) == 2
    for term in terms:
        assert term.propagator_powers == (1, 1)
        assert len(tuple(term.numerator.match(s.LoopMomentum(s.LoopMomentumIndexWildcard)))) == 2
        assert len(tuple(term.numerator.match(s.Gamma(s.CDIndexWildcard)))) == 2
        assert "pychete::NCM(pychete::NCM" not in canonical_string(term.numerator)


def test_wilson_line_postprocess_closes_pure_fermion_loop_dirac_traces() -> None:
    theory = Theory("wilson_line_close_fermion_loop_postprocess")
    left = theory.define_field("psi", s.Fermion)
    right = theory.define_field("Psi", s.Fermion)
    vector = theory.define_field("V", s.Vector, self_conjugate=True, mass=0)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")
    rho = theory.lorentz_index("rho")
    scalar = S("x")
    closed_gamma_word = s.NCM(s.Gamma(mu), s.Gamma(nu))
    closed_loop_momentum_word = s.LoopMomentum(mu) * s.LoopMomentum(nu) * closed_gamma_word
    field_strength_trace = s.Metric(mu, nu) * s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List())
    open_chain = s.NCM(s.Bar(left()), s.Gamma(mu), right())

    assert_expr_equal(
        matching_module._postprocess_wilson_line_numerator(scalar, close_fermion_loop=True),
        4 * scalar,
    )
    closed_gamma_result = matching_module._postprocess_wilson_line_numerator(
        closed_gamma_word,
        close_fermion_loop=True,
    )
    assert canonical_string(closed_gamma_result) in {
        canonical_string(4 * s.Metric(mu, nu)),
        canonical_string(4 * s.Metric(nu, mu)),
    }
    assert_expr_equal(
        matching_module._postprocess_wilson_line_numerator(closed_loop_momentum_word, close_fermion_loop=True),
        4 * s.LoopMomentumSquared,
    )
    assert_expr_equal(
        matching_module._postprocess_wilson_line_numerator(
            s.Metric(mu, rho) * s.FieldStrength(vector.label, s.List(rho, nu), s.List(), s.List()),
            close_fermion_loop=False,
        ),
        s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List()),
    )
    assert_expr_equal(
        matching_module._postprocess_wilson_line_numerator(field_strength_trace, close_fermion_loop=False),
        Expression.num(0),
    )
    assert_expr_equal(
        matching_module._postprocess_wilson_line_numerator(open_chain, close_fermion_loop=True),
        open_chain,
    )


def test_power_type_numerator_simplifies_mixed_ncm_dirac_subwords_before_eft_truncation() -> None:
    theory = Theory("power_type_mixed_ncm_dirac")
    mu = theory.dummy_index(0)
    trace = SupertraceBlockTrace(
        theory=theory,
        name="mixed_ncm_dirac",
        blocks=(),
        modes=(),
        expression=s.NCM(S("left"), s.PR, s.Gamma(mu), s.PR, S("right")),
    )
    contribution = PowerTypeSupertraceContribution(theory=theory, trace=trace, eft_order=6)

    assert_expr_equal(contribution.numerator_expression, Expression.num(0))


def test_one_loop_setup_routes_generated_kernels_through_vakint_engine() -> None:
    theory = Theory("one_loop_setup_vakint")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = heavy() ** 2 + light() ** 2 - y() * heavy() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, max_trace_order=1)

    canonical_engine = FakeKernelVakintEngine()
    canonicalized = setup.canonicalize_integrals(short_form=True, engine=canonical_engine)
    assert [name for name, _expr, _short in canonical_engine.calls] == ["to_canonical"]
    assert canonical_engine.calls[0][2] is True
    assert_expr_equal(canonicalized.block_traces[0].expression, S("canonical")(setup.block_traces[0].expression))

    reduction_engine = FakeKernelVakintEngine()
    reduced = setup.tensor_reduce_integrals(engine=reduction_engine)
    assert [name for name, _expr, _short in reduction_engine.calls] == ["tensor_reduce"]
    assert_expr_equal(reduced.block_traces[0].expression, S("reduced")(setup.block_traces[0].expression))

    evaluation_engine = FakeKernelVakintEngine()
    evaluated = setup.evaluate_integrals(engine=evaluation_engine)
    assert [name for name, _expr, _short in evaluation_engine.calls] == ["evaluate"]
    assert_expr_equal(evaluated.block_traces[0].expression, S("evaluated")(setup.block_traces[0].expression))

    assert canonicalized.fluctuation_operator is setup.fluctuation_operator
    assert reduced.supertrace_plan is setup.supertrace_plan
    assert evaluated.block_traces[0].name == setup.block_traces[0].name


def test_one_loop_setup_routes_generated_kernels_through_spenso(monkeypatch: pytest.MonkeyPatch) -> None:
    theory = Theory("one_loop_setup_spenso")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True)
    y = theory.define_coupling("y", self_conjugate=True)
    lagrangian = heavy() ** 2 + light() ** 2 - y() * heavy() * light() ** 2 / 2
    calls: list[tuple[Expression, object, object, int | None, object]] = []

    def fake_evaluate_tensor_network(
        expr: Expression,
        *,
        library: object | None = None,
        function_library: object | None = None,
        n_steps: int | None = None,
        mode: object | None = None,
    ) -> FakeTensorNetwork:
        calls.append((expr, library, function_library, n_steps, mode))
        return FakeTensorNetwork(expr)

    def fake_tensor_network_result_scalar(network: FakeTensorNetwork) -> Expression:
        return S("tensor")(network.expr)

    monkeypatch.setattr(spenso_backend, "evaluate_tensor_network", fake_evaluate_tensor_network)
    monkeypatch.setattr(spenso_backend, "tensor_network_result_scalar", fake_tensor_network_result_scalar)

    setup = theory.one_loop_setup(lagrangian, max_trace_order=1)
    evaluated = setup.evaluate_tensor_networks(
        library="library",
        function_library="functions",
        n_steps=7,
        mode="mode",
    )

    assert len(calls) == setup.supertrace_kernel_count
    assert calls[0][1:] == ("library", "functions", 7, "mode")
    assert evaluated.fluctuation_operator is setup.fluctuation_operator
    assert evaluated.supertrace_plan is setup.supertrace_plan
    assert evaluated.block_traces[0].name == setup.block_traces[0].name
    assert_expr_equal(evaluated.block_traces[0].expression, S("tensor")(setup.block_traces[0].expression))


def test_supertrace_block_trace_lowers_registered_cg_tensors_before_spenso(monkeypatch: pytest.MonkeyPatch) -> None:
    theory = Theory("supertrace_spenso_cg")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    eps = theory.cg_tensor_handle("eps_SU2F")
    trace = SupertraceBlockTrace(
        theory=theory,
        name="cg_kernel",
        blocks=(),
        modes=(),
        expression=eps(S("i"), S("j")),
    )
    calls: list[tuple[Expression, object | None]] = []

    def fake_evaluate_tensor_network(
        expr: Expression,
        *,
        library: object | None = None,
        function_library: object | None = None,
        n_steps: int | None = None,
        mode: object | None = None,
    ) -> FakeTensorNetwork:
        calls.append((expr, library))
        return FakeTensorNetwork(expr)

    def fake_tensor_network_result_scalar(network: FakeTensorNetwork) -> Expression:
        return S("tensor")(network.expr)

    monkeypatch.setattr(spenso_backend, "evaluate_tensor_network", fake_evaluate_tensor_network)
    monkeypatch.setattr(spenso_backend, "tensor_network_result_scalar", fake_tensor_network_result_scalar)

    evaluated = trace.evaluate_tensor_network(builtin_cg_components=True)

    assert len(calls) == 1
    assert canonical_string(calls[0][0]).startswith("spenso_python::pychete_supertrace_spenso_cg_cg_eps_SU2F(")
    assert "pychete::CG" not in canonical_string(calls[0][0])
    assert type(calls[0][1]).__name__ == "TensorLibrary"
    assert evaluated.name == trace.name
    assert_expr_equal(evaluated.expression, S("tensor")(calls[0][0]))


def test_supertrace_block_trace_auto_uses_stored_cg_tensor_components(monkeypatch: pytest.MonkeyPatch) -> None:
    theory = Theory("supertrace_spenso_stored_cg")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    fund = theory.define_representation("SU2F", "fund")
    custom = theory.define_cg_tensor(
        "custom_eps",
        (fund, fund),
        tensor=spenso_backend.cg_tensor_component_expression(
            (2, 2),
            (Expression.num(0), S("a"), -S("a"), Expression.num(0)),
        ),
        source="unit-test",
    )
    trace = SupertraceBlockTrace(
        theory=theory,
        name="stored_cg_kernel",
        blocks=(),
        modes=(),
        expression=custom(S("i"), S("j")),
    )
    calls: list[tuple[Expression, object | None]] = []

    def fake_evaluate_tensor_network(
        expr: Expression,
        *,
        library: object | None = None,
        function_library: object | None = None,
        n_steps: int | None = None,
        mode: object | None = None,
    ) -> FakeTensorNetwork:
        calls.append((expr, library))
        return FakeTensorNetwork(expr)

    def fake_tensor_network_result_scalar(network: FakeTensorNetwork) -> Expression:
        return S("tensor")(network.expr)

    monkeypatch.setattr(spenso_backend, "evaluate_tensor_network", fake_evaluate_tensor_network)
    monkeypatch.setattr(spenso_backend, "tensor_network_result_scalar", fake_tensor_network_result_scalar)

    evaluated = trace.evaluate_tensor_network()

    assert len(calls) == 1
    assert "pychete::CG" not in canonical_string(calls[0][0])
    assert type(calls[0][1]).__name__ == "TensorLibrary"
    assert evaluated.name == trace.name
    assert_expr_equal(evaluated.expression, S("tensor")(calls[0][0]))


def test_supertrace_block_trace_can_use_native_hep_spenso_builtins(monkeypatch: pytest.MonkeyPatch) -> None:
    theory = Theory("supertrace_spenso_hep")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    generator = theory.cg_tensor_handle("gen_SU3c_fund")
    trace = SupertraceBlockTrace(
        theory=theory,
        name="hep_cg_kernel",
        blocks=(),
        modes=(),
        expression=generator(S("A"), S("i"), S("j")),
    )
    calls: list[tuple[Expression, object | None]] = []

    def fake_evaluate_tensor_network(
        expr: Expression,
        *,
        library: object | None = None,
        function_library: object | None = None,
        n_steps: int | None = None,
        mode: object | None = None,
    ) -> FakeTensorNetwork:
        calls.append((expr, library))
        return FakeTensorNetwork(expr)

    def fake_tensor_network_result_scalar(network: FakeTensorNetwork) -> Expression:
        return S("tensor")(network.expr)

    monkeypatch.setattr(spenso_backend, "evaluate_tensor_network", fake_evaluate_tensor_network)
    monkeypatch.setattr(spenso_backend, "tensor_network_result_scalar", fake_tensor_network_result_scalar)

    evaluated = trace.evaluate_tensor_network(native_hep_cg_builtins=True)

    assert len(calls) == 1
    assert canonical_string(calls[0][0]).startswith("spenso::t(")
    assert "pychete::CG" not in canonical_string(calls[0][0])
    assert type(calls[0][1]).__name__ == "TensorLibrary"
    assert evaluated.name == trace.name
    assert_expr_equal(evaluated.expression, S("tensor")(calls[0][0]))
