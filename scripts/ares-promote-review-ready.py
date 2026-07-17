#!/usr/bin/env python3
"""Promote cleaned Ares review assets from 00_REVIEW to 01_READY_CANDIDATE.

Moves/renames the existing cleaned Drive copy. Does not touch RAW/UPLOAD_CANVAS.
Uses the canonical MGS Service Account route through the shared Drive helper.
No local user credential cache or fallback is supported.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

EXECUTOR = Path("/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py")
DEFAULT_QUEUE = Path("/root/mgs-agent/data/ares/creative-inventory/final-organization-review/final-review-promote-to-ready-queue-20260615T031500Z.csv")
DEFAULT_REPORT = Path("/root/mgs-agent/data/ares/creative-inventory/final-organization-review/final-review-promote-to-ready-report-20260615T031500Z.csv")
FIELDS = [
    "ts_utc",
    "status",
    "source_review_drive_id",
    "target_drive_id",
    "old_name",
    "new_name",
    "target_folder",
    "error",
]
VARIANT_RE = re.compile(r"_(\d{3})\.[^.]+$")
BAD_VARIANT_RE = re.compile(r"_(\d{1,2})\.[^.]+$")


def load_executor() -> Any:
    spec = importlib.util.spec_from_file_location("ares_drive_executor", EXECUTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load executor: {EXECUTOR}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.load_env()
    return mod


def report_done(report: Path) -> set[str]:
    if not report.exists():
        return set()
    done: set[str] = set()
    with report.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "PROMOTED" and row.get("source_review_drive_id"):
                done.add(row["source_review_drive_id"])
    return done


def append_report(report: Path, row: dict[str, str]) -> None:
    report.parent.mkdir(parents=True, exist_ok=True)
    exists = report.exists()
    with report.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})


def validate_rows(rows: list[dict[str, str]]) -> None:
    for i, row in enumerate(rows, start=2):
        name = row.get("target_filename", "")
        if BAD_VARIANT_RE.search(name) and not VARIANT_RE.search(name):
            raise RuntimeError(f"row {i} has non-3-digit variant: {name}")
        if not VARIANT_RE.search(name):
            raise RuntimeError(f"row {i} missing 3-digit variant: {name}")
        folder = row.get("target_folder", "")
        if not folder.startswith("MGS-AGENTS/CRIATIVOS/") or not folder.endswith("/01_READY_CANDIDATE"):
            raise RuntimeError(f"row {i} unexpected target folder: {folder}")
        if not row.get("source_review_drive_id"):
            raise RuntimeError(f"row {i} missing source_review_drive_id")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("queue_csv", nargs="?", default=str(DEFAULT_QUEUE))
    ap.add_argument("--report-csv", default=str(DEFAULT_REPORT))
    args = ap.parse_args()

    queue = Path(args.queue_csv)
    report = Path(args.report_csv)
    rows = list(csv.DictReader(queue.open(newline="", encoding="utf-8")))
    validate_rows(rows)

    mod = load_executor()
    token, auth_mode = mod.build_access_token()
    drive = mod.Drive(token)
    done = report_done(report)

    stats = {"promoted": 0, "already_promoted": 0, "errors": 0}
    for row in rows:
        source_id = row["source_review_drive_id"]
        if source_id in done:
            stats["already_promoted"] += 1
            continue
        out = {
            "ts_utc": dt.datetime.now(dt.UTC).isoformat(),
            "source_review_drive_id": source_id,
            "target_drive_id": source_id,
            "old_name": row.get("current_review_filename", ""),
            "new_name": row["target_filename"],
            "target_folder": row["target_folder"],
        }
        try:
            meta = drive.request(
                f"https://www.googleapis.com/drive/v3/files/{source_id}?"
                + urllib.parse.urlencode({"supportsAllDrives": "true", "fields": "id,name,parents"})
            ) or {}
            parents = meta.get("parents") or []
            target_parent = drive.ensure_path(row["target_folder"])
            params = {"supportsAllDrives": "true", "fields": "id,name,parents", "addParents": target_parent}
            if parents:
                params["removeParents"] = ",".join(parents)
            body = json.dumps({"name": row["target_filename"]}).encode()
            drive.request(
                f"https://www.googleapis.com/drive/v3/files/{source_id}?" + urllib.parse.urlencode(params),
                method="PATCH",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            verify = drive.request(
                f"https://www.googleapis.com/drive/v3/files/{source_id}?"
                + urllib.parse.urlencode({"supportsAllDrives": "true", "fields": "id,name,parents"})
            ) or {}
            if verify.get("name") == row["target_filename"] and target_parent in (verify.get("parents") or []):
                out["status"] = "PROMOTED"
                stats["promoted"] += 1
            else:
                out["status"] = "VERIFY_FAILED"
                out["error"] = json.dumps({"name": verify.get("name"), "parents": verify.get("parents")}, ensure_ascii=False)[:1000]
                stats["errors"] += 1
        except Exception as exc:
            out["status"] = "ERROR"
            out["error"] = mod.describe_exception(exc)
            stats["errors"] += 1
        append_report(report, out)

    print(json.dumps({
        "done": stats["errors"] == 0,
        "auth_mode": auth_mode,
        "queue_rows": len(rows),
        "summary": stats,
        "report_csv": str(report),
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest() if report.exists() else "",
    }, ensure_ascii=False, indent=2))
    return 0 if stats["errors"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
