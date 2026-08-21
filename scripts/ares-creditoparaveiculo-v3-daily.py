#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path("/root/mgs-agent")
if str(BASE / "scripts") not in sys.path:
    sys.path.insert(0, str(BASE / "scripts"))

from ares_campaign_v3.daily_cpv import DailyPaths, offline_smoke, run_daily

SP = ZoneInfo("America/Sao_Paulo")


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Creditoparaveiculo daily Campaign Engine v3 runner")
    ap.add_argument("--gate", action="store_true", help="Start only at 17:00 São Paulo; resumable states may continue later")
    ap.add_argument("--post-discord", action="store_true", help="Post sanitized result to the fixed creation thread")
    ap.add_argument("--quiet", action="store_true", help="Suppress stdout on normal scheduler runs")
    ap.add_argument("--operational-date", help="Testing override YYYY-MM-DD; does not bypass live gates")
    ap.add_argument("--offline-smoke", action="store_true", help="Fully offline fake transport; no Drive/Meta/Discord")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.offline_smoke:
        result = offline_smoke()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    now_sp = datetime.now(SP)
    if args.operational_date:
        now_sp = datetime.fromisoformat(args.operational_date).replace(hour=17, minute=0, second=0, microsecond=0, tzinfo=SP)
    result = run_daily(paths=DailyPaths(), now_sp=now_sp, gate=args.gate, post_report=args.post_discord, quiet=args.quiet)
    return 0 if result.get("status") in {"SILENT_NOT_DUE", "ALREADY_COMPLETE", "COMPLETE_FUTURE_ACTIVE", "PARTIAL_DEFERRED_QUOTA"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
