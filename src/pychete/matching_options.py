from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, Mapping, Sequence, TypeAlias

from symbolica import Expression, Replacement

from .symbols import s


class OneLoopIntegralBackend(StrEnum):
    """Integral backend used for one-loop matching preview results."""

    VAKINT = "vakint"
    VAKINT_MINIMAL_SUBTRACTION = "vakint_minimal_subtraction"
    INTERNAL = "internal"
    INTERNAL_MINIMAL_SUBTRACTION = "internal_minimal_subtraction"

    @classmethod
    def from_user(cls, value: OneLoopIntegralBackend | str) -> OneLoopIntegralBackend:
        """Normalize a user-provided one-loop integral backend selector."""

        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                "one-loop integral backend must be 'vakint', "
                "'vakint_minimal_subtraction', 'internal', or "
                "'internal_minimal_subtraction'"
            ) from exc


class VakintIntegralStage(StrEnum):
    """Native vakint processing stage for lowered one-loop integral expressions."""

    RAW = "raw"
    CANONICAL = "canonical"
    TENSOR_REDUCED = "tensor_reduced"
    EVALUATED = "evaluated"

    @classmethod
    def from_user(cls, value: VakintIntegralStage | str) -> VakintIntegralStage:
        """Normalize a user-provided vakint integral stage selector."""

        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError("vakint integral stage must be 'raw', 'canonical', 'tensor_reduced', or 'evaluated'") from exc


class OneLoopNormalization(StrEnum):
    """Loop-normalization convention for one-loop matching preview results."""

    PREVIEW = "preview"
    MATCHETE_HBAR = "matchete_hbar"
    MATCHETE_EVALUATED_HBAR = "matchete_evaluated_hbar"
    MATCHETE_LOOP_FACTOR = "matchete_loop_factor"

    @classmethod
    def from_user(cls, value: OneLoopNormalization | str) -> OneLoopNormalization:
        """Normalize a user-provided one-loop normalization selector."""

        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                "one-loop normalization must be 'preview', 'matchete_hbar', "
                "'matchete_evaluated_hbar', or 'matchete_loop_factor'"
            ) from exc


OneLoopNormalizationInput: TypeAlias = OneLoopNormalization | str | Expression | None
OnShellReplacementInput: TypeAlias = Mapping[Expression, Expression] | Sequence[Replacement] | None
TensorComponentInput: TypeAlias = Expression | int | float | complex
BosonicCDEExpansionInput: TypeAlias = Mapping[str, Sequence[Sequence[Expression]]] | None
WilsonLineExpansionInput: TypeAlias = Mapping[str, Sequence[Sequence[Expression]]] | None
CovariantDerivativeCommutatorModeInput: TypeAlias = Literal["inversions", "all_distinct"]


@dataclass(frozen=True, slots=True)
class OneLoopMatchOptions:
    """User-facing options for ``Theory.match(..., loop_order=1)``.

    The defaults preserve pychete's current public one-loop preview: an
    interaction-power internal minimal-subtraction result, no native vakint
    tensor reduction, and a native Symbolica ``together()`` combine pass after
    pychete's analytic one-loop integral evaluation. Optional on-shell
    reductions are expressed as native Symbolica replacement rules, either
    supplied directly through ``on_shell_replacements`` or generated from
    ``on_shell_eom_lagrangian`` by matching derivative field targets in the
    evaluated one-loop result. Final off/on-shell result stages are truncated
    to the requested inclusive EFT order by default before matching-condition
    projection. Matchete-style implicit Abelian and non-Abelian covariant
    derivatives can be expanded before fluctuation-operator extraction with
    ``expand_abelian_covariant_derivatives`` and
    ``expand_non_abelian_covariant_derivatives``. Explicit formal
    ``CovariantDerivativeCommutator`` markers can be emitted from out-of-order
    derivative slots with ``emit_covariant_derivative_commutators`` and lowered
    to ``FieldStrength`` insertions with
    ``expand_covariant_derivative_commutators``. The bounded
    ``emit_covariant_derivative_commutator_passes`` count controls how far the
    adjacent-swap emitter canonicalizes derivative lists. Registered pychete CG
    generator and structure-constant tensors can be simplified through
    idenso's native SU(N) color algebra with
    ``simplify_pychete_color_algebra``.
    Heavy scalar backgrounds can be substituted by their tree-level EFT
    solutions before final EFT truncation and projection by enabling
    ``substitute_heavy_scalar_solutions``. This is opt-in while the full
    Matchete-scale projection path is still being optimized for large
    expressions.
    ``heavy_scalar_solution_expand`` controls whether that replacement stage
    immediately expands the reduced on-shell expression; keep it disabled for
    exploratory large-model projection when a less-expanded expression scales
    better.
    ``include_tree_level_matching`` adds pychete's tree-level heavy-scalar
    matched EFT Lagrangian to the one-loop result before final truncation and
    matching-condition projection. The tree part is added after loop
    normalization, so Matchete-style loop prefactors are applied only to loop
    terms. Matching-condition projection then uses staged loop-only and
    tree-level source expressions when those stages are available, which keeps
    target-local aliases such as IBP-equivalent derivative operators from
    hiding a tree contribution behind a direct loop coefficient in the summed
    source.
    ``hbar`` optionally supplies the symbol used by the
    ``MATCHETE_HBAR`` normalization factor. When omitted, pychete uses the
    central ``s.HBar`` symbol; Matchete-derived validation fixtures can pass
    their registered external ``hbar`` symbol to compare against converted
    Matchete conditions without a separate replacement pass.
    Use ``MATCHETE_EVALUATED_HBAR`` instead when the selected backend has
    already evaluated one-loop integrals and therefore already contains the
    explicit ``i/(16*pi^2)`` factor. This maps evaluated internal-backend
    terms into Matchete's external ``hbar`` loop-counting convention.
    ``bosonic_cde_expansion_indices_by_trace`` enables the current opt-in CDE
    interaction-supertrace path for explicitly selected trace names. The value
    maps each trace name to one Lorentz-index sequence per propagator slot in
    that trace. For generated plans, set ``bosonic_cde_max_total_order`` and
    optionally ``bosonic_cde_trace_names``/``bosonic_cde_max_slot_order``; the
    one-loop setup will enumerate all trace-slot derivative-order allocations
    up to that bound. When explicit or generated CDE expansion is supplied to
    the public matcher, the selected trace families are replaced by their
    CDE-expanded aggregate while unselected interaction-power traces remain in
    the one-loop source. The lower-level ``interaction_bosonic_cde_*`` setup
    methods still expose pure selected-CDE diagnostics.
    ``bosonic_cde_emit_covariant_derivative_commutators`` and
    ``bosonic_cde_expand_covariant_derivative_commutators`` apply the existing
    Symbolica replacement-rule commutator emitter/lowerer to CDE numerators
    after optional open-derivative action. This is separate from the pre-setup
    Lagrangian commutator flags above.
    ``bosonic_cde_filter_terms_by_matching_targets`` is an opt-in performance
    guard for target-local matching-condition runs. When CDE expansion and
    matching-condition targets are both supplied, generated CDE terms whose
    numerator does not contain the field/field-strength atoms required by any
    requested target are skipped before tensor reduction and integral
    evaluation. This filter is conservative and uses Symbolica pattern matches;
    final coefficient extraction still runs through the ordinary projection
    path.
    ``wilson_line_expansion_indices_by_trace`` enables the forward
    current-Matchete-style explicit Wilson-line trace route for selected
    interaction trace names. The value maps each trace name to one
    Lorentz-index sequence per propagator slot. This path is separate from the
    legacy CDE options: it builds ordered ``WilsonLineTracePath`` terms,
    lets open derivatives act on the closing ``WilsonTerm`` when requested,
    then lowers supported Wilson terms with ``expand_wilson_terms``. Public
    matching uses the hybrid selected-trace route: selected trace families are
    replaced by their Wilson-line aggregate while unselected interaction-power
    traces remain in the one-loop source. It is intentionally opt-in until the
    higher-order Wilson-line expansion coverage is validated against committed
    fixtures.
    ``wilson_line_emit_covariant_derivative_commutators`` and
    ``wilson_line_expand_covariant_derivative_commutators`` apply the existing
    Symbolica replacement-rule commutator emitter/lowerer to generated
    Wilson-line numerators after open derivatives and WilsonTerm lowering.
    Use these for current-Matchete Wilson-line parity probes that need
    derivative-slot commutators lowered to registered ``FieldStrength`` atoms.
    ``wilson_line_covariant_derivative_commutator_mode`` selects the local
    emitter policy. The default ``"inversions"`` keeps the stable
    canonical-order rewrite. ``"all_distinct"`` emits the Matchete
    ``CommuteCDs`` adjacent-pair identity for the first distinct neighboring
    derivative pair and is limited to one pass.
    For generated Wilson-line plans, set ``wilson_line_max_total_order`` and
    optionally ``wilson_line_trace_names``/``wilson_line_max_slot_order``.
    This is the preferred convenience route for new Matchete parity probes
    because it avoids deepening the legacy CDE-named planning surface.
    ``wilson_line_filter_terms_by_matching_targets`` applies the same
    conservative target-local filtering policy to generated Wilson-line terms
    as the CDE filter does for legacy CDE terms. It uses Symbolica pattern
    matches to drop terms whose numerator lacks the field/field-strength atom
    content required by the requested projection targets before tensor
    reduction/evaluation; final coefficient extraction still uses the normal
    projection path.
    ``wilson_line_expose_scalar_derivative_commutator_bilinears`` enables a
    post-tensor internal Wilson-line normal-form pass that decomposes
    two-derivative scalar bilinears into their antisymmetric commutator
    component plus residual derivative terms. It is off by default while the
    Matchete-parity normal-form layer is still being validated.
    """

    max_trace_order: int = 2
    include_light_only: bool = False
    heavy_field_dimension: bool = False
    include_light: bool = True
    integral_backend: OneLoopIntegralBackend | str = OneLoopIntegralBackend.INTERNAL_MINIMAL_SUBTRACTION
    vakint_stage: VakintIntegralStage | str = VakintIntegralStage.RAW
    vakint_short_form: bool | None = None
    vakint_engine: Any | None = None
    named_supertrace_stage: VakintIntegralStage | str = VakintIntegralStage.RAW
    named_supertrace_short_form: bool | None = None
    named_supertrace_engine: Any | None = None
    normalization: OneLoopNormalizationInput = OneLoopNormalization.PREVIEW
    hbar: Expression | None = None
    tensor_reduce: bool = False
    tensor_reduce_engine: Any | None = None
    combine_terms: bool = True
    max_pole_order: int = 1
    epsilon: Expression | None = None
    mu_r_squared: Expression | None = None
    on_shell_replacements: OnShellReplacementInput = None
    on_shell_eom_lagrangian: Expression | None = None
    on_shell_eom_fields: Sequence[Any] | None = None
    on_shell_eom_min_derivative_order: int = 2
    on_shell_eom_strict: bool = False
    on_shell_replacement_repeat: bool = False
    substitute_heavy_scalar_solutions: bool = False
    heavy_scalar_solution_lagrangian: Expression | None = None
    heavy_scalar_solution_expand: bool = False
    include_tree_level_matching: bool = False
    truncate_eft_result: bool = True
    expand_abelian_covariant_derivatives: bool = False
    expand_non_abelian_covariant_derivatives: bool = False
    emit_covariant_derivative_commutators: bool = False
    emit_covariant_derivative_commutator_passes: int = 1
    expand_covariant_derivative_commutators: bool = False
    bosonic_cde_expansion_indices_by_trace: BosonicCDEExpansionInput = None
    bosonic_cde_trace_names: Sequence[str] | None = None
    bosonic_cde_max_total_order: int | None = None
    bosonic_cde_max_slot_order: int | None = None
    bosonic_cde_index_prefix: str = "cde"
    bosonic_cde_act_open_derivatives: bool = False
    bosonic_cde_emit_covariant_derivative_commutators: bool = False
    bosonic_cde_emit_covariant_derivative_commutator_passes: int = 1
    bosonic_cde_expand_covariant_derivative_commutators: bool = False
    bosonic_cde_filter_terms_by_matching_targets: bool = False
    wilson_line_expansion_indices_by_trace: WilsonLineExpansionInput = None
    wilson_line_trace_names: Sequence[str] | None = None
    wilson_line_max_total_order: int | None = None
    wilson_line_max_slot_order: int | None = None
    wilson_line_index_prefix: str = "wilson_line"
    wilson_line_act_open_derivatives: bool = False
    wilson_line_emit_covariant_derivative_commutators: bool = False
    wilson_line_emit_covariant_derivative_commutator_passes: int = 1
    wilson_line_covariant_derivative_commutator_mode: CovariantDerivativeCommutatorModeInput = "inversions"
    wilson_line_expand_covariant_derivative_commutators: bool = False
    wilson_line_max_derivative_order: int = 4
    wilson_line_filter_terms_by_matching_targets: bool = False
    wilson_line_expose_scalar_derivative_commutator_bilinears: bool = False
    simplify_pychete_color_algebra: bool = False
    loop_momentum_squared: Expression | None = None
    require_registered_mass: bool = True
    evaluate_tensor_networks: bool = False
    tensor_network_library: Any | None = None
    tensor_network_cg_components_by_name: Mapping[str, Sequence[TensorComponentInput]] | None = None
    tensor_network_builtin_cg_components: bool = False
    tensor_network_native_hep_cg_builtins: bool = False
    tensor_network_symbolic_cg_components: bool = False
    tensor_network_function_library: Any | None = None
    tensor_network_n_steps: int | None = None
    tensor_network_mode: Any | None = None

    def _repr_latex_(self) -> str:
        backend = OneLoopIntegralBackend.from_user(self.integral_backend).value.replace("_", r"\_")
        return rf"$\mathrm{{OneLoopMatchOptions}}\left({backend},\ N={self.max_trace_order}\right)$"

    def _repr_html_(self) -> str:
        backend = OneLoopIntegralBackend.from_user(self.integral_backend).value
        return f"<code>OneLoopMatchOptions(backend={backend} max_trace_order={self.max_trace_order})</code>"


def one_loop_normalization_factor(
    normalization: OneLoopNormalizationInput = OneLoopNormalization.PREVIEW,
    *,
    hbar: Expression | None = None,
) -> Expression:
    """Return the Symbolica factor for a one-loop normalization convention."""

    if normalization is None:
        selected = OneLoopNormalization.PREVIEW
    elif isinstance(normalization, Expression):
        return normalization
    else:
        selected = OneLoopNormalization.from_user(normalization)
    if selected is OneLoopNormalization.PREVIEW:
        return Expression.num(1)
    if selected is OneLoopNormalization.MATCHETE_HBAR:
        return Expression.I * (s.HBar if hbar is None else hbar)
    if selected is OneLoopNormalization.MATCHETE_EVALUATED_HBAR:
        return -16 * Expression.PI**2 * Expression.I * (s.HBar if hbar is None else hbar)
    return Expression.I / (16 * Expression.PI**2)


def one_loop_normalization_label(normalization: OneLoopNormalizationInput) -> str:
    """Return the metadata label for a one-loop normalization choice."""

    if isinstance(normalization, Expression):
        return "custom"
    selected = OneLoopNormalization.PREVIEW if normalization is None else OneLoopNormalization.from_user(normalization)
    return selected.value


__all__ = [
    "OneLoopIntegralBackend",
    "OneLoopNormalization",
    "OneLoopNormalizationInput",
    "OnShellReplacementInput",
    "BosonicCDEExpansionInput",
    "WilsonLineExpansionInput",
    "VakintIntegralStage",
    "one_loop_normalization_factor",
    "one_loop_normalization_label",
]
