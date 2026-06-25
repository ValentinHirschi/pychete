from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from html import escape
from pathlib import Path
from typing import Any

from symbolica import Expression

from .matching_options import OneLoopIntegralBackend, OneLoopMatchOptions, VakintIntegralStage
from .matching_results import MatchingResult
from .state import PycheteState
from .theory import Theory
from .validation import (
    NumericProbePlan,
    NumericValue,
    ProbeParameterMode,
    build_numeric_probe_plan,
)

TensorComponent = Expression | int | float | complex


@dataclass(frozen=True)
class MatchingFixtureGapReport:
    """Coverage report comparing a current pychete candidate to a fixture result."""

    candidate_fixture: str
    reference_name: str
    candidate_stage: str | None
    reference_stage: str | None
    candidate_supertrace_names: tuple[str, ...]
    reference_supertrace_names: tuple[str, ...]
    common_supertrace_names: tuple[str, ...]
    candidate_only_supertrace_names: tuple[str, ...]
    reference_only_supertrace_names: tuple[str, ...]
    canonical_equal_common_supertrace_names: tuple[str, ...]
    canonical_different_common_supertrace_names: tuple[str, ...]
    numeric_probe_equal_common_supertrace_names: tuple[str, ...]
    numeric_probe_different_common_supertrace_names: tuple[str, ...]
    candidate_matching_condition_names: tuple[str, ...]
    reference_matching_condition_names: tuple[str, ...]
    common_matching_condition_names: tuple[str, ...]
    candidate_only_matching_condition_names: tuple[str, ...]
    reference_only_matching_condition_names: tuple[str, ...]
    canonical_equal_common_matching_condition_names: tuple[str, ...]
    canonical_different_common_matching_condition_names: tuple[str, ...]
    numeric_probe_equal_common_matching_condition_names: tuple[str, ...]
    numeric_probe_different_common_matching_condition_names: tuple[str, ...]
    common_expression_names: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """Whether candidate and reference expose the same validation surface."""

        return (
            not self.candidate_only_supertrace_names
            and not self.reference_only_supertrace_names
            and not self.candidate_only_matching_condition_names
            and not self.reference_only_matching_condition_names
        )

    @property
    def candidate_supertrace_count(self) -> int:
        """Number of supertrace expressions exposed by the candidate."""

        return len(self.candidate_supertrace_names)

    @property
    def reference_supertrace_count(self) -> int:
        """Number of supertrace expressions exposed by the reference fixture."""

        return len(self.reference_supertrace_names)

    @property
    def missing_reference_supertrace_count(self) -> int:
        """Number of reference supertraces not yet generated under matching names."""

        return len(self.reference_only_supertrace_names)

    @property
    def canonical_equal_common_supertrace_count(self) -> int:
        """Number of shared supertrace names whose expressions are canonically equal."""

        return len(self.canonical_equal_common_supertrace_names)

    @property
    def canonical_different_common_supertrace_count(self) -> int:
        """Number of shared supertrace names whose expressions still differ."""

        return len(self.canonical_different_common_supertrace_names)

    @property
    def numeric_probe_equal_common_supertrace_count(self) -> int:
        """Number of canonical-different shared supertraces accepted by numeric probes."""

        return len(self.numeric_probe_equal_common_supertrace_names)

    @property
    def numeric_probe_different_common_supertrace_count(self) -> int:
        """Number of numeric-probed shared supertraces that remain different."""

        return len(self.numeric_probe_different_common_supertrace_names)

    @property
    def accepted_common_supertrace_names(self) -> tuple[str, ...]:
        """Shared supertrace names accepted by canonical equality or numeric probe."""

        return _accepted_names(
            self.common_supertrace_names,
            self.canonical_equal_common_supertrace_names,
            self.numeric_probe_equal_common_supertrace_names,
        )

    @property
    def accepted_common_supertrace_count(self) -> int:
        """Number of shared supertraces accepted by canonical equality or probes."""

        return len(self.accepted_common_supertrace_names)

    @property
    def different_after_probe_common_supertrace_names(self) -> tuple[str, ...]:
        """Shared supertrace names still different after enabled probe fallbacks."""

        accepted = set(self.accepted_common_supertrace_names)
        return tuple(
            name
            for name in self.common_supertrace_names
            if name not in accepted
        )

    @property
    def different_after_probe_common_supertrace_count(self) -> int:
        """Number of shared supertraces still different after enabled probes."""

        return len(self.different_after_probe_common_supertrace_names)

    @property
    def candidate_matching_condition_count(self) -> int:
        """Number of matching conditions exposed by the candidate."""

        return len(self.candidate_matching_condition_names)

    @property
    def reference_matching_condition_count(self) -> int:
        """Number of matching conditions exposed by the reference fixture."""

        return len(self.reference_matching_condition_names)

    @property
    def missing_reference_matching_condition_count(self) -> int:
        """Number of reference matching conditions not yet generated."""

        return len(self.reference_only_matching_condition_names)

    @property
    def canonical_equal_common_matching_condition_count(self) -> int:
        """Number of shared matching conditions whose expressions are canonically equal."""

        return len(self.canonical_equal_common_matching_condition_names)

    @property
    def canonical_different_common_matching_condition_count(self) -> int:
        """Number of shared matching conditions whose expressions still differ."""

        return len(self.canonical_different_common_matching_condition_names)

    @property
    def numeric_probe_equal_common_matching_condition_count(self) -> int:
        """Number of canonical-different shared matching conditions accepted by probes."""

        return len(self.numeric_probe_equal_common_matching_condition_names)

    @property
    def numeric_probe_different_common_matching_condition_count(self) -> int:
        """Number of numeric-probed shared matching conditions that remain different."""

        return len(self.numeric_probe_different_common_matching_condition_names)

    @property
    def accepted_common_matching_condition_names(self) -> tuple[str, ...]:
        """Shared matching conditions accepted by canonical equality or numeric probe."""

        return _accepted_names(
            self.common_matching_condition_names,
            self.canonical_equal_common_matching_condition_names,
            self.numeric_probe_equal_common_matching_condition_names,
        )

    @property
    def accepted_common_matching_condition_count(self) -> int:
        """Number of shared matching conditions accepted by canonical equality or probes."""

        return len(self.accepted_common_matching_condition_names)

    @property
    def different_after_probe_common_matching_condition_names(self) -> tuple[str, ...]:
        """Shared matching conditions still different after enabled probe fallbacks."""

        accepted = set(self.accepted_common_matching_condition_names)
        return tuple(
            name
            for name in self.common_matching_condition_names
            if name not in accepted
        )

    @property
    def different_after_probe_common_matching_condition_count(self) -> int:
        """Number of shared matching conditions still different after enabled probes."""

        return len(self.different_after_probe_common_matching_condition_names)

    def to_json_obj(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of this report."""

        return {
            "candidate_fixture": self.candidate_fixture,
            "reference_name": self.reference_name,
            "candidate_stage": self.candidate_stage,
            "reference_stage": self.reference_stage,
            "complete": self.complete,
            "candidate_supertrace_count": self.candidate_supertrace_count,
            "reference_supertrace_count": self.reference_supertrace_count,
            "common_supertrace_count": len(self.common_supertrace_names),
            "missing_reference_supertrace_count": self.missing_reference_supertrace_count,
            "candidate_only_supertrace_count": len(self.candidate_only_supertrace_names),
            "canonical_equal_common_supertrace_count": self.canonical_equal_common_supertrace_count,
            "canonical_different_common_supertrace_count": self.canonical_different_common_supertrace_count,
            "numeric_probe_equal_common_supertrace_count": self.numeric_probe_equal_common_supertrace_count,
            "numeric_probe_different_common_supertrace_count": self.numeric_probe_different_common_supertrace_count,
            "accepted_common_supertrace_count": self.accepted_common_supertrace_count,
            "different_after_probe_common_supertrace_count": self.different_after_probe_common_supertrace_count,
            "candidate_matching_condition_count": self.candidate_matching_condition_count,
            "reference_matching_condition_count": self.reference_matching_condition_count,
            "common_matching_condition_count": len(self.common_matching_condition_names),
            "missing_reference_matching_condition_count": self.missing_reference_matching_condition_count,
            "candidate_only_matching_condition_count": len(self.candidate_only_matching_condition_names),
            "canonical_equal_common_matching_condition_count": self.canonical_equal_common_matching_condition_count,
            "canonical_different_common_matching_condition_count": (
                self.canonical_different_common_matching_condition_count
            ),
            "numeric_probe_equal_common_matching_condition_count": (
                self.numeric_probe_equal_common_matching_condition_count
            ),
            "numeric_probe_different_common_matching_condition_count": (
                self.numeric_probe_different_common_matching_condition_count
            ),
            "accepted_common_matching_condition_count": self.accepted_common_matching_condition_count,
            "different_after_probe_common_matching_condition_count": (
                self.different_after_probe_common_matching_condition_count
            ),
            "common_expression_names": list(self.common_expression_names),
            "candidate_only_supertrace_names": list(self.candidate_only_supertrace_names),
            "reference_only_supertrace_names": list(self.reference_only_supertrace_names),
            "canonical_equal_common_supertrace_names": list(self.canonical_equal_common_supertrace_names),
            "canonical_different_common_supertrace_names": list(self.canonical_different_common_supertrace_names),
            "numeric_probe_equal_common_supertrace_names": list(self.numeric_probe_equal_common_supertrace_names),
            "numeric_probe_different_common_supertrace_names": list(self.numeric_probe_different_common_supertrace_names),
            "accepted_common_supertrace_names": list(self.accepted_common_supertrace_names),
            "different_after_probe_common_supertrace_names": list(
                self.different_after_probe_common_supertrace_names
            ),
            "candidate_only_matching_condition_names": list(self.candidate_only_matching_condition_names),
            "reference_only_matching_condition_names": list(self.reference_only_matching_condition_names),
            "canonical_equal_common_matching_condition_names": list(self.canonical_equal_common_matching_condition_names),
            "canonical_different_common_matching_condition_names": list(
                self.canonical_different_common_matching_condition_names
            ),
            "numeric_probe_equal_common_matching_condition_names": list(
                self.numeric_probe_equal_common_matching_condition_names
            ),
            "numeric_probe_different_common_matching_condition_names": list(
                self.numeric_probe_different_common_matching_condition_names
            ),
            "accepted_common_matching_condition_names": list(self.accepted_common_matching_condition_names),
            "different_after_probe_common_matching_condition_names": list(
                self.different_after_probe_common_matching_condition_names
            ),
        }

    def _repr_latex_(self) -> str:
        status = r"\checkmark" if self.complete else r"\times"
        return (
            rf"$\mathrm{{MatchingFixtureGapReport}}\left({status},\ "
            rf"{self.candidate_supertrace_count}/{self.reference_supertrace_count}\ \mathrm{{STr}},\ "
            rf"{self.accepted_common_supertrace_count}\ \mathrm{{accepted}}\right)$"
        )

    def _repr_html_(self) -> str:
        status = "complete" if self.complete else "incomplete"
        return (
            f"<code>MatchingFixtureGapReport({escape(self.candidate_fixture)} vs "
            f"{escape(self.reference_name)}: {status}, "
            f"supertraces={self.candidate_supertrace_count}/{self.reference_supertrace_count}, "
            f"accepted_common_supertraces={self.accepted_common_supertrace_count}, "
            f"matching_conditions={self.candidate_matching_condition_count}/{self.reference_matching_condition_count}, "
            f"accepted_common_matching_conditions={self.accepted_common_matching_condition_count})</code>"
        )


@dataclass(frozen=True)
class ValidationFixture:
    """Mathematica-independent validation fixture loaded from repo assets."""

    name: str
    kind: str
    state: PycheteState
    source: dict[str, Any]
    expression_names: tuple[str, ...]
    matching_result_specs: dict[str, dict[str, Any]] = field(default_factory=dict)
    schema_version: int = 1

    def theory(self, name: str | None = None) -> Theory:
        """Return the requested theory, or the active fixture theory."""

        if name is not None:
            return self.state.theories[name]
        active = self.state.active
        if active is None:
            raise ValueError(f"Validation fixture {self.name!r} has no active theory")
        return active

    def expression(self, name: str) -> Expression:
        """Return a named validation expression."""

        if name not in self.expression_names:
            raise KeyError(f"Validation fixture {self.name!r} has no expression {name!r}")
        return self.state.get_expression(name)

    def matching_result(self, name: str = "default") -> MatchingResult:
        """Return a structured matching result described by this fixture."""

        if name not in self.matching_result_specs:
            raise KeyError(f"Validation fixture {self.name!r} has no matching result {name!r}")
        spec = self.matching_result_specs[name]
        theory = self.theory(str(spec.get("theory"))) if spec.get("theory") is not None else self.theory()
        return MatchingResult(
            theory=theory,
            uv_lagrangian=self.expression(str(spec["uv_lagrangian"])),
            off_shell_eft_lagrangian=self.expression(str(spec["off_shell_eft_lagrangian"])),
            on_shell_eft_lagrangian=self.expression(str(spec["on_shell_eft_lagrangian"])),
            matching_conditions=_expression_map(self, spec.get("matching_conditions", {}), "matching_conditions"),
            fluctuation_operators=_expression_map(self, spec.get("fluctuation_operators", {}), "fluctuation_operators"),
            supertraces=_expression_map(self, spec.get("supertraces", {}), "supertraces"),
            metadata=_metadata(spec.get("metadata", {})),
        )

    def one_loop_preview(
        self,
        *,
        lagrangian: str = "lagrangian",
        eft_order: int = 6,
        max_trace_order: int = 2,
        include_light_only: bool = False,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        integral_backend: OneLoopIntegralBackend | str = OneLoopIntegralBackend.VAKINT,
        internal_tensor_reduce: bool = True,
        internal_combine_terms: bool = False,
        internal_max_pole_order: int = 1,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
        evaluate_tensor_networks: bool = False,
        tensor_network_library: Any | None = None,
        tensor_network_cg_components_by_name: Mapping[str, Sequence[TensorComponent]] | None = None,
        tensor_network_builtin_cg_components: bool = False,
        tensor_network_native_hep_cg_builtins: bool = False,
        tensor_network_symbolic_cg_components: bool = False,
        tensor_network_function_library: Any | None = None,
        tensor_network_n_steps: int | None = None,
        tensor_network_mode: Any | None = None,
    ) -> MatchingResult:
        """Build the current incomplete interaction-power preview from fixture expressions."""

        theory = self.theory()
        setup = theory.one_loop_setup(
            self.expression(lagrangian),
            eft_order=eft_order,
            max_trace_order=max_trace_order,
            include_light_only=include_light_only,
        )
        tensor_network_cg_component_source: str | None = None
        if evaluate_tensor_networks:
            tensor_network_cg_component_source = _tensor_network_component_source(
                theory,
                library=tensor_network_library,
                cg_components_by_name=tensor_network_cg_components_by_name,
                builtin_cg_components=tensor_network_builtin_cg_components,
                native_hep_cg_builtins=tensor_network_native_hep_cg_builtins,
                symbolic_cg_components=tensor_network_symbolic_cg_components,
            )
            setup = setup.evaluate_tensor_networks(
                library=tensor_network_library,
                cg_components_by_name=tensor_network_cg_components_by_name,
                builtin_cg_components=tensor_network_builtin_cg_components,
                native_hep_cg_builtins=tensor_network_native_hep_cg_builtins,
                symbolic_cg_components=tensor_network_symbolic_cg_components,
                function_library=tensor_network_function_library,
                n_steps=tensor_network_n_steps,
                mode=tensor_network_mode,
            )
        selected_backend = OneLoopIntegralBackend.from_user(integral_backend)
        if selected_backend is OneLoopIntegralBackend.INTERNAL:
            result = setup.interaction_power_type_internal_matching_result(
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                tensor_reduce=internal_tensor_reduce,
                tensor_reduce_engine=vakint_engine,
                combine_terms=internal_combine_terms,
            )
        elif selected_backend is OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION:
            result = setup.interaction_power_type_internal_minimal_subtraction_result(
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                tensor_reduce=internal_tensor_reduce,
                tensor_reduce_engine=vakint_engine,
                combine_terms=internal_combine_terms,
                max_pole_order=internal_max_pole_order,
            )
        else:
            result = setup.interaction_power_type_matching_result(
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                vakint_stage=vakint_stage,
                vakint_short_form=vakint_short_form,
                vakint_engine=vakint_engine,
                named_supertrace_stage=named_supertrace_stage,
                named_supertrace_short_form=named_supertrace_short_form,
                named_supertrace_engine=named_supertrace_engine,
            )
        return MatchingResult(
            theory=result.theory,
            uv_lagrangian=result.uv_lagrangian,
            off_shell_eft_lagrangian=result.off_shell_eft_lagrangian,
            on_shell_eft_lagrangian=result.on_shell_eft_lagrangian,
            matching_conditions=result.matching_conditions,
            fluctuation_operators=result.fluctuation_operators,
            supertraces=result.supertraces,
            metadata={
                **result.metadata,
                "fixture": self.name,
                "fixture_kind": self.kind,
                "lagrangian_expression": lagrangian,
                "tensor_networks_evaluated": evaluate_tensor_networks,
                "tensor_network_cg_component_source": tensor_network_cg_component_source,
                "tensor_network_native_hep_cg_builtins": tensor_network_native_hep_cg_builtins,
            },
        )

    def one_loop_preview_gap_report(
        self,
        reference: MatchingResult,
        *,
        reference_name: str = "reference",
        lagrangian: str = "lagrangian",
        eft_order: int = 6,
        max_trace_order: int = 2,
        include_light_only: bool = False,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        integral_backend: OneLoopIntegralBackend | str = OneLoopIntegralBackend.VAKINT,
        internal_tensor_reduce: bool = True,
        internal_combine_terms: bool = False,
        internal_max_pole_order: int = 1,
        probe_parameters: Sequence[Expression] | None = None,
        probe_samples: Sequence[Sequence[NumericValue]] | None = None,
        probe_supertrace_names: Iterable[str] | None = None,
        probe_matching_condition_names: Iterable[str] | None = None,
        auto_probe_samples: bool = False,
        probe_sample_count: int = 3,
        probe_exclude_symbols: Sequence[Expression] = (),
        probe_parameter_mode: ProbeParameterMode = "symbols",
        probe_absolute_tolerance: float = 1e-9,
        probe_relative_tolerance: float = 1e-9,
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
        evaluate_tensor_networks: bool = False,
        tensor_network_library: Any | None = None,
        tensor_network_cg_components_by_name: Mapping[str, Sequence[TensorComponent]] | None = None,
        tensor_network_builtin_cg_components: bool = False,
        tensor_network_native_hep_cg_builtins: bool = False,
        tensor_network_symbolic_cg_components: bool = False,
        tensor_network_function_library: Any | None = None,
        tensor_network_n_steps: int | None = None,
        tensor_network_mode: Any | None = None,
        project_reference_matching_conditions: bool = False,
        matching_condition_projection_source: str = "on_shell_eft_lagrangian",
        matching_condition_projection_drop_zero: bool = False,
        use_public_match_api: bool = False,
    ) -> MatchingFixtureGapReport:
        """Report current one-loop preview coverage against a reference result."""

        projected_targets = (
            _reference_matching_condition_targets(reference)
            if project_reference_matching_conditions
            else None
        )
        if use_public_match_api:
            if evaluate_tensor_networks:
                raise ValueError("use_public_match_api does not support fixture-local tensor-network evaluation")
            matched = self.theory().match(
                self.expression(lagrangian),
                eft_order=eft_order,
                loop_order=1,
                one_loop_options=OneLoopMatchOptions(
                    max_trace_order=max_trace_order,
                    include_light_only=include_light_only,
                    heavy_field_dimension=heavy_field_dimension,
                    include_light=include_light,
                    integral_backend=integral_backend,
                    vakint_stage=vakint_stage,
                    vakint_short_form=vakint_short_form,
                    vakint_engine=vakint_engine,
                    named_supertrace_stage=named_supertrace_stage,
                    named_supertrace_short_form=named_supertrace_short_form,
                    named_supertrace_engine=named_supertrace_engine,
                    tensor_reduce=internal_tensor_reduce,
                    tensor_reduce_engine=vakint_engine,
                    combine_terms=internal_combine_terms,
                    max_pole_order=internal_max_pole_order,
                ),
                matching_condition_targets=projected_targets,
                matching_condition_source=matching_condition_projection_source,
                matching_condition_drop_zero=matching_condition_projection_drop_zero,
            )
            if not isinstance(matched, MatchingResult):
                raise TypeError("public one-loop match returned a tree-level expression")
            candidate = replace(
                matched,
                metadata={
                    **matched.metadata,
                    "fixture": self.name,
                    "fixture_kind": self.kind,
                    "lagrangian_expression": lagrangian,
                    "tensor_networks_evaluated": False,
                    "tensor_network_cg_component_source": None,
                    "tensor_network_native_hep_cg_builtins": False,
                    "fixture_preview_source": "public_match_api",
                },
            )
        else:
            candidate = self.one_loop_preview(
                lagrangian=lagrangian,
                eft_order=eft_order,
                max_trace_order=max_trace_order,
                include_light_only=include_light_only,
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                vakint_stage=vakint_stage,
                vakint_short_form=vakint_short_form,
                vakint_engine=vakint_engine,
                integral_backend=integral_backend,
                internal_tensor_reduce=internal_tensor_reduce,
                internal_combine_terms=internal_combine_terms,
                internal_max_pole_order=internal_max_pole_order,
                named_supertrace_stage=named_supertrace_stage,
                named_supertrace_short_form=named_supertrace_short_form,
                named_supertrace_engine=named_supertrace_engine,
                evaluate_tensor_networks=evaluate_tensor_networks,
                tensor_network_library=tensor_network_library,
                tensor_network_cg_components_by_name=tensor_network_cg_components_by_name,
                tensor_network_builtin_cg_components=tensor_network_builtin_cg_components,
                tensor_network_native_hep_cg_builtins=tensor_network_native_hep_cg_builtins,
                tensor_network_symbolic_cg_components=tensor_network_symbolic_cg_components,
                tensor_network_function_library=tensor_network_function_library,
                tensor_network_n_steps=tensor_network_n_steps,
                tensor_network_mode=tensor_network_mode,
            )
        if project_reference_matching_conditions and not use_public_match_api:
            candidate = candidate.with_projected_matching_conditions(
                projected_targets or {},
                source=matching_condition_projection_source,
                drop_zero=matching_condition_projection_drop_zero,
            )
        return _gap_report(
            self.name,
            reference_name,
            candidate,
            reference,
            probe_parameters=probe_parameters,
            probe_samples=probe_samples,
            probe_supertrace_names=probe_supertrace_names,
            probe_matching_condition_names=probe_matching_condition_names,
            auto_probe_samples=auto_probe_samples,
            probe_sample_count=probe_sample_count,
            probe_exclude_symbols=probe_exclude_symbols,
            probe_parameter_mode=probe_parameter_mode,
            probe_absolute_tolerance=probe_absolute_tolerance,
            probe_relative_tolerance=probe_relative_tolerance,
        )

    @classmethod
    def from_json_obj(cls, obj: dict[str, Any]) -> ValidationFixture:
        """Restore a validation fixture from a JSON object."""

        schema_version = int(obj.get("schema_version", 1))
        if schema_version != 1:
            raise ValueError(f"Unsupported validation fixture schema version {schema_version}")
        state_obj = obj.get("state")
        if not isinstance(state_obj, dict):
            raise ValueError("Validation fixture must contain a state object")
        state = PycheteState.from_json_obj(state_obj)
        raw_expression_names = obj.get("expressions", sorted(state.expressions))
        if not isinstance(raw_expression_names, list) or not all(isinstance(name, str) for name in raw_expression_names):
            raise ValueError("Validation fixture expressions must be a list of names")
        missing = sorted(set(raw_expression_names).difference(state.expressions))
        if missing:
            raise ValueError(f"Validation fixture references missing expressions: {missing}")
        source = obj.get("source", {})
        if not isinstance(source, dict):
            raise ValueError("Validation fixture source metadata must be an object")
        matching_result_specs = _matching_result_specs(obj.get("matching_results", {}), set(state.expressions))
        return cls(
            name=str(obj["name"]),
            kind=str(obj.get("kind", "validation")),
            state=state,
            source=source,
            expression_names=tuple(raw_expression_names),
            matching_result_specs=matching_result_specs,
            schema_version=schema_version,
        )

    @classmethod
    def from_json(cls, text: str) -> ValidationFixture:
        """Restore a validation fixture from a JSON string."""

        return cls.from_json_obj(json.loads(text))

    @classmethod
    def read_json(cls, path: str | Path) -> ValidationFixture:
        """Read a validation fixture from a JSON file."""

        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def load_validation_fixture(path: str | Path) -> ValidationFixture:
    """Load a Mathematica-independent pychete validation fixture."""

    return ValidationFixture.read_json(path)


def _sorted_names(names: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(names))


def _accepted_names(
    common_names: Iterable[str],
    canonical_equal_names: Iterable[str],
    numeric_probe_equal_names: Iterable[str],
) -> tuple[str, ...]:
    accepted = set(canonical_equal_names) | set(numeric_probe_equal_names)
    return tuple(name for name in common_names if name in accepted)


def _metadata_stage(result: MatchingResult) -> str | None:
    stage = result.metadata.get("stage")
    return str(stage) if stage is not None else None


def _tensor_network_component_source(
    theory: Theory,
    *,
    library: Any | None,
    cg_components_by_name: Mapping[str, Sequence[TensorComponent]] | None,
    builtin_cg_components: bool,
    native_hep_cg_builtins: bool,
    symbolic_cg_components: bool,
) -> str | None:
    if cg_components_by_name is not None:
        return "explicit"
    if builtin_cg_components:
        return "builtin"
    if symbolic_cg_components:
        return "symbolic"
    from .backends import spenso

    if spenso.has_stored_cg_tensor_components(theory):
        return "stored"
    if native_hep_cg_builtins:
        return "native_hep"
    if library is not None:
        return "library"
    return None


def _reference_matching_condition_targets(reference: MatchingResult) -> dict[str, Expression]:
    return {
        name: reference.theory._parse_registered_expression(name)
        for name in reference.matching_conditions
    }


def _probe_plan_for_names(
    candidate: MatchingResult,
    reference: MatchingResult,
    names: Iterable[str],
    *,
    sample_count: int,
    exclude_symbols: Sequence[Expression],
    parameter_mode: ProbeParameterMode,
) -> NumericProbePlan:
    expressions: list[Expression] = []
    for name in names:
        for result in (candidate, reference):
            try:
                expressions.append(result.expression(name))
            except KeyError:
                continue
    return build_numeric_probe_plan(
        expressions,
        exclude_symbols=exclude_symbols,
        parameter_mode=parameter_mode,
        sample_count=sample_count,
    )


def _gap_report(
    candidate_fixture: str,
    reference_name: str,
    candidate: MatchingResult,
    reference: MatchingResult,
    *,
    probe_parameters: Sequence[Expression] | None = None,
    probe_samples: Sequence[Sequence[NumericValue]] | None = None,
    probe_supertrace_names: Iterable[str] | None = None,
    probe_matching_condition_names: Iterable[str] | None = None,
    auto_probe_samples: bool = False,
    probe_sample_count: int = 3,
    probe_exclude_symbols: Sequence[Expression] = (),
    probe_parameter_mode: ProbeParameterMode = "symbols",
    probe_absolute_tolerance: float = 1e-9,
    probe_relative_tolerance: float = 1e-9,
) -> MatchingFixtureGapReport:
    if auto_probe_samples and (probe_parameters is not None or probe_samples is not None):
        raise ValueError("auto_probe_samples cannot be combined with explicit probe_parameters/probe_samples")
    if auto_probe_samples and probe_supertrace_names is None and probe_matching_condition_names is None:
        raise ValueError("auto_probe_samples requires probe_supertrace_names or probe_matching_condition_names")

    candidate_supertraces = set(candidate.supertraces)
    reference_supertraces = set(reference.supertraces)
    common_supertraces = candidate_supertraces & reference_supertraces
    supertrace_probe_parameters: Sequence[Expression] | None
    supertrace_probe_samples: Sequence[Sequence[NumericValue]] | None
    if auto_probe_samples and probe_supertrace_names is not None:
        supertrace_plan = _probe_plan_for_names(
            candidate,
            reference,
            probe_supertrace_names,
            sample_count=probe_sample_count,
            exclude_symbols=probe_exclude_symbols,
            parameter_mode=probe_parameter_mode,
        )
        supertrace_probe_parameters = supertrace_plan.parameters
        supertrace_probe_samples = supertrace_plan.samples
    elif auto_probe_samples:
        supertrace_probe_parameters = None
        supertrace_probe_samples = None
    elif probe_matching_condition_names is not None and probe_supertrace_names is None:
        supertrace_probe_parameters = None
        supertrace_probe_samples = None
    else:
        supertrace_probe_parameters = probe_parameters
        supertrace_probe_samples = probe_samples
    compared_supertraces = candidate.compare_to(
        reference,
        names=_sorted_names(common_supertraces),
        probe_parameters=supertrace_probe_parameters,
        probe_samples=supertrace_probe_samples,
        probe_names=probe_supertrace_names,
        absolute_tolerance=probe_absolute_tolerance,
        relative_tolerance=probe_relative_tolerance,
    )
    candidate_conditions = set(candidate.matching_conditions)
    reference_conditions = set(reference.matching_conditions)
    common_conditions = candidate_conditions & reference_conditions
    condition_probe_parameters: Sequence[Expression] | None
    condition_probe_samples: Sequence[Sequence[NumericValue]] | None
    if auto_probe_samples and probe_matching_condition_names is not None:
        condition_plan = _probe_plan_for_names(
            candidate,
            reference,
            probe_matching_condition_names,
            sample_count=probe_sample_count,
            exclude_symbols=probe_exclude_symbols,
            parameter_mode=probe_parameter_mode,
        )
        condition_probe_parameters = condition_plan.parameters
        condition_probe_samples = condition_plan.samples
    elif auto_probe_samples:
        condition_probe_parameters = None
        condition_probe_samples = None
    else:
        condition_probe_parameters = probe_parameters if probe_matching_condition_names is not None else None
        condition_probe_samples = probe_samples if probe_matching_condition_names is not None else None
    compared_conditions = candidate.compare_to(
        reference,
        names=_sorted_names(common_conditions),
        probe_parameters=condition_probe_parameters,
        probe_samples=condition_probe_samples,
        probe_names=probe_matching_condition_names,
        absolute_tolerance=probe_absolute_tolerance,
        relative_tolerance=probe_relative_tolerance,
    )
    candidate_names = set(candidate.expression_names())
    reference_names = set(reference.expression_names())
    return MatchingFixtureGapReport(
        candidate_fixture=candidate_fixture,
        reference_name=reference_name,
        candidate_stage=_metadata_stage(candidate),
        reference_stage=_metadata_stage(reference),
        candidate_supertrace_names=_sorted_names(candidate_supertraces),
        reference_supertrace_names=_sorted_names(reference_supertraces),
        common_supertrace_names=_sorted_names(common_supertraces),
        candidate_only_supertrace_names=_sorted_names(candidate_supertraces - reference_supertraces),
        reference_only_supertrace_names=_sorted_names(reference_supertraces - candidate_supertraces),
        canonical_equal_common_supertrace_names=tuple(
            item.name for item in compared_supertraces.expressions if item.canonical_equal
        ),
        canonical_different_common_supertrace_names=tuple(
            item.name for item in compared_supertraces.expressions if not item.canonical_equal
        ),
        numeric_probe_equal_common_supertrace_names=tuple(
            item.name
            for item in compared_supertraces.expressions
            if not item.canonical_equal and item.numeric_probe is not None and item.numeric_probe.equal
        ),
        numeric_probe_different_common_supertrace_names=tuple(
            item.name
            for item in compared_supertraces.expressions
            if item.numeric_probe is not None and not item.numeric_probe.equal
        ),
        candidate_matching_condition_names=_sorted_names(candidate_conditions),
        reference_matching_condition_names=_sorted_names(reference_conditions),
        common_matching_condition_names=_sorted_names(candidate_conditions & reference_conditions),
        candidate_only_matching_condition_names=_sorted_names(candidate_conditions - reference_conditions),
        reference_only_matching_condition_names=_sorted_names(reference_conditions - candidate_conditions),
        canonical_equal_common_matching_condition_names=tuple(
            item.name for item in compared_conditions.expressions if item.canonical_equal
        ),
        canonical_different_common_matching_condition_names=tuple(
            item.name for item in compared_conditions.expressions if not item.canonical_equal
        ),
        numeric_probe_equal_common_matching_condition_names=tuple(
            item.name
            for item in compared_conditions.expressions
            if not item.canonical_equal and item.numeric_probe is not None and item.numeric_probe.equal
        ),
        numeric_probe_different_common_matching_condition_names=tuple(
            item.name
            for item in compared_conditions.expressions
            if item.numeric_probe is not None and not item.numeric_probe.equal
        ),
        common_expression_names=_sorted_names(candidate_names & reference_names),
    )


def _metadata(value: Any) -> dict[str, str | int | float | bool | None]:
    if not isinstance(value, dict):
        raise ValueError("Matching result metadata must be an object")
    out: dict[str, str | int | float | bool | None] = {}
    for key, item in value.items():
        if item is None or isinstance(item, (str, int, float, bool)):
            out[str(key)] = item
        else:
            raise ValueError(f"Matching result metadata value for {key!r} is not JSON-scalar")
    return out


def _expression_map(fixture: ValidationFixture, value: Any, section: str) -> dict[str, Expression]:
    if not isinstance(value, dict):
        raise ValueError(f"Matching result {section} must be an object")
    return {str(label): fixture.expression(str(expression_name)) for label, expression_name in value.items()}


def _matching_result_specs(value: Any, expression_names: set[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        raise ValueError("Validation fixture matching_results must be an object")
    out: dict[str, dict[str, Any]] = {}
    for result_name, raw_spec in value.items():
        if not isinstance(raw_spec, dict):
            raise ValueError(f"Matching result {result_name!r} must be an object")
        spec = dict(raw_spec)
        for required in ("uv_lagrangian", "off_shell_eft_lagrangian", "on_shell_eft_lagrangian"):
            if required not in spec:
                raise ValueError(f"Matching result {result_name!r} is missing {required!r}")
            expression_name = str(spec[required])
            if expression_name not in expression_names:
                raise ValueError(f"Matching result {result_name!r} references missing expression {expression_name!r}")
        for section in ("matching_conditions", "fluctuation_operators", "supertraces"):
            raw_section = spec.get(section, {})
            if not isinstance(raw_section, dict):
                raise ValueError(f"Matching result {result_name!r} {section} must be an object")
            for expression_name in raw_section.values():
                if str(expression_name) not in expression_names:
                    raise ValueError(f"Matching result {result_name!r} references missing expression {expression_name!r}")
        out[str(result_name)] = spec
    return out
