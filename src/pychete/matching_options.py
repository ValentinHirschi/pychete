from __future__ import annotations

from enum import StrEnum
from typing import TypeAlias

from symbolica import Expression

from .symbols import s


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
    "OneLoopNormalization",
    "OneLoopNormalizationInput",
    "VakintIntegralStage",
    "one_loop_normalization_factor",
    "one_loop_normalization_label",
]
