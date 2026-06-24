from __future__ import annotations

from symbolica import S

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
