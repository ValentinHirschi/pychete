from __future__ import annotations

from symbolica import Expression


def _idenso():
    import symbolica.community.idenso as idenso

    return idenso


def simplify_gamma(expr: Expression) -> Expression:
    return _idenso().simplify_gamma(expr)


def simplify_color(expr: Expression) -> Expression:
    return _idenso().simplify_color(expr)


def simplify_metrics(expr: Expression) -> Expression:
    return _idenso().simplify_metrics(expr)
