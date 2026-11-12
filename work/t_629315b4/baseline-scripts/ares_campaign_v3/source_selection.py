from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

TERMINAL_STATUSES = {"DELETED", "ARCHIVED"}
MOTO_TOKEN = re.compile(r"(?:^|[^A-Z0-9])MOTO(?:$|[^A-Z0-9])", re.IGNORECASE)
AD_SLOT_TOKEN = re.compile(r"(?:^|[^A-Z0-9])AD\s*0*([1-3])(?:$|[^A-Z0-9])", re.IGNORECASE)
MAXVOL_TOKEN = re.compile(r"(?:^|[^A-Z0-9])MAXVOL(?:$|[^A-Z0-9])", re.IGNORECASE)


class SourceSelectionError(ValueError):
    pass


def vehicle_type_from_text(value: Any) -> str:
    return "MOTO" if MOTO_TOKEN.search(str(value or "")) else "CARRO"


def canonical_vehicle_type(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"CAR", "CARRO"}:
        return "CARRO"
    if text == "MOTO":
        return "MOTO"
    raise SourceSelectionError(f"unsupported vehicle type: {text or 'empty'}")


def asset_group_vehicle_types(asset_refs: list[dict[str, Any]], campaigns: int) -> list[str]:
    if campaigns < 1 or len(asset_refs) != campaigns * 3:
        raise SourceSelectionError("source selection requires exactly three assets per campaign")
    result: list[str] = []
    for index in range(campaigns):
        group = asset_refs[index * 3:(index + 1) * 3]
        types = {vehicle_type_from_text(row.get("canonical_filename")) for row in group}
        if len(types) != 1:
            raise SourceSelectionError(f"campaign {index + 1} mixes CARRO and MOTO assets")
        result.append(next(iter(types)))
    return result


def authorized_request_vehicle_type(operation: dict[str, Any], request_id: str) -> str | None:
    routine = operation.get("daily_new_campaign_routine") or {}
    for key, value in routine.items():
        if not str(key).startswith("one_time_override_") or not isinstance(value, dict):
            continue
        if str(value.get("request_id") or "") != str(request_id):
            continue
        raw = value.get("vehicle_type") or value.get("campaign_name_tag")
        return canonical_vehicle_type(raw) if raw else None
    return None


def expand_source_selections(payload: dict[str, Any]) -> list[dict[str, Any]]:
    vehicle_types = payload.get("campaign_vehicle_types") or []
    sources = payload.get("sources_by_vehicle") or {}
    result: list[dict[str, Any]] = []
    for value in vehicle_types:
        vehicle_type = canonical_vehicle_type(value)
        source = sources.get(vehicle_type)
        if not isinstance(source, dict):
            raise SourceSelectionError(f"source snapshot missing {vehicle_type}")
        result.append(source)
    if not result:
        raise SourceSelectionError("source snapshot has no campaign mappings")
    return result


def select_canonical_source_ads(ads: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible = [
        row
        for row in ads
        if str(row.get("configured_status") or row.get("status") or "").upper() not in TERMINAL_STATUSES
    ]
    slots: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        match = AD_SLOT_TOKEN.search(str(row.get("name") or ""))
        if match:
            slots[int(match.group(1))].append(row)
    if set(slots) == {1, 2, 3} and all(len(slots[index]) == 1 for index in (1, 2, 3)):
        selected = [slots[index][0] for index in (1, 2, 3)]
    else:
        active = [
            row
            for row in eligible
            if str(row.get("configured_status") or row.get("status") or "").upper() == "ACTIVE"
        ]
        if len(active) == 3:
            selected = sorted(active, key=lambda row: (str(row.get("name") or ""), str(row.get("id") or "")))
        elif len(eligible) == 3:
            selected = sorted(eligible, key=lambda row: (str(row.get("name") or ""), str(row.get("id") or "")))
        else:
            raise SourceSelectionError(
                "ROI-winning source does not expose one unambiguous AD01/AD02/AD03 set"
            )
    selected_ids = {str(row.get("id") or "") for row in selected}
    ignored = [row for row in eligible if str(row.get("id") or "") not in selected_ids]
    return selected, ignored


def aggregate_smart_bidding_roi(
    rows: list[dict[str, Any]],
    *,
    target_date: str,
    account_id: str,
    domain: str,
) -> dict[str, dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"investment_usd": 0.0, "net_revenue_usd": 0.0, "row_count": 0, "campaign_name": ""}
    )
    for row in rows:
        if str(row.get("DATE") or "")[:10] != target_date:
            continue
        if str(row.get("DOMAIN") or "").strip().lower() != domain.lower():
            continue
        if str(row.get("CUSTOMER_ID") or "").removeprefix("act_") != str(account_id).removeprefix("act_"):
            continue
        campaign_id = str(row.get("CAMPAIGN_ID") or "").strip()
        if not campaign_id:
            continue
        item = totals[campaign_id]
        try:
            item["investment_usd"] += float(row.get("INVESTIMENT") or 0)
            item["net_revenue_usd"] += float(row.get("NET_REVENUE") or 0)
        except (TypeError, ValueError) as exc:
            raise SourceSelectionError(f"invalid Smart Bidding numeric value for campaign {campaign_id}") from exc
        item["row_count"] += 1
        if row.get("CAMPAIGN_NAME"):
            item["campaign_name"] = str(row["CAMPAIGN_NAME"])
    result: dict[str, dict[str, Any]] = {}
    for campaign_id, item in totals.items():
        investment = float(item["investment_usd"])
        if investment <= 0:
            continue
        revenue = float(item["net_revenue_usd"])
        result[campaign_id] = {
            **item,
            "campaign_id": campaign_id,
            "roi_pct": (revenue - investment) * 100.0 / investment,
            "target_date": target_date,
            "currency": "USD",
            "metric": "Smart Bidding NET_REVENUE with revenue share",
            "formula": "(NET_REVENUE - INVESTIMENT) * 100 / INVESTIMENT",
        }
    return result


def select_best_roi_campaign(
    meta_campaigns: list[dict[str, Any]],
    roi_by_campaign: dict[str, dict[str, Any]],
    *,
    vehicle_type: str,
) -> dict[str, Any]:
    wanted = canonical_vehicle_type(vehicle_type)
    candidates: list[dict[str, Any]] = []
    for campaign in meta_campaigns:
        campaign_id = str(campaign.get("id") or "").strip()
        roi = roi_by_campaign.get(campaign_id)
        name = str(campaign.get("name") or "")
        status = str(campaign.get("configured_status") or campaign.get("status") or "").upper()
        if not campaign_id or roi is None or status in TERMINAL_STATUSES:
            continue
        if vehicle_type_from_text(name) != wanted:
            continue
        if not MAXVOL_TOKEN.search(name):
            continue
        candidates.append({
            "campaign_id": campaign_id,
            "campaign_name": name,
            "status": status,
            "vehicle_type": wanted,
            **roi,
        })
    if not candidates:
        raise SourceSelectionError(f"no non-terminal MAXVOL campaign with valid Smart Bidding ROI for {wanted}")
    candidates.sort(
        key=lambda row: (
            -float(row["roi_pct"]),
            -float(row["investment_usd"]),
            str(row["campaign_id"]),
        )
    )
    winner = dict(candidates[0])
    winner["candidate_count"] = len(candidates)
    winner["tie_breaker"] = "roi_pct desc, investment_usd desc, campaign_id asc"
    return winner
