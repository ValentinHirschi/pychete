from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from html import escape
from types import MappingProxyType
from typing import TYPE_CHECKING, cast

from symbolica import Expression

from .theory_metadata import ExternalHandle

if TYPE_CHECKING:
    from .theory import Theory


OperatorBuilder = Callable[["Theory", tuple[Expression, ...]], Expression | None]


@dataclass(frozen=True)
class OperatorBasis:
    """Named operator basis with pychete-native operator builders."""

    name: str
    builders: Mapping[str, OperatorBuilder]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "builders",
            cast(Mapping[str, OperatorBuilder], MappingProxyType(dict(self.builders))),
        )

    def operator_names(self) -> tuple[str, ...]:
        """Return operator labels supported by this basis."""

        return tuple(self.builders)

    def _repr_html_(self) -> str:
        """Return a compact notebook HTML representation."""

        preview_names = self.operator_names()[:8]
        preview = ", ".join(escape(name) for name in preview_names)
        suffix = ", ..." if len(self.builders) > len(preview_names) else ""
        return (
            f"<code>OperatorBasis({escape(self.name)}; "
            f"{len(self.builders)} operators"
            f"{': ' + preview + suffix if preview else ''})</code>"
        )

    def _repr_latex_(self) -> str:
        """Return a compact notebook LaTeX representation."""

        name = self.name.replace("_", r"\_")
        return (
            rf"$\mathrm{{OperatorBasis}}\left("
            rf"\mathrm{{{name}}}, {len(self.builders)}\ \mathrm{{operators}}\right)$"
        )

    def operator(
        self,
        theory: Theory,
        name: str,
        indices: Iterable[Expression] = (),
    ) -> Expression | None:
        """Build one operator monomial for ``theory`` if this basis supports it."""

        builder = self.builders.get(name)
        if builder is None:
            return None
        return builder(theory, tuple(indices))


def define_wilson_coefficient_from_basis(
    theory: Theory,
    operator_basis: OperatorBasis,
    name: str,
    *,
    indices: Iterable[Expression] = (),
    eft_order: int = 0,
    basis: str | None = None,
) -> ExternalHandle:
    """Define a Wilson coefficient using operator metadata from a basis."""

    index_tuple = tuple(indices)
    return theory.define_wilson_coefficient(
        name,
        indices=index_tuple,
        eft_order=eft_order,
        basis=operator_basis.name if basis is None else basis,
        operator=operator_basis.operator(theory, name, index_tuple),
    )


__all__ = [
    "OperatorBasis",
    "define_wilson_coefficient_from_basis",
]
