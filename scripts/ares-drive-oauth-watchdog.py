#!/usr/bin/env python3
"""Ares Drive OAuth watchdog.

Script-only cron target: stays silent while OAuth refresh works; prints a short
Discord-ready alert only when write OAuth is invalid/revoked, or when it recovers.
Never prints client_secret, refresh_token, access_token, or raw credential JSON.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

TOKEN_FILE = Path(os.environ.get("ARES_DRIVE_OAUTH_CLIENT_TOKEN_FILE", "/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json"))
STATE_FILE = Path(os.environ.get("ARES_DRIVE_OAUTH_WATCHDOG_STATE", "/root/mgs-agent/data/ares/drive-oauth-watchdog-state.json"))
REMIND_AFTER_SECONDS = int(os.environ.get("ARES_DRIVE_OAUTH_WATCHDOG_REMIND_SECONDS", str(6 * 3600)))
ZEUS_MENTION = "<@1496296175014252634>"
RODOLFO_MENTION = "<@344196393512075265>"


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, mode=0o755, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def post_form(url: str, data: dict[str, str]) -> tuple[bool, int | None, dict[str, Any]]:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return True, getattr(r, "status", 200), json.load(r)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="ignore")
        try:
            obj = json.loads(raw)
        except Exception:
            obj = {"error": raw[:200]}
        return False, e.code, obj
    except Exception as exc:
        return False, None, {"error": type(exc).__name__, "error_description": str(exc)[:200]}


def check_oauth() -> dict[str, Any]:
    if not TOKEN_FILE.exists():
        return {"ok": False, "stage": "token_file", "error": "missing_token_file", "detail": str(TOKEN_FILE)}
    try:
        creds = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "stage": "token_file", "error": "invalid_json", "detail": type(exc).__name__}
    missing = [k for k in ("client_id", "client_secret", "refresh_token") if not creds.get(k)]
    if missing:
        return {"ok": False, "stage": "token_file", "error": "missing_fields", "detail": ",".join(missing)}
    ok, status, obj = post_form(
        "https://oauth2.googleapis.com/token",
        {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
            "grant_type": "refresh_token",
        },
    )
    if ok and obj.get("access_token"):
        return {"ok": True, "stage": "refresh", "http_status": status}
    return {
        "ok": False,
        "stage": "refresh",
        "http_status": status,
        "error": obj.get("error", "unknown"),
        "detail": (obj.get("error_description") or obj.get("error") or "")[:180],
    }


def should_emit_failure(state: dict[str, Any], ts: dt.datetime) -> bool:
    if state.get("last_status") != "fail":
        return True
    last_alert_raw = state.get("last_alert_at")
    if not last_alert_raw:
        return True
    try:
        last_alert = dt.datetime.fromisoformat(last_alert_raw)
    except Exception:
        return True
    return (ts - last_alert).total_seconds() >= REMIND_AFTER_SECONDS


def main() -> int:
    ts = now_utc()
    state = load_json(STATE_FILE, {})
    result = check_oauth()
    ts_iso = ts.isoformat()

    if result.get("ok"):
        recovered = state.get("last_status") == "fail"
        state.update({"last_status": "ok", "last_ok_at": ts_iso, "last_error": ""})
        save_json(STATE_FILE, state)
        if recovered:
            print(
                f"[ARES-DRIVE-OAUTH-RECOVERED] {ZEUS_MENTION} {RODOLFO_MENTION}\n"
                f"Status: OAuth de write/upload do Google Drive voltou a responder.\n"
                f"Validação: refresh token HTTP {result.get('http_status')} em {ts_iso}.\n"
                f"Segredo: não exibido."
            )
        return 0

    state_error = {
        "stage": result.get("stage", "unknown"),
        "http_status": result.get("http_status"),
        "error": result.get("error", "unknown"),
        "detail": result.get("detail", ""),
    }
    emit = should_emit_failure(state, ts)
    state.update({"last_status": "fail", "last_fail_at": ts_iso, "last_error": state_error})
    if emit:
        state["last_alert_at"] = ts_iso
    save_json(STATE_FILE, state)

    if emit:
        print(
            f"[ARES-DRIVE-OAUTH-ALERT] {ZEUS_MENTION} {RODOLFO_MENTION}\n"
            f"Status: OAuth de write/upload do Google Drive falhou.\n"
            f"Etapa: {state_error['stage']}\n"
            f"HTTP: {state_error.get('http_status')}\n"
            f"Erro: {state_error.get('error')}\n"
            f"Detalhe: {state_error.get('detail')}\n"
            f"Impacto: uploads/renomeações Drive via OAuth usuário ficam bloqueados; leitura por service account pode continuar OK.\n"
            f"Ação esperada: revalidar OAuth pelo fluxo desktop do Ares. Segredos não exibidos."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
