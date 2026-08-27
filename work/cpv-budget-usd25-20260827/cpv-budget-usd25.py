#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("/root/mgs-agent")
COMMON_PATH = ROOT / "scripts/ares-meta-common.py"
OPERATION_PATH = ROOT / "data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json"
ACCOUNT_PATH = ROOT / "data/ares/meta-ads/accounts/1046241194533786.json"
AUDIT_PATH = ROOT / "data/ares/meta-ads/audit/controlled-write/Creditoparaveiculo-BR-CAR-BR/c07-c25-c30-budget-usd25-20260827.json"
REQUEST_ID = "cpv-budget-usd25-c07-c25-c30-20260827"
ACCOUNT_ID = "1046241194533786"
ACCOUNT_ACT = f"act_{ACCOUNT_ID}"
CAMPAIGN_NUMBERS = [7, 25, 26, 27, 28, 29, 30]
TARGET_MINOR = 2500
SOURCE = "discord:thread:1542574918791856199"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(raw, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(raw):
            os.unlink(raw)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_common():
    spec = importlib.util.spec_from_file_location("ares_meta_common_cpv_budget_25", COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Meta common helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_error(common, body: Any) -> Any:
    return common.safe_meta_error(body) if isinstance(body, dict) else {"response_type": type(body).__name__}


def graph_get_ok(common, token: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
    status, body, _ = common.graph_get(path, token, params)
    if status != 200 or not isinstance(body, dict) or body.get("error"):
        raise RuntimeError(json.dumps({"stage": "meta_get", "path_label": path.split("/")[0], "http": status, "error": safe_error(common, body)}, ensure_ascii=False))
    return body


def campaign_snapshot(common, token: str, campaign_id: str) -> dict[str, Any]:
    fields = "id,account_id,name,status,effective_status,configured_status,daily_budget,bid_strategy,start_time,updated_time"
    body = graph_get_ok(common, token, campaign_id, {"fields": fields})
    return {key: body.get(key) for key in fields.split(",")}


def list_campaigns(common, token: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        params: dict[str, Any] = {
            "fields": "id,account_id,name,status,effective_status,configured_status,daily_budget,updated_time",
            "limit": 500,
        }
        if after:
            params["after"] = after
        body = graph_get_ok(common, token, f"{ACCOUNT_ACT}/campaigns", params)
        page = body.get("data") or []
        if not isinstance(page, list):
            raise RuntimeError("Meta campaigns payload is malformed")
        rows.extend(item for item in page if isinstance(item, dict))
        cursors = ((body.get("paging") or {}).get("cursors") or {})
        next_after = cursors.get("after")
        if not (body.get("paging") or {}).get("next") or not next_after or next_after == after:
            break
        after = str(next_after)
    return rows


def is_terminal(row: dict[str, Any]) -> bool:
    statuses = {str(row.get(key) or "").upper() for key in ("status", "configured_status", "effective_status")}
    return bool(statuses & {"DELETED", "ARCHIVED"})


def is_configured_active(row: dict[str, Any]) -> bool:
    configured = str(row.get("configured_status") or row.get("status") or "").upper()
    return configured == "ACTIVE" and not is_terminal(row)


def active_budget_minor(rows: list[dict[str, Any]]) -> int:
    total = 0
    for row in rows:
        if not is_configured_active(row):
            continue
        try:
            value = int(str(row.get("daily_budget") or "0"))
        except ValueError as exc:
            raise RuntimeError(f"malformed active campaign budget for {row.get('id')}") from exc
        if value <= 0:
            raise RuntimeError(f"missing active campaign budget for {row.get('id')}")
        total += value
    return total


def validate_identity(number: int, row: dict[str, Any], expected_id: str) -> None:
    if str(row.get("id")) != expected_id:
        raise RuntimeError(f"C{number:02d} campaign ID drift")
    if str(row.get("account_id")) != ACCOUNT_ID:
        raise RuntimeError(f"C{number:02d} account ID mismatch")
    if not re.search(rf"\bb01fb13c{number:02d}\b", str(row.get("name") or ""), re.IGNORECASE):
        raise RuntimeError(f"C{number:02d} canonical wrapper mismatch")
    if is_terminal(row):
        raise RuntimeError(f"C{number:02d} is terminal and cannot receive a budget write")
    try:
        current = int(str(row.get("daily_budget") or "0"))
    except ValueError as exc:
        raise RuntimeError(f"C{number:02d} current budget is malformed") from exc
    if current <= 0:
        raise RuntimeError(f"C{number:02d} current budget is missing")


def sanitized(rows: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "campaign": f"C{number:02d}",
            "campaign_id": str(row.get("id")),
            "name": str(row.get("name") or ""),
            "status": str(row.get("configured_status") or row.get("status") or ""),
            "effective_status": str(row.get("effective_status") or ""),
            "daily_budget_minor": int(str(row.get("daily_budget") or "0")),
            "daily_budget_usd": int(str(row.get("daily_budget") or "0")) / 100,
            "updated_time": row.get("updated_time"),
        }
        for number, row in sorted(rows.items())
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    operation = load_json(OPERATION_PATH)
    account_config = load_json(ACCOUNT_PATH)["accounts"][0]
    token_item = str(account_config.get("token_1password_item") or "")
    if not token_item:
        raise RuntimeError("Meta token item is not configured")
    if operation.get("account", {}).get("account_id") != ACCOUNT_ID:
        raise RuntimeError("operation account mismatch")
    if operation.get("account_currency") != "USD" or operation.get("account_timezone") != "America/Sao_Paulo":
        raise RuntimeError("operation currency/timezone mismatch")

    allowed = (((operation.get("management_scope") or {}).get("autonomous_action_scope") or {}).get("allowed_campaigns") or {})
    expected_ids = {number: str((allowed.get(f"{number:02d}") or {}).get("campaign_id") or "") for number in CAMPAIGN_NUMBERS}
    if any(not value for value in expected_ids.values()):
        raise RuntimeError("one or more campaign IDs are missing from the immutable allowlist")

    common = load_common()
    token, token_field = common.get_token_from_1password(item_name=token_item)
    account = graph_get_ok(common, token, ACCOUNT_ACT, {"fields": "id,name,account_status,currency,timezone_name,disable_reason"})
    if (
        str(account.get("id")) != ACCOUNT_ACT
        or str(account.get("currency")) != "USD"
        or str(account.get("timezone_name")) != "America/Sao_Paulo"
        or int(account.get("account_status") or 0) != 1
        or int(account.get("disable_reason") or 0) != 0
    ):
        raise RuntimeError("Meta account identity or health gate failed")

    account_rows_before = list_campaigns(common, token)
    by_id = {str(row.get("id")): row for row in account_rows_before}
    preflight: dict[int, dict[str, Any]] = {}
    for number in CAMPAIGN_NUMBERS:
        row = campaign_snapshot(common, token, expected_ids[number])
        validate_identity(number, row, expected_ids[number])
        duplicates = [
            item for item in account_rows_before
            if not is_terminal(item)
            and re.search(rf"\bb01fb13c{number:02d}\b", str(item.get("name") or ""), re.IGNORECASE)
        ]
        if len(duplicates) != 1 or str(duplicates[0].get("id")) != expected_ids[number]:
            raise RuntimeError(f"C{number:02d} has ambiguous non-terminal identity")
        if expected_ids[number] not in by_id:
            raise RuntimeError(f"C{number:02d} is absent from the live account collection")
        preflight[number] = row

    active_before = active_budget_minor(account_rows_before)
    planned_delta = sum(
        TARGET_MINOR - int(str(row.get("daily_budget") or "0"))
        for row in preflight.values()
        if is_configured_active(row)
    )
    projected_active = active_before + planned_delta
    effective_envelope = max(50000, projected_active)
    audit: dict[str, Any] = {
        "schema_version": 1,
        "request_id": REQUEST_ID,
        "operation": "Creditoparaveiculo-BR-CAR-BR-13-G006",
        "authorization": {"authorized_by": "Rodolfo Mattei", "source": SOURCE, "scope": [f"C{number:02d}" for number in CAMPAIGN_NUMBERS], "target_budget_usd": 25},
        "mode": "CONTROLLED_WRITE" if args.execute else "DRY_RUN",
        "created_at_utc": utc_now(),
        "account": {"id": ACCOUNT_ID, "name": account.get("name"), "currency": account.get("currency"), "timezone": account.get("timezone_name"), "healthy": True},
        "credential_report": {"item": token_item, "field": token_field, "len": len(token)},
        "preflight": sanitized(preflight),
        "budget_plan": {
            "active_before_minor": active_before,
            "active_before_usd": active_before / 100,
            "selected_active_delta_minor": planned_delta,
            "selected_active_delta_usd": planned_delta / 100,
            "projected_active_minor": projected_active,
            "projected_active_usd": projected_active / 100,
            "effective_internal_envelope_minor": effective_envelope,
            "effective_internal_envelope_usd": effective_envelope / 100,
            "target_per_campaign_minor": TARGET_MINOR,
            "target_per_campaign_usd": 25,
        },
        "writes": [],
        "status": "DRY_RUN_OK" if not args.execute else "PREFLIGHT_COMPLETE",
        "side_effects": {"campaign_budget_writes": False, "campaign_status_writes": False, "billing_writes": False},
    }
    if args.verify:
        off_target = [row for row in sanitized(preflight) if row["daily_budget_minor"] != TARGET_MINOR]
        print(json.dumps({
            "status": "VERIFY_OK" if not off_target else "VERIFY_MISMATCH",
            "request_id": REQUEST_ID,
            "campaigns": sanitized(preflight),
            "active_account_budget_minor": active_before,
            "active_account_budget_usd": active_before / 100,
            "off_target": off_target,
            "side_effects": False,
        }, ensure_ascii=False, indent=2))
        return 0 if not off_target else 3
    atomic_json(AUDIT_PATH, audit)

    if not args.execute:
        print(json.dumps({"status": "DRY_RUN_OK", "request_id": REQUEST_ID, "campaigns": sanitized(preflight), "budget_plan": audit["budget_plan"], "audit": str(AUDIT_PATH)}, ensure_ascii=False, indent=2))
        return 0

    for number in CAMPAIGN_NUMBERS:
        campaign_id = expected_ids[number]
        original = preflight[number]
        current = campaign_snapshot(common, token, campaign_id)
        validate_identity(number, current, campaign_id)
        if str(current.get("updated_time") or "") != str(original.get("updated_time") or "") or str(current.get("daily_budget") or "") != str(original.get("daily_budget") or ""):
            raise RuntimeError(f"C{number:02d} changed after preflight; budget write aborted before this campaign")
        original_minor = int(str(current.get("daily_budget") or "0"))
        entry = {
            "campaign": f"C{number:02d}",
            "campaign_id": campaign_id,
            "original_budget_minor": original_minor,
            "target_budget_minor": TARGET_MINOR,
            "status_before": str(current.get("configured_status") or current.get("status") or ""),
            "updated_time_before": current.get("updated_time"),
            "stage": "in_flight",
            "started_at_utc": utc_now(),
        }
        audit["writes"].append(entry)
        audit["status"] = f"C{number:02d}_IN_FLIGHT"
        atomic_json(AUDIT_PATH, audit)

        if original_minor == TARGET_MINOR:
            entry.update(stage="already_target", post_attempted=False, completed_at_utc=utc_now())
            atomic_json(AUDIT_PATH, audit)
            continue

        status, body, _ = common.graph_post_once(campaign_id, token, {"daily_budget": str(TARGET_MINOR)})
        entry["post_attempted"] = True
        entry["post_http_status"] = status
        entry["post_success"] = bool(isinstance(body, dict) and body.get("success") is True)
        if not entry["post_success"]:
            entry["post_error"] = safe_error(common, body)
        atomic_json(AUDIT_PATH, audit)

        after = campaign_snapshot(common, token, campaign_id)
        validate_identity(number, after, campaign_id)
        after_minor = int(str(after.get("daily_budget") or "0"))
        entry["readback"] = sanitized({number: after})[0]
        if after_minor != TARGET_MINOR:
            entry["stage"] = "readback_mismatch"
            audit["status"] = "RECOVERY_REQUIRED"
            audit["failure"] = {"campaign": f"C{number:02d}", "http": status, "error": safe_error(common, body), "readback_budget_minor": after_minor}
            atomic_json(AUDIT_PATH, audit)
            raise RuntimeError(f"C{number:02d} budget write did not converge; readback preserved for recovery")
        if str(after.get("configured_status") or after.get("status") or "") != entry["status_before"]:
            entry["stage"] = "status_drift"
            audit["status"] = "RECOVERY_REQUIRED"
            atomic_json(AUDIT_PATH, audit)
            raise RuntimeError(f"C{number:02d} status changed unexpectedly")
        entry.update(stage="readback_verified", completed_at_utc=utc_now())
        audit["side_effects"]["campaign_budget_writes"] = True
        atomic_json(AUDIT_PATH, audit)

    final_rows = list_campaigns(common, token)
    final: dict[int, dict[str, Any]] = {}
    for number in CAMPAIGN_NUMBERS:
        row = campaign_snapshot(common, token, expected_ids[number])
        validate_identity(number, row, expected_ids[number])
        if int(str(row.get("daily_budget") or "0")) != TARGET_MINOR:
            raise RuntimeError(f"C{number:02d} failed final consolidated budget readback")
        final[number] = row
    active_after = active_budget_minor(final_rows)
    audit["final_readback"] = sanitized(final)
    audit["budget_result"] = {
        "active_before_minor": active_before,
        "active_after_minor": active_after,
        "active_before_usd": active_before / 100,
        "active_after_usd": active_after / 100,
        "effective_internal_envelope_usd": max(50000, active_after) / 100,
    }
    audit["status"] = "COMPLETE_READBACK_VERIFIED"
    audit["completed_at_utc"] = utc_now()
    atomic_json(AUDIT_PATH, audit)
    print(json.dumps({"status": audit["status"], "request_id": REQUEST_ID, "campaigns": audit["final_readback"], "budget_result": audit["budget_result"], "audit": str(AUDIT_PATH)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAILED_OR_RECOVERY_REQUIRED", "request_id": REQUEST_ID, "error": str(exc)[:1000], "audit": str(AUDIT_PATH)}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
