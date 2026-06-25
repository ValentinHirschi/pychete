from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import (
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
    Theory,
    VakintIntegralStage,
    canonical_string,
    one_loop_normalization_factor,
    s,
)
import pychete.matching as matching_module
from pychete.backends import idenso as idenso_backend
from pychete.backends import spenso as spenso_backend
from pychete.backends import vacuum_integrals as vacuum_integrals_backend
from pychete.backends import vakint as vakint_backend
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
        z() ** 2 * s.Bar(light_fermion()) ** 2 + z() ** 2 * light_fermion() ** 2,
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
        -Expression.num(3) - y() ** 2 * light() ** 2 / 2,
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
        + vakint_backend.one_loop_vacuum_integral(-(heavy_mass**2) ** 2 / 2, (heavy_mass**2, heavy_mass**2))
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
    assert_expr_equal(one_loop_normalization_factor(None), Expression.num(1))
    assert_expr_equal(matchete_hbar_factor, Expression.I * s.HBar)
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
    assert_expr_equal(
        numerator,
        (s.PR * scalar() ** 2 * y() ** 2 + s.PL * scalar() ** 2 * s.Bar(y()) ** 2) / 2,
    )
    assert "pychete::NCM(" in canonical_string(open_chain_numerator)
    assert canonical_string(s.NCM(s.Bar(light()), s.PR) ** 2) not in canonical_string(open_chain_numerator)
    assert canonical_string(s.NCM(s.PL, light()) ** 2) not in canonical_string(open_chain_numerator)
    assert_expr_equal(
        open_chain_numerator,
        (
            y() ** 2 * s.NCM(s.Bar(light()), s.PR, s.Bar(light()), s.PR)
            + s.Bar(y()) ** 2 * s.NCM(s.PL, light(), s.PL, light())
        )
        / 2,
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
