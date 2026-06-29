from __future__ import annotations

import pytest
from symbolica import Expression, S

from pychete import EffectiveCouplingTarget, MatchingResult, Theory, hermitian_conjugate, map_effective_couplings, s
from pychete.functional import expand_cd_operators
from pychete.indices import relabel_dummy_indices

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


def test_map_effective_couplings_recovers_hermitian_conjugate_target_operator() -> None:
    theory = Theory("effective_coupling_hermitian_target")
    theory.define_gauge_group("SU2F", s.SU(Expression.num(2)), "g2", "W")
    theory.define_gauge_group("SU3C", s.SU(Expression.num(3)), "g3", "G")
    weak = theory.define_representation("SU2F", "fund")
    color = theory.define_representation("SU3C", "fund")
    flavor = theory.define_flavor_index("Flavor", 3)
    higgs = theory.define_field("H", s.Scalar, indices=[weak], self_conjugate=False, mass=0)
    up = theory.define_field("u", s.Fermion, indices=[color, flavor.symbol], chirality="right")
    down = theory.define_field("d", s.Fermion, indices=[color, flavor.symbol], chirality="right")
    yd = theory.define_coupling("Yd", indices=[flavor.symbol, flavor.symbol])
    yu = theory.define_coupling("Yu", indices=[flavor.symbol, flavor.symbol])
    eps = theory.cg_tensor_handle("eps_SU2F")
    mu = theory.index("mu")
    weak_i = theory.index("i", weak)
    weak_j = theory.index("j", weak)
    alpha = theory.index("alpha", color)
    i1 = theory.index("i1", flavor.symbol)
    i2 = theory.index("i2", flavor.symbol)
    dummy = theory.dummy_index(3, flavor.symbol)
    operator = (
        Expression.I
        * higgs(weak_j)
        * s.Bar(eps(weak_i, weak_j))
        * s.CD(mu, higgs(weak_i))
        * s.NCM(s.Bar(up(alpha, i1)), s.Gamma(mu), down(alpha, i2))
    )
    coefficient = -yd(dummy, i2) * s.Bar(yu(dummy, i1)) / Expression.num(2)
    source = expand_cd_operators(hermitian_conjugate((coefficient * operator).expand()))
    wilson = theory.define_wilson_coefficient("cHud", indices=[i1, i2], operator=operator)

    mapped = map_effective_couplings(
        source,
        (EffectiveCouplingTarget("cHud", wilson(), operator),),
        allow_incomplete_target=True,
    )

    assert_expr_equal(
        relabel_dummy_indices(mapped["cHud"], start=1),
        relabel_dummy_indices(coefficient, start=1),
    )


def test_map_effective_couplings_does_not_double_count_hermitian_conjugate_when_direct_target_exists() -> None:
    theory = Theory("effective_coupling_direct_plus_hc")
    theory.define_gauge_group("SU2F", s.SU(Expression.num(2)), "g2", "W")
    theory.define_gauge_group("SU3C", s.SU(Expression.num(3)), "g3", "G")
    weak = theory.define_representation("SU2F", "fund")
    color = theory.define_representation("SU3C", "fund")
    flavor = theory.define_flavor_index("Flavor", 3)
    lepton = theory.define_field("l", s.Fermion, indices=[weak, flavor.symbol], chirality="left")
    electron = theory.define_field("e", s.Fermion, indices=[flavor.symbol], chirality="right")
    quark = theory.define_field("q", s.Fermion, indices=[color, weak, flavor.symbol], chirality="left")
    down = theory.define_field("d", s.Fermion, indices=[color, flavor.symbol], chirality="right")
    ye = theory.define_coupling("Ye", indices=[flavor.symbol, flavor.symbol])
    yd = theory.define_coupling("Yd", indices=[flavor.symbol, flavor.symbol])
    weak_i = theory.index("i", weak)
    alpha = theory.index("alpha", color)
    i1 = theory.index("i1", flavor.symbol)
    i2 = theory.index("i2", flavor.symbol)
    i3 = theory.index("i3", flavor.symbol)
    i4 = theory.index("i4", flavor.symbol)
    operator = s.NCM(s.Bar(lepton(weak_i, i1)), electron(i2)) * s.NCM(
        s.Bar(down(alpha, i3)),
        quark(alpha, weak_i, i4),
    )
    coefficient = ye(i1, i2) * s.Bar(yd(i4, i3)) / Expression.num(6)
    source = (coefficient * operator + expand_cd_operators(hermitian_conjugate(coefficient * operator))).expand()
    wilson = theory.define_wilson_coefficient("cledq", indices=[i1, i2, i3, i4], operator=operator)

    mapped = map_effective_couplings(
        source,
        (EffectiveCouplingTarget("cledq", wilson(), operator),),
        allow_incomplete_target=True,
    )

    assert_expr_equal(mapped["cledq"], coefficient)


def test_map_effective_couplings_aligns_additive_target_operator_terms() -> None:
    theory = Theory("effective_coupling_additive_target_alignment")
    flavor = theory.define_flavor_index("Flavor", 3)
    phi = theory.define_field("phi", s.Scalar, indices=[flavor.symbol], self_conjugate=True, mass=0)
    chi = theory.define_field("chi", s.Scalar, indices=[flavor.symbol], self_conjugate=True, mass=0)
    rho = theory.define_field("rho", s.Scalar, indices=[flavor.symbol], self_conjugate=True, mass=0)
    eta = theory.define_field("eta", s.Scalar, indices=[flavor.symbol], self_conjugate=True, mass=0)
    coefficient = theory.define_coupling("C")
    i = theory.index("i", flavor.symbol)
    j = theory.index("j", flavor.symbol)
    a = theory.index("a", flavor.symbol)
    b = theory.index("b", flavor.symbol)
    operator = phi(i) * chi(j) + rho(i) * eta(j)
    source = coefficient() * (phi(a) * chi(b) + rho(a) * eta(b))
    wilson = theory.define_wilson_coefficient("cAdd", indices=[i, j], operator=operator)

    mapped = map_effective_couplings(
        source,
        (EffectiveCouplingTarget("cAdd", wilson(), operator),),
        allow_incomplete_target=True,
    )

    assert_expr_equal(mapped["cAdd"], coefficient())


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


def test_map_effective_couplings_decomposes_color_fierz_singlet_octet_currents() -> None:
    theory = Theory("effective_coupling_color_fierz")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    color = theory.define_representation("SU3c", "fund")
    adjoint = theory.define_representation("SU3c", "adj")
    flavor = theory.define_flavor_index("Flavor", 3)
    q = theory.define_field("q", s.Fermion, indices=[color, flavor.symbol], chirality="left")
    u = theory.define_field("u", s.Fermion, indices=[color, flavor.symbol], chirality="right")
    yukawa = theory.define_coupling("Y", indices=[flavor.symbol, flavor.symbol])
    gen = theory.cg_tensor_handle("gen_SU3c_fund")
    mu = theory.index("mu")
    adj = theory.index("A", adjoint)
    alpha = theory.index("alpha", color)
    beta = theory.index("beta", color)
    delta = theory.index("delta", color)
    kappa = theory.index("kappa", color)
    i1 = theory.index("i1", flavor.symbol)
    i2 = theory.index("i2", flavor.symbol)
    i3 = theory.index("i3", flavor.symbol)
    i4 = theory.index("i4", flavor.symbol)
    c1 = theory.index("c1", color)
    c2 = theory.index("c2", color)
    f1 = theory.index("f1", flavor.symbol)
    f2 = theory.index("f2", flavor.symbol)
    f3 = theory.index("f3", flavor.symbol)
    f4 = theory.index("f4", flavor.symbol)
    singlet_operator = s.NCM(s.Bar(u(beta, i3)), s.Gamma(mu), u(beta, i4)) * s.NCM(
        s.Bar(q(alpha, i1)),
        s.Gamma(mu),
        q(alpha, i2),
    )
    octet_operator = (
        gen(adj, alpha, beta)
        * gen(adj, delta, kappa)
        * s.NCM(s.Bar(u(delta, i3)), s.Gamma(mu), u(kappa, i4))
        * s.NCM(s.Bar(q(alpha, i1)), s.Gamma(mu), q(beta, i2))
    )
    source_operator = s.NCM(s.Bar(u(c2, f4)), q(c2, f1)) * s.NCM(s.Bar(q(c1, f3)), u(c1, f2))
    coefficient = yukawa(f3, f2) * s.Bar(yukawa(f1, f4))
    c_singlet = theory.define_wilson_coefficient("cqu1", indices=[i1, i2, i3, i4], operator=singlet_operator)
    c_octet = theory.define_wilson_coefficient("cqu8", indices=[i1, i2, i3, i4], operator=octet_operator)

    mapped = map_effective_couplings(
        coefficient * source_operator,
        (
            EffectiveCouplingTarget("cqu1", c_singlet(), singlet_operator),
            EffectiveCouplingTarget("cqu8", c_octet(), octet_operator),
        ),
    )

    expected = yukawa(i1, i4) * s.Bar(yukawa(i2, i3))
    assert_expr_equal(mapped["cqu1"], -expected / 6)
    assert_expr_equal(mapped["cqu8"], -expected)


@pytest.mark.parametrize("field_name", ["l", "q"])
def test_map_effective_couplings_decomposes_su2_higgs_current_singlet_triplet_pair(
    field_name: str,
) -> None:
    theory = Theory(f"ec_su2_hc_{field_name}")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    weak = theory.define_representation("SU2L", "fund")
    adjoint = theory.define_representation("SU2L", "adj")
    if field_name == "q":
        theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
        color = theory.define_representation("SU3c", "fund")
    else:
        color = None
    flavor = theory.define_flavor_index("Flavor", 3)
    h = theory.define_field("H", s.Scalar, indices=[weak])
    if field_name == "q":
        assert color is not None
        fermion = theory.define_field(
            field_name,
            s.Fermion,
            indices=[color, weak],
            chirality="left",
        )
    else:
        fermion = theory.define_field(field_name, s.Fermion, indices=[weak], chirality="left")
    gen = theory.cg_tensor_handle("gen_SU2L_fund")
    mu = theory.index("mu")
    adj = theory.index("A", adjoint)
    h_i = theory.index("hi", weak)
    h_j = theory.index("hj", weak)
    f_j = theory.index("fj", weak)
    f_k = theory.index("fk", weak)
    f_m = theory.index("fm", weak)
    p = theory.index("p", flavor.symbol)
    r = theory.index("r", flavor.symbol)
    alpha = theory.index("alpha", color) if color is not None else None
    singlet_coefficient = S(f"effective_coupling_su2_{field_name}_singlet")
    crossed_coefficient = S(f"effective_coupling_su2_{field_name}_crossed")

    def current(left_weak: Expression, right_weak: Expression) -> Expression:
        if alpha is None:
            return s.NCM(s.Bar(fermion(left_weak, p)), s.Gamma(mu), fermion(right_weak, r))
        return s.NCM(s.Bar(fermion(alpha, left_weak, p)), s.Gamma(mu), fermion(alpha, right_weak, r))

    singlet_operator = (
        -Expression.I * h(h_i) * s.Bar(h(h_i, derivatives=[mu])) * current(f_j, f_j)
        + Expression.I * h(h_i, derivatives=[mu]) * s.Bar(h(h_i)) * current(f_j, f_j)
    ).expand()
    triplet_operator = (
        -4
        * Expression.I
        * h(h_j)
        * s.Bar(h(h_i, derivatives=[mu]))
        * current(f_k, f_m)
        * gen(adj, h_i, h_j)
        * gen(adj, f_k, f_m)
        + 4
        * Expression.I
        * h(h_j, derivatives=[mu])
        * s.Bar(h(h_i))
        * current(f_k, f_m)
        * gen(adj, h_i, h_j)
        * gen(adj, f_k, f_m)
    ).expand()
    crossed_operator = (
        -Expression.I * h(h_j) * s.Bar(h(h_i, derivatives=[mu])) * current(h_j, h_i)
        + Expression.I * h(h_j, derivatives=[mu]) * s.Bar(h(h_i)) * current(h_j, h_i)
    ).expand()
    c_singlet = theory.define_wilson_coefficient(f"cH{field_name}1", indices=[p, r], operator=singlet_operator)
    c_triplet = theory.define_wilson_coefficient(f"cH{field_name}3", indices=[p, r], operator=triplet_operator)

    mapped = map_effective_couplings(
        singlet_coefficient * singlet_operator + crossed_coefficient * crossed_operator,
        (
            EffectiveCouplingTarget(f"cH{field_name}1", c_singlet(), singlet_operator),
            EffectiveCouplingTarget(f"cH{field_name}3", c_triplet(), triplet_operator),
        ),
    )

    assert_expr_equal(mapped[f"cH{field_name}1"], singlet_coefficient + crossed_coefficient / 2)
    assert_expr_equal(mapped[f"cH{field_name}3"], crossed_coefficient / 2)


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
