#!/usr/bin/env python3
"""Canonical MGS Google Workspace Service Account authentication helper.

Loads the Service Account JSON from 1Password, creates a short-lived OAuth2 JWT
access token, and optionally validates Drive/Sheets access without printing any
credential material. Import ``service_account_access_token`` from operational
scripts; the CLI is diagnostics-only and never emits the token.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

BASE = Path("/root/mgs-agent")
DEFAULT_VAULT = os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
DEFAULT_ITEM = os.environ.get("MGS_GOOGLE_SERVICE_ACCOUNT_ITEM", "Google Service Account - Ares Drive")
TOKEN_URI = "https://oauth2.googleapis.com/token"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def load_env(path: Path = BASE / ".env") -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _op_item_json(item: str, vault: str, attempts: int = 4) -> dict[str, Any]:
    last_error = "op_item_unreadable"
    for attempt in range(1, attempts + 1):
        try:
            proc = subprocess.run(
                ["op", "item", "get", item, "--vault", vault, "--format", "json", "--reveal"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=45,
            )
            if proc.returncode == 0:
                value = json.loads(proc.stdout)
                if isinstance(value, dict):
                    return value
            last_error = "op_item_unreadable"
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            last_error = "op_item_read_failed"
        if attempt < attempts:
            time.sleep(attempt)
    raise RuntimeError(last_error)


def load_service_account(item: str | None = None, vault: str | None = None) -> dict[str, Any]:
    load_env()
    item = item or os.environ.get("MGS_GOOGLE_SERVICE_ACCOUNT_ITEM", DEFAULT_ITEM)
    vault = vault or os.environ.get("OP_DEFAULT_VAULT", DEFAULT_VAULT)
    obj = _op_item_json(item, vault)
    candidates: list[str] = []
    for field in obj.get("fields") or []:
        value = field.get("value")
        if value:
            candidates.append(str(value))
    for raw in candidates:
        if "private_key" not in raw or "client_email" not in raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        required = ("client_email", "private_key")
        if all(data.get(k) for k in required):
            return data
    raise RuntimeError("service_account_json_not_found")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _normalize_scopes(scopes: str | Iterable[str] | None) -> str:
    if scopes is None:
        return f"{DRIVE_SCOPE} {SHEETS_SCOPE}"
    if isinstance(scopes, str):
        return " ".join(scopes.split())
    return " ".join(str(scope).strip() for scope in scopes if str(scope).strip())


def service_account_access_token(
    scopes: str | Iterable[str] | None = None,
    *,
    item: str | None = None,
    vault: str | None = None,
) -> str:
    """Return a short-lived Service Account access token without logging it."""
    sa = load_service_account(item=item, vault=vault)
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {
        "iss": sa["client_email"],
        "scope": _normalize_scopes(scopes),
        "aud": sa.get("token_uri") or TOKEN_URI,
        "iat": now,
        "exp": now + 3600,
    }
    signing_input = (
        _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + _b64url(json.dumps(claim, separators=(",", ":")).encode("utf-8"))
    ).encode("ascii")
    key = serialization.load_pem_private_key(sa["private_key"].encode("utf-8"), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise RuntimeError("private_key_not_rsa")
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    assertion = signing_input.decode("ascii") + "." + _b64url(signature)
    payload = urllib.parse.urlencode(
        {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}
    ).encode("utf-8")
    req = urllib.request.Request(
        sa.get("token_uri") or TOKEN_URI,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "MGS-Google-SA/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8", "replace"))
    token = body.get("access_token")
    if not token:
        raise RuntimeError("service_account_access_token_missing")
    return str(token)


def api_json(method: str, url: str, token: str, payload: Any = None) -> tuple[int, dict[str, Any]]:
    body = None
    headers = {"Authorization": "Bearer " + token, "User-Agent": "MGS-Google-SA/1.0"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=UTF-8"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"error": {"status": "HTTP_ERROR", "message": raw[:500]}}
        return exc.code, data
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        return 0, {"error": {"status": type(exc).__name__}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate MGS Google Service Account access without printing tokens.")
    parser.add_argument("--check-drive-id")
    parser.add_argument("--check-sheet-id")
    args = parser.parse_args()
    scopes = []
    if args.check_drive_id:
        scopes.append(DRIVE_SCOPE)
    if args.check_sheet_id:
        scopes.append(SHEETS_SCOPE)
    token = service_account_access_token(scopes or None)
    result: dict[str, Any] = {"token_created": True}
    ok = True
    if args.check_drive_id:
        fields = urllib.parse.quote("id,name,driveId,trashed,capabilities(canEdit,canModifyContent)", safe=",()")
        status, data = api_json(
            "GET",
            f"https://www.googleapis.com/drive/v3/files/{args.check_drive_id}?supportsAllDrives=true&fields={fields}",
            token,
        )
        caps = data.get("capabilities") or {}
        result["drive"] = {
            "http": status,
            "accessible": status == 200,
            "can_edit": bool(caps.get("canEdit")),
            "can_modify": bool(caps.get("canModifyContent")),
        }
        ok = ok and status == 200 and bool(caps.get("canEdit")) and bool(caps.get("canModifyContent"))
    if args.check_sheet_id:
        status, data = api_json(
            "GET",
            f"https://sheets.googleapis.com/v4/spreadsheets/{args.check_sheet_id}?fields=spreadsheetId",
            token,
        )
        error = data.get("error") or {}
        result["sheets"] = {"http": status, "accessible": status == 200, "status": error.get("status")}
        ok = ok and status == 200
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
