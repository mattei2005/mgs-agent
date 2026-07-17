#!/usr/bin/env python3
"""Read-only Google Drive inventory for MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL.

Uses the canonical MGS Google Service Account JSON stored in 1Password item
"Google Service Account - MGS Agent". Does not print or persist credentials.
"""
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
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

ROOT_FOLDER_ID = "0AEwt4Ye690ocUk9PVA"
CREATIVES_FOLDER_NAME = "CRIATIVOS"
UPLOAD_FOLDER_NAME = "UPLOAD MANUAL"
OP_ITEM = os.environ.get("MGS_GOOGLE_SERVICE_ACCOUNT_ITEM", "Google Service Account - MGS Agent")
DEFAULT_VAULT = os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
SCOPES = "https://www.googleapis.com/auth/drive.readonly"
FOLDER_MIME = "application/vnd.google-apps.folder"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def load_env(path: str = "/root/mgs-agent/.env") -> None:
    if not os.path.exists(path):
        return
    for line in Path(path).read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_op_item_json() -> dict[str, Any]:
    cmd = ["op", "item", "get", OP_ITEM, "--vault", DEFAULT_VAULT, "--format", "json"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"op item get failed: {proc.stderr[:300]}")
    return json.loads(proc.stdout)


def extract_service_account(item: dict[str, Any]) -> dict[str, Any]:
    candidates: list[str] = []
    for field in item.get("fields", []):
        value = field.get("value") or ""
        if value:
            candidates.append(value)
    for section in item.get("sections", []):
        for field in section.get("fields", []):
            value = field.get("value") or ""
            if value:
                candidates.append(value)
    for value in candidates:
        if "private_key" not in value or "client_email" not in value:
            continue
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            continue
        if parsed.get("private_key") and parsed.get("client_email"):
            return parsed
    raise RuntimeError("Service account JSON not found in expected 1Password item")


def get_access_token(sa: dict[str, Any]) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {
        "iss": sa["client_email"],
        "scope": SCOPES,
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + b64url(json.dumps(claim, separators=(",", ":")).encode())
    ).encode()
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise RuntimeError("Service account private key is not RSA")
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    jwt = signing_input.decode() + "." + b64url(signature)
    body = urllib.parse.urlencode(
        {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}
    ).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


class DriveClient:
    def __init__(self, token: str):
        self.token = token

    def list_children(self, parent_id: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params = {
                "q": f"'{parent_id}' in parents and trashed=false",
                "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,createdTime,size,fileExtension,md5Checksum,imageMediaMetadata(width,height),videoMediaMetadata(width,height,durationMillis))",
                "pageSize": "1000",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "orderBy": "name_natural",
            }
            if page_token:
                params["pageToken"] = page_token
            req = urllib.request.Request(
                "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params),
                headers={"Authorization": "Bearer " + self.token},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)
            out.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                return out


def normalize_text(value: str) -> str:
    value = value.upper()
    value = re.sub(r"[_\-/()]+", " ", value)
    value = value.replace("Á", "A").replace("À", "A").replace("Ã", "A").replace("Â", "A")
    value = value.replace("É", "E").replace("Ê", "E")
    value = value.replace("Í", "I")
    value = value.replace("Ó", "O").replace("Ô", "O").replace("Õ", "O")
    value = value.replace("Ú", "U").replace("Ç", "C")
    return value


def guess_vertical(path: str, name: str) -> tuple[str, str, str]:
    text = normalize_text(path + " " + name)
    if re.search(r"\b(EMPREGO|JOB|JOBS|TRABALHO|VAGA|VAGAS)\b", text):
        return "JOBS", "folder/name keyword", "EMPREGO/JOB"
    if re.search(r"\b(TARJETA|CARD|CREDITO|CREDIT|CARTAO|CC_)\b", text):
        return "CC", "folder/name keyword", "TARJETA/CARD/CREDITO"
    if re.search(r"\b(GAME|GAMES|ROBUX|ROBLOX|GAMING)\b", text):
        return "GAME", "folder/name keyword", "GAME/ROBLOX"
    if re.search(r"\b(CAR|AUTO|CARRO|VEHICLE|VEICULO)\b", text):
        return "CAR", "folder/name keyword", "CAR/AUTO"
    return "UNKNOWN", "insufficient evidence", ""


def guess_language(path: str, name: str) -> tuple[str, str]:
    text = normalize_text(path + " " + name)
    if re.search(r"\b(INGLES|ENGLISH|\bEN\b)", text):
        return "EN", "folder/name keyword"
    if re.search(r"\b(ESPANHOL|ESPANOL|SPANISH|\bES\b)", text):
        return "ES", "folder/name keyword"
    if re.search(r"\b(ALEMAO|ALEMAN|GERMAN|DEUTSCH|\bDE\b)", text):
        return "DE", "folder/name keyword"
    if re.search(r"\b(PORTUGUES PT|PORTUGUESE PT|PT PT|PORTUGAL)\b", text):
        return "PT", "explicit Portuguese-Portugal keyword"
    if re.search(r"\b(PORTUGUES|PORTUGUESE|BR)\b", text):
        return "BR", "Brazilian Portuguese default/keyword"
    if re.search(r"\b(FRANCES|FRENCH|FRANCAIS|\bFR\b)", text):
        return "FR", "folder/name keyword"
    if re.search(r"\b(TURCO|TURKISH|\bTR\b)", text):
        return "TR", "folder/name keyword"
    return "UNKNOWN", "insufficient evidence"


def format_kind(mime: str, extension: str) -> str:
    ext = (extension or "").lower()
    if mime.startswith("image/") or ext in {"png", "jpg", "jpeg", "webp", "gif"}:
        return "IMG"
    if mime.startswith("video/") or ext in {"mp4", "mov", "m4v", "webm"}:
        return "VID"
    if ext == "zip" or mime == "application/zip":
        return "ZIP"
    return "OTHER"


def aspect_ratio(width: int | None, height: int | None) -> str:
    if not width or not height:
        return ""
    if abs(width / height - 1) < 0.02:
        return "1:1"
    if abs(width / height - 9 / 16) < 0.02:
        return "9:16"
    if abs(width / height - 16 / 9) < 0.02:
        return "16:9"
    return f"{width}:{height}"


def placement_fit(width: int | None, height: int | None) -> str:
    ratio = aspect_ratio(width, height)
    if ratio == "1:1":
        return "FEED"
    if ratio == "9:16":
        return "STORY"
    if ratio == "16:9":
        return "LANDSCAPE"
    return "UNKNOWN"


def inventory(client: DriveClient) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root_children = client.list_children(ROOT_FOLDER_ID)
    creatives = next(
        (
            f
            for f in root_children
            if f.get("name") == CREATIVES_FOLDER_NAME and f.get("mimeType") == FOLDER_MIME
        ),
        None,
    )
    if not creatives:
        raise RuntimeError(f"{CREATIVES_FOLDER_NAME} not found under MGS-AGENTS root")

    creatives_children = client.list_children(creatives["id"])
    upload = next(
        (
            f
            for f in creatives_children
            if f.get("name") == UPLOAD_FOLDER_NAME and f.get("mimeType") == FOLDER_MIME
        ),
        None,
    )
    if not upload:
        raise RuntimeError(
            f"{UPLOAD_FOLDER_NAME} not found under MGS-AGENTS/{CREATIVES_FOLDER_NAME}"
        )

    queue = collections.deque(
        [(upload["id"], f"{CREATIVES_FOLDER_NAME}/{UPLOAD_FOLDER_NAME}")]
    )
    rows: list[dict[str, Any]] = []
    folder_count = 0
    while queue:
        parent_id, parent_path = queue.popleft()
        for child in client.list_children(parent_id):
            rel_path = parent_path + "/" + child["name"]
            if child.get("mimeType") == FOLDER_MIME:
                folder_count += 1
                queue.append((child["id"], rel_path))
                continue
            parts = rel_path.split("/")
            top_folder = parts[2] if len(parts) > 3 else "ROOT"
            ext = (child.get("fileExtension") or Path(child["name"]).suffix.lstrip(".")).lower()
            image_meta = child.get("imageMediaMetadata") or {}
            video_meta = child.get("videoMediaMetadata") or {}
            width = image_meta.get("width") or video_meta.get("width") or ""
            height = image_meta.get("height") or video_meta.get("height") or ""
            try:
                width_i = int(width) if width else None
                height_i = int(height) if height else None
            except ValueError:
                width_i = height_i = None
            vertical, vertical_reason, vertical_keyword = guess_vertical(rel_path, child["name"])
            language, language_reason = guess_language(rel_path, child["name"])
            fmt = format_kind(child.get("mimeType", ""), ext)
            rows.append(
                {
                    "drive_id": child.get("id", ""),
                    "original_filename": child.get("name", ""),
                    "relative_path": rel_path,
                    "source_top_folder": top_folder,
                    "mime_type": child.get("mimeType", ""),
                    "extension": ext,
                    "format": fmt,
                    "size_bytes": child.get("size", ""),
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio(width_i, height_i),
                    "placement_fit": placement_fit(width_i, height_i),
                    "duration_ms": video_meta.get("durationMillis", ""),
                    "md5_checksum": child.get("md5Checksum", ""),
                    "created_time": child.get("createdTime", ""),
                    "modified_time": child.get("modifiedTime", ""),
                    "vertical_guess": vertical,
                    "vertical_confidence": "medium" if vertical != "UNKNOWN" else "low",
                    "vertical_reason": vertical_reason,
                    "vertical_keyword": vertical_keyword,
                    "language_guess": language,
                    "language_confidence": "medium" if language != "UNKNOWN" else "low",
                    "language_reason": language_reason,
                    "status": "RAW_IN_UPLOAD_MANUAL",
                    "proposed_action": "INVENTORY_ONLY_NO_DRIVE_CHANGE",
                    "notes": "",
                }
            )
    summary = build_summary(rows, folder_count)
    return rows, summary


def build_summary(rows: list[dict[str, Any]], folder_count: int) -> dict[str, Any]:
    by_top: dict[str, Any] = collections.defaultdict(lambda: {"files": 0, "bytes": 0, "IMG": 0, "VID": 0, "ZIP": 0, "OTHER": 0})
    by_ext = collections.Counter()
    by_format = collections.Counter()
    by_vertical = collections.Counter()
    by_language = collections.Counter()
    by_placement = collections.Counter()
    by_dimension = collections.Counter()
    by_md5: dict[str, int] = collections.Counter()
    total_bytes = 0
    for row in rows:
        size = int(row["size_bytes"] or 0)
        total_bytes += size
        top = row["source_top_folder"] or "ROOT"
        fmt = row["format"]
        by_top[top]["files"] += 1
        by_top[top]["bytes"] += size
        by_top[top][fmt] += 1
        by_ext[row["extension"] or "no_ext"] += 1
        by_format[fmt] += 1
        by_vertical[row["vertical_guess"]] += 1
        by_language[row["language_guess"]] += 1
        by_placement[row["placement_fit"] or "UNKNOWN"] += 1
        dim = f"{row['width']}x{row['height']}" if row["width"] and row["height"] else "unknown"
        by_dimension[dim] += 1
        if row.get("md5_checksum"):
            by_md5[row["md5_checksum"]] += 1
    duplicate_groups = sum(1 for count in by_md5.values() if count > 1)
    duplicate_files = sum(count for count in by_md5.values() if count > 1)
    return {
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "source": "MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL",
        "root_folder_id_sha256_12": hashlib.sha256(ROOT_FOLDER_ID.encode()).hexdigest()[:12],
        "files": len(rows),
        "folders": folder_count,
        "bytes": total_bytes,
        "by_format": dict(by_format.most_common()),
        "by_extension": dict(by_ext.most_common()),
        "by_vertical_guess": dict(by_vertical.most_common()),
        "by_language_guess": dict(by_language.most_common()),
        "by_placement_fit": dict(by_placement.most_common()),
        "by_dimension_top20": dict(by_dimension.most_common(20)),
        "duplicate_md5_groups": duplicate_groups,
        "duplicate_md5_files": duplicate_files,
        "by_top_folder": dict(sorted(by_top.items())),
    }


def write_outputs(rows: list[dict[str, Any]], summary: dict[str, Any], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    csv_path = out_dir / f"upload-manual-inventory-{stamp}.csv"
    json_path = out_dir / f"upload-manual-summary-{stamp}.json"
    md_path = out_dir / f"upload-manual-summary-{stamp}.md"
    fields = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path), "markdown": str(md_path)}


def render_markdown(summary: dict[str, Any]) -> str:
    lines = ["# UPLOAD MANUAL inventory summary", "", f"Generated UTC: {summary['generated_at_utc']}", "", "## Totals", ""]
    lines += [f"- Files: {summary['files']}", f"- Folders: {summary['folders']}", f"- Bytes: {summary['bytes']}", f"- Duplicate MD5 groups: {summary['duplicate_md5_groups']}", f"- Duplicate MD5 files: {summary['duplicate_md5_files']}", ""]
    for key in ["by_format", "by_extension", "by_vertical_guess", "by_language_guess", "by_placement_fit", "by_dimension_top20"]:
        lines += [f"## {key}", "", "```text"]
        data = summary.get(key, {})
        for k, v in data.items():
            lines.append(f"{k}\t{v}")
        lines += ["```", ""]
    lines += ["## by_top_folder", "", "```text", "folder\tfiles\tIMG\tVID\tZIP\tOTHER\tbytes"]
    for folder, data in summary.get("by_top_folder", {}).items():
        lines.append(f"{folder}\t{data['files']}\t{data['IMG']}\t{data['VID']}\t{data['ZIP']}\t{data['OTHER']}\t{data['bytes']}")
    lines += ["```", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="/root/mgs-agent/data/ares/creative-ops/intake")
    args = parser.parse_args()
    load_env()
    item = get_op_item_json()
    sa = extract_service_account(item)
    token = get_access_token(sa)
    rows, summary = inventory(DriveClient(token))
    paths = write_outputs(rows, summary, Path(args.out_dir))
    print(json.dumps({"summary": summary, "paths": paths}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
