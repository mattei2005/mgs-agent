#!/usr/bin/env python3
"""Retired one-shot writer.

The canonical restricted-pages writer is dtr-sb-page-health-sync.py. This
compatibility tombstone prevents accidental execution of the obsolete GID-based
rebuild path.
"""

from __future__ import annotations


def main() -> int:
    print(
        "retired: use dtr-sb-page-health-sync.py; obsolete rebuild path is disabled",
    )
    return 64


if __name__ == "__main__":
    raise SystemExit(main())
