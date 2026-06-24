from __future__ import annotations

from math import factorial

from symbolica import Expression, Replacement, S

from ..expr import as_int, is_head, pow_parts, product_expr, sum_expr
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

    return _single_scale_integral_from_mass_squared(
        numerator,
        mass_squared,
        beta=power,
        alpha=0,
        epsilon=epsilon,
        mu_r_squared=mu_r_squared,
    ).expand()


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


def evaluate_one_loop_vakint_expression(
    expr: Expression,
    *,
    epsilon: Expression | None = None,
    mu_r_squared: Expression | None = None,
) -> Expression:
    """Evaluate scalar one-loop ``vakint::topo`` factors with pychete.

    This implements Matchete's one-loop vacuum-integral reduction formula:
    zero-mass propagators are treated as powers of ``1/k^2``, repeated
    nonzero masses are combined, and multiscale topologies are reduced to
    derivatives of single-scale massive integrals with respect to mass-squared
    variables. Tensor numerators should be reduced before this scalar
    evaluation stage.
    """

    pattern = _topology_pattern()
    for match in expr.match(pattern):
        _topology_data(pattern.replace_wildcards(match))

    def evaluate_topology(match: dict[Expression, Expression]) -> Expression:
        topology = pattern.replace_wildcards(match)
        mass_powers, massless_power = _topology_data(topology)
        return _multi_scale_integral_from_mass_squareds(
            mass_powers,
            alpha=massless_power,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
        )

    return expr.replace(pattern, evaluate_topology).expand()


def _single_scale_integral_from_mass_squared(
    numerator: Expression,
    mass_squared: Expression,
    *,
    beta: int,
    alpha: int,
    epsilon: Expression | None = None,
    mu_r_squared: Expression | None = None,
) -> Expression:
    if beta < 1:
        return Expression.num(0)
    regulator = epsilon_symbol() if epsilon is None else epsilon
    scale_squared = mu_r_squared_symbol() if mu_r_squared is None else mu_r_squared
    normalization = imaginary_unit_symbol() * numerator / (16 * Expression.PI**2)
    prefactor = (
        normalization
        * _sign(alpha + beta)
        * mass_squared ** (2 - alpha - beta)
        / factorial(beta - 1)
    )
    log_ratio = scale_squared.log() - _mass_squared_log(mass_squared)

    if alpha >= 2:
        coefficient = -prefactor * _gamma_integer(alpha + beta - 2) * _sign(alpha - 2) / factorial(alpha - 2)
        finite_bracket = -_harmonic_number(alpha - 2) + log_ratio + 1 + _harmonic_number(alpha + beta - 3)
        return (coefficient * (Expression.num(1) / regulator + finite_bracket)).expand()

    if alpha + beta <= 2:
        coefficient = (
            prefactor
            * _gamma_integer(2 - alpha)
            * _sign(alpha + beta)
            / factorial(2 - alpha - beta)
        )
        finite_bracket = _harmonic_number(2 - alpha - beta) + log_ratio + 1 - _harmonic_number(1 - alpha)
        return (coefficient * (Expression.num(1) / regulator + finite_bracket)).expand()

    return (prefactor * _gamma_integer(2 - alpha) * _gamma_integer(alpha + beta - 2)).expand()


def _multi_scale_integral_from_mass_squareds(
    mass_powers: tuple[tuple[Expression, int], ...],
    *,
    alpha: int,
    epsilon: Expression | None = None,
    mu_r_squared: Expression | None = None,
) -> Expression:
    if not mass_powers:
        return Expression.num(0)
    if len(mass_powers) == 1:
        mass_squared, beta = mass_powers[0]
        return _single_scale_integral_from_mass_squared(
            Expression.num(1),
            mass_squared,
            beta=beta,
            alpha=alpha,
            epsilon=epsilon,
            mu_r_squared=mu_r_squared,
        )

    temp_masses = tuple(S(f"pychete_internal_mass_squared_{i}") for i, _entry in enumerate(mass_powers))
    replacements = [
        Replacement(temp_mass, mass_squared)
        for temp_mass, (mass_squared, _power) in zip(temp_masses, mass_powers, strict=True)
    ]
    terms: list[Expression] = []
    for i, (mass_squared, beta) in enumerate(mass_powers):
        other_indices = tuple(j for j in range(len(mass_powers)) if j != i)
        for derivative_order in range(beta):
            product = product_expr(
                (temp_masses[i] - temp_masses[j]) ** (-mass_powers[j][1])
                for j in other_indices
            )
            derivative = product
            for _ in range(derivative_order):
                derivative = derivative.derivative(temp_masses[i])
            derivative = derivative.replace_multiple(replacements).expand() / factorial(derivative_order)
            terms.append(
                _single_scale_integral_from_mass_squared(
                    Expression.num(1),
                    mass_squared,
                    beta=beta - derivative_order,
                    alpha=alpha,
                    epsilon=epsilon,
                    mu_r_squared=mu_r_squared,
                )
                * derivative
            )
    out = sum_expr(terms).expand()
    if _is_finite_multiscale(mass_powers, alpha):
        scale_squared = mu_r_squared_symbol() if mu_r_squared is None else mu_r_squared
        out = out.replace(scale_squared, mass_powers[0][0]).expand()
    return out


def _is_finite_multiscale(mass_powers: tuple[tuple[Expression, int], ...], alpha: int) -> bool:
    return sum(power for _mass, power in mass_powers) + alpha > 2 and alpha < 2


def _gamma_integer(n: int) -> Expression:
    if n < 1:
        raise ValueError("gamma argument must be a positive integer")
    return Expression.num(factorial(n - 1))


def _harmonic_number(n: int) -> Expression:
    if n < 1:
        return Expression.num(0)
    return sum_expr(Expression.num(1) / k for k in range(1, n + 1))


def _sign(power: int) -> int:
    return -1 if power % 2 else 1


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
    mass_powers, massless_power = _topology_data(topology_expr)
    if massless_power:
        raise ValueError("massless propagators require pychete's multiscale integral evaluator")
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


def _topology_data(topology_expr: Expression) -> tuple[tuple[tuple[Expression, int], ...], int]:
    if not is_head(topology_expr, vakint.symbol("topo")) or len(topology_expr) != 1:
        raise ValueError("expected a vakint::topo(...) expression")
    massless_power = 0
    mass_powers: list[tuple[Expression, int]] = []
    for mass_squared, power in _topology_mass_powers(topology_expr):
        if bool(mass_squared == Expression.num(0)):
            massless_power += power
            continue
        if power < 1:
            raise ValueError("massive vakint propagator powers must be positive integers for internal evaluation")
        for index, (existing_mass, existing_power) in enumerate(mass_powers):
            if bool(mass_squared == existing_mass):
                mass_powers[index] = (existing_mass, existing_power + power)
                break
        else:
            mass_powers.append((mass_squared, power))
    return tuple(mass_powers), massless_power


def _topology_mass_powers(topology_expr: Expression) -> tuple[tuple[Expression, int], ...]:
    pattern = _propagator_pattern()
    mass_wildcard = _propagator_mass_pattern()
    power_wildcard = _propagator_power_pattern()
    mass_powers: list[tuple[Expression, int]] = []
    for match in topology_expr.match(pattern):
        power_expr = power_wildcard.replace_wildcards(match)
        power = as_int(power_expr)
        if power is None:
            raise ValueError("vakint propagator powers must be integers for internal evaluation")
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
    "evaluate_one_loop_vakint_expression",
    "imaginary_unit_symbol",
    "mu_r_squared_symbol",
]
