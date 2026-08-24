from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Callable


def _number(value: Any) -> Decimal:
    try:
        parsed = Decimal(str(value or 0))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")
    return parsed if parsed.is_finite() else Decimal("0")


def _pct(part: Decimal, total: Decimal) -> float:
    if total <= 0:
        return 0.0
    return float((part * Decimal("100") / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _asset_campaign_ids(row: dict[str, Any]) -> set[str]:
    ids = {str(row.get("meta_campaign_id") or "")}
    ids.update(str(item.get("campaign_id") or item.get("meta_campaign_id") or "") for item in row.get("test_history") or [])
    return {value for value in ids if value}


def _asset_ad_id(row: dict[str, Any], campaign_id: str) -> str:
    for item in reversed(row.get("test_history") or []):
        item_campaign = str(item.get("campaign_id") or item.get("meta_campaign_id") or "")
        if item_campaign == campaign_id and item.get("ad_id"):
            return str(item["ad_id"])
    if str(row.get("meta_campaign_id") or "") == campaign_id:
        return str(row.get("meta_ad_id") or "")
    return ""


def _positive(value: Any) -> bool:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return False
    return parsed.is_finite() and parsed > 0


def _negative(value: Any) -> bool:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return False
    return parsed.is_finite() and parsed < 0


def _classification_event(
    campaign: dict[str, Any],
    checkpoint_state: dict[str, Any],
    now_sp: datetime,
    policy: dict[str, Any],
) -> str | None:
    cycle_day = int(campaign.get("cycle_day") or 0)
    actual = campaign.get("sb_roi")
    estimated = campaign.get("estimated_roi")
    status = str(campaign.get("status") or "").upper()

    terminal_d3 = (
        cycle_day == 3
        and status == "PAUSED"
        and checkpoint_state.get("terminal") is True
        and str(checkpoint_state.get("terminal_reason") or "") == "PARAR D3 ESTIMADO"
        and _negative(actual)
        and _negative(estimated)
    )
    if terminal_d3:
        return "D3_REJECTED"

    winner = policy.get("winner") or {}
    if cycle_day == 4 and now_sp.hour == int(winner.get("d4_checkpoint_hour") or 16):
        date_key = now_sp.date().isoformat()
        morning_actual = ((checkpoint_state.get("morning_actual_roi") or {}).get(date_key) or {}).get("actual_roi")
        morning_estimated = ((checkpoint_state.get("morning_estimated_roi") or {}).get(date_key) or {}).get("estimated_roi")
        if all(_positive(value) for value in (morning_actual, morning_estimated, actual, estimated)):
            return "D4_WINNER"
    if cycle_day >= 5 and now_sp.hour == int(winner.get("d5_checkpoint_hour") or 8):
        if _positive(actual) and _positive(estimated):
            return "D5_WINNER"
    return None


def classify_campaign_assets(
    *,
    inventory: list[dict[str, Any]],
    ad_insights: list[dict[str, Any]],
    campaign: dict[str, Any],
    checkpoint_state: dict[str, Any],
    now_sp: datetime,
    lifecycle_policy: dict[str, Any],
    anomaly: bool,
) -> list[dict[str, Any]]:
    """Classify one campaign's assets without performing external writes.

    Plain Meta DELETED/PAUSED state never implies rejection. D3 rejection requires
    the persisted terminal performance reason. D4/D5 winners require both real and
    estimated ROI to be positive. Underexposed assets are only released for retest
    after a terminal D3 campaign; underexposed assets in a live winner remain TESTING.
    """
    if lifecycle_policy.get("enabled") is not True or anomaly:
        return []
    campaign_id = str(campaign.get("campaign_id") or campaign.get("id") or "")
    if not campaign_id:
        return []
    event = _classification_event(campaign, checkpoint_state, now_sp, lifecycle_policy)
    if event is None:
        return []

    by_ad: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"spend": Decimal("0"), "impressions": Decimal("0")})
    for insight in ad_insights:
        if str(insight.get("campaign_id") or "") != campaign_id:
            continue
        ad_id = str(insight.get("ad_id") or "")
        if not ad_id:
            continue
        by_ad[ad_id]["spend"] += _number(insight.get("spend"))
        by_ad[ad_id]["impressions"] += _number(insight.get("impressions"))
    total_spend = sum((item["spend"] for item in by_ad.values()), Decimal("0"))
    total_impressions = sum((item["impressions"] for item in by_ad.values()), Decimal("0"))
    if total_spend <= 0:
        return []

    threshold = _number(lifecycle_policy.get("minimum_meaningful_spend_share_pct") or 10)
    retest_policy = lifecycle_policy.get("retest") or {}
    max_attempts = int(retest_policy.get("max_test_attempts") or 2)
    retest_enabled = retest_policy.get("enabled") is True
    decisions: list[dict[str, Any]] = []
    for row in inventory:
        if str(row.get("status") or "") != "02_TESTING" or campaign_id not in _asset_campaign_ids(row):
            continue
        ad_id = _asset_ad_id(row, campaign_id)
        if not ad_id:
            continue
        metrics = by_ad.get(ad_id) or {"spend": Decimal("0"), "impressions": Decimal("0")}
        spend_share = _pct(metrics["spend"], total_spend)
        impression_share = _pct(metrics["impressions"], total_impressions)
        meaningful = Decimal(str(spend_share)) >= threshold
        attempts = max(1, int(row.get("test_attempt_count") or 1))
        base = {
            "asset_id": str(row.get("asset_id") or ""),
            "campaign_id": campaign_id,
            "ad_id": ad_id,
            "spend": float(metrics["spend"]),
            "spend_share_pct": spend_share,
            "impressions": int(metrics["impressions"]),
            "impression_share_pct": impression_share,
            "test_attempt_count": attempts,
        }
        if event == "D3_REJECTED":
            if meaningful:
                decisions.append({
                    **base,
                    "target_status": "05_REJECTED",
                    "evaluation_status": "REJECTED_D3_ROI_REAL_E_ESTIMADO_NEGATIVOS",
                    "retest_eligible": False,
                })
            else:
                decisions.append({
                    **base,
                    "target_status": "03_TESTED",
                    "evaluation_status": "INCONCLUSIVO_POR_SUBENTREGA",
                    "retest_eligible": bool(retest_enabled and attempts < max_attempts),
                })
        elif meaningful:
            decisions.append({
                **base,
                "target_status": "04_WINNERS",
                "evaluation_status": "WINNER_D4_POSITIVO_ESTAVEL" if event == "D4_WINNER" else "WINNER_D5_POSITIVO",
                "retest_eligible": False,
            })
    decisions.sort(key=lambda item: item["asset_id"])
    return decisions


def apply_inventory_decisions(
    inventory: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    *,
    move: Callable[[dict[str, Any], str], dict[str, Any]],
    now_sp: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply Drive moves through an injected readback function, then mutate rows."""
    by_asset = {str(row.get("asset_id") or ""): row for row in inventory}
    applied: list[dict[str, Any]] = []
    for decision in decisions:
        asset_id = str(decision.get("asset_id") or "")
        row = by_asset.get(asset_id)
        if not row:
            raise RuntimeError(f"creative lifecycle inventory asset missing: {asset_id}")
        target = str(decision.get("target_status") or "")
        readback = move(row, target)
        row.update(
            status=target,
            evaluation_status=decision.get("evaluation_status"),
            retest_eligible=bool(decision.get("retest_eligible")),
            ares_eligible=bool(target == "03_TESTED" and decision.get("retest_eligible")),
            reservation_status=("LIBERADO_PARA_RETESTE" if target == "03_TESTED" and decision.get("retest_eligible") else "CLASSIFICADO_POR_PERFORMANCE"),
            used_by=(None if target == "03_TESTED" and decision.get("retest_eligible") else "ARES"),
            last_reconciled_at=now_sp.isoformat(),
            drive_status_readback=readback,
        )
        row.setdefault("classification_history", []).append({
            **decision,
            "classified_at_sp": now_sp.isoformat(),
            "drive_readback": readback,
        })
        applied.append({**decision, "drive_readback": readback})
    return inventory, applied
