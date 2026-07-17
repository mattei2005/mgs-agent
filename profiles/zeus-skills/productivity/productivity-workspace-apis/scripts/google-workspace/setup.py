#!/usr/bin/env python3
"""Canonical MGS Google readiness check.

Personal Google credential setup is retired. This compatibility entry point only
validates the mgs-core-prod Service Account and never creates local credentials.
"""
from __future__ import annotations
import subprocess
import sys


def main() -> int:
    proc = subprocess.run([
        sys.executable,
        "/root/mgs-agent/scripts/monitor-drive-auth-unified.py",
        "--dry-run",
        "--force-sa",
    ], check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
