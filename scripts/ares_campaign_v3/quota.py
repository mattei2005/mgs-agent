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
    def __init__(
        self,
        root: Path | str,
        *,
        soft_score: int = 100,
        hard_score: int = 120,
        window_seconds: int = 300,
        development_score_max: int = 60,
        standard_score_max: int = 9000,
    ):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.soft_score = int(soft_score)
        self.hard_score = int(hard_score)
        self.window_seconds = int(window_seconds)
        self.development_score_max = int(development_score_max)
        self.standard_score_max = int(standard_score_max)
        if not (0 < self.soft_score <= self.hard_score):
            raise ValueError("invalid quota thresholds")
        if self.development_score_max <= 0 or self.standard_score_max <= 0:
            raise ValueError("invalid tier score maximum")

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

    @staticmethod
    def _business_access_tier(value: Any) -> str | None:
        if isinstance(value, dict):
            tier = str(value.get("ads_api_access_tier") or "").strip().lower()
            if tier in {"development_access", "standard_access"}:
                return tier
            for child in value.values():
                found = LaneQuotaStore._business_access_tier(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = LaneQuotaStore._business_access_tier(child)
                if found:
                    return found
        return None

    def _effective_limits(self, state: dict[str, Any]) -> tuple[int, int, str | None]:
        tier = str(((state.get("live_usage") or {}).get("ads_api_access_tier") or "")).strip().lower() or None
        if tier == "development_access":
            hard = min(self.hard_score, self.development_score_max)
            return min(self.soft_score, hard), hard, tier
        if tier == "standard_access":
            return self.standard_score_max, self.standard_score_max, tier
        return self.soft_score, self.hard_score, tier

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
            effective_soft, effective_hard, tier = self._effective_limits(state)
            events = [row for row in (state.get("events") or []) if float(row.get("at") or 0) > at - self.window_seconds]
            reservations = dict(state.get("reservations") or {})
            if request_id in reservations and any(row.get("request_id") == request_id for row in events):
                current = sum(int(row.get("points") or 0) for row in events)
                return {
                    "points": current,
                    "idempotent": True,
                    "path": str(path),
                    "soft_score": effective_soft,
                    "hard_score": effective_hard,
                    "ads_api_access_tier": tier,
                }
            current = sum(int(row.get("points") or 0) for row in events)
            projected = current + points
            if projected > effective_hard or projected > effective_soft:
                raise QuotaBlocked({
                    "lane": {"app_key": lane[0], "account_id": lane[1]},
                    "current": current,
                    "requested": points,
                    "projected": projected,
                    "soft_score": effective_soft,
                    "hard_score": effective_hard,
                    "configured_soft_score": self.soft_score,
                    "configured_hard_score": self.hard_score,
                    "ads_api_access_tier": tier,
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
                "soft_score": effective_soft,
                "hard_score": effective_hard,
                "configured_soft_score": self.soft_score,
                "configured_hard_score": self.hard_score,
                "ads_api_access_tier": tier,
                "updated_at": at,
            })
            self._write(fh, state)
            fcntl.flock(fh, fcntl.LOCK_UN)
        return {
            "points": projected,
            "idempotent": False,
            "path": str(path),
            "soft_score": effective_soft,
            "hard_score": effective_hard,
            "ads_api_access_tier": tier,
        }

    def complete(self, lane: tuple[str, str], request_id: str, *, now: float | None = None) -> dict[str, Any]:
        at = time.time() if now is None else float(now)
        path = self._path(lane)
        if not path.exists():
            return {"released": False, "reason": "missing_state"}
        with path.open("r+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            state = self._read(fh)
            live = state.get("live_usage") or {}
            tier = str(live.get("ads_api_access_tier") or "")
            util = live.get("acc_id_util_pct")
            healthy_full_access = tier == "standard_access" and (util is None or float(util) < 80.0)
            if healthy_full_access:
                state["events"] = [row for row in (state.get("events") or []) if row.get("request_id") != request_id]
                reservations = dict(state.get("reservations") or {})
                reservations.pop(request_id, None)
                state["reservations"] = reservations
                state["points"] = sum(int(row.get("points") or 0) for row in state["events"])
                state["updated_at"] = at
                state["last_completed_request_id"] = request_id
                self._write(fh, state)
            fcntl.flock(fh, fcntl.LOCK_UN)
        return {"released": healthy_full_access, "tier": tier or None, "acc_id_util_pct": util}

    def observe_headers(self, lane: tuple[str, str], headers: dict[str, Any], *, now: float | None = None) -> dict[str, Any]:
        at = time.time() if now is None else float(now)
        normalized = {str(key).lower(): value for key, value in (headers or {}).items()}
        def parse(name: str) -> Any:
            raw = normalized.get(name)
            if isinstance(raw, (dict, list)):
                return raw
            if not raw:
                return None
            try:
                return json.loads(str(raw))
            except json.JSONDecodeError:
                return None
        ad_usage = parse('x-ad-account-usage')
        business_usage = parse('x-business-use-case-usage')
        tier = ad_usage.get('ads_api_access_tier') if isinstance(ad_usage, dict) else None
        if not tier:
            tier = self._business_access_tier(business_usage)
        live = {
            'observed_at': at,
            'ad_account_usage_present': isinstance(ad_usage, dict),
            'business_usage_present': isinstance(business_usage, (dict, list)),
            'acc_id_util_pct': ad_usage.get('acc_id_util_pct') if isinstance(ad_usage, dict) else None,
            'reset_time_duration': ad_usage.get('reset_time_duration') if isinstance(ad_usage, dict) else None,
            'ads_api_access_tier': tier,
            'business_usage': business_usage,
        }
        path = self._path(lane)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, 'r+') as fh:
            os.fchmod(fh.fileno(), 0o600)
            fcntl.flock(fh, fcntl.LOCK_EX)
            state = self._read(fh)
            state['lane'] = {'app_key': lane[0], 'account_id': lane[1]}
            state['live_usage'] = live
            state['updated_at'] = at
            self._write(fh, state)
            fcntl.flock(fh, fcntl.LOCK_UN)
        return live

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
