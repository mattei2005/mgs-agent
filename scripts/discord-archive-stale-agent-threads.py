#!/usr/bin/env python3
"""Archive stale active Discord threads for MGS agent channels.

Discord sometimes leaves auto-created private threads visible/active for users even
when their configured auto-archive window has elapsed. This enforces the same
visibility behavior for every member: if a thread's last message is older than
its auto_archive_duration, archive it.

Safe defaults:
- dry-run unless --apply is provided;
- uses each profile's own bot token from .env;
- never prints tokens;
- skips threads with recent activity;
- deduplicates thread IDs across profiles/channels.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"ERROR: missing PyYAML: {exc}", file=sys.stderr)
    raise

BASE = "https://discord.com/api/v10"
DISCORD_EPOCH_MS = 1420070400000
DEFAULT_PROFILES = ("zeus", "atena", "ares", "hera")
PROFILE_ROOT = pathlib.Path("/root/.hermes/profiles")


@dataclass
class Profile:
    name: str
    token: str
    channels: list[str]


def load_env(path: pathlib.Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        data[key.strip()] = value
    return data


def csv_ids(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        raw = ",".join(str(x) for x in value)
    else:
        raw = str(value)
    return [x for x in re.split(r"[,\s]+", raw) if x.isdigit()]


def load_profile(name: str) -> Profile | None:
    prof_dir = PROFILE_ROOT / name
    env = load_env(prof_dir / ".env")
    token = env.get("DISCORD_BOT_TOKEN", "")
    if not token:
        return None

    cfg_channels: list[str] = []
    cfg_path = prof_dir / "config.yaml"
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
        discord = cfg.get("discord") or {}
        cfg_channels.extend(csv_ids(discord.get("allowed_channels")))
        cfg_channels.extend(csv_ids(discord.get("free_response_channels")))

    env_channels: list[str] = []
    env_channels.extend(csv_ids(env.get("DISCORD_ALLOWED_CHANNELS")))
    env_channels.extend(csv_ids(env.get("DISCORD_FREE_RESPONSE_CHANNELS")))

    # Env is runtime authority when present, but include cfg too for audit safety.
    channels = sorted(set(env_channels or cfg_channels or []))
    return Profile(name=name, token=token, channels=channels)


def request_json(token: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {"Authorization": f"Bot {token}", "User-Agent": "mgs-thread-archive-enforcer"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()
        if not raw:
            return None
        return json.loads(raw.decode())


def snowflake_time(sf: str | None) -> dt.datetime | None:
    if not sf or not str(sf).isdigit():
        return None
    ms = (int(sf) >> 22) + DISCORD_EPOCH_MS
    return dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc)


def iso(ts: dt.datetime | None) -> str:
    if ts is None:
        return "unknown"
    return ts.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description="Archive stale active MGS Discord threads")
    ap.add_argument("--profiles", default=",".join(DEFAULT_PROFILES), help="Comma-separated profile names")
    ap.add_argument("--apply", action="store_true", help="Actually archive stale threads")
    ap.add_argument("--grace-minutes", type=int, default=30, help="Extra grace after auto_archive_duration")
    ap.add_argument("--max-archive", type=int, default=200, help="Safety cap per run")
    ap.add_argument("--summary-only", action="store_true", help="Print only compact summary JSON")
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    loaded = [p for name in profiles if (p := load_profile(name))]

    seen_threads: set[str] = set()
    checked = stale = archived = skipped_recent = errors = 0
    actions: list[dict[str, Any]] = []

    for prof in loaded:
        if not prof.channels:
            continue
        try:
            first = request_json(prof.token, "GET", f"/channels/{prof.channels[0]}")
            guild_id = first.get("guild_id")
            if not guild_id:
                continue
            active = request_json(prof.token, "GET", f"/guilds/{guild_id}/threads/active")
        except Exception as exc:
            errors += 1
            actions.append({"profile": prof.name, "error": f"active_threads_failed:{type(exc).__name__}"})
            continue

        parent_set = set(prof.channels)
        for thread in active.get("threads", []):
            tid = str(thread.get("id"))
            parent = str(thread.get("parent_id"))
            if parent not in parent_set or tid in seen_threads:
                continue
            seen_threads.add(tid)
            checked += 1
            meta = thread.get("thread_metadata") or {}
            if meta.get("archived"):
                continue
            duration = int(meta.get("auto_archive_duration") or 1440)
            last_at = snowflake_time(str(thread.get("last_message_id") or thread.get("id")))
            cutoff = (last_at or now) + dt.timedelta(minutes=duration + args.grace_minutes)
            name = str(thread.get("name") or "")[:80]
            if cutoff > now:
                skipped_recent += 1
                actions.append({"profile": prof.name, "thread": tid, "parent": parent, "state": "recent", "last": iso(last_at), "archive_after": iso(cutoff), "name": name})
                continue
            stale += 1
            item: dict[str, Any] = {"profile": prof.name, "thread": tid, "parent": parent, "state": "stale", "last": iso(last_at), "archive_after": iso(cutoff), "name": name}
            if args.apply and archived < args.max_archive:
                try:
                    request_json(prof.token, "PATCH", f"/channels/{tid}", {"archived": True})
                    archived += 1
                    item["archived"] = True
                    time.sleep(0.35)
                except urllib.error.HTTPError as exc:
                    errors += 1
                    item["error"] = f"HTTP {exc.code}"
                except Exception as exc:
                    errors += 1
                    item["error"] = type(exc).__name__
            actions.append(item)

    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "profiles": [p.name for p in loaded],
        "checked": checked,
        "stale": stale,
        "archived": archived,
        "skipped_recent": skipped_recent,
        "errors": errors,
    }
    if args.summary_only:
        print(json.dumps({"summary": summary}, ensure_ascii=False))
    else:
        print(json.dumps({"summary": summary, "actions": actions}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
