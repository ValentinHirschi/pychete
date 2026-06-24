from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALLER_PATH = REPO_ROOT / "dependencies" / "install_dependencies.py"


def load_installer_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("install_dependencies_for_test", INSTALLER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dependency_patch_manifest_lists_discovered_patches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installer = load_installer_module()
    target_dir = tmp_path / "dependency"
    patch_dir = tmp_path / "patches"
    target_dir.mkdir()
    patch_dir.mkdir()
    patch_path = patch_dir / "example.patch"
    patch_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        installer,
        "dependency_patch_specs",
        lambda: (("example", target_dir, patch_dir),),
    )

    assert {
        "dependency": "example",
        "path": str(patch_path),
    } in installer.dependency_patch_manifest_entries()


def test_apply_dependency_patches_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    installer = load_installer_module()
    target_dir = tmp_path / "dependency"
    patch_dir = tmp_path / "patches"
    target_dir.mkdir()
    patch_dir.mkdir()
    (target_dir / "example.txt").write_text("old\n", encoding="utf-8")
    patch_path = patch_dir / "example.patch"
    patch_path.write_text(
        "\n".join(
            [
                "diff --git a/example.txt b/example.txt",
                "--- a/example.txt",
                "+++ b/example.txt",
                "@@ -1 +1 @@",
                "-old",
                "+new",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        installer,
        "dependency_patch_specs",
        lambda: (("example", target_dir, patch_dir),),
    )

    installer.apply_dependency_patches()
    assert (target_dir / "example.txt").read_text(encoding="utf-8") == "new\n"

    installer.apply_dependency_patches()
    assert (target_dir / "example.txt").read_text(encoding="utf-8") == "new\n"
