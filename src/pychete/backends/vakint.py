from __future__ import annotations

from functools import cache
from typing import Any, Mapping, Sequence

from symbolica import Expression, Replacement, S

from ..expr import as_int, factors, is_head, pow_parts, product_expr, sum_expr
from ..logging import get_logger, progress
from ..symbols import canonical_string, s
from .common import import_backend

_LOGGER = get_logger("backends.vakint")


def native_module():
    """Return the native vakint Python module."""

    return import_backend("symbolica.community.vakint")


def symbol(name: str) -> Expression:
    """Return a Symbolica symbol in vakint's namespace."""

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
    ``vakint::k(loop_id, scalar_index)^2``. The replacement is delegated to
    Symbolica's wildcard matcher so callers can pass a full integral expression
    or only a numerator.
    """

    pattern = _pychete_loop_momentum_pattern()

    def lower_open_momentum(match: dict[Expression, Expression]) -> Expression:
        return loop_momentum(loop_id, match[s.LoopMomentumIndexWildcard])

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


@cache
def default_engine() -> Any:
    """Return a cached default native vakint engine."""

    return create_engine()


def _engine(engine: Any | None) -> Any:
    if engine is not None:
        return engine
    return default_engine()


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
    return _engine(engine).tensor_reduce(integral_expression)


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
    "collect_identical_propagators",
    "default_engine",
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
