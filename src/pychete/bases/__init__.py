"""Optional built-in operator-basis providers.

The matching engine consumes generic :class:`pychete.OperatorBasis` metadata.
Basis-specific modules live here as convenience providers and validation
fixtures; core matching code must stay basis-agnostic. Importing this package
registers bundled providers in the generic operator-basis registry.
"""

from __future__ import annotations

from ..operator_bases import (
    define_wilson_coefficient_from_registered_basis,
    operator_basis_names,
    registered_operator_basis,
    register_operator_basis,
)
from .smeft_warsaw import (
    SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES,
    define_smeft_wilson_coefficient,
    smeft_warsaw_basis,
    smeft_warsaw_operator,
    smeft_warsaw_operator_names,
)

smeft_warsaw_basis()

__all__ = [
    "SUPPORTED_SMEFT_WARSAW_OPERATOR_NAMES",
    "define_wilson_coefficient_from_registered_basis",
    "define_smeft_wilson_coefficient",
    "operator_basis_names",
    "registered_operator_basis",
    "register_operator_basis",
    "smeft_warsaw_basis",
    "smeft_warsaw_operator",
    "smeft_warsaw_operator_names",
]
