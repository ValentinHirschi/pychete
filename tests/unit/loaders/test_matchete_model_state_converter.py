from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from pychete.symbols import SymbolDataKey, canonical_string, s
from pychete.backends import spenso
from pychete.validation_fixtures import load_validation_fixture


def _load_converter() -> ModuleType:
    path = Path("helper_mathematica_scripts/convert_matchete_model_state.py")
    spec = importlib.util.spec_from_file_location("convert_matchete_model_state", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_matchete_model_state_converter_builds_normal_pychete_fixture(tmp_path: Path) -> None:
    converter = _load_converter()
    exported = {
        "schema_version": 1,
        "kind": "matchete_loaded_model_state",
        "generator": "export_matchete_model_state.wls",
        "model": "Synthetic_Model",
        "lagrangian_input_form": (
            "-1/2*Coupling[m, {}, 1]^2*Field[phi, Scalar, {}, {}]^2"
            "-1/24*Coupling[lambda, {}, 0]*Field[phi, Scalar, {}, {}]^4"
        ),
        "flavor_indices": [{"name_input_form": "Flavor", "dimension_input_form": "3"}],
        "gauge_groups": [
            {
                "name_input_form": "U1x",
                "kind": "gauge",
                "group_input_form": "U1",
                "coupling_input_form": "g",
                "field_input_form": "A",
                "abelian": True,
            }
        ],
        "global_groups": [],
        "representations": [],
        "cg_tensors": [],
        "couplings": [
            {
                "name_input_form": "m",
                "indices_input_form": [],
                "eft_order": 1,
                "mass_dimension": 1,
                "self_conjugate_input_form": "True",
                "symmetries_input_form": "{}",
                "diagonal_coupling": [],
                "thermal_power_counting": 1,
                "unitary": False,
            },
            {
                "name_input_form": "A",
                "indices_input_form": ["Flavor", "Flavor"],
                "eft_order": 0,
                "self_conjugate_input_form": "False",
                "symmetries_input_form": "<|{1, 2} -> 1, {2, 1} -> -1|>",
                "diagonal_coupling": [False, False],
                "thermal_power_counting": 1,
                "unitary": False,
            },
            {
                "name_input_form": "S",
                "indices_input_form": ["Flavor", "Flavor"],
                "eft_order": 0,
                "self_conjugate_input_form": "False",
                "symmetries_input_form": "Association[{1, 2} -> 1, {2, 1} -> 1]",
                "diagonal_coupling": [False, False],
                "thermal_power_counting": 1,
                "unitary": False,
            },
            {
                "name_input_form": "lambda",
                "indices_input_form": [],
                "eft_order": 0,
                "self_conjugate_input_form": "True",
                "symmetries_input_form": "{}",
                "diagonal_coupling": [],
                "thermal_power_counting": 1,
                "unitary": False,
            }
        ],
        "fields": [
            {
                "name_input_form": "phi",
                "type_input_form": "Scalar",
                "indices_input_form": [],
                "charges_input_form": [],
                "self_conjugate": True,
                "chirality_input_form": "False",
                "mass_input_form": "m",
                "heavy": False,
                "zero_mode": False,
                "field_role": "physical",
                "propagating": True,
            }
        ],
    }

    fixture_obj, warnings = converter.build_fixture_from_model_state(exported)
    assert warnings == []
    assert fixture_obj["source"]["matchete_runtime_required"] is False
    assert fixture_obj["expressions"] == ["lagrangian"]

    path = tmp_path / "Synthetic_Model.model_fixture.json"
    path.write_text(json.dumps(fixture_obj), encoding="utf-8")
    fixture = load_validation_fixture(path)
    theory = fixture.theory()

    assert sorted(theory.fields) == ["A", "phi"]
    assert sorted(theory.couplings) == ["A", "S", "g", "lambda", "m"]
    assert theory.groups["U1x"]["field"] == "A"
    assert theory.coupling_handle("g").definition.canonical_mass_dimension == 0
    assert theory.coupling_handle("m").definition.canonical_mass_dimension == 1
    assert theory.coupling_handle("lambda").definition.canonical_mass_dimension == 0
    lagrangian_string = canonical_string(fixture.expression("lagrangian"))
    assert lagrangian_string.count("field_phi") == 2
    assert "coupling_lambda" in lagrangian_string
    antisymmetric = theory.coupling_handle("A").definition
    symmetric = theory.coupling_handle("S").definition
    assert [canonical_string(expr) for expr in antisymmetric.symmetry_exprs] == [
        canonical_string(s.AntisymmetricPermutation(2, 1))
    ]
    assert [canonical_string(expr) for expr in symmetric.symmetry_exprs] == [
        canonical_string(s.SymmetricPermutation(2, 1))
    ]
    assert antisymmetric.label.get_symbol_data(SymbolDataKey.SYMMETRIES.value) == [
        s.AntisymmetricPermutation(2, 1)
    ]


def test_matchete_model_state_exporter_documents_loaded_state_contract() -> None:
    text = Path("helper_mathematica_scripts/export_matchete_model_state.wls").read_text(encoding="utf-8")

    assert '"matchete_loaded_model_state"' in text
    assert "LoadModel[model]" in text
    assert "GetFields[]" in text
    assert "GetCouplings[]" in text
    assert "GetGaugeGroups[]" in text
    assert "GetRepresentations[]" in text


def test_matchete_model_state_converter_decodes_sparse_cg_tensor_components(tmp_path: Path) -> None:
    converter = _load_converter()
    exported = {
        "schema_version": 1,
        "kind": "matchete_loaded_model_state",
        "generator": "export_matchete_model_state.wls",
        "model": "Sparse_CG_Model",
        "lagrangian_input_form": "",
        "flavor_indices": [],
        "gauge_groups": [],
        "global_groups": [
            {
                "name_input_form": "SU2F",
                "kind": "global",
                "group_input_form": "SU @ 2",
                "abelian": False,
            }
        ],
        "representations": [],
        "couplings": [],
        "fields": [],
        "cg_tensors": [
            {
                "name_input_form": "customEps",
                "representations_input_form": ["SU2F[fund]", "SU2F[fund]"],
                "tensor_input_form": (
                    "SparseArray[Automatic, {2, 2}, 0, "
                    "{1, {{0, 1, 2}, {{2}, {1}}}, {Sqrt[3], -1}}]"
                ),
            }
        ],
    }

    fixture_obj, warnings = converter.build_fixture_from_model_state(exported)
    assert warnings == []

    path = tmp_path / "Sparse_CG_Model.model_fixture.json"
    path.write_text(json.dumps(fixture_obj), encoding="utf-8")
    fixture = load_validation_fixture(path)
    theory = fixture.theory()
    definition = theory.cg_tensor_handle("customEps").definition
    decoded = spenso.cg_tensor_components_from_expression(definition.tensor_expr)

    assert decoded is not None
    dimensions, components = decoded
    assert dimensions == (2, 2)
    assert [canonical_string(component) for component in components] == ["0", "sqrt(3)", "-1", "0"]
    assert "SparseArray[Automatic" in (definition.source_text or "")


def test_optional_top_level_matchete_conversion_scripts_are_checked_in_wrappers() -> None:
    wrappers: dict[Path, tuple[Path, ...]] = {
        Path("scripts/export_matchete_model_state.wls"): (
            Path("helper_mathematica_scripts/export_matchete_model_state.wls"),
        ),
        Path("scripts/convert_matchete_model_state.wls"): (
            Path("scripts/export_matchete_model_state.wls"),
            Path("scripts/convert_matchete_model_state.py"),
        ),
        Path("scripts/convert_matchete_model_state.py"): (
            Path("helper_mathematica_scripts/convert_matchete_model_state.py"),
        ),
        Path("scripts/export_matchete_matching_snapshots.wls"): (
            Path("helper_mathematica_scripts/export_matchete_matching_snapshots.wls"),
        ),
        Path("scripts/convert_matchete_previous_results.py"): (
            Path("helper_mathematica_scripts/convert_matchete_previous_results.py"),
        ),
    }

    for wrapper, dependencies in wrappers.items():
        assert wrapper.is_file()
        text = wrapper.read_text(encoding="utf-8")
        for dependency in dependencies:
            assert dependency.is_file()
            assert dependency.parent.name in text
            assert dependency.name in text

    one_command_wrapper = Path("scripts/convert_matchete_model_state.wls").read_text(encoding="utf-8")
    assert "PYTHONPATH=" in one_command_wrapper
    assert "Runtime pychete code and pytest must not call this script" in one_command_wrapper

    readme = " ".join(Path("scripts/README.md").read_text(encoding="utf-8").split())
    assert "not imported by pychete" in readme
    assert "not used by pytest" in readme
    assert "One-command optional export and conversion" in readme
