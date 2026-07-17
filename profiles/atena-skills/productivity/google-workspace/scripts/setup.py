#!/usr/bin/env python3
"""Canonical MGS Google readiness check; never creates local credentials."""
from __future__ import annotations
import subprocess
import sys


def main() -> int:
    return subprocess.run([sys.executable, "/root/mgs-agent/scripts/monitor-drive-auth-unified.py", "--dry-run", "--force-sa"], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
