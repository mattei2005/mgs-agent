from __future__ import annotations

import json
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
    update_operation_after_creation,
    move_to_testing,
    campaign_name_collisions,
    failure_resume_state,
    discord_failure_message,
    rollover_completed_state,
    media_title,
    LiveDailyBackend,
    safe_error,
    BatchTransportError,
    account_budget_summary,
    usd_minor_label,
    corrective_write_authorization,
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
    resume["manual_reconciliation_required"] = True
    assert gate_due(datetime(2026, 8, 21, 18, 0, tzinfo=SP), resume) is False


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
    assert "Solução proposta:" in message
    assert "Autorização necessária: Rodolfo ou Nicolas" in message
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


def test_failure_message_identifies_campaigns_and_blocks_corrective_write_until_authorized():
    message = discord_failure_message(
        {"type": "DailyBlocked", "stage": "readback", "message": "campaign hierarchy validation failed"},
        "READBACK_DEFERRED",
        date(2026, 8, 22),
        [17, 18, 19],
    )
    assert "Objeto: C17, C18, C19 · criação CBO programada" in message
    assert "Ares faz somente diagnóstico/readback" in message
    assert "não executa write corretivo" in message


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


def test_exact_manifest_name_collision_blocks_unmapped_live_campaign():
    name = "14 - 22-08 - Garagem Brasil - (b01fb13c14) event_Subscribe - MAXVOL"
    manifest = SimpleNamespace(campaigns=[SimpleNamespace(name=name)])
    live = [{"id": "live-14", "name": name, "status": "ACTIVE", "effective_status": "ACTIVE"}]
    assert campaign_name_collisions(manifest, live, set()) == [{"campaign_id": "live-14", "name": name, "status": "ACTIVE"}]
    assert campaign_name_collisions(manifest, live, {"live-14"}) == []
    live[0]["effective_status"] = "ARCHIVED"
    assert campaign_name_collisions(manifest, live, set()) == []


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
    assert failure_resume_state({}, known_campaign_ids=False) == ("FAILED", False)


def test_corrective_write_authorization_is_exclusively_rodolfo_or_nicolas():
    assert corrective_write_authorization() == {
        "required": True,
        "authorized_roles": ["Rodolfo", "Nicolas"],
        "scope": "any corrective write after this failure",
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
