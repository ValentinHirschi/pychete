from __future__ import annotations

from symbolica import Expression, S

from ..expr import as_int, is_head, pow_parts
from . import vakint


def epsilon_symbol() -> Expression:
    """Return the dimensional regulator used by pychete's vacuum-integral series."""

    return S("vakint::ε")


def mu_r_squared_symbol() -> Expression:
    """Return the renormalization-scale-squared symbol used in vacuum-integral series."""

    return S("vakint::mursq")


def imaginary_unit_symbol() -> Expression:
    """Return vakint's imaginary-unit convention for backend comparison."""

    return S("vakint::𝑖")


def evaluate_one_loop_single_scale_vacuum_integral(
    numerator: Expression,
    mass: Expression,
    *,
    power: int = 1,
    epsilon: Expression | None = None,
    mu_r_squared: Expression | None = None,
) -> Expression:
    """Evaluate the one-loop single-scale massive tadpole through finite order.

    This is pychete's internal analytic expression for the scalar one-loop
    vacuum integral with one propagator of mass ``mass`` and integer
    propagator ``power``, in the same normalization convention used by vakint's
    default MSbar evaluation with ``number_of_terms_in_epsilon_expansion=2``.
    It returns the pole and finite terms. Mixed-scale and massless topologies
    are intentionally left to later Matchete-style integral-backend slices.
    """

    return evaluate_one_loop_single_scale_vacuum_integral_from_mass_squared(
        numerator,
        mass**2,
        power=power,
        epsilon=epsilon,
        mu_r_squared=mu_r_squared,
    )


def evaluate_one_loop_single_scale_vacuum_integral_from_mass_squared(
    numerator: Expression,
    mass_squared: Expression,
    *,
    power: int = 1,
    epsilon: Expression | None = None,
    mu_r_squared: Expression | None = None,
) -> Expression:
    """Evaluate a single-scale massive tadpole from a mass-squared slot.

    The input convention matches vakint's ``prop(..., mass_squared, power)``
    topology slots, so this helper is the internal analytic counterpart of
    native vakint evaluation after topology-independent tensor reduction.
    """

    if power < 1:
        raise ValueError("power must be at least 1")
    if bool(mass_squared == Expression.num(0)):
        raise ValueError("single-scale massive vacuum integrals require a nonzero mass")

    regulator = epsilon_symbol() if epsilon is None else epsilon
    scale_squared = mu_r_squared_symbol() if mu_r_squared is None else mu_r_squared
    normalization = imaginary_unit_symbol() * numerator / (16 * Expression.PI**2)
    mass_log = _mass_squared_log(mass_squared)
    if power == 1:
        return (
            normalization
            * mass_squared
            * (Expression.num(1) / regulator + 1 + scale_squared.log() - mass_log)
        ).expand()
    if power == 2:
        return (normalization * (Expression.num(1) / regulator + scale_squared.log() - mass_log)).expand()
    denominator = (power - 1) * (power - 2) * mass_squared ** (power - 2)
    sign = -1 if power % 2 else 1
    return (normalization * sign / denominator).expand()


def evaluate_one_loop_single_scale_vakint_expression(
    expr: Expression,
    *,
    epsilon: Expression | None = None,
    mu_r_squared: Expression | None = None,
) -> Expression:
    """Evaluate single-scale massive one-loop ``vakint::topo`` factors.

    This replacement-based evaluator is intended for vakint expressions after
    tensor reduction, where numerator algebra has already been handled and the
    remaining scalar topology is a one-loop, single-mass, massive vacuum
    topology. Unsupported zero-mass or mixed-mass topologies raise
    ``ValueError`` instead of delegating to native vakint.
    """

    pattern = _topology_pattern()
    for match in expr.match(pattern):
        _single_scale_topology_data(pattern.replace_wildcards(match))

    def evaluate_topology(match: dict[Expression, Expression]) -> Expression:
        topology = pattern.replace_wildcards(match)
        mass_squared, power = _single_scale_topology_data(topology)
        return evaluate_one_loop_single_scale_vacuum_integral_from_mass_squared(
            Expression.num(1),
            mass_squared,
            power=power,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
        )

    return expr.replace(pattern, evaluate_topology).expand()


def _mass_squared_log(mass_squared: Expression) -> Expression:
    parts = pow_parts(mass_squared)
    if parts is not None:
        base, exponent = parts
        if as_int(exponent) == 2:
            return 2 * base.log()
    return mass_squared.log()


def _single_scale_topology_data(topology_expr: Expression) -> tuple[Expression, int]:
    if not is_head(topology_expr, vakint.symbol("topo")) or len(topology_expr) != 1:
        raise ValueError("expected a vakint::topo(...) expression")
    mass_powers = _topology_mass_powers(topology_expr)
    if not mass_powers:
        raise ValueError("expected a one-loop topology with at least one propagator")
    reference_mass, total_power = mass_powers[0]
    if bool(reference_mass == Expression.num(0)):
        raise ValueError("single-scale massive vacuum integrals require nonzero masses")
    for mass_squared, power in mass_powers[1:]:
        if bool(mass_squared == Expression.num(0)):
            raise ValueError("single-scale massive vacuum integrals require nonzero masses")
        if not bool(mass_squared == reference_mass):
            raise ValueError("mixed-mass topologies require pychete's later mixed-scale integral backend")
        total_power += power
    return reference_mass, total_power


def _topology_mass_powers(topology_expr: Expression) -> tuple[tuple[Expression, int], ...]:
    pattern = _propagator_pattern()
    mass_wildcard = _propagator_mass_pattern()
    power_wildcard = _propagator_power_pattern()
    mass_powers: list[tuple[Expression, int]] = []
    for match in topology_expr.match(pattern):
        power_expr = power_wildcard.replace_wildcards(match)
        power = as_int(power_expr)
        if power is None or power < 1:
            raise ValueError("vakint propagator powers must be positive integers for internal evaluation")
        mass_powers.append((mass_wildcard.replace_wildcards(match), power))
    return tuple(mass_powers)


def _topology_pattern() -> Expression:
    return vakint.symbol("topo")(S("pychete_vakint_topology_factors_"))


def _propagator_pattern() -> Expression:
    return vakint.symbol("prop")(
        S("pychete_vakint_prop_id_"),
        S("pychete_vakint_prop_edge_"),
        S("pychete_vakint_prop_momentum_"),
        S("pychete_vakint_prop_mass_squared_"),
        S("pychete_vakint_prop_power_"),
    )


def _propagator_mass_pattern() -> Expression:
    return S("pychete_vakint_prop_mass_squared_")


def _propagator_power_pattern() -> Expression:
    return S("pychete_vakint_prop_power_")


__all__ = [
    "epsilon_symbol",
    "evaluate_one_loop_single_scale_vakint_expression",
    "evaluate_one_loop_single_scale_vacuum_integral",
    "evaluate_one_loop_single_scale_vacuum_integral_from_mass_squared",
    "imaginary_unit_symbol",
    "mu_r_squared_symbol",
]
