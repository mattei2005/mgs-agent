from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ares_campaign_v3.creative_lifecycle import classify_campaign_assets


SP = ZoneInfo("America/Sao_Paulo")


def inventory_rows(attempts: int = 1):
    rows = []
    for index in range(1, 4):
        rows.append(
            {
                "asset_id": f"asset-{index}",
                "asset_drive_id": f"drive-{index}",
                "status": "02_TESTING",
                "meta_campaign_id": "campaign-1",
                "meta_ad_id": f"ad-{index}",
                "test_attempt_count": attempts,
            }
        )
    return rows


def policy():
    return {
        "enabled": True,
        "minimum_meaningful_spend_share_pct": 10,
        "winner": {"d4_checkpoint_hour": 16, "d5_checkpoint_hour": 8},
        "retest": {"enabled": True, "max_test_attempts": 2},
    }


def delivery():
    return [
        {"campaign_id": "campaign-1", "ad_id": "ad-1", "spend": "90", "impressions": "900"},
        {"campaign_id": "campaign-1", "ad_id": "ad-2", "spend": "5", "impressions": "50"},
        {"campaign_id": "campaign-1", "ad_id": "ad-3", "spend": "5", "impressions": "50"},
    ]


def test_d3_terminal_negative_rejects_delivered_and_retests_underexposed():
    decisions = classify_campaign_assets(
        inventory=inventory_rows(),
        ad_insights=delivery(),
        campaign={
            "campaign_id": "campaign-1",
            "cycle_day": 3,
            "sb_roi": -12,
            "estimated_roi": -8,
            "status": "PAUSED",
        },
        checkpoint_state={"terminal": True, "terminal_reason": "PARAR D3 ESTIMADO"},
        now_sp=datetime(2026, 8, 24, 8, 5, tzinfo=SP),
        lifecycle_policy=policy(),
        anomaly=False,
    )
    by_asset = {row["asset_id"]: row for row in decisions}
    assert by_asset["asset-1"]["target_status"] == "05_REJECTED"
    assert by_asset["asset-1"]["retest_eligible"] is False
    assert by_asset["asset-2"]["target_status"] == "03_TESTED"
    assert by_asset["asset-2"]["evaluation_status"] == "INCONCLUSIVO_POR_SUBENTREGA"
    assert by_asset["asset-2"]["retest_eligible"] is True
    assert by_asset["asset-3"]["retest_eligible"] is True


def test_d4_positive_stable_marks_only_meaningfully_delivered_winner():
    decisions = classify_campaign_assets(
        inventory=inventory_rows(),
        ad_insights=delivery(),
        campaign={
            "campaign_id": "campaign-1",
            "cycle_day": 4,
            "sb_roi": 22,
            "estimated_roi": 17,
            "status": "ACTIVE",
        },
        checkpoint_state={
            "morning_actual_roi": {"2026-08-24": {"actual_roi": 15}},
            "morning_estimated_roi": {"2026-08-24": {"estimated_roi": 11}},
        },
        now_sp=datetime(2026, 8, 24, 16, 0, tzinfo=SP),
        lifecycle_policy=policy(),
        anomaly=False,
    )
    assert decisions == [
        {
            "asset_id": "asset-1",
            "campaign_id": "campaign-1",
            "ad_id": "ad-1",
            "target_status": "04_WINNERS",
            "evaluation_status": "WINNER_D4_POSITIVO_ESTAVEL",
            "retest_eligible": False,
            "spend": 90.0,
            "spend_share_pct": 90.0,
            "impressions": 900,
            "impression_share_pct": 90.0,
            "test_attempt_count": 1,
        }
    ]


def test_d5_positive_is_winner_fallback_without_d4_snapshot():
    decisions = classify_campaign_assets(
        inventory=inventory_rows(),
        ad_insights=delivery(),
        campaign={
            "campaign_id": "campaign-1",
            "cycle_day": 5,
            "sb_roi": 4,
            "estimated_roi": 2,
            "status": "ACTIVE",
        },
        checkpoint_state={},
        now_sp=datetime(2026, 8, 25, 8, 0, tzinfo=SP),
        lifecycle_policy=policy(),
        anomaly=False,
    )
    assert [row["asset_id"] for row in decisions] == ["asset-1"]
    assert decisions[0]["target_status"] == "04_WINNERS"
    assert decisions[0]["evaluation_status"] == "WINNER_D5_POSITIVO"


def test_anomaly_or_plain_deleted_status_never_classifies():
    base = {
        "campaign_id": "campaign-1",
        "cycle_day": 3,
        "sb_roi": -10,
        "estimated_roi": -10,
        "status": "DELETED",
    }
    assert classify_campaign_assets(
        inventory=inventory_rows(),
        ad_insights=delivery(),
        campaign=base,
        checkpoint_state={},
        now_sp=datetime(2026, 8, 24, 8, 0, tzinfo=SP),
        lifecycle_policy=policy(),
        anomaly=False,
    ) == []
    assert classify_campaign_assets(
        inventory=inventory_rows(),
        ad_insights=delivery(),
        campaign={**base, "status": "PAUSED"},
        checkpoint_state={"terminal": True, "terminal_reason": "PARAR D3 ESTIMADO"},
        now_sp=datetime(2026, 8, 24, 8, 0, tzinfo=SP),
        lifecycle_policy=policy(),
        anomaly=True,
    ) == []


def test_second_underexposed_attempt_is_tested_but_not_retestable():
    decisions = classify_campaign_assets(
        inventory=inventory_rows(attempts=2),
        ad_insights=delivery(),
        campaign={
            "campaign_id": "campaign-1",
            "cycle_day": 3,
            "sb_roi": -12,
            "estimated_roi": -8,
            "status": "PAUSED",
        },
        checkpoint_state={"terminal": True, "terminal_reason": "PARAR D3 ESTIMADO"},
        now_sp=datetime(2026, 8, 24, 8, 5, tzinfo=SP),
        lifecycle_policy=policy(),
        anomaly=False,
    )
    underexposed = [row for row in decisions if row["asset_id"] in {"asset-2", "asset-3"}]
    assert all(row["target_status"] == "03_TESTED" for row in underexposed)
    assert all(row["retest_eligible"] is False for row in underexposed)