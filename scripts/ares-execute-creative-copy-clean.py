#!/usr/bin/env python3
"""Execute the approved Ares creative clean + copy queue.

Reads upload-canvas-dedup-copy-queue CSV, keeps UPLOAD_CANVAS raw files unchanged,
downloads each unique source, cleans metadata locally, verifies clean=true, creates
Drive destination folders, and uploads the cleaned file.

Resume-safe: skips queue_id already marked UPLOADED in the report CSV.
"""
from __future__ import annotations

import argparse
import base64
import collections
import csv
import datetime as dt
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

DEFAULT_ROOT_FOLDER_ID = "0AEwt4Ye690ocUk9PVA"
ROOT_FOLDER_ID = os.environ.get("ARES_DRIVE_ROOT_FOLDER_ID", DEFAULT_ROOT_FOLDER_ID)
OP_ITEM = os.environ.get("ARES_DRIVE_OP_ITEM", "Google Service Account - MGS Agent")
DEFAULT_VAULT = os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
SCOPES = "https://www.googleapis.com/auth/drive"
FOLDER_MIME = "application/vnd.google-apps.folder"
SANITIZER = "/root/mgs-agent/scripts/clean-creative-metadata.sh"


def load_env(path: str = "/root/mgs-agent/.env") -> None:
    if not os.path.exists(path):
        return
    for line in Path(path).read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def op_item_json(item_name: str) -> dict[str, Any]:
    proc = subprocess.run(["op", "item", "get", item_name, "--vault", DEFAULT_VAULT, "--format", "json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"op item get failed for {item_name}: {proc.stderr[:300]}")
    return json.loads(proc.stdout)


def service_account() -> dict[str, Any]:
    item = op_item_json(OP_ITEM)
    for field in item.get("fields", []):
        val = field.get("value") or ""
        if "private_key" in val and "client_email" in val:
            return json.loads(val)
    raise RuntimeError("service account JSON not found")


def build_access_token() -> tuple[str, str]:
    mode = os.environ.get("ARES_DRIVE_AUTH_MODE", "service_account").strip().lower().replace("-", "_")
    if mode != "service_account":
        raise RuntimeError(f"unsupported Drive auth mode after MGS cutover: {mode}")
    return access_token(service_account()), "service_account"


def access_token(sa: dict[str, Any]) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {"iss": sa["client_email"], "scope": SCOPES, "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600}
    msg = (b64url(json.dumps(header, separators=(",", ":")).encode()) + "." + b64url(json.dumps(claim, separators=(",", ":")).encode())).encode()
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise RuntimeError("service account private key is not RSA")
    jwt = msg.decode() + "." + b64url(key.sign(msg, padding.PKCS1v15(), hashes.SHA256()))
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


class Drive:
    def __init__(self, token: str):
        self.token = token
        self.folder_cache: dict[tuple[str, str], str] = {}

    def request(self, url: str, *, method: str = "GET", data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 60) -> Any:
        h = {"Authorization": "Bearer " + self.token, "User-Agent": "mgs-ares"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    body = r.read()
                    if not body:
                        return None
                    ctype = r.headers.get("Content-Type", "")
                    return json.loads(body) if "json" in ctype else body
            except urllib.error.HTTPError as e:
                if e.code in {429, 500, 502, 503, 504} and attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except Exception:
                if attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise

    def find_child_folder(self, parent_id: str, name: str) -> str | None:
        key = (parent_id, name)
        if key in self.folder_cache:
            return self.folder_cache[key]
        safe = name.replace("'", "\\'")
        q = f"'{parent_id}' in parents and mimeType='{FOLDER_MIME}' and name='{safe}' and trashed=false"
        params = {"q": q, "fields": "files(id,name)", "pageSize": "10", "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
        data = self.request("https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params))
        files = (data or {}).get("files", [])
        if files:
            self.folder_cache[key] = files[0]["id"]
            return files[0]["id"]
        return None

    def create_folder(self, parent_id: str, name: str) -> str:
        existing = self.find_child_folder(parent_id, name)
        if existing:
            return existing
        meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
        params = {"fields": "id,name", "supportsAllDrives": "true"}
        data = json.dumps(meta).encode()
        created = self.request("https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params), method="POST", data=data, headers={"Content-Type": "application/json"})
        folder_id = created["id"]
        self.folder_cache[(parent_id, name)] = folder_id
        return folder_id

    def root_metadata(self) -> dict[str, Any]:
        params = {
            "fields": "id,name,driveId,ownedByMe,owners(emailAddress,displayName),capabilities(canAddChildren,canEdit,canModifyContent)",
            "supportsAllDrives": "true",
        }
        return self.request(f"https://www.googleapis.com/drive/v3/files/{ROOT_FOLDER_ID}?" + urllib.parse.urlencode(params)) or {}

    def preflight_destination(self, auth_mode: str) -> dict[str, Any]:
        meta = self.root_metadata()
        if auth_mode == "service_account" and not meta.get("driveId"):
            owner = ", ".join(o.get("emailAddress", "") for o in meta.get("owners", []) if o.get("emailAddress"))
            raise RuntimeError(
                "DESTINATION_BLOCKED_MY_DRIVE_SERVICE_ACCOUNT: "
                f"root '{meta.get('name', ROOT_FOLDER_ID)}' is a My Drive folder owned by {owner or 'unknown owner'}. "
                "Google Service Accounts do not have storage quota for file uploads in My Drive. "
                "Use the canonical MGS-AGENTS Shared Drive and set ARES_DRIVE_ROOT_FOLDER_ID to "
                "0AEwt4Ye690ocUk9PVA, then revalidate the configured credential."
            )
        return meta

    def ensure_path(self, folder_path: str) -> str:
        parts = folder_path.split("/")
        if len(parts) < 2 or parts[:2] != ["MGS-AGENTS", "CRIATIVOS"]:
            raise ValueError(f"unexpected destination path: {folder_path}")
        creatives_id = self.find_child_folder(ROOT_FOLDER_ID, "CRIATIVOS")
        if not creatives_id:
            raise RuntimeError("canonical folder MGS-AGENTS/CRIATIVOS not found; refusing to create paths at Shared Drive root")
        parent = creatives_id
        for part in parts[2:]:
            parent = self.create_folder(parent, part)
        return parent

    def download(self, file_id: str, out_path: Path) -> None:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + self.token, "User-Agent": "mgs-ares"})
        with urllib.request.urlopen(req, timeout=300) as r, out_path.open("wb") as f:
            shutil.copyfileobj(r, f, length=1024 * 1024)

    def upload_resumable(self, parent_id: str, name: str, path: Path, mime: str) -> str:
        meta = {"name": name, "parents": [parent_id]}
        params = {"uploadType": "resumable", "supportsAllDrives": "true", "fields": "id,name,md5Checksum,size"}
        init_headers = {"Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(path.stat().st_size)}
        req = urllib.request.Request("https://www.googleapis.com/upload/drive/v3/files?" + urllib.parse.urlencode(params), data=json.dumps(meta).encode(), headers={"Authorization": "Bearer " + self.token, **init_headers}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            session_url = r.headers["Location"]
        size = path.stat().st_size
        chunk_size = 8 * 1024 * 1024
        sent = 0
        with path.open("rb") as f:
            while sent < size:
                chunk = f.read(chunk_size)
                start = sent
                end = sent + len(chunk) - 1
                sent += len(chunk)
                headers = {"Content-Type": mime, "Content-Length": str(len(chunk)), "Content-Range": f"bytes {start}-{end}/{size}"}
                req = urllib.request.Request(session_url, data=chunk, headers=headers, method="PUT")
                try:
                    with urllib.request.urlopen(req, timeout=300) as r:
                        body = r.read()
                        if sent == size:
                            return json.loads(body)["id"]
                except urllib.error.HTTPError as e:
                    if e.code == 308:
                        continue
                    raise
        raise RuntimeError("upload finished without final response")


def describe_exception(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode(errors="ignore")
        except Exception:
            body = ""
        return f"HTTP Error {exc.code}: {exc.reason} {body}"[:2000]
    return str(exc)[:2000]


def clean_and_verify(src: Path, out_dir: Path) -> tuple[Path, str]:
    out = out_dir / f"{src.stem}.metadata-clean{src.suffix}"
    proc = subprocess.run([SANITIZER, "clean", str(src), "--out", str(out), "--agent", "ares"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"sanitizer clean failed rc={proc.returncode}: {proc.stdout[-500:]} {proc.stderr[-500:]}")
    verify = subprocess.run([SANITIZER, "verify", str(out)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, timeout=300)
    if verify.returncode != 0 or "clean: true" not in verify.stdout:
        raise RuntimeError(f"sanitizer verify failed rc={verify.returncode}: {verify.stdout[-500:]} {verify.stderr[-500:]}")
    return out, verify.stdout


def existing_uploaded(report_path: Path) -> set[str]:
    if not report_path.exists():
        return set()
    done = set()
    with report_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "UPLOADED":
                done.add(row.get("queue_id", ""))
    return done


def append_report(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fields = ["ts_utc", "queue_id", "status", "source_drive_id", "dest_drive_id", "destination_folder", "destination_filename", "source_sha256", "clean_sha256", "bytes_clean", "error"]
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def process_queue(args: argparse.Namespace) -> dict[str, Any]:
    load_env()
    global ROOT_FOLDER_ID, OP_ITEM
    ROOT_FOLDER_ID = os.environ.get("ARES_DRIVE_ROOT_FOLDER_ID", ROOT_FOLDER_ID)
    OP_ITEM = os.environ.get("ARES_DRIVE_OP_ITEM", OP_ITEM)
    token, auth_mode = build_access_token()
    drive = Drive(token)
    root_meta = drive.preflight_destination(auth_mode)
    print(json.dumps({"preflight_destination": {"name": root_meta.get("name"), "root_folder_id": ROOT_FOLDER_ID, "drive_id": root_meta.get("driveId"), "storage": "shared_drive" if root_meta.get("driveId") else "my_drive", "auth_mode": auth_mode}}, ensure_ascii=False), flush=True)
    rows = list(csv.DictReader(open(args.queue_csv, encoding="utf-8")))
    if args.limit:
        rows = rows[: args.limit]
    report_path = Path(args.report_csv)
    done = existing_uploaded(report_path)
    stats = collections.Counter()
    tmp_root = Path(args.work_dir)
    tmp_root.mkdir(parents=True, exist_ok=True)

    for row in rows:
        qid = row["queue_id"]
        if qid in done:
            stats["already_uploaded"] += 1
            continue
        if row["queue_action"] != "CLEAN_METADATA_THEN_COPY_KEEP_RAW":
            stats["manual_review_skipped"] += 1
            append_report(report_path, {"ts_utc": dt.datetime.now(dt.UTC).isoformat(), "queue_id": qid, "status": "SKIPPED_MANUAL_REVIEW", "source_drive_id": row["source_drive_id"], "destination_folder": row["destination_folder"], "destination_filename": row["destination_filename"]})
            continue
        item_attempt = 0
        while item_attempt < 2:
            try:
                with tempfile.TemporaryDirectory(prefix="ares-clean-", dir=str(tmp_root)) as td:
                    tdp = Path(td)
                    ext = Path(row["original_filename"]).suffix or Path(row["destination_filename"]).suffix
                    raw = tdp / f"raw{ext}"
                    drive.download(row["source_drive_id"], raw)
                    raw_sha = sha256_file(raw)
                    clean, _verify_out = clean_and_verify(raw, tdp)
                    clean_sha = sha256_file(clean)
                    parent = drive.ensure_path(row["destination_folder"])
                    mime = mimetypes.guess_type(row["destination_filename"])[0] or "application/octet-stream"
                    dest_id = drive.upload_resumable(parent, row["destination_filename"], clean, mime)
                    append_report(report_path, {
                        "ts_utc": dt.datetime.now(dt.UTC).isoformat(),
                        "queue_id": qid,
                        "status": "UPLOADED",
                        "source_drive_id": row["source_drive_id"],
                        "dest_drive_id": dest_id,
                        "destination_folder": row["destination_folder"],
                        "destination_filename": row["destination_filename"],
                        "source_sha256": raw_sha,
                        "clean_sha256": clean_sha,
                        "bytes_clean": str(clean.stat().st_size),
                    })
                    stats["uploaded"] += 1
                    if stats["uploaded"] % 25 == 0:
                        print(json.dumps({"progress_uploaded": stats["uploaded"], "queue_id": qid, "ts": dt.datetime.now(dt.UTC).isoformat()}), flush=True)
                    break
            except Exception as e:
                error_text = describe_exception(e)
                if auth_mode == "oauth_user" and "HTTP Error 401" in error_text and item_attempt == 0:
                    token, _auth_mode = build_access_token()
                    drive.token = token
                    item_attempt += 1
                    print(json.dumps({"auth_refreshed": True, "retry_queue_id": qid, "ts": dt.datetime.now(dt.UTC).isoformat()}), flush=True)
                    continue
                stats["errors"] += 1
                append_report(report_path, {"ts_utc": dt.datetime.now(dt.UTC).isoformat(), "queue_id": qid, "status": "ERROR", "source_drive_id": row.get("source_drive_id", ""), "destination_folder": row.get("destination_folder", ""), "destination_filename": row.get("destination_filename", ""), "error": error_text[:1000]})
                print(json.dumps({"error_queue_id": qid, "error": error_text[:500]}), flush=True)
                if stats["errors"] >= args.max_errors:
                    break
                break
        if stats["errors"] >= args.max_errors:
            break
    return dict(stats)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("queue_csv")
    ap.add_argument("--report-csv", default="/root/mgs-agent/data/ares/creative-inventory/upload-canvas-clean-copy-execution-report.csv")
    ap.add_argument("--work-dir", default="/root/mgs-agent/tmp/ares-clean-copy")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-errors", type=int, default=20)
    args = ap.parse_args()
    try:
        summary = process_queue(args)
    except Exception as e:
        print(json.dumps({"done": False, "blocked": True, "error": describe_exception(e)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"done": True, "summary": summary, "report_csv": args.report_csv}, ensure_ascii=False, indent=2))
    return 0 if not summary.get("errors") else 2


if __name__ == "__main__":
    raise SystemExit(main())
