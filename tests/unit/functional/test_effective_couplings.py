from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import EffectiveCouplingTarget, MatchingResult, Theory, map_effective_couplings, s

from tests.conftest import assert_expr_equal


def test_map_effective_couplings_solves_exact_target_lagrangian_with_symbolica() -> None:
    theory = Theory("effective_coupling_exact")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    operator = phi() ** 2
    wilson = theory.define_wilson_coefficient("cPhi2", operator=operator)
    coefficient = S("effective_coupling_exact_k")

    mapped = map_effective_couplings(
        coefficient * operator,
        (EffectiveCouplingTarget("cPhi2", wilson(), operator),),
    )

    assert_expr_equal(mapped["cPhi2"], coefficient)


def test_map_effective_couplings_encodes_complex_numeric_coefficients_for_symbolica_solver() -> None:
    theory = Theory("effective_coupling_complex")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    operator = phi() ** 2
    wilson = theory.define_wilson_coefficient("cPhi2", operator=operator)
    coefficient = S("effective_coupling_complex_k")

    mapped = map_effective_couplings(
        Expression.I * coefficient * operator,
        (EffectiveCouplingTarget("cPhi2", wilson(), operator),),
    )

    assert_expr_equal(mapped["cPhi2"], Expression.I * coefficient)


def test_map_effective_couplings_uses_operator_identities_when_direct_projection_fails() -> None:
    theory = Theory("effective_coupling_identity")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.index("mu")
    redundant_operator = s.Bar(phi()) * phi(derivatives=[mu])
    target_operator = phi() * s.Bar(phi(derivatives=[mu]))
    wilson = theory.define_wilson_coefficient("cPhiDer", operator=target_operator)
    coefficient = S("effective_coupling_identity_k")

    assert_expr_equal((coefficient * redundant_operator).coefficient(target_operator), Expression.num(0))

    mapped = map_effective_couplings(
        coefficient * redundant_operator,
        (EffectiveCouplingTarget("cPhiDer", wilson(), target_operator),),
        identities=(redundant_operator - 2 * target_operator,),
    )

    assert_expr_equal(mapped["cPhiDer"], 2 * coefficient)


def test_map_effective_couplings_incomplete_target_mode_is_explicit() -> None:
    theory = Theory("effective_coupling_incomplete")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    chi = theory.define_field("chi", s.Scalar, self_conjugate=True, mass=0)
    target_operator = phi() ** 2
    unrelated_operator = chi() ** 2
    wilson = theory.define_wilson_coefficient("cPhi2", operator=target_operator)
    coefficient = S("effective_coupling_incomplete_k")
    target = EffectiveCouplingTarget("cPhi2", wilson(), target_operator)

    with pytest.raises(ValueError, match="Inconsistent"):
        map_effective_couplings(coefficient * target_operator + unrelated_operator, (target,))

    mapped = map_effective_couplings(
        coefficient * target_operator + unrelated_operator,
        (target,),
        allow_incomplete_target=True,
    )

    assert_expr_equal(mapped["cPhi2"], coefficient)


def test_matching_result_map_effective_couplings_uses_registered_operator_metadata() -> None:
    theory = Theory("matching_result_effective_coupling")
    phi = theory.define_field("phi", s.Scalar, self_conjugate=True, mass=0)
    mu = theory.index("mu")
    redundant_operator = s.Bar(phi()) * phi(derivatives=[mu])
    target_operator = phi() * s.Bar(phi(derivatives=[mu]))
    wilson = theory.define_wilson_coefficient("cPhiDer", operator=target_operator)
    coefficient = S("matching_result_effective_coupling_k")
    result = MatchingResult(
        theory=theory,
        uv_lagrangian=Expression.num(0),
        off_shell_eft_lagrangian=Expression.num(0),
        on_shell_eft_lagrangian=coefficient * redundant_operator,
    )

    mapped = result.map_effective_couplings(
        {"cPhiDer": wilson()},
        identities=(redundant_operator - 2 * target_operator,),
    )

    assert_expr_equal(mapped["cPhiDer"], 2 * coefficient)
