#!/usr/bin/env python3
"""Validate an MGS Discord per-channel thread auto-add policy.

The validator is order-independent for systemd properties, waits through a
bounded restart window, proves config/file-env/process-env/runtime-helper
parity, and optionally repairs membership on explicitly named existing
threads. It never prints bot credentials.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

DEFAULT_LAUNCHER = Path("/root/.local/bin/hermes")
DEFAULT_MGS_ROOT = Path("/root/mgs-agent")
ENV_KEY = "DISCORD_THREAD_AUTO_ADD_USERS_BY_CHANNEL"


class ValidationError(RuntimeError):
    def __init__(self, code: str, *, transient: bool = False):
        super().__init__(code)
        self.code = code
        self.transient = transient


def parse_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def parse_systemctl_properties(text: str) -> dict[str, str]:
    """Parse key=value output; property order is intentionally irrelevant."""
    result: dict[str, str] = {}
    for raw in text.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def systemd_snapshot(profile: str) -> dict[str, str]:
    service = f"{profile}-gateway.service"
    completed = subprocess.run(
        [
            "systemctl",
            "show",
            service,
            "--no-pager",
            "--property=ActiveState",
            "--property=SubState",
            "--property=MainPID",
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if completed.returncode != 0:
        raise ValidationError("systemd_show_failed", transient=True)
    values = parse_systemctl_properties(completed.stdout)
    if values.get("ActiveState") != "active" or values.get("SubState") != "running":
        raise ValidationError("gateway_not_ready", transient=True)
    pid = values.get("MainPID", "")
    if not pid.isdigit() or pid == "0":
        raise ValidationError("gateway_pid_missing", transient=True)
    return {"service": service, "pid": pid, **values}


def current_pid_connected(service: str, pid: str) -> bool:
    completed = subprocess.run(
        ["journalctl", f"_PID={pid}", "-u", service, "--no-pager", "-o", "cat"],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if completed.returncode != 0:
        return False
    text = completed.stdout
    return "Connected as" in text and ("discord connected" in text or "platform(s)" in text)


def read_mapping(value: str, *, code: str) -> dict[str, list[str]]:
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(code) from exc
    if not isinstance(parsed, dict):
        raise ValidationError(code)
    result: dict[str, list[str]] = {}
    for channel, users in parsed.items():
        if users is None:
            rows: list[Any] = []
        elif isinstance(users, str):
            rows = users.split(",")
        elif isinstance(users, list):
            rows = users
        else:
            raise ValidationError(code)
        result[str(channel)] = [str(user).strip() for user in rows if str(user).strip()]
    return result


def config_mapping(path: Path) -> dict[str, list[str]]:
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        mapping = (config.get("discord") or {}).get("thread_auto_add_users_by_channel")
    except Exception as exc:
        raise ValidationError("config_invalid") from exc
    if not isinstance(mapping, dict):
        raise ValidationError("config_mapping_missing")
    return read_mapping(json.dumps(mapping), code="config_mapping_invalid")


def process_mapping(pid: str) -> dict[str, list[str]]:
    try:
        raw = (Path("/proc") / pid / "environ").read_bytes().split(b"\0")
    except OSError as exc:
        raise ValidationError("process_environ_unavailable", transient=True) from exc
    values: dict[str, str] = {}
    for item in raw:
        if b"=" in item:
            key, value = item.split(b"=", 1)
            values[key.decode(errors="replace")] = value.decode(errors="replace")
    if ENV_KEY not in values:
        raise ValidationError("process_mapping_missing", transient=True)
    try:
        return read_mapping(values[ENV_KEY], code="process_mapping_invalid")
    except ValidationError as exc:
        raise ValidationError(exc.code, transient=True) from exc


def resolve_active_runtime(launcher: Path = DEFAULT_LAUNCHER) -> tuple[Path, Path]:
    try:
        wrapper = launcher.resolve(strict=True)
        first = wrapper.open("r", encoding="utf-8").readline().strip()
        if not first.startswith("#!"):
            raise ValueError("missing_shebang")
        command = shlex.split(first[2:].strip())
        if not command or command[0] == "/usr/bin/env":
            raise ValueError("ambiguous_interpreter")
        python = Path(command[0])
        repo = python.parent.parent.parent
        if not python.is_file() or not (repo / "plugins/platforms/discord/adapter.py").is_file():
            raise FileNotFoundError("runtime_incomplete")
    except (OSError, ValueError) as exc:
        raise ValidationError("active_runtime_unresolvable") from exc
    return repo, python


def runtime_helper_targets(mapping: dict[str, list[str]], channel_id: str) -> tuple[list[str], bool]:
    repo, python = resolve_active_runtime()
    code = (
        "import json,sys; "
        "from plugins.platforms.discord.adapter import _discord_thread_auto_add_user_ids as f; "
        "users,configured=f(sys.argv[1]); "
        "print(json.dumps({'users':users,'configured':configured},separators=(',',':')))"
    )
    env = os.environ.copy()
    env[ENV_KEY] = json.dumps(mapping, separators=(",", ":"))
    completed = subprocess.run(
        [str(python), "-c", code, channel_id],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        raise ValidationError("runtime_helper_failed")
    try:
        data = json.loads(completed.stdout.strip())
        users = [str(value) for value in data["users"]]
        configured = data["configured"] is True
    except Exception as exc:
        raise ValidationError("runtime_helper_invalid") from exc
    return users, configured


def discord_request(token: str, method: str, path: str) -> tuple[int, Any]:
    request = urllib.request.Request(
        "https://discord.com/api/v10" + path,
        data=b"" if method != "GET" else None,
        method=method,
        headers={"Authorization": "Bot " + token, "User-Agent": "MGS-ThreadPolicy/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode(errors="ignore")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except Exception as exc:
        raise ValidationError("discord_request_failed", transient=True) from exc


def ensure_thread_members(
    token: str,
    thread_ids: list[str],
    expected_users: list[str],
    *,
    repair: bool,
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for thread_id in thread_ids:
        status, channel = discord_request(token, "GET", f"/channels/{thread_id}")
        if status != 200:
            raise ValidationError(f"thread_channel_http_{status}", transient=status == 429)
        row: dict[str, int] = {"channel": status}
        for user_id in expected_users:
            member_path = f"/channels/{thread_id}/thread-members/{user_id}"
            member_status, _ = discord_request(token, "GET", member_path)
            if member_status != 200 and repair:
                put_status, _ = discord_request(token, "PUT", member_path)
                if put_status != 204:
                    raise ValidationError(f"thread_member_put_http_{put_status}", transient=put_status == 429)
                member_status, _ = discord_request(token, "GET", member_path)
            if member_status != 200:
                raise ValidationError(f"thread_member_get_http_{member_status}", transient=member_status == 429)
            row[user_id] = member_status
        result[thread_id] = row
    return result


def append_audit(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def validate_once(args: argparse.Namespace) -> dict[str, Any]:
    profile_root = Path("/root/.hermes/profiles") / args.profile
    live_config = profile_root / "config.yaml"
    mirror_config = DEFAULT_MGS_ROOT / "profiles" / f"{args.profile}-config.yaml"
    env_file = parse_env(profile_root / ".env")
    token = env_file.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise ValidationError("bot_token_missing")

    live_mapping = config_mapping(live_config)
    mirror_mapping = config_mapping(mirror_config)
    if live_mapping != mirror_mapping:
        raise ValidationError("live_mirror_mapping_drift")
    expected = args.expected_user
    if live_mapping.get(args.channel_id) != expected:
        raise ValidationError("config_targets_mismatch")
    if ENV_KEY not in env_file:
        raise ValidationError("env_mapping_missing")
    file_mapping = read_mapping(env_file[ENV_KEY], code="env_mapping_invalid")
    if file_mapping.get(args.channel_id) != expected:
        raise ValidationError("env_targets_mismatch")

    systemd = systemd_snapshot(args.profile)
    runtime_mapping = process_mapping(systemd["pid"])
    if runtime_mapping.get(args.channel_id) != expected:
        raise ValidationError("process_targets_mismatch", transient=True)
    if not current_pid_connected(systemd["service"], systemd["pid"]):
        raise ValidationError("discord_connection_not_ready", transient=True)

    helper_users, helper_configured = runtime_helper_targets(runtime_mapping, args.channel_id)
    if not helper_configured or helper_users != expected:
        raise ValidationError("runtime_helper_targets_mismatch")

    thread_readback = ensure_thread_members(
        token,
        args.thread_id,
        expected,
        repair=args.repair_existing_members,
    )
    return {
        "success": True,
        "profile": args.profile,
        "channel_id": args.channel_id,
        "expected_users": expected,
        "service": systemd["service"],
        "pid": systemd["pid"],
        "config_live_mirror_parity": True,
        "file_env_targets": expected,
        "process_env_targets": expected,
        "runtime_helper_targets": helper_users,
        "runtime_helper_configured": helper_configured,
        "discord_connected_current_pid": True,
        "threads_readback": thread_readback,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--profile", required=True)
    value.add_argument("--channel-id", required=True)
    value.add_argument("--expected-user", action="append", required=True)
    value.add_argument("--thread-id", action="append", default=[])
    value.add_argument("--repair-existing-members", action="store_true")
    value.add_argument("--timeout", type=int, default=300)
    value.add_argument("--poll-interval", type=float, default=2.0)
    value.add_argument("--audit-path", type=Path)
    value.add_argument("--source-thread-id")
    return value


def main() -> int:
    args = parser().parse_args()
    deadline = time.monotonic() + max(1, args.timeout)
    last_error = "validation_not_started"
    while True:
        try:
            result = validate_once(args)
            result["validated_at"] = datetime.now(timezone.utc).isoformat()
            if args.audit_path:
                append_audit(args.audit_path, {
                    "ts": result["validated_at"],
                    "event": "discord_thread_auto_add_policy_validated",
                    "actor": "mgs-thread-policy-validator",
                    "source_thread_id": args.source_thread_id,
                    "profile": args.profile,
                    "channel_id": args.channel_id,
                    "expected_users": args.expected_user,
                    "threads": args.thread_id,
                    "status": "passed",
                    "evidence": {
                        "config_live_mirror_parity": True,
                        "process_env_parity": True,
                        "runtime_helper_parity": True,
                        "discord_current_pid_connected": True,
                        "thread_readback_count": len(args.thread_id),
                    },
                })
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
            return 0
        except ValidationError as exc:
            last_error = exc.code
            if not exc.transient or time.monotonic() >= deadline:
                break
            time.sleep(max(0.1, args.poll_interval))
    failed = {
        "success": False,
        "profile": args.profile,
        "channel_id": args.channel_id,
        "error_code": last_error,
    }
    if args.audit_path:
        append_audit(args.audit_path, {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "discord_thread_auto_add_policy_validated",
            "actor": "mgs-thread-policy-validator",
            "source_thread_id": args.source_thread_id,
            "profile": args.profile,
            "channel_id": args.channel_id,
            "status": "failed",
            "error_code": last_error,
        })
    print(json.dumps(failed, ensure_ascii=False, separators=(",", ":")))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
