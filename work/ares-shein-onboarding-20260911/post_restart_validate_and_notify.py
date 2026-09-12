#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROFILE_ROOT = Path("/root/.hermes/profiles/ares")
RESULT = Path("/root/mgs-agent/work/ares-shein-onboarding-20260911/post-restart-channel-validation.json")
AUDIT = Path("/root/mgs-agent/logs/events-audit.jsonl")
THREAD_ID = "1548151961499734066"
CHANNEL_IDS = [
    "1548149087206121613",
    "1548149300826079333",
    "1548149483039236137",
    "1548149654926135486",
    "1548150015275438220",
    "1548150155184701440",
]
EXPECTED_MAPPING = {
    "1548149087206121613": ["1496296175014252634", "344196393512075265", "321263240782807040", "409878085807112207"],
    "1548149300826079333": ["1496296175014252634", "344196393512075265", "321263240782807040"],
    "1548149483039236137": ["1496296175014252634", "344196393512075265", "321263240782807040", "432898782188011543"],
    "1548149654926135486": ["1496296175014252634", "344196393512075265", "321263240782807040", "1214246869484576890"],
    "1548150015275438220": ["1496296175014252634", "344196393512075265", "321263240782807040", "1291113428982693940"],
    "1548150155184701440": ["1496296175014252634", "344196393512075265", "321263240782807040", "1055570806945620030"],
}


def parse_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in (PROFILE_ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def discord_request(token: str, method: str, path: str, body: dict | None = None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Authorization": "Bot " + token, "User-Agent": "MGS-Ares-PostRestartValidation/1.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request("https://discord.com/api/v10" + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def service_snapshot() -> dict[str, str]:
    completed = subprocess.run(
        [
            "systemctl", "show", "ares-gateway.service", "--no-pager",
            "--property=ActiveState", "--property=SubState", "--property=MainPID",
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if completed.returncode != 0:
        return {}
    output: dict[str, str] = {}
    for raw in completed.stdout.splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            output[key] = value
    return output


def process_environment(pid: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in (Path("/proc") / pid / "environ").read_bytes().split(b"\0"):
        if b"=" in item:
            key, value = item.split(b"=", 1)
            values[key.decode(errors="replace")] = value.decode(errors="replace")
    return values


def contains_all(raw: str, expected: list[str]) -> bool:
    values = [part.strip() for part in raw.split(",") if part.strip()]
    return all(value in values for value in expected)


def append_audit(event: dict) -> None:
    with AUDIT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def main() -> int:
    deadline = time.monotonic() + 240
    errors: list[str] = []
    verified_channels = 0
    runtime_mapping_ok = False
    allowed_ok = False
    free_ok = False
    connected_ok = False
    token = parse_env_file()["DISCORD_BOT_TOKEN"]

    while time.monotonic() < deadline:
        errors = []
        snapshot = service_snapshot()
        if snapshot.get("ActiveState") != "active" or snapshot.get("SubState") != "running":
            errors.append("service_not_ready")
            time.sleep(3)
            continue
        pid = snapshot.get("MainPID", "")
        if not pid.isdigit() or pid == "0":
            errors.append("service_identity_missing")
            time.sleep(3)
            continue
        try:
            env = process_environment(pid)
        except OSError:
            errors.append("runtime_environment_unavailable")
            time.sleep(3)
            continue
        allowed_ok = contains_all(env.get("DISCORD_ALLOWED_CHANNELS", ""), CHANNEL_IDS)
        free_ok = contains_all(env.get("DISCORD_FREE_RESPONSE_CHANNELS", ""), CHANNEL_IDS)
        try:
            runtime_mapping = json.loads(env.get("DISCORD_THREAD_AUTO_ADD_USERS_BY_CHANNEL", "{}"))
        except json.JSONDecodeError:
            runtime_mapping = {}
        runtime_mapping_ok = all(runtime_mapping.get(channel_id) == users for channel_id, users in EXPECTED_MAPPING.items())
        if not allowed_ok:
            errors.append("allowed_channels_missing")
        if not free_ok:
            errors.append("free_response_channels_missing")
        if not runtime_mapping_ok:
            errors.append("auto_add_mapping_missing")

        verified_channels = 0
        for channel_id in CHANNEL_IDS:
            status, payload = discord_request(token, "GET", f"/channels/{channel_id}")
            if status == 200 and payload.get("id") == channel_id:
                verified_channels += 1
        connected_ok = verified_channels == len(CHANNEL_IDS)
        if not connected_ok:
            errors.append("discord_channel_readback_incomplete")
        if not errors:
            break
        time.sleep(3)

    success = not errors and allowed_ok and free_ok and runtime_mapping_ok and connected_ok
    visible = (
        "✅ **SHEIN ativa no Ares:** 6/6 canais liberados para conversa, auto-thread e auto-add por gestor, com readback pós-reinício confirmado."
        if success
        else "⚠️ **SHEIN:** a validação pós-reinício dos 6 canais não fechou; não vou declarar o runtime ativo. A causa ficou registrada para reconciliação."
    )
    post_status, posted = discord_request(token, "POST", f"/channels/{THREAD_ID}/messages", {"content": visible})
    message_id = posted.get("id") if post_status in {200, 201} else None
    readback_ok = False
    if message_id:
        get_status, readback = discord_request(token, "GET", f"/channels/{THREAD_ID}/messages/{message_id}")
        readback_ok = get_status == 200 and readback.get("content") == visible and readback.get("id") == message_id

    result = {
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "allowed_channels_runtime": allowed_ok,
        "free_response_channels_runtime": free_ok,
        "auto_add_mapping_runtime": runtime_mapping_ok,
        "discord_channels_readback": verified_channels,
        "visible_message_posted": bool(message_id),
        "visible_message_readback": readback_ok,
        "errors": errors,
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    append_audit(
        {
            "ts": result["validated_at_utc"],
            "event": "ares_shein_channels_post_restart_validation",
            "actor": "ares-post-restart-channel-validator",
            "source_thread_id": THREAD_ID,
            "status": "passed" if success else "failed",
            "evidence": {
                "allowed_channels_runtime": allowed_ok,
                "free_response_channels_runtime": free_ok,
                "auto_add_mapping_runtime": runtime_mapping_ok,
                "discord_channels_readback": verified_channels,
                "visible_message_readback": readback_ok,
            },
            "errors": errors,
        }
    )
    return 0 if success and readback_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
