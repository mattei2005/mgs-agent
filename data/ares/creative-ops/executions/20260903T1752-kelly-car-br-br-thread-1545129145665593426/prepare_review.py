#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT_ID = "0AEwt4Ye690ocUk9PVA"
EXPECTED_DRIVE = "MGS-AGENTS"
EXPECTED_EMAIL = "mgsagent@mgs-core-prod.iam.gserviceaccount.com"
EXPECTED_PROJECT = "mgs-core-prod"
FOLDER_MIME = "application/vnd.google-apps.folder"
EXECUTOR = Path("/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py")
CSV_PATH = Path("/root/mgs-agent/data/ares/creative-ops/intake/current-kelly-car-br-br-1545129145665593426/upload-manual-inventory-20260903T175223Z.csv")
BASE = Path("/root/mgs-agent/data/ares/creative-ops/executions/20260903T1752-kelly-car-br-br-thread-1545129145665593426")
RAW_DIR = BASE / "runtime" / "review-raw"
FRAME_DIR = BASE / "runtime" / "review-frames"
SHEET_DIR = BASE / "runtime" / "review-sheets"
MANIFEST = BASE / "review-manifest.json"


def load_executor():
    spec = importlib.util.spec_from_file_location("ares_executor", EXECUTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical Drive executor")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def api_get(drive, file_id: str) -> dict[str, Any]:
    fields = "id,name,mimeType,parents,driveId,size,md5Checksum,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive,canModifyContent,canTrash,canDelete)"
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?" + urllib.parse.urlencode({"supportsAllDrives": "true", "fields": fields})
    return drive.request(url) or {}


def probe(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,codec_name:format=duration", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path.name}: {proc.stderr[-300:]}")
    data = json.loads(proc.stdout)
    stream = data["streams"][0]
    return {"width": int(stream["width"]), "height": int(stream["height"]), "codec": stream.get("codec_name"), "duration": float(data["format"]["duration"])}


def extract_frame(video: Path, out: Path, seconds: float) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{seconds:.3f}", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=120,
    )
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"frame extraction failed: {video.name} @ {seconds:.3f}s")


def font(size: int):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def make_sheet(group: list[dict[str, Any]], sheet_no: int) -> Path:
    frame_w, frame_h = 405, 720
    label_h, gap = 70, 8
    canvas = Image.new("RGB", (frame_w * 3 + gap * 2, len(group) * (frame_h + label_h + gap)), color=(255, 255, 255))  # type: ignore[arg-type]
    draw = ImageDraw.Draw(canvas)
    fnt = font(28)
    for row_no, item in enumerate(group):
        y = row_no * (frame_h + label_h + gap)
        label = f"#{item['index']:02d} | {item['original_filename']}"
        draw.rectangle((0, y, canvas.width, y + label_h), fill=(20, 20, 20))
        draw.text((12, y + 16), label, fill="white", font=fnt)
        for col, frame_path in enumerate(item["frames"]):
            with Image.open(frame_path) as im:
                rendered = im.convert("RGB").resize((frame_w, frame_h), Image.Resampling.LANCZOS)
            canvas.paste(rendered, (col * (frame_w + gap), y + label_h))
    out = SHEET_DIR / f"review-sheet-{sheet_no:02d}.jpg"
    canvas.save(out, quality=92, optimize=True)
    return out


def main() -> int:
    rows = [r for r in csv.DictReader(CSV_PATH.open(encoding="utf-8")) if r.get("format") == "VID"]
    if len(rows) != 24:
        raise RuntimeError(f"expected 24 videos, found {len(rows)}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    SHEET_DIR.mkdir(parents=True, exist_ok=True)

    ex = load_executor()
    ex.load_env()
    sa = ex.service_account()
    if sa.get("client_email") != EXPECTED_EMAIL or sa.get("project_id") != EXPECTED_PROJECT:
        raise RuntimeError("canonical service account identity mismatch")
    token, auth_mode = ex.build_access_token()
    if auth_mode != "service_account":
        raise RuntimeError("non-service-account auth refused")
    drive = ex.Drive(token)
    root = drive.preflight_destination(auth_mode)
    shared = drive.request(f"https://www.googleapis.com/drive/v3/drives/{ROOT_ID}?fields=id,name") or {}
    if root.get("driveId") != ROOT_ID or shared.get("name") != EXPECTED_DRIVE:
        raise RuntimeError("canonical Shared Drive validation failed")

    items = []
    for idx, row in enumerate(rows, 1):
        live = api_get(drive, row["drive_id"])
        caps = live.get("capabilities") or {}
        if live.get("driveId") != ROOT_ID or live.get("name") != row["original_filename"] or live.get("trashed"):
            raise RuntimeError(f"source readback mismatch: {row['original_filename']}")
        if not caps.get("canDownload") or not caps.get("canMoveItemWithinDrive"):
            raise RuntimeError(f"required capability missing: {row['original_filename']}")
        raw = RAW_DIR / f"{idx:02d}.mp4"
        if not raw.exists() or raw.stat().st_size != int(row["size_bytes"]):
            drive.download(row["drive_id"], raw)
        tech = probe(raw)
        if tech["width"] != 1080 or tech["height"] != 1920 or tech["duration"] <= 0:
            raise RuntimeError(f"unexpected technical profile: {row['original_filename']} {tech}")
        frames = []
        for frame_no, fraction in enumerate((0.18, 0.50, 0.82), 1):
            frame_path = FRAME_DIR / f"{idx:02d}-{frame_no}.jpg"
            if not frame_path.exists():
                extract_frame(raw, frame_path, tech["duration"] * fraction)
            frames.append(str(frame_path))
        items.append({
            "index": idx,
            "drive_id": row["drive_id"],
            "original_filename": row["original_filename"],
            "size_bytes": int(row["size_bytes"]),
            "md5_checksum": row["md5_checksum"],
            "tech": tech,
            "frames": frames,
            "drive_readback_valid": True,
            "capabilities_valid": True,
        })

    sheets = []
    for start in range(0, len(items), 4):
        sheets.append(str(make_sheet(items[start:start + 4], len(sheets) + 1)))
    payload = {
        "auth_mode": auth_mode,
        "service_account": EXPECTED_EMAIL,
        "project": EXPECTED_PROJECT,
        "shared_drive": EXPECTED_DRIVE,
        "shared_drive_id": ROOT_ID,
        "source_count": len(items),
        "technical_profiles_valid": len(items),
        "items": items,
        "review_sheets": sheets,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"source_count": len(items), "technical_profiles_valid": len(items), "sheets": sheets, "manifest": str(MANIFEST)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
