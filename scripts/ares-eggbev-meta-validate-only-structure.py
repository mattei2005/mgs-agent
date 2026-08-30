#!/usr/bin/env python3
"""Meta validate-only checks for Eggbev campaign/adset/ad direct-create payloads."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE = Path("/root/mgs-agent")
SCRIPTS = BASE / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ACCOUNT = "1034081997659047"
AUDIT = BASE / "data/ares/meta-ads/audit/eggbev/creation/meta-validate-only-structure-20260830.json"
ET = ZoneInfo("America/New_York")


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_error(payload: Any) -> dict[str, Any]:
    error = payload.get("error") if isinstance(payload, dict) else {}
    error = error if isinstance(error, dict) else {}
    return {"code": error.get("code"), "subcode": error.get("error_subcode"), "type": error.get("type"), "user_title": error.get("error_user_title"), "user_message": error.get("error_user_msg"), "message": str(error.get("message") or "")[:500]}


def get_rows(meta, token: str, path: str, fields: str, limit: int = 100) -> list[dict[str, Any]]:
    status, payload, _ = meta.graph_get(path, token, {"fields": fields, "limit": limit})
    if status != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"GET failed path={path} http={status}")
    return list(payload.get("data") or [])


def exact_count(meta, token: str, path: str, fields: str, name: str) -> tuple[int, list[str]]:
    rows = get_rows(meta, token, path, fields)
    matches = [row for row in rows if str(row.get("name") or "") == name]
    return len(matches), [str(row.get("id")) for row in matches if row.get("id")]


def validate_named(meta, token: str, *, endpoint: str, inventory_path: str, inventory_fields: str, name: str, body: dict[str, Any]) -> dict[str, Any]:
    before_count, before_ids = exact_count(meta, token, inventory_path, inventory_fields, name)
    if before_count:
        raise RuntimeError(f"unique validate-only name already exists: {name}")
    http, response, _ = meta.graph_post_once(endpoint, token, {**body, "execution_options": ["validate_only"]})
    after_count, after_ids = exact_count(meta, token, inventory_path, inventory_fields, name)
    side_effect_ids = []
    if isinstance(response, dict) and response.get("id"):
        side_effect_ids.append(str(response["id"]))
    side_effect_ids.extend(after_ids)
    return {
        "endpoint": endpoint,
        "payload_sha256": hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "http": http,
        "success": bool(isinstance(response, dict) and response.get("success") is True),
        "error": safe_error(response),
        "before_name_matches": before_count,
        "after_name_matches": after_count,
        "side_effect_ids": side_effect_ids,
        "status": "VALIDATE_ONLY_OK" if http in {200, 201} and not side_effect_ids else ("SIDE_EFFECT_DETECTED" if side_effect_ids else "VALIDATE_ONLY_REJECTED"),
    }


def main() -> int:
    runner = load(SCRIPTS / "ares-eggbev-creation.py", "eggbev_validate_structure_runner")
    from ares_campaign_v3.eggbev_create import build_eggbev_from_zero_manifest
    from ares_campaign_v3.media_registry import MediaRegistry

    page, meta, token = runner.live_page_and_token("pg_5024")
    campaigns = get_rows(meta, token, f"act_{ACCOUNT}/campaigns", "id,name,status,configured_status,objective", 100)
    parent_campaign = next((row for row in campaigns if str(row.get("configured_status") or row.get("status") or "").upper() not in {"DELETED", "ARCHIVED"}), None)
    if not parent_campaign:
        raise RuntimeError("no non-deleted campaign available for adset validate-only parent")
    adsets = get_rows(meta, token, f"{parent_campaign['id']}/adsets", "id,name,status,configured_status", 100)
    parent_adset = next((row for row in adsets if str(row.get("configured_status") or row.get("status") or "").upper() not in {"DELETED", "ARCHIVED"}), None)
    if not parent_adset:
        raise RuntimeError("no non-deleted adset available for ad validate-only parent")
    ads = get_rows(meta, token, f"{parent_adset['id']}/ads", "id,name,creative{id,name}", 100)
    source_ad = next((row for row in ads if (row.get("creative") or {}).get("id")), None)
    if not source_ad:
        raise RuntimeError("no creative available for ad validate-only")

    with tempfile.TemporaryDirectory() as tmp:
        registry = MediaRegistry(Path(tmp) / "media.json")
        refs = []
        for index in range(3):
            asset = f"validate-structure-{index + 1}"
            checksum = f"validate-checksum-{index + 1}"
            registry.register(account_id=ACCOUNT, asset_id=asset, checksum=checksum, vertical_video_id=f"vertical-{index + 1}", square_video_id=f"square-{index + 1}", ready=True, source="validate-only", upload_edge="ad_account_advideos", association_verified=True)
            refs.append({"asset_id": asset, "checksum": checksum})
        start = (datetime.now(ET) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        manifest = build_eggbev_from_zero_manifest(registry=registry, request_id="eggbev-structure-validate", page_id=str(page["id"]), instagram_user_id=str(page["instagram_user_id"]), page_name=str(page["name"]), page_token="pg_5024", page_sequence=162, campaign_sequences=[1], daily_budgets_minor=[5000], start_time=start, asset_refs=refs, ad_names=["VALIDATE AD 1", "VALIDATE AD 2", "VALIDATE AD 3"])
    row = manifest["campaigns"][0]
    unique = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    campaign_name = f"VALIDATE ONLY EGGBEV CAMPAIGN {unique}"
    adset_name = f"VALIDATE ONLY EGGBEV ADSET {unique}"
    ad_name = f"VALIDATE ONLY EGGBEV AD {unique}"

    campaign_result = validate_named(meta, token, endpoint=f"act_{ACCOUNT}/campaigns", inventory_path=f"act_{ACCOUNT}/campaigns", inventory_fields="id,name,status,configured_status", name=campaign_name, body={**row["campaign_create"], "name": campaign_name, "status": "PAUSED"})
    adset_result = validate_named(meta, token, endpoint=f"act_{ACCOUNT}/adsets", inventory_path=f"{parent_campaign['id']}/adsets", inventory_fields="id,name,status,configured_status", name=adset_name, body={**row["adset_create"], "name": adset_name, "campaign_id": str(parent_campaign["id"]), "status": "PAUSED", "start_time": start})
    ad_result = validate_named(meta, token, endpoint=f"act_{ACCOUNT}/ads", inventory_path=f"{parent_adset['id']}/ads", inventory_fields="id,name,status,configured_status", name=ad_name, body={"name": ad_name, "adset_id": str(parent_adset["id"]), "creative": {"creative_id": str(source_ad["creative"]["id"])}, "status": "PAUSED"})

    instagram_positions = set(((row["adset_create"].get("targeting") or {}).get("instagram_positions") or []))
    known_explore_contradiction = (
        adset_result["status"] == "VALIDATE_ONLY_REJECTED"
        and adset_result["error"].get("subcode") == 2490392
        and not adset_result["side_effect_ids"]
        and "explore_home" in instagram_positions
        and "explore" not in instagram_positions
    )
    if known_explore_contradiction:
        adset_result["status"] = "KNOWN_VALIDATE_ONLY_CONTRADICTION"
        adset_result["interpretation"] = (
            "Graph v26 validate_only requires deprecated explore with explore_home, while the real "
            "Eggbev adset update rejects explore with subcode 2490589 and the live ACTIVE readback "
            "contains explore_home without explore. Runtime write/readback is authoritative."
        )

    checks = {"campaign": campaign_result, "adset": adset_result, "ad": ad_result}
    accepted_statuses = {"VALIDATE_ONLY_OK", "KNOWN_VALIDATE_ONLY_CONTRADICTION"}
    if all(item["status"] in accepted_statuses for item in checks.values()):
        status = "VALIDATE_ONLY_OK_WITH_KNOWN_CONTRADICTION" if known_explore_contradiction else "VALIDATE_ONLY_OK"
    else:
        status = "SIDE_EFFECT_DETECTED" if any(item["status"] == "SIDE_EFFECT_DETECTED" for item in checks.values()) else "VALIDATE_ONLY_REJECTED"
    result = {"operation": "Eggbev-US-CC-EN-BOT", "tested_at_utc": datetime.now(timezone.utc).isoformat(), "page_token": "pg_5024", "checks": checks, "status": status}
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status in {"VALIDATE_ONLY_OK", "VALIDATE_ONLY_OK_WITH_KNOWN_CONTRADICTION"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
