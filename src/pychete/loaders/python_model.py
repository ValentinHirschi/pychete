from __future__ import annotations

import importlib.util
from pathlib import Path

from ..theory import Theory


def load_python_model(path: str | Path) -> Theory:
    model_path = Path(path)
    spec = importlib.util.spec_from_file_location(f"pychete_model_{model_path.stem}", model_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import Python model from {model_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build = getattr(module, "build", None)
    if build is None:
        raise AttributeError(f"{model_path} does not define build() -> Theory")
    theory = build()
    if not isinstance(theory, Theory):
        raise TypeError(f"{model_path}.build() returned {type(theory).__name__}, not Theory")
    return theory
