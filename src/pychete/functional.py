from __future__ import annotations

from symbolica import Expression
from symbolica.core import AtomType

from .expr import (
    args,
    atom_type,
    bar_field_inner,
    collect_bar_field_atoms,
    collect_bar_field_atoms_for_label,
    collect_field_atoms,
    collect_field_atoms_for_label,
    expr_key,
    factors,
    field_derivatives,
    field_label,
    field_type,
    field_with_derivatives,
    is_head,
    list_expr,
    pow_parts,
    product_expr,
    replace_many,
    sum_expr,
    terms,
)
from .symbols import canonical_string, s
from .theory import FieldDefinition, FieldHandle, Theory


def apply_cd(indices: tuple[Expression, ...] | list[Expression], expr: Expression) -> Expression:
    out = expr
    for index in indices:
        out = _single_cd(index, out).expand()
    return out


def _single_cd(index: Expression, expr: Expression) -> Expression:
    kind = atom_type(expr)
    if kind is AtomType.Num or kind is AtomType.Var:
        return s.zero
    if kind is AtomType.Add:
        return sum_expr(_single_cd(index, term) for term in terms(expr))
    if kind is AtomType.Mul:
        facs = list(factors(expr))
        pieces = []
        for i, factor in enumerate(facs):
            df = _single_cd(index, factor)
            if canonical_string(df.expand()) != "0":
                pieces.append(product_expr([*facs[:i], df, *facs[i + 1 :]]))
        return sum_expr(pieces)
    parts = pow_parts(expr)
    if parts is not None:
        base, exponent = parts
        n = exponent.to_atom_tree().head
        if n is None:
            return s.zero
        try:
            n_int = int(n)
        except ValueError:
            return s.zero
        if n_int == 0:
            return s.zero
        return n_int * (base ** (n_int - 1)) * _single_cd(index, base)
    if is_head(expr, s.Field):
        return field_with_derivatives(expr, (*field_derivatives(expr), index))
    if is_head(expr, s.Bar):
        inner_derivative = _single_cd(index, expr[0])
        if canonical_string(inner_derivative.expand()) == "0":
            return s.zero
        return s.Bar(inner_derivative)
    if is_head(expr, s.CD):
        return s.CD(expr[0], _single_cd(index, expr[1]))
    return s.zero


def _variation_atoms(lagrangian: Expression) -> tuple[Expression, ...]:
    return (*collect_bar_field_atoms(lagrangian), *collect_field_atoms(lagrangian))


def partial_functional_derivative(lagrangian: Expression, target_field: Expression) -> Expression:
    fields = _variation_atoms(lagrangian)
    replacements: list[tuple[Expression, Expression]] = []
    inverse: list[tuple[Expression, Expression]] = []
    target_var: Expression | None = None
    for i, field in enumerate(fields):
        tmp = s.head(f"fd_tmp_{i}")
        replacements.append((field, tmp))
        inverse.append((tmp, field))
        if expr_key(field) == expr_key(target_field):
            target_var = tmp
    if target_var is None:
        return s.zero
    encoded = replace_many(lagrangian, replacements)
    differentiated = encoded.derivative(target_var)
    return replace_many(differentiated, inverse).expand()


def derive_eom(
    theory: Theory,
    lagrangian: Expression,
    field: FieldHandle | FieldDefinition | str,
    *,
    eft_order: int = 6,
    variation: str = "auto",
) -> Expression:
    if isinstance(field, str):
        definition = theory.fields[field]
    elif isinstance(field, FieldHandle):
        definition = field.definition
    else:
        definition = field

    if variation == "auto":
        variation = "field" if definition.self_conjugate else "bar"
    if variation not in {"field", "bar"}:
        raise ValueError("variation must be 'auto', 'field', or 'bar'")

    if variation == "bar":
        atoms = collect_bar_field_atoms_for_label(lagrangian, definition.label)
        derivative_sets = {field_derivatives(bar_field_inner(atom)) for atom in atoms}
    else:
        atoms = collect_field_atoms_for_label(lagrangian, definition.label)
        derivative_sets = {field_derivatives(atom) for atom in atoms}
    derivative_sets.add(())

    residual = s.zero
    base = definition.expr()
    for derivatives in sorted(derivative_sets, key=lambda d: (len(d), tuple(canonical_string(x) for x in d))):
        target = field_with_derivatives(base, derivatives)
        if variation == "bar":
            target = s.Bar(target)
        partial = partial_functional_derivative(lagrangian, target)
        if len(derivatives) == 0:
            residual = residual + partial
        else:
            contribution = apply_cd(tuple(reversed(derivatives)), partial)
            residual = residual + ((-1) ** len(derivatives)) * contribution

    result = residual.expand()
    theory.analysis.eoms[definition.name] = result
    return result


def eom_expression(theory: Theory, lagrangian: Expression, field: FieldHandle | FieldDefinition | str, *, eft_order: int = 6) -> Expression:
    definition = theory.fields[field] if isinstance(field, str) else field.definition if isinstance(field, FieldHandle) else field
    return s.EOM(definition.expr(), derive_eom(theory, lagrangian, definition, eft_order=eft_order))
