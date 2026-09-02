#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

work = Path("/root/mgs-agent/work/meta-app-force-live-20260902-114854")
before = json.loads((work / "before.json").read_text(encoding="utf-8"))
token = os.environ["DISCORD_BOT_TOKEN"]
role_apps = [
    "B001-4", "B002-3", "B003-3", "B004-4", "B005-4", "B006-4",
    "B007-2", "B008-3", "B009-3", "B010-3", "B011-2", "B012-2",
]
all_apps = role_apps + ["B013-4"]
summary = {}
raw_summary = {}
for app in all_apps:
    channel = before["channels"][app]
    channel_id = channel["channel_id"]
    after_id = channel["latest_message_id"]
    query = urllib.parse.urlencode({"after": after_id, "limit": 100})
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages?{query}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "MGS-Zeus-Force-Live-Readback/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        rows = json.load(resp)
    rows.sort(key=lambda row: int(row["id"]))
    assert rows, f"no messages after baseline for {app}"
    assert all((row.get("author") or {}).get("id") == "1496296175014252634" for row in rows)
    title = f"Meta APP - {app}"
    candidates = []
    for index, row in enumerate(rows):
        embed = (row.get("embeds") or [{}])[0]
        if embed.get("title") == title and "Alerta live solicitado" in str(embed.get("description") or ""):
            candidates.append(index)
    assert len(candidates) == 1, (app, candidates)
    start = candidates[0]
    end = len(rows)
    for index in range(start + 1, len(rows)):
        if rows[index].get("embeds"):
            end = index
            break
    family = rows[start:end]
    assert len(family) >= 3, (app, len(family))
    embed = (family[0].get("embeds") or [{}])[0]
    assert (family[0].get("content") or "").startswith("<@344196393512075265>")
    assert all((row.get("content") or "").startswith("```") for row in family[1:])
    field_names = [field.get("name") for field in embed.get("fields") or []]
    if app in role_apps:
        assert field_names == ["ESTADO", "CONTAGEM", "USO"], (app, field_names)
    else:
        assert field_names == ["ESTADO", "CONTAGEM", "PENDENTES", "PÁGINAS", "DTR", "META"], field_names
    combined = "\n".join(row.get("content") or "" for row in family[1:])
    required_headings = [
        "USUÁRIOS ATUAIS",
        "USUÁRIOS REMOVIDOS AGORA",
        "USUÁRIOS ADICIONADOS AGORA",
        "REMOVIDOS ACUMULADOS" if app in role_apps else "REMOVIDOS CONFIRMADOS",
    ]
    for heading in required_headings:
        assert heading in combined, (app, heading)
    assert "+N outros" not in combined and " outros" not in combined
    family_ids = [row["id"] for row in family]
    summary[app] = {
        "channel_id": channel_id,
        "logical_force_live_alerts": 1,
        "physical_messages": len(family),
        "message_ids": family_ids,
        "embed_title": embed.get("title"),
        "embed_fields": field_names,
        "messages_after_baseline_total": len(rows),
        "extra_messages_outside_force_family": len(rows) - len(family),
    }
    raw_summary[app] = [
        {
            "id": row["id"],
            "timestamp": row.get("timestamp"),
            "title": ((row.get("embeds") or [{}])[0]).get("title"),
            "description": ((row.get("embeds") or [{}])[0]).get("description"),
            "content_kind": "code_block" if (row.get("content") or "").startswith("```") else ("mention" if (row.get("content") or "").startswith("<@") else "other"),
        }
        for row in rows
    ]
assert len(summary) == 13
result = {
    "status": "PASS",
    "apps_validated": len(summary),
    "logical_force_live_alerts": sum(row["logical_force_live_alerts"] for row in summary.values()),
    "physical_messages": sum(row["physical_messages"] for row in summary.values()),
    "apps": summary,
}
(work / "readback-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(work / "messages-after-sanitized.json").write_text(json.dumps(raw_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
