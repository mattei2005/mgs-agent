from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


class QuotaBlocked(RuntimeError):
    def __init__(self, detail: dict[str, Any]):
        self.detail = detail
        super().__init__("lane quota blocked")


class LaneQuotaStore:
    def __init__(self, root: Path | str, *, soft_score: int = 100, hard_score: int = 120, window_seconds: int = 300):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.soft_score = int(soft_score)
        self.hard_score = int(hard_score)
        self.window_seconds = int(window_seconds)
        if not (0 < self.soft_score <= self.hard_score):
            raise ValueError("invalid quota thresholds")

    def _path(self, lane: tuple[str, str]) -> Path:
        digest = hashlib.sha256(f"{lane[0]}|{lane[1]}".encode()).hexdigest()[:24]
        return self.root / f"lane-{digest}.json"

    @staticmethod
    def _read(fh) -> dict[str, Any]:
        fh.seek(0)
        raw = fh.read()
        if not raw.strip():
            return {"events": [], "reservations": {}}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {"events": [], "reservations": {}}
        return value if isinstance(value, dict) else {"events": [], "reservations": {}}

    @staticmethod
    def _write(fh, value: dict[str, Any]) -> None:
        fh.seek(0)
        fh.truncate()
        fh.write(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        fh.flush()
        os.fsync(fh.fileno())

    def reserve(self, lane: tuple[str, str], points: int, *, request_id: str, now: float | None = None) -> dict[str, Any]:
        at = time.time() if now is None else float(now)
        points = int(points)
        if points <= 0:
            raise ValueError("points must be positive")
        path = self._path(lane)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "r+") as fh:
            os.fchmod(fh.fileno(), 0o600)
            fcntl.flock(fh, fcntl.LOCK_EX)
            state = self._read(fh)
            events = [row for row in (state.get("events") or []) if float(row.get("at") or 0) > at - self.window_seconds]
            reservations = dict(state.get("reservations") or {})
            if request_id in reservations and any(row.get("request_id") == request_id for row in events):
                current = sum(int(row.get("points") or 0) for row in events)
                return {"points": current, "idempotent": True, "path": str(path)}
            current = sum(int(row.get("points") or 0) for row in events)
            projected = current + points
            if projected > self.hard_score or projected > self.soft_score:
                raise QuotaBlocked({
                    "lane": {"app_key": lane[0], "account_id": lane[1]},
                    "current": current,
                    "requested": points,
                    "projected": projected,
                    "soft_score": self.soft_score,
                    "hard_score": self.hard_score,
                    "retry_after_seconds": self.window_seconds,
                })
            events.append({"at": at, "points": points, "request_id": request_id})
            reservations[request_id] = {"at": at, "points": points}
            state.update({
                "lane": {"app_key": lane[0], "account_id": lane[1]},
                "events": events,
                "reservations": reservations,
                "points": projected,
                "window_seconds": self.window_seconds,
                "soft_score": self.soft_score,
                "hard_score": self.hard_score,
                "updated_at": at,
            })
            self._write(fh, state)
            fcntl.flock(fh, fcntl.LOCK_UN)
        return {"points": projected, "idempotent": False, "path": str(path)}

    def snapshot(self, lane: tuple[str, str], now: float | None = None) -> dict[str, Any]:
        at = time.time() if now is None else float(now)
        path = self._path(lane)
        if not path.exists():
            return {"points": 0, "events": [], "lane": {"app_key": lane[0], "account_id": lane[1]}}
        with path.open("r") as fh:
            fcntl.flock(fh, fcntl.LOCK_SH)
            state = self._read(fh)
            fcntl.flock(fh, fcntl.LOCK_UN)
        events = [row for row in (state.get("events") or []) if float(row.get("at") or 0) > at - self.window_seconds]
        state["events"] = events
        state["points"] = sum(int(row.get("points") or 0) for row in events)
        return state
