from __future__ import annotations

from collections.abc import Callable

from symbolica import Expression
from symbolica.core import AtomType

from .common import import_backend
from ..expr import as_int, is_head
from ..symbols import s

_MAX_NATIVE_PROJECTOR_POWER = 16


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


def simplify_pychete_dirac_projectors(expr: Expression) -> Expression:
    """Simplify pychete projector-only Dirac words through native idenso.

    pychete's public expressions use compact ``s.PR`` and ``s.PL`` symbols,
    while idenso's gamma simplifier expects explicit spenso projector tensors
    with bispinor endpoints. This adapter lowers projector-only words to native
    spenso tensors, delegates simplification to ``idenso.simplify_gamma``, and
    decodes the simple scalar/projector result back to pychete symbols.
    """

    replacements: tuple[tuple[Expression, Expression], ...] = (
        (s.PR * s.PR, _native_projector_word((s.PR, s.PR))),
        (s.PL * s.PL, _native_projector_word((s.PL, s.PL))),
        (s.PR * s.PL, _native_projector_word((s.PR, s.PL))),
        (s.PL * s.PR, _native_projector_word((s.PL, s.PR))),
    )
    out = expr
    for projector, power_replacement in (
        (s.PR, _projector_power_replacement(s.PR)),
        (s.PL, _projector_power_replacement(s.PL)),
    ):
        out = out.replace(projector ** s.PowExponentWildcard, power_replacement)
    for pattern, replacement in replacements:
        out = out.replace(pattern, replacement, repeat=True)
    return out.expand()


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

    result = simplify_pychete_dirac_projectors(expr)
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
    return simplify_pychete_dirac_projectors(result)


def _projector_power_replacement(
    projector: Expression,
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_power(match: dict[Expression, Expression]) -> Expression:
        exponent = as_int(match[s.PowExponentWildcard])
        if exponent is None or exponent < 1 or exponent > _MAX_NATIVE_PROJECTOR_POWER:
            return projector ** match[s.PowExponentWildcard]
        return _native_projector_word((projector,) * exponent)

    return replace_power


def _native_projector_word(projectors: tuple[Expression, ...]) -> Expression:
    if not projectors:
        return Expression.num(1)
    native_expr = Expression.num(1)
    for index, projector in enumerate(projectors, start=1):
        native_expr *= _native_projector_tensor(projector)(index, index + 1)
    return _decode_simple_native_projector_result(native_module().simplify_gamma(native_expr))


def _native_projector_tensor(projector: Expression) -> Callable[..., Expression]:
    from symbolica import S
    from symbolica.community.spenso import TensorLibrary

    if bool(projector == s.PR):
        return TensorLibrary.hep_lib()[S("spenso::projp")]
    if bool(projector == s.PL):
        return TensorLibrary.hep_lib()[S("spenso::projm")]
    raise ValueError(f"Unsupported pychete Dirac projector {projector}")


def _decode_simple_native_projector_result(expr: Expression) -> Expression:
    if bool(expr == Expression.num(0)):
        return Expression.num(0)
    if _is_native_single_projector_chain(expr, "spenso::projp"):
        return s.PR
    if _is_native_single_projector_chain(expr, "spenso::projm"):
        return s.PL
    return expr


def _is_native_single_projector_chain(expr: Expression, projector_name: str) -> bool:
    if (
        expr.get_type() is not AtomType.Fn
        or expr.get_name() != "spenso::chain"
        or len(expr) != 3
    ):
        return False
    factor = expr[2]
    return is_head(factor, Expression.symbol(projector_name)) and len(factor) == 2


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
    "simplify_pychete_dirac_projectors",
    "to_dots",
    "wrap_dummies",
    "wrap_indices",
]
