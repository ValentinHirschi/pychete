from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from symbolica import Expression, S

from pychete.backends import vakint
from pychete.symbols import canonical_string, s


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


def test_vakint_method_factories_import_without_engine_creation() -> None:
    method = vakint.new_alphaloop_method()

    assert "AlphaLoop" in str(method)


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

    with pytest.raises(ValueError, match="max_pole_order"):
        vakint.pole_part(expr, max_pole_order=0)


def test_vakint_laurent_helpers_accept_custom_epsilon_symbol() -> None:
    eps = S("custom_eps")
    expr = S("pole") / eps + S("finite")

    assert canonical_string(vakint.epsilon_coefficient(expr, -1, epsilon=eps)) == canonical_string(S("pole"))
    assert canonical_string(vakint.finite_part(expr, epsilon=eps)) == canonical_string(S("finite"))
    assert canonical_string(vakint.pole_part(expr, epsilon=eps)) == canonical_string(S("pole") / eps)
