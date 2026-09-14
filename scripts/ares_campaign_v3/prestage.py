from __future__ import annotations

import hashlib
import concurrent.futures
import json
import time
from pathlib import Path
from typing import Any, Callable

import requests

from .media_registry import MediaNotReady, MediaRegistry


class MediaUploadError(RuntimeError):
    pass


def deterministic_media_title(variant: str, asset_id: str, checksum: str) -> str:
    normalized = str(variant or "").strip().lower()
    if normalized not in {"vertical", "square"}:
        raise ValueError("media title variant must be vertical or square")
    suffix = str(checksum or "")[:12]
    if not asset_id or len(suffix) < 8:
        raise ValueError("media title requires asset_id and checksum")
    return f"V3 {normalized.upper()} {asset_id} {suffix}"


class AdAccountVideoUploader:
    def __init__(self, *, common: Any, user_token: str, account_id: str, graph_version: str = "v26.0", attempts: int = 12, interval_seconds: int = 5, title_scan_pages: int = 20, title_scan_page_size: int = 500, association_scan_pages: int = 20, association_scan_page_size: int = 500):
        self.common = common
        self.user_token = user_token
        self.account_id = str(account_id).removeprefix("act_")
        self.graph_version = graph_version
        self.attempts = int(attempts)
        self.interval_seconds = int(interval_seconds)
        self.title_scan_pages = max(1, int(title_scan_pages))
        self.title_scan_page_size = max(1, min(500, int(title_scan_page_size)))
        self.association_scan_pages = max(1, int(association_scan_pages))
        self.association_scan_page_size = max(1, min(500, int(association_scan_page_size)))

    def upload(self, path: Path | str, title: str) -> str:
        source = Path(path)
        url = f"https://graph-video.facebook.com/{self.graph_version}/act_{self.account_id}/advideos"
        for attempt in range(2):
            self.common._throttle_before_request()
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
            if response.status_code in {200, 201} and isinstance(payload, dict) and not payload.get("error") and payload.get("id"):
                return str(payload["id"])
            matches = self.find_by_title(title)
            if len(matches) == 1:
                return str(matches[0]["id"])
            if len(matches) > 1:
                raise MediaUploadError("video upload became ambiguous because duplicate titles exist")
            if 500 <= int(response.status_code) < 600 and attempt == 0:
                time.sleep(10)
                continue
            error = payload.get("error") if isinstance(payload, dict) else None
            raise MediaUploadError(f"video upload rejected http={response.status_code} error_code={(error or {}).get('code')}")
        raise MediaUploadError("video upload failed after bounded retry")

    def find_by_title(self, title: str) -> list[dict[str, Any]]:
        return self.find_by_titles([title]).get(str(title), [])

    def find_by_titles(self, titles: list[str]) -> dict[str, list[dict[str, Any]]]:
        required = {str(title) for title in titles if str(title)}
        matches: dict[str, list[dict[str, Any]]] = {
            title: [] for title in required
        }
        if not required:
            return matches
        after: str | None = None
        for _ in range(self.title_scan_pages):
            params: dict[str, Any] = {"fields": "id,title,length,status", "limit": self.title_scan_page_size}
            if after:
                params["after"] = after
            status, payload, _ = self.common.graph_get(
                f"act_{self.account_id}/advideos", self.user_token, params
            )
            if status != 200 or not isinstance(payload, dict):
                raise MediaUploadError(f"ad-account video title readback failed http={status}")
            for row in payload.get("data") or []:
                title = str(row.get("title") or "")
                if title in required:
                    matches[title].append(row)
            after = str((((payload.get("paging") or {}).get("cursors") or {}).get("after")) or "")
            if not after:
                break
        return matches

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
            for _ in range(self.association_scan_pages):
                params: dict[str, Any] = {"fields": "id,title,length,status", "limit": self.association_scan_page_size}
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

    def prestage(
        self,
        *,
        account_id: str,
        asset_id: str,
        checksum: str,
        vertical_path: Path | str,
        square_path: Path | str | None = None,
        required_variants: tuple[str, ...] = ("vertical", "square"),
        existing_video_ids: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        vertical = Path(vertical_path)
        requested = set(required_variants)
        if not requested or not requested.issubset({"vertical", "square"}):
            raise ValueError("required_variants must contain vertical and/or square")
        if "vertical" not in requested:
            raise ValueError("vertical is required by the v3 media contract")
        square = Path(square_path) if square_path is not None else None
        paths = [vertical, *([square] if "square" in requested else [])]
        for path in paths:
            if path is None:
                raise MediaNotReady("square media file is required")
            if not path.is_file() or path.stat().st_size <= 0:
                raise MediaNotReady(f"media file missing or empty: {path}")
        actual_checksum = hashlib.sha256(vertical.read_bytes()).hexdigest()
        if actual_checksum != checksum:
            raise MediaNotReady("vertical media checksum mismatch")
        try:
            return self.registry.require_ready(
                account_id,
                asset_id,
                checksum,
                required_variants=required_variants,
            )
        except MediaNotReady:
            pass
        existing = existing_video_ids or {}
        vertical_id = str(existing.get("vertical") or "")
        if not vertical_id:
            vertical_id = str(
                self.uploader.upload(
                    vertical,
                    deterministic_media_title("vertical", asset_id, checksum),
                )
            )
        square_id = (
            str(existing.get("square") or "")
            if "square" in requested and square is not None
            else None
        )
        if "square" in requested and square is not None and not square_id:
            square_id = str(
                self.uploader.upload(
                    square,
                    deterministic_media_title("square", asset_id, checksum),
                )
            )
        video_ids = [vertical_id, *([square_id] if square_id else [])]
        processing = self.uploader.wait_ready(video_ids)
        if not processing or any(
            (processing.get(video_id) or {}).get("ready") is not True
            for video_id in video_ids
        ):
            raise MediaNotReady("required uploaded videos must be ready before registry commit")
        association = self.uploader.verify_association(video_ids)
        if any(
            (association.get(video_id) or {}).get("associated") is not True
            for video_id in video_ids
        ):
            raise MediaNotReady("required uploaded videos must be associated with the ad account")
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


class OnDemandMediaPipeline:
    """Prepare and upload media only after the exact ad account is known.

    The operation adapter owns Drive selection, variants and local preparation.
    This class only parallelizes independent asset pipelines and preserves input
    order. Registry writes remain account+asset+checksum scoped.
    """

    def __init__(self, service: PrestageService, *, max_workers: int = 5):
        workers = int(max_workers)
        if not 1 <= workers <= 8:
            raise ValueError("on-demand media max_workers must be 1..8")
        self.service = service
        self.max_workers = workers

    def run(
        self,
        *,
        account_id: str,
        assets: list[dict[str, Any]],
        prepare_asset: Callable[[dict[str, Any]], dict[str, Any]],
        required_variants: tuple[str, ...] = ("vertical", "square"),
    ) -> dict[str, Any]:
        account = str(account_id or "").removeprefix("act_").strip()
        if not account:
            raise ValueError("on-demand media requires an exact account_id")
        if not assets:
            return {
                "account_id": account,
                "assets": [],
                "required_variants": list(required_variants),
                "workers": 0,
                "duration_ms": 0.0,
            }
        identities = [str(row.get("asset_id") or "") for row in assets]
        if any(not value for value in identities) or len(identities) != len(set(identities)):
            raise ValueError("on-demand media requires unique nonempty asset_id values")
        started = time.perf_counter()

        def process(row: dict[str, Any]) -> dict[str, Any]:
            asset_id = str(row["asset_id"])
            checksum = str(row.get("clean_checksum") or row.get("checksum") or "")
            if not checksum:
                raise ValueError(f"on-demand media checksum missing for asset={asset_id}")
            prepared = prepare_asset(row)
            if not isinstance(prepared, dict) or not prepared.get("vertical_path"):
                raise ValueError(f"prepare_asset returned no vertical_path for asset={asset_id}")
            record = self.service.prestage(
                account_id=account,
                asset_id=asset_id,
                checksum=checksum,
                vertical_path=prepared["vertical_path"],
                square_path=prepared.get("square_path"),
                required_variants=required_variants,
            )
            return {
                "asset_id": asset_id,
                "checksum": checksum,
                "prepared": {
                    key: value
                    for key, value in prepared.items()
                    if key not in {"vertical_path", "square_path"}
                },
                "registry": record,
            }

        workers = min(self.max_workers, len(assets))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(process, assets))
        return {
            "account_id": account,
            "assets": results,
            "required_variants": list(required_variants),
            "workers": workers,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        }
