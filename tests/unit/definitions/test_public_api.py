from __future__ import annotations

import inspect

import pychete
from pychete import api


def test_package_root_reexports_declared_public_api() -> None:
    assert pychete.__all__ == api.__all__
    for name in api.__all__:
        assert getattr(pychete, name) is getattr(api, name)


def test_lagrangian_manipulations_are_theory_methods_not_top_level_exports() -> None:
    assert "derive_eom" not in pychete.__all__
    assert "match_tree" not in pychete.__all__
    assert "solve_heavy_scalar_eoms" not in pychete.__all__
    assert "load_validation_fixture" not in pychete.__all__
    assert not hasattr(pychete, "derive_eom")
    assert not hasattr(pychete, "match_tree")
    assert not hasattr(pychete, "solve_heavy_scalar_eoms")
    assert not hasattr(pychete, "load_validation_fixture")

    assert callable(pychete.Theory.derive_eom)
    assert callable(pychete.Theory.solve_heavy_scalar_eoms)
    assert callable(pychete.Theory.match)


def test_public_api_exports_have_docstrings() -> None:
    missing = [
        name
        for name in pychete.__all__
        if not inspect.getdoc(getattr(pychete, name))
    ]

    assert missing == []


def test_public_api_methods_have_docstrings() -> None:
    method_names = {
        pychete.Theory: [
            "define_index_type",
            "define_flavor_index",
            "index",
            "lorentz_index",
            "dummy_index",
            "define_coupling",
            "define_field",
            "field_handle",
            "coupling_handle",
            "define_gauge_group",
            "group_charge",
            "mass_expr",
            "free_lag",
            "derive_eom",
            "solve_heavy_scalar_eoms",
            "match",
            "to_json_obj",
            "to_json",
            "write_json",
            "from_json_obj",
        ],
        pychete.FieldHandle: ["__call__"],
        pychete.CouplingHandle: ["__call__"],
        pychete.PycheteState: [
            "add_theory",
            "add_expression",
            "get_expression",
            "to_json_obj",
            "to_json",
            "write_json",
            "save_state",
            "from_json_obj",
            "from_json",
            "read_json",
        ],
        pychete.MatchingResult: [
            "expression",
            "expression_names",
            "validate",
        ],
    }
    missing = [
        f"{cls.__name__}.{method_name}"
        for cls, names in method_names.items()
        for method_name in names
        if not inspect.getdoc(getattr(cls, method_name))
    ]

    assert missing == []
