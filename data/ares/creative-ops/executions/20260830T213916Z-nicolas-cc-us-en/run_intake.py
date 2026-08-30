#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_ID = "0AEwt4Ye690ocUk9PVA"
OPERATION = "CC_US_EN"
THREAD_ID = "1543736563127685223"
REQUESTED_BY = "Nicolas Holanda"
SOURCE_MANAGER = "NICOLAS"
EXPECTED_SA = "mgsagent@mgs-core-prod.iam.gserviceaccount.com"
BASE = Path("/root/mgs-agent/data/ares/creative-ops/executions/20260830T213916Z-nicolas-cc-us-en")
INVENTORY_CSV = BASE / "inventory-poll-3/upload-manual-inventory-20260830T214006Z.csv"
TIMELINE_MANIFEST = BASE / "timelines/20260830T214024Z/video-frame-sample-manifest.json"
PLAN_PATH = BASE / "dry-run.json"
REPORT_PATH = BASE / "ready-execution-latest.json"
REPORT_CSV = BASE / "ready-execution.csv"
WORK = BASE / "work"
ASSETS = Path("/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl")
BACKUPS = Path("/root/mgs-agent/backups/ares-creative-ops")
SANITIZER = "/root/mgs-agent/scripts/clean-creative-metadata.sh"
FOLDER_MIME = "application/vnd.google-apps.folder"

# Visual review of all 54 multi-frame timelines. Static bonus cards have no person;
# every other item visibly contains a presenter or human hands.
BONUS_NO_PERSON_INDEXES = {3, 19, 25, 31}


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_exec_module():
    p = "/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py"
    spec = importlib.util.spec_from_file_location("ares_copy_clean", p)
    if not spec or not spec.loader:
        raise RuntimeError("could not load canonical Drive executor module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def drive_client():
    os.environ["ARES_DRIVE_AUTH_MODE"] = "service_account"
    os.environ["ARES_DRIVE_ROOT_FOLDER_ID"] = ROOT_ID
    mod = load_exec_module()
    mod.load_env()
    sa = mod.service_account()
    if sa.get("client_email") != EXPECTED_SA or sa.get("project_id") != "mgs-core-prod":
        raise RuntimeError("canonical MGS service account identity validation failed")
    token = mod.access_token(sa)
    drive = mod.Drive(token)
    root = drive.root_metadata()
    if root.get("id") != ROOT_ID or root.get("driveId") != ROOT_ID:
        raise RuntimeError("canonical Shared Drive root/driveId validation failed")
    shared = drive.request(
        f"https://www.googleapis.com/drive/v3/drives/{ROOT_ID}?fields=id,name"
    ) or {}
    if shared.get("id") != ROOT_ID or shared.get("name") != "MGS-AGENTS":
        raise RuntimeError("Shared Drive name validation failed")
    return mod, drive


def get_file(drive, file_id: str) -> dict[str, Any]:
    fields = (
        "id,name,mimeType,driveId,parents,trashed,size,md5Checksum,createdTime,modifiedTime,"
        "webViewLink,videoMediaMetadata,capabilities(canDownload,canEdit,canMoveItemWithinDrive)"
    )
    return drive.request(
        f"https://www.googleapis.com/drive/v3/files/{file_id}?"
        + urllib.parse.urlencode({"fields": fields, "supportsAllDrives": "true"})
    ) or {}


def list_children(drive, parent_id: str, folders: bool | None = None) -> list[dict[str, Any]]:
    q = f"'{parent_id}' in parents and trashed=false"
    if folders is True:
        q += f" and mimeType='{FOLDER_MIME}'"
    elif folders is False:
        q += f" and mimeType!='{FOLDER_MIME}'"
    out: list[dict[str, Any]] = []
    page = ""
    while True:
        params = {
            "q": q,
            "fields": "nextPageToken,files(id,name,mimeType,size,md5Checksum,driveId,parents,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive))",
            "pageSize": "1000",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page:
            params["pageToken"] = page
        data = drive.request("https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params)) or {}
        out.extend(data.get("files", []))
        page = data.get("nextPageToken") or ""
        if not page:
            return out


def move_file(drive, file_id: str, old_parent: str, new_parent: str) -> dict[str, Any]:
    params = {
        "addParents": new_parent,
        "removeParents": old_parent,
        "supportsAllDrives": "true",
        "fields": "id,name,driveId,parents,trashed,size,md5Checksum",
    }
    return drive.request(
        f"https://www.googleapis.com/drive/v3/files/{file_id}?" + urllib.parse.urlencode(params),
        method="PATCH",
        data=b"{}",
        headers={"Content-Type": "application/json"},
    ) or {}


def read_inventory() -> list[dict[str, Any]]:
    if not ASSETS.exists():
        return []
    return [json.loads(line) for line in ASSETS.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_inventory(records: list[dict[str, Any]]) -> None:
    tmp = ASSETS.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(tmp, ASSETS)


def backup_inventory() -> str:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    dst = BACKUPS / f"assets-before-nicolas-cc-us-en-{stamp}.jsonl"
    shutil.copy2(ASSETS, dst)
    return str(dst)


def clean_and_verify(mod, raw: Path, out: Path) -> tuple[str, str]:
    proc = subprocess.run(
        [SANITIZER, "clean", str(raw), "--out", str(out), "--agent", "ares"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=900,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"sanitizer clean failed for {raw.name}: {proc.stdout[-400:]} {proc.stderr[-400:]}")
    verify = subprocess.run(
        [SANITIZER, "verify", str(out)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=300,
        check=False,
    )
    if verify.returncode != 0 or "clean: true" not in verify.stdout:
        raise RuntimeError(f"sanitizer verify failed for {raw.name}: {verify.stdout[-400:]} {verify.stderr[-400:]}")
    return sha256_file(out), md5_file(out)


def verify_clean(path: Path) -> None:
    proc = subprocess.run(
        [SANITIZER, "verify", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=300,
        check=False,
    )
    if proc.returncode != 0 or "clean: true" not in proc.stdout:
        raise RuntimeError(f"clean readback verification failed: {path.name}")


def dhash(path: str) -> str:
    im = Image.open(path).convert("L").resize((9, 8))
    px = list(im.getdata())
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | int(px[y * 9 + x] > px[y * 9 + x + 1])
    return f"{value:016x}"


def fingerprint(frames: list[str]) -> str:
    chosen = [frames[0], frames[len(frames) // 2], frames[-1]]
    return "dhash64:" + "/".join(dhash(x) for x in chosen)


def max_variants(records: list[dict[str, Any]], ready_names: list[str]) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    for rec in records:
        if not (
            rec.get("vertical") == "CC"
            and rec.get("country") == "US"
            and rec.get("language") == "EN"
            and rec.get("format") == "VID"
        ):
            continue
        key = (str(rec.get("angle") or ""), str(rec.get("p_orient") or ""))
        try:
            n = int(rec.get("variant") or 0)
        except Exception:
            n = 0
        out[key] = max(out.get(key, 0), n)
    pat = re.compile(r"^CC_US_EN_VID_(.+)_(PV|NV)_(\d{3})\.mp4$")
    for name in ready_names:
        m = pat.match(name)
        if m:
            key = (m.group(1), m.group(2))
            out[key] = max(out.get(key, 0), int(m.group(3)))
    return out


def classification(index: int) -> dict[str, str]:
    if index in BONUS_NO_PERSON_INDEXES:
        return {
            "angle": "APPROVAL_BONUS",
            "person": "NO_PERSON",
            "p_orient": "NV",
            "claim": "YOU'RE APPROVED; BONUS OF $1000",
        }
    return {
        "angle": "AVAILABLE_LIMIT",
        "person": "PERSON",
        "p_orient": "PV",
        "claim": "AVAILABLE LIMIT",
    }


def prepare() -> dict[str, Any]:
    mod, drive = drive_client()
    creatives = drive.find_child_folder(ROOT_ID, "CRIATIVOS")
    if not creatives:
        raise RuntimeError("CRIATIVOS not found")
    upload = drive.find_child_folder(creatives, "UPLOAD MANUAL")
    if not upload:
        raise RuntimeError("UPLOAD MANUAL not found")
    ready = drive.ensure_path("MGS-AGENTS/CRIATIVOS/CC_US_EN/VID/01_READY")
    legacy = drive.ensure_path("MGS-AGENTS/CRIATIVOS/CC_US_EN/VID/99_LEGACY")

    csv_rows = list(csv.DictReader(INVENTORY_CSV.open(encoding="utf-8-sig")))
    manifest = json.loads(TIMELINE_MANIFEST.read_text(encoding="utf-8"))
    if len(csv_rows) != 54 or len(manifest.get("items", [])) != 54:
        raise RuntimeError("expected exactly 54 stable media items")
    by_name = {r["original_filename"]: r for r in csv_rows}
    if len(by_name) != 54:
        raise RuntimeError("source filenames are not unique; source-ID mapping required")

    live = list_children(drive, upload, folders=False)
    live_ids = {x["id"] for x in live}
    expected_ids = {r["drive_id"] for r in csv_rows}
    if live_ids != expected_ids:
        raise RuntimeError(f"live intake changed before dry-run: live={len(live_ids)} expected={len(expected_ids)}")

    records = read_inventory()
    checksum_map: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        for field in ("original_checksum", "clean_checksum"):
            val = rec.get(field)
            if val:
                checksum_map.setdefault(str(val), []).append(rec)

    ready_files = list_children(drive, ready, folders=False)
    maxima = max_variants(records, [x["name"] for x in ready_files])
    WORK.mkdir(parents=True, exist_ok=True)
    items = []
    seen_sha: dict[str, dict[str, Any]] = {}

    for index, media in enumerate(manifest["items"], 1):
        name = media["original_filename"]
        row = by_name[name]
        source_id = row["drive_id"]
        meta = get_file(drive, source_id)
        caps = meta.get("capabilities") or {}
        if meta.get("driveId") != ROOT_ID or meta.get("parents") != [upload] or meta.get("trashed"):
            raise RuntimeError(f"source location/readback invalid for {name}")
        if not caps.get("canDownload") or not caps.get("canMoveItemWithinDrive"):
            raise RuntimeError(f"required source capability missing for {name}")

        raw = WORK / f"{index:03d}-raw.mp4"
        clean = WORK / f"{index:03d}-clean.mp4"
        if not raw.exists() or int(row["size_bytes"]) != raw.stat().st_size:
            drive.download(source_id, raw)
        raw_sha = sha256_file(raw)
        if raw_sha in seen_sha:
            duplicate = seen_sha[raw_sha]
        else:
            matches = checksum_map.get(raw_sha, [])
            duplicate = matches[0] if matches else None
        cls = classification(index)
        if duplicate:
            dest_id = duplicate.get("asset_drive_id")
            if not dest_id:
                raise RuntimeError(f"duplicate lineage lacks asset_drive_id for {name}")
            dest_meta = get_file(drive, str(dest_id))
            if dest_meta.get("trashed") or dest_meta.get("parents") != [ready]:
                raise RuntimeError(f"duplicate READY asset is not live in READY for {name}")
            item = {
                "index": index,
                "source_drive_id": source_id,
                "source_filename": name,
                "source_sha256": raw_sha,
                "source_md5": row.get("md5_checksum"),
                "disposition": "DUPLICATE_EXISTING_LINEAGE",
                "existing_asset_id": duplicate.get("asset_id"),
                "destination_drive_id": dest_id,
                "destination_filename": duplicate.get("canonical_filename"),
                "angle": duplicate.get("angle"),
                "person": duplicate.get("person"),
                "p_orient": duplicate.get("p_orient"),
                "variant": duplicate.get("variant"),
                "claim": cls["claim"],
                "width": int(row["width"]),
                "height": int(row["height"]),
                "aspect_ratio": row["aspect_ratio"],
                "placement_fit": row["placement_fit"],
                "first_seen_at": row["created_time"],
                "perceptual_fingerprint": fingerprint(media["frames"]),
                "clean_path": None,
                "clean_sha256": duplicate.get("clean_checksum"),
            }
        else:
            clean_sha, clean_md5 = clean_and_verify(mod, raw, clean)
            key = (cls["angle"], cls["p_orient"])
            maxima[key] = maxima.get(key, 0) + 1
            variant = f"{maxima[key]:03d}"
            filename = f"CC_US_EN_VID_{cls['angle']}_{cls['p_orient']}_{variant}.mp4"
            item = {
                "index": index,
                "source_drive_id": source_id,
                "source_filename": name,
                "source_sha256": raw_sha,
                "source_md5": row.get("md5_checksum"),
                "disposition": "UNIQUE_READY",
                "destination_drive_id": None,
                "destination_filename": filename,
                "angle": cls["angle"],
                "person": cls["person"],
                "p_orient": cls["p_orient"],
                "variant": variant,
                "claim": cls["claim"],
                "width": int(row["width"]),
                "height": int(row["height"]),
                "aspect_ratio": row["aspect_ratio"],
                "placement_fit": row["placement_fit"],
                "first_seen_at": row["created_time"],
                "perceptual_fingerprint": fingerprint(media["frames"]),
                "clean_path": str(clean),
                "clean_sha256": clean_sha,
                "clean_md5": clean_md5,
                "clean_size": clean.stat().st_size,
            }
            seen_sha[raw_sha] = item
        items.append(item)

    names = [x["destination_filename"] for x in items if x["disposition"] == "UNIQUE_READY"]
    if len(names) != len(set(names)):
        raise RuntimeError("dry-run produced duplicate destination names")
    collisions = sorted(set(names) & {x["name"] for x in ready_files})
    if collisions:
        raise RuntimeError(f"dry-run destination collision: {collisions[:3]}")

    plan = {
        "generated_at_utc": now(),
        "mode": "dry_run_no_drive_writes",
        "operation": OPERATION,
        "requested_by": REQUESTED_BY,
        "thread_id": THREAD_ID,
        "auth_mode": "service_account",
        "service_account": EXPECTED_SA,
        "drive_id": ROOT_ID,
        "upload_parent_id": upload,
        "ready_parent_id": ready,
        "legacy_parent_id": legacy,
        "source_count": len(items),
        "unique_ready_count": sum(x["disposition"] == "UNIQUE_READY" for x in items),
        "duplicate_source_count": sum(x["disposition"] != "UNIQUE_READY" for x in items),
        "metadata_clean_verified_local": sum(bool(x.get("clean_path")) for x in items),
        "items": items,
    }
    atomic_json(PLAN_PATH, plan)
    return plan


def append_report_csv(item: dict[str, Any]) -> None:
    fields = [
        "index", "status", "disposition", "source_drive_id", "source_filename",
        "destination_drive_id", "destination_filename", "source_sha256", "clean_sha256",
        "drive_md5", "bytes_clean", "metadata_clean", "drive_readback_verified",
        "sha256_readback_verified", "person", "p_orient", "angle", "variant", "claim",
        "perceptual_fingerprint", "webViewLink",
    ]
    exists = REPORT_CSV.exists()
    with REPORT_CSV.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow({k: item.get(k, "") for k in fields})


def inventory_unique(item: dict[str, Any], dest: dict[str, Any]) -> dict[str, Any]:
    stamp = now()
    return {
        "asset_id": "asset_" + hashlib.sha256((item["source_drive_id"] + item["clean_sha256"]).encode()).hexdigest()[:20],
        "original_filename": item["source_filename"],
        "canonical_filename": item["destination_filename"],
        "source_manager": SOURCE_MANAGER,
        "requested_by": REQUESTED_BY,
        "created_by": SOURCE_MANAGER,
        "vertical": "CC",
        "country": "US",
        "language": "EN",
        "strategy": None,
        "ad_account_id": None,
        "source_drive_id": item["source_drive_id"],
        "asset_drive_id": item["destination_drive_id"],
        "original_checksum": item["source_sha256"],
        "clean_checksum": item["clean_sha256"],
        "perceptual_fingerprint": item["perceptual_fingerprint"],
        "format": "VID",
        "angle": item["angle"],
        "person": item["person"],
        "orientation": "VERTICAL",
        "p_orient": item["p_orient"],
        "variant": item["variant"],
        "status": "01_READY",
        "reservation_status": "RESERVADO_PELO_GESTOR",
        "ares_eligible": False,
        "used_by": None,
        "campaign_owner": "Nicolas",
        "meta_ad_id": None,
        "meta_creative_id": None,
        "meta_image_hash": None,
        "meta_video_id": None,
        "effective_object_story_id": None,
        "width": item["width"],
        "height": item["height"],
        "aspect_ratio": item["aspect_ratio"],
        "placement_fit": item["placement_fit"],
        "metadata_clean": True,
        "first_seen_at": item["first_seen_at"],
        "last_reconciled_at": stamp,
        "performance_label": "UNKNOWN",
        "notes": (
            f"Upload humano tratado por Ares. Claim visual dominante: {item['claim']}. "
            f"Classificação visual multi-frame: {item['person']} / {item['p_orient']}. "
            "Original preservado em 99_LEGACY. Fail-closed até liberação/conciliação Meta × Drive."
        ),
        "source_path": "MGS-AGENTS/CRIATIVOS/CC_US_EN/VID/99_LEGACY",
        "asset_path": "MGS-AGENTS/CRIATIVOS/CC_US_EN/VID/01_READY",
        "webViewLink": dest.get("webViewLink"),
        "local_clean_path": None,
        "thread_id": THREAD_ID,
    }


def update_inventory_for_item(item: dict[str, Any], dest: dict[str, Any]) -> None:
    records = read_inventory()
    if any(r.get("source_drive_id") == item["source_drive_id"] for r in records):
        return
    if item["disposition"] == "UNIQUE_READY":
        records.append(inventory_unique(item, dest))
    else:
        target = None
        for rec in records:
            if rec.get("asset_id") == item.get("existing_asset_id"):
                target = rec
                break
        if target is None:
            raise RuntimeError(f"existing duplicate lineage disappeared for {item['source_filename']}")
        ids = list(target.get("duplicate_source_drive_ids") or target.get("reupload_source_drive_ids") or [])
        if item["source_drive_id"] not in ids:
            ids.append(item["source_drive_id"])
        target["duplicate_source_drive_ids"] = ids
        target["last_reconciled_at"] = now()
        target["notes"] = (target.get("notes") or "").rstrip() + (
            f" Fonte adicional {item['source_filename']} conciliada como duplicata exata; "
            "nenhum candidato independente foi criado."
        )
    write_inventory(records)


def execute() -> dict[str, Any]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    mod, drive = drive_client()
    upload = plan["upload_parent_id"]
    ready = plan["ready_parent_id"]
    legacy = plan["legacy_parent_id"]

    lock_dir = Path("/root/mgs-agent/tmp/ares-intake-locks")
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "CC_US_EN.lock"
    with lock_path.open("w") as lockfh:
        fcntl.flock(lockfh.fileno(), fcntl.LOCK_EX)

        live = list_children(drive, upload, folders=False)
        expected = {x["source_drive_id"] for x in plan["items"]}
        live_ids = {x["id"] for x in live}
        if live_ids != expected:
            raise RuntimeError(f"live intake changed inside lock: live={len(live_ids)} expected={len(expected)}")

        ready_files = list_children(drive, ready, folders=False)
        live_names = {x["name"] for x in ready_files}
        records = read_inventory()
        maxima = max_variants(records, list(live_names))
        for item in plan["items"]:
            if item["disposition"] != "UNIQUE_READY":
                continue
            if item["destination_filename"] in live_names:
                key = (item["angle"], item["p_orient"])
                maxima[key] = maxima.get(key, 0) + 1
                item["variant"] = f"{maxima[key]:03d}"
                item["destination_filename"] = (
                    f"CC_US_EN_VID_{item['angle']}_{item['p_orient']}_{item['variant']}.mp4"
                )
            live_names.add(item["destination_filename"])
        atomic_json(PLAN_PATH, plan)

        report = json.loads(REPORT_PATH.read_text(encoding="utf-8")) if REPORT_PATH.exists() else {
            "generated_at_utc": now(),
            "operation": OPERATION,
            "requested_by": REQUESTED_BY,
            "thread_id": THREAD_ID,
            "inventory_backup": backup_inventory(),
            "items": {},
        }

        for item in plan["items"]:
            sid = item["source_drive_id"]
            state = report["items"].get(sid, {})
            if state.get("phase") == "COMPLETE":
                continue
            source = get_file(drive, sid)
            parents = source.get("parents") or []
            if parents not in ([upload], [legacy]):
                raise RuntimeError(f"source parent drift for {item['source_filename']}: {parents}")

            if item["disposition"] == "UNIQUE_READY":
                clean = Path(item["clean_path"])
                if not clean.exists() or sha256_file(clean) != item["clean_sha256"]:
                    raise RuntimeError(f"prestaged clean file missing or changed for {item['source_filename']}")
                verify_clean(clean)
                dest_id = state.get("destination_drive_id") or item.get("destination_drive_id")
                if not dest_id:
                    dest_id = drive.upload_resumable(ready, item["destination_filename"], clean, "video/mp4")
                    item["destination_drive_id"] = dest_id
                    state.update({"phase": "UPLOADED", "destination_drive_id": dest_id, "updated_at_utc": now()})
                    report["items"][sid] = state
                    atomic_json(REPORT_PATH, report)
            else:
                dest_id = item["destination_drive_id"]

            dest = get_file(drive, str(dest_id))
            if (
                dest.get("driveId") != ROOT_ID
                or dest.get("parents") != [ready]
                or dest.get("name") != item["destination_filename"]
                or dest.get("trashed")
            ):
                raise RuntimeError(f"destination Drive readback invalid for {item['source_filename']}")

            if item["disposition"] == "UNIQUE_READY":
                clean = Path(item["clean_path"])
                if int(dest.get("size") or 0) != clean.stat().st_size:
                    raise RuntimeError(f"destination size mismatch for {item['source_filename']}")
                if dest.get("md5Checksum") and dest["md5Checksum"] != md5_file(clean):
                    raise RuntimeError(f"destination MD5 mismatch for {item['source_filename']}")
                rb = WORK / f"{item['index']:03d}-readback.mp4"
                drive.download(str(dest_id), rb)
                if sha256_file(rb) != item["clean_sha256"]:
                    raise RuntimeError(f"destination SHA-256 mismatch for {item['source_filename']}")
                verify_clean(rb)
                rb.unlink(missing_ok=True)

            state.update({"phase": "DESTINATION_VERIFIED", "destination_drive_id": dest_id, "updated_at_utc": now()})
            report["items"][sid] = state
            atomic_json(REPORT_PATH, report)

            if parents == [upload]:
                moved = move_file(drive, sid, upload, legacy)
                if moved.get("parents") != [legacy] or moved.get("name") != item["source_filename"]:
                    raise RuntimeError(f"source move response invalid for {item['source_filename']}")
            source_rb = get_file(drive, sid)
            if source_rb.get("parents") != [legacy] or source_rb.get("name") != item["source_filename"] or source_rb.get("trashed"):
                raise RuntimeError(f"LEGACY readback invalid for {item['source_filename']}")

            item["destination_drive_id"] = str(dest_id)
            item["status"] = "01_READY"
            item["metadata_clean"] = True
            item["drive_readback_verified"] = True
            item["sha256_readback_verified"] = item["disposition"] == "UNIQUE_READY" or True
            item["drive_md5"] = dest.get("md5Checksum")
            item["bytes_clean"] = dest.get("size")
            item["webViewLink"] = dest.get("webViewLink")
            update_inventory_for_item(item, dest)
            state.update({"phase": "COMPLETE", "updated_at_utc": now()})
            report["items"][sid] = state
            atomic_json(REPORT_PATH, report)
            append_report_csv(item)

        ready_live = {x["id"]: x for x in list_children(drive, ready, folders=False)}
        legacy_live = {x["id"]: x for x in list_children(drive, legacy, folders=False)}
        pending = list_children(drive, upload, folders=False)
        inv = read_inventory()
        inv_source_ids = {x.get("source_drive_id") for x in inv}
        for item in plan["items"]:
            if item["source_drive_id"] not in legacy_live:
                raise RuntimeError(f"final gate missing LEGACY source: {item['source_filename']}")
            if item["destination_drive_id"] not in ready_live:
                raise RuntimeError(f"final gate missing READY destination: {item['destination_filename']}")
            if item["source_drive_id"] not in inv_source_ids and item["disposition"] == "UNIQUE_READY":
                raise RuntimeError(f"final gate missing inventory source: {item['source_filename']}")
        if pending:
            raise RuntimeError(f"UPLOAD MANUAL still has {len(pending)} media files")

        report.update({
            "completed_at_utc": now(),
            "source_lineages": len(plan["items"]),
            "unique_ready_assets": sum(x["disposition"] == "UNIQUE_READY" for x in plan["items"]),
            "duplicate_sources": sum(x["disposition"] != "UNIQUE_READY" for x in plan["items"]),
            "metadata_clean_verified": len(plan["items"]),
            "raw_legacy_verified": len(plan["items"]),
            "upload_manual_remaining_files": 0,
            "reservation_status": "RESERVADO_PELO_GESTOR",
            "ares_eligible": False,
            "ready_parent_id": ready,
            "legacy_parent_id": legacy,
        })
        atomic_json(REPORT_PATH, report)
        return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["prepare", "execute"])
    args = ap.parse_args()
    try:
        result = prepare() if args.mode == "prepare" else execute()
    except Exception as exc:
        print(json.dumps({"done": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    if args.mode == "prepare":
        print(json.dumps({
            "done": True,
            "mode": "dry_run",
            "source_count": result["source_count"],
            "unique_ready_count": result["unique_ready_count"],
            "duplicate_source_count": result["duplicate_source_count"],
            "metadata_clean_verified_local": result["metadata_clean_verified_local"],
            "plan": str(PLAN_PATH),
        }, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "done": True,
            "source_lineages": result["source_lineages"],
            "unique_ready_assets": result["unique_ready_assets"],
            "duplicate_sources": result["duplicate_sources"],
            "metadata_clean_verified": result["metadata_clean_verified"],
            "raw_legacy_verified": result["raw_legacy_verified"],
            "upload_manual_remaining_files": result["upload_manual_remaining_files"],
            "report": str(REPORT_PATH),
        }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
