from __future__ import annotations

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
    assert not hasattr(pychete, "derive_eom")
    assert not hasattr(pychete, "match_tree")
    assert not hasattr(pychete, "solve_heavy_scalar_eoms")

    assert callable(pychete.Theory.derive_eom)
    assert callable(pychete.Theory.solve_heavy_scalar_eoms)
    assert callable(pychete.Theory.match)
