"""Optional built-in operator-basis providers.

The matching engine consumes generic :class:`pychete.OperatorBasis` metadata.
Basis-specific modules live here as convenience providers and validation
fixtures; core matching code must stay basis-agnostic.
"""

from __future__ import annotations

from .smeft_warsaw import (
    SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES,
    define_smeft_wilson_coefficient,
    smeft_warsaw_basis,
    smeft_warsaw_operator,
    smeft_warsaw_operator_names,
)

__all__ = [
    "SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES",
    "define_smeft_wilson_coefficient",
    "smeft_warsaw_basis",
    "smeft_warsaw_operator",
    "smeft_warsaw_operator_names",
]
