from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import TypeAlias

from symbolica import Expression
from symbolica.core import AtomType

from .symbols import canonical_string, s

Expr: TypeAlias = Expression


def list_expr(*items: Expr) -> Expr:
    return s.List(*items)


def list_items(expr: Expr) -> tuple[Expr, ...]:
    if not is_head(expr, s.List):
        raise ValueError(f"Expected pychete List expression, got {canonical_string(expr)}")
    return tuple(expr[i] for i in range(len(expr)))


def expr_key(expr: Expr) -> str:
    return canonical_string(expr)


def atom_type(expr: Expr) -> AtomType:
    return expr.to_atom_tree().atom_type


def head_name(expr: Expr) -> str | None:
    return expr.to_atom_tree().head


def is_head(expr: Expr, head: Expr) -> bool:
    tree = expr.to_atom_tree()
    return tree.atom_type is AtomType.Fn and tree.head == head_name(head)


def is_var(expr: Expr) -> bool:
    return atom_type(expr) is AtomType.Var


def is_num(expr: Expr) -> bool:
    return atom_type(expr) is AtomType.Num


def as_int(expr: Expr) -> int | None:
    tree = expr.to_atom_tree()
    if tree.atom_type is not AtomType.Num or tree.head is None:
        return None
    try:
        return int(tree.head)
    except ValueError:
        return None


def args(expr: Expr) -> tuple[Expr, ...]:
    return tuple(expr[i] for i in range(len(expr.to_atom_tree().tail)))


def terms(expr: Expr) -> tuple[Expr, ...]:
    return args(expr) if atom_type(expr) is AtomType.Add else (expr,)


def factors(expr: Expr) -> tuple[Expr, ...]:
    return args(expr) if atom_type(expr) is AtomType.Mul else (expr,)


def pow_parts(expr: Expr) -> tuple[Expr, Expr] | None:
    if atom_type(expr) is AtomType.Pow:
        return expr[0], expr[1]
    return None


def sum_expr(items: Iterable[Expr]) -> Expr:
    out = s.zero
    for item in items:
        out = out + item
    return out


def product_expr(items: Iterable[Expr]) -> Expr:
    out = s.one
    for item in items:
        out = out * item
    return out


def walk(expr: Expr) -> Iterator[Expr]:
    yield expr
    for child in args(expr):
        yield from walk(child)


def unique_subexpressions(expr: Expr, predicate: Callable[[Expr], bool]) -> tuple[Expr, ...]:
    seen: set[str] = set()
    out: list[Expr] = []
    for sub in walk(expr):
        if predicate(sub):
            key = expr_key(sub)
            if key not in seen:
                seen.add(key)
                out.append(sub)
    return tuple(out)


def is_zero(expr: Expr) -> bool:
    return canonical_string(expr.expand()) == "0"


def replace_many(expr: Expr, replacements: Iterable[tuple[Expr, Expr]]) -> Expr:
    out = expr
    for old, new in replacements:
        out = out.replace(old, new)
    return out


def field_label(expr: Expr) -> Expr:
    if not is_head(expr, s.Field):
        raise ValueError(f"Expected Field expression, got {canonical_string(expr)}")
    return expr[0]


def field_type(expr: Expr) -> Expr:
    if not is_head(expr, s.Field):
        raise ValueError(f"Expected Field expression, got {canonical_string(expr)}")
    return expr[1]


def field_indices(expr: Expr) -> tuple[Expr, ...]:
    if not is_head(expr, s.Field):
        raise ValueError(f"Expected Field expression, got {canonical_string(expr)}")
    return list_items(expr[2])


def field_derivatives(expr: Expr) -> tuple[Expr, ...]:
    if not is_head(expr, s.Field):
        raise ValueError(f"Expected Field expression, got {canonical_string(expr)}")
    return list_items(expr[3])


def field_with_derivatives(expr: Expr, derivatives: Iterable[Expr]) -> Expr:
    return s.Field(field_label(expr), field_type(expr), expr[2], list_expr(*derivatives))


def is_bar_field(expr: Expr) -> bool:
    return is_head(expr, s.Bar) and is_head(expr[0], s.Field)


def bar_field_inner(expr: Expr) -> Expr:
    if not is_bar_field(expr):
        raise ValueError(f"Expected Bar[Field] expression, got {canonical_string(expr)}")
    return expr[0]


def has_field_label(expr: Expr, label: Expr) -> bool:
    label_key = expr_key(label)
    return any(is_head(sub, s.Field) and expr_key(sub[0]) == label_key for sub in walk(expr))


def collect_field_atoms(expr: Expr) -> tuple[Expr, ...]:
    return unique_subexpressions(expr, lambda sub: is_head(sub, s.Field))


def collect_bar_field_atoms(expr: Expr) -> tuple[Expr, ...]:
    return unique_subexpressions(expr, is_bar_field)


def collect_field_atoms_for_label(expr: Expr, label: Expr) -> tuple[Expr, ...]:
    label_key = expr_key(label)
    return unique_subexpressions(
        expr,
        lambda sub: is_head(sub, s.Field) and expr_key(sub[0]) == label_key,
    )


def collect_bar_field_atoms_for_label(expr: Expr, label: Expr) -> tuple[Expr, ...]:
    label_key = expr_key(label)
    return unique_subexpressions(
        expr,
        lambda sub: is_bar_field(sub) and expr_key(field_label(bar_field_inner(sub))) == label_key,
    )


def contains_any_field(expr: Expr) -> bool:
    return any(is_head(sub, s.Field) for sub in walk(expr))


def transform(expr: Expr, visitor: Callable[[Expr], Expr | None]) -> Expr:
    replacement = visitor(expr)
    if replacement is not None:
        return replacement

    kind = atom_type(expr)
    if kind is AtomType.Num or kind is AtomType.Var:
        return expr
    if kind is AtomType.Add:
        return sum_expr(transform(child, visitor) for child in args(expr))
    if kind is AtomType.Mul:
        return product_expr(transform(child, visitor) for child in args(expr))
    if kind is AtomType.Pow:
        base, exponent = args(expr)
        return transform(base, visitor) ** transform(exponent, visitor)
    if kind is AtomType.Fn:
        head = head_name(expr)
        if head == head_name(s.List):
            return list_expr(*(transform(child, visitor) for child in args(expr)))
        if head == head_name(s.Field):
            return s.Field(
                transform(expr[0], visitor),
                transform(expr[1], visitor),
                transform(expr[2], visitor),
                transform(expr[3], visitor),
            )
        if head == head_name(s.Coupling):
            return s.Coupling(
                transform(expr[0], visitor),
                transform(expr[1], visitor),
                transform(expr[2], visitor),
            )
        if head == head_name(s.Index):
            return s.Index(transform(expr[0], visitor), transform(expr[1], visitor))
        if head == head_name(s.Bar):
            return s.Bar(transform(expr[0], visitor))
        if head == head_name(s.NCM):
            return s.NCM(*(transform(child, visitor) for child in args(expr)))
        if head == head_name(s.CD):
            return s.CD(transform(expr[0], visitor), transform(expr[1], visitor))
    return expr
