"""Compatibility exports for the optional SMEFT Warsaw basis provider.

New code should import SMEFT helpers from :mod:`pychete.bases.smeft_warsaw`
or discover the provider through the generic operator-basis registry after
importing :mod:`pychete.bases`. This module remains as a compatibility shim so
existing pychete model fixtures keep working without making SMEFT a core
matching-engine module.
"""

from __future__ import annotations

from .bases.smeft_warsaw import (
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
