from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from html import escape
from typing import TYPE_CHECKING

from symbolica import Expression, Replacement

from .eft import series_eft
from .expr import as_int, coupling_pattern, list_items
from .matching_options import (
    OneLoopNormalization,
    OneLoopNormalizationInput,
    OnShellReplacementInput,
    one_loop_normalization_factor,
    one_loop_normalization_label,
)
from .supertraces import is_named_supertrace
from .symbols import SymbolDataKey, SymbolRole, canonical_string, display_string, latex_string, s, symbol_data
from .theory_metadata import (
    ExternalKind,
    external_basis_from_label,
    external_kind_from_label,
    external_operator_from_label,
)
from .validation import NumericProbeResult, NumericValue, evaluator_probe_equal

if TYPE_CHECKING:
    from .theory import Theory


MatchingConditionTargetInput = Mapping[str, Expression] | Iterable[Expression] | str


_DEFAULT_LOOP_NORMALIZED_SUPERTRACE_SOURCES = {
    "interaction_power_type_vakint_pole_part": "interaction_power_type_normalized_vakint_pole_part",
    "interaction_power_type_vakint_finite_part": "interaction_power_type_normalized_vakint_finite_part",
    "interaction_power_type_internal_integral_pole_part": (
        "interaction_power_type_normalized_internal_integral_pole_part"
    ),
    "interaction_power_type_internal_integral_finite_part": (
        "interaction_power_type_normalized_internal_integral_finite_part"
    ),
}


@dataclass(frozen=True)
class MatchingExpressionComparison:
    """Comparison result for one named matching expression."""

    name: str
    equal: bool
    candidate: Expression | None = None
    reference: Expression | None = None
    canonical_equal: bool = False
    numeric_probe: NumericProbeResult | None = None

    def _repr_latex_(self) -> str:
        status = r"\checkmark" if self.equal else r"\times"
        return rf"$\mathrm{{{escape(self.name)}}}: {status}$"

    def _repr_html_(self) -> str:
        if self.canonical_equal:
            status = "canonically equal"
        elif self.numeric_probe is not None and self.numeric_probe.equal:
            status = "numeric-probe equal"
        elif self.numeric_probe is not None:
            status = f"different, max_abs_difference={self.numeric_probe.max_abs_difference:g}"
        else:
            status = "different"
        return f"<code>{escape(self.name)}: {status}</code>"


@dataclass(frozen=True)
class MatchingResultComparison:
    """Canonical comparison of two structured matching results."""

    candidate: MatchingResult
    reference: MatchingResult
    expressions: tuple[MatchingExpressionComparison, ...]

    @property
    def equal(self) -> bool:
        """Whether every compared expression is present and canonically equal."""

        return all(item.equal for item in self.expressions)

    @property
    def failed_names(self) -> tuple[str, ...]:
        """Names of expressions that are missing or canonically different."""

        return tuple(item.name for item in self.expressions if not item.equal)

    def assert_equal(self) -> None:
        """Raise ``AssertionError`` if any expression differs."""

        if not self.equal:
            raise AssertionError(f"Matching results differ for: {', '.join(self.failed_names)}")

    def _repr_latex_(self) -> str:
        status = r"\checkmark" if self.equal else r"\times"
        return rf"$\mathrm{{MatchingResultComparison}}\left({status},\ {len(self.expressions)}\right)$"

    def _repr_html_(self) -> str:
        status = "equal" if self.equal else f"different: {', '.join(escape(name) for name in self.failed_names)}"
        return f"<code>MatchingResultComparison({status})</code>"


@dataclass(frozen=True)
class MatchingConditionTarget:
    """Structured metadata for a matching-condition projection target."""

    name: str
    expression: Expression
    label: Expression | None = None
    symbol_role: SymbolRole | None = None
    external_kind: ExternalKind | None = None
    indices: tuple[Expression, ...] = ()
    eft_order: int | None = None
    basis: str | None = None
    operator: Expression | None = None

    @property
    def is_coupling(self) -> bool:
        """Whether the target label is a registered model coupling."""

        return self.symbol_role is SymbolRole.COUPLING

    @property
    def is_external(self) -> bool:
        """Whether the target label is an imported external symbol."""

        return self.symbol_role is SymbolRole.EXTERNAL

    @property
    def is_wilson_coefficient(self) -> bool:
        """Whether the target label is tagged as a Wilson coefficient."""

        return self.external_kind is ExternalKind.WILSON_COEFFICIENT

    @property
    def projection_expression(self) -> Expression:
        """Expression whose coefficient defines this matching condition."""

        return self.operator if self.operator is not None else self.expression

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{MatchingConditionTarget}}\left({latex_string(self.expression)}\right)$"

    def _repr_html_(self) -> str:
        details: list[str] = []
        if self.symbol_role is not None:
            details.append(self.symbol_role.value)
        if self.external_kind is not None:
            details.append(self.external_kind.value)
        if self.basis:
            details.append(self.basis)
        suffix = "" if not details else f" {' '.join(escape(detail) for detail in details)}"
        return f"<code>MatchingConditionTarget({escape(display_string(self.expression))}{suffix})</code>"


@dataclass(frozen=True)
class MatchingResult:
    """Structured output of a pychete matching calculation.

    The result stores the major expression stages used by one-loop matching so
    tests and notebooks can inspect individual supertraces, off-shell and
    on-shell EFT Lagrangians, and final matching conditions without relying on
    Matchete's Mathematica data structures.
    """

    theory: Theory
    uv_lagrangian: Expression
    off_shell_eft_lagrangian: Expression
    on_shell_eft_lagrangian: Expression
    matching_conditions: dict[str, Expression] = field(default_factory=dict)
    fluctuation_operators: dict[str, Expression] = field(default_factory=dict)
    supertraces: dict[str, Expression] = field(default_factory=dict)
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    def expression(self, name: str) -> Expression:
        """Return a named expression stage from the matching result."""

        if name == "uv_lagrangian":
            return self.uv_lagrangian
        if name == "off_shell_eft_lagrangian":
            return self.off_shell_eft_lagrangian
        if name == "on_shell_eft_lagrangian":
            return self.on_shell_eft_lagrangian
        for collection in (self.matching_conditions, self.fluctuation_operators, self.supertraces):
            if name in collection:
                return collection[name]
        raise KeyError(f"Matching result has no expression {name!r}")

    def expression_names(self) -> tuple[str, ...]:
        """Return all named expression stages available on the result."""

        return (
            "uv_lagrangian",
            "off_shell_eft_lagrangian",
            "on_shell_eft_lagrangian",
            *self.matching_conditions,
            *self.fluctuation_operators,
            *self.supertraces,
        )

    def validate(self) -> None:
        """Validate every stored expression against the owning theory."""

        for name in self.expression_names():
            self.theory._validate_registered_expression(self.expression(name))

    def project_matching_conditions(
        self,
        targets: MatchingConditionTargetInput,
        *,
        source: str = "on_shell_eft_lagrangian",
        expand_source: bool = True,
        drop_zero: bool = False,
        include_coupling_identities: bool = False,
    ) -> dict[str, Expression]:
        """Project matching conditions from a result expression using Symbolica coefficients.

        ``targets`` may be a mapping from output condition names to target
        monomials, or an iterable of target expressions. Iterable targets use
        their canonical pychete string as the condition key. Coefficients are
        extracted with native ``Expression.coefficient(...)`` so products such
        as ``C*O`` can be projected without a Python expression walker. Wilson
        coefficient targets with stored operator metadata project the
        coefficient of the operator monomial, while ordinary targets project
        the coefficient of the target expression itself.
        ``include_coupling_identities`` adds the tree-level identity value for
        target couplings that are registered in the candidate theory. This is
        intended for loop-correction expressions where unchanged renormalizable
        couplings should still project to themselves, while external Wilson
        coefficients absent from the candidate theory remain zero.
        """

        expr = self.expression(source)
        if expand_source:
            expr = expr.expand()
        conditions: dict[str, Expression] = {}
        for target in matching_condition_targets(_resolve_matching_condition_targets(self.theory, targets)):
            coefficient = expr.coefficient(target.projection_expression).expand()
            if include_coupling_identities:
                identity = _tree_level_coupling_identity(self.theory, target)
                if identity is not None:
                    coefficient = (coefficient + identity).expand()
            if drop_zero and _canonical_expr(coefficient) == "0":
                continue
            conditions[target.name] = coefficient
        return conditions

    def with_projected_matching_conditions(
        self,
        targets: MatchingConditionTargetInput,
        *,
        source: str = "on_shell_eft_lagrangian",
        expand_source: bool = True,
        drop_zero: bool = False,
        merge: bool = True,
        include_coupling_identities: bool = False,
    ) -> MatchingResult:
        """Return a result with matching conditions projected from an expression stage."""

        projected = self.project_matching_conditions(
            targets,
            source=source,
            expand_source=expand_source,
            drop_zero=drop_zero,
            include_coupling_identities=include_coupling_identities,
        )
        matching_conditions = {**self.matching_conditions, **projected} if merge else projected
        return replace(
            self,
            matching_conditions=matching_conditions,
            metadata={
                **self.metadata,
                "matching_conditions_projected": True,
                "matching_condition_projection_source": source,
                "matching_condition_projection_count": len(projected),
                "matching_condition_projection_expand_source": expand_source,
                "matching_condition_projection_coupling_identities": include_coupling_identities,
            },
        )

    def with_loop_normalization(
        self,
        normalization: OneLoopNormalizationInput,
        *,
        stage: str | None = None,
        unnormalized_expression_name: str | None = None,
        unnormalized_expression_alias: str | None = None,
        normalized_supertrace_sources: Mapping[str, str] | None = None,
    ) -> MatchingResult:
        """Return a one-loop result scaled by a convention-normalization factor.

        Normalization is a convention layer on top of the backend result. The
        backend still computes the unnormalized EFT preview; this method records
        that expression, scales the off/on-shell Lagrangians and any existing
        matching-condition coefficients, and stores the factor as a Symbolica
        expression stage for inspection.
        """

        normalization_label = one_loop_normalization_label(normalization)
        if normalization_label == OneLoopNormalization.PREVIEW.value:
            return self
        factor = one_loop_normalization_factor(normalization)
        normalized_off_shell = (factor * self.off_shell_eft_lagrangian).expand()
        normalized_on_shell = (factor * self.on_shell_eft_lagrangian).expand()
        normalized_matching_conditions = {
            name: (factor * expression).expand() for name, expression in self.matching_conditions.items()
        }
        supertraces = dict(self.supertraces)
        normalized_named_supertraces = {
            name: (factor * expression).expand()
            for name, expression in self.supertraces.items()
            if is_named_supertrace(name)
        }
        for name, expression in normalized_named_supertraces.items():
            raw_alias = f"{name}[unnormalized]"
            if raw_alias not in supertraces:
                supertraces[raw_alias] = self.supertraces[name]
            supertraces[name] = expression
        supertraces["interaction_power_type_loop_normalization_factor"] = factor
        supertraces["interaction_power_type_unnormalized_eft_lagrangian"] = self.off_shell_eft_lagrangian
        supertraces["interaction_power_type_normalized_eft_lagrangian"] = normalized_off_shell
        if unnormalized_expression_name is not None:
            alias = unnormalized_expression_alias or f"{unnormalized_expression_name}_unnormalized"
            supertraces[alias] = self.expression(unnormalized_expression_name)
        stage_sources = _DEFAULT_LOOP_NORMALIZED_SUPERTRACE_SOURCES
        if normalized_supertrace_sources is not None:
            stage_sources = {**stage_sources, **normalized_supertrace_sources}
        for source_name, target_name in stage_sources.items():
            if source_name in self.supertraces:
                supertraces[target_name] = (factor * self.supertraces[source_name]).expand()
        previous_stage = self.metadata.get("stage")
        normalized_stage = stage
        if normalized_stage is None:
            if isinstance(previous_stage, str):
                normalized_stage = f"normalized_{previous_stage}"
            else:
                normalized_stage = "normalized_one_loop_result"
        return replace(
            self,
            off_shell_eft_lagrangian=normalized_off_shell,
            on_shell_eft_lagrangian=normalized_on_shell,
            matching_conditions=normalized_matching_conditions,
            supertraces=supertraces,
            metadata={
                **self.metadata,
                "stage": normalized_stage,
                "unnormalized_stage": previous_stage if isinstance(previous_stage, str) else None,
                "loop_normalization": normalization_label,
                "loop_normalization_applied": True,
                "named_supertrace_loop_normalization_count": len(normalized_named_supertraces),
                "complete": False,
            },
        )

    def with_on_shell_reduction(
        self,
        replacements: OnShellReplacementInput,
        *,
        source: str = "on_shell_eft_lagrangian",
        repeat: bool = False,
        expand: bool = True,
    ) -> MatchingResult:
        """Return a result with the on-shell Lagrangian reduced by Symbolica replacements.

        ``replacements`` can be either a mapping of exact expressions to
        replacements or an ordered sequence of Symbolica ``Replacement``
        objects. The actual rewrite is delegated to
        ``Expression.replace_multiple(...)`` so EOM/on-shell rules can use the
        same native matching machinery as the rest of pychete.
        """

        replacement_rules = _on_shell_replacement_rules(replacements)
        if not replacement_rules:
            return self
        input_expression = self.expression(source)
        reduced = input_expression.replace_multiple(replacement_rules, repeat=repeat)
        if expand:
            reduced = reduced.expand()
        return replace(
            self,
            on_shell_eft_lagrangian=reduced,
            supertraces={
                **self.supertraces,
                "on_shell_eft_lagrangian_before_reduction": input_expression,
                "on_shell_eft_lagrangian_after_reduction": reduced,
            },
            metadata={
                **self.metadata,
                "on_shell_reduced": True,
                "on_shell_reduction_source": source,
                "on_shell_reduction_replacement_count": len(replacement_rules),
                "on_shell_reduction_repeat": repeat,
            },
        )

    def with_eft_truncation(
        self,
        eft_order: int,
        *,
        heavy_field_dimension: bool = False,
        expand: bool = True,
    ) -> MatchingResult:
        """Return a result with off/on-shell EFT Lagrangians truncated by EFT order.

        Truncation is delegated to ``series_eft(...)``, which uses Symbolica
        replacement rules, marker coefficients, and coefficient extraction for
        the actual order selection. The original off/on-shell expressions are
        preserved as named stages for diagnostics.
        """

        truncated_off_shell = series_eft(
            self.off_shell_eft_lagrangian,
            self.theory,
            eft_order=eft_order,
            heavy_field_dimension=heavy_field_dimension,
        )
        truncated_on_shell = series_eft(
            self.on_shell_eft_lagrangian,
            self.theory,
            eft_order=eft_order,
            heavy_field_dimension=heavy_field_dimension,
        )
        if expand:
            truncated_off_shell = truncated_off_shell.expand()
            truncated_on_shell = truncated_on_shell.expand()
        truncated_matching_conditions = {
            name: series_eft(
                expression,
                self.theory,
                eft_order=eft_order,
                heavy_field_dimension=heavy_field_dimension,
            ).expand()
            for name, expression in self.matching_conditions.items()
        }
        previous_stage = self.metadata.get("stage")
        return replace(
            self,
            off_shell_eft_lagrangian=truncated_off_shell,
            on_shell_eft_lagrangian=truncated_on_shell,
            matching_conditions=truncated_matching_conditions,
            supertraces={
                **self.supertraces,
                "off_shell_eft_lagrangian_before_eft_truncation": self.off_shell_eft_lagrangian,
                "on_shell_eft_lagrangian_before_eft_truncation": self.on_shell_eft_lagrangian,
                "off_shell_eft_lagrangian_after_eft_truncation": truncated_off_shell,
                "on_shell_eft_lagrangian_after_eft_truncation": truncated_on_shell,
            },
            metadata={
                **self.metadata,
                "eft_result_truncated": True,
                "eft_result_truncation_order": eft_order,
                "eft_result_truncation_heavy_field_dimension": heavy_field_dimension,
                "eft_result_untruncated_stage": previous_stage if isinstance(previous_stage, str) else None,
            },
        )

    def compare_to(
        self,
        reference: MatchingResult,
        *,
        names: Iterable[str] | None = None,
        expression_transform: Callable[[Expression], Expression] | None = None,
        probe_parameters: Sequence[Expression] | None = None,
        probe_samples: Sequence[Sequence[NumericValue]] | None = None,
        probe_names: Iterable[str] | None = None,
        absolute_tolerance: float = 1e-9,
        relative_tolerance: float = 1e-9,
    ) -> MatchingResultComparison:
        """Compare this result to a reference result.

        Canonical Symbolica equality is the primary comparison. If
        ``expression_transform`` is supplied, it is applied to both candidate
        and reference expressions before canonical comparison and before any
        numeric-probe fallback. If ``probe_parameters`` and ``probe_samples``
        are provided, expressions that are not canonically equal are
        additionally tested with Symbolica's evaluator-backed numeric probes.
        ``probe_names`` can restrict the probe fallback to a subset of compared
        names.
        """

        if self.theory.name != reference.theory.name:
            raise ValueError(f"Cannot compare matching results from {self.theory.name!r} and {reference.theory.name!r}")
        if (probe_parameters is None) != (probe_samples is None):
            raise ValueError("probe_parameters and probe_samples must be provided together")
        if probe_names is not None and probe_parameters is None:
            raise ValueError("probe_names requires probe_parameters and probe_samples")
        if names is None:
            comparison_names = tuple(dict.fromkeys((*self.expression_names(), *reference.expression_names())))
        else:
            comparison_names = tuple(names)
        probed_names = set(comparison_names) if probe_names is None else set(probe_names)
        comparisons: list[MatchingExpressionComparison] = []
        for name in comparison_names:
            candidate_expr = _optional_expression(self, name)
            reference_expr = _optional_expression(reference, name)
            compared_candidate = _transform_optional_expression(candidate_expr, expression_transform)
            compared_reference = _transform_optional_expression(reference_expr, expression_transform)
            canonical_equal = (
                compared_candidate is not None
                and compared_reference is not None
                and _canonical_expr(compared_candidate) == _canonical_expr(compared_reference)
            )
            numeric_probe: NumericProbeResult | None = None
            equal = canonical_equal
            if (
                not canonical_equal
                and compared_candidate is not None
                and compared_reference is not None
                and probe_parameters is not None
                and probe_samples is not None
                and name in probed_names
            ):
                numeric_probe = evaluator_probe_equal(
                    compared_candidate,
                    compared_reference,
                    probe_parameters,
                    probe_samples,
                    absolute_tolerance=absolute_tolerance,
                    relative_tolerance=relative_tolerance,
                )
                equal = numeric_probe.equal
            comparisons.append(
                MatchingExpressionComparison(
                    name=name,
                    equal=equal,
                    candidate=compared_candidate,
                    reference=compared_reference,
                    canonical_equal=canonical_equal,
                    numeric_probe=numeric_probe,
                )
            )
        return MatchingResultComparison(candidate=self, reference=reference, expressions=tuple(comparisons))

    def matching_condition_targets(self) -> tuple[MatchingConditionTarget, ...]:
        """Return structured projection-target metadata for stored matching conditions."""

        return matching_condition_targets(
            {
                name: self.theory._parse_registered_expression(name)
                for name in self.matching_conditions
            }
        )

    def _repr_latex_(self) -> str:
        return rf"$\mathrm{{MatchingResult}}\left({self.theory.name},\ {len(self.supertraces)}\ \mathrm{{supertraces}}\right)$"

    def _repr_html_(self) -> str:
        return (
            f"<code>MatchingResult(theory={escape(self.theory.name)} "
            f"supertraces={len(self.supertraces)} "
            f"matching_conditions={len(self.matching_conditions)})</code>"
        )


def _optional_expression(result: MatchingResult, name: str) -> Expression | None:
    try:
        return result.expression(name)
    except KeyError:
        return None


def _transform_optional_expression(
    expr: Expression | None,
    expression_transform: Callable[[Expression], Expression] | None,
) -> Expression | None:
    if expr is None or expression_transform is None:
        return expr
    return expression_transform(expr)


def _on_shell_replacement_rules(replacements: OnShellReplacementInput) -> tuple[Replacement, ...]:
    if replacements is None:
        return ()
    if isinstance(replacements, Mapping):
        return tuple(Replacement(old, new) for old, new in replacements.items())
    return tuple(replacements)


def registered_wilson_matching_condition_targets(
    theory: Theory,
    *,
    basis: str | None = None,
    include_without_operator: bool = False,
) -> dict[str, Expression]:
    """Return target expressions for theory-registered Wilson coefficients.

    The targets are built from the theory-owned external labels and stored
    index/EFT-order metadata. By default only Wilson coefficients with stored
    operator monomials are returned, because those can be projected from an EFT
    Lagrangian through ``MatchingConditionTarget.projection_expression``.
    """

    targets: dict[str, Expression] = {}
    for name in sorted(theory.externals):
        definition = theory.externals[name]
        if definition.kind is not ExternalKind.WILSON_COEFFICIENT:
            continue
        if basis is not None and definition.basis_name != basis:
            continue
        if not include_without_operator and definition.operator_expr is None:
            continue
        expression = s.Coupling(definition.label, s.List(*definition.index_exprs), Expression.num(definition.order))
        targets[canonical_string(expression)] = expression
    return targets


def _resolve_matching_condition_targets(
    theory: Theory,
    targets: MatchingConditionTargetInput,
) -> Mapping[str, Expression] | Iterable[Expression]:
    if not isinstance(targets, str):
        return targets
    if targets in {"registered_wilsons", "registered_wilson_coefficients"}:
        return registered_wilson_matching_condition_targets(theory)
    raise ValueError(
        "Unknown matching-condition target selector "
        f"{targets!r}; supported selector is 'registered_wilsons'"
    )


def _matching_condition_targets(
    targets: Mapping[str, Expression] | Iterable[Expression],
) -> tuple[tuple[str, Expression], ...]:
    if isinstance(targets, Mapping):
        return tuple((str(name), target) for name, target in targets.items())
    if isinstance(targets, str):
        raise ValueError("String target selectors require a MatchingResult or Theory context")
    return tuple((canonical_string(target), target) for target in targets)


def matching_condition_targets(
    targets: Mapping[str, Expression] | Iterable[Expression],
) -> tuple[MatchingConditionTarget, ...]:
    """Return structured matching-condition targets from user expressions.

    Coupling targets are recognized with native Symbolica pattern matching and
    role-tag restrictions. Any Symbolica expression can still be projected, but
    pychete coupling/external targets carry explicit metadata for later SMEFT
    basis and Wilson-coefficient logic.
    """

    return tuple(_matching_condition_target(name, target) for name, target in _matching_condition_targets(targets))


def _matching_condition_target(name: str, expression: Expression) -> MatchingConditionTarget:
    if bool(
        expression.matches(
            coupling_pattern(),
            s.CouplingLabelWildcard.req_tag(SymbolRole.COUPLING.value),
            partial=False,
        )
    ):
        return _coupling_matching_condition_target(name, expression, SymbolRole.COUPLING)
    if bool(
        expression.matches(
            coupling_pattern(),
            s.CouplingLabelWildcard.req_tag(SymbolRole.EXTERNAL.value),
            partial=False,
        )
    ):
        return _coupling_matching_condition_target(name, expression, SymbolRole.EXTERNAL)
    return MatchingConditionTarget(name=name, expression=expression)


def _coupling_matching_condition_target(
    name: str,
    expression: Expression,
    symbol_role: SymbolRole,
) -> MatchingConditionTarget:
    label = expression[0]
    external_kind = external_kind_from_label(label) if symbol_role is SymbolRole.EXTERNAL else None
    return MatchingConditionTarget(
        name=name,
        expression=expression,
        label=label,
        symbol_role=symbol_role,
        external_kind=external_kind,
        indices=list_items(expression[1]),
        eft_order=as_int(expression[2]),
        basis=external_basis_from_label(label) if symbol_role is SymbolRole.EXTERNAL else None,
        operator=external_operator_from_label(label) if symbol_role is SymbolRole.EXTERNAL else None,
    )


def _tree_level_coupling_identity(theory: Theory, target: MatchingConditionTarget) -> Expression | None:
    if target.symbol_role is not SymbolRole.COUPLING or target.label is None:
        return None
    name = symbol_data(target.label, SymbolDataKey.LABEL)
    if not isinstance(name, str) or name not in theory.couplings:
        return None
    return target.expression


def _canonical_expr(expr: Expression) -> str:
    return canonical_string(expr.expand())


__all__ = [
    "MatchingConditionTarget",
    "MatchingExpressionComparison",
    "MatchingResult",
    "MatchingResultComparison",
    "matching_condition_targets",
    "registered_wilson_matching_condition_targets",
]
