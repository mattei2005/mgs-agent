from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class ManifestError(ValueError):
    pass


def _iso(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ManifestError(f"invalid {field_name}") from exc
    if parsed.tzinfo is None:
        raise ManifestError(f"{field_name} must include timezone")
    return parsed


def _has_key(value: Any, target: str) -> bool:
    if isinstance(value, dict):
        return target in value or any(_has_key(item, target) for item in value.values())
    if isinstance(value, list):
        return any(_has_key(item, target) for item in value)
    return False


def _has_text(value: Any, target: str) -> bool:
    if isinstance(value, str):
        return target.lower() in value.lower()
    if isinstance(value, dict):
        return any(_has_text(item, target) for item in value.values())
    if isinstance(value, list):
        return any(_has_text(item, target) for item in value)
    return False


@dataclass(frozen=True)
class MediaSpec:
    asset_id: str
    checksum: str
    vertical_video_id: str
    square_video_id: str
    ready: bool

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MediaSpec":
        required = ("asset_id", "checksum", "vertical_video_id", "square_video_id")
        missing = [name for name in required if not str(value.get(name) or "").strip()]
        if missing:
            raise ManifestError(f"media missing fields: {','.join(missing)}")
        if value.get("ready") is not True:
            raise ManifestError("media is not ready")
        return cls(
            asset_id=str(value["asset_id"]),
            checksum=str(value["checksum"]),
            vertical_video_id=str(value["vertical_video_id"]),
            square_video_id=str(value["square_video_id"]),
            ready=True,
        )


@dataclass(frozen=True)
class AdSpec:
    name: str
    media: MediaSpec
    creative_payload: dict[str, Any]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AdSpec":
        name = str(value.get("name") or "").strip()
        if not name:
            raise ManifestError("ad name is required")
        payload = value.get("creative_payload")
        if not isinstance(payload, dict) or not payload:
            raise ManifestError("creative_payload is required")
        if _has_key(payload, "standard_enhancements"):
            raise ManifestError("standard_enhancements is prohibited")
        if _has_text(payload, "https://fb.com/messenger_doc/"):
            raise ManifestError("messenger_doc external URL is prohibited")
        return cls(name=name, media=MediaSpec.from_dict(value.get("media") or {}), creative_payload=payload)


@dataclass(frozen=True)
class CampaignSpec:
    idempotency_key: str
    app_key: str
    account_id: str
    mode: str
    source_campaign_id: str
    name: str
    start_time: str
    status: str
    source_adset_id: str | None = None
    adset_name: str | None = None
    campaign_updates: dict[str, Any] = field(default_factory=dict)
    ads: tuple[AdSpec, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CampaignSpec":
        required = ("idempotency_key", "app_key", "account_id", "mode", "source_campaign_id", "name", "start_time", "status")
        missing = [name for name in required if not str(value.get(name) or "").strip()]
        if missing:
            raise ManifestError(f"campaign missing fields: {','.join(missing)}")
        mode = str(value["mode"])
        if mode not in {"pure_clone", "clone_prestaged"}:
            raise ManifestError(f"unsupported mode: {mode}")
        status = str(value["status"]).upper()
        if status not in {"PAUSED", "ACTIVE"}:
            raise ManifestError("status must be PAUSED or ACTIVE")
        start = _iso(str(value["start_time"]), "start_time")
        if status == "ACTIVE" and start <= datetime.now(timezone.utc):
            raise ManifestError("ACTIVE requires future start_time")
        ads = tuple(AdSpec.from_dict(item) for item in (value.get("ads") or []))
        source_adset_id = str(value.get("source_adset_id") or "") or None
        adset_name = str(value.get("adset_name") or "") or None
        if mode == "clone_prestaged":
            if not source_adset_id:
                raise ManifestError("clone_prestaged requires source_adset_id")
            if len(ads) != 3:
                raise ManifestError("clone_prestaged requires exactly three ads")
        elif ads:
            raise ManifestError("pure_clone must not provide replacement ads")
        updates = value.get("campaign_updates") or {}
        if not isinstance(updates, dict):
            raise ManifestError("campaign_updates must be an object")
        return cls(
            idempotency_key=str(value["idempotency_key"]),
            app_key=str(value["app_key"]),
            account_id=str(value["account_id"]).removeprefix("act_"),
            mode=mode,
            source_campaign_id=str(value["source_campaign_id"]),
            name=str(value["name"]),
            start_time=str(value["start_time"]),
            status=status,
            source_adset_id=source_adset_id,
            adset_name=adset_name,
            campaign_updates=updates,
            ads=ads,
        )


@dataclass(frozen=True)
class Manifest:
    schema_version: int
    request_id: str
    operation: str
    graph_version: str
    created_at: str
    campaigns: tuple[CampaignSpec, ...]
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Manifest":
        if int(value.get("schema_version") or 0) != 3:
            raise ManifestError("schema_version must be 3")
        request_id = str(value.get("request_id") or "").strip()
        operation = str(value.get("operation") or "").strip()
        graph_version = str(value.get("graph_version") or "").strip()
        if not request_id or not operation or not graph_version:
            raise ManifestError("request_id, operation and graph_version are required")
        _iso(str(value.get("created_at") or ""), "created_at")
        campaigns = tuple(CampaignSpec.from_dict(item) for item in (value.get("campaigns") or []))
        if not campaigns:
            raise ManifestError("at least one campaign is required")
        if len(campaigns) > 100:
            raise ManifestError("a manifest supports at most 100 campaigns")
        keys = [item.idempotency_key for item in campaigns]
        if len(keys) != len(set(keys)):
            raise ManifestError("duplicate idempotency_key")
        return cls(
            schema_version=3,
            request_id=request_id,
            operation=operation,
            graph_version=graph_version,
            created_at=str(value["created_at"]),
            campaigns=campaigns,
            raw=value,
        )

    @property
    def digest(self) -> str:
        encoded = json.dumps(self.raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()
