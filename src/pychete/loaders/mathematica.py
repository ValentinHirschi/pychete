"""Supported-subset Matchete/Wolfram input helpers.

This module is intentionally not a general Wolfram Language parser. It handles
the declarative subset pychete currently needs for simple Matchete-style model
assets and saved validation-result snippets: model declarations such as
``ParentModel``, ``ParameterDefault``, ``DefineFlavorIndex``,
``DefineGaugeGroup``, ``DefineGlobalGroup``, ``DefineRepresentation``,
``DefineCG``, ``DefineField``, and ``DefineCoupling``, plus the limited
expression syntax accepted by ``parse_matchete_expression``.

Complex Mathematica models should be loaded by Wolfram/Matchete itself in a
development-only helper script, then exported as pychete-owned serialized state
or Python fixture files. Runtime pychete code and normal pytest runs should
consume those committed fixtures instead of growing this Python parser toward
full Wolfram syntax support.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import factorial
from pathlib import Path
from typing import TypeAlias

from symbolica import Expression
from symbolica.core import AtomType, ParseMode

from ..backends.vacuum_integrals import canonize_loop_function, loop_function
from ..expr import args, as_int, list_expr, product_expr, sum_expr
from ..symbols import SymbolRole, safe_symbol_name, s
from ..theory import Theory
from ..theory_metadata import CouplingSelfConjugate, FieldChirality, FieldRole, FreeLagConvention


_COMMENT_RE = re.compile(r"\(\*.*?\*\)", re.DOTALL)
_NCM_CHAIN_RE = re.compile(
    r"(Bar\[[A-Za-z][A-Za-z0-9_]*\[\]\]|[A-Za-z][A-Za-z0-9_]*\[\])"
    r"\s*\*\*\s*"
    r"(PR|PL)"
    r"\s*\*\*\s*"
    r"([A-Za-z][A-Za-z0-9_]*\[\])"
)


@dataclass(frozen=True)
class _LocalFunction:
    parameters: tuple[str, ...]
    body: str


_ModuleEnv: TypeAlias = dict[str, Expression | _LocalFunction]


def _strip_comments(text: str) -> str:
    return _COMMENT_RE.sub("", text)


def _preprocess_names(text: str) -> str:
    for source, replacement in {
        r"\[CapitalPhi]": "Phi",
        r"\[CapitalPsi]": "Psi",
        r"\[Alpha]": "alpha",
        r"\[Beta]": "beta",
        r"\[Epsilon]": "epsilon",
        r"\[Kappa]": "kappa",
        r"\[Lambda]": "lambda",
        r"\[Mu]": "mu",
        r"\[Psi]": "psi",
        r"\[Phi]": "phi",
        r"\[Tau]": "tau",
    }.items():
        text = text.replace(source, replacement)
    return text


def _parse_string(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    raise NotImplementedError(f"Unsupported string literal: {raw}")


def _split_top_level(text: str, separator: str) -> list[str]:
    parts: list[str] = []
    start = 0
    square = curly = paren = assoc = 0
    in_string = False
    i = 0
    while i < len(text):
        if not in_string and text.startswith("<|", i):
            assoc += 1
            i += 2
            continue
        if not in_string and text.startswith("|>", i):
            assoc -= 1
            i += 2
            continue
        char = text[i]
        if char == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
            i += 1
            continue
        if in_string:
            i += 1
            continue
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
        elif char == separator and square == 0 and curly == 0 and paren == 0 and assoc == 0:
            part = text[start:i].strip()
            if part:
                parts.append(part)
            start = i + 1
        i += 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _split_statements(text: str) -> list[str]:
    statements: list[str] = []
    start = 0
    square = curly = paren = 0
    in_string = False
    i = 0
    while i < len(text):
        char = text[i]
        if char == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
            i += 1
            continue
        if in_string:
            i += 1
            continue
        if char == "[":
            square += 1
        elif char == "]":
            square -= 1
            if square == 0 and curly == 0 and paren == 0:
                next_i = i + 1
                while next_i < len(text) and text[next_i].isspace():
                    next_i += 1
                if next_i >= len(text) or text[next_i] not in ";,+-*/^)]}":
                    statement = text[start : i + 1].strip()
                    if statement:
                        statements.append(statement)
                    start = next_i
                    i = next_i
                    continue
        elif char == "{":
            curly += 1
        elif char == "}":
            curly -= 1
        elif char == "(":
            paren += 1
        elif char == ")":
            paren -= 1
        elif char == ";" and square == 0 and curly == 0 and paren == 0:
            statement = text[start:i].strip()
            if statement:
                statements.append(statement)
            start = i + 1
        i += 1
    tail = text[start:].strip()
    if tail:
        statements.append(tail)
    return statements


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


def _parse_int(raw: str) -> int:
    return int(_preprocess_names(raw).strip())


def _parse_int_list(raw: str) -> tuple[int, ...]:
    value = _preprocess_names(raw).strip()
    if value.startswith("{") and value.endswith("}"):
        return tuple(_parse_int(part) for part in _split_top_level(value[1:-1], ",") if part.strip())
    return (_parse_int(value),)


def _parse_pattern_name(raw: str) -> str:
    value = _preprocess_names(raw).strip()
    if value.endswith("_"):
        value = value[:-1]
    return _clean_name(value)


def _parse_coupling_self_conjugate(raw: str) -> CouplingSelfConjugate:
    value = _preprocess_names(raw).strip()
    if value.startswith("{") and value.endswith("}"):
        return _parse_int_list(value)
    return _parse_bool(value)


def _parse_diagonal_coupling(raw: str) -> bool | tuple[bool, ...] | None:
    value = _preprocess_names(raw).strip()
    if value == "Default":
        return None
    if value.startswith("{") and value.endswith("}"):
        return tuple(_parse_bool(part) for part in _split_top_level(value[1:-1], ",") if part.strip())
    return _parse_bool(value)


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


def _parse_chirality(raw: str) -> FieldChirality:
    return FieldChirality.from_user(_clean_name(raw))


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
    if name == "Ghost":
        return s.Ghost
    if name == "AntiGhost":
        return s.AntiGhost
    raise NotImplementedError(f"Unsupported field type: {raw}")


def _field_role_from_options(type_expr: Expression, opts: dict[str, str]) -> FieldRole:
    selected = FieldRole.from_type(type_expr)
    if "GoldstoneBoson" in opts and _parse_bool(opts["GoldstoneBoson"]):
        selected = FieldRole.GOLDSTONE
    if "BackgroundField" in opts and _parse_bool(opts["BackgroundField"]):
        if selected is not FieldRole.PHYSICAL:
            raise NotImplementedError("BackgroundField cannot be combined with ghost or Goldstone field metadata")
        selected = FieldRole.BACKGROUND
    return selected


def _field_propagating_from_options(role: FieldRole, opts: dict[str, str]) -> bool | None:
    if "Propagating" in opts:
        return _parse_bool(opts["Propagating"])
    if "NonPropagating" in opts:
        return not _parse_bool(opts["NonPropagating"])
    if "BackgroundField" in opts and _parse_bool(opts["BackgroundField"]):
        return False
    if role is FieldRole.BACKGROUND:
        return False
    return None


def _group_type(raw: str) -> Expression:
    normalized = _preprocess_names(raw).strip()
    su_apply = re.fullmatch(r"SU\s*@\s*(\d+)", normalized)
    if su_apply:
        return s.SU(Expression.num(int(su_apply.group(1))))
    name = _clean_name(normalized)
    if name == "U1":
        return s.U1
    if name.startswith("SU"):
        return s.SU
    raise NotImplementedError(f"Unsupported gauge group type: {raw}")


def _parse_representation_name(raw: str) -> tuple[str, str]:
    normalized = _preprocess_names(raw).strip()
    call_match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_]*)\[(.+)\]", normalized, re.DOTALL)
    if call_match:
        return _clean_name(call_match.group(1)), _clean_name(call_match.group(2))
    apply_match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_]*)\s*@\s*(.+)", normalized, re.DOTALL)
    if apply_match:
        return _clean_name(apply_match.group(1)), _clean_name(apply_match.group(2))
    raise NotImplementedError(f"Unsupported representation name: {raw}")


def _parse_module_function_definition(statement: str) -> tuple[str, _LocalFunction] | None:
    if ":=" not in statement:
        return None
    lhs, body = statement.split(":=", 1)
    try:
        head, raw_args = _parse_call(lhs.strip())
    except NotImplementedError:
        return None
    return _clean_name(head), _LocalFunction(tuple(_parse_pattern_name(arg) for arg in raw_args), body.strip())


def _rewrite_prefix_apply(expr: str, head: str) -> str:
    prefix = f"{head}@"
    while prefix in expr:
        start = expr.rfind(prefix)
        arg_start = start + len(prefix)
        while arg_start < len(expr) and expr[arg_start].isspace():
            arg_start += 1
        if arg_start >= len(expr):
            break
        name_match = re.match(r"[A-Za-z][A-Za-z0-9_]*", expr[arg_start:])
        if not name_match:
            break
        arg_end = arg_start + name_match.end()
        if arg_end < len(expr) and expr[arg_end] == "[":
            depth = 0
            for j in range(arg_end, len(expr)):
                if expr[j] == "[":
                    depth += 1
                elif expr[j] == "]":
                    depth -= 1
                    if depth == 0:
                        arg_end = j + 1
                        break
        replacement = f"{head}[{expr[arg_start:arg_end]}]"
        expr = expr[:start] + replacement + expr[arg_end:]
    return expr


def _rewrite_integer_factorials(expr: str) -> str:
    return re.sub(r"(?<![A-Za-z])(\d+)!", lambda match: str(factorial(int(match.group(1)))), expr)


def _matching_left_bracket(expr: str, close_pos: int) -> int:
    depth = 0
    for i in range(close_pos, -1, -1):
        if expr[i] == "]":
            depth += 1
        elif expr[i] == "[":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"Unbalanced brackets in expression: {expr}")


def _matching_right_bracket(expr: str, open_pos: int) -> int:
    depth = 0
    for i in range(open_pos, len(expr)):
        if expr[i] == "[":
            depth += 1
        elif expr[i] == "]":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"Unbalanced brackets in expression: {expr}")


def _identifier_start(expr: str, end_pos: int) -> int:
    i = end_pos
    while i > 0 and (expr[i - 1].isalnum() or expr[i - 1] == "_"):
        i -= 1
    return i


def _identifier_end(expr: str, start_pos: int) -> int:
    i = start_pos
    while i < len(expr) and (expr[i].isalnum() or expr[i] == "_"):
        i += 1
    return i


def _left_operand_span(expr: str, operator_pos: int) -> tuple[int, int]:
    end = operator_pos
    while end > 0 and expr[end - 1].isspace():
        end -= 1
    if end == 0:
        raise ValueError(f"Missing left operand for ** in expression: {expr}")
    if expr[end - 1] == "]":
        open_pos = _matching_left_bracket(expr, end - 1)
        return (_identifier_start(expr, open_pos), end)
    return (_identifier_start(expr, end), end)


def _right_operand_span(expr: str, operator_pos: int) -> tuple[int, int]:
    start = operator_pos + 2
    while start < len(expr) and expr[start].isspace():
        start += 1
    name_end = _identifier_end(expr, start)
    if name_end == start:
        raise ValueError(f"Missing right operand for ** in expression: {expr}")
    if name_end < len(expr) and expr[name_end] == "[":
        return (start, _matching_right_bracket(expr, name_end) + 1)
    return (start, name_end)


def _rewrite_ncm(expr: str) -> str:
    while "**" in expr:
        operator_pos = expr.find("**")
        chain_start, left_end = _left_operand_span(expr, operator_pos)
        operands = [expr[chain_start:left_end].strip()]
        chain_end = left_end
        next_operator = operator_pos
        while next_operator != -1:
            right_start, right_end = _right_operand_span(expr, next_operator)
            operands.append(expr[right_start:right_end].strip())
            chain_end = right_end
            probe = chain_end
            while probe < len(expr) and expr[probe].isspace():
                probe += 1
            next_operator = probe if expr.startswith("**", probe) else -1
        expr = expr[:chain_start] + f"NCM[{', '.join(operands)}]" + expr[chain_end:]
    return expr


def _rewrite_lists(expr: str) -> str:
    return expr.replace("{", "List[").replace("}", "]")


def _rewrite_implicit_products(expr: str) -> str:
    expr = re.sub(r"\]\s*(?=[A-Za-z])", "]*", expr)
    expr = re.sub(r"(?<=[0-9])\s+(?=[A-Za-z])", "*", expr)
    return expr


def _normalize_expression(text: str) -> str:
    expr = _preprocess_names(text.strip())
    expr = re.sub(r"\s*//\s*RelabelIndices\s*$", "", expr)
    expr = expr.replace(r"\[CenterDot]", "**")
    expr = _rewrite_prefix_apply(expr, "CConj")
    expr = _rewrite_prefix_apply(expr, "Bar")
    expr = _rewrite_integer_factorials(expr)
    expr = _rewrite_lists(expr)
    expr = _NCM_CHAIN_RE.sub(r"NCM[\1, \2, \3]", expr)
    expr = _rewrite_ncm(expr)
    expr = _rewrite_implicit_products(expr)
    return expr


def _is_parsed_head(expr: Expression, name: str) -> bool:
    return expr.get_type() is AtomType.Fn and _plain_name(expr) == name


def _matchete_list_items(expr: Expression, theory: Theory, env: _ModuleEnv) -> tuple[Expression, ...]:
    if not _is_parsed_head(expr, "List"):
        raise ValueError(f"Expected Mathematica List expression, got {expr.format_plain()}")
    return tuple(_convert_expression(expr[i], theory, env) for i in range(len(expr)))


def _matchete_field_type(expr: Expression, theory: Theory, env: _ModuleEnv) -> Expression:
    if expr.get_type() is AtomType.Var:
        name = _plain_name(expr)
        if name == "Scalar":
            return s.Scalar
        if name == "Fermion":
            return s.Fermion
        if name == "Ghost":
            return s.Ghost
        if name == "AntiGhost":
            return s.AntiGhost
    return _convert_expression(expr, theory, env)


def _matchete_registered_label(expr: Expression, theory: Theory, registry: str) -> Expression:
    if expr.get_type() is not AtomType.Var:
        return _convert_expression(expr, theory, {})
    name = _clean_name(_plain_name(expr))
    if registry == "field" and name in theory.fields:
        return theory.fields[name].label
    if registry == "coupling" and name in theory.couplings:
        return theory.couplings[name].label
    return theory.define_external(name).label


def _matchete_index_label(expr: Expression, theory: Theory, env: _ModuleEnv) -> Expression:
    if expr.get_type() is AtomType.Var:
        name = _plain_name(expr)
        dummy = re.fullmatch(r"d\$\$(\d+)", name)
        if dummy:
            return s.dummy_index(int(dummy.group(1)))
        return theory.symbol(_clean_name(name), role=SymbolRole.INDEX)
    return _convert_expression(expr, theory, env)


def _matchete_projector(expr: Expression, theory: Theory, env: _ModuleEnv) -> Expression:
    if len(expr) != 1:
        raise NotImplementedError(f"Unsupported Proj expression: {expr.format_plain()}")
    value = _convert_expression(expr[0], theory, env)
    value_int = as_int(value)
    if value_int == 1:
        return s.PR
    if value_int == -1:
        return s.PL
    return s.Proj(value)


def _matchete_group_name(expr: Expression, theory: Theory) -> str:
    if expr.get_type() is AtomType.Var:
        name = _plain_name(expr)
        if name in theory.groups:
            return name
    raise NotImplementedError(f"Unsupported CG group label: {expr.format_plain()}")


def _matchete_builtin_cg_label(expr: Expression, theory: Theory, env: _ModuleEnv) -> Expression | None:
    if expr.get_type() is not AtomType.Fn:
        return None
    name = _plain_name(expr)
    if name in {"eps", "fStruct", "dSym"} and len(expr) == 1:
        group = _matchete_group_name(expr[0], theory)
        return theory._builtin_cg_tensor_label(name, group)
    if name in {"gen", "del"} and len(expr) == 1:
        representation = _convert_expression(expr[0], theory, env)
        definition = theory.representation_definition(representation)
        return theory._builtin_cg_tensor_label(name, definition.group, representation)
    return None


def _matchete_cg(expr: Expression, theory: Theory, env: _ModuleEnv) -> Expression:
    if len(expr) != 2:
        raise NotImplementedError(f"Unsupported CG expression: {expr.format_plain()}")
    label = _matchete_builtin_cg_label(expr[0], theory, env)
    if label is None:
        label = _convert_expression(expr[0], theory, env)
    return s.CG(label, list_expr(*_matchete_list_items(expr[1], theory, env)))


def _plain_name(expr: Expression) -> str:
    kind = expr.get_type()
    if kind is not AtomType.Var and kind is not AtomType.Fn:
        raise ValueError("Expression does not have a symbol name")
    return expr.get_name().split("::")[-1]


def _convert_expression(expr: Expression, theory: Theory, env: _ModuleEnv) -> Expression:
    kind = expr.get_type()
    if kind is AtomType.Num:
        return expr
    if kind is AtomType.Var:
        name = _plain_name(expr)
        if name in env:
            value = env[name]
            if isinstance(value, _LocalFunction):
                raise ValueError(f"Local function {name} was used without arguments")
            return value
        if name == "PR":
            return s.PR
        if name == "PL":
            return s.PL
        if name == "fund":
            return s.fund
        if name == "adj":
            return s.adj
        if name == "Flavor":
            return theory.define_flavor_index().symbol
        if name in theory.groups:
            return theory.symbol(name, role=SymbolRole.GROUP)
        if name in theory.index_types:
            return theory.index_types[name].symbol
        if name in theory.representation_labels:
            return theory.representation_labels[name]
        if name in theory.fields:
            return theory.field_handle(name)()
        if name in theory.couplings:
            return theory.coupling_handle(name)()
        if name in theory.cg_tensors:
            return theory.cg_tensor_handle(name)()
        return theory.define_external(name)()
    if kind is AtomType.Add:
        return sum_expr(_convert_expression(child, theory, env) for child in args(expr))
    if kind is AtomType.Mul:
        return product_expr(_convert_expression(child, theory, env) for child in args(expr))
    if kind is AtomType.Pow:
        return _convert_expression(expr[0], theory, env) ** _convert_expression(expr[1], theory, env)
    if kind is AtomType.Fn:
        name = _plain_name(expr)
        local_value = env.get(name)
        if isinstance(local_value, _LocalFunction):
            local_function = local_value
            if len(expr) != len(local_function.parameters):
                raise NotImplementedError(
                    f"Local function {name} expects {len(local_function.parameters)} arguments, got {len(expr)}"
                )
            call_env: _ModuleEnv = dict(env)
            for parameter, argument in zip(local_function.parameters, args(expr), strict=True):
                call_env[parameter] = _convert_expression(argument, theory, env)
            return _eval_expression(local_function.body, theory, call_env)
        if name == "List":
            return list_expr(*(_convert_expression(child, theory, env) for child in args(expr)))
        if name == "Bar":
            return s.Bar(_convert_expression(expr[0], theory, env))
        if name == "CConj":
            return s.CConj(_convert_expression(expr[0], theory, env))
        if name == "NCM":
            return s.NCM(*(_convert_expression(child, theory, env) for child in args(expr)))
        if name == "Field":
            if len(expr) != 4:
                raise NotImplementedError(f"Unsupported Field expression: {expr.format_plain()}")
            return s.Field(
                _matchete_registered_label(expr[0], theory, "field"),
                _matchete_field_type(expr[1], theory, env),
                list_expr(*_matchete_list_items(expr[2], theory, env)),
                list_expr(*_matchete_list_items(expr[3], theory, env)),
            )
        if name == "Coupling":
            if len(expr) != 3:
                raise NotImplementedError(f"Unsupported Coupling expression: {expr.format_plain()}")
            return s.Coupling(
                _matchete_registered_label(expr[0], theory, "coupling"),
                list_expr(*_matchete_list_items(expr[1], theory, env)),
                _convert_expression(expr[2], theory, env),
            )
        if name == "Index":
            if len(expr) != 2:
                raise NotImplementedError(f"Unsupported Index expression: {expr.format_plain()}")
            return s.Index(
                _matchete_index_label(expr[0], theory, env),
                _convert_expression(expr[1], theory, env),
            )
        if name == "FieldStrength":
            if len(expr) != 4:
                raise NotImplementedError(f"Unsupported FieldStrength expression: {expr.format_plain()}")
            return s.FieldStrength(
                _matchete_registered_label(expr[0], theory, "field"),
                list_expr(*_matchete_list_items(expr[1], theory, env)),
                list_expr(*_matchete_list_items(expr[2], theory, env)),
                list_expr(*_matchete_list_items(expr[3], theory, env)),
            )
        if name == "DiracProduct":
            return s.DiracProduct(*(_convert_expression(child, theory, env) for child in args(expr)))
        if name == "GammaM":
            return s.Gamma(*(_convert_expression(child, theory, env) for child in args(expr)))
        if name == "Proj":
            return _matchete_projector(expr, theory, env)
        if name == "CG":
            return _matchete_cg(expr, theory, env)
        if name == "LF":
            if len(expr) != 2:
                raise NotImplementedError(f"Unsupported LF expression: {expr.format_plain()}")
            return canonize_loop_function(
                loop_function(
                    _matchete_list_items(expr[0], theory, env),
                    _matchete_list_items(expr[1], theory, env),
                )
            )
        if name == "log":
            if len(expr) != 1:
                raise NotImplementedError(f"Unsupported Log expression: {expr.format_plain()}")
            return _convert_expression(expr[0], theory, env).log()
        if name == "sqrt":
            if len(expr) != 1:
                raise NotImplementedError(f"Unsupported Sqrt expression: {expr.format_plain()}")
            return _convert_expression(expr[0], theory, env).sqrt()
        if name == "PlusHc":
            body = _convert_expression(expr[0], theory, env)
            return body + s.Bar(body)
        if name == "FreeLag":
            names = [_clean_name(_plain_name(child)) for child in args(expr)]
            return theory.free_lag(*names, convention=FreeLagConvention.MATCHETE)
        symmetry_heads = {
            "SymmetricIndices": s.SymmetricIndices,
            "AntisymmetricIndices": s.AntisymmetricIndices,
            "SymmetricPermutation": s.SymmetricPermutation,
            "AntisymmetricPermutation": s.AntisymmetricPermutation,
            "SymmetryOverride": s.SymmetryOverride,
        }
        if name in symmetry_heads:
            return symmetry_heads[name](*(_convert_expression(child, theory, env) for child in args(expr)))
        if name in theory.groups:
            return theory.symbol(name, role=SymbolRole.GROUP)(*(_convert_expression(child, theory, env) for child in args(expr)))
        if name in theory.cg_tensors:
            return theory.cg_tensor_handle(name)(*(_convert_expression(child, theory, env) for child in args(expr)))
        if name in theory.fields:
            return theory.field_handle(name)(*(_convert_expression(child, theory, env) for child in args(expr)))
        if name in theory.couplings:
            return theory.coupling_handle(name)(*(_convert_expression(child, theory, env) for child in args(expr)))
        return theory.define_external(name)(*(_convert_expression(child, theory, env) for child in args(expr)))
    raise NotImplementedError(f"Unsupported parsed expression: {expr.format_plain()}")


def _eval_expression(text: str, theory: Theory, env: _ModuleEnv) -> Expression:
    normalized = _normalize_expression(text)
    parsed = Expression.parse(normalized, mode=ParseMode.Mathematica)
    return _convert_expression(parsed, theory, env).expand()


def parse_matchete_expression(text: str, theory: Theory) -> Expression:
    """Parse the supported saved-result expression subset into pychete heads."""

    return _eval_expression(text, theory, {})


def _eval_expression_list(text: str, theory: Theory) -> list[Expression]:
    normalized = _preprocess_names(text.strip())
    if normalized.startswith("{") and normalized.endswith("}"):
        items = _split_top_level(normalized[1:-1], ",")
    else:
        items = [normalized]
    return [_eval_expression(item, theory, {}) for item in items if item.strip()]


def _eval_module(args_raw: list[str], theory: Theory) -> Expression:
    if len(args_raw) != 2:
        raise NotImplementedError("Only Module[{locals}, body] is supported")
    env: _ModuleEnv = {}
    body = args_raw[1]
    statements = _split_top_level(body, ";")
    result = Expression.num(0)
    for statement in statements:
        if ":=" in statement:
            definition = _parse_module_function_definition(statement)
            if definition is None:
                continue
            name, local_function = definition
            env[name] = local_function
            continue
        if "=" in statement:
            name, value = statement.split("=", 1)
            env[_clean_name(name)] = _eval_expression(value, theory, env)
        else:
            result = _eval_expression(statement, theory, env)
    return result


def _parse_dimension(raw: str, parameters: dict[str, int]) -> int | None:
    value = _clean_name(raw)
    if value in parameters:
        return parameters[value]
    try:
        return int(value)
    except ValueError:
        return None


def _load_matchete_model_into(
    model_path: Path,
    theory: Theory,
    expressions: dict[str, Expression],
    *,
    include_lagrangian: bool,
    parameters: dict[str, int],
    visited: set[Path],
) -> None:
    resolved = model_path.resolve()
    if resolved in visited:
        return
    visited.add(resolved)
    text = _preprocess_names(_strip_comments(model_path.read_text(encoding="utf-8")))

    for statement in _split_statements(text):
        if not statement:
            continue
        head, raw_args = _parse_call(statement)
        if head == "ParentModel":
            if len(raw_args) != 1:
                raise NotImplementedError(f"Unsupported ParentModel: {statement}")
            parent_path = model_path.parent / f"{_parse_string(raw_args[0])}.m"
            _load_matchete_model_into(
                parent_path,
                theory,
                expressions,
                include_lagrangian=False,
                parameters=parameters,
                visited=visited,
            )
        elif head == "ParameterDefault":
            for raw_arg in raw_args:
                if "->" not in raw_arg:
                    raise NotImplementedError(f"Unsupported ParameterDefault: {statement}")
                key, value = raw_arg.split("->", 1)
                parameters[_clean_name(key)] = _parse_int(value)
        elif head == "DefineFlavorIndex":
            if len(raw_args) < 2:
                raise NotImplementedError(f"Unsupported DefineFlavorIndex: {statement}")
            theory.define_flavor_index(_clean_name(raw_args[0]), _parse_dimension(raw_args[1], parameters))
        elif head == "DefineGaugeGroup":
            if len(raw_args) < 4:
                raise NotImplementedError(f"Unsupported DefineGaugeGroup: {statement}")
            theory.define_gauge_group(
                _clean_name(raw_args[0]),
                _group_type(raw_args[1]),
                _clean_name(raw_args[2]),
                _clean_name(raw_args[3]),
            )
        elif head == "DefineGlobalGroup":
            if len(raw_args) < 2:
                raise NotImplementedError(f"Unsupported DefineGlobalGroup: {statement}")
            theory.define_global_group(
                _clean_name(raw_args[0]),
                _group_type(raw_args[1]),
            )
        elif head == "DefineRepresentation":
            if len(raw_args) < 3:
                raise NotImplementedError(f"Unsupported DefineRepresentation: {statement}")
            parsed_group, label = _parse_representation_name(raw_args[0])
            declared_group = _clean_name(raw_args[1])
            if parsed_group != declared_group:
                raise NotImplementedError(f"Representation group mismatch in {statement}")
            theory.define_representation(
                declared_group,
                label,
                dynkin=_eval_expression_list(raw_args[2], theory),
            )
        elif head == "DefineCG":
            if len(raw_args) < 3:
                raise NotImplementedError(f"Unsupported DefineCG: {statement}")
            theory.define_cg_tensor(
                _clean_name(raw_args[0]),
                _eval_expression_list(raw_args[1], theory),
                source=_preprocess_names(raw_args[2].strip()),
            )
        elif head == "DefineField":
            if len(raw_args) < 2:
                raise NotImplementedError(f"Unsupported DefineField: {statement}")
            opts = _options(raw_args[2:])
            type_expr = _field_type(raw_args[1])
            field_role = _field_role_from_options(type_expr, opts)
            theory.define_field(
                _clean_name(raw_args[0]),
                type_expr,
                indices=_eval_expression_list(opts["Indices"], theory) if "Indices" in opts else (),
                charges=_eval_expression_list(opts["Charges"], theory) if "Charges" in opts else (),
                chirality=_parse_chirality(opts["Chiral"]) if "Chiral" in opts else FieldChirality.NONE,
                field_role=field_role,
                propagating=_field_propagating_from_options(field_role, opts),
                zero_mode=_parse_bool(opts["ZeroMode"]) if "ZeroMode" in opts else False,
                self_conjugate=_parse_bool(opts["SelfConjugate"]) if "SelfConjugate" in opts else False,
                mass=_parse_mass(opts["Mass"]) if "Mass" in opts else None,
            )
        elif head == "DefineCoupling":
            if not raw_args:
                raise NotImplementedError(f"Unsupported DefineCoupling: {statement}")
            opts = _options(raw_args[1:])
            labels_raw = _preprocess_names(raw_args[0].strip())
            labels = _split_top_level(labels_raw[1:-1], ",") if labels_raw.startswith("{") and labels_raw.endswith("}") else [labels_raw]
            for label in labels:
                theory.define_coupling(
                    _clean_name(label),
                    indices=_eval_expression_list(opts["Indices"], theory) if "Indices" in opts else (),
                    eft_order=_parse_int(opts["EFTOrder"]) if "EFTOrder" in opts else 0,
                    self_conjugate=_parse_coupling_self_conjugate(opts["SelfConjugate"]) if "SelfConjugate" in opts else False,
                    symmetries=_eval_expression_list(opts["Symmetries"], theory) if "Symmetries" in opts else (),
                    diagonal=_parse_diagonal_coupling(opts["DiagonalCoupling"]) if "DiagonalCoupling" in opts else None,
                    thermal_power_counting=_parse_int(opts["ThermalPowerCounting"]) if "ThermalPowerCounting" in opts else 1,
                    unitary=_parse_bool(opts["Unitary"]) if "Unitary" in opts else False,
                )
        elif head == "Module":
            if not include_lagrangian:
                continue
            lagrangian = _eval_module(raw_args, theory)
            theory._validate_registered_expression(lagrangian)
            if "lagrangian" in expressions:
                expressions["parent_lagrangian"] = expressions["lagrangian"]
                lagrangian = expressions["lagrangian"] + lagrangian
            expressions["lagrangian"] = lagrangian
        else:
            raise NotImplementedError(f"Unsupported Matchete construct: {head}")


def load_matchete_model(
    path: str | Path,
    *,
    theory_name: str | None = None,
    include_lagrangian: bool = True,
) -> tuple[Theory, dict[str, Expression]]:
    """Load the supported Matchete model subset into a pychete theory.

    This loader is for declarative model fixtures whose syntax stays within the
    explicitly supported subset documented at module scope. More complicated
    Mathematica models should be loaded by Matchete in Wolfram Language and
    exported into pychete-owned fixtures before normal tests or users consume
    them.

    Set ``include_lagrangian=False`` to load only model metadata. This is used
    for parent-model validation assets whose full Lagrangian syntax is broader
    than the current direct Wolfram-subset parser.
    """

    model_path = Path(path)
    theory = Theory(theory_name or model_path.stem)
    expressions: dict[str, Expression] = {}
    _load_matchete_model_into(
        model_path,
        theory,
        expressions,
        include_lagrangian=include_lagrangian,
        parameters={},
        visited=set(),
    )
    return theory, expressions
