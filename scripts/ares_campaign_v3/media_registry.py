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

    def register(
        self,
        *,
        account_id: str,
        asset_id: str,
        checksum: str,
        vertical_video_id: str,
        square_video_id: str | None,
        ready: bool,
        source: str = "manual-readback",
        upload_edge: str | None = None,
        association_verified: bool = False,
        media_type: str = "video",
        image_hash: str | None = None,
    ) -> dict[str, Any]:
        if media_type not in {"video", "image"}:
            raise ValueError("unsupported media type")
        if media_type == "image" and (not image_hash or vertical_video_id or square_video_id or upload_edge != "ad_account_adimages"):
            raise ValueError("image registry requires image hash and exact ad-account image edge only")
        if media_type == "video" and image_hash:
            raise ValueError("video registry cannot contain image hash")
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
                "square_video_id": (str(square_video_id) if square_video_id else None),
                "ready": bool(ready),
                "source": source,
                "upload_edge": upload_edge,
                "association_verified": bool(association_verified),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            records[key] = record
            if media_type == "image":
                record.pop("vertical_video_id")
                record.pop("square_video_id")
                record.update(media_type="image", image_hash=str(image_hash))
            data["schema_version"] = 3
            self._atomic(data)
            fcntl.flock(lock, fcntl.LOCK_UN)
        return record

    def register_image(self, *, account_id, asset_id, checksum, image_hash, ready, association_verified, source="v3-ad-account-image-prestage"):
        return self.register(account_id=account_id, asset_id=asset_id, checksum=checksum,
                             vertical_video_id="", square_video_id=None, ready=ready, source=source,
                             upload_edge="ad_account_adimages", association_verified=association_verified,
                             media_type="image", image_hash=image_hash)

    def require_ready(
        self,
        account_id: str,
        asset_id: str,
        checksum: str,
        *,
        required_variants: tuple[str, ...] = ("vertical", "square"),
        media_type: str = "video",
    ) -> dict[str, Any]:
        data = self._load()
        record = (data.get("records") or {}).get(self._key(account_id, asset_id, checksum))
        if not isinstance(record, dict) or record.get("ready") is not True:
            raise MediaNotReady(f"media not ready for account={str(account_id).removeprefix('act_')} asset={asset_id}")
        if media_type not in {"image", "video"} or record.get("media_type", "video") != media_type:
            raise MediaNotReady("registry media type mismatch")
        if media_type == "image":
            if (not record.get("image_hash") or record.get("vertical_video_id") or record.get("square_video_id")
                    or record.get("upload_edge") != "ad_account_adimages" or record.get("association_verified") is not True):
                raise MediaNotReady("image not associated with exact ad account")
            return record
        allowed = {"vertical", "square"}
        requested = set(required_variants)
        if not requested or not requested.issubset(allowed):
            raise ValueError("required_variants must contain vertical and/or square")
        missing = [
            variant
            for variant in required_variants
            if not record.get(f"{variant}_video_id")
        ]
        if missing:
            raise MediaNotReady(
                f"media IDs incomplete for asset={asset_id} variants={','.join(missing)}"
            )
        if record.get("upload_edge") != "ad_account_advideos" or record.get("association_verified") is not True:
            raise MediaNotReady(f"media is not associated with the ad account for asset={asset_id}")
        return record

    def summary(self) -> dict[str, Any]:
        records = list((self._load().get("records") or {}).values())
        return {
            "total": len(records),
            "ready": sum(row.get("ready") is True for row in records),
            "associated": sum(
                row.get("ready") is True
                and row.get("upload_edge") in {"ad_account_advideos", "ad_account_adimages"}
                and row.get("association_verified") is True
                for row in records
            ),
            "accounts": sorted({str(row.get("account_id")) for row in records}),
        }
