from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from html import escape
from pathlib import Path
from typing import Any, Literal

from symbolica import Expression

from .logging import get_logger, progress
from .matching_options import (
    CovariantDerivativeCommutatorModeInput,
    OneLoopIntegralBackend,
    OneLoopMatchOptions,
    OneLoopNormalization,
    OneLoopNormalizationInput,
    VakintIntegralStage,
    one_loop_normalization_label,
)
from .matching import (
    BosonicCDEExpansionPlan,
    WilsonLineExpansionPlan,
    _term_atom_requirements_for_targets,
)
from .matching_results import (
    MatchingConditionTarget,
    MatchingResult,
    _canonize_comparison_indices,
    registered_wilson_matching_condition_targets,
)
from .state import PycheteState
from .supertraces import is_unnormalized_supertrace_alias, supertrace_word_order
from .symbols import SymbolDataKey, s, symbol_data
from .theory import Theory
from .theory_metadata import ExternalKind
from .tree_matching import heavy_scalar_solution_replacements, solve_heavy_scalar_eoms
from .wilson_line_eom import (
    _apply_on_shell_eom_reduction_to_expression,
    _apply_wilson_line_post_integral_scalar_commutator_bilinears,
    _apply_wilson_line_scalar_eom_field_redefinition,
)
from .validation import (
    NumericProbePlan,
    NumericValue,
    ProbeParameterMode,
    build_numeric_probe_plan,
)

TensorComponent = Expression | int | float | complex
TraceOrderInput = int | Literal["reference"]
ProbeNamePreset = Literal["common", "canonical_different", "wilson", "canonical_different_wilson"]
ProbeNameSelection = Iterable[str] | ProbeNamePreset
ProjectionNameSelection = str | Iterable[str]
MetadataJsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None
_PROBE_NAME_PRESETS = {"common", "canonical_different", "wilson", "canonical_different_wilson"}
_WILSON_PROBE_NAME_PRESETS = {"wilson", "canonical_different_wilson"}
_LOGGER = get_logger("validation")


@dataclass(frozen=True)
class _MatchingConditionProjectionTargets:
    targets: dict[str, Expression]
    registered_wilson_names: tuple[str, ...] = ()
    reference_non_wilson_names: tuple[str, ...] = ()
    reference_wilson_fallback_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class SupertraceOrderCoverage:
    """Per-word-order coverage diagnostics for Matchete-style supertrace names."""

    order: int
    candidate_names: tuple[str, ...]
    reference_names: tuple[str, ...]
    common_names: tuple[str, ...]
    candidate_only_names: tuple[str, ...]
    reference_only_names: tuple[str, ...]
    canonical_equal_common_names: tuple[str, ...]
    accepted_common_names: tuple[str, ...]
    different_after_probe_common_names: tuple[str, ...]

    @property
    def candidate_count(self) -> int:
        """Number of candidate supertraces at this word order."""

        return len(self.candidate_names)

    @property
    def reference_count(self) -> int:
        """Number of reference supertraces at this word order."""

        return len(self.reference_names)

    @property
    def common_count(self) -> int:
        """Number of shared supertrace names at this word order."""

        return len(self.common_names)

    @property
    def candidate_only_count(self) -> int:
        """Number of candidate-only supertrace names at this word order."""

        return len(self.candidate_only_names)

    @property
    def missing_reference_count(self) -> int:
        """Number of reference-only supertrace names at this word order."""

        return len(self.reference_only_names)

    @property
    def canonical_equal_common_count(self) -> int:
        """Number of shared supertraces canonically equal at this word order."""

        return len(self.canonical_equal_common_names)

    @property
    def accepted_common_count(self) -> int:
        """Number of shared supertraces accepted by canonical equality or probes."""

        return len(self.accepted_common_names)

    @property
    def different_after_probe_common_count(self) -> int:
        """Number of shared supertraces still different after enabled probes."""

        return len(self.different_after_probe_common_names)

    def to_json_obj(self) -> dict[str, Any]:
        """Return this order diagnostic as a JSON-serializable object."""

        return {
            "order": self.order,
            "candidate_count": self.candidate_count,
            "reference_count": self.reference_count,
            "common_count": self.common_count,
            "candidate_only_count": self.candidate_only_count,
            "missing_reference_count": self.missing_reference_count,
            "canonical_equal_common_count": self.canonical_equal_common_count,
            "accepted_common_count": self.accepted_common_count,
            "different_after_probe_common_count": self.different_after_probe_common_count,
            "candidate_names": list(self.candidate_names),
            "reference_names": list(self.reference_names),
            "common_names": list(self.common_names),
            "candidate_only_names": list(self.candidate_only_names),
            "reference_only_names": list(self.reference_only_names),
            "canonical_equal_common_names": list(self.canonical_equal_common_names),
            "accepted_common_names": list(self.accepted_common_names),
            "different_after_probe_common_names": list(self.different_after_probe_common_names),
        }

    def _repr_latex_(self) -> str:
        return (
            rf"$\mathrm{{SupertraceOrderCoverage}}\left({self.order},\ "
            rf"{self.candidate_count}/{self.reference_count},\ "
            rf"{self.accepted_common_count}\ \mathrm{{accepted}}\right)$"
        )

    def _repr_html_(self) -> str:
        return (
            f"<code>SupertraceOrderCoverage(order={self.order}, "
            f"supertraces={self.candidate_count}/{self.reference_count}, "
            f"accepted={self.accepted_common_count}, "
            f"missing={self.missing_reference_count})</code>"
        )


@dataclass(frozen=True)
class MatchingFixtureGapReport:
    """Coverage report comparing a current pychete candidate to a fixture result."""

    candidate_fixture: str
    reference_name: str
    candidate_stage: str | None
    reference_stage: str | None
    candidate_supertrace_names: tuple[str, ...]
    reference_supertrace_names: tuple[str, ...]
    candidate_max_supertrace_order: int
    reference_max_supertrace_order: int
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
    reference_wilson_matching_condition_names: tuple[str, ...]
    matching_condition_projection_registered_wilson_names: tuple[str, ...] = ()
    matching_condition_projection_reference_non_wilson_names: tuple[str, ...] = ()
    matching_condition_projection_reference_wilson_fallback_names: tuple[str, ...] = ()
    comparison_canonize_indices: bool = True
    candidate_metadata: dict[str, MetadataJsonValue] = field(default_factory=dict)
    reference_metadata: dict[str, MetadataJsonValue] = field(default_factory=dict)

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
    def max_supertrace_order_gap(self) -> int:
        """Difference between reference and candidate maximum supertrace word order."""

        return self.reference_max_supertrace_order - self.candidate_max_supertrace_order

    @property
    def supertrace_order_coverage(self) -> tuple[SupertraceOrderCoverage, ...]:
        """Per-order coverage diagnostics for Matchete-style supertrace words."""

        return _supertrace_order_coverage(self)

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
    def reference_wilson_matching_condition_count(self) -> int:
        """Number of reference matching conditions targeting Wilson coefficients."""

        return len(self.reference_wilson_matching_condition_names)

    @property
    def matching_condition_projection_registered_wilson_count(self) -> int:
        """Number of projected targets sourced from theory-registered Wilson metadata."""

        return len(self.matching_condition_projection_registered_wilson_names)

    @property
    def matching_condition_projection_reference_non_wilson_count(self) -> int:
        """Number of projected targets sourced from reference non-Wilson conditions."""

        return len(self.matching_condition_projection_reference_non_wilson_names)

    @property
    def matching_condition_projection_reference_wilson_fallback_count(self) -> int:
        """Number of projected Wilson targets not available from theory metadata."""

        return len(self.matching_condition_projection_reference_wilson_fallback_names)

    @property
    def common_wilson_matching_condition_names(self) -> tuple[str, ...]:
        """Shared matching-condition names whose reference target is a Wilson coefficient."""

        common = set(self.common_matching_condition_names)
        return tuple(name for name in self.reference_wilson_matching_condition_names if name in common)

    @property
    def common_wilson_matching_condition_count(self) -> int:
        """Number of shared Wilson-coefficient matching-condition targets."""

        return len(self.common_wilson_matching_condition_names)

    @property
    def accepted_common_wilson_matching_condition_names(self) -> tuple[str, ...]:
        """Wilson matching conditions accepted by canonical equality or probes."""

        accepted = set(self.accepted_common_matching_condition_names)
        return tuple(name for name in self.common_wilson_matching_condition_names if name in accepted)

    @property
    def accepted_common_wilson_matching_condition_count(self) -> int:
        """Number of accepted shared Wilson-coefficient matching conditions."""

        return len(self.accepted_common_wilson_matching_condition_names)

    @property
    def different_after_probe_common_wilson_matching_condition_names(self) -> tuple[str, ...]:
        """Wilson matching conditions still different after enabled probe fallbacks."""

        accepted = set(self.accepted_common_wilson_matching_condition_names)
        return tuple(name for name in self.common_wilson_matching_condition_names if name not in accepted)

    @property
    def different_after_probe_common_wilson_matching_condition_count(self) -> int:
        """Number of Wilson matching conditions still different after enabled probes."""

        return len(self.different_after_probe_common_wilson_matching_condition_names)

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
            "candidate_max_supertrace_order": self.candidate_max_supertrace_order,
            "reference_max_supertrace_order": self.reference_max_supertrace_order,
            "max_supertrace_order_gap": self.max_supertrace_order_gap,
            "supertrace_order_coverage": [
                coverage.to_json_obj() for coverage in self.supertrace_order_coverage
            ],
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
            "comparison_canonize_indices": self.comparison_canonize_indices,
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
            "reference_wilson_matching_condition_count": self.reference_wilson_matching_condition_count,
            "candidate_metadata": self.candidate_metadata,
            "reference_metadata": self.reference_metadata,
            "matching_condition_projection_registered_wilson_count": (
                self.matching_condition_projection_registered_wilson_count
            ),
            "matching_condition_projection_reference_non_wilson_count": (
                self.matching_condition_projection_reference_non_wilson_count
            ),
            "matching_condition_projection_reference_wilson_fallback_count": (
                self.matching_condition_projection_reference_wilson_fallback_count
            ),
            "common_wilson_matching_condition_count": self.common_wilson_matching_condition_count,
            "accepted_common_wilson_matching_condition_count": self.accepted_common_wilson_matching_condition_count,
            "different_after_probe_common_wilson_matching_condition_count": (
                self.different_after_probe_common_wilson_matching_condition_count
            ),
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
            "reference_wilson_matching_condition_names": list(self.reference_wilson_matching_condition_names),
            "matching_condition_projection_registered_wilson_names": list(
                self.matching_condition_projection_registered_wilson_names
            ),
            "matching_condition_projection_reference_non_wilson_names": list(
                self.matching_condition_projection_reference_non_wilson_names
            ),
            "matching_condition_projection_reference_wilson_fallback_names": list(
                self.matching_condition_projection_reference_wilson_fallback_names
            ),
            "common_wilson_matching_condition_names": list(self.common_wilson_matching_condition_names),
            "accepted_common_wilson_matching_condition_names": list(
                self.accepted_common_wilson_matching_condition_names
            ),
            "different_after_probe_common_wilson_matching_condition_names": list(
                self.different_after_probe_common_wilson_matching_condition_names
            ),
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
            f"max_order={self.candidate_max_supertrace_order}/{self.reference_max_supertrace_order}, "
            f"accepted_common_supertraces={self.accepted_common_supertrace_count}, "
            f"matching_conditions={self.candidate_matching_condition_count}/{self.reference_matching_condition_count}, "
            f"accepted_common_matching_conditions={self.accepted_common_matching_condition_count}, "
            f"accepted_common_wilson={self.accepted_common_wilson_matching_condition_count}/"
            f"{self.common_wilson_matching_condition_count})</code>"
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
        normalization: OneLoopNormalizationInput = OneLoopNormalization.PREVIEW,
        hbar: Expression | None = None,
        internal_tensor_reduce: bool = True,
        internal_combine_terms: bool = False,
        internal_max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
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
        expand_abelian_covariant_derivatives: bool = False,
        expand_non_abelian_covariant_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        bosonic_cde_expansion_indices_by_trace: Mapping[str, Sequence[Sequence[Expression]]] | None = None,
        bosonic_cde_trace_names: Sequence[str] | None = None,
        bosonic_cde_max_total_order: int | None = None,
        bosonic_cde_max_slot_order: int | None = None,
        bosonic_cde_index_prefix: str = "cde",
        bosonic_cde_act_open_derivatives: bool = False,
        bosonic_cde_emit_covariant_derivative_commutators: bool = False,
        bosonic_cde_emit_covariant_derivative_commutator_passes: int = 1,
        bosonic_cde_expand_covariant_derivative_commutators: bool = False,
        wilson_line_expansion_indices_by_trace: Mapping[str, Sequence[Sequence[Expression]]] | None = None,
        wilson_line_trace_names: Sequence[str] | None = None,
        wilson_line_max_total_order: int | None = None,
        wilson_line_max_slot_order: int | None = None,
        wilson_line_index_prefix: str = "wilson_line",
        wilson_line_act_open_derivatives: bool = False,
        wilson_line_emit_covariant_derivative_commutators: bool = False,
        wilson_line_emit_covariant_derivative_commutator_passes: int = 1,
        wilson_line_covariant_derivative_commutator_mode: CovariantDerivativeCommutatorModeInput = "inversions",
        wilson_line_expand_covariant_derivative_commutators: bool = False,
        wilson_line_max_derivative_order: int = 4,
        wilson_line_filter_terms_by_matching_targets: bool = False,
        wilson_line_expose_scalar_derivative_commutator_bilinears: bool = False,
        wilson_line_expose_scalar_eom_terms: bool = False,
        wilson_line_tensor_reduce_before_wilson_expand: bool = False,
        matching_condition_targets: Mapping[str, Expression] | Iterable[Expression] | str | None = None,
        simplify_pychete_color_algebra: bool = False,
        on_shell_eom_lagrangian: Expression | str | None = None,
        on_shell_eom_fields: Sequence[Any] | None = None,
        on_shell_eom_min_derivative_order: int = 2,
        on_shell_eom_strict: bool = False,
        on_shell_eom_abelian_vector_field_redefinition: bool = False,
        on_shell_replacement_repeat: bool = False,
        substitute_heavy_scalar_solutions: bool = False,
        heavy_scalar_solution_lagrangian: Expression | str | None = None,
        heavy_scalar_solution_expand: bool = False,
    ) -> MatchingResult:
        """Build the current incomplete interaction-power preview from fixture expressions."""

        if wilson_line_filter_terms_by_matching_targets and matching_condition_targets is None:
            raise ValueError("Wilson-line target filtering requires matching_condition_targets")
        selected_backend = OneLoopIntegralBackend.from_user(integral_backend)
        normalization_label = one_loop_normalization_label(normalization)
        _LOGGER.info(
            (
                "building one-loop preview for fixture %s "
                "(backend=%s, normalization=%s, eft_order=%s, max_trace_order=%s)"
            ),
            self.name,
            selected_backend.value,
            normalization_label,
            eft_order,
            max_trace_order,
        )
        theory = self.theory()
        resolved_hbar = hbar if hbar is not None else _optional_no_index_external(theory, "hbar")
        lagrangian_expr = self.expression(lagrangian)
        explicit_heavy_scalar_solution_lagrangian = heavy_scalar_solution_lagrangian is not None
        resolved_heavy_scalar_solution_lagrangian = (
            self.expression(heavy_scalar_solution_lagrangian)
            if isinstance(heavy_scalar_solution_lagrangian, str)
            else heavy_scalar_solution_lagrangian
        )
        resolved_on_shell_eom_lagrangian = (
            self.expression(on_shell_eom_lagrangian)
            if isinstance(on_shell_eom_lagrangian, str)
            else on_shell_eom_lagrangian
        )
        if expand_abelian_covariant_derivatives:
            lagrangian_expr = theory.expand_abelian_covariant_derivatives(lagrangian_expr)
        if expand_non_abelian_covariant_derivatives:
            lagrangian_expr = theory.expand_non_abelian_covariant_derivatives(lagrangian_expr)
        if emit_covariant_derivative_commutators:
            lagrangian_expr = theory.emit_covariant_derivative_commutators(
                lagrangian_expr,
                max_passes=emit_covariant_derivative_commutator_passes,
            )
        if expand_covariant_derivative_commutators:
            lagrangian_expr = theory.expand_covariant_derivative_commutators(lagrangian_expr)
        heavy_scalar_solutions = None
        if substitute_heavy_scalar_solutions:
            solution_lagrangian = (
                resolved_heavy_scalar_solution_lagrangian
                if resolved_heavy_scalar_solution_lagrangian is not None
                else lagrangian_expr
            )
            theory._validate_registered_expression(solution_lagrangian)
            heavy_scalar_solutions = solve_heavy_scalar_eoms(theory, solution_lagrangian, eft_order=eft_order)
        setup = theory.one_loop_setup(
            lagrangian_expr,
            eft_order=eft_order,
            max_trace_order=max_trace_order,
            include_light_only=include_light_only,
        )
        if simplify_pychete_color_algebra:
            setup = setup.simplify_index_algebra(
                expand=False,
                gamma=False,
                color=False,
                pychete_color=True,
                metrics=False,
                dots=False,
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
        bosonic_cde_expansion_request: Any = bosonic_cde_expansion_indices_by_trace
        if bosonic_cde_expansion_request is None and bosonic_cde_max_total_order is not None:
            bosonic_cde_expansion_request = setup.interaction_bosonic_cde_expansion_plan(
                trace_names=bosonic_cde_trace_names,
                max_total_order=bosonic_cde_max_total_order,
                max_slot_order=bosonic_cde_max_slot_order,
                index_prefix=bosonic_cde_index_prefix,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
            )
        wilson_line_expansion_request: Any = wilson_line_expansion_indices_by_trace
        if wilson_line_expansion_request is None and wilson_line_max_total_order is not None:
            wilson_line_expansion_request = setup.interaction_wilson_line_expansion_plan(
                trace_names=wilson_line_trace_names,
                max_total_order=wilson_line_max_total_order,
                max_slot_order=wilson_line_max_slot_order,
                index_prefix=wilson_line_index_prefix,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                include_light_only=include_light_only,
            )
        if bosonic_cde_expansion_request is not None and wilson_line_expansion_request is not None:
            raise ValueError("CDE and Wilson-line expansion options are mutually exclusive")
        wilson_line_term_atom_requirements = (
            _term_atom_requirements_for_targets(
                theory,
                matching_condition_targets,
                heavy_scalar_solutions=heavy_scalar_solutions,
            )
            if wilson_line_filter_terms_by_matching_targets and wilson_line_expansion_request is not None
            else None
        )
        if (
            wilson_line_expansion_request is not None
            and selected_backend is OneLoopIntegralBackend.INTERNAL
        ):
            result = setup.interaction_wilson_line_hybrid_internal_matching_result(
                wilson_line_expansion_request,
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                include_light_only=include_light_only,
                act_open_derivatives=wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=wilson_line_expand_covariant_derivative_commutators,
                max_wilson_derivative_order=wilson_line_max_derivative_order,
                tensor_reduce=internal_tensor_reduce,
                tensor_reduce_engine=vakint_engine,
                tensor_reduce_before_wilson_expand=wilson_line_tensor_reduce_before_wilson_expand,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
                combine_terms=internal_combine_terms,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_expose_scalar_derivative_commutator_bilinears
                ),
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
        elif (
            wilson_line_expansion_request is not None
            and selected_backend is OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION
        ):
            result = setup.interaction_wilson_line_hybrid_internal_minimal_subtraction_result(
                wilson_line_expansion_request,
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                include_light_only=include_light_only,
                act_open_derivatives=wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=wilson_line_expand_covariant_derivative_commutators,
                max_wilson_derivative_order=wilson_line_max_derivative_order,
                tensor_reduce=internal_tensor_reduce,
                tensor_reduce_engine=vakint_engine,
                tensor_reduce_before_wilson_expand=wilson_line_tensor_reduce_before_wilson_expand,
                combine_terms=internal_combine_terms,
                max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_expose_scalar_derivative_commutator_bilinears
                ),
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
        elif (
            wilson_line_expansion_request is not None
            and selected_backend is OneLoopIntegralBackend.VAKINT_MINIMAL_SUBTRACTION
        ):
            result = setup.interaction_wilson_line_hybrid_minimal_subtraction_result(
                wilson_line_expansion_request,
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                include_light_only=include_light_only,
                act_open_derivatives=wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=wilson_line_expand_covariant_derivative_commutators,
                max_wilson_derivative_order=wilson_line_max_derivative_order,
                vakint_engine=vakint_engine,
                max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                named_supertrace_stage=named_supertrace_stage,
                named_supertrace_short_form=named_supertrace_short_form,
                named_supertrace_engine=named_supertrace_engine,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_expose_scalar_derivative_commutator_bilinears
                ),
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
        elif wilson_line_expansion_request is not None:
            result = setup.interaction_wilson_line_hybrid_matching_result(
                wilson_line_expansion_request,
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                include_light_only=include_light_only,
                act_open_derivatives=wilson_line_act_open_derivatives,
                emit_covariant_derivative_commutators=wilson_line_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=(
                    wilson_line_emit_covariant_derivative_commutator_passes
                ),
                covariant_derivative_commutator_mode=(
                    wilson_line_covariant_derivative_commutator_mode
                ),
                expand_covariant_derivative_commutators=wilson_line_expand_covariant_derivative_commutators,
                max_wilson_derivative_order=wilson_line_max_derivative_order,
                vakint_stage=vakint_stage,
                vakint_short_form=vakint_short_form,
                vakint_engine=vakint_engine,
                max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                named_supertrace_stage=named_supertrace_stage,
                named_supertrace_short_form=named_supertrace_short_form,
                named_supertrace_engine=named_supertrace_engine,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_expose_scalar_derivative_commutator_bilinears
                ),
                term_atom_requirements=wilson_line_term_atom_requirements,
            )
        elif bosonic_cde_expansion_request is not None and selected_backend is OneLoopIntegralBackend.INTERNAL:
            result = setup.interaction_bosonic_cde_hybrid_internal_matching_result(
                bosonic_cde_expansion_request,
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                act_open_derivatives=bosonic_cde_act_open_derivatives,
                emit_covariant_derivative_commutators=bosonic_cde_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=bosonic_cde_emit_covariant_derivative_commutator_passes,
                expand_covariant_derivative_commutators=bosonic_cde_expand_covariant_derivative_commutators,
                tensor_reduce=internal_tensor_reduce,
                tensor_reduce_engine=vakint_engine,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
                combine_terms=internal_combine_terms,
            )
        elif (
            bosonic_cde_expansion_request is not None
            and selected_backend is OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION
        ):
            result = setup.interaction_bosonic_cde_hybrid_internal_minimal_subtraction_result(
                bosonic_cde_expansion_request,
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                act_open_derivatives=bosonic_cde_act_open_derivatives,
                emit_covariant_derivative_commutators=bosonic_cde_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=bosonic_cde_emit_covariant_derivative_commutator_passes,
                expand_covariant_derivative_commutators=bosonic_cde_expand_covariant_derivative_commutators,
                tensor_reduce=internal_tensor_reduce,
                tensor_reduce_engine=vakint_engine,
                combine_terms=internal_combine_terms,
                max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
            )
        elif (
            bosonic_cde_expansion_request is not None
            and selected_backend is OneLoopIntegralBackend.VAKINT_MINIMAL_SUBTRACTION
        ):
            result = setup.interaction_bosonic_cde_hybrid_minimal_subtraction_result(
                bosonic_cde_expansion_request,
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                act_open_derivatives=bosonic_cde_act_open_derivatives,
                emit_covariant_derivative_commutators=bosonic_cde_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=bosonic_cde_emit_covariant_derivative_commutator_passes,
                expand_covariant_derivative_commutators=bosonic_cde_expand_covariant_derivative_commutators,
                vakint_engine=vakint_engine,
                max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                named_supertrace_stage=named_supertrace_stage,
                named_supertrace_short_form=named_supertrace_short_form,
                named_supertrace_engine=named_supertrace_engine,
            )
        elif bosonic_cde_expansion_request is not None:
            result = setup.interaction_bosonic_cde_hybrid_matching_result(
                bosonic_cde_expansion_request,
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                act_open_derivatives=bosonic_cde_act_open_derivatives,
                emit_covariant_derivative_commutators=bosonic_cde_emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=bosonic_cde_emit_covariant_derivative_commutator_passes,
                expand_covariant_derivative_commutators=bosonic_cde_expand_covariant_derivative_commutators,
                vakint_stage=vakint_stage,
                vakint_short_form=vakint_short_form,
                vakint_engine=vakint_engine,
                max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                named_supertrace_stage=named_supertrace_stage,
                named_supertrace_short_form=named_supertrace_short_form,
                named_supertrace_engine=named_supertrace_engine,
            )
        elif selected_backend is OneLoopIntegralBackend.INTERNAL:
            result = setup.interaction_power_type_internal_matching_result(
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                tensor_reduce=internal_tensor_reduce,
                tensor_reduce_engine=vakint_engine,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
                combine_terms=internal_combine_terms,
            )
        elif selected_backend is OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION:
            result = setup.interaction_power_type_internal_minimal_subtraction_result(
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                tensor_reduce=internal_tensor_reduce,
                tensor_reduce_engine=vakint_engine,
                combine_terms=internal_combine_terms,
                max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
            )
        elif selected_backend is OneLoopIntegralBackend.VAKINT_MINIMAL_SUBTRACTION:
            result = setup.interaction_power_type_minimal_subtraction_result(
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                vakint_engine=vakint_engine,
                max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                named_supertrace_stage=named_supertrace_stage,
                named_supertrace_short_form=named_supertrace_short_form,
                named_supertrace_engine=named_supertrace_engine,
            )
        elif normalization_label != OneLoopNormalization.PREVIEW.value:
            result = setup.interaction_power_type_normalized_matching_result(
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                vakint_stage=vakint_stage,
                vakint_short_form=vakint_short_form,
                vakint_engine=vakint_engine,
                max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                normalization=normalization,
                hbar=resolved_hbar,
                named_supertrace_stage=named_supertrace_stage,
                named_supertrace_short_form=named_supertrace_short_form,
                named_supertrace_engine=named_supertrace_engine,
            )
        else:
            result = setup.interaction_power_type_matching_result(
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
                vakint_stage=vakint_stage,
                vakint_short_form=vakint_short_form,
                vakint_engine=vakint_engine,
                max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                named_supertrace_stage=named_supertrace_stage,
                named_supertrace_short_form=named_supertrace_short_form,
                named_supertrace_engine=named_supertrace_engine,
            )
        if (
            normalization_label != OneLoopNormalization.PREVIEW.value
            and result.metadata.get("loop_normalization_applied") is not True
        ):
            result = result.with_loop_normalization(normalization, hbar=resolved_hbar)
        if simplify_pychete_color_algebra:
            result = _decode_preview_native_color_wrappers(theory, result)
        if substitute_heavy_scalar_solutions:
            solutions = heavy_scalar_solutions or {}
            replacement_rules = heavy_scalar_solution_replacements(solutions, fresh_dummy_indices=True)
            if replacement_rules:
                _LOGGER.info(
                    "substituting %d heavy scalar solution(s) in one-loop preview for fixture %s",
                    len(solutions),
                    self.name,
                )
                result = result.with_on_shell_reduction(
                    replacement_rules,
                    expand=heavy_scalar_solution_expand,
                )
            result = replace(
                result,
                metadata={
                    **result.metadata,
                    "heavy_scalar_solutions_substituted": bool(replacement_rules),
                    "heavy_scalar_solution_count": len(solutions),
                    "heavy_scalar_solution_rule_count": len(replacement_rules),
                    "heavy_scalar_solution_source": (
                        "option" if explicit_heavy_scalar_solution_lagrangian else "matching_lagrangian"
                    ),
                    "heavy_scalar_solution_expand": heavy_scalar_solution_expand,
                    "heavy_scalar_solution_fresh_dummy_indices": True,
                },
            )
        else:
            result = replace(
                result,
                metadata={
                    **result.metadata,
                    "heavy_scalar_solutions_substituted": False,
                    "heavy_scalar_solution_count": 0,
                    "heavy_scalar_solution_rule_count": 0,
                    "heavy_scalar_solution_source": "disabled",
                    "heavy_scalar_solution_expand": False,
                    "heavy_scalar_solution_fresh_dummy_indices": False,
                },
            )
        if resolved_on_shell_eom_lagrangian is not None:
            eom_source = result.on_shell_eft_lagrangian
            eom_rules = theory.eom_replacement_rules_for_expression(
                resolved_on_shell_eom_lagrangian,
                eom_source,
                fields=on_shell_eom_fields,
                eft_order=eft_order,
                min_derivative_order=on_shell_eom_min_derivative_order,
                strict=on_shell_eom_strict,
            )
            vector_field_redefinition_delta = Expression.num(0)
            if on_shell_eom_abelian_vector_field_redefinition:
                vector_field_redefinition_delta = theory.abelian_vector_eom_field_redefinition_delta(
                    resolved_on_shell_eom_lagrangian,
                    eom_source,
                    fields=on_shell_eom_fields,
                    strict=on_shell_eom_strict,
                )
            if eom_rules:
                result = result.with_on_shell_reduction(
                    eom_rules,
                    repeat=on_shell_replacement_repeat,
                )
            if not bool(vector_field_redefinition_delta == Expression.num(0)):
                before_field_redefinition = result.on_shell_eft_lagrangian
                after_field_redefinition = (before_field_redefinition + vector_field_redefinition_delta).expand()
                result = replace(
                    result,
                    on_shell_eft_lagrangian=after_field_redefinition,
                    supertraces={
                        **result.supertraces,
                        "on_shell_eft_lagrangian_before_abelian_vector_field_redefinition": (
                            before_field_redefinition
                        ),
                        "on_shell_eft_lagrangian_after_abelian_vector_field_redefinition": (
                            after_field_redefinition
                        ),
                        "on_shell_eft_lagrangian_abelian_vector_field_redefinition_delta": (
                            vector_field_redefinition_delta
                        ),
                    },
                )
            result = replace(
                result,
                metadata={
                    **result.metadata,
                    "on_shell_eom_reduction_requested": True,
                    "on_shell_eom_reduction_rule_count": len(eom_rules),
                    "on_shell_eom_min_derivative_order": on_shell_eom_min_derivative_order,
                    "on_shell_eom_strict": on_shell_eom_strict,
                    "on_shell_eom_abelian_vector_field_redefinition": (
                        on_shell_eom_abelian_vector_field_redefinition
                    ),
                    "on_shell_eom_abelian_vector_field_redefinition_applied": (
                        not bool(vector_field_redefinition_delta == Expression.num(0))
                    ),
                },
            )
        if wilson_line_expose_scalar_derivative_commutator_bilinears or wilson_line_expose_scalar_eom_terms:
            before_scalar_exposure = result.on_shell_eft_lagrangian
            scalar_exposed_on_shell = _apply_wilson_line_post_integral_scalar_commutator_bilinears(
                theory,
                before_scalar_exposure,
                eom_lagrangian=resolved_on_shell_eom_lagrangian,
                eom_fields=on_shell_eom_fields,
                expose_scalar_eom_terms=wilson_line_expose_scalar_eom_terms,
            )
            reduced_on_shell = scalar_exposed_on_shell
            scalar_commutator_vector_eom_rule_count = 0
            scalar_commutator_vector_field_redefinition_delta = Expression.num(0)
            if (
                resolved_on_shell_eom_lagrangian is not None
                and on_shell_eom_abelian_vector_field_redefinition
            ):
                (
                    reduced_on_shell,
                    scalar_commutator_vector_eom_rule_count,
                    scalar_commutator_vector_field_redefinition_delta,
                ) = _apply_on_shell_eom_reduction_to_expression(
                    theory,
                    scalar_exposed_on_shell,
                    eom_lagrangian=resolved_on_shell_eom_lagrangian,
                    fields=on_shell_eom_fields,
                    eft_order=eft_order,
                    min_derivative_order=on_shell_eom_min_derivative_order,
                    strict=on_shell_eom_strict,
                    abelian_vector_field_redefinition=True,
                    repeat=on_shell_replacement_repeat,
                )
            after_scalar_eom_field_redefinition = reduced_on_shell
            scalar_eom_field_redefinition_delta = Expression.num(0)
            if wilson_line_expose_scalar_eom_terms:
                assert resolved_on_shell_eom_lagrangian is not None
                scalar_source_lagrangian = (resolved_on_shell_eom_lagrangian + reduced_on_shell).expand()
                (
                    after_scalar_eom_field_redefinition,
                    scalar_eom_field_redefinition_delta,
                ) = _apply_wilson_line_scalar_eom_field_redefinition(
                    theory,
                    reduced_on_shell,
                    source_lagrangian=scalar_source_lagrangian,
                    max_order=eft_order,
                    fields=on_shell_eom_fields,
                    strict=on_shell_eom_strict,
                )
            scalar_supertraces = {
                **result.supertraces,
                "on_shell_eft_lagrangian_before_scalar_commutator_bilinear_exposure": (
                    before_scalar_exposure
                ),
                "on_shell_eft_lagrangian_after_scalar_commutator_bilinear_exposure": scalar_exposed_on_shell,
            }
            if scalar_commutator_vector_eom_rule_count or not bool(
                scalar_commutator_vector_field_redefinition_delta == Expression.num(0)
            ):
                scalar_supertraces = {
                    **scalar_supertraces,
                    "on_shell_eft_lagrangian_after_scalar_commutator_abelian_vector_eom_reduction": (
                        reduced_on_shell
                    ),
                    "on_shell_eft_lagrangian_scalar_commutator_abelian_vector_field_redefinition_delta": (
                        scalar_commutator_vector_field_redefinition_delta
                    ),
                }
            if wilson_line_expose_scalar_eom_terms:
                scalar_supertraces = {
                    **scalar_supertraces,
                    "on_shell_eft_lagrangian_scalar_eom_field_redefinition_delta": (
                        scalar_eom_field_redefinition_delta
                    ),
                    "on_shell_eft_lagrangian_after_scalar_eom_field_redefinition": (
                        after_scalar_eom_field_redefinition
                    ),
                }
            result = replace(
                result,
                on_shell_eft_lagrangian=after_scalar_eom_field_redefinition,
                supertraces=scalar_supertraces,
                metadata={
                    **result.metadata,
                    "wilson_line_scalar_commutator_bilinears_reduced": (
                        wilson_line_expose_scalar_derivative_commutator_bilinears
                    ),
                    "wilson_line_scalar_eom_terms_reduced": wilson_line_expose_scalar_eom_terms,
                    "wilson_line_scalar_eom_field_redefinition_applied": (
                        not bool(scalar_eom_field_redefinition_delta == Expression.num(0))
                    ),
                    "wilson_line_scalar_commutator_abelian_vector_eom_reduction_rule_count": (
                        scalar_commutator_vector_eom_rule_count
                    ),
                    "wilson_line_scalar_commutator_abelian_vector_field_redefinition_applied": (
                        not bool(scalar_commutator_vector_field_redefinition_delta == Expression.num(0))
                    ),
                },
            )
        preview = MatchingResult(
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
                "abelian_covariant_derivatives_expanded": expand_abelian_covariant_derivatives,
                "non_abelian_covariant_derivatives_expanded": expand_non_abelian_covariant_derivatives,
                "covariant_derivative_commutators_emitted": emit_covariant_derivative_commutators,
                "covariant_derivative_commutator_emit_passes": (
                    emit_covariant_derivative_commutator_passes
                    if emit_covariant_derivative_commutators
                    else 0
                ),
                "covariant_derivative_commutators_expanded": expand_covariant_derivative_commutators,
                "bosonic_cde_expansion_enabled": bosonic_cde_expansion_request is not None,
                "bosonic_cde_expansion_planned": isinstance(bosonic_cde_expansion_request, BosonicCDEExpansionPlan),
                "bosonic_cde_trace_names": (
                    ",".join(bosonic_cde_trace_names)
                    if bosonic_cde_trace_names is not None
                    else ",".join(bosonic_cde_expansion_indices_by_trace or ())
                ),
                "bosonic_cde_max_total_order": bosonic_cde_max_total_order,
                "bosonic_cde_max_slot_order": bosonic_cde_max_slot_order,
                "bosonic_cde_index_prefix": bosonic_cde_index_prefix,
                "bosonic_cde_act_open_derivatives": bosonic_cde_act_open_derivatives,
                "bosonic_cde_commutators_emitted": bosonic_cde_emit_covariant_derivative_commutators,
                "bosonic_cde_commutator_emit_passes": (
                    bosonic_cde_emit_covariant_derivative_commutator_passes
                    if bosonic_cde_emit_covariant_derivative_commutators
                    else 0
                ),
                "bosonic_cde_commutators_expanded": bosonic_cde_expand_covariant_derivative_commutators,
                "wilson_line_expansion_enabled": wilson_line_expansion_request is not None,
                "wilson_line_expansion_planned": isinstance(wilson_line_expansion_request, WilsonLineExpansionPlan),
                "wilson_line_trace_names": (
                    ",".join(wilson_line_trace_names)
                    if wilson_line_trace_names is not None
                    else (
                        ",".join(wilson_line_expansion_request.trace_names)
                        if isinstance(wilson_line_expansion_request, WilsonLineExpansionPlan)
                        else ",".join(wilson_line_expansion_indices_by_trace or ())
                    )
                ),
                "wilson_line_max_total_order": wilson_line_max_total_order,
                "wilson_line_max_slot_order": wilson_line_max_slot_order,
                "wilson_line_index_prefix": wilson_line_index_prefix,
                "wilson_line_act_open_derivatives": wilson_line_act_open_derivatives,
                "wilson_line_commutators_emitted": wilson_line_emit_covariant_derivative_commutators,
                "wilson_line_commutator_emit_passes": (
                    wilson_line_emit_covariant_derivative_commutator_passes
                    if wilson_line_emit_covariant_derivative_commutators
                    else 0
                ),
                "wilson_line_commutator_emit_mode": (
                    wilson_line_covariant_derivative_commutator_mode
                    if wilson_line_emit_covariant_derivative_commutators
                    else None
                ),
                "wilson_line_commutators_expanded": wilson_line_expand_covariant_derivative_commutators,
                "wilson_line_max_derivative_order": wilson_line_max_derivative_order,
                "wilson_line_tensor_reduce_before_wilson_expand": (
                    wilson_line_tensor_reduce_before_wilson_expand
                ),
                "wilson_line_terms_filtered_by_matching_targets": (
                    wilson_line_term_atom_requirements is not None
                ),
                "wilson_line_scalar_derivative_commutator_bilinears_exposed": (
                    wilson_line_expose_scalar_derivative_commutator_bilinears
                ),
                "wilson_line_scalar_eom_terms_exposed": wilson_line_expose_scalar_eom_terms,
                "pychete_color_algebra_simplified": simplify_pychete_color_algebra,
            },
        )
        _LOGGER.info(
            "one-loop preview for fixture %s contains %d supertraces",
            self.name,
            len(preview.supertraces),
        )
        return preview

    def one_loop_preview_gap_report(
        self,
        reference: MatchingResult,
        *,
        reference_name: str = "reference",
        lagrangian: str = "lagrangian",
        eft_order: int = 6,
        max_trace_order: TraceOrderInput = 2,
        include_light_only: bool = False,
        heavy_field_dimension: bool = False,
        include_light: bool = True,
        vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        vakint_short_form: bool | None = None,
        vakint_engine: Any | None = None,
        integral_backend: OneLoopIntegralBackend | str = OneLoopIntegralBackend.VAKINT,
        normalization: OneLoopNormalizationInput = OneLoopNormalization.PREVIEW,
        hbar: Expression | None = None,
        internal_tensor_reduce: bool = True,
        internal_combine_terms: bool = False,
        internal_max_pole_order: int = 1,
        epsilon: Expression | None = None,
        mu_r_squared: Expression | None = None,
        loop_momentum_squared: Expression | None = None,
        require_registered_mass: bool = True,
        probe_parameters: Sequence[Expression] | None = None,
        probe_samples: Sequence[Sequence[NumericValue]] | None = None,
        probe_supertrace_names: ProbeNameSelection | None = None,
        probe_matching_condition_names: ProbeNameSelection | None = None,
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
        expand_abelian_covariant_derivatives: bool = False,
        expand_non_abelian_covariant_derivatives: bool = False,
        emit_covariant_derivative_commutators: bool = False,
        emit_covariant_derivative_commutator_passes: int = 1,
        expand_covariant_derivative_commutators: bool = False,
        bosonic_cde_expansion_indices_by_trace: Mapping[str, Sequence[Sequence[Expression]]] | None = None,
        bosonic_cde_trace_names: Sequence[str] | None = None,
        bosonic_cde_max_total_order: int | None = None,
        bosonic_cde_max_slot_order: int | None = None,
        bosonic_cde_index_prefix: str = "cde",
        bosonic_cde_act_open_derivatives: bool = False,
        bosonic_cde_emit_covariant_derivative_commutators: bool = False,
        bosonic_cde_emit_covariant_derivative_commutator_passes: int = 1,
        bosonic_cde_expand_covariant_derivative_commutators: bool = False,
        bosonic_cde_filter_terms_by_matching_targets: bool = False,
        wilson_line_expansion_indices_by_trace: Mapping[str, Sequence[Sequence[Expression]]] | None = None,
        wilson_line_trace_names: Sequence[str] | None = None,
        wilson_line_max_total_order: int | None = None,
        wilson_line_max_slot_order: int | None = None,
        wilson_line_index_prefix: str = "wilson_line",
        wilson_line_act_open_derivatives: bool = False,
        wilson_line_emit_covariant_derivative_commutators: bool = False,
        wilson_line_emit_covariant_derivative_commutator_passes: int = 1,
        wilson_line_covariant_derivative_commutator_mode: CovariantDerivativeCommutatorModeInput = "inversions",
        wilson_line_expand_covariant_derivative_commutators: bool = False,
        wilson_line_max_derivative_order: int = 4,
        wilson_line_filter_terms_by_matching_targets: bool = False,
        wilson_line_expose_scalar_derivative_commutator_bilinears: bool = False,
        wilson_line_expose_scalar_eom_terms: bool = False,
        wilson_line_tensor_reduce_before_wilson_expand: bool = False,
        simplify_pychete_color_algebra: bool = False,
        on_shell_eom_lagrangian: Expression | str | None = None,
        on_shell_eom_fields: Sequence[Any] | None = None,
        on_shell_eom_min_derivative_order: int = 2,
        on_shell_eom_strict: bool = False,
        on_shell_eom_abelian_vector_field_redefinition: bool = False,
        on_shell_replacement_repeat: bool = False,
        substitute_heavy_scalar_solutions: bool = False,
        heavy_scalar_solution_lagrangian: Expression | str | None = None,
        heavy_scalar_solution_expand: bool = False,
        include_tree_level_matching: bool = False,
        truncate_eft_result: bool = True,
        project_reference_matching_conditions: bool = False,
        matching_condition_projection_names: ProjectionNameSelection | None = None,
        matching_condition_projection_source: str = "on_shell_eft_lagrangian",
        matching_condition_projection_expand_source: bool = True,
        matching_condition_projection_canonize_indices: bool = True,
        matching_condition_projection_normalize_derivative_operators: bool = True,
        matching_condition_projection_normalize_ibp_scalar_bilinears: bool = False,
        matching_condition_projection_truncate_eft: bool = False,
        matching_condition_projection_drop_zero: bool = False,
        matching_condition_include_coupling_identities: bool = True,
        use_public_match_api: bool = False,
        simplify_loop_functions_for_comparison: bool = False,
        evaluate_loop_functions_for_comparison: bool = False,
        comparison_combine_terms: bool = True,
        comparison_canonize_indices: bool = True,
    ) -> MatchingFixtureGapReport:
        """Report current one-loop preview coverage against a reference result.

        Set ``max_trace_order="reference"`` to generate traces up to the
        largest supertrace word order present in the reference fixture.
        ``probe_supertrace_names`` and ``probe_matching_condition_names`` may
        be explicit name iterables, ``"common"``, or ``"canonical_different"``.
        Matching-condition probes additionally accept ``"wilson"`` and
        ``"canonical_different_wilson"`` to focus evaluator probes on SMEFT
        Wilson-coefficient targets identified from Symbolica symbol metadata.
        Derivative-operator normalization is enabled by default so explicit
        ``CD(...)`` operators in fixture metadata project against generated
        field-derivative-slot one-loop sources.
        Set ``matching_condition_projection_normalize_ibp_scalar_bilinears``
        to additionally recognize target-local total-derivative-equivalent
        scalar bilinear projections such as ``A * CD([mu, mu], B)``.
        When ``use_public_match_api=True``, set ``truncate_eft_result=False``
        together with ``matching_condition_projection_truncate_eft=True`` to
        avoid a global EFT truncation before target-local Wilson projection.
        ``bosonic_cde_filter_terms_by_matching_targets`` is available only on
        the public match route with ``project_reference_matching_conditions``:
        it forwards target-compatible CDE term filtering to
        :class:`OneLoopMatchOptions`.
        ``wilson_line_filter_terms_by_matching_targets`` forwards
        target-compatible Wilson-line term filtering for generated or explicit
        Wilson-line expansion requests. It works through the public matcher or
        this fixture's direct preview route as long as reference matching
        conditions are being projected.
        ``wilson_line_expose_scalar_derivative_commutator_bilinears`` forwards
        the opt-in post-evaluation scalar two-derivative
        commutator-bilinear exposure pass to Wilson-line internal and vakint
        preview routes.
        ``wilson_line_expose_scalar_eom_terms`` additionally enables formal
        scalar-EOM exposure in that Green pass and requires
        ``on_shell_eom_lagrangian``.
        ``wilson_line_tensor_reduce_before_wilson_expand`` forwards the
        Matchete-order internal Wilson-line path where loop-momentum tensor
        reduction contracts metrics into formal Wilson terms before supported
        Wilson-term expansion.
        ``wilson_line_covariant_derivative_commutator_mode`` forwards the
        Wilson-line local commutator identity mode, including the bounded
        Matchete-adjacent ``"all_distinct"`` mode used by current Singlet
        frontier probes.
        ``on_shell_eom_lagrangian`` may be a fixture expression name or
        expression and forwards the public one-loop EOM reduction path. The
        bounded ``on_shell_eom_abelian_vector_field_redefinition`` option also
        forwards the current scalar-current Abelian vector field-redefinition
        companion used by the Singlet ``cHD`` frontier.
        ``substitute_heavy_scalar_solutions`` applies the same heavy-scalar
        on-shell replacement pass as the public one-loop matcher before direct
        preview matching-condition projection. ``heavy_scalar_solution_lagrangian``
        may be either a fixture expression name or a validated expression.
        Prefer the ``wilson_line_*`` options for current-Matchete-style
        selected trace expansion. They route through the hybrid Wilson-line
        matcher and are mutually exclusive with the legacy ``bosonic_cde_*``
        expansion options. For generated Wilson-line plans, set
        ``wilson_line_max_total_order`` and optionally
        ``wilson_line_trace_names``/``wilson_line_max_slot_order``.
        ``matching_condition_projection_names`` restricts projected reference
        matching conditions to a target-local subset. Entries may be canonical
        condition names or external Wilson names such as ``cHW``; the reserved
        string ``"wilson"`` selects all Wilson-coefficient conditions.
        ``comparison_canonize_indices`` keeps Symbolica tensor-index
        canonicalization enabled for common-expression comparisons so fixture
        reports do not flag alpha-equivalent dummy-index relabelings as gaps.
        """

        _LOGGER.info("building one-loop preview gap report for fixture %s against %s", self.name, reference_name)
        resolved_max_trace_order = _resolve_max_trace_order(max_trace_order, reference)
        if matching_condition_projection_names is not None and not project_reference_matching_conditions:
            raise ValueError(
                "matching_condition_projection_names requires project_reference_matching_conditions=True"
            )
        if bosonic_cde_filter_terms_by_matching_targets and not use_public_match_api:
            raise ValueError("CDE target filtering in fixture reports requires use_public_match_api=True")
        if bosonic_cde_filter_terms_by_matching_targets and not project_reference_matching_conditions:
            raise ValueError(
                "CDE target filtering in fixture reports requires project_reference_matching_conditions=True"
            )
        if wilson_line_filter_terms_by_matching_targets and not project_reference_matching_conditions:
            raise ValueError(
                "Wilson-line target filtering in fixture reports requires project_reference_matching_conditions=True"
            )
        projected_target_selection = (
            _matching_condition_projection_targets(
                self.theory(),
                reference,
                names=matching_condition_projection_names,
            )
            if project_reference_matching_conditions
            else None
        )
        projected_targets = projected_target_selection.targets if projected_target_selection is not None else None
        reference_for_report = (
            _reference_with_matching_conditions(reference, tuple(projected_targets or ()))
            if matching_condition_projection_names is not None and projected_targets is not None
            else reference
        )
        resolved_hbar = hbar if hbar is not None else _optional_no_index_external(self.theory(), "hbar")
        resolved_heavy_scalar_solution_lagrangian = (
            self.expression(heavy_scalar_solution_lagrangian)
            if isinstance(heavy_scalar_solution_lagrangian, str)
            else heavy_scalar_solution_lagrangian
        )
        resolved_on_shell_eom_lagrangian = (
            self.expression(on_shell_eom_lagrangian)
            if isinstance(on_shell_eom_lagrangian, str)
            else on_shell_eom_lagrangian
        )
        if use_public_match_api:
            matched = self.theory().match(
                self.expression(lagrangian),
                eft_order=eft_order,
                loop_order=1,
                one_loop_options=OneLoopMatchOptions(
                    max_trace_order=resolved_max_trace_order,
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
                    normalization=normalization,
                    hbar=resolved_hbar,
                    tensor_reduce=internal_tensor_reduce,
                    tensor_reduce_engine=vakint_engine,
                    combine_terms=internal_combine_terms,
                    max_pole_order=internal_max_pole_order,
                    epsilon=epsilon,
                    mu_r_squared=mu_r_squared,
                    loop_momentum_squared=loop_momentum_squared,
                    require_registered_mass=require_registered_mass,
                    evaluate_tensor_networks=evaluate_tensor_networks,
                    tensor_network_library=tensor_network_library,
                    tensor_network_cg_components_by_name=tensor_network_cg_components_by_name,
                    tensor_network_builtin_cg_components=tensor_network_builtin_cg_components,
                    tensor_network_native_hep_cg_builtins=tensor_network_native_hep_cg_builtins,
                    tensor_network_symbolic_cg_components=tensor_network_symbolic_cg_components,
                    tensor_network_function_library=tensor_network_function_library,
                    tensor_network_n_steps=tensor_network_n_steps,
                    tensor_network_mode=tensor_network_mode,
                    expand_abelian_covariant_derivatives=expand_abelian_covariant_derivatives,
                    expand_non_abelian_covariant_derivatives=expand_non_abelian_covariant_derivatives,
                    emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                    emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                    expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                    bosonic_cde_expansion_indices_by_trace=bosonic_cde_expansion_indices_by_trace,
                    bosonic_cde_trace_names=bosonic_cde_trace_names,
                    bosonic_cde_max_total_order=bosonic_cde_max_total_order,
                    bosonic_cde_max_slot_order=bosonic_cde_max_slot_order,
                    bosonic_cde_index_prefix=bosonic_cde_index_prefix,
                    bosonic_cde_act_open_derivatives=bosonic_cde_act_open_derivatives,
                    bosonic_cde_emit_covariant_derivative_commutators=bosonic_cde_emit_covariant_derivative_commutators,
                    bosonic_cde_emit_covariant_derivative_commutator_passes=(
                        bosonic_cde_emit_covariant_derivative_commutator_passes
                    ),
                    bosonic_cde_expand_covariant_derivative_commutators=(
                        bosonic_cde_expand_covariant_derivative_commutators
                    ),
                    bosonic_cde_filter_terms_by_matching_targets=bosonic_cde_filter_terms_by_matching_targets,
                    wilson_line_expansion_indices_by_trace=wilson_line_expansion_indices_by_trace,
                    wilson_line_trace_names=wilson_line_trace_names,
                    wilson_line_max_total_order=wilson_line_max_total_order,
                    wilson_line_max_slot_order=wilson_line_max_slot_order,
                    wilson_line_index_prefix=wilson_line_index_prefix,
                    wilson_line_act_open_derivatives=wilson_line_act_open_derivatives,
                    wilson_line_emit_covariant_derivative_commutators=(
                        wilson_line_emit_covariant_derivative_commutators
                    ),
                    wilson_line_emit_covariant_derivative_commutator_passes=(
                        wilson_line_emit_covariant_derivative_commutator_passes
                    ),
                    wilson_line_covariant_derivative_commutator_mode=(
                        wilson_line_covariant_derivative_commutator_mode
                    ),
                    wilson_line_expand_covariant_derivative_commutators=(
                        wilson_line_expand_covariant_derivative_commutators
                    ),
                    wilson_line_max_derivative_order=wilson_line_max_derivative_order,
                    wilson_line_filter_terms_by_matching_targets=wilson_line_filter_terms_by_matching_targets,
                    wilson_line_expose_scalar_derivative_commutator_bilinears=(
                        wilson_line_expose_scalar_derivative_commutator_bilinears
                    ),
                    wilson_line_expose_scalar_eom_terms=wilson_line_expose_scalar_eom_terms,
                    wilson_line_tensor_reduce_before_wilson_expand=(
                        wilson_line_tensor_reduce_before_wilson_expand
                    ),
                    simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                    on_shell_eom_lagrangian=resolved_on_shell_eom_lagrangian,
                    on_shell_eom_fields=on_shell_eom_fields,
                    on_shell_eom_min_derivative_order=on_shell_eom_min_derivative_order,
                    on_shell_eom_strict=on_shell_eom_strict,
                    on_shell_eom_abelian_vector_field_redefinition=(
                        on_shell_eom_abelian_vector_field_redefinition
                    ),
                    on_shell_replacement_repeat=on_shell_replacement_repeat,
                    substitute_heavy_scalar_solutions=substitute_heavy_scalar_solutions,
                    heavy_scalar_solution_lagrangian=resolved_heavy_scalar_solution_lagrangian,
                    heavy_scalar_solution_expand=heavy_scalar_solution_expand,
                    include_tree_level_matching=include_tree_level_matching,
                    truncate_eft_result=truncate_eft_result,
                ),
                matching_condition_targets=projected_targets,
                matching_condition_source=matching_condition_projection_source,
                matching_condition_expand_source=matching_condition_projection_expand_source,
                matching_condition_canonize_indices=matching_condition_projection_canonize_indices,
                matching_condition_normalize_derivative_operators=(
                    matching_condition_projection_normalize_derivative_operators
                ),
                matching_condition_normalize_ibp_scalar_bilinears=(
                    matching_condition_projection_normalize_ibp_scalar_bilinears
                ),
                matching_condition_truncate_eft=matching_condition_projection_truncate_eft,
                matching_condition_drop_zero=matching_condition_projection_drop_zero,
                matching_condition_include_coupling_identities=(
                    matching_condition_include_coupling_identities
                ),
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
                    "fixture_preview_source": "public_match_api",
                },
            )
        else:
            candidate = self.one_loop_preview(
                lagrangian=lagrangian,
                eft_order=eft_order,
                max_trace_order=resolved_max_trace_order,
                include_light_only=include_light_only,
                heavy_field_dimension=heavy_field_dimension,
                include_light=include_light,
                vakint_stage=vakint_stage,
                vakint_short_form=vakint_short_form,
                vakint_engine=vakint_engine,
                integral_backend=integral_backend,
                normalization=normalization,
                hbar=resolved_hbar,
                internal_tensor_reduce=internal_tensor_reduce,
                internal_combine_terms=internal_combine_terms,
                internal_max_pole_order=internal_max_pole_order,
                epsilon=epsilon,
                mu_r_squared=mu_r_squared,
                loop_momentum_squared=loop_momentum_squared,
                require_registered_mass=require_registered_mass,
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
                expand_abelian_covariant_derivatives=expand_abelian_covariant_derivatives,
                expand_non_abelian_covariant_derivatives=expand_non_abelian_covariant_derivatives,
                emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
                expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
                bosonic_cde_expansion_indices_by_trace=bosonic_cde_expansion_indices_by_trace,
                bosonic_cde_trace_names=bosonic_cde_trace_names,
                bosonic_cde_max_total_order=bosonic_cde_max_total_order,
                bosonic_cde_max_slot_order=bosonic_cde_max_slot_order,
                bosonic_cde_index_prefix=bosonic_cde_index_prefix,
                bosonic_cde_act_open_derivatives=bosonic_cde_act_open_derivatives,
                bosonic_cde_emit_covariant_derivative_commutators=bosonic_cde_emit_covariant_derivative_commutators,
                bosonic_cde_emit_covariant_derivative_commutator_passes=(
                    bosonic_cde_emit_covariant_derivative_commutator_passes
                ),
                bosonic_cde_expand_covariant_derivative_commutators=(
                    bosonic_cde_expand_covariant_derivative_commutators
                ),
                wilson_line_expansion_indices_by_trace=wilson_line_expansion_indices_by_trace,
                wilson_line_trace_names=wilson_line_trace_names,
                wilson_line_max_total_order=wilson_line_max_total_order,
                wilson_line_max_slot_order=wilson_line_max_slot_order,
                wilson_line_index_prefix=wilson_line_index_prefix,
                wilson_line_act_open_derivatives=wilson_line_act_open_derivatives,
                wilson_line_emit_covariant_derivative_commutators=(
                    wilson_line_emit_covariant_derivative_commutators
                ),
                wilson_line_emit_covariant_derivative_commutator_passes=(
                    wilson_line_emit_covariant_derivative_commutator_passes
                ),
                wilson_line_covariant_derivative_commutator_mode=(
                    wilson_line_covariant_derivative_commutator_mode
                ),
                wilson_line_expand_covariant_derivative_commutators=(
                    wilson_line_expand_covariant_derivative_commutators
                ),
                wilson_line_max_derivative_order=wilson_line_max_derivative_order,
                wilson_line_filter_terms_by_matching_targets=wilson_line_filter_terms_by_matching_targets,
                wilson_line_expose_scalar_derivative_commutator_bilinears=(
                    wilson_line_expose_scalar_derivative_commutator_bilinears
                ),
                wilson_line_expose_scalar_eom_terms=wilson_line_expose_scalar_eom_terms,
                wilson_line_tensor_reduce_before_wilson_expand=(
                    wilson_line_tensor_reduce_before_wilson_expand
                ),
                matching_condition_targets=projected_targets,
                simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                on_shell_eom_lagrangian=resolved_on_shell_eom_lagrangian,
                on_shell_eom_fields=on_shell_eom_fields,
                on_shell_eom_min_derivative_order=on_shell_eom_min_derivative_order,
                on_shell_eom_strict=on_shell_eom_strict,
                on_shell_eom_abelian_vector_field_redefinition=(
                    on_shell_eom_abelian_vector_field_redefinition
                ),
                on_shell_replacement_repeat=on_shell_replacement_repeat,
                substitute_heavy_scalar_solutions=substitute_heavy_scalar_solutions,
                heavy_scalar_solution_lagrangian=resolved_heavy_scalar_solution_lagrangian,
                heavy_scalar_solution_expand=heavy_scalar_solution_expand,
            )
        if project_reference_matching_conditions and not use_public_match_api:
            candidate = candidate.with_projected_matching_conditions(
                projected_targets or {},
                source=matching_condition_projection_source,
                expand_source=matching_condition_projection_expand_source,
                canonize_indices=matching_condition_projection_canonize_indices,
                normalize_derivative_operators=matching_condition_projection_normalize_derivative_operators,
                normalize_ibp_scalar_bilinears=matching_condition_projection_normalize_ibp_scalar_bilinears,
                eft_order=eft_order if matching_condition_projection_truncate_eft else None,
                heavy_field_dimension=heavy_field_dimension,
                drop_zero=matching_condition_projection_drop_zero,
                include_coupling_identities=matching_condition_include_coupling_identities,
            )
        with progress(f"comparing fixture {self.name} one-loop preview to {reference_name}", logger=_LOGGER):
            report = _gap_report(
                self.name,
                reference_name,
                candidate,
                reference_for_report,
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
                comparison_expression_transform=_comparison_expression_transform(
                    simplify_loop_functions_for_comparison=simplify_loop_functions_for_comparison,
                    evaluate_loop_functions_for_comparison=evaluate_loop_functions_for_comparison,
                    comparison_combine_terms=comparison_combine_terms,
                ),
                comparison_canonize_indices=comparison_canonize_indices,
                matching_condition_projection_targets=projected_target_selection,
            )
        _LOGGER.info(
            (
                "gap report for fixture %s: %d/%d common supertraces canonical-equal, "
                "%d/%d common matching conditions canonical-equal"
            ),
            self.name,
            report.canonical_equal_common_supertrace_count,
            len(report.common_supertrace_names),
            report.canonical_equal_common_matching_condition_count,
            len(report.common_matching_condition_names),
        )
        return report

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


def _decode_preview_native_color_wrappers(theory: Theory, result: MatchingResult) -> MatchingResult:
    from .backends import idenso as idenso_backend

    def simplify(expression: Expression) -> Expression:
        return idenso_backend.decode_native_color_wrappers_and_simplify_field_strengths(theory, expression)

    return replace(
        result,
        off_shell_eft_lagrangian=simplify(result.off_shell_eft_lagrangian),
        on_shell_eft_lagrangian=simplify(result.on_shell_eft_lagrangian),
        matching_conditions={name: simplify(expression) for name, expression in result.matching_conditions.items()},
        supertraces={name: simplify(expression) for name, expression in result.supertraces.items()},
        metadata={
            **result.metadata,
            "native_color_wrappers_decoded": True,
            "post_decode_field_strength_metric_simplified": True,
            "su2_field_strength_generator_bilinears_simplified": True,
            "su2_u1_field_strength_generator_bilinears_simplified": True,
        },
    )


def _sorted_names(names: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(names))


def _validation_supertrace_names(supertraces: Mapping[str, Expression]) -> set[str]:
    return {name for name in supertraces if not is_unnormalized_supertrace_alias(name)}


def _resolve_max_trace_order(max_trace_order: TraceOrderInput, reference: MatchingResult) -> int:
    if max_trace_order == "reference":
        return max(1, _max_supertrace_order(reference.supertraces))
    if not isinstance(max_trace_order, int):
        raise ValueError("max_trace_order must be an integer or 'reference'")
    return max_trace_order


def _max_supertrace_order(names: Iterable[str]) -> int:
    return max((supertrace_word_order(name) for name in names), default=0)


def _names_at_supertrace_order(names: Iterable[str], order: int) -> tuple[str, ...]:
    return _sorted_names(name for name in names if supertrace_word_order(name) == order)


def _supertrace_order_coverage(report: MatchingFixtureGapReport) -> tuple[SupertraceOrderCoverage, ...]:
    orders = sorted(
        {
            supertrace_word_order(name)
            for name in (*report.candidate_supertrace_names, *report.reference_supertrace_names)
            if supertrace_word_order(name) > 0
        }
    )
    return tuple(
        SupertraceOrderCoverage(
            order=order,
            candidate_names=_names_at_supertrace_order(report.candidate_supertrace_names, order),
            reference_names=_names_at_supertrace_order(report.reference_supertrace_names, order),
            common_names=_names_at_supertrace_order(report.common_supertrace_names, order),
            candidate_only_names=_names_at_supertrace_order(report.candidate_only_supertrace_names, order),
            reference_only_names=_names_at_supertrace_order(report.reference_only_supertrace_names, order),
            canonical_equal_common_names=_names_at_supertrace_order(
                report.canonical_equal_common_supertrace_names,
                order,
            ),
            accepted_common_names=_names_at_supertrace_order(report.accepted_common_supertrace_names, order),
            different_after_probe_common_names=_names_at_supertrace_order(
                report.different_after_probe_common_supertrace_names,
                order,
            ),
        )
        for order in orders
    )


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


def _matching_condition_projection_targets(
    theory: Theory,
    reference: MatchingResult,
    *,
    names: ProjectionNameSelection | None = None,
) -> _MatchingConditionProjectionTargets:
    registered_wilsons = registered_wilson_matching_condition_targets(theory)
    registered_wilsons_by_external_name = _registered_wilson_targets_by_external_name(theory)
    selected_names = _projection_name_selection_set(names)
    seen_selected_names: set[str] = set()
    targets: dict[str, Expression] = {}
    registered_wilson_names: list[str] = []
    reference_non_wilson_names: list[str] = []
    reference_wilson_fallback_names: list[str] = []
    for target in reference.matching_condition_targets():
        target_names = _matching_condition_target_selection_names(target)
        if selected_names is not None and "wilson" not in selected_names and not (selected_names & target_names):
            continue
        if selected_names is not None and "wilson" in selected_names and not target.is_wilson_coefficient:
            continue
        if selected_names is not None:
            seen_selected_names.update(selected_names & target_names)
            if "wilson" in selected_names and target.is_wilson_coefficient:
                seen_selected_names.add("wilson")
        if target.is_wilson_coefficient:
            registered_target = registered_wilsons.get(target.name)
            if registered_target is None:
                external_name = _matching_condition_target_external_name(target)
                registered_target = (
                    None
                    if external_name is None
                    else registered_wilsons_by_external_name.get(external_name)
                )
            if registered_target is not None:
                targets[target.name] = registered_target
                registered_wilson_names.append(target.name)
            else:
                targets[target.name] = target.expression
                reference_wilson_fallback_names.append(target.name)
            continue
        targets[target.name] = target.expression
        reference_non_wilson_names.append(target.name)
    result = _MatchingConditionProjectionTargets(
        targets=targets,
        registered_wilson_names=_sorted_names(registered_wilson_names),
        reference_non_wilson_names=_sorted_names(reference_non_wilson_names),
        reference_wilson_fallback_names=_sorted_names(reference_wilson_fallback_names),
    )
    if selected_names is not None:
        missing = selected_names - seen_selected_names
        if missing:
            raise ValueError(f"Unknown matching-condition projection name(s): {', '.join(_sorted_names(missing))}")
    return result


def _projection_name_selection_set(names: ProjectionNameSelection | None) -> set[str] | None:
    if names is None:
        return None
    if isinstance(names, str):
        return {names}
    return {str(name) for name in names}


def _matching_condition_target_selection_names(target: MatchingConditionTarget) -> set[str]:
    names = {target.name}
    external_name = _matching_condition_target_external_name(target)
    if external_name is not None:
        names.add(external_name)
    return names


def _reference_with_matching_conditions(reference: MatchingResult, names: tuple[str, ...]) -> MatchingResult:
    selected = {name: reference.matching_conditions[name] for name in names if name in reference.matching_conditions}
    return replace(reference, matching_conditions=selected)


def _registered_wilson_targets_by_external_name(theory: Theory) -> dict[str, Expression]:
    targets: dict[str, Expression] = {}
    for name, definition in theory.externals.items():
        if definition.kind is not ExternalKind.WILSON_COEFFICIENT:
            continue
        if definition.operator_expr is None:
            continue
        targets[name] = s.Coupling(definition.label, s.List(*definition.index_exprs), Expression.num(definition.order))
    return targets


def _matching_condition_target_external_name(target: MatchingConditionTarget) -> str | None:
    if target.label is None:
        return None
    name = symbol_data(target.label, SymbolDataKey.NAME)
    if isinstance(name, str) and name:
        return name
    label = symbol_data(target.label, SymbolDataKey.LABEL)
    if isinstance(label, str) and label:
        return label
    return None


def _reference_wilson_matching_condition_names(reference: MatchingResult) -> tuple[str, ...]:
    return _sorted_names(
        target.name
        for target in reference.matching_condition_targets()
        if target.is_wilson_coefficient
    )


def _probe_plan_for_names(
    candidate: MatchingResult,
    reference: MatchingResult,
    names: Iterable[str],
    *,
    sample_count: int,
    exclude_symbols: Sequence[Expression],
    parameter_mode: ProbeParameterMode,
    expression_transform: Callable[[Expression], Expression] | None = None,
    canonize_indices: bool = True,
) -> NumericProbePlan:
    expressions: list[Expression] = []
    for name in names:
        try:
            candidate_expression = candidate.expression(name)
        except KeyError:
            candidate_expression = None
        try:
            reference_expression = reference.expression(name)
        except KeyError:
            reference_expression = None
        if expression_transform is not None:
            if candidate_expression is not None:
                candidate_expression = expression_transform(candidate_expression)
            if reference_expression is not None:
                reference_expression = expression_transform(reference_expression)
        if canonize_indices and candidate_expression is not None and reference_expression is not None:
            candidate_canonized, reference_canonized = _canonize_comparison_indices(
                candidate_expression,
                reference_expression,
            )
            expressions.extend((candidate_canonized.expression, reference_canonized.expression))
            continue
        if candidate_expression is not None:
            expressions.append(candidate_expression)
        if reference_expression is not None:
            expressions.append(reference_expression)
    return build_numeric_probe_plan(
        expressions,
        exclude_symbols=exclude_symbols,
        parameter_mode=parameter_mode,
        sample_count=sample_count,
    )


def _canonical_different_names(comparison: Any) -> tuple[str, ...]:
    return tuple(item.name for item in comparison.expressions if not item.canonical_equal)


def _probe_name_selection(
    selection: ProbeNameSelection | None,
    *,
    common_names: Iterable[str],
    canonical_different_names: Iterable[str],
    reference_wilson_names: Iterable[str] = (),
    allow_wilson: bool = False,
) -> tuple[str, ...] | None:
    if selection is None:
        return None
    if isinstance(selection, str):
        if selection not in _PROBE_NAME_PRESETS:
            raise ValueError(
                "Unknown probe-name preset "
                f"{selection!r}; pass a tuple/list when selecting one literal expression name"
            )
        if selection in _WILSON_PROBE_NAME_PRESETS and not allow_wilson:
            raise ValueError("Wilson probe-name presets are only valid for matching conditions")
        common = set(common_names)
        canonical_different = set(canonical_different_names)
        if selection == "common":
            return _sorted_names(common)
        if selection == "canonical_different":
            return _sorted_names(canonical_different)
        if selection == "wilson":
            return tuple(name for name in reference_wilson_names if name in common)
        return tuple(
            name
            for name in reference_wilson_names
            if name in common and name in canonical_different
        )
    return tuple(selection)


def _gap_report(
    candidate_fixture: str,
    reference_name: str,
    candidate: MatchingResult,
    reference: MatchingResult,
    *,
    probe_parameters: Sequence[Expression] | None = None,
    probe_samples: Sequence[Sequence[NumericValue]] | None = None,
    probe_supertrace_names: ProbeNameSelection | None = None,
    probe_matching_condition_names: ProbeNameSelection | None = None,
    auto_probe_samples: bool = False,
    probe_sample_count: int = 3,
    probe_exclude_symbols: Sequence[Expression] = (),
    probe_parameter_mode: ProbeParameterMode = "symbols",
    probe_absolute_tolerance: float = 1e-9,
    probe_relative_tolerance: float = 1e-9,
    comparison_expression_transform: Callable[[Expression], Expression] | None = None,
    comparison_canonize_indices: bool = True,
    matching_condition_projection_targets: _MatchingConditionProjectionTargets | None = None,
) -> MatchingFixtureGapReport:
    if auto_probe_samples and (probe_parameters is not None or probe_samples is not None):
        raise ValueError("auto_probe_samples cannot be combined with explicit probe_parameters/probe_samples")
    if auto_probe_samples and probe_supertrace_names is None and probe_matching_condition_names is None:
        raise ValueError("auto_probe_samples requires probe_supertrace_names or probe_matching_condition_names")

    candidate_supertraces = _validation_supertrace_names(candidate.supertraces)
    reference_supertraces = _validation_supertrace_names(reference.supertraces)
    common_supertraces = candidate_supertraces & reference_supertraces
    base_compared_supertraces = candidate.compare_to(
        reference,
        names=_sorted_names(common_supertraces),
        expression_transform=comparison_expression_transform,
        canonize_indices=comparison_canonize_indices,
    )
    selected_supertrace_probe_names = _probe_name_selection(
        probe_supertrace_names,
        common_names=common_supertraces,
        canonical_different_names=_canonical_different_names(base_compared_supertraces),
    )
    if (
        not auto_probe_samples
        and probe_supertrace_names is not None
        and (probe_parameters is None or probe_samples is None)
    ):
        raise ValueError("probe_supertrace_names requires probe_parameters/probe_samples or auto_probe_samples=True")
    supertrace_probe_parameters: Sequence[Expression] | None
    supertrace_probe_samples: Sequence[Sequence[NumericValue]] | None
    if auto_probe_samples and selected_supertrace_probe_names:
        supertrace_plan = _probe_plan_for_names(
            candidate,
            reference,
            selected_supertrace_probe_names,
            sample_count=probe_sample_count,
            exclude_symbols=probe_exclude_symbols,
            parameter_mode=probe_parameter_mode,
            expression_transform=comparison_expression_transform,
            canonize_indices=comparison_canonize_indices,
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
    if supertrace_probe_parameters is not None and supertrace_probe_samples is not None:
        compared_supertraces = candidate.compare_to(
            reference,
            names=_sorted_names(common_supertraces),
            probe_parameters=supertrace_probe_parameters,
            probe_samples=supertrace_probe_samples,
            probe_names=selected_supertrace_probe_names,
            absolute_tolerance=probe_absolute_tolerance,
            relative_tolerance=probe_relative_tolerance,
            expression_transform=comparison_expression_transform,
            canonize_indices=comparison_canonize_indices,
        )
    else:
        compared_supertraces = base_compared_supertraces
    candidate_conditions = set(candidate.matching_conditions)
    reference_conditions = set(reference.matching_conditions)
    common_conditions = candidate_conditions & reference_conditions
    reference_wilson_conditions = _reference_wilson_matching_condition_names(reference)
    base_compared_conditions = candidate.compare_to(
        reference,
        names=_sorted_names(common_conditions),
        expression_transform=comparison_expression_transform,
        canonize_indices=comparison_canonize_indices,
    )
    selected_condition_probe_names = _probe_name_selection(
        probe_matching_condition_names,
        common_names=common_conditions,
        canonical_different_names=_canonical_different_names(base_compared_conditions),
        reference_wilson_names=reference_wilson_conditions,
        allow_wilson=True,
    )
    if (
        not auto_probe_samples
        and probe_matching_condition_names is not None
        and (probe_parameters is None or probe_samples is None)
    ):
        raise ValueError(
            "probe_matching_condition_names requires probe_parameters/probe_samples or auto_probe_samples=True"
        )
    condition_probe_parameters: Sequence[Expression] | None
    condition_probe_samples: Sequence[Sequence[NumericValue]] | None
    if auto_probe_samples and selected_condition_probe_names:
        condition_plan = _probe_plan_for_names(
            candidate,
            reference,
            selected_condition_probe_names,
            sample_count=probe_sample_count,
            exclude_symbols=probe_exclude_symbols,
            parameter_mode=probe_parameter_mode,
            expression_transform=comparison_expression_transform,
            canonize_indices=comparison_canonize_indices,
        )
        condition_probe_parameters = condition_plan.parameters
        condition_probe_samples = condition_plan.samples
    elif auto_probe_samples:
        condition_probe_parameters = None
        condition_probe_samples = None
    else:
        condition_probe_parameters = probe_parameters if selected_condition_probe_names is not None else None
        condition_probe_samples = probe_samples if selected_condition_probe_names is not None else None
    if condition_probe_parameters is not None and condition_probe_samples is not None:
        compared_conditions = candidate.compare_to(
            reference,
            names=_sorted_names(common_conditions),
            probe_parameters=condition_probe_parameters,
            probe_samples=condition_probe_samples,
            probe_names=selected_condition_probe_names,
            absolute_tolerance=probe_absolute_tolerance,
            relative_tolerance=probe_relative_tolerance,
            expression_transform=comparison_expression_transform,
            canonize_indices=comparison_canonize_indices,
        )
    else:
        compared_conditions = base_compared_conditions
    candidate_names = set(candidate.expression_names())
    reference_names = set(reference.expression_names())
    return MatchingFixtureGapReport(
        candidate_fixture=candidate_fixture,
        reference_name=reference_name,
        candidate_stage=_metadata_stage(candidate),
        reference_stage=_metadata_stage(reference),
        candidate_supertrace_names=_sorted_names(candidate_supertraces),
        reference_supertrace_names=_sorted_names(reference_supertraces),
        candidate_max_supertrace_order=_max_supertrace_order(candidate_supertraces),
        reference_max_supertrace_order=_max_supertrace_order(reference_supertraces),
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
        reference_wilson_matching_condition_names=reference_wilson_conditions,
        matching_condition_projection_registered_wilson_names=(
            ()
            if matching_condition_projection_targets is None
            else matching_condition_projection_targets.registered_wilson_names
        ),
        matching_condition_projection_reference_non_wilson_names=(
            ()
            if matching_condition_projection_targets is None
            else matching_condition_projection_targets.reference_non_wilson_names
        ),
        matching_condition_projection_reference_wilson_fallback_names=(
            ()
            if matching_condition_projection_targets is None
            else matching_condition_projection_targets.reference_wilson_fallback_names
        ),
        comparison_canonize_indices=comparison_canonize_indices,
        candidate_metadata=_metadata_json_snapshot(candidate.metadata),
        reference_metadata=_metadata_json_snapshot(reference.metadata),
    )


def _metadata_json_snapshot(metadata: Mapping[str, Any]) -> dict[str, MetadataJsonValue]:
    return {key: _metadata_json_value(value) for key, value in sorted(metadata.items())}


def _metadata_json_value(value: Any) -> MetadataJsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Expression):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): _metadata_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_metadata_json_value(item) for item in value]
    return str(value)


def _comparison_expression_transform(
    *,
    simplify_loop_functions_for_comparison: bool = False,
    evaluate_loop_functions_for_comparison: bool,
    comparison_combine_terms: bool,
) -> Callable[[Expression], Expression] | None:
    if not simplify_loop_functions_for_comparison and not evaluate_loop_functions_for_comparison:
        return None

    from .backends import vacuum_integrals

    def transform(expr: Expression) -> Expression:
        transformed = expr
        if simplify_loop_functions_for_comparison:
            transformed = vacuum_integrals.simplify_loop_functions(
                transformed,
                combine_terms=comparison_combine_terms,
            )
        if evaluate_loop_functions_for_comparison:
            transformed = vacuum_integrals.evaluate_loop_functions(
                transformed,
                combine_terms=comparison_combine_terms,
            )
        return transformed

    return transform


def _optional_no_index_external(theory: Theory, name: str) -> Expression | None:
    definition = theory.externals.get(name)
    if definition is None or definition.index_exprs:
        return None
    return theory.external_handle(name)()


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
