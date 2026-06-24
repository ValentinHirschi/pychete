from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from html import escape

from symbolica import Expression, Replacement, S

from .expr import as_int, index_pattern, is_head, power_pattern
from .symbols import canonical_string, display_string, latex_string, s


@dataclass(frozen=True)
class IndexInfo:
    """Information extracted from a pychete ``Index`` expression."""

    expr: Expression
    label: Expression
    representation: Expression

    def _repr_latex_(self) -> str:
        return f"${latex_string(self.expr)}$"

    def _repr_html_(self) -> str:
        return f"<code>{escape(display_string(self.expr))}</code>"


def index_info(expr: Expression) -> IndexInfo:
    """Return the label and representation of an ``Index`` expression."""

    if not is_head(expr, s.Index):
        raise ValueError(f"Expected Index expression, got {canonical_string(expr)}")
    return IndexInfo(expr=expr, label=expr[0], representation=expr[1])


def collect_indices(expr: Expression) -> tuple[IndexInfo, ...]:
    """Collect unique index expressions appearing in ``expr``."""

    return tuple(index_info(sub) for sub in _matched_index_atoms(expr, unique=True))


def _matched_index_atoms(expr: Expression, *, unique: bool) -> tuple[Expression, ...]:
    pattern = index_pattern()
    matches = (pattern.replace_wildcards(match) for match in expr.match(pattern))
    return tuple(dict.fromkeys(matches)) if unique else tuple(matches)


def _index_counts(expr: Expression) -> Counter[Expression]:
    counts: Counter[Expression] = Counter()
    for index in _matched_index_atoms(expr, unique=False):
        counts[index] += 1

    pow_pat = power_pattern()
    for match in expr.match(pow_pat):
        n = as_int(match[s.PowExponentWildcard])
        if n is None:
            continue
        for index, count in _index_counts(match[s.PowBaseWildcard]).items():
            counts[index] += (n - 1) * count

    return counts


def open_indices(expr: Expression) -> tuple[IndexInfo, ...]:
    """Return indices that occur exactly once in ``expr``."""

    counts = _index_counts(expr)
    return tuple(info for info in collect_indices(expr) if counts[info.expr] == 1)


def dummy_indices(expr: Expression) -> tuple[IndexInfo, ...]:
    """Return indices that occur more than once in ``expr``."""

    counts = _index_counts(expr)
    return tuple(info for info in collect_indices(expr) if counts[info.expr] > 1)


def relabel_dummy_indices(expr: Expression, *, prefix: str = "d") -> Expression:
    """Alpha-rename repeated indices deterministically.

    With the default ``prefix="d"``, labels are generated as
    ``s.dummy_index(0)``, ``s.dummy_index(1)``, and so on. Other prefixes build
    plain Symbolica symbols such as ``S("i0")`` and let Symbolica report
    invalid names.
    """

    replacements: list[tuple[Expression, Expression]] = []
    for i, info in enumerate(sorted(dummy_indices(expr), key=lambda item: (canonical_string(item.representation), canonical_string(item.expr)))):
        new_label = s.dummy_index(i) if prefix == "d" else S(f"{prefix}{i}")
        replacements.append((info.expr, s.Index(new_label, info.representation)))
    return expr.replace_multiple([Replacement(old, new) for old, new in replacements])
