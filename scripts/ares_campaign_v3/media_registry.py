from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MediaNotReady(RuntimeError):
    pass


class MediaRegistry:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    @staticmethod
    def _key(account_id: str, asset_id: str, checksum: str) -> str:
        return f"{str(account_id).removeprefix('act_')}|{asset_id}|{checksum}"

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 3, "records": {}}
        try:
            value = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return {"schema_version": 3, "records": {}}
        return value if isinstance(value, dict) else {"schema_version": 3, "records": {}}

    def _atomic(self, value: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)
        os.chmod(self.path, 0o600)

    def register(self, *, account_id: str, asset_id: str, checksum: str, vertical_video_id: str, square_video_id: str, ready: bool, source: str = "manual-readback") -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "r+") as lock:
            os.fchmod(lock.fileno(), 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = self._load()
            records = data.setdefault("records", {})
            key = self._key(account_id, asset_id, checksum)
            record = {
                "account_id": str(account_id).removeprefix("act_"),
                "asset_id": asset_id,
                "checksum": checksum,
                "vertical_video_id": str(vertical_video_id),
                "square_video_id": str(square_video_id),
                "ready": bool(ready),
                "source": source,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            records[key] = record
            data["schema_version"] = 3
            self._atomic(data)
            fcntl.flock(lock, fcntl.LOCK_UN)
        return record

    def require_ready(self, account_id: str, asset_id: str, checksum: str) -> dict[str, Any]:
        data = self._load()
        record = (data.get("records") or {}).get(self._key(account_id, asset_id, checksum))
        if not isinstance(record, dict) or record.get("ready") is not True:
            raise MediaNotReady(f"media not ready for account={str(account_id).removeprefix('act_')} asset={asset_id}")
        if not record.get("vertical_video_id") or not record.get("square_video_id"):
            raise MediaNotReady(f"media IDs incomplete for asset={asset_id}")
        return record

    def summary(self) -> dict[str, Any]:
        records = list((self._load().get("records") or {}).values())
        return {"total": len(records), "ready": sum(row.get("ready") is True for row in records), "accounts": sorted({str(row.get("account_id")) for row in records})}
