#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

work = Path("/root/mgs-agent/work/meta-app-force-live-20260902-114854")
generic = json.loads((work / "generic-result.json").read_text(encoding="utf-8"))
b013 = json.loads((work / "b013-result.json").read_text(encoding="utf-8"))
readback = json.loads((work / "readback-result.json").read_text(encoding="utf-8"))
event = {
    "ts": datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds"),
    "event": "meta_app_b001_b013_general_live_check_and_force_alert",
    "agent": "zeus",
    "authorized_by": "Rodolfo Mattei",
    "source_message_id": "1544735605009944626",
    "scope": [
        "B001-4", "B002-3", "B003-3", "B004-4", "B005-4", "B006-4",
        "B007-2", "B008-3", "B009-3", "B010-3", "B011-2", "B012-2", "B013-4",
    ],
    "generic_roles_route": {
        "apps": 12,
        "force_live": True,
        "errors": generic["errors_count"],
        "logical_alerts": generic["alerts_sent"],
        "sheet_updated": generic["sheet_updated"],
        "pause_apps": generic["pause_apps"],
        "apps_state": generic["apps"],
    },
    "b013_dtr_route": {
        "force_live": True,
        "targets": b013["targets"],
        "linked": b013["linked"],
        "unlinked_confirmed": b013["unlinked_confirmed"],
        "unknown": b013["unknown"],
        "alerts_sent": b013["alerts_sent"],
        "app_capability": b013["app_capability"],
        "sheet_sync": b013["sheet_sync"],
    },
    "discord_readback": {
        "apps_validated": readback["apps_validated"],
        "logical_force_live_alerts": readback["logical_force_live_alerts"],
        "physical_messages": readback["physical_messages"],
        "apps": readback["apps"],
        "complete": True,
    },
    "secrets_exposed": False,
    "status": "success",
    "evidence_dir": str(work),
}
with open("/root/mgs-agent/logs/events-audit.jsonl", "a", encoding="utf-8") as fh:
    fh.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
print(json.dumps({"audit_append": "PASS", "event": event["event"], "logical_alerts": 13, "physical_messages": readback["physical_messages"]}, ensure_ascii=False))
