from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from symbolica import S

from pychete.backends import vakint
from pychete.symbols import canonical_string


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
