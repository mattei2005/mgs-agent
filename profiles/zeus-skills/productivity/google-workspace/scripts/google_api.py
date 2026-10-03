#!/usr/bin/env python3
"""Retired compatibility entry point for MGS Google operations."""
from __future__ import annotations


def main() -> int:
    print("retired: use /root/mgs-agent/scripts/mgs_google_workspace_auth.py with the mgs-core-prod Service Account")
    return 64


if __name__ == "__main__":
    raise SystemExit(main())
