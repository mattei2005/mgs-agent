#!/usr/bin/env python3
"""Meta Ads source mirror diagnostic for MGS/Ares.

Read-only tool: dumps campaign/adset/ad/creative source fields explicitly, builds a
clone-source payload candidate in memory, and diffs source vs payload.

No POST/DELETE/write to Meta is performed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
COMMON_PATH = SCRIPT_DIR / "ares-meta-common.py"
AUDIT_DIR = Path("/root/mgs-agent/data/ares/meta-ads/audit/clone")

READONLY_ROOTS = {
    "id",
    "account_id",
    "created_time",
    "updated_time",
    "effective_status",
    "configured_status",
    "budget_remaining",
    "source_campaign_id",
    "source_adset_id",
    "source_ad_id",
    "issues_info",
    "recommendations",
    "campaign",
    "preview_shareable_link",
    "effective_object_story_id",
    "object_type",
}

WRITABLE_HINTS = {
    "name",
    "objective",
    "buying_type",
    "status",
    "special_ad_categories",
    "special_ad_category_country",
    "bid_strategy",
    "daily_budget",
    "lifetime_budget",
    "spend_cap",
    "start_time",
    "stop_time",
    "billing_event",
    "optimization_goal",
    "optimization_sub_event",
    "destination_type",
    "promoted_object",
    "targeting",
    "attribution_spec",
    "bid_amount",
    "pacing_type",
    "is_dynamic_creative",
    "use_new_app_click",
    "frequency_control_specs",
    "adset_schedule",
    "dsa_beneficiary",
    "dsa_payor",
    "tracking_specs",
    "conversion_specs",
    "creative",
    "object_story_spec",
    "asset_feed_spec",
    "degrees_of_freedom_spec",
    "url_tags",
}

LEGACY_PATTERNS = [
    "standard_enhancements",
    "effective_object_story_id",
    "creative_id",
    "source_",
    "messenger_doc",
]

COMPLIANCE_RE = re.compile(r"(dsa|beneficiary|payor|payer|regulated|special_ad|financ)", re.I)

CAMPAIGN_FIELDS = list(dict.fromkeys("""
id name objective buying_type status configured_status effective_status
special_ad_categories special_ad_category_country bid_strategy daily_budget
lifetime_budget budget_remaining spend_cap start_time stop_time created_time
updated_time source_campaign_id smart_promotion_type is_skadnetwork_attribution
can_use_spend_cap boosted_object_id brand_lift_studies budget_rebalance_flag
topline_id pacing_type promoted_object adlabels issues_info recommendations
""".split()))
# Some fields are intentionally probed separately because unsupported fields should not
# break the whole dump.
CAMPAIGN_PROBE_FIELDS = CAMPAIGN_FIELDS + [
    "dsa_beneficiary",
    "dsa_payor",
    "regulated_categories",
    "regional_regulated_categories",
    "authorization_category",
]

ADSET_FIELDS = list(dict.fromkeys("""
id name account_id campaign_id campaign configured_status status effective_status
created_time updated_time start_time end_time billing_event optimization_goal
optimization_sub_event destination_type promoted_object targeting attribution_spec
bid_strategy bid_amount daily_budget lifetime_budget budget_remaining pacing_type
is_dynamic_creative use_new_app_click source_adset_id frequency_control_specs
adset_schedule rf_prediction_id dsa_beneficiary dsa_payor dsa_beneficiary_id
dsa_payor_id beneficiary payor payer advertiser regulated_categories
regional_regulated_categories special_ad_categories special_ad_category_country
issues_info recommendations targeting_optimization_types instagram_actor_id page_id
""".split()))

AD_FIELDS_COMPOSITE = (
    "id,name,account_id,campaign_id,adset_id,configured_status,status,effective_status,"
    "created_time,updated_time,creative{id,name,object_story_spec,asset_feed_spec,"
    "effective_object_story_id,object_type,url_tags,degrees_of_freedom_spec},"
    "tracking_specs,conversion_specs,bid_amount,bid_type,source_ad_id,"
    "issues_info,recommendations,preview_shareable_link"
)
AD_PROBE_FIELDS = [
    "tracking_specs",
    "conversion_specs",
    "source_ad_id",
    "issues_info",
    "recommendations",
    "dsa_beneficiary",
    "dsa_payor",
]


def load_common():
    spec = importlib.util.spec_from_file_location("ares_meta_common", COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {COMMON_PATH}")
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    common.GRAPH_VERSION = os.environ.get("ARES_META_GRAPH_VERSION", "v25.0")
    return common


def safe_meta(common, payload: Any) -> Any:
    if isinstance(payload, dict):
        return common.safe_meta_error(payload)
    return payload


def graph_get(common, token: str, path: str, fields: str | list[str] | None = None, extra: dict[str, Any] | None = None):
    params = dict(extra or {})
    if fields:
        params["fields"] = ",".join(fields) if isinstance(fields, list) else fields
    status, payload, _ = common.graph_get(path, token, params)
    return status, payload


def try_fields(common, token: str, object_id: str, fields: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    got: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []
    unsupported: list[str] = []
    for field in fields:
        status, payload = graph_get(common, token, object_id, [field])
        if status == 200:
            if isinstance(payload, dict):
                if field in payload:
                    got[field] = payload[field]
                else:
                    # Some fields expand into child keys; keep whatever Graph returned.
                    got.update({k: v for k, v in payload.items() if k != "id"})
        else:
            err = safe_meta(common, payload)
            errors.append({"field": field, "error": err})
            if isinstance(err, dict) and err.get("code") in (100, 2500):
                unsupported.append(field)
    status, payload = graph_get(common, token, object_id, ["id"])
    if status == 200 and isinstance(payload, dict):
        got["id"] = payload.get("id")
    return got, errors, unsupported


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, val in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(val, dict):
                out.update(flatten(val, path))
            else:
                out[path] = val
    else:
        out[prefix] = value
    return out


def classify_field(field: str) -> str:
    root = field.split(".")[0]
    low = field.lower()
    if root in READONLY_ROOTS or field in READONLY_ROOTS:
        return "READ-ONLY/derivado"
    if any(pat in low for pat in LEGACY_PATTERNS):
        return "LEGADO/obsoleto"
    if COMPLIANCE_RE.search(field):
        return "gravável provável/compliance"
    if root in WRITABLE_HINTS:
        return "gravável provável"
    return "desconhecido"


def diff(source: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    sf = flatten(source)
    pf = flatten(payload)
    rows: list[dict[str, Any]] = []
    for field in sorted(set(sf) | set(pf)):
        source_has = field in sf
        payload_has = field in pf
        if source_has and payload_has and sf[field] == pf[field]:
            status = "IGUAL"
        elif source_has and not payload_has:
            status = "SÓ NA SOURCE"
        elif payload_has and not source_has:
            status = "SÓ NO PAYLOAD"
        else:
            status = "VALOR DIFERENTE"
        rows.append({
            "field": field,
            "status": status,
            "class": classify_field(field),
            "source": sf.get(field),
            "payload": pf.get(field),
        })
    return rows


def priority(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if row["status"] in ("SÓ NA SOURCE", "VALOR DIFERENTE")
        and row["class"].startswith("gravável")
    ]


def text_from_asset_feed(asset_feed_spec: dict[str, Any], key: str, fallback: str) -> str:
    vals = asset_feed_spec.get(key) or []
    if vals and isinstance(vals[0], dict):
        return vals[0].get("text") or vals[0].get("name") or fallback
    return fallback


def resolve_asset(creative: dict[str, Any]) -> dict[str, Any] | None:
    afs = creative.get("asset_feed_spec") or {}
    for video in afs.get("videos") or []:
        if isinstance(video, dict) and video.get("video_id"):
            return {"kind": "video", "video_id": video.get("video_id"), "thumbnail_url": video.get("thumbnail_url")}
    for image in afs.get("images") or []:
        if isinstance(image, dict) and image.get("hash"):
            return {"kind": "image", "image_hash": image.get("hash")}
    if creative.get("video_id"):
        return {"kind": "video", "video_id": creative["video_id"]}
    if creative.get("image_hash"):
        return {"kind": "image", "image_hash": creative["image_hash"]}
    return None


def build_payloads(args: argparse.Namespace, campaign: dict[str, Any], adsets: list[dict[str, Any]], ads: list[dict[str, Any]]) -> dict[str, Any]:
    tz = ZoneInfo(args.timezone)
    start_local = (datetime.now(timezone.utc).astimezone(tz) + timedelta(days=args.start_days_ahead)).replace(
        hour=args.start_hour, minute=0, second=0, microsecond=0
    )
    start_utc_z = start_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_tag = start_local.strftime("%Y%m%d")

    source_name = campaign.get("name") or f"campaign_{args.source_campaign_id}"
    parts = [p.strip() for p in source_name.split(" - ")]
    prefix = " - ".join(parts[:4]) if len(parts) >= 4 else source_name

    campaign_payload = {
        "name": f"{prefix} - RPL - {date_tag} - DRYRUN",
        "objective": campaign.get("objective"),
        "buying_type": campaign.get("buying_type") or "AUCTION",
        "status": "PAUSED",
        "daily_budget": str(int(round(args.daily_budget_usd * 100))),
        "bid_strategy": campaign.get("bid_strategy"),
        "special_ad_categories": campaign.get("special_ad_categories") or [],
        "special_ad_category_country": campaign.get("special_ad_category_country") or [],
        "start_time": start_utc_z,
    }
    if campaign.get("pacing_type"):
        campaign_payload["pacing_type"] = campaign.get("pacing_type")

    adset_payloads = []
    source_adset_map = {a.get("id"): a for a in adsets}
    for src in adsets:
        payload = {
            "name": f"{src.get('name', 'Adset')} - RPL {date_tag}",
            "campaign_id": "<NEW_CAMPAIGN_ID>",
            "status": "PAUSED",
            "billing_event": src.get("billing_event"),
            "optimization_goal": src.get("optimization_goal"),
            "optimization_sub_event": src.get("optimization_sub_event"),
            "destination_type": src.get("destination_type"),
            "targeting": src.get("targeting") or {},
            "promoted_object": src.get("promoted_object") or {},
            "attribution_spec": src.get("attribution_spec"),
            "start_time": start_utc_z,
            "bid_strategy": src.get("bid_strategy"),
            "bid_amount": src.get("bid_amount"),
            "is_dynamic_creative": src.get("is_dynamic_creative"),
            "use_new_app_click": src.get("use_new_app_click"),
        }
        # EU/financial compliance fields: copy exact API strings if present.
        if src.get("dsa_beneficiary") is not None:
            payload["dsa_beneficiary"] = src.get("dsa_beneficiary")
        if src.get("dsa_payor") is not None:
            payload["dsa_payor"] = src.get("dsa_payor")
        # Include only if present and likely writable; avoid derived/source IDs.
        for opt in ("pacing_type", "frequency_control_specs", "adset_schedule"):
            if src.get(opt) is not None:
                payload[opt] = src.get(opt)
        adset_payloads.append(payload)

    selected_ads = []
    for ad in ads:
        creative = ad.get("creative") or {}
        asset = resolve_asset(creative)
        if asset:
            selected_ads.append({"ad": ad, "creative": creative, "asset": asset})
        if len(selected_ads) == args.ads_count:
            break

    creative_payloads = []
    ad_payloads = []
    selected_assets = []
    for idx, item in enumerate(selected_ads, 1):
        ad = item["ad"]
        creative = item["creative"]
        asset = item["asset"]
        afs = creative.get("asset_feed_spec") or {}
        body = text_from_asset_feed(afs, "bodies", "Hola, toca el botón para continuar.")
        title = text_from_asset_feed(afs, "titles", "TARJETA DE CRÉDITO DISPONIBLE ✅")
        cta = (afs.get("call_to_action_types") or ["APPLY_NOW"])[0]
        src_adset = source_adset_map.get(ad.get("adset_id"), {})
        page_id = (src_adset.get("promoted_object") or {}).get("page_id") or (adsets[0].get("promoted_object") or {}).get("page_id")
        object_story_spec = {"page_id": page_id}
        if asset["kind"] == "video":
            video_data = {
                "video_id": asset["video_id"],
                "message": body,
                "title": title,
                "call_to_action": {"type": cta, "value": {"app_destination": "MESSENGER"}},
            }
            if asset.get("thumbnail_url"):
                video_data["image_url"] = asset["thumbnail_url"]
            object_story_spec["video_data"] = video_data
        else:
            object_story_spec["link_data"] = {
                "image_hash": asset["image_hash"],
                "message": body,
                "name": title,
                "call_to_action": {"type": cta, "value": {"app_destination": "MESSENGER"}},
            }
        creative_payloads.append({
            "name": f"RPL clone-source {date_tag} {idx:02d}",
            "object_story_spec": object_story_spec,
            "page_welcome_message": {"is_user_editing": True},
            "degrees_of_freedom_spec": {"creative_features_spec": {}},
        })
        ad_payload = {
            "name": f"Ad RPL {idx:02d} - clone-source {asset['kind']}",
            "adset_id": f"<NEW_ADSET_ID_FOR_SOURCE_ADSET_{ad.get('adset_id')}>",
            "status": "PAUSED",
            "creative": {"creative_id": f"<NEW_CREATIVE_ID_{idx}>"},
        }
        # Source ads often carry tracking/conversion specs. Keep in candidate for review;
        # executor can decide if Meta accepts them at POST /ads checkpoint.
        if ad.get("tracking_specs") is not None:
            ad_payload["tracking_specs"] = ad.get("tracking_specs")
        if ad.get("conversion_specs") is not None:
            ad_payload["conversion_specs"] = ad.get("conversion_specs")
        ad_payloads.append(ad_payload)
        selected_assets.append({
            "source_ad_id": ad.get("id"),
            "source_ad_name": ad.get("name"),
            "source_adset_id": ad.get("adset_id"),
            "source_creative_id": creative.get("id"),
            "asset": asset,
        })

    return {
        "api_base": f"https://graph.facebook.com/{os.environ.get('ARES_META_GRAPH_VERSION', 'v25.0')}",
        "start_time": {"timezone": args.timezone, "local": start_local.isoformat(), "utc_z": start_utc_z},
        "selected_assets": selected_assets,
        "would_post": {
            f"act_{args.account_id}/campaigns": campaign_payload,
            f"act_{args.account_id}/adsets": adset_payloads,
            f"act_{args.account_id}/adcreatives": creative_payloads,
            f"act_{args.account_id}/ads": ad_payloads,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Meta source mirror/diff for clone-source")
    parser.add_argument("--account-id", default="1356770869843984")
    parser.add_argument("--source-campaign-id", required=True)
    parser.add_argument("--source-adset-id", action="append", help="Optional source adset id(s). Defaults to all campaign adsets.")
    parser.add_argument("--source-ad-id", action="append", help="Optional source ad id(s). Defaults to campaign ads in API order.")
    parser.add_argument("--ads-count", type=int, default=3)
    parser.add_argument("--daily-budget-usd", type=float, default=25.0)
    parser.add_argument("--timezone", default="Europe/Madrid")
    parser.add_argument("--start-days-ahead", type=int, default=1)
    parser.add_argument("--start-hour", type=int, default=1)
    parser.add_argument("--output", help="Audit JSON path. Defaults under clone audit dir.")
    args = parser.parse_args()

    os.environ.setdefault("ARES_META_GRAPH_VERSION", "v25.0")
    common = load_common()
    token, token_field = common.get_token_from_1password()

    campaign, campaign_errors, campaign_unsupported = try_fields(common, token, args.source_campaign_id, CAMPAIGN_PROBE_FIELDS)

    if args.source_adset_id:
        adset_ids = args.source_adset_id
    else:
        status, payload = graph_get(common, token, f"{args.source_campaign_id}/adsets", "id,name", {"limit": 100})
        if status != 200:
            raise RuntimeError(json.dumps({"adsets_status": status, "error": safe_meta(common, payload)}, ensure_ascii=False))
        adset_ids = [row["id"] for row in payload.get("data", [])]

    adsets = []
    adset_errors = {}
    adset_unsupported = {}
    for adset_id in adset_ids:
        adset, errors, unsupported = try_fields(common, token, adset_id, ADSET_FIELDS)
        adsets.append(adset)
        adset_errors[adset_id] = errors
        adset_unsupported[adset_id] = unsupported

    if args.source_ad_id:
        ad_ids = args.source_ad_id
    else:
        status, payload = graph_get(common, token, f"{args.source_campaign_id}/ads", "id,name,status,effective_status,adset_id", {"limit": 100})
        if status != 200:
            raise RuntimeError(json.dumps({"ads_status": status, "error": safe_meta(common, payload)}, ensure_ascii=False))
        ad_ids = [row["id"] for row in payload.get("data", [])][: args.ads_count]

    ads = []
    ad_errors = {}
    ad_unsupported = {}
    for ad_id in ad_ids:
        status, ad = graph_get(common, token, ad_id, AD_FIELDS_COMPOSITE)
        if status != 200:
            ad = {"id": ad_id, "_composite_error": safe_meta(common, ad)}
        extra, errors, unsupported = try_fields(common, token, ad_id, AD_PROBE_FIELDS)
        if isinstance(ad, dict):
            ad.update(extra)
        ads.append(ad)
        ad_errors[ad_id] = errors
        ad_unsupported[ad_id] = unsupported

    payloads = build_payloads(args, campaign, adsets, ads)
    campaign_payload = payloads["would_post"][f"act_{args.account_id}/campaigns"]
    adset_payloads = payloads["would_post"][f"act_{args.account_id}/adsets"]
    ad_payloads = payloads["would_post"][f"act_{args.account_id}/ads"]
    creative_payloads = payloads["would_post"][f"act_{args.account_id}/adcreatives"]

    campaign_diff = diff(campaign, campaign_payload)
    adset_diffs = []
    for src, pay in zip(adsets, adset_payloads):
        adset_diffs.append({"source_adset_id": src.get("id"), "diff": diff(src, pay)})
    ad_diffs = []
    for src, ad_pay, cr_pay in zip(ads, ad_payloads, creative_payloads):
        ad_diffs.append({"source_ad_id": src.get("id"), "diff": diff(src, {"ad": ad_pay, "creative": cr_pay})})

    compliance_fields = {
        "campaign": {k: v for k, v in flatten(campaign).items() if COMPLIANCE_RE.search(k)},
        "adsets": {src.get("id"): {k: v for k, v in flatten(src).items() if COMPLIANCE_RE.search(k)} for src in adsets},
        "ads": {src.get("id"): {k: v for k, v in flatten(src).items() if COMPLIANCE_RE.search(k)} for src in ads},
    }

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "GET_ONLY_SOURCE_MIRROR_NO_WRITES",
        "graph_version": os.environ.get("ARES_META_GRAPH_VERSION", "v25.0"),
        "token_field": token_field,
        "token_len": len(token),
        "source_ids": {"campaign": args.source_campaign_id, "adsets": adset_ids, "ads": ad_ids},
        "source_raw": {"campaign": campaign, "adsets": adsets, "ads": ads},
        "unsupported_fields": {"campaign": campaign_unsupported, "adsets": adset_unsupported, "ads": ad_unsupported},
        "field_errors": {"campaign": campaign_errors, "adsets": adset_errors, "ads": ad_errors},
        "payloads": payloads,
        "diffs": {"campaign": campaign_diff, "adsets": adset_diffs, "ads": ad_diffs},
        "priority_writable_diffs": {
            "campaign": priority(campaign_diff),
            "adsets": [{"source_adset_id": item["source_adset_id"], "rows": priority(item["diff"])} for item in adset_diffs],
            "ads": [{"source_ad_id": item["source_ad_id"], "rows": priority(item["diff"])} for item in ad_diffs],
        },
        "source_compliance_fields": compliance_fields,
        "safety": {
            "no_meta_post_performed": True,
            "status_in_payloads": "PAUSED",
            "api_base": payloads["api_base"],
        },
    }

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.output) if args.output else AUDIT_DIR / f"source-mirror-{args.source_campaign_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    summary = {
        "audit": str(out),
        "mode": result["mode"],
        "source_ids": result["source_ids"],
        "source_compliance_fields": result["source_compliance_fields"],
        "selected_assets": payloads["selected_assets"],
        "start_time": payloads["start_time"],
        "priority_writable_diffs": result["priority_writable_diffs"],
        "unsupported_fields": result["unsupported_fields"],
        "safety": result["safety"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
