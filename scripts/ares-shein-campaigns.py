#!/usr/bin/env python3
"""SHEIN-US-DIRECT materializer for the shared Campaign Engine v3.

This runner owns operation-specific request materialization and approval state.
It does not implement reporting, optimization, or an alternate campaign writer.
Every campaign mutation is delegated to ares-campaign-engine-v3.py.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.prevalidation import prevalidate_payload, validate_account_policy
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.shein import (
    SHEIN_ACCOUNT_ID,
    SHEIN_APP_KEY,
    build_clone_prestaged_manifest,
    build_from_zero_manifest,
    build_pure_clone_manifest,
    next_campaign_numbers,
)
from ares_campaign_v3.transport import FakeBatchTransport

BASE = Path("/root/mgs-agent")
CONFIG_PATH = BASE / "data/ares/meta-ads/engine-v3/config.json"
REGISTRY_PATH = BASE / "data/ares/meta-ads/engine-v3/media-registry.json"
STATE_ROOT = BASE / "data/ares/meta-ads/state/shein-campaigns"
AUDIT_ROOT = BASE / "data/ares/meta-ads/audit/shein/campaigns"
ENGINE_CLI = BASE / "scripts/ares-campaign-engine-v3.py"
META_COMMON_PATH = BASE / "scripts/ares-meta-common.py"
DRIVE_AUTH_PATH = BASE / "scripts/ares-drive-upload-manual-inventory.py"
ACCOUNT_PATH = BASE / "data/ares/meta-ads/accounts/2429758060563333.json"
OPERATION_PATH = BASE / "data/ares/meta-ads/operations/SHEIN-US-DIRECT.json"
OPERATION_V3_PATH = BASE / "data/ares/meta-ads/operations/SHEIN-US-DIRECT-v3.json"
INVENTORY_PATH = BASE / "data/ares/creative-ops/inventory/assets.jsonl"
SHARED_DRIVE_ID = "0AEwt4Ye690ocUk9PVA"
ET = ZoneInfo("America/New_York")
AUTHORIZED_EXECUTORS = {
    "Rodolfo",
    "Rodolfo Mattei",
    "Geizian",
    "Kelly",
    "Kelly Nice",
}
MODE_ORDER = ["from_zero_prestaged", "pure_clone", "clone_prestaged"]


class SheinRunnerBlocked(RuntimeError):
    def __init__(self, stage: str, detail: Any):
        self.stage = stage
        self.detail = detail
        super().__init__(f"{stage}: {detail}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SheinRunnerBlocked("json", f"cannot load {path.name}") from exc
    if not isinstance(value, dict):
        raise SheinRunnerBlocked("json", f"expected object in {path.name}")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def safe_request_id(value: str) -> str:
    text = "".join(char if char.isalnum() or char in "_.-" else "-" for char in str(value))
    text = text.strip("-")
    if not text:
        raise SheinRunnerBlocked("request_id", "invalid request id")
    return text[:160]


def state_path(request_id: str) -> Path:
    return STATE_ROOT / f"{safe_request_id(request_id)}.json"


def summary_digest(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _register_fake_media(registry: MediaRegistry, assets: list[dict[str, Any]]) -> None:
    for asset in assets:
        registry.register(
            account_id=SHEIN_ACCOUNT_ID,
            asset_id=asset["asset_id"],
            checksum=asset["checksum"],
            vertical_video_id=asset["vertical_video_id"],
            square_video_id=asset["square_video_id"],
            ready=True,
            source="shein-offline-smoke",
            upload_edge="ad_account_advideos",
            association_verified=True,
        )


def _fake_campaign(number: int, budget: str) -> dict[str, Any]:
    return {
        "id": f"campaign-{number}",
        "name": f"{number} - PRODUTOS SHEIN - US-EN (b01fb03c{number:03d}) event_add_to_wishlist",
        "daily_budget": budget,
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "objective": "OUTCOME_SALES",
        "buying_type": "AUCTION",
        "special_ad_categories": [],
        "special_ad_category_country": [],
    }


def _fake_adset(number: int) -> dict[str, Any]:
    return {
        "id": f"adset-{number}",
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "OFFSITE_CONVERSIONS",
        "targeting": {
            "age_min": 18,
            "age_max": 65,
            "geo_locations": {
                "countries": ["US"],
                "location_types": ["frequently_in", "home", "recent"],
            },
            "targeting_automation": {"advantage_audience": 1},
        },
        "promoted_object": {
            "pixel_id": "1049581090103163",
            "custom_event_type": "ADD_TO_WISHLIST",
            "smart_pse_enabled": False,
        },
        "attribution_spec": [
            {"event_type": "CLICK_THROUGH", "window_days": 7},
            {"event_type": "VIEW_THROUGH", "window_days": 1},
            {"event_type": "ENGAGED_VIDEO_VIEW", "window_days": 1},
        ],
        "regional_regulated_categories": ["VOLUNTARY_VERIFICATION"],
        "regional_regulation_identities": {
            "universal_beneficiary": "1773412024030451",
            "universal_payer": "1773412024030451",
        },
        "is_dynamic_creative": False,
    }


def _fake_ad(campaign_number: int, slot: int, *, upstream: str | None = None) -> dict[str, Any]:
    return {
        "id": f"ad-{campaign_number}-{slot}",
        "name": f"VIDEO - {slot:02d}",
        "source_ad_id": upstream or f"ad-{campaign_number - 1}-{slot}",
        "creative": {
            "id": f"creative-{campaign_number}-{slot}",
            "effective_object_story_id": f"410983488769165_post-{campaign_number}-{slot}",
            "object_story_spec": {
                "page_id": "410983488769165",
                "instagram_user_id": "17841469509077092",
                "video_data": {
                    "video_id": f"source-video-{campaign_number}-{slot}",
                    "title": "CLICK HERE ✅",
                    "message": "😱 SHEIN PRODUCTS FREE\n✔️ NO EXTRA COSTS OR FEES.",
                    "call_to_action": {
                        "type": "GET_OFFER_VIEW",
                        "value": {
                            "link": (
                                "https://yolokfx.com/quiz/us/sh2-g005/"
                                f"?utm_source=facebook&utm_medium=g005-s"
                                f"&utm_campaign=b01fb03c{campaign_number:03d}"
                                f"&utm_adgroup=b01fb03c{campaign_number:03d}g01"
                            )
                        },
                    },
                    "image_url": "https://example.test/source.jpg",
                    "image_hash": "source-image-hash",
                },
            },
            "degrees_of_freedom_spec": {
                "creative_features_spec": {
                    "advantage_plus_creative": {"enroll_status": "OPT_OUT"},
                    "standard_enhancements": {"enroll_status": "OPT_IN"},
                }
            },
        },
    }


def _fake_assets(product: str, count: int) -> list[dict[str, Any]]:
    return [
        {
            "asset_id": f"asset-{product}-{index}",
            "checksum": f"checksum-{product}-{index}",
            "canonical_filename": f"SHEIN_US_EN_VID_FREE_{product}_PV_{index:03d}.mp4",
            "vertical_video_id": f"video-{product}-{index}",
            "square_video_id": f"square-{product}-{index}",
            "thumbnail_url": f"https://example.test/{product}-{index}.jpg",
            "ready": True,
            "upload_edge": "ad_account_advideos",
            "association_verified": True,
        }
        for index in range(1, count + 1)
    ]


def seal_and_plan(
    payload: dict[str, Any],
    *,
    registry: MediaRegistry,
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed = Manifest.from_dict(payload)
    validate_account_policy(parsed, config)
    sealed = prevalidate_payload(payload, registry)
    manifest = Manifest.from_dict(sealed)
    plan = CampaignEngine(
        config,
        transport_factory=lambda account: FakeBatchTransport(account),
    ).dry_run(manifest)
    return sealed, plan


def offline_smoke(output: Path | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as raw:
        registry = MediaRegistry(Path(raw) / "registry.json")
        blender = _fake_assets("PORTABLE_BLENDER", 3)
        makeup = _fake_assets("MAKEUP_BAG", 3)
        _register_fake_media(registry, [*blender, *makeup])
        start = (datetime.now(ET) + timedelta(days=2)).replace(
            hour=0, minute=10, second=0, microsecond=0
        ).isoformat()
        c34 = _fake_campaign(34, "3000")
        c20 = _fake_campaign(20, "2500")
        a34 = [_fake_ad(34, 1), _fake_ad(34, 2)]
        a20 = [
            _fake_ad(20, 1, upstream="ad-19-1"),
            _fake_ad(20, 2, upstream="ad-19-2"),
        ]
        manifests = [
            build_from_zero_manifest(
                request_id="shein-offline-c038",
                number=38,
                start_time=start,
                reference_campaign=c34,
                reference_adset=_fake_adset(34),
                copy_source_ad=a34[0],
                assets=blender,
                budget_minor=5000,
                product_label="LIQUIDIFICADOR",
            ),
            build_pure_clone_manifest(
                request_id="shein-offline-c039",
                number=39,
                start_time=start,
                source_campaign=c34,
                source_adset=_fake_adset(34),
                source_ads=a34,
            ),
            build_clone_prestaged_manifest(
                request_id="shein-offline-c040",
                number=40,
                start_time=start,
                source_campaign=c20,
                source_adset=_fake_adset(20),
                source_ads=a20,
                assets=makeup,
                budget_minor=5000,
                product_label="MALETA DE MAQUIAGEM",
            ),
        ]
        config = load_json(CONFIG_PATH)
        sealed: list[dict[str, Any]] = []
        plans: list[dict[str, Any]] = []
        for payload in manifests:
            final, plan = seal_and_plan(payload, registry=registry, config=config)
            sealed.append(final)
            plans.append(plan["plan"])
        result = {
            "status": "OFFLINE_SMOKE_OK",
            "engine_version": 3,
            "campaigns": len(sealed),
            "ads": sum(
                len(campaign.get("ads") or [])
                for payload in sealed
                for campaign in payload.get("campaigns") or []
            ),
            "modes": [payload["execution_mode"] for payload in sealed],
            "plans": plans,
            "network_calls": 0,
            "writes": 0,
        }
        if output:
            atomic_json(output, {"manifests": sealed, "result": result})
        return result


def materialize_resolved(
    request: dict[str, Any],
    output_dir: Path,
    *,
    registry_path: Path = REGISTRY_PATH,
    config_path: Path = CONFIG_PATH,
) -> dict[str, Any]:
    started = time.perf_counter()
    request_id = safe_request_id(str(request.get("request_id") or ""))
    start_time = str(request.get("start_time") or "")
    live_campaigns = list(request.get("live_campaigns") or [])
    numbers = next_campaign_numbers(live_campaigns, 3)
    expected_modes = list(request.get("mode_order") or MODE_ORDER)
    if expected_modes != MODE_ORDER:
        raise SheinRunnerBlocked("mode_order", f"expected {MODE_ORDER}")
    zero = request.get("from_zero") or {}
    pure = request.get("pure_clone") or {}
    clone = request.get("clone_prestaged") or {}
    zero_assets = list(zero.get("assets") or [])
    clone_assets = list(clone.get("assets") or [])
    all_asset_ids = [
        str(row.get("asset_id") or "") for row in [*zero_assets, *clone_assets]
    ]
    if len(zero_assets) != 3 or not 1 <= len(clone_assets) <= 5:
        raise SheinRunnerBlocked(
            "asset_selection",
            "from-zero requires three assets and clone requires one through five",
        )
    expected_unique = 3 + len(clone_assets)
    if (
        any(not value for value in all_asset_ids)
        or len(set(all_asset_ids)) != expected_unique
    ):
        raise SheinRunnerBlocked(
            "asset_selection",
            f"{expected_unique} unique asset lineages are required across the request",
        )
    manifests = [
        build_from_zero_manifest(
            request_id=f"{request_id}-c{numbers[0]:03d}",
            number=numbers[0],
            start_time=start_time,
            reference_campaign=zero["reference_campaign"],
            reference_adset=zero["reference_adset"],
            copy_source_ad=zero["copy_source_ad"],
            assets=list(zero["assets"]),
            budget_minor=int(zero["budget_minor"]),
            product_label=str(zero["product_label"]),
        ),
        build_pure_clone_manifest(
            request_id=f"{request_id}-c{numbers[1]:03d}",
            number=numbers[1],
            start_time=start_time,
            source_campaign=pure["source_campaign"],
            source_adset=pure["source_adset"],
            source_ads=list(pure["source_ads"]),
            budget_minor=(
                int(pure["budget_minor"])
                if pure.get("budget_minor") is not None
                else None
            ),
        ),
        build_clone_prestaged_manifest(
            request_id=f"{request_id}-c{numbers[2]:03d}",
            number=numbers[2],
            start_time=start_time,
            source_campaign=clone["source_campaign"],
            source_adset=clone["source_adset"],
            source_ads=list(clone["source_ads"]),
            assets=list(clone["assets"]),
            budget_minor=int(clone["budget_minor"]),
            product_label=str(clone["product_label"]),
        ),
    ]
    registry = MediaRegistry(registry_path)
    config = load_json(config_path)
    sealed: list[dict[str, Any]] = []
    plans: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for payload in manifests:
        final, plan = seal_and_plan(payload, registry=registry, config=config)
        path = output_dir / f"{safe_request_id(final['request_id'])}-sealed.json"
        atomic_json(path, final)
        sealed.append(final)
        plans.append(plan["plan"])
    summary = {
        "request_id": request_id,
        "engine_version": 3,
        "account_id": SHEIN_ACCOUNT_ID,
        "start_time": start_time,
        "numbers": numbers,
        "campaigns": [
            {
                "request_id": payload["request_id"],
                "mode": payload["execution_mode"],
                "name": payload["campaigns"][0]["name"],
                "budget_minor": (
                    payload["campaigns"][0].get("campaign_updates", {}).get("daily_budget")
                    or payload["campaigns"][0].get("campaign_create", {}).get("daily_budget")
                ),
                "ads": len(payload["campaigns"][0]["ads"]),
                "manifest_digest": Manifest.from_dict(payload).digest,
            }
            for payload in sealed
        ],
        "plans": plans,
    }
    digest = summary_digest(summary)
    state = {
        "schema_version": 1,
        "request_id": request_id,
        "phase": "AWAITING_FINAL_APPROVAL",
        "summary": summary,
        "summary_digest": digest,
        "manifest_paths": [
            str(output_dir / f"{safe_request_id(payload['request_id'])}-sealed.json")
            for payload in sealed
        ],
        "new_media_assets": [
            *list(zero["assets"]),
            *list(clone["assets"]),
        ],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "campaign_writes": 0,
        "network_calls": 0,
        "timings": {
            "materialization_duration_ms": round(
                (time.perf_counter() - started) * 1000, 3
            )
        },
    }
    atomic_json(state_path(request_id), state)
    atomic_json(AUDIT_ROOT / f"{request_id}-materialization.json", state)
    return {
        "status": "AWAITING_FINAL_APPROVAL",
        "request_id": request_id,
        "summary_digest": digest,
        "summary": summary,
        "campaign_writes": 0,
        "network_calls": 0,
    }


def prepare_live_request(
    specification: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    started = time.perf_counter()
    request_id = safe_request_id(str(specification.get("request_id") or ""))
    zero = specification.get("from_zero") or {}
    pure = specification.get("pure_clone") or {}
    clone = specification.get("clone_prestaged") or {}
    source_ids = {
        "zero": str(zero.get("reference_campaign_id") or ""),
        "pure": str(pure.get("source_campaign_id") or ""),
        "clone": str(clone.get("source_campaign_id") or ""),
    }
    if any(not value for value in source_ids.values()):
        raise SheinRunnerBlocked("source", "all three source campaign IDs are required")
    common, token, credential = meta_runtime()
    requests: list[dict[str, Any]] = [
        {
            "name": "account",
            "path": f"act_{SHEIN_ACCOUNT_ID}",
            "params": {
                "fields": "id,name,currency,timezone_name,account_status,disable_reason"
            },
        },
        {
            "name": "campaigns",
            "path": f"act_{SHEIN_ACCOUNT_ID}/campaigns",
            "params": {
                "fields": "id,name,status,effective_status,configured_status",
                "limit": 500,
            },
        },
    ]
    unique_sources = list(dict.fromkeys(source_ids.values()))
    for index, campaign_id in enumerate(unique_sources, 1):
        requests.extend(
            [
                {
                    "name": f"source_{index}_campaign",
                    "path": campaign_id,
                    "params": {
                        "fields": "id,name,status,effective_status,configured_status,objective,buying_type,bid_strategy,daily_budget,start_time,special_ad_categories,special_ad_category_country"
                    },
                },
                {
                    "name": f"source_{index}_adsets",
                    "path": f"{campaign_id}/adsets",
                    "params": {
                        "fields": "id,name,status,effective_status,configured_status,billing_event,optimization_goal,targeting,attribution_spec,promoted_object,is_dynamic_creative,regional_regulated_categories,regional_regulation_identities",
                        "limit": 20,
                    },
                },
                {
                    "name": f"source_{index}_ads",
                    "path": f"{campaign_id}/ads",
                    "params": {
                        "fields": "id,name,status,effective_status,configured_status,source_ad_id,adset_id,creative{id,name,status,object_story_id,effective_object_story_id,object_story_spec,media_sourcing_spec,url_tags,degrees_of_freedom_spec}",
                        "limit": 50,
                    },
                },
            ]
        )
    status, responses, headers = common.graph_batch_get(token, requests)
    if status != 200 or any(row.get("code") != 200 for row in responses):
        raise SheinRunnerBlocked(
            "meta_preflight",
            {
                "outer_http": status,
                "children": [
                    {"name": row.get("name"), "http": row.get("code")}
                    for row in responses
                ],
            },
        )
    by_name = {row["name"]: row["body"] for row in responses}
    account = by_name["account"]
    if (
        str(account.get("id")) != f"act_{SHEIN_ACCOUNT_ID}"
        or account.get("currency") != "USD"
        or account.get("timezone_name") != "America/New_York"
        or account.get("account_status") != 1
        or account.get("disable_reason") != 0
    ):
        raise SheinRunnerBlocked("meta_preflight", "account identity or health failed")
    if (by_name["campaigns"].get("paging") or {}).get("next"):
        raise SheinRunnerBlocked("meta_preflight", "campaign inventory pagination incomplete")
    sources: dict[str, dict[str, Any]] = {}
    for index, campaign_id in enumerate(unique_sources, 1):
        campaign = by_name[f"source_{index}_campaign"]
        adsets = list(by_name[f"source_{index}_adsets"].get("data") or [])
        ads = [
            row
            for row in (by_name[f"source_{index}_ads"].get("data") or [])
            if str(row.get("configured_status") or row.get("status") or "").upper()
            == "ACTIVE"
        ]
        if str(campaign.get("id")) != campaign_id or len(adsets) != 1 or not ads:
            raise SheinRunnerBlocked(
                "meta_preflight",
                {"source_campaign_id": campaign_id, "adsets": len(adsets), "ads": len(ads)},
            )
        if str(campaign.get("configured_status") or campaign.get("status")) in {
            "DELETED",
            "ARCHIVED",
        }:
            raise SheinRunnerBlocked("meta_preflight", "source campaign is terminal")
        sources[campaign_id] = {
            "campaign": campaign,
            "adset": adsets[0],
            "ads": sorted(ads, key=lambda row: str(row.get("name") or "")),
        }
    zero_source = sources[source_ids["zero"]]
    pure_source = sources[source_ids["pure"]]
    clone_source = sources[source_ids["clone"]]
    resolved = {
        "request_id": request_id,
        "start_time": str(specification.get("start_time") or ""),
        "live_campaigns": list(by_name["campaigns"].get("data") or []),
        "mode_order": MODE_ORDER,
        "from_zero": {
            "reference_campaign": zero_source["campaign"],
            "reference_adset": zero_source["adset"],
            "copy_source_ad": zero_source["ads"][0],
            "assets": list(zero.get("assets") or []),
            "budget_minor": int(zero["budget_minor"]),
            "product_label": str(zero["product_label"]),
        },
        "pure_clone": {
            "source_campaign": pure_source["campaign"],
            "source_adset": pure_source["adset"],
            "source_ads": pure_source["ads"],
            "budget_minor": (
                int(pure["budget_minor"])
                if pure.get("budget_minor") is not None
                else None
            ),
        },
        "clone_prestaged": {
            "source_campaign": clone_source["campaign"],
            "source_adset": clone_source["adset"],
            "source_ads": clone_source["ads"],
            "assets": list(clone.get("assets") or []),
            "budget_minor": int(clone["budget_minor"]),
            "product_label": str(clone["product_label"]),
        },
    }
    result = materialize_resolved(resolved, output_dir)
    path = state_path(request_id)
    state = load_json(path)
    state["network_calls"] = 1
    state["credential_readback"] = credential
    state["meta_preflight"] = {
        "account": account,
        "source_campaign_ids": source_ids,
        "campaign_count": len(resolved["live_campaigns"]),
        "outer_graph_batches": 1,
    }
    state.setdefault("timings", {})["prepare_live_duration_ms"] = round(
        (time.perf_counter() - started) * 1000, 3
    )
    atomic_json(path, state)
    atomic_json(AUDIT_ROOT / f"{request_id}-materialization.json", state)
    result["network_calls"] = 1
    result["credential_readback"] = credential
    result["meta_preflight"] = state["meta_preflight"]
    result["timings"] = state["timings"]
    return result


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SheinRunnerBlocked("module", f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def meta_runtime():
    config = load_json(CONFIG_PATH)
    account = (config.get("accounts") or {}).get(SHEIN_ACCOUNT_ID) or {}
    token_item = str(account.get("token_item") or "")
    if not token_item:
        raise SheinRunnerBlocked("credential", "account token item is missing")
    os.environ["ARES_META_GRAPH_VERSION"] = str(config.get("graph_version") or "v26.0")
    common = load_module(META_COMMON_PATH, "ares_shein_v3_meta")
    token, field = common.get_token_from_1password(item_name=token_item)
    return common, token, {
        "item": token_item,
        "field": field,
        "token_len": len(token),
    }


def _same_instant(left: Any, right: Any) -> bool:
    try:
        a = datetime.fromisoformat(str(left).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(right).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return a.astimezone(timezone.utc) == b.astimezone(timezone.utc)


def _ad_video_id(ad: dict[str, Any]) -> str:
    creative = ad.get("creative") or {}
    story = creative.get("object_story_spec") or {}
    video = story.get("video_data") or {}
    return str(video.get("video_id") or "")


def verify_live_result(
    *,
    common: Any,
    token: str,
    manifest: dict[str, Any],
    campaign_id: str,
    page_token: str | None,
) -> dict[str, Any]:
    expected = manifest["campaigns"][0]
    requests = [
        {
            "name": "campaign",
            "path": campaign_id,
            "params": {
                "fields": "id,name,status,effective_status,configured_status,objective,buying_type,bid_strategy,daily_budget,start_time"
            },
        },
        {
            "name": "adsets",
            "path": f"{campaign_id}/adsets",
            "params": {
                "fields": "id,name,status,effective_status,configured_status,start_time,optimization_goal,promoted_object",
                "limit": 20,
            },
        },
        {
            "name": "ads",
            "path": f"{campaign_id}/ads",
            "params": {
                "fields": "id,name,status,effective_status,configured_status,source_ad_id,issues_info,creative{id,name,status,object_story_id,effective_object_story_id,object_story_spec,media_sourcing_spec,url_tags}",
                "limit": 50,
            },
        },
    ]
    status, responses, _ = common.graph_batch_get(token, requests)
    if status != 200 or any(row.get("code") != 200 for row in responses):
        raise SheinRunnerBlocked(
            "meta_readback",
            {
                "outer_http": status,
                "children": [
                    {"name": row.get("name"), "http": row.get("code")}
                    for row in responses
                ],
            },
        )
    by_name = {row["name"]: row["body"] for row in responses}
    campaign = by_name["campaign"]
    adsets = list(by_name["adsets"].get("data") or [])
    ads = list(by_name["ads"].get("data") or [])
    expected_budget = str(
        (expected.get("campaign_updates") or {}).get("daily_budget")
        or (expected.get("campaign_create") or {}).get("daily_budget")
        or ""
    )
    if (
        str(campaign.get("id")) != str(campaign_id)
        or campaign.get("name") != expected.get("name")
        or str(campaign.get("configured_status") or campaign.get("status"))
        != str(expected.get("status"))
        or str(campaign.get("daily_budget") or "") != expected_budget
        or not _same_instant(campaign.get("start_time"), expected.get("start_time"))
        or len(adsets) != 1
        or adsets[0].get("name") != expected.get("adset_name")
    ):
        raise SheinRunnerBlocked("meta_readback", "campaign or adset differs from manifest")
    active_ads = [
        row
        for row in ads
        if str(row.get("configured_status") or row.get("status")) == str(expected.get("status"))
    ]
    if len(active_ads) != len(expected.get("ads") or []):
        raise SheinRunnerBlocked(
            "meta_readback",
            {"expected_active_ads": len(expected.get("ads") or []), "actual": len(active_ads)},
        )
    if any(row.get("issues_info") for row in active_ads):
        raise SheinRunnerBlocked("meta_readback", "one or more active ads has issues_info")
    assignments: list[dict[str, Any]] = []
    social: list[dict[str, Any]] = []
    if expected["mode"] == "pure_clone":
        expected_by_source = {
            str(row["source_ad_id"]): row for row in expected.get("ads") or []
        }
        actual_by_source = {
            str(row.get("source_ad_id") or ""): row for row in active_ads
        }
        if set(actual_by_source) != set(expected_by_source):
            raise SheinRunnerBlocked("pure_clone_readback", "source_ad_id set drifted")
        for source_ad_id, expected_ad in expected_by_source.items():
            actual = actual_by_source[source_ad_id]
            creative = actual.get("creative") or {}
            payload = expected_ad["creative_payload"]
            post_id = str(payload["object_story_id"])
            if (
                str(creative.get("object_story_id") or "") != post_id
                or str(creative.get("effective_object_story_id") or "") != post_id
                or str(creative.get("url_tags") or "") != str(payload["url_tags"])
            ):
                raise SheinRunnerBlocked(
                    "pure_clone_readback", "post identity or target url_tags drifted"
                )
            if page_token:
                post_status, post, _ = common.graph_get(
                    post_id,
                    page_token,
                    {
                        "fields": "id,reactions.limit(0).summary(true),comments.limit(0).summary(true),shares"
                    },
                )
                if post_status != 200 or str(post.get("id")) != post_id:
                    raise SheinRunnerBlocked("pure_clone_social", {"http": post_status})
                social.append(
                    {
                        "post_id": post_id,
                        "reactions": ((post.get("reactions") or {}).get("summary") or {}).get(
                            "total_count"
                        ),
                        "comments": ((post.get("comments") or {}).get("summary") or {}).get(
                            "total_count"
                        ),
                        "shares": (post.get("shares") or {}).get("count"),
                    }
                )
    else:
        expected_by_video = {
            str(row["media"]["vertical_video_id"]): row
            for row in expected.get("ads") or []
        }
        actual_by_video = {_ad_video_id(row): row for row in active_ads}
        if set(actual_by_video) != set(expected_by_video):
            raise SheinRunnerBlocked("media_readback", "target video set drifted")
        for video_id, expected_ad in expected_by_video.items():
            actual = actual_by_video[video_id]
            creative = actual.get("creative") or {}
            if expected["mode"] == "clone_prestaged":
                sourcing = creative.get("media_sourcing_spec") or {}
                sourcing_ids = {
                    str(row.get("video_id") or "")
                    for row in sourcing.get("videos") or []
                }
                if video_id not in sourcing_ids:
                    raise SheinRunnerBlocked(
                        "media_readback", "primary video missing from media_sourcing_spec"
                    )
            assignments.append(
                {
                    "asset_id": expected_ad["media"]["asset_id"],
                    "campaign_id": campaign_id,
                    "adset_id": str(adsets[0]["id"]),
                    "ad_id": str(actual["id"]),
                    "creative_id": str(creative["id"]),
                    "video_id": video_id,
                    "effective_object_story_id": str(
                        creative.get("effective_object_story_id") or ""
                    ),
                }
            )
    return {
        "campaign": campaign,
        "adset": adsets[0],
        "ads": active_ads,
        "assignments": assignments,
        "social": social,
    }


def drive_runtime_token() -> tuple[str, dict[str, Any]]:
    module = load_module(DRIVE_AUTH_PATH, "ares_shein_v3_drive")
    module.load_env()
    service_account = module.extract_service_account(module.get_op_item_json())
    if (
        service_account.get("client_email")
        != "mgsagent@mgs-core-prod.iam.gserviceaccount.com"
        or service_account.get("project_id") != "mgs-core-prod"
    ):
        raise SheinRunnerBlocked("drive_identity", "canonical service account mismatch")
    setattr(module, "SCOPES", "https://www.googleapis.com/auth/drive")
    return module.get_access_token(service_account), {
        "client_email": service_account.get("client_email"),
        "project_id": service_account.get("project_id"),
    }


def drive_file_readback(token: str, file_id: str) -> dict[str, Any]:
    fields = "id,name,size,md5Checksum,driveId,parents,trashed"
    url = (
        f"https://www.googleapis.com/drive/v3/files/{file_id}?"
        + urllib.parse.urlencode({"fields": fields, "supportsAllDrives": "true"})
    )
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "MGS-Ares-SHEIN-V3/3.6.1",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def move_asset_to_testing(
    token: str,
    asset: dict[str, Any],
    *,
    ready_id: str,
    testing_id: str,
) -> dict[str, Any]:
    file_id = str(asset.get("asset_drive_id") or "")
    if not file_id:
        raise SheinRunnerBlocked("drive_postprocess", "asset_drive_id is required")
    before = drive_file_readback(token, file_id)
    parents = set(str(value) for value in before.get("parents") or [])
    if testing_id not in parents:
        if ready_id not in parents:
            raise SheinRunnerBlocked(
                "drive_postprocess", {"file_id": file_id, "parents": sorted(parents)}
            )
        params = urllib.parse.urlencode(
            {
                "addParents": testing_id,
                "removeParents": ready_id,
                "fields": "id,name,size,md5Checksum,driveId,parents,trashed",
                "supportsAllDrives": "true",
            }
        )
        request = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?{params}",
            data=b"{}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "MGS-Ares-SHEIN-V3/3.6.1",
            },
            method="PATCH",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            json.loads(response.read())
    after = drive_file_readback(token, file_id)
    if (
        after.get("driveId") != SHARED_DRIVE_ID
        or after.get("trashed")
        or set(after.get("parents") or []) != {testing_id}
        or (
            asset.get("drive_md5")
            and str(after.get("md5Checksum") or "") != str(asset.get("drive_md5"))
        )
    ):
        raise SheinRunnerBlocked("drive_postprocess", f"readback failed for {file_id}")
    return after


def atomic_inventory(rows: list[dict[str, Any]]) -> None:
    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{INVENTORY_PATH.name}.", dir=INVENTORY_PATH.parent)
    temporary = Path(raw)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, INVENTORY_PATH)
        os.chmod(INVENTORY_PATH, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def close_write_gate(request_id: str) -> dict[str, Any]:
    stamp = datetime.now(timezone.utc).isoformat()
    account = load_json(ACCOUNT_PATH)
    row = (account.get("accounts") or [{}])[0]
    route = ((row.get("runtime_routes") or {}).get("campaign_creation") or {})
    if route.get("write_enabled") is True:
        if str(route.get("active_request_id") or "") != request_id:
            raise SheinRunnerBlocked("write_gate", "active account request changed")
        route.pop("active_request_id", None)
        route.update(
            write_enabled=False,
            last_completed_request_id=request_id,
            last_completed_at_utc=stamp,
            write_gate="closed after terminal reconciliation",
        )
        atomic_json(ACCOUNT_PATH, account)
    operation = load_json(OPERATION_PATH)
    registry_rows = (operation.get("runtime_readiness") or {}).get("account_registry") or []
    matched = [item for item in registry_rows if str(item.get("account_id")) == SHEIN_ACCOUNT_ID]
    if len(matched) != 1:
        raise SheinRunnerBlocked("write_gate", "operation account registry is ambiguous")
    operation_row = matched[0]
    if operation_row.get("write_enabled") is True:
        if str(operation_row.get("active_request_id") or "") != request_id:
            raise SheinRunnerBlocked("write_gate", "active operation request changed")
        operation_row.pop("active_request_id", None)
        operation_row.update(
            write_enabled=False,
            last_completed_request_id=request_id,
            last_completed_at_utc=stamp,
            write_gate="closed after terminal reconciliation",
        )
        atomic_json(OPERATION_PATH, operation)
    return {"closed": True, "completed_at_utc": stamp}


def finalize_materialized(state: dict[str, Any]) -> dict[str, Any]:
    manifests = [load_json(Path(path)) for path in state.get("manifest_paths") or []]
    results = list(state.get("engine_results") or [])
    result_by_request = {str(row.get("request_id")): row for row in results}
    common, token, credential = meta_runtime()
    pages_status, pages, _ = common.graph_get(
        "me/accounts", token, {"fields": "id,name,tasks,access_token", "limit": 200}
    )
    page = next(
        (
            row
            for row in (pages.get("data") or [])
            if str(row.get("id")) == "410983488769165"
        ),
        None,
    )
    if pages_status != 200 or not page or not page.get("access_token"):
        raise SheinRunnerBlocked("page_readback", {"http": pages_status})
    readbacks = []
    assignments = []
    for manifest in manifests:
        result = result_by_request.get(str(manifest["request_id"])) or {}
        campaign_ids = list(result.get("campaign_ids") or [])
        if len(campaign_ids) != 1:
            raise SheinRunnerBlocked("postprocess", "engine campaign identity is incomplete")
        readback = verify_live_result(
            common=common,
            token=token,
            manifest=manifest,
            campaign_id=str(campaign_ids[0]),
            page_token=str(page["access_token"]),
        )
        readbacks.append(
            {
                "request_id": manifest["request_id"],
                "campaign_id": str(campaign_ids[0]),
                "mode": manifest["execution_mode"],
                "active_ads": len(readback["ads"]),
                "social": readback["social"],
            }
        )
        assignments.extend(readback["assignments"])
    assets = list(state.get("new_media_assets") or [])
    asset_by_id = {str(row.get("asset_id")): row for row in assets}
    assignment_by_id = {str(row.get("asset_id")): row for row in assignments}
    if set(asset_by_id) != set(assignment_by_id):
        raise SheinRunnerBlocked("postprocess", "asset and Meta assignment sets differ")
    drive_token, service_account = drive_runtime_token()
    operation_v3 = load_json(OPERATION_V3_PATH)
    vid_folders = (((operation_v3.get("drive") or {}).get("folders") or {}).get("VID") or {})
    ready_id = str(vid_folders.get("01_READY") or "")
    testing_id = str(vid_folders.get("02_TESTING") or "")
    if not ready_id or not testing_id:
        raise SheinRunnerBlocked("drive_postprocess", "VID lifecycle IDs are missing")
    def move_one(item: tuple[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        asset_id, asset = item
        return (
            asset_id,
            move_asset_to_testing(
                drive_token,
                asset,
                ready_id=ready_id,
                testing_id=testing_id,
            ),
        )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(5, max(1, len(asset_by_id)))
    ) as pool:
        drive_readbacks = dict(pool.map(move_one, asset_by_id.items()))
    inventory_rows = [
        json.loads(line)
        for line in INVENTORY_PATH.read_text().splitlines()
        if line.strip()
    ]
    inventory_by_id = {
        str(row.get("asset_id")): row for row in inventory_rows
    }
    if not set(asset_by_id).issubset(inventory_by_id):
        raise SheinRunnerBlocked("inventory_postprocess", "selected inventory rows disappeared")
    backup = AUDIT_ROOT / f"{safe_request_id(state['request_id'])}-inventory-before.jsonl"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(INVENTORY_PATH, backup)
    stamp = datetime.now(timezone.utc).isoformat()
    registry = MediaRegistry(REGISTRY_PATH)
    for asset_id, asset in asset_by_id.items():
        row = inventory_by_id[asset_id]
        if str(row.get("reservation_request_id") or "") != str(state["request_id"]):
            raise SheinRunnerBlocked(
                "inventory_postprocess", f"reservation request drift: {asset_id}"
            )
        assignment = assignment_by_id[asset_id]
        checksum = str(asset.get("checksum") or asset.get("clean_checksum") or "")
        media = registry.require_ready(
            SHEIN_ACCOUNT_ID,
            asset_id,
            checksum,
            required_variants=("vertical",),
        )
        row.update(
            status="02_TESTING",
            reservation_status="UTILIZADO_PELO_ARES",
            ares_eligible=False,
            used_by="ARES",
            campaign_owner="Ares",
            ad_account_id=SHEIN_ACCOUNT_ID,
            meta_campaign_id=assignment["campaign_id"],
            meta_adset_id=assignment["adset_id"],
            meta_ad_id=assignment["ad_id"],
            meta_creative_id=assignment["creative_id"],
            meta_video_id=assignment["video_id"],
            meta_prestage_video_ids=[
                value
                for value in (
                    media.get("vertical_video_id"),
                    media.get("square_video_id"),
                )
                if value
            ],
            effective_object_story_id=assignment["effective_object_story_id"],
            asset_path="MGS-AGENTS/CRIATIVOS/SHEIN_US_EN/VID/02_TESTING",
            drive_status_readback=drive_readbacks[asset_id],
            last_reconciled_at=stamp,
        )
        history = row.setdefault("test_history", [])
        event = {
            "request_id": state["request_id"],
            **assignment,
            "used_at": stamp,
        }
        if not any(
            isinstance(item, dict)
            and item.get("request_id") == state["request_id"]
            and item.get("ad_id") == assignment["ad_id"]
            for item in history
        ):
            history.append(event)
    atomic_inventory(inventory_rows)
    reread = [
        json.loads(line)
        for line in INVENTORY_PATH.read_text().splitlines()
        if line.strip()
    ]
    reread_by_id = {str(row.get("asset_id")): row for row in reread}
    if any(
        reread_by_id[asset_id].get("status") != "02_TESTING"
        or reread_by_id[asset_id].get("ares_eligible") is not False
        for asset_id in asset_by_id
    ):
        raise SheinRunnerBlocked("inventory_postprocess", "inventory readback failed")
    gate = close_write_gate(str(state["request_id"]))
    return {
        "status": "COMPLETE",
        "credential": credential,
        "service_account": service_account,
        "campaigns": readbacks,
        "assets_finalized": len(asset_by_id),
        "drive_moves_confirmed": len(drive_readbacks),
        "inventory_status": "02_TESTING",
        "write_gate": gate,
        "completed_at_utc": stamp,
    }


def execute_materialized(args: argparse.Namespace) -> dict[str, Any]:
    run_started = time.perf_counter()
    if not args.confirm_execute:
        raise SheinRunnerBlocked("approval", "--confirm-execute is required")
    if args.authorized_by not in AUTHORIZED_EXECUTORS:
        raise SheinRunnerBlocked("authority", "authorized executor is required")
    path = state_path(args.request_id)
    state = load_json(path)
    if state.get("phase") not in {
        "AWAITING_FINAL_APPROVAL",
        "EXECUTION_DEFERRED",
        "RECOVERY_PENDING",
        "POSTPROCESS_PENDING",
    }:
        raise SheinRunnerBlocked("state", f"request is not executable: {state.get('phase')}")
    if args.summary_digest != state.get("summary_digest"):
        raise SheinRunnerBlocked("approval", "summary digest mismatch")
    account = load_json(BASE / "data/ares/meta-ads/accounts/2429758060563333.json")
    account_row = (account.get("accounts") or [{}])[0]
    route = ((account_row.get("runtime_routes") or {}).get("campaign_creation") or {})
    if route.get("write_enabled") is not True:
        raise SheinRunnerBlocked("write_gate", "account-scoped write gate is closed")
    if str(route.get("active_request_id") or "") != str(args.request_id):
        raise SheinRunnerBlocked("write_gate", "account-scoped request id does not match")
    results = list(state.get("engine_results") or [])
    completed_requests = {
        str(row.get("request_id"))
        for row in results
        if row.get("status") in {"COMPLETE_FUTURE_ACTIVE", "COMPLETE_PAUSED"}
    }
    for manifest_path in state.get("manifest_paths") or []:
        manifest = load_json(Path(manifest_path))
        request_id = str(manifest["request_id"])
        if request_id in completed_requests:
            continue
        command = [
            "python3",
            str(ENGINE_CLI),
            "execute",
            "--manifest",
            str(manifest_path),
            "--confirm-execute",
        ]
        proc = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=1800,
            check=False,
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = {"status": "FAILED", "message": "engine returned non-JSON output"}
        results.append(payload)
        state["engine_results"] = results
        if proc.returncode != 0:
            state.update(
                phase="RECOVERY_PENDING",
                automatic_recovery_required=True,
                last_engine_error={
                    "request_id": request_id,
                    "status": payload.get("status"),
                    "message": payload.get("message"),
                },
            )
            atomic_json(path, state)
            raise SheinRunnerBlocked("engine", state["last_engine_error"])
        if payload.get("status") == "PARTIAL_DEFERRED_QUOTA":
            state.update(phase="EXECUTION_DEFERRED", automatic_recovery_required=True)
            atomic_json(path, state)
            return {
                "status": "EXECUTION_DEFERRED",
                "request_id": args.request_id,
                "engine_results": results,
            }
        if payload.get("status") not in {"COMPLETE_FUTURE_ACTIVE", "COMPLETE_PAUSED"}:
            state.update(phase="RECOVERY_PENDING", automatic_recovery_required=True)
            atomic_json(path, state)
            raise SheinRunnerBlocked("engine", payload)
    state.update(
        phase="POSTPROCESS_PENDING",
        automatic_recovery_required=False,
        engine_results=results,
        completed_engine_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    atomic_json(path, state)
    started = time.perf_counter()
    try:
        postprocess = finalize_materialized(state)
    except Exception as exc:
        state.update(
            phase="POSTPROCESS_PENDING",
            automatic_recovery_required=True,
            postprocess_error={
                "type": type(exc).__name__,
                "message": str(exc)[:500],
            },
        )
        atomic_json(path, state)
        if isinstance(exc, SheinRunnerBlocked):
            raise
        raise SheinRunnerBlocked("postprocess", state["postprocess_error"]) from exc
    state.pop("postprocess_error", None)
    state.update(
        phase="COMPLETE",
        automatic_recovery_required=False,
        postprocess=postprocess,
        completed_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    state.setdefault("timings", {})["postprocess_duration_ms"] = round(
        (time.perf_counter() - started) * 1000, 3
    )
    state["timings"]["execution_run_duration_ms"] = round(
        (time.perf_counter() - run_started) * 1000, 3
    )
    atomic_json(path, state)
    atomic_json(AUDIT_ROOT / f"{safe_request_id(args.request_id)}-final.json", state)
    return {
        "status": "COMPLETE",
        "request_id": args.request_id,
        "campaign_count": len(
            {
                str(row.get("request_id"))
                for row in results
                if row.get("status") in {"COMPLETE_FUTURE_ACTIVE", "COMPLETE_PAUSED"}
            }
        ),
        "postprocess": postprocess,
        "timings": state.get("timings") or {},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    smoke = sub.add_parser("offline-smoke")
    smoke.add_argument("--output", type=Path)
    materialize = sub.add_parser("materialize")
    materialize.add_argument("--input", type=Path, required=True)
    materialize.add_argument("--output-dir", type=Path, required=True)
    materialize.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    materialize.add_argument("--config", type=Path, default=CONFIG_PATH)
    prepare_live = sub.add_parser("prepare-live")
    prepare_live.add_argument("--input", type=Path, required=True)
    prepare_live.add_argument("--output-dir", type=Path, required=True)
    status = sub.add_parser("status")
    status.add_argument("--request-id", required=True)
    execute = sub.add_parser("execute")
    execute.add_argument("--request-id", required=True)
    execute.add_argument("--summary-digest", required=True)
    execute.add_argument("--authorized-by", required=True)
    execute.add_argument("--confirm-execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "offline-smoke":
            result = offline_smoke(args.output)
        elif args.command == "materialize":
            result = materialize_resolved(
                load_json(args.input),
                args.output_dir,
                registry_path=args.registry,
                config_path=args.config,
            )
        elif args.command == "prepare-live":
            result = prepare_live_request(load_json(args.input), args.output_dir)
        elif args.command == "status":
            result = load_json(state_path(args.request_id))
        else:
            result = execute_materialized(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (SheinRunnerBlocked, KeyError, ValueError) as exc:
        if isinstance(exc, SheinRunnerBlocked):
            stage, detail = exc.stage, exc.detail
        else:
            stage, detail = "materialization", str(exc)
        print(
            json.dumps(
                {"status": "BLOCKED", "stage": stage, "detail": detail},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
