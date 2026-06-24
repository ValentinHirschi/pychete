from __future__ import annotations

from symbolica import Expression

from .common import import_backend


def native_module():
    """Return the native idenso Python module."""

    return import_backend("symbolica.community.idenso")


def cook_function(expr: Expression) -> Expression:
    """Delegate function-symbol flattening to idenso."""

    return native_module().cook_function(expr)


def cook_indices(expr: Expression) -> Expression:
    """Delegate index-symbol flattening to idenso."""

    return native_module().cook_indices(expr)


def dirac_adjoint(expr: Expression) -> Expression:
    """Delegate Dirac-adjoint construction to idenso."""

    return native_module().dirac_adjoint(expr)


def expand_bis(expr: Expression) -> Expression:
    """Delegate bispinor-index expansion to idenso."""

    return native_module().expand_bis(expr)


def expand_color(expr: Expression) -> Expression:
    """Delegate colour-index expansion to idenso."""

    return native_module().expand_color(expr)


def expand_metrics(expr: Expression) -> Expression:
    """Delegate metric-index expansion to idenso."""

    return native_module().expand_metrics(expr)


def expand_mink(expr: Expression) -> Expression:
    """Delegate Minkowski-index expansion to idenso."""

    return native_module().expand_mink(expr)


def expand_mink_bis(expr: Expression) -> Expression:
    """Delegate combined Minkowski and bispinor expansion to idenso."""

    return native_module().expand_mink_bis(expr)


def list_dangling(expr: Expression) -> list[Expression]:
    """Return native idenso dangling-index detection."""

    return native_module().list_dangling(expr)


def simplify_color(expr: Expression) -> Expression:
    """Delegate colour algebra simplification to idenso."""

    return native_module().simplify_color(expr)


def simplify_gamma(expr: Expression) -> Expression:
    """Delegate gamma-matrix algebra simplification to idenso."""

    return native_module().simplify_gamma(expr)


def simplify_metrics(expr: Expression) -> Expression:
    """Delegate metric algebra simplification to idenso."""

    return native_module().simplify_metrics(expr)


def to_dots(expr: Expression) -> Expression:
    """Delegate contracted-vector dot-product conversion to idenso."""

    return native_module().to_dots(expr)


def wrap_dummies(expr: Expression, header: Expression) -> Expression:
    """Wrap only dummy indices through idenso's native routine."""

    return native_module().wrap_dummies(expr, header)


def wrap_indices(expr: Expression, header: Expression) -> Expression:
    """Wrap all abstract indices through idenso's native routine."""

    return native_module().wrap_indices(expr, header)


def simplify_index_algebra(
    expr: Expression,
    *,
    expand: bool = True,
    gamma: bool = True,
    color: bool = True,
    metrics: bool = True,
    dots: bool = False,
) -> Expression:
    """Run a native idenso simplification pipeline for index algebra."""

    result = expr
    if expand:
        result = expand_mink_bis(result)
        result = expand_color(result)
        result = expand_metrics(result)
    if gamma:
        result = simplify_gamma(result)
    if color:
        result = simplify_color(result)
    if metrics:
        result = simplify_metrics(result)
    if dots:
        result = to_dots(result)
    return result


__all__ = [
    "cook_function",
    "cook_indices",
    "dirac_adjoint",
    "expand_bis",
    "expand_color",
    "expand_metrics",
    "expand_mink",
    "expand_mink_bis",
    "list_dangling",
    "native_module",
    "simplify_color",
    "simplify_gamma",
    "simplify_index_algebra",
    "simplify_metrics",
    "to_dots",
    "wrap_dummies",
    "wrap_indices",
]
