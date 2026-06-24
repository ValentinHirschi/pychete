from __future__ import annotations

from collections.abc import Callable
from functools import cache

from symbolica import Expression, Replacement
from symbolica.core import AtomType

from .common import import_backend
from ..expr import args, as_int, factors, is_head, product_expr, sum_expr
from ..symbols import s

_MAX_NATIVE_PROJECTOR_POWER = 16
_MAX_NATIVE_DIRAC_WORD_ARITY = 8


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


def simplify_pychete_dirac_algebra(expr: Expression) -> Expression:
    """Simplify compact pychete Dirac words by delegating to native idenso."""

    out = simplify_pychete_dirac_projectors(expr)
    out = out.replace_multiple(_dirac_product_replacements())
    out = out.replace_multiple(_ncm_dirac_word_replacements())
    return simplify_pychete_dirac_projectors(out).expand()


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

    result = simplify_pychete_dirac_algebra(expr)
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
    return simplify_pychete_dirac_algebra(result)


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


@cache
def _dirac_product_replacements() -> tuple[Replacement, ...]:
    return _dirac_word_replacements(s.DiracProduct, "product")


@cache
def _ncm_dirac_word_replacements() -> tuple[Replacement, ...]:
    return _dirac_word_replacements(s.NCM, "ncm")


def _dirac_word_replacements(head: Expression, kind: str) -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_NATIVE_DIRAC_WORD_ARITY + 1):
        wildcards = _dirac_word_wildcards(kind, arity)
        pattern = head(*wildcards)
        replacements.append(
            Replacement(
                pattern,
                _dirac_word_replacement(pattern, wildcards),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _dirac_word_replacement(
    pattern: Expression,
    wildcards: tuple[Expression, ...],
) -> Callable[[dict[Expression, Expression]], Expression]:
    def replace_word(match: dict[Expression, Expression]) -> Expression:
        matched = pattern.replace_wildcards(match)
        factors_to_simplify = _flatten_pychete_dirac_factors(tuple(match[wildcard] for wildcard in wildcards))
        if factors_to_simplify is None:
            return matched
        simplified = _native_dirac_word(factors_to_simplify)
        return matched if simplified is None else simplified

    return replace_word


def _dirac_word_wildcards(kind: str, arity: int) -> tuple[Expression, ...]:
    return tuple(s.head(f"dirac_{kind}_{arity}_{index}_") for index in range(arity))


def _flatten_pychete_dirac_factors(operands: tuple[Expression, ...]) -> tuple[Expression, ...] | None:
    flattened: list[Expression] = []
    for operand in operands:
        if is_head(operand, s.DiracProduct):
            nested = _flatten_pychete_dirac_factors(args(operand))
            if nested is None:
                return None
            flattened.extend(nested)
            continue
        if not _is_pychete_dirac_factor(operand):
            return None
        flattened.append(operand)
    return tuple(flattened)


def _is_pychete_dirac_factor(expr: Expression) -> bool:
    return bool(expr == s.PR) or bool(expr == s.PL) or (is_head(expr, s.Gamma) and len(expr) == 1)


def _native_dirac_word(pychete_factors: tuple[Expression, ...]) -> Expression | None:
    if not pychete_factors:
        return Expression.num(1)
    native_expr = Expression.num(1)
    for index, factor in enumerate(pychete_factors, start=1):
        native_factor = _native_dirac_factor(factor, index, index + 1)
        if native_factor is None:
            return None
        native_expr *= native_factor
    return _decode_simple_native_dirac_result(native_module().simplify_gamma(native_expr))


def _native_dirac_factor(factor: Expression, left: int, right: int) -> Expression | None:
    if bool(factor == s.PR) or bool(factor == s.PL):
        return _native_projector_tensor(factor)(left, right)
    if is_head(factor, s.Gamma) and len(factor) == 1:
        return _native_gamma_tensor()(left, right, factor[0])
    return None


@cache
def _native_hep_tensor(name: str) -> Callable[..., Expression]:
    from symbolica import S
    from symbolica.community.spenso import TensorLibrary

    return TensorLibrary.hep_lib()[S(name)]


def _native_projector_tensor(projector: Expression) -> Callable[..., Expression]:
    if bool(projector == s.PR):
        return _native_hep_tensor("spenso::projp")
    if bool(projector == s.PL):
        return _native_hep_tensor("spenso::projm")
    raise ValueError(f"Unsupported pychete Dirac projector {projector}")


def _native_gamma_tensor() -> Callable[..., Expression]:
    return _native_hep_tensor("spenso::gamma")


def _decode_simple_native_projector_result(expr: Expression) -> Expression:
    decoded = _decode_simple_native_dirac_result(expr)
    return expr if decoded is None else decoded


def _decode_simple_native_dirac_result(expr: Expression) -> Expression | None:
    if bool(expr == Expression.num(0)):
        return Expression.num(0)
    chain = _decode_native_dirac_chain(expr)
    if chain is not None:
        return chain
    if _is_native_spinor_metric(expr):
        return Expression.num(1)
    kind = expr.get_type()
    if kind is AtomType.Num:
        return expr
    if kind is AtomType.Add:
        decoded_terms = tuple(_decode_simple_native_dirac_result(term) for term in args(expr))
        if any(term is None for term in decoded_terms):
            return None
        return sum_expr(term for term in decoded_terms if term is not None)
    if kind is AtomType.Mul:
        decoded_factors = tuple(_decode_simple_native_dirac_result(factor) for factor in factors(expr))
        if any(factor is None for factor in decoded_factors):
            return None
        return product_expr(factor for factor in decoded_factors if factor is not None)
    return None


def _decode_native_dirac_chain(expr: Expression) -> Expression | None:
    if (
        expr.get_type() is not AtomType.Fn
        or expr.get_name() != "spenso::chain"
        or len(expr) < 3
    ):
        return None
    decoded_factors = tuple(_decode_native_dirac_factor(factor) for factor in args(expr)[2:])
    if any(factor is None for factor in decoded_factors):
        return None
    return _pychete_dirac_word(tuple(factor for factor in decoded_factors if factor is not None))


def _decode_native_dirac_factor(expr: Expression) -> Expression | None:
    if is_head(expr, Expression.symbol("spenso::projp")) and len(expr) == 2:
        return s.PR
    if is_head(expr, Expression.symbol("spenso::projm")) and len(expr) == 2:
        return s.PL
    if is_head(expr, Expression.symbol("spenso::gamma")) and len(expr) == 3:
        return s.Gamma(_decode_native_lorentz_index(expr[2]))
    return None


def _decode_native_lorentz_index(expr: Expression) -> Expression:
    if is_head(expr, Expression.symbol("spenso::mink")) and len(expr) == 2:
        return expr[1]
    return expr


def _is_native_spinor_metric(expr: Expression) -> bool:
    return (
        is_head(expr, Expression.symbol("spenso::g"))
        and len(expr) == 2
        and _is_native_bis_index(expr[0])
        and _is_native_bis_index(expr[1])
    )


def _is_native_bis_index(expr: Expression) -> bool:
    return is_head(expr, Expression.symbol("spenso::bis")) and len(expr) == 2


def _pychete_dirac_word(dirac_factors: tuple[Expression, ...]) -> Expression:
    if not dirac_factors:
        return Expression.num(1)
    if len(dirac_factors) == 1:
        return dirac_factors[0]
    return s.DiracProduct(*dirac_factors)


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
    "simplify_pychete_dirac_algebra",
    "simplify_pychete_dirac_projectors",
    "to_dots",
    "wrap_dummies",
    "wrap_indices",
]
