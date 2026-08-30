#!/usr/bin/env python3
"""Read-only Drive × Meta reconciliation for Eggbev CC_US_EN assets."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BASE = Path("/root/mgs-agent")
INVENTORY = BASE / "data/ares/creative-ops/inventory/assets.jsonl"
OUTPUT = BASE / "data/ares/meta-ads/reconciliation/Eggbev-US-CC-EN-BOT.json"
ACCOUNT_FILE = BASE / "data/ares/meta-ads/accounts/1034081997659047.json"
META_COMMON = BASE / "scripts/ares-meta-common.py"
DRIVE_MODULE = BASE / "scripts/ares-drive-upload-manual-inventory.py"
DRIVE_ID = "0AEwt4Ye690ocUk9PVA"
FOLDER_MIME = "application/vnd.google-apps.folder"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_account() -> dict[str, Any]:
    raw = json.loads(ACCOUNT_FILE.read_text())
    return dict((raw.get("accounts") or [raw])[0])


def drive_request(token: str, url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": "MGS-Ares-Eggbev-Reconcile/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def drive_children(token: str, parent_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        params = {
            "q": f"'{parent_id}' in parents and trashed=false",
            "fields": "nextPageToken,files(id,name,mimeType,createdTime,modifiedTime,size,md5Checksum,driveId,parents,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive),videoMediaMetadata(width,height,durationMillis))",
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "orderBy": "name_natural",
        }
        if page_token:
            params["pageToken"] = page_token
        data = drive_request(token, "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params))
        rows.extend(data.get("files") or [])
        page_token = data.get("nextPageToken")
        if not page_token:
            return rows


def one_folder(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    found = [row for row in rows if row.get("name") == name and row.get("mimeType") == FOLDER_MIME]
    if len(found) != 1:
        raise RuntimeError(f"expected one Drive folder {name}; got {len(found)}")
    return found[0]


def drive_inventory(token: str) -> dict[str, Any]:
    root = drive_request(token, f"https://www.googleapis.com/drive/v3/files/{DRIVE_ID}?" + urllib.parse.urlencode({"fields": "id,name,driveId,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive)", "supportsAllDrives": "true"}))
    caps = root.get("capabilities") or {}
    if root.get("driveId") != DRIVE_ID or root.get("trashed") or not all(caps.get(key) for key in ("canDownload", "canEdit", "canMoveItemWithinDrive")):
        raise RuntimeError("canonical Drive root/capabilities mismatch")
    creatives = one_folder(drive_children(token, DRIVE_ID), "CRIATIVOS")
    operation = one_folder(drive_children(token, creatives["id"]), "CC_US_EN")
    video = one_folder(drive_children(token, operation["id"]), "VID")
    ready = one_folder(drive_children(token, video["id"]), "01_READY")
    testing = one_folder(drive_children(token, video["id"]), "02_TESTING")
    files = [row for row in drive_children(token, ready["id"]) if row.get("mimeType") != FOLDER_MIME]
    return {"root": root, "operation": operation, "ready": ready, "testing": testing, "files": files}


def graph_pages(meta, token: str, path: str, fields: str, *, max_rows: int | None = None, page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    after = None
    for _ in range(100):
        params: dict[str, Any] = {"fields": fields, "limit": min(100, max(1, page_size))}
        if after:
            params["after"] = after
        status, payload, _ = meta.graph_get(path, token, params)
        if status != 200 or not isinstance(payload, dict):
            raise RuntimeError(f"Meta GET {path} failed http={status}")
        rows.extend(payload.get("data") or [])
        if max_rows is not None and len(rows) >= max_rows:
            return rows[:max_rows]
        after = (((payload.get("paging") or {}).get("cursors") or {}).get("after"))
        if not after:
            return rows
    raise RuntimeError(f"Meta pagination exceeded safety limit for {path}")


def meta_video_titles(meta, token: str, limit_per_account: int) -> dict[str, Any]:
    accounts = graph_pages(meta, token, "me/adaccounts", "id,name,account_status")
    accounts = [row for row in accounts if "eggbev-us-cc-en" in str(row.get("name") or "").lower()]
    videos: list[dict[str, Any]] = []
    for account in accounts:
        rows = graph_pages(
            meta,
            token,
            f"{account['id']}/advideos",
            "id,title,status,created_time",
            max_rows=limit_per_account,
            page_size=25,
        )
        for row in rows:
            row["account_id"] = str(account["id"]).removeprefix("act_")
            row["account_name"] = account.get("name")
        videos.extend(rows)
    return {"accounts": accounts, "videos": videos, "limit_per_account": limit_per_account}


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def candidate_markers(row: dict[str, Any]) -> set[str]:
    values = [
        row.get("asset_id"),
        row.get("canonical_filename"),
        Path(str(row.get("canonical_filename") or "")).stem,
        row.get("original_filename"),
        Path(str(row.get("original_filename") or "")).stem,
        row.get("clean_checksum"),
        str(row.get("clean_checksum") or "")[:12],
    ]
    return {norm(item) for item in values if len(norm(item)) >= 8}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--required", type=int, default=9)
    parser.add_argument("--valid-seconds", type=int, default=21600)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--meta-video-limit-per-account", type=int, default=100)
    args = parser.parse_args()
    if args.required < 1 or args.required > 500:
        parser.error("required must be 1..500")

    drive_mod = load_module(DRIVE_MODULE, "eggbev_drive_identity")
    drive_mod.load_env()
    service_account = drive_mod.extract_service_account(drive_mod.get_op_item_json())
    if service_account.get("client_email") != "mgsagent@mgs-core-prod.iam.gserviceaccount.com" or service_account.get("project_id") != "mgs-core-prod":
        raise RuntimeError("canonical Drive service account mismatch")
    drive_token = drive_mod.get_access_token(service_account)
    drive = drive_inventory(drive_token)
    live_by_id = {str(row["id"]): row for row in drive["files"]}

    meta = load_module(META_COMMON, "eggbev_meta_reconcile")
    account = load_account()
    token_item = str(account.get("token_1password_item") or "").strip()
    if not token_item:
        raise RuntimeError("account has no canonical Meta token reference")
    token, _ = meta.get_token_from_1password(item_name=token_item)
    meta_snapshot = meta_video_titles(meta, token, max(25, args.meta_video_limit_per_account))
    title_rows = [(row, norm(row.get("title"))) for row in meta_snapshot["videos"]]
    used_video_ids = {str(row.get("id")) for row in meta_snapshot["videos"] if row.get("id")}

    inventory_rows = [json.loads(line) for line in INVENTORY.read_text().splitlines() if line.strip()]
    candidates = [
        row for row in inventory_rows
        if str(row.get("vertical") or "").upper() == "CC"
        and str(row.get("country") or "").upper() == "US"
        and str(row.get("language") or "").upper() == "EN"
        and row.get("format") == "VID"
        and row.get("status") == "01_READY"
        and row.get("metadata_clean") is True
    ]
    fingerprint_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        fingerprint_groups[str(row.get("perceptual_fingerprint") or row.get("clean_checksum") or row.get("asset_id"))].append(row)
    duplicate_assets = {
        str(row.get("asset_id"))
        for group in fingerprint_groups.values()
        for row in sorted(group, key=lambda item: (str(item.get("first_seen_at") or ""), str(item.get("asset_id") or "")))[1:]
    }

    assets: list[dict[str, Any]] = []
    for row in candidates:
        conflicts: list[str] = []
        drive_row = live_by_id.get(str(row.get("asset_drive_id") or ""))
        if not drive_row:
            conflicts.append("missing_from_drive_ready")
        else:
            if drive_row.get("driveId") != DRIVE_ID or drive_row.get("trashed"):
                conflicts.append("drive_identity_invalid")
            if str(drive_row.get("md5Checksum") or "") != str(row.get("clean_md5") or row.get("asset_md5") or drive_row.get("md5Checksum") or ""):
                conflicts.append("drive_md5_mismatch")
            if not (drive_row.get("capabilities") or {}).get("canDownload"):
                conflicts.append("drive_download_forbidden")
        if row.get("used_by") or row.get("meta_ad_id") or row.get("meta_campaign_id"):
            conflicts.append("inventory_already_used")
        known_ids = {str(item) for item in (row.get("meta_video_ids") or []) if item}
        if row.get("meta_video_id"):
            known_ids.add(str(row["meta_video_id"]))
        if known_ids & used_video_ids:
            conflicts.append("known_meta_video_id_present")
        markers = candidate_markers(row)
        title_matches = [video for video, normalized in title_rows if normalized and any(marker in normalized for marker in markers)]
        if title_matches:
            conflicts.append("meta_video_title_lineage_match")
        if str(row.get("asset_id") or "") in duplicate_assets:
            conflicts.append("duplicate_perceptual_lineage")
        assets.append({
            "asset_id": row.get("asset_id"),
            "canonical_filename": row.get("canonical_filename"),
            "asset_drive_id": row.get("asset_drive_id"),
            "clean_checksum": row.get("clean_checksum"),
            "perceptual_fingerprint": row.get("perceptual_fingerprint"),
            "angle": row.get("angle"),
            "orientation": row.get("p_orient"),
            "first_seen_at": row.get("first_seen_at"),
            "reservation_status": row.get("reservation_status"),
            "requires_scoped_manager_release": row.get("reservation_status") == "RESERVADO_PELO_GESTOR" or row.get("ares_eligible") is not True,
            "drive_readback": ({key: drive_row.get(key) for key in ("id", "name", "size", "md5Checksum", "driveId", "parents", "videoMediaMetadata")} if drive_row else None),
            "meta_title_matches": [{"account_name": item.get("account_name"), "title": item.get("title")} for item in title_matches[:10]],
            "conflicts": sorted(set(conflicts)),
            "approved_for_scoped_request": not conflicts,
        })

    approved = [row for row in assets if row["approved_for_scoped_request"]]
    approved.sort(key=lambda row: (str(row.get("angle") or "ZZZ"), str(row.get("first_seen_at") or ""), str(row.get("perceptual_fingerprint") or "")))
    now = datetime.now(timezone.utc)
    manifest = {
        "schema_version": 1,
        "status": "valid" if len(approved) >= args.required else "insufficient",
        "operation": "Eggbev-US-CC-EN-BOT",
        "account_id": "1034081997659047",
        "generated_at_utc": now.isoformat(),
        "valid_until_utc": (now + timedelta(seconds=max(300, args.valid_seconds))).isoformat(),
        "read_only": True,
        "writes": {"meta": 0, "drive": 0, "inventory": 0, "reservations": 0},
        "drive": {
            "service_account": service_account.get("client_email"),
            "project_id": service_account.get("project_id"),
            "drive_id": drive["root"].get("driveId"),
            "ready_files": len(drive["files"]),
        },
        "meta": {
            "accounts_scanned": [row.get("name") for row in meta_snapshot["accounts"]],
            "advideos_scanned": len(meta_snapshot["videos"]),
            "advideos_limit_per_account": meta_snapshot["limit_per_account"],
            "coverage": "bounded_recent_window_per_account",
            "matching_policy": "known Meta IDs plus asset/checksum/canonical/original markers in ad-account video titles",
            "limitation": "no downloadable Meta visual fingerprint was generated; scoped manager release plus title/ID/current-inventory checks remain mandatory",
        },
        "summary": {
            "required": args.required,
            "inventory_candidates": len(candidates),
            "approved_for_scoped_request": len(approved),
            "conflicted": len(assets) - len(approved),
            "manager_release_required": sum(bool(row["requires_scoped_manager_release"]) for row in approved),
        },
        "assets": assets,
        "approved_selection_order": [row["asset_id"] for row in approved],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": manifest["status"], **manifest["summary"], "drive_ready_files": len(drive["files"]), "meta_advideos_scanned": len(meta_snapshot["videos"]), "writes": manifest["writes"]}, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "valid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
