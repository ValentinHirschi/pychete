from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from symbolica import Expression, S

from pychete import Theory
from pychete.backends import idenso, vakint
from pychete.symbols import SymbolRole, canonical_string, s


@dataclass
class FakeVakintEngine:
    calls: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)

    def to_canonical(self, expr: Any, short_form: bool | None = None) -> Any:
        self.calls.append(("to_canonical", (expr, short_form)))
        return S("canonical")(expr)

    def tensor_reduce(self, expr: Any) -> Any:
        self.calls.append(("tensor_reduce", (expr,)))
        return S("reduced")(expr)

    def evaluate_integral(self, expr: Any) -> Any:
        self.calls.append(("evaluate_integral", (expr,)))
        return S("integral")(expr)

    def evaluate(self, expr: Any) -> Any:
        self.calls.append(("evaluate", (expr,)))
        return S("evaluated")(expr)

    def numerical_result_from_expression(self, expr: Any) -> str:
        self.calls.append(("numerical_result_from_expression", (expr,)))
        return "numerical-result"

    def numerical_result_to_expression(self, result: Any) -> Any:
        self.calls.append(("numerical_result_to_expression", (result,)))
        return S("epsilon_series")

    def numerical_evaluation(
        self,
        evaluated_integral: Any,
        params: dict[str, float],
        externals: dict[int, tuple[float, float, float, float]] | None = None,
    ) -> tuple[str, None]:
        self.calls.append(("numerical_evaluation", (evaluated_integral, params, externals)))
        return ("value", None)


def test_vakint_metric_symbol_matches_native_symmetry_before_import() -> None:
    mu, nu = S("mu", "nu")

    assert canonical_string(vakint.symbol("g")(nu, mu)) == canonical_string(vakint.symbol("g")(mu, nu))


def test_vakint_method_factories_import_without_engine_creation() -> None:
    method = vakint.new_alphaloop_method()

    assert "AlphaLoop" in str(method)


def test_vakint_tensor_reduce_uses_tensor_only_default_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FakeVakintEngine()
    expr = S("I")

    def fail_default_engine() -> None:
        raise AssertionError("tensor_reduce should not use the full default evaluation engine")

    monkeypatch.setattr(vakint, "default_engine", fail_default_engine)
    monkeypatch.setattr(vakint, "default_tensor_reduction_engine", lambda: engine)

    assert canonical_string(vakint.tensor_reduce(expr)) == canonical_string(S("reduced")(expr))
    assert [name for name, _args in engine.calls] == ["tensor_reduce"]


def test_vakint_adapters_delegate_integral_operations_to_engine() -> None:
    engine = FakeVakintEngine()
    expr = S("I")

    assert canonical_string(vakint.to_canonical(expr, short_form=True, engine=engine)) == canonical_string(
        S("canonical")(expr)
    )
    assert canonical_string(vakint.tensor_reduce(expr, engine=engine)) == canonical_string(S("reduced")(expr))
    assert canonical_string(vakint.evaluate_integral(expr, engine=engine)) == canonical_string(S("integral")(expr))
    assert canonical_string(vakint.evaluate(expr, engine=engine)) == canonical_string(S("evaluated")(expr))
    assert [name for name, _args in engine.calls] == [
        "to_canonical",
        "tensor_reduce",
        "evaluate_integral",
        "evaluate",
    ]


@pytest.mark.parametrize("operation", [vakint.to_canonical, vakint.evaluate_integral, vakint.evaluate])
def test_vakint_adapters_reject_zero_mass_topologies_before_engine_call(operation: Any) -> None:
    engine = FakeVakintEngine()
    expr = vakint.one_loop_vacuum_integral(S("numerator"), (Expression.num(0), S("M") ** 2))

    with pytest.raises(ValueError, match="zero-mass propagators"):
        operation(expr, engine=engine)

    assert engine.calls == []


@pytest.mark.parametrize("operation", [vakint.to_canonical, vakint.evaluate_integral, vakint.evaluate])
def test_vakint_adapters_reject_mixed_mass_topologies_before_engine_call(operation: Any) -> None:
    engine = FakeVakintEngine()
    expr = vakint.one_loop_vacuum_integral(S("numerator"), (S("M1") ** 2, S("M2") ** 2))

    with pytest.raises(ValueError, match="mixed-mass topologies"):
        operation(expr, engine=engine)

    assert engine.calls == []


@pytest.mark.parametrize(
    "expr",
    [
        vakint.one_loop_vacuum_integral(S("numerator"), (Expression.num(0), S("M") ** 2)),
        vakint.one_loop_vacuum_integral(S("numerator"), (S("M1") ** 2, S("M2") ** 2)),
    ],
)
def test_vakint_adapters_delegate_tensor_reduction_for_unsupported_analytic_topologies(expr: Expression) -> None:
    engine = FakeVakintEngine()

    assert canonical_string(vakint.tensor_reduce(expr, engine=engine)) == canonical_string(S("reduced")(expr))
    assert [name for name, _args in engine.calls] == ["tensor_reduce"]


def test_vakint_adapters_delegate_single_scale_massive_topologies_to_engine() -> None:
    engine = FakeVakintEngine()
    expr = vakint.one_loop_vacuum_integral(S("numerator"), (S("M") ** 2, S("M") ** 2), powers=(1, 2))

    assert canonical_string(vakint.to_canonical(expr, short_form=True, engine=engine)) == canonical_string(
        S("canonical")(expr)
    )
    assert [name for name, _args in engine.calls] == ["to_canonical"]


def test_vakint_loop_momentum_builders_use_native_tensor_numerator_syntax() -> None:
    mu = S("mu")

    assert canonical_string(vakint.loop_momentum(2)) == canonical_string(S("vakint::k")(2))
    assert canonical_string(vakint.loop_momentum(2, mu)) == canonical_string(S("vakint::k")(2, mu))
    assert canonical_string(vakint.loop_momentum_squared(2, 3)) == canonical_string(S("vakint::k")(2, 3) ** 2)


def test_vakint_lowers_pychete_loop_momentum_numerators_with_symbolica_patterns() -> None:
    mu = S("mu")
    expr = S("x") * s.LoopMomentum(mu) + s.LoopMomentumSquared
    expected = S("x") * S("vakint::k")(3, mu) + S("vakint::k")(3, 7) ** 2

    lowered = vakint.lower_pychete_loop_momentum_numerators(expr, loop_id=3, scalar_index=7)

    assert canonical_string(lowered) == canonical_string(expected)


def test_vakint_lowers_pychete_loop_momentum_index_wrappers_to_backend_safe_symbols() -> None:
    theory = Theory("vakint_safe_loop_index_lowering")
    mu = theory.index("mu")
    lowered = vakint.lower_pychete_loop_momentum_numerators(s.LoopMomentum(mu), loop_id=2)
    index_wildcard = S("vakint_safe_loop_index_")
    match = next(iter(lowered.match(vakint.symbol("k")(2, index_wildcard), partial=False)))
    safe_index = match[index_wildcard]

    assert "pychete::Index" not in canonical_string(lowered)
    assert canonical_string(safe_index) != canonical_string(mu)
    assert canonical_string(vakint.decode_pychete_namespace(theory, vakint.symbol("g")(safe_index, safe_index))) == (
        canonical_string(s.Metric(mu, mu))
    )


def test_vakint_decoder_restores_generated_covariant_commutator_index_labels() -> None:
    theory = Theory("vakint_covariant_commutator_index_decode")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    adjoint = theory.define_representation("SU2L", "adj")
    encoded = vakint.symbol("Index")(S("vakint::covariant_commutator_7_1"), adjoint)
    expected = theory.index(
        theory.symbol("covariant_commutator_7_1", role=SymbolRole.INDEX),
        adjoint,
    )

    decoded = vakint.decode_pychete_namespace(theory, encoded)

    assert canonical_string(decoded) == canonical_string(expected)
    assert "vakint::covariant_commutator" not in canonical_string(decoded)


def test_vakint_decoder_restores_backend_delta_to_pychete_delta() -> None:
    theory = Theory("vakint_delta_decode")
    theory.define_gauge_group("SU2L", s.SU(Expression.num(2)), "gL", "W")
    fund = theory.define_representation("SU2L", "fund")
    left = vakint.symbol("Index")(S("vakint::left"), fund)
    right = vakint.symbol("Index")(S("vakint::right"), s.Bar(fund))
    encoded = vakint.symbol("Delta")(left, right)
    expected = s.Delta(theory.index(S("vakint::left"), fund), theory.index(S("vakint::right"), s.Bar(fund)))

    decoded = vakint.decode_pychete_namespace(theory, encoded)

    assert canonical_string(decoded) == canonical_string(expected)
    assert "vakint::Delta" not in canonical_string(decoded)


def test_vakint_one_loop_vacuum_integral_lowers_pychete_loop_momentum_numerators() -> None:
    mu = S("mu")
    mass_squared = S("M") ** 2
    topology = vakint.one_loop_vacuum_topology((mass_squared,))
    expected = (S("x") * S("vakint::k")(1, mu) + S("vakint::k")(1, 1) ** 2) * topology

    integral = vakint.one_loop_vacuum_integral(S("x") * s.LoopMomentum(mu) + s.LoopMomentumSquared, (mass_squared,))

    assert canonical_string(integral) == canonical_string(expected)


def test_vakint_tensor_reduce_lowers_direct_pychete_loop_momentum_numerators_before_engine_call() -> None:
    engine = FakeVakintEngine()
    mu = S("mu")
    topology = vakint.one_loop_vacuum_topology((S("M") ** 2,))
    expr = s.LoopMomentum(mu) * topology

    vakint.tensor_reduce(expr, engine=engine)

    expected = S("vakint::k")(1, mu) * topology
    assert canonical_string(engine.calls[0][1][0]) == canonical_string(expected)


def test_vakint_tensor_reduce_hides_pychete_index_wrappers_from_engine_vector_slots() -> None:
    engine = FakeVakintEngine()
    theory = Theory("vakint_safe_loop_index_engine")
    mu = theory.index("mu")
    topology = vakint.one_loop_vacuum_topology((S("M") ** 2,))
    expr = s.LoopMomentum(mu) * topology

    vakint.tensor_reduce(expr, engine=engine)

    engine_expr = engine.calls[0][1][0]
    index_wildcard = S("vakint_engine_loop_index_")
    match = next(iter(engine_expr.match(vakint.symbol("k")(1, index_wildcard))))
    safe_index = match[index_wildcard]
    assert "pychete::Index" not in canonical_string(engine_expr)
    assert canonical_string(vakint.decode_pychete_namespace(theory, vakint.symbol("g")(safe_index, safe_index))) == (
        canonical_string(s.Metric(mu, mu))
    )


def test_vakint_one_loop_vacuum_topology_builders_use_native_namespace() -> None:
    m1 = S("M1sq")
    m2 = S("M2sq")
    expected_topology = S("vakint::topo")(
        S("vakint::prop")(1, S("vakint::edge")(1, 1), S("vakint::k")(1), m1, 1)
        * S("vakint::prop")(2, S("vakint::edge")(1, 1), S("vakint::k")(1), m2, 2)
    )

    topology = vakint.one_loop_vacuum_topology((m1, m2), powers=(1, 2))
    integral = vakint.one_loop_vacuum_integral(S("numerator"), (m1, m2), powers=(1, 2))

    assert canonical_string(topology) == canonical_string(expected_topology)
    assert canonical_string(integral) == canonical_string(S("numerator") * expected_topology)


def test_vakint_one_loop_vacuum_topology_combines_equal_mass_powers() -> None:
    m1 = S("M1sq")
    m2 = S("M2sq")
    expected_topology = S("vakint::topo")(
        S("vakint::prop")(1, S("vakint::edge")(1, 1), S("vakint::k")(1), m1, 4)
        * S("vakint::prop")(2, S("vakint::edge")(1, 1), S("vakint::k")(1), m2, 2)
    )

    topology = vakint.one_loop_vacuum_topology((m1, m2, m1), powers=(1, 2, 3))
    integral = vakint.one_loop_vacuum_integral(S("numerator"), (m1, m2, m1), powers=(1, 2, 3))

    assert canonical_string(topology) == canonical_string(expected_topology)
    assert canonical_string(integral) == canonical_string(S("numerator") * expected_topology)


def test_vakint_collect_identical_propagators_sums_matching_signature_powers() -> None:
    mass = S("M") ** 2
    first = vakint.propagator(1, mass, power=3)
    duplicate = vakint.propagator(99, mass, power=-1)
    distinct = vakint.propagator(2, S("N") ** 2, power=4)
    topology = vakint.symbol("topo")(first * duplicate * distinct)
    expected = vakint.symbol("topo")(
        vakint.propagator(1, mass, power=2) * vakint.propagator(2, S("N") ** 2, power=4)
    )

    assert canonical_string(vakint.collect_identical_propagators(topology)) == canonical_string(expected)


def test_vakint_collect_identical_propagators_handles_powered_factors_and_zero_power() -> None:
    mass = S("M") ** 2
    first = vakint.propagator(1, mass, power=2)
    inverse = vakint.propagator(2, mass, power=-6)
    powered_topology = vakint.symbol("topo")(first**3)
    canceled_topology = vakint.symbol("topo")(first**3 * inverse)

    assert canonical_string(vakint.collect_identical_propagators(powered_topology)) == canonical_string(
        vakint.symbol("topo")(vakint.propagator(1, mass, power=6))
    )
    assert canonical_string(vakint.collect_identical_propagators(canceled_topology)) == canonical_string(
        vakint.symbol("topo")(Expression.num(1))
    )


def test_vakint_collect_identical_propagators_accumulates_arbitrary_powered_signatures() -> None:
    mass = S("M") ** 2
    first = vakint.propagator(1, mass, power=2)
    inverse_duplicate = vakint.propagator(7, mass, power=3)
    final_duplicate = vakint.propagator(9, mass, power=5)
    distinct_momentum = vakint.propagator(2, mass, loop_id=2, power=11)
    topology = vakint.symbol("topo")(first**4 * inverse_duplicate**-2 * final_duplicate * distinct_momentum)
    expected = vakint.symbol("topo")(
        vakint.propagator(1, mass, power=7) * vakint.propagator(2, mass, loop_id=2, power=11)
    )

    assert canonical_string(vakint.collect_identical_propagators(topology)) == canonical_string(expected)


def test_vakint_adapters_collect_identical_propagators_before_engine_call() -> None:
    engine = FakeVakintEngine()
    mass = S("M") ** 2
    first = vakint.propagator(1, mass, power=1)
    duplicate = vakint.propagator(9, mass, power=2)
    expr = S("num") * vakint.symbol("topo")(first * duplicate)
    expected = S("num") * vakint.symbol("topo")(vakint.propagator(1, mass, power=3))

    vakint.tensor_reduce(expr, engine=engine)

    assert canonical_string(engine.calls[0][1][0]) == canonical_string(expected)


def test_vakint_decodes_native_pychete_namespace_wrappers() -> None:
    theory = Theory("vakint_decode_wrappers")
    phi = theory.define_field("phi", s.Scalar)
    kappa = theory.define_coupling("kappa")
    native = vakint.symbol("Field")(
        vakint.symbol("phi"),
        vakint.symbol("Scalar"),
        vakint.symbol("List"),
        vakint.symbol("List"),
    ) * vakint.symbol("Coupling")(vakint.symbol("kappa"), vakint.symbol("List"), 0)

    decoded = vakint.decode_pychete_namespace(theory, native)

    assert canonical_string(decoded) == canonical_string(phi() * kappa())


def test_vakint_decodes_native_wilson_term_wrapper() -> None:
    theory = Theory("vakint_decode_wilson_term")
    phi = theory.define_field("phi", s.Scalar)
    left = theory.index("left")
    right = theory.index("right")
    mu = theory.index("mu")
    nu = theory.index("nu")
    native = vakint.symbol("WilsonTerm")(
        vakint.symbol("phi"),
        vakint.symbol("List")(left, right),
        vakint.symbol("List")(mu, nu),
    )

    decoded = vakint.decode_pychete_namespace(theory, native)

    assert canonical_string(decoded) == canonical_string(
        s.WilsonTerm(phi.label, s.List(left, right), s.List(mu, nu))
    )


def test_vakint_tensor_reduction_round_trips_pychete_fields_and_couplings() -> None:
    theory = Theory("vakint_decode_scalar")
    phi = theory.define_field("phi", s.Scalar, mass=("Heavy", "M"))
    kappa = theory.define_coupling("kappa")
    expr = phi() * kappa() * vakint.one_loop_vacuum_topology((theory.mass_expr(phi.definition) ** 2,))

    reduced = vakint.tensor_reduce(expr)
    decoded = vakint.decode_pychete_namespace(theory, reduced)

    assert "vakint::Field" in canonical_string(reduced)
    assert "vakint::Coupling(vakint::kappa" in canonical_string(reduced)
    assert "vakint::Field" not in canonical_string(decoded)
    assert "vakint::Coupling(vakint::kappa" not in canonical_string(decoded)
    assert canonical_string(decoded) == canonical_string(expr)


def test_vakint_tensor_reduction_escapes_short_user_symbols_without_corrupting_vec_helper() -> None:
    theory = Theory("vakint_decode_short_symbol")
    electron = theory.define_field("e", s.Fermion, mass=0)
    higgs = theory.define_field("H", s.Scalar, mass=("Heavy", "M"))
    yukawa = theory.define_coupling("Ye")
    mu = theory.lorentz_index("mu")
    mass = theory.mass_expr(higgs.definition)
    assert mass is not None
    numerator = yukawa() * s.NCM(s.Bar(electron()), s.PR) * s.NCM(s.PL, electron()) * s.LoopMomentum(mu) ** 2
    expr = vakint.one_loop_vacuum_integral(numerator, (mass**2,))

    reduced = vakint.tensor_reduce(expr)
    decoded = vakint.decode_pychete_namespace(theory, reduced)

    assert "v[e]c" not in str(reduced)
    assert "vakint::Field(vakint::e" in canonical_string(reduced)
    assert "vakint::Field" not in canonical_string(decoded)
    assert canonical_string(decoded) != "0"


def test_vakint_tensor_reduction_round_trips_indexed_pychete_fields() -> None:
    theory = Theory("vakint_decode_indexed")
    theory.define_gauge_group("SU2L", s.SU(2), coupling="gL", field="W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=(fund,))
    kappa = theory.define_coupling("kappa")
    index = theory.dummy_index(1, fund)
    expr = higgs(index) * kappa() * vakint.one_loop_vacuum_topology((S("M") ** 2,))

    reduced = vakint.tensor_reduce(expr)
    decoded = vakint.decode_pychete_namespace(theory, reduced)

    assert "vakint::Index" in canonical_string(reduced)
    assert "vakint::Index" not in canonical_string(decoded)
    assert canonical_string(decoded) == canonical_string(expr)


def test_vakint_decodes_native_imaginary_and_pi_symbols() -> None:
    theory = Theory("vakint_decode_builtin_numbers")
    native = vakint.symbol("𝑖") * vakint.symbol("I") * vakint.symbol("𝜋") * vakint.symbol("π")

    decoded = vakint.decode_pychete_namespace(theory, native)

    assert canonical_string(decoded) == canonical_string(-Expression.PI**2)


def test_vakint_decodes_native_metric_and_cg_wrappers() -> None:
    theory = Theory("vakint_decode_metric_cg")
    theory.define_gauge_group("SU2L", s.SU(2), coupling="gL", field="W")
    theory.define_representation("SU2L", "fund")
    gen = theory.cg_tensor_handle("gen_SU2L_fund")
    adj, fund, barred_fund = theory.cg_tensors["gen_SU2L_fund"].representation_exprs
    mu = s.Index(vakint.symbol("mu"), s.Lorentz)
    nu = s.Index(vakint.symbol("nu"), s.Lorentz)
    a = s.Index(vakint.symbol("A"), adj)
    i = s.Index(vakint.symbol("i"), fund)
    j = s.Index(vakint.symbol("j"), barred_fund)
    native = vakint.symbol("g")(
        vakint.symbol("Index")(vakint.symbol("mu"), vakint.symbol("Lorentz")),
        vakint.symbol("Index")(vakint.symbol("nu"), vakint.symbol("Lorentz")),
    ) * vakint.symbol("CG")(
        vakint.symbol("gen_SU2L_fund"),
        vakint.symbol("List")(
            vakint.symbol("Index")(vakint.symbol("A"), vakint.symbol("SU2L")(vakint.symbol("adj"))),
            vakint.symbol("Index")(vakint.symbol("i"), vakint.symbol("SU2L")(vakint.symbol("fund"))),
            vakint.symbol("Index")(
                vakint.symbol("j"),
                vakint.symbol("Bar")(vakint.symbol("SU2L")(vakint.symbol("fund"))),
            ),
        ),
    )

    decoded = vakint.decode_pychete_namespace(theory, native)

    assert "vakint::g" not in canonical_string(decoded)
    assert "vakint::CG" not in canonical_string(decoded)
    assert canonical_string(decoded) == canonical_string(s.Metric(mu, nu) * gen(a, i, j))


def test_vakint_decodes_generated_metric_indices_for_field_strength_simplification() -> None:
    theory = Theory("vakint_decode_generated_metric_indices")
    theory.define_gauge_group("SU2L", s.SU(2), coupling="gL", field="W")
    vector = theory.field_handle("W")
    mu = s.Index(vakint.symbol("mu"), s.Lorentz)
    right = s.Index(S("pychete::wilson_line_probe_1"), s.Lorentz)
    expected_strength = s.FieldStrength(vector.label, s.List(right, mu), s.List(), s.List())
    native = vakint.symbol("g")(
        vakint.symbol("Index")(
            S(f"{theory.name}::index_wilson_line_probe_0"),
            vakint.symbol("Lorentz"),
        ),
        vakint.symbol("Index")(
            S(f"{theory.name}::index_wilson_line_probe_1"),
            vakint.symbol("Lorentz"),
        ),
    ) * vakint.symbol("FieldStrength")(
        vakint.symbol("W"),
        vakint.symbol("List")(
            vakint.symbol("Index")(vakint.symbol("wilson_line_probe_0"), vakint.symbol("Lorentz")),
            vakint.symbol("Index")(vakint.symbol("mu"), vakint.symbol("Lorentz")),
        ),
        vakint.symbol("List"),
        vakint.symbol("List"),
    ) * vakint.symbol("FieldStrength")(
        vakint.symbol("W"),
        vakint.symbol("List")(
            vakint.symbol("Index")(vakint.symbol("wilson_line_probe_1"), vakint.symbol("Lorentz")),
            vakint.symbol("Index")(vakint.symbol("mu"), vakint.symbol("Lorentz")),
        ),
        vakint.symbol("List"),
        vakint.symbol("List"),
    )

    decoded = vakint.decode_pychete_namespace(theory, native)
    simplified = idenso.simplify_pychete_field_strength_metrics(decoded)

    assert canonical_string(simplified) == canonical_string(expected_strength**2)


def test_vakint_decodes_native_ncm_wrappers_before_projection() -> None:
    theory = Theory("vakint_decode_ncm")
    phi = theory.define_field("phi", s.Scalar)
    kappa = theory.define_coupling("kappa")
    native = vakint.symbol("NCM")(
        vakint.symbol("Field")(
            vakint.symbol("phi"),
            vakint.symbol("Scalar"),
            vakint.symbol("List"),
            vakint.symbol("List"),
        ),
        vakint.symbol("Coupling")(vakint.symbol("kappa"), vakint.symbol("List"), 0),
    )

    decoded = vakint.decode_pychete_namespace(theory, native)

    assert "vakint::NCM" not in canonical_string(decoded)
    assert "pychete::NCM" not in canonical_string(decoded)
    assert canonical_string(decoded) == canonical_string(phi() * kappa())


def test_vakint_decodes_native_covariant_derivative_wrappers() -> None:
    theory = Theory("vakint_decode_cd")
    theory.define_gauge_group("SU2L", s.SU(2), coupling="gL", field="W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=(fund,))
    mu = s.Index(vakint.symbol("mu"), s.Lorentz)
    i = s.Index(vakint.symbol("i"), fund)
    native = vakint.symbol("CD")(
        vakint.symbol("List")(
            vakint.symbol("Index")(vakint.symbol("mu"), vakint.symbol("Lorentz")),
        ),
        vakint.symbol("Field")(
            vakint.symbol("H"),
            vakint.symbol("Scalar"),
            vakint.symbol("List")(
                vakint.symbol("Index")(vakint.symbol("i"), vakint.symbol("SU2L")(vakint.symbol("fund"))),
            ),
            vakint.symbol("List"),
        ),
    )

    decoded = vakint.decode_pychete_namespace(theory, native)

    assert "vakint::CD" not in canonical_string(decoded)
    assert "vakint::List" not in canonical_string(decoded)
    assert canonical_string(decoded) == canonical_string(s.CD(s.List(mu), higgs(i)))


def test_vakint_tensor_reduction_decodes_metric_and_cg_wrappers() -> None:
    theory = Theory("vakint_decode_reduced_metric_cg")
    theory.define_gauge_group("SU2L", s.SU(2), coupling="gL", field="W")
    fund = theory.define_representation("SU2L", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=(fund,))
    kappa = theory.define_coupling("kappa")
    adj = theory.cg_tensors["gen_SU2L_fund"].representation_exprs[0]
    mu = theory.index("mu")
    nu = theory.index("nu")
    a = theory.index("A", adj)
    i = theory.dummy_index(1, fund)
    j = theory.dummy_index(2, fund)
    mass = S("M") ** 2
    numerator = (
        kappa()
        * s.LoopMomentum(mu)
        * s.LoopMomentum(nu)
        * higgs(i)
        * s.Bar(higgs(j))
        * theory.cg_tensor_handle("gen_SU2L_fund")(a, i, j)
    )
    reduced = vakint.tensor_reduce(vakint.one_loop_vacuum_integral(numerator, (mass,)))
    decoded = vakint.decode_pychete_namespace(theory, reduced)

    assert "vakint::g" in canonical_string(reduced)
    assert "vakint::CG" in canonical_string(reduced)
    assert "vakint::g" not in canonical_string(decoded)
    assert "vakint::CG" not in canonical_string(decoded)
    assert "pychete::Metric" in canonical_string(decoded)
    assert "pychete::CG" in canonical_string(decoded)


def test_vakint_adapters_delegate_numerical_operations_to_engine() -> None:
    engine = FakeVakintEngine()
    expr = S("series")
    params = {"m": 1.0}
    externals = {1: (1.0, 0.0, 0.0, 0.0)}

    assert vakint.numerical_result_from_expression(expr, engine=engine) == "numerical-result"
    assert canonical_string(vakint.numerical_result_to_expression("result", engine=engine)) == canonical_string(
        S("epsilon_series")
    )
    assert vakint.numerical_evaluation("integral", params, externals, engine=engine) == ("value", None)
    assert [name for name, _args in engine.calls] == [
        "numerical_result_from_expression",
        "numerical_result_to_expression",
        "numerical_evaluation",
    ]


def test_vakint_laurent_helpers_use_symbolica_coefficients() -> None:
    eps = vakint.epsilon_symbol()
    a = S("a")
    b = S("b")
    c = S("c")
    d = S("d")
    expr = a / eps**2 + b / eps + c + d * eps

    assert canonical_string(vakint.epsilon_coefficient(expr, -2)) == canonical_string(a)
    assert canonical_string(vakint.epsilon_coefficient(expr, -1)) == canonical_string(b)
    assert canonical_string(vakint.epsilon_coefficient(expr, 0)) == canonical_string(c)
    assert canonical_string(vakint.epsilon_coefficient(expr, 1)) == canonical_string(d)
    assert canonical_string(vakint.epsilon_coefficient(expr, 2)) == "0"
    assert canonical_string(vakint.pole_part(expr, max_pole_order=2)) == canonical_string(a / eps**2 + b / eps)
    assert canonical_string(vakint.finite_part(expr)) == canonical_string(c)
    assert canonical_string(vakint.through_finite_part(expr, max_pole_order=2)) == canonical_string(
        a / eps**2 + b / eps + c
    )

    with pytest.raises(ValueError, match="max_pole_order"):
        vakint.pole_part(expr, max_pole_order=0)


def test_vakint_laurent_helpers_expand_epsilon_rational_terms_with_series() -> None:
    eps = vakint.epsilon_symbol()
    pole = S("pole")
    finite = S("finite")
    rational = pole / (eps * (eps - 2)) + finite / (eps - 2)

    assert canonical_string(vakint.epsilon_coefficient(rational, -1)) == canonical_string(-pole / 2)
    assert canonical_string(vakint.finite_part(rational)) == canonical_string(-pole / 4 - finite / 2)


def test_vakint_laurent_helpers_accept_custom_epsilon_symbol() -> None:
    eps = S("custom_eps")
    expr = S("pole") / eps + S("finite")

    assert canonical_string(vakint.epsilon_coefficient(expr, -1, epsilon=eps)) == canonical_string(S("pole"))
    assert canonical_string(vakint.finite_part(expr, epsilon=eps)) == canonical_string(S("finite"))
    assert canonical_string(vakint.pole_part(expr, epsilon=eps)) == canonical_string(S("pole") / eps)
