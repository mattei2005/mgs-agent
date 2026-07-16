#!/usr/bin/env python3
"""Monitor staged Hermes memory/skill writes without reading their content.

Default mode updates a small anti-spam state and sends Discord embeds for
items aged >= threshold, memory/user stores at or above the capacity threshold,
daily reminders, scanner errors, and recovery. The ``--summary-json`` mode is
strictly read-only and is used by REPORT-INFRA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

DEFAULT_PROFILES_ROOT = Path("/root/.hermes/profiles")
DEFAULT_STATE = Path("/root/mgs-agent/data/hermes-pending-write-monitor-state.json")
DEFAULT_POSTER = Path("/root/mgs-agent/scripts/discord-bot-post.py")
DEFAULT_CHANNEL = "1498132022634483894"
PROFILES = ("zeus", "atena", "ares")
SUBSYSTEMS = ("memory", "skills")
RODOLFO = "344196393512075265"
DEFAULT_MEMORY_LIMIT = 2200
DEFAULT_USER_LIMIT = 1375
DEFAULT_CAPACITY_THRESHOLD_PERCENT = 90.0
MEMORY_ENTRY_DELIMITER = "\n§\n"


def _created_epoch(value: Any, fallback: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    return fallback


def scan_capacity(
    profiles_root: Path | str = DEFAULT_PROFILES_ROOT,
    *,
    threshold_percent: float = DEFAULT_CAPACITY_THRESHOLD_PERCENT,
    profiles: Iterable[str] = PROFILES,
) -> Dict[str, Any]:
    """Return character usage only; memory/user content never leaves this function."""
    root = Path(profiles_root)
    rows: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []

    for profile in profiles:
        profile_root = root / profile
        limits = {"memory": DEFAULT_MEMORY_LIMIT, "user": DEFAULT_USER_LIMIT}
        config_path = profile_root / "config.yaml"
        if config_path.exists():
            try:
                raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                memory_config = raw.get("memory") or {}
                limits["memory"] = int(memory_config.get("memory_char_limit", DEFAULT_MEMORY_LIMIT))
                limits["user"] = int(memory_config.get("user_char_limit", DEFAULT_USER_LIMIT))
            except Exception as exc:
                errors.append(f"{profile}/config.yaml: {type(exc).__name__}")
                continue

        for store, filename in (("memory", "MEMORY.md"), ("user", "USER.md")):
            path = profile_root / "memories" / filename
            try:
                chars = len(path.read_text(encoding="utf-8")) if path.exists() else 0
                limit = limits[store]
                if limit <= 0:
                    raise ValueError("limit must be positive")
                percent = round(chars * 100.0 / limit, 1)
                key = f"{profile}.{store}"
                rows[key] = {
                    "chars": chars,
                    "limit": limit,
                    "percent": percent,
                    "warning": percent >= threshold_percent,
                }
            except Exception as exc:
                errors.append(f"{profile}/{filename}: {type(exc).__name__}")

    warning_ids = sorted(key for key, row in rows.items() if row["warning"])
    return {
        "threshold_percent": threshold_percent,
        "warning_count": len(warning_ids),
        "warning_ids": warning_ids,
        "rows": rows,
        "errors": errors,
    }


def scan_pending(
    profiles_root: Path | str = DEFAULT_PROFILES_ROOT,
    *,
    now_epoch: Optional[float] = None,
    threshold_hours: float = 24.0,
    capacity_threshold_percent: float = DEFAULT_CAPACITY_THRESHOLD_PERCENT,
    profiles: Iterable[str] = PROFILES,
) -> Dict[str, Any]:
    """Return metadata-only counts. Never returns staged summary/payload content."""
    root = Path(profiles_root)
    profiles = tuple(profiles)
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
                        failure_type = str(raw.get("failure_type") or "")
                        item = {
                            "key": f"{profile}/{subsystem}/{pending_id}",
                            "id": pending_id,
                            "profile": profile,
                            "subsystem": subsystem,
                            "age_hours": round(age_seconds / 3600.0, 1),
                            "aged": age_seconds >= threshold_seconds,
                            "failure_type": failure_type or None,
                            "dead_letter": failure_type == "capacity_overflow",
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
    dead_letter_records = [item for item in records if item["dead_letter"]]
    capacity = scan_capacity(
        root,
        threshold_percent=capacity_threshold_percent,
        profiles=profiles,
    )
    errors.extend(capacity["errors"])
    return {
        "checked_at_epoch": now,
        "threshold_hours": threshold_hours,
        "total": len(records),
        "aged": len(aged_records),
        "oldest_hours": max((item["age_hours"] for item in records), default=0.0),
        "aged_ids": sorted(item["key"] for item in aged_records),
        "dead_letter_count": len(dead_letter_records),
        "dead_letter_ids": sorted(item["key"] for item in dead_letter_records),
        "records": records,
        "breakdown": breakdown,
        "capacity": capacity,
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
    current_capacity = set((summary.get("capacity") or {}).get("warning_ids") or [])
    previous_capacity = set(state.get("capacity_warning_ids") or [])
    current_dead_letters = set(summary.get("dead_letter_ids") or [])
    previous_dead_letters = set(state.get("dead_letter_ids") or [])
    last_alert = float(state.get("last_alert_at") or 0.0)

    if summary.get("errors"):
        signature = "|".join(sorted(summary["errors"]))
        if signature != state.get("last_error_signature") or now - last_alert >= reminder_hours * 3600:
            return {"action": "error", "reason": "scanner_error"}
        return {"action": "none", "reason": "error_suppressed"}
    if current_dead_letters:
        if not previous_dead_letters:
            return {"action": "alert", "reason": "first_dead_letter"}
        if current_dead_letters - previous_dead_letters:
            return {"action": "alert", "reason": "new_dead_letter"}
        if now - last_alert >= reminder_hours * 3600:
            return {"action": "alert", "reason": "dead_letter_daily_reminder"}
    if current:
        if not previous:
            return {"action": "alert", "reason": "first_aged"}
        if current - previous:
            return {"action": "alert", "reason": "new_aged_ids"}
        if now - last_alert >= reminder_hours * 3600:
            return {"action": "alert", "reason": "daily_reminder"}
    if current_capacity:
        if not previous_capacity:
            return {"action": "alert", "reason": "first_capacity_warning"}
        if current_capacity - previous_capacity:
            return {"action": "alert", "reason": "new_capacity_warning"}
        if now - last_alert >= reminder_hours * 3600:
            return {"action": "alert", "reason": "capacity_daily_reminder"}
    if current or current_capacity or current_dead_letters:
        return {"action": "none", "reason": "anti_spam"}
    if previous or previous_capacity or previous_dead_letters:
        return {"action": "recovery", "reason": "warnings_cleared"}
    return {"action": "none", "reason": "healthy"}


def next_state(
    summary: Dict[str, Any],
    state: Dict[str, Any],
    decision: Dict[str, str],
    *,
    now_epoch: float,
) -> Dict[str, Any]:
    # A scanner error is an unknown queue state, not proof that aged items
    # disappeared. Preserve the last confirmed aged set so recovery is emitted
    # only after a later complete scan confirms zero.
    confirmed_aged = state.get("aged_ids", []) if summary.get("errors") else summary["aged_ids"]
    confirmed_capacity = (
        state.get("capacity_warning_ids", [])
        if summary.get("errors")
        else summary["capacity"]["warning_ids"]
    )
    confirmed_dead_letters = (
        state.get("dead_letter_ids", [])
        if summary.get("errors")
        else summary.get("dead_letter_ids", [])
    )
    return {
        "last_check_at": now_epoch,
        "aged_ids": confirmed_aged,
        "capacity_warning_ids": confirmed_capacity,
        "dead_letter_ids": confirmed_dead_letters,
        "last_alert_at": now_epoch if decision["action"] in {"alert", "error"} else state.get("last_alert_at"),
        "last_recovery_at": now_epoch if decision["action"] == "recovery" else state.get("last_recovery_at"),
        "last_error_signature": "|".join(sorted(summary["errors"])) if summary["errors"] else "",
        "last_total": summary["total"],
        "last_aged": summary["aged"],
        "last_oldest_hours": summary["oldest_hours"],
        "last_capacity_warning_count": summary["capacity"]["warning_count"],
        "last_dead_letter_count": summary.get("dead_letter_count", 0),
    }


def report_field(summary: Dict[str, Any]) -> str:
    if summary.get("errors"):
        return f"indisponível ({len(summary['errors'])} erro(s) de leitura)"
    return (
        f"total={summary['total']} | >={summary['threshold_hours']:g}h={summary['aged']} "
        f"| mais antiga={summary['oldest_hours']:.1f}h "
        f"| dead-letter={summary.get('dead_letter_count', 0)} "
        f"| memória>={summary['capacity']['threshold_percent']:g}%={summary['capacity']['warning_count']}"
    )


def _breakdown_lines(summary: Dict[str, Any]) -> str:
    lines = []
    for key, row in summary["breakdown"].items():
        if row["total"]:
            lines.append(f"{key}: total={row['total']} aged={row['aged']} oldest={row['oldest_hours']:.1f}h")
    return "\n".join(lines) or "zero pendências"


def _capacity_lines(summary: Dict[str, Any]) -> str:
    lines = []
    for key in summary["capacity"]["warning_ids"]:
        row = summary["capacity"]["rows"][key]
        lines.append(f"{key}: {row['chars']}/{row['limit']} ({row['percent']:.1f}%)")
    return "\n".join(lines) or "stores abaixo do limiar"


def create_compaction_proposals(
    summary: Dict[str, Any],
    profiles_root: Path | str = DEFAULT_PROFILES_ROOT,
    *,
    now_epoch: Optional[float] = None,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """Create secure read-only before/after proposals for stores at capacity.

    The automatic transformation is deliberately conservative: it removes only
    exact duplicate entries while preserving their first occurrence. If there
    are no exact duplicates, before and after remain byte-identical and the
    proposal records that semantic review is required. USER.md and MEMORY.md
    are never modified here.
    """
    root = Path(profiles_root)
    now = float(now_epoch if now_epoch is not None else time.time())
    created_at = datetime.fromtimestamp(now).astimezone().isoformat()
    proposals: List[Dict[str, Any]] = []

    for key in summary.get("capacity", {}).get("warning_ids", []):
        try:
            profile, store = key.split(".", 1)
            if profile not in PROFILES or store not in {"memory", "user"}:
                raise ValueError("unsupported profile/store")
            filename = "USER.md" if store == "user" else "MEMORY.md"
            source = root / profile / "memories" / filename
            before = source.read_text(encoding="utf-8")
            before_hash = hashlib.sha256(before.encode("utf-8")).hexdigest()

            entries = [part.strip() for part in before.split(MEMORY_ENTRY_DELIMITER) if part.strip()]
            unique_entries = list(dict.fromkeys(entries))
            duplicate_entries = len(entries) - len(unique_entries)
            after = (
                MEMORY_ENTRY_DELIMITER.join(unique_entries) + ("\n" if unique_entries else "")
                if duplicate_entries
                else before
            )
            after_hash = hashlib.sha256(after.encode("utf-8")).hexdigest()
            proposal_id = hashlib.sha256(
                f"memory-compaction-v1|{key}|{before_hash}".encode("utf-8")
            ).hexdigest()[:16]
            proposal_dir = root / profile / "pending" / "memory-compaction"
            proposal_path = proposal_dir / f"{proposal_id}.json"
            row = summary["capacity"]["rows"][key]
            record = {
                "id": proposal_id,
                "kind": "memory_compaction_proposal",
                "created_at": created_at,
                "profile": profile,
                "store": store,
                "source_path": str(source),
                "threshold_percent": summary["capacity"]["threshold_percent"],
                "usage": {
                    "chars": row["chars"],
                    "limit": row["limit"],
                    "percent": row["percent"],
                },
                "policy": {
                    "apply_automatically": False,
                    "requires_rodolfo_approval": True,
                    "automatic_scope": "exact_duplicate_entries_only",
                    "semantic_review_required": duplicate_entries == 0,
                },
                "before": {"sha256": before_hash, "chars": len(before), "text": before},
                "after": {"sha256": after_hash, "chars": len(after), "text": after},
                "savings_chars": len(before) - len(after),
                "duplicate_entries_removed_in_proposal": duplicate_entries,
            }

            existed = proposal_path.exists()
            if not dry_run and not existed:
                proposal_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                os.chmod(proposal_dir, 0o700)
                temp_name = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w", encoding="utf-8", dir=proposal_dir,
                        prefix=f".{proposal_id}.", suffix=".tmp", delete=False,
                    ) as temp:
                        temp_name = temp.name
                        json.dump(record, temp, ensure_ascii=False, indent=2)
                        temp.write("\n")
                        temp.flush(); os.fsync(temp.fileno())
                    os.chmod(temp_name, 0o600)
                    os.replace(temp_name, proposal_path)
                    os.chmod(proposal_path, 0o600)
                    temp_name = None
                finally:
                    if temp_name:
                        try: os.unlink(temp_name)
                        except FileNotFoundError: pass

            proposals.append({
                "id": proposal_id,
                "key": key,
                "path": str(proposal_path),
                "before_chars": len(before),
                "after_chars": len(after),
                "savings_chars": len(before) - len(after),
                "duplicate_entries_removed": duplicate_entries,
                "created": not existed and not dry_run,
                "dry_run": dry_run,
            })
        except Exception as exc:
            proposals.append({"key": key, "error": type(exc).__name__})
    return proposals


def _proposal_lines(proposals: List[Dict[str, Any]]) -> str:
    lines = []
    for item in proposals:
        if item.get("error"):
            lines.append(f"{item.get('key', 'unknown')}: erro={item['error']}")
        else:
            lines.append(f"{item['key']}: id={item['id']} economia={item['savings_chars']} chars")
    return "\n".join(lines) or "nenhuma proposta"


def _attach_proposals(payload: Dict[str, Any], proposals: List[Dict[str, Any]]) -> Dict[str, Any]:
    if proposals and payload.get("embeds"):
        payload["embeds"][0].setdefault("fields", []).append({
            "name": "Proposta automática (não aplicada)",
            "value": f"```text\n{_proposal_lines(proposals)[:850]}\n```",
            "inline": False,
        })
    return payload


def build_payload(
    summary: Dict[str, Any],
    decision: Dict[str, str],
    proposals: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    proposals = proposals or []
    action = decision["action"]
    if action == "recovery":
        return {
            "content": "",
            "embeds": [{
                "title": "Fila Hermes regularizada",
                "color": 3066993,
                "fields": [
                    {"name": "Estado", "value": "Nenhuma fila vencida ou store de memória acima do limiar.", "inline": False},
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
    if decision.get("reason") in {
        "first_dead_letter",
        "new_dead_letter",
        "dead_letter_daily_reminder",
    }:
        dead_letter_ids = "\n".join(summary.get("dead_letter_ids") or [])[:900] or "nenhum"
        return {
            "content": f"<@{RODOLFO}> write de memória recusado e preservado",
            "embeds": [{
                "title": "Dead-letter Hermes — capacity_overflow",
                "color": 15105570,
                "fields": [
                    {"name": "IDs", "value": f"```text\n{dead_letter_ids}\n```", "inline": False},
                    {"name": "Estado", "value": "Payload preservado; memória original inalterada.", "inline": False},
                    {"name": "Ação", "value": "Revisar a pending manualmente. O alerta não expõe nem modifica o conteúdo.", "inline": False},
                ],
            }],
        }
    ids = "\n".join(summary.get("aged_ids") or [])[:900] or "nenhum"
    capacity_ids = summary["capacity"]["warning_ids"]
    if capacity_ids and not summary.get("aged_ids"):
        return {
            "content": f"<@{RODOLFO}> capacidade de memória Hermes acima do limiar",
            "embeds": [{
                "title": f"Memória Hermes acima de {summary['capacity']['threshold_percent']:g}%",
                "color": 15844367,
                "fields": [
                    {"name": "Uso", "value": f"```text\n{_capacity_lines(summary)[:850]}\n```", "inline": False},
                    {"name": "Ação", "value": "Revisar a proposta before/after. Aplicação exige aprovação de Rodolfo; o monitor nunca altera USER/MEMORY.", "inline": False},
                ],
            }],
        }
    return {
        "content": f"<@{RODOLFO}> pendências Hermes aguardam revisão",
        "embeds": [{
            "title": "Pendências Hermes acima de 24h",
            "color": 15844367,
            "fields": [
                {"name": "Resumo", "value": report_field(summary), "inline": False},
                {"name": "Por perfil", "value": f"```text\n{_breakdown_lines(summary)[:850]}\n```", "inline": False},
                {"name": "IDs", "value": f"```text\n{ids}\n```", "inline": False},
                {"name": "Capacidade", "value": f"```text\n{_capacity_lines(summary)[:850]}\n```", "inline": False},
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
    parser.add_argument("--capacity-threshold-percent", type=float, default=DEFAULT_CAPACITY_THRESHOLD_PERCENT)
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
        capacity_threshold_percent=args.capacity_threshold_percent,
    )
    if args.summary_json:
        print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
        return 0 if not summary["errors"] else 2

    state = _load_state(args.state_file)
    decision = decide(summary, state, now_epoch=now, reminder_hours=args.reminder_hours)
    proposals = (
        create_compaction_proposals(
            summary, args.profiles_root, now_epoch=now, dry_run=args.dry_run,
        )
        if summary.get("capacity", {}).get("warning_count") and not summary.get("errors")
        else []
    )
    payload = build_payload(summary, decision) if decision["action"] != "none" else None
    if payload is not None:
        payload = _attach_proposals(payload, proposals)
    send_result = "not_sent"
    if payload is not None:
        send_result = _send(args.poster, args.channel_id, payload, dry_run=args.dry_run)

    if not args.dry_run:
        _write_state(args.state_file, next_state(summary, state, decision, now_epoch=now))

    print(json.dumps({
        "action": decision["action"],
        "reason": decision["reason"],
        "summary": report_field(summary),
        "discord": send_result,
        "compaction_proposals": proposals,
        "dry_run": args.dry_run,
    }, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
