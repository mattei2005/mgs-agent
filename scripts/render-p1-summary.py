#!/usr/bin/env python3
"""Compatibility wrapper for Rodolfo-approved P1 summary rendering."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render-article-summary.py"

if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, str(SCRIPT), "--type", "p1", *sys.argv[1:]]))
