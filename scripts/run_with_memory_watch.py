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
import time
from collections.abc import Sequence


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a command with RLIMIT_AS/RLIMIT_DATA memory caps.",
    )
    parser.add_argument("--limit-gb", type=float, required=True, help="memory cap in GiB")
    parser.add_argument(
        "--stop-file",
        default="stop.order",
        help=(
            "path to a file whose creation requests termination of the wrapped "
            "process group; use an empty value to disable"
        ),
    )
    parser.add_argument(
        "--poll-interval-sec",
        type=float,
        default=1.0,
        help="seconds between process/stop-file checks",
    )
    parser.add_argument(
        "--terminate-grace-sec",
        type=float,
        default=10.0,
        help="seconds to wait after SIGTERM before SIGKILL",
    )
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
    if args.poll_interval_sec <= 0:
        parser.error("--poll-interval-sec must be positive")
    if args.terminate_grace_sec < 0:
        parser.error("--terminate-grace-sec must be non-negative")
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


def _terminate_with_grace(process: subprocess.Popen[bytes], *, grace_sec: float) -> int:
    _terminate_process_group(process, signal.SIGTERM)
    try:
        return process.wait(timeout=grace_sec)
    except subprocess.TimeoutExpired:
        _terminate_process_group(process, signal.SIGKILL)
        return process.wait()


def _stop_file_requested(stop_file: str | None) -> bool:
    return bool(stop_file) and os.path.exists(stop_file)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    limit_bytes = int(args.limit_gb * 1024**3)
    stop_file = args.stop_file or None
    print(
        (
            f"[memory-watch] limit={args.limit_gb:g} GiB "
            f"stop_file={stop_file or '<disabled>'} command={' '.join(args.command)}"
        ),
        flush=True,
    )
    process = subprocess.Popen(
        args.command,
        preexec_fn=lambda: _apply_memory_limit(limit_bytes),
    )
    try:
        while True:
            return_code = process.poll()
            if return_code is not None:
                return return_code
            if _stop_file_requested(stop_file):
                print(
                    f"[memory-watch] stop file detected: {stop_file}; terminating process group",
                    flush=True,
                )
                return _terminate_with_grace(process, grace_sec=args.terminate_grace_sec)
            time.sleep(args.poll_interval_sec)
    except KeyboardInterrupt:
        _terminate_process_group(process, signal.SIGINT)
        try:
            return process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process, signal.SIGKILL)
            return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
