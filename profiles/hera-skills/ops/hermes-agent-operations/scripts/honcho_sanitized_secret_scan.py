#!/usr/bin/env python3
"""Scan a Honcho sanitized dataset for obvious secret leakage before ingestion.

Usage:
  python scripts/honcho_sanitized_secret_scan.py /path/to/sanitized_mgs_events.json

Exit codes:
  0 = no obvious secret-like pattern found
  1 = one or more patterns matched; do not ingest
  2 = usage/read error
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS = {
    "honcho_key": r"hch-v3-[A-Za-z0-9]+",
    "openai_key": r"sk-[A-Za-z0-9][A-Za-z0-9_-]{10,}",
    "github_pat": r"github_pat_[A-Za-z0-9_]+",
    "github_ghp": r"ghp_[A-Za-z0-9_]+",
    "aws_access_key": r"AKIA[A-Z0-9]{16}",
    "password_assignment": r"(?i)password\s*[=:]\s*[^\s,;]+",
    "token_assignment": r"(?i)token\s*[=:]\s*[^\s,;]+",
    "secret_assignment": r"(?i)secret\s*[=:]\s*[^\s,;]+",
    "api_key_assignment": r"(?i)api[_-]?key\s*[=:]\s*[^\s,;]+",
    "authorization_assignment": r"(?i)authorization\s*[=:]\s*[^\s,;]+",
    "url_embedded_creds": r"https?://[^\s/@:]+:[^\s/@]+@",
}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: honcho_sanitized_secret_scan.py /path/to/dataset.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        text = path.read_text(errors="replace")
    except Exception as exc:
        print(f"read_error: {exc}", file=sys.stderr)
        return 2

    hits = []
    for name, pattern in PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            snippet = text[start:end].replace("\n", " ")
            hits.append((name, snippet))

    if hits:
        print("SECRET_SCAN_FAIL")
        for name, snippet in hits:
            print(f"{name}: {snippet}")
        return 1

    print(f"SECRET_SCAN_OK bytes={len(text)} path={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
