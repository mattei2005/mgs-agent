#!/usr/bin/env python3
"""Compatibility wrapper for the retired UPLOAD_CANVAS script name.

Current intake is MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL. New callers should use
`ares-drive-upload-manual-inventory.py`.
"""
from __future__ import annotations

import os
import sys

TARGET = "/root/mgs-agent/scripts/ares-drive-upload-manual-inventory.py"

if __name__ == "__main__":
    print(
        "DEPRECATED: use ares-drive-upload-manual-inventory.py; "
        "inventory target is MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL",
        file=sys.stderr,
    )
    os.execv(TARGET, [TARGET, *sys.argv[1:]])
