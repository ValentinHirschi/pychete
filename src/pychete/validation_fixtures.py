from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

from symbolica import Expression

from .matching_options import OneLoopIntegralBackend, VakintIntegralStage
from .matching_results import MatchingResult
from .state import PycheteState
from .theory import Theory


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
    candidate_matching_condition_names: tuple[str, ...]
    reference_matching_condition_names: tuple[str, ...]
    common_matching_condition_names: tuple[str, ...]
    candidate_only_matching_condition_names: tuple[str, ...]
    reference_only_matching_condition_names: tuple[str, ...]
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
            "candidate_matching_condition_count": self.candidate_matching_condition_count,
            "reference_matching_condition_count": self.reference_matching_condition_count,
            "common_matching_condition_count": len(self.common_matching_condition_names),
            "missing_reference_matching_condition_count": self.missing_reference_matching_condition_count,
            "candidate_only_matching_condition_count": len(self.candidate_only_matching_condition_names),
            "common_expression_names": list(self.common_expression_names),
            "candidate_only_supertrace_names": list(self.candidate_only_supertrace_names),
            "reference_only_supertrace_names": list(self.reference_only_supertrace_names),
            "canonical_equal_common_supertrace_names": list(self.canonical_equal_common_supertrace_names),
            "canonical_different_common_supertrace_names": list(self.canonical_different_common_supertrace_names),
            "candidate_only_matching_condition_names": list(self.candidate_only_matching_condition_names),
            "reference_only_matching_condition_names": list(self.reference_only_matching_condition_names),
        }

    def _repr_latex_(self) -> str:
        status = r"\checkmark" if self.complete else r"\times"
        return (
            rf"$\mathrm{{MatchingFixtureGapReport}}\left({status},\ "
            rf"{self.candidate_supertrace_count}/{self.reference_supertrace_count}\ \mathrm{{STr}},\ "
            rf"{self.canonical_equal_common_supertrace_count}\ \mathrm{{equal}}\right)$"
        )

    def _repr_html_(self) -> str:
        status = "complete" if self.complete else "incomplete"
        return (
            f"<code>MatchingFixtureGapReport({escape(self.candidate_fixture)} vs "
            f"{escape(self.reference_name)}: {status}, "
            f"supertraces={self.candidate_supertrace_count}/{self.reference_supertrace_count}, "
            f"canonical_equal_common_supertraces={self.canonical_equal_common_supertrace_count}, "
            f"matching_conditions={self.candidate_matching_condition_count}/{self.reference_matching_condition_count})</code>"
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
    ) -> MatchingResult:
        """Build the current incomplete interaction-power preview from fixture expressions."""

        theory = self.theory()
        setup = theory.one_loop_setup(
            self.expression(lagrangian),
            eft_order=eft_order,
            max_trace_order=max_trace_order,
            include_light_only=include_light_only,
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
        named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
        named_supertrace_short_form: bool | None = None,
        named_supertrace_engine: Any | None = None,
    ) -> MatchingFixtureGapReport:
        """Report current one-loop preview coverage against a reference result."""

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
        )
        return _gap_report(self.name, reference_name, candidate, reference)

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


def _metadata_stage(result: MatchingResult) -> str | None:
    stage = result.metadata.get("stage")
    return str(stage) if stage is not None else None


def _gap_report(
    candidate_fixture: str,
    reference_name: str,
    candidate: MatchingResult,
    reference: MatchingResult,
) -> MatchingFixtureGapReport:
    candidate_supertraces = set(candidate.supertraces)
    reference_supertraces = set(reference.supertraces)
    common_supertraces = candidate_supertraces & reference_supertraces
    compared_supertraces = candidate.compare_to(reference, names=_sorted_names(common_supertraces))
    candidate_conditions = set(candidate.matching_conditions)
    reference_conditions = set(reference.matching_conditions)
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
        candidate_matching_condition_names=_sorted_names(candidate_conditions),
        reference_matching_condition_names=_sorted_names(reference_conditions),
        common_matching_condition_names=_sorted_names(candidate_conditions & reference_conditions),
        candidate_only_matching_condition_names=_sorted_names(candidate_conditions - reference_conditions),
        reference_only_matching_condition_names=_sorted_names(reference_conditions - candidate_conditions),
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
