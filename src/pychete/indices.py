from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from symbolica import Expression
from symbolica.core import AtomType

from .expr import args, as_int, atom_type, expr_key, is_head, pow_parts, replace_many, unique_subexpressions
from .symbols import canonical_string, s
from .theory import Theory


@dataclass(frozen=True)
class IndexInfo:
    expr: Expression
    label: Expression
    representation: Expression

    @property
    def key(self) -> str:
        return expr_key(self.expr)


def index_info(expr: Expression) -> IndexInfo:
    if not is_head(expr, s.Index):
        raise ValueError(f"Expected Index expression, got {canonical_string(expr)}")
    return IndexInfo(expr=expr, label=expr[0], representation=expr[1])


def collect_indices(expr: Expression) -> tuple[IndexInfo, ...]:
    return tuple(index_info(sub) for sub in unique_subexpressions(expr, lambda sub: is_head(sub, s.Index)))


def _index_counts(expr: Expression) -> Counter[str]:
    counts: Counter[str] = Counter()
    _count_indices(expr, counts, multiplier=1)
    return counts


def _count_indices(expr: Expression, counts: Counter[str], *, multiplier: int) -> None:
    if is_head(expr, s.Index):
        counts[expr_key(expr)] += multiplier
        return
    parts = pow_parts(expr)
    if parts is not None:
        base, exponent = parts
        n = as_int(exponent)
        _count_indices(base, counts, multiplier=multiplier * (n if n is not None else 1))
        return
    kind = atom_type(expr)
    if kind is AtomType.Num or kind is AtomType.Var:
        return
    for child in args(expr):
        _count_indices(child, counts, multiplier=multiplier)


def open_indices(expr: Expression) -> tuple[IndexInfo, ...]:
    counts = _index_counts(expr)
    return tuple(info for info in collect_indices(expr) if counts[info.key] == 1)


def dummy_indices(expr: Expression) -> tuple[IndexInfo, ...]:
    counts = _index_counts(expr)
    return tuple(info for info in collect_indices(expr) if counts[info.key] > 1)


def relabel_dummy_indices(theory: Theory, expr: Expression, *, prefix: str = "d") -> Expression:
    replacements: list[tuple[Expression, Expression]] = []
    for i, info in enumerate(sorted(dummy_indices(expr), key=lambda item: (canonical_string(item.representation), item.key))):
        new_label = theory.symbol(f"{prefix}{i}", role="index")
        replacements.append((info.expr, s.Index(new_label, info.representation)))
    return replace_many(expr, replacements)
