from __future__ import annotations

from importlib import import_module
from typing import Any


class BackendUnavailableError(RuntimeError):
    """Raised when a required native pychete backend cannot be imported."""


def import_backend(module_name: str) -> Any:
    """Import a native backend module and convert import failures to pychete errors."""

    try:
        return import_module(module_name)
    except ImportError as exc:
        raise BackendUnavailableError(
            f"Native backend {module_name!r} is unavailable. "
            "Run dependencies/install_dependencies.py and use dependencies/.venv."
        ) from exc


__all__ = ["BackendUnavailableError", "import_backend"]
