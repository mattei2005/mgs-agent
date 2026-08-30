from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .media_registry import MediaRegistry
from .schema import Manifest

ACCOUNT_ID = "1034081997659047"
APP_KEY = "mgs-meta-app-current"
OPERATION = "Eggbev-US-CC-EN-BOT"
PAGE_TOKEN_RE = re.compile(r"^pg_[0-9]+$")

FACEBOOK_POSITIONS = [
    "feed",
    "instream_video",
    "marketplace",
    "story",
    "search",
    "biz_disco_feed",
    "facebook_reels",
    "facebook_reels_overlay",
    "profile_feed",
]
INSTAGRAM_POSITIONS = ["stream", "story", "reels", "explore", "explore_home", "profile_feed"]
MESSENGER_POSITIONS = ["story"]
SQUARE_RULE_FACEBOOK = ["feed", "instream_video", "marketplace", "biz_disco_feed", "profile_feed"]
SQUARE_RULE_INSTAGRAM = ["stream", "explore", "explore_home", "profile_feed"]


def _positive_int(value: Any, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def _clean_display(value: Any, name: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        raise ValueError(f"{name} is required")
    if any(char in text for char in "\r\n\t"):
        raise ValueError(f"{name} contains control whitespace")
    return text


def messenger_welcome_message() -> str:
    payload = {
        "performance_booster_enabled": False,
        "ctm_deprecate_quick_replies_enabled": False,
        "message_data": {
            "message": {
                "template_type": "text_with_buttons",
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "button",
                        "text": "💳 Hi, I just reviewed your access…\n\nDo you want to see your approved card? ⤵️",
                        "buttons": [
                            {
                                "type": "postback",
                                "payload": "GET_STARTED_PAYLOAD",
                                "title": "🟢 YES, SHOW ME",
                            }
                        ],
                    },
                },
            },
            "performance_booster_enabled": False,
            "ctm_deprecate_quick_replies_enabled": False,
        },
        "type": "JSON_SETUP",
        "is_user_editing": False,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _creative_payload(
    *,
    media: dict[str, Any],
    page_id: str,
    page_token: str,
    label_prefix: str,
    primary_text: str,
    headlines: list[str],
    description: str,
    cta: str,
) -> dict[str, Any]:
    vertical_label = {"name": f"{label_prefix}_vertical"}
    square_label = {"name": f"{label_prefix}_square"}
    return {
        "name": f"Eggbev {page_token} {label_prefix}",
        "object_story_spec": {"page_id": page_id},
        "asset_feed_spec": {
            "ad_formats": ["AUTOMATIC_FORMAT"],
            "optimization_type": "PLACEMENT",
            "videos": [
                {"video_id": str(media["vertical_video_id"]), "adlabels": [vertical_label]},
                {"video_id": str(media["square_video_id"]), "adlabels": [square_label]},
            ],
            "bodies": [{"text": primary_text}],
            "titles": [{"text": item} for item in headlines],
            "descriptions": [{"text": description}],
            "call_to_action_types": [cta],
            "asset_customization_rules": [
                {
                    "customization_spec": {
                        "age_min": 18,
                        "age_max": 65,
                        "publisher_platforms": ["facebook", "instagram"],
                        "facebook_positions": SQUARE_RULE_FACEBOOK,
                        "instagram_positions": SQUARE_RULE_INSTAGRAM,
                    },
                    "video_label": square_label,
                    "priority": 1,
                },
                {
                    "customization_spec": {"age_min": 18, "age_max": 65},
                    "video_label": vertical_label,
                    "priority": 2,
                },
            ],
            "additional_data": {
                "multi_share_end_card": False,
                "page_welcome_message": messenger_welcome_message(),
                "is_click_to_message": False,
            },
        },
        "url_tags": f"utm_campaign={page_token}",
        "degrees_of_freedom_spec": {
            "creative_features_spec": {
                "advantage_plus_creative": {"enroll_status": "OPT_OUT"},
                "image_brightness_and_contrast": {"enroll_status": "OPT_OUT"},
                "image_templates": {"enroll_status": "OPT_OUT"},
                "image_touchups": {"enroll_status": "OPT_OUT"},
                "inline_comment": {"enroll_status": "OPT_OUT"},
                "pac_relaxation": {"enroll_status": "OPT_OUT"},
                "replace_media_text": {"enroll_status": "OPT_OUT"},
                "reveal_details_over_time": {"enroll_status": "OPT_OUT"},
                "show_destination_blurbs": {"enroll_status": "OPT_OUT"},
                "show_summary": {"enroll_status": "OPT_OUT"},
                "text_optimizations": {"enroll_status": "OPT_OUT"},
                "text_translation": {"enroll_status": "OPT_OUT"},
                "translate_voiceover": {"enroll_status": "OPT_OUT"},
            }
        },
    }


def build_eggbev_from_zero_manifest(
    *,
    registry: MediaRegistry,
    request_id: str,
    page_id: str,
    page_name: str,
    page_token: str,
    page_sequence: int,
    campaign_sequences: list[int],
    daily_budgets_minor: list[int],
    start_time: str,
    asset_refs: list[dict[str, str]],
    ad_names: list[str],
    primary_text: str = "",
    headlines: list[str] | None = None,
    description: str = "⭐️⭐️⭐️⭐️⭐️",
    cta: str = "APPLY_NOW",
    status: str = "ACTIVE",
) -> dict[str, Any]:
    request_id = _clean_display(request_id, "request_id")
    page_id = _clean_display(page_id, "page_id")
    page_name = _clean_display(page_name, "page_name")
    page_token = str(page_token or "").strip().lower()
    if PAGE_TOKEN_RE.fullmatch(page_token) is None:
        raise ValueError("page_token must match pg_XXXXX")
    page_sequence = _positive_int(page_sequence, "page_sequence")
    campaign_sequences = [_positive_int(item, "campaign_sequence") for item in campaign_sequences]
    if not campaign_sequences or len(campaign_sequences) > 100 or len(set(campaign_sequences)) != len(campaign_sequences):
        raise ValueError("campaign_sequences must contain 1..100 unique positive integers")
    budgets = [_positive_int(item, "daily_budget_minor") for item in daily_budgets_minor]
    if len(budgets) != len(campaign_sequences):
        raise ValueError("one daily budget is required per campaign")
    if status != "ACTIVE":
        raise ValueError("Eggbev production from-zero manifest requires ACTIVE")
    parsed_start = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
    if parsed_start.tzinfo is None or parsed_start <= datetime.now(timezone.utc):
        raise ValueError("start_time must be a future timezone-aware datetime")
    if parsed_start.astimezone().utcoffset() is None:
        raise ValueError("start_time timezone is invalid")
    ads_per_campaign = len(asset_refs) // len(campaign_sequences) if campaign_sequences else 0
    if ads_per_campaign not in {3, 5} or len(asset_refs) != len(campaign_sequences) * ads_per_campaign:
        raise ValueError("Eggbev requires exactly three or five assets per campaign")
    if len(ad_names) != len(asset_refs):
        raise ValueError("one ad name is required per creative")
    clean_ad_names = [_clean_display(item, "ad_name") for item in ad_names]
    if len(set(clean_ad_names)) != len(clean_ad_names):
        raise ValueError("ad names must be unique across the request")
    media_keys = [(str(row.get("asset_id") or ""), str(row.get("checksum") or "")) for row in asset_refs]
    if any(not asset or not checksum for asset, checksum in media_keys) or len(set(media_keys)) != len(media_keys):
        raise ValueError("asset_refs must contain unique asset_id+checksum lineages")
    headlines = headlines or ["APPLY NOW ✅", "CARD APPROVED", "✔️ APPLY CARD"]
    if not headlines or any(not str(item).strip() for item in headlines):
        raise ValueError("at least one nonempty headline is required")
    campaigns: list[dict[str, Any]] = []
    for campaign_index, sequence in enumerate(campaign_sequences):
        campaign_name = f"{page_sequence} - {page_name} - ENG - US - ({page_token}) C{sequence:03d}"
        ads: list[dict[str, Any]] = []
        for ad_index in range(ads_per_campaign):
            global_index = campaign_index * ads_per_campaign + ad_index
            ref = asset_refs[global_index]
            ready = registry.require_ready(ACCOUNT_ID, ref["asset_id"], ref["checksum"])
            label_prefix = f"c{sequence:03d}_ad{ad_index + 1:02d}"
            ads.append(
                {
                    "name": clean_ad_names[global_index],
                    "media": ready,
                    "creative_payload": _creative_payload(
                        media=ready,
                        page_id=page_id,
                        page_token=page_token,
                        label_prefix=label_prefix,
                        primary_text=str(primary_text),
                        headlines=[str(headlines[global_index % len(headlines)])],
                        description=str(description),
                        cta=str(cta),
                    ),
                }
            )
        campaigns.append(
            {
                "idempotency_key": f"{request_id}-c{sequence:03d}",
                "app_key": APP_KEY,
                "account_id": ACCOUNT_ID,
                "mode": "from_zero_prestaged",
                "name": campaign_name,
                "adset_name": "AdG1",
                "start_time": start_time,
                "status": status,
                "campaign_updates": {},
                "campaign_create": {
                    "objective": "OUTCOME_SALES",
                    "buying_type": "AUCTION",
                    "daily_budget": str(budgets[campaign_index]),
                    "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                    "special_ad_categories": ["FINANCIAL_PRODUCTS_SERVICES"],
                    "special_ad_category_country": ["US"],
                },
                "adset_create": {
                    "billing_event": "IMPRESSIONS",
                    "optimization_goal": "OFFSITE_CONVERSIONS",
                    "destination_type": "MESSENGER",
                    "targeting": {
                        "age_min": 18,
                        "age_max": 65,
                        "geo_locations": {
                            "countries": ["US"],
                            "location_types": ["frequently_in", "home", "recent"],
                        },
                        "targeting_automation": {"advantage_audience": 1},
                        "publisher_platforms": ["facebook", "instagram", "messenger"],
                        "facebook_positions": FACEBOOK_POSITIONS,
                        "instagram_positions": INSTAGRAM_POSITIONS,
                        "messenger_positions": MESSENGER_POSITIONS,
                        "device_platforms": ["mobile", "desktop"],
                    },
                    "promoted_object": {
                        "pixel_id": "935354115143283",
                        "custom_event_type": "OTHER",
                        "page_id": page_id,
                        "smart_pse_enabled": False,
                    },
                    "attribution_spec": [
                        {"event_type": "CLICK_THROUGH", "window_days": 7},
                        {"event_type": "VIEW_THROUGH", "window_days": 1},
                    ],
                    "regional_regulated_categories": ["VOLUNTARY_VERIFICATION"],
                    "regional_regulation_identities": {
                        "universal_beneficiary": "1919111075424645",
                        "universal_payer": "1919111075424645",
                    },
                    "is_dynamic_creative": False,
                },
                "ads": ads,
            }
        )
    payload = {
        "schema_version": 3,
        "request_id": request_id,
        "operation": OPERATION,
        "graph_version": "v26.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prevalidated": False,
        "execution_mode": "from_zero_prestaged",
        "campaigns": campaigns,
    }
    Manifest.from_dict(payload)
    return payload
