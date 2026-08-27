from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path("/root/mgs-agent")
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from ares_campaign_v3.source_selection import (
    SourceSelectionError,
    aggregate_smart_bidding_roi,
    asset_group_vehicle_types,
    authorized_request_vehicle_type,
    expand_source_selections,
    select_best_roi_campaign,
)


def sb_row(campaign_id: str, revenue: float, investment: float, *, name: str) -> dict:
    return {
        "DATE": "2026-08-27",
        "DOMAIN": "creditoparaveiculo",
        "CUSTOMER_ID": "1046241194533786",
        "CAMPAIGN_ID": campaign_id,
        "CAMPAIGN_NAME": name,
        "INVESTIMENT": investment,
        "NET_REVENUE": revenue,
    }


def campaign(campaign_id: str, name: str, status: str = "ACTIVE") -> dict:
    return {"id": campaign_id, "name": name, "configured_status": status}


def test_best_roi_is_selected_only_inside_matching_vehicle_type():
    campaigns = [
        campaign("car-low", "08 - Garagem Brasil - (b01fb13c08) event_Subscribe - MAXVOL"),
        campaign("car-best", "12 - Garagem Brasil - (b01fb13c12) event_Subscribe - MAXVOL"),
        campaign("moto-best", "25 - Garagem Brasil - MOTO - (b01fb13c25) event_Subscribe - MAXVOL"),
    ]
    rows = [
        sb_row("car-low", 120, 100, name=campaigns[0]["name"]),
        sb_row("car-best", 150, 100, name=campaigns[1]["name"]),
        sb_row("moto-best", 300, 100, name=campaigns[2]["name"]),
    ]
    roi = aggregate_smart_bidding_roi(
        rows,
        target_date="2026-08-27",
        account_id="1046241194533786",
        domain="creditoparaveiculo",
    )
    car = select_best_roi_campaign(campaigns, roi, vehicle_type="CARRO")
    moto = select_best_roi_campaign(campaigns, roi, vehicle_type="MOTO")
    assert car["campaign_id"] == "car-best"
    assert car["roi_pct"] == 50.0
    assert moto["campaign_id"] == "moto-best"
    assert moto["roi_pct"] == 200.0


def test_terminal_wrong_strategy_and_zero_investment_are_not_eligible():
    campaigns = [
        campaign("deleted", "12 - MAXVOL", "DELETED"),
        campaign("costcap", "13 - COSTCAP-0.50"),
        campaign("zero", "14 - MAXVOL"),
    ]
    rows = [
        sb_row("deleted", 200, 100, name=campaigns[0]["name"]),
        sb_row("costcap", 300, 100, name=campaigns[1]["name"]),
        sb_row("zero", 0, 0, name=campaigns[2]["name"]),
    ]
    roi = aggregate_smart_bidding_roi(
        rows,
        target_date="2026-08-27",
        account_id="1046241194533786",
        domain="creditoparaveiculo",
    )
    with pytest.raises(SourceSelectionError, match="no non-terminal MAXVOL"):
        select_best_roi_campaign(campaigns, roi, vehicle_type="CARRO")


def test_tie_breaker_prefers_higher_investment_then_stable_id():
    campaigns = [campaign("b", "08 - MAXVOL"), campaign("a", "09 - MAXVOL")]
    rows = [
        sb_row("b", 150, 100, name=campaigns[0]["name"]),
        sb_row("a", 300, 200, name=campaigns[1]["name"]),
    ]
    roi = aggregate_smart_bidding_roi(
        rows,
        target_date="2026-08-27",
        account_id="1046241194533786",
        domain="creditoparaveiculo",
    )
    assert select_best_roi_campaign(campaigns, roi, vehicle_type="CARRO")["campaign_id"] == "a"


def test_asset_groups_cannot_mix_car_and_moto():
    assets = [
        {"canonical_filename": "CAR_BR_BR_VID_CAR_PV_001.mp4"},
        {"canonical_filename": "CAR_BR_BR_VID_MOTO_PV_002.mp4"},
        {"canonical_filename": "CAR_BR_BR_VID_CAR_PV_003.mp4"},
    ]
    with pytest.raises(SourceSelectionError, match="mixes CARRO and MOTO"):
        asset_group_vehicle_types(assets, 1)


def test_request_vehicle_gate_and_snapshot_expansion_are_deterministic():
    operation = {
        "daily_new_campaign_routine": {
            "one_time_override_20260827": {
                "request_id": "req",
                "vehicle_type": "CARRO",
            }
        }
    }
    assert authorized_request_vehicle_type(operation, "req") == "CARRO"
    payload = {
        "campaign_vehicle_types": ["CARRO", "MOTO", "CARRO"],
        "sources_by_vehicle": {
            "CARRO": {"source_campaign_id": "car"},
            "MOTO": {"source_campaign_id": "moto"},
        },
    }
    assert [row["source_campaign_id"] for row in expand_source_selections(payload)] == ["car", "moto", "car"]
