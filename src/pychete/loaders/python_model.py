from __future__ import annotations

import importlib.util
from pathlib import Path

from symbolica import Expression

from ..theory import Theory


def load_python_model(path: str | Path) -> tuple[Theory, dict[str, Expression]]:
    model_path = Path(path)
    spec = importlib.util.spec_from_file_location(f"pychete_model_{model_path.stem}", model_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import Python model from {model_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build = getattr(module, "build", None)
    if build is None:
        raise AttributeError(f"{model_path} does not define build() -> tuple[Theory, dict[str, Expression]]")
    result = build()
    if not isinstance(result, tuple) or len(result) != 2:
        raise TypeError(f"{model_path}.build() must return (Theory, dict[str, Expression])")
    theory, expressions = result
    if not isinstance(theory, Theory):
        raise TypeError(f"{model_path}.build() returned {type(theory).__name__}, not Theory")
    if not isinstance(expressions, dict):
        raise TypeError(f"{model_path}.build() returned {type(expressions).__name__} for expressions, not dict")
    for name, expression in expressions.items():
        if not isinstance(name, str):
            raise TypeError(f"{model_path}.build() returned a non-string expression name: {name!r}")
        if not isinstance(expression, Expression):
            raise TypeError(f"{model_path}.build() expression {name!r} is {type(expression).__name__}, not Expression")
        theory._validate_registered_expression(expression)
    return theory, expressions
