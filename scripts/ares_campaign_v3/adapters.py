from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .media_registry import MediaRegistry

CPV_ACCOUNT_ID = "1046241194533786"
CPV_APP_KEY = "mgs-meta-app-current"
CPV_SOURCE_CAMPAIGN_ID = "120250209380780632"
CPV_SOURCE_ADSET_ID = "120250209380820632"
CPV_PAGE_ID = "621037101089579"
SP = ZoneInfo("America/Sao_Paulo")


def _replace_cpv_utm(value: Any, number: int) -> Any:
    if isinstance(value, str):
        return re.sub(r"b01fb13c08", f"b01fb13c{number:02d}", value)
    if isinstance(value, list):
        return [_replace_cpv_utm(item, number) for item in value]
    if isinstance(value, dict):
        return {key: _replace_cpv_utm(item, number) for key, item in value.items()}
    return value


def build_cpv_manifest(*, registry: MediaRegistry, asset_refs: list[dict[str, str]], campaign_numbers: list[int], operational_date: str, request_id: str, creative_templates: list[dict[str, Any]] | None = None, status: str = "PAUSED") -> dict[str, Any]:
    status = str(status).upper()
    if status not in {"PAUSED", "ACTIVE"}:
        raise ValueError("CPV v3 status must be PAUSED or ACTIVE")
    if not 1 <= len(campaign_numbers) <= 100:
        raise ValueError("CPV v3 requires 1..100 campaign numbers")
    required_assets = len(campaign_numbers) * 3
    if len(asset_refs) != required_assets:
        raise ValueError(f"CPV v3 requires exactly {required_assets} pre-staged assets for {len(campaign_numbers)} campaigns")
    base_date = datetime.fromisoformat(operational_date).replace(tzinfo=SP)
    start = (base_date + timedelta(days=1)).replace(hour=0, minute=30, second=0, microsecond=0)
    templates = creative_templates or [
        {"object_story_spec": {"page_id": CPV_PAGE_ID}, "asset_feed_spec": {"videos": []}}
        for _ in range(3)
    ]
    if len(templates) != 3:
        raise ValueError("CPV v3 requires three creative templates")
    campaigns = []
    for campaign_index, number in enumerate(campaign_numbers):
        ads = []
        for ad_index in range(3):
            ref = asset_refs[campaign_index * 3 + ad_index]
            ready = registry.require_ready(CPV_ACCOUNT_ID, ref["asset_id"], ref["checksum"])
            source_template = templates[ad_index]
            payload_template = source_template.get("creative_payload") if isinstance(source_template, dict) else None
            template = _replace_cpv_utm(copy.deepcopy(payload_template if isinstance(payload_template, dict) else source_template), number)
            asset_feed = dict(template.get("asset_feed_spec") or {})
            asset_feed["videos"] = [{"video_id": ready["vertical_video_id"]}, {"video_id": ready["square_video_id"]}]
            template["asset_feed_spec"] = asset_feed
            template.setdefault("object_story_spec", {"page_id": CPV_PAGE_ID})
            template["name"] = f"CPV C{number:02d} AD{ad_index + 1:02d} {ref['asset_id']}"
            ads.append({
                "name": f"AD {ad_index + 1:02d} - {ref['asset_id']}",
                "media": ready,
                "creative_payload": template,
            })
        campaigns.append({
            "idempotency_key": f"{request_id}-c{number:02d}",
            "app_key": CPV_APP_KEY,
            "account_id": CPV_ACCOUNT_ID,
            "mode": "clone_prestaged",
            "source_campaign_id": CPV_SOURCE_CAMPAIGN_ID,
            "source_adset_id": CPV_SOURCE_ADSET_ID,
            "name": f"{number:02d} - {start:%d-%m} - Garagem Brasil - (b01fb13c{number:02d}) event_Subscribe - MAXVOL",
            "adset_name": f"01 - AdGroup - (b01fb13c{number:02d}g01) event_Subscribe - MAXVOL",
            "start_time": start.isoformat(),
            "status": status,
            "campaign_updates": {"daily_budget": "3000", "bid_strategy": "LOWEST_COST_WITHOUT_CAP"},
            "ads": ads,
        })
    return {
        "schema_version": 3,
        "request_id": request_id,
        "operation": "Creditoparaveiculo-BR-CAR-BR-13-G006",
        "graph_version": "v26.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prevalidated": False,
        "campaigns": campaigns,
    }
