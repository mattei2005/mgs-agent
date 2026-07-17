#!/usr/bin/env python3
"""Fail closed when a retired MGS host reappears on operational surfaces."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RETIRED_HOST = "87.99." + "151.107"
REPO = Path("/root/mgs-agent")
MAX_FILE_BYTES = 8_000_000

# Historical evidence is preserved intentionally and must not drive connections.
REPO_ALLOWLIST_PREFIXES = (
    "logs/events-audit.jsonl",
    "data/discord-thread-imports/",
    "data/infra-inventory.json",
    "backups/",
)

PROFILE_NAMES = ("zeus", "atena", "ares")
PROFILE_OPERATIONAL_NAMES = ("config.yaml", "SOUL.md", "skills", "scripts", "cron")
SYSTEM_PATHS = (
    Path("/etc/systemd/system"),
    Path("/etc/cron.d"),
    Path("/etc/cron.daily"),
    Path("/etc/cron.hourly"),
    Path("/etc/cron.weekly"),
    Path("/etc/cron.monthly"),
    Path("/root/.ssh/config"),
)


def read_contains(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return False
        return RETIRED_HOST in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def scan_tree(path: Path, label: str, failures: list[str]) -> None:
    if path.is_file():
        if read_contains(path):
            failures.append(f"{label}:{path}")
        return
    if not path.exists():
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in {".git", "logs", "sessions", "browser-profiles", "home", "cache", "audio_cache", "pending"}]
        for filename in files:
            candidate = Path(root) / filename
            if read_contains(candidate):
                failures.append(f"{label}:{candidate}")


def tracked_repo_failures(failures: list[str]) -> None:
    result = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8", errors="surrogateescape")
        if any(relative == prefix or relative.startswith(prefix) for prefix in REPO_ALLOWLIST_PREFIXES):
            continue
        path = REPO / relative
        if read_contains(path):
            failures.append(f"repo:{relative}")


def crontab_failure(failures: list[str]) -> None:
    result = subprocess.run(["crontab", "-l"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if RETIRED_HOST in result.stdout:
        failures.append("root-crontab")


def hashed_known_host_failures(failures: list[str]) -> None:
    for path in sorted(Path("/root/.ssh").glob("known_hosts*")):
        if not path.is_file():
            continue
        result = subprocess.run(
            ["ssh-keygen", "-F", RETIRED_HOST, "-f", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            failures.append(f"known-host:{path}")


def main() -> int:
    failures: list[str] = []
    tracked_repo_failures(failures)

    for profile in PROFILE_NAMES:
        root = Path("/root/.hermes/profiles") / profile
        for name in PROFILE_OPERATIONAL_NAMES:
            scan_tree(root / name, f"profile-{profile}", failures)

    for path in SYSTEM_PATHS:
        scan_tree(path, "system", failures)

    crontab_failure(failures)
    hashed_known_host_failures(failures)

    if failures:
        print("FAIL retired-host-reference guard")
        for failure in sorted(set(failures))[:100]:
            print(f"- {failure}")
        return 1

    print("OK retired-host-reference guard: no operational references or hashed known-host entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
