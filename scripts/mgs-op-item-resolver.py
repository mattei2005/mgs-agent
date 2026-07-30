#!/usr/bin/env python3
"""Shared 1Password item resolver for MGS recurring jobs.

Caches only non-secret metadata (vault/item IDs, titles and DTR usernames).
Credential values are fetched as one full item per operation and stay in memory.
"""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

CACHE_DIR = Path(os.environ.get("MGS_OP_METADATA_CACHE_DIR", "/root/.cache/mgs/1password-metadata"))
INDEX_PATH = CACHE_DIR / "item-index.json"
DTR_MAP_PATH = CACHE_DIR / "dtr-user-item-map.json"
INDEX_LOCK_PATH = CACHE_DIR / ".index-refresh.lock"
DTR_LOCK_PATH = CACHE_DIR / ".dtr-refresh.lock"
CACHE_SCHEMA = 2
LOCK_TIMEOUT = int(os.environ.get("MGS_OP_METADATA_LOCK_TIMEOUT_SECONDS", "120"))
INDEX_MAX_AGE = int(os.environ.get("MGS_OP_ITEM_INDEX_MAX_AGE_SECONDS", "86400"))
DTR_MAP_MAX_AGE = int(os.environ.get("MGS_OP_DTR_MAP_MAX_AGE_SECONDS", "86400"))


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(CACHE_DIR, 0o700)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_cache_dir()
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=CACHE_DIR)
    tmp = Path(tmp_name)
    os.fchmod(fd, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _read_cache(path: Path, vault: str) -> dict[str, Any] | None:
    try:
        st = path.stat()
        if st.st_mode & 0o077:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != CACHE_SCHEMA or data.get("vault") != vault:
            return None
        return data
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _read_fresh(path: Path, max_age: int, vault: str) -> dict[str, Any] | None:
    data = _read_cache(path, vault)
    if not data:
        return None
    try:
        age = time.time() - float(data.get("updated_at_epoch") or 0)
        return data if 0 <= age <= max_age else None
    except (ValueError, TypeError):
        return None


def _lock_file(path: Path):
    _ensure_cache_dir()
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, "r+")


def _acquire_lock(lock, timeout: int = LOCK_TIMEOUT) -> None:
    deadline = time.monotonic() + max(1, timeout)
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"1Password metadata refresh lock timed out after {timeout}s")
            time.sleep(0.2)


def _op_json(args: list[str], timeout: int = 90) -> Any:
    proc = subprocess.run(
        ["op", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        env=os.environ.copy(),
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "op command failed").strip().replace("\n", " ")[:240]
        raise RuntimeError(f"1Password command failed: {detail}")
    return json.loads(proc.stdout)


def get_vault_index(vault: str | None = None, force_refresh: bool = False) -> dict[str, Any]:
    vault = vault or os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
    if not force_refresh:
        cached = _read_fresh(INDEX_PATH, INDEX_MAX_AGE, vault)
        if cached:
            return cached
    with _lock_file(INDEX_LOCK_PATH) as lock:
        try:
            _acquire_lock(lock)
        except TimeoutError:
            stale = None if force_refresh else _read_cache(INDEX_PATH, vault)
            if stale:
                return stale
            raise
        if not force_refresh:
            cached = _read_fresh(INDEX_PATH, INDEX_MAX_AGE, vault)
            if cached:
                return cached
        vault_obj = _op_json(["vault", "get", vault, "--format", "json"])
        vault_id = str(vault_obj.get("id") or "").strip()
        if not vault_id:
            raise RuntimeError("1Password vault ID not returned")
        rows = _op_json(["item", "list", "--vault", vault_id, "--format", "json"])
        items: dict[str, dict[str, str]] = {}
        duplicate_titles: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            title = str(row.get("title") or "").strip()
            item_id = str(row.get("id") or row.get("uuid") or "").strip()
            if title and item_id and (
                "digitaltrchat" in title.casefold()
                or (title.startswith("BOT B") and title.endswith(" Token"))
            ):
                entry = {"id": item_id, "title": title}
                if title in items:
                    duplicate_titles[title] = [items.pop(title), entry]
                elif title in duplicate_titles:
                    duplicate_titles[title].append(entry)
                else:
                    items[title] = entry
        payload = {
            "schema": CACHE_SCHEMA,
            "vault": vault,
            "vault_id": vault_id,
            "updated_at_epoch": int(time.time()),
            "items": items,
            # Exact duplicate titles are omitted from title resolution. Callers
            # must pin the intended immutable item ID instead of silently using
            # whichever duplicate happened to be returned last by 1Password.
            "duplicate_titles": duplicate_titles,
        }
        _atomic_json(INDEX_PATH, payload)
        return payload


def _is_not_found_error(exc: Exception) -> bool:
    text = str(exc).casefold()
    return any(marker in text for marker in ("not found", "isn't an item", "could not find", "does not exist"))


def get_item_json(
    item_ref: str,
    vault: str | None = None,
    index: dict[str, Any] | None = None,
    _retry_index: bool = True,
) -> dict[str, Any]:
    vault = vault or os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
    index = index or get_vault_index(vault)
    entry = (index.get("items") or {}).get(item_ref)
    item_id = str((entry or {}).get("id") or item_ref).strip()
    vault_id = str(index.get("vault_id") or "").strip()
    if not item_id or not vault_id:
        raise RuntimeError("1Password item/vault ID unavailable")
    try:
        return _op_json(["item", "get", item_id, "--vault", vault_id, "--format", "json", "--reveal"])
    except RuntimeError as exc:
        if not (_retry_index and entry and _is_not_found_error(exc)):
            raise
        refreshed = get_vault_index(vault, force_refresh=True)
        refreshed_entry = (refreshed.get("items") or {}).get(item_ref)
        if not refreshed_entry:
            raise
        return get_item_json(item_ref, vault, refreshed, _retry_index=False)


def field_value(item: dict[str, Any], *names: str, required: bool = False) -> str:
    wanted = [str(name).strip().casefold() for name in names if str(name).strip()]
    values: dict[str, str] = {}
    for field in item.get("fields") or []:
        value = field.get("value")
        if value is None:
            continue
        for key in (field.get("label"), field.get("id")):
            norm = str(key or "").strip().casefold()
            if norm:
                values[norm] = str(value).strip()
    for name in wanted:
        if values.get(name):
            return values[name]
    if required:
        raise RuntimeError(f"1Password field missing: {'/'.join(names)}")
    return ""


def resolve_dtr_items(target_users: Iterable[str], vault: str | None = None, force_refresh: bool = False):
    vault = vault or os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
    targets = {str(user).strip().casefold() for user in target_users if str(user).strip()}
    if not force_refresh:
        cached = _read_fresh(DTR_MAP_PATH, DTR_MAP_MAX_AGE, vault)
        if cached:
            users = cached.get("users") or {}
            return {u: users[u] for u in targets if u in users}, sorted(targets - set(users)), [], cached

    index = get_vault_index(vault, force_refresh=force_refresh)
    with _lock_file(DTR_LOCK_PATH) as lock:
        try:
            _acquire_lock(lock)
        except TimeoutError:
            stale = None if force_refresh else _read_cache(DTR_MAP_PATH, vault)
            if stale:
                users = stale.get("users") or {}
                return {u: users[u] for u in targets if u in users}, sorted(targets - set(users)), [], stale
            raise
        if not force_refresh:
            cached = _read_fresh(DTR_MAP_PATH, DTR_MAP_MAX_AGE, vault)
            if cached:
                users = cached.get("users") or {}
                return {u: users[u] for u in targets if u in users}, sorted(targets - set(users)), [], cached

        candidates = [
            entry for title, entry in (index.get("items") or {}).items()
            if "digitaltrchat" in title.casefold()
        ]
        users: dict[str, dict[str, str]] = {}
        errors: list[dict[str, str]] = []
        for entry in sorted(candidates, key=lambda row: row["title"].casefold()):
            try:
                item = get_item_json(entry["id"], vault, index)
                username = field_value(item, "username", "user", "email").casefold()
                if username and username not in users:
                    users[username] = {"id": entry["id"], "title": entry["title"]}
            except Exception as exc:
                errors.append({"item": entry["title"], "error": type(exc).__name__})
        payload = {
            "schema": CACHE_SCHEMA,
            "vault": vault,
            "vault_id": index.get("vault_id"),
            "updated_at_epoch": int(time.time()),
            "candidate_count": len(candidates),
            "users": users,
        }
        _atomic_json(DTR_MAP_PATH, payload)
        return {u: users[u] for u in targets if u in users}, sorted(targets - set(users)), errors, payload


def get_login_bundle(item_ref: str, vault: str | None = None, index: dict[str, Any] | None = None) -> dict[str, str]:
    item = get_item_json(item_ref, vault, index)
    username = field_value(item, "username", "user", "email", required=True)
    password = field_value(item, "credential", "password", required=True)
    return {"username": username, "password": password}
