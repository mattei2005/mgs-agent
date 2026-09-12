#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = "https://discord.com/api/v10"
GUILD_ID = "1185714635991679006"
ARES_ID = "1508864261504630925"
ZEUS_ID = "1496296175014252634"
RODOLFO_ID = "344196393512075265"
GEIZIAN_ID = "321263240782807040"
WORK = Path("/root/mgs-agent/work/ares-shein-onboarding-20260911")
STATE = WORK / "fixed-create-threads-state.json"
RESULT = WORK / "fixed-create-threads-result.json"
CHANNELS = [
    {"channel_id": "1548149087206121613", "channel_name": "shein-g001", "code": "G001", "manager": "Icaro", "manager_id": "409878085807112207"},
    {"channel_id": "1548149300826079333", "channel_name": "shein-g002", "code": "G002", "manager": "Geizian", "manager_id": "321263240782807040"},
    {"channel_id": "1548149483039236137", "channel_name": "shein-g003", "code": "G003", "manager": "Isliago", "manager_id": "432898782188011543"},
    {"channel_id": "1548149654926135486", "channel_name": "shein-g004", "code": "G004", "manager": "Joe", "manager_id": "1214246869484576890"},
    {"channel_id": "1548150015275438220", "channel_name": "shein-g005", "code": "G005", "manager": "Kelly", "manager_id": "1291113428982693940"},
    {"channel_id": "1548150155184701440", "channel_name": "shein-g006", "code": "G006", "manager": "Nicolas", "manager_id": "1055570806945620030"},
]


def unique(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


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


def request(token: str, method: str, path: str, body: dict | None = None) -> tuple[int, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Authorization": "Bot " + token, "User-Agent": "MGS-Ares-SHEINFixedRoutes/1.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
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
        if exc.code == 429:
            wait = min(10.0, float(payload.get("retry_after", 1.0)))
            time.sleep(wait)
            return request(token, method, path, body)
        return exc.code, payload
    except (TimeoutError, urllib.error.URLError):
        return 0, {}


def paginate_archived(token: str, channel_id: str) -> list[dict]:
    output: list[dict] = []
    before = ""
    for _ in range(20):
        params = {"limit": "100"}
        if before:
            params["before"] = before
        status, data = request(token, "GET", f"/channels/{channel_id}/threads/archived/public?" + urllib.parse.urlencode(params))
        if status != 200:
            raise RuntimeError(f"archived thread read HTTP {status}")
        rows = data.get("threads", [])
        output.extend(rows)
        if not data.get("has_more") or not rows:
            return output
        before = rows[-1].get("archive_timestamp", "")
        if not before:
            return output
    raise RuntimeError("archived thread pagination exceeded bound")


def active_threads(token: str) -> list[dict]:
    status, data = request(token, "GET", f"/guilds/{GUILD_ID}/threads/active")
    if status != 200:
        raise RuntimeError(f"active thread read HTTP {status}")
    return data.get("threads", [])


def exact_threads(token: str, channel_id: str, title: str) -> list[dict]:
    rows = [row for row in active_threads(token) if row.get("parent_id") == channel_id and row.get("name") == title]
    rows += [row for row in paginate_archived(token, channel_id) if row.get("name") == title]
    unique_rows = {row["id"]: row for row in rows if row.get("id")}
    return list(unique_rows.values())


def recent_messages(token: str, thread_id: str) -> list[dict]:
    status, data = request(token, "GET", f"/channels/{thread_id}/messages?limit=100")
    if status != 200:
        raise RuntimeError(f"message read HTTP {status}")
    return data


def seed_content(row: dict) -> str:
    return f"""🚀 **Criar Campanhas — SHEIN {row['code']}**

Fase atual: criação do zero, duplicação e clone de campanhas Meta da operação SHEIN nos EUA.

- Gestor: **{row['manager']} / {row['code']}**; use somente as contas e o perfil anunciante deste gestor.
- Sites EN: `yolokfx.com` e `vizioid.com`.
- Site ES: `mavroa.com`; os criativos/copies precisam estar em espanhol. A pasta `SHEIN_US_ES` será criada quando o intake ES começar.
- No primeiro pedido de cada conta, informe a conta/perfil ou alias, site/idioma, modo e quantidade, budget/moeda e início/status. O Ares valida conta, timezone, moeda, saúde e capacidade antes do write.
- Nunca envie token no Discord. O token do perfil deve ficar no 1Password e o Ares registra somente a referência segura.
- Relatórios, Intraday/Otimização e automações ficam para uma fase posterior definida pelo Rodolfo.

O Ares pergunta somente o que bloquear a criação e conclui cada write com readback Meta."""


def persist_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    token = load_token()
    status, me = request(token, "GET", "/users/@me")
    if status != 200 or me.get("id") != ARES_ID:
        raise RuntimeError("Ares Discord identity readback failed")

    plan = []
    for row in CHANNELS:
        channel_status, channel = request(token, "GET", f"/channels/{row['channel_id']}")
        if channel_status != 200 or channel.get("name") != row["channel_name"]:
            raise RuntimeError(f"channel readback failed for {row['code']}")
        title = f"Criar Campanhas SHEIN {row['code']}"
        matches = exact_threads(token, row["channel_id"], title)
        if len(matches) > 1:
            raise RuntimeError(f"multiple exact fixed threads for {row['code']}")
        plan.append({**row, "title": title, "existing_thread_id": matches[0]["id"] if matches else None})

    if not args.apply:
        print(json.dumps({"success": True, "apply": False, "channels": 6, "create": sum(not row["existing_thread_id"] for row in plan), "reuse": sum(bool(row["existing_thread_id"]) for row in plan)}))
        return 0

    state = {"request": "shein-phase1-fixed-create-threads-20260911", "items": {}}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    state.setdefault("items", {})

    result_items = []
    for row in plan:
        item = state["items"].setdefault(row["code"], {})
        thread_id = item.get("thread_id") or row["existing_thread_id"]
        created = False
        if not thread_id:
            post_status, created_payload = request(
                token,
                "POST",
                f"/channels/{row['channel_id']}/threads",
                {"name": row["title"], "type": 11, "auto_archive_duration": 1440},
            )
            if post_status == 0:
                matches = exact_threads(token, row["channel_id"], row["title"])
                if len(matches) == 1:
                    thread_id = matches[0]["id"]
                else:
                    raise RuntimeError(f"ambiguous thread creation response for {row['code']}")
            elif post_status not in {200, 201} or not created_payload.get("id"):
                raise RuntimeError(f"thread create HTTP {post_status} for {row['code']}")
            else:
                thread_id = created_payload["id"]
                created = True
            item.update({"thread_id": thread_id, "created": created})
            persist_state(state)

        thread_status, thread = request(token, "GET", f"/channels/{thread_id}")
        if thread_status != 200 or thread.get("parent_id") != row["channel_id"] or thread.get("name") != row["title"]:
            raise RuntimeError(f"thread identity readback failed for {row['code']}")
        if thread.get("thread_metadata", {}).get("archived"):
            patch_status, _ = request(token, "PATCH", f"/channels/{thread_id}", {"archived": False})
            if patch_status != 200:
                raise RuntimeError(f"thread unarchive HTTP {patch_status} for {row['code']}")
            thread_status, thread = request(token, "GET", f"/channels/{thread_id}")
            if thread_status != 200 or thread.get("thread_metadata", {}).get("archived"):
                raise RuntimeError(f"thread unarchive readback failed for {row['code']}")

        expected_members = unique([ZEUS_ID, RODOLFO_ID, GEIZIAN_ID, row["manager_id"]])
        for user_id in expected_members:
            member_status, _ = request(token, "GET", f"/channels/{thread_id}/thread-members/{user_id}")
            if member_status != 200:
                put_status, _ = request(token, "PUT", f"/channels/{thread_id}/thread-members/{user_id}")
                if put_status != 204:
                    raise RuntimeError(f"member add HTTP {put_status} for {row['code']}")
                member_status, _ = request(token, "GET", f"/channels/{thread_id}/thread-members/{user_id}")
            if member_status != 200:
                raise RuntimeError(f"member readback failed for {row['code']}")

        content = seed_content(row)
        messages = recent_messages(token, thread_id)
        exact = [message for message in messages if message.get("content") == content and (message.get("author") or {}).get("id") == ARES_ID]
        if len(exact) > 1:
            raise RuntimeError(f"duplicate exact seed messages for {row['code']}")
        if exact:
            message_id = exact[0]["id"]
        else:
            message_status, message = request(token, "POST", f"/channels/{thread_id}/messages", {"content": content})
            if message_status == 0:
                exact = [message for message in recent_messages(token, thread_id) if message.get("content") == content and (message.get("author") or {}).get("id") == ARES_ID]
                if len(exact) != 1:
                    raise RuntimeError(f"ambiguous seed response for {row['code']}")
                message_id = exact[0]["id"]
            elif message_status not in {200, 201} or not message.get("id"):
                raise RuntimeError(f"seed post HTTP {message_status} for {row['code']}")
            else:
                message_id = message["id"]
            item["seed_message_id"] = message_id
            persist_state(state)

        read_status, readback = request(token, "GET", f"/channels/{thread_id}/messages/{message_id}")
        if read_status != 200 or readback.get("content") != content or (readback.get("author") or {}).get("id") != ARES_ID:
            raise RuntimeError(f"seed message readback failed for {row['code']}")

        result_items.append(
            {
                "manager_code": row["code"],
                "manager_name": row["manager"],
                "parent_channel_id": row["channel_id"],
                "thread_id": thread_id,
                "thread_name": row["title"],
                "created": created,
                "archived": False,
                "expected_member_ids": expected_members,
                "members_readback": True,
                "seed_message_id": message_id,
                "seed_message_readback": True,
            }
        )

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "request": state["request"],
        "success": True,
        "channels": len(result_items),
        "created": sum(item["created"] for item in result_items),
        "reused": sum(not item["created"] for item in result_items),
        "threads": result_items,
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"success": True, "channels": result["channels"], "created": result["created"], "reused": result["reused"], "members_readback": 6, "seed_readback": 6}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
