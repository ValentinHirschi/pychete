from __future__ import annotations

from typing import Any

from symbolica import Expression

from .common import import_backend


def native_module():
    """Return the native spenso Python module."""

    return import_backend("symbolica.community.spenso")


def empty_tensor_library() -> Any:
    """Create an empty native spenso tensor library."""

    return native_module().TensorLibrary.construct()


def hep_tensor_library(*, atom: bool = False) -> Any:
    """Create spenso's built-in HEP tensor library."""

    tensor_library = native_module().TensorLibrary
    if atom:
        return tensor_library.hep_lib_atom()
    return tensor_library.hep_lib()


def tensor_network(expr: Expression | Any, *, library: Any | None = None) -> Any:
    """Build a native spenso tensor network for an expression."""

    return native_module().TensorNetwork(expr, library)


def execute_tensor_network(
    network: Any,
    *,
    library: Any | None = None,
    function_library: Any | None = None,
    n_steps: int | None = None,
    mode: Any | None = None,
) -> Any:
    """Execute a native spenso tensor network and return the same network."""

    if mode is None:
        network.execute(
            library=library,
            function_library=function_library,
            n_steps=n_steps,
        )
    else:
        network.execute(
            library=library,
            function_library=function_library,
            n_steps=n_steps,
            mode=mode,
        )
    return network


def tensor_network_result_scalar(network: Any) -> Expression:
    """Return a scalar result from an executed native spenso tensor network."""

    return network.result_scalar()


def tensor_network_result_tensor(network: Any, *, library: Any | None = None) -> Any:
    """Return a tensor result from an executed native spenso tensor network."""

    return network.result_tensor(library)


def evaluate_tensor_network(
    expr: Expression | Any,
    *,
    library: Any | None = None,
    function_library: Any | None = None,
    n_steps: int | None = None,
    mode: Any | None = None,
) -> Any:
    """Build and execute a native spenso tensor network for an expression."""

    network = tensor_network(expr, library=library)
    return execute_tensor_network(
        network,
        library=library,
        function_library=function_library,
        n_steps=n_steps,
        mode=mode,
    )


__all__ = [
    "empty_tensor_library",
    "evaluate_tensor_network",
    "execute_tensor_network",
    "hep_tensor_library",
    "native_module",
    "tensor_network",
    "tensor_network_result_scalar",
    "tensor_network_result_tensor",
]
