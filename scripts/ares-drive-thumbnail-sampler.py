#!/usr/bin/env python3
"""Read-only thumbnail sampler/contact-sheet generator for UPLOAD_CANVAS inventory."""
from __future__ import annotations

import argparse
import base64
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from PIL import Image, ImageDraw, ImageFont

OP_ITEM = os.environ.get("MGS_GOOGLE_SERVICE_ACCOUNT_ITEM", "Google Service Account - MGS Agent")
DEFAULT_VAULT = os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
SCOPES = "https://www.googleapis.com/auth/drive.readonly"


def load_env(path: str = "/root/mgs-agent/.env") -> None:
    if not os.path.exists(path):
        return
    for line in Path(path).read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def service_account() -> dict[str, Any]:
    proc = subprocess.run(
        ["op", "item", "get", OP_ITEM, "--vault", DEFAULT_VAULT, "--format", "json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"op failed: {proc.stderr[:300]}")
    item = json.loads(proc.stdout)
    for field in item.get("fields", []):
        value = field.get("value") or ""
        if "private_key" in value and "client_email" in value:
            return json.loads(value)
    raise RuntimeError("service account JSON not found")


def access_token(sa: dict[str, Any]) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {"iss": sa["client_email"], "scope": SCOPES, "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600}
    msg = (b64url(json.dumps(header, separators=(",", ":")).encode()) + "." + b64url(json.dumps(claim, separators=(",", ":")).encode())).encode()
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise RuntimeError("not RSA key")
    jwt = msg.decode() + "." + b64url(key.sign(msg, padding.PKCS1v15(), hashes.SHA256()))
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def drive_get(token: str, file_id: str) -> dict[str, Any]:
    params = {"fields": "id,name,mimeType,thumbnailLink,hasThumbnail,webContentLink", "supportsAllDrives": "true"}
    req = urllib.request.Request(
        f"https://www.googleapis.com/drive/v3/files/{file_id}?" + urllib.parse.urlencode(params),
        headers={"Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def download_thumb(token: str, meta: dict[str, Any], out_path: Path) -> bool:
    url = meta.get("thumbnailLink")
    if url:
        # Increase thumbnail size if Google provided an =sXXX suffix.
        url = re.sub(r"=s\d+", "=s512", url)
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "User-Agent": "mgs-ares"})
    else:
        # Fallback downloads the real file; only used for small images.
        req = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{meta['id']}?alt=media&supportsAllDrives=true",
            headers={"Authorization": "Bearer " + token, "User-Agent": "mgs-ares"},
        )
    try:
        data = urllib.request.urlopen(req, timeout=45).read()
        out_path.write_bytes(data)
        return True
    except Exception:
        return False


def safe_label(row: dict[str, str]) -> str:
    label = f"{row['source_top_folder']} | {row['format']} {row['placement_fit']} {row['language_guess']} | {row['original_filename']}"
    return label[:90]


def make_sheet(items: list[tuple[dict[str, str], Path]], sheet_path: Path, title: str, cols: int = 4) -> None:
    thumb_w, thumb_h, label_h = 260, 260, 62
    rows_n = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows_n * (thumb_h + label_h) + 40), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 12)
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
        title_font = font
    draw.text((10, 8), title, fill="black", font=title_font)
    for idx, (row, img_path) in enumerate(items):
        x = (idx % cols) * thumb_w
        y = 40 + (idx // cols) * (thumb_h + label_h)
        try:
            img = Image.open(img_path).convert("RGB")
            img.thumbnail((thumb_w - 12, thumb_h - 12))
            ix = x + (thumb_w - img.width) // 2
            iy = y + (thumb_h - img.height) // 2
            sheet.paste(img, (ix, iy))
        except Exception:
            draw.rectangle([x + 8, y + 8, x + thumb_w - 8, y + thumb_h - 8], outline="red")
            draw.text((x + 12, y + 20), "thumbnail error", fill="red", font=font)
        draw.rectangle([x, y, x + thumb_w - 1, y + thumb_h + label_h - 1], outline=(220, 220, 220))
        label = safe_label(row)
        chunks = [label[i : i + 42] for i in range(0, len(label), 42)][:4]
        for j, chunk in enumerate(chunks):
            draw.text((x + 6, y + thumb_h + 4 + j * 14), chunk, fill="black", font=font)
    sheet.save(sheet_path, quality=90)


def select_rows(rows: list[dict[str, str]], max_per_group: int, max_total: int) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    counts: dict[tuple[str, str, str, str], int] = collections.Counter()
    for row in rows:
        if row.get("vertical_guess") != "UNKNOWN":
            continue
        group = (row["source_top_folder"], row["format"], row["placement_fit"], row["language_guess"])
        if counts[group] >= max_per_group:
            continue
        counts[group] += 1
        selected.append(row)
        if len(selected) >= max_total:
            break
    return selected


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inventory_csv")
    ap.add_argument("--out-dir", default="/root/mgs-agent/data/ares/creative-inventory/thumbnails")
    ap.add_argument("--max-per-group", type=int, default=3)
    ap.add_argument("--max-total", type=int, default=180)
    args = ap.parse_args()
    load_env()
    out_dir = Path(args.out_dir) / dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    thumbs = out_dir / "thumbs"
    sheets = out_dir / "sheets"
    thumbs.mkdir(parents=True, exist_ok=True)
    sheets.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(open(args.inventory_csv, encoding="utf-8")))
    rows = sorted(rows, key=lambda r: (r["source_top_folder"], r["format"], r["placement_fit"], r["language_guess"], r["relative_path"]))
    selected = select_rows(rows, args.max_per_group, args.max_total)
    token = access_token(service_account())
    downloaded: list[tuple[dict[str, str], Path]] = []
    failures = 0
    for row in selected:
        meta = drive_get(token, row["drive_id"])
        name = hashlib.sha256(row["drive_id"].encode()).hexdigest()[:16] + ".jpg"
        out = thumbs / name
        if download_thumb(token, meta, out):
            downloaded.append((row, out))
        else:
            failures += 1

    by_top: dict[str, list[tuple[dict[str, str], Path]]] = collections.defaultdict(list)
    for item in downloaded:
        by_top[item[0]["source_top_folder"]].append(item)
    sheet_paths = []
    for top, items in sorted(by_top.items()):
        sheet = sheets / f"{re.sub(r'[^A-Za-z0-9_.-]+','_',top)}.jpg"
        make_sheet(items, sheet, f"UNKNOWN samples — {top}")
        sheet_paths.append(str(sheet))
    manifest = {
        "inventory_csv": args.inventory_csv,
        "selected": len(selected),
        "downloaded": len(downloaded),
        "failures": failures,
        "out_dir": str(out_dir),
        "sheets": sheet_paths,
    }
    (out_dir / "thumbnail-sample-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
