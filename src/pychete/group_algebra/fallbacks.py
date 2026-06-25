from __future__ import annotations

from symbolica import Expression

from ..spinor import normalize_ncm


def identity(expr: Expression) -> Expression:
    """Placeholder for future Symbolica replacement-rule fallbacks."""

    return expr


def simplify_projectors(expr: Expression) -> Expression:
    """Apply pychete's Symbolica replacement-rule projector fallback."""

    return normalize_ncm(expr)
