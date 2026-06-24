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


def test_dummy_relabeling_is_deterministic_without_theory_owned_labels() -> None:
    theory = Theory("indices_relabel")
    flavor = theory.define_flavor_index("Flavor", 3)
    phi = theory.define_field("phi", s.Scalar, indices=[flavor.symbol], self_conjugate=True, mass=0)
    a = theory.index("a", flavor.symbol)

    relabeled = relabel_dummy_indices(phi(a) * phi(a))
    canonical = canonical_string(relabeled)

    assert "pychete::index_d0" in canonical
    assert "indices_relabel::index_d0" not in canonical
    assert "pychete::index_a" not in canonical


def test_index_labels_are_central_across_theories() -> None:
    first = Theory("first_indices")
    second = Theory("second_indices")

    assert canonical_string(first.lorentz_index("mu")[0]) == "pychete::index_mu"
    assert canonical_string(first.lorentz_index("mu")[0]) == canonical_string(second.lorentz_index("mu")[0])


def test_same_index_label_with_different_representations_does_not_collide() -> None:
    theory = Theory("index_representation_identity")
    flavor = theory.define_flavor_index("Flavor", 3)
    lorentz_i = theory.index("i", s.Lorentz)
    flavor_i = theory.index("i", flavor.symbol)

    assert canonical_string(lorentz_i[0]) == canonical_string(flavor_i[0])
    assert canonical_string(lorentz_i) != canonical_string(flavor_i)
    assert [info.expr for info in dummy_indices(lorentz_i**2 * flavor_i)] == [lorentz_i]
    assert [info.expr for info in open_indices(lorentz_i**2 * flavor_i)] == [flavor_i]


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
