from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .media_registry import MediaRegistry
from .schema import Manifest, ManifestError


def content_digest(payload: dict[str, Any]) -> str:
    clean = copy.deepcopy(payload)
    clean.pop("prevalidated", None)
    clean.pop("prevalidation", None)
    encoded = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def verify_prevalidation(payload: dict[str, Any]) -> bool:
    prevalidation = payload.get("prevalidation") or {}
    expected = str(prevalidation.get("content_digest") or "")
    return payload.get("prevalidated") is True and bool(expected) and expected == content_digest(payload)


def prevalidate_payload(payload: dict[str, Any], registry: MediaRegistry) -> dict[str, Any]:
    manifest = Manifest.from_dict(payload)
    checks = ["schema_v3", "unique_idempotency", "timezone_start", "safe_creative_payload"]
    media_keys: list[str] = []
    source_ad_ids: list[str] = []
    for campaign in manifest.campaigns:
        if campaign.mode not in {"clone_prestaged", "from_zero_prestaged"}:
            continue
        for ad in campaign.ads:
            if ad.source_ad_id:
                source_ad_ids.append(ad.source_ad_id)
            record = registry.require_ready(campaign.account_id, ad.media.asset_id, ad.media.checksum)
            if str(record["vertical_video_id"]) != ad.media.vertical_video_id or str(record["square_video_id"]) != ad.media.square_video_id:
                raise ManifestError(f"manifest media IDs drifted for asset={ad.media.asset_id}")
            if record.get("upload_edge") != "ad_account_advideos" or record.get("association_verified") is not True:
                raise ManifestError(f"manifest media is not associated with the ad account for asset={ad.media.asset_id}")
            media_keys.append(f"{campaign.account_id}|{ad.media.asset_id}|{ad.media.checksum}")
    if len(media_keys) != len(set(media_keys)):
        raise ManifestError("duplicate media lineage in manifest")
    if media_keys:
        checks.extend(["media_registry_exact", "media_lineage_unique", "ad_account_video_association"])
    if source_ad_ids:
        checks.append("source_ad_lineage")
    result = copy.deepcopy(payload)
    result.pop("prevalidation", None)
    result["prevalidated"] = True
    result["prevalidation"] = {
        "engine_version": 3,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "content_digest": content_digest(result),
    }
    if not verify_prevalidation(result):
        raise RuntimeError("prevalidation digest self-check failed")
    return result
