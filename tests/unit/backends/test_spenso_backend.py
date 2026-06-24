from __future__ import annotations

from symbolica import Expression, S

from pychete import RepresentationReality, Theory, s
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
