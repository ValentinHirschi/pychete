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


def test_map_effective_couplings_normalizes_chiral_scalar_projectors() -> None:
    theory = Theory("effective_coupling_chiral_projectors")
    left = theory.define_field("l", s.Fermion, chirality="left")
    right = theory.define_field("e", s.Fermion, chirality="right")
    target_operator = s.NCM(s.Bar(left()), right())
    source_operator = s.NCM(s.Bar(left()), s.DiracProduct(s.PR), right())
    wilson = theory.define_wilson_coefficient("cLe", operator=target_operator)
    coefficient = S("effective_coupling_chiral_projectors_k")

    assert_expr_equal((coefficient * source_operator).coefficient(target_operator), Expression.num(0))

    mapped = map_effective_couplings(
        coefficient * source_operator,
        (EffectiveCouplingTarget("cLe", wilson(), target_operator),),
    )

    assert_expr_equal(mapped["cLe"], coefficient)


def test_map_effective_couplings_aligns_target_operator_indices_into_coefficients() -> None:
    theory = Theory("effective_coupling_index_alignment")
    flavor = theory.define_flavor_index("Flavor", 3)
    left = theory.define_field("l", s.Fermion, indices=[flavor.symbol], chirality="left")
    right = theory.define_field("e", s.Fermion, indices=[flavor.symbol], chirality="right")
    yukawa = theory.define_coupling("Y", indices=[flavor.symbol, flavor.symbol])
    i = theory.index("i", flavor.symbol)
    j = theory.index("j", flavor.symbol)
    a = theory.index("a", flavor.symbol)
    b = theory.index("b", flavor.symbol)
    target_operator = s.NCM(s.Bar(left(i)), right(j))
    source_operator = s.NCM(s.Bar(left(a)), s.DiracProduct(s.PR), right(b))
    wilson = theory.define_wilson_coefficient("cLe", indices=[i, j], operator=target_operator)

    mapped = map_effective_couplings(
        yukawa(a, b) * source_operator,
        (EffectiveCouplingTarget("cLe", wilson(), target_operator),),
    )

    assert_expr_equal(mapped["cLe"], yukawa(i, j))


def test_map_effective_couplings_canonicalizes_builtin_epsilon_orientation() -> None:
    theory = Theory("effective_coupling_epsilon_orientation")
    theory.define_gauge_group("SU2F", s.SU(Expression.num(2)), "g", "W")
    fund = theory.define_representation("SU2F", "fund")
    left_l = theory.define_field("l", s.Fermion, indices=[fund], chirality="left")
    right_e = theory.define_field("e", s.Fermion, chirality="right")
    left_q = theory.define_field("q", s.Fermion, indices=[fund], chirality="left")
    right_u = theory.define_field("u", s.Fermion, chirality="right")
    coupling = theory.define_coupling("Y")
    eps = theory.cg_tensor_handle("eps_SU2F")
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    a = theory.index("a", fund)
    b = theory.index("b", fund)
    target_operator = s.NCM(s.Bar(left_l(i)), right_e()) * s.NCM(s.Bar(left_q(j)), right_u()) * eps(i, j)
    source_operator = (
        s.NCM(s.Bar(left_l(b)), s.DiracProduct(s.PR), right_e())
        * s.NCM(s.Bar(left_q(a)), s.DiracProduct(s.PR), right_u())
        * eps(a, b)
    )
    wilson = theory.define_wilson_coefficient("cLq", operator=target_operator)

    mapped = map_effective_couplings(
        coupling() * source_operator,
        (EffectiveCouplingTarget("cLq", wilson(), target_operator),),
    )

    assert_expr_equal(mapped["cLq"], -coupling())


def test_map_effective_couplings_uses_chiral_fierz_identity_for_vector_currents() -> None:
    theory = Theory("effective_coupling_chiral_fierz")
    flavor = theory.define_flavor_index("Flavor", 3)
    left = theory.define_field("l", s.Fermion, indices=[flavor.symbol], chirality="left")
    right = theory.define_field("e", s.Fermion, indices=[flavor.symbol], chirality="right")
    yukawa = theory.define_coupling("Y", indices=[flavor.symbol, flavor.symbol])
    mu = theory.index("mu")
    i1 = theory.index("i1", flavor.symbol)
    i2 = theory.index("i2", flavor.symbol)
    i3 = theory.index("i3", flavor.symbol)
    i4 = theory.index("i4", flavor.symbol)
    a = theory.index("a", flavor.symbol)
    b = theory.index("b", flavor.symbol)
    c = theory.index("c", flavor.symbol)
    d = theory.index("d", flavor.symbol)
    target_operator = s.NCM(s.Bar(right(i3)), s.Gamma(mu), right(i4)) * s.NCM(
        s.Bar(left(i1)), s.Gamma(mu), left(i2)
    )
    source_operator = s.NCM(s.Bar(right(c)), left(b)) * s.NCM(s.Bar(left(a)), right(d))
    wilson = theory.define_wilson_coefficient("cLe", indices=[i1, i2, i3, i4], operator=target_operator)

    mapped = map_effective_couplings(
        yukawa(a, d) * s.Bar(yukawa(b, c)) * source_operator,
        (EffectiveCouplingTarget("cLe", wilson(), target_operator),),
    )

    assert_expr_equal(mapped["cLe"], -yukawa(i1, i4) * s.Bar(yukawa(i2, i3)) / 2)


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
