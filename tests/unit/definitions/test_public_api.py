from __future__ import annotations

import pychete
from pychete import api


def test_package_root_reexports_declared_public_api() -> None:
    assert pychete.__all__ == api.__all__
    for name in api.__all__:
        assert getattr(pychete, name) is getattr(api, name)
