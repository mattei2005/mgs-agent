#!/usr/bin/env python3
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

work = Path("/root/mgs-agent/work/meta-app-force-live-20260902-114854")
work.mkdir(parents=True, exist_ok=True)
registry = json.loads(Path("/root/mgs-agent/data/meta-app-registry.json").read_text(encoding="utf-8"))
token = os.environ["DISCORD_BOT_TOKEN"]
channels = {row["app"]: str(row["channel_id"]) for row in registry["apps"]}
before = {
    "captured_at": datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds"),
    "channels": {},
}
for app, channel_id in channels.items():
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=1",
        headers={"Authorization": f"Bot {token}", "User-Agent": "MGS-Zeus-Force-Live/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        rows = json.load(resp)
    before["channels"][app] = {
        "channel_id": channel_id,
        "latest_message_id": rows[0]["id"] if rows else "0",
        "latest_timestamp": rows[0]["timestamp"] if rows else None,
    }
path = work / "before.json"
path.write_text(json.dumps(before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "PASS", "captured_at": before["captured_at"], "apps": len(channels), "path": str(path)}, ensure_ascii=False))
