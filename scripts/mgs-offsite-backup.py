#!/usr/bin/env python3
"""Encrypted off-site disaster-recovery backups for MGS.

The normal backup path uses only the versioned public key. The private key is
read from 1Password exclusively during an isolated restore test. Archives are
uploaded to the canonical MGS-AGENTS Shared Drive and validated by metadata,
size, MD5 and SHA-256 readback.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import fcntl
import hashlib
import json
import mimetypes
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

REPO = Path("/root/mgs-agent")
CONFIG_PATH = REPO / "config/backup/mgs-offsite-backup.json"
ENV_PATH = REPO / ".env"
HERMES = Path("/root/.local/bin/hermes")
FOLDER_MIME = "application/vnd.google-apps.folder"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
MGS_DATA_SUFFIXES = {
    "", ".json", ".jsonl", ".db", ".sqlite", ".csv", ".tsv", ".md",
    ".txt", ".yaml", ".yml", ".toml", ".py", ".sh", ".bash", ".js",
    ".ts", ".html", ".css", ".sql", ".xml",
}
GLOBAL_SKIP_DIRS = {
    ".git", "backups", "reports", "tmp", "work", "node_modules",
    "__pycache__", ".cache", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}
DATA_SKIP_PREFIXES = {
    "data/generated",
    "data/ares/creative-inventory",
    "data/ares/creative-ops/ready",
    "data/ares/creative-ops/raw",
    "data/ares/creative-ops/processed",
}
FULL_DIRS = (
    "context", "docs", "scripts", "profiles", "skills", "contracts",
    "references", "patches", "api", "tests", "config", "data", ".secrets",
)
FULL_FILES = ("AGENT.md", "CLAUDE.md", ".env")
QUICK_FILES = (
    "AGENT.md",
    "context/knowledge-governance.md",
    "context/mgs-os-map.md",
    "data/agent-checkpoints.json",
    "data/knowledge-registry.json",
    "data/knowledge-inbox.jsonl",
    "data/knowledge-regression-cases.json",
    "data/authorized-users.json",
    "data/infra-inventory.json",
    "logs/events-audit.jsonl",
    "config/backup/mgs-offsite-backup.json",
    "config/backup/mgs-dr-backup-public.asc",
)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_now() -> str:
    return utcnow().isoformat()


def load_config() -> dict[str, Any]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise RuntimeError("unsupported backup config schema")
    return data


def load_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def append_event(config: dict[str, Any], event: str, **fields: Any) -> None:
    path = Path(config["log_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts_utc": iso_now(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def op_item(item_name: str) -> dict[str, Any]:
    load_env()
    vault = os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
    proc = subprocess.run(
        ["op", "item", "get", item_name, "--vault", vault, "--format", "json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=90,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"1Password item lookup failed for {item_name}: rc={proc.returncode}")
    return json.loads(proc.stdout)


def service_account(config: dict[str, Any]) -> dict[str, Any]:
    item = op_item(config["service_account_item"])
    for field in item.get("fields", []):
        value = field.get("value") or ""
        if "private_key" in value and "client_email" in value:
            data = json.loads(value)
            required = {"client_email", "private_key"}
            if not required.issubset(data):
                break
            return data
    raise RuntimeError("Google Drive service-account JSON not found in 1Password item")


def private_backup_key(config: dict[str, Any]) -> str:
    item = op_item(config["backup_key_item"])
    for field in item.get("fields", []):
        if field.get("label") == "private_key":
            value = field.get("value") or ""
            if value.startswith("-----BEGIN PGP PRIVATE KEY BLOCK-----"):
                return value
    raise RuntimeError("disaster-recovery private key not found in 1Password item")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def drive_access_token(sa: dict[str, Any]) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {
        "iss": sa["client_email"],
        "scope": DRIVE_SCOPE,
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    message = (
        b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + b64url(json.dumps(claim, separators=(",", ":")).encode())
    ).encode()
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise RuntimeError("Google Drive service-account key is not RSA")
    signature = key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    assertion = message.decode() + "." + b64url(signature)
    body = urllib.parse.urlencode(
        {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}
    ).encode()
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if not result.get("access_token"):
        raise RuntimeError("Google token response did not include access_token")
    return result["access_token"]


class Drive:
    def __init__(self, token: str):
        self.token = token

    def request(
        self,
        url: str,
        *,
        method: str = "GET",
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 90,
    ) -> Any:
        merged = {"Authorization": "Bearer " + self.token, "User-Agent": "mgs-disaster-recovery"}
        if headers:
            merged.update(headers)
        for attempt in range(6):
            request = urllib.request.Request(url, data=data, headers=merged, method=method)
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    raw = response.read()
                    if not raw:
                        return None
                    return json.loads(raw) if "json" in response.headers.get("Content-Type", "") else raw
            except urllib.error.HTTPError as exc:
                if exc.code in {429, 500, 502, 503, 504} and attempt < 5:
                    time.sleep(min(32, 2 ** attempt))
                    continue
                detail = exc.read().decode(errors="ignore")[:500]
                raise RuntimeError(f"Drive HTTP {exc.code}: {detail}") from exc
            except (TimeoutError, urllib.error.URLError) as exc:
                if attempt < 5:
                    time.sleep(min(32, 2 ** attempt))
                    continue
                raise RuntimeError(f"Drive request failed: {type(exc).__name__}") from exc

    def metadata(self, file_id: str) -> dict[str, Any]:
        fields = "id,name,mimeType,parents,driveId,size,md5Checksum,trashed,createdTime,appProperties,capabilities(canAddChildren,canEdit)"
        query = urllib.parse.urlencode({"supportsAllDrives": "true", "fields": fields})
        return self.request(f"https://www.googleapis.com/drive/v3/files/{file_id}?{query}") or {}

    def ensure_folder(self, parent_id: str, name: str, marker: str) -> str:
        safe_name = name.replace("'", "\\'")
        q = f"'{parent_id}' in parents and mimeType='{FOLDER_MIME}' and name='{safe_name}' and trashed=false"
        params = {
            "q": q,
            "fields": "files(id,name,mimeType,parents,driveId,trashed,appProperties)",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "pageSize": "20",
        }
        found = (self.request("https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params)) or {}).get("files", [])
        if len(found) > 1:
            raise RuntimeError(f"ambiguous Drive folder {name}: {len(found)} matches")
        if found:
            return found[0]["id"]
        body = {
            "name": name,
            "mimeType": FOLDER_MIME,
            "parents": [parent_id],
            "appProperties": {"mgs_dr_folder": marker},
        }
        params = {"supportsAllDrives": "true", "fields": "id,name,parents,driveId,appProperties"}
        created = self.request(
            "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params),
            method="POST",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        return created["id"]

    def upload_resumable(
        self,
        parent_id: str,
        path: Path,
        *,
        tier: str,
        mode: str,
        sha256: str,
    ) -> dict[str, Any]:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        metadata = {
            "name": path.name,
            "parents": [parent_id],
            "appProperties": {
                "mgs_dr": "true",
                "tier": tier,
                "mode": mode,
                "sha256": sha256,
            },
        }
        params = {
            "uploadType": "resumable",
            "supportsAllDrives": "true",
            "fields": "id,name,size,md5Checksum,parents,driveId,trashed,createdTime,appProperties",
        }
        headers = {
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime,
            "X-Upload-Content-Length": str(path.stat().st_size),
            "User-Agent": "mgs-disaster-recovery",
        }
        request = urllib.request.Request(
            "https://www.googleapis.com/upload/drive/v3/files?" + urllib.parse.urlencode(params),
            data=json.dumps(metadata).encode(),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            session_url = response.headers["Location"]
        size = path.stat().st_size
        chunk_size = 8 * 1024 * 1024
        sent = 0
        final: dict[str, Any] | None = None
        with path.open("rb") as fh:
            while sent < size:
                chunk = fh.read(chunk_size)
                start = sent
                end = sent + len(chunk) - 1
                sent += len(chunk)
                chunk_headers = {
                    "Content-Type": mime,
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{size}",
                }
                chunk_request = urllib.request.Request(session_url, data=chunk, headers=chunk_headers, method="PUT")
                try:
                    with urllib.request.urlopen(chunk_request, timeout=300) as response:
                        raw = response.read()
                        if sent == size:
                            final = json.loads(raw)
                except urllib.error.HTTPError as exc:
                    if exc.code == 308:
                        continue
                    detail = exc.read().decode(errors="ignore")[:500]
                    raise RuntimeError(f"Drive upload HTTP {exc.code}: {detail}") from exc
        if not final:
            raise RuntimeError("Drive resumable upload ended without final metadata")
        return final

    def download(self, file_id: str, output: Path) -> None:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
        request = urllib.request.Request(
            url,
            headers={"Authorization": "Bearer " + self.token, "User-Agent": "mgs-disaster-recovery"},
        )
        with urllib.request.urlopen(request, timeout=300) as response, output.open("wb") as fh:
            shutil.copyfileobj(response, fh, length=1024 * 1024)

    def list_managed(self, parent_id: str) -> list[dict[str, Any]]:
        q = f"'{parent_id}' in parents and trashed=false and appProperties has {{ key='mgs_dr' and value='true' }}"
        params = {
            "q": q,
            "fields": "files(id,name,size,md5Checksum,parents,driveId,trashed,createdTime,appProperties)",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "pageSize": "1000",
            "orderBy": "createdTime desc",
        }
        return (self.request("https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params)) or {}).get("files", [])

    def trash(self, file_id: str) -> dict[str, Any]:
        params = {"supportsAllDrives": "true", "fields": "id,name,trashed,appProperties"}
        return self.request(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?" + urllib.parse.urlencode(params),
            method="PATCH",
            data=b'{"trashed":true}',
            headers={"Content-Type": "application/json"},
        ) or {}


def classify_full_tier(now: dt.datetime) -> str:
    if now.day == 1:
        return "monthly"
    if now.weekday() == 6:
        return "weekly"
    return "daily"


def safe_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"corrupt zip member: {bad}")
        for member in archive.infolist():
            target = Path(member.filename)
            if target.is_absolute() or ".." in target.parts:
                raise RuntimeError(f"unsafe zip member: {member.filename}")


def archive_write_if_present(archive: zipfile.ZipFile, source: Path, arcname: str) -> bool:
    """Archive a live file, tolerating deletion after inventory enumeration."""
    try:
        archive.write(source, arcname)
    except FileNotFoundError:
        if not source.exists():
            return False
        raise
    return True


QUICK_PROFILE_ENTRIES = (
    "state.db", "config.yaml", ".env", "auth.json", "cron", "channel_directory.json",
    "channel_aliases.json", "pairing", "platforms/pairing", "projects.db",
    "response_store.db", "memory_store.db", "verification_evidence.db", "kanban",
    "sessions", "memories",
)
PROFILE_SKIP_DIRS = {
    "home", "lsp", "bin", "cache", "logs", "artifacts", "browser-profiles",
    "browser-profile-backups", "state-snapshots", "backups", "checkpoints",
    "node_modules", "__pycache__", ".cache", ".git",
}


def iter_profile_files(profile: str, mode: str) -> Iterable[tuple[Path, Path]]:
    home = Path("/root/.hermes/profiles") / profile
    if not home.is_dir():
        raise RuntimeError(f"Hermes profile home is missing: {profile}")
    candidates: list[Path] = []
    if mode == "quick":
        roots = [home / rel for rel in QUICK_PROFILE_ENTRIES]
    else:
        roots = [home]
    for root in roots:
        if root.is_file():
            candidates.append(root)
            continue
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            current = Path(dirpath)
            dirnames[:] = [name for name in dirnames if name not in PROFILE_SKIP_DIRS]
            for filename in filenames:
                candidates.append(current / filename)
    seen: set[Path] = set()
    for path in candidates:
        if not path.is_file() or path.is_symlink() or path in seen:
            continue
        if path.name.endswith((".db-wal", ".db-shm", ".db-journal", ".pyc", ".pyo")):
            continue
        seen.add(path)
        yield path, path.relative_to(home)


def run_hermes_backup(profile: str, mode: str, output: Path) -> dict[str, Any]:
    rows = list(iter_profile_files(profile, mode))
    with tempfile.TemporaryDirectory(prefix=f"mgs-profile-{profile}-", dir=str(output.parent)) as raw:
        scratch = Path(raw)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for source, rel in rows:
                if source.suffix == ".db":
                    snapshot = scratch / (hashlib.sha256(str(source).encode()).hexdigest() + ".db")
                    try:
                        sqlite_snapshot(source, snapshot)
                        archive.write(snapshot, rel.as_posix())
                    finally:
                        snapshot.unlink(missing_ok=True)
                else:
                    archive_write_if_present(archive, source, rel.as_posix())
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"Hermes backup did not create {output}")
    safe_zip(output)
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
    markers = {Path(name).name for name in names}
    if not markers.intersection({"config.yaml", "state.db", ".env"}):
        raise RuntimeError(f"Hermes backup for {profile} has no expected state marker")
    return {
        "component": f"hermes-{profile}",
        "filename": output.name,
        "size_bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "member_count": len(names),
    }


def is_skipped_rel(rel: Path) -> bool:
    parts = rel.parts
    if any(part in GLOBAL_SKIP_DIRS for part in parts):
        return True
    posix = rel.as_posix()
    if any(posix == prefix or posix.startswith(prefix + "/") for prefix in DATA_SKIP_PREFIXES):
        return True
    if rel.name.startswith(".env.bak"):
        return True
    if rel.suffix in {".pyc", ".pyo", ".log"}:
        return True
    return False


def iter_mgs_files(mode: str) -> Iterable[tuple[Path, Path]]:
    seen: set[Path] = set()
    if mode == "quick":
        candidates = [REPO / rel for rel in QUICK_FILES]
    else:
        candidates = [REPO / rel for rel in FULL_FILES]
        for dirname in FULL_DIRS:
            root = REPO / dirname
            if not root.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
                current = Path(dirpath)
                rel_dir = current.relative_to(REPO)
                dirnames[:] = [
                    name for name in dirnames
                    if not is_skipped_rel(rel_dir / name)
                ]
                for filename in filenames:
                    candidates.append(current / filename)
        candidates.append(REPO / "logs/events-audit.jsonl")
    for path in candidates:
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(REPO)
        if is_skipped_rel(rel):
            continue
        if rel.parts and rel.parts[0] == "data" and rel.suffix.lower() not in MGS_DATA_SUFFIXES:
            continue
        if path in seen:
            continue
        seen.add(path)
        yield path, Path("mgs-agent") / rel


def sqlite_snapshot(src: Path, dst: Path) -> None:
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def add_runtime_metadata(archive: zipfile.ZipFile) -> None:
    cron = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False).stdout
    archive.writestr("mgs-agent/runtime/root.crontab", cron)
    unit_dir = Path("/etc/systemd/system")
    patterns = ("zeus*.service", "atena*.service", "ares*.service", "mgs*.service")
    units: set[Path] = set()
    for pattern in patterns:
        units.update(unit_dir.glob(pattern))
    for unit in sorted(units):
        if unit.is_file() and not unit.is_symlink():
            archive_write_if_present(archive, unit, "mgs-agent/runtime/systemd/" + unit.name)


def build_mgs_zip(mode: str, output: Path, scratch: Path) -> dict[str, Any]:
    entries = list(iter_mgs_files(mode))
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for source, arcname in entries:
            if source.suffix.lower() in {".db", ".sqlite"}:
                snapshot = scratch / (hashlib.sha256(str(source).encode()).hexdigest() + source.suffix)
                try:
                    sqlite_snapshot(source, snapshot)
                    archive.write(snapshot, arcname.as_posix())
                finally:
                    snapshot.unlink(missing_ok=True)
            else:
                archive_write_if_present(archive, source, arcname.as_posix())
        add_runtime_metadata(archive)
        git_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False
        ).stdout.strip()
        archive.writestr(
            "mgs-agent/runtime/backup-source.json",
            json.dumps({"created_at_utc": iso_now(), "mode": mode, "git_head": git_head}, indent=2) + "\n",
        )
    safe_zip(output)
    return {
        "component": "mgs-agent",
        "filename": output.name,
        "size_bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "member_count": len(entries) + 2,
    }


def build_bundle(mode: str, work: Path, config: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    components: list[dict[str, Any]] = []
    component_paths: list[Path] = []
    for profile in config["profiles"]:
        path = work / f"hermes-{profile}-{mode}.zip"
        components.append(run_hermes_backup(profile, mode, path))
        component_paths.append(path)
    mgs_zip = work / f"mgs-agent-{mode}.zip"
    components.append(build_mgs_zip(mode, mgs_zip, work))
    component_paths.append(mgs_zip)
    manifest = {
        "schema_version": 1,
        "created_at_utc": iso_now(),
        "mode": mode,
        "profiles": config["profiles"],
        "components": components,
    }
    bundle = work / f"mgs-dr-{mode}-bundle.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_STORED) as archive:
        for component in component_paths:
            archive.write(component, component.name)
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    safe_zip(bundle)
    manifest["bundle_size_bytes"] = bundle.stat().st_size
    manifest["bundle_sha256"] = sha256_file(bundle)
    return bundle, manifest


def encrypt_bundle(bundle: Path, output: Path, config: dict[str, Any], work: Path) -> str:
    public_key = Path(config["public_key_path"])
    if not public_key.is_file():
        raise RuntimeError("versioned disaster-recovery public key is missing")
    gnupg = work / "gnupg-public"
    gnupg.mkdir(mode=0o700)
    subprocess.run(["gpg", "--homedir", str(gnupg), "--batch", "--import", str(public_key)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    listing = subprocess.run(
        ["gpg", "--homedir", str(gnupg), "--batch", "--with-colons", "--list-keys"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout
    fingerprint = next((line.split(":")[9] for line in listing.splitlines() if line.startswith("fpr:")), "")
    if len(fingerprint) != 40:
        raise RuntimeError("could not resolve disaster-recovery public-key fingerprint")
    subprocess.run(
        [
            "gpg", "--homedir", str(gnupg), "--batch", "--yes", "--trust-model", "always",
            "--recipient", fingerprint, "--output", str(output), "--encrypt", str(bundle),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=True,
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("GPG did not create encrypted archive")
    return fingerprint


def drive_client(config: dict[str, Any]) -> Drive:
    return Drive(drive_access_token(service_account(config)))


def validate_drive_root(drive: Drive, config: dict[str, Any]) -> dict[str, Any]:
    meta = drive.metadata(config["drive_root_id"])
    if meta.get("driveId") != config["drive_root_id"] or meta.get("trashed") is True:
        raise RuntimeError("configured backup destination is not the canonical live Shared Drive")
    if not (meta.get("capabilities") or {}).get("canAddChildren"):
        raise RuntimeError("Drive credential cannot add backup children")
    return meta


def state_load(config: dict[str, Any]) -> dict[str, Any]:
    path = Path(config["state_path"])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {"schema_version": 1, "last_success": {}, "last_restore_test": {}}
    data.setdefault("schema_version", 1)
    data.setdefault("last_success", {})
    data.setdefault("last_restore_test", {})
    return data


def apply_retention(drive: Drive, folder_id: str, keep: int) -> list[str]:
    files = sorted(drive.list_managed(folder_id), key=lambda row: row.get("createdTime", ""), reverse=True)
    trashed: list[str] = []
    for row in files[keep:]:
        if (row.get("appProperties") or {}).get("mgs_dr") != "true":
            continue
        result = drive.trash(row["id"])
        if result.get("trashed") is not True:
            raise RuntimeError(f"Drive retention readback failed for {row['id']}")
        trashed.append(row["id"])
    return trashed


def acquire_lock(config: dict[str, Any]):
    path = Path(config["lock_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise RuntimeError("another MGS off-site backup or restore is already running")
    return handle


def backup(mode: str) -> dict[str, Any]:
    config = load_config()
    lock = acquire_lock(config)
    started = time.monotonic()
    try:
        now = utcnow()
        tier = "hourly" if mode == "quick" else classify_full_tier(now)
        with tempfile.TemporaryDirectory(prefix="mgs-dr-backup-", dir=str(REPO / "tmp")) as tmpdir:
            work = Path(tmpdir)
            bundle, manifest = build_bundle(mode, work, config)
            stamp = now.strftime("%Y%m%dT%H%M%SZ")
            encrypted = work / f"mgs-dr-{tier}-{stamp}.zip.gpg"
            fingerprint = encrypt_bundle(bundle, encrypted, config, work)
            encrypted_sha = sha256_file(encrypted)
            encrypted_md5 = md5_file(encrypted)
            drive = drive_client(config)
            root_meta = validate_drive_root(drive, config)
            dr_root = drive.ensure_folder(config["drive_root_id"], config["drive_folder_name"], "root")
            tier_folder = drive.ensure_folder(dr_root, tier, tier)
            uploaded = drive.upload_resumable(tier_folder, encrypted, tier=tier, mode=mode, sha256=encrypted_sha)
            readback = drive.metadata(uploaded["id"])
            if readback.get("parents") != [tier_folder] or readback.get("driveId") != config["drive_root_id"]:
                raise RuntimeError("Drive upload placement readback mismatch")
            if int(readback.get("size") or 0) != encrypted.stat().st_size:
                raise RuntimeError("Drive upload size readback mismatch")
            if readback.get("md5Checksum") != encrypted_md5:
                raise RuntimeError("Drive upload MD5 readback mismatch")
            if (readback.get("appProperties") or {}).get("sha256") != encrypted_sha:
                raise RuntimeError("Drive upload SHA-256 property readback mismatch")
            trashed = apply_retention(drive, tier_folder, int(config["retention_count"][tier]))
            result = {
                "status": "PASS",
                "mode": mode,
                "tier": tier,
                "created_at_utc": iso_now(),
                "duration_seconds": round(time.monotonic() - started, 3),
                "remote_file_id": readback["id"],
                "remote_name": readback["name"],
                "remote_size_bytes": int(readback["size"]),
                "encrypted_sha256": encrypted_sha,
                "encrypted_md5": encrypted_md5,
                "public_key_fingerprint": fingerprint,
                "drive_id": root_meta["driveId"],
                "tier_folder_id": tier_folder,
                "retention_trashed_count": len(trashed),
                "bundle": manifest,
            }
            state = state_load(config)
            state["last_success"][mode] = result
            state["updated_at_utc"] = iso_now()
            atomic_json(Path(config["state_path"]), state)
            append_event(config, "backup_success", mode=mode, tier=tier, remote_file_id=readback["id"], size_bytes=int(readback["size"]), sha256=encrypted_sha, retention_trashed_count=len(trashed))
            return result
    except Exception as exc:
        append_event(config, "backup_failure", mode=mode, error_type=type(exc).__name__, error=str(exc)[:500])
        raise
    finally:
        lock.close()


def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        try:
            target.relative_to(destination)
        except ValueError as exc:
            raise RuntimeError(f"unsafe restore member: {member.filename}") from exc
    archive.extractall(destination)


def sqlite_check(path: Path, *, repair_derived_fts: bool = False) -> list[str]:
    connection = sqlite3.connect(path if repair_derived_fts else f"file:{path}?mode=ro", uri=not repair_derived_fts)
    repaired: list[str] = []
    try:
        row = connection.execute("PRAGMA quick_check").fetchone()
        result = row[0] if row else "missing quick_check result"
        if result == "ok":
            return repaired
        if repair_derived_fts and "malformed inverted index for FTS5 table" in result:
            tables = [
                record[0]
                for record in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND sql LIKE 'CREATE VIRTUAL TABLE%USING fts5%'"
                )
            ]
            for table in tables:
                quoted = table.replace('"', '""')
                connection.execute(f'INSERT INTO "{quoted}"("{quoted}") VALUES (\'rebuild\')')
                repaired.append(table)
            connection.commit()
            row = connection.execute("PRAGMA quick_check").fetchone()
            result = row[0] if row else "missing post-rebuild quick_check result"
            if result == "ok":
                return repaired
        raise RuntimeError(f"SQLite integrity check failed: {path.name}: {result}")
    finally:
        connection.close()


def validate_restored_profile(profile: str, component_zip: Path, root: Path) -> dict[str, Any]:
    target = root / f"hermes-{profile}"
    env = dict(os.environ)
    env["HERMES_HOME"] = str(target)
    proc = subprocess.run(
        [str(HERMES), "import", str(component_zip), "--force"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=900,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"isolated Hermes import failed for {profile}: rc={proc.returncode}")
    markers = [target / "config.yaml", target / "state.db"]
    if not any(path.exists() for path in markers):
        raise RuntimeError(f"isolated Hermes import for {profile} has no expected marker")
    dbs = list(target.rglob("*.db"))
    repaired_fts: list[str] = []
    for db in dbs:
        repaired_fts.extend(sqlite_check(db, repair_derived_fts=True))
    return {
        "profile": profile,
        "imported": True,
        "sqlite_checked": len(dbs),
        "derived_fts_rebuilt": sorted(set(repaired_fts)),
        "target_markers": sum(path.exists() for path in markers),
    }


def restore_test(remote_id: str | None = None) -> dict[str, Any]:
    config = load_config()
    lock = acquire_lock(config)
    started = time.monotonic()
    try:
        state = state_load(config)
        if not remote_id:
            full = state.get("last_success", {}).get("full") or {}
            quick = state.get("last_success", {}).get("quick") or {}
            remote_id = full.get("remote_file_id") or quick.get("remote_file_id")
        if not remote_id:
            raise RuntimeError("no successful remote backup is available for restore test")
        with tempfile.TemporaryDirectory(prefix="mgs-dr-restore-", dir=str(REPO / "tmp")) as tmpdir:
            work = Path(tmpdir)
            drive = drive_client(config)
            validate_drive_root(drive, config)
            remote = drive.metadata(remote_id)
            if (remote.get("appProperties") or {}).get("mgs_dr") != "true" or remote.get("trashed") is True:
                raise RuntimeError("restore target is not a live managed MGS DR backup")
            encrypted = work / remote["name"]
            drive.download(remote_id, encrypted)
            if encrypted.stat().st_size != int(remote.get("size") or 0):
                raise RuntimeError("downloaded backup size mismatch")
            if md5_file(encrypted) != remote.get("md5Checksum"):
                raise RuntimeError("downloaded backup MD5 mismatch")
            expected_sha = (remote.get("appProperties") or {}).get("sha256")
            if not expected_sha or sha256_file(encrypted) != expected_sha:
                raise RuntimeError("downloaded backup SHA-256 mismatch")
            private_key = private_backup_key(config)
            gnupg = work / "gnupg-private"
            gnupg.mkdir(mode=0o700)
            key_file = work / "private.asc"
            key_file.write_text(private_key, encoding="utf-8")
            os.chmod(key_file, 0o600)
            subprocess.run(["gpg", "--homedir", str(gnupg), "--batch", "--import", str(key_file)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            key_file.unlink(missing_ok=True)
            bundle = work / "bundle.zip"
            subprocess.run(
                ["gpg", "--homedir", str(gnupg), "--batch", "--yes", "--output", str(bundle), "--decrypt", str(encrypted)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
            )
            safe_zip(bundle)
            extracted = work / "bundle"
            extracted.mkdir()
            with zipfile.ZipFile(bundle) as archive:
                safe_extract(archive, extracted)
            manifest = json.loads((extracted / "manifest.json").read_text(encoding="utf-8"))
            component_results: list[dict[str, Any]] = []
            for component in manifest.get("components", []):
                path = extracted / component["filename"]
                if not path.is_file() or path.stat().st_size != int(component["size_bytes"]):
                    raise RuntimeError(f"restore component size mismatch: {component['component']}")
                if sha256_file(path) != component["sha256"]:
                    raise RuntimeError(f"restore component SHA mismatch: {component['component']}")
                safe_zip(path)
            isolated = work / "isolated"
            isolated.mkdir()
            for profile in config["profiles"]:
                component = next(row for row in manifest["components"] if row["component"] == f"hermes-{profile}")
                component_results.append(validate_restored_profile(profile, extracted / component["filename"], isolated))
            mgs_component = next(row for row in manifest["components"] if row["component"] == "mgs-agent")
            mgs_root = isolated / "mgs"
            mgs_root.mkdir()
            with zipfile.ZipFile(extracted / mgs_component["filename"]) as archive:
                safe_extract(archive, mgs_root)
            restored_repo = mgs_root / "mgs-agent"
            if not (restored_repo / "context/mgs-os-map.md").is_file():
                raise RuntimeError("restored MGS OS map is missing")
            dbs = list(restored_repo.rglob("*.db")) + list(restored_repo.rglob("*.sqlite"))
            for db in dbs:
                sqlite_check(db)
            knowledge_validation = "not_applicable"
            knowledge_tool = restored_repo / "scripts/mgs-knowledge-control.py"
            if knowledge_tool.is_file():
                proc = subprocess.run(
                    [sys.executable, str(knowledge_tool), "--root", str(restored_repo), "validate"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=120,
                    check=False,
                )
                if proc.returncode != 0:
                    raise RuntimeError("restored MGS knowledge validation failed")
                knowledge_validation = "PASS"
            result = {
                "status": "PASS",
                "tested_at_utc": iso_now(),
                "duration_seconds": round(time.monotonic() - started, 3),
                "remote_file_id": remote_id,
                "remote_name": remote["name"],
                "remote_size_bytes": int(remote["size"]),
                "download_sha256": expected_sha,
                "bundle_mode": manifest.get("mode"),
                "components_validated": len(manifest.get("components", [])),
                "profiles": component_results,
                "mgs_sqlite_checked": len(dbs),
                "knowledge_validation": knowledge_validation,
                "isolated_only": True,
            }
            state = state_load(config)
            state["last_restore_test"] = result
            state["updated_at_utc"] = iso_now()
            atomic_json(Path(config["state_path"]), state)
            append_event(config, "restore_test_success", remote_file_id=remote_id, bundle_mode=manifest.get("mode"), components=len(manifest.get("components", [])), duration_seconds=result["duration_seconds"])
            return result
    except Exception as exc:
        append_event(config, "restore_test_failure", remote_file_id=remote_id or "", error_type=type(exc).__name__, error=str(exc)[:500])
        raise
    finally:
        lock.close()


def parse_iso(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


def monitor() -> tuple[bool, list[str]]:
    config = load_config()
    state = state_load(config)
    now = utcnow()
    issues: list[str] = []
    quick = state.get("last_success", {}).get("quick") or {}
    full = state.get("last_success", {}).get("full") or {}
    restore = state.get("last_restore_test") or {}
    if not quick.get("created_at_utc"):
        issues.append("nenhum backup horário aprovado")
    elif (now - parse_iso(quick["created_at_utc"])).total_seconds() > float(config["monitor"]["max_quick_age_hours"]) * 3600:
        issues.append("backup horário acima do RPO")
    if not full.get("created_at_utc"):
        issues.append("nenhum backup completo aprovado")
    elif (now - parse_iso(full["created_at_utc"])).total_seconds() > float(config["monitor"]["max_full_age_hours"]) * 3600:
        issues.append("backup completo atrasado")
    if not restore.get("tested_at_utc"):
        issues.append("nenhum restore test aprovado")
    elif (now - parse_iso(restore["tested_at_utc"])).total_seconds() > float(config["monitor"]["max_restore_age_days"]) * 86400:
        issues.append("restore test vencido")
    return not issues, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="MGS encrypted off-site backup and restore drill")
    sub = parser.add_subparsers(dest="command", required=True)
    backup_parser = sub.add_parser("backup")
    backup_parser.add_argument("--mode", choices=("quick", "full"), required=True)
    restore_parser = sub.add_parser("restore-test")
    restore_parser.add_argument("--remote-id")
    sub.add_parser("monitor")
    sub.add_parser("status")
    args = parser.parse_args()
    try:
        if args.command == "backup":
            result = backup(args.mode)
            print(json.dumps({k: result[k] for k in ("status", "mode", "tier", "remote_file_id", "remote_name", "remote_size_bytes", "duration_seconds", "retention_trashed_count")}, ensure_ascii=False))
        elif args.command == "restore-test":
            result = restore_test(args.remote_id)
            print(json.dumps(result, ensure_ascii=False))
        elif args.command == "monitor":
            healthy, issues = monitor()
            if not healthy:
                print("[MGS-DR-ALERT] <@344196393512075265> Backup/recuperação fora do SLA: " + "; ".join(issues) + ". Zeus investigará a rotina.")
        elif args.command == "status":
            config = load_config()
            healthy, issues = monitor()
            state = state_load(config)
            print(json.dumps({"healthy": healthy, "issues": issues, "state": state}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:500]}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
