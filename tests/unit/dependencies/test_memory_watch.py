from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.dependencies]


def test_memory_watch_terminates_process_group_when_stop_file_appears(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[3] / "scripts" / "run_with_memory_watch.py"
    child = "from pathlib import Path; import time; Path('stop.order').touch(); time.sleep(5)"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--limit-gb",
            "30",
            "--poll-interval-sec",
            "0.05",
            "--terminate-grace-sec",
            "0.05",
            "--",
            sys.executable,
            "-c",
            child,
        ],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=5,
        check=False,
    )

    assert result.returncode != 0
    assert "stop file detected: stop.order" in result.stdout
