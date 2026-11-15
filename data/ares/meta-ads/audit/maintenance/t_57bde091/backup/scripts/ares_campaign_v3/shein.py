from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any

SHEIN_ACCOUNT_ID = "2429758060563333"
SHEIN_APP_KEY = "mgs-meta-app-1299247318762949"
SHEIN_OPERATION = "SHEIN-US-DIRECT"
SHEIN_PAGE_ID = "410983488769165"
SHEIN_INSTAGRAM_USER_ID = "17841469509077092"
SHEIN_PIXEL_ID = "1049581090103163"
SHEIN_REGULATED_IDENTITY = "1773412024030451"
SHEIN_DESTINATION = "https://yolokfx.com/quiz/us/sh2-g005/"
SHEIN_CUSTOM_EVENT_TYPE = "ADD_TO_WISHLIST"
_CAMPAIGN_RE = re.compile(
    r"^\s*(?P<number>\d+)\s*-\s*(?P<label>.+?)\s*-\s*US-EN\s*"
    r"\(b01fb03c\d+\)\s*event_add_to_wishlist(?:\s+COPY\s+C\d+)?\s*$",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"^\s*(\d+)\s*-")


class SheinManifestError(ValueError):
    pass


def _positive_int(value: Any, field: str) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as exc:
        raise SheinManifestError(f"{field} must be an integer") from exc
    if parsed <= 0:
        raise SheinManifestError(f"{field} must be positive")
    return parsed


def _source_identity(source_campaign: dict[str, Any]) -> tuple[int, str]:
    match = _CAMPAIGN_RE.fullmatch(str(source_campaign.get("name") or ""))
    if not match:
        raise SheinManifestError("source campaign name is not canonical SHEIN US-EN")
    return int(match.group("number")), match.group("label").strip()


def _require_shein_source_event(source_adset: dict[str, Any]) -> None:
    promoted = source_adset.get("promoted_object") or {}
    actual = str(promoted.get("custom_event_type") or "").upper()
    if actual != SHEIN_CUSTOM_EVENT_TYPE:
        raise SheinManifestError(
            "SHEIN source ad set must use ADD_TO_WISHLIST"
        )


def next_campaign_numbers(live_campaigns: list[dict[str, Any]], count: int) -> list[int]:
    count = _positive_int(count, "count")
    numbers = []
    for row in live_campaigns:
        match = _NUMBER_RE.match(str(row.get("name") or ""))
        if match:
            numbers.append(int(match.group(1)))
    if not numbers:
        raise SheinManifestError("no numbered live campaign found")
    start = max(numbers) + 1
    return list(range(start, start + count))


def campaign_token(number: int) -> str:
    return f"b01fb03c{_positive_int(number, 'number'):03d}"


def adgroup_token(number: int) -> str:
    return f"{campaign_token(number)}g01"


def tracking_tags(number: int) -> str:
    return (
        "utm_source=facebook&utm_medium=g005-s"
        f"&utm_campaign={campaign_token(number)}"
        f"&utm_adgroup={adgroup_token(number)}"
    )


def destination_url(number: int) -> str:
    return f"{SHEIN_DESTINATION}?{tracking_tags(number)}"


def campaign_name(number: int, product_label: str, *, copy_source_number: int | None = None) -> str:
    label = str(product_label or "").strip()
    if not label:
        raise SheinManifestError("product_label is required")
    value = (
        f"{_positive_int(number, 'number')} - {label} - US-EN "
        f"({campaign_token(number)}) event_add_to_wishlist"
    )
    if copy_source_number is not None:
        value += f" COPY C{_positive_int(copy_source_number, 'copy_source_number')}"
    return value


def adset_name(number: int) -> str:
    return f"01 - ADGROUP - VIDEOS ({adgroup_token(number)})"


def _individual_dof(source_creative: dict[str, Any] | None = None) -> dict[str, Any]:
    source = source_creative or {}
    features = ((source.get("degrees_of_freedom_spec") or {}).get("creative_features_spec") or {})
    source_advantage = features.get("advantage_plus_creative") or {}
    status = str(source_advantage.get("enroll_status") or "OPT_OUT").upper()
    if status not in {"OPT_IN", "OPT_OUT"}:
        status = "OPT_OUT"
    return {
        "creative_features_spec": {
            "advantage_plus_creative": {"enroll_status": status}
        }
    }


def _source_video_data(source_ad: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    creative = source_ad.get("creative") or {}
    story = creative.get("object_story_spec") or {}
    video = story.get("video_data") or {}
    if not str(story.get("page_id") or "").strip():
        raise SheinManifestError("source creative is missing page_id")
    for field in ("title", "message", "call_to_action"):
        if not video.get(field):
            raise SheinManifestError(f"source creative is missing video_data.{field}")
    return creative, video


def _media_for_manifest(asset: dict[str, Any]) -> dict[str, Any]:
    required = (
        "asset_id",
        "checksum",
        "vertical_video_id",
        "upload_edge",
    )
    missing = [field for field in required if not str(asset.get(field) or "").strip()]
    if missing:
        raise SheinManifestError(f"asset media missing fields: {','.join(missing)}")
    if asset.get("ready") is not True or asset.get("association_verified") is not True:
        raise SheinManifestError("asset media is not ready and associated")
    return {
        field: copy.deepcopy(asset[field])
        for field in (
            "asset_id",
            "checksum",
            "vertical_video_id",
            "ready",
            "upload_edge",
            "association_verified",
        )
    }


def _new_video_payload(
    *,
    source_ad: dict[str, Any],
    asset: dict[str, Any],
    number: int,
    creative_name: str,
    include_media_sourcing: bool,
) -> dict[str, Any]:
    source_creative, source_video = _source_video_data(source_ad)
    thumbnail = str(asset.get("thumbnail_url") or "").strip()
    if not thumbnail:
        raise SheinManifestError("asset thumbnail_url is required")
    video_id = str(asset.get("vertical_video_id") or "").strip()
    if not video_id:
        raise SheinManifestError("asset vertical_video_id is required")
    call_to_action = copy.deepcopy(source_video["call_to_action"])
    call_to_action.setdefault("value", {})["link"] = destination_url(number)
    video_data: dict[str, Any] = {
        "video_id": video_id,
        "title": str(source_video["title"]),
        "message": str(source_video["message"]),
        "call_to_action": call_to_action,
        # Graph v26 rejects image_url + image_hash together. New media uses its
        # own preferred thumbnail URL and never inherits the source image hash.
        "image_url": thumbnail,
    }
    if source_video.get("link_description"):
        video_data["link_description"] = source_video["link_description"]
    payload: dict[str, Any] = {
        "name": creative_name,
        "object_story_spec": {
            "page_id": str((source_creative.get("object_story_spec") or {}).get("page_id") or SHEIN_PAGE_ID),
            "instagram_user_id": str(
                (source_creative.get("object_story_spec") or {}).get("instagram_user_id")
                or SHEIN_INSTAGRAM_USER_ID
            ),
            "video_data": video_data,
        },
        "degrees_of_freedom_spec": _individual_dof(source_creative),
    }
    if include_media_sourcing:
        payload["media_sourcing_spec"] = {
            "titles": [{"text": str(source_video["title"])}],
            "bodies": [{"text": str(source_video["message"])}],
            "videos": [
                {
                    "video_id": video_id,
                    "original_video_id": video_id,
                    "source": "multi_media",
                    "opt_in_status": "opt_in",
                    "thumbnail_source": "generated_default",
                    "thumbnail_url": thumbnail,
                }
            ],
        }
    return payload


def _campaign_create(reference_campaign: dict[str, Any], budget_minor: int) -> dict[str, Any]:
    return {
        "objective": str(reference_campaign.get("objective") or "OUTCOME_SALES"),
        "buying_type": str(reference_campaign.get("buying_type") or "AUCTION"),
        "daily_budget": str(_positive_int(budget_minor, "budget_minor")),
        "bid_strategy": str(
            reference_campaign.get("bid_strategy") or "LOWEST_COST_WITHOUT_CAP"
        ),
        "special_ad_categories": copy.deepcopy(
            reference_campaign.get("special_ad_categories") or []
        ),
        "special_ad_category_country": copy.deepcopy(
            reference_campaign.get("special_ad_category_country") or []
        ),
    }


def _targeting(value: dict[str, Any]) -> dict[str, Any]:
    geo = copy.deepcopy(value.get("geo_locations") or {})
    result: dict[str, Any] = {
        "age_min": int(value.get("age_min") or 18),
        "age_max": int(value.get("age_max") or 65),
        "geo_locations": geo or {
            "countries": ["US"],
            "location_types": ["frequently_in", "home", "recent"],
        },
        "targeting_automation": copy.deepcopy(
            value.get("targeting_automation") or {"advantage_audience": 1}
        ),
    }
    if value.get("genders"):
        result["genders"] = copy.deepcopy(value["genders"])
    return result


def _adset_create(reference_adset: dict[str, Any]) -> dict[str, Any]:
    promoted = copy.deepcopy(reference_adset.get("promoted_object") or {})
    promoted.setdefault("pixel_id", SHEIN_PIXEL_ID)
    promoted["custom_event_type"] = SHEIN_CUSTOM_EVENT_TYPE
    promoted.setdefault("smart_pse_enabled", False)
    return {
        "billing_event": str(reference_adset.get("billing_event") or "IMPRESSIONS"),
        "optimization_goal": str(
            reference_adset.get("optimization_goal") or "OFFSITE_CONVERSIONS"
        ),
        "targeting": _targeting(reference_adset.get("targeting") or {}),
        "promoted_object": promoted,
        "attribution_spec": copy.deepcopy(
            reference_adset.get("attribution_spec")
            or [
                {"event_type": "CLICK_THROUGH", "window_days": 7},
                {"event_type": "VIEW_THROUGH", "window_days": 1},
                {"event_type": "ENGAGED_VIDEO_VIEW", "window_days": 1},
            ]
        ),
        "regional_regulated_categories": copy.deepcopy(
            reference_adset.get("regional_regulated_categories")
            or ["VOLUNTARY_VERIFICATION"]
        ),
        "regional_regulation_identities": copy.deepcopy(
            reference_adset.get("regional_regulation_identities")
            or {
                "universal_beneficiary": SHEIN_REGULATED_IDENTITY,
                "universal_payer": SHEIN_REGULATED_IDENTITY,
            }
        ),
        "is_dynamic_creative": bool(reference_adset.get("is_dynamic_creative", False)),
    }


def _manifest(request_id: str, mode: str, campaign: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 3,
        "request_id": request_id,
        "operation": SHEIN_OPERATION,
        "graph_version": "v26.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prevalidated": False,
        "execution_mode": mode,
        "campaigns": [campaign],
    }


def build_from_zero_manifest(
    *,
    request_id: str,
    number: int,
    start_time: str,
    reference_campaign: dict[str, Any],
    reference_adset: dict[str, Any],
    copy_source_ad: dict[str, Any],
    assets: list[dict[str, Any]],
    budget_minor: int,
    product_label: str,
    status: str = "ACTIVE",
) -> dict[str, Any]:
    if len(assets) != 3:
        raise SheinManifestError("SHEIN from-zero requires exactly three assets")
    ads = []
    for index, asset in enumerate(assets, 1):
        payload = _new_video_payload(
            source_ad=copy_source_ad,
            asset=asset,
            number=number,
            creative_name=f"SHEIN C{number:03d} VIDEO {index:02d} {asset['asset_id']}",
            include_media_sourcing=False,
        )
        ads.append(
            {
                "name": f"VIDEO - {index:02d}",
                "media": _media_for_manifest(asset),
                "creative_payload": payload,
            }
        )
    campaign = {
        "idempotency_key": request_id,
        "app_key": SHEIN_APP_KEY,
        "account_id": SHEIN_ACCOUNT_ID,
        "mode": "from_zero_prestaged",
        "name": campaign_name(number, product_label),
        "adset_name": adset_name(number),
        "start_time": start_time,
        "status": str(status).upper(),
        "campaign_create": _campaign_create(reference_campaign, budget_minor),
        "adset_create": _adset_create(reference_adset),
        "ads": ads,
    }
    return _manifest(request_id, "from_zero_prestaged", campaign)


def build_pure_clone_manifest(
    *,
    request_id: str,
    number: int,
    start_time: str,
    source_campaign: dict[str, Any],
    source_adset: dict[str, Any],
    source_ads: list[dict[str, Any]],
    budget_minor: int | None = None,
    status: str = "ACTIVE",
) -> dict[str, Any]:
    _require_shein_source_event(source_adset)
    source_number, label = _source_identity(source_campaign)
    if not 1 <= len(source_ads) <= 5:
        raise SheinManifestError("SHEIN pure clone requires one through five source ads")
    ads = []
    for index, source_ad in enumerate(sorted(source_ads, key=lambda row: str(row.get("name") or "")), 1):
        source_id = str(source_ad.get("id") or "").strip()
        creative = source_ad.get("creative") or {}
        post_id = str(creative.get("effective_object_story_id") or "").strip()
        if not source_id or not post_id:
            raise SheinManifestError("pure clone source ad requires id and effective_object_story_id")
        payload = {
            "name": f"SHEIN C{number:03d} VIDEO {index:02d} COPY C{source_number}",
            # Reusing the source post is what preserves reactions/comments.
            # Target tracking stays ad-specific through url_tags.
            "object_story_id": post_id,
            "url_tags": tracking_tags(number),
            "degrees_of_freedom_spec": _individual_dof(creative),
        }
        ads.append(
            {
                "name": str(source_ad.get("name") or f"VIDEO - {index:02d}"),
                "source_ad_id": source_id,
                "creative_payload": payload,
            }
        )
    budget = budget_minor
    if budget is None:
        budget = _positive_int(source_campaign.get("daily_budget"), "source daily_budget")
    campaign = {
        "idempotency_key": request_id,
        "app_key": SHEIN_APP_KEY,
        "account_id": SHEIN_ACCOUNT_ID,
        "mode": "pure_clone",
        "creative_materialization_route": "existing_post_two_phase",
        "source_campaign_id": str(source_campaign.get("id") or ""),
        "source_adset_id": str(source_adset.get("id") or ""),
        "name": campaign_name(number, label, copy_source_number=source_number),
        "adset_name": adset_name(number),
        "start_time": start_time,
        "status": str(status).upper(),
        "campaign_updates": {
            "daily_budget": str(_positive_int(budget, "budget_minor")),
            "bid_strategy": str(
                source_campaign.get("bid_strategy") or "LOWEST_COST_WITHOUT_CAP"
            ),
        },
        "ads": ads,
    }
    return _manifest(request_id, "pure_clone", campaign)


def _unique_lineage_ids(source_ads: list[dict[str, Any]], count: int) -> list[str]:
    candidates: list[str] = []
    for row in sorted(source_ads, key=lambda item: str(item.get("name") or "")):
        value = str(row.get("id") or "").strip()
        if value and value != "0" and value not in candidates:
            candidates.append(value)
    for row in sorted(source_ads, key=lambda item: str(item.get("name") or "")):
        value = str(row.get("source_ad_id") or "").strip()
        if value and value != "0" and value not in candidates:
            candidates.append(value)
    if len(candidates) < count:
        raise SheinManifestError(
            f"insufficient unique ad lineage: required={count} available={len(candidates)}"
        )
    return candidates[:count]


def build_clone_prestaged_manifest(
    *,
    request_id: str,
    number: int,
    start_time: str,
    source_campaign: dict[str, Any],
    source_adset: dict[str, Any],
    source_ads: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    budget_minor: int,
    product_label: str,
    status: str = "ACTIVE",
) -> dict[str, Any]:
    _require_shein_source_event(source_adset)
    if not 1 <= len(assets) <= 5:
        raise SheinManifestError("SHEIN clone requires one through five assets")
    if not source_ads:
        raise SheinManifestError("SHEIN clone requires source ads")
    ordered_sources = sorted(source_ads, key=lambda row: str(row.get("name") or ""))
    lineage_ids = _unique_lineage_ids(source_ads, len(assets))
    ads = []
    for index, (asset, lineage_id) in enumerate(zip(assets, lineage_ids), 1):
        source_template = ordered_sources[(index - 1) % len(ordered_sources)]
        payload = _new_video_payload(
            source_ad=source_template,
            asset=asset,
            number=number,
            creative_name=f"SHEIN C{number:03d} VIDEO {index:02d} {asset['asset_id']}",
            include_media_sourcing=True,
        )
        ads.append(
            {
                "name": f"VIDEO - {index:02d}",
                "source_ad_id": lineage_id,
                "media": _media_for_manifest(asset),
                "creative_payload": payload,
            }
        )
    campaign = {
        "idempotency_key": request_id,
        "app_key": SHEIN_APP_KEY,
        "account_id": SHEIN_ACCOUNT_ID,
        "mode": "clone_prestaged",
        "source_campaign_id": str(source_campaign.get("id") or ""),
        "source_adset_id": str(source_adset.get("id") or ""),
        "name": campaign_name(number, product_label),
        "adset_name": adset_name(number),
        "start_time": start_time,
        "status": str(status).upper(),
        "campaign_updates": {
            "daily_budget": str(_positive_int(budget_minor, "budget_minor")),
            "bid_strategy": str(
                source_campaign.get("bid_strategy") or "LOWEST_COST_WITHOUT_CAP"
            ),
        },
        "ads": ads,
    }
    return _manifest(request_id, "clone_prestaged", campaign)
