from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Sequence, TypeAlias

from symbolica import Expression

from .symbols import s


class OneLoopIntegralBackend(StrEnum):
    """Integral backend used for one-loop matching preview results."""

    VAKINT = "vakint"
    INTERNAL = "internal"
    INTERNAL_MINIMAL_SUBTRACTION = "internal_minimal_subtraction"

    @classmethod
    def from_user(cls, value: OneLoopIntegralBackend | str) -> OneLoopIntegralBackend:
        """Normalize a user-provided one-loop integral backend selector."""

        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                "one-loop integral backend must be 'vakint', 'internal', "
                "or 'internal_minimal_subtraction'"
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
    MATCHETE_LOOP_FACTOR = "matchete_loop_factor"

    @classmethod
    def from_user(cls, value: OneLoopNormalization | str) -> OneLoopNormalization:
        """Normalize a user-provided one-loop normalization selector."""

        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                "one-loop normalization must be 'preview', 'matchete_hbar', or 'matchete_loop_factor'"
            ) from exc


OneLoopNormalizationInput: TypeAlias = OneLoopNormalization | str | Expression | None
TensorComponentInput: TypeAlias = Expression | int | float | complex


@dataclass(frozen=True, slots=True)
class OneLoopMatchOptions:
    """User-facing options for ``Theory.match(..., loop_order=1)``.

    The defaults preserve pychete's current public one-loop preview: an
    interaction-power internal minimal-subtraction result, no native vakint
    tensor reduction, and a native Symbolica ``together()`` combine pass after
    pychete's analytic one-loop integral evaluation.
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
    tensor_reduce: bool = False
    tensor_reduce_engine: Any | None = None
    combine_terms: bool = True
    max_pole_order: int = 1
    epsilon: Expression | None = None
    mu_r_squared: Expression | None = None
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
        return Expression.I * s.HBar
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
    "VakintIntegralStage",
    "one_loop_normalization_factor",
    "one_loop_normalization_label",
]
