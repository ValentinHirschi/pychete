from __future__ import annotations

from symbolica import Expression, S

from pychete import RepresentationReality, SymbolDataKey, SymbolRole, Theory, s
from pychete.backends import spenso
from pychete.symbols import canonical_string


def test_spenso_backend_constructs_native_tensor_libraries() -> None:
    empty_library = spenso.empty_tensor_library()
    hep_library = spenso.hep_tensor_library()
    atom_hep_library = spenso.hep_tensor_library(atom=True)

    assert type(empty_library).__name__ == "TensorLibrary"
    assert type(hep_library).__name__ == "TensorLibrary"
    assert type(atom_hep_library).__name__ == "TensorLibrary"


def test_spenso_backend_exposes_tensor_network_execution() -> None:
    network = spenso.tensor_network(S("x") + 1)
    executed = spenso.execute_tensor_network(network)

    assert executed is network
    assert canonical_string(spenso.tensor_network_result_scalar(network)) == canonical_string(S("x") + 1)


def test_spenso_backend_builds_and_executes_tensor_network() -> None:
    network = spenso.evaluate_tensor_network(S("x") + 2)

    assert canonical_string(spenso.tensor_network_result_scalar(network)) == canonical_string(S("x") + 2)


def test_spenso_backend_lowers_registered_representations() -> None:
    theory = Theory("spenso_bridge_reps")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    su3_fund = theory.define_representation("SU3c", "fund")
    su2_fund = theory.define_representation("SU2F", "fund")

    native_fund = spenso.representation_to_spenso(theory, su3_fund)
    native_conjugate = spenso.representation_to_spenso(theory, s.Bar(su3_fund))
    native_pseudoreal = spenso.representation_to_spenso(theory, s.Bar(su2_fund))

    assert type(native_fund).__name__ == "Representation"
    assert canonical_string(native_fund.to_expression()) == "spenso::pychete_spenso_bridge_reps_SU3c_fund_d3_complex(3)"
    assert (
        canonical_string(native_conjugate.to_expression())
        == "spenso::dind(spenso::pychete_spenso_bridge_reps_SU3c_fund_d3_complex(3))"
    )
    assert canonical_string(native_pseudoreal.to_expression()) == (
        "spenso::pychete_spenso_bridge_reps_SU2F_fund_d2_pseudoreal(2)"
    )


def test_spenso_backend_lowers_compatible_su3_representations_to_native_hep_reps() -> None:
    theory = Theory("spenso_bridge_hep_reps")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    su3_fund = theory.define_representation("SU3c", "fund")
    su3_adj = theory.define_representation("SU3c", "adj")
    su2_fund = theory.define_representation("SU2F", "fund")

    native_fund = spenso.native_hep_representation_to_spenso(theory, su3_fund)
    native_conjugate = spenso.native_hep_representation_to_spenso(theory, s.Bar(su3_fund))
    native_adj = spenso.native_hep_representation_to_spenso(theory, su3_adj)

    assert canonical_string(native_fund.to_expression()) == "spenso::cof(3)"
    assert canonical_string(native_conjugate.to_expression()) == "spenso::dind(spenso::cof(3))"
    assert canonical_string(native_adj.to_expression()) == "spenso::coad(8)"
    assert spenso.native_hep_representation_to_spenso(theory, su2_fund) is None


def test_spenso_backend_lowers_registered_cg_tensors() -> None:
    theory = Theory("spenso_bridge_cg")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    generator = theory.cg_tensor_handle("gen_SU3c_fund")
    indexed_expr = generator(S("A"), S("i"), S("j"))

    structure = spenso.cg_tensor_structure_to_spenso(theory, generator)
    indexed = spenso.indexed_cg_tensor_to_spenso(theory, indexed_expr)
    indexed_text = canonical_string(indexed.to_expression())

    assert type(structure).__name__ == "TensorStructure"
    assert len(structure) == 72
    assert canonical_string(structure.get_name().to_expression()) == "spenso_python::pychete_spenso_bridge_cg_cg_gen_SU3c_fund"
    assert indexed_text == (
        "spenso_python::pychete_spenso_bridge_cg_cg_gen_SU3c_fund("
        "spenso::pychete_spenso_bridge_cg_SU3c_adj_d8_real(8,python::A),"
        "spenso::pychete_spenso_bridge_cg_SU3c_fund_d3_complex(3,python::i),"
        "spenso::dind(spenso::pychete_spenso_bridge_cg_SU3c_fund_d3_complex(3,python::j)))"
    )


def test_spenso_backend_lowers_compatible_su3_cg_tensors_to_native_hep_tensors() -> None:
    theory = Theory("spenso_bridge_hep_cg")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    generator = theory.cg_tensor_handle("gen_SU3c_fund")
    fstruct = theory.cg_tensor_handle("fStruct_SU3c")

    gen_structure = spenso.native_hep_cg_tensor_structure_to_spenso(theory, generator)
    f_structure = spenso.native_hep_cg_tensor_structure_to_spenso(theory, fstruct)
    gen_indexed = spenso.indexed_cg_tensor_to_spenso(
        theory,
        generator(S("A"), S("i"), S("j")),
        native_hep_builtins=True,
    )
    f_indexed = spenso.indexed_cg_tensor_to_spenso(
        theory,
        fstruct(S("A"), S("B"), S("C")),
        native_hep_builtins=True,
    )

    assert canonical_string(gen_structure.get_name().to_expression()) == "spenso::t"
    assert canonical_string(f_structure.get_name().to_expression()) == "spenso::f"
    assert canonical_string(gen_indexed.to_expression()) == (
        "spenso::t(spenso::coad(8,python::A),spenso::cof(3,python::i),spenso::dind(spenso::cof(3,python::j)))"
    )
    f_text = canonical_string(f_indexed.to_expression())
    assert "spenso::f(" in f_text
    assert all(label in f_text for label in ("python::A", "python::B", "python::C"))
    assert spenso.native_hep_cg_tensor_structure_to_spenso(theory, "gen_SU2F_fund") is None


def test_spenso_backend_lowers_cg_atoms_with_symbolica_replacement() -> None:
    theory = Theory("spenso_bridge_lower")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    generator = theory.cg_tensor_handle("gen_SU3c_fund")

    expr = S("x") + 2 * generator(S("A"), S("i"), S("j")) + s.CG(S("plain"), s.List(S("u")))
    lowered = spenso.lower_cg_tensors_to_spenso(theory, expr)
    lowered_text = canonical_string(lowered)

    assert "spenso_python::pychete_spenso_bridge_lower_cg_gen_SU3c_fund" in lowered_text
    assert "pychete::CG(python::plain,pychete::List(python::u))" in lowered_text
    assert "spenso::dind(spenso::pychete_spenso_bridge_lower_SU3c_fund_d3_complex(3,python::j))" in lowered_text


def test_spenso_backend_lowers_cg_atoms_with_native_hep_builtins() -> None:
    theory = Theory("spenso_bridge_hep_lower")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    generator = theory.cg_tensor_handle("gen_SU3c_fund")

    lowered = spenso.lower_cg_tensors_to_spenso(
        theory,
        S("x") + generator(S("A"), S("i"), S("j")),
        native_hep_builtins=True,
    )
    lowered_text = canonical_string(lowered)

    assert "spenso::t(spenso::coad(8,python::A),spenso::cof(3,python::i),spenso::dind(spenso::cof(3,python::j)))" in lowered_text
    assert "pychete::CG" not in lowered_text


def test_spenso_backend_lowers_generated_non_abelian_derivative_cg_tensors() -> None:
    theory = Theory("spenso_bridge_generated_nonabelian_cd")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    fund = theory.define_representation("SU3c", "fund")
    higgs = theory.define_field("H", s.Scalar, indices=[fund], mass=0)
    mu = theory.dummy_index(0)
    index = theory.index("i", fund)
    expanded = theory.expand_non_abelian_covariant_derivatives(
        s.Bar(higgs(index, derivatives=[mu])) * higgs(index, derivatives=[mu])
    )

    lowered = spenso.lower_cg_tensors_to_spenso(theory, expanded, native_hep_builtins=True)
    lowered_text = canonical_string(lowered)

    assert "pychete::CG" not in lowered_text
    assert "spenso::t(" in lowered_text
    assert "spenso_bridge_generated_nonabelian_cd::index_covariant_derivative_0_1" in lowered_text
    assert "spenso_bridge_generated_nonabelian_cd::index_covariant_derivative_1_1" in lowered_text


def test_spenso_backend_evaluates_pychete_tensor_network_after_cg_lowering(monkeypatch) -> None:
    theory = Theory("spenso_bridge_eval")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    generator = theory.cg_tensor_handle("gen_SU3c_fund")
    expr = generator(S("A"), S("i"), S("j"))
    calls: list[Expression] = []

    class FakeNetwork:
        def __init__(self, lowered: Expression) -> None:
            self.lowered = lowered

    def fake_evaluate_tensor_network(lowered: Expression, **_kwargs) -> FakeNetwork:
        calls.append(lowered)
        return FakeNetwork(lowered)

    monkeypatch.setattr(spenso, "evaluate_tensor_network", fake_evaluate_tensor_network)

    network = spenso.evaluate_pychete_tensor_network(theory, expr)

    assert isinstance(network, FakeNetwork)
    assert calls == [network.lowered]
    assert canonical_string(calls[0]).startswith("spenso_python::pychete_spenso_bridge_eval_cg_gen_SU3c_fund(")


def test_spenso_backend_evaluates_pychete_tensor_network_with_native_hep_builtins(monkeypatch) -> None:
    theory = Theory("spenso_bridge_eval_hep")
    theory.define_gauge_group("SU3c", s.SU(Expression.num(3)), "gs", "G")
    generator = theory.cg_tensor_handle("gen_SU3c_fund")
    calls: list[tuple[Expression, object | None]] = []

    class FakeNetwork:
        def __init__(self, lowered: Expression) -> None:
            self.lowered = lowered

    def fake_evaluate_tensor_network(lowered: Expression, **kwargs) -> FakeNetwork:
        calls.append((lowered, kwargs["library"]))
        return FakeNetwork(lowered)

    monkeypatch.setattr(spenso, "evaluate_tensor_network", fake_evaluate_tensor_network)

    network = spenso.evaluate_pychete_tensor_network(
        theory,
        generator(S("A"), S("i"), S("j")),
        native_hep_cg_builtins=True,
    )

    assert isinstance(network, FakeNetwork)
    assert canonical_string(calls[0][0]).startswith("spenso::t(")
    assert type(calls[0][1]).__name__ == "TensorLibrary"


def test_spenso_backend_registers_cg_tensor_components_in_native_library() -> None:
    theory = Theory("spenso_bridge_library")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    eps = theory.cg_tensor_handle("eps_SU2F")
    components = tuple(S(f"eps{i}") for i in range(4))

    tensor = spenso.cg_tensor_library_tensor_to_spenso(theory, eps, components=components)
    library = spenso.register_cg_tensor_in_spenso_library(theory, eps, components=components)
    structure = spenso.cg_tensor_structure_to_spenso(theory, eps)
    registered = library[structure.get_name().to_expression()]

    assert type(tensor).__name__ == "LibraryTensor"
    assert canonical_string(tensor.structure().get_name().to_expression()) == "spenso_python::pychete_spenso_bridge_library_cg_eps_SU2F"
    assert type(registered).__name__ == "TensorStructure"
    assert len(registered) == 4
    assert canonical_string(registered.get_name().to_expression()) == "spenso_python::pychete_spenso_bridge_library_cg_eps_SU2F"


def test_spenso_backend_uses_stored_cg_tensor_component_metadata() -> None:
    theory = Theory("spenso_bridge_stored_library")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    fund = theory.define_representation("SU2F", "fund")
    tensor_data = spenso.cg_tensor_component_expression(
        (2, 2),
        (Expression.num(0), S("a"), -S("a"), Expression.num(0)),
    )
    custom = theory.define_cg_tensor("custom_eps", (fund, fund), tensor=tensor_data, source="unit-test")

    components = spenso.stored_cg_tensor_components(theory, custom)
    library = spenso.cg_tensor_library_to_spenso(theory)
    structure = spenso.cg_tensor_structure_to_spenso(theory, custom)
    registered = library[structure.get_name().to_expression()]

    assert components is not None
    assert [canonical_string(component) for component in components] == ["0", "python::a", "-python::a", "0"]
    assert type(registered).__name__ == "TensorStructure"
    assert len(registered) == 4


def test_spenso_backend_auto_registers_stored_cg_components_for_tensor_network(monkeypatch) -> None:
    theory = Theory("spenso_bridge_auto_stored_library")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    fund = theory.define_representation("SU2F", "fund")
    custom = theory.define_cg_tensor(
        "custom_eps",
        (fund, fund),
        tensor=spenso.cg_tensor_component_expression((2, 2), (Expression.num(0), S("a"), -S("a"), Expression.num(0))),
        source="unit-test",
    )
    calls: list[object | None] = []

    class FakeNetwork:
        def __init__(self, lowered: Expression) -> None:
            self.lowered = lowered

    def fake_evaluate_tensor_network(lowered: Expression, **kwargs) -> FakeNetwork:
        calls.append(kwargs["library"])
        return FakeNetwork(lowered)

    monkeypatch.setattr(spenso, "evaluate_tensor_network", fake_evaluate_tensor_network)

    network = spenso.evaluate_pychete_tensor_network(theory, custom(S("i"), S("j")))

    assert isinstance(network, FakeNetwork)
    assert spenso.has_stored_cg_tensor_components(theory) is True
    assert type(calls[0]).__name__ == "TensorLibrary"


def test_spenso_backend_can_build_symbolic_cg_tensor_library() -> None:
    theory = Theory("spenso_bridge_symbolic_library")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))

    library = spenso.cg_tensor_library_to_spenso(theory, symbolic_components=True)
    structure = spenso.cg_tensor_structure_to_spenso(theory, "eps_SU2F")
    registered = library[structure.get_name().to_expression()]
    component = theory.symbol(
        "spenso_component_eps_SU2F_0",
        role=SymbolRole.EXTERNAL,
    )

    assert type(registered).__name__ == "TensorStructure"
    assert component.get_symbol_data(SymbolDataKey.CG_SOURCE.value) == "generated:spenso_symbolic_component"
    assert component.get_symbol_data(SymbolDataKey.CG_TENSOR.value) == theory.cg_tensor_handle("eps_SU2F").label


def test_spenso_backend_builds_builtin_delta_and_epsilon_components() -> None:
    theory = Theory("spenso_bridge_builtin_components")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))

    assert spenso.builtin_cg_tensor_components(theory, "eps_SU2F") == (0, 1, -1, 0)
    assert spenso.builtin_cg_tensor_components(theory, "del_SU2F_fund") == (1, 0, 0, 1)
    assert spenso.builtin_cg_tensor_components(theory, "gen_SU2F_fund") is None


def test_spenso_backend_registers_supported_builtin_components_only() -> None:
    theory = Theory("spenso_bridge_builtin_library")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))

    library = spenso.cg_tensor_library_to_spenso(theory, builtin_components=True)
    eps_structure = spenso.cg_tensor_structure_to_spenso(theory, "eps_SU2F")
    del_structure = spenso.cg_tensor_structure_to_spenso(theory, "del_SU2F_fund")
    gen_structure = spenso.cg_tensor_structure_to_spenso(theory, "gen_SU2F_fund")

    assert type(library[eps_structure.get_name().to_expression()]).__name__ == "TensorStructure"
    assert type(library[del_structure.get_name().to_expression()]).__name__ == "TensorStructure"
    try:
        library[gen_structure.get_name().to_expression()]
    except RuntimeError as exc:
        assert "invalid key" in str(exc).lower() or "not found" in str(exc).lower() or "missing" in str(exc).lower()
    else:
        raise AssertionError("unsupported generator tensor was registered as a built-in component tensor")


def test_spenso_backend_rejects_cg_library_registration_without_components() -> None:
    theory = Theory("spenso_bridge_library_errors")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    eps = theory.cg_tensor_handle("eps_SU2F")

    try:
        spenso.cg_tensor_library_tensor_to_spenso(theory, eps)
    except ValueError as exc:
        assert "requires explicit components" in str(exc)
    else:
        raise AssertionError("CG tensor library tensor was created without component data")

    try:
        spenso.cg_tensor_library_tensor_to_spenso(theory, eps, components=(S("only_one"),))
    except ValueError as exc:
        assert "expects 4 components" in str(exc)
    else:
        raise AssertionError("CG tensor library tensor accepted the wrong number of components")


def test_spenso_backend_evaluates_pychete_tensor_network_with_registered_cg_library(monkeypatch) -> None:
    theory = Theory("spenso_bridge_eval_library")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    eps = theory.cg_tensor_handle("eps_SU2F")
    calls: list[object] = []

    class FakeNetwork:
        def __init__(self, lowered: Expression) -> None:
            self.lowered = lowered

    def fake_evaluate_tensor_network(lowered: Expression, **kwargs) -> FakeNetwork:
        calls.append(kwargs["library"])
        return FakeNetwork(lowered)

    monkeypatch.setattr(spenso, "evaluate_tensor_network", fake_evaluate_tensor_network)

    network = spenso.evaluate_pychete_tensor_network(
        theory,
        eps(S("i"), S("j")),
        cg_components_by_name={"eps_SU2F": tuple(S(f"eps{i}") for i in range(4))},
    )

    assert isinstance(network, FakeNetwork)
    assert type(calls[0]).__name__ == "TensorLibrary"


def test_spenso_backend_evaluates_pychete_tensor_network_with_builtin_cg_library(monkeypatch) -> None:
    theory = Theory("spenso_bridge_eval_builtin_library")
    theory.define_global_group("SU2F", s.SU(Expression.num(2)))
    eps = theory.cg_tensor_handle("eps_SU2F")
    calls: list[object] = []

    class FakeNetwork:
        def __init__(self, lowered: Expression) -> None:
            self.lowered = lowered

    def fake_evaluate_tensor_network(lowered: Expression, **kwargs) -> FakeNetwork:
        calls.append(kwargs["library"])
        return FakeNetwork(lowered)

    monkeypatch.setattr(spenso, "evaluate_tensor_network", fake_evaluate_tensor_network)

    network = spenso.evaluate_pychete_tensor_network(
        theory,
        eps(S("i"), S("j")),
        builtin_cg_components=True,
    )

    assert isinstance(network, FakeNetwork)
    assert type(calls[0]).__name__ == "TensorLibrary"


def test_spenso_backend_rejects_dimensionless_representations() -> None:
    theory = Theory("spenso_bridge_unknown")
    theory.define_global_group("GX", s.U1)
    representation = theory.define_representation(
        "GX",
        "unknown",
        reality=RepresentationReality.COMPLEX,
    )

    try:
        spenso.representation_to_spenso(theory, representation)
    except ValueError as exc:
        assert "without dimension metadata" in str(exc)
    else:
        raise AssertionError("dimensionless representation was lowered to spenso")
