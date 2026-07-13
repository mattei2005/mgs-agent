#!/usr/bin/env python3
"""Monitor staged Hermes memory/skill writes without reading their content.

Default mode updates a small anti-spam state and sends Discord embeds only for
items aged >= threshold, daily reminders, scanner errors, and recovery. The
``--summary-json`` mode is strictly read-only and is used by REPORT-INFRA.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_PROFILES_ROOT = Path("/root/.hermes/profiles")
DEFAULT_STATE = Path("/root/mgs-agent/data/hermes-pending-write-monitor-state.json")
DEFAULT_POSTER = Path("/root/mgs-agent/scripts/discord-bot-post.py")
DEFAULT_CHANNEL = "1498132022634483894"
PROFILES = ("zeus", "atena", "ares")
SUBSYSTEMS = ("memory", "skills")
RODOLFO = "344196393512075265"


def _created_epoch(value: Any, fallback: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    return fallback


def scan_pending(
    profiles_root: Path | str = DEFAULT_PROFILES_ROOT,
    *,
    now_epoch: Optional[float] = None,
    threshold_hours: float = 24.0,
    profiles: Iterable[str] = PROFILES,
) -> Dict[str, Any]:
    """Return metadata-only counts. Never returns staged summary/payload content."""
    root = Path(profiles_root)
    now = float(now_epoch if now_epoch is not None else time.time())
    threshold_seconds = threshold_hours * 3600.0
    records: List[Dict[str, Any]] = []
    errors: List[str] = []
    breakdown: Dict[str, Dict[str, Any]] = {}

    for profile in profiles:
        for subsystem in SUBSYSTEMS:
            key = f"{profile}.{subsystem}"
            bucket: List[Dict[str, Any]] = []
            directory = root / profile / "pending" / subsystem
            if directory.exists():
                for path in sorted(directory.glob("*.json")):
                    try:
                        raw = json.loads(path.read_text(encoding="utf-8"))
                        if not isinstance(raw, dict):
                            raise ValueError("record is not an object")
                        pending_id = str(raw.get("id") or path.stem)
                        created = _created_epoch(raw.get("created_at"), path.stat().st_mtime)
                        age_seconds = max(0.0, now - created)
                        item = {
                            "key": f"{profile}/{subsystem}/{pending_id}",
                            "id": pending_id,
                            "profile": profile,
                            "subsystem": subsystem,
                            "age_hours": round(age_seconds / 3600.0, 1),
                            "aged": age_seconds >= threshold_seconds,
                        }
                        records.append(item)
                        bucket.append(item)
                    except Exception as exc:
                        errors.append(f"{profile}/{subsystem}/{path.name}: {type(exc).__name__}")
            breakdown[key] = {
                "total": len(bucket),
                "aged": sum(1 for item in bucket if item["aged"]),
                "oldest_hours": max((item["age_hours"] for item in bucket), default=0.0),
            }

    aged_records = [item for item in records if item["aged"]]
    return {
        "checked_at_epoch": now,
        "threshold_hours": threshold_hours,
        "total": len(records),
        "aged": len(aged_records),
        "oldest_hours": max((item["age_hours"] for item in records), default=0.0),
        "aged_ids": sorted(item["key"] for item in aged_records),
        "records": records,
        "breakdown": breakdown,
        "errors": errors,
    }


def decide(
    summary: Dict[str, Any],
    state: Dict[str, Any],
    *,
    now_epoch: Optional[float] = None,
    reminder_hours: float = 24.0,
) -> Dict[str, str]:
    now = float(now_epoch if now_epoch is not None else time.time())
    current = set(summary.get("aged_ids") or [])
    previous = set(state.get("aged_ids") or [])
    last_alert = float(state.get("last_alert_at") or 0.0)

    if summary.get("errors"):
        signature = "|".join(sorted(summary["errors"]))
        if signature != state.get("last_error_signature") or now - last_alert >= reminder_hours * 3600:
            return {"action": "error", "reason": "scanner_error"}
        return {"action": "none", "reason": "error_suppressed"}
    if current:
        if not previous:
            return {"action": "alert", "reason": "first_aged"}
        if current - previous:
            return {"action": "alert", "reason": "new_aged_ids"}
        if now - last_alert >= reminder_hours * 3600:
            return {"action": "alert", "reason": "daily_reminder"}
        return {"action": "none", "reason": "anti_spam"}
    if previous:
        return {"action": "recovery", "reason": "aged_queue_cleared"}
    return {"action": "none", "reason": "healthy"}


def report_field(summary: Dict[str, Any]) -> str:
    if summary.get("errors"):
        return f"indisponível ({len(summary['errors'])} erro(s) de leitura)"
    return (
        f"total={summary['total']} | >={summary['threshold_hours']:g}h={summary['aged']} "
        f"| mais antiga={summary['oldest_hours']:.1f}h"
    )


def _breakdown_lines(summary: Dict[str, Any]) -> str:
    lines = []
    for key, row in summary["breakdown"].items():
        if row["total"]:
            lines.append(f"{key}: total={row['total']} aged={row['aged']} oldest={row['oldest_hours']:.1f}h")
    return "\n".join(lines) or "zero pendências"


def build_payload(summary: Dict[str, Any], decision: Dict[str, str]) -> Dict[str, Any]:
    action = decision["action"]
    if action == "recovery":
        return {
            "content": "",
            "embeds": [{
                "title": "Fila Hermes regularizada",
                "color": 3066993,
                "fields": [
                    {"name": "Estado", "value": "Nenhuma pendência acima do limite de idade.", "inline": False},
                    {"name": "Fila atual", "value": report_field(summary), "inline": False},
                ],
            }],
        }
    if action == "error":
        return {
            "content": f"<@{RODOLFO}> erro no monitor de pendências Hermes",
            "embeds": [{
                "title": "Monitor pending/ com erro",
                "color": 15158332,
                "fields": [
                    {"name": "Erros", "value": "\n".join(summary["errors"])[:900], "inline": False},
                    {"name": "Ação", "value": "Investigar leitura dos JSONs; nenhum item foi alterado.", "inline": False},
                ],
            }],
        }
    ids = "\n".join(summary.get("aged_ids") or [])[:900] or "nenhum"
    return {
        "content": f"<@{RODOLFO}> pendências Hermes aguardam revisão",
        "embeds": [{
            "title": "Pendências Hermes acima de 24h",
            "color": 15844367,
            "fields": [
                {"name": "Resumo", "value": report_field(summary), "inline": False},
                {"name": "Por perfil", "value": f"```text\n{_breakdown_lines(summary)[:850]}\n```", "inline": False},
                {"name": "IDs", "value": f"```text\n{ids}\n```", "inline": False},
                {"name": "Ação", "value": "Revisar manualmente; o monitor não aprova, rejeita ou expira itens.", "inline": False},
            ],
        }],
    }


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as temp:
            temp_name = temp.name
            json.dump(state, temp, ensure_ascii=False, indent=2)
            temp.write("\n")
            temp.flush(); os.fsync(temp.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name:
            try: os.unlink(temp_name)
            except FileNotFoundError: pass


def _send(poster: Path, channel_id: str, payload: Dict[str, Any], *, dry_run: bool) -> str:
    command = [str(poster), "--channel-id", channel_id]
    if dry_run:
        command.append("--dry-run")
    result = subprocess.run(
        command,
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Discord poster failed rc={result.returncode}: {result.stderr[:300]}")
    return result.stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles-root", type=Path, default=DEFAULT_PROFILES_ROOT)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--poster", type=Path, default=DEFAULT_POSTER)
    parser.add_argument("--channel-id", default=DEFAULT_CHANNEL)
    parser.add_argument("--threshold-hours", type=float, default=24.0)
    parser.add_argument("--reminder-hours", type=float, default=24.0)
    parser.add_argument("--summary-json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--now-epoch", type=float)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    now = args.now_epoch if args.now_epoch is not None else time.time()
    summary = scan_pending(
        args.profiles_root,
        now_epoch=now,
        threshold_hours=args.threshold_hours,
    )
    if args.summary_json:
        print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
        return 0 if not summary["errors"] else 2

    state = _load_state(args.state_file)
    decision = decide(summary, state, now_epoch=now, reminder_hours=args.reminder_hours)
    payload = build_payload(summary, decision) if decision["action"] != "none" else None
    send_result = "not_sent"
    if payload is not None:
        send_result = _send(args.poster, args.channel_id, payload, dry_run=args.dry_run)

    if not args.dry_run:
        new_state = {
            "last_check_at": now,
            "aged_ids": summary["aged_ids"],
            "last_alert_at": now if decision["action"] in {"alert", "error"} else state.get("last_alert_at"),
            "last_recovery_at": now if decision["action"] == "recovery" else state.get("last_recovery_at"),
            "last_error_signature": "|".join(sorted(summary["errors"])) if summary["errors"] else "",
            "last_total": summary["total"],
            "last_aged": summary["aged"],
            "last_oldest_hours": summary["oldest_hours"],
        }
        _write_state(args.state_file, new_state)

    print(json.dumps({
        "action": decision["action"],
        "reason": decision["reason"],
        "summary": report_field(summary),
        "discord": send_result,
        "dry_run": args.dry_run,
    }, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
