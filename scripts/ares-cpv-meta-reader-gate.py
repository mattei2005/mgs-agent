#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path("/root/mgs-agent")
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from ares_campaign_v3.coordination import reader_block_reason


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed reader gate for the CPV Meta account lane")
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--operation-state")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    reason = reader_block_reason(
        args.account_id,
        args.state_root,
        operation_state=args.operation_state,
    )
    if reason:
        if args.json:
            print(json.dumps({"allowed": False, "reason": reason}, ensure_ascii=False, sort_keys=True))
        return 75
    if args.json:
        print(json.dumps({"allowed": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())