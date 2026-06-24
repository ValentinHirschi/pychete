from __future__ import annotations

from symbolica import Expression, S


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
    epsilon: Expression | None = None,
    mu_r_squared: Expression | None = None,
) -> Expression:
    """Evaluate the one-loop single-scale massive tadpole through finite order.

    This is pychete's internal analytic expression for the scalar one-loop
    vacuum integral with one propagator of mass ``mass`` and power one, in the
    same normalization convention used by vakint's default MSbar evaluation
    with ``number_of_terms_in_epsilon_expansion=2``. It returns the pole and
    finite terms. Higher propagator powers and mixed-scale topologies are
    intentionally left to later Matchete-style integral-backend slices.
    """

    regulator = epsilon_symbol() if epsilon is None else epsilon
    scale_squared = mu_r_squared_symbol() if mu_r_squared is None else mu_r_squared
    mass_squared = mass**2
    prefactor = imaginary_unit_symbol() * numerator * mass_squared / (16 * Expression.PI**2)
    series = Expression.num(1) / regulator + 1 + scale_squared.log() - 2 * mass.log()
    return (prefactor * series).expand()


__all__ = [
    "epsilon_symbol",
    "evaluate_one_loop_single_scale_vacuum_integral",
    "imaginary_unit_symbol",
    "mu_r_squared_symbol",
]
