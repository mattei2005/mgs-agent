#!/usr/bin/env python3
"""Serialize AdsPower MCP operations across Zeus and Ares without monopolizing PC1 while idle.

The proxy exposes stdio MCP to Hermes, runs the official AdsPower MCP on PC1 over
key-only SSH/Tailscale, and uses the shared PC1 lease only around active tool
sequences. It never prints credentials or remote stderr.
"""
from __future__ import annotations

import atexit
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

LOCK = "/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py"
SSH_KEY = "/root/.ssh/mgs-pc1-zeus_ed25519"
REMOTE = "matte@100.85.69.58"
REMOTE_LAUNCHER = r"C:\Users\matte\AppData\Local\MGS\AdsPowerMCP\start-adspower-mcp.ps1"
THREAD_ID = os.environ.get("MGS_ADSPOWER_THREAD_ID", "1517183244297179251")
AGENT = os.environ.get("MGS_ADSPOWER_OPERATOR", "")
LEASE_TTL = 240
LEASE_RENEW_EVERY = 60
LEASE_IDLE_RELEASE = 180
READ_ONLY_TOOLS = {
    "check-status",
    "get-browser-list",
    "get-opened-browser",
    "get-browser-active",
}
RELEASE_AFTER_TOOLS = {"close-browser"}

if AGENT not in {"zeus", "ares"}:
    print("AdsPower MCP proxy refused: invalid operator", file=sys.stderr, flush=True)
    raise SystemExit(64)
if not Path(LOCK).is_file() or not Path(SSH_KEY).is_file():
    print("AdsPower MCP proxy refused: required local transport missing", file=sys.stderr, flush=True)
    raise SystemExit(66)

SESSION_ID = f"adspower-mcp-{AGENT}-{os.getpid()}"
lease_lock = threading.RLock()
lease_held = False
last_tool_at = 0.0
stopping = threading.Event()
child: subprocess.Popen[str] | None = None


def _lock_cmd(action: str) -> subprocess.CompletedProcess[str]:
    args = [LOCK, action]
    if action in {"acquire", "renew", "release"}:
        args += ["--agent", AGENT, "--session-id", SESSION_ID]
    if action == "acquire":
        args += ["--thread-id", THREAD_ID, "--ttl", str(LEASE_TTL)]
    elif action == "renew":
        args += ["--ttl", str(LEASE_TTL)]
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)


def acquire_lease() -> bool:
    global lease_held, last_tool_at
    with lease_lock:
        if lease_held:
            last_tool_at = time.monotonic()
            return True
        result = _lock_cmd("acquire")
        if result.returncode != 0:
            return False
        lease_held = True
        last_tool_at = time.monotonic()
        return True


def release_lease() -> None:
    global lease_held
    with lease_lock:
        if not lease_held:
            return
        try:
            _lock_cmd("release")
        finally:
            lease_held = False


def lease_maintenance() -> None:
    global lease_held
    while not stopping.wait(5):
        with lease_lock:
            if not lease_held:
                continue
            idle = time.monotonic() - last_tool_at
            if idle >= LEASE_IDLE_RELEASE:
                try:
                    _lock_cmd("release")
                finally:
                    lease_held = False
                continue
            # Keep the lease alive for a multi-call AdsPower operation.
            if int(idle) % LEASE_RENEW_EVERY < 5:
                result = _lock_cmd("renew")
                if result.returncode != 0:
                    lease_held = False


def cleanup() -> None:
    stopping.set()
    release_lease()
    global child
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def handle_signal(signum: int, _frame: Any) -> None:
    cleanup()
    raise SystemExit(128 + signum)


atexit.register(cleanup)
signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGHUP, handle_signal)
threading.Thread(target=lease_maintenance, name="adspower-lease", daemon=True).start()

ssh_cmd = [
    "ssh", "-T", "-i", SSH_KEY,
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=yes",
    "-o", "ClearAllForwardings=yes",
    "-o", "ConnectTimeout=10",
    REMOTE,
    f"powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File {REMOTE_LAUNCHER}",
]
child = subprocess.Popen(
    ssh_cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
)
assert child.stdin is not None and child.stdout is not None and child.stderr is not None
child_stderr = child.stderr


def discard_stderr() -> None:
    for _ in child_stderr:
        pass


threading.Thread(target=discard_stderr, name="adspower-stderr", daemon=True).start()


def send_client(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def lease_busy(request_id: Any) -> None:
    send_client({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32001,
            "message": "PC1 AdsPower is busy in another authorized Zeus/Ares operation; retry after that lease is released.",
        },
    })


try:
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        request_id = request.get("id") if isinstance(request, dict) else None
        method = request.get("method") if isinstance(request, dict) else None
        params = request.get("params") if isinstance(request, dict) else None
        tool_name = params.get("name") if method == "tools/call" and isinstance(params, dict) else None
        tool_call = isinstance(tool_name, str)

        acquired_for_call = False
        if tool_call:
            if not acquire_lease():
                lease_busy(request_id)
                continue
            acquired_for_call = True

        child.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        child.stdin.flush()

        # Notifications do not have a response.
        if request_id is None:
            continue

        matched = False
        while not matched:
            response_line = child.stdout.readline()
            if not response_line:
                raise RuntimeError("remote AdsPower MCP closed its stdout")
            try:
                response = json.loads(response_line)
            except json.JSONDecodeError:
                continue
            send_client(response)
            matched = response.get("id") == request_id

        if acquired_for_call:
            with lease_lock:
                last_tool_at = time.monotonic()
            if tool_name in READ_ONLY_TOOLS or tool_name in RELEASE_AFTER_TOOLS:
                release_lease()
finally:
    cleanup()
