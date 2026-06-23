from __future__ import annotations

from symbolica import Expression
from symbolica.core import AtomType

from .expr import as_int, atom_type, expr_key, factors, field_derivatives, field_label, field_type, is_head, pow_parts, sum_expr, terms
from .symbols import canonical_string, s
from .theory import Theory


def type_dimension(type_expr: Expression) -> int | float:
    if canonical_string(type_expr) == canonical_string(s.Fermion):
        return 1.5
    return 1


def _coupling_order(expr: Expression) -> int:
    order = as_int(expr[2])
    if order is None:
        raise ValueError(f"Coupling EFT order is not an integer: {canonical_string(expr)}")
    return order


def operator_dimension(expr: Expression, theory: Theory | None = None, *, heavy_field_dimension: bool = True) -> float:
    kind = atom_type(expr)
    if kind is AtomType.Num:
        return 0
    if kind is AtomType.Var:
        return 0
    if kind is AtomType.Add:
        return min(operator_dimension(t, theory, heavy_field_dimension=heavy_field_dimension) for t in terms(expr))
    if kind is AtomType.Mul:
        return sum(operator_dimension(f, theory, heavy_field_dimension=heavy_field_dimension) for f in factors(expr))
    parts = pow_parts(expr)
    if parts is not None:
        base, exponent = parts
        n = as_int(exponent)
        if n is None:
            return 0
        return n * operator_dimension(base, theory, heavy_field_dimension=heavy_field_dimension)
    if is_head(expr, s.Coupling):
        return _coupling_order(expr)
    if is_head(expr, s.Field):
        dim = len(field_derivatives(expr)) + type_dimension(field_type(expr))
        if heavy_field_dimension and theory is not None:
            label = expr_key(field_label(expr))
            for definition in theory.fields.values():
                if expr_key(definition.label) == label and definition.heavy:
                    dim += 1
                    break
        return dim
    if is_head(expr, s.FieldStrength):
        return len(expr[3]) + 2
    if is_head(expr, s.Bar):
        return operator_dimension(expr[0], theory, heavy_field_dimension=heavy_field_dimension)
    return 0


def series_eft(
    expr: Expression,
    theory: Theory | None = None,
    *,
    eft_order: int | tuple[int],
    heavy_field_dimension: bool = True,
) -> Expression:
    expanded = expr.expand()
    exact = isinstance(eft_order, tuple)
    order = eft_order[0] if exact else eft_order
    kept: list[Expression] = []
    for term in terms(expanded):
        dim = operator_dimension(term, theory, heavy_field_dimension=heavy_field_dimension)
        if (dim == order) if exact else (dim <= order):
            kept.append(term)
    return sum_expr(kept).expand()
