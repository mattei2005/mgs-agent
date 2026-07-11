#!/usr/bin/env python3
"""Post a JSON payload to Discord with the local Zeus bot credential.

Reads one JSON object from stdin. The bot token is loaded from the Zeus profile
.env and is never printed. Intended for cron/watchdog/report transports that do
not need a 1Password lookup merely to send an alert.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_CHANNEL = "1498132022634483894"
DEFAULT_ENV = Path("/root/.hermes/profiles/zeus/.env")


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel-id", default=os.environ.get("MGS_DISCORD_CHANNEL_ID", DEFAULT_CHANNEL))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        print(f"discord_bot_post=failed reason=invalid_json error={type(exc).__name__}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("discord_bot_post=failed reason=payload_not_object", file=sys.stderr)
        return 2

    if args.dry_run or os.environ.get("MGS_DRY_RUN") == "1":
        title = ((payload.get("embeds") or [{}])[0] or {}).get("title", "payload")
        print(f"discord_bot_post=dry_run channel={args.channel_id} title={str(title)[:120]}")
        return 0

    load_env(Path(os.environ.get("MGS_DISCORD_BOT_ENV", str(DEFAULT_ENV))))
    token = os.environ.get("MGS_DISCORD_BOT_TOKEN_OVERRIDE") or os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("discord_bot_post=failed reason=bot_token_missing", file=sys.stderr)
        return 1

    override = os.environ.get("MGS_DISCORD_API_URL_OVERRIDE")
    url = override or f"https://discord.com/api/v10/channels/{args.channel_id}/messages"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": "Bot " + token,
            "Content-Type": "application/json",
            "User-Agent": "MGS-Zeus/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            status = response.status
            raw = response.read().decode(errors="ignore")
    except urllib.error.HTTPError as exc:
        print(f"discord_bot_post=failed http={exc.code}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"discord_bot_post=failed reason={type(exc).__name__}", file=sys.stderr)
        return 1

    if status not in (200, 201):
        print(f"discord_bot_post=failed http={status}", file=sys.stderr)
        return 1
    try:
        response_data = json.loads(raw) if raw else {}
    except Exception:
        response_data = {}
    if not override and str(response_data.get("channel_id", "")) != str(args.channel_id):
        print("discord_bot_post=failed reason=channel_readback_mismatch", file=sys.stderr)
        return 1
    print(f"discord_bot_post=ok http={status} message_id={response_data.get('id', 'n/a')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
