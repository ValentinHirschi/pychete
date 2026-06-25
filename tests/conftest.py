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
        if _path_has_parts(path_parts, ("tests", "unit", "backends")):
            item.add_marker(pytest.mark.backend)
        if _path_has_parts(path_parts, ("tests", "integration", "matching")):
            item.add_marker(pytest.mark.matching)
        if _path_has_parts(path_parts, ("tests", "integration", "validation")):
            item.add_marker(pytest.mark.validation)
            item.add_marker(pytest.mark.slow)


def _path_has_parts(path_parts: tuple[str, ...], expected: tuple[str, ...]) -> bool:
    for index in range(0, len(path_parts) - len(expected) + 1):
        if path_parts[index : index + len(expected)] == expected:
            return True
    return False
