from __future__ import annotations

from symbolica import Expression


def assert_expr_equal(actual: Expression, expected: Expression) -> None:
    diff = (actual - expected).expand().rationalize().expand()
    assert bool(diff == Expression.num(0)), diff.format_plain()
