from __future__ import annotations

from functools import cache
from typing import Any, Mapping, Sequence

from symbolica import Expression, S

from ..expr import product_expr
from .common import import_backend


def native_module():
    """Return the native vakint Python module."""

    return import_backend("symbolica.community.vakint")


def symbol(name: str) -> Expression:
    """Return a Symbolica symbol in vakint's namespace."""

    return S(f"vakint::{name}")


def loop_momentum(loop_id: int = 1) -> Expression:
    """Return vakint's loop-momentum expression ``k(loop_id)``."""

    return symbol("k")(loop_id)


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

    return symbol("topo")(product_expr(propagators))


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

    return numerator * one_loop_vacuum_topology(mass_squareds, powers=powers)


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

    return _engine(engine).to_canonical(integral_expression, short_form)


def tensor_reduce(integral_expression: Expression, *, engine: Any | None = None) -> Expression:
    """Reduce vakint tensor integrals to scalar integrals with native vakint."""

    return _engine(engine).tensor_reduce(integral_expression)


def evaluate_integral(integral_expression: Expression, *, engine: Any | None = None) -> Expression:
    """Evaluate only the integral factor of a vakint expression."""

    return _engine(engine).evaluate_integral(integral_expression)


def evaluate(integral_expression: Expression, *, engine: Any | None = None) -> Expression:
    """Run vakint's complete tensor reduction and integral evaluation."""

    return _engine(engine).evaluate(integral_expression)


__all__ = [
    "create_engine",
    "default_engine",
    "edge",
    "evaluate",
    "evaluate_integral",
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
    "propagator",
    "symbol",
    "tensor_reduce",
    "to_canonical",
    "topology",
    "vakint_expression",
]
