#!/usr/bin/env python3
"""Read-only intake simulation for Eggbev campaign creation requests."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OP_PATH = ROOT / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
OP_V3_PATH = ROOT / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT-v3.json"
ACCOUNT_PATH = ROOT / "data/ares/meta-ads/accounts/1034081997659047.json"
INVENTORY_PATH = ROOT / "data/ares/creative-ops/inventory/assets.jsonl"
MEDIA_REGISTRY_PATH = ROOT / "data/ares/meta-ads/engine-v3/media-registry.json"
COMMON_PATH = ROOT / "scripts/ares-eggbev-roas-common.py"
TZ = ZoneInfo("America/New_York")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def account_entry() -> dict[str, Any]:
    raw = load_json(ACCOUNT_PATH)
    rows = raw.get("accounts") if isinstance(raw, dict) else None
    if isinstance(rows, list) and rows:
        return dict(rows[0])
    return dict(raw)


def inventory_summary(required: int) -> dict[str, Any]:
    rows = []
    for raw in INVENTORY_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if str(row.get("vertical") or "").upper() != "CC":
            continue
        if str(row.get("country") or "").upper() != "US":
            continue
        if str(row.get("language") or "").upper() != "EN":
            continue
        rows.append(row)
    ready = [row for row in rows if row.get("status") == "01_READY" and row.get("metadata_clean") is True]
    eligible = [row for row in ready if row.get("ares_eligible") is True and row.get("reservation_status") != "RESERVADO_PELO_GESTOR"]
    reserved = [row for row in ready if row.get("reservation_status") == "RESERVADO_PELO_GESTOR"]
    return {
        "pool": "CC_US_EN/01_READY",
        "inventory_total": len(rows),
        "technically_ready_clean": len(ready),
        "ares_eligible_now": len(eligible),
        "manager_reserved_now": len(reserved),
        "required_unique_assets": required,
        "sufficient_eligible_now": len(eligible) >= required,
        "request_can_trigger_scoped_release_review": True,
        "selection_policy": "reconcile Drive x Meta, skip used/conflicting assets, reserve exactly the selected unique lineage; never select by filename order alone",
    }


def recursive_count_account_assets(value: Any, account_id: str) -> int:
    count = 0
    if isinstance(value, dict):
        account_match = str(value.get("account_id") or value.get("ad_account_id") or "").replace("act_", "") == account_id
        asset_marker = bool(value.get("asset_id") or value.get("video_id") or value.get("image_hash") or value.get("meta_video_id"))
        if account_match and asset_marker:
            count += 1
        count += sum(recursive_count_account_assets(child, account_id) for child in value.values())
    elif isinstance(value, list):
        count += sum(recursive_count_account_assets(child, account_id) for child in value)
    return count


def media_summary(account_id: str) -> dict[str, Any]:
    registry = load_json(MEDIA_REGISTRY_PATH) if MEDIA_REGISTRY_PATH.exists() else {}
    count = recursive_count_account_assets(registry, account_id)
    return {"account_registry_entries": count, "prestage_ready": count > 0}


def load_common():
    spec = importlib.util.spec_from_file_location("eggbev_creation_intake_common", COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Eggbev common module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def live_page_check(page_token: str, operation: dict[str, Any], account: dict[str, Any]) -> dict[str, Any]:
    common = load_common()
    meta, sb, token, _ = common.load_runtime_modules(account)
    report_date = dt.datetime.now(TZ).date().isoformat()
    bundle = common.fetch_sb_bundle(sb, operation, report_date)
    page_rows = [row for row in bundle.get("page_rows") or [] if str(row.get("UTM_CAMPAIGN") or "").lower() == page_token.lower()]
    page_ids = {str(row.get("FB_PAGE_ID") or "") for row in page_rows if row.get("FB_PAGE_ID")}
    page_id = next(iter(page_ids)) if len(page_ids) == 1 else None
    page_get_http = None
    page_name = None
    if page_id:
        page_get_http, page_body, _ = meta.graph_get(page_id, token, {"fields": "id,name,link"})
        if page_get_http == 200 and isinstance(page_body, dict):
            page_name = page_body.get("name")
    account_id = str(account.get("account_id") or "").replace("act_", "")
    filtering = json.dumps([{"field": "name", "operator": "CONTAIN", "value": page_token}], separators=(",", ":"))
    campaign_status, campaign_body, _ = meta.graph_get("act_" + account_id + "/campaigns", token, {"fields": "id,name,status,effective_status", "filtering": filtering, "limit": 100})
    campaigns = (campaign_body.get("data") or []) if campaign_status == 200 and isinstance(campaign_body, dict) else []
    return {
        "page_token": page_token,
        "smart_bidding_page_rows": len(page_rows),
        "unique_page_identity": len(page_ids) == 1,
        "page_id_present": bool(page_id),
        "meta_page_read_http": page_get_http,
        "meta_page_accessible": page_get_http == 200,
        "page_name": page_name,
        "leads_snapshot": page_rows[0].get("LEADS") if len(page_rows) == 1 else None,
        "messenger_source_ready": bundle.get("ready"),
        "messenger_source_reason": bundle.get("reason"),
        "existing_campaign_name_matches": len(campaigns),
    }


def next_midnight(now: dt.datetime | None = None) -> str:
    current = now.astimezone(TZ) if now else dt.datetime.now(TZ)
    tomorrow = current.date() + dt.timedelta(days=1)
    return dt.datetime.combine(tomorrow, dt.time(0, 0), tzinfo=TZ).isoformat()


def simulate(args: argparse.Namespace) -> dict[str, Any]:
    operation = load_json(OP_PATH)
    operation_v3 = load_json(OP_V3_PATH)
    account = account_entry()
    account_id = str(account.get("account_id") or "").replace("act_", "")
    required_assets = args.campaign_count * args.creatives_per_campaign
    inventory = inventory_summary(required_assets)
    media = media_summary(account_id)
    page = live_page_check(args.page_token, operation, account) if args.live_page_check else {"page_token": args.page_token, "live_check": False}

    missing_inputs = []
    if args.daily_budget_usd is None:
        missing_inputs.append("daily_budget_usd_per_campaign")
    explicit_creation_package = all([
        args.primary_text,
        args.headline,
        args.description,
        args.cta,
        args.campaign_name_template,
        args.ad_name_template,
        args.tracking_reference,
        args.placements_reference,
    ])
    if not args.creation_reference and not explicit_creation_package:
        missing_inputs.append("canonical_creation_reference_or_explicit_naming_copy_tracking_placements_package")

    readiness_blockers = []
    runtime_creation = (account.get("runtime_routes") or {}).get("campaign_creation") or {}
    if runtime_creation.get("write_enabled") is not True:
        readiness_blockers.append("creation_write_disabled")
    if runtime_creation.get("runner_built") is not True:
        readiness_blockers.append("eggbev_from_zero_runner_not_built")
    if "from_zero_prestaged" not in (operation_v3.get("supported_modes") or []):
        readiness_blockers.append("operation_v3_from_zero_mode_not_onboarded")
    adset = operation.get("campaign_structure", {}).get("adset", {})
    if adset.get("placements_mode") == "MANUAL_ONLY" and not adset.get("manual_positions"):
        readiness_blockers.append("exact_manual_placements_not_materialized")
    if not media["prestage_ready"]:
        readiness_blockers.append("eggbev_media_not_prestaged_in_v3")
    if not inventory["sufficient_eligible_now"]:
        readiness_blockers.append("insufficient_currently_eligible_unique_assets")
    if args.live_page_check and not page.get("unique_page_identity"):
        readiness_blockers.append("page_token_not_uniquely_reconciled")
    if args.live_page_check and not page.get("meta_page_accessible"):
        readiness_blockers.append("meta_page_access_not_verified")

    status = "NEEDS_INPUT" if missing_inputs else ("BLOCKED_READINESS" if readiness_blockers else "READY_FOR_FINAL_SUMMARY")
    return {
        "mode": "read_only_simulation",
        "meta_writes": 0,
        "drive_writes": 0,
        "reservations_written": 0,
        "request": {
            "page_token": args.page_token,
            "campaign_count": args.campaign_count,
            "creatives_per_campaign": args.creatives_per_campaign,
            "required_unique_assets": required_assets,
            "source_folder_input": args.source_folder,
            "source_folder_canonical": "CC_US_EN",
        },
        "defaults_applied": {
            "structure": f"{args.campaign_count} campaigns x 1 ad set x {args.creatives_per_campaign} ads",
            "status": "ACTIVE",
            "start_time": next_midnight(),
            "timezone": "America/New_York",
            "destination": "MESSENGER",
            "adset_name": "AdG1",
            "creative_reuse_across_campaigns": False,
        },
        "provided_inputs": {
            "daily_budget_usd": args.daily_budget_usd,
            "creation_reference": args.creation_reference,
            "copy_complete": all([args.primary_text, args.headline, args.description, args.cta]),
            "explicit_creation_package_complete": explicit_creation_package,
        },
        "page_preflight": page,
        "creative_inventory": inventory,
        "media_registry": media,
        "missing_user_inputs": missing_inputs,
        "readiness_blockers": readiness_blockers,
        "final_approval_gate": "not_reached; show full Page/start/budget/assets/copy/JSON/tracking/placements/status summary and wait for explicit OK",
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-token", required=True)
    parser.add_argument("--campaign-count", type=int, required=True)
    parser.add_argument("--creatives-per-campaign", type=int, choices=[3, 5], required=True)
    parser.add_argument("--source-folder", default="cc en us")
    parser.add_argument("--daily-budget-usd", type=float)
    parser.add_argument("--creation-reference")
    parser.add_argument("--primary-text")
    parser.add_argument("--headline")
    parser.add_argument("--description")
    parser.add_argument("--cta")
    parser.add_argument("--campaign-name-template")
    parser.add_argument("--ad-name-template")
    parser.add_argument("--tracking-reference")
    parser.add_argument("--placements-reference")
    parser.add_argument("--live-page-check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.campaign_count < 1 or args.campaign_count > 100:
        parser.error("campaign-count must be between 1 and 100")
    payload = simulate(args)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
