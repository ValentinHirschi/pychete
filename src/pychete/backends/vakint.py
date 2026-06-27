from __future__ import annotations

from hashlib import sha256
from functools import cache
from typing import Any, Callable, Mapping, Sequence

from symbolica import Expression, Replacement, S

from ..expr import args, as_int, factors, is_head, list_expr, pow_parts, product_expr, sum_expr
from ..logging import get_logger, progress
from ..noncommutative import scalarize_commutative_ncm_chains
from ..symbols import SymbolRole, canonical_string, s, safe_symbol_name
from .common import import_backend

_LOGGER = get_logger("backends.vakint")
_LOOP_MOMENTUM_INDEX_SYMBOLS_BY_INDEX: dict[str, Expression] = {}
_LOOP_MOMENTUM_INDEX_BY_SAFE_SYMBOL: dict[str, Expression] = {}
_MAX_VAKINT_NCM_DECODE_ARITY = 16


def native_module():
    """Return the native vakint Python module."""

    return import_backend("symbolica.community.vakint")


def symbol(name: str) -> Expression:
    """Return a Symbolica symbol in vakint's namespace."""

    if name == "g":
        return S("vakint::g", is_symmetric=True)
    return S(f"vakint::{name}")


def epsilon_symbol() -> Expression:
    """Return vakint's default dimensional-regularization epsilon symbol."""

    return symbol("ε")


def loop_momentum(loop_id: int = 1, index: Expression | int | None = None) -> Expression:
    """Return vakint's loop-momentum expression.

    ``loop_momentum(loop_id)`` is the momentum object used in topology
    propagators, while ``loop_momentum(loop_id, index)`` is vakint's native
    tensor-numerator component ``k(loop_id, index)``.
    """

    if index is not None:
        return symbol("k")(loop_id, index)
    return symbol("k")(loop_id)


def loop_momentum_squared(loop_id: int = 1, scalar_index: int = 1) -> Expression:
    """Return vakint's native scalar loop-momentum product ``k(loop_id, i)^2``."""

    return loop_momentum(loop_id, scalar_index) ** 2


def lower_pychete_loop_momentum_numerators(
    expr: Expression,
    *,
    loop_id: int = 1,
    scalar_index: int = 1,
) -> Expression:
    """Lower pychete loop-momentum numerator heads to vakint-native syntax.

    Open pychete numerator components ``LoopMomentum(mu)`` become
    ``vakint::k(loop_id, mu)`` and the scalar ``LoopMomentumSquared`` becomes
    ``vakint::k(loop_id, scalar_index)^2``. Full pychete ``Index(...)``
    metadata is first mapped to flat backend-safe symbols so native vakint/FORM
    never sees nested pychete index wrappers in vector slots. The mapping is
    process-local and decoded back to ``Index(...)`` by
    ``decode_pychete_namespace``. The replacement is delegated to Symbolica's
    wildcard matcher so callers can pass a full integral expression or only a
    numerator.
    """

    pattern = _pychete_loop_momentum_pattern()

    def lower_open_momentum(match: dict[Expression, Expression]) -> Expression:
        return loop_momentum(loop_id, _backend_safe_loop_momentum_index(match[s.LoopMomentumIndexWildcard]))

    return expr.replace_multiple(
        (
            Replacement(s.LoopMomentumSquared, loop_momentum_squared(loop_id, scalar_index)),
            Replacement(pattern, lower_open_momentum),
        ),
        repeat=True,
    )


def edge(left: int = 1, right: int = 1) -> Expression:
    """Return a vakint graph edge expression."""

    return symbol("edge")(left, right)


def propagator(
    prop_id: int,
    mass_squared: Expression,
    *,
    loop_id: int = 1,
    power: int = 1,
    edge_left: int = 1,
    edge_right: int = 1,
) -> Expression:
    """Build one vakint ``prop`` factor for a single-loop vacuum topology."""

    return symbol("prop")(prop_id, edge(edge_left, edge_right), loop_momentum(loop_id), mass_squared, power)


def topology(propagators: Sequence[Expression]) -> Expression:
    """Build a vakint ``topo`` expression from propagator factors."""

    return collect_identical_propagators(symbol("topo")(product_expr(propagators)))


def collect_identical_propagators(expr: Expression) -> Expression:
    """Collect identical vakint propagator signatures inside all topologies.

    Propagators with the same edge, momentum, and mass-squared signature are
    represented as a single ``vakint::prop`` whose power is the sum of all
    matching powers. Powered propagator factors are handled generically, so
    ``prop(..., p)^n`` contributes ``n * p`` to the collected power.
    """

    pattern = _topology_pattern()

    def collect_match(match: dict[Expression, Expression]) -> Expression:
        return _collect_topology_propagators(pattern.replace_wildcards(match))

    return expr.replace(pattern, collect_match)


def one_loop_vacuum_topology(
    mass_squareds: Sequence[Expression],
    *,
    powers: Sequence[int] | None = None,
) -> Expression:
    """Build a one-loop vacuum topology with powered distinct-mass propagators."""

    if powers is not None and len(powers) != len(mass_squareds):
        raise ValueError("powers must match the number of mass-squared entries")
    prop_powers = tuple(1 for _ in mass_squareds) if powers is None else tuple(powers)
    mass_powers = _combine_equal_mass_powers(mass_squareds, prop_powers)
    return topology(
        tuple(
            propagator(index, mass_squared, power=power)
            for index, (mass_squared, power) in enumerate(mass_powers, start=1)
        )
    )


def one_loop_vacuum_integral(
    numerator: Expression,
    mass_squareds: Sequence[Expression],
    *,
    powers: Sequence[int] | None = None,
) -> Expression:
    """Build a vakint one-loop vacuum integral from a numerator and masses."""

    return lower_pychete_loop_momentum_numerators(numerator) * one_loop_vacuum_topology(
        mass_squareds,
        powers=powers,
    )


def _combine_equal_mass_powers(
    mass_squareds: Sequence[Expression],
    powers: Sequence[int],
) -> tuple[tuple[Expression, int], ...]:
    combined: list[tuple[Expression, int]] = []
    for mass_squared, power in zip(mass_squareds, powers, strict=True):
        for index, (existing_mass_squared, existing_power) in enumerate(combined):
            if bool(mass_squared == existing_mass_squared):
                combined[index] = (existing_mass_squared, existing_power + power)
                break
        else:
            combined.append((mass_squared, power))
    return tuple(combined)


def _collect_topology_propagators(topology_expr: Expression) -> Expression:
    if not is_head(topology_expr, symbol("topo")) or len(topology_expr) != 1:
        return topology_expr
    collected: dict[tuple[str, str, str], tuple[Expression, Expression, Expression, Expression, int]] = {}
    passthrough: list[Expression] = []
    for factor in factors(topology_expr[0]):
        data = _propagator_factor_data(factor)
        if data is None:
            passthrough.append(factor)
            continue
        prop_id, edge_expr, momentum_expr, mass_squared, power = data
        signature = (
            canonical_string(edge_expr),
            canonical_string(momentum_expr),
            canonical_string(mass_squared),
        )
        if signature in collected:
            existing_id, existing_edge, existing_momentum, existing_mass, existing_power = collected[signature]
            collected[signature] = (
                existing_id,
                existing_edge,
                existing_momentum,
                existing_mass,
                existing_power + power,
            )
        else:
            collected[signature] = (prop_id, edge_expr, momentum_expr, mass_squared, power)
    collected_props = tuple(
        symbol("prop")(prop_id, edge_expr, momentum_expr, mass_squared, power)
        for prop_id, edge_expr, momentum_expr, mass_squared, power in collected.values()
        if power
    )
    return symbol("topo")(product_expr((*passthrough, *collected_props)))


def _propagator_factor_data(factor: Expression) -> tuple[Expression, Expression, Expression, Expression, int] | None:
    power_multiplier = 1
    base = factor
    parts = pow_parts(factor)
    if parts is not None:
        base, exponent = parts
        n = as_int(exponent)
        if n is None:
            return None
        power_multiplier = n
    if not is_head(base, symbol("prop")) or len(base) != 5:
        return None
    power = as_int(base[4])
    if power is None:
        return None
    return base[0], base[1], base[2], base[3], power * power_multiplier


def new_alphaloop_method() -> Any:
    """Create vakint's native alphaLoop evaluation method descriptor."""

    return native_module().VakintEvaluationMethod.new_alphaloop_method()


def new_matad_method(**kwargs: Any) -> Any:
    """Create vakint's native MATAD evaluation method descriptor."""

    return native_module().VakintEvaluationMethod.new_matad_method(**kwargs)


def new_fmft_method(**kwargs: Any) -> Any:
    """Create vakint's native FMFT evaluation method descriptor."""

    return native_module().VakintEvaluationMethod.new_fmft_method(**kwargs)


def new_pysecdec_method(**kwargs: Any) -> Any:
    """Create vakint's native pySecDec evaluation method descriptor."""

    return native_module().VakintEvaluationMethod.new_pysecdec_method(**kwargs)


def create_engine(**kwargs: Any) -> Any:
    """Create a native vakint engine.

    Engine construction can be expensive because vakint initializes known
    topologies. Prefer passing an existing engine into the adapter functions
    during matching workflows.
    """

    with progress("creating native vakint engine", logger=_LOGGER):
        return native_module().Vakint(**kwargs)


def create_tensor_reduction_engine(**kwargs: Any) -> Any:
    """Create a native vakint engine that does not require evaluation backends.

    Tensor reduction is topology independent in vakint and does not need the
    analytic or numerical integral-evaluation stack. Passing an explicit empty
    evaluation order avoids constructor-time checks for optional evaluators
    such as PySecDec while keeping the native tensor reducer available.
    """

    kwargs.setdefault("evaluation_order", [])
    return create_engine(**kwargs)


@cache
def default_engine() -> Any:
    """Return a cached default native vakint engine."""

    return create_engine()


@cache
def default_tensor_reduction_engine() -> Any:
    """Return a cached native vakint tensor-reduction-only engine."""

    return create_tensor_reduction_engine()


def _engine(engine: Any | None) -> Any:
    if engine is not None:
        return engine
    return default_engine()


def _tensor_reduction_engine(engine: Any | None) -> Any:
    if engine is not None:
        return engine
    return default_tensor_reduction_engine()


def vakint_expression(expr: Expression) -> Any:
    """Wrap a Symbolica expression in vakint's native integral expression type."""

    return native_module().VakintExpression(expr)


def numerical_result(values: Sequence[tuple[int, tuple[float, float]]]) -> Any:
    """Create vakint's native numerical-result container."""

    return native_module().VakintNumericalResult(values)


def numerical_result_from_expression(expr: Expression, *, engine: Any | None = None) -> Any:
    """Convert a Symbolica Laurent expression using a native vakint engine."""

    return _engine(engine).numerical_result_from_expression(expr)


def numerical_result_to_expression(result: Any, *, engine: Any | None = None) -> Expression:
    """Convert a native vakint numerical result back to a Symbolica expression."""

    return _engine(engine).numerical_result_to_expression(result)


def numerical_evaluation(
    evaluated_integral: Any,
    params: Mapping[str, float],
    externals: Mapping[int, tuple[float, float, float, float]] | None = None,
    *,
    engine: Any | None = None,
) -> tuple[Any, Any | None]:
    """Delegate numerical evaluation of a vakint-evaluated integral."""

    return _engine(engine).numerical_evaluation(evaluated_integral, params, externals)


def to_canonical(
    integral_expression: Expression,
    *,
    short_form: bool | None = None,
    engine: Any | None = None,
) -> Expression:
    """Canonicalize a vakint integral expression with native vakint."""

    integral_expression = _prepare_integral_expression(integral_expression)
    _raise_for_native_analytic_integral_scope(integral_expression)
    _LOGGER.debug("canonicalizing vakint expression with native engine")
    return _engine(engine).to_canonical(integral_expression, short_form)


def tensor_reduce(integral_expression: Expression, *, engine: Any | None = None) -> Expression:
    """Reduce tensor numerators with native vakint.

    This operation is topology-independent and is allowed before pychete's own
    analytic handling of zero-mass or mixed-mass vacuum-integral topologies.
    """

    integral_expression = _prepare_integral_expression(integral_expression)
    _LOGGER.debug("tensor-reducing vakint expression with native engine")
    return _tensor_reduction_engine(engine).tensor_reduce(integral_expression)


def evaluate_integral(integral_expression: Expression, *, engine: Any | None = None) -> Expression:
    """Evaluate only the integral factor of a vakint expression."""

    integral_expression = _prepare_integral_expression(integral_expression)
    _raise_for_native_analytic_integral_scope(integral_expression)
    _LOGGER.debug("evaluating vakint integral factor with native engine")
    return _engine(engine).evaluate_integral(integral_expression)


def evaluate(integral_expression: Expression, *, engine: Any | None = None) -> Expression:
    """Run vakint's complete tensor reduction and integral evaluation."""

    integral_expression = _prepare_integral_expression(integral_expression)
    _raise_for_native_analytic_integral_scope(integral_expression)
    _LOGGER.debug("evaluating vakint expression with native engine")
    return _engine(engine).evaluate(integral_expression)


def decode_pychete_namespace(theory: Any, expr: Expression) -> Expression:
    """Decode pychete atoms that native vakint emitted in its own namespace.

    Vakint's tensor reducer preserves arbitrary numerator factors but can emit
    pychete ``Field``/``Coupling``/``Index`` atoms as ``vakint::...`` wrappers.
    Matching-condition projection expects the theory-owned pychete heads, so
    convert only those known wrappers back through Symbolica replacement rules.
    """

    context = _DecodeContext(theory)
    namespace_replacements = (
        Replacement(symbol("𝑖"), Expression.I),
        Replacement(symbol("I"), Expression.I),
        Replacement(symbol("𝜋"), Expression.PI),
        Replacement(symbol("π"), Expression.PI),
        Replacement(
            _vakint_bar_pattern(),
            lambda match: context.decode_bar(match[_wild("bar_body")]),
        ),
        Replacement(
            _vakint_index_pattern(),
            lambda match: context.decode_index(
                match[_wild("index_label")],
                match[_wild("index_representation")],
            ),
        ),
        Replacement(
            _vakint_coupling_pattern(),
            lambda match: context.decode_coupling(
                match[_wild("coupling_label")],
                match[_wild("coupling_indices")],
                match[_wild("coupling_order")],
            ),
        ),
        Replacement(
            _vakint_field_pattern(),
            lambda match: context.decode_field(
                match[_wild("field_label")],
                match[_wild("field_type")],
                match[_wild("field_indices")],
                match[_wild("field_derivatives")],
            ),
        ),
        Replacement(
            _vakint_field_strength_pattern(),
            lambda match: context.decode_field_strength(
                match[_wild("field_strength_label")],
                match[_wild("field_strength_lorentz")],
                match[_wild("field_strength_indices")],
                match[_wild("field_strength_derivatives")],
            ),
        ),
        Replacement(
            _vakint_wilson_term_pattern(),
            lambda match: context.decode_wilson_term(
                match[_wild("wilson_term_field")],
                match[_wild("wilson_term_link_indices")],
                match[_wild("wilson_term_derivative_indices")],
            ),
        ),
        Replacement(
            _vakint_metric_pattern(),
            lambda match: context.decode_metric(
                match[_wild("metric_left")],
                match[_wild("metric_right")],
            ),
        ),
        Replacement(
            _vakint_delta_pattern(),
            lambda match: context.decode_delta(
                match[_wild("delta_left")],
                match[_wild("delta_right")],
            ),
        ),
        Replacement(
            _vakint_cg_pattern(),
            lambda match: context.decode_cg(
                match[_wild("cg_label")],
                match[_wild("cg_indices")],
            ),
        ),
        *_vakint_ncm_replacements(context),
    )
    decoded = expr.replace_multiple(namespace_replacements)
    decoded = decoded.replace_multiple(
        (
            Replacement(
                _vakint_cd_pattern(),
                lambda match: context.decode_cd(
                    match[_wild("cd_indices")],
                    match[_wild("cd_body")],
                ),
            ),
        )
    )
    return scalarize_commutative_ncm_chains(decoded)


def _vakint_ncm_replacements(context: _DecodeContext) -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for arity in range(1, _MAX_VAKINT_NCM_DECODE_ARITY + 1):
        wildcards = tuple(_wild(f"ncm_operand_{arity}_{index}") for index in range(arity))
        replacements.append(
            Replacement(
                symbol("NCM")(*wildcards),
                _vakint_ncm_replacement(context, wildcards),
                rhs_cache_size=0,
            )
        )
    return tuple(replacements)


def _vakint_ncm_replacement(
    context: _DecodeContext,
    wildcards: tuple[Expression, ...],
) -> Callable[[Mapping[Expression, Expression]], Expression]:
    def replacement(match: Mapping[Expression, Expression]) -> Expression:
        return s.NCM(*(decode_pychete_namespace(context.theory, match[wildcard]) for wildcard in wildcards))

    return replacement


class _DecodeContext:
    def __init__(self, theory: Any) -> None:
        self.theory = theory
        self.fields_by_safe_name = _registry_safe_name_map(theory.fields)
        self.couplings_by_safe_name = _registry_safe_name_map(theory.couplings)
        self.externals_by_safe_name = _registry_safe_name_map(theory.externals)
        self.groups_by_safe_name = _registry_safe_name_map(theory.groups)
        self.cg_tensors_by_safe_name = _registry_safe_name_map(theory.cg_tensors)

    def decode_bar(self, body: Expression) -> Expression:
        return s.Bar(self.decode_payload(body))

    def decode_field(
        self,
        label: Expression,
        type_expr: Expression,
        indices: Expression,
        derivatives: Expression,
    ) -> Expression:
        name = _vakint_local_name(label)
        field_name = self._registered_name(name, self.theory.fields, self.fields_by_safe_name)
        if field_name is None:
            return symbol("Field")(label, type_expr, indices, derivatives)
        return s.Field(
            self.theory.field_handle(field_name).label,
            self.decode_payload(type_expr),
            list_expr(*self.decode_sequence(indices)),
            list_expr(*self.decode_sequence(derivatives)),
        )

    def decode_field_strength(
        self,
        label: Expression,
        lorentz: Expression,
        indices: Expression,
        derivatives: Expression,
    ) -> Expression:
        name = _vakint_local_name(label)
        field_name = self._registered_name(name, self.theory.fields, self.fields_by_safe_name)
        if field_name is None:
            return symbol("FieldStrength")(label, lorentz, indices, derivatives)
        return s.FieldStrength(
            self.theory.field_handle(field_name).label,
            list_expr(*self.decode_sequence(lorentz)),
            list_expr(*self.decode_sequence(indices)),
            list_expr(*self.decode_sequence(derivatives)),
        )

    def decode_wilson_term(self, field: Expression, link_indices: Expression, derivatives: Expression) -> Expression:
        return s.WilsonTerm(
            self.decode_wilson_field_label(field),
            list_expr(*self.decode_sequence(link_indices)),
            list_expr(*self.decode_sequence(derivatives)),
        )

    def decode_wilson_field_label(self, field: Expression) -> Expression:
        if is_head(field, symbol("Bar")) and len(field) == 1:
            return s.Bar(self.decode_wilson_field_label(field[0]))
        name = _vakint_local_name(field)
        field_name = self._registered_name(name, self.theory.fields, self.fields_by_safe_name)
        if field_name is not None:
            return self.theory.field_handle(field_name).label
        return self.decode_payload(field)

    def decode_coupling(self, label: Expression, indices: Expression, order: Expression) -> Expression:
        name = _vakint_local_name(label)
        coupling_name = self._registered_name(name, self.theory.couplings, self.couplings_by_safe_name)
        if coupling_name is not None:
            decoded_label = self.theory.coupling_handle(coupling_name).label
        else:
            external_name = self._registered_name(name, self.theory.externals, self.externals_by_safe_name)
            if external_name is None:
                return symbol("Coupling")(label, indices, order)
            decoded_label = self.theory.external_handle(external_name).label
        return s.Coupling(decoded_label, list_expr(*self.decode_sequence(indices)), order)

    def decode_index(self, label: Expression, representation: Expression) -> Expression:
        return s.Index(self.decode_index_label(label), self.decode_payload(representation))

    def decode_metric(self, left: Expression, right: Expression) -> Expression:
        return s.Metric(self.decode_payload(left), self.decode_payload(right))

    def decode_delta(self, left: Expression, right: Expression) -> Expression:
        return s.Delta(self.decode_payload(left), self.decode_payload(right))

    def decode_cg(self, label: Expression, indices: Expression) -> Expression:
        name = _vakint_local_name(label)
        cg_name = self._registered_name(name, self.theory.cg_tensors, self.cg_tensors_by_safe_name)
        if cg_name is None:
            return symbol("CG")(label, indices)
        return s.CG(
            self.theory.cg_tensor_handle(cg_name).label,
            list_expr(*self.decode_sequence(indices)),
        )

    def decode_cd(self, indices: Expression, body: Expression) -> Expression:
        index_expr = (
            list_expr(*self.decode_sequence(indices))
            if _is_bare_vakint_symbol(indices, "List") or is_head(indices, symbol("List")) or is_head(indices, s.List)
            else self.decode_payload(indices)
        )
        return s.CD(index_expr, self.decode_payload(body))

    def decode_sequence(self, expr: Expression) -> tuple[Expression, ...]:
        if _is_bare_vakint_symbol(expr, "List"):
            return ()
        if is_head(expr, symbol("List")):
            return tuple(self.decode_payload(item) for item in args(expr))
        if is_head(expr, s.List):
            return tuple(self.decode_payload(item) for item in args(expr))
        return (self.decode_payload(expr),)

    def decode_index_label(self, label: Expression) -> Expression:
        if is_head(label, symbol("dummy_index")) and len(label) == 1:
            return s.dummy_index(label[0])
        decoded = self.decode_payload(label)
        generated_index = self._decode_theory_generated_index_label(decoded)
        if generated_index is not None:
            return generated_index
        return _decode_generated_backend_index_alias(decoded) or decoded

    def _decode_theory_generated_index_label(self, label: Expression) -> Expression | None:
        local_name = _symbol_local_name(label)
        if local_name is None:
            return None
        if local_name.startswith("index_covariant_commutator_"):
            local_name = local_name.removeprefix("index_")
        if not local_name.startswith("covariant_commutator_"):
            return None
        return self.theory.symbol(local_name, role=SymbolRole.INDEX)

    def decode_payload(self, expr: Expression) -> Expression:
        safe_loop_index = _decode_backend_safe_loop_momentum_index(expr)
        if safe_loop_index is not None:
            return safe_loop_index
        builtin = _decode_vakint_builtin(expr)
        if builtin is not None:
            return builtin
        if is_head(expr, symbol("List")):
            return list_expr(*(self.decode_payload(item) for item in args(expr)))
        if is_head(expr, symbol("Bar")) and len(expr) == 1:
            return self.decode_bar(expr[0])
        if is_head(expr, symbol("Index")) and len(expr) == 2:
            return self.decode_index(expr[0], expr[1])
        if is_head(expr, symbol("Coupling")) and len(expr) == 3:
            return self.decode_coupling(expr[0], expr[1], expr[2])
        if is_head(expr, symbol("Field")) and len(expr) == 4:
            return self.decode_field(expr[0], expr[1], expr[2], expr[3])
        if is_head(expr, symbol("FieldStrength")) and len(expr) == 4:
            return self.decode_field_strength(expr[0], expr[1], expr[2], expr[3])
        if is_head(expr, symbol("WilsonTerm")) and len(expr) == 3:
            return self.decode_wilson_term(expr[0], expr[1], expr[2])
        if is_head(expr, symbol("g")) and len(expr) == 2:
            return self.decode_metric(expr[0], expr[1])
        if is_head(expr, symbol("Delta")) and len(expr) == 2:
            return self.decode_delta(expr[0], expr[1])
        if is_head(expr, symbol("CG")) and len(expr) == 2:
            return self.decode_cg(expr[0], expr[1])
        if is_head(expr, symbol("CD")) and len(expr) == 2:
            return self.decode_cd(expr[0], expr[1])
        if is_head(expr, symbol("Vector")) and len(expr) == 1:
            return s.Vector(self.decode_payload(expr[0]))
        if is_head(expr, symbol("Ghost")) and len(expr) == 1:
            return s.Ghost(self.decode_payload(expr[0]))
        if is_head(expr, symbol("AntiGhost")) and len(expr) == 1:
            return s.AntiGhost(self.decode_payload(expr[0]))
        group_expr = self._decode_group_expression(expr)
        if group_expr is not None:
            return group_expr
        return expr

    def _decode_group_expression(self, expr: Expression) -> Expression | None:
        name = _vakint_local_name(expr)
        if name is None:
            return None
        group_name = self._registered_name(name, self.theory.groups, self.groups_by_safe_name)
        if group_name is None or not is_head(expr, symbol(name)):
            return None
        return self.theory.symbol(group_name, role=SymbolRole.GROUP)(
            *(self.decode_payload(item) for item in args(expr))
        )

    @staticmethod
    def _registered_name(
        name: str | None,
        registry: Mapping[str, Any],
        safe_names: Mapping[str, str],
    ) -> str | None:
        if name is None:
            return None
        if name in registry:
            return name
        return safe_names.get(name)


def _registry_safe_name_map(registry: Mapping[str, Any]) -> dict[str, str]:
    return {safe_symbol_name(name): name for name in registry}


def _vakint_local_name(expr: Expression) -> str | None:
    try:
        name = expr.get_name()
    except TypeError:
        return None
    prefix = "vakint::"
    if not name.startswith(prefix):
        return None
    return name.removeprefix(prefix)


def _symbol_local_name(expr: Expression) -> str | None:
    try:
        name = expr.get_name()
    except TypeError:
        return None
    return name.rsplit("::", maxsplit=1)[-1]


def _is_vakint_symbol(expr: Expression, name: str) -> bool:
    return _vakint_local_name(expr) == name


def _is_bare_vakint_symbol(expr: Expression, name: str) -> bool:
    return _is_vakint_symbol(expr, name) and not is_head(expr, symbol(name))


def _decode_vakint_builtin(expr: Expression) -> Expression | None:
    name = _vakint_local_name(expr)
    if name is None:
        return None
    if name in {"𝑖", "I"}:
        return Expression.I
    if name in {"𝜋", "π"}:
        return Expression.PI
    if name == "List" and _is_bare_vakint_symbol(expr, "List"):
        return s.List()
    if name == "Scalar":
        return s.Scalar
    if name == "Fermion":
        return s.Fermion
    if name == "Lorentz":
        return s.Lorentz
    if name == "fund":
        return s.fund
    if name == "adj":
        return s.adj
    return None


def _backend_safe_loop_momentum_index(index: Expression) -> Expression:
    if not is_head(index, s.Index):
        return index
    key = canonical_string(index)
    if key not in _LOOP_MOMENTUM_INDEX_SYMBOLS_BY_INDEX:
        digest = sha256(key.encode("utf-8")).hexdigest()[:24]
        safe_symbol = S(f"pychete_vakint_index_{digest}")
        safe_name = _safe_symbol_name(safe_symbol)
        _LOOP_MOMENTUM_INDEX_SYMBOLS_BY_INDEX[key] = safe_symbol
        _LOOP_MOMENTUM_INDEX_BY_SAFE_SYMBOL[safe_name] = index
    return _LOOP_MOMENTUM_INDEX_SYMBOLS_BY_INDEX[key]


def _decode_backend_safe_loop_momentum_index(expr: Expression) -> Expression | None:
    return _LOOP_MOMENTUM_INDEX_BY_SAFE_SYMBOL.get(_safe_symbol_name(expr))


def _decode_generated_backend_index_alias(expr: Expression) -> Expression | None:
    try:
        full_name = expr.get_name()
    except TypeError:
        return None
    local_name = full_name.rsplit("::", maxsplit=1)[-1]
    for prefix in ("index_wilson_line_", "index_cde_"):
        if local_name.startswith(prefix):
            return Expression.symbol(f"pychete::{local_name.removeprefix('index_')}")
    for prefix in ("wilson_line_", "cde_"):
        if local_name.startswith(prefix):
            return Expression.symbol(f"pychete::{local_name}")
    return None


def _safe_symbol_name(expr: Expression) -> str:
    try:
        return expr.get_name()
    except TypeError:
        return canonical_string(expr)


@cache
def _wild(name: str) -> Expression:
    return S(f"vakint_decode_{name}_")


@cache
def _vakint_bar_pattern() -> Expression:
    return symbol("Bar")(_wild("bar_body"))


@cache
def _vakint_index_pattern() -> Expression:
    return symbol("Index")(_wild("index_label"), _wild("index_representation"))


@cache
def _vakint_coupling_pattern() -> Expression:
    return symbol("Coupling")(
        _wild("coupling_label"),
        _wild("coupling_indices"),
        _wild("coupling_order"),
    )


@cache
def _vakint_field_pattern() -> Expression:
    return symbol("Field")(
        _wild("field_label"),
        _wild("field_type"),
        _wild("field_indices"),
        _wild("field_derivatives"),
    )


@cache
def _vakint_field_strength_pattern() -> Expression:
    return symbol("FieldStrength")(
        _wild("field_strength_label"),
        _wild("field_strength_lorentz"),
        _wild("field_strength_indices"),
        _wild("field_strength_derivatives"),
    )


@cache
def _vakint_wilson_term_pattern() -> Expression:
    return symbol("WilsonTerm")(
        _wild("wilson_term_field"),
        _wild("wilson_term_link_indices"),
        _wild("wilson_term_derivative_indices"),
    )


@cache
def _vakint_metric_pattern() -> Expression:
    return symbol("g")(_wild("metric_left"), _wild("metric_right"))


@cache
def _vakint_delta_pattern() -> Expression:
    return symbol("Delta")(_wild("delta_left"), _wild("delta_right"))


@cache
def _vakint_cg_pattern() -> Expression:
    return symbol("CG")(_wild("cg_label"), _wild("cg_indices"))


@cache
def _vakint_cd_pattern() -> Expression:
    return symbol("CD")(_wild("cd_indices"), _wild("cd_body"))


@cache
def _pychete_loop_momentum_pattern() -> Expression:
    return s.LoopMomentum(s.LoopMomentumIndexWildcard)


def _prepare_integral_expression(integral_expression: Expression) -> Expression:
    return collect_identical_propagators(lower_pychete_loop_momentum_numerators(integral_expression))


def _raise_for_native_analytic_integral_scope(integral_expression: Expression) -> None:
    """Reject integral evaluation outside native vakint's analytic single-scale scope."""

    for topology_expr in _topologies(integral_expression):
        masses = _topology_mass_squareds(topology_expr)
        if not masses:
            continue
        zero_masses = tuple(mass for mass in masses if bool(mass == Expression.num(0)))
        if zero_masses:
            raise ValueError(
                "native vakint is only used for analytically supported single-scale "
                "massive vacuum integrals; zero-mass propagators must be handled by "
                "pychete's separate integral backend"
            )
        reference_mass = masses[0]
        if any(not bool(mass == reference_mass) for mass in masses[1:]):
            raise ValueError(
                "native vakint is only used for analytically supported single-scale "
                "massive vacuum integrals; mixed-mass topologies must be handled by "
                "pychete's separate integral backend"
            )


def _topologies(integral_expression: Expression) -> tuple[Expression, ...]:
    pattern = _topology_pattern()
    return tuple(pattern.replace_wildcards(match) for match in integral_expression.match(pattern))


@cache
def _topology_pattern() -> Expression:
    return symbol("topo")(S("vakint_topology_factors_"))


def _topology_mass_squareds(topology_expr: Expression) -> tuple[Expression, ...]:
    if not is_head(topology_expr, symbol("topo")) or len(topology_expr) != 1:
        return ()
    pattern = _propagator_pattern()
    mass = _propagator_mass_pattern()
    return tuple(mass.replace_wildcards(match) for match in topology_expr.match(pattern))


@cache
def _propagator_pattern() -> Expression:
    return symbol("prop")(
        S("vakint_prop_id_"),
        S("vakint_prop_edge_"),
        S("vakint_prop_momentum_"),
        S("vakint_prop_mass_squared_"),
        S("vakint_prop_power_"),
    )


@cache
def _propagator_mass_pattern() -> Expression:
    return S("vakint_prop_mass_squared_")


def epsilon_coefficient(expr: Expression, power: int, *, epsilon: Expression | None = None) -> Expression:
    """Return the coefficient of one epsilon Laurent power using Symbolica."""

    regulator = epsilon_symbol() if epsilon is None else epsilon
    try:
        return expr.series(regulator, 0, max(power, 0))[power].expand()
    except Exception:
        target = Expression.num(1) if power == 0 else regulator**power
        for epsilon_power, coefficient in expr.coefficient_list(regulator):
            if bool(epsilon_power == target):
                return coefficient.expand()
    return Expression.num(0)


def pole_part(
    expr: Expression,
    *,
    max_pole_order: int = 1,
    epsilon: Expression | None = None,
) -> Expression:
    """Return the negative-power epsilon pole part of a Laurent expression."""

    if max_pole_order < 1:
        raise ValueError("max_pole_order must be at least 1")
    regulator = epsilon_symbol() if epsilon is None else epsilon
    return sum_expr(
        epsilon_coefficient(expr, power, epsilon=regulator) * regulator**power
        for power in range(-max_pole_order, 0)
    ).expand()


def finite_part(expr: Expression, *, epsilon: Expression | None = None) -> Expression:
    """Return the epsilon^0 coefficient of a Laurent expression."""

    return epsilon_coefficient(expr, 0, epsilon=epsilon)


__all__ = [
    "create_engine",
    "create_tensor_reduction_engine",
    "collect_identical_propagators",
    "decode_pychete_namespace",
    "default_engine",
    "default_tensor_reduction_engine",
    "edge",
    "epsilon_coefficient",
    "epsilon_symbol",
    "evaluate",
    "evaluate_integral",
    "finite_part",
    "loop_momentum_squared",
    "lower_pychete_loop_momentum_numerators",
    "loop_momentum",
    "native_module",
    "new_alphaloop_method",
    "new_fmft_method",
    "new_matad_method",
    "new_pysecdec_method",
    "numerical_evaluation",
    "numerical_result",
    "numerical_result_from_expression",
    "numerical_result_to_expression",
    "one_loop_vacuum_integral",
    "one_loop_vacuum_topology",
    "pole_part",
    "propagator",
    "symbol",
    "tensor_reduce",
    "to_canonical",
    "topology",
    "vakint_expression",
]
