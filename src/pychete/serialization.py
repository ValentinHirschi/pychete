from __future__ import annotations

from symbolica import Expression, PrintMode


_CANONICAL_PRINT_MODE = "canonical"
_CUSTOM_PRINT_MODE_KEY = "pychete"


def canonical_string(expr: Expression, *, show_namespaces: bool = True) -> str:
    """Return the parse-stable canonical representation of ``expr``.

    By default, canonical strings include namespaces and disable pychete's
    pretty printer, making them suitable for JSON checkpoints and exact test
    fixtures. Pass ``show_namespaces=False`` for a compact Symbolica string
    that still bypasses pychete's pretty-printer callbacks.
    """

    return expr.format(
        max_terms=None,
        mode=PrintMode.Symbolica,
        max_line_length=None,
        color_top_level_sum=False,
        color_builtin_symbols=False,
        bracket_level_colors=None,
        print_ring=False,
        multiplication_operator="*",
        double_star_for_exponentiation=False,
        function_brackets=("(", ")"),
        num_exp_as_superscript=False,
        show_namespaces=show_namespaces,
        include_attributes=False,
        custom_print_mode={_CUSTOM_PRINT_MODE_KEY: _CANONICAL_PRINT_MODE},
    )


def expression_from_canonical(text: str) -> Expression:
    """Parse an expression produced by ``canonical_string``."""

    from .symbols import s

    s.register_builtins()
    return Expression.parse(text)
