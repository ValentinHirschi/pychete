#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    helper = Path(__file__).resolve().parents[1] / "helper_mathematica_scripts" / "convert_matchete_model_state.py"
    runpy.run_path(str(helper), run_name="__main__")
