#!/usr/bin/env python3
"""Cross-agent lease for the shared PC1 interactive desktop.

Zeus and Ares must not send concurrent Computer Use input to the same Windows
session. This helper provides a credential-free, expiring lease with atomic
state transitions. Runtime state stays outside Git under /root/.hermes.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, NoReturn

DEFAULT_ROOT = Path("/root/.hermes/shared/locks")
DEFAULT_TTL = 900
MAX_TTL = 3600
ALLOWED_AGENTS = ("zeus", "ares")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def emit(payload: dict[str, Any], exit_code: int = 0) -> NoReturn:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    raise SystemExit(exit_code)


def read_state(path: Path) -> dict[str, Any] | None:
    value: Any = None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        emit({"ok": False, "reason": "invalid_lock_state", "detail": type(exc).__name__}, 3)
    return value if isinstance(value, dict) else None


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def active_state(path: Path, now: datetime) -> dict[str, Any] | None:
    state = read_state(path)
    if not state:
        return None
    expiry = parse_time(str(state.get("expires_at", "")))
    if expiry is None or expiry <= now:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return None
    return state


def public_state(state: dict[str, Any] | None, now: datetime) -> dict[str, Any]:
    if not state:
        return {"locked": False}
    expiry = parse_time(str(state.get("expires_at", "")))
    remaining = max(0, int((expiry - now).total_seconds())) if expiry else 0
    return {
        "locked": True,
        "agent": state.get("agent"),
        "session_id": state.get("session_id"),
        "thread_id": state.get("thread_id"),
        "acquired_at": state.get("acquired_at"),
        "expires_at": state.get("expires_at"),
        "remaining_seconds": remaining,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lease the shared MGS PC1 Computer Use desktop")
    parser.add_argument("action", choices=("status", "acquire", "renew", "release"))
    parser.add_argument("--agent", choices=ALLOWED_AGENTS)
    parser.add_argument("--session-id")
    parser.add_argument("--thread-id")
    parser.add_argument("--ttl", type=int, default=DEFAULT_TTL)
    return parser


def require_identity(args: argparse.Namespace) -> None:
    if not args.agent or not args.session_id:
        emit({"ok": False, "reason": "agent_and_session_required"}, 2)
    if len(args.session_id) > 160 or (args.thread_id and len(args.thread_id) > 160):
        emit({"ok": False, "reason": "identifier_too_long"}, 2)
    if args.ttl < 60 or args.ttl > MAX_TTL:
        emit({"ok": False, "reason": "ttl_out_of_range", "min": 60, "max": MAX_TTL}, 2)


def main() -> None:
    args = build_parser().parse_args()
    root = Path(os.environ.get("MGS_PC1_CUA_LOCK_ROOT", str(DEFAULT_ROOT)))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    state_path = root / "pc1-computer-use.json"
    guard_path = root / "pc1-computer-use.guard"

    with guard_path.open("a+", encoding="utf-8") as guard:
        os.chmod(guard_path, 0o600)
        fcntl.flock(guard.fileno(), fcntl.LOCK_EX)
        now = utc_now()
        state = active_state(state_path, now)

        if args.action == "status":
            emit({"ok": True, **public_state(state, now)})

        require_identity(args)
        same_owner = bool(
            state
            and state.get("agent") == args.agent
            and state.get("session_id") == args.session_id
        )

        if args.action == "acquire":
            if state and not same_owner:
                emit({"ok": False, "reason": "lock_held", **public_state(state, now)}, 2)
            acquired_at = state.get("acquired_at") if state else iso(now)
            next_state = {
                "version": 1,
                "resource": "pc1-interactive-desktop",
                "agent": args.agent,
                "session_id": args.session_id,
                "thread_id": args.thread_id or (state.get("thread_id") if state else None),
                "acquired_at": acquired_at,
                "updated_at": iso(now),
                "expires_at": iso(now + timedelta(seconds=args.ttl)),
            }
            write_state(state_path, next_state)
            emit({"ok": True, "action": "acquired" if not state else "renewed", **public_state(next_state, now)})

        if args.action == "renew":
            if not state:
                emit({"ok": False, "reason": "lock_not_held"}, 2)
            if not same_owner:
                emit({"ok": False, "reason": "owner_mismatch", **public_state(state, now)}, 2)
            assert state is not None
            state["updated_at"] = iso(now)
            state["expires_at"] = iso(now + timedelta(seconds=args.ttl))
            if args.thread_id:
                state["thread_id"] = args.thread_id
            write_state(state_path, state)
            emit({"ok": True, "action": "renewed", **public_state(state, now)})

        if args.action == "release":
            if not state:
                emit({"ok": True, "action": "already_free", "locked": False})
            if not same_owner:
                emit({"ok": False, "reason": "owner_mismatch", **public_state(state, now)}, 2)
            try:
                state_path.unlink()
            except FileNotFoundError:
                pass
            emit({"ok": True, "action": "released", "locked": False})

    emit({"ok": False, "reason": "unreachable"}, 3)


if __name__ == "__main__":
    main()
