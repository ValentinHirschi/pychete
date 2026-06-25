from __future__ import annotations

SUPERTRACE_CATEGORY_WORDS = frozenset(
    {
        "hScalar",
        "lScalar",
        "hFermion",
        "lFermion",
        "hVector",
        "lVector",
        "hGhost",
        "lGhost",
        "hAntiGhost",
        "lAntiGhost",
    }
)


def supertrace_word_order(name: str) -> int:
    """Return the Matchete-style word order encoded in a named supertrace."""

    parts = name.split("-")
    if all(part in SUPERTRACE_CATEGORY_WORDS for part in parts):
        return len(parts)
    return 0


def is_named_supertrace(name: str) -> bool:
    """Whether ``name`` is a Matchete-style trace category sequence."""

    return supertrace_word_order(name) > 0


__all__ = ["SUPERTRACE_CATEGORY_WORDS", "is_named_supertrace", "supertrace_word_order"]
