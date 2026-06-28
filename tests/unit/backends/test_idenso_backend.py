from __future__ import annotations

from symbolica import Expression, S
from symbolica.community import idenso as native_idenso

from pychete import Theory
from pychete.backends import idenso, vakint
from pychete.expr import field_with_derivatives
from pychete.group_algebra import simplify_color, simplify_gamma, simplify_metrics, simplify_pychete_color
from pychete.symbols import SymbolRole, canonical_string, s


def _same(lhs, rhs) -> bool:
    return canonical_string(lhs) == canonical_string(rhs)


def test_idenso_backend_delegates_core_simplifiers() -> None:
    x = S("x")

    assert _same(idenso.simplify_gamma(x), native_idenso.simplify_gamma(x))
    assert _same(idenso.simplify_color(x), native_idenso.simplify_color(x))
    assert _same(idenso.simplify_metrics(x), native_idenso.simplify_metrics(x))
    assert _same(idenso.to_dots(x), native_idenso.to_dots(x))


def test_idenso_backend_exposes_index_helpers() -> None:
    x = S("x")
    header = S("wrapped")

    assert idenso.list_dangling(x) == native_idenso.list_dangling(x)
    assert _same(idenso.wrap_indices(x, header), native_idenso.wrap_indices(x, header))
    assert _same(idenso.wrap_dummies(x, header), native_idenso.wrap_dummies(x, header))
    assert _same(idenso.cook_indices(x), native_idenso.cook_indices(x))


def test_existing_group_algebra_shim_uses_idenso_backend() -> None:
    x = S("x")

    assert _same(simplify_gamma(x), idenso.simplify_gamma(x))
    assert _same(simplify_color(x), idenso.simplify_color(x))
    assert _same(simplify_metrics(x), idenso.simplify_metrics(x))


def test_group_algebra_shim_exposes_pychete_color_bridge() -> None:
    theory = Theory("idenso_group_algebra_shim")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    adjoint = theory.index("A", adj)
    left = theory.index("i", fund)
    right = theory.index("i", s.Bar(fund))

    assert _same(simplify_pychete_color(theory, generator(adjoint, left, right)), Expression.num(0))


def test_idenso_pipeline_is_native_noop_for_plain_symbol() -> None:
    x = S("x")

    assert _same(idenso.simplify_index_algebra(x, dots=True), x)


def test_idenso_bridge_simplifies_pychete_su2_generator_trace() -> None:
    theory = Theory("idenso_color_su2_trace")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    delta_adj = theory.cg_tensor_handle("del_SU2L_adj")
    adj_a = theory.index("A", adj)
    adj_b = theory.index("B", adj)
    i_fund = theory.index("i", fund)
    j_fund = theory.index("j", fund)
    i_dual = theory.index("i", s.Bar(fund))
    j_dual = theory.index("j", s.Bar(fund))

    expr = generator(adj_a, i_fund, j_dual) * generator(adj_b, j_fund, i_dual)
    expected = (Expression.num(1) / Expression.num(2)) * delta_adj(adj_a, adj_b)
    simplified = idenso.simplify_pychete_color_algebra(theory, expr)

    assert _same(simplified, expected)
    assert "spenso::" not in canonical_string(simplified)


def test_idenso_bridge_decodes_uncontracted_pychete_su2_generator() -> None:
    theory = Theory("idenso_color_su2_uncontracted_generator")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    adj_a = theory.index("A", adj)
    i = theory.index("i", fund)
    j = theory.index("j", s.Bar(fund))
    expr = generator(adj_a, i, j)

    simplified = idenso.simplify_pychete_color_algebra(theory, expr)

    assert _same(simplified, expr)
    assert "spenso::" not in canonical_string(simplified)


def test_idenso_bridge_contracts_pychete_generator_with_delta() -> None:
    theory = Theory("idenso_color_su2_generator_delta")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    delta_fund = theory.cg_tensor_handle("del_SU2L_fund")
    adj_a = theory.index("A", adj)
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    k = theory.index("k", s.Bar(fund))
    j_dual = theory.index("j", s.Bar(fund))

    expr = generator(adj_a, i, j_dual) * delta_fund(j, k)
    expected = generator(adj_a, i, k)
    simplified = idenso.simplify_pychete_color_algebra(theory, expr)

    assert _same(simplified, expected)
    assert "spenso::" not in canonical_string(simplified)


def test_idenso_bridge_contracts_pychete_delta_head_into_cg_tensor() -> None:
    theory = Theory("idenso_color_su2_generator_pychete_delta")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    adj_a = theory.index("A", adj)
    i = theory.index("i", s.Bar(fund))
    k = theory.index("k", fund)
    ell = theory.index("ell", fund)
    ell_dual = theory.index("ell", s.Bar(fund))

    expr = s.Delta(k, ell_dual) * generator(adj_a, ell, i)
    expected = generator(adj_a, k, i)
    simplified = idenso.contract_pychete_deltas_into_cg_tensors(expr)

    assert _same(simplified, expected)
    assert "pychete::Delta" not in canonical_string(simplified)


def test_idenso_bridge_contracts_closed_pychete_dummy_delta_to_representation_dimension() -> None:
    theory = Theory("idenso_color_su2_closed_pychete_delta")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    left = theory.dummy_index(1, fund)
    right = theory.dummy_index(2, s.Bar(fund))

    simplified = idenso.contract_pychete_deltas(theory, s.Delta(left, right))

    assert_expr = Expression.num(2)
    assert _same(simplified, assert_expr)


def test_idenso_bridge_contracts_pychete_delta_through_registered_field_index() -> None:
    theory = Theory("idenso_color_su2_field_pychete_delta")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    left = theory.index("i", fund)
    right = theory.index("j", s.Bar(fund))
    expected_index = theory.index("j", fund)

    simplified = idenso.contract_pychete_deltas(theory, s.Delta(left, right) * higgs(left))

    assert _same(simplified, higgs(expected_index))
    assert "pychete::Delta" not in canonical_string(simplified)


def test_idenso_bridge_contracts_pychete_delta_through_barred_field_index() -> None:
    theory = Theory("idenso_color_su2_barred_field_pychete_delta")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    left = theory.index("i", fund)
    right = theory.index("j", s.Bar(fund))
    right_inner = theory.index("j", fund)

    simplified = idenso.contract_pychete_deltas(theory, s.Delta(left, right) * s.Bar(higgs(right_inner)))

    assert _same(simplified, s.Bar(higgs(left)))
    assert "pychete::Delta" not in canonical_string(simplified)


def test_idenso_bridge_contracts_pychete_delta_chain_through_higgs_derivative_bilinear() -> None:
    theory = Theory("idenso_color_su2_higgs_derivative_delta_chain")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    k = theory.index("k", fund)
    ell = theory.index("ell", fund)
    mu = theory.index("mu")
    expr = (
        higgs(i)
        * field_with_derivatives(higgs(k), (mu,))
        * s.Bar(higgs(ell))
        * s.Bar(field_with_derivatives(higgs(j), (mu,)))
        * s.Delta(i, theory.index("j", s.Bar(fund)))
        * s.Delta(k, theory.index("ell", s.Bar(fund)))
    )
    expected = (
        higgs(j)
        * field_with_derivatives(higgs(ell), (mu,))
        * s.Bar(higgs(ell))
        * s.Bar(field_with_derivatives(higgs(j), (mu,)))
    )

    simplified = idenso.contract_pychete_deltas(theory, expr)

    assert _same(simplified, expected)
    assert "pychete::Delta" not in canonical_string(simplified)


def test_idenso_bridge_decodes_uncontracted_pychete_structure_constant() -> None:
    theory = Theory("idenso_color_su3_uncontracted_f")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    adj = theory.define_representation("SU3c", "adj")
    fstruct = theory.cg_tensor_handle("fStruct_SU3c")
    expr = fstruct(theory.index("A", adj), theory.index("B", adj), theory.index("C", adj))

    simplified = idenso.simplify_pychete_color_algebra(theory, expr)

    assert _same(simplified, expr)
    assert "spenso::" not in canonical_string(simplified)


def test_idenso_bridge_rewrites_pychete_adjoint_generator_to_structure_constant() -> None:
    theory = Theory("idenso_color_su2_adjoint_generator")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    adj = theory.define_representation("SU2L", "adj")
    generator = theory.cg_tensor_handle("gen_SU2L_adj")
    fstruct = theory.cg_tensor_handle("fStruct_SU2L")
    adj_a = theory.index("A", adj)
    adj_b = theory.index("B", adj)
    adj_c = theory.index("C", adj)
    expr = generator(adj_a, adj_b, adj_c)
    expected = -Expression.I * fstruct(adj_a, adj_b, adj_c)

    simplified = idenso.simplify_pychete_color_algebra(theory, expr)

    assert _same(simplified, expected)
    assert "gen_SU2L_adj" not in canonical_string(simplified)
    assert "spenso::" not in canonical_string(simplified)


def test_idenso_bridge_simplifies_field_strength_commutator_adjoint_generator() -> None:
    theory = Theory("idenso_color_field_strength_commutator")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    adj = theory.define_representation("SU2L", "adj")
    vector = theory.field_handle("W")
    fstruct = theory.cg_tensor_handle("fStruct_SU2L")
    mu = theory.index("mu")
    nu = theory.index("nu")
    rho = theory.index("rho")
    sigma = theory.index("sigma")
    source_index = theory.index("A", adj)
    body = s.FieldStrength(vector.label, s.List(rho, sigma), s.List(source_index), s.List())

    commutator = theory.covariant_derivative_commutator(body, mu, nu)
    simplified = idenso.simplify_pychete_color_algebra(theory, commutator)
    transformed_index = theory.index(theory.symbol("covariant_commutator_0_0", role=SymbolRole.INDEX), adj)
    adjoint_index = theory.index(theory.symbol("covariant_commutator_0_1", role=SymbolRole.INDEX), adj)
    expected = (
        theory.coupling_handle("gL")()
        * s.FieldStrength(vector.label, s.List(mu, nu), s.List(adjoint_index), s.List())
        * fstruct(transformed_index, adjoint_index, source_index)
        * s.FieldStrength(vector.label, s.List(rho, sigma), s.List(transformed_index), s.List())
    )

    assert _same(simplified, expected)
    assert "gen_SU2L_adj" not in canonical_string(simplified)
    assert "spenso::" not in canonical_string(simplified)


def test_idenso_bridge_preserves_non_native_pychete_cg_tensors() -> None:
    theory = Theory("idenso_color_preserve_delta")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    delta_fund = theory.cg_tensor_handle("del_SU2L_fund")
    adj_a = theory.index("A", adj)
    adj_b = theory.index("B", adj)
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    i_dual = theory.index("i", s.Bar(fund))
    j_dual = theory.index("j", s.Bar(fund))
    spectator_delta = delta_fund(i, j_dual)

    expr = spectator_delta + generator(adj_a, i, j_dual) * generator(adj_b, j, i_dual)
    simplified = idenso.simplify_pychete_color_algebra(theory, expr)
    simplified_text = canonical_string(simplified)

    assert "pychete::CG(idenso_color_preserve_delta::cg_tensor_del_SU2L_fund" in simplified_text
    assert "spenso_python::" not in simplified_text
    assert "spenso::" not in simplified_text


def test_idenso_bridge_simplifies_pychete_su3_structure_constants() -> None:
    theory = Theory("idenso_color_su3_f")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    adj = theory.define_representation("SU3c", "adj")
    fstruct = theory.cg_tensor_handle("fStruct_SU3c")
    delta_adj = theory.cg_tensor_handle("del_SU3c_adj")
    adj_a = theory.index("A", adj)
    adj_b = theory.index("B", adj)
    adj_c = theory.index("C", adj)
    adj_d = theory.index("D", adj)

    expr = fstruct(adj_a, adj_b, adj_c) * fstruct(adj_a, adj_b, adj_d)
    expected = Expression.num(3) * delta_adj(adj_c, adj_d)
    simplified = idenso.simplify_pychete_color_algebra(theory, expr)

    assert _same(simplified, expected)
    assert "pychete::CG" in canonical_string(simplified)
    assert "spenso::" not in canonical_string(simplified)


def test_idenso_bridge_simplifies_pychete_su2_fierz_contraction() -> None:
    theory = Theory("idenso_color_su2_fierz")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    delta_fund = theory.cg_tensor_handle("del_SU2L_fund")
    adj_a = theory.index("A", adj)
    i = theory.index("i", fund)
    k = theory.index("k", fund)
    j = theory.index("j", s.Bar(fund))
    l = theory.index("l", s.Bar(fund))

    expr = generator(adj_a, i, j) * generator(adj_a, k, l)
    expected = (
        (Expression.num(1) / Expression.num(2)) * delta_fund(i, l) * delta_fund(k, j)
        - (Expression.num(1) / Expression.num(4)) * delta_fund(i, j) * delta_fund(k, l)
    )
    simplified = idenso.simplify_pychete_color_algebra(theory, expr)

    assert _same(simplified, expected.expand())
    assert "spenso::" not in canonical_string(simplified)


def test_idenso_bridge_decodes_native_generator_chain_with_pychete_payload() -> None:
    theory = Theory("idenso_color_su2_generator_chain_payload")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    adj_a = theory.index("A", adj)
    adj_b = theory.index("B", adj)
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    k = theory.index("k", fund)
    k_dual = theory.index("k", s.Bar(fund))
    j_dual = theory.index("j", s.Bar(fund))
    mu = theory.index("mu")
    nu = theory.index("nu")
    field_strength_a = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adj_a), s.List())
    field_strength_b = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adj_b), s.List())
    expr = (
        s.Bar(higgs(j))
        * higgs(i)
        * generator(adj_a, i, k_dual)
        * generator(adj_b, k, j_dual)
        * field_strength_a
        * field_strength_b
    )

    simplified = idenso.simplify_pychete_color_algebra(theory, expr)
    simplified_text = canonical_string(simplified)

    assert "spenso::" not in simplified_text
    assert simplified_text.count("cg_tensor_gen_SU2L_fund") == 2
    assert simplified_text.count("FieldStrength") == 2
    assert "index_native_color_chain_" in simplified_text


def test_idenso_bridge_projects_su2_field_strength_generator_bilinear_to_singlet() -> None:
    theory = Theory("idenso_color_su2_field_strength_singlet")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    adj_a = theory.index("A", adj)
    adj_b = theory.index("B", adj)
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    k = theory.index("k", fund)
    k_dual = theory.index("k", s.Bar(fund))
    j_dual = theory.index("j", s.Bar(fund))
    mu = theory.index("mu")
    nu = theory.index("nu")
    field_strength_a = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adj_a), s.List())
    field_strength_b = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adj_b), s.List())
    expr = (
        higgs(i)
        * s.Bar(higgs(j))
        * generator(adj_a, i, k_dual)
        * generator(adj_b, k, j_dual)
        * field_strength_a
        * field_strength_b
    )
    expected = Expression.num(1) / Expression.num(4) * higgs(i) * s.Bar(higgs(i)) * field_strength_a**2

    simplified = idenso.simplify_su2_field_strength_generator_bilinears(theory, expr)

    assert _same(simplified, expected)
    assert "cg_tensor_gen_SU2L_fund" not in canonical_string(simplified)


def test_idenso_bridge_shared_field_strength_group_helper_projects_su2_bilinear() -> None:
    theory = Theory("idenso_color_shared_field_strength_group_helper")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    adj_a = theory.index("A", adj)
    adj_b = theory.index("B", adj)
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    k = theory.index("k", fund)
    k_dual = theory.index("k", s.Bar(fund))
    j_dual = theory.index("j", s.Bar(fund))
    mu = theory.index("mu")
    nu = theory.index("nu")
    field_strength_a = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adj_a), s.List())
    field_strength_b = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adj_b), s.List())
    expr = (
        higgs(i)
        * s.Bar(higgs(j))
        * generator(adj_a, i, k_dual)
        * generator(adj_b, k, j_dual)
        * field_strength_a
        * field_strength_b
    )
    expected = Expression.num(1) / Expression.num(4) * higgs(i) * s.Bar(higgs(i)) * field_strength_a**2

    simplified = idenso.simplify_pychete_field_strength_group_algebra(theory, expr)

    assert _same(simplified, expected)
    assert "cg_tensor_gen_SU2L_fund" not in canonical_string(simplified)


def test_idenso_bridge_projects_su2_field_strength_bilinear_with_pychete_delta() -> None:
    theory = Theory("idenso_color_su2_field_strength_pychete_delta")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    adj_a = theory.index("A", adj)
    adj_b = theory.index("B", adj)
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    k = theory.index("k", fund)
    ell = theory.index("ell", fund)
    k_dual = theory.index("k", s.Bar(fund))
    ell_dual = theory.index("ell", s.Bar(fund))
    j_dual = theory.index("j", s.Bar(fund))
    mu = theory.index("mu")
    nu = theory.index("nu")
    field_strength_a = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adj_a), s.List())
    field_strength_b = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adj_b), s.List())
    expr = (
        higgs(i)
        * s.Bar(higgs(j))
        * s.Delta(k, ell_dual)
        * generator(adj_a, i, k_dual)
        * generator(adj_b, ell, j_dual)
        * field_strength_a
        * field_strength_b
    )
    expected = Expression.num(1) / Expression.num(4) * higgs(i) * s.Bar(higgs(i)) * field_strength_a**2

    simplified = idenso.simplify_pychete_field_strength_group_algebra(theory, expr)

    assert _same(simplified, expected)
    assert "pychete::Delta" not in canonical_string(simplified)
    assert "cg_tensor_gen_SU2L_fund" not in canonical_string(simplified)


def test_idenso_bridge_projects_vakint_decoded_wilson_line_su2_bilinear() -> None:
    theory = Theory("idenso_color_vakint_wilson_line_su2")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    field_index = theory.index("field", fund)
    bar_index = theory.index(S("vakint::bar_h"), fund)
    internal_index = theory.index(
        theory.symbol("covariant_commutator_18_0", role=SymbolRole.INDEX),
        fund,
    )
    internal_dual = theory.index(
        theory.symbol("covariant_commutator_18_0", role=SymbolRole.INDEX),
        s.Bar(fund),
    )
    adjoint_left = theory.index(
        theory.symbol("covariant_commutator_4_1", role=SymbolRole.INDEX),
        adj,
    )
    adjoint_right = vakint.symbol("Index")(S("vakint::covariant_commutator_18_1"), adj)
    right_index = vakint.symbol("Index")(S("vakint::right_h"), fund)
    right_dual = vakint.symbol("Index")(S("vakint::right_h"), s.Bar(fund))
    bar_dual = vakint.symbol("Index")(S("vakint::bar_h"), s.Bar(fund))
    mu = theory.index("mu")
    nu = theory.index("nu")
    left_strength = s.FieldStrength(
        theory.field_handle("W").label,
        s.List(mu, nu),
        s.List(adjoint_left),
        s.List(),
    )
    right_strength = s.FieldStrength(
        theory.field_handle("W").label,
        s.List(mu, nu),
        s.List(adjoint_right),
        s.List(),
    )
    encoded = (
        higgs(field_index)
        * s.Bar(higgs(bar_index))
        * generator(adjoint_left, field_index, internal_dual)
        * generator(adjoint_right, internal_index, right_dual)
        * vakint.symbol("Delta")(bar_dual, right_index)
        * left_strength
        * right_strength
    )
    decoded = vakint.decode_pychete_namespace(theory, encoded)
    expected = Expression.num(1) / Expression.num(4) * higgs(field_index) * s.Bar(higgs(field_index)) * left_strength**2

    simplified = idenso.simplify_pychete_field_strength_group_algebra(theory, decoded)

    assert _same(simplified, expected)
    assert "vakint::Delta" not in canonical_string(simplified)
    assert "vakint::covariant_commutator" not in canonical_string(simplified)
    assert "cg_tensor_gen_SU2L_fund" not in canonical_string(simplified)


def test_idenso_bridge_projects_reversed_su2_field_strength_generator_bilinear_to_singlet() -> None:
    theory = Theory("idenso_color_su2_field_strength_reversed_singlet")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], self_conjugate=False, mass=0)
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    adj_a = theory.index("A", adj)
    adj_b = theory.index("B", adj)
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    k = theory.index("k", fund)
    k_dual = theory.index("k", s.Bar(fund))
    j_dual = theory.index("j", s.Bar(fund))
    mu = theory.index("mu")
    nu = theory.index("nu")
    field_strength_a = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adj_a), s.List())
    field_strength_b = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adj_b), s.List())
    expr = (
        higgs(i)
        * s.Bar(higgs(j))
        * generator(adj_a, k, j_dual)
        * generator(adj_b, i, k_dual)
        * field_strength_a
        * field_strength_b
    )
    expected = Expression.num(1) / Expression.num(4) * higgs(i) * s.Bar(higgs(i)) * field_strength_b**2

    simplified = idenso.simplify_su2_field_strength_generator_bilinears(theory, expr)

    assert _same(simplified, expected)
    assert "cg_tensor_gen_SU2L_fund" not in canonical_string(simplified)


def test_idenso_bridge_canonicalizes_mixed_su2_u1_field_strength_generator_bilinear() -> None:
    theory = Theory("idenso_color_su2_u1_field_strength_mixed")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    theory.define_gauge_group("U1Y", s.U1, "gY", "B")
    fund = theory.define_representation("SU2L", "fund")
    adj = theory.define_representation("SU2L", "adj")
    higgs = theory.define_field(
        "H",
        s.Scalar,
        indices=[fund],
        charges=[theory.group_charge("U1Y", Expression.num(1) / Expression.num(2))],
        self_conjugate=False,
        mass=0,
    )
    generator = theory.cg_tensor_handle("gen_SU2L_fund")
    adjoint = theory.index("A", adj)
    i = theory.index("i", fund)
    j = theory.index("j", fund)
    i_dual = theory.index("i", s.Bar(fund))
    j_dual = theory.index("j", s.Bar(fund))
    mu = theory.index("mu")
    nu = theory.index("nu")
    w_strength = s.FieldStrength(theory.field_handle("W").label, s.List(mu, nu), s.List(adjoint), s.List())
    b_strength = s.FieldStrength(theory.field_handle("B").label, s.List(mu, nu), s.List(), s.List())
    expr = higgs(i) * s.Bar(higgs(j)) * generator(adjoint, i, j_dual) * w_strength * b_strength
    expected = s.Bar(higgs(j)) * generator(adjoint, j, i_dual) * higgs(i) * w_strength * b_strength

    simplified = idenso.simplify_su2_u1_field_strength_generator_bilinears(theory, expr)

    assert _same(simplified, expected)


def test_idenso_bridge_contracts_pychete_loop_momentum_metrics() -> None:
    mu = s.Index(s.dummy_index(0), s.Lorentz)
    nu = s.Index(s.dummy_index(1), s.Lorentz)
    rho = s.Index(s.dummy_index(2), s.Lorentz)
    expr = s.Metric(mu, nu) * s.LoopMomentum(mu) * s.LoopMomentum(nu)
    delta_expr = s.Delta(mu, nu) * s.LoopMomentum(mu) * s.LoopMomentum(rho)

    assert _same(idenso.simplify_pychete_loop_momentum_metrics(expr), s.LoopMomentumSquared)
    assert _same(
        idenso.simplify_pychete_loop_momentum_metrics(delta_expr),
        s.LoopMomentum(nu) * s.LoopMomentum(rho),
    )


def test_idenso_bridge_contracts_pychete_metrics_into_field_derivative_slots() -> None:
    theory = Theory("idenso_field_derivative_metrics")
    phi = theory.define_field("phi", s.Scalar, mass=0)
    mu = s.Index(S(f"{theory.name}::index_wilson_line_mu"), s.Lorentz)
    nu = s.Index(S(f"{theory.name}::index_wilson_line_nu"), s.Lorentz)
    rho = theory.index("rho")
    expr = s.Metric(mu, nu) * s.Bar(phi(derivatives=[mu, rho]))

    simplified = idenso.simplify_pychete_field_derivative_metrics(expr)

    assert _same(simplified, s.Bar(phi(derivatives=[nu, rho])))


def test_idenso_bridge_simplifies_pychete_field_strength_metrics() -> None:
    theory = Theory("idenso_field_strength_metrics")
    vector = theory.define_field("V", s.Vector, self_conjugate=True, mass=0)
    mu = s.Index(s.dummy_index(0), s.Lorentz)
    nu = s.Index(s.dummy_index(1), s.Lorentz)
    rho = s.Index(s.dummy_index(2), s.Lorentz)
    strength = s.FieldStrength(vector.label, s.List(mu, nu), s.List(), s.List())

    assert _same(
        idenso.simplify_pychete_field_strength_metrics(s.Metric(mu, rho) * strength),
        -s.FieldStrength(vector.label, s.List(nu, rho), s.List(), s.List()),
    )
    assert _same(
        idenso.simplify_pychete_field_strength_metrics(s.Metric(mu, nu) * strength),
        Expression.num(0),
    )
    assert _same(
        idenso.simplify_pychete_field_strength_metrics(
            s.FieldStrength(vector.label, s.List(nu, mu), s.List(), s.List())
        ),
        -strength,
    )


def test_idenso_bridge_simplifies_generated_field_strength_metric_aliases() -> None:
    theory = Theory("idenso_generated_field_strength_metric_aliases")
    vector = theory.define_field("V", s.Vector, self_conjugate=True, mass=0)
    mu = s.Index(S("vakint::mu"), s.Lorentz)
    left = s.Index(S("vakint::wilson_line_probe_0"), s.Lorentz)
    right = s.Index(S("vakint::wilson_line_probe_1"), s.Lorentz)
    canonical_right = s.Index(S("pychete::wilson_line_probe_1"), s.Lorentz)
    metric_left = s.Index(S(f"{theory.name}::index_wilson_line_probe_0"), s.Lorentz)
    metric_right = s.Index(S(f"{theory.name}::index_wilson_line_probe_1"), s.Lorentz)
    expr = (
        s.Metric(metric_left, metric_right)
        * s.FieldStrength(vector.label, s.List(left, mu), s.List(), s.List())
        * s.FieldStrength(vector.label, s.List(right, mu), s.List(), s.List())
    )
    expected = s.FieldStrength(vector.label, s.List(canonical_right, mu), s.List(), s.List()) ** 2

    simplified = idenso.simplify_pychete_field_strength_metrics(expr)

    assert _same(simplified, expected)


def test_idenso_pipeline_simplifies_cde_field_strength_metric_trace() -> None:
    theory = Theory("idenso_cde_field_strength_trace")
    theory.define_gauge_group("SU2L", s.SU(2), "gL", "W_gauge")
    adjoint_representation = theory.define_representation("SU2L", "adj")
    vector = theory.define_field("W", s.Vector, self_conjugate=True, mass=0)
    b = s.Index(S("b"), s.Lorentz)
    c = s.Index(S("c"), s.Lorentz)
    adjoint = theory.index("A", adjoint_representation)
    source = S("x") * s.Metric(b, c) * s.FieldStrength(vector.label, s.List(c, b), s.List(adjoint), s.List())

    assert _same(
        idenso.simplify_index_algebra(source, expand=False, gamma=False, color=False, dots=False),
        Expression.num(0),
    )


def test_idenso_pipeline_contracts_pychete_loop_momentum_metrics() -> None:
    mu = s.Index(s.dummy_index(0), s.Lorentz)
    nu = s.Index(s.dummy_index(1), s.Lorentz)
    expr = S("x") * s.Metric(mu, nu) * s.LoopMomentum(mu) * s.LoopMomentum(nu)

    assert _same(
        idenso.simplify_index_algebra(expr, expand=False, gamma=False, color=False, dots=False),
        S("x") * s.LoopMomentumSquared,
    )


def test_idenso_pipeline_simplifies_pychete_projectors_through_native_bridge() -> None:
    expr = s.PR**3 + s.PL**2 + s.PR * s.PL + S("x") * s.PL * s.PR

    simplified = idenso.simplify_index_algebra(expr, expand=False, color=False, metrics=False)

    assert _same(simplified, s.PR + s.PL)
    assert _same(idenso.simplify_pychete_dirac_projectors(s.PR**2), s.PR)
    assert _same(idenso.simplify_pychete_dirac_projectors(s.PL**2), s.PL)
    assert _same(idenso.simplify_pychete_dirac_projectors(s.PR * s.PL), Expression.num(0))


def test_idenso_bridge_simplifies_pychete_dirac_products_through_native_gamma() -> None:
    mu = s.Index(s.dummy_index(0), s.Lorentz)
    nu = s.Index(s.dummy_index(1), s.Lorentz)

    assert _same(idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PR, s.PR)), s.PR)
    assert _same(idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PR, s.PL)), Expression.num(0))
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PR, s.Gamma(mu), s.PR)),
        Expression.num(0),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PL, s.Gamma(mu), s.PL)),
        Expression.num(0),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PR, s.Gamma(mu), s.PL)),
        s.DiracProduct(s.Gamma(mu), s.PL),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.PL, s.Gamma(mu), s.PR)),
        s.DiracProduct(s.Gamma(mu), s.PR),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.Gamma(mu), s.Gamma(mu))),
        Expression.num(4),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.DiracProduct(s.Gamma(mu), s.Gamma(nu), s.Gamma(mu))),
        -2 * s.Gamma(nu),
    )


def test_idenso_bridge_simplifies_pychete_dirac_products_inside_ncm() -> None:
    mu = s.Index(s.dummy_index(0), s.Lorentz)

    assert _same(idenso.simplify_pychete_dirac_algebra(s.NCM(s.PR, s.Gamma(mu), s.PR)), Expression.num(0))
    assert _same(
        idenso.simplify_pychete_dirac_algebra(
            s.NCM(S("left"), s.DiracProduct(s.PR, s.Gamma(mu), s.PL), S("right"))
        ),
        s.NCM(S("left"), s.DiracProduct(s.Gamma(mu), s.PL), S("right")),
    )


def test_idenso_bridge_traces_closed_pychete_dirac_chains_through_native_gamma() -> None:
    theory = Theory("idenso_closed_dirac_trace")
    left = theory.define_field("psi", s.Fermion)
    right = theory.define_field("Psi", s.Fermion)
    mu = theory.lorentz_index("mu")
    nu = theory.lorentz_index("nu")

    traced = idenso.trace_pychete_closed_dirac_chains(s.NCM(s.Gamma(mu), s.Gamma(nu)))

    assert _same(traced, 4 * s.Metric(mu, nu))
    assert "spenso::" not in canonical_string(traced)
    assert _same(idenso.trace_pychete_closed_dirac_chains(s.NCM(s.Gamma(mu))), Expression.num(0))
    assert _same(
        idenso.trace_pychete_closed_dirac_chains(s.NCM(s.Bar(left()), s.Gamma(mu), right())),
        s.NCM(s.Bar(left()), s.Gamma(mu), right()),
    )


def test_idenso_bridge_expands_bounded_ncm_powers_before_dirac_simplification() -> None:
    left = S("left")
    right = S("right")
    x = S("x")
    symbolic_power = S("n")

    assert _same(
        idenso.expand_pychete_ncm_powers(s.NCM(left, s.PR) ** 2),
        s.NCM(left, s.PR, left, s.PR),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(x * s.NCM(left, s.PR) ** 2),
        x * s.NCM(left, s.PR, left, s.PR),
    )
    assert _same(
        idenso.expand_pychete_ncm_powers(s.NCM(left, s.PR, right) ** symbolic_power),
        s.NCM(left, s.PR, right) ** symbolic_power,
    )


def test_idenso_bridge_simplifies_registered_open_fermion_chains_through_native_gamma() -> None:
    theory = Theory("idenso_open_fermion_chain")
    left = theory.define_field("psi", s.Fermion)
    right = theory.define_field("Psi", s.Fermion)
    mu = s.Index(s.dummy_index(0), s.Lorentz)

    assert _same(
        idenso.simplify_pychete_open_dirac_chains(
            s.NCM(s.Bar(left()), s.PR, s.Gamma(mu), s.PR, right())
        ),
        Expression.num(0),
    )
    assert _same(
        idenso.simplify_pychete_open_dirac_chains(
            s.NCM(s.Bar(left()), s.PR, s.Gamma(mu), s.PL, right())
        ),
        s.NCM(s.Bar(left()), s.DiracProduct(s.Gamma(mu), s.PL), right()),
    )
    assert _same(
        idenso.simplify_pychete_open_dirac_chains(
            s.NCM(s.Bar(left()), s.Gamma(mu), s.Gamma(mu), right())
        ),
        4 * s.NCM(s.Bar(left()), right()),
    )


def test_idenso_open_fermion_chain_bridge_requires_registered_field_labels() -> None:
    theory = Theory("idenso_open_fermion_chain_tags")
    right = theory.define_field("Psi", s.Fermion)
    mu = s.Index(s.dummy_index(0), s.Lorentz)
    plain_left = s.Field(S("plain_left"), s.Fermion, s.List(), s.List())
    expression = s.NCM(s.Bar(plain_left), s.PR, s.Gamma(mu), s.PR, right())

    assert _same(idenso.simplify_pychete_open_dirac_chains(expression), expression)


def test_idenso_bridge_simplifies_contiguous_dirac_subwords_inside_mixed_ncm() -> None:
    mu = s.Index(s.dummy_index(0), s.Lorentz)

    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.NCM(S("left"), s.PR, s.Gamma(mu), s.PR, S("right"))),
        Expression.num(0),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.NCM(S("left"), s.PR, s.Gamma(mu), s.PL, S("right"))),
        s.NCM(S("left"), s.DiracProduct(s.Gamma(mu), s.PL), S("right")),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.NCM(S("left"), s.Gamma(mu), s.Gamma(mu), S("right"))),
        4 * s.NCM(S("left"), S("right")),
    )
    assert _same(
        idenso.simplify_pychete_dirac_algebra(s.NCM(S("left"), s.Gamma(mu), s.Gamma(mu))),
        4 * S("left"),
    )
