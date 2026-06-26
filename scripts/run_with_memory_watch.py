#!/usr/bin/env python3
"""Run a command with a hard memory cap.

This wrapper is intentionally dependency-free so it works inside pychete's
managed virtual environment without installing monitoring packages. On Unix
systems it applies ``setrlimit`` in the child process before ``exec``; child
processes inherit the limit from the wrapped command.
"""

from __future__ import annotations

import argparse
import os
import resource
import signal
import subprocess
import sys
from collections.abc import Sequence


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a command with RLIMIT_AS/RLIMIT_DATA memory caps.",
    )
    parser.add_argument("--limit-gb", type=float, required=True, help="memory cap in GiB")
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="command to run, optionally preceded by --",
    )
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a command is required after --")
    if args.limit_gb <= 0:
        parser.error("--limit-gb must be positive")
    return args


def _apply_memory_limit(limit_bytes: int) -> None:
    os.setsid()
    for limit_name in ("RLIMIT_AS", "RLIMIT_DATA", "RLIMIT_RSS"):
        limit = getattr(resource, limit_name, None)
        if limit is None:
            continue
        try:
            soft, hard = resource.getrlimit(limit)
            capped_hard = limit_bytes if hard < 0 else min(hard, limit_bytes)
            capped_soft = min(limit_bytes, capped_hard)
            resource.setrlimit(limit, (capped_soft, capped_hard))
        except (OSError, ValueError):
            continue


def _terminate_process_group(process: subprocess.Popen[bytes], signum: int) -> None:
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        return


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    limit_bytes = int(args.limit_gb * 1024**3)
    print(
        f"[memory-watch] limit={args.limit_gb:g} GiB command={' '.join(args.command)}",
        flush=True,
    )
    process = subprocess.Popen(
        args.command,
        preexec_fn=lambda: _apply_memory_limit(limit_bytes),
    )
    try:
        return process.wait()
    except KeyboardInterrupt:
        _terminate_process_group(process, signal.SIGINT)
        try:
            return process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process, signal.SIGKILL)
            return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
