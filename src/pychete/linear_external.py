from __future__ import annotations

from symbolica import Expression

from .symbols import SymbolDataKey, SymbolRole, canonical_string, symbol_data
from .theory_metadata import EXTERNAL_LINEAR_FUNCTION_TAG


def linear_external_function_heads(expr: Expression) -> tuple[Expression, ...]:
    """Return tagged external function heads that should be treated as linear."""

    return tuple(
        sorted(
            (symbol for symbol in expr.get_all_symbols() if is_linear_external_function_head(symbol)),
            key=canonical_string,
        )
    )


def is_linear_external_function_head(symbol: Expression) -> bool:
    """Whether ``symbol`` is a theory-owned external head tagged as linear."""

    return (
        symbol_data(symbol, SymbolDataKey.ROLE) == SymbolRole.EXTERNAL.value
        and EXTERNAL_LINEAR_FUNCTION_TAG in {str(tag).split("::")[-1] for tag in symbol.get_tags()}
    )
