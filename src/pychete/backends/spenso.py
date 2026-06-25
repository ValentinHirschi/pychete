from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from itertools import permutations
from typing import Any

from symbolica import Expression, Replacement

from .common import import_backend
from ..expr import args, as_int, cg_tensor_pattern, is_head, list_expr, list_items
from ..symbols import SymbolDataKey, SymbolRole, canonical_string, display_string, s, safe_symbol_name
from ..theory import Theory
from ..theory_metadata import CGTensorDefinition, CGTensorHandle, RepresentationReality

TensorComponent = Expression | int | float | complex


def cg_tensor_component_expression(dimensions: Sequence[int], components: Sequence[Expression | int]) -> Expression:
    """Encode dense row-major CG component data as pychete-owned Symbolica metadata."""

    dimension_exprs = tuple(Expression.num(int(dimension)) for dimension in dimensions)
    component_exprs = tuple(component if isinstance(component, Expression) else Expression.num(int(component)) for component in components)
    count = 1
    for dimension in dimensions:
        count *= int(dimension)
    if len(component_exprs) != count:
        raise ValueError(f"CG tensor component data expects {count} components, got {len(component_exprs)}")
    return list_expr(list_expr(*dimension_exprs), list_expr(*component_exprs))


def cg_tensor_components_from_expression(tensor: Expression) -> tuple[tuple[int, ...], tuple[Expression, ...]] | None:
    """Decode pychete's dense CG component metadata expression."""

    if not is_head(tensor, s.List) or len(tensor) != 2:
        return None
    dimensions = tuple(as_int(item) for item in list_items(tensor[0]))
    if any(dimension is None for dimension in dimensions):
        return None
    components = list_items(tensor[1])
    count = 1
    decoded_dimensions = tuple(int(dimension) for dimension in dimensions if dimension is not None)
    for dimension in decoded_dimensions:
        count *= dimension
    if len(components) != count:
        raise ValueError(f"CG tensor component metadata expects {count} components, got {len(components)}")
    return decoded_dimensions, components


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


def native_hep_representation_to_spenso(theory: Theory, representation: Expression) -> Any | None:
    """Lower compatible SU(3) pychete representations to spenso HEP representations."""

    definition = theory.representation_definition(representation)
    group_entry = theory.groups.get(definition.group)
    if group_entry is None or group_entry.get("type") != canonical_string(s.SU(Expression.num(3))):
        return None
    spenso = native_module()
    if definition.name == "fund" and definition.dimension_value == 3:
        native = spenso.Representation.cof(3)
        return native.dual() if theory.is_conjugate_representation(representation) else native
    if definition.name == "adj" and definition.dimension_value == 8:
        return spenso.Representation.coad(8)
    return None


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


def native_hep_cg_tensor_structure_to_spenso(
    theory: Theory,
    cg_tensor: str | Expression | CGTensorDefinition | CGTensorHandle,
) -> Any | None:
    """Lower compatible built-in SU(3) CG tensors to spenso HEP structures."""

    definition = _cg_tensor_definition(theory, cg_tensor)
    representations = tuple(
        native_hep_representation_to_spenso(theory, representation)
        for representation in definition.representation_exprs
    )
    if any(representation is None for representation in representations):
        return None
    spenso = native_module()
    if definition.source_text == "builtin:gen" and len(representations) == 3:
        base_definition = tuple(theory.representation_definition(representation) for representation in definition.representation_exprs)
        if (
            base_definition[0].name == "adj"
            and base_definition[1].name == "fund"
            and theory.is_conjugate_representation(definition.representation_exprs[2])
            and base_definition[2].name == "fund"
        ):
            return spenso.TensorName.t()(*representations)
    if definition.source_text == "builtin:fStruct" and len(representations) == 3:
        if all(theory.representation_definition(representation).name == "adj" for representation in definition.representation_exprs):
            return spenso.TensorName.f()(*representations)
    return None


def indexed_cg_tensor_to_spenso(theory: Theory, expr: Expression, *, native_hep_builtins: bool = False) -> Any:
    """Lower a pychete ``CG(label, indices)`` expression to native spenso indices."""

    if not is_head(expr, s.CG) or len(expr) != 2:
        raise ValueError(f"Expected a pychete CG(label, indices) expression, got {display_string(expr)}")
    structure = native_hep_cg_tensor_structure_to_spenso(theory, expr[0]) if native_hep_builtins else None
    if structure is None:
        structure = cg_tensor_structure_to_spenso(theory, expr[0])
    return structure.index(*_cg_index_labels(expr), cook_indices=True)


def _cg_index_labels(expr: Expression) -> tuple[Expression, ...]:
    return tuple(index[0] if is_head(index, s.Index) and len(index) == 2 else index for index in args(expr[1]))


def _cg_tensor_dimensions(theory: Theory, definition: CGTensorDefinition) -> tuple[int, ...]:
    dimensions = tuple(theory.representation_dimension(representation) for representation in definition.representation_exprs)
    if any(dimension is None for dimension in dimensions):
        raise ValueError(f"CG tensor {definition.name!r} has representation without dimension metadata")
    return tuple(int(dimension) for dimension in dimensions if dimension is not None)


def _permutation_sign(values: tuple[int, ...]) -> int:
    inversions = sum(1 for i, left in enumerate(values) for right in values[i + 1 :] if left > right)
    return -1 if inversions % 2 else 1


def _row_major_index(values: tuple[int, ...], dimension: int) -> int:
    index = 0
    for value in values:
        index = index * dimension + value
    return index


def builtin_cg_tensor_components(
    theory: Theory,
    cg_tensor: str | Expression | CGTensorDefinition | CGTensorHandle,
) -> tuple[int, ...] | None:
    """Return finite component data for supported built-in CG tensors."""

    definition = _cg_tensor_definition(theory, cg_tensor)
    source = definition.source_text
    dimensions = _cg_tensor_dimensions(theory, definition)
    if source == "builtin:del":
        if len(dimensions) != 2 or dimensions[0] != dimensions[1]:
            raise ValueError(f"Delta CG tensor {definition.name!r} must have two equal dimensions")
        dimension = dimensions[0]
        return tuple(1 if i == j else 0 for i in range(dimension) for j in range(dimension))
    if source == "builtin:eps":
        if len(set(dimensions)) != 1 or len(dimensions) != dimensions[0]:
            raise ValueError(f"Epsilon CG tensor {definition.name!r} must have rank equal to its common dimension")
        dimension = dimensions[0]
        components = [0 for _ in range(dimension**dimension)]
        for values in permutations(range(dimension)):
            components[_row_major_index(values, dimension)] = _permutation_sign(values)
        return tuple(components)
    return None


def stored_cg_tensor_components(
    theory: Theory,
    cg_tensor: str | Expression | CGTensorDefinition | CGTensorHandle,
) -> tuple[Expression, ...] | None:
    """Return dense component data stored on a registered CG tensor label."""

    definition = _cg_tensor_definition(theory, cg_tensor)
    tensor = definition.tensor_expr
    if tensor is None:
        return None
    decoded = cg_tensor_components_from_expression(tensor)
    if decoded is None:
        return None
    dimensions, components = decoded
    expected_dimensions = _cg_tensor_dimensions(theory, definition)
    if dimensions != expected_dimensions:
        raise ValueError(
            f"CG tensor {definition.name!r} stores dimensions {dimensions}, "
            f"but its registered representations have dimensions {expected_dimensions}"
        )
    return components


def has_stored_cg_tensor_components(theory: Theory) -> bool:
    """Return whether at least one registered CG tensor stores dense components."""

    return any(stored_cg_tensor_components(theory, definition) is not None for definition in theory.cg_tensors.values())


def _symbolic_cg_components(theory: Theory, definition: CGTensorDefinition, count: int) -> tuple[Expression, ...]:
    return tuple(
        theory.symbol(
            _backend_name("spenso_component", definition.name, str(index)),
            role=SymbolRole.EXTERNAL,
            data={
                SymbolDataKey.NAME.value: _backend_name(definition.name, "component", str(index)),
                SymbolDataKey.CG_TENSOR.value: definition.label,
                SymbolDataKey.CG_SOURCE.value: "generated:spenso_symbolic_component",
            },
            tags=("spenso_component", _backend_name("cg_tensor", definition.name)),
        )
        for index in range(count)
    )


def cg_tensor_library_tensor_to_spenso(
    theory: Theory,
    cg_tensor: str | Expression | CGTensorDefinition | CGTensorHandle,
    *,
    components: Sequence[TensorComponent] | None = None,
    builtin_components: bool = False,
    symbolic_components: bool = False,
) -> Any:
    """Create a native spenso ``LibraryTensor`` for a registered CG tensor."""

    definition = _cg_tensor_definition(theory, cg_tensor)
    structure = cg_tensor_structure_to_spenso(theory, definition)
    if components is not None and symbolic_components:
        raise ValueError("Pass either explicit components or symbolic_components=True, not both")
    if components is None:
        if builtin_components:
            components = builtin_cg_tensor_components(theory, definition)
        if components is None:
            components = stored_cg_tensor_components(theory, definition)
        if components is not None:
            component_values: Sequence[TensorComponent] = tuple(components)
        elif not symbolic_components:
            raise ValueError(
                "CG tensor library registration requires explicit components; "
                "store dense component metadata on the CG tensor label, "
                "pass builtin_components=True for supported built-ins, or "
                "symbolic_components=True to create formal component symbols"
            )
        else:
            component_values = _symbolic_cg_components(theory, definition, len(structure))
    else:
        component_values = tuple(components)
    if len(component_values) != len(structure):
        raise ValueError(
            f"CG tensor {definition.name!r} expects {len(structure)} components, got {len(component_values)}"
        )
    return native_module().LibraryTensor.dense(structure, component_values)


def register_cg_tensor_in_spenso_library(
    theory: Theory,
    cg_tensor: str | Expression | CGTensorDefinition | CGTensorHandle,
    *,
    library: Any | None = None,
    components: Sequence[TensorComponent] | None = None,
    builtin_components: bool = False,
    symbolic_components: bool = False,
) -> Any:
    """Register one pychete CG tensor in a native spenso ``TensorLibrary``."""

    tensor_library = empty_tensor_library() if library is None else library
    tensor_library.register(
        cg_tensor_library_tensor_to_spenso(
            theory,
            cg_tensor,
            components=components,
            builtin_components=builtin_components,
            symbolic_components=symbolic_components,
        )
    )
    return tensor_library


def cg_tensor_library_to_spenso(
    theory: Theory,
    *,
    library: Any | None = None,
    components_by_name: Mapping[str, Sequence[TensorComponent]] | None = None,
    builtin_components: bool = False,
    symbolic_components: bool = False,
) -> Any:
    """Register pychete CG tensors in a native spenso ``TensorLibrary``."""

    has_stored_components = has_stored_cg_tensor_components(theory)
    if components_by_name is None and not builtin_components and not symbolic_components and not has_stored_components:
        raise ValueError(
            "CG tensor library construction requires components_by_name, "
            "stored CG tensor component metadata, builtin_components=True, "
            "or symbolic_components=True"
        )
    tensor_library = empty_tensor_library() if library is None else library
    explicit_components = {} if components_by_name is None else dict(components_by_name)
    unknown = sorted(set(explicit_components) - set(theory.cg_tensors))
    if unknown:
        raise KeyError(f"Unknown CG tensor component data for {unknown}")
    for name in sorted(theory.cg_tensors):
        components = explicit_components.get(name)
        if components is None and builtin_components:
            components = builtin_cg_tensor_components(theory, name)
        if components is None:
            components = stored_cg_tensor_components(theory, name)
        if components is None and not symbolic_components:
            continue
        register_cg_tensor_in_spenso_library(
            theory,
            name,
            library=tensor_library,
            components=components,
            builtin_components=False,
            symbolic_components=components is None,
        )
    return tensor_library


def lower_cg_tensors_to_spenso(
    theory: Theory,
    expr: Expression,
    *,
    native_hep_builtins: bool = False,
) -> Expression:
    """Replace registered pychete CG atoms by native spenso tensor expressions."""

    pattern = cg_tensor_pattern()

    def lower(match: dict[Expression, Expression]) -> Expression:
        atom = pattern.replace_wildcards(match)
        return indexed_cg_tensor_to_spenso(theory, atom, native_hep_builtins=native_hep_builtins).to_expression()

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
    cg_components_by_name: Mapping[str, Sequence[TensorComponent]] | None = None,
    builtin_cg_components: bool = False,
    native_hep_cg_builtins: bool = False,
    symbolic_cg_components: bool = False,
    function_library: Any | None = None,
    n_steps: int | None = None,
    mode: Any | None = None,
) -> Any:
    """Lower pychete CG tensors and execute a native spenso tensor network."""

    if native_hep_cg_builtins and library is None:
        library = hep_tensor_library(atom=True)
    if (
        cg_components_by_name is not None
        or builtin_cg_components
        or symbolic_cg_components
        or (library is None and has_stored_cg_tensor_components(theory))
    ):
        library = cg_tensor_library_to_spenso(
            theory,
            library=library,
            components_by_name=cg_components_by_name,
            builtin_components=builtin_cg_components,
            symbolic_components=symbolic_cg_components,
        )
    return evaluate_tensor_network(
        lower_cg_tensors_to_spenso(theory, expr, native_hep_builtins=native_hep_cg_builtins),
        library=library,
        function_library=function_library,
        n_steps=n_steps,
        mode=mode,
    )


__all__ = [
    "builtin_cg_tensor_components",
    "cg_tensor_library_tensor_to_spenso",
    "cg_tensor_library_to_spenso",
    "cg_tensor_structure_to_spenso",
    "empty_tensor_library",
    "evaluate_pychete_tensor_network",
    "evaluate_tensor_network",
    "execute_tensor_network",
    "hep_tensor_library",
    "indexed_cg_tensor_to_spenso",
    "lower_cg_tensors_to_spenso",
    "native_module",
    "native_hep_cg_tensor_structure_to_spenso",
    "native_hep_representation_to_spenso",
    "register_cg_tensor_in_spenso_library",
    "representation_to_spenso",
    "TensorComponent",
    "tensor_network",
    "tensor_network_result_scalar",
    "tensor_network_result_tensor",
]
