from __future__ import annotations

from pychete import Theory, canonical_string, dummy_indices, open_indices, relabel_dummy_indices, s
from pychete.indices import _index_counts


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

    assert "index_d0" in canonical_string(relabeled)
    assert "index_a" not in canonical_string(relabeled)


def test_index_counts_use_symbolica_patterns_for_normalized_powers() -> None:
    theory = Theory("index_power_counts")
    flavor = theory.define_flavor_index("Flavor", 3)
    phi = theory.define_field("phi", s.Scalar, indices=[flavor.symbol], self_conjugate=True, mass=0)
    a = theory.index("a", flavor.symbol)
    b = theory.index("b", flavor.symbol)

    counts = _index_counts(phi(a) ** 2 * phi(b))

    assert counts[a] == 2
    assert counts[b] == 1
    assert [info.expr for info in dummy_indices(phi(a) ** 2 * phi(b))] == [a]
    assert [info.expr for info in open_indices(phi(a) ** 2 * phi(b))] == [b]


def test_index_counts_multiply_nested_integer_power_bases() -> None:
    theory = Theory("nested_index_power_counts")
    flavor = theory.define_flavor_index("Flavor", 3)
    a = theory.index("a", flavor.symbol)
    b = theory.index("b", flavor.symbol)

    counts = _index_counts((a**2 + b) ** 3)

    assert counts[a] == 6
    assert counts[b] == 3


def test_index_counts_keep_non_integer_power_base_once() -> None:
    theory = Theory("fractional_index_power_counts")
    flavor = theory.define_flavor_index("Flavor", 3)
    phi = theory.define_field("phi", s.Scalar, indices=[flavor.symbol], self_conjugate=True, mass=0)
    a = theory.index("a", flavor.symbol)

    counts = _index_counts(phi(a) ** s.half)

    assert counts[a] == 1
