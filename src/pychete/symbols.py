from __future__ import annotations

import re
from enum import StrEnum
from functools import cached_property
from typing import Any

from symbolica import Expression, PrintMode, S
from symbolica.core import AtomType


_CANONICAL_PRINT_MODE = "canonical"
_CUSTOM_PRINT_MODE_KEY = "pychete"


_LATEX_NAMES = {
    "phi": r"\phi",
    "psi": r"\psi",
    "lambda": r"\lambda",
    "kappa": r"\kappa",
    "mu": r"\mu",
    "nu": r"\nu",
    "rho": r"\rho",
    "sigma": r"\sigma",
    "CapitalPhi": r"\Phi",
    "CapitalPsi": r"\Psi",
}

_MATHEMATICA_NAMES = {
    "phi": r"\[Phi]",
    "psi": r"\[Psi]",
    "lambda": r"\[Lambda]",
    "kappa": r"\[Kappa]",
    "mu": r"\[Mu]",
    "nu": r"\[Nu]",
    "rho": r"\[Rho]",
    "sigma": r"\[Sigma]",
    "CapitalPhi": r"\[CapitalPhi]",
    "CapitalPsi": r"\[CapitalPsi]",
}

_DISPLAY_NAMES = {
    "CapitalPhi": "Phi",
    "CapitalPsi": "Psi",
}


def _sym(name: str, **kwargs: Any) -> Expression:
    try:
        return S(name, **kwargs)
    except TypeError:
        if "print" not in kwargs:
            raise
        retry_kwargs = dict(kwargs)
        retry_kwargs.pop("print")
        return S(name, **retry_kwargs)


def _parse(text: str) -> Expression:
    return Expression.parse(text)


def _custom_print_mode(kwargs: dict[str, Any]) -> str | None:
    custom = kwargs.get("custom_print_mode")
    return custom.get(_CUSTOM_PRINT_MODE_KEY) if isinstance(custom, dict) else None


def _is_canonical_print(kwargs: dict[str, Any]) -> bool:
    return _custom_print_mode(kwargs) == _CANONICAL_PRINT_MODE


def _local_name(expr: Expression) -> str:
    return expr.get_name().split("::")[-1]


def _items(expr: Expression) -> tuple[Expression, ...]:
    return tuple(expr[i] for i in range(len(expr)))


def _list_items(expr: Expression) -> tuple[Expression, ...]:
    return _items(expr)


def _format_child(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    return expr.format(
        max_terms=kwargs.get("max_terms"),
        mode=mode,
        max_line_length=None,
        color_top_level_sum=False,
        color_builtin_symbols=False,
        bracket_level_colors=None,
        print_ring=False,
        number_thousands_separator=kwargs.get("number_thousands_separator"),
        multiplication_operator=kwargs.get("multiplication_operator", "*"),
        double_star_for_exponentiation=kwargs.get("double_star_for_exponentiation", mode is PrintMode.Sympy),
        function_brackets=kwargs.get("function_brackets", ("(", ")")),
        num_exp_as_superscript=False,
        precision=kwargs.get("precision"),
        show_namespaces=kwargs.get("show_namespaces", False),
        hide_namespace=kwargs.get("hide_namespace"),
        include_attributes=kwargs.get("include_attributes", False),
        custom_print_mode=kwargs.get("custom_print_mode", {}),
    )


def _display_name(name: str, mode: PrintMode) -> str:
    if mode is PrintMode.Latex:
        return _LATEX_NAMES.get(name, _DISPLAY_NAMES.get(name, name))
    if mode is PrintMode.Mathematica:
        return _MATHEMATICA_NAMES.get(name, _DISPLAY_NAMES.get(name, name))
    return _DISPLAY_NAMES.get(name, name)


def _mode_key(mode: PrintMode) -> str:
    return str(mode).split(".")[-1]


def _join(items: tuple[str, ...], mode: PrintMode) -> str:
    if mode is PrintMode.Latex:
        return r", ".join(items)
    return ", ".join(items)


def _call(name: str, args: tuple[str, ...], mode: PrintMode) -> str:
    if mode is PrintMode.Latex:
        if not args:
            return rf"\mathrm{{{name}}}"
        return rf"\mathrm{{{name}}}\left({_join(args, mode)}\right)"
    if mode is PrintMode.Mathematica:
        return f"{name}[{_join(args, mode)}]" if args else name
    return f"{name}({_join(args, mode)})" if args else name


def _subscript(base: str, indices: tuple[str, ...], mode: PrintMode) -> str:
    if not indices:
        return base
    if mode is PrintMode.Latex:
        return rf"{base}_{{{_join(indices, mode)}}}"
    if mode is PrintMode.Mathematica:
        return f"{base}[{_join(indices, mode)}]"
    return f"{base}[{_join(indices, mode)}]"


def _derivative(body: str, derivatives: tuple[str, ...], mode: PrintMode) -> str:
    if not derivatives:
        return body
    if mode is PrintMode.Latex:
        return rf"D_{{{_join(derivatives, mode)}}}\left({body}\right)"
    if mode is PrintMode.Mathematica:
        return f"CD[{{{_join(derivatives, mode)}}}, {body}]"
    return f"D[{_join(derivatives, mode)}]({body})"


def _format_list(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> tuple[str, ...]:
    return tuple(_format_child(item, mode, kwargs) for item in _list_items(expr))


def _print_user_symbol(expr: Expression, mode: PrintMode, **kwargs: Any) -> str | None:
    if _is_canonical_print(kwargs):
        return None
    try:
        label = expr.get_symbol_data(SymbolDataKey.LABEL.value)
    except KeyError:
        label = _local_name(expr)
    name = str(label)
    base = _display_name(name, mode)
    if expr.get_type() is AtomType.Fn:
        return _call(base, tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode)
    return base


def _print_field(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    base = _format_child(expr[0], mode, kwargs)
    indices = _format_list(expr[2], mode, kwargs)
    derivatives = _format_list(expr[3], mode, kwargs)
    return _derivative(_subscript(base, indices, mode), derivatives, mode)


def _print_coupling(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    return _subscript(_format_child(expr[0], mode, kwargs), _format_list(expr[1], mode, kwargs), mode)


def _print_index(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    return _format_child(expr[0], mode, kwargs)


def _print_field_strength(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    label = _format_child(expr[0], mode, kwargs)
    lorentz = _format_list(expr[1], mode, kwargs)
    internal = _format_list(expr[2], mode, kwargs)
    derivatives = _format_list(expr[3], mode, kwargs)
    indices = (label, *lorentz, *internal)
    body = _subscript("F", indices, mode)
    return _derivative(body, derivatives, mode)


def _print_bar(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    body = _format_child(expr[0], mode, kwargs)
    if mode is PrintMode.Latex:
        return rf"\bar{{{body}}}"
    if mode is PrintMode.Mathematica:
        return f"Bar[{body}]"
    if mode is PrintMode.Typst:
        return f"overline({body})"
    return f"bar({body})"


def _print_cd(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    index = _format_child(expr[0], mode, kwargs)
    body = _format_child(expr[1], mode, kwargs)
    return _derivative(body, (index,), mode)


def _print_delta(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    args = tuple(_format_child(arg, mode, kwargs) for arg in _items(expr))
    if mode is PrintMode.Latex and len(args) == 2:
        return rf"\delta_{{{args[0]} {args[1]}}}"
    return _call("Delta" if mode is PrintMode.Mathematica else "delta", args, mode)


def _print_metric(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    args = tuple(_format_child(arg, mode, kwargs) for arg in _items(expr))
    if mode is PrintMode.Latex and len(args) == 2:
        return rf"g_{{{args[0]} {args[1]}}}"
    return _call("Metric" if mode is PrintMode.Mathematica else "g", args, mode)


def _print_ncm(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    args = tuple(_format_child(arg, mode, kwargs) for arg in _items(expr))
    if mode is PrintMode.Latex:
        return r"\,".join(args)
    if mode is PrintMode.Mathematica:
        return f"NonCommutativeMultiply[{_join(args, mode)}]"
    return " ** ".join(args)


def _print_gamma(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    args = tuple(_format_child(arg, mode, kwargs) for arg in _items(expr))
    if mode is PrintMode.Latex and len(args) == 1:
        return rf"\gamma^{{{args[0]}}}"
    return _call("Gamma" if mode is PrintMode.Mathematica else "gamma", args, mode)


def _print_eom(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    args = tuple(_format_child(arg, mode, kwargs) for arg in _items(expr))
    if len(args) == 2:
        if mode is PrintMode.Latex:
            return rf"\mathrm{{EOM}}\left[{args[0]}\right]={args[1]}"
        return f"EOM[{args[0]}] = {args[1]}"
    return _call("EOM", args, mode)


def _print_builtin(expr: Expression, mode: PrintMode, **kwargs: Any) -> str | None:
    if _is_canonical_print(kwargs):
        return None
    name = _local_name(expr)
    if name.endswith("_"):
        return name
    if expr.get_type() is not AtomType.Fn:
        return _BUILTIN_VARIABLE_PRINT_NAMES.get(_mode_key(mode), {}).get(name, _BUILTIN_VARIABLE_PRINT_NAMES["Symbolica"].get(name, name))

    handlers = {
        "List": lambda: "{" + _join(tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode) + "}",
        "Field": lambda: _print_field(expr, mode, kwargs),
        "Coupling": lambda: _print_coupling(expr, mode, kwargs),
        "Index": lambda: _print_index(expr, mode, kwargs),
        "FieldStrength": lambda: _print_field_strength(expr, mode, kwargs),
        "Bar": lambda: _print_bar(expr, mode, kwargs),
        "CD": lambda: _print_cd(expr, mode, kwargs),
        "Delta": lambda: _print_delta(expr, mode, kwargs),
        "Metric": lambda: _print_metric(expr, mode, kwargs),
        "FlavorSum": lambda: _call("FlavorSum", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
        "NCM": lambda: _print_ncm(expr, mode, kwargs),
        "DiracProduct": lambda: _print_ncm(expr, mode, kwargs),
        "Gamma": lambda: _print_gamma(expr, mode, kwargs),
        "Proj": lambda: _call("Proj", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
        "CG": lambda: _call("CG", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
        "EOM": lambda: _print_eom(expr, mode, kwargs),
        "HeavyFieldOrder": lambda: _call("HFO", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
        "Vector": lambda: _call("Vector", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
        "SU": lambda: _call("SU", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
        "U1": lambda: _call("U1", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
    }
    if name in handlers:
        return handlers[name]()
    return _call(name, tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode)


_BUILTIN_VARIABLE_PRINT_NAMES: dict[str, dict[str, str]] = {
    "Symbolica": {
        "Scalar": "Scalar",
        "Fermion": "Fermion",
        "Vector": "Vector",
        "Ghost": "Ghost",
        "AntiGhost": "AntiGhost",
        "Lorentz": "Lorentz",
        "U1": "U1",
        "SU": "SU",
        "fund": "fund",
        "adj": "adj",
        "PR": "P_R",
        "PL": "P_L",
        "eft_order_parameter": "eps_EFT",
        "cd_variation_parameter": "eta_CD",
        "functional_variation_parameter": "eta_FD",
    },
    "Sympy": {
        "Scalar": "Scalar",
        "Fermion": "Fermion",
        "Vector": "Vector",
        "Ghost": "Ghost",
        "AntiGhost": "AntiGhost",
        "Lorentz": "Lorentz",
        "U1": "U1",
        "SU": "SU",
        "fund": "fund",
        "adj": "adj",
        "PR": "P_R",
        "PL": "P_L",
        "eft_order_parameter": "eps_EFT",
        "cd_variation_parameter": "eta_CD",
        "functional_variation_parameter": "eta_FD",
    },
    "Mathematica": {
        "Scalar": "Scalar",
        "Fermion": "Fermion",
        "Vector": "Vector",
        "Ghost": "Ghost",
        "AntiGhost": "AntiGhost",
        "Lorentz": "Lorentz",
        "U1": "U1",
        "SU": "SU",
        "fund": "Fund",
        "adj": "Adj",
        "PR": "PR",
        "PL": "PL",
        "eft_order_parameter": "epsEFT",
        "cd_variation_parameter": "etaCD",
        "functional_variation_parameter": "etaFD",
    },
    "Latex": {
        "Scalar": r"\mathrm{Scalar}",
        "Fermion": r"\mathrm{Fermion}",
        "Vector": r"\mathrm{Vector}",
        "Ghost": r"\mathrm{Ghost}",
        "AntiGhost": r"\mathrm{AntiGhost}",
        "Lorentz": r"\mathrm{Lorentz}",
        "U1": r"\mathrm{U}(1)",
        "SU": r"\mathrm{SU}",
        "fund": r"\mathbf{fund}",
        "adj": r"\mathbf{adj}",
        "PR": r"P_R",
        "PL": r"P_L",
        "eft_order_parameter": r"\epsilon_{\mathrm{EFT}}",
        "cd_variation_parameter": r"\eta_{\mathrm{CD}}",
        "functional_variation_parameter": r"\eta_{\mathrm{FD}}",
    },
    "Typst": {
        "Scalar": "Scalar",
        "Fermion": "Fermion",
        "Vector": "Vector",
        "Ghost": "Ghost",
        "AntiGhost": "AntiGhost",
        "Lorentz": "Lorentz",
        "U1": "U1",
        "SU": "SU",
        "fund": "fund",
        "adj": "adj",
        "PR": "P_R",
        "PL": "P_L",
        "eft_order_parameter": "epsilon_EFT",
        "cd_variation_parameter": "eta_CD",
        "functional_variation_parameter": "eta_FD",
    },
}


class SymbolRole(StrEnum):
    PROJECT = "pychete"
    LABEL = "label"
    FIELD = "field"
    COUPLING = "coupling"
    INDEX = "index"
    INDEX_TYPE = "index_type"
    GROUP = "group"
    EXTERNAL = "external"


class SymbolDataKey(StrEnum):
    THEORY = "theory"
    ROLE = "role"
    LABEL = "label"
    NAME = "name"
    FIELD_TYPE = "field_type"
    INDICES = "indices"
    EFT_ORDER = "eft_order"
    SELF_CONJUGATE = "self_conjugate"
    MASS_KIND = "mass_kind"
    MASS_LABEL = "mass_label"
    MASS_INDICES = "mass_indices"
    DIMENSION = "dimension"
    GROUP_TYPE = "group_type"
    GROUP_COUPLING = "group_coupling"
    GROUP_FIELD = "group_field"


class SymbolStore:
    """Central store for every reusable Symbolica symbol used by pychete."""

    namespace = "pychete"

    def head(self, name: str, **kwargs: Any) -> Expression:
        kwargs.setdefault("print", _print_builtin)
        return _sym(f"{self.namespace}::{name}", **kwargs)

    def user(self, namespace: str, name: str, **kwargs: Any) -> Expression:
        kwargs.setdefault("print", _print_user_symbol)
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

    @cached_property
    def FieldLabelWildcard(self) -> Expression:
        return self.head("field_label_")

    @cached_property
    def FieldTypeWildcard(self) -> Expression:
        return self.head("field_type_")

    @cached_property
    def FieldIndicesWildcard(self) -> Expression:
        return self.head("field_indices_")

    @cached_property
    def FieldDerivativesWildcard(self) -> Expression:
        return self.head("field_derivatives_")

    @cached_property
    def IndexLabelWildcard(self) -> Expression:
        return self.head("index_label_")

    @cached_property
    def IndexRepresentationWildcard(self) -> Expression:
        return self.head("index_representation_")

    @cached_property
    def PowBaseWildcard(self) -> Expression:
        return self.head("pow_base_")

    @cached_property
    def PowExponentWildcard(self) -> Expression:
        return self.head("pow_exponent_")

    @cached_property
    def CDIndexWildcard(self) -> Expression:
        return self.head("cd_index_")

    @cached_property
    def CDBodyWildcard(self) -> Expression:
        return self.head("cd_body_")

    @cached_property
    def CouplingLabelWildcard(self) -> Expression:
        return self.head("coupling_label_")

    @cached_property
    def CouplingIndicesWildcard(self) -> Expression:
        return self.head("coupling_indices_")

    @cached_property
    def CouplingOrderWildcard(self) -> Expression:
        return self.head("coupling_order_")

    @cached_property
    def FieldStrengthLabelWildcard(self) -> Expression:
        return self.head("field_strength_label_")

    @cached_property
    def FieldStrengthLorentzWildcard(self) -> Expression:
        return self.head("field_strength_lorentz_")

    @cached_property
    def FieldStrengthIndicesWildcard(self) -> Expression:
        return self.head("field_strength_indices_")

    @cached_property
    def FieldStrengthDerivativesWildcard(self) -> Expression:
        return self.head("field_strength_derivatives_")

    @cached_property
    def EFTExpansionParameter(self) -> Expression:
        return self.head("eft_order_parameter")

    @cached_property
    def CDVariationParameter(self) -> Expression:
        return self.head("cd_variation_parameter")

    @cached_property
    def FunctionalVariationParameter(self) -> Expression:
        return self.head("functional_variation_parameter")


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
        show_namespaces=True,
        include_attributes=False,
        custom_print_mode={_CUSTOM_PRINT_MODE_KEY: _CANONICAL_PRINT_MODE},
    )


def expression_from_canonical(text: str) -> Expression:
    return Expression.parse(text)


def symbol_data(expr: Expression, key: SymbolDataKey, default: Any = None) -> Any:
    try:
        return expr.get_symbol_data(key.value)
    except KeyError:
        return default
