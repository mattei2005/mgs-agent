#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path
from typing import Any

BASE = Path("/root/mgs-agent/data/ares/creative-ops/executions/20260901T195657Z-kelly-cc-us-en-thread-1544435564688707625")
CORE = BASE / "run_valid_intake.py"
PLAN_PATH = BASE / "dry-run.json"
REPORT_PATH = BASE / "ready-execution-latest.json"
REPORT_CSV = BASE / "ready-execution.csv"
ASSETS = Path("/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl")
ROOT_ID = "0AEwt4Ye690ocUk9PVA"
DUP_ID = "1LmQ60JL8jyQ6yDieGwkzy09PJpIxO0PI"
DUP_NAME = "5_21 US_CC_EN_01-09  - IA - Story (INGLES) .mp4"
TARGET_NAME = "10_22 US_CC_EN_31-08 - IA - Story (INGLES) .mp4"
REJECT_ID = "12Aiw5djmBRpi2PsclfJNHs-njuzxf6V_"
REJECT_NAME = "Record_2026_08_31_22_04_13_66.mp4"
THREAD_ID = "1544435564688707625"


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def atomic_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_core():
    spec = importlib.util.spec_from_file_location("kelly_cc_us_en_core", CORE)
    if not spec or not spec.loader:
        raise RuntimeError("could not load run-local intake module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def media_hash(path: Path, stream: str) -> str:
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", stream, "-c", "copy", "-f", "hash", "-hash", "sha256", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=300,
        check=False,
    )
    if proc.returncode != 0 or "SHA256=" not in proc.stdout:
        raise RuntimeError(f"media essence hash failed for {path.name} {stream}: {proc.stderr[-300:]}")
    return proc.stdout.strip()


def read_records() -> list[dict[str, Any]]:
    return [json.loads(x) for x in ASSETS.read_text(encoding="utf-8").splitlines() if x.strip()]


def write_records(records: list[dict[str, Any]]) -> None:
    tmp = ASSETS.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(tmp, ASSETS)


def append_csv(row: dict[str, Any]) -> None:
    fields = [
        "index", "status", "disposition", "source_drive_id", "source_filename",
        "destination_drive_id", "destination_filename", "source_sha256", "clean_sha256",
        "drive_md5", "bytes_clean", "metadata_clean", "drive_readback_verified",
        "sha256_readback_verified", "person", "p_orient", "angle", "variant", "claim",
        "perceptual_fingerprint", "webViewLink",
    ]
    with REPORT_CSV.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writerow({k: row.get(k, "") for k in fields})


def strict_folders(core, drive) -> dict[str, str]:
    creatives = drive.find_child_folder(ROOT_ID, "CRIATIVOS")
    operation = drive.find_child_folder(creatives, "CC_US_EN") if creatives else None
    vid = drive.find_child_folder(operation, "VID") if operation else None
    if not vid:
        raise RuntimeError("canonical CC_US_EN/VID hierarchy not found")
    out = {name: drive.find_child_folder(vid, name) for name in ("01_READY", "05_REJECTED", "99_LEGACY")}
    if not all(out.values()):
        raise RuntimeError("canonical READY/REJECTED/LEGACY folders must already exist")
    upload = drive.find_child_folder(creatives, "UPLOAD MANUAL")
    if not upload:
        raise RuntimeError("canonical UPLOAD MANUAL not found")
    return {"upload": upload, "ready": out["01_READY"], "rejected": out["05_REJECTED"], "legacy": out["99_LEGACY"]}


def main() -> int:
    core = load_core()
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    mod, drive = core.drive_client()
    folders = strict_folders(core, drive)
    lock_dir = Path("/root/mgs-agent/tmp/ares-intake-locks")
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / "CC_US_EN.lock").open("w") as lockfh:
        fcntl.flock(lockfh.fileno(), fcntl.LOCK_EX)

        pending = {x["id"]: x for x in core.list_children(drive, folders["upload"], folders=False)}
        if set(pending) != {DUP_ID, REJECT_ID}:
            raise RuntimeError(f"special-source live drift before finalization: {len(pending)} pending")

        target = next(x for x in plan["items"] if x["source_filename"] == TARGET_NAME)
        target_state = report["items"].get(target["source_drive_id"], {})
        if target_state.get("phase") != "COMPLETE" or not target_state.get("destination_drive_id"):
            raise RuntimeError("READY target lineage is not complete for duplicate reconciliation")
        dest_id = str(target_state["destination_drive_id"])
        dest = core.get_file(drive, dest_id)
        if dest.get("parents") != [folders["ready"]] or dest.get("name") != target["destination_filename"] or dest.get("trashed"):
            raise RuntimeError("duplicate target READY readback invalid")

        target_raw = BASE / "work" / f"{target['index']:03d}-raw.mp4"
        duplicate_raw = BASE / "work/special-duplicate-raw.mp4"
        if not target_raw.exists() or not duplicate_raw.exists():
            raise RuntimeError("prestaged duplicate comparison files missing")
        target_v = media_hash(target_raw, "0:v:0")
        duplicate_v = media_hash(duplicate_raw, "0:v:0")
        target_a = media_hash(target_raw, "0:a:0?")
        duplicate_a = media_hash(duplicate_raw, "0:a:0?")
        if (target_v, target_a) != (duplicate_v, duplicate_a):
            raise RuntimeError("visual duplicate failed exact audio/video essence reconciliation")
        dup_sha = hashlib.sha256(duplicate_raw.read_bytes()).hexdigest()
        if pending[DUP_ID].get("md5Checksum") and pending[DUP_ID]["md5Checksum"] != core.md5_file(duplicate_raw):
            raise RuntimeError("duplicate source download MD5 mismatch")

        moved_dup = core.move_file(drive, DUP_ID, folders["upload"], folders["legacy"])
        if moved_dup.get("parents") != [folders["legacy"]] or moved_dup.get("name") != DUP_NAME:
            raise RuntimeError("duplicate source move response invalid")
        dup_rb = core.get_file(drive, DUP_ID)
        if dup_rb.get("parents") != [folders["legacy"]] or dup_rb.get("name") != DUP_NAME or dup_rb.get("trashed"):
            raise RuntimeError("duplicate source LEGACY readback invalid")

        reject_meta = core.get_file(drive, REJECT_ID)
        if reject_meta.get("parents") != [folders["upload"]] or reject_meta.get("name") != REJECT_NAME or reject_meta.get("trashed"):
            raise RuntimeError("rejected source pre-move readback invalid")
        moved_reject = core.move_file(drive, REJECT_ID, folders["upload"], folders["rejected"])
        if moved_reject.get("parents") != [folders["rejected"]] or moved_reject.get("name") != REJECT_NAME:
            raise RuntimeError("rejected source move response invalid")
        reject_rb = core.get_file(drive, REJECT_ID)
        if reject_rb.get("parents") != [folders["rejected"]] or reject_rb.get("name") != REJECT_NAME or reject_rb.get("trashed"):
            raise RuntimeError("rejected source Drive readback invalid")

        records = read_records()
        target_record = next((r for r in records if r.get("source_drive_id") == target["source_drive_id"]), None)
        if not target_record:
            raise RuntimeError("target inventory record missing")
        duplicate_ids = list(target_record.get("duplicate_source_drive_ids") or [])
        if DUP_ID not in duplicate_ids:
            duplicate_ids.append(DUP_ID)
        target_record["duplicate_source_drive_ids"] = duplicate_ids
        duplicate_names = list(target_record.get("duplicate_original_filenames") or [])
        if DUP_NAME not in duplicate_names:
            duplicate_names.append(DUP_NAME)
        target_record["duplicate_original_filenames"] = duplicate_names
        target_record["last_reconciled_at"] = now()
        target_record["notes"] = (target_record.get("notes") or "").rstrip() + (
            f" Fonte adicional {DUP_NAME} conciliada como mesma mídia por hashes exatos dos streams de vídeo e áudio; nenhum candidato independente foi criado."
        )

        rejected_record = next((r for r in records if r.get("source_drive_id") == REJECT_ID), None)
        if rejected_record is None:
            rejected_record = {
                "asset_id": "asset_" + hashlib.sha256((REJECT_ID + REJECT_NAME).encode()).hexdigest()[:20],
                "original_filename": REJECT_NAME,
                "canonical_filename": None,
                "source_manager": "KELLY",
                "requested_by": "Kelly Nice",
                "created_by": "KELLY",
                "vertical": "CC",
                "country": "US",
                "language": "EN",
                "strategy": None,
                "ad_account_id": None,
                "source_drive_id": REJECT_ID,
                "asset_drive_id": None,
                "original_checksum": None,
                "clean_checksum": None,
                "perceptual_fingerprint": None,
                "format": "VID",
                "angle": "UNKNOWN",
                "person": "NO_PERSON",
                "orientation": "HORIZONTAL",
                "p_orient": None,
                "variant": None,
                "status": "05_REJECTED",
                "reservation_status": "RESERVADO_PELO_GESTOR",
                "ares_eligible": False,
                "used_by": None,
                "campaign_owner": "Kelly",
                "meta_ad_id": None,
                "meta_creative_id": None,
                "meta_image_hash": None,
                "meta_video_id": None,
                "effective_object_story_id": None,
                "width": 2504,
                "height": 924,
                "aspect_ratio": "2504:924",
                "placement_fit": "UNKNOWN",
                "metadata_clean": False,
                "first_seen_at": "2026-09-01T02:08:11.555Z",
                "last_reconciled_at": now(),
                "performance_label": "REJECTED_TECHNICAL",
                "notes": "Gravação de tela/dashboard, não contém material criativo de cartão utilizável. Evidência: frames locais em 20/50/80/final e thumbnail independente do Google Drive mostram apenas interfaces tabulares; nenhum candidato READY criado.",
                "source_path": "MGS-AGENTS/CRIATIVOS/CC_US_EN/VID/05_REJECTED",
                "asset_path": None,
                "webViewLink": reject_rb.get("webViewLink"),
                "local_clean_path": None,
                "thread_id": THREAD_ID,
            }
            records.append(rejected_record)
        write_records(records)

        duplicate_report = {
            "index": 13,
            "status": "01_READY",
            "disposition": "DUPLICATE_BATCH_SOURCE",
            "source_drive_id": DUP_ID,
            "source_filename": DUP_NAME,
            "destination_drive_id": dest_id,
            "destination_filename": target["destination_filename"],
            "source_sha256": dup_sha,
            "clean_sha256": target["clean_sha256"],
            "drive_md5": dest.get("md5Checksum"),
            "bytes_clean": dest.get("size"),
            "metadata_clean": True,
            "drive_readback_verified": True,
            "sha256_readback_verified": True,
            "person": "PERSON",
            "p_orient": "PV",
            "angle": "AVAILABLE_LIMIT",
            "variant": target["variant"],
            "claim": "AVAILABLE LIMIT: $12,566",
            "perceptual_fingerprint": target["perceptual_fingerprint"],
            "webViewLink": dest.get("webViewLink"),
        }
        rejected_report = {
            "index": 14,
            "status": "05_REJECTED",
            "disposition": "REJECTED_TECHNICAL_NON_CREATIVE_SCREEN_RECORDING",
            "source_drive_id": REJECT_ID,
            "source_filename": REJECT_NAME,
            "metadata_clean": False,
            "drive_readback_verified": True,
            "sha256_readback_verified": False,
            "person": "NO_PERSON",
            "p_orient": "",
            "angle": "UNKNOWN",
            "claim": "NON_CREATIVE_SCREEN_RECORDING",
        }
        append_csv(duplicate_report)
        append_csv(rejected_report)
        report["items"][DUP_ID] = {"phase": "COMPLETE", "destination_drive_id": dest_id, "disposition": "DUPLICATE_BATCH_SOURCE", "updated_at_utc": now()}
        report["items"][REJECT_ID] = {"phase": "COMPLETE", "destination_drive_id": None, "disposition": "REJECTED_TECHNICAL_NON_CREATIVE_SCREEN_RECORDING", "updated_at_utc": now()}

        pending_after = core.list_children(drive, folders["upload"], folders=False)
        if pending_after:
            raise RuntimeError(f"UPLOAD MANUAL still has {len(pending_after)} files")
        records_after = read_records()
        target_after = next(r for r in records_after if r.get("source_drive_id") == target["source_drive_id"])
        rejected_after = next(r for r in records_after if r.get("source_drive_id") == REJECT_ID)
        if DUP_ID not in (target_after.get("duplicate_source_drive_ids") or []):
            raise RuntimeError("duplicate inventory linkage missing after write")
        if rejected_after.get("status") != "05_REJECTED" or rejected_after.get("ares_eligible") is not False:
            raise RuntimeError("rejected inventory fail-closed gate invalid")

        report.update({
            "completed_at_utc": now(),
            "source_lineages": 14,
            "unique_ready_assets": 12,
            "duplicate_sources": 1,
            "rejected_technical": 1,
            "metadata_clean_verified": 12,
            "raw_legacy_verified": 13,
            "sources_archived": 13,
            "sources_rejected": 1,
            "upload_manual_remaining_files": 0,
            "reservation_status": "RESERVADO_PELO_GESTOR",
            "ares_eligible": False,
            "ready_parent_id": folders["ready"],
            "legacy_parent_id": folders["legacy"],
            "rejected_parent_id": folders["rejected"],
            "duplicate_media_essence": {"video": target_v, "audio": target_a},
            "special_items": [duplicate_report, rejected_report],
        })
        atomic_json(REPORT_PATH, report)

    print(json.dumps({
        "done": True,
        "source_lineages": 14,
        "unique_ready_assets": 12,
        "duplicate_sources": 1,
        "rejected_technical": 1,
        "metadata_clean_verified": 12,
        "raw_legacy_verified": 13,
        "sources_rejected": 1,
        "upload_manual_remaining_files": 0,
        "report": str(REPORT_PATH),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
