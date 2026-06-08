#!/usr/bin/env python3
"""Initialize Ares Google Drive user OAuth via Google's device flow.

Prereq in 1Password item "Google OAuth - Ares Drive": fields client_id and
client_secret from a Google OAuth Client of type "TVs and Limited Input devices".
This script prints only the Google verification URL/code, polls for completion,
and saves refresh_token back into 1Password without printing it.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_VAULT = os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
DEFAULT_ITEM = os.environ.get("ARES_DRIVE_OAUTH_OP_ITEM", "Google OAuth - Ares Drive")
SCOPES = "https://www.googleapis.com/auth/drive"


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
        raise RuntimeError(f"1Password item not found/readable: {item_name}. Create it with fields client_id and client_secret. Detail: {proc.stderr[:300]}")
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


def save_refresh_token(item_name: str, vault: str, refresh_token: str) -> None:
    # Use stdin/template instead of assignment args so the token is never exposed
    # in process argv and special characters cannot break op's field parser.
    proc = subprocess.run(["op", "item", "edit", item_name, "--vault", vault, "refresh_token[password]"], input=json.dumps({"value": refresh_token}), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0:
        # Fallback to assignment syntax. The token may appear in argv briefly, but
        # this keeps the one-time OAuth flow recoverable if stdin JSON is not
        # accepted by the installed op CLI version.
        proc = subprocess.run(["op", "item", "edit", item_name, "--vault", vault, f"refresh_token[password]={refresh_token}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"failed to save refresh_token to 1Password: {proc.stderr[:300]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", default=DEFAULT_ITEM)
    ap.add_argument("--vault", default=os.environ.get("OP_DEFAULT_VAULT", DEFAULT_VAULT))
    ap.add_argument("--scope", default=SCOPES)
    args = ap.parse_args()

    load_env()
    vault = os.environ.get("OP_DEFAULT_VAULT") or args.vault or DEFAULT_VAULT
    item = op_item_json(args.item, vault)
    creds = item_fields(item)
    missing = [k for k in ("client_id", "client_secret") if not creds.get(k)]
    if missing:
        raise RuntimeError(f"OAuth item {args.item} missing fields: {', '.join(missing)}")

    device = post_form("https://oauth2.googleapis.com/device/code", {
        "client_id": creds["client_id"],
        "scope": args.scope,
    })
    if device.get("error"):
        raise RuntimeError("device authorization failed: " + json.dumps(device, ensure_ascii=False))

    print("Open this Google URL and approve Drive access for the personal account that owns MGS-CRIATIVOS:")
    print(device.get("verification_url") or device.get("verification_uri"))
    print("Code:", device["user_code"])
    print("Waiting for approval; no tokens will be printed.", flush=True)

    interval = int(device.get("interval", 5))
    deadline = time.time() + int(device.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(interval)
        token = post_form("https://oauth2.googleapis.com/token", {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "device_code": device["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        err = token.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        if err:
            raise RuntimeError("token exchange failed: " + json.dumps(token, ensure_ascii=False))
        refresh_token = token.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("Google did not return refresh_token; revoke prior grant or use prompt/consent flow with offline access")
        save_refresh_token(args.item, vault, refresh_token)
        print(f"OAuth ready: refresh_token saved to 1Password item '{args.item}' (len={len(refresh_token)}).")
        return 0

    raise RuntimeError("authorization timed out before approval")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ERROR:", str(exc), file=sys.stderr)
        raise SystemExit(2)
