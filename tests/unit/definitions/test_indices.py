from __future__ import annotations

from pychete import Theory, dummy_indices, open_indices, relabel_dummy_indices, s


def test_open_and_dummy_indices_are_detected_by_full_index_expression() -> None:
    theory = Theory("indices")
    flavor = theory.define_flavor_index("Flavor", 3)
    phi = theory.define_field("phi", s.Scalar, indices=[flavor.symbol], self_conjugate=True, mass=0)
    a = theory.index("a", flavor.symbol)
    b = theory.index("b", flavor.symbol)

    expr = phi(a) * phi(a) * phi(b)

    assert [info.expr for info in dummy_indices(expr)] == [a]
    assert [info.expr for info in open_indices(expr)] == [b]


def test_dummy_relabeling_is_deterministic_per_theory() -> None:
    theory = Theory("indices_relabel")
    flavor = theory.define_flavor_index("Flavor", 3)
    phi = theory.define_field("phi", s.Scalar, indices=[flavor.symbol], self_conjugate=True, mass=0)
    a = theory.index("a", flavor.symbol)

    relabeled = relabel_dummy_indices(theory, phi(a) * phi(a))

    assert "index_d0" in relabeled.format_plain()
    assert "index_a" not in relabeled.format_plain()
