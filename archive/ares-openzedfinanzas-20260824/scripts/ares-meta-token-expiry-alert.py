#!/usr/bin/env python3
"""Script-only alert for Meta Ads token expiration.

Outputs nothing while token is healthy outside the warning window.
Outputs a sanitized Discord-ready alert when token is invalid or near expiry.
Never prints access tokens or credential values.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

COMMON_PATH = "/root/mgs-agent/scripts/ares-meta-common.py"
TOKEN_ITEM = "Token Meta API - 00 - ANUNCIANTE - Alana Figueiredo - OPENZED SPAIN"
RODOLFO_MENTION = "<@344196393512075265>"
DEFAULT_WARN_DAYS = 7.0


def load_common():
    spec = importlib.util.spec_from_file_location("ares_meta_common", COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load common helper: {COMMON_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fmt_dt(ts: int | None, tz_name: str = "America/New_York") -> str:
    if not isinstance(ts, int):
        return "não informado"
    z = ZoneInfo(tz_name)
    return dt.datetime.fromtimestamp(ts, dt.UTC).astimezone(z).strftime("%Y-%m-%d %H:%M:%S %Z")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--warn-days", type=float, default=DEFAULT_WARN_DAYS)
    ap.add_argument("--always-output", action="store_true", help="print sanitized status even outside alert window")
    args = ap.parse_args()

    common = load_common()
    token, field = common.get_token_from_1password(TOKEN_ITEM)
    status, payload, _headers = common.graph_get("debug_token", token, {"input_token": token})
    now = dt.datetime.now(dt.UTC)

    if not (200 <= status < 300):
        error = common.safe_meta_error(payload)
        print(
            f"{RODOLFO_MENTION} alerta crítico: token Meta API inválido ou não depurável.\n\n"
            "```text\n"
            "Meta Token Expiry Watch\n\n"
            f"Item 1Password | {TOKEN_ITEM}\n"
            f"Campo usado     | {field}\n"
            f"Len             | {len(token)}\n"
            f"HTTP            | {status}\n"
            f"Erro            | {json.dumps(error, ensure_ascii=False)[:700]}\n"
            "Ação            | Renovar/substituir token antes dos crons Meta\n"
            "```"
        )
        return 0

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    is_valid = bool(data.get("is_valid"))
    expires_at = data.get("expires_at")
    data_access_expires_at = data.get("data_access_expires_at")
    app = data.get("application") or "não informado"
    token_type = data.get("type") or "não informado"
    scopes = data.get("scopes") or []

    if isinstance(expires_at, int):
        expires_dt = dt.datetime.fromtimestamp(expires_at, dt.UTC)
        remaining_seconds = (expires_dt - now).total_seconds()
        remaining_days = remaining_seconds / 86400
    else:
        remaining_days = None

    should_alert = (not is_valid) or (remaining_days is None) or (remaining_days <= args.warn_days)

    if should_alert or args.always_output:
        status_label = "ALERTA" if should_alert else "OK"
        remaining_text = "desconhecido" if remaining_days is None else f"{remaining_days:.2f} dias"
        action = "Renovar/substituir token" if should_alert else "Sem ação agora"
        print(
            (f"{RODOLFO_MENTION} alerta: token Meta API perto da expiração.\n\n" if should_alert else "")
            + "```text\n"
            + "Meta Token Expiry Watch\n\n"
            + f"Status          | {status_label}\n"
            + f"Item 1Password | {TOKEN_ITEM}\n"
            + f"Campo usado     | {field}\n"
            + f"Len             | {len(token)}\n"
            + f"Token válido    | {is_valid}\n"
            + f"Tipo            | {token_type}\n"
            + f"App             | {app}\n"
            + f"Expira em       | {fmt_dt(expires_at)}\n"
            + f"Tempo restante  | {remaining_text}\n"
            + f"Data access     | {fmt_dt(data_access_expires_at)}\n"
            + f"Warn threshold  | {args.warn_days:.1f} dias\n"
            + f"Scopes          | {', '.join(scopes[:8])}{'...' if len(scopes) > 8 else ''}\n"
            + f"Ação            | {action}\n"
            + "```"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
