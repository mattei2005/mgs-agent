#!/usr/bin/env python3
"""Account-wide Meta activity monitor for external/untracked writes.

Reads the Ad Account /activities edge, suppresses Meta lifecycle noise and
Ares writes that have matching local audit evidence, and posts only external
or unaudited material changes to an existing Discord thread. Tokens are never
printed or persisted.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path("/root/mgs-agent")
DEFAULT_OPERATION = BASE / "data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json"
DEFAULT_ACCOUNT = BASE / "data/ares/meta-ads/accounts/1046241194533786.json"
META_COMMON = BASE / "scripts/ares-meta-common.py"
POSTER = BASE / "scripts/ares-discord-post-with-thread.py"
AUDIT_ROOT = BASE / "data/ares/meta-ads/audit"
EVENT_AUDIT = BASE / "logs/events-audit.jsonl"

SYSTEM_LIFECYCLE_EVENTS = {
    "first_delivery_event",
    "ad_review_approved",
    "ad_review_declined",
    "di_ad_set_learning_stage_exit",
    "campaign_ended",
    "lifetime_budget_spent",
}
SYSTEM_STATUS_TRANSITIONS = {
    ("Pending Process", "Pending Review"),
    ("Pending Review", "Active"),
    ("Pending Process", "Active"),
    ("Active", "Pending Process"),
}
MATERIAL_EXACT = {
    "add_funding_source", "remove_funding_source", "billing_event",
    "account_spending_limit_reached", "campaign_spending_limit_reached",
    "add_images", "edit_images", "delete_images",
    "create_audience", "update_audience", "delete_audience", "share_audience",
    "receive_audience", "unshare_audience", "remove_shared_audience",
    "create_ad", "update_ad_creative", "edit_and_update_ad_creative",
    "update_ad_bid_info", "update_ad_bid_type", "update_ad_run_status",
    "update_ad_run_status_to_be_set_after_review", "update_ad_friendly_name",
    "update_ad_targets_spec", "update_ad_labels", "update_ad_audience_persona",
    "update_adgroup_stop_delivery",
    "create_ad_set", "create_campaign_group", "create_campaign_legacy",
}
MATERIAL_PREFIXES = (
    "ad_account_", "adaccount_", "update_campaign_", "update_ad_set_",
    "create_campaign_", "create_adaccount_", "update_adaccount_", "funding_event_",
)
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_utc(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(raw: Any) -> dt.datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if re.search(r"[+-]\d{4}$", text):
        text = text[:-5] + text[-5:-2] + ":" + text[-2:]
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o640)
    try:
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_extra(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(str(raw or "{}"))
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError, json.JSONDecodeError):
        return {}


def event_key(event: dict[str, Any]) -> str:
    canonical = {k: event.get(k) for k in (
        "event_time", "event_type", "object_id", "actor_id", "application_id", "extra_data"
    )}
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_material(event: dict[str, Any]) -> bool:
    kind = str(event.get("event_type") or "")
    return kind in MATERIAL_EXACT or kind.startswith(MATERIAL_PREFIXES)


def system_lifecycle_noise(event: dict[str, Any]) -> bool:
    kind = str(event.get("event_type") or "")
    if kind in SYSTEM_LIFECYCLE_EVENTS:
        return True
    if str(event.get("actor_id") or "") != "0":
        return False
    if kind not in {"update_ad_run_status", "update_ad_set_run_status"}:
        return False
    extra = safe_extra(event.get("extra_data"))
    return (str(extra.get("old_value")), str(extra.get("new_value"))) in SYSTEM_STATUS_TRANSITIONS


def trusted_source(event: dict[str, Any], config: dict[str, Any]) -> bool:
    actor = str(event.get("actor_id") or "")
    app = str(event.get("application_id") or "")
    for item in config.get("trusted_api_sources") or []:
        if actor == str(item.get("actor_id") or "") and app == str(item.get("application_id") or ""):
            return True
    return False


def collect_times(value: Any) -> list[dt.datetime]:
    found: list[dt.datetime] = []
    if isinstance(value, dict):
        for child in value.values():
            found.extend(collect_times(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_times(child))
    elif isinstance(value, str) and TIMESTAMP_RE.match(value):
        parsed = parse_time(value)
        if parsed:
            found.append(parsed)
    return found


def contains_exact(value: Any, needle: str) -> bool:
    if isinstance(value, dict):
        return any(contains_exact(child, needle) for child in value.values())
    if isinstance(value, list):
        return any(contains_exact(child, needle) for child in value)
    return str(value) == needle


def matching_subtrees(value: Any, object_id: str) -> list[Any]:
    matches: list[Any] = []
    if isinstance(value, dict):
        if any(str(value.get(key) or "") == object_id for key in ("object_id", "campaign_id", "adset_id", "ad_id", "id")):
            matches.append(value)
        for child in value.values():
            matches.extend(matching_subtrees(child, object_id))
    elif isinstance(value, list):
        for child in value:
            matches.extend(matching_subtrees(child, object_id))
    return matches


def recent_audit_files(event_time: dt.datetime, max_files: int = 300) -> list[Path]:
    lower = event_time.timestamp() - 86400
    upper = event_time.timestamp() + 86400
    candidates: list[tuple[float, Path]] = []
    for path in AUDIT_ROOT.rglob("*.json"):
        try:
            stamp = path.stat().st_mtime
        except OSError:
            continue
        if lower <= stamp <= upper:
            candidates.append((stamp, path))
    candidates.sort(reverse=True)
    return [path for _, path in candidates[:max_files]]


def local_audit_match(event: dict[str, Any], window_seconds: int = 1800) -> dict[str, Any] | None:
    object_id = str(event.get("object_id") or "")
    when = parse_time(event.get("event_time"))
    if not object_id or not when:
        return None
    for path in recent_audit_files(when):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if object_id not in text:
            continue
        try:
            payload = json.loads(text)
        except (ValueError, json.JSONDecodeError):
            continue
        if not contains_exact(payload, object_id):
            continue
        subtrees = matching_subtrees(payload, object_id)
        times = [stamp for subtree in subtrees for stamp in collect_times(subtree)]
        if any(abs((stamp - when).total_seconds()) <= window_seconds for stamp in times):
            return {"path": str(path.relative_to(BASE)), "basis": "object_and_timestamp"}
        try:
            mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)
        except OSError:
            continue
        if abs((mtime - when).total_seconds()) <= window_seconds:
            return {"path": str(path.relative_to(BASE)), "basis": "object_and_file_mtime"}
    return None


def classify_event(event: dict[str, Any], config: dict[str, Any], *, audit_lookup=True) -> dict[str, Any]:
    if not is_material(event):
        return {"classification": "ignored_nonmaterial", "alert": False}
    if system_lifecycle_noise(event):
        return {"classification": "ignored_meta_lifecycle", "alert": False}
    if trusted_source(event, config):
        match = local_audit_match(event, int(config.get("audit_match_window_seconds") or 1800)) if audit_lookup else None
        if match:
            return {"classification": "trusted_ares_audited", "alert": False, "audit_match": match}
        return {"classification": "trusted_app_without_local_audit", "alert": True}
    if str(event.get("actor_id") or "") == "0":
        return {"classification": "meta_or_native_rule_material_change", "alert": True}
    return {"classification": "external_or_manual_change", "alert": True}


def fetch_activities(meta, token: str, account_id: str, since: dt.datetime, until: dt.datetime, max_pages: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    path = f"act_{account_id}/activities"
    fields = "event_time,date_time_in_timezone,event_type,object_id,object_name,object_type,actor_id,actor_name,application_id,application_name,translated_event_type,extra_data"
    after = None
    rows: list[dict[str, Any]] = []
    page_reports: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        params: dict[str, Any] = {
            "fields": fields,
            "since": since.isoformat(),
            "until": until.isoformat(),
            "limit": 500,
        }
        if after:
            params["after"] = after
        status, body, _ = meta.graph_get(path, token, params)
        if status != 200 or not isinstance(body, dict):
            raise RuntimeError(f"Meta activities failed: HTTP {status}")
        batch = body.get("data") or []
        rows.extend(row for row in batch if isinstance(row, dict))
        paging = body.get("paging") or {}
        after = ((paging.get("cursors") or {}).get("after")) if paging.get("next") else None
        page_reports.append({"page": page, "http_status": status, "count": len(batch), "has_next": bool(after)})
        if not after:
            break
    if page_reports and page_reports[-1]["has_next"]:
        raise RuntimeError("Meta activities pagination exceeded configured max_pages")
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        unique[event_key(row)] = row
    return sorted(unique.values(), key=lambda row: str(row.get("event_time") or "")), page_reports


def amount_label(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value)
    currency = str(value.get("currency") or "")
    minor = value.get("old_value") if "old_value" in value else value.get("new_value")
    try:
        if minor is None:
            raise ValueError("missing amount")
        return f"{currency} {float(str(minor)) / 100:.2f}"
    except (TypeError, ValueError):
        return str(minor)


def change_label(event: dict[str, Any]) -> str:
    extra = safe_extra(event.get("extra_data"))
    old = extra.get("old_value")
    new = extra.get("new_value")
    if isinstance(old, dict) and old.get("type") == "payment_amount":
        old_text = amount_label(old)
    else:
        old_text = str(old) if old is not None else "—"
    if isinstance(new, dict) and new.get("type") == "payment_amount":
        new_text = amount_label(new)
    else:
        new_text = str(new) if new is not None else "—"
    if len(old_text) > 120:
        old_text = old_text[:117] + "..."
    if len(new_text) > 120:
        new_text = new_text[:117] + "..."
    return f"{old_text} → {new_text}"


def build_alert(items: list[dict[str, Any]], config: dict[str, Any], timezone_name: str) -> str:
    tz = ZoneInfo(timezone_name)
    lines = [
        "<@344196393512075265> ⚠️ **ALTERAÇÃO EXTERNA NA CONTA META**",
        f"Conta: **{config.get('account_alias')}**",
        "",
    ]
    for item in items[:12]:
        event = item["event"]
        when = parse_time(event.get("event_time"))
        local = when.astimezone(tz).strftime("%d/%m %H:%M") if when else "horário n/d"
        actor = str(event.get("actor_name") or "Meta/desconhecido")
        app = str(event.get("application_name") or "aplicativo não informado")
        action = str(event.get("translated_event_type") or event.get("event_type") or "alteração")
        obj = str(event.get("object_name") or event.get("object_type") or "objeto sem nome")
        lines.extend([
            f"- **{local} SP — {action}**",
            f"  Ator: **{actor}** · Origem: **{app}**",
            f"  Objeto: {obj}",
            f"  Mudança: `{change_label(event)}`",
        ])
    if len(items) > 12:
        lines.append(f"- ... e mais {len(items) - 12} alterações no mesmo lote.")
    lines.extend(["", "Nenhuma correção automática foi aplicada; alteração preservada para revisão."])
    return "\n".join(lines)


def post_alert(thread_id: str, message: str) -> dict[str, Any]:
    process = subprocess.run(
        [sys.executable, str(POSTER), "--thread-id", thread_id, "--fallback-title", "Alteração externa Meta", "--verify-readback"],
        input=message,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    raw = (process.stdout or process.stderr or "").strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"ok": False, "error": "poster_non_json_response"}
    payload["returncode"] = process.returncode
    payload["ok"] = bool(process.returncode == 0 and payload.get("ok"))
    return payload


def prune_state(state: dict[str, Any], now: dt.datetime, retention_days: int) -> None:
    cutoff = now - dt.timedelta(days=retention_days)
    seen = state.get("seen") or {}
    state["seen"] = {
        key: value for key, value in seen.items()
        if (parse_time((value or {}).get("event_time")) or now) >= cutoff
    }
    deliveries = state.get("deliveries") or {}
    state["deliveries"] = {
        key: value for key, value in deliveries.items()
        if (parse_time((value or {}).get("delivered_at")) or now) >= cutoff
    }


def state_path(config: dict[str, Any]) -> Path:
    return BASE / str(config["state_path"])


def audit_dir(config: dict[str, Any]) -> Path:
    return BASE / str(config["audit_dir"])


def load_inputs(operation_path: Path, account_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    operation = json.loads(operation_path.read_text())
    account = json.loads(account_path.read_text())["accounts"][0]
    config = dict(operation.get("account_activity_monitor") or {})
    config.setdefault("account_alias", (operation.get("account") or {}).get("account_alias"))
    return operation, account, config


def fixture_events(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise RuntimeError("fixture must be a JSON list or an object with a data list")
    return [row for row in rows if isinstance(row, dict)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", type=Path, default=DEFAULT_OPERATION)
    parser.add_argument("--account", type=Path, default=DEFAULT_ACCOUNT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--baseline", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--now", help="ISO UTC override for deterministic tests")
    parser.add_argument("--skip-audit-lookup", action="store_true")
    args = parser.parse_args()

    operation, account, config = load_inputs(args.operation, args.account)
    if not config.get("enabled") and not args.dry_run:
        raise RuntimeError("account_activity_monitor is not enabled")
    account_id = str((operation.get("account") or {}).get("account_id") or "")
    if account_id != str(account.get("account_id") or ""):
        raise RuntimeError("operation/account identity mismatch")
    if str(config.get("graph_version")) != "v26.0":
        raise RuntimeError("activity monitor requires graph_version v26.0")
    now = parse_time(args.now) if args.now else utcnow()
    if now is None:
        raise RuntimeError("invalid --now")
    path = state_path(config)
    if path.exists():
        state = json.loads(path.read_text())
    else:
        state = {"schema_version": "1.0", "seen": {}, "pending_alerts": [], "deliveries": {}}
    overlap = int(config.get("overlap_seconds") or 600)
    last_check = parse_time(state.get("last_check_at"))
    if args.baseline:
        since = now - dt.timedelta(days=int(config.get("baseline_days") or 2))
    elif last_check:
        since = max(last_check - dt.timedelta(seconds=overlap), now - dt.timedelta(days=7))
    else:
        since = now - dt.timedelta(seconds=overlap)

    credential_report = None
    if args.fixture:
        events = fixture_events(args.fixture)
        pages = [{"page": 1, "http_status": 200, "count": len(events), "has_next": False, "fixture": True}]
    else:
        os.environ["ARES_META_GRAPH_VERSION"] = "v26.0"
        meta = load_module(META_COMMON, "ares_meta_activity_common")
        token, field = meta.get_token_from_1password(account.get("token_1password_item"))
        credential_report = {"item": account.get("token_1password_item"), "field": field, "token_len": len(token)}
        events, pages = fetch_activities(meta, token, account_id, since, now, int(config.get("max_pages") or 8))

    run = {
        "schema_version": "1.0",
        "operation_id": operation.get("operation_id"),
        "account_id": account_id,
        "mode": "baseline" if args.baseline else ("apply" if args.apply else "dry_run"),
        "started_at": iso_utc(now),
        "query_since": iso_utc(since),
        "query_until": iso_utc(now),
        "credential": credential_report,
        "pages": pages,
        "events_fetched": len(events),
        "classifications": {},
        "new_external": [],
        "delivery": None,
    }
    new_items: list[dict[str, Any]] = []
    for event in events:
        key = event_key(event)
        result = classify_event(event, config, audit_lookup=not args.skip_audit_lookup)
        label = result["classification"]
        run["classifications"][label] = int(run["classifications"].get(label) or 0) + 1
        if args.baseline:
            state["seen"][key] = {"event_time": event.get("event_time"), "classification": label}
            continue
        if key in state.get("seen", {}):
            continue
        state.setdefault("seen", {})[key] = {"event_time": event.get("event_time"), "classification": label}
        if result.get("alert"):
            item = {"alert_id": key, "event": event, "classification": label, "detected_at": iso_utc(now)}
            new_items.append(item)
            run["new_external"].append({
                "alert_id": key,
                "event_time": event.get("event_time"),
                "event_type": event.get("event_type"),
                "object_id": event.get("object_id"),
                "actor_id": event.get("actor_id"),
                "actor_name": event.get("actor_name"),
                "application_id": event.get("application_id"),
                "application_name": event.get("application_name"),
                "classification": label,
            })

    state["last_check_at"] = iso_utc(now)
    state["last_successful_fetch_at"] = iso_utc(now)
    state["last_query_since"] = iso_utc(since)
    state["last_query_until"] = iso_utc(now)
    state["last_event_count"] = len(events)
    state["last_classifications"] = run["classifications"]
    state.setdefault("pending_alerts", [])
    existing_pending = {item.get("alert_id") for item in state["pending_alerts"]}
    for item in new_items:
        if item["alert_id"] not in existing_pending:
            state["pending_alerts"].append(item)
    prune_state(state, now, int(config.get("retention_days") or 14))

    if args.baseline:
        state["baseline_at"] = iso_utc(now)
        atomic_json(path, state)
    elif args.apply:
        # Persist detection before the external Discord action to prevent loops.
        atomic_json(path, state)
        pending = list(state.get("pending_alerts") or [])
        if pending:
            message = build_alert(pending, config, str(operation.get("account_timezone") or "America/Sao_Paulo"))
            delivery = post_alert(str(config.get("destination_thread_id") or ""), message)
            run["delivery"] = {k: v for k, v in delivery.items() if k not in {"error"}}
            if delivery.get("ok"):
                delivered_at = iso_utc(now)
                for item in pending:
                    state.setdefault("deliveries", {})[item["alert_id"]] = {
                        "delivered_at": delivered_at,
                        "message_ids": delivery.get("message_ids") or [],
                        "readbacks_confirmed": delivery.get("readbacks_confirmed"),
                    }
                state["pending_alerts"] = []
                state["last_alert_at"] = delivered_at
                atomic_json(path, state)
            else:
                state["last_delivery_error_at"] = iso_utc(now)
                atomic_json(path, state)
    else:
        run["dry_run_pending_count"] = len(state.get("pending_alerts") or [])

    run["finished_at"] = iso_utc(utcnow())
    run["state_path"] = str(path.relative_to(BASE))
    run["pending_after"] = len(state.get("pending_alerts") or [])
    if not args.dry_run:
        out_dir = audit_dir(config)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        audit_path = out_dir / f"run-{stamp}-{run['mode']}.json"
        atomic_json(audit_path, run)
        append_jsonl(EVENT_AUDIT, {
            "ts": iso_utc(now),
            "event": "meta_account_activity_monitor_run",
            "agent": "ares",
            "operation_id": operation.get("operation_id"),
            "account_id": account_id,
            "mode": run["mode"],
            "events_fetched": len(events),
            "new_external": len(new_items),
            "pending_after": run["pending_after"],
            "delivery_ok": (run.get("delivery") or {}).get("ok") if run.get("delivery") else None,
            "audit_path": str(audit_path.relative_to(BASE)),
        })
        run["audit_path"] = str(audit_path.relative_to(BASE))

    print(json.dumps({
        "ok": True,
        "mode": run["mode"],
        "events_fetched": len(events),
        "new_external": len(new_items),
        "pending_after": run["pending_after"],
        "delivery_ok": (run.get("delivery") or {}).get("ok") if run.get("delivery") else None,
        "classifications": run["classifications"],
        "audit_path": run.get("audit_path"),
    }, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
