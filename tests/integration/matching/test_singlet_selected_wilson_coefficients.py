from __future__ import annotations

import json
from functools import cache
from pathlib import Path

import pytest
from symbolica import Expression, S

from pychete import (
    MatchingResult,
    OneLoopIntegralBackend,
    OneLoopMatchOptions,
    OneLoopNormalization,
    Theory,
    canonical_string,
    load_validation_fixture,
    one_loop_normalization_factor,
    s,
)
import pychete.matching as matching_module
import pychete.matching_results as matching_results_module
from pychete.backends import vakint as vakint_backend
from pychete.bases.smeft_warsaw import smeft_warsaw_operator

from tests.conftest import assert_expr_equal


_SINGLET_CHD_FOUR_SLOT_DEBUG = Path(
    "assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.debug.json"
)


@cache
def _selected_higgs_gauge_projection() -> tuple[Theory, dict[str, Expression]]:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    targets = {
        target_name: target
        for target_name in ("cHW", "cHB", "cHWB")
        if (target := smeft_warsaw_operator(theory, target_name)) is not None
    }
    assert set(targets) == {"cHW", "cHB", "cHWB"}
    hbar = theory.external_handle("hbar")()
    setup = theory.one_loop_setup(
        fixture.expression("lagrangian"),
        eft_order=6,
        max_trace_order=2,
    )
    plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar-lScalar",),
        max_total_order=4,
        max_slot_order=4,
        index_prefix="singlet_higgs_gauge_subset",
    )
    requirements = matching_module._term_atom_requirements_for_targets(theory, targets)
    grouped_terms = setup.interaction_wilson_line_expansion_terms_by_trace(
        plan,
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=False,
        max_wilson_derivative_order=4,
        simplify_pychete_color_algebra=True,
        term_atom_requirements=requirements,
    )
    evaluated_by_entry = matching_module._wilson_line_internal_evaluated_terms_by_entry_from_terms(
        theory,
        grouped_terms,
        tensor_reduce=True,
        tensor_reduce_engine=None,
        tensor_reduce_before_wilson_expand=True,
        max_wilson_derivative_order=4,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=False,
        simplify_pychete_color_algebra=True,
        expose_scalar_derivative_commutator_bilinears=False,
        epsilon=None,
        mu_r_squared=None,
    )
    selected = sum(
        (term for entry_terms in evaluated_by_entry.values() for term in entry_terms),
        Expression.num(0),
    )
    normalized_finite = (
        one_loop_normalization_factor(OneLoopNormalization.MATCHETE_EVALUATED_HBAR, hbar=hbar)
        * vakint_backend.finite_part(selected)
    ).expand()
    normalized_finite = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
        theory,
        normalized_finite,
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=normalized_finite,
    )

    projected = result.project_matching_conditions(
        targets,
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )
    return theory, dict(projected)


def _selected_higgs_gauge_expected(theory: Theory, condition_name: str) -> Expression:
    mass = theory.coupling_handle("M")()
    source = theory.coupling_handle("A")()
    g_l = theory.coupling_handle("gL")()
    g_y = theory.coupling_handle("gY")()
    hbar = theory.external_handle("hbar")()
    if condition_name == "cHW":
        return hbar * source**2 * g_l**2 / (12 * mass**4)
    if condition_name == "cHB":
        return hbar * source**2 * g_y**2 / (12 * mass**4)
    if condition_name == "cHWB":
        return hbar * source**2 * g_l * g_y / (6 * mass**4)
    raise ValueError(f"Unknown selected Singlet Higgs-gauge coefficient {condition_name!r}")


def _selected_chd_four_slot_target(theory: Theory) -> tuple[str, Expression]:
    registered_targets = matching_results_module.registered_wilson_matching_condition_targets(theory, basis="SMEFT")
    return next(
        (name, target)
        for name, target in registered_targets.items()
        if "external_cHD" in name
    )


def _selected_chd_four_slot_quarter_path_projection(path_index: int) -> tuple[Theory, Expression]:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    condition_name, target = _selected_chd_four_slot_target(theory)
    setup = theory.one_loop_setup(
        fixture.expression("lagrangian"),
        eft_order=6,
        max_trace_order=4,
    )
    paths = setup.interaction_wilson_line_trace_paths_by_trace(
        trace_names=("hScalar-lScalar-lVector-lScalar",),
    )["hScalar-lScalar-lVector-lScalar"]
    heavy_scalar_solutions = matching_module.solve_heavy_scalar_eoms(
        theory,
        fixture.expression("lagrangian"),
        eft_order=6,
    )
    requirements = matching_module._term_atom_requirements_for_targets(
        theory,
        {condition_name: target},
        heavy_scalar_solutions=heavy_scalar_solutions,
    )
    terms = paths[path_index].propagator_expansion_terms(
        ((), (), (), ()),
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=False,
        max_wilson_derivative_order=4,
        simplify_pychete_color_algebra=True,
    )
    terms = matching_module._filter_wilson_line_terms_by_projection_requirements(terms, requirements)
    evaluated_by_entry = matching_module._wilson_line_internal_evaluated_terms_by_entry_from_terms(
        theory,
        {f"path{path_index}": terms},
        tensor_reduce=True,
        tensor_reduce_engine=None,
        tensor_reduce_before_wilson_expand=True,
        max_wilson_derivative_order=4,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=False,
        simplify_pychete_color_algebra=True,
        expose_scalar_derivative_commutator_bilinears=False,
        epsilon=None,
        mu_r_squared=None,
    )
    selected = sum(evaluated_by_entry[f"path{path_index}"], Expression.num(0))
    normalized = (
        one_loop_normalization_factor(
            OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
            hbar=theory.external_handle("hbar")(),
        )
        * selected
    ).expand()
    normalized = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
        theory,
        normalized,
    )
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=normalized,
    )
    projected = result.project_matching_conditions(
        {condition_name: target},
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )[condition_name]
    return theory, projected


def _selected_chd_four_slot_quarter_expected(theory: Theory) -> Expression:
    mass = theory.coupling_handle("M")()
    return (
        theory.external_handle("hbar")()
        * theory.coupling_handle("A")() ** 2
        * theory.coupling_handle("gY")() ** 2
        * (
            mass.log() / 2
            - S("vakint::mursq").log() / 4
            - Expression.num(1) / (4 * vakint_backend.epsilon_symbol())
            - Expression.num(1) / 4
        )
        / mass**4
    )


@pytest.mark.parametrize("condition_name", ("cHW", "cHB", "cHWB"))
def test_selected_higgs_gauge_wilson_coefficient_matches_matchete_subset(condition_name: str) -> None:
    theory, projected = _selected_higgs_gauge_projection()

    assert set(projected) == {"cHW", "cHB", "cHWB"}
    assert_expr_equal(projected[condition_name], _selected_higgs_gauge_expected(theory, condition_name))


@pytest.mark.slow
def test_public_match_selected_higgs_gauge_wilson_subset_matches_matchete_fixture() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    reference = load_validation_fixture(
        Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json")
    ).matching_result("matchete_previous")
    theory = fixture.theory()
    expected_names = tuple(
        sorted(
            canonical_string(
                s.Coupling(
                    theory.external_handle(target_name).label,
                    s.List(*theory.external_handle(target_name).definition.index_exprs),
                    Expression.num(0),
                )
            )
            for target_name in ("cHW", "cHB", "cHWB")
        )
    )

    report = fixture.one_loop_preview_gap_report(
        reference,
        reference_name="Singlet_Scalar_Extension.matchete_previous",
        max_trace_order=2,
        integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
        normalization=OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
        hbar=theory.external_handle("hbar")(),
        wilson_line_trace_names=("hScalar-lScalar",),
        wilson_line_max_total_order=4,
        wilson_line_max_slot_order=4,
        wilson_line_index_prefix="public_singlet_higgs_gauge_subset_gap",
        wilson_line_act_open_derivatives=True,
        wilson_line_emit_covariant_derivative_commutators=False,
        wilson_line_emit_covariant_derivative_commutator_passes=1,
        wilson_line_covariant_derivative_commutator_mode="all_distinct",
        wilson_line_expand_covariant_derivative_commutators=False,
        wilson_line_max_derivative_order=4,
        wilson_line_filter_terms_by_matching_targets=True,
        wilson_line_expose_scalar_derivative_commutator_bilinears=True,
        wilson_line_tensor_reduce_before_wilson_expand=True,
        simplify_pychete_color_algebra=True,
        project_reference_matching_conditions=True,
        matching_condition_projection_names=("cHW", "cHB", "cHWB"),
        matching_condition_projection_source="on_shell_eft_lagrangian",
        matching_condition_projection_expand_source=False,
        matching_condition_projection_truncate_eft=True,
        matching_condition_projection_drop_zero=False,
        use_public_match_api=True,
        truncate_eft_result=False,
    )

    assert report.candidate_stage == "normalized_interaction_wilson_line_hybrid_internal_minimal_subtraction_result"
    assert report.candidate_metadata["fixture_preview_source"] == "public_match_api"
    assert report.candidate_metadata["wilson_line_terms_filtered_by_matching_targets"] is True
    assert report.candidate_metadata["interaction_wilson_line_tensor_reduce_before_wilson_expand"] is True
    assert report.candidate_metadata["interaction_wilson_line_term_count"] == 14
    assert report.candidate_metadata["interaction_wilson_line_plan_entry_count"] == 15
    assert report.candidate_matching_condition_names == expected_names
    assert report.reference_matching_condition_names == expected_names
    assert report.accepted_common_wilson_matching_condition_names == expected_names
    assert report.different_after_probe_common_wilson_matching_condition_names == ()


@pytest.mark.slow
def test_public_match_selected_chd_four_slot_wilson_coefficient_matches_matchete_subset() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    registered_targets = matching_results_module.registered_wilson_matching_condition_targets(theory, basis="SMEFT")
    condition_name, target = next(
        (name, target)
        for name, target in registered_targets.items()
        if "external_cHD" in name
    )
    hbar = theory.external_handle("hbar")()

    result = theory.match(
        fixture.expression("lagrangian"),
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=4,
            integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
            normalization=OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
            hbar=hbar,
            wilson_line_trace_names=("hScalar-lScalar-lVector-lScalar",),
            wilson_line_max_total_order=0,
            wilson_line_max_slot_order=0,
            wilson_line_index_prefix="public_singlet_cHD_four_slot",
            wilson_line_act_open_derivatives=True,
            wilson_line_emit_covariant_derivative_commutators=False,
            wilson_line_emit_covariant_derivative_commutator_passes=1,
            wilson_line_covariant_derivative_commutator_mode="all_distinct",
            wilson_line_expand_covariant_derivative_commutators=False,
            wilson_line_max_derivative_order=4,
            wilson_line_filter_terms_by_matching_targets=True,
            wilson_line_expose_scalar_derivative_commutator_bilinears=True,
            wilson_line_tensor_reduce_before_wilson_expand=True,
            simplify_pychete_color_algebra=True,
            truncate_eft_result=False,
        ),
        matching_condition_targets={condition_name: target},
        matching_condition_source="on_shell_eft_lagrangian",
        matching_condition_expand_source=False,
        matching_condition_truncate_eft=True,
        matching_condition_drop_zero=False,
    )
    projected = result.matching_conditions[condition_name]
    mass = theory.coupling_handle("M")()
    expected = (
        hbar
        * theory.coupling_handle("A")() ** 2
        * theory.coupling_handle("gY")() ** 2
        * (mass.log() - S("vakint::mursq").log() / 2 - Expression.num(1) / 2)
        / mass**4
    )

    assert result.metadata["wilson_line_terms_filtered_by_matching_targets"] is True
    assert result.metadata["interaction_wilson_line_term_count"] == 4
    assert result.metadata["interaction_wilson_line_plan_entry_count"] == 1
    assert result.metadata["interaction_wilson_line_nonzero_plan_entries"] == (
        "hScalar-lScalar-lVector-lScalar#wilson0_o0_0_0_0",
    )
    assert_expr_equal((projected - expected).expand(), Expression.num(0))


@pytest.mark.parametrize("path_index", (0, 26))
def test_selected_chd_four_slot_quarter_paths_match_matchete_insertion_checkpoint(path_index: int) -> None:
    debug = json.loads(_SINGLET_CHD_FOUR_SLOT_DEBUG.read_text(encoding="utf-8"))
    theory, projected = _selected_chd_four_slot_quarter_path_projection(path_index)
    expected = _selected_chd_four_slot_quarter_expected(theory)

    assert debug["trace_name"] == "hScalar-lScalar-lVector-lScalar"
    assert debug["target"] == "cHD"
    assert debug["prop_order"] == 0
    assert debug["insertion_count"] == 88
    assert debug["insertions"][0]["manual_minus_evaluate_str_input_form"] == "0"
    assert "(-1/4*" in debug["insertions"][0]["validation_simplified_prefactored_evaluate_str_input_form"]
    assert_expr_equal((projected - expected).expand(), Expression.num(0))


def test_selected_chd_four_slot_wilson_coefficient_matches_matchete_subset() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    condition_name, target = _selected_chd_four_slot_target(theory)
    hbar = theory.external_handle("hbar")()
    setup = theory.one_loop_setup(
        fixture.expression("lagrangian"),
        eft_order=6,
        max_trace_order=4,
    )
    heavy_scalar_solutions = matching_module.solve_heavy_scalar_eoms(
        theory,
        fixture.expression("lagrangian"),
        eft_order=6,
    )
    plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar-lScalar-lVector-lScalar",),
        max_total_order=0,
        max_slot_order=0,
        index_prefix="singlet_chd_four_slot",
    )
    requirements = matching_module._term_atom_requirements_for_targets(
        theory,
        {condition_name: target},
        heavy_scalar_solutions=heavy_scalar_solutions,
    )
    grouped_terms = setup.interaction_wilson_line_expansion_terms_by_trace(
        plan,
        act_open_derivatives=True,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=False,
        max_wilson_derivative_order=4,
        simplify_pychete_color_algebra=True,
        term_atom_requirements=requirements,
    )
    evaluated_by_entry = matching_module._wilson_line_internal_evaluated_terms_by_entry_from_terms(
        theory,
        grouped_terms,
        tensor_reduce=True,
        tensor_reduce_engine=None,
        tensor_reduce_before_wilson_expand=True,
        max_wilson_derivative_order=4,
        emit_covariant_derivative_commutators=False,
        emit_covariant_derivative_commutator_passes=1,
        covariant_derivative_commutator_mode="all_distinct",
        expand_covariant_derivative_commutators=False,
        simplify_pychete_color_algebra=True,
        expose_scalar_derivative_commutator_bilinears=False,
        epsilon=None,
        mu_r_squared=None,
    )
    selected = sum(
        (term for entry_terms in evaluated_by_entry.values() for term in entry_terms),
        Expression.num(0),
    )
    normalized_finite = (
        one_loop_normalization_factor(OneLoopNormalization.MATCHETE_EVALUATED_HBAR, hbar=hbar)
        * vakint_backend.finite_part(selected)
    ).expand()
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=normalized_finite,
    )

    projected = result.project_matching_conditions(
        {condition_name: target},
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )
    mass = theory.coupling_handle("M")()
    expected = (
        hbar
        * theory.coupling_handle("A")() ** 2
        * theory.coupling_handle("gY")() ** 2
        * (mass.log() - S("vakint::mursq").log() / 2 - Expression.num(1) / 2)
        / mass**4
    )

    assert_expr_equal(projected[condition_name], expected)

    replacement_rules = matching_module.heavy_scalar_solution_replacements(
        heavy_scalar_solutions,
        fresh_dummy_indices=True,
    )
    post_heavy = result.with_on_shell_reduction(replacement_rules, expand=False)
    post_commutator = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
        theory,
        post_heavy.on_shell_eft_lagrangian,
    )
    post_commutator_result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=post_commutator,
    )
    post_commutator_projected = post_commutator_result.project_matching_conditions(
        {condition_name: target},
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
    )

    assert_expr_equal(post_commutator_projected[condition_name], expected)
