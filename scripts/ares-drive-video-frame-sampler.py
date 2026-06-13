#!/usr/bin/env python3
"""Sample multiple frames from Google Drive videos listed in an Ares inventory CSV.

Purpose: avoid misclassifying Canva/Drive videos from the first Drive thumbnail when
content appears only after a few seconds. This script is read-only against Drive:
it downloads selected videos to local temp/output folders and generates timeline
contact sheets for visual classification.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

EXECUTOR_PATH = Path("/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py")
DEFAULT_OUT_DIR = Path("/root/mgs-agent/data/ares/creative-inventory/video-frame-samples")


def load_executor():
    spec = importlib.util.spec_from_file_location("ares_drive_executor", EXECUTOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXECUTOR_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_seconds(value: str) -> list[float]:
    out: list[float] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    if not out:
        raise ValueError("at least one second offset is required")
    return out


def select_rows(rows: list[dict[str, str]], args: argparse.Namespace) -> list[dict[str, str]]:
    selected = [r for r in rows if r.get("format") == "VID"]
    if args.drive_id:
        wanted = set(args.drive_id)
        selected = [r for r in selected if r.get("drive_id") in wanted]
    if args.filename_regex:
        rx = re.compile(args.filename_regex, re.I)
        selected = [r for r in selected if rx.search(r.get("original_filename", "")) or rx.search(r.get("relative_path", ""))]
    selected = sorted(selected, key=lambda r: (r.get("source_top_folder", ""), r.get("relative_path", "")))
    if args.limit:
        selected = selected[: args.limit]
    return selected


def ffprobe_duration(path: Path) -> float | None:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    try:
        return float(proc.stdout.strip())
    except Exception:
        return None


def extract_frame(video: Path, second: float, out: Path) -> bool:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-ss", str(second), "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0 and out.exists() and out.stat().st_size > 0


def make_sheet(row: dict[str, str], frames: list[tuple[float, Path]], out_path: Path) -> None:
    thumb_w, thumb_h, label_h = 260, 462, 82
    cols = len(frames)
    sheet = Image.new("RGB", (cols * thumb_w, thumb_h + label_h + 44), color="white")  # type: ignore[arg-type]
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 12)
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        title_font = font
    title = f"{row.get('original_filename','')} | {row.get('format')} {row.get('language_guess')} {row.get('placement_fit')}"
    draw.text((10, 8), title[:150], fill="black", font=title_font)
    for idx, (second, frame_path) in enumerate(frames):
        x = idx * thumb_w
        y = 40
        try:
            img = Image.open(frame_path).convert("RGB")
            img.thumbnail((thumb_w - 12, thumb_h - 12))
            sheet.paste(img, (x + (thumb_w - img.width) // 2, y + (thumb_h - img.height) // 2))
        except Exception:
            draw.rectangle([x + 8, y + 8, x + thumb_w - 8, y + thumb_h - 8], outline="red")
            draw.text((x + 12, y + 20), "frame error", fill="red", font=font)
        draw.rectangle([x, y, x + thumb_w - 1, y + thumb_h + label_h - 1], outline=(220, 220, 220))
        draw.text((x + 8, y + thumb_h + 5), f"t={second:.1f}s", fill="black", font=title_font)
        label = row.get("relative_path", "")[:80]
        for j, chunk in enumerate([label[i : i + 38] for i in range(0, len(label), 38)][:3]):
            draw.text((x + 8, y + thumb_h + 28 + j * 14), chunk, fill="black", font=font)
    sheet.save(out_path, quality=92)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate multi-frame contact sheets for Drive videos in an inventory CSV")
    ap.add_argument("inventory_csv")
    ap.add_argument("--drive-id", action="append", help="Drive file id to sample; can be passed multiple times")
    ap.add_argument("--filename-regex", help="Regex matched against original_filename or relative_path")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seconds", default="0.5,2.0,3.2,4.5,6.0")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()

    seconds = parse_seconds(args.seconds)
    rows = list(csv.DictReader(open(args.inventory_csv, encoding="utf-8")))
    selected = select_rows(rows, args)
    if not selected:
        raise RuntimeError("no video rows selected")

    executor = load_executor()
    executor.load_env()
    token, auth_mode = executor.build_access_token()
    drive = executor.Drive(token)

    run_dir = Path(args.out_dir) / dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    video_dir = run_dir / "videos"
    frame_dir = run_dir / "frames"
    sheet_dir = run_dir / "sheets"
    for d in [video_dir, frame_dir, sheet_dir]:
        d.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "inventory_csv": args.inventory_csv,
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "auth_mode": auth_mode,
        "seconds": seconds,
        "selected_count": len(selected),
        "run_dir": str(run_dir),
        "items": [],
    }

    for row in selected:
        fid = row["drive_id"]
        safe_id = hashlib.sha256(fid.encode()).hexdigest()[:16]
        ext = Path(row.get("original_filename", "video.mp4")).suffix or ".mp4"
        video_path = video_dir / f"{safe_id}{ext}"
        media_url = "https://www.googleapis.com/drive/v3/files/" + fid + "?" + urllib.parse.urlencode({"alt": "media", "supportsAllDrives": "true"})
        data = drive.request(media_url, timeout=180)
        if not isinstance(data, (bytes, bytearray)):
            raise RuntimeError(f"download did not return bytes for {fid}")
        video_path.write_bytes(data)
        duration = ffprobe_duration(video_path)
        item_frames: list[tuple[float, Path]] = []
        for second in seconds:
            # Keep requested offsets but avoid going past duration when known.
            sample_second = second
            if duration and sample_second >= duration:
                sample_second = max(0.1, duration - 0.2)
            frame_path = frame_dir / f"{safe_id}_{str(second).replace('.', '_')}.jpg"
            ok = extract_frame(video_path, sample_second, frame_path)
            if ok:
                item_frames.append((second, frame_path))
        sheet_path = sheet_dir / f"{safe_id}_timeline.jpg"
        make_sheet(row, item_frames, sheet_path)
        manifest["items"].append(
            {
                "drive_id_sha256_12": hashlib.sha256(fid.encode()).hexdigest()[:12],
                "original_filename": row.get("original_filename"),
                "relative_path": row.get("relative_path"),
                "language_guess": row.get("language_guess"),
                "placement_fit": row.get("placement_fit"),
                "duration_seconds": duration,
                "video_local": str(video_path),
                "sheet": str(sheet_path),
                "frames": [str(p) for _, p in item_frames],
            }
        )

    manifest_path = run_dir / "video-frame-sample-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "run_dir": str(run_dir), "selected_count": len(selected), "sheets": [i["sheet"] for i in manifest["items"]]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
