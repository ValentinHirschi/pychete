from __future__ import annotations

from collections.abc import Iterable
from typing import TypeAlias

from symbolica import Condition, Expression, PatternRestriction
from symbolica.core import AtomType

from .symbols import canonical_string, s

Expr: TypeAlias = Expression


def list_expr(*items: Expr) -> Expr:
    return s.List(*items)


def list_items(expr: Expr) -> tuple[Expr, ...]:
    if not any(is_head(expr, head) for head in (s.List, s.InternalIndices, s.DerivativeIndices, s.LorentzIndices)):
        raise ValueError(f"Expected pychete index collection expression, got {canonical_string(expr)}")
    return tuple(expr[i] for i in range(len(expr)))


def internal_indices_expr(*items: Expr) -> Expr:
    return s.InternalIndices(*items)


def derivative_indices_expr(*items: Expr) -> Expr:
    return s.DerivativeIndices(*items)


def lorentz_indices_expr(*items: Expr) -> Expr:
    return s.LorentzIndices(*items)


def is_head(expr: Expr, head: Expr) -> bool:
    return expr.get_type() is AtomType.Fn and expr.get_name() == head.get_name()


def as_int(expr: Expr) -> int | None:
    if expr.get_type() is not AtomType.Num:
        return None
    try:
        return int(expr)
    except (TypeError, ValueError):
        return None


def args(expr: Expr) -> tuple[Expr, ...]:
    kind = expr.get_type()
    if kind is AtomType.Num or kind is AtomType.Var:
        return ()
    return tuple(expr[i] for i in range(len(expr)))


def terms(expr: Expr) -> tuple[Expr, ...]:
    return args(expr) if expr.get_type() is AtomType.Add else (expr,)


def factors(expr: Expr) -> tuple[Expr, ...]:
    return args(expr) if expr.get_type() is AtomType.Mul else (expr,)


def pow_parts(expr: Expr) -> tuple[Expr, Expr] | None:
    if expr.get_type() is AtomType.Pow:
        return expr[0], expr[1]
    return None


def sum_expr(items: Iterable[Expr]) -> Expr:
    out = Expression.num(0)
    for item in items:
        out = out + item
    return out


def product_expr(items: Iterable[Expr]) -> Expr:
    out = Expression.num(1)
    for item in items:
        out = out * item
    return out


def field_pattern(label: Expr | None = None) -> Expr:
    return s.Field(
        s.FieldLabelWildcard if label is None else label,
        s.FieldTypeWildcard,
        s.FieldIndicesWildcard,
        s.FieldDerivativesWildcard,
    )


def bar_field_pattern(label: Expr | None = None) -> Expr:
    return s.Bar(field_pattern(label))


def index_pattern() -> Expr:
    return s.Index(s.IndexLabelWildcard, s.IndexRepresentationWildcard)


def power_pattern() -> Expr:
    return s.PowBaseWildcard ** s.PowExponentWildcard


def cd_pattern() -> Expr:
    return s.CD(s.CDIndexWildcard, s.CDBodyWildcard)


def coupling_pattern(label: Expr | None = None) -> Expr:
    return s.Coupling(
        s.CouplingLabelWildcard if label is None else label,
        s.CouplingIndicesWildcard,
        s.CouplingOrderWildcard,
    )


def field_strength_pattern(label: Expr | None = None) -> Expr:
    return s.FieldStrength(
        s.FieldStrengthLabelWildcard if label is None else label,
        s.FieldStrengthLorentzWildcard,
        s.FieldStrengthIndicesWildcard,
        s.FieldStrengthDerivativesWildcard,
    )


MatchCondition: TypeAlias = PatternRestriction | Condition | None


def pattern_matches(expr: Expr, pattern: Expr, cond: MatchCondition = None) -> tuple[Expr, ...]:
    return tuple(pattern.replace_wildcards(match) for match in expr.match(pattern, cond))


def matching_subexpressions(expr: Expr, pattern: Expr, cond: MatchCondition = None) -> tuple[Expr, ...]:
    return tuple(dict.fromkeys(pattern_matches(expr, pattern, cond)))


def is_zero(expr: Expr) -> bool:
    return bool(expr.expand() == Expression.num(0))


def field_label(expr: Expr) -> Expr:
    if not is_head(expr, s.Field):
        raise ValueError(f"Expected Field expression, got {canonical_string(expr)}")
    return expr[0]


def field_type(expr: Expr) -> Expr:
    if not is_head(expr, s.Field):
        raise ValueError(f"Expected Field expression, got {canonical_string(expr)}")
    return expr[1]


def field_derivatives(expr: Expr) -> tuple[Expr, ...]:
    if not is_head(expr, s.Field):
        raise ValueError(f"Expected Field expression, got {canonical_string(expr)}")
    return list_items(expr[3])


def field_with_derivatives(expr: Expr, derivatives: Iterable[Expr]) -> Expr:
    return s.Field(field_label(expr), field_type(expr), expr[2], derivative_indices_expr(*derivatives))


def is_bar_field(expr: Expr) -> bool:
    return is_head(expr, s.Bar) and is_head(expr[0], s.Field)


def bar_field_inner(expr: Expr) -> Expr:
    if not is_bar_field(expr):
        raise ValueError(f"Expected Bar[Field] expression, got {canonical_string(expr)}")
    return expr[0]
