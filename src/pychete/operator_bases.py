from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from html import escape
from types import MappingProxyType
from typing import TYPE_CHECKING, cast

from symbolica import Expression

from .theory_metadata import ExternalHandle

if TYPE_CHECKING:
    from .theory import Theory


OperatorBuilder = Callable[["Theory", tuple[Expression, ...]], Expression | None]
_OPERATOR_BASIS_REGISTRY: dict[str, "OperatorBasis"] = {}


@dataclass(frozen=True)
class OperatorBasis:
    """Named operator basis with pychete-native operator builders."""

    name: str
    builders: Mapping[str, OperatorBuilder]
    effective_projection_builders: Mapping[str, OperatorBuilder] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "builders",
            cast(Mapping[str, OperatorBuilder], MappingProxyType(dict(self.builders))),
        )
        object.__setattr__(
            self,
            "effective_projection_builders",
            cast(
                Mapping[str, OperatorBuilder],
                MappingProxyType(dict(self.effective_projection_builders)),
            ),
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

    def effective_projection_operator(
        self,
        theory: Theory,
        name: str,
        indices: Iterable[Expression] = (),
    ) -> Expression | None:
        """Build the operator representative used in effective-coupling maps."""

        index_tuple = tuple(indices)
        projection_builder = self.effective_projection_builders.get(name)
        if projection_builder is not None:
            return projection_builder(theory, index_tuple)
        return self.operator(theory, name, index_tuple)


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
        effective_projection_operator=operator_basis.effective_projection_operator(theory, name, index_tuple),
    )


def register_operator_basis(operator_basis: OperatorBasis, *, replace: bool = False) -> OperatorBasis:
    """Register a generic operator-basis provider by name.

    Basis-specific modules should use this hook when they are imported. The
    matching engine still consumes only generic ``OperatorBasis`` metadata; the
    registry is a convenience layer for discovery and user code.
    """

    existing = _OPERATOR_BASIS_REGISTRY.get(operator_basis.name)
    if existing is not None and existing is not operator_basis and not replace:
        raise ValueError(f"operator basis {operator_basis.name!r} is already registered")
    _OPERATOR_BASIS_REGISTRY[operator_basis.name] = operator_basis
    return operator_basis


def registered_operator_basis(name: str) -> OperatorBasis:
    """Return a registered operator basis by name."""

    try:
        return _OPERATOR_BASIS_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"no operator basis {name!r} is registered") from exc


def operator_basis_names() -> tuple[str, ...]:
    """Return registered operator-basis names in deterministic order."""

    return tuple(sorted(_OPERATOR_BASIS_REGISTRY))


def define_wilson_coefficient_from_registered_basis(
    theory: Theory,
    basis: str,
    name: str,
    *,
    indices: Iterable[Expression] = (),
    eft_order: int = 0,
) -> ExternalHandle:
    """Define a Wilson coefficient from a registered operator basis."""

    return define_wilson_coefficient_from_basis(
        theory,
        registered_operator_basis(basis),
        name,
        indices=indices,
        eft_order=eft_order,
    )


__all__ = [
    "OperatorBasis",
    "define_wilson_coefficient_from_registered_basis",
    "define_wilson_coefficient_from_basis",
    "operator_basis_names",
    "registered_operator_basis",
    "register_operator_basis",
]
