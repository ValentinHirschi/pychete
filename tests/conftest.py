from __future__ import annotations

from pathlib import Path

import pytest
from symbolica import Expression


def assert_expr_equal(actual: Expression, expected: Expression) -> None:
    diff = (actual - expected).expand()
    assert diff.format_plain() == "0", diff.format_plain()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = Path(str(item.path))
        path_parts = path.parts
        if _path_has_parts(path_parts, ("tests", "unit")):
            item.add_marker(pytest.mark.unit)
        if _path_has_parts(path_parts, ("tests", "integration")):
            item.add_marker(pytest.mark.integration)
        if _path_has_parts(path_parts, ("tests", "unit", "backends")):
            item.add_marker(pytest.mark.backend)
        if _path_has_parts(path_parts, ("tests", "unit", "definitions")):
            item.add_marker(pytest.mark.definitions)
        if _path_has_parts(path_parts, ("tests", "unit", "dependencies")):
            item.add_marker(pytest.mark.dependencies)
        if _path_has_parts(path_parts, ("tests", "unit", "eft")):
            item.add_marker(pytest.mark.eft)
        if _path_has_parts(path_parts, ("tests", "unit", "functional")):
            item.add_marker(pytest.mark.functional)
        if _path_has_parts(path_parts, ("tests", "unit", "loaders")):
            item.add_marker(pytest.mark.loaders)
        if _path_has_parts(path_parts, ("tests", "integration", "matching")):
            item.add_marker(pytest.mark.matching)
        if _path_has_parts(path_parts, ("tests", "integration", "models")):
            item.add_marker(pytest.mark.models)
            item.add_marker(pytest.mark.loaders)
        if _path_has_parts(path_parts, ("tests", "integration", "validation")):
            item.add_marker(pytest.mark.validation)
            item.add_marker(pytest.mark.slow)
        if path.name == "test_static_typing.py":
            item.add_marker(pytest.mark.typing)
        if path.name == "test_symbolica_local_versions.py":
            item.add_marker(pytest.mark.dependencies)


def _path_has_parts(path_parts: tuple[str, ...], expected: tuple[str, ...]) -> bool:
    for index in range(0, len(path_parts) - len(expected) + 1):
        if path_parts[index : index + len(expected)] == expected:
            return True
    return False
