#!/usr/bin/env python3
"""Unified Google Drive auth watchdog owned by Zeus.

Checks local user OAuth every cycle. The 1Password-backed Service Account is a
fallback and is refreshed at most once per 24h while user OAuth is healthy; it
is checked immediately if user OAuth fails. Alerts are posted by the local Zeus
bot, never by a 1Password webhook.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

BASE = Path("/root/mgs-agent")
TOKEN_FILE = Path(os.environ.get("MGS_DRIVE_OAUTH_TOKEN_FILE", str(BASE / ".secrets/ares-google-drive-oauth-client.json")))
STATE_FILE = Path(os.environ.get("MGS_DRIVE_AUTH_STATE_FILE", str(BASE / "data/drive-auth-unified-state.json")))
ROOT_ID = os.environ.get("MGS_DRIVE_ROOT_ID", "0AEwt4Ye690ocUk9PVA")
SA_ITEM = os.environ.get("MGS_DRIVE_SA_ITEM", "Google Service Account - MGS Agent")
SA_INTERVAL = int(os.environ.get("MGS_DRIVE_SA_INTERVAL_SECONDS", "86400"))
PRIMARY_MODE = os.environ.get("MGS_DRIVE_AUTH_PRIMARY", "service_account").strip().lower()
REMIND_INTERVAL = int(os.environ.get("MGS_DRIVE_ALERT_REPEAT_SECONDS", "21600"))
CHANNEL_ID = os.environ.get("MGS_DRIVE_ALERT_CHANNEL_ID", "1498132022634483894")
RODOLFO_ID = "344196393512075265"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def http_json(req: urllib.request.Request, timeout: int = 30) -> tuple[int, dict[str, Any]]:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode(errors="ignore")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="ignore")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"error": "http_error"}
        return exc.code, data
    except Exception as exc:
        return 0, {"error": type(exc).__name__}


def override_result(name: str) -> dict[str, Any] | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{name}_not_object")
    return value


def check_user_oauth() -> dict[str, Any]:
    forced = override_result("MGS_DRIVE_AUTH_USER_RESULT_JSON")
    if forced is not None:
        return forced
    if not TOKEN_FILE.exists():
        return {"ok": False, "state": "missing_file"}
    try:
        creds = json.loads(TOKEN_FILE.read_text())
        missing = [key for key in ("client_id", "client_secret", "refresh_token") if not creds.get(key)]
        if missing:
            return {"ok": False, "state": "missing_fields"}
        body = urllib.parse.urlencode(
            {
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": creds["refresh_token"],
                "grant_type": "refresh_token",
            }
        ).encode()
        status, data = http_json(
            urllib.request.Request(
                "https://oauth2.googleapis.com/token",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        )
        if status == 200 and data.get("access_token"):
            return {"ok": True, "state": "token_ok", "http": status}
        return {"ok": False, "state": "token_failed", "http": status, "error": data.get("error", "unknown")}
    except Exception as exc:
        return {"ok": False, "state": "exception", "error": type(exc).__name__}


def load_service_account() -> dict[str, Any]:
    load_env(BASE / ".env")
    vault = os.environ.get("OP_DEFAULT_VAULT", "MGS Conteúdo")
    proc = subprocess.run(
        ["op", "item", "get", SA_ITEM, "--vault", vault, "--format", "json", "--reveal"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError("op_item_unreadable")
    item = json.loads(proc.stdout)
    values: list[str] = []
    for field in item.get("fields", []):
        value = field.get("value")
        if value:
            values.append(str(value))
    for value in values:
        if "private_key" in value and "client_email" in value:
            return json.loads(value)
    raise RuntimeError("service_account_json_not_found")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def check_service_account() -> dict[str, Any]:
    forced = override_result("MGS_DRIVE_AUTH_SA_RESULT_JSON")
    if forced is not None:
        return forced
    try:
        sa = load_service_account()
        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT"}
        claim = {
            "iss": sa["client_email"],
            "scope": "https://www.googleapis.com/auth/drive",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }
        signing_input = (b64url(json.dumps(header, separators=(",", ":")).encode()) + "." + b64url(json.dumps(claim, separators=(",", ":")).encode())).encode()
        key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
        if not isinstance(key, rsa.RSAPrivateKey):
            raise RuntimeError("private_key_not_rsa")
        signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        assertion = signing_input.decode() + "." + b64url(signature)
        status, token_data = http_json(
            urllib.request.Request(
                "https://oauth2.googleapis.com/token",
                data=urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        )
        if status != 200 or not token_data.get("access_token"):
            return {"ok": False, "state": "token_failed", "http": status, "error": token_data.get("error", "unknown")}
        fields = urllib.parse.quote("id,name,driveId,trashed,capabilities(canAddChildren,canEdit,canModifyContent)", safe=",()")
        status, data = http_json(
            urllib.request.Request(
                f"https://www.googleapis.com/drive/v3/files/{ROOT_ID}?supportsAllDrives=true&fields={fields}",
                headers={"Authorization": "Bearer " + token_data["access_token"]},
            )
        )
        caps = data.get("capabilities", {}) if isinstance(data, dict) else {}
        drive_id = data.get("driveId") if isinstance(data, dict) else None
        if status == 200 and not drive_id:
            return {"ok": False, "state": "my_drive_sa_upload_blocked", "http": status, "error": "storageQuotaExceeded_risk"}
        ok = bool(
            status == 200
            and data.get("id") == ROOT_ID
            and not data.get("trashed")
            and caps.get("canAddChildren")
            and caps.get("canEdit")
            and caps.get("canModifyContent")
        )
        return {"ok": ok, "state": "root_access_ok" if ok else "root_access_failed", "http": status, "destination": "shared_drive" if drive_id else "my_drive"}
    except Exception as exc:
        return {"ok": False, "state": "exception", "error": type(exc).__name__}


def load_state() -> dict[str, Any]:
    try:
        value = json.loads(STATE_FILE.read_text())
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_FILE.with_suffix(STATE_FILE.suffix + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, STATE_FILE)


def send_payload(payload: dict[str, Any], dry_run: bool) -> None:
    command = [str(BASE / "scripts/discord-bot-post.py"), "--channel-id", CHANNEL_ID]
    if dry_run:
        command.append("--dry-run")
    proc = subprocess.run(command, input=json.dumps(payload, ensure_ascii=False), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
    if proc.returncode != 0:
        raise RuntimeError("discord_bot_post_failed")


def payload_for(user: dict[str, Any], sa: dict[str, Any], recovered: bool = False) -> dict[str, Any]:
    title = "Drive auth restabelecida" if recovered else "Drive auth indisponível"
    color = 3066993 if recovered else 15158332
    content = "" if recovered else f"<@{RODOLFO_ID}> alerta de autenticação Google Drive"
    return {
        "content": content,
        "allowed_mentions": {"users": [] if recovered else [RODOLFO_ID]},
        "embeds": [
            {
                "title": title,
                "color": color,
                "fields": [
                    {"name": "OAuth usuário", "value": str(user.get("state", "unknown")), "inline": True},
                    {"name": "Service Account", "value": str(sa.get("state", "unknown")), "inline": True},
                    {"name": "Impacto", "value": "Uploads ficam bloqueados apenas se OAuth usuário e Service Account estiverem ambos indisponíveis.", "inline": False},
                ],
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-sa", action="store_true")
    parser.add_argument("--check-user-rollback", action="store_true")
    args = parser.parse_args()
    if PRIMARY_MODE not in {"service_account", "user_oauth"}:
        raise RuntimeError(f"unsupported primary auth mode: {PRIMARY_MODE}")
    now = int(time.time())
    state = load_state()
    user = check_user_oauth() if PRIMARY_MODE == "user_oauth" or args.check_user_rollback else {"ok": False, "state": "not_checked_rollback"}
    last_sa_check = int(state.get("last_sa_check_ts") or 0)
    should_check_sa = PRIMARY_MODE == "service_account" or args.force_sa or not user.get("ok") or not state.get("sa_result") or now - last_sa_check >= SA_INTERVAL
    if should_check_sa:
        sa = check_service_account()
        last_sa_check = now
    else:
        sa = state.get("sa_result", {"ok": False, "state": "not_checked"})
    healthy = bool(sa.get("ok")) if PRIMARY_MODE == "service_account" else bool(user.get("ok") or sa.get("ok"))
    previous_healthy = state.get("healthy")
    last_alert = int(state.get("last_alert_ts") or 0)
    should_alert = not healthy and (previous_healthy is not False or now - last_alert >= REMIND_INTERVAL)
    should_recover = healthy and previous_healthy is False

    new_state = {
        "last_check_ts": now,
        "healthy": healthy,
        "user_result": user,
        "sa_result": sa,
        "last_sa_check_ts": last_sa_check,
        "last_alert_ts": now if should_alert else last_alert,
        "primary_credential": "service_account" if PRIMARY_MODE == "service_account" and sa.get("ok") else ("user_oauth" if PRIMARY_MODE == "user_oauth" and user.get("ok") else "none"),
    }
    if not args.dry_run:
        save_state(new_state)
    if should_alert:
        send_payload(payload_for(user, sa), args.dry_run)
    elif should_recover:
        send_payload(payload_for(user, sa, recovered=True), args.dry_run)
    print(
        "drive_auth status={} primary={} user={} sa={} sa_checked={} dry_run={}".format(
            "ok" if healthy else "fail",
            PRIMARY_MODE,
            user.get("state", "unknown"),
            sa.get("state", "unknown"),
            int(should_check_sa),
            int(args.dry_run),
        )
    )
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
