#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = "https://discord.com/api/v10"
ARES_ID = "1508864261504630925"
SOURCE = Path("/root/mgs-agent/data/ares/discord/shein-fixed-routes.json")
AUDIT = Path("/root/mgs-agent/data/ares/discord/shein-fixed-routes-deletion-20260912.json")


def load_token() -> str:
    values: dict[str, str] = {}
    for raw in Path("/root/.hermes/profiles/ares/.env").read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    token = values.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("Ares Discord credential missing")
    return token


def request(token: str, method: str, path: str) -> tuple[int, Any]:
    req = urllib.request.Request(
        API + path,
        data=b"" if method == "DELETE" else None,
        headers={"Authorization": "Bot " + token, "User-Agent": "MGS-Ares-SHEINThreadDeletion/1.0"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        return exc.code, payload


def persist(audit: dict) -> None:
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    registry = json.loads(SOURCE.read_text(encoding="utf-8"))
    routes = registry.get("threads", {})
    if set(routes) != {"G001", "G002", "G003", "G004", "G005", "G006"}:
        raise RuntimeError("expected exact six SHEIN fixed routes")
    token = load_token()
    audit = {
        "request": "delete-six-shein-fixed-threads-rodolfo-20260912",
        "authorization_source": "discord:thread:1548151961499734066",
        "requested_by": "Rodolfo Mattei",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "items": {},
    }

    # Pre-read the complete set before the first DELETE.
    for code in sorted(routes):
        row = routes[code]
        thread_id = row["thread_id"]
        status, thread = request(token, "GET", f"/channels/{thread_id}")
        if status == 404:
            audit["items"][code] = {
                "thread_id": thread_id,
                "parent_channel_id": row["parent_channel_id"],
                "thread_name": row["thread_name"],
                "pre_read": "already_absent",
                "delete_required": False,
            }
            continue
        if status != 200:
            raise RuntimeError(f"pre-read HTTP {status} for {code}")
        if thread.get("id") != thread_id or thread.get("parent_id") != row["parent_channel_id"] or thread.get("name") != row["thread_name"]:
            raise RuntimeError(f"thread identity mismatch for {code}")
        if thread.get("owner_id") != ARES_ID:
            raise RuntimeError(f"thread owner mismatch for {code}")
        seed_status, seed = request(token, "GET", f"/channels/{thread_id}/messages/{row['seed_message_id']}")
        if seed_status != 200 or (seed.get("author") or {}).get("id") != ARES_ID:
            raise RuntimeError(f"seed ownership mismatch for {code}")
        audit["items"][code] = {
            "thread_id": thread_id,
            "parent_channel_id": row["parent_channel_id"],
            "thread_name": row["thread_name"],
            "seed_message_id": row["seed_message_id"],
            "pre_read": "identity_and_owner_verified",
            "delete_required": True,
        }
    persist(audit)

    for code in sorted(audit["items"]):
        item = audit["items"][code]
        if item["delete_required"]:
            delete_status, _ = request(token, "DELETE", f"/channels/{item['thread_id']}")
            if delete_status not in {200, 204, 404}:
                raise RuntimeError(f"delete HTTP {delete_status} for {code}")
            item["delete_http"] = delete_status
            persist(audit)
        readback_status, _ = request(token, "GET", f"/channels/{item['thread_id']}")
        if readback_status != 404:
            raise RuntimeError(f"thread still exists after delete for {code}: HTTP {readback_status}")
        item["readback_http"] = 404
        item["deleted_verified"] = True
        persist(audit)

    audit["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    audit["success"] = True
    audit["deleted_verified"] = sum(bool(item.get("deleted_verified")) for item in audit["items"].values())
    persist(audit)
    print(json.dumps({"success": True, "targets": 6, "deleted_verified": audit["deleted_verified"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
