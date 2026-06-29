from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from symbolica import Expression

from .expr import as_int, factors, is_head, pow_parts, product_expr, sum_expr, terms
from .functional import expand_cd_operators, normalize_conjugate_scalar_field_slots, simplify_trivial_cd_operators
from .logging import get_logger, progress
from .matching_options import VakintIntegralStage
from .noncommutative import normalize_ncm_chains, scalarize_commutative_ncm_chains
from .symbols import SymbolRole, s
from .theory import CovariantDerivativeCommutatorMode, Theory
from .wilson_line_eom import _apply_wilson_line_post_integral_scalar_commutator_bilinears

_LOGGER = get_logger("matching.integrals")


def postprocess_wilson_line_numerator(
    numerator: Expression,
    *,
    close_fermion_loop: bool = False,
) -> Expression:
    from .backends import idenso

    normalized = normalize_ncm_chains(numerator)
    if close_fermion_loop:
        traced = idenso.trace_pychete_closed_dirac_chains(normalized)
        if (
            bool(traced == normalized)
            and not contains_registered_fermion_field(normalized)
            and not contains_pychete_dirac_factor(normalized)
        ):
            traced = (Expression.num(4) * traced).expand()
        normalized = traced
    simplified = idenso.simplify_pychete_dirac_algebra(normalized)
    simplified = idenso.simplify_pychete_loop_momentum_metrics(simplified)
    simplified = idenso.simplify_pychete_field_strength_metrics(simplified)
    return scalarize_commutative_ncm_chains(simplified)


def postprocess_wilson_line_tensor_reduced_expression(
    theory: Theory,
    expr: Expression,
    *,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    expand_covariant_derivative_commutators: bool,
    simplify_pychete_color_algebra: bool,
    covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
    expose_scalar_derivative_commutator_bilinears_option: bool = False,
    epsilon: Expression | None = None,
) -> Expression:
    """Normalize tensor-reduced Wilson-line expressions before scalar evaluation."""

    from .backends import idenso
    from .loop_integration import contract_lorentz_metric_traces

    out = idenso.simplify_pychete_field_derivative_metrics(expr)
    out = restore_theory_owned_generated_lorentz_indices(theory, out)
    out = normalize_conjugate_scalar_field_slots(theory, out)
    if expose_scalar_derivative_commutator_bilinears_option:
        out = _apply_wilson_line_post_integral_scalar_commutator_bilinears(theory, out)
    if emit_covariant_derivative_commutators or expand_covariant_derivative_commutators:
        max_cycles = max(1, min(8, emit_covariant_derivative_commutator_passes + 1))
        for _ in range(max_cycles):
            updated = out
            if emit_covariant_derivative_commutators:
                updated = theory.emit_covariant_derivative_commutators(
                    updated,
                    max_passes=emit_covariant_derivative_commutator_passes,
                    mode=covariant_derivative_commutator_mode,
                )
            if expand_covariant_derivative_commutators:
                updated = theory.expand_covariant_derivative_commutators(
                    updated,
                    include_gauge_coupling=False,
                )
                updated = expand_cd_operators(updated)
            updated = simplify_trivial_cd_operators(updated)
            if bool(updated == out):
                out = updated
                break
            out = updated
    out = simplify_trivial_cd_operators(out)
    if expose_scalar_derivative_commutator_bilinears_option:
        out = _apply_wilson_line_post_integral_scalar_commutator_bilinears(theory, out)
    out = idenso.simplify_pychete_field_strength_group_algebra(theory, out)
    if simplify_pychete_color_algebra:
        out = idenso.simplify_pychete_color_algebra(theory, out)
    out = contract_lorentz_metric_traces(out, epsilon=epsilon)
    return scalarize_commutative_ncm_chains(out)


def postprocess_pre_wilson_line_tensor_reduced_expression(
    theory: Theory,
    expr: Expression,
    *,
    max_wilson_derivative_order: int,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    expand_covariant_derivative_commutators: bool,
    simplify_pychete_color_algebra: bool,
    covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
    expose_scalar_derivative_commutator_bilinears_option: bool = False,
    epsilon: Expression | None = None,
) -> Expression:
    """Normalize tensor-reduced expressions before lowering formal Wilson terms."""

    from .wilson_lines import contract_wilson_term_derivative_metrics, expand_wilson_terms

    out = restore_theory_owned_generated_lorentz_indices(theory, expr)
    out = contract_wilson_term_derivative_metrics(
        out,
        max_derivative_order=max_wilson_derivative_order,
    )
    out = expand_wilson_terms(
        theory,
        out,
        max_derivative_order=max_wilson_derivative_order,
    )
    return postprocess_wilson_line_tensor_reduced_expression(
        theory,
        out,
        emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
        emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
        expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
        simplify_pychete_color_algebra=simplify_pychete_color_algebra,
        covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
        expose_scalar_derivative_commutator_bilinears_option=(
            expose_scalar_derivative_commutator_bilinears_option
        ),
        epsilon=epsilon,
    )


def postprocess_wilson_line_vakint_stage_expression(
    theory: Theory,
    expr: Expression,
    *,
    stage: VakintIntegralStage,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    expand_covariant_derivative_commutators: bool,
    simplify_pychete_color_algebra: bool,
    covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode = "inversions",
    expose_scalar_derivative_commutator_bilinears: bool = False,
    epsilon: Expression | None = None,
) -> Expression:
    """Normalize Wilson-line vakint tensor-reduced or evaluated expressions."""

    if stage in (VakintIntegralStage.RAW, VakintIntegralStage.CANONICAL):
        return expr
    return postprocess_wilson_line_tensor_reduced_expression(
        theory,
        expr,
        emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
        emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
        expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
        simplify_pychete_color_algebra=simplify_pychete_color_algebra,
        covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
        expose_scalar_derivative_commutator_bilinears_option=(
            expose_scalar_derivative_commutator_bilinears
        ),
        epsilon=epsilon,
    )


def restore_theory_owned_generated_lorentz_indices(theory: Theory, expr: Expression) -> Expression:
    label = s.head("generated_lorentz_label_")
    index = s.Index(label, s.Lorentz)

    def replace_index(match: dict[Expression, Expression]) -> Expression:
        replacement = theory_owned_generated_lorentz_index(theory, match[label])
        return index.replace_wildcards(match) if replacement is None else replacement

    return expr.replace(index, replace_index, rhs_cache_size=0).expand()


def theory_owned_generated_lorentz_index(theory: Theory, label: Expression) -> Expression | None:
    try:
        full_name = label.get_name()
    except TypeError:
        return None
    if not full_name.startswith("pychete::"):
        return None
    local_name = full_name.rsplit("::", maxsplit=1)[-1]
    for prefix in ("wilson_line_", "cde_"):
        if local_name.startswith(prefix):
            return theory.index(theory.symbol(local_name, role=SymbolRole.INDEX), s.Lorentz)
    for prefix in ("index_wilson_line_", "index_cde_"):
        if local_name.startswith(prefix):
            label_name = local_name.removeprefix("index_")
            return theory.index(theory.symbol(label_name, role=SymbolRole.INDEX), s.Lorentz)
    return None


def contains_registered_fermion_field(expr: Expression) -> bool:
    label = s.head("fermion_field_label_")
    indices = s.head("fermion_field_indices_")
    derivatives = s.head("fermion_field_derivatives_")
    field = s.Field(label, s.Fermion, indices, derivatives)
    label_is_field = label.req_tag(SymbolRole.FIELD.value)
    return bool(tuple(expr.match(field, label_is_field))) or bool(tuple(expr.match(s.Bar(field), label_is_field)))


def contains_pychete_dirac_factor(expr: Expression) -> bool:
    index = s.head("dirac_factor_index_")
    return bool(expr.contains(s.PR) or expr.contains(s.PL) or tuple(expr.match(s.Gamma(index))))


def named_vakint_supertraces(
    contributions: Iterable[Any],
    *,
    include_light: bool = True,
    stage: VakintIntegralStage | str = VakintIntegralStage.RAW,
    short_form: bool | None = None,
    engine: Any | None = None,
) -> dict[str, Expression]:
    selected = VakintIntegralStage.from_user(stage)
    return {
        contribution.name: vakint_expression_at_stage(
            contribution.vakint_integral_expression(include_light=include_light),
            theory=contribution.theory,
            stage=selected,
            short_form=short_form,
            engine=engine,
        )
        for contribution in contributions
    }


def named_internal_supertraces(
    contributions: Iterable[Any],
    *,
    include_light: bool = True,
    tensor_reduce: bool = True,
    tensor_reduce_engine: Any | None = None,
    epsilon: Expression | None = None,
    mu_r_squared: Expression | None = None,
    combine_terms: bool = False,
) -> dict[str, Expression]:
    from .backends import vakint, vacuum_integrals

    out: dict[str, Expression] = {}
    for contribution in contributions:
        raw = contribution.vakint_integral_expression(include_light=include_light)
        if tensor_reduce:
            raw = vakint.tensor_reduce(raw, engine=tensor_reduce_engine)
            raw = vakint.decode_pychete_namespace(contribution.theory, raw)
        out[contribution.name] = vacuum_integrals.evaluate_one_loop_vakint_expression(
            raw,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
            combine_terms=combine_terms,
        )
    return out


def finite_named_supertraces(
    supertraces: Mapping[str, Expression],
    names: Iterable[str],
    *,
    epsilon: Expression | None = None,
) -> dict[str, Expression]:
    from .backends import vakint

    return {
        name: vakint.finite_part(supertraces[name], epsilon=epsilon)
        for name in names
        if name in supertraces
    }


def vakint_expression_at_stage(
    expr: Expression,
    *,
    theory: Theory | None = None,
    stage: VakintIntegralStage,
    short_form: bool | None = None,
    engine: Any | None = None,
) -> Expression:
    if stage is VakintIntegralStage.RAW:
        return expr
    from .backends import vakint

    if stage is VakintIntegralStage.CANONICAL:
        result = vakint.to_canonical(expr, short_form=short_form, engine=engine)
    elif stage is VakintIntegralStage.TENSOR_REDUCED:
        result = vakint.tensor_reduce(expr, engine=engine)
    else:
        result = vakint.evaluate(expr, engine=engine)
    if theory is None:
        return result
    return vakint.decode_pychete_namespace(theory, result)


def vakint_integral_terms_at_stage(
    raw_terms: Sequence[Expression],
    *,
    theory: Theory,
    stage: VakintIntegralStage,
    short_form: bool | None = None,
    engine: Any | None = None,
    label: str,
) -> Expression:
    if stage is VakintIntegralStage.RAW:
        return sum_expr(raw_terms).expand()
    if not raw_terms:
        return Expression.num(0)

    from .backends import vakint

    staged_terms: list[Expression] = []
    with progress(
        f"{stage.value.replace('_', '-')} {len(raw_terms)} {label} vakint integrals termwise",
        logger=_LOGGER,
    ):
        for raw in raw_terms:
            if stage is VakintIntegralStage.CANONICAL:
                staged = vakint.to_canonical(raw, short_form=short_form, engine=engine)
            elif stage is VakintIntegralStage.TENSOR_REDUCED:
                staged = vakint.tensor_reduce(raw, engine=engine)
            else:
                staged = vakint.evaluate(raw, engine=engine)
            staged_terms.append(vakint.decode_pychete_namespace(theory, staged))
    return sum_expr(staged_terms).expand()


def wilson_line_internal_integral_sum_from_terms(
    theory: Theory,
    terms_in: Sequence[Any],
    *,
    tensor_reduce: bool,
    tensor_reduce_engine: Any | None,
    tensor_reduce_before_wilson_expand: bool,
    max_wilson_derivative_order: int,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode,
    expand_covariant_derivative_commutators: bool,
    simplify_pychete_color_algebra: bool,
    expose_scalar_derivative_commutator_bilinears: bool,
    epsilon: Expression | None,
    mu_r_squared: Expression | None,
    combine_terms: bool,
) -> Expression:
    evaluated_terms = wilson_line_internal_evaluated_terms_from_terms(
        theory,
        terms_in,
        tensor_reduce=tensor_reduce,
        tensor_reduce_engine=tensor_reduce_engine,
        tensor_reduce_before_wilson_expand=tensor_reduce_before_wilson_expand,
        max_wilson_derivative_order=max_wilson_derivative_order,
        emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
        emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
        covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
        expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
        simplify_pychete_color_algebra=simplify_pychete_color_algebra,
        expose_scalar_derivative_commutator_bilinears=expose_scalar_derivative_commutator_bilinears,
        epsilon=epsilon,
        mu_r_squared=mu_r_squared,
    )
    return sum_wilson_line_internal_terms(evaluated_terms, combine_terms=combine_terms)


def wilson_line_internal_evaluated_terms_from_terms(
    theory: Theory,
    terms_in: Sequence[Any],
    *,
    tensor_reduce: bool,
    tensor_reduce_engine: Any | None,
    tensor_reduce_before_wilson_expand: bool,
    max_wilson_derivative_order: int,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode,
    expand_covariant_derivative_commutators: bool,
    simplify_pychete_color_algebra: bool,
    expose_scalar_derivative_commutator_bilinears: bool,
    epsilon: Expression | None,
    mu_r_squared: Expression | None,
) -> tuple[Expression, ...]:
    grouped_terms = {"selected": tuple(terms_in)}
    evaluated_by_entry = wilson_line_internal_evaluated_terms_by_entry_from_terms(
        theory,
        grouped_terms,
        tensor_reduce=tensor_reduce,
        tensor_reduce_engine=tensor_reduce_engine,
        tensor_reduce_before_wilson_expand=tensor_reduce_before_wilson_expand,
        max_wilson_derivative_order=max_wilson_derivative_order,
        emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
        emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
        covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
        expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
        simplify_pychete_color_algebra=simplify_pychete_color_algebra,
        expose_scalar_derivative_commutator_bilinears=expose_scalar_derivative_commutator_bilinears,
        epsilon=epsilon,
        mu_r_squared=mu_r_squared,
    )
    return evaluated_by_entry["selected"]


def wilson_line_internal_evaluated_terms_by_entry_from_terms(
    theory: Theory,
    grouped_terms: Mapping[str, Sequence[Any]],
    *,
    tensor_reduce: bool,
    tensor_reduce_engine: Any | None,
    tensor_reduce_before_wilson_expand: bool,
    max_wilson_derivative_order: int,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode,
    expand_covariant_derivative_commutators: bool,
    simplify_pychete_color_algebra: bool,
    expose_scalar_derivative_commutator_bilinears: bool,
    epsilon: Expression | None,
    mu_r_squared: Expression | None,
) -> dict[str, tuple[Expression, ...]]:
    from .backends import vakint, vacuum_integrals

    total_terms = sum(len(terms) for terms in grouped_terms.values())
    evaluated_by_entry: dict[str, tuple[Expression, ...]] = {}
    with progress(
        f"evaluating {total_terms} Wilson-line scalar vacuum integrals termwise",
        logger=_LOGGER,
    ):
        for entry_label, entry_terms in grouped_terms.items():
            evaluated_terms: list[Expression] = []
            for term in entry_terms:
                use_pre_wilson_numerator = (
                    tensor_reduce
                    and tensor_reduce_before_wilson_expand
                    and term.pre_wilson_numerator is not None
                )
                if use_pre_wilson_numerator:
                    raw = wilson_line_matchete_order_pre_wilson_integral_expression(
                        theory,
                        term,
                        max_wilson_derivative_order=max_wilson_derivative_order,
                        emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                        emit_covariant_derivative_commutator_passes=(
                            emit_covariant_derivative_commutator_passes
                        ),
                        covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                        expand_covariant_derivative_commutators=(
                            expand_covariant_derivative_commutators
                        ),
                        simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                        expose_scalar_derivative_commutator_bilinears=False,
                        epsilon=epsilon,
                    )
                else:
                    raw = term.vakint_integral_expression()
                if tensor_reduce and not use_pre_wilson_numerator:
                    raw = vakint.tensor_reduce(raw, engine=tensor_reduce_engine)
                    raw = vakint.decode_pychete_namespace(theory, raw)
                    raw = postprocess_wilson_line_tensor_reduced_expression(
                        theory,
                        raw,
                        emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
                        emit_covariant_derivative_commutator_passes=(
                            emit_covariant_derivative_commutator_passes
                        ),
                        covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
                        expand_covariant_derivative_commutators=(
                            expand_covariant_derivative_commutators
                        ),
                        simplify_pychete_color_algebra=simplify_pychete_color_algebra,
                        expose_scalar_derivative_commutator_bilinears_option=False,
                        epsilon=epsilon,
                    )
                evaluated_terms.append(
                    vacuum_integrals.evaluate_one_loop_vakint_expression(
                        raw,
                        epsilon=epsilon,
                        mu_r_squared=mu_r_squared,
                        combine_terms=False,
                    )
                )
            evaluated_by_entry[entry_label] = tuple(evaluated_terms)
    return evaluated_by_entry


def wilson_line_matchete_order_pre_wilson_integral_expression(
    theory: Theory,
    term: Any,
    *,
    max_wilson_derivative_order: int,
    emit_covariant_derivative_commutators: bool,
    emit_covariant_derivative_commutator_passes: int,
    covariant_derivative_commutator_mode: CovariantDerivativeCommutatorMode,
    expand_covariant_derivative_commutators: bool,
    simplify_pychete_color_algebra: bool,
    expose_scalar_derivative_commutator_bilinears: bool,
    epsilon: Expression | None,
) -> Expression:
    """Lower a formal WilsonTerm numerator in Matchete's tensor-stage order."""

    from .backends import vakint
    from .loop_integration import (
        collect_loop_momenta_to_symmetric_lorentz,
        contract_lorentz_metrics,
        evaluate_symmetric_lorentz_indices,
    )
    from .wilson_lines import expand_wilson_terms, remove_symmetry_vanishing_wilson_terms

    if term.pre_wilson_numerator is None:
        return term.vakint_integral_expression()
    numerator = scalarize_commutative_ncm_chains(term.pre_wilson_numerator)
    numerator = collect_loop_momenta_to_symmetric_lorentz(
        numerator,
        include_massless_denominator_shift=True,
        loop_momentum_squared=s.LoopMomentumSquared,
    )
    numerator = remove_symmetry_vanishing_wilson_terms(numerator)
    numerator = evaluate_symmetric_lorentz_indices(
        numerator,
        epsilon=epsilon,
        evaluate_gamma=True,
        contract_metrics=False,
    )
    numerator = expand_wilson_terms(
        theory,
        numerator,
        max_derivative_order=max_wilson_derivative_order,
    )
    numerator = contract_lorentz_metrics(numerator)
    numerator = postprocess_wilson_line_tensor_reduced_expression(
        theory,
        numerator,
        emit_covariant_derivative_commutators=emit_covariant_derivative_commutators,
        emit_covariant_derivative_commutator_passes=emit_covariant_derivative_commutator_passes,
        covariant_derivative_commutator_mode=covariant_derivative_commutator_mode,
        expand_covariant_derivative_commutators=expand_covariant_derivative_commutators,
        simplify_pychete_color_algebra=simplify_pychete_color_algebra,
        expose_scalar_derivative_commutator_bilinears_option=(
            expose_scalar_derivative_commutator_bilinears
        ),
        epsilon=epsilon,
    )
    return wilson_line_matchete_order_numerator_to_vakint_integral(
        numerator,
        term.mass_squareds,
        term.propagator_powers,
        vakint_module=vakint,
    )


def wilson_line_matchete_order_numerator_to_vakint_integral(
    numerator: Expression,
    mass_squareds: Sequence[Expression],
    propagator_powers: Sequence[int],
    *,
    vakint_module: Any,
) -> Expression:
    if len(mass_squareds) != len(propagator_powers):
        raise ValueError("mass_squareds and propagator_powers must have the same length")
    lowered_terms: list[Expression] = []
    for term in terms(numerator.expand()):
        stripped, shifts = extract_propagator_denominator_power_shifts(term)
        shifted_masses, shifted_powers = combine_propagator_power_shifts(
            mass_squareds,
            propagator_powers,
            shifts,
        )
        lowered_terms.append(
            vakint_module.one_loop_vacuum_integral(
                stripped,
                shifted_masses,
                powers=shifted_powers,
            )
        )
    return sum_expr(lowered_terms).expand()


def extract_propagator_denominator_power_shifts(
    term: Expression,
) -> tuple[Expression, tuple[tuple[Expression, int], ...]]:
    remaining: list[Expression] = []
    shifts: list[tuple[Expression, int]] = []
    for factor in factors(term):
        data = propagator_denominator_factor_data(factor)
        if data is None:
            remaining.append(factor)
            continue
        shifts.append(data)
    return product_expr(remaining).expand(), tuple(shifts)


def propagator_denominator_factor_data(factor: Expression) -> tuple[Expression, int] | None:
    base = factor
    exponent = 1
    parts = pow_parts(factor)
    if parts is not None:
        base, exponent_expr = parts
        parsed_exponent = as_int(exponent_expr)
        if parsed_exponent is None:
            return None
        exponent = parsed_exponent
    if not is_head(base, s.PropagatorDenominator) or len(base) != 2:
        return None
    if not bool(base[0] == s.LoopMomentumSquared):
        return None
    return base[1], exponent


def combine_propagator_power_shifts(
    mass_squareds: Sequence[Expression],
    propagator_powers: Sequence[int],
    shifts: Sequence[tuple[Expression, int]],
) -> tuple[tuple[Expression, ...], tuple[int, ...]]:
    combined: list[tuple[Expression, int]] = [
        (mass_squared, power)
        for mass_squared, power in zip(mass_squareds, propagator_powers, strict=True)
    ]
    for shifted_mass, shifted_power in shifts:
        for index, (mass_squared, power) in enumerate(combined):
            if bool(mass_squared == shifted_mass):
                combined[index] = (mass_squared, power + shifted_power)
                break
        else:
            combined.append((shifted_mass, shifted_power))
    kept = tuple((mass_squared, power) for mass_squared, power in combined if power)
    return (
        tuple(mass_squared for mass_squared, _power in kept),
        tuple(power for _mass_squared, power in kept),
    )


def wilson_line_internal_expression_map_by_entry(
    terms_by_entry: Mapping[str, Sequence[Expression]],
    prefix: str,
    *,
    combine_terms: bool,
) -> dict[str, Expression]:
    return {
        f"{prefix}[{entry_label}]": sum_wilson_line_internal_terms(entry_terms, combine_terms=combine_terms)
        for entry_label, entry_terms in terms_by_entry.items()
        if entry_terms
    }


def sum_wilson_line_internal_terms(
    terms_in: Iterable[Expression],
    *,
    combine_terms: bool,
) -> Expression:
    evaluated = sum_expr(terms_in)
    return evaluated.together() if combine_terms else evaluated


def cde_vakint_integral_terms_at_stage(
    raw_terms: Sequence[Expression],
    *,
    theory: Theory,
    stage: VakintIntegralStage,
    short_form: bool | None = None,
    engine: Any | None = None,
) -> Expression:
    return vakint_integral_terms_at_stage(
        raw_terms,
        theory=theory,
        stage=stage,
        short_form=short_form,
        engine=engine,
        label="CDE",
    )
