#!/usr/bin/env python3
"""Poll one Hermes gateway until systemd and a *new* Discord marker are ready."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Callable, Dict, Optional, Sequence

DISCORD_MARKERS = (
    "✓ discord connected",
    "[Discord] Connected as",
    "Gateway running with 1 platform",
)


def systemctl_status(service: str) -> Dict[str, str]:
    proc = subprocess.run(
        [
            "systemctl",
            "show",
            service,
            "-p",
            "ActiveState",
            "-p",
            "SubState",
            "-p",
            "MainPID",
            "-p",
            "NRestarts",
            "-p",
            "ExecMainStartTimestamp",
            "--no-pager",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        return {"ActiveState": "unknown", "SubState": "unknown", "MainPID": "0", "NRestarts": "0"}
    result: Dict[str, str] = {}
    for raw in proc.stdout.splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            result[key] = value
    return result


def has_new_discord_marker(log_path: Path, offset: int) -> bool:
    try:
        size = log_path.stat().st_size
        start = offset if 0 <= offset <= size else 0
        with log_path.open("rb") as handle:
            handle.seek(start)
            text = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return False
    return any(marker in text for marker in DISCORD_MARKERS)


def wait_gateway_ready(
    service: str,
    log_path: Path,
    offset: int,
    *,
    timeout: float,
    poll_interval: float = 2.0,
    status_fn: Callable[[str], Dict[str, str]] = systemctl_status,
    monotonic_fn: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Dict[str, object]:
    started = monotonic_fn()
    last_status: Dict[str, str] = {}
    while True:
        last_status = status_fn(service)
        active = last_status.get("ActiveState") == "active"
        running = last_status.get("SubState") == "running"
        try:
            pid = int(last_status.get("MainPID") or "0")
        except ValueError:
            pid = 0
        connected = has_new_discord_marker(log_path, offset)
        now = monotonic_fn()
        elapsed = max(0.0, now - started)
        if active and running and pid > 0 and connected:
            return {
                "ready": True,
                "service": service,
                "ActiveState": "active",
                "SubState": "running",
                "MainPID": pid,
                "NRestarts": int(last_status.get("NRestarts") or "0"),
                "ExecMainStartTimestamp": last_status.get("ExecMainStartTimestamp", ""),
                "discord_connected": True,
                "elapsed_seconds": round(elapsed, 3),
            }
        if elapsed >= timeout:
            reason = "timeout_waiting_for_discord" if active and running and pid > 0 else "timeout_waiting_for_service"
            return {
                "ready": False,
                "service": service,
                "ActiveState": last_status.get("ActiveState", "unknown"),
                "SubState": last_status.get("SubState", "unknown"),
                "MainPID": pid,
                "NRestarts": int(last_status.get("NRestarts") or "0"),
                "discord_connected": connected,
                "elapsed_seconds": round(elapsed, 3),
                "reason": reason,
            }
        sleep_fn(poll_interval)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--offset", required=True, type=int)
    parser.add_argument("--timeout", required=True, type=float)
    parser.add_argument("--poll", type=float, default=2.0)
    args = parser.parse_args(argv)
    result = wait_gateway_ready(
        args.service,
        Path(args.log),
        args.offset,
        timeout=args.timeout,
        poll_interval=args.poll,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
