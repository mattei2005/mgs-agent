#!/usr/bin/env python3
"""Daily Drive-backed campaign creation for Creditoparaveiculo G006.

Creates two scheduled MAXVOL CBO campaigns, each 1x1x3, using six
reconciled CAR_BR_BR videos from the canonical Shared Drive. The runner is
fail-closed, idempotent by São Paulo operational date, and keeps credentials
out of logs/audits.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

BASE = Path("/root/mgs-agent")
PROFILE = Path("/root/.hermes/profiles/ares")
COMMON_PATH = BASE / "scripts/ares-meta-common.py"
DRIVE_MODULE_PATH = BASE / "scripts/ares-drive-upload-manual-inventory.py"
OP_PATH = BASE / "data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json"
INVENTORY_PATH = BASE / "data/ares/creative-ops/inventory/assets.jsonl"
AUDIT_DIR = BASE / "data/ares/meta-ads/audit/controlled-write/Creditoparaveiculo-BR-CAR-BR"
STATE_PATH = BASE / "data/ares/meta-ads/state/creditoparaveiculo-daily-create.json"
RECONCILIATION_PATH = BASE / "data/ares/meta-ads/reconciliation/Creditoparaveiculo-BR-CAR-BR.json"
WORK_ROOT = PROFILE / "work/creditoparaveiculo-daily-create"
ACCOUNT_ID = "1046241194533786"
ACCOUNT_ACT = f"act_{ACCOUNT_ID}"
ACCOUNT_ALIAS = "Creditoparaveiculo-BR-CAR-BR-13-G006"
TOKEN_ITEM = "Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006"
PAGE_ID = "621037101089579"
SOURCE_CAMPAIGN_ID = "120250209380780632"  # C08 MAXVOL
SOURCE_ADSET_ID = "120250209380820632"
GRAPH_VERSION = "v26.0"
DRIVE_ID = "0AEwt4Ye690ocUk9PVA"
DRIVE_ROOT_ID = DRIVE_ID
FOLDER_MIME = "application/vnd.google-apps.folder"
SP = ZoneInfo("America/Sao_Paulo")
THREAD_CREATION = "1539826050765299872"
BUDGET_MINOR = 3000
ACCOUNT_CAP_MINOR = 30000
CAMPAIGN_COUNT = 2
ADS_PER_CAMPAIGN = 3
ASSET_COUNT = CAMPAIGN_COUNT * ADS_PER_CAMPAIGN
PREFERRED_SLOT_ORDER = [12, 13]  # contiguous next sequence; fail closed if either slot is occupied
CLONE_READ_CALLS_PER_CAMPAIGN = 6
CLONE_WRITE_CALLS_PER_CAMPAIGN = 12
FROM_ZERO_WRITE_CALLS_PER_CAMPAIGN = 13
SCORE_READBACK_RESERVE_POINTS = 5
SANITIZER = BASE / "scripts/clean-creative-metadata.sh"
DEFAULT_EXPLICIT_ASSETS = [
    "CAR_BR_BR_VID_SCORE_BAIXO_PV_016.mp4",
    "CAR_BR_BR_VID_SCORE_BAIXO_PV_017.mp4",
    "CAR_BR_BR_VID_SCORE_BAIXO_PV_018.mp4",
    "CAR_BR_BR_VID_SEM_ENTRADA_PV_037.mp4",
    "CAR_BR_BR_VID_SEM_ENTRADA_PV_038.mp4",
    "CAR_BR_BR_VID_SEM_ENTRADA_PV_039.mp4",
]


class Stop(RuntimeError):
    def __init__(self, stage: str, detail: Any):
        self.stage = stage
        self.detail = detail
        super().__init__(f"{stage}: {detail}")


class ReadbackDeferred(Stop):
    def __init__(self, stage: str, detail: Any, retry_after_seconds: int = 300):
        self.retry_after_seconds = max(60, int(retry_after_seconds))
        super().__init__(stage, detail)


def now_sp() -> datetime:
    return datetime.now(SP)


def stamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp_sp() -> str:
    return now_sp().isoformat()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def atomic_inventory(rows: list[dict[str, Any]]) -> None:
    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{INVENTORY_PATH.name}.", dir=INVENTORY_PATH.parent)
    tmp = Path(tmp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, INVENTORY_PATH)
        os.chmod(INVENTORY_PATH, 0o600)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def load_inventory() -> list[dict[str, Any]]:
    return [json.loads(line) for line in INVENTORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_common():
    os.environ.setdefault("ARES_META_TOKEN_CACHE_PATH", "/root/.cache/mgs/ares-meta-token-creditoparaveiculo-rafael.json")
    os.environ.setdefault("ARES_META_TOKEN_CACHE_LOCK_PATH", "/root/.cache/mgs/ares-meta-token-creditoparaveiculo-rafael.json.lock")
    os.environ.setdefault("ARES_META_GRAPH_VERSION", GRAPH_VERSION)
    spec = importlib.util.spec_from_file_location("ares_meta_cpv_daily_create", COMMON_PATH)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load Meta common helper")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.GRAPH_VERSION = GRAPH_VERSION
    return mod


def load_drive_module():
    spec = importlib.util.spec_from_file_location("ares_drive_cpv_daily_create", DRIVE_MODULE_PATH)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load Drive helper")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.load_env()
    mod.SCOPES = "https://www.googleapis.com/auth/drive"
    return mod


def safe_meta(common, payload: Any) -> dict[str, Any]:
    return common.safe_meta_error(payload) if isinstance(payload, dict) else {"payload_type": type(payload).__name__}


def quota_retry_after_seconds(common, minimum: int = 60) -> int:
    try:
        state = common.read_throttle_state()
    except Exception:
        state = {}
    remaining = int(math.ceil(max(0.0, float(state.get("blocked_until_epoch") or 0) - time.time())))
    return max(int(minimum), remaining or 300)


def graph_get(common, token: str, path: str, params: dict[str, Any], stage: str) -> tuple[dict[str, Any], dict[str, Any]]:
    status, payload, headers = common.graph_get(path, token, params)
    if status != 200 or not isinstance(payload, dict) or payload.get("error"):
        error = safe_meta(common, payload)
        if error.get("code") in {17, 613} or error.get("error_subcode") == 2446079:
            raise ReadbackDeferred(stage, {"http": status, "error": error}, quota_retry_after_seconds(common))
        raise Stop(stage, {"http": status, "error": error})
    return payload, headers


def graph_post_once(common, token: str, path: str, params: dict[str, Any], stage: str, expect_id: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        status, payload, headers = common.graph_post_once(path, token, params)
    except Exception as exc:
        raise Stop(stage, {"transport_exception": f"{type(exc).__name__}: {str(exc)[:500]}"}) from exc
    if status not in {200, 201} or not isinstance(payload, dict) or payload.get("error"):
        raise Stop(stage, {"http": status, "error": safe_meta(common, payload)})
    if expect_id and not payload.get("id"):
        raise Stop(stage, {"http": status, "message": "response missing id", "payload_keys": sorted(payload)})
    copied_id_present = any(key.startswith("copied_") and key.endswith("_id") and payload.get(key) for key in payload)
    if not expect_id and not (payload.get("success") is True or payload.get("id") or copied_id_present):
        raise Stop(stage, {"http": status, "message": "response missing success/id/copied_id", "payload_keys": sorted(payload)})
    return payload, headers


def batch_get(common, token: str, requests_: list[dict[str, Any]], stage: str) -> dict[str, Any]:
    status, rows, _ = common.graph_batch_get(token, requests_)
    if status != 200 or not isinstance(rows, list):
        error = safe_meta(common, rows)
        if error.get("code") in {17, 613}:
            raise ReadbackDeferred(stage, {"http": status, "error": error}, quota_retry_after_seconds(common))
        raise Stop(stage, {"http": status, "error": error})
    bad = [row for row in rows if row.get("code") != 200]
    if bad:
        errors = [{"name": item.get("name"), "http": item.get("code"), "error": safe_meta(common, item.get("body") or {})} for item in bad]
        if any((item.get("error") or {}).get("code") in {17, 613} or (item.get("error") or {}).get("error_subcode") == 2446079 for item in errors):
            raise ReadbackDeferred(stage, {"batch_errors": errors}, quota_retry_after_seconds(common))
        raise Stop(stage, {"batch_errors": errors})
    return {str(row["name"]): row["body"] for row in rows}


def writable_targeting(value: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(value)
    out.pop("age_range", None)
    out.pop("brand_safety_content_filter_levels", None)
    return out


def writable_promoted(value: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(value)
    out.pop("smart_pse_enabled", None)
    return out


def strip_asset_readonly(value: Any) -> Any:
    if isinstance(value, list):
        return [strip_asset_readonly(item) for item in value]
    if not isinstance(value, dict):
        return value
    out: dict[str, Any] = {}
    for key, item in value.items():
        if key in {"thumbnail_url", "thumbnail_hash"}:
            continue
        if key == "id" and set(value).issubset({"id", "name"}):
            continue
        out[key] = strip_asset_readonly(item)
    return out


def replace_utm(value: Any, number: int) -> Any:
    if isinstance(value, str):
        return re.sub(r"b01fb13c08", f"b01fb13c{number:02d}", value)
    if isinstance(value, list):
        return [replace_utm(item, number) for item in value]
    if isinstance(value, dict):
        return {key: replace_utm(item, number) for key, item in value.items()}
    return value


def campaign_name(number: int, operational_date: datetime) -> str:
    return f"{number:02d} - {operational_date:%d-%m} - Garagem Brasil - (b01fb13c{number:02d}) event_Subscribe - MAXVOL"


def adset_name(number: int) -> str:
    return f"01 - AdGroup - (b01fb13c{number:02d}g01) event_Subscribe - MAXVOL"


def scheduled_start(operational_date: datetime) -> datetime:
    return (operational_date + timedelta(days=1)).replace(hour=0, minute=30, second=0, microsecond=0)


def parse_number(name: str) -> int | None:
    match = re.match(r"^\s*(\d{1,3})\s*-", str(name or ""))
    return int(match.group(1)) if match else None


def list_campaigns(common, token: str) -> list[dict[str, Any]]:
    payload, _ = graph_get(common, token, ACCOUNT_ACT + "/campaigns", {
        "fields": "id,name,status,effective_status,configured_status,daily_budget,bid_strategy,objective,start_time,updated_time",
        "effective_status": ["ACTIVE", "PAUSED", "ARCHIVED"],
        "limit": 500,
    }, "campaign_inventory")
    return payload.get("data") or []


def source_preflight(common, token: str) -> dict[str, Any]:
    req = [
        {"name": "account", "path": ACCOUNT_ACT, "params": {"fields": "id,name,account_status,currency,timezone_name,disable_reason"}},
        {"name": "campaign", "path": SOURCE_CAMPAIGN_ID, "params": {"fields": "id,name,status,effective_status,configured_status,daily_budget,bid_strategy,objective,buying_type,special_ad_categories,special_ad_category_country,start_time,updated_time"}},
        {"name": "adset", "path": SOURCE_ADSET_ID, "params": {"fields": "id,name,status,effective_status,configured_status,bid_amount,billing_event,optimization_goal,targeting,promoted_object,attribution_spec,regional_regulated_categories,regional_regulation_identities,dsa_beneficiary,dsa_payor,is_dynamic_creative"}},
        {"name": "ads", "path": SOURCE_CAMPAIGN_ID + "/ads", "params": {"fields": "id,name,status,effective_status,configured_status,creative{id,name,object_story_spec,asset_feed_spec,degrees_of_freedom_spec}", "limit": 20}},
        {"name": "pages", "path": "me/accounts", "params": {"fields": "id,name,tasks,access_token", "limit": 200}},
        {"name": "debug", "path": "debug_token", "params": {"input_token": token}},
    ]
    data = batch_get(common, token, req, "source_preflight")
    account = data["account"]
    if account.get("account_status") != 1 or account.get("currency") != "USD" or account.get("timezone_name") != "America/Sao_Paulo" or account.get("disable_reason") not in {0, None}:
        raise Stop("source_preflight", {"message": "account invariant failed", "account": account})
    debug = data["debug"].get("data") or {}
    required_scopes = {"ads_management", "ads_read", "pages_manage_ads", "pages_show_list"}
    missing = sorted(required_scopes - set(debug.get("scopes") or []))
    if not debug.get("is_valid") or missing:
        raise Stop("source_preflight", {"message": "token invariant failed", "is_valid": debug.get("is_valid"), "missing": missing})
    page = next((row for row in data["pages"].get("data") or [] if str(row.get("id")) == PAGE_ID), None)
    if not page or "ADVERTISE" not in set(page.get("tasks") or []) or not page.get("access_token"):
        raise Stop("source_preflight", {"message": "Page ADVERTISE/access token missing"})
    page_token = str(page.pop("access_token"))
    campaign = data["campaign"]
    adset = data["adset"]
    ads = data["ads"].get("data") or []
    if campaign.get("bid_strategy") != "LOWEST_COST_WITHOUT_CAP":
        raise Stop("source_preflight", {"message": "source C08 is no longer MAXVOL", "campaign": campaign})
    if adset.get("bid_amount") not in {None, "", 0, "0"}:
        raise Stop("source_preflight", {"message": "source C08 unexpectedly has bid_amount", "adset": adset})
    if len(ads) != 3 or any(len(((row.get("creative") or {}).get("asset_feed_spec") or {}).get("videos") or []) != 2 for row in ads):
        raise Stop("source_preflight", {"message": "source requires exactly three dynamic creatives with two videos", "ad_count": len(ads)})
    ads.sort(key=lambda row: parse_number(str(row.get("name") or "")) or 999)
    return {
        "account": account,
        "campaign": campaign,
        "adset": adset,
        "ads": ads,
        "page": {"id": page.get("id"), "name": page.get("name"), "tasks": page.get("tasks")},
        "page_token": page_token,
        "token_debug": {"is_valid": True, "type": debug.get("type"), "app_id": debug.get("app_id"), "scopes": debug.get("scopes")},
    }


def account_ads_snapshot(common, token: str) -> list[dict[str, Any]]:
    base_params = {
        "fields": "id,name,status,effective_status,configured_status,created_time,updated_time,campaign{id,name,status,effective_status,created_time,updated_time},adset{id,name,status,effective_status},creative{id,name,object_story_id,effective_object_story_id,object_story_spec,asset_feed_spec}",
        "limit": 500,
    }
    rows_by_id: dict[str, dict[str, Any]] = {}
    for status_filter in (None, ["ARCHIVED"]):
        params = dict(base_params)
        if status_filter:
            params["effective_status"] = status_filter
        after: str | None = None
        for _ in range(20):
            if after:
                params["after"] = after
            elif "after" in params:
                params.pop("after", None)
            payload, _ = graph_get(common, token, ACCOUNT_ACT + "/ads", params, "account_ads_snapshot")
            for row in payload.get("data") or []:
                rows_by_id[str(row.get("id"))] = row
            paging = payload.get("paging") or {}
            after = ((paging.get("cursors") or {}).get("after")) if paging.get("next") else None
            if not after:
                break
    return sorted(rows_by_id.values(), key=lambda row: str(row.get("id") or ""))


def known_cleaned_daily_ids() -> dict[str, set[str]]:
    cleaned = {"ads": set(), "creatives": set(), "videos": set(), "campaigns": set()}
    for path in AUDIT_DIR.glob("daily-create-*.json"):
        try:
            audit = json.loads(path.read_text())
        except Exception:
            continue
        cleanup = audit.get("cleanup") or {}
        if cleanup.get("complete") is not True:
            continue
        cleaned["ads"].update(str(row.get("id")) for row in cleanup.get("ads") or [] if row.get("id"))
        cleaned["creatives"].update(str(row.get("id")) for row in cleanup.get("creatives") or [] if row.get("id"))
        cleaned["videos"].update(str(row.get("id")) for row in cleanup.get("videos") or [] if row.get("id"))
        cleaned["campaigns"].update(str(row.get("id")) for row in cleanup.get("campaigns") or [] if row.get("id"))
    return cleaned


def extract_video_ids(ads: list[dict[str, Any]]) -> list[str]:
    out: set[str] = set()
    for ad in ads:
        creative = ad.get("creative") or {}
        for video in ((creative.get("asset_feed_spec") or {}).get("videos") or []):
            if video.get("video_id"):
                out.add(str(video["video_id"]))
        video_data = ((creative.get("object_story_spec") or {}).get("video_data") or {})
        if video_data.get("video_id"):
            out.add(str(video_data["video_id"]))
    return sorted(out)


def video_metadata(common, page_token: str, video_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for start in range(0, len(video_ids), 50):
        req = [{"name": video_id, "path": video_id, "params": {"fields": "id,title,description,created_time,updated_time,length"}} for video_id in video_ids[start:start + 50]]
        status, batch, _ = common.graph_batch_get(page_token, req)
        if status != 200 or not isinstance(batch, list):
            raise Stop("video_metadata", {"http": status, "error": safe_meta(common, batch)})
        for item in batch:
            body = item.get("body") or {}
            if item.get("code") != 200:
                error = safe_meta(common, body)
                if error.get("code") == 100 and error.get("error_subcode") == 33:
                    rows.append({"video_id": str(item.get("name")), "title": None, "created_time": None, "updated_time": None, "length": None, "unavailable_deleted": True})
                    continue
                if error.get("code") in {17, 613} or error.get("error_subcode") == 2446079:
                    raise ReadbackDeferred("video_metadata", {"video_id": item.get("name"), "http": item.get("code"), "error": error})
                raise Stop("video_metadata", {"video_id": item.get("name"), "http": item.get("code"), "error": error})
            rows.append({
                "video_id": str(item.get("name")),
                "title": body.get("title"),
                "created_time": body.get("created_time"),
                "updated_time": body.get("updated_time"),
                "length": body.get("length"),
                "unavailable_deleted": False,
            })
    return rows


def normalize_title(value: str | None) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def source_sequence(original_filename: str | None) -> str | None:
    matches = re.findall(r"(?:^|[_\s-])(\d{3})(?:\s*-|[_\s])", str(original_filename or ""))
    return matches[-1] if matches else None


def selected_meta_conflicts(selected: list[dict[str, Any]], ads: list[dict[str, Any]], videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    haystacks: list[dict[str, str]] = []
    for ad in ads:
        creative = ad.get("creative") or {}
        haystacks.append({
            "kind": "ad",
            "id": str(ad.get("id") or ""),
            "text": normalize_title(" ".join([str(ad.get("name") or ""), str(creative.get("name") or ""), str((ad.get("campaign") or {}).get("name") or "")])),
        })
    for video in videos:
        haystacks.append({"kind": "video", "id": str(video.get("video_id") or ""), "text": normalize_title(video.get("title"))})
    conflicts: list[dict[str, Any]] = []
    for row in selected:
        canonical = normalize_title(Path(str(row.get("canonical_filename") or "")).stem)
        original = normalize_title(Path(str(row.get("original_filename") or "")).stem)
        seq = source_sequence(row.get("original_filename"))
        for hay in haystacks:
            text = hay["text"]
            exact_name = bool(canonical and canonical in text) or bool(original and len(original) >= 12 and original in text)
            sequence_match = bool(seq and re.search(rf"(?:^|\s){re.escape(seq)}(?:\s|$)", text))
            if exact_name or sequence_match:
                conflicts.append({"asset_id": row.get("asset_id"), "canonical_filename": row.get("canonical_filename"), "match_kind": hay["kind"], "match_id": hay["id"], "exact_name": exact_name, "source_sequence": seq if sequence_match else None})
    return conflicts


def load_reconciliation_manifest(selected: list[dict[str, Any]]) -> dict[str, Any]:
    if not RECONCILIATION_PATH.exists():
        raise Stop("reconciliation_manifest", {"message": "separate reconciliation manifest missing", "path": str(RECONCILIATION_PATH)})
    try:
        manifest = json.loads(RECONCILIATION_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise Stop("reconciliation_manifest", {"message": "manifest unreadable", "error": type(exc).__name__}) from exc
    if manifest.get("status") != "valid" or str(manifest.get("account_id") or "") != ACCOUNT_ID:
        raise Stop("reconciliation_manifest", {"message": "manifest invalid or wrong account", "status": manifest.get("status"), "account_id": manifest.get("account_id")})
    valid_until = parse_datetime_meta(str(manifest.get("valid_until_utc") or ""))
    if valid_until is None or valid_until <= datetime.now(timezone.utc):
        raise Stop("reconciliation_manifest", {"message": "manifest expired", "valid_until_utc": manifest.get("valid_until_utc")})
    assets = {str(row.get("asset_id") or ""): row for row in manifest.get("assets") or []}
    checks: list[dict[str, Any]] = []
    for row in selected:
        asset_id = str(row.get("asset_id") or "")
        approved = assets.get(asset_id)
        check = {
            "asset_id": asset_id,
            "present": approved is not None,
            "approved": bool((approved or {}).get("approved")),
            "drive_id_match": str((approved or {}).get("asset_drive_id") or "") == str(row.get("asset_drive_id") or ""),
            "checksum_match": str((approved or {}).get("clean_checksum") or "") == str(row.get("clean_checksum") or ""),
            "conflict_count": len((approved or {}).get("meta_conflicts") or []),
        }
        checks.append(check)
    if not checks or not all(item["present"] and item["approved"] and item["drive_id_match"] and item["checksum_match"] and item["conflict_count"] == 0 for item in checks):
        raise Stop("reconciliation_manifest", {"message": "selected assets not approved by separate reconciler", "checks": checks})
    return {
        "path": str(RECONCILIATION_PATH),
        "generated_at_utc": manifest.get("generated_at_utc"),
        "valid_until_utc": manifest.get("valid_until_utc"),
        "source": manifest.get("source"),
        "checks": checks,
        "meta_counts": manifest.get("meta_counts") or {},
    }


def drive_request(token: str, method: str, url: str, *, body: bytes | None = None, content_type: str | None = None) -> dict[str, Any]:
    headers = {"Authorization": "Bearer " + token, "User-Agent": "MGS-Ares-CPV-Daily-Create/1.0"}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
            return json.loads(payload.decode("utf-8")) if payload else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            error = json.loads(raw)
        except Exception:
            error = {"raw_length": len(raw)}
        raise Stop("drive_request", {"http": exc.code, "error": error}) from exc


def drive_list_children(token: str, parent_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        params = {
            "q": f"'{parent_id}' in parents and trashed=false",
            "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,createdTime,size,md5Checksum,driveId,parents,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive,canTrash,canDelete),videoMediaMetadata(width,height,durationMillis),imageMediaMetadata(width,height))",
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "orderBy": "name_natural",
        }
        if page_token:
            params["pageToken"] = page_token
        payload = drive_request(token, "GET", "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params))
        rows.extend(payload.get("files") or [])
        page_token = payload.get("nextPageToken")
        if not page_token:
            return rows


def find_folder(rows: list[dict[str, Any]], name: str, stage: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("name") == name and row.get("mimeType") == FOLDER_MIME]
    if len(matches) != 1:
        raise Stop(stage, {"message": "expected exactly one folder", "name": name, "count": len(matches)})
    return matches[0]


def drive_inventory(token: str) -> dict[str, Any]:
    root_meta = drive_request(token, "GET", f"https://www.googleapis.com/drive/v3/files/{DRIVE_ROOT_ID}?" + urllib.parse.urlencode({"fields": "id,name,driveId,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive,canTrash,canDelete)", "supportsAllDrives": "true"}))
    required_caps = {"canDownload", "canEdit", "canMoveItemWithinDrive"}
    if root_meta.get("driveId") != DRIVE_ID or root_meta.get("trashed") or not all((root_meta.get("capabilities") or {}).get(key) for key in required_caps):
        raise Stop("drive_root_preflight", {"root": root_meta, "required_caps": sorted(required_caps)})
    creatives = find_folder(drive_list_children(token, DRIVE_ROOT_ID), "CRIATIVOS", "drive_creatives")
    operation = find_folder(drive_list_children(token, creatives["id"]), "CAR_BR_BR", "drive_operation")
    types: dict[str, dict[str, Any]] = {}
    all_ready: list[dict[str, Any]] = []
    for kind in ("IMG", "VID"):
        kind_folder = find_folder(drive_list_children(token, operation["id"]), kind, f"drive_{kind}")
        children = drive_list_children(token, kind_folder["id"])
        ready = find_folder(children, "01_READY", f"drive_{kind}_ready")
        testing = find_folder(children, "02_TESTING", f"drive_{kind}_testing")
        files = [row for row in drive_list_children(token, ready["id"]) if row.get("mimeType") != FOLDER_MIME]
        for row in files:
            row["kind"] = kind
            row["ready_parent_id"] = ready["id"]
            row["testing_parent_id"] = testing["id"]
        all_ready.extend(files)
        types[kind] = {"ready": ready, "testing": testing, "files": files}
    return {"root": root_meta, "types": types, "files": all_ready, "counts": {"IMG": len(types["IMG"]["files"]), "VID": len(types["VID"]["files"]), "TOTAL": len(all_ready)}}


def download_drive_file(token: str, file_row: dict[str, Any], destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://www.googleapis.com/drive/v3/files/{file_row['id']}?" + urllib.parse.urlencode({"alt": "media", "supportsAllDrives": "true"})
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "User-Agent": "MGS-Ares-CPV-Daily-Create/1.0"})
    md5 = hashlib.md5()
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as fh:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                md5.update(chunk)
                size += len(chunk)
    except Exception:
        try:
            destination.unlink()
        except FileNotFoundError:
            pass
        raise
    actual = md5.hexdigest()
    expected = str(file_row.get("md5Checksum") or "")
    if not expected or actual != expected or size != int(file_row.get("size") or 0):
        raise Stop("drive_download_readback", {"id": file_row.get("id"), "name": file_row.get("name"), "expected_md5": expected, "actual_md5": actual, "expected_size": file_row.get("size"), "actual_size": size})
    return {"md5": actual, "bytes": size, "path": str(destination)}


def drive_move_to_testing(token: str, file_row: dict[str, Any]) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "addParents": file_row["testing_parent_id"],
        "removeParents": file_row["ready_parent_id"],
        "fields": "id,name,driveId,parents,trashed,size,md5Checksum",
        "supportsAllDrives": "true",
    })
    payload = drive_request(token, "PATCH", f"https://www.googleapis.com/drive/v3/files/{file_row['id']}?{params}", body=b"{}", content_type="application/json")
    if payload.get("driveId") != DRIVE_ID or payload.get("trashed") or set(payload.get("parents") or []) != {file_row["testing_parent_id"]} or str(payload.get("md5Checksum") or "") != str(file_row.get("md5Checksum") or ""):
        raise Stop("drive_move_readback", {"file_id": file_row.get("id"), "readback": payload})
    return payload


def verify_clean(path: Path) -> dict[str, Any]:
    result = subprocess.run([str(SANITIZER), "verify", str(path)], capture_output=True, text=True, timeout=120, check=False)
    if result.returncode != 0 or "clean: true" not in result.stdout:
        raise Stop("metadata_verify", {"path": str(path), "rc": result.returncode, "stdout": result.stdout[-800:], "stderr": result.stderr[-800:]})
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"clean": True, "sha256": sha, "bytes": path.stat().st_size}


def make_square_clean(source: Path, destination: Path) -> dict[str, Any]:
    raw = destination.with_suffix(".raw.mp4")
    ffmpeg = subprocess.run([
        "ffmpeg", "-y", "-i", str(source), "-vf", "crop=iw:iw:0:(ih-iw)/2,scale=1080:1080", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(raw),
    ], capture_output=True, text=True, timeout=300, check=False)
    if ffmpeg.returncode != 0:
        raise Stop("square_crop", {"source": str(source), "stderr": ffmpeg.stderr[-1200:]})
    clean = subprocess.run([str(SANITIZER), "clean", str(raw), "--out", str(destination), "--agent", "ares", "--json"], capture_output=True, text=True, timeout=300, check=False)
    try:
        raw.unlink()
    except FileNotFoundError:
        pass
    if clean.returncode != 0:
        raise Stop("square_sanitize", {"source": str(source), "stderr": clean.stderr[-1200:], "stdout": clean.stdout[-1200:]})
    result = verify_clean(destination)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", str(destination)], capture_output=True, text=True, timeout=60, check=False)
    data = json.loads(probe.stdout or "{}") if probe.returncode == 0 else {}
    video = next((row for row in data.get("streams") or [] if row.get("codec_type") == "video"), {})
    if video.get("width") != 1080 or video.get("height") != 1080:
        raise Stop("square_probe", {"path": str(destination), "video": video})
    result["width"] = 1080
    result["height"] = 1080
    return result


def multipart_video_upload(common, page_token: str, path: Path, title: str, stage: str) -> dict[str, Any]:
    common._throttle_before_request()
    url = f"https://graph-video.facebook.com/{GRAPH_VERSION}/{PAGE_ID}/videos"
    try:
        with path.open("rb") as fh:
            response = requests.post(url, data={"access_token": page_token, "title": title}, files={"source": (path.name, fh, "video/mp4")}, timeout=300)
    except Exception as exc:
        raise Stop(stage, {"transport_exception": f"{type(exc).__name__}: {str(exc)[:500]}"}) from exc
    try:
        payload = response.json()
    except Exception:
        payload = {"raw_length": len(response.content)}
    common.record_response_usage(dict(response.headers), response.status_code, payload)
    if response.status_code not in {200, 201} or not isinstance(payload, dict) or payload.get("error") or not payload.get("id"):
        raise Stop(stage, {"http": response.status_code, "error": safe_meta(common, payload), "payload_keys": sorted(payload) if isinstance(payload, dict) else []})
    return {"id": str(payload["id"]), "title": title, "bytes": path.stat().st_size}


def wait_videos_ready_batch(common, page_token: str, video_ids: list[str], stage: str) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    unique_ids = list(dict.fromkeys(str(item) for item in video_ids))
    for attempt in range(1, 13):
        requests_ = [{"name": video_id, "path": video_id, "params": {"fields": "id,title,length,status"}} for video_id in unique_ids]
        status, rows, _ = common.graph_batch_get(page_token, requests_)
        if status != 200 or not isinstance(rows, list):
            error = safe_meta(common, rows)
            if error.get("code") in {17, 613} or error.get("error_subcode") == 2446079:
                raise ReadbackDeferred(stage, {"http": status, "error": error})
            raise Stop(stage, {"http": status, "error": error})
        snapshot: dict[str, Any] = {}
        all_ready = True
        for row in rows:
            body = row.get("body") or {}
            if row.get("code") != 200:
                error = safe_meta(common, body)
                if error.get("code") in {17, 613} or error.get("error_subcode") == 2446079:
                    raise ReadbackDeferred(stage, {"video_id": row.get("name"), "http": row.get("code"), "error": error})
                raise Stop(stage, {"video_id": row.get("name"), "http": row.get("code"), "error": error})
            video_status = body.get("status") or {}
            text = json.dumps(video_status, ensure_ascii=False).upper()
            ready = any(value in text for value in ["READY", "COMPLETE", "PUBLISHED"]) and not any(value in text for value in ["ERROR", "FAILED"])
            if any(value in text for value in ["ERROR", "FAILED"]):
                raise Stop(stage, {"video_id": row.get("name"), "status": video_status})
            snapshot[str(row.get("name"))] = {"readback": body, "ready": ready}
            all_ready = all_ready and ready
        attempts.append({"attempt": attempt, "ready_count": sum(item["ready"] for item in snapshot.values()), "total": len(unique_ids)})
        if all_ready and len(snapshot) == len(unique_ids):
            return {"videos": snapshot, "attempts": attempts}
        time.sleep(5)
    raise Stop(stage, {"message": "video processing did not become ready", "video_ids": unique_ids, "attempts": attempts})


def campaign_payload(source: dict[str, Any], number: int, operational_date: datetime) -> dict[str, Any]:
    campaign = source["campaign"]
    return {
        "name": campaign_name(number, operational_date),
        "objective": campaign.get("objective"),
        "buying_type": campaign.get("buying_type") or "AUCTION",
        "status": "PAUSED",
        "daily_budget": str(BUDGET_MINOR),
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "special_ad_categories": campaign.get("special_ad_categories"),
        "special_ad_category_country": campaign.get("special_ad_category_country"),
        "start_time": scheduled_start(operational_date).isoformat(),
    }


def adset_payload(source: dict[str, Any], campaign_id: str, number: int) -> dict[str, Any]:
    adset = source["adset"]
    payload = {
        "name": adset_name(number),
        "campaign_id": campaign_id,
        "status": "ACTIVE",
        "billing_event": adset.get("billing_event"),
        "optimization_goal": adset.get("optimization_goal"),
        "targeting": writable_targeting(adset.get("targeting") or {}),
        "promoted_object": writable_promoted(adset.get("promoted_object") or {}),
        "attribution_spec": adset.get("attribution_spec"),
        "regional_regulated_categories": adset.get("regional_regulated_categories") or ["BRAZIL_REGULATION"],
        "regional_regulation_identities": adset.get("regional_regulation_identities"),
        "dsa_beneficiary": adset.get("dsa_beneficiary") or "Digital Trust",
        "dsa_payor": adset.get("dsa_payor") or "Digital Trust",
    }
    return {key: value for key, value in payload.items() if value is not None}


def copy_response_id(payload: dict[str, Any], singular: str, plural: str) -> str | None:
    value = payload.get(singular) or payload.get("id")
    rows = payload.get(plural) or []
    if not value and rows and isinstance(rows[0], dict):
        value = rows[0].get("id")
    return str(value) if value else None


def build_quota_plan(common, desired_count: int, *, clone_source: bool, replacement: bool) -> dict[str, Any]:
    state = common.read_throttle_state()
    ad_usage = state.get("ad_account_usage") or {}
    business_usage = state.get("business_usage") or {}
    local_score = state.get("local_score") or {}
    writes_per_campaign = CLONE_WRITE_CALLS_PER_CAMPAIGN if clone_source else FROM_ZERO_WRITE_CALLS_PER_CAMPAIGN
    if replacement:
        writes_per_campaign += 1
    options: dict[str, Any] = {}
    for count in range(max(1, int(desired_count)), 0, -1):
        options[str(count)] = common.ads_management_score_budget(
            ad_usage,
            business_usage,
            read_calls=CLONE_READ_CALLS_PER_CAMPAIGN * count,
            write_calls=writes_per_campaign * count,
            reserve_points=SCORE_READBACK_RESERVE_POINTS,
            local_score=local_score,
        )
    selected_count = next((count for count in range(max(1, int(desired_count)), 0, -1) if options[str(count)]["allowed"]), 0)
    return {
        "desired_count": max(1, int(desired_count)),
        "selected_count": selected_count,
        "fallback_applied": 0 < selected_count < max(1, int(desired_count)),
        "options": options,
        "state_updated_at_epoch": state.get("ad_account_usage_updated_at_epoch") or state.get("usage_updated_at_epoch"),
        "blocked_until_epoch": state.get("blocked_until_epoch") or 0,
        "block_reason": state.get("block_reason"),
    }


def build_async_deep_copy_adbatch(number: int, operational_date: datetime) -> list[dict[str, str]]:
    copy_params = {
        "deep_copy": "true",
        "status_option": "PAUSED",
        "start_time": scheduled_start(operational_date).isoformat(),
        "rename_options": json.dumps({"rename_strategy": "DEEP_RENAME", "rename_suffix": f" - C{number:02d} ASYNC CLONE"}, separators=(",", ":")),
    }
    return [{
        "name": f"copy-campaign-c{number:02d}",
        "relative_url": f"{GRAPH_VERSION}/{SOURCE_CAMPAIGN_ID}/copies",
        "body": urllib.parse.urlencode(copy_params),
    }]


def submit_async_deep_copy(common, token: str, number: int, operational_date: datetime) -> str:
    payload, _ = graph_post_once(common, token, ACCOUNT_ACT + "/async_batch_requests", {
        "name": f"CPV C{number:02d} async deep copy",
        "adbatch": build_async_deep_copy_adbatch(number, operational_date),
    }, f"c{number}_async_deep_copy_submit", expect_id=True)
    return str(payload["id"])


def poll_async_deep_copy(common, token: str, request_set_id: str, *, attempts: int = 20, interval_seconds: int = 15) -> dict[str, Any]:
    history: list[dict[str, Any]] = []
    for attempt in range(1, max(1, int(attempts)) + 1):
        status, _ = graph_get(common, token, request_set_id, {
            "fields": "id,name,total_count,success_count,error_count,is_completed",
        }, "async_deep_copy_status")
        history.append({key: status.get(key) for key in ["id", "total_count", "success_count", "error_count", "is_completed"]})
        if status.get("is_completed") is True:
            requests_payload, _ = graph_get(common, token, request_set_id + "/requests", {
                "fields": "id,status,result,input",
                "limit": 100,
            }, "async_deep_copy_results")
            rows = requests_payload.get("data") or []
            if int(status.get("error_count") or 0) > 0 or any(str(row.get("status") or "").lower() == "error" for row in rows):
                raise Stop("async_deep_copy_results", {"status": status, "requests": rows})
            return {"status": status, "requests": rows, "history": history}
        if attempt < attempts:
            time.sleep(max(1, int(interval_seconds)))
    raise ReadbackDeferred("async_deep_copy_status", {"request_set_id": request_set_id, "history": history}, max(60, int(interval_seconds)))


def clone_campaign_adset_shell(common, token: str, source: dict[str, Any], number: int, operational_date: datetime, audit: dict[str, Any], audit_path: Path) -> tuple[str, str, dict[str, Any]]:
    campaign_copy, _ = graph_post_once(common, token, SOURCE_CAMPAIGN_ID + "/copies", {
        "deep_copy": "false",
        "status_option": "PAUSED",
        "rename_options": {"rename_strategy": "ONLY_TOP_LEVEL_RENAME", "rename_suffix": f" - C{number:02d} DAILY CLONE"},
    }, f"c{number}_campaign_clone")
    campaign_id = copy_response_id(campaign_copy, "copied_campaign_id", "copied_campaigns")
    if not campaign_id:
        raise Stop(f"c{number}_campaign_clone", {"message": "copy response missing campaign id", "payload_keys": sorted(campaign_copy)})
    audit["created_campaign_ids"].append(campaign_id)
    audit.setdefault("clone_shells", {})[str(number)] = {"stage": "campaign_cloned", "campaign_id": campaign_id}
    atomic_json(audit_path, audit)
    graph_post_once(common, token, campaign_id, {
        "name": campaign_name(number, operational_date),
        "daily_budget": str(BUDGET_MINOR),
        "status": "PAUSED",
        "start_time": scheduled_start(operational_date).isoformat(),
    }, f"c{number}_campaign_clone_update")
    adset_copy, _ = graph_post_once(common, token, SOURCE_ADSET_ID + "/copies", {
        "campaign_id": campaign_id,
        "deep_copy": "false",
        "status_option": "ACTIVE",
        "rename_options": {"rename_strategy": "ONLY_TOP_LEVEL_RENAME", "rename_suffix": f" - C{number:02d} DAILY CLONE"},
    }, f"c{number}_adset_clone")
    adset_id = copy_response_id(adset_copy, "copied_adset_id", "copied_adsets")
    if not adset_id:
        raise Stop(f"c{number}_adset_clone", {"message": "copy response missing adset id", "payload_keys": sorted(adset_copy)})
    audit.setdefault("clone_shells", {})[str(number)].update({"stage": "adset_cloned", "adset_id": adset_id})
    atomic_json(audit_path, audit)
    graph_post_once(common, token, adset_id, {
        "name": adset_name(number),
        "status": "ACTIVE",
        "targeting": writable_targeting(source["adset"].get("targeting") or {}),
    }, f"c{number}_adset_clone_update")
    readback = batch_get(common, token, [
        {"name": "campaign", "path": campaign_id, "params": {"fields": "id,name,status,effective_status,configured_status,daily_budget,bid_strategy,start_time"}},
        {"name": "adset", "path": adset_id, "params": {"fields": "id,name,status,effective_status,configured_status,bid_amount,billing_event,optimization_goal,promoted_object,attribution_spec,regional_regulated_categories,regional_regulation_identities,dsa_beneficiary,dsa_payor"}},
    ], f"c{number}_clone_shell_readback")
    campaign = readback["campaign"]
    adset = readback["adset"]
    checks = {
        "campaign_paused": (campaign.get("configured_status") or campaign.get("status")) == "PAUSED" and campaign.get("effective_status") in {"PAUSED", "IN_PROCESS", "PENDING_REVIEW", "WITH_ISSUES"},
        "campaign_maxvol": campaign.get("bid_strategy") == "LOWEST_COST_WITHOUT_CAP",
        "campaign_budget": str(campaign.get("daily_budget")) == str(BUDGET_MINOR),
        "adset_active_under_paused": (adset.get("configured_status") or adset.get("status")) == "ACTIVE" and adset.get("effective_status") in {"CAMPAIGN_PAUSED", "IN_PROCESS", "PENDING_REVIEW", "WITH_ISSUES"},
        "bid_amount_absent": adset.get("bid_amount") in {None, "", 0, "0"},
        "subscribe_pixel": (adset.get("promoted_object") or {}).get("custom_event_type") == "SUBSCRIBE" and str((adset.get("promoted_object") or {}).get("pixel_id")) == "1033279451747443",
        "attribution_exact": (adset.get("attribution_spec") or []) == (source["adset"].get("attribution_spec") or []),
        "regional_identity_exact": (adset.get("regional_regulation_identities") or {}) == (source["adset"].get("regional_regulation_identities") or {}),
    }
    if not all(checks.values()):
        raise Stop(f"c{number}_clone_shell_readback", {"checks": checks, "readback": readback})
    result = {"checks": checks, "readback": readback, "route": "native_shallow_clone_C08_campaign_adset"}
    audit.setdefault("clone_shells", {})[str(number)].update({"stage": "validated", "validation": result})
    atomic_json(audit_path, audit)
    return campaign_id, adset_id, result


def creative_payload(source_ad: dict[str, Any], number: int, index: int, canonical_filename: str, vertical_video_id: str, square_video_id: str) -> dict[str, Any]:
    creative = source_ad["creative"]
    asset = replace_utm(strip_asset_readonly(copy.deepcopy(creative.get("asset_feed_spec") or {})), number)
    videos = asset.get("videos") or []
    if len(videos) != 2:
        raise Stop("creative_payload", {"message": "source creative no longer has exactly two video slots", "source_ad_id": source_ad.get("id")})
    videos[0]["video_id"] = vertical_video_id
    videos[1]["video_id"] = square_video_id
    asset["videos"] = videos
    story = copy.deepcopy(creative.get("object_story_spec") or {})
    dof = copy.deepcopy(creative.get("degrees_of_freedom_spec") or {})
    features = (dof.get("creative_features_spec") or {}) if isinstance(dof, dict) else {}
    features.pop("standard_enhancements", None)
    if isinstance(dof, dict) and "creative_features_spec" in dof:
        if features:
            dof["creative_features_spec"] = features
        else:
            dof.pop("creative_features_spec", None)
    payload: dict[str, Any] = {
        "name": f"CPV C{number:02d} AD{index:02d} {Path(canonical_filename).stem}",
        "object_story_spec": story,
        "asset_feed_spec": asset,
    }
    if dof:
        payload["degrees_of_freedom_spec"] = dof
    return payload


def read_hierarchy(common, token: str, campaign_id: str, stage: str) -> dict[str, Any]:
    return batch_get(common, token, [
        {"name": "campaign", "path": campaign_id, "params": {"fields": "id,name,status,effective_status,configured_status,daily_budget,bid_strategy,objective,buying_type,special_ad_categories,special_ad_category_country,start_time,updated_time"}},
        {"name": "adsets", "path": campaign_id + "/adsets", "params": {"fields": "id,name,status,effective_status,configured_status,bid_amount,billing_event,optimization_goal,targeting,promoted_object,attribution_spec,regional_regulated_categories,regional_regulation_identities,dsa_beneficiary,dsa_payor,start_time", "limit": 20}},
        {"name": "ads", "path": campaign_id + "/ads", "params": {"fields": "id,name,status,effective_status,configured_status,creative{id,name,object_story_spec,asset_feed_spec,degrees_of_freedom_spec}", "limit": 20}},
    ], stage)


def contains_exact_json_key(value: Any, target: str) -> bool:
    """Return True only for an exact recursive JSON key match."""
    if isinstance(value, dict):
        return target in value or any(contains_exact_json_key(item, target) for item in value.values())
    if isinstance(value, list):
        return any(contains_exact_json_key(item, target) for item in value)
    return False


def validate_hierarchy(readback: dict[str, Any], source: dict[str, Any], number: int, operational_date: datetime, expected_assets: list[dict[str, Any]]) -> dict[str, Any]:
    campaign = readback["campaign"]
    adsets = readback["adsets"].get("data") or []
    ads = readback["ads"].get("data") or []
    expected_code = f"b01fb13c{number:02d}"
    start = scheduled_start(operational_date)
    campaign_start = datetime.fromisoformat(str(campaign.get("start_time") or "").replace("Z", "+00:00")) if campaign.get("start_time") else None
    checks: dict[str, bool] = {
        "campaign_exact_name": campaign.get("name") == campaign_name(number, operational_date),
        "campaign_configured_paused": (campaign.get("configured_status") or campaign.get("status")) == "PAUSED",
        "campaign_effective_safe": campaign.get("effective_status") in {"PAUSED", "IN_PROCESS", "PENDING_REVIEW", "WITH_ISSUES"},
        "activation_checkpoint_local": scheduled_start(operational_date).hour == 0 and scheduled_start(operational_date).minute == 30,
        "budget_usd30": str(campaign.get("daily_budget")) == str(BUDGET_MINOR),
        "bid_strategy_maxvol": campaign.get("bid_strategy") == "LOWEST_COST_WITHOUT_CAP",
        "financial_category_br": set(campaign.get("special_ad_categories") or []) == {"FINANCIAL_PRODUCTS_SERVICES"} and set(campaign.get("special_ad_category_country") or []) == {"BR"},
        "one_adset": len(adsets) == 1,
        "three_ads": len(ads) == 3,
    }
    if len(adsets) == 1:
        adset = adsets[0]
        checks.update({
            "adset_exact_name": adset.get("name") == adset_name(number),
            "adset_configured_active": (adset.get("configured_status") or adset.get("status")) == "ACTIVE",
            "bid_amount_absent": adset.get("bid_amount") in {None, "", 0, "0"},
            "subscribe_pixel": (adset.get("promoted_object") or {}).get("custom_event_type") == "SUBSCRIBE" and str((adset.get("promoted_object") or {}).get("pixel_id")) == "1033279451747443",
            "regional_brazil": "BRAZIL_REGULATION" in set(adset.get("regional_regulated_categories") or []),
            "regional_identity_exact": (adset.get("regional_regulation_identities") or {}) == (source["adset"].get("regional_regulation_identities") or {}),
            "attribution_exact": (adset.get("attribution_spec") or []) == (source["adset"].get("attribution_spec") or []),
        })
    asset_names = {row["canonical_filename"] for row in expected_assets}
    seen_names: set[str] = set()
    creative_checks: list[dict[str, Any]] = []
    for ad in ads:
        creative = ad.get("creative") or {}
        asset_feed = creative.get("asset_feed_spec") or {}
        urls = [row.get("website_url") for row in asset_feed.get("link_urls") or []]
        dof = creative.get("degrees_of_freedom_spec") or {}
        ad_name = str(ad.get("name") or "")
        matched = next((name for name in asset_names if Path(name).stem in ad_name), None)
        if matched:
            seen_names.add(matched)
        creative_checks.append({
            "ad_id": ad.get("id"),
            "configured_active": (ad.get("configured_status") or ad.get("status")) == "ACTIVE",
            "effective_safe": ad.get("effective_status") in {"ACTIVE", "CAMPAIGN_PAUSED", "IN_PROCESS", "WITH_ISSUES", "PENDING_REVIEW", "PREPARED"},
            "utm_exact": bool(urls) and all(expected_code in str(url) and f"{expected_code}g01" in str(url) and "b01fb13c08" not in str(url) for url in urls),
            "standard_enhancements_absent": not contains_exact_json_key(dof, "standard_enhancements"),
            "page_exact": str((creative.get("object_story_spec") or {}).get("page_id")) == PAGE_ID,
            "video_count_two": len(asset_feed.get("videos") or []) == 2,
            "asset_name_match": bool(matched),
        })
    checks.update({
        "ads_configured_active": len(creative_checks) == 3 and all(row["configured_active"] for row in creative_checks),
        "ads_effective_safe": len(creative_checks) == 3 and all(row["effective_safe"] for row in creative_checks),
        "utm_exact_all": len(creative_checks) == 3 and all(row["utm_exact"] for row in creative_checks),
        "standard_enhancements_absent_all": len(creative_checks) == 3 and all(row["standard_enhancements_absent"] for row in creative_checks),
        "page_exact_all": len(creative_checks) == 3 and all(row["page_exact"] for row in creative_checks),
        "video_count_two_all": len(creative_checks) == 3 and all(row["video_count_two"] for row in creative_checks),
        "asset_names_exact": seen_names == asset_names,
    })
    return {"valid": all(checks.values()), "checks": checks, "creative_checks": creative_checks}


def delete_edge(common, token: str, object_id: str, stage: str) -> dict[str, Any]:
    common._throttle_before_request()
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{object_id}"
    response = requests.delete(url, data={"access_token": token}, timeout=60)
    try:
        payload = response.json()
    except Exception:
        payload = {"raw_length": len(response.content)}
    common.record_response_usage(dict(response.headers), response.status_code, payload)
    if response.status_code not in {200, 201} or not isinstance(payload, dict) or payload.get("error") or payload.get("success") is not True:
        raise Stop(stage, {"object_id": object_id, "http": response.status_code, "error": safe_meta(common, payload)})
    return payload


def cleanup_failure(common, user_token: str, page_token: str | None, audit: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"ads": [], "campaigns": [], "creatives": [], "videos": [], "complete": True}
    for ad_id in reversed(audit.get("created_ad_ids") or []):
        try:
            payload, _ = graph_post_once(common, user_token, ad_id, {"status": "DELETED"}, "cleanup_ad")
            result["ads"].append({"id": ad_id, "success": payload.get("success") is True})
        except Exception as exc:
            result["ads"].append({"id": ad_id, "error": f"{type(exc).__name__}: {str(exc)[:500]}"})
            result["complete"] = False
    for campaign_id in reversed(audit.get("created_campaign_ids") or []):
        try:
            payload, _ = graph_post_once(common, user_token, campaign_id, {"status": "DELETED"}, "cleanup_campaign")
            readback, _ = graph_get(common, user_token, campaign_id, {"fields": "id,name,status,effective_status"}, "cleanup_campaign_readback")
            ok = readback.get("effective_status") == "ARCHIVED" or readback.get("status") in {"DELETED", "ARCHIVED"}
            result["campaigns"].append({"id": campaign_id, "success": payload.get("success") is True, "deleted": ok})
            result["complete"] = result["complete"] and ok
        except Exception as exc:
            result["campaigns"].append({"id": campaign_id, "error": f"{type(exc).__name__}: {str(exc)[:500]}"})
            result["complete"] = False
    for creative_id in reversed(audit.get("created_creative_ids") or []):
        try:
            delete_edge(common, user_token, creative_id, "cleanup_creative")
            result["creatives"].append({"id": creative_id, "deleted": True})
        except Exception as exc:
            result["creatives"].append({"id": creative_id, "error": f"{type(exc).__name__}: {str(exc)[:500]}"})
            result["complete"] = False
    if page_token:
        for video_id in reversed(audit.get("created_video_ids") or []):
            try:
                delete_edge(common, page_token, video_id, "cleanup_video")
                result["videos"].append({"id": video_id, "deleted": True})
            except Exception as exc:
                result["videos"].append({"id": video_id, "error": f"{type(exc).__name__}: {str(exc)[:500]}"})
                result["complete"] = False
    return result


def load_discord_token() -> str:
    for line in (PROFILE / ".env").read_text(errors="ignore").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("Ares Discord token unavailable")


def post_discord(text: str) -> dict[str, Any]:
    if len(text) > 1900:
        raise Stop("discord_post", {"message": "message exceeds 1900 characters", "length": len(text)})
    token = load_discord_token()
    payload = json.dumps({"content": text, "allowed_mentions": {"parse": []}}, ensure_ascii=False).encode()
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{THREAD_CREATION}/messages",
        data=payload,
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json", "User-Agent": "MGS-Ares-CPV-Daily-Create/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        message = json.load(response)
    message_id = str(message.get("id") or "")
    if not message_id:
        raise Stop("discord_post", {"message": "response missing message id"})
    readback = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{THREAD_CREATION}/messages/{message_id}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "MGS-Ares-CPV-Daily-Create/1.0"},
    )
    with urllib.request.urlopen(readback, timeout=30) as response:
        check = json.load(response)
    if str(check.get("channel_id") or "") != THREAD_CREATION or str(check.get("content") or "") != text:
        raise Stop("discord_readback", {"message_id": message_id, "channel_id": check.get("channel_id"), "content_match": str(check.get("content") or "") == text})
    return {"message_id": message_id, "channel_id": THREAD_CREATION, "content_match": True}


def choose_slots(campaigns: list[dict[str, Any]], explicit: list[int] | None, allow_replacement: bool = False, required_count: int = CAMPAIGN_COUNT) -> tuple[list[int], dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    history: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for campaign in campaigns:
        number = parse_number(str(campaign.get("name") or ""))
        if number is not None:
            history[number].append(campaign)
    candidates = explicit or PREFERRED_SLOT_ORDER
    selected: list[int] = []
    replacements: dict[str, dict[str, Any]] = {}
    for number in candidates:
        rows = history.get(number, [])
        nondeleted = [row for row in rows if row.get("effective_status") != "ARCHIVED"]
        if not nondeleted:
            selected.append(number)
        elif allow_replacement and len(nondeleted) == 1 and (nondeleted[0].get("configured_status") or nondeleted[0].get("status")) == "PAUSED" and nondeleted[0].get("effective_status") == "PAUSED":
            selected.append(number)
            replacements[str(number)] = {key: nondeleted[0].get(key) for key in ["id", "name", "status", "effective_status", "configured_status", "daily_budget", "bid_strategy", "start_time", "updated_time"]}
        if len(selected) == required_count:
            break
    if len(selected) != required_count:
        raise Stop("slot_selection", {"message": "fewer than required contiguous reusable/replacement campaign slots", "requested": candidates, "selected": selected, "required_count": required_count, "allow_replacement": allow_replacement})
    summarized = {
        str(number): [{key: row.get(key) for key in ["id", "name", "status", "effective_status", "configured_status", "daily_budget", "updated_time"]} for row in history.get(number, [])]
        for number in selected
    }
    return selected, summarized, replacements


def pool_candidates(rows: list[dict[str, Any]], live_by_id: dict[str, dict[str, Any]], latest_meta_created: datetime | None, release_new_pool: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible: list[dict[str, Any]] = []
    duplicate_blocked: list[dict[str, Any]] = []
    if release_new_pool:
        if latest_meta_created is None:
            raise Stop("pool_release", {"message": "latest Meta media timestamp unavailable"})
        new_rows: list[dict[str, Any]] = []
        for row in rows:
            if row.get("vertical") != "CAR" or row.get("country") != "BR" or row.get("language") != "BR" or row.get("format") != "VID" or row.get("status") != "01_READY" or row.get("metadata_clean") is not True or row.get("used_by") or row.get("asset_drive_id") not in live_by_id:
                continue
            try:
                first_seen = datetime.fromisoformat(str(row.get("first_seen_at") or "").replace("Z", "+00:00"))
            except ValueError:
                continue
            if first_seen > latest_meta_created:
                new_rows.append(row)
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in new_rows:
            groups[str(row.get("perceptual_fingerprint") or row.get("clean_checksum") or row.get("asset_id"))].append(row)
        for group in groups.values():
            group.sort(key=lambda row: (str(row.get("first_seen_at") or ""), str(row.get("canonical_filename") or "")))
            eligible.append(group[0])
            duplicate_blocked.extend(group[1:])
        return sorted(eligible, key=lambda row: (str(row.get("first_seen_at") or ""), str(row.get("canonical_filename") or ""))), duplicate_blocked
    for row in rows:
        if row.get("ares_eligible") is True and row.get("status") == "01_READY" and row.get("metadata_clean") is True and not row.get("used_by") and row.get("asset_drive_id") in live_by_id and row.get("format") == "VID":
            eligible.append(row)
    return sorted(eligible, key=lambda row: (str(row.get("first_seen_at") or ""), str(row.get("canonical_filename") or ""))), duplicate_blocked


def choose_assets(candidates: list[dict[str, Any]], explicit_names: list[str] | None, required_count: int = ASSET_COUNT) -> list[dict[str, Any]]:
    if explicit_names:
        by_name = {str(row.get("canonical_filename")): row for row in candidates}
        requested_names = explicit_names[:required_count]
        missing = [name for name in requested_names if name not in by_name]
        if missing:
            raise Stop("asset_selection", {"message": "explicit assets unavailable", "missing": missing})
        selected = [by_name[name] for name in requested_names]
    else:
        selected = candidates[:required_count]
    if len(selected) != required_count:
        raise Stop("asset_selection", {"message": "insufficient eligible assets", "required": required_count, "available": len(candidates), "selected": len(selected)})
    fingerprints = [str(row.get("perceptual_fingerprint") or row.get("clean_checksum") or "") for row in selected]
    if len(set(fingerprints)) != required_count:
        raise Stop("asset_selection", {"message": "selected assets contain duplicate lineage/fingerprint", "fingerprints": fingerprints})
    return selected


def inventory_mark_pool(rows: list[dict[str, Any]], eligible: list[dict[str, Any]], duplicate_blocked: list[dict[str, Any]], reconcile_at: str, evidence: dict[str, Any]) -> None:
    eligible_ids = {str(row.get("asset_id")) for row in eligible}
    duplicate_ids = {str(row.get("asset_id")) for row in duplicate_blocked}
    for row in rows:
        asset_id = str(row.get("asset_id") or "")
        if asset_id in eligible_ids:
            row["reservation_status"] = "LIBERADO_POR_RODOLFO_PARA_ARES_DAILY"
            row["ares_eligible"] = True
            row["campaign_owner"] = "Ares"
            row["last_reconciled_at"] = reconcile_at
            row["release_authorized_by"] = "Rodolfo Mattei"
            row["release_authorized_at"] = reconcile_at
            row["release_evidence"] = evidence
        elif asset_id in duplicate_ids:
            row["reservation_status"] = "DUPLICATE_LINEAGE_BLOCKED"
            row["ares_eligible"] = False
            row["last_reconciled_at"] = reconcile_at
            row["duplicate_block_evidence"] = evidence


def reserve_selected(rows: list[dict[str, Any]], selected: list[dict[str, Any]], audit_path: Path) -> None:
    selected_ids = {str(row.get("asset_id")) for row in selected}
    for row in rows:
        if str(row.get("asset_id") or "") in selected_ids:
            row["reservation_status"] = "RESERVADO_PELO_ARES_DAILY"
            row["ares_eligible"] = False
            row["used_by"] = "ARES_IN_FLIGHT"
            row["campaign_owner"] = "Ares"
            row["reservation_audit"] = str(audit_path)
            row["last_reconciled_at"] = stamp_utc()


def release_after_clean_failure(rows: list[dict[str, Any]], selected: list[dict[str, Any]]) -> None:
    selected_ids = {str(row.get("asset_id")) for row in selected}
    for row in rows:
        if str(row.get("asset_id") or "") in selected_ids:
            row["reservation_status"] = "LIBERADO_POR_RODOLFO_PARA_ARES_DAILY"
            row["ares_eligible"] = True
            row["used_by"] = None
            row["campaign_owner"] = "Ares"
            row.pop("reservation_audit", None)


def finish_inventory(rows: list[dict[str, Any]], assignments: list[dict[str, Any]], drive_moves: dict[str, dict[str, Any]], audit_path: Path) -> None:
    by_asset = {str(row["asset_id"]): row for row in assignments}
    for row in rows:
        assignment = by_asset.get(str(row.get("asset_id") or ""))
        if not assignment:
            continue
        row["status"] = "02_TESTING" if str(row.get("asset_drive_id")) in drive_moves else "01_READY_USED_MOVE_PENDING"
        row["reservation_status"] = "UTILIZADO_PELO_ARES"
        row["ares_eligible"] = False
        row["used_by"] = "ARES"
        row["campaign_owner"] = "Ares"
        row["ad_account_id"] = ACCOUNT_ID
        row["meta_campaign_id"] = assignment["campaign_id"]
        row["meta_adset_id"] = assignment["adset_id"]
        row["meta_ad_id"] = assignment["ad_id"]
        row["meta_creative_id"] = assignment["creative_id"]
        row["meta_video_id"] = assignment["vertical_video_id"]
        row["meta_video_ids"] = [assignment["vertical_video_id"], assignment["square_video_id"]]
        row["last_reconciled_at"] = stamp_utc()
        row["campaign_audit"] = str(audit_path)
        row["drive_status_readback"] = drive_moves.get(str(row.get("asset_drive_id")))


def stock_counts(rows: list[dict[str, Any]], drive: dict[str, Any]) -> dict[str, int]:
    live_ids = {str(row.get("id")) for row in drive["files"]}
    eligible_fingerprints: set[str] = set()
    eligible_files = 0
    for row in rows:
        if row.get("ares_eligible") is True and row.get("status") == "01_READY" and not row.get("used_by") and str(row.get("asset_drive_id") or "") in live_ids:
            eligible_files += 1
            eligible_fingerprints.add(str(row.get("perceptual_fingerprint") or row.get("clean_checksum") or row.get("asset_id")))
    return {"ready_folder_total": int(drive["counts"]["TOTAL"]), "ready_folder_img": int(drive["counts"]["IMG"]), "ready_folder_vid": int(drive["counts"]["VID"]), "eligible_files": eligible_files, "eligible_unique_creatives": len(eligible_fingerprints)}


def parse_datetime_meta(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))


def execute(args: argparse.Namespace) -> int:
    operational_date = datetime.fromisoformat(args.operational_date).replace(tzinfo=SP) if args.operational_date else now_sp()
    date_key = operational_date.strftime("%Y-%m-%d")
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    audit_path = AUDIT_DIR / f"daily-create-{date_key}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    audit: dict[str, Any] = {
        "created_at_utc": stamp_utc(),
        "authorized_by": "Rodolfo Mattei",
        "authorization_scope": "daily 17:00 Sao Paulo; 2x MAXVOL USD30; Drive assets; stock remaining report",
        "mode": "DRY_RUN" if args.dry_run else ("CONTROLLED_WRITE_DAILY_C08_CLONE_WITH_DRIVE_CREATIVES" if args.clone_source else "CONTROLLED_WRITE_DAILY_DRIVE_MAXVOL_FROM_ZERO"),
        "creation_route_requested": "native_shallow_clone_C08_campaign_adset" if args.clone_source else "from_zero_campaign_adset",
        "graph_version": GRAPH_VERSION,
        "account_id": ACCOUNT_ID,
        "account_alias": ACCOUNT_ALIAS,
        "operational_date_sp": date_key,
        "scheduled_start_sp": scheduled_start(operational_date).isoformat(),
        "audit_path": str(audit_path),
        "created_campaign_ids": [],
        "created_ad_ids": [],
        "created_creative_ids": [],
        "created_video_ids": [],
        "stage": "initializing",
    }
    atomic_json(audit_path, audit)
    common = load_common()
    drive_mod = load_drive_module()
    token: str | None = None
    page_token: str | None = None
    inventory_rows: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    reserved = False
    external_write_started = False
    replacement_commit_started = False
    try:
        prior = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
        if not args.dry_run and prior.get("completed_operational_date_sp") == date_key:
            raise Stop("idempotency_state", {"message": "daily creation already completed for operational date", "state": {key: prior.get(key) for key in ["status", "completed_operational_date_sp", "audit_path"]}})
        token, token_field = common.get_token_from_1password(TOKEN_ITEM, force_refresh=True)
        audit["token_report"] = {"item": TOKEN_ITEM, "field": token_field, "len": len(token)}
        source = source_preflight(common, token)
        page_token = source.pop("page_token")
        campaigns = list_campaigns(common, token)
        if args.campaign_numbers:
            explicit_slots = [int(item) for item in args.campaign_numbers.split(",")]
        elif prior.get("completed_operational_date_sp") and str(prior.get("completed_operational_date_sp")) < date_key and prior.get("campaign_numbers"):
            next_number = max(int(item) for item in prior.get("campaign_numbers") or []) + 1
            explicit_slots = [next_number, next_number + 1]
        else:
            explicit_slots = list(PREFERRED_SLOT_ORDER)
        desired_slots = list(explicit_slots[:CAMPAIGN_COUNT])
        quota_plan = build_quota_plan(
            common,
            len(desired_slots),
            clone_source=bool(args.clone_source),
            replacement=bool(args.replace_existing_sequential),
        )
        campaign_count = int(quota_plan["selected_count"] or 0)
        if args.dry_run and campaign_count == 0:
            campaign_count = len(desired_slots)
            quota_plan["dry_run_write_gate_bypassed"] = True
        elif campaign_count == 0:
            raise ReadbackDeferred("quota_prewrite_gate", {"quota_plan": quota_plan}, quota_retry_after_seconds(common))
        execution_slots = desired_slots[:campaign_count]
        remaining_slots = desired_slots[campaign_count:]
        active_budget_before = sum(int(row.get("daily_budget") or 0) for row in campaigns if row.get("effective_status") == "ACTIVE")
        if active_budget_before + campaign_count * BUDGET_MINOR > ACCOUNT_CAP_MINOR:
            raise Stop("budget_cap", {"active_budget_usd": active_budget_before / 100, "new_budget_usd": campaign_count * BUDGET_MINOR / 100, "cap_usd": ACCOUNT_CAP_MINOR / 100})
        slots, slot_history, replacement_targets = choose_slots(
            campaigns,
            execution_slots,
            allow_replacement=args.replace_existing_sequential,
            required_count=campaign_count,
        )
        if args.release_new_pool:
            raise Stop("reconciliation_route", {"message": "release/reconciliation is prohibited inside campaign writer; run the separate reconciler first"})
        drive_sa = drive_mod.extract_service_account(drive_mod.get_op_item_json())
        if drive_sa.get("client_email") != "mgsagent@mgs-core-prod.iam.gserviceaccount.com" or drive_sa.get("project_id") != "mgs-core-prod":
            raise Stop("drive_identity", {"client_email": drive_sa.get("client_email"), "project_id": drive_sa.get("project_id")})
        drive_token = drive_mod.get_access_token(drive_sa)
        drive_before = drive_inventory(drive_token)
        live_by_id = {str(row["id"]): row for row in drive_before["files"]}
        inventory_rows = load_inventory()
        candidates, duplicate_blocked = pool_candidates(inventory_rows, live_by_id, None, False)
        explicit_names = [item.strip() for item in args.asset_names.split(",") if item.strip()] if args.asset_names else None
        required_asset_count = campaign_count * ADS_PER_CAMPAIGN
        remaining_asset_names = explicit_names[required_asset_count:] if explicit_names else []
        selected = choose_assets(candidates, explicit_names, required_count=required_asset_count)
        reconciliation = load_reconciliation_manifest(selected)
        conflicts: list[dict[str, Any]] = []
        audit["preflight"] = {
            "account": source["account"],
            "token_debug": source["token_debug"],
            "page": source["page"],
            "source_campaign": source["campaign"],
            "source_adset": source["adset"],
            "source_ads": [{"id": row["id"], "name": row["name"], "creative_id": row["creative"]["id"]} for row in source["ads"]],
            "active_budget_usd_before": active_budget_before / 100,
            "active_budget_usd_after_planned": (active_budget_before + campaign_count * BUDGET_MINOR) / 100,
            "account_cap_usd": ACCOUNT_CAP_MINOR / 100,
            "desired_slots": desired_slots,
            "slots": slots,
            "remaining_slots_after_quota_fallback": remaining_slots,
            "quota_plan": quota_plan,
            "slot_history": slot_history,
            "replacement_targets": replacement_targets,
            "replacement_authorized_by": "Rodolfo Mattei" if replacement_targets else None,
            "reconciliation_manifest": reconciliation,
            "meta_ads_scanned_current_and_archived": int((reconciliation.get("meta_counts") or {}).get("ads_scanned") or 0),
            "meta_video_ids_scanned": int((reconciliation.get("meta_counts") or {}).get("video_ids_scanned") or 0),
            "writer_global_reconciliation_calls": 0,
            "drive_identity": {"service_account": drive_sa.get("client_email"), "project_id": drive_sa.get("project_id"), "drive_id": drive_before["root"].get("driveId")},
            "drive_counts_before": drive_before["counts"],
            "pool_candidates": len(candidates),
            "duplicate_lineages_blocked": len(duplicate_blocked),
            "selected_assets": [{key: row.get(key) for key in ["asset_id", "original_filename", "canonical_filename", "asset_drive_id", "clean_checksum", "perceptual_fingerprint", "first_seen_at"]} for row in selected],
            "meta_conflicts": conflicts,
        }
        audit["stage"] = "preflight_complete"
        atomic_json(audit_path, audit)
        if args.dry_run:
            result = {
                "status": "DRY_RUN_OK",
                "operational_date_sp": date_key,
                "campaign_numbers": slots,
                "scheduled_start_sp": scheduled_start(operational_date).isoformat(),
                "selected_assets": [row["canonical_filename"] for row in selected],
                "drive_counts_before": drive_before["counts"],
                "reconciled_pool_unique": len(candidates),
                "duplicate_lineages_blocked": len(duplicate_blocked),
                "active_budget_usd_before": active_budget_before / 100,
                "active_budget_usd_after_planned": (active_budget_before + campaign_count * BUDGET_MINOR) / 100,
                "quota_plan": quota_plan,
                "remaining_slots_after_quota_fallback": remaining_slots,
                "audit": str(audit_path),
            }
            audit["final"] = result
            audit["stage"] = "dry_run_complete"
            atomic_json(audit_path, audit)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        reserve_selected(inventory_rows, selected, audit_path)
        atomic_inventory(inventory_rows)
        reserved = True
        atomic_json(STATE_PATH, {"status": "in_flight_reserved", "operational_date_sp": date_key, "audit_path": str(audit_path), "selected_asset_ids": [row["asset_id"] for row in selected], "updated_at_utc": stamp_utc()})
        run_dir = WORK_ROOT / f"{date_key}-{datetime.now(timezone.utc):%H%M%SZ}"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        assets_dir = run_dir / "assets"
        crops_dir = run_dir / "square"
        assets_dir.mkdir(parents=True, exist_ok=True)
        crops_dir.mkdir(parents=True, exist_ok=True)
        prepared: list[dict[str, Any]] = []
        for row in selected:
            drive_row = live_by_id[str(row["asset_drive_id"])]
            source_path = assets_dir / str(row["canonical_filename"])
            drive_readback = download_drive_file(drive_token, drive_row, source_path)
            clean_readback = verify_clean(source_path)
            if clean_readback["sha256"] != str(row.get("clean_checksum") or ""):
                raise Stop("inventory_checksum", {"asset_id": row.get("asset_id"), "expected": row.get("clean_checksum"), "actual": clean_readback["sha256"]})
            square_path = crops_dir / (source_path.stem + "__SQUARE.mp4")
            square_readback = make_square_clean(source_path, square_path)
            prepared.append({"inventory": row, "drive": drive_row, "source_path": source_path, "square_path": square_path, "drive_readback": drive_readback, "clean_readback": clean_readback, "square_readback": square_readback})
        audit["prepared_assets"] = [{"asset_id": item["inventory"]["asset_id"], "canonical_filename": item["inventory"]["canonical_filename"], "drive": item["drive_readback"], "clean": item["clean_readback"], "square": item["square_readback"]} for item in prepared]
        audit["stage"] = "assets_prepared"
        atomic_json(audit_path, audit)
        external_write_started = True
        for item in prepared:
            name = str(item["inventory"]["canonical_filename"])
            vertical = multipart_video_upload(common, page_token, item["source_path"], name, "upload_vertical")
            audit["created_video_ids"].append(vertical["id"])
            atomic_json(audit_path, audit)
            square = multipart_video_upload(common, page_token, item["square_path"], "SQUARE__" + name, "upload_square")
            audit["created_video_ids"].append(square["id"])
            atomic_json(audit_path, audit)
            item["vertical_upload"] = vertical
            item["square_upload"] = square
        processing = wait_videos_ready_batch(common, page_token, audit["created_video_ids"], "uploaded_videos_ready_batch")
        for item in prepared:
            item["vertical_upload"]["processing"] = processing["videos"][item["vertical_upload"]["id"]]
            item["square_upload"]["processing"] = processing["videos"][item["square_upload"]["id"]]
        audit["video_processing_batch"] = processing["attempts"]
        audit["stage"] = "videos_uploaded_ready"
        atomic_json(audit_path, audit)
        assignments: list[dict[str, Any]] = []
        for campaign_index, number in enumerate(slots):
            campaign_assets = prepared[campaign_index * ADS_PER_CAMPAIGN:(campaign_index + 1) * ADS_PER_CAMPAIGN]
            if args.clone_source:
                campaign_id, adset_id, clone_validation = clone_campaign_adset_shell(common, token, source, number, operational_date, audit, audit_path)
                audit.setdefault("clone_shells", {})[str(number)]["final"] = clone_validation
                atomic_json(audit_path, audit)
                time.sleep(5)
            else:
                cp = campaign_payload(source, number, operational_date)
                validate = dict(cp)
                validate["execution_options"] = ["validate_only"]
                result, _ = graph_post_once(common, token, ACCOUNT_ACT + "/campaigns", validate, f"c{number}_campaign_validate")
                if result.get("success") is not True:
                    raise Stop(f"c{number}_campaign_validate", {"message": "validate_only did not return success=true"})
                created, _ = graph_post_once(common, token, ACCOUNT_ACT + "/campaigns", cp, f"c{number}_campaign_create", expect_id=True)
                campaign_id = str(created["id"])
                audit["created_campaign_ids"].append(campaign_id)
                atomic_json(audit_path, audit)
                ap = adset_payload(source, campaign_id, number)
                av = dict(ap)
                av["execution_options"] = ["validate_only"]
                result, _ = graph_post_once(common, token, ACCOUNT_ACT + "/adsets", av, f"c{number}_adset_validate")
                if result.get("success") is not True:
                    raise Stop(f"c{number}_adset_validate", {"message": "validate_only did not return success=true"})
                created, _ = graph_post_once(common, token, ACCOUNT_ACT + "/adsets", ap, f"c{number}_adset_create", expect_id=True)
                adset_id = str(created["id"])
            for ad_index, (source_ad, item) in enumerate(zip(source["ads"], campaign_assets), 1):
                creative_params = creative_payload(source_ad, number, ad_index, str(item["inventory"]["canonical_filename"]), item["vertical_upload"]["id"], item["square_upload"]["id"])
                created, _ = graph_post_once(common, token, ACCOUNT_ACT + "/adcreatives", creative_params, f"c{number}_creative_{ad_index}_create", expect_id=True)
                creative_id = str(created["id"])
                audit["created_creative_ids"].append(creative_id)
                atomic_json(audit_path, audit)
                ad_params = {"name": f"AD {ad_index:02d} - {Path(str(item['inventory']['canonical_filename'])).stem}", "adset_id": adset_id, "creative": {"creative_id": creative_id}, "status": "ACTIVE"}
                validated = False
                propagation: list[dict[str, Any]] = []
                for attempt in range(1, 7):
                    avp = dict(ad_params)
                    avp["execution_options"] = ["validate_only"]
                    try:
                        check, _ = graph_post_once(common, token, ACCOUNT_ACT + "/ads", avp, f"c{number}_ad_{ad_index}_validate")
                        validated = check.get("success") is True
                        propagation.append({"attempt": attempt, "success": validated})
                        break
                    except Stop as exc:
                        error = (exc.detail or {}).get("error") or {}
                        propagation.append({"attempt": attempt, "success": False, "error": error})
                        if error.get("error_subcode") != 2446289 or attempt == 6:
                            raise
                        time.sleep(5)
                if not validated:
                    raise Stop(f"c{number}_ad_{ad_index}_validate", {"message": "validate_only did not pass", "propagation": propagation})
                created, _ = graph_post_once(common, token, ACCOUNT_ACT + "/ads", ad_params, f"c{number}_ad_{ad_index}_create", expect_id=True)
                ad_id = str(created["id"])
                audit["created_ad_ids"].append(ad_id)
                assignment = {
                    "asset_id": item["inventory"]["asset_id"],
                    "canonical_filename": item["inventory"]["canonical_filename"],
                    "campaign_number": number,
                    "campaign_id": campaign_id,
                    "adset_id": adset_id,
                    "ad_id": ad_id,
                    "creative_id": creative_id,
                    "vertical_video_id": item["vertical_upload"]["id"],
                    "square_video_id": item["square_upload"]["id"],
                    "propagation": propagation,
                }
                assignments.append(assignment)
                audit["assignments"] = assignments
                audit["stage"] = "write_in_flight"
                atomic_json(audit_path, audit)
        audit["assignments"] = assignments
        audit["stage"] = "write_complete_readback_pending"
        atomic_json(audit_path, audit)
        time.sleep(5)
        validations: dict[str, Any] = {}
        for campaign_index, number in enumerate(slots):
            campaign_assets = selected[campaign_index * ADS_PER_CAMPAIGN:(campaign_index + 1) * ADS_PER_CAMPAIGN]
            campaign_id = next(item["campaign_id"] for item in assignments if item["campaign_number"] == number)
            readback = read_hierarchy(common, token, campaign_id, f"c{number}_final_readback")
            validation = validate_hierarchy(readback, source, number, operational_date, campaign_assets)
            validations[str(number)] = {"readback": readback, "validation": validation}
            if not validation["valid"]:
                raise Stop("final_validation", {"campaign_number": number, "validation": validation})
        campaigns_after = list_campaigns(common, token)
        active_budget_after = sum(int(row.get("daily_budget") or 0) for row in campaigns_after if row.get("effective_status") in {"ACTIVE", "IN_PROCESS", "PENDING_REVIEW", "PREPARED"})
        if active_budget_after > ACCOUNT_CAP_MINOR:
            raise Stop("final_budget_cap", {"active_budget_usd_after": active_budget_after / 100, "cap_usd": ACCOUNT_CAP_MINOR / 100})
        replacement_deletions: dict[str, Any] = {}
        if replacement_targets:
            replacement_commit_started = True
            audit["stage"] = "replacement_commit_in_flight"
            audit["replacement_targets"] = replacement_targets
            audit["replacement_deletions"] = replacement_deletions
            atomic_json(audit_path, audit)
            atomic_json(STATE_PATH, {
                "status": "replacement_commit_in_flight",
                "operational_date_sp": date_key,
                "audit_path": str(audit_path),
                "campaign_numbers": slots,
                "campaign_ids": audit.get("created_campaign_ids") or [],
                "replacement_targets": replacement_targets,
                "updated_at_utc": stamp_utc(),
            })
            for number in slots:
                old = replacement_targets.get(str(number))
                if not old:
                    continue
                old_id = str(old.get("id") or "")
                new_id = next(item["campaign_id"] for item in assignments if item["campaign_number"] == number)
                if not old_id or old_id == new_id:
                    raise Stop("replacement_identity", {"number": number, "old_id_present": bool(old_id), "same_id": old_id == new_id})
                response, _ = graph_post_once(common, token, old_id, {"status": "DELETED"}, f"c{number}_old_campaign_delete")
                readback, _ = graph_get(common, token, old_id, {"fields": "id,name,status,effective_status,configured_status,updated_time"}, f"c{number}_old_campaign_delete_readback")
                deleted = readback.get("effective_status") == "ARCHIVED" or readback.get("status") in {"DELETED", "ARCHIVED"}
                replacement_deletions[str(number)] = {"old_campaign_id": old_id, "new_campaign_id": new_id, "response_success": response.get("success") is True, "deleted": deleted, "readback": readback}
                audit["replacement_deletions"] = replacement_deletions
                atomic_json(audit_path, audit)
                if not deleted:
                    raise Stop("replacement_delete_readback", {"number": number, "old_campaign_id": old_id, "readback": readback})
        drive_moves: dict[str, dict[str, Any]] = {}
        for item in prepared:
            readback = drive_move_to_testing(drive_token, item["drive"])
            drive_moves[str(item["inventory"]["asset_drive_id"])] = readback
        finish_inventory(inventory_rows, assignments, drive_moves, audit_path)
        atomic_inventory(inventory_rows)
        drive_after = drive_inventory(drive_token)
        stock = stock_counts(inventory_rows, drive_after)
        prior_prepared_numbers = [int(item) for item in (prior.get("prepared_campaign_numbers") or [])]
        prior_prepared_ids = [str(item) for item in (prior.get("prepared_campaign_ids") or [])]
        all_prepared_numbers = prior_prepared_numbers + [number for number in slots if number not in prior_prepared_numbers]
        current_campaign_ids = [next(item["campaign_id"] for item in assignments if item["campaign_number"] == number) for number in slots]
        all_prepared_ids = prior_prepared_ids + [campaign_id for campaign_id in current_campaign_ids if campaign_id not in prior_prepared_ids]
        final_status = "COMPLETE_PREPARED_PAUSED_PARTIAL_QUOTA" if remaining_slots else "COMPLETE_PREPARED_PAUSED"
        final = {
            "status": final_status,
            "creation_route": "native shallow clone of C08 MAXVOL campaign/adset with new Drive creatives" if args.clone_source else "from-zero campaign/adset with new Drive creatives",
            "campaigns": [{"number": number, "campaign_id": next(item["campaign_id"] for item in assignments if item["campaign_number"] == number), "budget_usd": 30, "bid_strategy": "MAXVOL", "structure": "1x1x3"} for number in slots],
            "scheduled_start_sp": scheduled_start(operational_date).isoformat(),
            "assets_used": [row["canonical_filename"] for row in selected],
            "stock_remaining": stock,
            "active_budget_usd_before": active_budget_before / 100,
            "active_budget_usd_after": active_budget_after / 100,
            "activation_projected_budget_usd": (active_budget_after + len(all_prepared_numbers) * BUDGET_MINOR) / 100,
            "validations": {number: item["validation"]["valid"] for number, item in validations.items()},
            "replacement_deletions": replacement_deletions,
            "quota_plan": quota_plan,
            "remaining_slots_after_quota_fallback": remaining_slots,
            "audit": str(audit_path),
        }
        audit["assignments"] = assignments
        audit["validations"] = validations
        audit["drive_moves"] = drive_moves
        audit["final"] = final
        audit["stage"] = "complete_partial_quota" if remaining_slots else "complete"
        audit["updated_at_utc"] = stamp_utc()
        atomic_json(audit_path, audit)
        campaign_ids = current_campaign_ids
        if remaining_slots:
            resume_after_epoch = max(int(time.time()) + 300, int(quota_plan.get("blocked_until_epoch") or 0))
            atomic_json(STATE_PATH, {
                "status": "preflight_deferred",
                "operational_date_sp": date_key,
                "resume_after_epoch": resume_after_epoch,
                "campaign_numbers": ",".join(str(item) for item in remaining_slots),
                "asset_names": ",".join(remaining_asset_names),
                "release_new_pool": False,
                "replace_existing_sequential": bool(args.replace_existing_sequential),
                "clone_source": bool(args.clone_source),
                "prepared_campaign_numbers": all_prepared_numbers,
                "prepared_campaign_ids": all_prepared_ids,
                "audit_path": str(audit_path),
                "stock_remaining": stock,
                "updated_at_utc": stamp_utc(),
            })
        else:
            atomic_json(STATE_PATH, {
                "status": "prepared_paused",
                "completed_operational_date_sp": date_key,
                "activation_at_sp": scheduled_start(operational_date).isoformat(),
                "campaign_numbers": all_prepared_numbers,
                "campaign_ids": all_prepared_ids,
                "audit_path": str(audit_path),
                "stock_remaining": stock,
                "updated_at_utc": stamp_utc(),
            })
        campaign_labels = " e ".join(f"C{number:02d}" for number in slots)
        remaining_note = f"\nPróxima etapa após cooldown: {' e '.join(f'C{number:02d}' for number in remaining_slots)}" if remaining_slots else ""
        message = (
            f"✅ CAMPANHA{'S' if len(slots) > 1 else ''} PREPARADA{'S' if len(slots) > 1 else ''} — Creditoparaveiculo 13 G006 — {operational_date:%d/%m}\n"
            f"{campaign_labels} · {'clone C08 MAXVOL' if args.clone_source else 'MAXVOL do zero'} · USD 30 cada · 1×1×3 · PAUSED\n"
            f"Ativação automática: 00:30 de {(operational_date + timedelta(days=1)):%d/%m} (São Paulo)\n"
            f"Criativos usados: {len(selected)} vídeos do Shared Drive\n"
            f"Estoque restante em 01_READY: {stock['ready_folder_total']} arquivos ({stock['ready_folder_img']} IMG + {stock['ready_folder_vid']} VID)\n"
            f"Disponíveis já liberados/reconciliados: {stock['eligible_unique_creatives']} criativos únicos"
            f"{remaining_note}"
        )
        if args.post_discord:
            final["discord_readback"] = post_discord(message)
            audit["final"] = final
            atomic_json(audit_path, audit)
        if not args.quiet:
            print(json.dumps(final, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        detail: dict[str, Any] = {"type": type(exc).__name__, "message": str(exc)[:3000]}
        if isinstance(exc, Stop):
            detail["stage"] = exc.stage
            detail["detail"] = exc.detail
        if isinstance(exc, ReadbackDeferred) and external_write_started:
            resume_after_epoch = int(time.time()) + exc.retry_after_seconds
            audit["failure"] = detail
            audit["stage"] = "readback_deferred"
            audit["resume_after_epoch"] = resume_after_epoch
            audit["updated_at_utc"] = stamp_utc()
            atomic_json(audit_path, audit)
            atomic_json(STATE_PATH, {
                "status": "readback_deferred",
                "operational_date_sp": date_key,
                "audit_path": str(audit_path),
                "resume_after_epoch": resume_after_epoch,
                "campaign_numbers": audit.get("preflight", {}).get("slots") or [],
                "campaign_ids": audit.get("created_campaign_ids") or [],
                "updated_at_utc": stamp_utc(),
            })
            if args.post_discord and not args.dry_run:
                try:
                    post_discord(f"🟡 READBACK ADIADO — Creditoparaveiculo 13 G006 — {operational_date:%d/%m}\nA Meta limitou temporariamente a leitura final. As campanhas permanecem em estado pendente de validação; os criativos continuam reservados e o reconciliador retomará após o cooldown. Não considero a criação concluída ainda.")
                except Exception:
                    pass
            if not args.quiet:
                print(json.dumps({"status": "READBACK_DEFERRED", "failure": detail, "resume_after_epoch": resume_after_epoch, "audit": str(audit_path)}, ensure_ascii=False, indent=2))
            return 2
        if isinstance(exc, ReadbackDeferred) and not external_write_started:
            resume_after_epoch = int(time.time()) + exc.retry_after_seconds
            audit["failure"] = detail
            audit["stage"] = "preflight_deferred"
            audit["resume_after_epoch"] = resume_after_epoch
            audit["updated_at_utc"] = stamp_utc()
            atomic_json(audit_path, audit)
            atomic_json(STATE_PATH, {
                "status": "preflight_deferred",
                "operational_date_sp": date_key,
                "audit_path": str(audit_path),
                "resume_after_epoch": resume_after_epoch,
                "asset_names": args.asset_names,
                "campaign_numbers": args.campaign_numbers,
                "release_new_pool": bool(args.release_new_pool),
                "replace_existing_sequential": bool(args.replace_existing_sequential),
                "clone_source": bool(args.clone_source),
                "updated_at_utc": stamp_utc(),
            })
            if args.post_discord and not args.dry_run:
                try:
                    post_discord(f"🟡 PREFLIGHT ADIADO — Creditoparaveiculo 13 G006 — {operational_date:%d/%m}\nA Meta limitou a reconciliação antes de qualquer write. Nenhuma campanha ou mídia foi criada e nenhum asset foi consumido. O runner retomará o mesmo plano após o cooldown.")
                except Exception:
                    pass
            if not args.quiet:
                print(json.dumps({"status": "PREFLIGHT_DEFERRED", "failure": detail, "resume_after_epoch": resume_after_epoch, "audit": str(audit_path)}, ensure_ascii=False, indent=2))
            return 2
        if replacement_commit_started and external_write_started:
            audit["failure"] = detail
            audit["stage"] = "replacement_commit_failed_preserved"
            audit["updated_at_utc"] = stamp_utc()
            atomic_json(audit_path, audit)
            atomic_json(STATE_PATH, {
                "status": "replacement_commit_failed_preserved",
                "operational_date_sp": date_key,
                "audit_path": str(audit_path),
                "campaign_numbers": audit.get("preflight", {}).get("slots") or [],
                "campaign_ids": audit.get("created_campaign_ids") or [],
                "replacement_targets": audit.get("preflight", {}).get("replacement_targets") or {},
                "replacement_deletions": audit.get("replacement_deletions") or {},
                "failure": detail,
                "updated_at_utc": stamp_utc(),
            })
            if args.post_discord:
                try:
                    post_discord(f"⚠️ REPLACEMENT PARCIAL PRESERVADO — Creditoparaveiculo 13 G006 — {operational_date:%d/%m}\nAs novas campanhas permanecem PAUSED e nenhum cleanup destrutivo foi feito após o início da troca das antigas. O estado foi congelado para reconciliação exata antes de continuar.")
                except Exception:
                    pass
            if not args.quiet:
                print(json.dumps({"status": "REPLACEMENT_COMMIT_FAILED_PRESERVED", "failure": detail, "audit": str(audit_path)}, ensure_ascii=False, indent=2))
            return 1
        cleanup = None
        if external_write_started and token:
            cleanup = cleanup_failure(common, token, page_token, audit)
        if reserved and inventory_rows and selected and (not external_write_started or (cleanup and cleanup.get("complete"))):
            release_after_clean_failure(inventory_rows, selected)
            atomic_inventory(inventory_rows)
        audit["failure"] = detail
        audit["cleanup"] = cleanup
        audit["stage"] = "failed_clean" if (not external_write_started or (cleanup and cleanup.get("complete"))) else "failed_cleanup_incomplete"
        audit["updated_at_utc"] = stamp_utc()
        atomic_json(audit_path, audit)
        atomic_json(STATE_PATH, {"status": audit["stage"], "operational_date_sp": date_key, "audit_path": str(audit_path), "failure_stage": detail.get("stage"), "updated_at_utc": stamp_utc()})
        if args.post_discord and not args.dry_run:
            try:
                post_discord(f"⚠️ CRIAÇÃO NÃO CONCLUÍDA — Creditoparaveiculo 13 G006 — {operational_date:%d/%m}\nA rotina falhou de forma fechada em {detail.get('stage') or detail['type']}. Nenhuma campanha será considerada pronta sem novo readback. Estoque não consumido quando o cleanup foi confirmado.")
            except Exception:
                pass
        if not args.quiet:
            print(json.dumps({"status": audit["stage"].upper(), "failure": detail, "cleanup_complete": None if cleanup is None else cleanup.get("complete"), "audit": str(audit_path)}, ensure_ascii=False, indent=2))
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--release-new-pool", action="store_true", help="Release only new post-Meta, exact-deduped assets under Rodolfo's authorization")
    parser.add_argument("--asset-names", default="")
    parser.add_argument("--campaign-numbers", default="")
    parser.add_argument("--replace-existing-sequential", action="store_true")
    parser.add_argument("--clone-source", action="store_true", help="Clone the C08 MAXVOL campaign/adset shell, then attach new Drive creatives")
    parser.add_argument("--operational-date", default="")
    parser.add_argument("--post-discord", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(execute(parse_args()))
