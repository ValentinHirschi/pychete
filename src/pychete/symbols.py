from __future__ import annotations

import re
from functools import cached_property
from typing import Any

from symbolica import Expression, S


def _sym(name: str, **kwargs: Any) -> Expression:
    return S(name, **kwargs)


def _parse(text: str) -> Expression:
    return Expression.parse(text)


class SymbolStore:
    """Central store for every reusable Symbolica symbol used by pychete."""

    namespace = "pychete"

    def head(self, name: str, **kwargs: Any) -> Expression:
        return _sym(f"{self.namespace}::{name}", **kwargs)

    def user(self, namespace: str, name: str, **kwargs: Any) -> Expression:
        return _sym(f"{namespace}::{safe_symbol_name(name)}", **kwargs)

    @cached_property
    def zero(self) -> Expression:
        return _parse("0")

    @cached_property
    def one(self) -> Expression:
        return _parse("1")

    @cached_property
    def half(self) -> Expression:
        return _parse("1/2")

    @cached_property
    def minus_half(self) -> Expression:
        return _parse("-1/2")

    @cached_property
    def sixth(self) -> Expression:
        return _parse("1/6")

    @cached_property
    def twenty_fourth(self) -> Expression:
        return _parse("1/24")

    @cached_property
    def I(self) -> Expression:
        return Expression.I

    @cached_property
    def List(self) -> Expression:
        return self.head("List")

    @cached_property
    def Field(self) -> Expression:
        return self.head("Field")

    @cached_property
    def Coupling(self) -> Expression:
        return self.head("Coupling")

    @cached_property
    def Index(self) -> Expression:
        return self.head("Index")

    @cached_property
    def FieldStrength(self) -> Expression:
        return self.head("FieldStrength")

    @cached_property
    def Bar(self) -> Expression:
        return self.head("Bar")

    @cached_property
    def CD(self) -> Expression:
        return self.head("CD")

    @cached_property
    def Delta(self) -> Expression:
        return self.head("Delta")

    @cached_property
    def Metric(self) -> Expression:
        return self.head("Metric")

    @cached_property
    def FlavorSum(self) -> Expression:
        return self.head("FlavorSum")

    @cached_property
    def NCM(self) -> Expression:
        return self.head("NCM")

    @cached_property
    def DiracProduct(self) -> Expression:
        return self.head("DiracProduct")

    @cached_property
    def Gamma(self) -> Expression:
        return self.head("Gamma")

    @cached_property
    def Proj(self) -> Expression:
        return self.head("Proj")

    @cached_property
    def CG(self) -> Expression:
        return self.head("CG")

    @cached_property
    def EOM(self) -> Expression:
        return self.head("EOM")

    @cached_property
    def HeavyFieldOrder(self) -> Expression:
        return self.head("HeavyFieldOrder")

    @cached_property
    def Scalar(self) -> Expression:
        return self.head("Scalar")

    @cached_property
    def Fermion(self) -> Expression:
        return self.head("Fermion")

    @cached_property
    def Vector(self) -> Expression:
        return self.head("Vector")

    @cached_property
    def Ghost(self) -> Expression:
        return self.head("Ghost")

    @cached_property
    def AntiGhost(self) -> Expression:
        return self.head("AntiGhost")

    @cached_property
    def Lorentz(self) -> Expression:
        return self.head("Lorentz")

    @cached_property
    def U1(self) -> Expression:
        return self.head("U1")

    @cached_property
    def SU(self) -> Expression:
        return self.head("SU")

    @cached_property
    def fund(self) -> Expression:
        return self.head("fund")

    @cached_property
    def adj(self) -> Expression:
        return self.head("adj")

    @cached_property
    def PR(self) -> Expression:
        return self.head("PR")

    @cached_property
    def PL(self) -> Expression:
        return self.head("PL")


s = SymbolStore()


_GREEK_ESCAPES = {
    r"\[Phi]": "phi",
    r"\[Psi]": "psi",
    r"\[CapitalPsi]": "CapitalPsi",
    r"\[Lambda]": "lambda",
    r"\[Kappa]": "kappa",
    r"\[Mu]": "mu",
    r"\[Nu]": "nu",
}


def safe_symbol_name(name: str) -> str:
    out = name.strip()
    for source, replacement in _GREEK_ESCAPES.items():
        out = out.replace(source, replacement)
    out = re.sub(r"[^0-9A-Za-z_]+", "_", out)
    out = out.strip("_")
    if not out:
        out = "unnamed"
    if out[0].isdigit():
        out = f"n_{out}"
    return out


def canonical_string(expr: Expression) -> str:
    """Parse-stable string representation for JSON checkpoints and fixtures."""

    return expr.format_plain()


def expression_from_canonical(text: str) -> Expression:
    return Expression.parse(text)
