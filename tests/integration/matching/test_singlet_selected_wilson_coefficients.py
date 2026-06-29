from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

import pytest
from symbolica import Expression, S

from pychete import (
    MatchingResult,
    MatchingFixtureGapReport,
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
_SINGLET_CHD_FOUR_SLOT_FULL_DEBUG = Path(
    "assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop0.full.debug.json"
)
_SINGLET_CHD_FOUR_SLOT_PROP1_DEBUG = Path(
    "assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop1.debug.json"
)
_SINGLET_CHD_FOUR_SLOT_PROP2_DEBUG = Path(
    "assets/validation/matchete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.prop2.debug.json"
)
_SINGLET_CHD_HSCALAR_LSCALAR_PROP4_DEBUG = Path(
    "assets/validation/matchete/debug/singlet_hScalar_lScalar_cHD.prop4.debug.json"
)
_SINGLET_CHD_MATCHETE_EOM_DEBUG = Path(
    "assets/validation/matchete/debug/singlet_eom_cHD.debug.json"
)
_SINGLET_CHD_PYCHETE_EOM_BOUNDARY_DEBUG = Path(
    "assets/validation/pychete/debug/singlet_eom_cHD.pychete.debug.json"
)
_SINGLET_CHD_PYCHETE_SOURCE_DEBUG = Path(
    "assets/validation/pychete/debug/singlet_hScalar_lScalar_lVector_lScalar_cHD.pychete.source.debug.json"
)
_SINGLET_CHD_PYCHETE_UNFILTERED_SOURCE_DEBUG = Path(
    "assets/validation/pychete/debug/"
    "singlet_hScalar_lScalar_lVector_lScalar_cHD.pychete.unfiltered.source.debug.json"
)

_MATHEMATICA_XTERM_PATTERN = re.compile(
    r"Xterm\["
    r"\{(.+?)\}, "
    r"\{Matchete`SuperTrace`PackagePrivate`i, Matchete`SuperTrace`PackagePrivate`j\}, "
    r"([0-9]+), ([0-9]+), ([0-9]+)"
    r"\]"
)


@cache
def _selected_higgs_gauge_projection(
    condition_names: tuple[str, ...] = ("cHW", "cHB", "cHWB"),
) -> tuple[Theory, dict[str, Expression], dict[str, int | tuple[str, ...]]]:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    targets = {
        target_name: target
        for target_name in condition_names
        if (target := smeft_warsaw_operator(theory, target_name)) is not None
    }
    assert set(targets) == set(condition_names)
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
    nonzero_plan_entries = tuple(entry for entry, terms in grouped_terms.items() if terms)
    term_count = sum(len(terms) for terms in grouped_terms.values())
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
    metadata: dict[str, int | tuple[str, ...]] = {
        "plan_entry_count": len(grouped_terms),
        "nonzero_plan_entry_count": len(nonzero_plan_entries),
        "term_count": term_count,
        "nonzero_plan_entries": nonzero_plan_entries,
    }
    return theory, dict(projected), metadata


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


def _registered_wilson_condition_name(theory: Theory, external_name: str) -> str:
    handle = theory.external_handle(external_name)
    return canonical_string(
        s.Coupling(
            handle.label,
            s.List(*handle.definition.index_exprs),
            Expression.num(0),
        )
    )


@cache
def _public_selected_higgs_gauge_gap_report() -> tuple[Theory, MatchingFixtureGapReport, dict[str, str]]:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    reference = load_validation_fixture(
        Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json")
    ).matching_result("matchete_previous")
    theory = fixture.theory()
    condition_names = {
        target_name: _registered_wilson_condition_name(theory, target_name)
        for target_name in ("cHW", "cHB", "cHWB")
    }

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
        matching_condition_projection_names=tuple(condition_names),
        matching_condition_projection_source="on_shell_eft_lagrangian",
        matching_condition_projection_expand_source=False,
        matching_condition_projection_truncate_eft=True,
        matching_condition_projection_drop_zero=False,
        use_public_match_api=True,
        truncate_eft_result=False,
    )
    return theory, report, condition_names


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


def _selected_chd_four_slot_quarter_finite_expected(theory: Theory) -> Expression:
    mass = theory.coupling_handle("M")()
    return (
        theory.external_handle("hbar")()
        * theory.coupling_handle("A")() ** 2
        * theory.coupling_handle("gY")() ** 2
        * (mass.log() / 2 - S("vakint::mursq").log() / 4 - Expression.num(1) / 4)
        / mass**4
    )


def _selected_chd_four_slot_order_one_finite_expected(theory: Theory) -> Expression:
    mass = theory.coupling_handle("M")()
    return (
        theory.external_handle("hbar")()
        * theory.coupling_handle("A")() ** 2
        * theory.coupling_handle("gY")() ** 2
        * (S("vakint::mursq").log() - 2 * mass.log() + Expression.num(3) / 2)
        / mass**4
    )


def _selected_chd_four_slot_order_two_finite_expected(theory: Theory) -> Expression:
    mass = theory.coupling_handle("M")()
    return (
        theory.external_handle("hbar")()
        * theory.coupling_handle("A")() ** 2
        * theory.coupling_handle("gY")() ** 2
        * (mass.log() - S("vakint::mursq").log() / 2 - Expression.num(3) / 4)
        / mass**4
    )


@cache
def _selected_chd_four_slot_finite_projection_by_total_order() -> tuple[
    Theory,
    dict[int, Expression],
    dict[int, dict[str, int]],
]:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    condition_name, target = _selected_chd_four_slot_target(theory)
    hbar = theory.external_handle("hbar")()
    lagrangian = fixture.expression("lagrangian")
    setup = theory.one_loop_setup(
        lagrangian,
        eft_order=6,
        max_trace_order=4,
    )
    heavy_scalar_solutions = matching_module.solve_heavy_scalar_eoms(
        theory,
        lagrangian,
        eft_order=6,
    )
    requirements = matching_module._term_atom_requirements_for_targets(
        theory,
        {condition_name: target},
        heavy_scalar_solutions=heavy_scalar_solutions,
    )
    full_plan = setup.interaction_wilson_line_expansion_plan(
        trace_names=("hScalar-lScalar-lVector-lScalar",),
        max_total_order=2,
        max_slot_order=2,
        index_prefix="singlet_chd_order12",
    )
    entries = tuple(entry for entry in full_plan.entries if entry.total_order in (1, 2))
    plan = matching_module.WilsonLineExpansionPlan(
        theory=full_plan.theory,
        entries=entries,
        trace_names=full_plan.trace_names,
        max_total_order=2,
        max_slot_order=2,
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
    order_by_entry = {entry.label: entry.total_order for entry in entries}
    counts_by_order: dict[int, dict[str, int]] = {1: {}, 2: {}}
    finite_by_order: dict[int, Expression] = {}
    normalization = one_loop_normalization_factor(OneLoopNormalization.MATCHETE_EVALUATED_HBAR, hbar=hbar)
    for entry_label, entry_terms in evaluated_by_entry.items():
        if not entry_terms:
            continue
        order = order_by_entry[entry_label]
        counts_by_order[order][entry_label] = len(entry_terms)
        finite = (normalization * vakint_backend.finite_part(sum(entry_terms, Expression.num(0)))).expand()
        finite_by_order[order] = (finite_by_order.get(order, Expression.num(0)) + finite).expand()

    projections: dict[int, Expression] = {}
    for order, finite in finite_by_order.items():
        post_commutator = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
            theory,
            finite,
        )
        result = MatchingResult(
            theory=theory,
            uv_lagrangian=Expression.num(0),
            off_shell_eft_lagrangian=Expression.num(0),
            on_shell_eft_lagrangian=post_commutator,
        )
        projections[order] = result.project_matching_conditions(
            {condition_name: target},
            expand_source=False,
            normalize_derivative_operators=True,
            eft_order=6,
        )[condition_name]
    return theory, projections, counts_by_order


@cache
def _selected_chd_four_slot_post_heavy_path_projection_map() -> tuple[
    Theory,
    dict[int, Expression],
    dict[int, tuple[int, int, int]],
]:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    condition_name, target = _selected_chd_four_slot_target(theory)
    hbar = theory.external_handle("hbar")()
    lagrangian = fixture.expression("lagrangian")
    setup = theory.one_loop_setup(
        lagrangian,
        eft_order=6,
        max_trace_order=4,
    )
    paths = setup.interaction_wilson_line_trace_paths_by_trace(
        trace_names=("hScalar-lScalar-lVector-lScalar",),
    )["hScalar-lScalar-lVector-lScalar"]
    heavy_scalar_solutions = matching_module.solve_heavy_scalar_eoms(
        theory,
        lagrangian,
        eft_order=6,
    )
    requirements = matching_module._term_atom_requirements_for_targets(
        theory,
        {condition_name: target},
        heavy_scalar_solutions=heavy_scalar_solutions,
    )
    replacement_rules = matching_module.heavy_scalar_solution_replacements(
        heavy_scalar_solutions,
        fresh_dummy_indices=True,
    )
    projections: dict[int, Expression] = {}
    counts: dict[int, tuple[int, int, int]] = {}
    for path_index in (0, 2, 12, 14, 24, 26, 36, 38):
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
        filtered_terms = matching_module._filter_wilson_line_terms_by_projection_requirements(
            terms,
            requirements,
        )
        evaluated_by_entry = matching_module._wilson_line_internal_evaluated_terms_by_entry_from_terms(
            theory,
            {f"path{path_index}": filtered_terms},
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
        evaluated_terms = evaluated_by_entry[f"path{path_index}"]
        selected = sum(evaluated_terms, Expression.num(0))
        normalized_finite = (
            one_loop_normalization_factor(OneLoopNormalization.MATCHETE_EVALUATED_HBAR, hbar=hbar)
            * vakint_backend.finite_part(selected)
        ).expand()
        post_heavy = normalized_finite.replace_multiple(replacement_rules, repeat=False).expand()
        post_commutator = matching_module._apply_wilson_line_post_integral_scalar_commutator_bilinears(
            theory,
            post_heavy,
        )
        result = MatchingResult(
            theory=theory,
            uv_lagrangian=Expression.num(0),
            off_shell_eft_lagrangian=Expression.num(0),
            on_shell_eft_lagrangian=post_commutator,
        )
        projections[path_index] = result.project_matching_conditions(
            {condition_name: target},
            expand_source=False,
            normalize_derivative_operators=True,
            eft_order=6,
        )[condition_name]
        counts[path_index] = (len(terms), len(filtered_terms), len(evaluated_terms))
    return theory, projections, counts


def _matchete_xterm_signatures(replacement: str) -> tuple[tuple[str, int, int, int], ...]:
    return tuple(
        (
            fields.replace("Matchete`PackageScope`", "").replace("\\[Phi]", "phi"),
            int(base_order),
            int(momentum_order),
            int(open_cd_order),
        )
        for fields, base_order, momentum_order, open_cd_order in _MATHEMATICA_XTERM_PATTERN.findall(replacement)
    )


def _matchete_nonzero_target_insertion_indices(debug: dict[str, object]) -> list[int]:
    insertions = debug["insertions"]
    assert isinstance(insertions, list)
    return [
        insertion["index"]
        for insertion in insertions
        if isinstance(insertion, dict)
        and insertion.get("validation_simplified_target_coefficient_input_form") not in ("0", "$Failed")
    ]


@pytest.mark.parametrize(
    ("condition_name", "expected_term_count", "expected_nonzero_entries"),
    (
        ("cHW", 10, ("hScalar-lScalar#wilson14_o4_0",)),
        ("cHB", 10, ("hScalar-lScalar#wilson14_o4_0",)),
        ("cHWB", 14, ("hScalar-lScalar#wilson5_o2_0", "hScalar-lScalar#wilson14_o4_0")),
    ),
)
def test_selected_higgs_gauge_partial_wilson_coefficient_matches_matchete_subset(
    condition_name: str,
    expected_term_count: int,
    expected_nonzero_entries: tuple[str, ...],
) -> None:
    theory, projected, metadata = _selected_higgs_gauge_projection((condition_name,))

    assert set(projected) == {condition_name}
    assert metadata["plan_entry_count"] == 15
    assert metadata["nonzero_plan_entry_count"] == len(expected_nonzero_entries)
    assert metadata["term_count"] == expected_term_count
    assert metadata["nonzero_plan_entries"] == expected_nonzero_entries
    assert_expr_equal(projected[condition_name], _selected_higgs_gauge_expected(theory, condition_name))


@pytest.mark.slow
def test_public_match_selected_higgs_gauge_wilson_subset_matches_matchete_fixture() -> None:
    _, report, condition_names = _public_selected_higgs_gauge_gap_report()
    expected_names = tuple(sorted(condition_names.values()))

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
@pytest.mark.parametrize("condition_name", ("cHW", "cHB", "cHWB"))
def test_public_match_selected_higgs_gauge_partial_wilson_coefficient_is_accepted(
    condition_name: str,
) -> None:
    _, report, condition_names = _public_selected_higgs_gauge_gap_report()
    target_condition = condition_names[condition_name]

    assert report.candidate_metadata["fixture_preview_source"] == "public_match_api"
    assert target_condition in report.candidate_matching_condition_names
    assert target_condition in report.reference_matching_condition_names
    assert target_condition in report.accepted_common_wilson_matching_condition_names
    assert target_condition not in report.different_after_probe_common_wilson_matching_condition_names


@pytest.mark.slow
def test_public_match_selected_chd_four_slot_wilson_coefficient_records_current_source_frontier() -> None:
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
    assert isinstance(result, MatchingResult)
    projected = result.matching_conditions[condition_name]
    mass = theory.coupling_handle("M")()
    expected = (
        hbar
        * theory.coupling_handle("A")() ** 2
        * theory.coupling_handle("gY")() ** 2
        * (4 * mass.log() - 2 * S("vakint::mursq").log() - Expression.num(2))
        / mass**4
    )

    assert result.metadata["wilson_line_terms_filtered_by_matching_targets"] is True
    # The indexed-variation fix exposes the full alpha-aware component
    # neighborhood for this older four-slot diagnostic. Matchete's committed
    # checkpoint still has eight target quarter insertions; pychete currently
    # keeps sixteen path copies and therefore overcounts this aggregate by a
    # factor of two. This is a multiplicity-preserving canonical-basis
    # frontier, not the active matched hScalar-lScalar B-vector replay.
    assert result.metadata["interaction_wilson_line_term_count"] == 16
    assert result.metadata["interaction_wilson_line_plan_entry_count"] == 1
    assert result.metadata["interaction_wilson_line_nonzero_plan_entries"] == (
        "hScalar-lScalar-lVector-lScalar#wilson0_o0_0_0_0",
    )
    assert_expr_equal((projected - 2 * expected).expand(), Expression.num(0))


@pytest.mark.slow
def test_public_match_selected_chd_hscalar_lscalar_eom_bridge_records_next_frontier() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    reference = load_validation_fixture(
        Path("assets/validation/pychete/Singlet_Scalar_Extension.matching_fixture.json")
    ).matching_result("matchete_previous")
    theory = fixture.theory()
    registered_targets = matching_results_module.registered_wilson_matching_condition_targets(theory, basis="SMEFT")
    condition_name, target = next(
        (name, target)
        for name, target in registered_targets.items()
        if "external_cHD" in name
    )

    result = theory.match(
        fixture.expression("lagrangian"),
        eft_order=6,
        loop_order=1,
        one_loop_options=OneLoopMatchOptions(
            max_trace_order=2,
            integral_backend=OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION,
            normalization=OneLoopNormalization.MATCHETE_EVALUATED_HBAR,
            hbar=theory.external_handle("hbar")(),
            wilson_line_trace_names=("hScalar-lScalar",),
            wilson_line_max_total_order=4,
            wilson_line_max_slot_order=4,
            wilson_line_index_prefix="public_singlet_cHD_hscalar_lscalar_eom_bridge",
            wilson_line_act_open_derivatives=True,
            wilson_line_emit_covariant_derivative_commutators=False,
            wilson_line_emit_covariant_derivative_commutator_passes=1,
            wilson_line_covariant_derivative_commutator_mode="all_distinct",
            wilson_line_expand_covariant_derivative_commutators=False,
            wilson_line_max_derivative_order=4,
            wilson_line_filter_terms_by_matching_targets=True,
            wilson_line_expose_scalar_derivative_commutator_bilinears=True,
            wilson_line_expose_scalar_eom_terms=True,
            wilson_line_tensor_reduce_before_wilson_expand=True,
            simplify_pychete_color_algebra=True,
            substitute_heavy_scalar_solutions=True,
            on_shell_eom_lagrangian=fixture.expression("lagrangian"),
            on_shell_eom_fields=[theory.field_handle("B")],
            on_shell_eom_abelian_vector_field_redefinition=True,
            truncate_eft_result=False,
        ),
        matching_condition_targets={condition_name: target},
        matching_condition_source="on_shell_eft_lagrangian",
        matching_condition_expand_source=False,
        matching_condition_truncate_eft=True,
        matching_condition_drop_zero=False,
    )

    assert isinstance(result, MatchingResult)
    projected = result.matching_conditions[condition_name]
    reference_projected = reference.matching_conditions[condition_name]
    projected_str = canonical_string(projected)

    assert result.metadata["heavy_scalar_solution_eft_limited"] is True
    assert result.metadata["wilson_line_scalar_eom_terms_reduced"] is True
    assert result.metadata["tensor_reduce"] is True
    assert result.metadata["on_shell_eom_reduction_deferred_to_wilson_line_scalar_eom"] is True
    assert result.metadata["interaction_wilson_line_scalar_derivative_commutator_bilinears_exposed"] is False
    assert result.metadata["wilson_line_scalar_commutator_abelian_vector_eom_reduction_rule_count"] == 3
    assert result.metadata["wilson_line_scalar_commutator_abelian_vector_field_redefinition_applied"] is True
    assert result.metadata["interaction_wilson_line_term_count"] == 32
    delta = result.supertraces["on_shell_eft_lagrangian_scalar_commutator_abelian_vector_field_redefinition_delta"]
    delta_projection = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=delta,
        on_shell_eft_lagrangian=delta,
    ).project_matching_conditions(
        {condition_name: target},
        expand_source=False,
        normalize_derivative_operators=True,
        eft_order=6,
        drop_zero=False,
    )[condition_name]
    mass = theory.coupling_handle("M")()
    selected_vector_delta = (
        theory.external_handle("hbar")()
        * theory.coupling_handle("A")() ** 2
        * theory.coupling_handle("gY")() ** 2
        * (-S("vakint::mursq").log() / 12 + mass.log() / 6 - Expression.num(17) / 72)
        / mass**4
    )
    assert_expr_equal((delta_projection - selected_vector_delta).expand(), Expression.num(0))
    assert "coupling_gY" in projected_str
    assert "coupling_kappa" in projected_str
    assert "coupling_muphi" in projected_str
    assert not bool((projected - reference_projected).expand() == Expression.num(0))


@pytest.mark.parametrize("path_index", (0, 12, 26, 38))
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
    assert "selected_scalar_vector_xterm_values_input_form" in debug
    assert_expr_equal((projected - expected).expand(), Expression.num(0))


def test_selected_chd_four_slot_post_heavy_path_projection_map_records_frontier() -> None:
    debug = json.loads(_SINGLET_CHD_FOUR_SLOT_FULL_DEBUG.read_text(encoding="utf-8"))
    theory, projections, counts = _selected_chd_four_slot_post_heavy_path_projection_map()
    expected_quarter = _selected_chd_four_slot_quarter_finite_expected(theory)

    assert debug["trace_name"] == "hScalar-lScalar-lVector-lScalar"
    assert debug["target"] == "cHD"
    assert set(projections) == {0, 2, 12, 14, 24, 26, 36, 38}
    assert counts == {
        0: (1, 1, 1),
        2: (1, 1, 1),
        12: (1, 1, 1),
        14: (1, 1, 1),
        24: (1, 1, 1),
        26: (1, 1, 1),
        36: (1, 1, 1),
        38: (1, 1, 1),
    }
    for path_index in sorted(projections):
        assert_expr_equal((projections[path_index] - expected_quarter).expand(), Expression.num(0))

    # Matchete records eight equivalent quarter checkpoints in the full
    # insertion dump. pychete currently keeps all eight component/dummy-index
    # path copies because collapsing them requires explicit multiplicity
    # weights, not just canonical dummy-label normalization.
    quarter_insertions = [
        insertion["index"]
        for insertion in debug["insertions"]
        if "(-1/4*" in insertion["validation_simplified_prefactored_evaluate_str_input_form"]
    ]
    assert quarter_insertions == [1, 3, 12, 14, 45, 47, 56, 58]


def test_selected_chd_four_slot_matchete_fixture_records_scalar_vector_frontier() -> None:
    debug = json.loads(_SINGLET_CHD_FOUR_SLOT_FULL_DEBUG.read_text(encoding="utf-8"))
    assert debug["trace_name"] == "hScalar-lScalar-lVector-lScalar"
    assert debug["target"] == "cHD"
    assert debug["prop_order"] == 0
    assert debug["insertion_count"] == 88
    assert debug["detailed_insertion_count"] == 88
    assert debug["selected_prop_order_target_coefficient_input_form"] == "$Failed"
    assert "-1/4*" in debug["previous_validation_trace_target_coefficient_input_form"]
    assert "6 + 5*\\[Epsilon] + 6*\\[Epsilon]*Log" in (
        debug["previous_validation_trace_target_coefficient_input_form"]
    )

    scalar_vector_orders = debug["selected_scalar_vector_x_orders_input_form"]
    scalar_vector_values = debug["selected_scalar_vector_xterm_values_input_form"]
    assert "{H, B} -> {{2, 0}, {1, 1}}" in scalar_vector_orders
    assert "{B, H} -> {{2, 0}, {1, 1}}" in scalar_vector_orders
    assert "LoopMom" in scalar_vector_values
    assert "OpenCD" in scalar_vector_values
    assert "Coupling[gY" in scalar_vector_values

    nonzero_a2_gy2_insertions = []
    quarter_insertions = []
    for insertion in debug["insertions"]:
        simplified = insertion["validation_simplified_prefactored_evaluate_str_input_form"]
        if simplified == "0":
            continue
        if (
            "Coupling[A" in simplified
            and "Coupling[gY" in simplified
            and "Coupling[\\[Kappa]" not in simplified
            and "Coupling[gL" not in simplified
        ):
            nonzero_a2_gy2_insertions.append(
                (insertion["index"], _matchete_xterm_signatures(insertion["replacement_input_form"]))
            )
        if "(-1/4*" in simplified:
            quarter_insertions.append(insertion["index"])

    target_quarter_insertions = [
        insertion["index"]
        for insertion in debug["insertions"]
        if insertion["validation_simplified_target_coefficient_input_form"].startswith("-1/4*")
    ]
    target_quarter_coefficients = {
        insertion["validation_simplified_target_coefficient_input_form"]
        for insertion in debug["insertions"]
        if insertion["index"] in target_quarter_insertions
    }

    assert len(nonzero_a2_gy2_insertions) == 20
    assert quarter_insertions == [1, 3, 12, 14, 45, 47, 56, 58]
    assert target_quarter_insertions == [1, 3, 12, 14, 45, 47, 56, 58]
    assert len(target_quarter_coefficients) == 1
    assert "1 + \\[Epsilon] + \\[Epsilon]*Log" in next(iter(target_quarter_coefficients))


def test_selected_chd_hscalar_lscalar_prop_order_four_dump_records_bilinear_frontier() -> None:
    debug = json.loads(_SINGLET_CHD_HSCALAR_LSCALAR_PROP4_DEBUG.read_text(encoding="utf-8"))

    assert debug["trace_name"] == "hScalar-lScalar"
    assert debug["target"] == "cHD"
    assert debug["prop_order"] == 4
    assert debug["skip_full_trace"] is True
    assert debug["skip_slot_order_summaries"] is True
    assert debug["power_prefactor_input_form"] == "(-1/2*I)*hbar"
    assert debug["insertion_count"] == 2
    assert debug["detailed_insertion_count"] == 2

    insertions = debug["insertions"]
    assert [insertion["index"] for insertion in insertions] == [1, 2]
    assert "Xterm[{\\[Phi], H}" in insertions[0]["replacement_input_form"]
    assert "Xterm[{H, \\[Phi]}" in insertions[0]["replacement_input_form"]
    assert "Xterm[{\\[Phi], Matchete`PackageScope`Conj[H]}" in insertions[1]["replacement_input_form"]
    assert "Xterm[{Matchete`PackageScope`Conj[H], \\[Phi]}" in insertions[1]["replacement_input_form"]

    coefficients_by_insertion = [
        {
            row["signature"]: row["coefficient_input_form"]
            for row in insertion["prefactored_evaluate_str_reference_h_bilinear_coefficients"]
        }
        for insertion in insertions
    ]
    assert set(coefficients_by_insertion[0]) == {"bar=0;field=aabb", "bar=0;field=abab", "bar=0;field=abba"}
    assert set(coefficients_by_insertion[1]) == {"bar=aabb;field=0", "bar=abab;field=0", "bar=abba;field=0"}
    assert "- 4*hbar*\\[Epsilon]*Coupling[A" in coefficients_by_insertion[0]["bar=0;field=aabb"]
    assert "+ 5*hbar*\\[Epsilon]*Coupling[A" in coefficients_by_insertion[0]["bar=0;field=abab"]
    assert "+ hbar*\\[Epsilon]*Coupling[A" in coefficients_by_insertion[0]["bar=0;field=abba"]
    assert coefficients_by_insertion[1]["bar=aabb;field=0"] == coefficients_by_insertion[0]["bar=0;field=aabb"]
    assert coefficients_by_insertion[1]["bar=abab;field=0"] == coefficients_by_insertion[0]["bar=0;field=abab"]
    assert coefficients_by_insertion[1]["bar=abba;field=0"] == coefficients_by_insertion[0]["bar=0;field=abba"]


@pytest.mark.slow
def test_selected_chd_four_slot_prop_order_one_two_match_matchete_dumps() -> None:
    prop1_debug = json.loads(_SINGLET_CHD_FOUR_SLOT_PROP1_DEBUG.read_text(encoding="utf-8"))
    prop2_debug = json.loads(_SINGLET_CHD_FOUR_SLOT_PROP2_DEBUG.read_text(encoding="utf-8"))
    theory, projections, counts = _selected_chd_four_slot_finite_projection_by_total_order()

    assert prop1_debug["trace_name"] == "hScalar-lScalar-lVector-lScalar"
    assert prop1_debug["target"] == "cHD"
    assert prop1_debug["prop_order"] == 1
    assert prop1_debug["insertion_count"] == 40
    assert _matchete_nonzero_target_insertion_indices(prop1_debug) == [
        1,
        2,
        4,
        6,
        7,
        9,
        21,
        22,
        24,
        26,
        27,
        29,
    ]
    assert prop2_debug["trace_name"] == "hScalar-lScalar-lVector-lScalar"
    assert prop2_debug["target"] == "cHD"
    assert prop2_debug["prop_order"] == 2
    assert prop2_debug["insertion_count"] == 8
    assert _matchete_nonzero_target_insertion_indices(prop2_debug) == [1, 2, 5, 6]

    assert counts[1] == {
        "hScalar-lScalar-lVector-lScalar#wilson2_o0_0_1_0": 8,
        "hScalar-lScalar-lVector-lScalar#wilson3_o0_1_0_0": 8,
        "hScalar-lScalar-lVector-lScalar#wilson4_o1_0_0_0": 8,
    }
    assert counts[2] == {
        "hScalar-lScalar-lVector-lScalar#wilson7_o0_0_2_0": 16,
        "hScalar-lScalar-lVector-lScalar#wilson9_o0_1_1_0": 8,
        "hScalar-lScalar-lVector-lScalar#wilson10_o0_2_0_0": 16,
        "hScalar-lScalar-lVector-lScalar#wilson12_o1_0_1_0": 8,
        "hScalar-lScalar-lVector-lScalar#wilson13_o1_1_0_0": 8,
        "hScalar-lScalar-lVector-lScalar#wilson14_o2_0_0_0": 16,
    }
    assert_expr_equal(
        (projections[1] - _selected_chd_four_slot_order_one_finite_expected(theory)).expand(),
        Expression.num(0),
    )
    assert_expr_equal(
        (projections[2] - _selected_chd_four_slot_order_two_finite_expected(theory)).expand(),
        Expression.num(0),
    )


def test_singlet_chd_matchete_eom_dump_records_dim6_dev3_shift_boundary() -> None:
    debug = json.loads(_SINGLET_CHD_MATCHETE_EOM_DEBUG.read_text(encoding="utf-8"))
    raw = debug["raw_lagrangian_eft_eom_boundary"]
    replay = raw["internal_field_redefinition_replay"]
    stages = {stage["name"]: stage for stage in replay["stages"]}

    assert raw["fields_to_shift_input_form"] == "{{d, 4}, {e, 4}, {H, 4}, {l, 4}, {q, 4}, {u, 4}}"
    assert raw["internal_fields_to_shift_preparation"]["eom_term_count"] == 105
    assert raw["internal_fields_to_shift_preparation"]["eom_field_labels_input_form"] == (
        "{H, B, d, e, u, l, q, W}"
    )
    assert raw["internal_higgs_scalar_shift_summary"]["eom_terms_containing_h_count"] == 105
    assert "Field[{H, _, 1}" in raw["internal_higgs_scalar_shift_summary"]["rules_input_form"]

    assert replay["source_name"] == "raw_internal_after_internal_simplify"
    assert replay["fields_to_shift_input_form"] == "{{H, 4}, {B, 6}, {d, 6}, {e, 6}, {l, 6}, {q, 6}, {u, 6}, {W, 6}}"
    assert stages["source"]["delta_from_replay_source_input_form"] == "0"
    assert stages["after_renormalize_matter"]["delta_from_replay_source_input_form"] == "0"
    assert stages["after_shift_dim6_dev4"]["delta_from_replay_source_input_form"] == "0"
    assert "6 + 17*\\[Epsilon] + 6*\\[Epsilon]*Log" in (
        stages["after_shift_dim6_dev3"]["delta_from_replay_source_input_form"]
    )
    assert stages["after_shift_dim6_dev3"]["selection_before_shift"]["selected_term_count"] == 12
    assert len(stages["after_shift_dim6_dev3"]["selection_before_shift"]["selected_eom_terms_input_form"]) == 12
    assert stages["after_shift_dim6_dev3"]["coefficient_input_form"] == (
        stages["after_shift_dim6_dev2"]["coefficient_input_form"]
    )
    assert stages["after_shift_dim6_dev3"]["coefficient_input_form"] == (
        stages["after_shift_dim6_dev1"]["coefficient_input_form"]
    )


def test_selected_chd_pychete_boundary_fixture_records_pre_eom_gap() -> None:
    debug = json.loads(_SINGLET_CHD_PYCHETE_EOM_BOUNDARY_DEBUG.read_text(encoding="utf-8"))
    references = debug["reference_projections"]
    projections = debug["selected_stage_projections"]
    projections_by_order = debug["selected_stage_projections_by_total_order"]
    eom_probe = debug["eom_exposure_probe_summary"]
    source_trace_probe = debug["source_trace_vector_eom_probe"]

    assert debug["generator"] == "scripts/debug_pychete_singlet_eom_boundary.py"
    assert debug["target"] == "cHD"
    assert debug["controls"]["max_total_order"] == 2
    assert debug["controls"]["max_slot_order"] == 2
    assert debug["controls"]["include_green_heavy_stages"] is False
    nonzero_entry_counts = {
        entry: count
        for entry, count in debug["term_counts_by_entry"].items()
        if count
    }
    assert nonzero_entry_counts == {
        "hScalar-lScalar-lVector-lScalar#wilson0_o0_0_0_0": 16,
        "hScalar-lScalar-lVector-lScalar#wilson2_o0_0_1_0": 16,
        "hScalar-lScalar-lVector-lScalar#wilson3_o0_1_0_0": 16,
        "hScalar-lScalar-lVector-lScalar#wilson4_o1_0_0_0": 16,
        "hScalar-lScalar-lVector-lScalar#wilson7_o0_0_2_0": 32,
        "hScalar-lScalar-lVector-lScalar#wilson9_o0_1_1_0": 16,
        "hScalar-lScalar-lVector-lScalar#wilson10_o0_2_0_0": 32,
        "hScalar-lScalar-lVector-lScalar#wilson12_o1_0_1_0": 16,
        "hScalar-lScalar-lVector-lScalar#wilson13_o1_1_0_0": 16,
        "hScalar-lScalar-lVector-lScalar#wilson14_o2_0_0_0": 32,
    }
    assert debug["term_counts_by_total_order"] == {"0": 16, "1": 48, "2": 144}
    assert debug["evaluated_term_counts_by_total_order"] == {"0": 16, "1": 48, "2": 144}
    assert references["matchete_trace_off_shell_input_form"] == references["matchete_eom_off_shell_input_form"]
    assert "6 + 5*\\[Epsilon] + 6*\\[Epsilon]*Log" in references["matchete_eom_off_shell_input_form"]
    assert "30 + 31*\\[Epsilon] + 30*\\[Epsilon]*Log" in references["matchete_eom_on_shell_input_form"]
    assert "representative-conversion boundary" in debug["first_differing_boundary"]
    assert "dim6/dev3 vector EOM selection over B/W" in debug["first_differing_boundary"]
    assert "hScalar-lScalar order-four Wilson-line trace" in debug["first_differing_boundary"]
    assert eom_probe == {
        "entry_count": 10,
        "field_strength_count": 0,
        "formal_vector_eom_count": 0,
        "nonzero_scalar_eom_exposed_heavy_vector_field_redefinition_delta_entry_count": 1,
        "nonzero_scalar_eom_exposed_heavy_vector_field_redefinition_delta_projection_entry_count": 0,
        "nonzero_scalar_eom_exposed_vector_field_redefinition_delta_entry_count": 1,
        "nonzero_scalar_eom_exposed_vector_field_redefinition_delta_projection_entry_count": 0,
        "nonzero_scalar_eom_field_redefinition_delta_entry_count": 4,
        "nonzero_vector_eom_current_exposed_delta_entry_count": 0,
        "nonzero_vector_field_redefinition_delta_entry_count": 0,
        "scalar_eom_exposed_formal_eom_count": 41,
        "scalar_eom_exposed_formal_vector_eom_count": 1,
        "scalar_eom_exposed_heavy_vector_field_redefinition_delta_error_count": 0,
        "scalar_eom_exposed_heavy_vector_field_redefinition_delta_projection_sum": "0",
        "scalar_eom_exposed_vector_field_redefinition_delta_error_count": 0,
        "scalar_eom_exposed_vector_field_redefinition_delta_projection_sum": "0",
        "scalar_eom_exposed_vector_field_strength_divergence_count": 0,
        "scalar_eom_exposure_error_count": 0,
        "scalar_eom_field_redefinition_delta_error_count": 0,
        "scalar_eom_identity_count": 28,
        "vector_eom_current_exposed_field_strength_divergence_count": 0,
        "vector_field_strength_divergence_count": 0,
    }
    assert {
        row["scalar_eom_exposure_error"]
        for row in debug["eom_exposure_probe_by_entry"].values()
        if row["scalar_eom_exposure_error"] is not None
    } == set()
    assert {
        row["scalar_eom_field_redefinition_delta_is_zero"]
        for row in debug["eom_exposure_probe_by_entry"].values()
    } == {False, True}
    assert {
        entry
        for entry, row in debug["eom_exposure_probe_by_entry"].items()
        if row["scalar_eom_exposed_formal_eom_count"]
    } == {
        "hScalar-lScalar-lVector-lScalar#wilson0_o0_0_0_0",
        "hScalar-lScalar-lVector-lScalar#wilson10_o0_2_0_0",
        "hScalar-lScalar-lVector-lScalar#wilson12_o1_0_1_0",
        "hScalar-lScalar-lVector-lScalar#wilson13_o1_1_0_0",
        "hScalar-lScalar-lVector-lScalar#wilson14_o2_0_0_0",
        "hScalar-lScalar-lVector-lScalar#wilson2_o0_0_1_0",
        "hScalar-lScalar-lVector-lScalar#wilson3_o0_1_0_0",
        "hScalar-lScalar-lVector-lScalar#wilson4_o1_0_0_0",
        "hScalar-lScalar-lVector-lScalar#wilson7_o0_0_2_0",
        "hScalar-lScalar-lVector-lScalar#wilson9_o0_1_1_0",
    }
    assert debug["eom_exposure_probe_by_entry"]["hScalar-lScalar-lVector-lScalar#wilson0_o0_0_0_0"][
        "scalar_eom_identity_count"
    ] == 0
    assert debug["eom_exposure_probe_by_entry"]["hScalar-lScalar-lVector-lScalar#wilson14_o2_0_0_0"][
        "scalar_eom_identity_count"
    ] == 10
    assert source_trace_probe["controls"]["trace_name"] == "hScalar-lScalar"
    assert source_trace_probe["controls"]["max_total_order"] == 4
    assert source_trace_probe["controls"]["filter_terms_by_matching_targets"] is True
    assert source_trace_probe["term_counts_by_total_order"] == {"0": 4, "1": 0, "2": 8, "3": 0, "4": 20}
    stage_probe = source_trace_probe["pre_wilson_stage_probe"]
    assert stage_probe["entry_label"] == "hScalar-lScalar#wilson14_o4_0"
    assert stage_probe["source_exposure_stages"] == [
        "matchete_contract_before_wilson_topology_lowered",
        "topology_lowered",
    ]
    assert stage_probe["by_stage"]["pre_wilson_numerator"]["source_operator_projection_skipped"] == (
        "metadata-only stage"
    )
    assert stage_probe["by_stage"]["symgamma_formal_uncontracted"]["byte_count"] > (
        stage_probe["by_stage"]["postprocessed_numerator"]["byte_count"]
    )
    assert stage_probe["by_stage"]["topology_lowered"]["byte_count"] < 150_000
    assert (
        stage_probe["by_stage"]["topology_lowered"][
            "scalar_eom_exposed_source_operator_projections"
        ]
        == stage_probe["by_stage"]["matchete_contract_before_wilson_topology_lowered"][
            "scalar_eom_exposed_source_operator_projections"
        ]
    )
    assert stage_probe["by_stage"]["topology_lowered"][
        "nonzero_scalar_eom_exposed_source_operator_projection_names"
    ] == [
        "barH_EOMB_DH",
        "DbarH_EOMB_H",
        "H_EOMB_DH_unbarred",
        "DH_EOMB_H_unbarred",
    ]
    assert source_trace_probe["summary"]["entry_count"] == 3
    assert source_trace_probe["summary"]["nonzero_vector_field_redefinition_delta_entry_count"] == 1
    assert source_trace_probe["summary"]["nonzero_vector_field_redefinition_delta_projection_entry_count"] == 1
    assert source_trace_probe["summary"]["scalar_eom_exposed_formal_vector_eom_count"] == 3
    source_projection = source_trace_probe["summary"]["vector_field_redefinition_delta_projection_sum"]
    assert "Coupling(Singlet_Scalar_Extension::coupling_A" in source_projection
    assert "Coupling(Singlet_Scalar_Extension::coupling_gY" in source_projection
    assert "vakint::ε" in source_projection
    source_operator_projections = source_trace_probe["summary"][
        "formal_vector_eom_source_operator_projection_sums"
    ]
    formal_symgamma_source_operator_projections = source_trace_probe["summary"][
        "formal_symgamma_topology_source_operator_projection_sums"
    ]
    assert set(source_operator_projections) == {
        "barH_EOMB_DH",
        "DbarH_EOMB_H",
        "H_EOMB_DH_unbarred",
        "DH_EOMB_H_unbarred",
    }
    assert "-1𝑖/12*Singlet_Scalar_Extension::external_hbar*log(vakint::mursq)" in (
        source_operator_projections["DbarH_EOMB_H"]
    )
    assert "-17𝑖/72*Singlet_Scalar_Extension::external_hbar*" in (
        source_operator_projections["DbarH_EOMB_H"]
    )
    assert "1𝑖/12*Singlet_Scalar_Extension::external_hbar*log(vakint::mursq)" in (
        source_operator_projections["barH_EOMB_DH"]
    )
    assert "+17𝑖/72*Singlet_Scalar_Extension::external_hbar*" in (
        source_operator_projections["barH_EOMB_DH"]
    )
    assert "-3𝑖/4*Singlet_Scalar_Extension::external_hbar*" in (
        source_operator_projections["H_EOMB_DH_unbarred"]
    )
    assert set(formal_symgamma_source_operator_projections) == {
        "barH_EOMB_DH",
        "DbarH_EOMB_H",
        "H_EOMB_DH_unbarred",
        "DH_EOMB_H_unbarred",
    }
    formal_dbar_source = formal_symgamma_source_operator_projections["DbarH_EOMB_H"]
    assert "16*𝜋^2*Singlet_Scalar_Extension::external_hbar*" in formal_dbar_source
    assert "pychete::SymGammaFactor(1,4)" in formal_dbar_source
    assert "-128*𝜋^2*Singlet_Scalar_Extension::external_hbar*" in formal_dbar_source
    assert "pychete::SymGammaFactor(2,4)" in formal_dbar_source
    assert "2*𝜋^2*Singlet_Scalar_Extension::external_hbar*" not in formal_dbar_source
    assert "vakint::topo(vakint::prop(1" in formal_dbar_source
    formal_bar_source = formal_symgamma_source_operator_projections["barH_EOMB_DH"]
    assert "-16*𝜋^2*Singlet_Scalar_Extension::external_hbar*" in formal_bar_source
    assert "pychete::SymGammaFactor(1,4)" in formal_bar_source
    assert "128*𝜋^2*Singlet_Scalar_Extension::external_hbar*" in formal_bar_source
    assert "pychete::SymGammaFactor(2,4)" in formal_bar_source
    assert "-2*𝜋^2*Singlet_Scalar_Extension::external_hbar*" not in formal_bar_source
    assert "vakint::topo(vakint::prop(1" in formal_bar_source
    assert source_trace_probe["summary"][
        "nonzero_formal_symgamma_topology_source_operator_projection_names"
    ] == [
        "barH_EOMB_DH",
        "DbarH_EOMB_H",
        "H_EOMB_DH_unbarred",
        "DH_EOMB_H_unbarred",
    ]
    assert source_trace_probe["summary"][
        "nonzero_formal_vector_eom_source_operator_projection_names"
    ] == [
        "barH_EOMB_DH",
        "DbarH_EOMB_H",
        "H_EOMB_DH_unbarred",
        "DH_EOMB_H_unbarred",
    ]
    assert {
        entry
        for entry, row in source_trace_probe["by_entry"].items()
        if not row["vector_field_redefinition_delta_projection_is_zero"]
    } == {"hScalar-lScalar#wilson14_o4_0"}
    assert source_trace_probe["by_entry"]["hScalar-lScalar#wilson14_o4_0"][
        "nonzero_formal_vector_eom_source_operator_projection_names"
    ] == [
        "barH_EOMB_DH",
        "DbarH_EOMB_H",
        "H_EOMB_DH_unbarred",
        "DH_EOMB_H_unbarred",
    ]
    assert {
        entry
        for entry, row in source_trace_probe["formal_symgamma_by_entry"].items()
        if row["nonzero_formal_vector_eom_source_operator_projection_names"]
    } == {"hScalar-lScalar#wilson14_o4_0"}
    assert source_trace_probe["formal_symgamma_raw_term_counts_by_entry"]["hScalar-lScalar#wilson14_o4_0"] == 20
    assert debug["matchete_quarter_insertion_count"] == 8
    assert [row["index"] for row in debug["matchete_quarter_insertions"]] == [
        1,
        3,
        12,
        14,
        45,
        47,
        56,
        58,
    ]
    expected_paths = {
        f"path{index}": 13
        for index in (
            0,
            1,
            2,
            3,
            12,
            13,
            14,
            15,
            24,
            25,
            26,
            27,
            36,
            37,
            38,
            39,
        )
    }
    assert debug["pychete_nonzero_path_count"] == 16
    assert debug["term_counts_by_path"] == expected_paths
    assert debug["evaluated_term_counts_by_path"] == {}
    assert projections_by_order["selected_normalized_pole_part"]["0"].startswith(
        "-4*Singlet_Scalar_Extension::external_hbar*"
    )
    assert projections_by_order["selected_normalized_pole_part"]["1"].startswith(
        "2*Singlet_Scalar_Extension::external_hbar*"
    )
    assert projections_by_order["selected_normalized_pole_part"]["2"].startswith(
        "-Singlet_Scalar_Extension::external_hbar*"
    )
    assert projections["selected_normalized_pole_part"].startswith(
        "-3*Singlet_Scalar_Extension::external_hbar*"
    )
    assert "vakint::ε" in projections["selected_normalized_pole_part"]
    assert "-5/2*Singlet_Scalar_Extension::external_hbar*" in projections["selected_normalized_finite_part"]
    assert "selected_post_heavy_green" not in projections
    assert projections["selected_normalized_evaluated"] != references["pychete_reference_on_shell"]


def test_selected_chd_pychete_source_fixture_records_filtered_frontier() -> None:
    debug = json.loads(_SINGLET_CHD_PYCHETE_SOURCE_DEBUG.read_text(encoding="utf-8"))
    unfiltered_debug = json.loads(_SINGLET_CHD_PYCHETE_UNFILTERED_SOURCE_DEBUG.read_text(encoding="utf-8"))
    entry = "hScalar-lScalar-lVector-lScalar#wilson0_o0_0_0_0"

    assert debug["generator"] == "debug_pychete_singlet_wilson_trace.py"
    assert debug["mode"] == "source_only"
    assert debug["trace_name"] == "hScalar-lScalar-lVector-lScalar"
    assert debug["target"] == "cHD"
    assert debug["filter_terms_by_matching_targets"] is True
    assert debug["plan_entry_count"] == 1
    assert debug["plan_entries"] == [
        {
            "label": entry,
            "slot_orders": [0, 0, 0, 0],
            "total_order": 0,
            "trace_name": "hScalar-lScalar-lVector-lScalar",
        },
    ]
    assert debug["preaction_prefilter_nonempty_grouped_entries"] == {entry: 8}
    assert debug["prefinal_nonempty_grouped_entries"] == {entry: 8}
    assert debug["runtime_internal_nonempty_grouped_entries"] == {entry: 8}
    assert debug["preaction_prefilter_term_counts_by_total_order"] == {"0": 8}
    assert debug["prefinal_term_counts_by_total_order"] == {"0": 8}
    assert debug["runtime_internal_term_counts_by_total_order"] == {"0": 8}
    assert unfiltered_debug["filter_terms_by_matching_targets"] is False
    assert unfiltered_debug["preaction_prefilter_nonempty_grouped_entries"] == {entry: 8}
    assert unfiltered_debug["prefinal_nonempty_grouped_entries"] == {entry: 8}
    assert unfiltered_debug["runtime_internal_nonempty_grouped_entries"] == {entry: 8}
    assert unfiltered_debug["preaction_prefilter_term_counts_by_total_order"] == {"0": 8}
    assert unfiltered_debug["prefinal_term_counts_by_total_order"] == {"0": 8}
    assert unfiltered_debug["runtime_internal_term_counts_by_total_order"] == {"0": 8}


def test_registered_chd_filter_requirements_keep_vector_eom_alias_candidates() -> None:
    fixture = load_validation_fixture(Path("assets/validation/pychete/Singlet_Scalar_Extension.model_fixture.json"))
    theory = fixture.theory()
    condition_name, target = _selected_chd_four_slot_target(theory)
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

    h_label = canonical_string(theory.field_handle("H").label)
    phi_label = canonical_string(theory.field_handle("phi").label)
    b_label = canonical_string(theory.field_handle("B").label)
    assert requirements is not None
    assert (("field", h_label, 2), ("field_strength", b_label, 1)) in requirements
    assert (("field", phi_label, 1), ("field_strength", b_label, 1)) in requirements


def test_selected_chd_four_slot_wilson_coefficient_records_current_source_frontier() -> None:
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
        * (4 * mass.log() - 2 * S("vakint::mursq").log() - Expression.num(2))
        / mass**4
    )

    # Matchete's full prop-order-0 dump records eight target quarter
    # insertions. pychete currently keeps sixteen alpha-aware component paths
    # for this aggregate diagnostic, so the selected four-slot source remains
    # a factor-two multiplicity frontier after the indexed-variation fix.
    assert_expr_equal((projected[condition_name] - 2 * expected).expand(), Expression.num(0))

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

    # Projecting the aggregate post-heavy selected source needs the bounded
    # chunked termwise exact path: individual contributing Wilson-line paths
    # remain small, but the tensor-canonized aggregate exceeds the single-pass
    # projection byte guard.
    assert_expr_equal((post_commutator_projected[condition_name] - 2 * expected).expand(), Expression.num(0))
