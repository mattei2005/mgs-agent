#!/usr/bin/env python3
"""Canonical Google Drive Service Account watchdog owned by Zeus.

Validates the 1Password-backed MGS Agent identity against the canonical Shared
Drive. Personal user OAuth is retired and is not accepted as fallback. Alerts
are posted by the local Zeus bot, never by a 1Password webhook.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
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
STATE_FILE = Path(os.environ.get("MGS_DRIVE_AUTH_STATE_FILE", str(BASE / "data/drive-auth-unified-state.json")))
ROOT_ID = os.environ.get("MGS_DRIVE_ROOT_ID", "0AEwt4Ye690ocUk9PVA")
SA_ITEM = os.environ.get("MGS_DRIVE_SA_ITEM", "Google Service Account - MGS Agent")
SA_INTERVAL = int(os.environ.get("MGS_DRIVE_SA_INTERVAL_SECONDS", "86400"))
PRIMARY_MODE = os.environ.get("MGS_DRIVE_AUTH_PRIMARY", "service_account").strip().lower()
REMIND_INTERVAL = int(os.environ.get("MGS_DRIVE_ALERT_REPEAT_SECONDS", "21600"))
CHANNEL_ID = os.environ.get("MGS_DRIVE_ALERT_CHANNEL_ID", "1498132022634483894")
RODOLFO_ID = "344196393512075265"
LEGACY_RUNTIME_PATTERN = re.compile(
    r"(?i)(ares-google-drive-oauth-client|Google OAuth\s*-\s*Ares Drive|"
    r"ARES_DRIVE_AUTH_MODE\s*=\s*oauth|google_token\.json|"
    r"google_client_secret\.json|drive-oauth-watchdog|"
    r"mgsagent@mgs-ares\.iam\.gserviceaccount\.com|poised-team-502702-v8)"
)
CANONICAL_SELECTORS = {
    "ARES_DRIVE_AUTH_MODE": "service_account",
    "MGS_DRIVE_AUTH_PRIMARY": "service_account",
    "MGS_GOOGLE_SHEETS_AUTH_MODE": "service_account",
    "MGS_META_APP_ROLES_GOOGLE_AUTH_MODE": "service_account",
}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def check_legacy_runtime_residue() -> dict[str, Any]:
    """Fail closed if an active MGS runtime route can select retired Google auth."""
    load_env(BASE / ".env")
    selector_conflicts = {
        key: os.environ.get(key, "").strip().lower()
        for key, expected in CANONICAL_SELECTORS.items()
        if os.environ.get(key, "").strip().lower() != expected
    }
    roots = [
        BASE / "scripts",
        BASE / "config",
        Path("/root/.hermes/profiles/zeus/skills"),
        Path("/root/.hermes/profiles/atena/skills"),
        Path("/root/.hermes/profiles/ares/skills"),
    ]
    self_path = Path(__file__).resolve()
    hits: list[str] = []
    scanned = 0
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.resolve() == self_path:
                continue
            text_path = str(path)
            if any(part in path.parts for part in (".archive", ".curator_backups", "__pycache__")):
                continue
            if "/skills/" in text_path and "/scripts/" not in text_path:
                continue
            if path.suffix.lower() not in {".py", ".sh", ".bash", ".json", ".yaml", ".yml", ".env"}:
                continue
            try:
                if path.stat().st_size > 2_000_000:
                    continue
                scanned += 1
                if LEGACY_RUNTIME_PATTERN.search(path.read_text(errors="ignore")):
                    hits.append(text_path)
            except OSError:
                continue
    ok = not selector_conflicts and not hits
    return {
        "ok": ok,
        "state": "legacy_runtime_clean" if ok else "legacy_runtime_residue",
        "scanned": scanned,
        "hit_count": len(hits),
        "hits": hits[:20],
        "selector_conflicts": selector_conflicts,
    }


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


def payload_for(sa: dict[str, Any], guard: dict[str, Any], recovered: bool = False) -> dict[str, Any]:
    title = "Drive auth restabelecida" if recovered else "Drive auth ou guardrail indisponível"
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
                    {"name": "Service Account", "value": str(sa.get("state", "unknown")), "inline": True},
                    {"name": "Guardrail legado", "value": str(guard.get("state", "unknown")), "inline": True},
                    {"name": "Impacto", "value": "Drive, Sheets e backups MGS ficam bloqueados se a identidade técnica ou o guardrail estiverem indisponíveis.", "inline": False},
                ],
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-sa", action="store_true")
    args = parser.parse_args()
    if PRIMARY_MODE != "service_account":
        raise RuntimeError(f"unsupported primary auth mode: {PRIMARY_MODE}")
    now = int(time.time())
    state = load_state()
    last_sa_check = int(state.get("last_sa_check_ts") or 0)
    should_check_sa = args.force_sa or not state.get("sa_result") or now - last_sa_check >= SA_INTERVAL
    if should_check_sa:
        sa = check_service_account()
        last_sa_check = now
    else:
        sa = state.get("sa_result", {"ok": False, "state": "not_checked"})
    guard = check_legacy_runtime_residue()
    healthy = bool(sa.get("ok")) and bool(guard.get("ok"))
    previous_healthy = state.get("healthy")
    last_alert = int(state.get("last_alert_ts") or 0)
    should_alert = not healthy and (previous_healthy is not False or now - last_alert >= REMIND_INTERVAL)
    should_recover = healthy and previous_healthy is False

    new_state = {
        "last_check_ts": now,
        "healthy": healthy,
        "sa_result": sa,
        "legacy_runtime_guard": guard,
        "last_sa_check_ts": last_sa_check,
        "last_alert_ts": now if should_alert else last_alert,
        "primary_credential": "service_account" if sa.get("ok") else "none",
    }
    if not args.dry_run:
        save_state(new_state)
    if should_alert:
        send_payload(payload_for(sa, guard), args.dry_run)
    elif should_recover:
        send_payload(payload_for(sa, guard, recovered=True), args.dry_run)
    print(
        "drive_auth status={} primary={} sa={} guard={} guard_hits={} sa_checked={} dry_run={}".format(
            "ok" if healthy else "fail",
            PRIMARY_MODE,
            sa.get("state", "unknown"),
            guard.get("state", "unknown"),
            guard.get("hit_count", -1),
            int(should_check_sa),
            int(args.dry_run),
        )
    )
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
