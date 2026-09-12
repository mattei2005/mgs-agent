#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

API = "https://discord.com/api/v10"
GUILD_ID = "1185714635991679006"
ARES_ID = "1508864261504630925"
ZEUS_ID = "1496296175014252634"
RODOLFO_ID = "344196393512075265"
GEIZIAN_ID = "321263240782807040"
CHANNELS = [
    ("1548149087206121613", "409878085807112207"),
    ("1548149300826079333", "321263240782807040"),
    ("1548149483039236137", "432898782188011543"),
    ("1548149654926135486", "1214246869484576890"),
    ("1548150015275438220", "1291113428982693940"),
    ("1548150155184701440", "1055570806945620030"),
]
BITS = {
    "VIEW_CHANNEL": 1 << 10,
    "SEND_MESSAGES": 1 << 11,
    "READ_MESSAGE_HISTORY": 1 << 16,
    "MANAGE_CHANNELS": 1 << 4,
    "MANAGE_ROLES": 1 << 28,
    "MANAGE_THREADS": 1 << 34,
    "CREATE_PUBLIC_THREADS": 1 << 35,
    "CREATE_PRIVATE_THREADS": 1 << 36,
    "SEND_MESSAGES_IN_THREADS": 1 << 38,
}
ADMINISTRATOR = 1 << 3


def env_values(path: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            output[key.strip()] = value.strip().strip('"').strip("'")
    return output


def get(token: str, path: str):
    request = urllib.request.Request(
        API + path,
        headers={"Authorization": "Bot " + token, "User-Agent": "MGS-Ares-ChannelAudit/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def permissions(channel: dict, member: dict, roles_by_id: dict[str, dict]) -> int:
    everyone = roles_by_id[GUILD_ID]
    value = int(everyone.get("permissions", "0"))
    member_roles = [roles_by_id[role_id] for role_id in member.get("roles", []) if role_id in roles_by_id]
    for role in member_roles:
        value |= int(role.get("permissions", "0"))
    if value & ADMINISTRATOR:
        return (1 << 64) - 1

    overwrites = channel.get("permission_overwrites", [])
    everyone_ow = next((ow for ow in overwrites if ow.get("id") == GUILD_ID), None)
    if everyone_ow:
        value &= ~int(everyone_ow.get("deny", "0"))
        value |= int(everyone_ow.get("allow", "0"))

    role_ids = set(member.get("roles", []))
    role_deny = 0
    role_allow = 0
    for overwrite in overwrites:
        if overwrite.get("type") == 0 and overwrite.get("id") in role_ids:
            role_deny |= int(overwrite.get("deny", "0"))
            role_allow |= int(overwrite.get("allow", "0"))
    value &= ~role_deny
    value |= role_allow

    user_id = (member.get("user") or {}).get("id")
    member_ow = next(
        (overwrite for overwrite in overwrites if overwrite.get("type") == 1 and overwrite.get("id") == user_id),
        None,
    )
    if member_ow:
        value &= ~int(member_ow.get("deny", "0"))
        value |= int(member_ow.get("allow", "0"))
    return value


def main() -> int:
    token = env_values(Path("/root/.hermes/profiles/ares/.env"))["DISCORD_BOT_TOKEN"]
    status, me = get(token, "/users/@me")
    if status != 200 or me.get("id") != ARES_ID:
        raise RuntimeError("Ares bot identity validation failed")
    status, roles = get(token, f"/guilds/{GUILD_ID}/roles")
    if status != 200:
        raise RuntimeError(f"guild roles HTTP {status}")
    roles_by_id = {role["id"]: role for role in roles}

    member_cache: dict[str, dict] = {}
    for user_id in {ARES_ID, ZEUS_ID, RODOLFO_ID, GEIZIAN_ID, *[manager_id for _, manager_id in CHANNELS]}:
        member_status, member = get(token, f"/guilds/{GUILD_ID}/members/{user_id}")
        if member_status != 200:
            raise RuntimeError(f"guild member {user_id} HTTP {member_status}")
        member_cache[user_id] = member

    output = []
    required_for_ares = [
        "VIEW_CHANNEL",
        "SEND_MESSAGES",
        "READ_MESSAGE_HISTORY",
        "CREATE_PUBLIC_THREADS",
        "SEND_MESSAGES_IN_THREADS",
        "MANAGE_THREADS",
    ]
    for channel_id, manager_id in CHANNELS:
        channel_status, channel = get(token, f"/channels/{channel_id}")
        if channel_status != 200:
            raise RuntimeError(f"channel {channel_id} HTTP {channel_status}")
        ares_value = permissions(channel, member_cache[ARES_ID], roles_by_id)
        manager_value = permissions(channel, member_cache[manager_id], roles_by_id)
        zeus_value = permissions(channel, member_cache[ZEUS_ID], roles_by_id)
        rodolfo_value = permissions(channel, member_cache[RODOLFO_ID], roles_by_id)
        geizian_value = permissions(channel, member_cache[GEIZIAN_ID], roles_by_id)
        ares_flags = {name: bool(ares_value & bit) for name, bit in BITS.items()}
        if not all(ares_flags[name] for name in required_for_ares):
            raise RuntimeError(f"Ares missing required permissions in {channel_id}")
        for label, value in (
            ("manager", manager_value),
            ("Zeus", zeus_value),
            ("Rodolfo", rodolfo_value),
            ("Geizian", geizian_value),
        ):
            if not value & BITS["VIEW_CHANNEL"]:
                raise RuntimeError(f"{label} cannot view {channel_id}")
        output.append(
            {
                "channel_id": channel_id,
                "channel_name": channel.get("name"),
                "http": channel_status,
                "type": channel.get("type"),
                "parent_id": channel.get("parent_id"),
                "assigned_manager_id": manager_id,
                "ares_permissions": ares_flags,
                "participants_can_view": {
                    "assigned_manager": True,
                    "Zeus": True,
                    "Rodolfo": True,
                    "Geizian": True,
                },
            }
        )
    result = {"success": True, "bot_identity": "Ares", "guild_id": GUILD_ID, "channels": output}
    path = Path("/root/mgs-agent/work/ares-shein-onboarding-20260911/discord-channel-permissions-readback.json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"success": True, "channels_verified": len(output), "required_permissions": required_for_ares}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
