from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from symbolica import Expression

from .backends import idenso
from .expr import is_zero
from .functional import (
    abelian_vector_eom_field_redefinition_delta,
    eom_replacement_rules_for_expression,
    expose_scalar_derivative_commutator_bilinears,
    expose_vector_field_strength_divergences_as_formal_eom,
    expand_cd_operators,
    matchete_vector_eom_scalar_bilinear_normal_form,
    normalize_conjugate_scalar_field_slots,
    scalar_derivative_green_normal_form,
    scalar_derivative_green_normal_form_by_operator_class,
    simplify_trivial_cd_operators,
    systematic_scalar_eom_field_redefinition_delta,
)
from .noncommutative import scalarize_commutative_ncm_chains
from .theory import Theory

_WILSON_LINE_SCALAR_EOM_CLOSURE_BYTE_LIMIT = 50_000


def _apply_on_shell_eom_reduction_to_expression(
    theory: Theory,
    expr: Expression,
    *,
    eom_lagrangian: Expression,
    fields: Sequence[Any] | None = None,
    eft_order: int = 6,
    min_derivative_order: int = 2,
    strict: bool = False,
    abelian_vector_field_redefinition: bool = False,
    repeat: bool = False,
) -> tuple[Expression, int, Expression]:
    """Apply on-shell EOM rules and the optional Abelian vector companion."""

    eom_rules = eom_replacement_rules_for_expression(
        theory,
        eom_lagrangian,
        expr,
        fields=fields,
        eft_order=eft_order,
        min_derivative_order=min_derivative_order,
        strict=strict,
    )
    reduced = expr
    if eom_rules:
        reduced = reduced.replace_multiple(eom_rules, repeat=repeat).expand()
    vector_field_redefinition_delta = Expression.num(0)
    if abelian_vector_field_redefinition:
        vector_field_redefinition_delta = abelian_vector_eom_field_redefinition_delta(
            theory,
            eom_lagrangian,
            expr,
            fields=fields,
            strict=strict,
        )
        if not is_zero(vector_field_redefinition_delta):
            reduced = (reduced + vector_field_redefinition_delta).expand()
    return reduced, len(eom_rules), vector_field_redefinition_delta


def _apply_wilson_line_scalar_green_normal_form(theory: Theory, expr: Expression) -> Expression:
    out = scalar_derivative_green_normal_form(theory, expr)
    out = theory.expand_covariant_derivative_commutators(out, include_gauge_coupling=False)
    out = expand_cd_operators(out)
    out = simplify_trivial_cd_operators(out)
    return expose_scalar_derivative_commutator_bilinears(
        theory,
        out,
        include_gauge_coupling=False,
        expand_commutators=True,
    )


def _apply_wilson_line_post_integral_scalar_commutator_bilinears(
    theory: Theory,
    expr: Expression,
    *,
    eom_lagrangian: Expression | None = None,
    expose_scalar_eom_terms: bool = False,
) -> Expression:
    """Expose scalar derivative commutator bilinears after finite evaluation."""

    if expose_scalar_eom_terms and eom_lagrangian is None:
        raise ValueError("eom_lagrangian must be provided when expose_scalar_eom_terms=True")
    out = normalize_conjugate_scalar_field_slots(theory, expr)
    if expose_scalar_eom_terms:
        if out.get_byte_size() <= _WILSON_LINE_SCALAR_EOM_CLOSURE_BYTE_LIMIT:
            max_basis_terms = 256
            max_identities = 512
            max_rounds = 4
        else:
            max_basis_terms = 1536
            max_identities = 4096
            max_rounds = 1
        out = scalar_derivative_green_normal_form_by_operator_class(
            theory,
            out,
            include_eom=True,
            eom_lagrangian=eom_lagrangian,
            eom_standard_form_only=True,
            identity_generation="operator_basis",
            max_basis_terms=max_basis_terms,
            max_identities=max_identities,
            max_rounds=max_rounds,
        )
    out = theory.expand_covariant_derivative_commutators(out, include_gauge_coupling=False)
    out = expand_cd_operators(out)
    out = simplify_trivial_cd_operators(out)
    out = expose_scalar_derivative_commutator_bilinears(
        theory,
        out,
        include_gauge_coupling=False,
        expand_commutators=True,
    )
    if expose_scalar_eom_terms:
        out = expose_vector_field_strength_divergences_as_formal_eom(theory, out)
        out = matchete_vector_eom_scalar_bilinear_normal_form(theory, out)
    out = idenso.simplify_pychete_field_strength_group_algebra(theory, out)
    return scalarize_commutative_ncm_chains(out)


def _apply_wilson_line_scalar_eom_field_redefinition(
    theory: Theory,
    expr: Expression,
    *,
    source_lagrangian: Expression,
    max_order: int,
    fields: Sequence[Any] | None = None,
    strict: bool = False,
) -> tuple[Expression, Expression]:
    """Apply the scalar ``PerformSystematicFieldRedefs`` consumer to ``expr``."""

    delta = systematic_scalar_eom_field_redefinition_delta(
        theory,
        source_lagrangian,
        eom_terms_lagrangian=expr,
        max_order=max_order,
        fields=fields,
        strict=strict,
    )
    if is_zero(delta):
        return expr, delta
    return (expr + delta).expand(), delta


__all__ = [
    "_apply_on_shell_eom_reduction_to_expression",
    "_apply_wilson_line_post_integral_scalar_commutator_bilinears",
    "_apply_wilson_line_scalar_eom_field_redefinition",
    "_apply_wilson_line_scalar_green_normal_form",
]
