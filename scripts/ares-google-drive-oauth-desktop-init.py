#!/usr/bin/env python3
"""Initialize Ares Google Drive user OAuth via Desktop/loopback flow.

Use when Device Flow cannot request the full Drive scope. This script prints an
authorization URL. Rodolfo opens it locally, Google redirects to localhost, and
he copies only the short-lived `code` query param back to Zeus. The script then
exchanges the code and saves the refresh token to 1Password when possible, or to
/root/mgs-agent/.secrets/ares-google-drive-oauth.json (0600, gitignored).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_VAULT = os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
DEFAULT_ITEM = os.environ.get("ARES_DRIVE_OAUTH_OP_ITEM", "Google OAuth - Ares Drive")
TOKEN_FILE = os.environ.get("ARES_DRIVE_OAUTH_TOKEN_FILE", "/root/mgs-agent/.secrets/ares-google-drive-oauth.json")
CLIENT_TOKEN_FILE = os.environ.get("ARES_DRIVE_OAUTH_CLIENT_TOKEN_FILE", "/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json")
SCOPES = "https://www.googleapis.com/auth/drive"
REDIRECT_URI = "http://localhost:53682/"


def load_env(path: str = "/root/mgs-agent/.env") -> None:
    if not os.path.exists(path):
        return
    for line in Path(path).read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def op_item_json(item_name: str, vault: str) -> dict[str, Any]:
    proc = subprocess.run(["op", "item", "get", item_name, "--vault", vault, "--format", "json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"1Password item not found/readable: {item_name}. Detail: {proc.stderr[:300]}")
    return json.loads(proc.stdout)


def item_fields(item: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in item.get("fields", []):
        label = (field.get("label") or field.get("id") or "").lower().replace(" ", "_").replace("-", "_")
        val = field.get("value") or ""
        if label in {"client_id", "client_secret", "refresh_token"} and val:
            out[label] = val
        if val.strip().startswith("{"):
            try:
                obj = json.loads(val)
            except Exception:
                obj = {}
            for k in ("client_id", "client_secret", "refresh_token"):
                if obj.get(k):
                    out[k] = obj[k]
    return out


def post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="ignore")
        try:
            obj: dict[str, Any] = json.loads(raw)
        except Exception:
            obj = {"error": raw[:500]}
        obj["http_status"] = e.code
        return obj


def save_refresh_token(item_name: str, vault: str, refresh_token: str) -> str:
    import tempfile

    item = op_item_json(item_name, vault)
    fields = item.setdefault("fields", [])
    for field in fields:
        label = (field.get("label") or field.get("id") or "").lower().replace(" ", "_").replace("-", "_")
        if label == "refresh_token":
            field["value"] = refresh_token
            field["type"] = "CONCEALED"
            break
    else:
        fields.append({"label": "refresh_token", "type": "CONCEALED", "value": refresh_token})

    fd, template_path = tempfile.mkstemp(prefix="ares-oauth-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(item, f)
        proc = subprocess.run(["op", "item", "edit", item_name, "--vault", vault, "--template", template_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    finally:
        try:
            os.remove(template_path)
        except OSError:
            pass
    if proc.returncode == 0:
        client_path = Path(CLIENT_TOKEN_FILE)
        if client_path.exists():
            try:
                client_data = json.loads(client_path.read_text(encoding="utf-8"))
            except Exception:
                client_data = {}
            if isinstance(client_data, dict) and client_data.get("client_id") and client_data.get("client_secret"):
                client_data["refresh_token"] = refresh_token
                client_tmp = client_path.with_suffix(client_path.suffix + ".tmp")
                client_tmp.write_text(json.dumps(client_data, ensure_ascii=False), encoding="utf-8")
                os.chmod(client_tmp, 0o600)
                os.replace(client_tmp, client_path)
                os.chmod(client_path, 0o600)
                return "1password+client_file"
        return "1password"

    token_path = Path(TOKEN_FILE)
    token_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    tmp_path = token_path.with_suffix(token_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps({"refresh_token": refresh_token}, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, token_path)
    os.chmod(token_path, 0o600)

    # Keep the legacy upload credential file in sync. Existing upload scripts
    # read client_id/client_secret/refresh_token from this root-only JSON.
    client_path = Path(CLIENT_TOKEN_FILE)
    if client_path.exists():
        try:
            client_data = json.loads(client_path.read_text(encoding="utf-8"))
        except Exception:
            client_data = {}
        if isinstance(client_data, dict) and client_data.get("client_id") and client_data.get("client_secret"):
            client_data["refresh_token"] = refresh_token
            client_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            client_tmp = client_path.with_suffix(client_path.suffix + ".tmp")
            client_tmp.write_text(json.dumps(client_data, ensure_ascii=False), encoding="utf-8")
            os.chmod(client_tmp, 0o600)
            os.replace(client_tmp, client_path)
            os.chmod(client_path, 0o600)
            return "local_file+client_file"
    return "local_file"


def auth_url(client_id: str, scope: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def extract_code(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        q = urllib.parse.urlparse(raw).query
        code = urllib.parse.parse_qs(q).get("code", [""])[0]
        if code:
            return code
    return raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", default=DEFAULT_ITEM)
    ap.add_argument("--vault", default=os.environ.get("OP_DEFAULT_VAULT", DEFAULT_VAULT))
    ap.add_argument("--scope", default=SCOPES)
    ap.add_argument("--code", help="Short-lived OAuth code or full localhost redirect URL")
    args = ap.parse_args()

    load_env()
    vault = os.environ.get("OP_DEFAULT_VAULT") or args.vault or DEFAULT_VAULT
    item = op_item_json(args.item, vault)
    creds = item_fields(item)
    missing = [k for k in ("client_id", "client_secret") if not creds.get(k)]
    if missing:
        raise RuntimeError(f"OAuth item {args.item} missing fields: {', '.join(missing)}")

    if not args.code:
        print(auth_url(creds["client_id"], args.scope))
        return 0

    code = extract_code(args.code)
    token = post_form("https://oauth2.googleapis.com/token", {
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    })
    if token.get("error"):
        raise RuntimeError("token exchange failed: " + json.dumps(token, ensure_ascii=False))
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("Google did not return refresh_token; rerun auth URL with prompt=consent and approve again")
    target = save_refresh_token(args.item, vault, refresh_token)
    print(f"OAuth ready: refresh_token saved to {target} (len={len(refresh_token)}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ERROR:", str(exc), file=sys.stderr)
        raise SystemExit(2)
