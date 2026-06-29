from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import pytest
from symbolica import Expression, Replacement, S

import pychete.matching_results as matching_results_module
from pychete import (
    MatchingResult,
    NumericProbePlan,
    Theory,
    build_numeric_probe_plan,
    canonize_tensor_indices,
    canonical_string,
    deterministic_probe_samples,
    evaluator_probe_equal,
    load_validation_fixture,
    registered_wilson_matching_condition_targets,
    s,
    tensor_index_specs,
)
from pychete.backends import vacuum_integrals
from pychete.bases.smeft_warsaw import smeft_warsaw_operator
from pychete.expr import field_with_derivatives
from pychete.functional import apply_cd, expand_cd_operators
from pychete.validation_fixtures import _gap_report
from tests.conftest import assert_expr_equal


def _singlet_scalar_extension_theory() -> Theory:
    return load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json")).theory()


def test_evaluator_probe_equal_accepts_symbolically_equivalent_expressions() -> None:
    x, y = S("x", "y")

    result = evaluator_probe_equal(
        (x + y) ** 2,
        x**2 + 2 * x * y + y**2,
        [x, y],
        [
            [1.0, 2.0],
            [-3.5, 0.25],
        ],
    )

    assert result.equal is True
    assert result.max_abs_difference == 0.0


def test_evaluator_probe_equal_rejects_numerically_distinct_expressions() -> None:
    x = S("x")

    result = evaluator_probe_equal(
        x**2,
        x**2 + 1,
        [x],
        [[0.0], [2.0]],
    )

    assert result.equal is False
    assert result.max_abs_difference == 1.0


def test_evaluator_probe_equal_validates_samples_match_parameters() -> None:
    x, y = S("x", "y")

    with pytest.raises(ValueError, match="same length as parameters"):
        evaluator_probe_equal(x + y, y + x, [x, y], [[1.0]])


def test_build_numeric_probe_plan_discovers_symbols_with_symbolica() -> None:
    x, y, z = S("probe_plan_x", "probe_plan_y", "probe_plan_z")
    f = S("probe_plan_f")

    samples = deterministic_probe_samples([x, z], sample_count=2)
    plan = build_numeric_probe_plan(
        [x + y, (x + 1) / (z + 2), z.sin()],
        exclude_symbols=[y],
        sample_count=2,
    )

    assert isinstance(plan, NumericProbePlan)
    assert tuple(canonical_string(parameter) for parameter in plan.parameters) == (
        canonical_string(x),
        canonical_string(z),
    )
    assert plan.samples == samples
    assert plan.parameter_count == 2
    assert plan.sample_count == 2

    function_plan = build_numeric_probe_plan(
        [f(x) + y],
        exclude_symbols=[y],
        parameter_mode="indeterminates",
        sample_count=1,
    )
    assert tuple(canonical_string(parameter) for parameter in function_plan.parameters) == (
        canonical_string(f(x)),
    )


def test_matching_result_comparison_can_use_evaluator_probe_fallback() -> None:
    x = S("comparison_probe_x")
    theory = Theory("comparison_probe")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=x.sin() ** 2 + x.cos() ** 2,
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(1),
    )

    comparison = candidate.compare_to(
        reference,
        names=("on_shell_eft_lagrangian",),
        probe_parameters=[x],
        probe_samples=[[0.0], [0.7]],
    )

    assert comparison.equal is True
    expression = comparison.expressions[0]
    assert expression.canonical_equal is False
    assert expression.numeric_probe is not None
    assert expression.numeric_probe.equal is True


def test_matching_result_comparison_can_transform_expressions_before_comparing() -> None:
    mass = S("comparison_loop_mass")
    theory = Theory("comparison_loop_transform")
    loop_function = vacuum_integrals.loop_function((mass,), (1, 0))
    evaluated = vacuum_integrals.evaluate_loop_functions(loop_function)
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=evaluated,
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=loop_function,
    )

    raw_comparison = candidate.compare_to(reference, names=("on_shell_eft_lagrangian",))
    transformed_comparison = candidate.compare_to(
        reference,
        names=("on_shell_eft_lagrangian",),
        expression_transform=vacuum_integrals.evaluate_loop_functions,
    )

    assert raw_comparison.equal is False
    assert transformed_comparison.equal is True
    assert transformed_comparison.expressions[0].canonical_equal is True


def test_matching_result_comparison_canonizes_alpha_equivalent_index_contractions() -> None:
    theory = Theory("comparison_index_canonization")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    j = theory.dummy_index(2, fund)
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=s.Bar(higgs(i)) * higgs(i),
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=s.Bar(higgs(j)) * higgs(j),
    )

    canonicalized = candidate.compare_to(reference, names=("on_shell_eft_lagrangian",))
    raw = candidate.compare_to(
        reference,
        names=("on_shell_eft_lagrangian",),
        canonize_indices=False,
    )

    assert canonicalized.equal is True
    assert canonicalized.expressions[0].canonical_equal is True
    assert raw.equal is False
    assert raw.expressions[0].canonical_equal is False


def test_matching_result_comparison_can_restrict_evaluator_probe_names() -> None:
    x = S("comparison_probe_selected_x")
    theory = Theory("comparison_probe_selected")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "selected": x.sin() ** 2 + x.cos() ** 2,
            "unselected": x.sin() ** 2 + x.cos() ** 2 + x,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "selected": Expression.num(1),
            "unselected": x + 1,
        },
    )

    comparison = candidate.compare_to(
        reference,
        names=("selected", "unselected"),
        probe_parameters=[x],
        probe_samples=[[0.0], [0.7]],
        probe_names=("selected",),
    )

    selected, unselected = comparison.expressions
    assert selected.equal is True
    assert selected.numeric_probe is not None
    assert selected.numeric_probe.equal is True
    assert selected.canonical_equal is False
    assert unselected.equal is False
    assert unselected.canonical_equal is False
    assert unselected.numeric_probe is None


def test_gap_report_can_compare_after_loop_function_evaluation() -> None:
    mass = S("gap_report_loop_mass")
    theory = Theory("gap_report_loop_transform")
    loop_function = vacuum_integrals.loop_function((mass,), (1, 0))
    evaluated = vacuum_integrals.evaluate_loop_functions(loop_function)
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"loop": evaluated},
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"loop": loop_function},
    )

    raw_report = _gap_report("candidate", "reference", candidate, reference)
    transformed_report = _gap_report(
        "candidate",
        "reference",
        candidate,
        reference,
        comparison_expression_transform=vacuum_integrals.evaluate_loop_functions,
    )

    assert raw_report.canonical_equal_common_supertrace_names == ()
    assert raw_report.canonical_different_common_supertrace_names == ("loop",)
    assert transformed_report.canonical_equal_common_supertrace_names == ("loop",)
    assert transformed_report.canonical_different_common_supertrace_names == ()


def test_matching_result_comparison_requires_complete_probe_inputs() -> None:
    theory = Theory("comparison_probe_input")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
    )

    with pytest.raises(ValueError, match="provided together"):
        result.compare_to(result, probe_parameters=[])

    with pytest.raises(ValueError, match="probe_names requires"):
        result.compare_to(result, probe_names=("on_shell_eft_lagrangian",))


def test_matching_result_projects_conditions_with_symbolica_coefficients() -> None:
    coefficient_a, coefficient_b, operator_a, x = S(
        "condition_projection_a",
        "condition_projection_b",
        "condition_projection_operator_a",
        "condition_projection_x",
    )
    theory = Theory("condition_projection")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=(
            3 * coefficient_a * operator_a
            + (x + 1) * coefficient_b
            + 7 * coefficient_a * operator_a * coefficient_b
        ),
        matching_conditions={"existing": x},
    )

    projected = result.project_matching_conditions(
        {
            "a_operator": coefficient_a * operator_a,
            "b": coefficient_b,
            "missing": S("condition_projection_missing"),
        },
        drop_zero=True,
    )
    updated = result.with_projected_matching_conditions(
        {
            "a_operator": coefficient_a * operator_a,
            "b": coefficient_b,
        }
    )
    replacement = result.with_projected_matching_conditions(
        [coefficient_a * operator_a],
        merge=False,
    )

    assert set(projected) == {"a_operator", "b"}
    assert canonical_string((projected["a_operator"] - (3 + 7 * coefficient_b)).expand()) == "0"
    assert canonical_string((projected["b"] - (x + 1 + 7 * coefficient_a * operator_a)).expand()) == "0"
    assert set(updated.matching_conditions) == {"existing", "a_operator", "b"}
    assert canonical_string(updated.matching_conditions["existing"]) == canonical_string(x)
    assert updated.metadata["matching_conditions_projected"] is True
    assert updated.metadata["matching_condition_projection_source"] == "on_shell_eft_lagrangian"
    assert updated.metadata["matching_condition_projection_count"] == 2
    assert updated.metadata["matching_condition_projection_expand_source"] is True
    assert tuple(replacement.matching_conditions) == (canonical_string(coefficient_a * operator_a),)


def test_matching_result_can_project_from_unexpanded_source_expression() -> None:
    x = S("condition_projection_unexpanded_x")
    theory = Theory("condition_projection_unexpanded")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    operator = phi() ** 2
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=(x + 1) * operator,
    )

    projected = result.with_projected_matching_conditions(
        {"phi2": operator},
        expand_source=False,
    )

    assert projected.metadata["matching_condition_projection_expand_source"] is False
    assert_expr_equal(projected.matching_conditions["phi2"], x + 1)


def test_matching_result_loop_normalization_accepts_external_hbar_symbol() -> None:
    theory = Theory("condition_projection_external_hbar")
    hbar = theory.define_external("hbar")
    x = S("condition_projection_hbar_source")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=x,
        on_shell_eft_lagrangian=2 * x,
        matching_conditions={"x": 3 * x},
    )

    normalized = result.with_loop_normalization("matchete_hbar", hbar=hbar())

    assert normalized.metadata["loop_normalization"] == "matchete_hbar"
    assert_expr_equal(normalized.expression("interaction_power_type_loop_normalization_factor"), Expression.I * hbar())
    assert_expr_equal(normalized.off_shell_eft_lagrangian, Expression.I * hbar() * x)
    assert_expr_equal(normalized.on_shell_eft_lagrangian, 2 * Expression.I * hbar() * x)
    assert_expr_equal(normalized.matching_conditions["x"], 3 * Expression.I * hbar() * x)


def test_matching_result_projects_alpha_equivalent_index_contractions() -> None:
    theory = Theory("condition_projection_indices")
    theory.define_gauge_group("SU2L", s.SU(2), coupling="gL", field="W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=(fund,))
    named_index = theory.index("i", fund)
    dummy_index = theory.dummy_index(1, fund)
    target = higgs(named_index) * s.Bar(higgs(named_index))
    source_operator = higgs(dummy_index) * s.Bar(higgs(dummy_index))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=5 * source_operator,
    )

    projected = result.with_projected_matching_conditions({"HbarH": target}, expand_source=False)
    uncanonized = result.project_matching_conditions(
        {"HbarH": target},
        expand_source=False,
        canonize_indices=False,
    )

    assert projected.metadata["matching_condition_projection_canonize_indices"] is True
    assert_expr_equal(projected.matching_conditions["HbarH"], Expression.num(5))
    assert_expr_equal(uncanonized["HbarH"], Expression.num(0))


def test_tensor_canonization_helper_exposes_symbolica_dummy_index_payload() -> None:
    theory = Theory("condition_projection_canonization_payload")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    j = theory.dummy_index(2, fund)
    target = s.Bar(higgs(i)) * higgs(i)
    alpha_equivalent = s.Bar(higgs(j)) * higgs(j)

    canonized = canonize_tensor_indices(alpha_equivalent, tensor_index_specs(target, alpha_equivalent))

    assert_expr_equal(canonized.expression, target)
    assert canonized.external_indices == ()
    assert len(canonized.dummy_indices) == 1
    assert_expr_equal(canonized.dummy_indices[0].expr, i)
    assert_expr_equal(canonized.dummy_indices[0].group, fund)


def test_matching_result_comparison_canonizes_alpha_equivalent_dummy_indices() -> None:
    theory = Theory("condition_comparison_dummy_indices")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    j = theory.dummy_index(2, fund)
    lhs_operator = s.Bar(higgs(i)) * higgs(i)
    rhs_operator = s.Bar(higgs(j)) * higgs(j)
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=7 * lhs_operator,
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=7 * rhs_operator,
    )

    canonized = candidate.compare_to(reference, names=["on_shell_eft_lagrangian"])
    raw = candidate.compare_to(reference, names=["on_shell_eft_lagrangian"], canonize_indices=False)
    expression = canonized.expressions[0]

    assert canonized.equal is True
    assert expression.canonical_equal is True
    assert expression.index_canonized is True
    assert expression.index_canonization_failed_terms == 0
    assert len(expression.candidate_index_canonizations) == 1
    assert len(expression.reference_index_canonizations) == 1
    candidate_dummy = expression.candidate_index_canonizations[0].dummy_indices[0]
    reference_dummy = expression.reference_index_canonizations[0].dummy_indices[0]
    assert_expr_equal(candidate_dummy.expr, reference_dummy.expr)
    assert_expr_equal(candidate_dummy.group, fund)
    assert_expr_equal(reference_dummy.group, fund)
    assert raw.equal is False
    assert raw.expressions[0].index_canonized is False


def test_matching_result_projects_alpha_equivalent_conjugate_representation_indices() -> None:
    coefficient = S("condition_projection_conjugate_indices_coefficient")
    theory = Theory("condition_projection_conjugate_indices")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field(
        "H",
        s.Scalar,
        indices=[fund],
        charges=[theory.group_charge("U1Y", Expression.num(1) / Expression.num(2))],
        self_conjugate=False,
        mass=0,
    )
    target = smeft_warsaw_operator(theory, "cHWB")
    assert target is not None
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    adjoint = theory.index("A", theory.symbol("SU2L", role="group")(s.adj))
    left = theory.index("i", fund)
    right = theory.index("j", fund)
    right_dual = theory.index("j", s.Bar(fund))
    mu = theory.index("mu")
    nu = theory.index("nu")
    source_operator = (
        s.Bar(higgs(left))
        * generator(adjoint, left, right_dual)
        * higgs(right)
        * s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adjoint), s.List())
        * s.FieldStrength(theory.field_handle("B").label, s.List(mu, nu), s.List(), s.List())
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    projected = result.project_matching_conditions({"cHWB": target}, expand_source=False)

    assert_expr_equal(projected["cHWB"], coefficient * theory.coupling_handle("gL")() * theory.coupling_handle("gY")() / 2)


def test_matching_result_simplifies_projected_closed_dummy_delta_coefficient() -> None:
    coefficient = S("condition_projection_closed_delta_coefficient")
    theory = Theory("condition_projection_closed_delta")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    mu = theory.index("mu")
    nu = theory.index("nu")
    adjoint = theory.index("A", adj)
    left = theory.dummy_index(1, fund)
    right = theory.dummy_index(2, s.Bar(fund))
    strength = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adjoint), s.List())
    target = strength**2
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * s.Delta(left, right) * target,
    )

    projected = result.project_matching_conditions({"cWW": target}, expand_source=False)

    assert_expr_equal(projected["cWW"], 2 * coefficient)


def test_matching_result_truncates_projected_coefficients_target_locally() -> None:
    x = S("condition_projection_local_eft_x")
    theory = Theory("condition_projection_local_eft")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    operator = phi() ** 2
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=(x + phi() ** 4) * operator,
    )

    projected = result.with_projected_matching_conditions(
        {"phi2": operator},
        expand_source=False,
        eft_order=4,
    )

    assert projected.metadata["matching_condition_projection_eft_order"] == 4
    assert projected.metadata["matching_condition_projection_heavy_field_dimension"] is False
    assert_expr_equal(projected.matching_conditions["phi2"], x)


def test_matching_result_filters_wilson_coefficients_by_coupling_mass_dimension() -> None:
    theory = Theory("condition_projection_wilson_mass_dimension")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    source = theory.define_coupling("A", mass_dimension=1, self_conjugate=True)
    mass = theory.define_coupling("M", mass_dimension=1, self_conjugate=True)
    quartic = theory.define_coupling("kappa", mass_dimension=0, self_conjugate=True)
    unknown = theory.define_coupling("unknown", self_conjugate=True)
    operator = phi() ** 6
    wilson = theory.define_wilson_coefficient("cPhi6", eft_order=6, basis="toy", operator=operator)
    target = s.Coupling(wilson.label, s.List(), Expression.num(6))
    valid = source() ** 2 * quartic() / mass() ** 4
    dimension_incompatible = source() ** 2 * quartic() / mass() ** 6
    unknown_dimension = unknown() / mass() ** 6
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=(valid + dimension_incompatible + unknown_dimension) * operator,
    )

    projected = result.project_matching_conditions([target], expand_source=False, eft_order=6)

    assert_expr_equal(projected[canonical_string(target)], valid + unknown_dimension)


def test_matching_result_projects_wilson_conditions_from_operator_metadata() -> None:
    x = S("condition_projection_wilson_x")
    theory = Theory("condition_projection_wilson_operator")
    higgs = theory.define_field("H", s.Scalar, mass=0)
    operator = (s.Bar(higgs()) * higgs()) ** 3
    wilson = theory.define_wilson_coefficient("cH", eft_order=6, basis="SMEFT", operator=operator)
    theory.define_wilson_coefficient("cMissing", basis="SMEFT")
    theory.define_wilson_coefficient("cLEFT", basis="LEFT")
    target = s.Coupling(wilson.label, s.List(), Expression.num(6))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=11 * operator + 3 * target * operator + x * higgs(),
    )

    projected = result.project_matching_conditions([target])
    selector_projected = result.project_matching_conditions("registered_wilsons")
    smeft_targets = registered_wilson_matching_condition_targets(theory, basis="SMEFT")
    all_smeft_targets = registered_wilson_matching_condition_targets(
        theory,
        basis="SMEFT",
        include_without_operator=True,
    )

    assert tuple(projected) == (canonical_string(target),)
    assert canonical_string((projected[canonical_string(target)] - (11 + 3 * target)).expand()) == "0"
    assert tuple(selector_projected) == (canonical_string(target),)
    assert canonical_string((selector_projected[canonical_string(target)] - (11 + 3 * target)).expand()) == "0"
    assert set(smeft_targets) == {canonical_string(target)}
    assert set(all_smeft_targets) == {
        canonical_string(target),
        canonical_string(s.Coupling(theory.external_handle("cMissing").label, s.List(), Expression.num(0))),
    }

    with pytest.raises(ValueError, match="registered_wilsons"):
        result.project_matching_conditions("all_wilsons")


def test_matching_result_projects_negative_power_normalized_wilson_targets() -> None:
    x = S("condition_projection_negative_power_x")
    theory = Theory("condition_projection_negative_power")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    coupling = theory.define_coupling("g", self_conjugate=True)
    operator = s.Bar(phi()) * phi() / coupling() ** 2
    wilson = theory.define_wilson_coefficient("cPhi", eft_order=2, basis="toy", operator=operator)
    target = s.Coupling(wilson.label, s.List(), Expression.num(2))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=x * coupling() ** 2 * s.Bar(phi()) * phi(),
    )

    projected = result.project_matching_conditions([target])

    assert_expr_equal(projected[canonical_string(target)], x * coupling() ** 4)


def test_matching_result_projects_numeric_prefactor_normalized_targets() -> None:
    x = S("condition_projection_numeric_prefactor_x")
    theory = Theory("condition_projection_numeric_prefactor")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    operator = s.Bar(phi()) * phi()
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=x * operator,
    )

    projected = result.project_matching_conditions({"twice_phi": 2 * operator})

    assert_expr_equal(projected["twice_phi"], x / 2)


def test_matching_result_projection_normalizes_cd_targets_to_derivative_slots() -> None:
    coefficient = S("condition_projection_cd_coefficient")
    theory = Theory("condition_projection_cd_normalization")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    mu = theory.dummy_index(0)
    source = coefficient * phi(derivatives=[mu]) * s.Bar(phi(derivatives=[mu]))
    target = s.CD(mu, phi()) * s.CD(mu, s.Bar(phi()))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=source,
    )

    raw = result.project_matching_conditions({"kinetic": target}, normalize_derivative_operators=False)
    normalized = result.with_projected_matching_conditions({"kinetic": target})

    assert_expr_equal(raw["kinetic"], Expression.num(0))
    assert_expr_equal(normalized.matching_conditions["kinetic"], coefficient)
    assert normalized.metadata["matching_condition_projection_normalize_derivative_operators"] is True


def test_matching_result_projection_normalizes_additive_cd_targets() -> None:
    coefficient = S("condition_projection_cd_box_coefficient")
    theory = Theory("condition_projection_cd_box")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    mu = theory.dummy_index(0)
    source_operator = (
        phi(derivatives=[mu, mu]) * s.Bar(phi())
        + 2 * phi(derivatives=[mu]) * s.Bar(phi(derivatives=[mu]))
        + phi() * s.Bar(phi(derivatives=[mu, mu]))
    )
    target = s.CD(s.List(mu, mu), phi() * s.Bar(phi()))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    projected = result.project_matching_conditions({"box": target}, expand_source=False)

    assert_expr_equal(projected["box"], coefficient)


def test_matching_result_projection_can_use_ibp_scalar_bilinear_aliases() -> None:
    coefficient = S("condition_projection_ibp_box_coefficient")
    theory = Theory("condition_projection_ibp_box")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    mu = theory.dummy_index(0)
    bilinear = phi() * s.Bar(phi())
    derivative_bilinear = phi(derivatives=[mu]) * s.Bar(phi()) + phi() * s.Bar(phi(derivatives=[mu]))
    source_operator = -(derivative_bilinear * derivative_bilinear).expand()
    listed_target = bilinear * s.CD(s.List(mu, mu), bilinear)
    nested_target = bilinear * s.CD(mu, s.CD(mu, bilinear))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    raw = result.project_matching_conditions({"listed": listed_target, "nested": nested_target})
    normalized = result.with_projected_matching_conditions(
        {"listed": listed_target, "nested": nested_target},
        normalize_ibp_scalar_bilinears=True,
    )

    assert_expr_equal(raw["listed"], Expression.num(0))
    assert_expr_equal(raw["nested"], Expression.num(0))
    assert_expr_equal(normalized.matching_conditions["listed"], coefficient)
    assert_expr_equal(normalized.matching_conditions["nested"], coefficient)
    assert normalized.metadata["matching_condition_projection_normalize_ibp_scalar_bilinears"] is True


def test_matching_result_projection_uses_scalar_derivative_slot_ibp_alias() -> None:
    coefficient = S("condition_projection_ibp_derivative_slot_coefficient")
    theory = Theory("condition_projection_ibp_derivative_slot")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    target = s.Bar(phi()) * phi(derivatives=[mu, nu])
    source_operator = -s.Bar(phi(derivatives=[mu])) * phi(derivatives=[nu])
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    raw = result.project_matching_conditions({"slot": target}, expand_source=False)
    projected = result.project_matching_conditions(
        {"slot": target},
        expand_source=False,
        normalize_ibp_scalar_bilinears=True,
    )

    assert_expr_equal(raw["slot"], Expression.num(0))
    assert_expr_equal(projected["slot"], coefficient)


def test_matching_result_projection_factors_composite_smeft_hbox_targets() -> None:
    coefficient = S("condition_projection_hbox_factor_coefficient")
    theory = _singlet_scalar_extension_theory()
    target = smeft_warsaw_operator(theory, "cHBox")
    assert target is not None
    source = coefficient * expand_cd_operators(target)
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=source,
    )

    projected = result.project_matching_conditions({"cHBox": target})

    assert_expr_equal(projected["cHBox"], coefficient)


def test_matching_result_projection_handles_indexed_smeft_hbox_ibp_alias() -> None:
    coefficient = S("condition_projection_indexed_hbox_ibp_coefficient")
    theory = _singlet_scalar_extension_theory()
    target = smeft_warsaw_operator(theory, "cHBox")
    assert target is not None
    higgs = theory.field_handle("H")
    fund = theory.fields["H"].indices[0]
    i = theory.index(theory.symbol("projection_hbox_i"), fund)
    j = theory.index(theory.symbol("projection_hbox_j"), fund)
    mu = theory.dummy_index(0)
    left_bilinear = s.Bar(higgs(i)) * higgs(i)
    right_bilinear = s.Bar(higgs(j)) * higgs(j)
    source_operator = -(
        expand_cd_operators(s.CD(mu, left_bilinear)) * expand_cd_operators(s.CD(mu, right_bilinear))
    ).expand()
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    raw = result.project_matching_conditions({"cHBox": target})
    projected = result.project_matching_conditions(
        {"cHBox": target},
        normalize_ibp_scalar_bilinears=True,
    )

    assert_expr_equal(raw["cHBox"], Expression.num(0))
    assert_expr_equal(projected["cHBox"], coefficient)


def test_matching_result_projection_uses_registered_wilson_ibp_aliases() -> None:
    coefficient = S("condition_projection_registered_hbox_ibp_coefficient")
    theory = _singlet_scalar_extension_theory()
    definition = theory.externals["cHBox"]
    wilson_target = s.Coupling(definition.label, s.List(*definition.index_exprs), Expression.num(definition.order))
    raw_target = smeft_warsaw_operator(theory, "cHBox")
    assert raw_target is not None
    higgs = theory.field_handle("H")
    fund = theory.fields["H"].indices[0]
    i = theory.index(theory.symbol("projection_registered_hbox_i"), fund)
    j = theory.index(theory.symbol("projection_registered_hbox_j"), fund)
    mu = theory.dummy_index(0)
    left_bilinear = s.Bar(higgs(i)) * higgs(i)
    right_bilinear = s.Bar(higgs(j)) * higgs(j)
    source_operator = -(
        expand_cd_operators(s.CD(mu, left_bilinear)) * expand_cd_operators(s.CD(mu, right_bilinear))
    ).expand()
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    raw = result.project_matching_conditions({"cHBox": raw_target})
    registered = result.project_matching_conditions([wilson_target])

    assert_expr_equal(raw["cHBox"], Expression.num(0))
    assert_expr_equal(registered[canonical_string(wilson_target)], coefficient)


def test_matching_result_staged_projection_preserves_hbox_tree_alias_with_direct_loop_term() -> None:
    tree_coefficient = S("condition_projection_staged_hbox_tree_coefficient")
    loop_coefficient = S("condition_projection_staged_hbox_loop_coefficient")
    theory = _singlet_scalar_extension_theory()
    target = smeft_warsaw_operator(theory, "cHBox")
    assert target is not None
    higgs = theory.field_handle("H")
    fund = theory.fields["H"].indices[0]
    i = theory.index(theory.symbol("projection_staged_hbox_i"), fund)
    j = theory.index(theory.symbol("projection_staged_hbox_j"), fund)
    mu = theory.dummy_index(0)
    left_bilinear = s.Bar(higgs(i)) * higgs(i)
    right_bilinear = s.Bar(higgs(j)) * higgs(j)
    tree_source = -(
        expand_cd_operators(s.CD(mu, left_bilinear)) * expand_cd_operators(s.CD(mu, right_bilinear))
    ).expand()
    loop_source = expand_cd_operators(target)
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=(tree_coefficient * tree_source + loop_coefficient * loop_source).expand(),
        supertraces={
            matching_results_module.LOOP_ONLY_ON_SHELL_PROJECTION_SOURCE: loop_coefficient * loop_source,
            matching_results_module.TREE_LEVEL_ON_SHELL_PROJECTION_SOURCE: tree_coefficient * tree_source,
        },
    )

    combined = result.project_matching_conditions(
        {"cHBox": target},
        expand_source=False,
        normalize_ibp_scalar_bilinears=True,
    )
    staged = result.with_projected_matching_conditions_from_sources(
        {"cHBox": target},
        result.staged_projection_sources(),
        expand_source=False,
        normalize_ibp_scalar_bilinears=True,
    )

    assert_expr_equal(combined["cHBox"], loop_coefficient)
    assert_expr_equal(staged.matching_conditions["cHBox"], tree_coefficient + loop_coefficient)
    assert staged.metadata["matching_condition_projection_source"] == "staged"
    assert staged.metadata["matching_condition_projection_sources"] == (
        f"{matching_results_module.LOOP_ONLY_ON_SHELL_PROJECTION_SOURCE},"
        f"{matching_results_module.TREE_LEVEL_ON_SHELL_PROJECTION_SOURCE}"
    )


def test_matching_result_staged_projection_prefers_wilson_line_entry_sources() -> None:
    theory = _singlet_scalar_extension_theory()
    entry_a = f"{matching_results_module.WILSON_LINE_ON_SHELL_PROJECTION_SOURCE}[entry_a]"
    entry_b = f"{matching_results_module.WILSON_LINE_ON_SHELL_PROJECTION_SOURCE}[entry_b]"
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            matching_results_module.LOOP_ONLY_ON_SHELL_PROJECTION_SOURCE: S("loop_source"),
            matching_results_module.TREE_LEVEL_ON_SHELL_PROJECTION_SOURCE: S("tree_source"),
            entry_b: S("entry_b_source"),
            entry_a: S("entry_a_source"),
        },
    )

    assert result.staged_projection_sources() == (
        entry_a,
        entry_b,
        matching_results_module.TREE_LEVEL_ON_SHELL_PROJECTION_SOURCE,
    )


def test_matching_result_projection_canonizes_source_once_for_ibp_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coefficient = S("condition_projection_single_source_canonize_coefficient")
    theory = _singlet_scalar_extension_theory()
    definition = theory.externals["cHBox"]
    wilson_target = s.Coupling(definition.label, s.List(*definition.index_exprs), Expression.num(definition.order))
    higgs = theory.field_handle("H")
    fund = theory.fields["H"].indices[0]
    light = theory.define_field("ProjectionNoise", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.index(theory.symbol("projection_registered_hbox_once_i"), fund)
    j = theory.index(theory.symbol("projection_registered_hbox_once_j"), fund)
    k = theory.index(theory.symbol("projection_registered_hbox_once_k"), fund)
    mu = theory.dummy_index(0)
    left_bilinear = s.Bar(higgs(i)) * higgs(i)
    right_bilinear = s.Bar(higgs(j)) * higgs(j)
    source_operator = -(
        expand_cd_operators(s.CD(mu, left_bilinear)) * expand_cd_operators(s.CD(mu, right_bilinear))
    ).expand()
    irrelevant_operator = (
        S("condition_projection_irrelevant_source_marker") * s.Bar(light(k)) * light(k)
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator + irrelevant_operator,
    )
    original_canonize_tensor_terms = matching_results_module._canonize_tensor_terms
    source_canonize_count = 0
    irrelevant_canonize_count = 0

    def counting_canonize_tensor_terms(
        expr: Expression,
        index_specs: Sequence[tuple[Expression, Expression]],
    ) -> Expression:
        nonlocal source_canonize_count, irrelevant_canonize_count
        rendered = canonical_string(expr)
        if "condition_projection_irrelevant_source_marker" in rendered:
            irrelevant_canonize_count += 1
        if "condition_projection_single_source_canonize_coefficient" in rendered:
            source_canonize_count += 1
        return original_canonize_tensor_terms(expr, index_specs)

    monkeypatch.setattr(
        matching_results_module,
        "_canonize_tensor_terms",
        counting_canonize_tensor_terms,
    )

    registered = result.project_matching_conditions([wilson_target])

    assert_expr_equal(registered[canonical_string(wilson_target)], coefficient)
    assert source_canonize_count == 1
    assert irrelevant_canonize_count == 0


def test_matching_result_projection_prunes_derivative_incompatible_terms_before_canonization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coefficient = S("condition_projection_derivative_pruned_coefficient")
    noise = S("condition_projection_derivative_pruned_noise")
    theory = _singlet_scalar_extension_theory()
    target = smeft_warsaw_operator(theory, "cHD")
    assert target is not None
    higgs = theory.field_handle("H")
    fund = theory.fields["H"].indices[0]
    i = theory.index(theory.symbol("projection_derivative_pruned_i"), fund)
    j = theory.index(theory.symbol("projection_derivative_pruned_j"), fund)
    mu = theory.dummy_index(0)
    valid_source = (
        s.Bar(higgs(j))
        * higgs(i)
        * field_with_derivatives(higgs(j), (mu,))
        * s.Bar(field_with_derivatives(higgs(i), (mu,)))
    )
    derivative_incompatible_noise = (
        noise
        * s.Bar(higgs(i))
        * higgs(i)
        * field_with_derivatives(higgs(j), (mu, mu))
        * s.Bar(field_with_derivatives(higgs(j), (mu, mu)))
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * valid_source + derivative_incompatible_noise,
    )
    original_canonize_tensor_terms = matching_results_module._canonize_tensor_terms
    source_canonize_count = 0
    noise_canonize_count = 0

    def counting_canonize_tensor_terms(
        expr: Expression,
        index_specs: Sequence[tuple[Expression, Expression]],
    ) -> Expression:
        nonlocal source_canonize_count, noise_canonize_count
        rendered = canonical_string(expr)
        if "condition_projection_derivative_pruned_coefficient" in rendered:
            source_canonize_count += 1
        if "condition_projection_derivative_pruned_noise" in rendered:
            noise_canonize_count += 1
        return original_canonize_tensor_terms(expr, index_specs)

    monkeypatch.setattr(
        matching_results_module,
        "_canonize_tensor_terms",
        counting_canonize_tensor_terms,
    )

    projected = result.project_matching_conditions({"cHD": target}, expand_source=False)

    assert_expr_equal(projected["cHD"], coefficient)
    assert source_canonize_count == 1
    assert noise_canonize_count == 0


def test_matching_result_projection_skips_tensor_canonization_for_exact_index_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("condition_projection_exact_index_match")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    target = s.Bar(higgs(i)) * higgs(i)
    coefficient = S("condition_projection_exact_index_match_coefficient")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * target,
    )

    def fail_canonize_tensor_terms(
        expr: Expression,
        index_specs: Sequence[tuple[Expression, Expression]],
    ) -> Expression:
        raise AssertionError("exact indexed projection should not call tensor canonicalization")

    monkeypatch.setattr(
        matching_results_module,
        "_canonize_tensor_terms",
        fail_canonize_tensor_terms,
    )

    projected = result.project_matching_conditions({"h2": target}, expand_source=False)

    assert_expr_equal(projected["h2"], coefficient)


def test_matching_result_projection_adds_exact_and_alpha_equivalent_index_matches() -> None:
    theory = Theory("condition_projection_mixed_index_matches")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    j = theory.dummy_index(2, fund)
    target = s.Bar(higgs(i)) * higgs(i)
    alpha_equivalent_target = s.Bar(higgs(j)) * higgs(j)
    exact_coefficient = S("condition_projection_exact_index_piece")
    alpha_coefficient = S("condition_projection_alpha_index_piece")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=exact_coefficient * target + alpha_coefficient * alpha_equivalent_target,
    )

    projected = result.project_matching_conditions({"h2": target}, expand_source=False)

    assert_expr_equal(projected["h2"], exact_coefficient + alpha_coefficient)


def test_matching_result_projection_reuses_source_term_atom_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("condition_projection_cached_atom_counts")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    light = theory.define_field("L", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    j = theory.dummy_index(2, fund)
    target_h2 = s.Bar(higgs(i)) * higgs(i)
    target_l2 = s.Bar(light(j)) * light(j)
    coefficient_h2 = S("source_scan_h2")
    coefficient_l2 = S("source_scan_l2")
    source = coefficient_h2 * target_h2 + coefficient_l2 * target_l2
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=source,
    )
    original_projection_atom_counts = matching_results_module._projection_atom_counts
    source_scan_count = 0

    def counting_projection_atom_counts(expr: Expression) -> Counter[tuple[str, str]]:
        nonlocal source_scan_count
        if "source_scan_" in canonical_string(expr):
            source_scan_count += 1
        return original_projection_atom_counts(expr)

    monkeypatch.setattr(
        matching_results_module,
        "_projection_atom_counts",
        counting_projection_atom_counts,
    )

    projected = result.project_matching_conditions(
        {
            "h2": target_h2,
            "l2": target_l2,
        },
        expand_source=False,
    )

    assert_expr_equal(projected["h2"], coefficient_h2)
    assert_expr_equal(projected["l2"], coefficient_l2)
    assert source_scan_count == 2


def test_matching_result_projection_prefilters_simple_coupling_targets() -> None:
    theory = Theory("condition_projection_simple_coupling_prefilter")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    coupling = theory.define_coupling("lambda", self_conjugate=True)
    coefficient = S("condition_projection_lambda_coefficient")
    irrelevant = S("condition_projection_lambda_irrelevant_source")
    i = theory.dummy_index(1, fund)
    target = coupling()
    source = coefficient * target + irrelevant * s.Bar(higgs(i)) * higgs(i)
    extractor = matching_results_module._ProjectionCoefficientExtractor(source)

    filtered = extractor._filtered_source(target)
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=source,
    ).project_matching_conditions(
        {"lambda": target},
        expand_source=False,
        include_coupling_identities=False,
    )

    assert "condition_projection_lambda_irrelevant_source" not in canonical_string(filtered)
    assert_expr_equal(result["lambda"], coefficient)


def test_matching_result_projection_skips_factor_fallback_for_large_filtered_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("condition_projection_skip_large_factor")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    bilinear = s.Bar(higgs(i)) * higgs(i)
    target = bilinear**3
    source = sum(
        S(f"condition_projection_skip_large_factor_{n}") * bilinear**2
        for n in range(matching_results_module._MAX_PROJECTION_FACTOR_TERMS + 2)
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=source,
    )

    def fail_factored_source(
        self: object,
        source: Expression,
    ) -> Expression:
        raise AssertionError("large filtered projection sources should not be globally factored")

    monkeypatch.setattr(
        matching_results_module._ProjectionCoefficientExtractor,
        "_factored_source",
        fail_factored_source,
    )

    projected = result.project_matching_conditions({"h6": target}, expand_source=False)

    assert_expr_equal(projected["h6"], Expression.num(0))


def test_matching_result_projection_skips_factor_fallback_for_large_expression_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("condition_projection_skip_large_byte_factor")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    bilinear = s.Bar(higgs(i)) * higgs(i)
    target = bilinear**3
    source = S("condition_projection_skip_large_byte_factor") * bilinear**2
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=source,
    )

    def fail_factored_source(
        self: object,
        source: Expression,
    ) -> Expression:
        raise AssertionError("large-byte filtered projection sources should not be globally factored")

    monkeypatch.setattr(matching_results_module, "_MAX_PROJECTION_FACTOR_TERMS", 1_000)
    monkeypatch.setattr(matching_results_module, "_MAX_PROJECTION_FACTOR_BYTES", 1)
    monkeypatch.setattr(
        matching_results_module._ProjectionCoefficientExtractor,
        "_factored_source",
        fail_factored_source,
    )

    projected = result.project_matching_conditions({"h6": target}, expand_source=False)

    assert_expr_equal(projected["h6"], Expression.num(0))


def test_matching_result_projection_skips_collect_fallback_for_large_expression_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("condition_projection_skip_large_byte_collect")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    bilinear = s.Bar(higgs(i)) * higgs(i)
    target = bilinear**3
    source = S("condition_projection_skip_large_byte_collect") * bilinear**2
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=source,
    )

    def fail_collected_source(
        self: object,
        source: Expression,
    ) -> Expression:
        raise AssertionError("large-byte filtered projection sources should not be globally collected")

    monkeypatch.setattr(matching_results_module, "_MAX_PROJECTION_COLLECT_TERMS", 1_000)
    monkeypatch.setattr(matching_results_module, "_MAX_PROJECTION_COLLECT_BYTES", 1)
    monkeypatch.setattr(
        matching_results_module._ProjectionCoefficientExtractor,
        "_collected_source",
        fail_collected_source,
    )

    projected = result.project_matching_conditions({"h6": target}, expand_source=False)

    assert_expr_equal(projected["h6"], Expression.num(0))


def test_matching_result_projection_skips_generic_fallback_for_large_canonized_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("condition_projection_skip_large_canonized_generic")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    bilinear = s.Bar(higgs(i)) * higgs(i)
    target = bilinear**3
    source = S("condition_projection_skip_large_canonized_generic") * bilinear**2
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=source,
    )

    def fail_generic_projection(
        extractor: object,
        projection_expression: Expression,
        ibp_aliases: object,
    ) -> Expression:
        raise AssertionError("large tensor-canonized projection sources should skip the generic fallback")

    def fail_termwise_exact_projection(
        extractor: object,
        projection_expression: Expression,
        ibp_aliases: object,
    ) -> Expression:
        raise AssertionError("large tensor-canonized projection sources should skip termwise exact fallback")

    monkeypatch.setattr(matching_results_module, "_MAX_CANONIZED_PROJECTION_GENERIC_TERMS", 1_000)
    monkeypatch.setattr(matching_results_module, "_MAX_CANONIZED_PROJECTION_GENERIC_BYTES", 1)
    monkeypatch.setattr(matching_results_module, "_MAX_CANONIZED_PROJECTION_TERMWISE_TERMS", 1_000)
    monkeypatch.setattr(matching_results_module, "_MAX_CANONIZED_PROJECTION_TERMWISE_BYTES", 1)
    monkeypatch.setattr(matching_results_module, "_MAX_CANONIZED_PROJECTION_CHUNKED_TERMWISE_TERMS", 1_000)
    monkeypatch.setattr(matching_results_module, "_MAX_CANONIZED_PROJECTION_CHUNKED_TERMWISE_BYTES", 1)
    monkeypatch.setattr(matching_results_module, "_matching_projection_coefficient", fail_generic_projection)
    monkeypatch.setattr(
        matching_results_module,
        "_termwise_exact_matching_projection_coefficient",
        fail_termwise_exact_projection,
    )

    projected = result.project_matching_conditions({"h6": target}, expand_source=False)

    assert_expr_equal(projected["h6"], Expression.num(0))


def test_matching_result_projection_uses_chunked_termwise_exact_for_bounded_canonized_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    theory = Theory("condition_projection_chunked_canonized_exact")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    target_index = theory.dummy_index(1, fund)
    source_indices = tuple(theory.dummy_index(n, fund) for n in range(2, 6))
    target = s.Bar(higgs(target_index)) * higgs(target_index)
    coefficients = tuple(S(f"condition_projection_chunked_canonized_exact_{n}") for n in range(len(source_indices)))
    source = sum(
        coefficient * s.Bar(higgs(index)) * higgs(index)
        for coefficient, index in zip(coefficients, source_indices, strict=True)
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=source,
    )

    def fail_generic_projection(
        extractor: object,
        projection_expression: Expression,
        ibp_aliases: object,
    ) -> Expression:
        raise AssertionError("bounded chunked exact projection should not reach generic fallback")

    monkeypatch.setattr(matching_results_module, "_MAX_CANONIZED_PROJECTION_TERMWISE_TERMS", 1_000)
    monkeypatch.setattr(matching_results_module, "_MAX_CANONIZED_PROJECTION_TERMWISE_BYTES", 1)
    monkeypatch.setattr(matching_results_module, "_MAX_CANONIZED_PROJECTION_CHUNKED_TERMWISE_TERMS", 1_000)
    monkeypatch.setattr(matching_results_module, "_MAX_CANONIZED_PROJECTION_CHUNKED_TERMWISE_BYTES", 1_000_000)
    monkeypatch.setattr(matching_results_module, "_CANONIZED_PROJECTION_TERMWISE_CHUNK_SIZE", 2)
    monkeypatch.setattr(matching_results_module, "_matching_projection_coefficient", fail_generic_projection)

    projected = result.project_matching_conditions({"h2": target}, expand_source=False)

    assert_expr_equal(projected["h2"], sum(coefficients, Expression.num(0)))


def test_matching_result_projection_canonicalizes_higgs_derivative_current_to_chd() -> None:
    coefficient = S("condition_projection_chd_current_coefficient")
    theory = _singlet_scalar_extension_theory()
    target = smeft_warsaw_operator(theory, "cHD")
    assert target is not None
    higgs = theory.field_handle("H")
    fund = theory.fields["H"].indices[0]
    i = theory.index(theory.symbol("projection_chd_i"), fund)
    j = theory.index(theory.symbol("projection_chd_j"), fund)
    mu = theory.dummy_index(0)
    left_current = (
        Expression.I * s.Bar(higgs(i)) * s.CD(mu, higgs(i))
        - Expression.I * higgs(i) * s.CD(mu, s.Bar(higgs(i)))
    )
    right_current = (
        Expression.I * s.Bar(higgs(j)) * s.CD(mu, higgs(j))
        - Expression.I * higgs(j) * s.CD(mu, s.Bar(higgs(j)))
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * expand_cd_operators((left_current * right_current).expand()),
    )

    raw = result.project_matching_conditions({"cHD": target}, canonize_indices=False)
    projected = result.project_matching_conditions({"cHD": target})

    assert_expr_equal(raw["cHD"], Expression.num(0))
    assert_expr_equal(projected["cHD"], 2 * coefficient)


def test_registered_wilson_projection_uses_abelian_gauge_eom_current_alias_for_chd() -> None:
    coefficient = S("condition_projection_chd_gauge_eom_coefficient")
    theory = _singlet_scalar_extension_theory()
    wilson_target = next(
        target
        for key, target in registered_wilson_matching_condition_targets(theory, basis="SMEFT").items()
        if "external_cHD" in key
    )
    higgs = theory.field_handle("H")
    hypercharge = theory.coupling_handle("gY")
    fund = theory.fields["H"].indices[0]
    i = theory.index(theory.symbol("projection_chd_gauge_eom_i"), fund)
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    current = (
        Expression.I * s.Bar(higgs(i)) * s.CD(mu, higgs(i))
        - Expression.I * s.CD(mu, s.Bar(higgs(i))) * higgs(i)
    )
    standard_divergence = s.FieldStrength(
        theory.field_handle("B").label,
        s.List(nu, mu),
        s.List(),
        s.List(nu),
    )
    opposite_divergence = s.FieldStrength(
        theory.field_handle("B").label,
        s.List(mu, nu),
        s.List(),
        s.List(nu),
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * expand_cd_operators((current * standard_divergence).expand())
        + 3 * coefficient * expand_cd_operators((current * opposite_divergence).expand()),
    )

    projected = result.project_matching_conditions({"cHD": wilson_target}, expand_source=False)

    assert_expr_equal(projected["cHD"], 2 * coefficient * hypercharge() ** 2)


def test_registered_wilson_abelian_gauge_eom_alias_is_on_shell_scoped_for_chd() -> None:
    coefficient = S("condition_projection_chd_gauge_eom_scoped_coefficient")
    theory = _singlet_scalar_extension_theory()
    wilson_target = next(
        target
        for key, target in registered_wilson_matching_condition_targets(theory, basis="SMEFT").items()
        if "external_cHD" in key
    )
    higgs = theory.field_handle("H")
    hypercharge = theory.coupling_handle("gY")
    fund = theory.fields["H"].indices[0]
    i = theory.index(theory.symbol("projection_chd_gauge_eom_scoped_i"), fund)
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    current = (
        Expression.I * s.Bar(higgs(i)) * s.CD(mu, higgs(i))
        - Expression.I * s.CD(mu, s.Bar(higgs(i))) * higgs(i)
    )
    standard_divergence = s.FieldStrength(
        theory.field_handle("B").label,
        s.List(nu, mu),
        s.List(),
        s.List(nu),
    )
    opposite_divergence = s.FieldStrength(
        theory.field_handle("B").label,
        s.List(mu, nu),
        s.List(),
        s.List(nu),
    )
    source = coefficient * expand_cd_operators(
        (current * standard_divergence + 3 * current * opposite_divergence).expand()
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=source,
        on_shell_eft_lagrangian=source,
    )

    off_shell = result.project_matching_conditions(
        {"cHD": wilson_target},
        source="off_shell_eft_lagrangian",
        expand_source=False,
    )
    on_shell = result.project_matching_conditions(
        {"cHD": wilson_target},
        source="on_shell_eft_lagrangian",
        expand_source=False,
    )

    assert_expr_equal(off_shell["cHD"], Expression.num(0))
    assert_expr_equal(on_shell["cHD"], 2 * coefficient * hypercharge() ** 2)


def test_registered_wilson_projection_uses_abelian_gauge_eom_ibp_alias_for_chd() -> None:
    coefficient = S("condition_projection_chd_gauge_eom_ibp_coefficient")
    theory = _singlet_scalar_extension_theory()
    wilson_target = next(
        target
        for key, target in registered_wilson_matching_condition_targets(theory, basis="SMEFT").items()
        if "external_cHD" in key
    )
    higgs = theory.field_handle("H")
    hypercharge = theory.coupling_handle("gY")
    fund = theory.fields["H"].indices[0]
    i = theory.index(theory.symbol("projection_chd_gauge_eom_ibp_i"), fund)
    mu = theory.dummy_index(0)
    nu = theory.dummy_index(1)
    current = (
        Expression.I * s.Bar(higgs(i)) * s.CD(mu, higgs(i))
        - Expression.I * s.CD(mu, s.Bar(higgs(i))) * higgs(i)
    )
    standard_strength = s.FieldStrength(
        theory.field_handle("B").label,
        s.List(nu, mu),
        s.List(),
        s.List(),
    )
    opposite_strength = s.FieldStrength(
        theory.field_handle("B").label,
        s.List(mu, nu),
        s.List(),
        s.List(),
    )
    source = (
        -apply_cd([nu], current) * standard_strength
        - 3 * apply_cd([nu], current) * opposite_strength
    ).expand()
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * expand_cd_operators(source),
    )

    projected = result.project_matching_conditions({"cHD": wilson_target}, expand_source=False)

    assert_expr_equal(projected["cHD"], 2 * coefficient * hypercharge() ** 2)


def test_registered_wilson_projection_uses_scalar_first_derivative_ibp_alias_for_chd() -> None:
    coefficient = S("condition_projection_chd_first_derivative_ibp_coefficient")
    theory = _singlet_scalar_extension_theory()
    wilson_target = next(
        target
        for key, target in registered_wilson_matching_condition_targets(theory, basis="SMEFT").items()
        if "external_cHD" in key
    )
    higgs = theory.field_handle("H")
    fund = theory.fields["H"].indices[0]
    i = theory.index(theory.symbol("projection_chd_first_derivative_ibp_i"), fund)
    j = theory.index(theory.symbol("projection_chd_first_derivative_ibp_j"), fund)
    mu = theory.dummy_index(0)
    spectator = s.Bar(higgs(j)) * higgs(i) * s.CD(mu, higgs(j))
    alias = -s.CD(mu, spectator) * s.Bar(higgs(i))
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * expand_cd_operators(alias).expand(),
    )

    projected = result.project_matching_conditions({"cHD": wilson_target}, expand_source=False)

    assert_expr_equal(projected["cHD"], coefficient)


def test_matching_result_projection_expands_indexed_higgs_bilinear_powers_to_ch() -> None:
    coefficient = S("condition_projection_ch_power_coefficient")
    theory = _singlet_scalar_extension_theory()
    target = smeft_warsaw_operator(theory, "cH")
    assert target is not None
    higgs = theory.field_handle("H")
    fund = theory.fields["H"].indices[0]
    i = theory.dummy_index(1, fund)
    source_operator = higgs(i) ** 3 * s.Bar(higgs(i)) ** 3
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    raw = result.project_matching_conditions({"cH": target}, canonize_indices=False)
    projected = result.project_matching_conditions({"cH": target})

    assert_expr_equal(raw["cH"], Expression.num(0))
    assert_expr_equal(projected["cH"], coefficient)


def test_matching_result_projection_expands_hidden_additive_source_for_ch() -> None:
    coefficient = S("condition_projection_ch_hidden_sum_coefficient")
    theory = _singlet_scalar_extension_theory()
    target = smeft_warsaw_operator(theory, "cH")
    assert target is not None
    higgs = theory.field_handle("H")
    fund = theory.fields["H"].indices[0]
    i = theory.dummy_index(1, fund)
    j = theory.dummy_index(2, fund)
    source_operator = (
        higgs(i) ** 2
        * s.Bar(higgs(i)) ** 2
        * (higgs(j) * s.Bar(higgs(j)) + S("condition_projection_ch_hidden_branch"))
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * source_operator,
    )

    raw = result.project_matching_conditions({"cH": target}, canonize_indices=False, expand_source=False)
    projected = result.project_matching_conditions({"cH": target}, expand_source=False)

    assert_expr_equal(raw["cH"], Expression.num(0))
    assert_expr_equal(projected["cH"], coefficient)


def test_singlet_tree_matching_projects_ch_and_hbox_terms() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    lagrangian = fixture.expression("lagrangian")
    tree = theory.match(lagrangian, eft_order=6, loop_order=0)
    assert isinstance(tree, Expression)
    ch_definition = theory.externals["cH"]
    ch_target = s.Coupling(ch_definition.label, s.List(*ch_definition.index_exprs), Expression.num(ch_definition.order))
    hbox_definition = theory.externals["cHBox"]
    hbox_target = s.Coupling(
        hbox_definition.label,
        s.List(*hbox_definition.index_exprs),
        Expression.num(hbox_definition.order),
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=lagrangian,
        off_shell_eft_lagrangian=tree,
        on_shell_eft_lagrangian=tree,
    )
    A = theory.coupling_handle("A")
    mass = theory.coupling_handle("M")
    kappa = theory.coupling_handle("kappa")
    muphi = theory.coupling_handle("muphi")

    projected = result.project_matching_conditions(
        {
            canonical_string(ch_target): ch_target,
            canonical_string(hbox_target): hbox_target,
        },
        expand_source=False,
        normalize_ibp_scalar_bilinears=True,
        eft_order=6,
    )

    assert_expr_equal(
        projected[canonical_string(ch_target)],
        -A() ** 2 * kappa() / (2 * mass() ** 4) + A() ** 3 * muphi() / (6 * mass() ** 6),
    )
    assert_expr_equal(projected[canonical_string(hbox_target)], -A() ** 2 / (2 * mass() ** 4))


def test_matching_result_applies_on_shell_replacements_with_symbolica_rules() -> None:
    theory = Theory("result_on_shell_reduction")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    coupling = theory.define_coupling("c", self_conjugate=True)
    off_shell = coupling() * phi() ** 2 + coupling()
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=off_shell,
        on_shell_eft_lagrangian=off_shell,
    )

    reduced = result.with_on_shell_reduction((Replacement(phi() ** 2, Expression.num(0)),))

    assert reduced.metadata["on_shell_reduced"] is True
    assert reduced.metadata["on_shell_reduction_source"] == "on_shell_eft_lagrangian"
    assert reduced.metadata["on_shell_reduction_replacement_count"] == 1
    assert_expr_equal(reduced.off_shell_eft_lagrangian, off_shell)
    assert_expr_equal(reduced.expression("on_shell_eft_lagrangian_before_reduction"), off_shell)
    assert_expr_equal(reduced.expression("on_shell_eft_lagrangian_after_reduction"), coupling())
    assert_expr_equal(reduced.on_shell_eft_lagrangian, coupling())


def test_matching_result_applies_theory_eom_replacement_before_projection() -> None:
    theory = Theory("result_eom_on_shell_reduction")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    source = theory.define_coupling("J", self_conjugate=True)
    coefficient = theory.define_coupling("c", self_conjugate=True)
    mu = theory.dummy_index(0)
    derivative_target = phi(derivatives=[mu, mu])
    eom_lagrangian = theory.free_lag(phi) + source() * phi()
    off_shell = coefficient() * phi() * derivative_target
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=eom_lagrangian,
        off_shell_eft_lagrangian=off_shell,
        on_shell_eft_lagrangian=off_shell,
    )

    reduced = result.with_on_shell_reduction(
        (theory.eom_replacement_rule(eom_lagrangian, phi, solve_for=derivative_target),)
    ).with_projected_matching_conditions({"c_phi": coefficient() * phi()})

    assert reduced.metadata["on_shell_reduced"] is True
    assert reduced.metadata["matching_conditions_projected"] is True
    assert_expr_equal(reduced.on_shell_eft_lagrangian, coefficient() * phi() * source())
    assert_expr_equal(reduced.matching_conditions["c_phi"], source())


def test_matching_result_truncates_eft_lagrangians_with_symbolica_series() -> None:
    theory = Theory("result_eft_truncation")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    low = phi() ** 4
    high = phi() ** 8
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=low + high,
        on_shell_eft_lagrangian=low + high,
        matching_conditions={"raw": low + high},
        metadata={"stage": "raw_stage"},
    )

    truncated = result.with_eft_truncation(6)

    assert truncated.metadata["stage"] == "raw_stage"
    assert truncated.metadata["eft_result_truncated"] is True
    assert truncated.metadata["eft_result_truncation_order"] == 6
    assert truncated.metadata["eft_result_untruncated_stage"] == "raw_stage"
    assert_expr_equal(truncated.off_shell_eft_lagrangian, low)
    assert_expr_equal(truncated.on_shell_eft_lagrangian, low)
    assert_expr_equal(truncated.matching_conditions["raw"], low)
    assert_expr_equal(truncated.expression("off_shell_eft_lagrangian_before_eft_truncation"), low + high)
    assert_expr_equal(truncated.expression("on_shell_eft_lagrangian_after_eft_truncation"), low)


def test_fixture_gap_report_records_evaluator_probe_equal_supertraces() -> None:
    x = S("fixture_gap_probe_x")
    theory = Theory("fixture_gap_probe")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "probe": x.sin() ** 2 + x.cos() ** 2,
            "unprobed": x.sin() ** 2 + x.cos() ** 2 + x,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "probe": Expression.num(1),
            "unprobed": x + 1,
        },
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        probe_parameters=[x],
        probe_samples=[[0.0], [0.7], [1.3]],
        probe_supertrace_names=("probe",),
    )
    report_obj = report.to_json_obj()

    assert report.common_supertrace_names == ("probe", "unprobed")
    assert report.canonical_equal_common_supertrace_names == ()
    assert report.canonical_different_common_supertrace_names == ("probe", "unprobed")
    assert report.numeric_probe_equal_common_supertrace_names == ("probe",)
    assert report.numeric_probe_different_common_supertrace_names == ()
    assert report.numeric_probe_equal_common_supertrace_count == 1
    assert report.numeric_probe_different_common_supertrace_count == 0
    assert report.accepted_common_supertrace_names == ("probe",)
    assert report.different_after_probe_common_supertrace_names == ("unprobed",)
    assert report.accepted_common_supertrace_count == 1
    assert report.different_after_probe_common_supertrace_count == 1
    assert report_obj["numeric_probe_equal_common_supertrace_names"] == ["probe"]
    assert report_obj["numeric_probe_equal_common_supertrace_count"] == 1
    assert report_obj["accepted_common_supertrace_names"] == ["probe"]
    assert report_obj["different_after_probe_common_supertrace_count"] == 1


def test_fixture_gap_report_can_probe_canonical_different_supertraces_by_preset() -> None:
    x = S("fixture_gap_probe_preset_x")
    theory = Theory("fixture_gap_probe_preset")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "already_equal": x,
            "probe": x.sin() ** 2 + x.cos() ** 2,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "already_equal": x,
            "probe": Expression.num(1),
        },
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        auto_probe_samples=True,
        probe_supertrace_names="canonical_different",
    )

    assert report.canonical_equal_common_supertrace_names == ("already_equal",)
    assert report.canonical_different_common_supertrace_names == ("probe",)
    assert report.numeric_probe_equal_common_supertrace_names == ("probe",)
    assert report.accepted_common_supertrace_names == ("already_equal", "probe")
    assert report.different_after_probe_common_supertrace_names == ()


def test_fixture_gap_report_records_supertrace_word_orders() -> None:
    theory = Theory("fixture_gap_supertrace_order")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "hScalar": Expression.num(0),
            "hScalar[unnormalized]": Expression.num(1),
            "hScalar-lScalar": Expression.num(0),
            "aggregate_stage": Expression.num(0),
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={
            "hScalar": Expression.num(0),
            "hScalar-lScalar-lVector": Expression.num(0),
        },
    )

    report = _gap_report("candidate_fixture", "reference_fixture", candidate, reference)
    report_obj = report.to_json_obj()
    coverage_by_order = {coverage.order: coverage for coverage in report.supertrace_order_coverage}
    json_coverage_by_order = {entry["order"]: entry for entry in report_obj["supertrace_order_coverage"]}

    assert report.candidate_max_supertrace_order == 2
    assert report.reference_max_supertrace_order == 3
    assert report.max_supertrace_order_gap == 1
    assert report.candidate_supertrace_count == 3
    assert "hScalar[unnormalized]" not in report.candidate_supertrace_names
    assert tuple(coverage_by_order) == (1, 2, 3)
    assert coverage_by_order[1].candidate_count == 1
    assert coverage_by_order[1].reference_count == 1
    assert coverage_by_order[1].accepted_common_count == 1
    assert coverage_by_order[2].candidate_count == 1
    assert coverage_by_order[2].reference_count == 0
    assert coverage_by_order[2].candidate_only_names == ("hScalar-lScalar",)
    assert coverage_by_order[3].candidate_count == 0
    assert coverage_by_order[3].reference_count == 1
    assert coverage_by_order[3].missing_reference_count == 1
    assert coverage_by_order[3].reference_only_names == ("hScalar-lScalar-lVector",)
    assert json_coverage_by_order[3]["missing_reference_count"] == 1
    assert json_coverage_by_order[3]["reference_only_names"] == ["hScalar-lScalar-lVector"]
    assert report_obj["candidate_max_supertrace_order"] == 2
    assert report_obj["reference_max_supertrace_order"] == 3
    assert report_obj["max_supertrace_order_gap"] == 1


def test_fixture_gap_report_compares_common_matching_conditions() -> None:
    c_equal, c_diff, x = S("condition_gap_equal", "condition_gap_diff", "condition_gap_x")
    theory = Theory("condition_gap")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            canonical_string(c_equal): x + 1,
            canonical_string(c_diff): x,
            "candidate_only": x,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            canonical_string(c_equal): x + 1,
            canonical_string(c_diff): x + 2,
            "reference_only": x,
        },
    )

    report = _gap_report("candidate_fixture", "reference_fixture", candidate, reference)
    report_obj = report.to_json_obj()

    assert report.common_matching_condition_names == (canonical_string(c_diff), canonical_string(c_equal))
    assert report.canonical_equal_common_matching_condition_names == (canonical_string(c_equal),)
    assert report.canonical_different_common_matching_condition_names == (canonical_string(c_diff),)
    assert report.canonical_equal_common_matching_condition_count == 1
    assert report.canonical_different_common_matching_condition_count == 1
    assert report.accepted_common_matching_condition_names == (canonical_string(c_equal),)
    assert report.different_after_probe_common_matching_condition_names == (canonical_string(c_diff),)
    assert report.accepted_common_matching_condition_count == 1
    assert report.different_after_probe_common_matching_condition_count == 1
    assert report.candidate_only_matching_condition_names == ("candidate_only",)
    assert report.reference_only_matching_condition_names == ("reference_only",)
    assert report_obj["canonical_equal_common_matching_condition_names"] == [canonical_string(c_equal)]
    assert report_obj["canonical_different_common_matching_condition_count"] == 1
    assert report_obj["accepted_common_matching_condition_names"] == [canonical_string(c_equal)]
    assert report_obj["different_after_probe_common_matching_condition_count"] == 1


def test_fixture_gap_report_canonizes_alpha_equivalent_matching_conditions() -> None:
    theory = Theory("condition_gap_index_canonization")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.dummy_index(1, fund)
    j = theory.dummy_index(2, fund)
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={"indexed": 3 * s.Bar(higgs(i)) * higgs(i)},
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={"indexed": 3 * s.Bar(higgs(j)) * higgs(j)},
    )

    report = _gap_report("candidate_fixture", "reference_fixture", candidate, reference)
    raw_report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        comparison_canonize_indices=False,
    )
    report_obj = report.to_json_obj()

    assert report.comparison_canonize_indices is True
    assert report.canonical_equal_common_matching_condition_names == ("indexed",)
    assert report.canonical_different_common_matching_condition_names == ()
    assert report_obj["comparison_canonize_indices"] is True
    assert raw_report.comparison_canonize_indices is False
    assert raw_report.canonical_equal_common_matching_condition_names == ()
    assert raw_report.canonical_different_common_matching_condition_names == ("indexed",)


def test_fixture_gap_report_records_wilson_matching_condition_frontier() -> None:
    x = S("condition_gap_wilson_x")
    theory = Theory("condition_gap_wilson")
    wilson = theory.define_wilson_coefficient("cH", basis="SMEFT")
    coupling = theory.define_coupling("g")
    wilson_name = canonical_string(s.Coupling(wilson.label, s.List(), Expression.num(0)))
    coupling_name = canonical_string(coupling())
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            wilson_name: x,
            coupling_name: x,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            wilson_name: x,
            coupling_name: x + 1,
        },
    )

    report = _gap_report("candidate_fixture", "reference_fixture", candidate, reference)
    report_obj = report.to_json_obj()

    assert report.reference_wilson_matching_condition_names == (wilson_name,)
    assert report.common_wilson_matching_condition_names == (wilson_name,)
    assert report.accepted_common_wilson_matching_condition_names == (wilson_name,)
    assert report.different_after_probe_common_wilson_matching_condition_names == ()
    assert report.reference_wilson_matching_condition_count == 1
    assert report.common_wilson_matching_condition_count == 1
    assert report.accepted_common_wilson_matching_condition_count == 1
    assert report.different_after_probe_common_wilson_matching_condition_count == 0
    assert report_obj["reference_wilson_matching_condition_names"] == [wilson_name]
    assert report_obj["accepted_common_wilson_matching_condition_count"] == 1


def test_fixture_gap_report_can_probe_wilson_matching_conditions_by_preset() -> None:
    x = S("condition_gap_wilson_probe_x")
    theory = Theory("condition_gap_wilson_probe")
    wilson = theory.define_wilson_coefficient("cH", basis="SMEFT")
    coupling = theory.define_coupling("g")
    wilson_name = canonical_string(s.Coupling(wilson.label, s.List(), Expression.num(0)))
    coupling_name = canonical_string(coupling())
    trig_identity = x.sin() ** 2 + x.cos() ** 2
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            wilson_name: trig_identity,
            coupling_name: trig_identity,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            wilson_name: Expression.num(1),
            coupling_name: Expression.num(1),
        },
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        auto_probe_samples=True,
        probe_matching_condition_names="canonical_different_wilson",
    )

    assert report.common_matching_condition_names == (coupling_name, wilson_name)
    assert report.reference_wilson_matching_condition_names == (wilson_name,)
    assert report.numeric_probe_equal_common_matching_condition_names == (wilson_name,)
    assert report.accepted_common_wilson_matching_condition_names == (wilson_name,)
    assert report.accepted_common_matching_condition_names == (wilson_name,)
    assert report.different_after_probe_common_matching_condition_names == (coupling_name,)


def test_fixture_gap_report_rejects_unknown_probe_name_preset_strings() -> None:
    x = S("fixture_gap_bad_probe_preset_x")
    theory = Theory("fixture_gap_bad_probe_preset")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        supertraces={"literal_name": x},
    )

    with pytest.raises(ValueError, match="tuple/list"):
        _gap_report(
            "candidate_fixture",
            "reference_fixture",
            result,
            result,
            auto_probe_samples=True,
            probe_supertrace_names="literal_name",
        )

    with pytest.raises(ValueError, match="only valid for matching conditions"):
        _gap_report(
            "candidate_fixture",
            "reference_fixture",
            result,
            result,
            auto_probe_samples=True,
            probe_supertrace_names="wilson",
        )


def test_fixture_gap_report_records_evaluator_probe_equal_matching_conditions() -> None:
    x = S("fixture_gap_condition_probe_x")
    theory = Theory("fixture_gap_condition_probe")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            "probe_condition": x.sin() ** 2 + x.cos() ** 2,
            "unprobed_condition": x.sin() ** 2 + x.cos() ** 2 + x,
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            "probe_condition": Expression.num(1),
            "unprobed_condition": x + 1,
        },
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        auto_probe_samples=True,
        probe_sample_count=3,
        probe_matching_condition_names=("probe_condition",),
    )
    report_obj = report.to_json_obj()

    assert report.common_matching_condition_names == ("probe_condition", "unprobed_condition")
    assert report.canonical_equal_common_matching_condition_names == ()
    assert report.canonical_different_common_matching_condition_names == ("probe_condition", "unprobed_condition")
    assert report.numeric_probe_equal_common_matching_condition_names == ("probe_condition",)
    assert report.numeric_probe_different_common_matching_condition_names == ()
    assert report.numeric_probe_equal_common_matching_condition_count == 1
    assert report.numeric_probe_different_common_matching_condition_count == 0
    assert report.accepted_common_matching_condition_names == ("probe_condition",)
    assert report.different_after_probe_common_matching_condition_names == ("unprobed_condition",)
    assert report.accepted_common_matching_condition_count == 1
    assert report.different_after_probe_common_matching_condition_count == 1
    assert report_obj["numeric_probe_equal_common_matching_condition_names"] == ["probe_condition"]
    assert report_obj["numeric_probe_equal_common_matching_condition_count"] == 1
    assert report_obj["accepted_common_matching_condition_names"] == ["probe_condition"]
    assert report_obj["different_after_probe_common_matching_condition_count"] == 1


def test_fixture_gap_report_auto_probe_handles_function_application_parameters() -> None:
    f, x = S("fixture_gap_function_probe_f", "fixture_gap_function_probe_x")
    theory = Theory("fixture_gap_function_probe")
    candidate = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            "function_condition": f(x),
        },
    )
    reference = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={
            "function_condition": f(x) + 1,
        },
    )

    report = _gap_report(
        "candidate_fixture",
        "reference_fixture",
        candidate,
        reference,
        auto_probe_samples=True,
        probe_parameter_mode="indeterminates",
        probe_matching_condition_names=("function_condition",),
    )

    assert report.numeric_probe_equal_common_matching_condition_names == ()
    assert report.numeric_probe_different_common_matching_condition_names == ("function_condition",)
    assert report.different_after_probe_common_matching_condition_names == ("function_condition",)


def test_fixture_gap_report_auto_probe_requires_unambiguous_inputs() -> None:
    x = S("fixture_gap_auto_probe_x")
    theory = Theory("fixture_gap_auto_probe")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=Expression.num(0),
        matching_conditions={"condition": x},
    )

    with pytest.raises(ValueError, match="cannot be combined"):
        _gap_report(
            "candidate_fixture",
            "reference_fixture",
            result,
            result,
            auto_probe_samples=True,
            probe_parameters=[x],
            probe_samples=[[2.0]],
            probe_matching_condition_names=("condition",),
        )

    with pytest.raises(ValueError, match="requires probe_supertrace_names or probe_matching_condition_names"):
        _gap_report(
            "candidate_fixture",
            "reference_fixture",
            result,
            result,
            auto_probe_samples=True,
        )

    with pytest.raises(ValueError, match="requires probe_parameters/probe_samples"):
        _gap_report(
            "candidate_fixture",
            "reference_fixture",
            result,
            result,
            probe_matching_condition_names="common",
        )
