#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROFILE_ROOT = Path("/root/.hermes/profiles/ares")
CONFIG = PROFILE_ROOT / "config.yaml"
DELETED_ROUTES = Path("/root/mgs-agent/data/ares/discord/shein-fixed-routes.json")
RESULT = Path("/root/mgs-agent/work/ares-shein-onboarding-20260911/post-restart-channel-validation.json")
AUDIT = Path("/root/mgs-agent/logs/events-audit.jsonl")
THREAD_ID = "1548151961499734066"
ARES_ID = "1508864261504630925"
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
    headers = {"Authorization": "Bot " + token, "User-Agent": "MGS-Ares-PostRestartValidation/2.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request("https://discord.com/api/v10" + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        if exc.code == 429:
            time.sleep(min(10.0, float(payload.get("retry_after", 1.0))))
            return discord_request(token, method, path, body)
        return exc.code, payload


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


def update_checkpoint(success: bool) -> bool:
    state = (
        "completed: six SHEIN manager channels are active after a fresh Ares restart; profile YAML routing, process auto-add mapping and 6/6 Discord channel readbacks passed. The six trial creation threads and their contained messages were deleted by Rodolfo request and verified absent; phase 1 has no fixed threads."
        if success
        else "blocked after correction: the SHEIN post-restart validation still did not pass; configuration and deletion audit are preserved and active runtime status must not be claimed."
    )
    next_step = (
        "Each manager starts natural campaign-creation conversations in their own channel. On the first request per account, bind the manager's 1Password token reference, read back account/currency/timezone/health/tier and register an alias before Campaign Engine v3 execution."
        if success
        else "Reconcile only the failed validation layer from the persisted result, without recreating the six deleted threads or expanding campaign scope."
    )
    completed = subprocess.run(
        [
            "python3", "/root/mgs-agent/scripts/mgs-knowledge-control.py", "checkpoint-upsert",
            "--id", "ARES-SHEIN-US-DIRECT-ONBOARDING-20260911",
            "--agent", "ares",
            "--thread-id", THREAD_ID,
            "--objective", "Onboard the SHEIN US direct-traffic operation across six manager channels, inventory live Drive creatives, and activate safe campaign-creation routing without fixed threads.",
            "--state", state,
            "--next-step", next_step,
            "--source", "discord:thread:1548151961499734066; data/ares/meta-ads/operations/SHEIN-US-DIRECT.json; data/ares/discord/shein-fixed-routes-deletion-20260912.json",
        ],
        cwd="/root/mgs-agent",
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    return completed.returncode == 0


def main() -> int:
    deadline = time.monotonic() + 240
    token = parse_env_file()["DISCORD_BOT_TOKEN"]
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    discord_config = config.get("discord") or {}
    deleted_registry = json.loads(DELETED_ROUTES.read_text(encoding="utf-8"))
    deleted_thread_ids = [row["thread_id"] for row in (deleted_registry.get("threads") or {}).values()]
    errors: list[str] = []
    verified_channels = 0
    deleted_absent = 0
    allowed_ok = False
    free_ok = False
    runtime_mapping_ok = False
    deleted_prompts_absent = False

    while time.monotonic() < deadline:
        errors = []
        snapshot = service_snapshot()
        if snapshot.get("ActiveState") != "active" or snapshot.get("SubState") != "running":
            time.sleep(3)
            continue
        pid = snapshot.get("MainPID", "")
        if not pid.isdigit() or pid == "0":
            time.sleep(3)
            continue
        try:
            env = process_environment(pid)
        except OSError:
            time.sleep(3)
            continue

        # The gateway reads allowed/free channels from raw profile YAML. Only the
        # MGS auto-add extension is bridged into process env. Requiring env copies
        # for allowed/free caused the prior false negative.
        allowed_ok = contains_all(str(discord_config.get("allowed_channels", "")), CHANNEL_IDS)
        free_ok = contains_all(str(discord_config.get("free_response_channels", "")), CHANNEL_IDS)
        try:
            runtime_mapping = json.loads(env.get("DISCORD_THREAD_AUTO_ADD_USERS_BY_CHANNEL", "{}"))
        except json.JSONDecodeError:
            runtime_mapping = {}
        runtime_mapping_ok = all(runtime_mapping.get(channel_id) == users for channel_id, users in EXPECTED_MAPPING.items())
        prompts = {str(key): str(value) for key, value in (discord_config.get("channel_prompts") or {}).items()}
        deleted_prompts_absent = not any(thread_id in prompts for thread_id in deleted_thread_ids)

        if not allowed_ok:
            errors.append("allowed_channels_config_missing")
        if not free_ok:
            errors.append("free_response_channels_config_missing")
        if not runtime_mapping_ok:
            errors.append("auto_add_mapping_runtime_missing")
        if not deleted_prompts_absent:
            errors.append("deleted_thread_prompt_still_active")

        verified_channels = 0
        for channel_id in CHANNEL_IDS:
            status, payload = discord_request(token, "GET", f"/channels/{channel_id}")
            if status == 200 and payload.get("id") == channel_id:
                verified_channels += 1
        if verified_channels != 6:
            errors.append("discord_channel_readback_incomplete")

        deleted_absent = 0
        for thread_id in deleted_thread_ids:
            status, _ = discord_request(token, "GET", f"/channels/{thread_id}")
            if status == 404:
                deleted_absent += 1
        if deleted_absent != 6:
            errors.append("deleted_threads_still_present")
        if not errors:
            break
        time.sleep(3)

    success = not errors and allowed_ok and free_ok and runtime_mapping_ok and verified_channels == 6 and deleted_absent == 6 and deleted_prompts_absent
    visible = (
        "✅ **SHEIN ativa no Ares:** 6/6 canais liberados para criação de campanhas, com auto-add por gestor validado e as 6 threads/mensagens removidas."
        if success
        else "⚠️ **SHEIN:** a validação corrigida ainda não fechou; não vou declarar o runtime ativo."
    )

    list_status, recent = discord_request(token, "GET", f"/channels/{THREAD_ID}/messages?limit=100")
    warning_matches = []
    if list_status == 200 and isinstance(recent, list):
        warning_matches = [
            message for message in recent
            if (message.get("author") or {}).get("id") == ARES_ID
            and str(message.get("content", "")).startswith("⚠️ **SHEIN:** a validação pós-reinício")
        ]
    corrected_in_place = False
    if success and warning_matches:
        message_id = warning_matches[0]["id"]
        post_status, _ = discord_request(token, "PATCH", f"/channels/{THREAD_ID}/messages/{message_id}", {"content": visible})
        corrected_in_place = post_status == 200
    else:
        post_status, posted = discord_request(token, "POST", f"/channels/{THREAD_ID}/messages", {"content": visible})
        message_id = posted.get("id") if post_status in {200, 201} else None

    readback_ok = False
    if message_id:
        get_status, readback = discord_request(token, "GET", f"/channels/{THREAD_ID}/messages/{message_id}")
        readback_ok = get_status == 200 and readback.get("content") == visible and readback.get("id") == message_id

    checkpoint_updated = update_checkpoint(success)
    result = {
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "allowed_channels_config": allowed_ok,
        "free_response_channels_config": free_ok,
        "auto_add_mapping_runtime": runtime_mapping_ok,
        "discord_channels_readback": verified_channels,
        "deleted_threads_readback_404": deleted_absent,
        "deleted_thread_prompts_absent": deleted_prompts_absent,
        "prior_false_negative_corrected_in_place": corrected_in_place,
        "visible_message_readback": readback_ok,
        "checkpoint_updated": checkpoint_updated,
        "errors": errors,
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    append_audit(
        {
            "ts": result["validated_at_utc"],
            "event": "ares_shein_channels_post_restart_validation_v2",
            "actor": "ares-post-restart-channel-validator",
            "source_thread_id": THREAD_ID,
            "status": "passed" if success else "failed",
            "validator_correction": "allowed/free channels are profile YAML settings, not process-env bridges",
            "evidence": {
                "allowed_channels_config": allowed_ok,
                "free_response_channels_config": free_ok,
                "auto_add_mapping_runtime": runtime_mapping_ok,
                "discord_channels_readback": verified_channels,
                "deleted_threads_readback_404": deleted_absent,
                "visible_message_readback": readback_ok,
            },
            "errors": errors,
        }
    )
    return 0 if success and readback_ok and checkpoint_updated else 1


if __name__ == "__main__":
    raise SystemExit(main())
