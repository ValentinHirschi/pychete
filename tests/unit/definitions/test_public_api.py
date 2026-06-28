from __future__ import annotations

import inspect

import pychete
from pychete import api


def test_package_root_reexports_declared_public_api() -> None:
    assert pychete.__all__ == api.__all__
    for name in api.__all__:
        assert getattr(pychete, name) is getattr(api, name)


def test_smeft_module_is_compatibility_shim() -> None:
    """The Warsaw provider lives in pychete.bases; pychete.smeft is legacy."""

    import pychete.smeft as smeft_compat
    from pychete.bases import smeft_warsaw

    assert smeft_compat.smeft_warsaw_basis is smeft_warsaw.smeft_warsaw_basis
    assert smeft_compat.define_smeft_wilson_coefficient is smeft_warsaw.define_smeft_wilson_coefficient


def test_bundled_basis_provider_registers_generically() -> None:
    """Bundled bases are discoverable through the generic registry boundary."""

    import pychete.bases

    assert "SMEFT" in pychete.operator_basis_names()
    assert pychete.registered_operator_basis("SMEFT") is pychete.bases.smeft_warsaw_basis()


def test_package_root_does_not_export_optional_smeft_provider() -> None:
    """SMEFT Warsaw stays an optional basis provider, not a core root API."""

    smeft_names = {
        "SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES",
        "define_smeft_wilson_coefficient",
        "smeft_warsaw_basis",
        "smeft_warsaw_operator",
        "smeft_warsaw_operator_names",
    }

    assert smeft_names.isdisjoint(pychete.__all__)
    for name in smeft_names:
        assert not hasattr(pychete, name)


def test_lagrangian_manipulations_are_theory_methods_not_top_level_exports() -> None:
    assert "derive_eom" not in pychete.__all__
    assert "match_tree" not in pychete.__all__
    assert "solve_heavy_scalar_eoms" not in pychete.__all__
    assert not hasattr(pychete, "derive_eom")
    assert not hasattr(pychete, "match_tree")
    assert not hasattr(pychete, "solve_heavy_scalar_eoms")

    assert callable(pychete.Theory.derive_eom)
    assert callable(pychete.Theory.solve_heavy_scalar_eoms)
    assert callable(pychete.Theory.one_loop_setup)
    assert callable(pychete.Theory.match)


def test_validation_fixture_diagnostics_are_public_api() -> None:
    assert pychete.load_validation_fixture is api.load_validation_fixture
    assert pychete.ValidationFixture is api.ValidationFixture
    assert pychete.MatchingFixtureGapReport is api.MatchingFixtureGapReport
    assert pychete.SupertraceOrderCoverage is api.SupertraceOrderCoverage


def test_public_api_exports_have_docstrings() -> None:
    missing = [
        name
        for name in pychete.__all__
        if not inspect.getdoc(getattr(pychete, name))
    ]

    assert missing == []


def test_public_api_methods_have_docstrings() -> None:
    method_names = {
        pychete.Theory: [
            "define_index_type",
            "define_flavor_index",
            "index",
            "lorentz_index",
            "dummy_index",
            "define_coupling",
            "define_field",
            "field_handle",
            "coupling_handle",
            "cg_tensor_handle",
            "external_handle",
            "define_external",
            "define_wilson_coefficient",
            "define_cg_tensor",
            "define_gauge_group",
            "define_global_group",
            "define_representation",
            "representation_definition",
            "representation_dimension",
            "representation_reality",
            "is_conjugate_representation",
            "group_charge",
            "mass_expr",
            "non_abelian_gauge_generator_insertion",
            "covariant_derivative_commutator",
            "covariant_derivative_commutator_identities",
            "covariant_derivative_commutator_local_normal_form",
            "covariant_derivative_commutator_normal_form",
            "emit_covariant_derivative_commutators",
            "expand_covariant_derivative_commutators",
            "expand_non_abelian_covariant_derivatives",
            "expand_abelian_covariant_derivatives",
            "free_lag",
            "derive_eom",
            "eom_replacement_rule",
            "eom_replacement_rules_for_expression",
            "solve_heavy_scalar_eoms",
            "fluctuation_basis",
            "fluctuation_operator",
            "one_loop_setup",
            "match",
            "to_json_obj",
            "to_json",
            "write_json",
            "from_json_obj",
        ],
        pychete.FieldHandle: ["__call__"],
        pychete.CouplingHandle: ["__call__"],
        pychete.CGTensorHandle: ["__call__"],
        pychete.ExternalHandle: ["__call__"],
        pychete.PycheteState: [
            "add_theory",
            "add_expression",
            "get_expression",
            "to_json_obj",
            "to_json",
            "write_json",
            "save_state",
            "from_json_obj",
            "from_json",
            "read_json",
        ],
        pychete.MatchingResult: [
            "expression",
            "expression_names",
            "matching_condition_targets",
            "validate",
            "staged_projection_sources",
            "project_matching_conditions",
            "project_matching_conditions_from_sources",
            "with_projected_matching_conditions",
            "with_projected_matching_conditions_from_sources",
            "with_eft_truncation",
            "compare_to",
        ],
        pychete.MatchingResultComparison: [
            "assert_equal",
        ],
        pychete.MatchingFixtureGapReport: [
            "to_json_obj",
            "supertrace_order_coverage",
        ],
        pychete.SupertraceOrderCoverage: [
            "to_json_obj",
        ],
        pychete.ValidationFixture: [
            "expression",
            "from_json",
            "from_json_obj",
            "matching_result",
            "one_loop_preview",
            "one_loop_preview_gap_report",
            "read_json",
            "theory",
        ],
        pychete.OneLoopSetup: [
            "canonicalize_vakint_integral_expression_map",
            "canonicalize_integrals",
            "evaluate_vakint_integral_expression_map",
            "evaluate_integrals",
            "evaluate_tensor_networks",
            "interaction_block_traces",
            "interaction_bosonic_cde_expansion_plan",
            "interaction_bosonic_cde_expansion_terms",
            "interaction_bosonic_cde_expansion_terms_by_trace",
            "interaction_power_type_contribution_count",
            "interaction_power_type_contributions",
            "interaction_power_type_eft_lagrangian",
            "interaction_power_type_expression_map",
            "interaction_power_type_internal_integral_sum",
            "interaction_power_type_internal_matching_result",
            "interaction_power_type_internal_minimal_subtraction_result",
            "interaction_power_type_matching_result",
            "interaction_power_type_minimal_subtraction_result",
            "interaction_power_type_normalized_matching_result",
            "interaction_power_type_traces",
            "interaction_power_type_vakint_epsilon_coefficient",
            "interaction_power_type_vakint_finite_part",
            "interaction_power_type_vakint_integral_sum",
            "interaction_power_type_vakint_pole_part",
            "interaction_bosonic_cde_kernel_expression_map",
            "interaction_bosonic_cde_hybrid_internal_matching_result",
            "interaction_bosonic_cde_hybrid_internal_minimal_subtraction_result",
            "interaction_bosonic_cde_hybrid_matching_result",
            "interaction_bosonic_cde_hybrid_minimal_subtraction_result",
            "interaction_bosonic_cde_internal_integral_sum",
            "interaction_bosonic_cde_internal_matching_result",
            "interaction_bosonic_cde_internal_minimal_subtraction_result",
            "interaction_bosonic_cde_matching_result",
            "interaction_bosonic_cde_minimal_subtraction_result",
            "interaction_bosonic_cde_vakint_integral_expression_map",
            "interaction_bosonic_cde_vakint_integral_sum",
            "interaction_wilson_line_expansion_kernel_expression_map",
            "interaction_wilson_line_expansion_plan",
            "interaction_wilson_line_expansion_terms",
            "interaction_wilson_line_expansion_terms_by_trace",
            "interaction_wilson_line_expansion_vakint_integral_expression_map",
            "interaction_wilson_line_hybrid_internal_matching_result",
            "interaction_wilson_line_hybrid_internal_minimal_subtraction_result",
            "interaction_wilson_line_hybrid_matching_result",
            "interaction_wilson_line_hybrid_minimal_subtraction_result",
            "interaction_wilson_line_internal_integral_sum",
            "interaction_wilson_line_internal_matching_result",
            "interaction_wilson_line_internal_minimal_subtraction_result",
            "interaction_wilson_line_kernel_expression_map",
            "interaction_wilson_line_matching_result",
            "interaction_wilson_line_minimal_subtraction_result",
            "interaction_wilson_line_trace_paths",
            "interaction_wilson_line_trace_paths_by_trace",
            "interaction_wilson_line_vakint_integral_sum",
            "interaction_supertrace_expression_map",
            "interaction_supertrace_plan",
            "max_trace_order",
            "operator_propagator_denominator_chain",
            "operator_propagator_expression",
            "operator_propagator_mass_squared_chain",
            "operator_vakint_integral_expression",
            "operator_vakint_integral_expression_map",
            "power_type_contribution_count",
            "power_type_contributions",
            "power_type_eft_lagrangian",
            "power_type_expression_map",
            "power_type_internal_integral_sum",
            "power_type_minimal_subtraction_result",
            "power_type_vakint_epsilon_coefficient",
            "power_type_vakint_finite_part",
            "power_type_matching_result",
            "power_type_matching_preview",
            "power_type_vakint_pole_part",
            "power_type_traces",
            "power_type_vakint_integral_sum",
            "propagator_count",
            "propagator_plan",
            "simplify_index_algebra",
            "supertrace_expression_map",
            "supertrace_operator_propagator_expression_map",
            "supertrace_propagator_expression_map",
            "supertrace_kernel_count",
            "tensor_reduce_vakint_integral_expression_map",
            "tensor_reduce_integrals",
            "to_expression_map",
            "vakint_integral_expression_map",
        ],
        pychete.FluctuationOperator: [
            "block",
            "differential_entry",
            "entry",
            "free_inverse_entry",
            "interaction_block",
            "interaction_entry",
            "interaction_expression_map",
            "interaction_supertrace_plan",
            "momentum_entry",
            "momentum_expression_map",
            "mode_for",
            "propagator_denominator_entry",
            "propagator_denominator_expression_map",
            "propagator_denominator_for_mode",
            "supertrace_plan",
            "to_expression_map",
        ],
        pychete.FluctuationOperatorBlock: [
            "entry",
            "to_expression_map",
        ],
        pychete.FluctuationBasis: [
            "mode_for",
        ],
        pychete.FluctuationMode: [
            "chiral_supertrace_factor",
            "chirality",
            "conjugate_mode_count",
            "index_dimensions",
            "index_representations",
            "internal_dimension",
            "is_heavy",
            "is_light",
            "known_component_count",
            "label",
            "mass",
            "mass_squared",
            "spin_lorentz_dimension",
            "supertrace_sign",
            "supertrace_weight",
        ],
        pychete.FluctuationPropagator: [
            "denominator",
            "field",
            "is_heavy",
            "is_light",
            "to_expression_map",
        ],
        pychete.PropagatorPlan: [
            "heavy",
            "light",
            "to_expression_map",
        ],
        pychete.PowerTypeSupertraceContribution: [
            "eft_numerator_expression",
            "name",
            "numerator_expression",
            "order",
            "prefactor",
            "to_expression_map",
            "vakint_integral_expression",
        ],
        pychete.SupertracePlan: [
            "block_trace",
            "blocks",
            "closed_block_traces",
            "heavy_mode_count",
            "heavy_supertrace_sign",
            "light_mode_count",
            "to_expression_map",
        ],
        pychete.SupertraceBlockTrace: [
            "block_sectors",
            "bosonic_cde_expansion_terms",
            "canonicalize_integrals",
            "cyclic_sector_key",
            "evaluate_integrals",
            "evaluate_tensor_network",
            "order",
            "propagator_denominator_chain",
            "propagator_expression",
            "propagator_mass_squared_chain",
            "simplify_index_algebra",
            "tensor_reduce_integrals",
            "to_expression_map",
            "vakint_integral_expression",
            "wilson_line_trace_paths",
        ],
        pychete.WilsonLineTracePath: [
            "closing_field_label",
            "kernel_expression",
            "mass_squareds",
            "order",
            "propagator_expansion_terms",
            "template_expression",
            "wilson_line_expression",
            "wilson_term_expanded_kernel_expression",
            "wilson_term_expanded_template_expression",
            "wilson_term_expression",
        ],
        pychete.WilsonLineTraceExpansionTerm: [
            "kernel_expression",
            "vakint_integral_expression",
        ],
        pychete.WilsonLineExpansionPlanEntry: [
            "as_explicit_map",
        ],
        pychete.WilsonLineExpansionPlan: [
            "by_trace",
            "entry_count",
            "explicit_maps",
            "trace_count",
        ],
        pychete.BosonicCDETraceExpansionTerm: [
            "kernel_expression",
            "vakint_integral_expression",
        ],
        pychete.BosonicCDEExpansionPlanEntry: [
            "as_explicit_map",
        ],
        pychete.BosonicCDEExpansionPlan: [
            "by_trace",
            "entry_count",
            "explicit_maps",
            "trace_count",
        ],
    }
    missing = [
        f"{cls.__name__}.{method_name}"
        for cls, names in method_names.items()
        for method_name in names
        if not inspect.getdoc(getattr(cls, method_name))
    ]

    assert missing == []
