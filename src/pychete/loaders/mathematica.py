from __future__ import annotations

import re
from pathlib import Path

from symbolica import Expression
from symbolica.core import AtomType, ParseMode

from ..expr import args, product_expr, sum_expr
from ..spinor import bar_expr, ncm_expr
from ..symbols import SymbolRole, safe_symbol_name, s
from ..theory import Theory


_COMMENT_RE = re.compile(r"\(\*.*?\*\)", re.DOTALL)
_BAR_APPLY_RE = re.compile(r"Bar@([A-Za-z][A-Za-z0-9_]*\[\])")
_NCM_CHAIN_RE = re.compile(
    r"(Bar\[[A-Za-z][A-Za-z0-9_]*\[\]\]|[A-Za-z][A-Za-z0-9_]*\[\])"
    r"\s*\*\*\s*"
    r"(PR|PL)"
    r"\s*\*\*\s*"
    r"([A-Za-z][A-Za-z0-9_]*\[\])"
)


def _strip_comments(text: str) -> str:
    return _COMMENT_RE.sub("", text)


def _preprocess_names(text: str) -> str:
    for source, replacement in {
        r"\[CapitalPhi]": "Phi",
        r"\[CapitalPsi]": "Psi",
        r"\[Psi]": "psi",
        r"\[Phi]": "phi",
    }.items():
        text = text.replace(source, replacement)
    return text


def _split_top_level(text: str, separator: str) -> list[str]:
    parts: list[str] = []
    start = 0
    square = curly = paren = 0
    for i, char in enumerate(text):
        if char == "[":
            square += 1
        elif char == "]":
            square -= 1
        elif char == "{":
            curly += 1
        elif char == "}":
            curly -= 1
        elif char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif char == separator and square == 0 and curly == 0 and paren == 0:
            part = text[start:i].strip()
            if part:
                parts.append(part)
            start = i + 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_call(statement: str) -> tuple[str, list[str]]:
    statement = statement.strip()
    match = re.match(r"^([A-Za-z][A-Za-z0-9_]*)\[(.*)\]$", statement, re.DOTALL)
    if not match:
        raise NotImplementedError(f"Unsupported Mathematica statement: {statement}")
    return match.group(1), _split_top_level(match.group(2), ",")


def _clean_name(raw: str) -> str:
    return safe_symbol_name(_preprocess_names(raw).strip())


def _parse_bool(raw: str) -> bool:
    value = raw.strip()
    if value == "True":
        return True
    if value == "False":
        return False
    raise NotImplementedError(f"Unsupported boolean option value: {raw}")


def _parse_mass(raw: str) -> int | tuple[str, str]:
    value = _preprocess_names(raw).strip()
    if value == "0":
        return 0
    if value.startswith("{") and value.endswith("}"):
        parts = _split_top_level(value[1:-1], ",")
        if len(parts) < 2:
            raise NotImplementedError(f"Unsupported Mass option: {raw}")
        return (_clean_name(parts[0]), _clean_name(parts[1]))
    raise NotImplementedError(f"Unsupported Mass option: {raw}")


def _parse_charges(raw: str, theory: Theory) -> tuple[Expression, ...]:
    value = _preprocess_names(raw).strip()
    if not (value.startswith("{") and value.endswith("}")):
        raise NotImplementedError(f"Unsupported Charges option: {raw}")
    charges: list[Expression] = []
    for item in _split_top_level(value[1:-1], ","):
        match = re.match(r"^([A-Za-z][A-Za-z0-9_]*)\[(.+)\]$", item.strip())
        if not match:
            raise NotImplementedError(f"Unsupported charge assignment: {item}")
        group = _clean_name(match.group(1))
        charge_text = match.group(2).strip()
        try:
            charge_value: int | Expression = int(charge_text)
        except ValueError:
            charge_value = Expression.parse(charge_text, mode=ParseMode.Mathematica)
        charges.append(theory.gauge_charge(group, charge_value).expr)
    return tuple(charges)


def _options(raw_parts: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in raw_parts:
        if "->" not in part:
            raise NotImplementedError(f"Expected option rule, got {part}")
        key, value = part.split("->", 1)
        out[_clean_name(key)] = value.strip()
    return out


def _field_type(raw: str) -> Expression:
    name = _clean_name(raw)
    if name == "Scalar":
        return s.Scalar
    if name == "Fermion":
        return s.Fermion
    raise NotImplementedError(f"Unsupported field type: {raw}")


def _group_type(raw: str) -> Expression:
    name = _clean_name(raw)
    if name == "U1":
        return s.U1
    if name.startswith("SU"):
        return s.SU
    raise NotImplementedError(f"Unsupported gauge group type: {raw}")


def _normalize_expression(text: str) -> str:
    expr = _preprocess_names(text.strip())
    expr = re.sub(r"\s*//\s*RelabelIndices\s*$", "", expr)
    expr = _BAR_APPLY_RE.sub(r"Bar[\1]", expr)
    expr = _NCM_CHAIN_RE.sub(r"NCM[\1, \2, \3]", expr)
    return expr


def _plain_name(expr: Expression) -> str:
    kind = expr.get_type()
    if kind is not AtomType.Var and kind is not AtomType.Fn:
        raise ValueError("Expression does not have a symbol name")
    return expr.get_name().split("::")[-1]


def _convert_expression(expr: Expression, theory: Theory, env: dict[str, Expression]) -> Expression:
    kind = expr.get_type()
    if kind is AtomType.Num:
        return expr
    if kind is AtomType.Var:
        name = _plain_name(expr)
        if name in env:
            return env[name]
        if name == "PR":
            return s.PR
        if name == "PL":
            return s.PL
        if name in theory.fields:
            return theory.field_handle(name)()
        if name in theory.couplings:
            return theory.coupling_handle(name)()
        return theory.symbol(name, role=SymbolRole.EXTERNAL)
    if kind is AtomType.Add:
        return sum_expr(_convert_expression(child, theory, env) for child in args(expr))
    if kind is AtomType.Mul:
        return product_expr(_convert_expression(child, theory, env) for child in args(expr))
    if kind is AtomType.Pow:
        return _convert_expression(expr[0], theory, env) ** _convert_expression(expr[1], theory, env)
    if kind is AtomType.Fn:
        name = _plain_name(expr)
        if name == "Bar":
            return bar_expr(_convert_expression(expr[0], theory, env))
        if name == "NCM":
            return ncm_expr(*(_convert_expression(child, theory, env) for child in args(expr)))
        if name == "PlusHc":
            body = _convert_expression(expr[0], theory, env)
            return body + bar_expr(body)
        if name == "FreeLag":
            names = [_clean_name(_plain_name(child)) for child in args(expr)]
            return theory.free_lag(*names)
        if name in theory.fields:
            return theory.field_handle(name)(*(_convert_expression(child, theory, env) for child in args(expr)))
        if name in theory.couplings:
            return theory.coupling_handle(name)(*(_convert_expression(child, theory, env) for child in args(expr)))
    raise NotImplementedError(f"Unsupported parsed expression: {expr.format_plain()}")


def _eval_expression(text: str, theory: Theory, env: dict[str, Expression]) -> Expression:
    normalized = _normalize_expression(text)
    parsed = Expression.parse(normalized, mode=ParseMode.Mathematica)
    return _convert_expression(parsed, theory, env).expand()


def _eval_module(args_raw: list[str], theory: Theory) -> Expression:
    if len(args_raw) != 2:
        raise NotImplementedError("Only Module[{locals}, body] is supported")
    env: dict[str, Expression] = {}
    body = args_raw[1]
    statements = _split_top_level(body, ";")
    result = Expression.num(0)
    for statement in statements:
        if "=" in statement:
            name, value = statement.split("=", 1)
            env[_clean_name(name)] = _eval_expression(value, theory, env)
        else:
            result = _eval_expression(statement, theory, env)
    return result


def load_matchete_model(path: str | Path, *, theory_name: str | None = None) -> tuple[Theory, dict[str, Expression]]:
    model_path = Path(path)
    text = _preprocess_names(_strip_comments(model_path.read_text(encoding="utf-8")))
    theory = Theory(theory_name or model_path.stem)
    expressions: dict[str, Expression] = {}

    for statement in _split_top_level(text, ";"):
        if not statement:
            continue
        head, raw_args = _parse_call(statement)
        if head == "DefineGaugeGroup":
            if len(raw_args) != 4:
                raise NotImplementedError(f"Unsupported DefineGaugeGroup: {statement}")
            theory.define_gauge_group(
                _clean_name(raw_args[0]),
                _group_type(raw_args[1]),
                _clean_name(raw_args[2]),
                _clean_name(raw_args[3]),
            )
        elif head == "DefineField":
            if len(raw_args) < 2:
                raise NotImplementedError(f"Unsupported DefineField: {statement}")
            opts = _options(raw_args[2:])
            theory.define_field(
                _clean_name(raw_args[0]),
                _field_type(raw_args[1]),
                charges=_parse_charges(opts["Charges"], theory) if "Charges" in opts else (),
                self_conjugate=_parse_bool(opts["SelfConjugate"]) if "SelfConjugate" in opts else False,
                mass=_parse_mass(opts["Mass"]) if "Mass" in opts else None,
            )
        elif head == "DefineCoupling":
            if len(raw_args) != 1:
                raise NotImplementedError(f"Unsupported DefineCoupling: {statement}")
            theory.define_coupling(_clean_name(raw_args[0]))
        elif head == "Module":
            lagrangian = _eval_module(raw_args, theory)
            theory._validate_registered_expression(lagrangian)
            expressions["lagrangian"] = lagrangian
        else:
            raise NotImplementedError(f"Unsupported Matchete construct: {head}")

    return theory, expressions
