from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from pychete import ExternalKind, PycheteState, SymbolRole, Theory, canonical_string


def _load_converter() -> ModuleType:
    path = Path("helper_mathematica_scripts/convert_matchete_previous_results.py")
    spec = importlib.util.spec_from_file_location("convert_matchete_previous_results", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_previous_result_converter_predeclares_lhs_wilson_targets_only() -> None:
    converter = _load_converter()
    theory = Theory("previous_converter")
    flavor = theory.define_flavor_index("Flavor", 3)
    theory.define_coupling("gL")
    state = PycheteState()
    state.add_theory(theory)

    refs = converter._add_matching_conditions(
        state,
        theory,
        (
            "{"
            "Coupling[gL, {}, 0] -> Coupling[gL, {}, 0],"
            "Coupling[cHd, {Index[i1_, Flavor], Index[i2_, Flavor]}, 0] -> Coupling[cRhs, {}, 0]"
            "}"
        ),
    )

    assert len(refs) == 2
    assert "gL" not in theory.externals
    assert theory.external_handle("cHd").definition.kind is ExternalKind.WILSON_COEFFICIENT
    assert theory.external_handle("cHd").definition.basis_name == "SMEFT"
    assert [canonical_string(index) for index in theory.external_handle("cHd").definition.index_exprs] == [
        canonical_string(theory.index(theory.symbol("i1", role=SymbolRole.INDEX), flavor.symbol)),
        canonical_string(theory.index(theory.symbol("i2", role=SymbolRole.INDEX), flavor.symbol)),
    ]
    assert theory.external_handle("cRhs").definition.kind is ExternalKind.GENERIC
    assert any("previous_converter::external_cHd" in key for key in refs)
    assert canonical_string(state.get_expression("matchete_matching_condition_002")) == (
        "pychete::Coupling(previous_converter::external_cRhs,pychete::List(),0)"
    )
