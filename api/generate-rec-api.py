#!/usr/bin/env python3
"""
generate-rec-api.py — DEPRECATED / DISABLED

This legacy FastAPI service used Anthropic/Claude pay-per-token calls for REC
article generation. MGS policy now defaults to GPT-5.5 via OpenAI Codex OAuth
and zero Anthropic API usage unless Rodolfo explicitly approves an exception.

Operational state:
- mgs-rec-api.service is masked.
- This file intentionally has no FastAPI/Anthropic imports.
- Historical implementation is recoverable from Git history.

Use the Atena REC pipeline (`content-generate-rec`) instead.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

STATUS = {
    "status": "disabled",
    "service": "mgs-rec-api",
    "reason": "Anthropic/Claude API pay-per-token usage disabled by MGS policy",
    "replacement": "Atena content-generate-rec pipeline via GPT-5.5/OpenAI Codex OAuth",
    "timestamp": datetime.now(timezone.utc).isoformat(),
}


def main() -> int:
    print(json.dumps(STATUS, ensure_ascii=False, indent=2), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
