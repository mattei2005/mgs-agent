#!/usr/bin/env python3
"""Check or repair the six fixed Eggbev Discord routes."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data/ares/discord/eggbev-fixed-routes.json"
PROFILE = Path("/root/.hermes/profiles/ares")
THREAD_REGISTRY = PROFILE / "discord_threads.json"
ENV_PATH = PROFILE / ".env"
ZEUS_ENV_PATH = Path("/root/.hermes/profiles/zeus/.env")
API = "https://discord.com/api/v10"
LEGACY_BANNERS = {
    "1543280854024060999": "1543421467851620372",
    "1543312825890381865": "1543421473769783367",
    "1543333373945053184": "1543421482166657166",
    "1541578606076231750": "1543421488399515680",
    "1541578596253175858": "1543421495223787571",
    "1541578556037927053": "1543421502433525884",
}


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def load_token() -> str:
    for raw in ENV_PATH.read_text(errors="ignore").splitlines():
        if raw.startswith("DISCORD_BOT_TOKEN="):
            value = raw.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError("Ares Discord token unavailable")


def load_zeus_token() -> str:
    for raw in ZEUS_ENV_PATH.read_text(errors="ignore").splitlines():
        if raw.startswith("DISCORD_BOT_TOKEN="):
            value = raw.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError("Zeus Discord token unavailable for legacy banner removal")



def request(token: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    for attempt in range(4):
        req = urllib.request.Request(
            API + path,
            data=data,
            method=method,
            headers={
                "Authorization": "Bot " + token,
                "Content-Type": "application/json",
                "User-Agent": "MGS-Ares-Eggbev-Thread-Reconcile/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode(errors="ignore")
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode(errors="ignore")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {}
            if exc.code == 429 and attempt < 3:
                retry_after = parsed.get("retry_after", 1.0)
                try:
                    delay = max(0.5, min(float(retry_after), 30.0))
                except (TypeError, ValueError):
                    delay = 1.0
                time.sleep(delay + 0.25)
                continue
            return exc.code, {"code": parsed.get("code"), "message": parsed.get("message"), "retry_after": parsed.get("retry_after")}
    return 429, {"message": "rate_limit_retry_exhausted"}


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def ensure_thread_registry(thread_ids: list[str], repair: bool) -> dict[str, Any]:
    current = json.loads(THREAD_REGISTRY.read_text()) if THREAD_REGISTRY.exists() else []
    values = [str(value) for value in current]
    missing = [value for value in thread_ids if value not in values]
    if repair and missing:
        atomic_json(THREAD_REGISTRY, values + missing)
        reread = [str(value) for value in json.loads(THREAD_REGISTRY.read_text())]
        if any(value not in reread for value in thread_ids):
            raise RuntimeError("discord_threads readback mismatch")
    return {"missing_before": missing, "complete": not missing or repair}


def remove_legacy_banner(token: str, thread_id: str, message_id: str) -> dict[str, Any]:
    message_status, _ = request(token, "GET", f"/channels/{thread_id}/messages/{message_id}")
    pins_status, pins = request(token, "GET", f"/channels/{thread_id}/pins")
    if pins_status != 200 or not isinstance(pins, list):
        return {"thread_id": thread_id, "message_id": message_id, "ok": False, "stage": "pins_pre_read", "http": pins_status}
    pinned_before = any(str(row.get("id")) == message_id for row in pins)
    changed: list[str] = []
    if pinned_before:
        unpin_status, _ = request(token, "DELETE", f"/channels/{thread_id}/pins/{message_id}")
        if unpin_status == 403:
            unpin_status, _ = request(load_zeus_token(), "DELETE", f"/channels/{thread_id}/pins/{message_id}")
        if unpin_status not in {200, 204, 404}:
            return {"thread_id": thread_id, "message_id": message_id, "ok": False, "stage": "unpin", "http": unpin_status}
        changed.append("unpin")
    if message_status == 200:
        delete_status, _ = request(token, "DELETE", f"/channels/{thread_id}/messages/{message_id}")
        if delete_status == 403:
            delete_status, _ = request(load_zeus_token(), "DELETE", f"/channels/{thread_id}/messages/{message_id}")
        if delete_status not in {200, 204, 404}:
            return {"thread_id": thread_id, "message_id": message_id, "ok": False, "stage": "message_delete", "http": delete_status}
        changed.append("delete_message")
    message_after_status, _ = request(token, "GET", f"/channels/{thread_id}/messages/{message_id}")
    pins_after_status, pins_after = request(token, "GET", f"/channels/{thread_id}/pins")
    pinned_after = any(str(row.get("id")) == message_id for row in (pins_after if isinstance(pins_after, list) else []))
    return {
        "thread_id": thread_id,
        "message_id": message_id,
        "existed_before": message_status == 200,
        "pinned_before": pinned_before,
        "changed": changed,
        "message_absent_after": message_after_status == 404,
        "pin_absent_after": pins_after_status == 200 and not pinned_after,
        "ok": message_after_status == 404 and pins_after_status == 200 and not pinned_after,
    }



def reconcile_route(token: str, label: str, route: dict[str, Any], policy: dict[str, Any], repair: bool) -> dict[str, Any]:
    thread_id = str(route["thread_id"])
    status, channel = request(token, "GET", f"/channels/{thread_id}")
    if status != 200 or not isinstance(channel, dict):
        return {"label": label, "thread_id": thread_id, "ok": False, "stage": "channel_read", "http": status}
    if str(channel.get("parent_id")) != str(policy_parent := load_registry()["parent_channel_id"]):
        return {"label": label, "thread_id": thread_id, "ok": False, "stage": "parent_mismatch", "actual_parent": channel.get("parent_id"), "expected_parent": policy_parent}

    metadata = dict(channel.get("thread_metadata") or {})
    changed: list[str] = []
    wanted_archive = int(policy["auto_archive_duration_minutes"])
    if int(metadata.get("auto_archive_duration") or 0) != wanted_archive and repair:
        patch_status, _ = request(token, "PATCH", f"/channels/{thread_id}", {"auto_archive_duration": wanted_archive})
        if patch_status != 200:
            return {"label": label, "thread_id": thread_id, "ok": False, "stage": "auto_archive_patch", "http": patch_status}
        changed.append("auto_archive_duration")

    members_status, members = request(token, "GET", f"/channels/{thread_id}/thread-members?with_member=true&limit=100")
    if members_status != 200 or not isinstance(members, list):
        return {"label": label, "thread_id": thread_id, "ok": False, "stage": "members_read", "http": members_status}
    member_ids = {str(row.get("user_id") or ((row.get("member") or {}).get("user") or {}).get("id") or "") for row in members}
    missing_members = [str(value) for value in policy["required_member_ids"] if str(value) not in member_ids]
    if repair:
        for user_id in missing_members:
            add_status, _ = request(token, "PUT", f"/channels/{thread_id}/thread-members/{user_id}")
            if add_status not in {204, 200}:
                return {"label": label, "thread_id": thread_id, "ok": False, "stage": "member_add", "user_id": user_id, "http": add_status}
            changed.append("member:" + user_id)

    # Exact post-write readback.
    channel_status, channel_after = request(token, "GET", f"/channels/{thread_id}")
    members_status, members_after = request(token, "GET", f"/channels/{thread_id}/thread-members?with_member=true&limit=100")
    metadata_after = dict((channel_after or {}).get("thread_metadata") or {}) if isinstance(channel_after, dict) else {}
    member_ids_after = {str(row.get("user_id") or ((row.get("member") or {}).get("user") or {}).get("id") or "") for row in (members_after if isinstance(members_after, list) else [])}
    prompt = ROOT / str(route["prompt_file"])
    checks = {
        "channel_http": channel_status == 200,
        "parent": str((channel_after or {}).get("parent_id")) == str(policy_parent),
        "unlocked": metadata_after.get("locked") is False,
        "archive_preserved": isinstance(metadata_after.get("archived"), bool),
        "auto_archive_7d": int(metadata_after.get("auto_archive_duration") or 0) == wanted_archive,
        "required_members": all(str(value) in member_ids_after for value in policy["required_member_ids"]),
        "prompt_file": prompt.exists() and bool(prompt.read_text().strip()),
    }
    return {
        "label": label,
        "thread_id": thread_id,
        "name": (channel_after or {}).get("name"),
        "archived": metadata_after.get("archived"),
        "changed": changed,
        "checks": checks,
        "ok": all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair", action="store_true", help="repair members, registry and 7-day archive setting")
    parser.add_argument("--remove-legacy-banners", action="store_true", help="remove the six superseded pinned route banner messages")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    registry = load_registry()
    policy = registry["preservation_policy"]
    token = load_token()
    removals = [remove_legacy_banner(token, thread_id, message_id) for thread_id, message_id in LEGACY_BANNERS.items()] if args.remove_legacy_banners else []
    results = [reconcile_route(token, label, route, policy, args.repair) for label, route in registry["routes"].items()]
    thread_registry = ensure_thread_registry([str(route["thread_id"]) for route in registry["routes"].values()], args.repair)
    payload = {
        "ok": all(row.get("ok") for row in results) and thread_registry["complete"] and all(row.get("ok") for row in removals),
        "mode": "remove_legacy_banners" if args.remove_legacy_banners else "repair" if args.repair else "check",
        "routes_expected": len(registry["routes"]),
        "routes_ok": sum(1 for row in results if row.get("ok")),
        "thread_registry": thread_registry,
        "legacy_banner_removals": removals,
        "routes": results,
    }
    if args.output:
        atomic_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
