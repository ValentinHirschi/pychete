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
    "Phi": r"\Phi",
    "Psi": r"\Psi",
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
    "Phi": r"\[CapitalPhi]",
    "Psi": r"\[CapitalPsi]",
}

_SYMBOL_NAMESPACE = "pychete"
_DISPLAY_NAMES: dict[str, str] = {}


def _sym(name: str, **kwargs: Any) -> Expression:
    try:
        return S(name, **kwargs)
    except TypeError:
        if "print" not in kwargs:
            raise
        retry_kwargs = dict(kwargs)
        retry_kwargs.pop("print")
        return S(name, **retry_kwargs)


def _custom_print_mode(kwargs: dict[str, Any]) -> str | None:
    custom = kwargs.get("custom_print_mode")
    return custom.get(_CUSTOM_PRINT_MODE_KEY) if isinstance(custom, dict) else None


def _is_canonical_print(kwargs: dict[str, Any]) -> bool:
    return _custom_print_mode(kwargs) == _CANONICAL_PRINT_MODE


def _local_name(expr: Expression) -> str:
    return expr.get_name().split("::")[-1]


def _is_builtin_fn(expr: Expression, name: str) -> bool:
    return expr.get_type() is AtomType.Fn and expr.get_name() == f"{_SYMBOL_NAMESPACE}::{name}"


def _is_builtin_symbol(expr: Expression, name: str) -> bool:
    kind = expr.get_type()
    return (kind is AtomType.Fn or kind is AtomType.Var) and expr.get_name() == f"{_SYMBOL_NAMESPACE}::{name}"


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
        return "".join(rf"D_{{{index}}}" for index in derivatives) + body
    if mode is PrintMode.Mathematica:
        return f"CD[{{{_join(derivatives, mode)}}}, {body}]"
    return f"D[{_join(derivatives, mode)}]({body})"


def _format_list(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> tuple[str, ...]:
    return tuple(_format_child(item, mode, kwargs) for item in _list_items(expr))


def _native_latex(expr: Expression) -> str:
    text = expr.format(
        max_terms=None,
        mode=PrintMode.Latex,
        max_line_length=None,
        color_top_level_sum=False,
        color_builtin_symbols=False,
        bracket_level_colors=None,
        print_ring=False,
        multiplication_operator="*",
        num_exp_as_superscript=False,
    )
    text = re.sub(r"(?<![0-9A-Za-z_.])([+-]?)1𝑖(?=([*/\\\s]|$))", r"\1𝑖", text)
    return text.replace("𝑖", r"\mathrm{i}")


def _int_value(expr: Expression) -> int | None:
    if expr.get_type() is not AtomType.Num:
        return None
    try:
        return int(expr)
    except (TypeError, ValueError):
        return None


def _number_parts(expr: Expression) -> tuple[str, str, str] | None:
    text = expr.format(
        max_terms=None,
        mode=PrintMode.Symbolica,
        max_line_length=None,
        color_top_level_sum=False,
        color_builtin_symbols=False,
        bracket_level_colors=None,
        print_ring=False,
        multiplication_operator="*",
        num_exp_as_superscript=False,
    )
    match = re.fullmatch(r"(-?)([0-9]+)(𝑖)?(?:/([0-9]+)(𝑖)?)?", text)
    if match is None:
        return None
    sign = "-" if match.group(1) else ""
    numerator = match.group(2)
    denominator = match.group(4) or "1"
    if match.group(3) or match.group(5):
        numerator = r"\mathrm{i}" if numerator == "1" else rf"{numerator}\mathrm{{i}}"
    return sign, numerator, denominator


def _latex_derivative_prefix(derivatives: tuple[Expression, ...]) -> str:
    labels = tuple(_latex_expr(index) for index in derivatives)
    pieces: list[str] = []
    index = 0
    while index < len(labels):
        label = labels[index]
        count = 1
        while index + count < len(labels) and labels[index + count] == label:
            count += 1
        pieces.append(rf"D^{{{count}}}" if count > 1 else rf"D_{{{label}}}")
        index += count
    return "".join(pieces)


def _latex_field_like(expr: Expression, *, barred: bool = False, extra_derivatives: tuple[Expression, ...] = ()) -> str:
    base = _latex_expr(expr[0])
    if barred:
        base = rf"\bar{{{base}}}"
    body = _subscript(base, tuple(_latex_expr(index) for index in _list_items(expr[2])), PrintMode.Latex)
    derivatives = extra_derivatives + _list_items(expr[3])
    return _latex_derivative_prefix(derivatives) + body


def _collect_cd(expr: Expression) -> tuple[tuple[Expression, ...], Expression]:
    derivatives: list[Expression] = []
    body = expr
    while _is_builtin_fn(body, "CD"):
        derivatives.append(body[0])
        body = body[1]
    return tuple(derivatives), body


def _latex_bar(body: Expression, *, extra_derivatives: tuple[Expression, ...] = ()) -> str:
    cd_derivatives, inner = _collect_cd(body)
    derivatives = extra_derivatives + cd_derivatives
    if _is_builtin_fn(inner, "Field"):
        return _latex_field_like(inner, barred=True, extra_derivatives=derivatives)
    return _latex_derivative_prefix(derivatives) + rf"\bar{{{_latex_expr(inner)}}}"


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


def _print_field_like(expr: Expression, mode: PrintMode, kwargs: dict[str, Any], *, barred: bool = False) -> str:
    base = _format_child(expr[0], mode, kwargs)
    if barred and mode is PrintMode.Latex:
        base = rf"\bar{{{base}}}"
    indices = _format_list(expr[2], mode, kwargs)
    derivatives = _format_list(expr[3], mode, kwargs)
    return _derivative(_subscript(base, indices, mode), derivatives, mode)


def _print_field(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    return _print_field_like(expr, mode, kwargs)


def _print_coupling(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    return _subscript(_format_child(expr[0], mode, kwargs), _format_list(expr[1], mode, kwargs), mode)


def _print_index(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    label = expr[0]
    if label.get_type() is AtomType.Var:
        return _display_name(_local_name(label), mode)
    return _format_child(label, mode, kwargs)


def _print_dummy_index(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    if len(expr) == 1:
        return f"d{_format_child(expr[0], mode, kwargs)}"
    return _call("d", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode)


def _print_field_strength(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    label = _format_child(expr[0], mode, kwargs)
    lorentz = _format_list(expr[1], mode, kwargs)
    internal = _format_list(expr[2], mode, kwargs)
    derivatives = _format_list(expr[3], mode, kwargs)
    indices = (label, *lorentz, *internal)
    body = _subscript("F", indices, mode)
    return _derivative(body, derivatives, mode)


def _print_latex_bar(body: Expression, kwargs: dict[str, Any]) -> str:
    if _is_builtin_fn(body, "Field"):
        return _print_field_like(body, PrintMode.Latex, kwargs, barred=True)
    if _is_builtin_fn(body, "CD"):
        index = _format_child(body[0], PrintMode.Latex, kwargs)
        return _derivative(_print_latex_bar(body[1], kwargs), (index,), PrintMode.Latex)
    return rf"\bar{{{_format_child(body, PrintMode.Latex, kwargs)}}}"


def _print_bar(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    body = _format_child(expr[0], mode, kwargs)
    if mode is PrintMode.Latex:
        return _print_latex_bar(expr[0], kwargs)
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


def _is_fermion_field_endpoint(expr: Expression) -> bool:
    if _is_builtin_fn(expr, "Field"):
        return _is_builtin_symbol(expr[1], "Fermion")
    if _is_builtin_fn(expr, "CD"):
        return _is_fermion_field_endpoint(expr[1])
    return False


def _is_barred_fermion_endpoint(expr: Expression) -> bool:
    if _is_builtin_fn(expr, "Bar"):
        return _is_fermion_field_endpoint(expr[0])
    if _is_builtin_fn(expr, "CD"):
        return _is_barred_fermion_endpoint(expr[1])
    return False


def _is_closed_ncm_chain(expr: Expression) -> bool:
    if len(expr) < 2:
        return False
    return _is_barred_fermion_endpoint(expr[0]) and _is_fermion_field_endpoint(expr[len(expr) - 1])


def _print_ncm(expr: Expression, mode: PrintMode, kwargs: dict[str, Any]) -> str:
    args = tuple(_format_child(arg, mode, kwargs) for arg in _items(expr))
    if mode is PrintMode.Latex:
        chain = r"\,".join(args)
        return rf"\left({chain}\right)" if _is_closed_ncm_chain(expr) else chain
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


def _is_coupling_expr(expr: Expression) -> bool:
    if _is_builtin_fn(expr, "Coupling"):
        return True
    if _is_builtin_fn(expr, "Bar") and len(expr) == 1:
        return _is_coupling_expr(expr[0])
    if expr.get_type() is AtomType.Pow:
        return _is_coupling_expr(expr[0])
    return False


def _factor_sort_key(item: tuple[int, Expression]) -> tuple[int, int]:
    original_index, factor = item
    return (0 if _is_coupling_expr(factor) else 1, original_index)


def _negative_integer_power_parts(expr: Expression) -> tuple[Expression, int] | None:
    if expr.get_type() is not AtomType.Pow:
        return None
    exponent = _int_value(expr[1])
    if exponent is None or exponent >= 0:
        return None
    return expr[0], -exponent


def _latex_power(base: Expression, exponent: Expression | int) -> str:
    base_text = _latex_expr(base)
    if _needs_latex_power_group(base):
        base_text = rf"\left({base_text}\right)"
    exponent_text = str(exponent) if isinstance(exponent, int) else _latex_expr(exponent)
    return rf"{base_text}^{{{exponent_text}}}"


def _latex_positive_power(base: Expression, exponent: int) -> str:
    if exponent == 1:
        return _latex_expr(base)
    return _latex_power(base, exponent)


def _ordered_latex_factors(factors: list[Expression]) -> list[str]:
    ordered = [factor for _, factor in sorted(enumerate(factors), key=_factor_sort_key)]
    return [_latex_expr(factor) for factor in ordered]


def _latex_factor_list(factors: list[Expression]) -> list[str]:
    return [_latex_expr(factor) for factor in factors]


def _latex_coefficient(
    sign: str,
    numerator: str,
    denominator: str,
    denominator_factors: list[Expression],
    following_parts: list[str],
) -> str | None:
    denominator_parts = []
    if denominator != "1":
        denominator_parts.append(denominator)
    denominator_parts.extend(_latex_factor_list(denominator_factors))
    if denominator_parts:
        return sign + rf"\frac{{{numerator}}}{{{' '.join(denominator_parts)}}}"
    if numerator != "1":
        return sign + numerator
    if sign:
        return "-" if following_parts else "-1"
    return None


def _latex_mul(expr: Expression) -> str:
    raw_factors = _items(expr)
    sign = ""
    coefficient_num = "1"
    coefficient_den = "1"
    coefficient_factors: list[Expression] = []
    coefficient_denominator_factors: list[Expression] = []
    operator_factors: list[Expression] = []

    for factor in raw_factors:
        if factor.get_type() is AtomType.Num:
            number = _number_parts(factor)
            if number is None:
                coefficient_factors.append(factor)
                continue
            factor_sign, coefficient_num, coefficient_den = number
            if factor_sign:
                sign = "-"
            continue

        negative_power = _negative_integer_power_parts(factor)
        if negative_power is not None:
            base, positive_exponent = negative_power
            positive_power = base if positive_exponent == 1 else base**positive_exponent
            if _is_coupling_expr(base):
                coefficient_denominator_factors.append(positive_power)
            else:
                operator_factors.append(factor)
            continue

        if _is_coupling_expr(factor):
            coefficient_factors.append(factor)
        else:
            operator_factors.append(factor)

    coefficient_parts = _ordered_latex_factors(coefficient_factors)
    operator_parts = _latex_factor_list(operator_factors)
    following_parts = coefficient_parts + operator_parts
    coefficient = _latex_coefficient(
        sign,
        coefficient_num,
        coefficient_den,
        coefficient_denominator_factors,
        following_parts,
    )
    parts: list[str] = []
    if coefficient is not None:
        if coefficient == "-":
            if following_parts:
                following_parts[0] = "-" + following_parts[0]
            else:
                following_parts.append("-1")
        else:
            parts.append(coefficient)
    parts.extend(following_parts)
    return " ".join(parts)


def _latex_add(expr: Expression) -> str:
    out = ""
    for index, term in enumerate(_items(expr)):
        rendered = _latex_expr(term)
        if index == 0:
            out = rendered
        elif rendered.startswith("-"):
            out += "-" + rendered[1:]
        else:
            out += "+" + rendered
    return out


def _field_has_derivatives(expr: Expression) -> bool:
    return _is_builtin_fn(expr, "Field") and len(expr[3]) > 0


def _is_derivative_field_expr(expr: Expression) -> bool:
    cd_derivatives, body = _collect_cd(expr)
    if cd_derivatives and (_is_builtin_fn(body, "Field") or _is_builtin_fn(body, "Bar")):
        return True
    if _field_has_derivatives(body):
        return True
    if _is_builtin_fn(body, "Bar"):
        return _is_derivative_field_expr(body[0])
    return False


def _needs_latex_power_group(expr: Expression) -> bool:
    if _is_derivative_field_expr(expr):
        return True
    kind = expr.get_type()
    return kind is AtomType.Add or kind is AtomType.Mul


def _latex_builtin_var(expr: Expression) -> str:
    name = _local_name(expr)
    return _BUILTIN_VARIABLE_PRINT_NAMES.get("Latex", {}).get(name, _native_latex(expr))


def _latex_user_symbol(expr: Expression) -> str:
    try:
        label = expr.get_symbol_data(SymbolDataKey.LABEL.value)
    except KeyError:
        label = _local_name(expr)
    return _display_name(str(label), PrintMode.Latex)


def _latex_call(name: str, args: tuple[str, ...]) -> str:
    return _call(name, args, PrintMode.Latex)


def _latex_expr(expr: Expression) -> str:
    kind = expr.get_type()
    if kind is AtomType.Num:
        return _native_latex(expr)
    if kind is AtomType.Add:
        return _latex_add(expr)
    if kind is AtomType.Mul:
        return _latex_mul(expr)
    if kind is AtomType.Pow:
        return _latex_power(expr[0], expr[1])
    if kind is AtomType.Var:
        if expr.get_name().startswith(f"{_SYMBOL_NAMESPACE}::"):
            name = _local_name(expr)
            if name.endswith("_"):
                return name
            return _latex_builtin_var(expr)
        return _latex_user_symbol(expr)
    if kind is not AtomType.Fn:
        return _native_latex(expr)

    if not expr.get_name().startswith(f"{_SYMBOL_NAMESPACE}::"):
        return _native_latex(expr)

    name = _local_name(expr)
    if name.endswith("_"):
        return name
    args = tuple(_latex_expr(arg) for arg in _items(expr))
    if name == "List":
        return "{" + _join(args, PrintMode.Latex) + "}"
    if name in {"InternalIndices", "DerivativeIndices", "LorentzIndices", "FlavorSum", "CG", "HeavyFieldOrder", "Vector", "SU", "U1"}:
        return _latex_call("HFO" if name == "HeavyFieldOrder" else name, args)
    if name == "Field":
        return _latex_field_like(expr)
    if name == "Coupling":
        return _subscript(_latex_expr(expr[0]), tuple(_latex_expr(index) for index in _list_items(expr[1])), PrintMode.Latex)
    if name == "Index":
        return _print_index(expr, PrintMode.Latex, {})
    if name == "dummy_index":
        return _print_dummy_index(expr, PrintMode.Latex, {})
    if name == "FieldStrength":
        label = _latex_expr(expr[0])
        lorentz = tuple(_latex_expr(index) for index in _list_items(expr[1]))
        internal = tuple(_latex_expr(index) for index in _list_items(expr[2]))
        field_strength_body = _subscript("F", (label, *lorentz, *internal), PrintMode.Latex)
        return _latex_derivative_prefix(_list_items(expr[3])) + field_strength_body
    if name == "Bar":
        return _latex_bar(expr[0])
    if name == "CD":
        derivatives, cd_body = _collect_cd(expr)
        if _is_builtin_fn(cd_body, "Field"):
            return _latex_field_like(cd_body, extra_derivatives=derivatives)
        if _is_builtin_fn(cd_body, "Bar"):
            return _latex_bar(cd_body[0], extra_derivatives=derivatives)
        return _latex_derivative_prefix(derivatives) + _latex_expr(cd_body)
    if name == "Delta" and len(args) == 2:
        return rf"\delta_{{{args[0]} {args[1]}}}"
    if name == "Metric" and len(args) == 2:
        return rf"g_{{{args[0]} {args[1]}}}"
    if name in {"NCM", "DiracProduct"}:
        chain = r"\,".join(args)
        return rf"\left({chain}\right)" if _is_closed_ncm_chain(expr) else chain
    if name == "Gamma" and len(args) == 1:
        return rf"\gamma^{{{args[0]}}}"
    if name == "EOM" and len(args) == 2:
        return rf"\mathrm{{EOM}}\left[{args[0]}\right]={args[1]}"
    return _latex_call(name, args)


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
        "InternalIndices": lambda: _call("InternalIndices", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
        "DerivativeIndices": lambda: _call("DerivativeIndices", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
        "LorentzIndices": lambda: _call("LorentzIndices", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
        "Field": lambda: _print_field(expr, mode, kwargs),
        "Coupling": lambda: _print_coupling(expr, mode, kwargs),
        "Index": lambda: _print_index(expr, mode, kwargs),
        "dummy_index": lambda: _print_dummy_index(expr, mode, kwargs),
        "FieldStrength": lambda: _print_field_strength(expr, mode, kwargs),
        "Bar": lambda: _print_bar(expr, mode, kwargs),
        "CD": lambda: _print_cd(expr, mode, kwargs),
        "Delta": lambda: _print_delta(expr, mode, kwargs),
        "Metric": lambda: _print_metric(expr, mode, kwargs),
        "FlavorSum": lambda: _call("FlavorSum", tuple(_format_child(arg, mode, kwargs) for arg in _items(expr)), mode),
        "NCM": lambda: _print_ncm(expr, mode, kwargs),
        "DiracProduct": lambda: _print_ncm(expr, mode, kwargs),
        "Gamma": lambda: _print_gamma(expr, mode, kwargs),
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
    """Role tags attached to pychete-managed Symbolica symbols."""

    PROJECT = "pychete"
    LABEL = "label"
    FIELD = "field"
    COUPLING = "coupling"
    INDEX = "index"
    INDEX_TYPE = "index_type"
    GROUP = "group"
    EXTERNAL = "external"


class SymbolDataKey(StrEnum):
    """Symbolica symbol-data keys used by pychete."""

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
    CHARGES = "charges"
    DIMENSION = "dimension"
    GROUP_TYPE = "group_type"
    GROUP_COUPLING = "group_coupling"
    GROUP_FIELD = "group_field"


class SymbolStore:
    """Central store for reusable pychete Symbolica symbols.

    The package-level instance ``s`` provides expression heads such as
    ``s.Field`` and atoms such as ``s.Scalar``. Construct reusable pychete
    atoms through this store so they receive the custom pretty-printer.
    """

    namespace = _SYMBOL_NAMESPACE
    builtin_registry_names = (
        "List",
        "InternalIndices",
        "DerivativeIndices",
        "LorentzIndices",
        "Field",
        "Coupling",
        "Index",
        "dummy_index",
        "FieldStrength",
        "Bar",
        "CD",
        "Delta",
        "Metric",
        "FlavorSum",
        "NCM",
        "DiracProduct",
        "Gamma",
        "CG",
        "EOM",
        "HeavyFieldOrder",
        "FreeLag",
        "Scalar",
        "Fermion",
        "Vector",
        "Ghost",
        "AntiGhost",
        "Lorentz",
        "U1",
        "SU",
        "fund",
        "adj",
        "PR",
        "PL",
        "ConjBodyWildcard",
        "NCMLeftWildcard",
        "NCMRightWildcard",
        "NCMInnerWildcard",
        "NCMFactorWildcard",
        "NCMSplitFactorWildcard",
        "NCMSplitRestWildcard",
        "NCMGammaIndexWildcard",
        "FieldLabelWildcard",
        "FieldTypeWildcard",
        "FieldIndicesWildcard",
        "FieldDerivativesWildcard",
        "IndexLabelWildcard",
        "IndexRepresentationWildcard",
        "PowBaseWildcard",
        "PowExponentWildcard",
        "CDIndexWildcard",
        "CDBodyWildcard",
        "CouplingLabelWildcard",
        "CouplingIndicesWildcard",
        "CouplingOrderWildcard",
        "FieldStrengthLabelWildcard",
        "FieldStrengthLorentzWildcard",
        "FieldStrengthIndicesWildcard",
        "FieldStrengthDerivativesWildcard",
        "EFTExpansionParameter",
        "CDVariationParameter",
        "FunctionalVariationParameter",
    )

    def head(self, name: str, **kwargs: Any) -> Expression:
        kwargs.setdefault("print", _print_builtin)
        return _sym(f"{self.namespace}::{name}", **kwargs)

    @cached_property
    def SymbolicaConj(self) -> Expression:
        """Symbolica's native conjugation head used by ``Expression.conj``."""

        return _sym("symbolica::conj")

    def user(self, namespace: str, name: str, **kwargs: Any) -> Expression:
        kwargs.setdefault("print", _print_user_symbol)
        return _sym(f"{namespace}::{safe_symbol_name(name)}", **kwargs)

    def register_builtins(self) -> None:
        for name in self.builtin_registry_names:
            getattr(self, name)

    def builtin_symbols_by_canonical_name(self) -> dict[str, Expression]:
        self.register_builtins()
        return {canonical_string(getattr(self, name)): getattr(self, name) for name in self.builtin_registry_names}

    @cached_property
    def List(self) -> Expression:
        return self.head("List")

    @cached_property
    def InternalIndices(self) -> Expression:
        return self.head("InternalIndices")

    @cached_property
    def DerivativeIndices(self) -> Expression:
        return self.head("DerivativeIndices")

    @cached_property
    def LorentzIndices(self) -> Expression:
        return self.head("LorentzIndices")

    @cached_property
    def Field(self) -> Expression:
        return self.head("Field")

    @cached_property
    def Coupling(self) -> Expression:
        return self.head("Coupling", is_scalar=True)

    @cached_property
    def Index(self) -> Expression:
        return self.head("Index")

    @cached_property
    def dummy_index(self) -> Expression:
        return self.head("dummy_index")

    @cached_property
    def FieldStrength(self) -> Expression:
        return self.head("FieldStrength", is_scalar=True)

    @cached_property
    def Bar(self) -> Expression:
        return self.head("Bar")

    @cached_property
    def CD(self) -> Expression:
        return self.head("CD")

    @cached_property
    def Delta(self) -> Expression:
        return self.head("Delta", is_scalar=True)

    @cached_property
    def Metric(self) -> Expression:
        return self.head("Metric", is_scalar=True)

    @cached_property
    def FlavorSum(self) -> Expression:
        return self.head("FlavorSum", is_scalar=True)

    @cached_property
    def NCM(self) -> Expression:
        return self.head("NCM", is_linear=True)

    @cached_property
    def DiracProduct(self) -> Expression:
        return self.head("DiracProduct")

    @cached_property
    def Gamma(self) -> Expression:
        return self.head("Gamma")

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
    def FreeLag(self) -> Expression:
        return self.head("FreeLag")

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
    def ConjBodyWildcard(self) -> Expression:
        return self.head("conj_body_")

    @cached_property
    def NCMLeftWildcard(self) -> Expression:
        return self.head("ncm_left__")

    @cached_property
    def NCMRightWildcard(self) -> Expression:
        return self.head("ncm_right__")

    @cached_property
    def NCMInnerWildcard(self) -> Expression:
        return self.head("ncm_inner__")

    @cached_property
    def NCMFactorWildcard(self) -> Expression:
        return self.head("ncm_factor_")

    @cached_property
    def NCMSplitFactorWildcard(self) -> Expression:
        return self.head("ncm_split_factor_")

    @cached_property
    def NCMSplitRestWildcard(self) -> Expression:
        return self.head("ncm_split_rest_")

    @cached_property
    def NCMGammaIndexWildcard(self) -> Expression:
        return self.head("ncm_gamma_index_")

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
        return self.head("eft_order_parameter", is_scalar=True)

    @cached_property
    def CDVariationParameter(self) -> Expression:
        return self.head("cd_variation_parameter", is_scalar=True)

    @cached_property
    def FunctionalVariationParameter(self) -> Expression:
        return self.head("functional_variation_parameter", is_scalar=True)


s = SymbolStore()


_GREEK_ESCAPES = {
    r"\[Phi]": "phi",
    r"\[Psi]": "psi",
    r"\[CapitalPhi]": "Phi",
    r"\[CapitalPsi]": "Psi",
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
    """Return the parse-stable canonical representation of ``expr``.

    Canonical strings include namespaces and disable pychete's pretty printer,
    making them suitable for JSON checkpoints and exact test fixtures.
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
        show_namespaces=True,
        include_attributes=False,
        custom_print_mode={_CUSTOM_PRINT_MODE_KEY: _CANONICAL_PRINT_MODE},
    )


def display_string(expr: Expression, mode: PrintMode = PrintMode.Symbolica) -> str:
    """Return a human-readable formatted string for ``expr``."""

    if mode is PrintMode.Latex:
        return latex_string(expr)

    return expr.format(
        max_terms=None,
        mode=mode,
        max_line_length=None,
        color_top_level_sum=False,
        color_builtin_symbols=False,
        bracket_level_colors=None,
        print_ring=False,
        multiplication_operator="*",
        num_exp_as_superscript=False,
    )


def latex_string(expr: Expression) -> str:
    """Return a human-readable LaTeX string for ``expr``."""

    return _latex_expr(expr)


def expression_from_canonical(text: str) -> Expression:
    s.register_builtins()
    return Expression.parse(text)


def symbol_data(expr: Expression, key: SymbolDataKey, default: Any = None) -> Any:
    try:
        return expr.get_symbol_data(key.value)
    except KeyError:
        return default
