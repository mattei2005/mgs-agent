from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIVE_OPERATION_STATES = {
    "PREFLIGHT_ACTIVE",
    "ASSETS_RESERVED",
    "MEDIA_READY",
    "MANIFEST_SEALED",
    "IN_PROGRESS",
    "DEFERRED_QUOTA",
    "READBACK_DEFERRED",
    "PARTIAL_DEFERRED_QUOTA",
    "POSTPROCESS_PENDING",
    "RECOVERY_PENDING",
    "FIRST_DELIVERY_ARM_IN_FLIGHT",
}


class WriterLeaseConflict(RuntimeError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


class AccountWriterLeaseStore:
    def __init__(self, state_root: Path | str):
        self.root = Path(state_root) / "writer-leases"
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)

    def path(self, account_id: str) -> Path:
        safe = "".join(ch for ch in str(account_id) if ch.isdigit())
        if not safe:
            raise ValueError("invalid account_id")
        return self.root / f"{safe}.json"

    def _locked_update(self, account_id: str, mutator) -> dict[str, Any]:
        path = self.path(account_id)
        lock_path = path.with_suffix(".lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "r+") as lock:
            os.fchmod(lock.fileno(), 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            current = _load(path)
            updated = mutator(current)
            tmp = path.with_suffix(f".json.{os.getpid()}.tmp")
            tmp.write_text(json.dumps(updated, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
            fcntl.flock(lock, fcntl.LOCK_UN)
        return updated

    def claim(self, account_id: str, request_id: str, *, status: str = "IN_PROGRESS") -> dict[str, Any]:
        request_id = str(request_id)

        def mutate(current: dict[str, Any]) -> dict[str, Any]:
            if current.get("blocks_readers") and current.get("request_id") not in {None, "", request_id}:
                raise WriterLeaseConflict(
                    f"account {account_id} already has active writer request {current.get('request_id')}"
                )
            return {
                "schema_version": 1,
                "account_id": str(account_id),
                "request_id": request_id,
                "status": str(status),
                "blocks_readers": True,
                "updated_at_utc": _utc(),
                "started_at_utc": current.get("started_at_utc") or _utc(),
            }

        return self._locked_update(account_id, mutate)

    def mark(self, account_id: str, request_id: str, status: str) -> dict[str, Any]:
        return self.claim(account_id, request_id, status=status)

    def release(self, account_id: str, request_id: str) -> dict[str, Any]:
        request_id = str(request_id)

        def mutate(current: dict[str, Any]) -> dict[str, Any]:
            if current.get("request_id") not in {None, "", request_id}:
                raise WriterLeaseConflict("cannot release another request's writer lease")
            released = dict(current)
            released.update({
                "schema_version": 1,
                "account_id": str(account_id),
                "request_id": request_id,
                "status": "COMPLETE",
                "blocks_readers": False,
                "updated_at_utc": _utc(),
                "released_at_utc": _utc(),
            })
            return released

        return self._locked_update(account_id, mutate)


def reader_block_reason(
    account_id: str,
    state_root: Path | str,
    *,
    operation_state: Path | str | None = None,
) -> dict[str, Any] | None:
    lease = _load(AccountWriterLeaseStore(state_root).path(account_id))
    if lease.get("blocks_readers") is True and str(lease.get("status") or "") != "COMPLETE":
        return {
            "source": "writer_lease",
            "request_id": lease.get("request_id"),
            "status": lease.get("status"),
        }
    if operation_state:
        state = _load(Path(operation_state))
        status = str(state.get("status") or "")
        if status in ACTIVE_OPERATION_STATES:
            return {"source": "operation_state", "request_id": state.get("request_id"), "status": status}
    return None