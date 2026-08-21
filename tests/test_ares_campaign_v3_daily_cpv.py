from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path("/root/mgs-agent")
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from ares_campaign_v3.daily_cpv import (
    DailyPaths,
    DailyBlocked,
    active_budget_minor,
    enforce_budget_cap,
    gate_due,
    next_campaign_numbers,
    offline_smoke,
    requested_campaign_count,
    reconciliation_conflicts,
    run_daily,
    select_assets,
    validate_engine_config,
    move_to_testing,
)

SP = ZoneInfo("America/Sao_Paulo")


def operation(*, next_number=14, cap=300, override=True):
    routine: dict[str, object] = {
        "new_campaign_budget_pool_usd": 60,
        "default_campaign_initial_budget_usd": 30,
    }
    if override:
        routine["one_time_override_20260821"] = {
            "status": "authorized_pending_media_manifest_and_live_preflight",
            "campaign_count": 3,
        }
    return {
        "daily_new_campaign_routine": routine,
        "daily_budget_policy": {
            "operational_account_cap_usd": cap,
            "new_campaign_initial_budget_usd": 30,
        },
        "campaign_numbering_policy": {"next_required_campaign_number": next_number},
    }


def campaign(number: int, *, budget=3000, status="ACTIVE"):
    return {
        "id": str(number),
        "name": f"{number:02d} - 21-08 - Garagem Brasil - (b01fb13c{number:02d}) event_Subscribe - MAXVOL",
        "configured_status": status,
        "status": status,
        "effective_status": status,
        "daily_budget": str(budget),
    }


def asset(index: int, *, fingerprint: str | None = None, eligible=True):
    return {
        "asset_id": f"asset-{index}",
        "asset_drive_id": f"drive-{index}",
        "canonical_filename": f"CAR_BR_BR_VID_TEST_PV_{index:03d}.mp4",
        "vertical": "CAR",
        "country": "BR",
        "language": "BR",
        "format": "VID",
        "status": "01_READY",
        "metadata_clean": True,
        "ares_eligible": eligible,
        "used_by": None,
        "perceptual_fingerprint": fingerprint or f"fp-{index}",
        "clean_checksum": f"sha-{index}",
        "first_seen_at": f"2026-08-20T00:{index:02d}:00+00:00",
    }


def test_gate_starts_only_at_17_sp_but_resume_may_run_later():
    assert gate_due(datetime(2026, 8, 21, 17, 0, tzinfo=SP), {}) is True
    assert gate_due(datetime(2026, 8, 21, 16, 59, tzinfo=SP), {}) is False
    resume = {
        "status": "PARTIAL_DEFERRED_QUOTA",
        "operational_date_sp": "2026-08-21",
        "retry_after_epoch": 0,
    }
    assert gate_due(datetime(2026, 8, 21, 18, 0, tzinfo=SP), resume) is True


def test_one_time_override_is_three_total_and_default_remains_two():
    day = datetime(2026, 8, 21, tzinfo=SP).date()
    assert requested_campaign_count(operation(override=True), day) == 3
    assert requested_campaign_count(operation(override=False), day) == 2


def test_next_numbers_ignore_deleted_c50_and_select_c14_to_c16():
    campaigns = [campaign(number) for number in range(7, 14)]
    campaigns.append(campaign(50, status="ARCHIVED"))
    assert next_campaign_numbers(campaigns, 3, operation()) == [14, 15, 16]


def test_next_number_drift_fails_closed():
    campaigns = [campaign(number) for number in range(7, 14)]
    with pytest.raises(DailyBlocked, match="drifted"):
        next_campaign_numbers(campaigns, 3, operation(next_number=15))


def test_budget_cap_exact_300_passes():
    campaigns = [campaign(number) for number in range(7, 14)]
    campaigns[2]["daily_budget"] = "3000"
    result = enforce_budget_cap(campaigns, 3, operation(cap=300))
    assert result == {
        "active_before_minor": 21000,
        "available_minor": 9000,
        "initial_minor": 3000,
        "desired_count": 3,
        "selected_count": 3,
        "deferred_by_budget_count": 0,
        "new_minor": 9000,
        "projected_minor": 30000,
        "cap_minor": 30000,
    }


def test_budget_planner_reduces_three_desired_to_two_selected_at_live_213():
    campaigns = [campaign(number) for number in range(7, 14)]
    campaigns[2]["daily_budget"] = "3300"
    assert active_budget_minor(campaigns) == 21300
    result = enforce_budget_cap(campaigns, 3, operation(cap=300))
    assert result["desired_count"] == 3
    assert result["selected_count"] == 2
    assert result["deferred_by_budget_count"] == 1
    assert result["new_minor"] == 6000
    assert result["projected_minor"] == 27300


def test_live_213_plan_maps_three_desired_to_c14_c15_only():
    campaigns = [campaign(number) for number in range(7, 14)]
    campaigns[2]["daily_budget"] = "3300"
    budget = enforce_budget_cap(campaigns, 3, operation(cap=300))
    assert budget["desired_count"] == 3
    assert budget["selected_count"] == 2
    assert next_campaign_numbers(campaigns, budget["selected_count"], operation()) == [14, 15]


def test_budget_planner_fails_closed_only_when_zero_campaigns_fit():
    campaigns = [campaign(number) for number in range(7, 14)]
    campaigns[0]["daily_budget"] = "12000"
    with pytest.raises(DailyBlocked, match="no new campaign fits"):
        enforce_budget_cap(campaigns, 3, operation(cap=300))


def test_engine_config_requires_all_independent_gates():
    config = {
        "engine_version": 3,
        "graph_version": "v26.0",
        "bundle_size": 2,
        "enabled": True,
        "write_enabled": True,
        "media_upload_enabled": True,
        "require_prevalidated_manifest": True,
    }
    validate_engine_config(config)
    config["media_upload_enabled"] = False
    with pytest.raises(DailyBlocked, match="gates"):
        validate_engine_config(config)


def test_asset_selection_requires_nine_unique_reconciled_ready_lineages():
    rows = [asset(index) for index in range(1, 11)]
    rows.append(asset(11, fingerprint="fp-1"))
    selected = select_assets(rows, {f"drive-{index}" for index in range(1, 12)}, 9)
    assert len(selected) == 9
    assert len({row["perceptual_fingerprint"] for row in selected}) == 9


def test_asset_selection_fails_when_only_eight_unique_assets_exist():
    rows = [asset(index) for index in range(1, 9)]
    with pytest.raises(DailyBlocked, match="insufficient"):
        select_assets(rows, {f"drive-{index}" for index in range(1, 9)}, 9)


def test_reconciliation_blocks_existing_canonical_name_in_meta_ads():
    row = asset(1)
    row["canonical_filename"] = "CAR_BR_BR_VID_SCORE_BAIXO_PV_016.mp4"
    ads = [{"id": "ad-1", "name": "AD 01 - CAR_BR_BR_VID_SCORE_BAIXO_PV_016", "creative": {"name": "creative"}, "campaign": {"name": "C12"}}]
    conflicts = reconciliation_conflicts([row], ads, [])
    assert conflicts == [{
        "asset_id": "asset-1",
        "match_kind": "ad",
        "match_id": "ad-1",
        "exact_name": True,
        "source_sequence": None,
    }]


def test_offline_smoke_exercises_two_plus_one_resume_without_network():
    result = offline_smoke()
    assert result["status"] == "OFFLINE_SMOKE_OK"
    assert result["planner"] == [2, 1]
    assert result["first_status"] == "PARTIAL_DEFERRED_QUOTA"
    assert result["first_campaigns"] == 2
    assert result["final_status"] == "COMPLETE_FUTURE_ACTIVE"
    assert result["final_campaigns"] == 3
    assert result["unique_campaign_ids"] == 3
    assert result["intermediate_get_calls"] == 0
    assert result["external_network_calls"] == 0


def test_wrapper_points_only_to_v3_runner_and_does_not_reactivate_v2():
    wrapper = Path("/root/.hermes/profiles/ares/scripts/creditoparaveiculo-v3-daily-create.sh").read_text()
    assert "ares-creditoparaveiculo-v3-daily.py" in wrapper
    assert "creditoparaveiculo-daily-create.sh" not in wrapper
    assert "--gate --post-discord --quiet" in wrapper


def test_plan_only_is_read_only_and_never_calls_prestage_or_engine(tmp_path):
    paths = DailyPaths(
        config=tmp_path / "config.json",
        operation=tmp_path / "operation.json",
        templates=tmp_path / "templates.json",
        registry=tmp_path / "registry.json",
        inventory=tmp_path / "inventory.jsonl",
        reconciliation=tmp_path / "reconciliation.json",
        state=tmp_path / "state.json",
        lock=tmp_path / "state.lock",
        audit_root=tmp_path / "audit",
        work_root=tmp_path / "work",
    )
    paths.config.write_text(json.dumps({
        "engine_version": 3,
        "graph_version": "v26.0",
        "bundle_size": 2,
        "enabled": True,
        "write_enabled": True,
        "media_upload_enabled": True,
        "require_prevalidated_manifest": True,
    }))
    paths.operation.write_text(json.dumps(operation()))
    paths.inventory.write_text("".join(json.dumps(asset(index)) + "\n" for index in range(1, 10)))
    paths.reconciliation.write_text(json.dumps({
        "status": "valid",
        "account_id": "1046241194533786",
        "generated_at_utc": "2026-08-21T00:00:00+00:00",
        "valid_until_utc": "2026-08-22T00:00:00+00:00",
        "assets": [
            {
                "asset_id": f"asset-{index}",
                "asset_drive_id": f"drive-{index}",
                "clean_checksum": f"sha-{index}",
                "approved": True,
                "meta_conflicts": [],
            }
            for index in range(1, 10)
        ],
    }))

    class PlanBackend:
        def __init__(self, _paths):
            self.calls = []

        def meta_preflight(self):
            self.calls.append("meta_preflight")
            return {"campaigns": [campaign(number) for number in range(7, 14)]}

        def drive_preflight(self):
            self.calls.append("drive_preflight")
            return {
                "drive": {
                    "files": [{"id": f"drive-{index}", "location": "01_READY"} for index in range(1, 10)],
                    "counts": {"IMG": 0, "VID": 9, "TOTAL": 9},
                }
            }

        def refresh_reconciliation(self, inventory, drive, now):
            self.calls.append("refresh_reconciliation")
            return json.loads(paths.reconciliation.read_text())

        def prepare_and_prestage(self, *args, **kwargs):
            raise AssertionError("plan-only must not prestage")

        def execute_engine(self, *args, **kwargs):
            raise AssertionError("plan-only must not execute engine")

        def move_asset(self, *args, **kwargs):
            raise AssertionError("plan-only must not move Drive assets")

    before = paths.inventory.read_bytes()
    result = run_daily(
        paths=paths,
        now_sp=datetime(2026, 8, 21, 17, 0, tzinfo=SP),
        gate=True,
        plan_only=True,
        backend_factory=PlanBackend,
    )
    assert result["status"] == "DRY_RUN_OK"
    assert result["desired_campaign_count"] == 3
    assert result["campaign_count"] == 3
    assert result["campaign_numbers"] == [14, 15, 16]
    assert result["planner_bundles"] == [2, 1]
    assert result["side_effects"] == {
        "inventory_reservation": False,
        "media_upload": False,
        "campaign_write": False,
        "drive_move": False,
    }
    assert paths.inventory.read_bytes() == before
    assert not paths.state.exists()


def test_move_to_testing_is_idempotent_after_crash_without_second_patch():
    source = {
        "id": "drive-1",
        "name": "asset.mp4",
        "driveId": "0AEwt4Ye690ocUk9PVA",
        "parents": ["testing-folder"],
        "testing_parent_id": "testing-folder",
        "ready_parent_id": "ready-folder",
        "location": "02_TESTING",
        "size": "100",
        "md5Checksum": "abc",
    }
    result = move_to_testing("unused-token", source)
    assert result["already_in_testing"] is True
    assert result["parents"] == ["testing-folder"]
