from __future__ import annotations

from symbolica import Expression

from pychete.matching import (
    WilsonLineTraceExpansionTerm,
    _wilson_line_term_matches_projection_requirements,
)
from pychete.symbols import canonical_string, s
from pychete.theory import Theory


def test_wilson_line_filter_keeps_derivative_terms_that_can_generate_field_strength_targets() -> None:
    theory = Theory("wilson_line_filter")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    weak = theory.field_handle("W")

    i = theory.index("i", fund)
    mu = theory.index("mu")
    nu = theory.index("nu")
    rho = theory.index("rho")
    sigma = theory.index("sigma")
    numerator = s.Bar(higgs(i)) * higgs(i)
    requirements = (
        (
            ("field", canonical_string(higgs.label), 2),
            ("field_strength", canonical_string(weak.label), 2),
        ),
    )

    term = WilsonLineTraceExpansionTerm(
        theory=theory,
        trace_name="hScalar-lScalar",
        path_index=0,
        expansion_indices=((mu, nu), (rho, sigma)),
        numerator=numerator,
        mass_squareds=(Expression.num(0),),
        propagator_powers=(1,),
        pre_wilson_numerator=numerator,
    )
    assert _wilson_line_term_matches_projection_requirements(term, requirements)

    no_derivative_budget = WilsonLineTraceExpansionTerm(
        theory=theory,
        trace_name="hScalar-lScalar",
        path_index=0,
        expansion_indices=((), ()),
        numerator=numerator,
        mass_squareds=(Expression.num(0),),
        propagator_powers=(1,),
        pre_wilson_numerator=numerator,
    )
    assert not _wilson_line_term_matches_projection_requirements(no_derivative_budget, requirements)
