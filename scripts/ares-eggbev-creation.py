#!/usr/bin/env python3
"""Deterministic Eggbev from-zero materializer for Campaign Engine v3.

The script never creates campaign objects itself. It performs intake, scoped media
preparation, manifest sealing, final-summary gating, and delegates every campaign
write/readback to ares-campaign-engine-v3.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ares_campaign_v3.eggbev_create import ACCOUNT_ID, build_eggbev_from_zero_manifest
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.media_registry import MediaNotReady, MediaRegistry
from ares_campaign_v3.prestage import AdAccountVideoUploader, PrestageService
from ares_campaign_v3.prevalidation import prevalidate_payload, validate_account_policy
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.transport import FakeBatchTransport

BASE = Path("/root/mgs-agent")
PROFILE = Path("/root/.hermes/profiles/ares")
ACCOUNT_PATH = BASE / "data/ares/meta-ads/accounts/1034081997659047.json"
OP_PATH = BASE / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
CONFIG_PATH = BASE / "data/ares/meta-ads/engine-v3/config.json"
REGISTRY_PATH = BASE / "data/ares/meta-ads/engine-v3/media-registry.json"
RECONCILIATION_PATH = BASE / "data/ares/meta-ads/reconciliation/Eggbev-US-CC-EN-BOT.json"
PAGE_SEQUENCE_PATH = BASE / "data/ares/meta-ads/operations/eggbev-page-sequences.json"
INVENTORY_PATH = BASE / "data/ares/creative-ops/inventory/assets.jsonl"
STATE_ROOT = BASE / "data/ares/meta-ads/state/eggbev-creation"
AUDIT_ROOT = BASE / "data/ares/meta-ads/audit/eggbev/creation"
WORK_ROOT = PROFILE / "work/eggbev-creation"
COMMON_PATH = BASE / "scripts/ares-eggbev-roas-common.py"
META_COMMON_PATH = BASE / "scripts/ares-meta-common.py"
DRIVE_MODULE_PATH = BASE / "scripts/ares-drive-upload-manual-inventory.py"
RECONCILER_PATH = BASE / "scripts/ares-eggbev-creative-reconcile.py"
ENGINE_CLI = BASE / "scripts/ares-campaign-engine-v3.py"
SANITIZER = BASE / "scripts/clean-creative-metadata.sh"
ET = ZoneInfo("America/New_York")
DRIVE_ID = "0AEwt4Ye690ocUk9PVA"
FINANCIAL_APPROVERS = {"Rodolfo", "Rodolfo Mattei", "Geizian"}


class CreationBlocked(RuntimeError):
    def __init__(self, stage: str, detail: Any):
        self.stage = stage
        self.detail = detail
        super().__init__(f"{stage}: {detail}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise CreationBlocked("schema", f"expected object in {path.name}")
    return value


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    finally:
        temp_path.unlink(missing_ok=True)


def load_inventory() -> list[dict[str, Any]]:
    return [json.loads(line) for line in INVENTORY_PATH.read_text().splitlines() if line.strip()]


def atomic_inventory(rows: list[dict[str, Any]]) -> None:
    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{INVENTORY_PATH.name}.", dir=INVENTORY_PATH.parent)
    temp_path = Path(temporary)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, INVENTORY_PATH)
        os.chmod(INVENTORY_PATH, 0o600)
    finally:
        temp_path.unlink(missing_ok=True)


def account_entry() -> dict[str, Any]:
    raw = load_json(ACCOUNT_PATH)
    return dict((raw.get("accounts") or [raw])[0])


def state_path(request_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", request_id).strip("-")
    if not safe:
        raise CreationBlocked("request_id", "invalid request id")
    return STATE_ROOT / f"{safe}.json"


def usd_minor_list(raw: str, campaigns: int) -> list[int]:
    values = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    if len(values) == 1:
        values *= campaigns
    if len(values) != campaigns:
        raise CreationBlocked("budget", "provide one USD budget or one value per campaign")
    result: list[int] = []
    for item in values:
        try:
            minor = int((Decimal(item) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        except (InvalidOperation, ValueError) as exc:
            raise CreationBlocked("budget", f"invalid USD value: {item}") from exc
        if minor <= 0:
            raise CreationBlocked("budget", "budget must be positive")
        result.append(minor)
    return result


def next_midnight() -> str:
    now = datetime.now(ET)
    return datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), tzinfo=ET).isoformat()


def graph_pages(meta, token: str, path: str, params: dict[str, Any], max_pages: int = 20) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    after = None
    for _ in range(max_pages):
        query = dict(params)
        if after:
            query["after"] = after
        status, payload, _ = meta.graph_get(path, token, query)
        if status != 200 or not isinstance(payload, dict):
            raise CreationBlocked("meta_get", {"path": path, "http": status})
        rows.extend(payload.get("data") or [])
        after = (((payload.get("paging") or {}).get("cursors") or {}).get("after"))
        if not after:
            return rows
    raise CreationBlocked("meta_get", f"pagination safety limit reached: {path}")


def live_page_and_token(page_token: str) -> tuple[dict[str, Any], Any, str]:
    account = account_entry()
    operation = load_json(OP_PATH)
    common = load_module(COMMON_PATH, "eggbev_creation_common")
    meta, smart_bidding, token, _ = common.load_runtime_modules(account)
    report_date = datetime.now(ET).date().isoformat()
    bundle = common.fetch_sb_bundle(smart_bidding, operation, report_date)
    rows = [row for row in (bundle.get("page_rows") or []) if str(row.get("UTM_CAMPAIGN") or "").lower() == page_token.lower()]
    page_ids = {str(row.get("FB_PAGE_ID") or "") for row in rows if row.get("FB_PAGE_ID")}
    if len(rows) != 1 or len(page_ids) != 1:
        raise CreationBlocked("page_reconciliation", {"page_rows": len(rows), "page_ids": len(page_ids)})
    page_id = next(iter(page_ids))
    status, page, _ = meta.graph_get(page_id, token, {"fields": "id,name,link"})
    if status != 200 or not isinstance(page, dict) or str(page.get("id")) != page_id:
        raise CreationBlocked("page_meta_readback", {"http": status})
    page["page_token"] = page_token
    page["leads_snapshot"] = rows[0].get("LEADS")
    page["messenger_source_ready"] = bundle.get("ready")
    return page, meta, token


def cross_account_page_history(meta, token: str, page_token: str) -> list[dict[str, Any]]:
    accounts = graph_pages(meta, token, "me/adaccounts", {"fields": "id,name,account_status", "limit": 100}, 10)
    accounts = [row for row in accounts if "eggbev-us-cc-en" in str(row.get("name") or "").lower()]
    filtering = json.dumps([{"field": "name", "operator": "CONTAIN", "value": page_token}], separators=(",", ":"))
    found: list[dict[str, Any]] = []
    for account in accounts:
        campaigns = graph_pages(
            meta,
            token,
            f"{account['id']}/campaigns",
            {"fields": "id,name,status,effective_status,configured_status", "filtering": filtering, "limit": 100},
            10,
        )
        for campaign in campaigns:
            if str(campaign.get("configured_status") or campaign.get("status") or "").upper() in {"DELETED", "ARCHIVED"}:
                continue
            found.append({"account_name": account.get("name"), **campaign})
    return found


def reserve_page_sequence(page_token: str, observed: set[int], request_id: str) -> int:
    PAGE_SEQUENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_path = PAGE_SEQUENCE_PATH.with_suffix(".json.lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        registry = load_json(PAGE_SEQUENCE_PATH)
        conflicts = registry.get("conflicting_page_tokens") or {}
        allocations = registry.setdefault("allocations", {})
        if page_token in conflicts:
            raise CreationBlocked("page_sequence", {"page_token": page_token, "conflicting_prefixes": conflicts[page_token]})
        allocated = allocations.get(page_token)
        if allocated:
            if str(allocated.get("request_id")) != request_id and allocated.get("status") == "RESERVED":
                raise CreationBlocked("page_sequence", "page token is reserved by another request")
            return int(allocated["page_sequence"])
        if len(observed) > 1:
            raise CreationBlocked("page_sequence", {"page_token": page_token, "observed": sorted(observed)})
        if len(observed) == 1:
            sequence = next(iter(observed))
        else:
            prior = [int(row.get("page_sequence") or 0) for row in allocations.values()]
            sequence = max([int(registry.get("max_observed_page_sequence") or 0), *prior]) + 1
        allocations[page_token] = {
            "page_sequence": sequence,
            "request_id": request_id,
            "status": "RESERVED",
            "reserved_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        atomic_json(PAGE_SEQUENCE_PATH, registry)
        return sequence


def naming_for_request(meta, token: str, page_token: str, count: int, request_id: str) -> tuple[int, list[int], list[dict[str, Any]]]:
    rows = cross_account_page_history(meta, token, page_token)
    pattern = re.compile(rf"^\s*(\d+)\s*-.*\({re.escape(page_token)}\).*?\bC(\d+)\b", re.I)
    page_numbers: set[int] = set()
    used_sequences: set[int] = set()
    for row in rows:
        match = pattern.search(str(row.get("name") or ""))
        if match:
            page_numbers.add(int(match.group(1)))
            used_sequences.add(int(match.group(2)))
    page_sequence = reserve_page_sequence(page_token, page_numbers, request_id)
    sequences: list[int] = []
    candidate = 1
    while len(sequences) < count:
        if candidate not in used_sequences:
            sequences.append(candidate)
        candidate += 1
    return page_sequence, sequences, rows


def load_reconciliation(required: int) -> dict[str, Any]:
    data = load_json(RECONCILIATION_PATH)
    if data.get("status") != "valid" or data.get("read_only") is not True:
        raise CreationBlocked("reconciliation", "valid read-only reconciliation is required")
    valid_until = datetime.fromisoformat(str(data.get("valid_until_utc") or "").replace("Z", "+00:00"))
    if valid_until <= datetime.now(timezone.utc):
        raise CreationBlocked("reconciliation", "reconciliation expired; rerun read-only reconciler")
    approved = [row for row in data.get("assets") or [] if row.get("approved_for_scoped_request") is True]
    if len(approved) < required:
        raise CreationBlocked("reconciliation", {"required": required, "approved": len(approved)})
    return data


def select_assets(reconciliation: dict[str, Any], request_id: str, required: int) -> list[dict[str, Any]]:
    approved = [row for row in reconciliation.get("assets") or [] if row.get("approved_for_scoped_request") is True]
    approved.sort(key=lambda row: hashlib.sha256(f"{request_id}|{row.get('asset_id')}".encode()).hexdigest())
    selected: list[dict[str, Any]] = []
    fingerprints: set[str] = set()
    for row in approved:
        fingerprint = str(row.get("perceptual_fingerprint") or row.get("clean_checksum") or row.get("asset_id"))
        if fingerprint in fingerprints:
            continue
        fingerprints.add(fingerprint)
        selected.append(row)
        if len(selected) == required:
            return selected
    raise CreationBlocked("asset_selection", {"required": required, "unique": len(selected)})


def reserve_inventory(selected: list[dict[str, Any]], request_id: str, authorized_by: str, audit_path: Path) -> None:
    rows = load_inventory()
    by_id = {str(row.get("asset_id")): row for row in selected}
    found: set[str] = set()
    stamp = datetime.now(timezone.utc).isoformat()
    for row in rows:
        asset_id = str(row.get("asset_id") or "")
        if asset_id not in by_id:
            continue
        expected = by_id[asset_id]
        if str(row.get("asset_drive_id") or "") != str(expected.get("asset_drive_id") or "") or str(row.get("clean_checksum") or "") != str(expected.get("clean_checksum") or ""):
            raise CreationBlocked("inventory_reservation", f"lineage drift for {asset_id}")
        existing_request = str(row.get("reservation_request_id") or "")
        if row.get("used_by") and not (row.get("used_by") == "ARES_IN_FLIGHT" and existing_request == request_id):
            raise CreationBlocked("inventory_reservation", f"asset became unavailable: {asset_id}")
        row.update({
            "reservation_status": "RESERVADO_PELO_ARES_REQUEST",
            "ares_eligible": False,
            "used_by": "ARES_IN_FLIGHT",
            "campaign_owner": "Ares",
            "reservation_request_id": request_id,
            "reservation_authorized_by": authorized_by,
            "reservation_authorized_at": stamp,
            "reservation_audit": str(audit_path),
            "last_reconciled_at": stamp,
        })
        found.add(asset_id)
    if found != set(by_id):
        raise CreationBlocked("inventory_reservation", "selected inventory rows disappeared")
    atomic_inventory(rows)


def drive_runtime(*, write: bool = False):
    reconciler = load_module(RECONCILER_PATH, "eggbev_creation_reconciler")
    drive_mod = load_module(DRIVE_MODULE_PATH, "eggbev_creation_drive")
    drive_mod.load_env()
    service_account = drive_mod.extract_service_account(drive_mod.get_op_item_json())
    if service_account.get("client_email") != "mgsagent@mgs-core-prod.iam.gserviceaccount.com" or service_account.get("project_id") != "mgs-core-prod":
        raise CreationBlocked("drive_identity", "canonical service account mismatch")
    if write:
        setattr(drive_mod, "SCOPES", "https://www.googleapis.com/auth/drive")
    token = drive_mod.get_access_token(service_account)
    drive = reconciler.drive_inventory(token)
    return reconciler, drive_mod, token, drive


def download_drive(token: str, row: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://www.googleapis.com/drive/v3/files/{row['id']}?" + urllib.parse.urlencode({"alt": "media", "supportsAllDrives": "true"})
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": "MGS-Ares-Eggbev-Create/1.0"})
    digest = hashlib.md5()
    size = 0
    with urllib.request.urlopen(request, timeout=240) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    if digest.hexdigest() != str(row.get("md5Checksum") or "") or size != int(row.get("size") or 0):
        destination.unlink(missing_ok=True)
        raise CreationBlocked("drive_download", f"MD5/size mismatch for {row.get('name')}")


def verify_clean(path: Path) -> str:
    result = subprocess.run([str(SANITIZER), "verify", str(path)], capture_output=True, text=True, timeout=180, check=False)
    if result.returncode != 0 or "clean: true" not in result.stdout:
        raise CreationBlocked("metadata", f"clean verification failed for {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_square(source: Path, destination: Path) -> None:
    raw = destination.with_suffix(".raw.mp4")
    result = subprocess.run([
        "ffmpeg", "-y", "-i", str(source), "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=1080:1080", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(raw),
    ], capture_output=True, text=True, timeout=600, check=False)
    if result.returncode != 0:
        raise CreationBlocked("square_render", result.stderr[-500:])
    clean = subprocess.run([str(SANITIZER), "clean", str(raw), "--out", str(destination), "--agent", "ares", "--json"], capture_output=True, text=True, timeout=300, check=False)
    raw.unlink(missing_ok=True)
    if clean.returncode != 0:
        raise CreationBlocked("square_sanitize", clean.stderr[-500:])
    verify_clean(destination)


def parse_ad_names(path: Path, required: int) -> list[str]:
    value = json.loads(path.read_text())
    names = value.get("ad_names") if isinstance(value, dict) else value
    if not isinstance(names, list) or len(names) != required:
        raise CreationBlocked("ad_names", f"expected exactly {required} ad names")
    return [str(item) for item in names]


def automatic_ad_names(selected: list[dict[str, Any]], creatives_per_campaign: int) -> list[str]:
    if creatives_per_campaign not in {3, 5}:
        raise CreationBlocked("ad_names", "automatic ad names require three or five creatives per campaign")
    names = []
    for index, row in enumerate(selected):
        filename = str(row.get("canonical_filename") or "").strip()
        if not filename:
            raise CreationBlocked("ad_names", "canonical filename is required for automatic ad naming")
        slot = (index % creatives_per_campaign) + 1
        names.append(f"AD {slot:02d} - {Path(filename).stem}")
    if len(set(names)) != len(names):
        raise CreationBlocked("ad_names", "automatic ad names are not unique within the request")
    return names


def build_summary(page: dict[str, Any], manifest: dict[str, Any], selected: list[dict[str, Any]]) -> dict[str, Any]:
    operation = load_json(OP_PATH)
    policy = operation["campaign_creation_policy"]
    return {
        "operation": "Eggbev-US-CC-EN-BOT",
        "account": "Eggbev-US-CC-EN-01-G006",
        "page": {"name": page.get("name"), "token": page.get("page_token"), "meta_readback": True, "leads_snapshot": page.get("leads_snapshot")},
        "status": "ACTIVE with future start_time",
        "start_time": manifest["campaigns"][0]["start_time"],
        "campaigns": [
            {"name": row["name"], "budget_usd": int(row["campaign_create"]["daily_budget"]) / 100, "adset": row["adset_name"], "ads": [ad["name"] for ad in row["ads"]]}
            for row in manifest["campaigns"]
        ],
        "assets": [row.get("canonical_filename") for row in selected],
        "copy": policy["copy_source_policy"]["template"],
        "messenger_template": policy["message_template"],
        "placements": policy["manual_placements_payload"],
        "tracking": manifest["campaigns"][0]["ads"][0]["creative_payload"]["url_tags"],
        "gates": ["Nicolas explicit OK on this exact summary", "Rodolfo/Geizian financial write approval", "Engine v3 --confirm-execute", "consolidated Meta readback"],
    }


def drive_file_readback(token: str, file_id: str) -> dict[str, Any]:
    params = urllib.parse.urlencode({"fields": "id,name,size,md5Checksum,driveId,parents,trashed", "supportsAllDrives": "true"})
    request = urllib.request.Request(
        f"https://www.googleapis.com/drive/v3/files/{file_id}?{params}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "MGS-Ares-Eggbev-Create/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def move_to_testing(token: str, file_id: str, ready_id: str, testing_id: str, expected: dict[str, Any]) -> dict[str, Any]:
    before = drive_file_readback(token, file_id)
    parents = set(str(value) for value in before.get("parents") or [])
    if testing_id not in parents:
        if ready_id not in parents:
            raise CreationBlocked("drive_postprocess", f"asset parent is neither READY nor TESTING: {file_id}")
        params = urllib.parse.urlencode({"addParents": testing_id, "removeParents": ready_id, "supportsAllDrives": "true", "fields": "id,name,size,md5Checksum,driveId,parents,trashed"})
        request = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?{params}",
            data=b"{}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "MGS-Ares-Eggbev-Create/1.0"},
            method="PATCH",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            json.loads(response.read())
    after = drive_file_readback(token, file_id)
    expected_drive = expected.get("drive_readback") or {}
    if after.get("driveId") != DRIVE_ID or after.get("trashed") or testing_id not in set(after.get("parents") or []):
        raise CreationBlocked("drive_postprocess", f"TESTING readback failed: {file_id}")
    if expected_drive.get("md5Checksum") and after.get("md5Checksum") != expected_drive.get("md5Checksum"):
        raise CreationBlocked("drive_postprocess", f"Drive MD5 changed: {file_id}")
    if expected_drive.get("size") and str(after.get("size")) != str(expected_drive.get("size")):
        raise CreationBlocked("drive_postprocess", f"Drive size changed: {file_id}")
    return after


def engine_assignments(engine_result: dict[str, Any], state: dict[str, Any]) -> list[dict[str, str]]:
    audit_path = Path(str(engine_result.get("audit_path") or ""))
    if not audit_path.is_file():
        raise CreationBlocked("postprocess", "Engine audit is missing")
    audit = load_json(audit_path)
    lane = (audit.get("lanes") or {}).get(ACCOUNT_ID) or {}
    bundles = sorted(lane.get("bundles") or [], key=lambda row: int(row.get("index") or 0))
    campaign_ids: list[str] = []
    adset_ids: list[str] = []
    creative_ids: list[str] = []
    ad_ids: list[str] = []
    for bundle in bundles:
        if bundle.get("status") != "COMPLETE":
            raise CreationBlocked("postprocess", "Engine bundle is not COMPLETE")
        campaign_ids.extend(str(value) for value in bundle.get("campaign_ids") or [])
        adset_ids.extend(str(value) for value in bundle.get("adset_ids") or [])
        creative_ids.extend(str(value) for value in bundle.get("creative_ids") or [])
        ad_ids.extend(str(value) for value in bundle.get("ad_ids") or [])
    selected = list(state.get("selected_assets") or [])
    campaigns = len(state.get("campaign_sequences") or [])
    if not campaigns or len(campaign_ids) != campaigns or len(adset_ids) != campaigns or len(ad_ids) != len(selected) or len(creative_ids) != len(selected):
        raise CreationBlocked("postprocess", "Engine audit identity counts do not match the selected lineage")
    ads_per_campaign = len(selected) // campaigns
    return [
        {"campaign_id": campaign_ids[index // ads_per_campaign], "adset_id": adset_ids[index // ads_per_campaign], "creative_id": creative_ids[index], "ad_id": ad_ids[index]}
        for index in range(len(selected))
    ]


def finalize_assets(state: dict[str, Any], engine_result: dict[str, Any]) -> dict[str, Any]:
    selected = list(state.get("selected_assets") or [])
    assignments = engine_assignments(engine_result, state)
    _, _, drive_token, drive = drive_runtime(write=True)
    ready_id = str(drive["ready"]["id"])
    testing_id = str(drive["testing"]["id"])
    drive_readbacks = [
        move_to_testing(drive_token, str(row["asset_drive_id"]), ready_id, testing_id, row)
        for row in selected
    ]
    registry = MediaRegistry(REGISTRY_PATH)
    media = [registry.require_ready(ACCOUNT_ID, str(row["asset_id"]), str(row["clean_checksum"])) for row in selected]
    rows = load_inventory()
    index_by_id = {str(row.get("asset_id")): index for index, row in enumerate(rows)}
    stamp = datetime.now(timezone.utc).isoformat()
    for selected_row, assignment, media_row, drive_row in zip(selected, assignments, media, drive_readbacks):
        asset_id = str(selected_row["asset_id"])
        inventory_index = index_by_id.get(asset_id)
        if inventory_index is None:
            raise CreationBlocked("postprocess", f"inventory row disappeared: {asset_id}")
        row = rows[inventory_index]
        if str(row.get("reservation_request_id") or "") != str(state["request_id"]):
            raise CreationBlocked("postprocess", f"reservation request drift: {asset_id}")
        row.update({
            "status": "02_TESTING",
            "reservation_status": "USED_BY_REQUEST",
            "ares_eligible": False,
            "used_by": str(state["request_id"]),
            "meta_account_id": ACCOUNT_ID,
            "meta_campaign_id": assignment["campaign_id"],
            "meta_adset_id": assignment["adset_id"],
            "meta_creative_id": assignment["creative_id"],
            "meta_ad_id": assignment["ad_id"],
            "meta_prestage_video_ids": [media_row["vertical_video_id"], media_row["square_video_id"]],
            "drive_folder": "02_TESTING",
            "drive_readback_after_use": drive_row,
            "used_at": stamp,
        })
        history = row.setdefault("test_history", [])
        event = {"request_id": str(state["request_id"]), **assignment, "used_at": stamp}
        if not any(isinstance(item, dict) and item.get("request_id") == event["request_id"] and item.get("ad_id") == event["ad_id"] for item in history):
            history.append(event)
    atomic_inventory(rows)
    return {"assets_finalized": len(selected), "drive_moves_confirmed": len(drive_readbacks), "inventory_status": "02_TESTING"}


def offline_smoke(output: Path | None) -> dict[str, Any]:
    temp = tempfile.TemporaryDirectory()
    registry = MediaRegistry(Path(temp.name) / "media.json")
    refs = []
    for index in range(9):
        asset_id = f"offline_eggbev_{index + 1:02d}"
        checksum = f"offline-checksum-{index + 1:02d}"
        registry.register(account_id=ACCOUNT_ID, asset_id=asset_id, checksum=checksum, vertical_video_id=f"v-{index + 1:02d}", square_video_id=f"s-{index + 1:02d}", ready=True, source="offline-smoke", upload_edge="ad_account_advideos", association_verified=True)
        refs.append({"asset_id": asset_id, "checksum": checksum})
    start = (datetime.now(ET) + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    payload = build_eggbev_from_zero_manifest(registry=registry, request_id="eggbev-offline-smoke", page_id="123456789012345", page_name="Amy Shook", page_token="pg_5024", page_sequence=162, campaign_sequences=[1, 2, 3], daily_budgets_minor=[5000, 5000, 5000], start_time=start, asset_refs=refs, ad_names=[f"AMY AD {index + 1:02d}" for index in range(9)])
    config = load_json(CONFIG_PATH)
    validate_account_policy(Manifest.from_dict(payload), config)
    sealed = prevalidate_payload(payload, registry)
    manifest = Manifest.from_dict(sealed)
    plan = CampaignEngine(config, transport_factory=lambda account: FakeBatchTransport(account)).dry_run(manifest)
    result = {"status": "OFFLINE_SMOKE_OK", "campaigns": len(manifest.campaigns), "ads": sum(len(row.ads) for row in manifest.campaigns), "manifest_digest": manifest.digest, "plan": plan["plan"], "network_calls": 0, "writes": 0}
    if output:
        atomic_json(output, {"manifest": sealed, "result": result})
    temp.cleanup()
    return result


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_scoped_release:
        raise CreationBlocked("authorization", "prepare requires --confirm-scoped-release")
    if not args.authorized_by:
        raise CreationBlocked("authorization", "authorized-by is required")
    required = args.campaign_count * args.creatives_per_campaign
    budgets = usd_minor_list(args.daily_budgets_usd, args.campaign_count)
    ad_names = parse_ad_names(args.ad_names_json, required) if args.ad_names_json else None
    request_state_path = state_path(args.request_id)
    audit_path = AUDIT_ROOT / f"{request_state_path.stem}.json"
    existing = load_json(request_state_path) if request_state_path.exists() else None
    if existing and existing.get("phase") in {"AWAITING_FINAL_APPROVAL", "EXECUTION_DEFERRED", "COMPLETE", "POSTPROCESS_PENDING"}:
        return {"status": existing["phase"], "request_id": args.request_id, "summary_digest": existing.get("summary_digest"), "summary": existing.get("summary")}

    page, meta, token = live_page_and_token(args.page_token)
    page_sequence, campaign_sequences, history = naming_for_request(meta, token, args.page_token, args.campaign_count, args.request_id)
    reconciliation = load_reconciliation(required)
    selected = select_assets(reconciliation, args.request_id, required)
    if ad_names is None:
        ad_names = automatic_ad_names(selected, args.creatives_per_campaign)
    reserve_inventory(selected, args.request_id, args.authorized_by, audit_path)
    state = existing or {
        "schema_version": 1,
        "request_id": args.request_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authorized_by": args.authorized_by,
        "authorization_scope": "scoped release/reconciliation/prestage/plan for this creation request; no campaign write before final gates",
        "selected_assets": selected,
        "page": page,
        "page_sequence": page_sequence,
        "campaign_sequences": campaign_sequences,
        "naming_history_matches": len(history),
        "budgets_minor": budgets,
        "ad_names": ad_names,
        "phase": "RESERVED_PRESTAGE_PENDING",
    }
    atomic_json(request_state_path, state)
    atomic_json(audit_path, state)

    reconciler, drive_mod, drive_token, drive = drive_runtime()
    drive_by_id = {str(row["id"]): row for row in drive["files"]}
    common = load_module(META_COMMON_PATH, "eggbev_creation_meta")
    uploader = AdAccountVideoUploader(common=common, user_token=token, account_id=ACCOUNT_ID, graph_version="v26.0", title_scan_pages=4, title_scan_page_size=25, association_scan_pages=4, association_scan_page_size=25)
    registry = MediaRegistry(REGISTRY_PATH)
    service = PrestageService(registry, uploader)
    workdir = WORK_ROOT / request_state_path.stem
    refs: list[dict[str, str]] = []
    processed_now = 0
    for selected_row in selected:
        asset_id = str(selected_row["asset_id"])
        checksum = str(selected_row["clean_checksum"])
        try:
            registry.require_ready(ACCOUNT_ID, asset_id, checksum)
            refs.append({"asset_id": asset_id, "checksum": checksum})
            continue
        except MediaNotReady:
            pass
        if processed_now >= args.max_assets_per_run:
            continue
        drive_row = drive_by_id.get(str(selected_row["asset_drive_id"]))
        if not drive_row:
            raise CreationBlocked("drive_readback", f"selected asset missing from READY: {asset_id}")
        vertical = workdir / f"{asset_id}-vertical.mp4"
        square = workdir / f"{asset_id}-square.mp4"
        if not vertical.exists():
            download_drive(drive_token, drive_row, vertical)
        actual_checksum = verify_clean(vertical)
        if actual_checksum != checksum:
            raise CreationBlocked("checksum", f"Drive/inventory checksum drift: {asset_id}")
        if not square.exists():
            make_square(vertical, square)
        service.prestage(account_id=ACCOUNT_ID, asset_id=asset_id, checksum=checksum, vertical_path=vertical, square_path=square)
        refs.append({"asset_id": asset_id, "checksum": checksum})
        processed_now += 1
        state.setdefault("prestage_completed_assets", []).append(asset_id)
        atomic_json(request_state_path, state)
    ready_refs = []
    for row in selected:
        asset_id = str(row["asset_id"])
        checksum = str(row["clean_checksum"])
        try:
            registry.require_ready(ACCOUNT_ID, asset_id, checksum)
            ready_refs.append({"asset_id": asset_id, "checksum": checksum})
        except MediaNotReady:
            pass
    if len(ready_refs) != required:
        state.update({"phase": "PRESTAGE_DEFERRED", "prestage_ready": len(ready_refs), "prestage_required": required, "automatic_recovery_required": True})
        atomic_json(request_state_path, state)
        atomic_json(audit_path, state)
        return {"status": "PRESTAGE_DEFERRED", "request_id": args.request_id, "ready": len(ready_refs), "required": required, "writes": {"campaign": 0, "media_uploads_possible": processed_now * 2}, "next_action": "rerun prepare with the same request_id after quota capacity is available"}

    manifest_payload = build_eggbev_from_zero_manifest(registry=registry, request_id=args.request_id, page_id=str(page["id"]), page_name=str(page["name"]), page_token=args.page_token, page_sequence=page_sequence, campaign_sequences=campaign_sequences, daily_budgets_minor=budgets, start_time=next_midnight(), asset_refs=ready_refs, ad_names=ad_names)
    config = load_json(CONFIG_PATH)
    validate_account_policy(Manifest.from_dict(manifest_payload), config)
    sealed = prevalidate_payload(manifest_payload, registry)
    manifest = Manifest.from_dict(sealed)
    plan = CampaignEngine(config, transport_factory=lambda account: FakeBatchTransport(account)).dry_run(manifest)
    manifest_path = AUDIT_ROOT / f"{request_state_path.stem}-manifest.json"
    atomic_json(manifest_path, sealed)
    summary = build_summary(page, sealed, selected)
    summary_digest = hashlib.sha256(json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    state.update({"phase": "AWAITING_FINAL_APPROVAL", "manifest_path": str(manifest_path), "manifest_digest": manifest.digest, "summary": summary, "summary_digest": summary_digest, "plan": plan, "campaign_writes": 0, "prepared_at_utc": datetime.now(timezone.utc).isoformat()})
    atomic_json(request_state_path, state)
    atomic_json(audit_path, state)
    shutil.rmtree(workdir, ignore_errors=True)
    return {"status": "AWAITING_FINAL_APPROVAL", "request_id": args.request_id, "summary_digest": summary_digest, "summary": summary, "plan": plan["plan"], "campaign_writes": 0}


def execute_request(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_nicolas_ok or not args.confirm_execute:
        raise CreationBlocked("approval", "Nicolas OK and --confirm-execute are required")
    if args.financial_approved_by not in FINANCIAL_APPROVERS:
        raise CreationBlocked("financial_gate", "Rodolfo or Geizian approval is required")
    path = state_path(args.request_id)
    state = load_json(path)
    if state.get("phase") not in {"AWAITING_FINAL_APPROVAL", "EXECUTION_DEFERRED", "POSTPROCESS_PENDING"}:
        raise CreationBlocked("state", f"request is not executable: {state.get('phase')}")
    if args.summary_digest != state.get("summary_digest"):
        raise CreationBlocked("approval", "summary digest mismatch")
    manifest_path = Path(str(state.get("manifest_path") or ""))
    manifest = load_json(manifest_path)
    if Manifest.from_dict(manifest).digest != state.get("manifest_digest"):
        raise CreationBlocked("manifest", "sealed manifest digest drift")
    command = ["python3", str(ENGINE_CLI), "execute", "--manifest", str(manifest_path), "--confirm-execute"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=1800, check=False)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"status": "FAILED", "message": "engine returned non-JSON output"}
    state["execution_approval"] = {"nicolas_ok": True, "summary_digest": args.summary_digest, "financial_approved_by": args.financial_approved_by, "confirmed_at_utc": datetime.now(timezone.utc).isoformat()}
    state["engine_result"] = payload
    if result.returncode != 0:
        state.update({"phase": "RECOVERY_PENDING", "automatic_recovery_required": True})
        atomic_json(path, state)
        raise CreationBlocked("engine", {"returncode": result.returncode, "status": payload.get("status"), "message": payload.get("message")})
    if payload.get("status") == "PARTIAL_DEFERRED_QUOTA":
        state.update({"phase": "EXECUTION_DEFERRED", "automatic_recovery_required": True})
    elif payload.get("status") in {"COMPLETE_FUTURE_ACTIVE", "COMPLETE_PAUSED"}:
        try:
            state["postprocess"] = finalize_assets(state, payload)
        except Exception as exc:
            state.update({
                "phase": "POSTPROCESS_PENDING",
                "automatic_recovery_required": True,
                "postprocess_error": {"type": type(exc).__name__, "message": str(exc)[:500]},
            })
            atomic_json(path, state)
            raise CreationBlocked("postprocess", state["postprocess_error"]) from exc
        state.pop("postprocess_error", None)
        state.update({"phase": "COMPLETE", "automatic_recovery_required": False, "completed_at_utc": datetime.now(timezone.utc).isoformat()})
        registry = load_json(PAGE_SEQUENCE_PATH)
        allocation = (registry.get("allocations") or {}).get(str(state["page"]["page_token"]))
        if allocation and allocation.get("request_id") == args.request_id:
            allocation["status"] = "COMMITTED"
            allocation["committed_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(PAGE_SEQUENCE_PATH, registry)
    else:
        state.update({"phase": "RECOVERY_PENDING", "automatic_recovery_required": True})
    atomic_json(path, state)
    return {"status": state["phase"], "request_id": args.request_id, "engine_status": payload.get("status"), "campaign_count": len(payload.get("campaign_ids") or []), "readback": payload.get("metrics"), "automatic_recovery_required": state.get("automatic_recovery_required")}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    smoke = sub.add_parser("offline-smoke")
    smoke.add_argument("--output", type=Path)
    status = sub.add_parser("status")
    status.add_argument("--request-id", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--request-id", required=True)
    prepare_parser.add_argument("--page-token", required=True)
    prepare_parser.add_argument("--campaign-count", type=int, required=True)
    prepare_parser.add_argument("--creatives-per-campaign", type=int, choices=[3, 5], required=True)
    prepare_parser.add_argument("--daily-budgets-usd", required=True)
    prepare_parser.add_argument("--ad-names-json", type=Path)
    prepare_parser.add_argument("--authorized-by", required=True)
    prepare_parser.add_argument("--confirm-scoped-release", action="store_true")
    prepare_parser.add_argument("--max-assets-per-run", type=int, default=3)
    execute_parser = sub.add_parser("execute")
    execute_parser.add_argument("--request-id", required=True)
    execute_parser.add_argument("--summary-digest", required=True)
    execute_parser.add_argument("--financial-approved-by", required=True)
    execute_parser.add_argument("--confirm-nicolas-ok", action="store_true")
    execute_parser.add_argument("--confirm-execute", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "offline-smoke":
            payload = offline_smoke(args.output)
        elif args.command == "status":
            payload = load_json(state_path(args.request_id))
        elif args.command == "prepare":
            if args.campaign_count < 1 or args.campaign_count > 100:
                raise CreationBlocked("campaign_count", "must be 1..100")
            if args.max_assets_per_run < 1 or args.max_assets_per_run > 5:
                raise CreationBlocked("max_assets_per_run", "must be 1..5")
            payload = prepare(args)
        else:
            payload = execute_request(args)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except CreationBlocked as exc:
        print(json.dumps({"status": "BLOCKED", "stage": exc.stage, "detail": exc.detail}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
