from __future__ import annotations

import json
from pathlib import Path

import pytest


DEPENDENCY_MANIFEST = Path(__file__).resolve().parents[1] / "dependencies" / "install_manifest.json"


def test_symbolica_exposes_local_versions() -> None:
    import symbolica

    local_versions = getattr(symbolica, "LOCAL_VERSIONS", None)

    assert isinstance(local_versions, dict)
    assert {"symbolica", "vakint", "spenso", "idenso"} <= set(local_versions)
    assert all(isinstance(local_versions[key], str) and local_versions[key] for key in local_versions)


def test_gammaloop_api_imports_if_requested() -> None:
    if not DEPENDENCY_MANIFEST.exists():
        pytest.skip("dependency manifest is absent; GammaLoop request status is unknown")

    manifest = json.loads(DEPENDENCY_MANIFEST.read_text(encoding="utf-8"))
    if not manifest.get("gammaloop", {}).get("requested", False):
        pytest.skip("GammaLoop API was not requested when dependencies were installed")

    import gammaloop

    assert hasattr(gammaloop, "GammaLoopAPI")
