from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from html import escape
from typing import TYPE_CHECKING

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .eft import series_eft
from .functional import expand_cd_operators
from .expr import (
    as_int,
    bar_field_pattern,
    bar_field_strength_pattern,
    cd_pattern,
    coupling_pattern,
    factors,
    field_pattern,
    field_strength_pattern,
    index_pattern,
    is_head,
    is_zero,
    list_items,
    matching_subexpressions,
    product_expr,
    pow_parts,
    sum_expr,
    terms,
)
from .indices import canonize_tensor_indices, tensor_index_specs
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

_MAX_PROJECTION_FACTOR_TERMS = 64
_MAX_PROJECTION_FACTOR_BYTES = 16_384
_MAX_PROJECTION_EXPAND_TERMS = 128
_MAX_PROJECTION_EXPAND_BYTES = 32_768


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
        canonize_indices: bool = True,
        normalize_derivative_operators: bool = True,
        normalize_ibp_scalar_bilinears: bool = False,
        drop_zero: bool = False,
        include_coupling_identities: bool = False,
        eft_order: int | tuple[int, ...] | None = None,
        heavy_field_dimension: bool = False,
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
        If ``eft_order`` is supplied, each projected contribution is truncated
        target-locally by applying ``series_eft`` to ``coefficient * target``
        and then extracting the target coefficient again. This preserves the
        total EFT-order semantics of a global truncation while avoiding a full
        expansion of the entire source expression for large matching results.
        ``include_coupling_identities`` adds the tree-level identity value for
        target couplings that are registered in the candidate theory. This is
        intended for loop-correction expressions where unchanged renormalizable
        couplings should still project to themselves, while external Wilson
        coefficients absent from the candidate theory remain zero.
        ``canonize_indices`` first tries exact native coefficient extraction
        on the raw source. If the exact projection exhausts the filtered
        target-local source, pychete keeps that coefficient and avoids tensor
        canonicalization. Otherwise, if the projection target contains
        indices, pychete filters the target-local source subset and applies
        Symbolica's native tensor-index canonicalizer to that smaller source
        together with the target and any aliases. This makes alpha-equivalent
        contracted-index relabelings projectable without a Python-side index
        matcher while avoiding global tensor canonicalization for isolated
        exact matches.
        ``normalize_derivative_operators`` expands explicit ``CD(...)``
        wrappers in the source and target operators into pychete's canonical
        field-derivative-slot representation before projection. The rewrite is
        guarded by native Symbolica pattern matching and is primarily needed
        when SMEFT operator metadata uses explicit derivative wrappers while a
        generated one-loop source stores derivatives directly on fields.
        ``normalize_ibp_scalar_bilinears`` additionally allows target-local
        integration-by-parts projection aliases for bilinears of the form
        ``A * CD([mu, mu], B)``. Exact coefficient extraction is still tried
        first; if it vanishes, pychete extracts the coefficient of the native
        Symbolica-normalized alias ``CD(mu, A) * CD(mu, B)`` with the
        corresponding minus sign. Registered Wilson-coefficient targets with
        stored operator metadata use these target-local aliases automatically,
        because the operator metadata is already a basis-level projection
        instruction. Raw expression targets still require the explicit flag.
        This is intentionally limited to projection onto known targets rather
        than a global IBP simplifier.
        """

        expr = self.expression(source)
        if expand_source:
            expr = expr.expand()
        structured_targets = matching_condition_targets(_resolve_matching_condition_targets(self.theory, targets))
        projection_expressions = tuple(target.projection_expression for target in structured_targets)
        ibp_projection_aliases = tuple(
            _ibp_scalar_bilinear_projection_aliases_for_target(
                target,
                projection_expression,
                normalize_ibp_scalar_bilinears=normalize_ibp_scalar_bilinears,
            )
            for target, projection_expression in zip(structured_targets, projection_expressions, strict=True)
        )
        if normalize_derivative_operators:
            expr = expand_cd_operators(expr)
            projection_expressions = tuple(expand_cd_operators(target) for target in projection_expressions)
            ibp_projection_aliases = tuple(
                tuple((expand_cd_operators(alias), weight) for alias, weight in aliases)
                for aliases in ibp_projection_aliases
            )
        conditions: dict[str, Expression] = {}
        coefficient_extractor = _ProjectionCoefficientExtractor(
            expr,
            wildcard_index_projection=canonize_indices,
        )
        for target, projection_expression, ibp_aliases in zip(
            structured_targets,
            projection_expressions,
            ibp_projection_aliases,
            strict=True,
        ):
            target_extractor = coefficient_extractor
            target_projection_expression = projection_expression
            target_ibp_aliases = ibp_aliases
            coefficient: Expression | None = None
            if canonize_indices:
                raw_extractor = _without_wildcard_index_projection(coefficient_extractor)
                raw_coefficient = raw_extractor.coefficient(projection_expression)
                if not is_zero(raw_coefficient) and _raw_projection_exhausts_filtered_source(
                    raw_extractor,
                    projection_expression,
                    raw_coefficient,
                    ibp_aliases,
                ):
                    coefficient = raw_coefficient
                else:
                    target_extractor, target_projection_expression, target_ibp_aliases = (
                        _target_local_canonized_projection(
                            coefficient_extractor,
                            projection_expression,
                            ibp_aliases,
                        )
                    )
            if coefficient is None:
                coefficient = _matching_projection_coefficient(
                    target_extractor,
                    target_projection_expression,
                    target_ibp_aliases,
                )
            if eft_order is not None:
                coefficient = _truncate_projected_coefficient(
                    coefficient,
                    target_projection_expression,
                    self.theory,
                    eft_order=eft_order,
                    heavy_field_dimension=heavy_field_dimension,
                )
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
        canonize_indices: bool = True,
        normalize_derivative_operators: bool = True,
        normalize_ibp_scalar_bilinears: bool = False,
        drop_zero: bool = False,
        merge: bool = True,
        include_coupling_identities: bool = False,
        eft_order: int | tuple[int, ...] | None = None,
        heavy_field_dimension: bool = False,
    ) -> MatchingResult:
        """Return a result with matching conditions projected from an expression stage."""

        projected = self.project_matching_conditions(
            targets,
            source=source,
            expand_source=expand_source,
            canonize_indices=canonize_indices,
            normalize_derivative_operators=normalize_derivative_operators,
            normalize_ibp_scalar_bilinears=normalize_ibp_scalar_bilinears,
            drop_zero=drop_zero,
            include_coupling_identities=include_coupling_identities,
            eft_order=eft_order,
            heavy_field_dimension=heavy_field_dimension,
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
                "matching_condition_projection_canonize_indices": canonize_indices,
                "matching_condition_projection_normalize_derivative_operators": normalize_derivative_operators,
                "matching_condition_projection_normalize_ibp_scalar_bilinears": (
                    normalize_ibp_scalar_bilinears
                ),
                "matching_condition_projection_coupling_identities": include_coupling_identities,
                "matching_condition_projection_eft_order": _metadata_eft_order(eft_order),
                "matching_condition_projection_heavy_field_dimension": heavy_field_dimension,
            },
        )

    def with_loop_normalization(
        self,
        normalization: OneLoopNormalizationInput,
        *,
        hbar: Expression | None = None,
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
        factor = one_loop_normalization_factor(normalization, hbar=hbar)
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
        canonize_indices: bool = True,
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
        numeric-probe fallback. When ``canonize_indices`` is true, compared
        expressions are first passed through Symbolica's tensor canonizer so
        alpha-equivalent dummy-index contractions line up before equality is
        tested. If ``probe_parameters`` and ``probe_samples`` are provided,
        expressions that are not canonically equal are additionally tested with
        Symbolica's evaluator-backed numeric probes. ``probe_names`` can
        restrict the probe fallback to a subset of compared names.
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
            if canonize_indices and compared_candidate is not None and compared_reference is not None:
                compared_candidate, compared_reference = _canonize_comparison_indices(
                    compared_candidate,
                    compared_reference,
                )
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


@dataclass
class _ProjectionCoefficientExtractor:
    source: Expression
    collected_source: Expression | None = None
    factored_source: Expression | None = None
    filtered_sources: dict[
        tuple[tuple[tuple[str, str, int], ...], ...],
        Expression,
    ] = field(default_factory=dict)
    coupling_filtered_sources: dict[str, Expression] = field(default_factory=dict)
    source_terms: tuple[Expression, ...] | None = None
    source_term_atom_counts: tuple[Counter[tuple[str, str]], ...] | None = None
    wildcard_index_projection: bool = True

    def coefficient(self, target: Expression) -> Expression:
        source = self._filtered_source(target)
        source = _projection_derivative_compatible_source(source, target)
        coefficient = source.coefficient(target).expand()
        if not is_zero(coefficient) or not _is_composite_projection_target(target):
            return coefficient
        collected = self._collected_source(source)
        coefficient = collected.coefficient(target).expand()
        if not is_zero(coefficient):
            return coefficient
        factored_target = target.factor()
        coefficient = collected.coefficient(factored_target).expand()
        if not is_zero(coefficient):
            return coefficient
        if _source_is_small_enough_to_factor(source):
            factored = self._factored_source(source)
            coefficient = factored.coefficient(target).expand()
            if not is_zero(coefficient):
                return coefficient
            coefficient = factored.coefficient(factored_target).expand()
            if not is_zero(coefficient):
                return coefficient
        expanded_coefficient = _expanded_projection_coefficient(
            source,
            target,
            wildcard_index_projection=self.wildcard_index_projection,
        )
        if expanded_coefficient is not None and not is_zero(expanded_coefficient):
            return expanded_coefficient
        numeric_normalized = _numeric_factor_normalized_target(target)
        if numeric_normalized is not None:
            normalized_target, numeric_factor = numeric_normalized
            coefficient = self.coefficient(normalized_target)
            return (coefficient / numeric_factor).expand()
        normalized = _negative_power_normalized_target(target)
        if normalized is None:
            wildcard_coefficient = (
                _wildcard_index_projection_coefficient(source, target)
                if self.wildcard_index_projection
                else None
            )
            return coefficient if wildcard_coefficient is None else wildcard_coefficient
        normalized_target, denominator = normalized
        coefficient = self.coefficient(normalized_target)
        return (coefficient * denominator).expand()

    def _filtered_source(self, target: Expression) -> Expression:
        coupling_label = _simple_coupling_projection_label(target)
        if coupling_label is not None:
            return self._filtered_source_for_coupling_label(coupling_label)
        if not _is_composite_projection_target(target):
            return self.source
        requirements = _projection_atom_requirement_groups(target)
        return self._filtered_source_for_requirements(requirements)

    def _filtered_source_for_coupling_label(self, label: Expression) -> Expression:
        key = canonical_string(label)
        try:
            return self.coupling_filtered_sources[key]
        except KeyError:
            pattern = coupling_pattern(label)
            filtered = sum_expr(term for term in self._source_terms() if bool(term.matches(pattern)))
            self.coupling_filtered_sources[key] = filtered
            return filtered

    def _filtered_source_for_expressions(self, expressions: Sequence[Expression]) -> Expression:
        requirements = _projection_atom_requirement_groups_for_expressions(expressions)
        return self._filtered_source_for_requirements(requirements)

    def _filtered_source_for_requirements(
        self,
        requirements: tuple[tuple[tuple[str, str, int], ...], ...],
    ) -> Expression:
        if not requirements:
            return self.source
        try:
            return self.filtered_sources[requirements]
        except KeyError:
            filtered = sum_expr(
                term
                for term, counts in zip(
                    self._source_terms(),
                    self._source_term_atom_counts(),
                    strict=True,
                )
                if _counts_satisfy_projection_atom_requirements(counts, requirements)
            )
            self.filtered_sources[requirements] = filtered
            return filtered

    def _source_terms(self) -> tuple[Expression, ...]:
        if self.source_terms is None:
            self.source_terms = tuple(terms(self.source))
        return self.source_terms

    def _source_term_atom_counts(self) -> tuple[Counter[tuple[str, str]], ...]:
        if self.source_term_atom_counts is None:
            self.source_term_atom_counts = tuple(_projection_atom_counts(term) for term in self._source_terms())
        return self.source_term_atom_counts

    def _collected_source(self, source: Expression) -> Expression:
        if source is self.source:
            if self.collected_source is None:
                self.collected_source = self.source.collect_factors()
            return self.collected_source
        return source.collect_factors()

    def _factored_source(self, source: Expression) -> Expression:
        if source is self.source:
            if self.factored_source is None:
                self.factored_source = self.source.factor()
            return self.factored_source
        return source.factor()


def _source_is_small_enough_to_factor(source: Expression) -> bool:
    return (
        len(source) <= _MAX_PROJECTION_FACTOR_TERMS
        and source.get_byte_size() <= _MAX_PROJECTION_FACTOR_BYTES
    )


def _source_is_small_enough_to_expand(source: Expression) -> bool:
    return (
        len(source) <= _MAX_PROJECTION_EXPAND_TERMS
        and source.get_byte_size() <= _MAX_PROJECTION_EXPAND_BYTES
    )


def _expanded_projection_coefficient(
    source: Expression,
    target: Expression,
    *,
    wildcard_index_projection: bool,
) -> Expression | None:
    if not _source_is_small_enough_to_expand(source):
        return None
    expanded = source.expand()
    if bool(expanded == source):
        return None
    return _ProjectionCoefficientExtractor(
        expanded,
        wildcard_index_projection=wildcard_index_projection,
    ).coefficient(target)


def _without_wildcard_index_projection(
    extractor: _ProjectionCoefficientExtractor,
) -> _ProjectionCoefficientExtractor:
    return _ProjectionCoefficientExtractor(
        source=extractor.source,
        collected_source=extractor.collected_source,
        factored_source=extractor.factored_source,
        filtered_sources=extractor.filtered_sources,
        coupling_filtered_sources=extractor.coupling_filtered_sources,
        source_terms=extractor._source_terms(),
        source_term_atom_counts=extractor._source_term_atom_counts(),
        wildcard_index_projection=False,
    )


def _simple_coupling_projection_label(target: Expression) -> Expression | None:
    matches = tuple(target.match(coupling_pattern(), partial=False))
    if len(matches) != 1:
        return None
    return matches[0][s.CouplingLabelWildcard]


def _raw_projection_exhausts_filtered_source(
    extractor: _ProjectionCoefficientExtractor,
    projection_expression: Expression,
    coefficient: Expression,
    ibp_aliases: Sequence[tuple[Expression, Expression]],
) -> bool:
    alias_expressions = tuple(alias for alias, _weight in ibp_aliases)
    filtered_source = extractor._filtered_source_for_expressions((projection_expression, *alias_expressions))
    filtered_source = _projection_derivative_compatible_source(filtered_source, projection_expression)
    return is_zero((filtered_source - coefficient * projection_expression).expand())


def _projection_atom_requirement_groups(target: Expression) -> tuple[tuple[tuple[str, str, int], ...], ...]:
    return tuple(
        group
        for group in (_projection_atom_requirement_group(term) for term in terms(target))
        if group
    )


def _projection_atom_requirement_groups_for_expressions(
    expressions: Sequence[Expression],
) -> tuple[tuple[tuple[str, str, int], ...], ...]:
    groups = (
        group
        for expression in expressions
        for group in _projection_atom_requirement_groups(expression)
    )
    return tuple(dict.fromkeys(groups))


def _projection_atom_requirement_group(target: Expression) -> tuple[tuple[str, str, int], ...]:
    counts = _projection_atom_counts(target)
    indexed_field_labels = _indexed_projection_field_labels(target)
    powered_field_labels = _powered_projection_field_labels(target)
    requirements: list[tuple[str, str, int]] = []
    for (kind, label), count in sorted(counts.items()):
        if kind != "field" or label not in powered_field_labels:
            required_count = count
        else:
            cap = 3 if label in indexed_field_labels else 2
            required_count = min(count, cap)
        requirements.append((kind, label, required_count))
    return tuple(requirements)


def _indexed_projection_field_labels(target: Expression) -> set[str]:
    indexed_labels: set[str] = set()
    field_pat = field_pattern()
    for match in target.match(field_pat):
        indices = match[s.FieldIndicesWildcard]
        if is_head(indices, s.List) and len(indices):
            indexed_labels.add(canonical_string(match[s.FieldLabelWildcard]))
    return indexed_labels


def _powered_projection_field_labels(target: Expression) -> set[str]:
    powered_labels: set[str] = set()
    power_pat = s.PowBaseWildcard ** s.PowExponentWildcard
    field_pat = field_pattern()
    for match in target.match(power_pat):
        base = match[s.PowBaseWildcard]
        for field_match in base.match(field_pat):
            powered_labels.add(canonical_string(field_match[s.FieldLabelWildcard]))
    return powered_labels


def _term_satisfies_projection_atom_requirements(
    term: Expression,
    requirements: Sequence[tuple[tuple[str, str, int], ...]],
) -> bool:
    counts = _projection_atom_counts(term)
    return _counts_satisfy_projection_atom_requirements(counts, requirements)


def _counts_satisfy_projection_atom_requirements(
    counts: Counter[tuple[str, str]],
    requirements: Sequence[tuple[tuple[str, str, int], ...]],
) -> bool:
    return any(_counts_satisfy_projection_atom_requirement_group(counts, group) for group in requirements)


def _counts_satisfy_projection_atom_requirement_group(
    counts: Counter[tuple[str, str]],
    group: Sequence[tuple[str, str, int]],
) -> bool:
    allowed_atoms = {(kind, label) for kind, label, _required_count in group}
    return all(counts[(kind, label)] >= required_count for kind, label, required_count in group) and all(
        atom in allowed_atoms for atom in counts
    )


def _projection_atom_counts(expr: Expression) -> Counter[tuple[str, str]]:
    expr = _expand_indexed_field_powers_for_projection(expr)
    counts: Counter[tuple[str, str]] = Counter()
    field_pat = field_pattern()
    for match in expr.match(field_pat):
        counts[("field", canonical_string(match[s.FieldLabelWildcard]))] += 1
    strength_pat = field_strength_pattern()
    for match in expr.match(strength_pat):
        counts[("field_strength", canonical_string(match[s.FieldStrengthLabelWildcard]))] += 1
    return counts


def _projection_derivative_compatible_source(source: Expression, target: Expression) -> Expression:
    field_signatures = _projection_field_derivative_signatures(target)
    strength_signatures = _projection_field_strength_derivative_signatures(target)
    if not field_signatures and not strength_signatures:
        return source
    pruned = source
    if field_signatures:
        pruned = _drop_incompatible_projection_field_derivatives(pruned, field_signatures)
    if strength_signatures:
        pruned = _drop_incompatible_projection_field_strength_derivatives(pruned, strength_signatures)
    return pruned


def _projection_field_derivative_signatures(target: Expression) -> dict[str, set[tuple[str, ...]]]:
    pattern = field_pattern()
    signatures: dict[str, set[tuple[str, ...]]] = {}
    for match in target.match(pattern):
        label = canonical_string(match[s.FieldLabelWildcard])
        signatures.setdefault(label, set()).add(_derivative_signature(match[s.FieldDerivativesWildcard]))
    return signatures


def _projection_field_strength_derivative_signatures(target: Expression) -> dict[str, set[tuple[str, ...]]]:
    pattern = field_strength_pattern()
    signatures: dict[str, set[tuple[str, ...]]] = {}
    for match in target.match(pattern):
        label = canonical_string(match[s.FieldStrengthLabelWildcard])
        signatures.setdefault(label, set()).add(_derivative_signature(match[s.FieldStrengthDerivativesWildcard]))
    return signatures


def _drop_incompatible_projection_field_derivatives(
    source: Expression,
    signatures: Mapping[str, set[tuple[str, ...]]],
) -> Expression:
    field_pat = field_pattern()
    bar_pat = bar_field_pattern()

    def replacement(pattern: Expression, match: dict[Expression, Expression]) -> Expression:
        label = canonical_string(match[s.FieldLabelWildcard])
        allowed = signatures.get(label)
        if allowed is None or _derivative_signature(match[s.FieldDerivativesWildcard]) in allowed:
            return pattern.replace_wildcards(match)
        return Expression.num(0)

    pruned = source.replace(bar_pat, lambda match: replacement(bar_pat, match), rhs_cache_size=0)
    return pruned.replace(field_pat, lambda match: replacement(field_pat, match), rhs_cache_size=0)


def _drop_incompatible_projection_field_strength_derivatives(
    source: Expression,
    signatures: Mapping[str, set[tuple[str, ...]]],
) -> Expression:
    strength_pat = field_strength_pattern()
    bar_pat = bar_field_strength_pattern()

    def replacement(pattern: Expression, match: dict[Expression, Expression]) -> Expression:
        label = canonical_string(match[s.FieldStrengthLabelWildcard])
        allowed = signatures.get(label)
        if allowed is None or _derivative_signature(match[s.FieldStrengthDerivativesWildcard]) in allowed:
            return pattern.replace_wildcards(match)
        return Expression.num(0)

    pruned = source.replace(bar_pat, lambda match: replacement(bar_pat, match), rhs_cache_size=0)
    return pruned.replace(strength_pat, lambda match: replacement(strength_pat, match), rhs_cache_size=0)


def _derivative_signature(derivatives: Expression) -> tuple[str, ...]:
    if not is_head(derivatives, s.List):
        return (canonical_string(derivatives),)
    return tuple(canonical_string(derivative) for derivative in list_items(derivatives))


def _numeric_factor_normalized_target(target: Expression) -> tuple[Expression, Expression] | None:
    numeric_factor = Expression.num(1)
    non_numeric_factors: list[Expression] = []
    for factor in factors(target):
        if factor.get_type() is AtomType.Num:
            numeric_factor *= factor
        else:
            non_numeric_factors.append(factor)
    if bool(numeric_factor == Expression.num(1)):
        return None
    return product_expr(non_numeric_factors), numeric_factor


def _negative_power_normalized_target(target: Expression) -> tuple[Expression, Expression] | None:
    denominator = Expression.num(1)
    for factor in factors(target):
        parts = pow_parts(factor)
        if parts is None:
            continue
        base, exponent = parts
        power = as_int(exponent)
        if power is None or power >= 0:
            continue
        denominator *= base ** (-power)
    if bool(denominator == Expression.num(1)):
        return None
    return (target * denominator).expand(), denominator


def _wildcard_index_projection_coefficient(source: Expression, target: Expression) -> Expression | None:
    pattern = _canonized_index_wildcard_projection_pattern(source, target)
    if pattern is None:
        return None
    marker = Expression.symbol("pychete::matching_projection_target")
    rewritten = source.replace(pattern, marker, rhs_cache_size=0)
    return rewritten.coefficient(marker).expand()


def _canonized_index_wildcard_projection_pattern(source: Expression, target: Expression) -> Expression | None:
    index_specs = _matching_projection_index_specs(source, (target,))
    if not index_specs:
        return None
    try:
        canonized_target = canonize_tensor_indices(target, index_specs)
    except ValueError:
        return _index_wildcard_projection_pattern(
            target,
            tuple(matching_subexpressions(target, index_pattern())),
        )
    canonical_indices = tuple(index.expr for index in canonized_target.canonical_indices)
    return _index_wildcard_projection_pattern(canonized_target.expression, canonical_indices)


def _index_wildcard_projection_pattern(
    target: Expression,
    indices: Sequence[Expression],
) -> Expression | None:
    wildcard_labels: dict[str, Expression] = {}
    seen_indices: set[str] = set()
    pattern = target
    for index in indices:
        label_key = canonical_string(index[0])
        if label_key not in wildcard_labels:
            wildcard_labels[label_key] = s.head(f"matching_projection_index_{len(wildcard_labels)}_")
        index_key = canonical_string(index)
        if index_key in seen_indices:
            continue
        seen_indices.add(index_key)
        pattern = pattern.replace(
            index,
            s.Index(wildcard_labels[label_key], index[1]),
            allow_new_wildcards_on_rhs=True,
        )
    return pattern if wildcard_labels else None


def _matching_projection_coefficient(
    extractor: _ProjectionCoefficientExtractor,
    projection_expression: Expression,
    ibp_aliases: Sequence[tuple[Expression, Expression]],
) -> Expression:
    coefficient = extractor.coefficient(projection_expression)
    if not ibp_aliases or not is_zero(coefficient):
        return coefficient
    alias_contributions = (
        weight * extractor.coefficient(alias)
        for alias, weight in ibp_aliases
        if not is_zero(alias)
    )
    return sum_expr(alias_contributions).expand()


def _target_local_canonized_projection(
    source_extractor: _ProjectionCoefficientExtractor,
    projection_expression: Expression,
    ibp_aliases: Sequence[tuple[Expression, Expression]],
) -> tuple[_ProjectionCoefficientExtractor, Expression, tuple[tuple[Expression, Expression], ...]]:
    alias_expressions = tuple(alias for alias, _weight in ibp_aliases)
    projection_family = (projection_expression, *alias_expressions)
    if not _expressions_have_indices(projection_family):
        return source_extractor, projection_expression, tuple(ibp_aliases)
    filtered_source = source_extractor._filtered_source_for_expressions(projection_family)
    canon_source, canon_projection_expressions, canon_alias_expressions = (
        _canonize_matching_projection_indices_with_aliases(
            filtered_source,
            (projection_expression,),
            alias_expressions,
        )
    )
    canon_projection_expression = canon_projection_expressions[0]
    canon_ibp_aliases = tuple(
        (canon_alias, weight)
        for canon_alias, (_alias, weight) in zip(canon_alias_expressions, ibp_aliases, strict=True)
    )
    filtered_sources = {
        requirements: canon_source
        for expression in (canon_projection_expression, *canon_alias_expressions)
        if (requirements := _projection_atom_requirement_groups(expression))
    }
    return (
        _ProjectionCoefficientExtractor(
            canon_source,
            filtered_sources=filtered_sources,
            wildcard_index_projection=True,
        ),
        canon_projection_expression,
        canon_ibp_aliases,
    )


def _expressions_have_indices(expressions: Sequence[Expression]) -> bool:
    pattern = index_pattern()
    return any(any(expression.match(pattern)) for expression in expressions)


def _ibp_scalar_bilinear_projection_aliases_for_target(
    target: MatchingConditionTarget,
    projection_expression: Expression,
    *,
    normalize_ibp_scalar_bilinears: bool,
) -> tuple[tuple[Expression, Expression], ...]:
    if normalize_ibp_scalar_bilinears or _uses_registered_wilson_operator_aliases(target):
        return _ibp_scalar_bilinear_projection_aliases(projection_expression)
    return ()


def _uses_registered_wilson_operator_aliases(target: MatchingConditionTarget) -> bool:
    return target.is_wilson_coefficient and target.operator is not None


def _is_composite_projection_target(target: Expression) -> bool:
    kind = target.get_type()
    return kind is AtomType.Add or kind is AtomType.Mul or kind is AtomType.Pow


def _ibp_scalar_bilinear_projection_aliases(target: Expression) -> tuple[tuple[Expression, Expression], ...]:
    """Return projection-only aliases for ``A * D^2(B)`` up to total derivatives."""

    aliases: list[tuple[Expression, Expression]] = []
    seen: set[str] = set()
    for cd_expr in matching_subexpressions(target, cd_pattern()):
        parts = _cd_box_parts(cd_expr)
        if parts is None:
            continue
        index, body = parts
        spectator = target.coefficient(cd_expr).expand()
        if is_zero(spectator):
            continue
        alias = s.CD(index, spectator) * s.CD(index, body)
        key = canonical_string(alias)
        if key in seen:
            continue
        seen.add(key)
        aliases.append((alias, Expression.num(-1)))
    return tuple(aliases)


def _cd_box_parts(expr: Expression) -> tuple[Expression, Expression] | None:
    match = _single_cd_match(expr)
    if match is None:
        return None
    indices = _cd_match_indices(match)
    body = match[s.CDBodyWildcard]
    if len(indices) == 2 and bool(indices[0] == indices[1]):
        return indices[0], body
    if len(indices) != 1:
        return None
    nested_match = _single_cd_match(body)
    if nested_match is None:
        return None
    nested_indices = _cd_match_indices(nested_match)
    if len(nested_indices) == 1 and bool(indices[0] == nested_indices[0]):
        return indices[0], nested_match[s.CDBodyWildcard]
    return None


def _single_cd_match(expr: Expression) -> dict[Expression, Expression] | None:
    matches = tuple(expr.match(cd_pattern(), partial=False))
    if len(matches) != 1:
        return None
    return matches[0]


def _cd_match_indices(match: Mapping[Expression, Expression]) -> tuple[Expression, ...]:
    index_expr = match[s.CDIndexWildcard]
    return list_items(index_expr) if is_head(index_expr, s.List) else (index_expr,)


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


def _canonize_matching_projection_indices(
    source: Expression,
    projection_expressions: Sequence[Expression],
) -> tuple[Expression, tuple[Expression, ...]]:
    canon_source, canon_targets, _canon_aliases = _canonize_matching_projection_indices_with_aliases(
        source,
        projection_expressions,
        (),
    )
    return canon_source, canon_targets


def _canonize_matching_projection_indices_with_aliases(
    source: Expression,
    projection_expressions: Sequence[Expression],
    alias_expressions: Sequence[Expression],
) -> tuple[Expression, tuple[Expression, ...], tuple[Expression, ...]]:
    source = _expand_indexed_field_powers_for_projection(source)
    projection_expressions = tuple(_expand_indexed_field_powers_for_projection(expr) for expr in projection_expressions)
    alias_expressions = tuple(_expand_indexed_field_powers_for_projection(expr) for expr in alias_expressions)
    index_specs = _matching_projection_index_specs(source, (*projection_expressions, *alias_expressions))
    if not index_specs:
        return source, tuple(projection_expressions), tuple(alias_expressions)
    canon_source = _canonize_tensor_terms(source, index_specs)
    canon_targets = tuple(_canonize_tensor_terms(target, index_specs) for target in projection_expressions)
    canon_aliases = tuple(_canonize_tensor_terms(alias, index_specs) for alias in alias_expressions)
    return canon_source, canon_targets, canon_aliases


def _expand_indexed_field_powers_for_projection(expr: Expression) -> Expression:
    """Expand indexed field powers into fresh-index factors for projection only."""

    label_cache: dict[tuple[str, int], Expression] = {}
    power_pattern = s.PowBaseWildcard ** s.PowExponentWildcard

    def replacement(match: dict[Expression, Expression]) -> Expression:
        base = match[s.PowBaseWildcard]
        exponent = as_int(match[s.PowExponentWildcard])
        if exponent is None or exponent <= 1:
            return power_pattern.replace_wildcards(match)
        parsed = _indexed_field_power_base(base)
        if parsed is None:
            return power_pattern.replace_wildcards(match)
        field_expr, conjugate = parsed
        indices = list_items(field_expr[2])
        if not indices:
            return power_pattern.replace_wildcards(match)
        factors: list[Expression] = []
        for copy in range(exponent):
            copied_indices = tuple(
                _indexed_power_projection_index(index, copy, label_cache=label_cache)
                for index in indices
            )
            copied_field = s.Field(field_expr[0], field_expr[1], s.List(*copied_indices), field_expr[3])
            factors.append(s.Bar(copied_field) if conjugate else copied_field)
        return product_expr(factors)

    return expr.replace(power_pattern, replacement, rhs_cache_size=0)


def _indexed_field_power_base(expr: Expression) -> tuple[Expression, bool] | None:
    if is_head(expr, s.Field):
        return expr, False
    if is_head(expr, s.Bar) and is_head(expr[0], s.Field):
        return expr[0], True
    return None


def _indexed_power_projection_index(
    index: Expression,
    copy: int,
    *,
    label_cache: dict[tuple[str, int], Expression],
) -> Expression:
    if not is_head(index, s.Index):
        return index
    key = (canonical_string(index), copy)
    if key not in label_cache:
        label_cache[key] = s.head(f"matching_projection_power_index_{len(label_cache)}")
    return s.Index(label_cache[key], index[1])


def _canonize_comparison_indices(lhs: Expression, rhs: Expression) -> tuple[Expression, Expression]:
    index_specs = _matching_projection_index_specs(lhs, (rhs,))
    if not index_specs:
        return lhs, rhs
    return _canonize_tensor_terms(lhs, index_specs), _canonize_tensor_terms(rhs, index_specs)


def _canonize_tensor_terms(
    expr: Expression,
    index_specs: Sequence[tuple[Expression, Expression]],
) -> Expression:
    canonized_terms: list[Expression] = []
    for term in terms(expr):
        try:
            canonized_terms.append(canonize_tensor_indices(term, index_specs).expression)
        except ValueError:
            # Some generated terms currently reuse the same dummy more than
            # twice. Preserve them rather than aborting projection; a later
            # matching slice should split those contractions at their source.
            canonized_terms.append(term)
    return sum_expr(canonized_terms)


def _matching_projection_index_specs(
    source: Expression,
    projection_expressions: Sequence[Expression],
) -> tuple[tuple[Expression, Expression], ...]:
    return tensor_index_specs(*projection_expressions, source)


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


def _truncate_projected_coefficient(
    coefficient: Expression,
    target: Expression,
    theory: Theory,
    *,
    eft_order: int | tuple[int, ...],
    heavy_field_dimension: bool,
) -> Expression:
    projected_piece = series_eft(
        (coefficient * target).expand(),
        theory,
        eft_order=eft_order,
        heavy_field_dimension=heavy_field_dimension,
    )
    return _ProjectionCoefficientExtractor(projected_piece).coefficient(target)


def _metadata_eft_order(eft_order: int | tuple[int, ...] | None) -> int | str | None:
    if eft_order is None:
        return None
    if isinstance(eft_order, tuple):
        return ",".join(str(item) for item in eft_order)
    return eft_order


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
