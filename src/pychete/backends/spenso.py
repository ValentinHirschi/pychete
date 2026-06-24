from __future__ import annotations

from functools import lru_cache
from typing import Any

from symbolica import Expression, Replacement

from .common import import_backend
from ..expr import args, cg_tensor_pattern, is_head
from ..symbols import SymbolRole, canonical_string, display_string, s, safe_symbol_name
from ..theory import CGTensorDefinition, CGTensorHandle, RepresentationReality, Theory


def native_module():
    """Return the native spenso Python module."""

    return import_backend("symbolica.community.spenso")


def _backend_name(*parts: str) -> str:
    return safe_symbol_name("_".join(parts))


@lru_cache(maxsize=None)
def _native_representation(name: str, dimension: int, is_self_dual: bool) -> Any:
    return native_module().Representation(name, dimension, is_self_dual=is_self_dual)


def representation_to_spenso(theory: Theory, representation: Expression) -> Any:
    """Lower a registered pychete representation to a native spenso representation.

    The conversion is metadata-only: pychete uses the registered theory
    representation dimension and reality data, then delegates index-space
    construction to spenso's Rust-backed ``Representation`` object.
    """

    definition = theory.representation_definition(representation)
    dimension = definition.dimension_value
    if dimension is None:
        raise ValueError(f"Cannot lower representation {display_string(definition.expr)} without dimension metadata")
    reality = definition.reality_kind
    is_self_dual = reality in {RepresentationReality.REAL, RepresentationReality.PSEUDOREAL}
    name = _backend_name(
        "pychete",
        theory.name,
        definition.group,
        definition.name,
        f"d{dimension}",
        reality.value,
    )
    native = _native_representation(name, dimension, is_self_dual)
    if theory.is_conjugate_representation(representation):
        return native.dual()
    return native


def _cg_tensor_definition(theory: Theory, cg_tensor: str | Expression | CGTensorDefinition | CGTensorHandle) -> CGTensorDefinition:
    if isinstance(cg_tensor, str):
        return theory.cg_tensors[cg_tensor]
    if isinstance(cg_tensor, CGTensorHandle):
        return cg_tensor.definition
    if isinstance(cg_tensor, CGTensorDefinition):
        return cg_tensor
    label_key = canonical_string(cg_tensor)
    for definition in theory.cg_tensors.values():
        if canonical_string(definition.label) == label_key:
            return definition
    raise KeyError(f"Unknown CG tensor label {label_key!r}")


def cg_tensor_structure_to_spenso(
    theory: Theory,
    cg_tensor: str | Expression | CGTensorDefinition | CGTensorHandle,
) -> Any:
    """Lower registered CG tensor metadata to a native spenso tensor structure."""

    definition = _cg_tensor_definition(theory, cg_tensor)
    tensor_name = native_module().TensorName(_backend_name("pychete", theory.name, "cg", definition.name))
    representations = tuple(representation_to_spenso(theory, representation) for representation in definition.representation_exprs)
    return native_module().TensorStructure(*representations, name=tensor_name)


def indexed_cg_tensor_to_spenso(theory: Theory, expr: Expression) -> Any:
    """Lower a pychete ``CG(label, indices)`` expression to native spenso indices."""

    if not is_head(expr, s.CG) or len(expr) != 2:
        raise ValueError(f"Expected a pychete CG(label, indices) expression, got {display_string(expr)}")
    structure = cg_tensor_structure_to_spenso(theory, expr[0])
    return structure.index(*(args(expr[1])))


def lower_cg_tensors_to_spenso(theory: Theory, expr: Expression) -> Expression:
    """Replace registered pychete CG atoms by native spenso tensor expressions."""

    pattern = cg_tensor_pattern()

    def lower(match: dict[Expression, Expression]) -> Expression:
        atom = pattern.replace_wildcards(match)
        return indexed_cg_tensor_to_spenso(theory, atom).to_expression()

    return expr.replace_multiple(
        [
            Replacement(
                pattern,
                lower,
                s.CGTensorLabelWildcard.req_tag(SymbolRole.CG_TENSOR.value),
            )
        ]
    )


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


def evaluate_pychete_tensor_network(
    theory: Theory,
    expr: Expression,
    *,
    library: Any | None = None,
    function_library: Any | None = None,
    n_steps: int | None = None,
    mode: Any | None = None,
) -> Any:
    """Lower pychete CG tensors and execute a native spenso tensor network."""

    return evaluate_tensor_network(
        lower_cg_tensors_to_spenso(theory, expr),
        library=library,
        function_library=function_library,
        n_steps=n_steps,
        mode=mode,
    )


__all__ = [
    "cg_tensor_structure_to_spenso",
    "empty_tensor_library",
    "evaluate_pychete_tensor_network",
    "evaluate_tensor_network",
    "execute_tensor_network",
    "hep_tensor_library",
    "indexed_cg_tensor_to_spenso",
    "lower_cg_tensors_to_spenso",
    "native_module",
    "representation_to_spenso",
    "tensor_network",
    "tensor_network_result_scalar",
    "tensor_network_result_tensor",
]
