from __future__ import annotations

import json
import subprocess
import sys
from types import SimpleNamespace
from datetime import date, datetime
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
    auto_arm_first_delivery_campaigns,
    enforce_budget_cap,
    gate_due,
    next_campaign_numbers,
    offline_smoke,
    requested_campaign_count,
    reconciliation_conflicts,
    run_daily,
    select_assets,
    validate_engine_config,
    validate_hierarchy,
    update_operation_after_creation,
    move_to_testing,
    move_to_status,
    make_square_clean,
    campaign_name_collisions,
    recovery_checkpoint_campaign_ids,
    failure_resume_state,
    discord_failure_message,
    rollover_completed_state,
    finalize_completed_state,
    request_operational_date,
    media_title,
    LiveDailyBackend,
    safe_error,
    BatchTransportError,
    account_budget_summary,
    resume_budget_plan,
    usd_minor_label,
    corrective_write_authorization,
    assignments_from_readback,
    update_inventory_assignments,
)


def test_assignments_preserve_source_lineage_and_use_materialized_video_ids():
    campaign_ads = []
    live_ads = []
    for index in range(1, 4):
        expected_videos = [
            {"video_id": f"pre-v-{index}", "adlabels": [{"id": f"vertical-label-{index}", "name": f"vertical-{index}"}]},
            {"video_id": f"pre-s-{index}", "adlabels": [{"id": f"square-label-{index}", "name": f"square-{index}"}]},
        ]
        campaign_ads.append(SimpleNamespace(
            name=f"AD {index:02d}",
            source_ad_id=f"source-ad-{index}",
            media=SimpleNamespace(asset_id=f"asset-{index}", vertical_video_id=f"pre-v-{index}", square_video_id=f"pre-s-{index}"),
            creative_payload={"asset_feed_spec": {"videos": expected_videos}},
        ))
        live_ads.append({
            "id": f"ad-{index}",
            "name": f"AD {index:02d}",
            "status": "ACTIVE",
            "source_ad_id": f"source-ad-{index}",
            "creative": {
                "id": f"creative-{index}",
                "status": "ACTIVE",
                "effective_object_story_id": f"page_post_{index}",
                "asset_feed_spec": {"videos": [
                    {"video_id": f"derived-s-{index}", "adlabels": [{"id": f"square-label-{index}", "name": f"square-{index}"}]},
                    {"video_id": f"derived-v-{index}", "adlabels": [{"id": f"vertical-label-{index}", "name": f"vertical-{index}"}]},
                ]},
            },
        })
    campaign = SimpleNamespace(
        name="C20",
        status="ACTIVE",
        start_time="2026-08-23T05:00:00-03:00",
        campaign_updates={"daily_budget": "3000"},
        ads=campaign_ads,
    )
    readbacks = {
        "campaign-20": {
            "campaign": {"name": "C20", "status": "ACTIVE", "daily_budget": "3000", "start_time": "2026-08-23T05:00:00-03:00"},
            "adsets": [{"id": "adset-20", "status": "ACTIVE"}],
            "ads": live_ads,
        }
    }
    result = assignments_from_readback(SimpleNamespace(campaigns=[campaign]), ["campaign-20"], readbacks)
    assert len(result) == 3
    assert [row["source_ad_id"] for row in result] == ["source-ad-1", "source-ad-2", "source-ad-3"]
    assert [row["vertical_video_id"] for row in result] == ["derived-v-1", "derived-v-2", "derived-v-3"]
    assert [row["square_video_id"] for row in result] == ["derived-s-1", "derived-s-2", "derived-s-3"]
    assert [row["prestage_vertical_video_id"] for row in result] == ["pre-v-1", "pre-v-2", "pre-v-3"]


SP = ZoneInfo("America/Sao_Paulo")


def operation(*, next_number=14, cap=300, override=True, dynamic=False):
    routine: dict[str, object] = {
        "new_campaign_budget_pool_usd": 60,
        "default_campaign_initial_budget_usd": 30,
        "clone_source_policy": {
            "authorized_by": "Rodolfo Mattei",
            "rule": "always clone from the eligible campaign with the highest Smart Bidding ROI within the same vehicle type",
        },
    }
    if override:
        routine["one_time_override_20260821"] = {
            "status": "authorized_pending_media_manifest_and_live_preflight",
            "campaign_count": 3,
        }
    budget_policy: dict[str, object] = {
        "operational_account_cap_usd": cap,
        "new_campaign_initial_budget_usd": 30,
    }
    if dynamic:
        budget_policy["dynamic_account_cap"] = {
            "enabled": True,
            "allowed_scopes": ["scheduled_creation", "roi_scale", "guardrail_reactivation"],
        }
    return {
        "daily_new_campaign_routine": routine,
        "daily_budget_policy": budget_policy,
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


def test_hierarchy_requires_active_creatives_with_effective_story_ids():
    expected = SimpleNamespace(
        name="20 - 23-08 - Garagem Brasil - (b01fb13c20) event_Subscribe - MAXVOL",
        status="ACTIVE",
        start_time="2026-08-23T03:00:00-03:00",
        campaign_updates={"daily_budget": "3000"},
    )
    readback = {
        "campaign": {
            "name": expected.name,
            "status": "ACTIVE",
            "daily_budget": "3000",
            "start_time": expected.start_time,
        },
        "adsets": [{"status": "ACTIVE"}],
        "ads": [
            {
                "status": "ACTIVE",
                "creative": {
                    "status": "ACTIVE",
                    "effective_object_story_id": f"page_story_{index}",
                },
            }
            for index in range(3)
        ],
    }
    assert validate_hierarchy(readback, expected)["valid"] is True
    readback["ads"][0]["creative"].pop("effective_object_story_id")
    result = validate_hierarchy(readback, expected)
    assert result["valid"] is False
    assert result["creatives_ok"] is False


def test_square_render_reuses_existing_clean_1080_output(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    destination = tmp_path / "square.mp4"
    source.write_bytes(b"source")
    destination.write_bytes(b"already-clean")
    monkeypatch.setattr(
        "ares_campaign_v3.daily_cpv.verify_clean",
        lambda path: {"sha256": "clean-sha", "bytes": path.stat().st_size, "clean": True},
    )
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"streams": [{"codec_type": "video", "width": 1080, "height": 1080}]}),
            stderr="",
        )
    monkeypatch.setattr("ares_campaign_v3.daily_cpv.subprocess.run", fake_run)
    result = make_square_clean(source, destination)
    assert result["reused_existing"] is True
    assert result["clean"] is True
    assert len(calls) == 1
    assert calls[0][0] == "ffprobe"


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
    resume["manual_reconciliation_required"] = True
    assert gate_due(datetime(2026, 8, 21, 18, 0, tzinfo=SP), resume) is True


def test_completed_request_is_not_reused_on_the_next_operational_day():
    previous = {
        "status": "POSTPROCESS_PENDING",
        "operational_date_sp": "2026-08-21",
        "completed_operational_date_sp": "2026-08-21",
        "request_id": "cpv-daily-20260821",
        "selected_asset_ids": ["old-asset"],
    }
    assert rollover_completed_state(previous, "2026-08-22") == {}
    assert rollover_completed_state(previous, "2026-08-21") == previous


def test_finalize_completed_state_clears_stale_recovery_markers():
    state = {
        "status": "READBACK_DEFERRED",
        "failure": {"type": "BatchTransportError"},
        "retry_after_epoch": 123,
        "operator_authorization": {"required": False},
        "automatic_recovery_required": True,
        "manual_reconciliation_required": True,
    }
    completed = finalize_completed_state(state, status="COMPLETE", campaign_ids=["1"])
    assert completed["status"] == "COMPLETE"
    assert completed["campaign_ids"] == ["1"]
    assert completed["automatic_recovery_required"] is False
    assert completed["manual_reconciliation_required"] is False
    assert "failure" not in completed
    assert "retry_after_epoch" not in completed
    assert "operator_authorization" not in completed


def test_resumable_request_preserves_operational_date_after_midnight():
    state = {
        "status": "POSTPROCESS_PENDING",
        "operational_date_sp": "2026-08-26",
        "retry_after_epoch": 0,
    }
    now_sp = datetime(2026, 8, 27, 0, 14, tzinfo=SP)
    assert request_operational_date(now_sp, state).isoformat() == "2026-08-26"
    assert gate_due(now_sp, state) is True


def test_discord_failure_explains_cause_impact_and_correction_without_internal_paths():
    message = discord_failure_message(
        {
            "type": "DailyBlocked",
            "stage": "reconciliation",
            "message": "reconciliation manifest expired",
            "detail": {"valid_until_utc": "2026-08-22T02:15:23+00:00", "path": "/root/private"},
        },
        "POSTPROCESS_PENDING",
        date(2026, 8, 22),
    )
    assert "Etapa: reconciliation" in message
    assert "Causa:" in message
    assert "Objeto: ciclo diário programado" in message
    assert "Consequência:" in message
    assert "Correção:" in message
    assert "Ação automática:" in message
    assert "Drive × Meta" in message
    assert "/root/" not in message


def test_batch_transport_failure_preserves_sanitized_meta_cause_for_operator_message():
    failure = safe_error(BatchTransportError("creative_ad_create", {
        "children": [{
            "name": "creative_1_1",
            "code": 400,
            "error": {
                "message": "Invalid parameter",
                "type": "OAuthException",
                "code": 100,
                "error_subcode": 2446173,
                "error_user_title": "O rótulo da regra não referencia um ativo",
                "fbtrace_id": "not-operator-output",
            },
        }],
        "outer_headers": {"authorization": "secret"},
    }))
    assert failure["stage"] == "creative_ad_create"
    assert failure["detail"]["children"][0]["error"]["error_subcode"] == 2446173
    serialized = json.dumps(failure)
    assert "authorization" not in serialized
    assert "fbtrace_id" not in serialized
    message = discord_failure_message(failure, "READBACK_DEFERRED", date(2026, 8, 22))
    assert "código 100/2446173" in message
    assert "O rótulo da regra" in message


def test_failure_message_identifies_campaigns_and_commits_to_automatic_recovery():
    message = discord_failure_message(
        {"type": "DailyBlocked", "stage": "readback", "message": "campaign hierarchy validation failed"},
        "READBACK_DEFERRED",
        date(2026, 8, 22),
        [17, 18, 19],
    )
    assert "Objeto: C17, C18, C19 · criação CBO programada" in message
    assert "Ares reconcilia o estado real" in message
    assert "sem replay cego" in message


def test_account_budget_summary_reports_remaining_operational_cap():
    summary = account_budget_summary({"projected_minor": 40500, "cap_minor": 50000})
    assert summary == {
        "active_minor": 40500,
        "remaining_minor": 9500,
        "cap_minor": 50000,
        "currency": "USD",
        "source": "live Meta preflight plus validated campaign budgets from this request",
    }
    assert usd_minor_label(summary["active_minor"]) == "405"
    assert usd_minor_label(summary["remaining_minor"]) == "95"


def test_resume_budget_plan_does_not_add_budget_when_all_campaigns_exist():
    campaigns = [
        {"configured_status": "ACTIVE", "effective_status": "ACTIVE", "daily_budget": "3000"},
        {"configured_status": "ACTIVE", "effective_status": "ACTIVE", "daily_budget": "3000"},
    ]
    operation_payload = {
        "daily_budget_policy": {
            "new_campaign_initial_budget_usd": 30,
            "operational_account_cap_usd": 500,
            "dynamic_account_cap": {"enabled": True, "allowed_scopes": ["scheduled_creation"]},
        }
    }
    budget = resume_budget_plan(campaigns, count=2, completed_before=2, operation=operation_payload)
    assert budget["new_minor"] == 0
    assert budget["projected_minor"] == 6000
    assert account_budget_summary(budget)["active_minor"] == 6000


def test_lifecycle_observation_hold_blocks_new_campaign_count_but_not_analysis_jobs():
    held = operation()
    held["daily_new_campaign_routine"]["status"] = "paused_lifecycle_observation"
    held["daily_new_campaign_routine"]["creation_hold"] = {
        "enabled": True,
        "observe_campaigns": [17, 18, 19],
        "resume_authority": ["Rodolfo", "Nicolas"],
    }
    with pytest.raises(DailyBlocked, match="paused for lifecycle observation") as exc:
        requested_campaign_count(held, date(2026, 8, 23))
    assert exc.value.stage == "creation_hold"


def test_creation_hold_alert_explains_loop_and_release_gate():
    message = discord_failure_message(
        {"type": "DailyBlocked", "stage": "creation_hold", "message": "scheduled campaign creation is paused for lifecycle observation"},
        "FAILED",
        date(2026, 8, 23),
        [17, 18, 19],
    )
    assert "pausada para observar a coorte mais recente durante D1, D2 e D3" in message
    assert "Manter análise, pausa e escala normais" in message
    assert "Rodolfo ou Nicolas" in message


def test_exact_manifest_name_collision_blocks_unmapped_live_campaign():
    name = "14 - 22-08 - Garagem Brasil - (b01fb13c14) event_Subscribe - MAXVOL"
    manifest = SimpleNamespace(campaigns=[SimpleNamespace(name=name)])
    live = [{"id": "live-14", "name": name, "status": "ACTIVE", "effective_status": "ACTIVE"}]
    assert campaign_name_collisions(manifest, live, set()) == [{"campaign_id": "live-14", "name": name, "status": "ACTIVE"}]
    assert campaign_name_collisions(manifest, live, {"live-14"}) == []
    live[0]["effective_status"] = "ARCHIVED"
    assert campaign_name_collisions(manifest, live, set()) == []


def test_recovery_checkpoint_campaign_ids_collects_only_persisted_numeric_ids(tmp_path):
    checkpoint_dir = tmp_path / "state" / "checkpoints"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / "request-1-100.json").write_text(json.dumps({
        "bundles": [
            {"campaign_ids": ["123", "456"]},
            {"campaign_ids": ["456", "not-an-id"]},
        ]
    }))
    (checkpoint_dir / "another-request-100.json").write_text(json.dumps({"bundles": [{"campaign_ids": ["999"]}]}))
    assert recovery_checkpoint_campaign_ids({"state_root": str(tmp_path / "state")}, "request-1") == ["123", "456"]


def test_media_title_binds_reuse_to_asset_and_checksum():
    first = media_title("VERTICAL", "asset-1", "a" * 64)
    second = media_title("VERTICAL", "asset-1", "b" * 64)
    square = media_title("SQUARE", "asset-1", "a" * 64)
    assert first == "V3 VERTICAL asset-1 aaaaaaaaaaaa"
    assert second == "V3 VERTICAL asset-1 bbbbbbbbbbbb"
    assert first != second
    assert first != square


def test_failure_after_external_side_effect_never_becomes_terminal_failed():
    assert failure_resume_state({"media_upload": True}, known_campaign_ids=False) == ("READBACK_DEFERRED", False)
    assert failure_resume_state({"campaign_write": True}, known_campaign_ids=False) == ("READBACK_DEFERRED", True)
    assert failure_resume_state({"campaign_write": True}, known_campaign_ids=True) == ("READBACK_DEFERRED", False)
    assert failure_resume_state({"drive_move": True, "campaign_write": True}, known_campaign_ids=True) == ("POSTPROCESS_PENDING", False)
    assert failure_resume_state({}, known_campaign_ids=False) == ("RECOVERY_PENDING", False)


def test_corrective_write_uses_rodolfo_standing_recovery_authority():
    assert corrective_write_authorization() == {
        "required": False,
        "standing_authority": "Rodolfo Mattei",
        "scope": "diagnose, reconcile and correct the same authorized request until completion",
        "guards": ["readback_before_write", "missing_layer_only", "no_blind_replay", "no_scope_expansion"],
    }


def test_first_delivery_auto_arm_helper_requires_exact_zero_write_readback(tmp_path):
    script = tmp_path / "guardrail.py"
    script.write_text(
        "import json,sys\n"
        "ids=[sys.argv[i+1] for i,x in enumerate(sys.argv) if x=='--campaign-id']\n"
        "print(json.dumps({'status':'AUTO_ARMED','campaign_ids':ids,'armed_count':len(ids),'meta_writes':0}))\n"
    )
    result = auto_arm_first_delivery_campaigns(
        ["c17", "c18"],
        datetime(2026, 8, 23, tzinfo=SP).date(),
        "request-17-18",
        script=script,
    )
    assert result["status"] == "AUTO_ARMED"
    assert result["campaign_ids"] == ["c17", "c18"]
    assert result["meta_writes"] == 0


def test_operation_partial_postprocess_adds_allowlist_without_closing_request(tmp_path):
    path = tmp_path / "operation.json"
    payload = operation(next_number=17)
    payload["management_scope"] = {"autonomous_action_scope": {"allowed_campaigns": {}}}
    payload["daily_new_campaign_routine"]["one_time_override_20260821"]["status"] = "pending"
    path.write_text(json.dumps(payload))
    manifest = SimpleNamespace(
        request_id="request-17",
        campaigns=[SimpleNamespace(name="17 - 22-08 - Garagem Brasil - (b01fb13c17) event_Subscribe - MAXVOL")],
    )
    update_operation_after_creation(
        path,
        manifest,
        ["campaign-17"],
        datetime(2026, 8, 21, tzinfo=SP).date(),
        complete_request=False,
    )
    readback = json.loads(path.read_text())
    allowed = readback["management_scope"]["autonomous_action_scope"]["allowed_campaigns"]["17"]
    assert allowed["campaign_id"] == "campaign-17"
    assert allowed["cycle_start_date"] == "2026-08-22"
    assert readback["campaign_numbering_policy"]["next_required_campaign_number"] == 18
    assert readback["daily_new_campaign_routine"]["one_time_override_20260821"]["status"] == "pending"


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
        "base_cap_minor": 30000,
        "cap_minor": 30000,
        "cap_adjusted_minor": 0,
        "dynamic_enabled": False,
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


def test_dynamic_budget_envelope_keeps_all_authorized_campaigns_when_floor_would_overflow():
    campaigns = [campaign(number) for number in range(7, 14)]
    campaigns[2]["daily_budget"] = "3300"
    result = enforce_budget_cap(campaigns, 3, operation(cap=300, dynamic=True))
    assert result["desired_count"] == 3
    assert result["selected_count"] == 3
    assert result["deferred_by_budget_count"] == 0
    assert result["projected_minor"] == 30300
    assert result["base_cap_minor"] == 30000
    assert result["cap_minor"] == 30300
    assert result["cap_adjusted_minor"] == 300
    assert result["dynamic_enabled"] is True


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


def test_meta_preflight_uses_cache_first_token_lookup_without_force_refresh():
    class FakeCommon:
        def __init__(self):
            self.token_calls = []

        def get_token_from_1password(self, item_name):
            self.token_calls.append(item_name)
            return "sanitized-token", "token"

        def graph_get(self, path, token, params):
            if path == "act_1046241194533786":
                return 200, {
                    "id": "act_1046241194533786",
                    "currency": "USD",
                    "timezone_name": "America/Sao_Paulo",
                    "account_status": 1,
                    "disable_reason": 0,
                }, {}
            if path == "me/accounts":
                return 200, {"data": [{"id": "621037101089579", "tasks": ["ADVERTISE"], "access_token": "sanitized-page-token"}]}, {}
            raise AssertionError(path)

    backend = object.__new__(LiveDailyBackend)
    backend.common = FakeCommon()
    backend.token = None
    backend.page_token = None
    backend.drive_token = None
    backend._graph_pages = lambda path, params: []
    result = backend.meta_preflight()
    assert backend.common.token_calls == ["Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006"]
    assert result["token_report"]["field"] == "token"
    assert result["page"]["tasks"] == ["ADVERTISE"]


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


def test_asset_selection_skips_unreconciled_drive_assets_before_filling_batch():
    rows = [asset(index) for index in range(1, 12)]
    reconciliation = {
        "assets": [
            {
                "asset_id": row["asset_id"],
                "asset_drive_id": row["asset_drive_id"],
                "clean_checksum": row["clean_checksum"],
                "approved": row["asset_id"] not in {"asset-1", "asset-2"},
                "meta_conflicts": ([{"match_id": f"video-{row['asset_id']}"}] if row["asset_id"] in {"asset-1", "asset-2"} else []),
            }
            for row in rows
        ],
    }
    selected = select_assets(
        rows,
        {f"drive-{index}" for index in range(1, 12)},
        9,
        reconciliation=reconciliation,
    )
    assert [row["asset_id"] for row in selected] == [f"asset-{index}" for index in range(3, 12)]


def test_asset_selection_uses_two_ready_plus_one_retest_per_campaign():
    ready = [asset(index) for index in range(1, 7)]
    retests = []
    for index in range(7, 10):
        row = asset(index)
        row.update(
            status="03_TESTED",
            evaluation_status="INCONCLUSIVO_POR_SUBENTREGA",
            retest_eligible=True,
            test_attempt_count=1,
        )
        retests.append(row)
    rows = [*ready, *retests]
    selected = select_assets(
        rows,
        {f"drive-{index}" for index in range(1, 10)},
        9,
        mix_policy={
            "enabled": True,
            "ready_slots_per_campaign": 2,
            "retest_slots_per_campaign": 1,
            "max_test_attempts": 2,
        },
    )
    assert [row["status"] for row in selected] == [
        "01_READY", "01_READY", "03_TESTED",
        "01_READY", "01_READY", "03_TESTED",
        "01_READY", "01_READY", "03_TESTED",
    ]


def test_asset_selection_falls_back_to_three_ready_when_no_retest_exists():
    rows = [asset(index) for index in range(1, 4)]
    selected = select_assets(
        rows,
        {f"drive-{index}" for index in range(1, 4)},
        3,
        mix_policy={
            "enabled": True,
            "ready_slots_per_campaign": 2,
            "retest_slots_per_campaign": 1,
            "max_test_attempts": 2,
        },
    )
    assert [row["asset_id"] for row in selected] == ["asset-1", "asset-2", "asset-3"]


def test_asset_selection_never_retests_after_second_attempt():
    rows = [asset(1), asset(2), asset(3)]
    rows[2].update(
        status="03_TESTED",
        evaluation_status="INCONCLUSIVO_POR_SUBENTREGA",
        retest_eligible=True,
        test_attempt_count=2,
    )
    with pytest.raises(DailyBlocked, match="insufficient"):
        select_assets(
            rows,
            {"drive-1", "drive-2", "drive-3"},
            3,
            mix_policy={
                "enabled": True,
                "ready_slots_per_campaign": 2,
                "retest_slots_per_campaign": 1,
                "max_test_attempts": 2,
            },
        )


def test_reconciliation_blocks_existing_canonical_name_in_meta_ads():
    row = asset(1)
    row["canonical_filename"] = "CAR_BR_BR_VID_SCORE_BAIXO_PV_016.mp4"
    ads = [{"id": "ad-1", "name": "AD 01 - CAR_BR_BR_VID_SCORE_BAIXO_PV_016", "creative": {"name": "creative"}, "campaign": {"name": "C12"}}]
    conflicts = reconciliation_conflicts([row], ads, [])
    assert len(conflicts) == 1
    assert {key: conflicts[0][key] for key in ("asset_id", "match_kind", "match_id", "exact_name", "source_sequence")} == {
        "asset_id": "asset-1",
        "match_kind": "ad",
        "match_id": "ad-1",
        "exact_name": True,
        "source_sequence": None,
    }


def test_offline_smoke_exercises_two_plus_one_resume_without_network():
    result = offline_smoke()
    assert result["status"] == "OFFLINE_SMOKE_OK"
    assert result["planner"] == [2, 1]
    assert result["first_status"] == "PARTIAL_DEFERRED_QUOTA"
    assert result["first_campaigns"] == 0
    assert result["first_stage"] == "two_campaign_writes_persisted_readback_deferred"
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
    assert "flock -E 75 -n /run/lock/ares-cpv-meta-lane-1046241194533786.lock" in wrapper
    assert "sleep " not in wrapper


def test_all_active_cpv_readers_use_one_persisted_writer_gate_and_shared_lane():
    wrappers = (
        "creditoparaveiculo-intraday.sh",
        "creditoparaveiculo-daily.sh",
        "creditoparaveiculo-snapshot.sh",
        "creditoparaveiculo-first-delivery-guardrail.sh",
        "creditoparaveiculo-guardrail-reactivate.sh",
    )
    for name in wrappers:
        content = (Path("/root/.hermes/profiles/ares/scripts") / name).read_text()
        assert "ares-cpv-meta-reader-gate.py" in content
        assert "flock -s -E 75 -n /run/lock/ares-cpv-meta-lane-1046241194533786.lock" in content
        assert "sleep " not in content

    intraday = (Path("/root/.hermes/profiles/ares/scripts") / wrappers[0]).read_text()
    assert "--mode intraday --actions-only --gate" in intraday


def test_reader_gate_blocks_engine_lease_and_resumable_daily_state(tmp_path):
    script = ROOT / "scripts/ares-cpv-meta-reader-gate.py"
    state_root = tmp_path / "engine-state"
    operation_state = tmp_path / "cpv-daily.json"
    lease_dir = state_root / "writer-leases"
    lease_dir.mkdir(parents=True)
    lease = lease_dir / "1046241194533786.json"

    def run_gate():
        return subprocess.run(
            [
                sys.executable,
                str(script),
                "--account-id", "1046241194533786",
                "--state-root", str(state_root),
                "--operation-state", str(operation_state),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    lease.write_text(json.dumps({
        "account_id": "1046241194533786",
        "request_id": "test-request",
        "status": "IN_PROGRESS",
        "blocks_readers": True,
    }))
    assert run_gate().returncode == 75

    lease.write_text(json.dumps({
        "account_id": "1046241194533786",
        "request_id": "test-request",
        "status": "COMPLETE",
        "blocks_readers": False,
    }))
    operation_state.write_text(json.dumps({"status": "READBACK_DEFERRED"}))
    assert run_gate().returncode == 75

    operation_state.write_text(json.dumps({"status": "COMPLETE"}))
    assert run_gate().returncode == 0


def test_campaign_engine_release_is_synchronized_across_runtime_and_governance():
    expected = "3.4.2"
    engine = (ROOT / "scripts/ares_campaign_v3/engine.py").read_text()
    config = json.loads((ROOT / "data/ares/meta-ads/engine-v3/config.json").read_text())
    operation_v3 = json.loads((ROOT / "data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR-v3.json").read_text())
    operation = json.loads((ROOT / "data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json").read_text())
    canonical_skill = (ROOT / "profiles/ares-skills/growth/meta-campaign-engine-v3/SKILL.md").read_text()
    live_skill = Path("/root/.hermes/profiles/ares/skills/growth/meta-campaign-engine-v3/SKILL.md").read_text()

    assert f'ENGINE_RELEASE_VERSION = "{expected}"' in engine
    assert config["release_version"] == expected
    assert operation_v3["release_version"] == expected
    assert operation["campaign_engine_v3"]["version"] == expected
    assert f"version: {expected}" in canonical_skill
    assert canonical_skill == live_skill


def test_plan_only_is_read_only_and_never_calls_prestage_or_engine(tmp_path):
    paths = DailyPaths(
        config=tmp_path / "config.json",
        operation=tmp_path / "operation.json",
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
    paths.inventory.write_text("".join(json.dumps(asset(index)) + "\n" for index in range(1, 12)))
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
                "approved": index > 2,
                "meta_conflicts": ([{"match_id": f"video-{index}"}] if index <= 2 else []),
            }
            for index in range(1, 12)
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
                    "files": [{"id": f"drive-{index}", "location": "01_READY"} for index in range(1, 12)],
                    "counts": {"IMG": 0, "VID": 11, "TOTAL": 11},
                }
            }

        def refresh_reconciliation(self, inventory, drive, now):
            self.calls.append("refresh_reconciliation")
            return json.loads(paths.reconciliation.read_text())

        def select_clone_sources(self, *, asset_refs, campaign_count, meta_campaigns, target_date, operation, request_id):
            self.calls.append("select_clone_sources")
            return {
                "schema_version": 1,
                "policy": "highest_smart_bidding_roi_same_vehicle_type_at_manifest_preflight",
                "selected_at_utc": "2026-08-21T20:00:00+00:00",
                "target_date": target_date,
                "currency": "USD",
                "request_id": request_id,
                "campaign_vehicle_types": ["CARRO"] * campaign_count,
                "sources_by_vehicle": {
                    "CARRO": {
                        "vehicle_type": "CARRO",
                        "source_campaign_id": "best-car-campaign",
                        "source_adset_id": "best-car-adset",
                        "source_campaign": {"name": "12 - MAXVOL"},
                        "templates": [],
                        "roi_evidence": {"roi_pct": 31.5, "target_date": target_date, "currency": "USD"},
                    }
                },
            }

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
    assert result["audit"].endswith("cpv-daily-20260821-dry-run.json")
    assert result["desired_campaign_count"] == 3
    assert result["campaign_count"] == 3
    assert result["campaign_numbers"] == [14, 15, 16]
    assert result["planner_bundles"] == [2, 1]
    assert result["source_selection"][0]["source_campaign_id"] == "best-car-campaign"
    assert result["selected_assets"] == [f"CAR_BR_BR_VID_TEST_PV_{index:03d}.mp4" for index in range(3, 12)]
    assert result["side_effects"] == {
        "inventory_reservation": False,
        "media_upload": False,
        "campaign_write": False,
        "drive_move": False,
    }
    assert paths.inventory.read_bytes() == before
    assert not paths.state.exists()
    audit = json.loads(Path(result["audit"]).read_text())
    observability = audit["observability"]
    assert observability["phase_order"] == [
        "meta_preflight",
        "drive_preflight",
        "reconciliation",
        "asset_selection",
        "source_selection",
        "prestage",
        "manifest_prevalidation",
        "engine",
        "postprocess",
    ]
    assert list(observability["phases"]) == observability["phase_order"]
    assert all("duration_ms" in observability["phases"][name] and "calls" in observability["phases"][name] for name in observability["phase_order"])
    assert observability["phases"]["meta_preflight"]["skipped"] is False
    assert observability["phases"]["drive_preflight"]["skipped"] is False
    assert observability["phases"]["reconciliation"]["skipped"] is False
    assert observability["phases"]["asset_selection"]["skipped"] is False
    assert observability["phases"]["source_selection"]["skipped"] is False
    assert observability["phases"]["prestage"]["skipped"] is True
    assert observability["phases"]["engine"]["skipped"] is True
    assert observability["total"]["duration_ms"] >= 0
    assert "access_token" not in json.dumps(observability).lower()


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


def test_inventory_assignment_history_is_idempotent_on_recovery(tmp_path):
    inventory_path = tmp_path / "assets.jsonl"
    rows = [asset(1)]
    inventory_path.write_text(json.dumps(rows[0]) + "\n")
    assignment = {
        "asset_id": "asset-1",
        "campaign_id": "campaign-1",
        "adset_id": "adset-1",
        "ad_id": "ad-1",
        "creative_id": "creative-1",
        "source_ad_id": "source-1",
        "effective_object_story_id": "page_post_1",
        "vertical_video_id": "derived-v-1",
        "square_video_id": "derived-s-1",
        "prestage_vertical_video_id": "pre-v-1",
        "prestage_square_video_id": "pre-s-1",
    }
    moves = {"drive-1": {"id": "drive-1", "target_status": "02_TESTING"}}
    update_inventory_assignments(inventory_path, rows, [assignment], moves, tmp_path / "audit.json")
    update_inventory_assignments(inventory_path, rows, [assignment], moves, tmp_path / "audit.json")
    assert rows[0]["test_attempt_count"] == 1
    assert len(rows[0]["test_history"]) == 1


def test_move_to_status_uses_exact_source_and_target_with_readback(monkeypatch):
    captured = {}

    def fake_drive_request(token, method, url, *, body=None, content_type=None):
        captured.update(token=token, method=method, url=url, body=body, content_type=content_type)
        return {
            "id": "drive-1",
            "name": "asset.mp4",
            "driveId": "0AEwt4Ye690ocUk9PVA",
            "parents": ["tested-folder"],
            "trashed": False,
            "size": "100",
            "md5Checksum": "abc",
        }

    monkeypatch.setattr("ares_campaign_v3.daily_cpv.drive_request", fake_drive_request)
    source = {
        "id": "drive-1",
        "name": "asset.mp4",
        "driveId": "0AEwt4Ye690ocUk9PVA",
        "parents": ["testing-folder"],
        "source_parent_id": "testing-folder",
        "status_parent_ids": {"02_TESTING": "testing-folder", "03_TESTED": "tested-folder"},
        "location": "02_TESTING",
        "size": "100",
        "md5Checksum": "abc",
    }
    result = move_to_status("token", source, "03_TESTED")
    assert captured["method"] == "PATCH"
    assert "addParents=tested-folder" in captured["url"]
    assert "removeParents=testing-folder" in captured["url"]
    assert result["target_status"] == "03_TESTED"
    assert result["parents"] == ["tested-folder"]
