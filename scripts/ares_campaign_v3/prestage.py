from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests

from .media_registry import MediaNotReady, MediaRegistry


class MediaUploadError(RuntimeError):
    pass


class AdAccountVideoUploader:
    def __init__(self, *, common: Any, user_token: str, account_id: str, graph_version: str = "v26.0", attempts: int = 12, interval_seconds: int = 5):
        self.common = common
        self.user_token = user_token
        self.account_id = str(account_id).removeprefix("act_")
        self.graph_version = graph_version
        self.attempts = int(attempts)
        self.interval_seconds = int(interval_seconds)

    def upload(self, path: Path | str, title: str) -> str:
        source = Path(path)
        self.common._throttle_before_request()
        url = f"https://graph-video.facebook.com/{self.graph_version}/act_{self.account_id}/advideos"
        try:
            with source.open("rb") as fh:
                response = requests.post(
                    url,
                    data={
                        "access_token": self.user_token,
                        "title": title,
                        "unpublished_content_type": "ADS_POST",
                    },
                    files={"source": (source.name, fh, "video/mp4")},
                    timeout=300,
                )
        except (OSError, requests.RequestException) as exc:
            raise MediaUploadError(f"video upload transport failed: {type(exc).__name__}") from exc
        try:
            payload = response.json()
        except ValueError:
            payload = {"error": {"message": "non-json video upload response"}}
        self.common.record_response_usage(dict(response.headers), response.status_code, payload, logical_points=3)
        if response.status_code not in {200, 201} or not isinstance(payload, dict) or payload.get("error") or not payload.get("id"):
            error = payload.get("error") if isinstance(payload, dict) else None
            raise MediaUploadError(f"video upload rejected http={response.status_code} error_code={(error or {}).get('code')}")
        return str(payload["id"])

    def wait_ready(self, video_ids: list[str]) -> dict[str, dict[str, Any]]:
        unique_ids = list(dict.fromkeys(str(item) for item in video_ids))
        latest: dict[str, dict[str, Any]] = {}
        for _ in range(self.attempts):
            requests_ = [{"name": video_id, "path": video_id, "params": {"fields": "id,title,length,status"}} for video_id in unique_ids]
            status, rows, _ = self.common.graph_batch_get(self.user_token, requests_)
            if status != 200 or not isinstance(rows, list):
                raise MediaUploadError(f"video processing readback failed http={status}")
            latest = {}
            terminal_failure = False
            for row in rows:
                body = row.get("body") or {}
                status_payload = body.get("status") or {}
                text = json.dumps(status_payload, ensure_ascii=False).upper()
                failed = any(value in text for value in ("ERROR", "FAILED"))
                ready = any(value in text for value in ("READY", "COMPLETE", "PUBLISHED")) and not failed
                latest[str(row.get("name"))] = {"ready": ready, "status": status_payload}
                terminal_failure = terminal_failure or failed
            if terminal_failure:
                raise MediaUploadError("video processing reached terminal failure")
            if len(latest) == len(unique_ids) and all(item.get("ready") is True for item in latest.values()):
                return latest
            time.sleep(max(1, self.interval_seconds))
        return latest

    def verify_association(self, video_ids: list[str]) -> dict[str, dict[str, Any]]:
        required = set(dict.fromkeys(str(item) for item in video_ids))
        found: dict[str, dict[str, Any]] = {}
        for attempt in range(self.attempts):
            after: str | None = None
            for _ in range(20):
                params: dict[str, Any] = {"fields": "id,title,length,status", "limit": 500}
                if after:
                    params["after"] = after
                status, payload, _ = self.common.graph_get(
                    f"act_{self.account_id}/advideos", self.user_token, params
                )
                if status != 200 or not isinstance(payload, dict):
                    raise MediaUploadError(f"ad-account video association readback failed http={status}")
                for row in payload.get("data") or []:
                    video_id = str(row.get("id") or "")
                    if video_id in required:
                        found[video_id] = row
                if required.issubset(found):
                    break
                after = str((((payload.get("paging") or {}).get("cursors") or {}).get("after")) or "")
                if not after:
                    break
            if required.issubset(found) or attempt == self.attempts - 1:
                break
            time.sleep(max(1, self.interval_seconds))
        return {
            video_id: {"associated": video_id in found, "readback": found.get(video_id)}
            for video_id in required
        }


class PrestageService:
    def __init__(self, registry: MediaRegistry, uploader: Any):
        self.registry = registry
        self.uploader = uploader

    def prestage(self, *, account_id: str, asset_id: str, checksum: str, vertical_path: Path | str, square_path: Path | str) -> dict[str, Any]:
        vertical = Path(vertical_path)
        square = Path(square_path)
        for path in (vertical, square):
            if not path.is_file() or path.stat().st_size <= 0:
                raise MediaNotReady(f"media file missing or empty: {path}")
        actual_checksum = hashlib.sha256(vertical.read_bytes()).hexdigest()
        if actual_checksum != checksum:
            raise MediaNotReady("vertical media checksum mismatch")
        vertical_id = str(self.uploader.upload(vertical, f"V3 VERTICAL {asset_id}"))
        square_id = str(self.uploader.upload(square, f"V3 SQUARE {asset_id}"))
        processing = self.uploader.wait_ready([vertical_id, square_id])
        if not processing or any((processing.get(video_id) or {}).get("ready") is not True for video_id in (vertical_id, square_id)):
            raise MediaNotReady("both uploaded videos must be ready before registry commit")
        association = self.uploader.verify_association([vertical_id, square_id])
        if any((association.get(video_id) or {}).get("associated") is not True for video_id in (vertical_id, square_id)):
            raise MediaNotReady("both uploaded videos must be associated with the ad account")
        return self.registry.register(
            account_id=account_id,
            asset_id=asset_id,
            checksum=checksum,
            vertical_video_id=vertical_id,
            square_video_id=square_id,
            ready=True,
            source="v3-ad-account-prestage-meta-readback",
            upload_edge="ad_account_advideos",
            association_verified=True,
        )
