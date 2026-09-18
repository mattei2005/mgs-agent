#!/usr/bin/env python3
"""Detect Honcho billing 402s from local gateway journals.

This watcher does not call Honcho. It persists only journal cursors and incident
metadata, posts an immediate Discord alert, repeats a bounded daily reminder,
and closes only after the paid health monitor records a newer healthy probe.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_CHANNEL_ID = "1498132022634483894"
RODOLFO_ID = "344196393512075265"
DEFAULT_UNITS = (
    "zeus-gateway.service",
    "atena-gateway.service",
    "ares-gateway.service",
)
BILLING_MARKERS = (
    "payment required: insufficient credits",
    "manual_billing_honcho",
)
BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STATE = BASE_DIR / "data" / "honcho-billing-watch-state.json"
DEFAULT_HEALTH_STATE = BASE_DIR / "data" / "honcho-health-state.json"
DEFAULT_POSTER = BASE_DIR / "scripts" / "discord-bot-post.py"


def _epoch_from_record(record: dict[str, Any]) -> float | None:
    raw = record.get("__REALTIME_TIMESTAMP")
    if raw is None:
        return None
    try:
        return int(raw) / 1_000_000
    except (TypeError, ValueError):
        return None


def _epoch_from_iso(value: Any) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _profile_from_unit(unit: str) -> str:
    return unit.removesuffix("-gateway.service")


def _is_billing_error(message: Any) -> bool:
    text = str(message or "").lower()
    return any(marker in text for marker in BILLING_MARKERS)


def summarize(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    profiles: set[str] = set()
    last_cursors: dict[str, str] = {}
    event_times: list[float] = []
    count = 0
    for record in records:
        unit = str(record.get("_SYSTEMD_UNIT") or "")
        cursor = record.get("__CURSOR")
        if unit and isinstance(cursor, str) and cursor:
            last_cursors[unit] = cursor
        if not _is_billing_error(record.get("MESSAGE")):
            continue
        count += 1
        if unit:
            profiles.add(_profile_from_unit(unit))
        if (event_at := _epoch_from_record(record)) is not None:
            event_times.append(event_at)
    return {
        "count": count,
        "profiles": sorted(profiles),
        "first_event_at": min(event_times) if event_times else None,
        "last_event_at": max(event_times) if event_times else None,
        "last_cursors": last_cursors,
    }


def decide(
    summary: dict[str, Any],
    state: dict[str, Any],
    health_state: dict[str, Any],
    *,
    now_epoch: float,
    reminder_hours: float,
) -> dict[str, str]:
    active = state.get("active") is True
    active_since = float(state.get("active_since") or 0)
    health_at = _epoch_from_iso(health_state.get("last_check"))
    last_event_at = float(summary.get("last_event_at") or 0)

    if active and health_state.get("last_status") == "ok" and health_at and health_at > active_since:
        if not last_event_at or last_event_at <= health_at:
            return {"action": "recovery", "reason": "validated_health_probe"}
    if summary.get("count", 0) > 0 and not active:
        return {"action": "alert", "reason": "first_402"}
    if active:
        last_alert = float(state.get("last_alert_at") or 0)
        if now_epoch - last_alert >= reminder_hours * 3600:
            return {"action": "alert", "reason": "daily_reminder"}
    return {"action": "none", "reason": "stable"}


def next_state(
    summary: dict[str, Any],
    state: dict[str, Any],
    decision: dict[str, str],
    *,
    now_epoch: float,
) -> dict[str, Any]:
    updated = {
        "schema_version": 1,
        "active": state.get("active") is True,
        "active_since": state.get("active_since"),
        "last_alert_at": state.get("last_alert_at"),
        "last_event_at": state.get("last_event_at"),
        "last_profiles": list(state.get("last_profiles") or []),
        "last_cursors": dict(state.get("last_cursors") or {}),
        "last_run_at": now_epoch,
    }
    updated["last_cursors"].update(summary.get("last_cursors") or {})
    if summary.get("count", 0):
        updated["last_event_at"] = summary.get("last_event_at") or now_epoch
        updated["last_profiles"] = list(summary.get("profiles") or [])
    if decision["action"] == "alert":
        if not updated["active"]:
            updated["active_since"] = summary.get("first_event_at") or now_epoch
        updated["active"] = True
        updated["last_alert_at"] = now_epoch
    elif decision["action"] == "recovery":
        updated["active"] = False
        updated["active_since"] = None
        updated["last_alert_at"] = None
        updated["last_profiles"] = []
    return updated


def payload(decision: dict[str, str], profiles: list[str], now_epoch: float) -> dict[str, Any]:
    when = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    if decision["action"] == "recovery":
        return {
            "content": "",
            "allowed_mentions": {"parse": []},
            "embeds": [{
                "title": "Honcho MGS restabelecido",
                "color": 3066993,
                "fields": [
                    {"name": "Status", "value": "Créditos e operação validados pelo health probe.", "inline": False},
                    {"name": "Validado em", "value": when, "inline": True},
                ],
            }],
        }
    reminder = decision.get("reason") == "daily_reminder"
    profile_text = ", ".join(profiles) if profiles else "Zeus/Atena/Ares"
    return {
        "content": f"<@{RODOLFO_ID}> alerta: Honcho MGS sem créditos",
        "allowed_mentions": {"users": [RODOLFO_ID]},
        "embeds": [{
            "title": "Honcho MGS — créditos insuficientes" if not reminder else "Honcho MGS — bloqueio continua",
            "color": 15158332,
            "fields": [
                {"name": "Detecção", "value": "Erro 402 observado localmente, sem gastar chamada adicional.", "inline": False},
                {"name": "Perfis observados", "value": profile_text, "inline": True},
                {"name": "Ação", "value": "Regularizar billing em https://app.honcho.dev/billing. O monitor fará recheck automático.", "inline": False},
            ],
        }],
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _journal_records(unit: str, cursor: str | None, initialize: bool) -> list[dict[str, Any]]:
    cmd = ["journalctl", "-u", unit, "--no-pager", "-o", "json"]
    if initialize or not cursor:
        cmd.extend(["-n", "1"])
    else:
        cmd.append(f"--after-cursor={cursor}")
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=30, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"journalctl failed for {unit}: rc={result.returncode}")
    rows: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            row.setdefault("_SYSTEMD_UNIT", unit)
            rows.append(row)
    return rows


def _send(channel_id: str, body: dict[str, Any], poster: Path) -> None:
    result = subprocess.run(
        [str(poster), "--channel-id", channel_id],
        input=json.dumps(body, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Discord delivery failed: rc={result.returncode}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--health-state", type=Path, default=DEFAULT_HEALTH_STATE)
    parser.add_argument("--channel-id", default=DEFAULT_CHANNEL_ID)
    parser.add_argument("--poster", type=Path, default=DEFAULT_POSTER)
    parser.add_argument("--reminder-hours", type=float, default=24)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fixture", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    now = time.time()
    state = _read_json(args.state)
    try:
        if args.fixture:
            records = [json.loads(line) for line in args.fixture.read_text().splitlines() if line.strip()]
        else:
            records = []
            cursors = state.get("last_cursors") or {}
            for unit in DEFAULT_UNITS:
                records.extend(_journal_records(unit, cursors.get(unit), args.initialize))
    except Exception as exc:
        print(f"monitor-honcho-billing-watch: scan_error={type(exc).__name__}", file=sys.stderr)
        return 1

    summary = summarize(records)
    if args.initialize:
        updated = next_state(summary, state, {"action": "none", "reason": "initialized"}, now_epoch=now)
        if not args.dry_run:
            _write_json_atomic(args.state, updated)
        print(json.dumps({"status": "initialized", "cursors": len(updated["last_cursors"])}, sort_keys=True))
        return 0

    health = _read_json(args.health_state)
    decision = decide(summary, state, health, now_epoch=now, reminder_hours=args.reminder_hours)
    updated = next_state(summary, state, decision, now_epoch=now)
    if decision["action"] in {"alert", "recovery"}:
        body = payload(decision, summary.get("profiles") or state.get("last_profiles") or [], now)
        if args.dry_run:
            print(json.dumps(body, ensure_ascii=False, sort_keys=True))
        else:
            _send(args.channel_id, body, args.poster)
    if not args.dry_run:
        _write_json_atomic(args.state, updated)
    print(json.dumps({"status": "ok", "action": decision["action"], "reason": decision["reason"], "events": summary["count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
