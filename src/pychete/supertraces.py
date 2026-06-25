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


def is_unnormalized_supertrace_alias(name: str) -> bool:
    """Whether ``name`` stores a raw convention copy of a normalized supertrace."""

    suffix = "[unnormalized]"
    return name.endswith(suffix) and is_named_supertrace(name[: -len(suffix)])


__all__ = [
    "SUPERTRACE_CATEGORY_WORDS",
    "is_named_supertrace",
    "is_unnormalized_supertrace_alias",
    "supertrace_word_order",
]
