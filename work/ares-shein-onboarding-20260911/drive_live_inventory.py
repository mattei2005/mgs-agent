#!/usr/bin/env python3
from __future__ import annotations

import collections
import csv
import importlib.util
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT_ID = "0AEwt4Ye690ocUk9PVA"
DRIVE_ID = ROOT_ID
FOLDER_MIME = "application/vnd.google-apps.folder"
WORK = Path("/root/mgs-agent/work/ares-shein-onboarding-20260911")
INVENTORY = Path("/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl")
HELPER = Path("/root/mgs-agent/scripts/ares-drive-upload-manual-inventory.py")


def load_helper():
    spec = importlib.util.spec_from_file_location("ares_drive_readonly", HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical Drive helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request_json(token: str, path: str, params: dict[str, str]) -> dict:
    url = "https://www.googleapis.com/drive/v3" + path + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + token, "User-Agent": "mgs-ares-live-inventory/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def list_children(token: str, parent_id: str) -> list[dict]:
    output: list[dict] = []
    page_token = ""
    while True:
        params = {
            "q": f"'{parent_id}' in parents and trashed=false",
            "fields": (
                "nextPageToken,files(id,name,mimeType,size,md5Checksum,createdTime,modifiedTime,"
                "parents,driveId,capabilities(canDownload,canEdit,canMoveItemWithinDrive,canTrash),"
                "imageMediaMetadata(width,height),videoMediaMetadata(width,height,durationMillis))"
            ),
            "pageSize": "1000",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "orderBy": "name_natural",
        }
        if page_token:
            params["pageToken"] = page_token
        data = request_json(token, "/files", params)
        output.extend(data.get("files", []))
        page_token = data.get("nextPageToken", "")
        if not page_token:
            return output


def one_folder(token: str, parent_id: str, name: str) -> dict:
    rows = [
        item
        for item in list_children(token, parent_id)
        if item.get("mimeType") == FOLDER_MIME and item.get("name") == name
    ]
    if len(rows) != 1:
        raise RuntimeError(f"folder {name!r}: expected 1, found {len(rows)}")
    return rows[0]


def load_inventory_rows() -> list[dict]:
    rows: list[dict] = []
    for line in INVENTORY.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("vertical") == "SHEIN" and row.get("country") == "US" and row.get("language") == "EN":
            rows.append(row)
    return rows


def main() -> int:
    helper = load_helper()
    helper.load_env()
    service_account = helper.extract_service_account(helper.get_op_item_json())
    if service_account.get("client_email") != "mgsagent@mgs-core-prod.iam.gserviceaccount.com":
        raise RuntimeError("unexpected service account identity")
    if service_account.get("project_id") != "mgs-core-prod":
        raise RuntimeError("unexpected GCP project")
    token = helper.get_access_token(service_account)

    root = request_json(
        token,
        f"/files/{ROOT_ID}",
        {
            "fields": "id,name,driveId,capabilities(canAddChildren,canEdit,canModifyContent)",
            "supportsAllDrives": "true",
        },
    )
    drive_resource = request_json(
        token,
        f"/drives/{DRIVE_ID}",
        {"fields": "id,name,capabilities(canAddChildren,canManageMembers,canRename)"},
    )
    if root.get("id") != ROOT_ID or root.get("driveId") != DRIVE_ID:
        safe_root = {key: root.get(key) for key in ("id", "name", "driveId")}
        raise RuntimeError(f"canonical Shared Drive root validation failed: {safe_root}")
    if drive_resource.get("id") != DRIVE_ID or drive_resource.get("name") != "MGS-AGENTS":
        safe_drive = {key: drive_resource.get(key) for key in ("id", "name")}
        raise RuntimeError(f"canonical Shared Drive resource validation failed: {safe_drive}")

    creatives = one_folder(token, ROOT_ID, "CRIATIVOS")
    operation = one_folder(token, creatives["id"], "SHEIN_US_EN")

    queue = collections.deque([(operation["id"], "MGS-AGENTS/CRIATIVOS/SHEIN_US_EN")])
    folders: list[dict] = []
    files: list[dict] = []
    while queue:
        parent_id, parent_path = queue.popleft()
        for item in list_children(token, parent_id):
            if item.get("driveId") != DRIVE_ID:
                raise RuntimeError(f"unexpected driveId for {item.get('name')!r}")
            row = {**item, "path": parent_path + "/" + item["name"]}
            if item.get("mimeType") == FOLDER_MIME:
                folders.append(row)
                queue.append((item["id"], row["path"]))
            else:
                files.append(row)

    inventory_rows = load_inventory_rows()
    by_asset: dict[str, list[dict]] = collections.defaultdict(list)
    by_source: dict[str, list[dict]] = collections.defaultdict(list)
    for row in inventory_rows:
        if row.get("asset_drive_id"):
            by_asset[row["asset_drive_id"]].append(row)
        if row.get("source_drive_id"):
            by_source[row["source_drive_id"]].append(row)

    for item in files:
        roles: list[dict] = []
        for role_name, candidates in (("asset", by_asset.get(item["id"], [])), ("source", by_source.get(item["id"], []))):
            for row in candidates:
                roles.append(
                    {
                        "role": role_name,
                        "asset_id": row.get("asset_id"),
                        "product_type": row.get("product_type"),
                        "status": row.get("status"),
                        "reservation_status": row.get("reservation_status"),
                        "ares_eligible": row.get("ares_eligible"),
                        "canonical_filename": row.get("canonical_filename"),
                        "original_filename": row.get("original_filename"),
                        "source_manager": row.get("source_manager"),
                    }
                )
        item["inventory_roles"] = roles

    WORK.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    report = {
        "generated_at_utc": now,
        "auth_mode": "service_account",
        "service_account_identity_verified": True,
        "project_id_verified": True,
        "shared_drive": {
            "id": drive_resource.get("id"),
            "driveId": root.get("driveId"),
            "name": drive_resource.get("name"),
            "root_file_name": root.get("name"),
            "capabilities": root.get("capabilities"),
            "drive_capabilities": drive_resource.get("capabilities"),
        },
        "operation_folder": {
            "id": operation["id"],
            "name": operation["name"],
            "driveId": operation.get("driveId"),
        },
        "folder_count": len(folders),
        "file_count": len(files),
        "folders": folders,
        "files": files,
    }
    (WORK / "drive-live-inventory.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fields = [
        "id", "name", "path", "mimeType", "size", "md5Checksum", "createdTime", "modifiedTime",
        "driveId", "product_type", "lineage_role", "asset_id", "source_manager", "inventory_status",
        "reservation_status", "ares_eligible",
    ]
    with (WORK / "drive-live-inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in files:
            role = (item.get("inventory_roles") or [{}])[0]
            writer.writerow(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "path": item["path"],
                    "mimeType": item["mimeType"],
                    "size": item.get("size"),
                    "md5Checksum": item.get("md5Checksum"),
                    "createdTime": item.get("createdTime"),
                    "modifiedTime": item.get("modifiedTime"),
                    "driveId": item.get("driveId"),
                    "product_type": role.get("product_type"),
                    "lineage_role": role.get("role"),
                    "asset_id": role.get("asset_id"),
                    "source_manager": role.get("source_manager"),
                    "inventory_status": role.get("status"),
                    "reservation_status": role.get("reservation_status"),
                    "ares_eligible": role.get("ares_eligible"),
                }
            )

    by_format_status: collections.Counter[tuple[str, str]] = collections.Counter()
    lineage_roles: collections.Counter[str] = collections.Counter()
    ready_video_products: collections.Counter[str] = collections.Counter()
    ready_video_source_manager: collections.Counter[str] = collections.Counter()
    unmatched: list[dict] = []
    for item in files:
        parts = item["path"].split("/")
        media_format = next((part for part in parts if part in {"IMG", "VID"}), "OTHER")
        status = next(
            (
                part
                for part in parts
                if part in {"01_READY", "02_TESTING", "03_TESTED", "04_WINNERS", "05_REJECTED", "99_LEGACY"}
            ),
            "OTHER",
        )
        by_format_status[(media_format, status)] += 1
        roles = item.get("inventory_roles", [])
        if any(role["role"] == "asset" for role in roles):
            lineage_role = "asset"
        elif any(role["role"] == "source" for role in roles):
            lineage_role = "source"
        else:
            lineage_role = "unmatched"
            unmatched.append({"id": item["id"], "name": item["name"], "path": item["path"]})
        lineage_roles[lineage_role] += 1
        if media_format == "VID" and status == "01_READY":
            asset_role = next((role for role in roles if role["role"] == "asset"), {})
            ready_video_products[asset_role.get("product_type") or "UNMATCHED"] += 1
            ready_video_source_manager[asset_role.get("source_manager") or "UNKNOWN"] += 1

    summary = {
        "generated_at_utc": now,
        "files_physical_total": len(files),
        "folders_total": len(folders),
        "by_format_status": {
            f"{key[0]}/{key[1]}": value for key, value in sorted(by_format_status.items())
        },
        "by_lineage_role": dict(lineage_roles),
        "ready_video_products": dict(ready_video_products.most_common()),
        "ready_video_source_manager": dict(ready_video_source_manager.most_common()),
        "unreconciled_count": len(unmatched),
        "unreconciled": unmatched,
    }
    (WORK / "drive-live-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
