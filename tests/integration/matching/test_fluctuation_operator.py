from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import (
    FieldMassKind,
    FieldRole,
    FluctuationSector,
    FluctuationStatistics,
    MatchingResult,
    SupertraceBlockTrace,
    Theory,
    VakintIntegralStage,
    canonical_string,
    s,
)
from pychete.backends import idenso as idenso_backend
from pychete.backends import spenso as spenso_backend
from pychete.backends import vakint as vakint_backend

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
    assert scalar_mode.self_conjugate is True
    assert scalar_mode.conjugated is False
    assert fermion_mode.mass_kind is FieldMassKind.LIGHT
    assert fermion_mode.statistics is FluctuationStatistics.FERMIONIC
    assert fermion_mode.supertrace_sign == -1
    assert fermion_mode.conjugated is False
    assert barred_fermion_mode.statistics is FluctuationStatistics.FERMIONIC
    assert barred_fermion_mode.conjugated is True
    assert basis.heavy_modes == (scalar_mode,)
    assert {canonical_string(mode.field) for mode in basis.light_modes} == {
        canonical_string(s.Bar(fermion())),
        canonical_string(fermion()),
    }


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

    with pytest.raises(ValueError, match="at least 1"):
        plan.closed_block_traces(0)


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
        "heavy-heavy",
        "heavy-heavy-heavy",
        "heavy-light-heavy",
        "light-heavy-light",
    )
    assert setup.fluctuation_operator.basis == (heavy(), light())
    assert setup.supertrace_plan.heavy_mode_count == 1
    assert_expr_equal(trace_map["supertrace_kernel[heavy-light-heavy]"], y() ** 2 * light() ** 2)
    assert tuple(trace.name for trace in setup.power_type_traces()) == (
        "heavy-heavy",
        "heavy-heavy-heavy",
        "heavy-light-heavy",
    )
    power_map = setup.power_type_expression_map()
    assert_expr_equal(
        power_map["power_type_supertrace[heavy-light-heavy,numerator]"],
        -y() ** 2 * light() ** 2 / 2,
    )
    assert_expr_equal(
        power_map["power_type_supertrace[heavy-light-heavy,eft_numerator]"],
        -y() ** 2 * light() ** 2 / 2,
    )
    assert_expr_equal(
        setup.power_type_eft_lagrangian(),
        -Expression.num(3) - y() ** 2 * light() ** 2 / 2,
    )
    assert setup.to_expression_map()
    assert_expr_equal(
        setup.to_expression_map()["one_loop_setup[power_type_eft_lagrangian]"],
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
        preview.expression("power_type_supertrace[heavy-light-heavy,eft_numerator]"),
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
    trace = next(trace for trace in setup.block_traces if trace.name == "heavy-light-heavy")
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
        decorated["supertrace_propagator_kernel[heavy-light-heavy]"],
        trace.propagator_expression(),
    )
    vakint_integral = vakint_backend.one_loop_vacuum_integral(trace.expression, (heavy_mass**2, light_mass**2))
    assert_expr_equal(trace.vakint_integral_expression(), vakint_integral)
    assert_expr_equal(
        setup.vakint_integral_expression_map()["vakint_integral[heavy-light-heavy]"],
        vakint_integral,
    )
    repeated_heavy_trace = next(trace for trace in setup.block_traces if trace.name == "heavy-heavy-heavy")
    repeated_heavy_integral = vakint_backend.one_loop_vacuum_integral(
        repeated_heavy_trace.expression,
        (heavy_mass**2,),
        powers=(2,),
    )
    assert_expr_equal(repeated_heavy_trace.vakint_integral_expression(), repeated_heavy_integral)
    assert_expr_equal(
        setup.vakint_integral_expression_map()["vakint_integral[heavy-heavy-heavy]"],
        repeated_heavy_integral,
    )
    canonical_engine = FakeKernelVakintEngine()
    canonicalized = setup.canonicalize_vakint_integral_expression_map(short_form=True, engine=canonical_engine)
    assert len(canonical_engine.calls) == setup.supertrace_kernel_count
    assert ("to_canonical", vakint_integral, True) in canonical_engine.calls
    assert_expr_equal(canonicalized["vakint_integral[heavy-light-heavy]"], S("canonical")(vakint_integral))
    reduction_engine = FakeKernelVakintEngine()
    reduced = setup.tensor_reduce_vakint_integral_expression_map(engine=reduction_engine)
    assert len(reduction_engine.calls) == setup.supertrace_kernel_count
    assert ("tensor_reduce", vakint_integral, None) in reduction_engine.calls
    assert_expr_equal(reduced["vakint_integral[heavy-light-heavy]"], S("reduced")(vakint_integral))
    evaluation_engine = FakeKernelVakintEngine()
    evaluated = setup.evaluate_vakint_integral_expression_map(engine=evaluation_engine)
    assert len(evaluation_engine.calls) == setup.supertrace_kernel_count
    assert ("evaluate", vakint_integral, None) in evaluation_engine.calls
    assert_expr_equal(evaluated["vakint_integral[heavy-light-heavy]"], S("evaluated")(vakint_integral))
    contribution = next(item for item in setup.power_type_contributions() if item.name == "heavy-light-heavy")
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
    canonical_power_sum = setup.power_type_vakint_integral_sum(
        stage=VakintIntegralStage.CANONICAL,
        short_form=True,
        engine=canonical_power_engine,
    )
    assert canonical_power_engine.calls == [("to_canonical", expected_power_type_vakint_sum, True)]
    assert_expr_equal(canonical_power_sum, S("canonical")(expected_power_type_vakint_sum))
    reduced_power_engine = FakeKernelVakintEngine()
    reduced_power_sum = setup.power_type_vakint_integral_sum(
        stage=VakintIntegralStage.TENSOR_REDUCED,
        engine=reduced_power_engine,
    )
    assert reduced_power_engine.calls == [("tensor_reduce", expected_power_type_vakint_sum, None)]
    assert_expr_equal(reduced_power_sum, S("reduced")(expected_power_type_vakint_sum))
    evaluated_power_engine = FakeKernelVakintEngine()
    evaluated_power_sum = setup.power_type_vakint_integral_sum(
        stage=VakintIntegralStage.EVALUATED,
        engine=evaluated_power_engine,
    )
    assert evaluated_power_engine.calls == [("evaluate", expected_power_type_vakint_sum, None)]
    assert_expr_equal(evaluated_power_sum, S("evaluated")(expected_power_type_vakint_sum))
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
    canonical_preview = setup.power_type_matching_preview(
        vakint_stage=VakintIntegralStage.CANONICAL,
        vakint_short_form=True,
        vakint_engine=preview_engine,
    )
    assert preview_engine.calls == [("to_canonical", expected_power_type_vakint_sum, True)]
    assert canonical_preview.metadata["vakint_stage"] == "canonical"
    assert_expr_equal(
        canonical_preview.expression("power_type_vakint_integral_sum"),
        S("canonical")(expected_power_type_vakint_sum),
    )
    assert_expr_equal(
        canonical_preview.expression("power_type_vakint_integral_sum[canonical]"),
        S("canonical")(expected_power_type_vakint_sum),
    )
    assert_expr_equal(canonical_preview.off_shell_eft_lagrangian, S("canonical")(expected_power_type_vakint_sum))
    assert "propagator_plan" in next(iter(full_plan.to_expression_map()))
    assert any(key.startswith("one_loop_setup.propagator[") for key in setup.to_expression_map())
    assert any(key.startswith("one_loop_setup.supertrace_propagator_kernel[") for key in setup.to_expression_map())
    assert any(key.startswith("one_loop_setup.vakint_integral[") for key in setup.to_expression_map())
    assert any(key.startswith("one_loop_setup.power_type_supertrace[") for key in setup.to_expression_map())
    assert any(key == "one_loop_setup[power_type_vakint_integral_sum]" for key in setup.to_expression_map())


def test_one_loop_setup_extracts_evaluated_vakint_poles_with_symbolica_coefficients() -> None:
    theory = Theory("one_loop_setup_poles")
    heavy = theory.define_field("H", s.Scalar, self_conjugate=True, mass=(FieldMassKind.HEAVY, "M"))
    light = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=(FieldMassKind.LIGHT, "m"))
    y = theory.define_coupling("y", self_conjugate=True)
    heavy_mass = theory.mass_expr(heavy.definition)
    light_mass = theory.mass_expr(light.definition)
    assert heavy_mass is not None
    assert light_mass is not None
    lagrangian = -heavy_mass**2 * heavy() ** 2 / 2 - light_mass**2 * light() ** 2 / 2 - y() * heavy() * light() ** 2 / 2
    setup = theory.one_loop_setup(lagrangian, eft_order=6, max_trace_order=2)
    expected_raw = setup.power_type_vakint_integral_sum()
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
