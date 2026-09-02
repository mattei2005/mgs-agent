from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .media_registry import MediaRegistry
from .source_selection import asset_group_vehicle_types, canonical_vehicle_type

CPV_ACCOUNT_ID = "1046241194533786"
CPV_APP_KEY = "mgs-meta-app-1299247318762949"
CPV_PAGE_ID = "621037101089579"
SP = ZoneInfo("America/Sao_Paulo")
CPV_CANONICAL_VIDEO_RE = re.compile(
    r"^CAR_BR_BR_VID_[A-Z0-9]+(?:_[A-Z0-9]+)*_(?:PV|NV|PH|NH)_\d{3}\.mp4$"
)


def _cpv_canonical_stem(ref: dict[str, str]) -> str:
    filename = str(ref.get("canonical_filename") or "").strip()
    if not filename:
        raise ValueError("CPV v3 asset_ref requires canonical_filename")
    if Path(filename).name != filename or not CPV_CANONICAL_VIDEO_RE.fullmatch(filename):
        raise ValueError(f"CPV v3 canonical_filename is invalid: {filename}")
    return Path(filename).stem


def _replace_cpv_utm(value: Any, number: int) -> Any:
    if isinstance(value, str):
        return re.sub(r"b01fb13c\d+", f"b01fb13c{number:02d}", value, flags=re.IGNORECASE)
    if isinstance(value, list):
        return [_replace_cpv_utm(item, number) for item in value]
    if isinstance(value, dict):
        return {key: _replace_cpv_utm(item, number) for key, item in value.items()}
    return value


def build_cpv_manifest(
    *,
    registry: MediaRegistry,
    asset_refs: list[dict[str, str]],
    campaign_numbers: list[int],
    operational_date: str,
    request_id: str,
    source_selections: list[dict[str, Any]] | None = None,
    mode: str = "clone_prestaged",
    from_zero_specs: list[dict[str, Any]] | None = None,
    status: str = "PAUSED",
    start_time: str | None = None,
    daily_budget_minor: int = 2500,
) -> dict[str, Any]:
    mode = str(mode).strip()
    if mode not in {"clone_prestaged", "from_zero_prestaged"}:
        raise ValueError("CPV v3 mode must be clone_prestaged or from_zero_prestaged")
    status = str(status).upper()
    if status not in {"PAUSED", "ACTIVE"}:
        raise ValueError("CPV v3 status must be PAUSED or ACTIVE")
    if not 1 <= len(campaign_numbers) <= 100:
        raise ValueError("CPV v3 requires 1..100 campaign numbers")
    daily_budget_minor = int(daily_budget_minor)
    if daily_budget_minor <= 0:
        raise ValueError("CPV v3 daily budget must be positive")
    required_assets = len(campaign_numbers) * 3
    if len(asset_refs) != required_assets:
        raise ValueError(f"CPV v3 requires exactly {required_assets} pre-staged assets for {len(campaign_numbers)} campaigns")
    base_date = datetime.fromisoformat(operational_date).replace(tzinfo=SP)
    if start_time:
        start = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
        if start.tzinfo is None:
            raise ValueError("CPV v3 explicit start_time requires timezone")
        start = start.astimezone(SP)
    else:
        start = (base_date + timedelta(days=1)).replace(hour=0, minute=30, second=0, microsecond=0)
    if source_selections is None or len(source_selections) != len(campaign_numbers):
        raise ValueError("CPV v3 requires one ROI-selected source per campaign")
    if mode == "from_zero_prestaged" and (from_zero_specs is None or len(from_zero_specs) != len(campaign_numbers)):
        raise ValueError("CPV v3 from-zero mode requires one explicit create spec per campaign")
    asset_vehicle_types = asset_group_vehicle_types(asset_refs, len(campaign_numbers))
    campaigns = []
    selection_audit = []
    for campaign_index, number in enumerate(campaign_numbers):
        source = source_selections[campaign_index]
        source_campaign_id = str(source.get("source_campaign_id") or "").strip()
        source_adset_id = str(source.get("source_adset_id") or "").strip()
        vehicle_type = canonical_vehicle_type(source.get("vehicle_type"))
        if vehicle_type != asset_vehicle_types[campaign_index]:
            raise ValueError(f"CPV v3 source vehicle type mismatch for campaign {number:02d}")
        if mode == "clone_prestaged" and (not source_campaign_id or not source_adset_id):
            raise ValueError(f"CPV v3 ROI source IDs are required for campaign {number:02d}")
        templates = source.get("templates") or []
        if len(templates) != 3:
            raise ValueError(f"CPV v3 ROI source requires three creative templates for campaign {number:02d}")
        ads = []
        for ad_index in range(3):
            ref = asset_refs[campaign_index * 3 + ad_index]
            canonical_stem = _cpv_canonical_stem(ref)
            ready = registry.require_ready(CPV_ACCOUNT_ID, ref["asset_id"], ref["checksum"])
            source_template = templates[ad_index]
            source_ad_id = str(source_template.get("source_ad_id") or "") if isinstance(source_template, dict) else ""
            if mode == "clone_prestaged" and (not source_ad_id or source_ad_id == "0"):
                raise ValueError(f"CPV v3 template AD {ad_index + 1:02d} requires nonzero source_ad_id")
            payload_template = source_template.get("creative_payload") if isinstance(source_template, dict) else None
            template = _replace_cpv_utm(copy.deepcopy(payload_template if isinstance(payload_template, dict) else source_template), number)
            asset_feed = dict(template.get("asset_feed_spec") or {})
            source_videos = list(asset_feed.get("videos") or [])
            replacement_videos = []
            for source_index, video_id in enumerate((ready["vertical_video_id"], ready["square_video_id"])):
                replacement = {"video_id": video_id}
                if source_index < len(source_videos):
                    labels = copy.deepcopy((source_videos[source_index] or {}).get("adlabels") or [])
                    if labels:
                        replacement["adlabels"] = labels
                replacement_videos.append(replacement)
            asset_feed["videos"] = replacement_videos
            template["asset_feed_spec"] = asset_feed
            template.setdefault("object_story_spec", {"page_id": CPV_PAGE_ID})
            template["name"] = f"CPV C{number:02d} AD{ad_index + 1:02d} {canonical_stem}"
            ad_row = {
                "name": f"AD {ad_index + 1:02d} - {canonical_stem}",
                "media": ready,
                "creative_payload": template,
            }
            if mode == "clone_prestaged":
                ad_row["source_ad_id"] = source_ad_id
            ads.append(ad_row)
        campaign_row = {
            "idempotency_key": f"{request_id}-c{number:02d}",
            "app_key": CPV_APP_KEY,
            "account_id": CPV_ACCOUNT_ID,
            "mode": mode,
            "name": f"{number:02d} - {start:%d-%m} - Garagem Brasil{' - MOTO' if vehicle_type == 'MOTO' else ''} - (b01fb13c{number:02d}) event_Subscribe - MAXVOL",
            "adset_name": f"01 - AdGroup - (b01fb13c{number:02d}g01) event_Subscribe - MAXVOL",
            "start_time": start.isoformat(),
            "status": status,
            "campaign_updates": {"daily_budget": str(daily_budget_minor), "bid_strategy": "LOWEST_COST_WITHOUT_CAP"},
            "ads": ads,
        }
        if mode == "clone_prestaged":
            campaign_row.update(source_campaign_id=source_campaign_id, source_adset_id=source_adset_id)
        else:
            create_spec = copy.deepcopy((from_zero_specs or [])[campaign_index])
            campaign_create = create_spec.get("campaign_create") or {}
            adset_create = create_spec.get("adset_create") or {}
            campaign_create.update(daily_budget=str(daily_budget_minor), bid_strategy="LOWEST_COST_WITHOUT_CAP")
            campaign_row["campaign_create"] = campaign_create
            campaign_row["adset_create"] = adset_create
            campaign_row["campaign_updates"] = {}
        campaigns.append(campaign_row)
        evidence = dict(source.get("roi_evidence") or {})
        if mode == "clone_prestaged":
            selection_audit.append({
                "campaign_number": number,
                "vehicle_type": vehicle_type,
                "source_campaign_id": source_campaign_id,
                "source_adset_id": source_adset_id,
                "roi_evidence": evidence,
            })
        else:
            selection_audit.append({
                "campaign_number": number,
                "vehicle_type": vehicle_type,
                "reference_campaign_id": source_campaign_id,
                "reference_adset_id": source_adset_id,
                "reference_only": True,
                "clone_edges_permitted": False,
            })
    return {
        "schema_version": 3,
        "request_id": request_id,
        "operation": "Creditoparaveiculo-BR-CAR-BR-13-G006",
        "graph_version": "v26.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prevalidated": False,
        "execution_mode": mode,
        "source_selection_policy": "live_compliant_same_vehicle_reference_only_no_clone" if mode == "from_zero_prestaged" else "highest_smart_bidding_roi_same_vehicle_type_at_manifest_preflight",
        "source_selections": selection_audit,
        "campaigns": campaigns,
    }
