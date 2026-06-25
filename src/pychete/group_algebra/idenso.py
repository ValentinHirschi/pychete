from __future__ import annotations

from symbolica import Expression

from pychete.backends import idenso
from pychete.theory import Theory


def simplify_gamma(expr: Expression) -> Expression:
    """Simplify gamma-matrix algebra through the native idenso backend."""

    return idenso.simplify_gamma(expr)


def simplify_color(expr: Expression) -> Expression:
    """Simplify colour algebra through the native idenso backend."""

    return idenso.simplify_color(expr)


def simplify_pychete_color(theory: Theory, expr: Expression) -> Expression:
    """Simplify pychete CG colour algebra through the native idenso backend."""

    return idenso.simplify_pychete_color_algebra(theory, expr)


def simplify_metrics(expr: Expression) -> Expression:
    """Simplify metric algebra through the native idenso backend."""

    return idenso.simplify_metrics(expr)
