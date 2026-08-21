from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT = Path("/root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py")


def load_reports_module():
    spec = importlib.util.spec_from_file_location("creditoparaveiculo_fixed_reports_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeMeta:
    def __init__(self, campaigns):
        self.campaigns = {str(row["id"]): dict(row) for row in campaigns}
        self.posts = []

    def get_token_from_1password(self, item, force_refresh=False):
        return "sanitized-test-token", "token"

    def graph_get(self, path, token, params=None):
        path = str(path)
        if path == "act_1046241194533786/campaigns":
            return 200, {"data": [dict(row) for row in self.campaigns.values()]}, {}
        if path.endswith("/adsets"):
            campaign_id = path.rsplit("/", 1)[0]
            if campaign_id not in self.campaigns:
                return 404, {"error": {"message": "not found"}}, {}
            return 200, {"data": [{"id": f"as-{campaign_id}", "status": "ACTIVE", "effective_status": "ACTIVE"}]}, {}
        if path.endswith("/ads"):
            campaign_id = path.rsplit("/", 1)[0]
            if campaign_id not in self.campaigns:
                return 404, {"error": {"message": "not found"}}, {}
            return 200, {
                "data": [
                    {"id": f"ad-{campaign_id}-{index}", "status": "ACTIVE", "effective_status": "ACTIVE"}
                    for index in range(1, 4)
                ]
            }, {}
        row = self.campaigns.get(path)
        if row is None:
            return 404, {"error": {"message": "not found"}}, {}
        return 200, dict(row), {}

    def graph_post_once(self, path, token, params=None):
        params = dict(params or {})
        self.posts.append((str(path), params))
        row = self.campaigns[str(path)]
        if "daily_budget" in params:
            row["daily_budget"] = str(params["daily_budget"])
        if "status" in params:
            row["status"] = str(params["status"])
            row["effective_status"] = str(params["status"])
        return 200, {"success": True}, {}

    @staticmethod
    def safe_meta_error(payload):
        return {"safe": True, "payload_type": type(payload).__name__}


def configure_runtime(monkeypatch, tmp_path, module, fake_meta, *, account_cap=300):
    monkeypatch.setattr(module, "AUTONOMOUS_WRITE_NUMBERS", {"09"})
    operation = {
        "operation_id": "Creditoparaveiculo-BR-CAR-BR",
        "management_scope": {
            "write_enabled": True,
            "reporting_mode": "autonomous_guarded",
            "manual_holds": [],
            "autonomous_action_scope": {
                "allowed_campaigns": {
                    "09": {"campaign_id": "1", "cycle_start_date": "2026-08-20"}
                },
                "scale_execution_gate": {
                    "window_minutes": 10,
                    "max_smart_bidding_delay_minutes": 120,
                    "required_matched_adgroups": 1,
                },
            },
        },
        "daily_budget_policy": {
            "campaign_daily_ceiling_usd": 150,
            "operational_account_cap_usd": account_cap,
        },
        "anomaly_gate": {"thresholds": "test_calibrated_v1"},
    }
    operation_path = tmp_path / "operation.json"
    operation_path.write_text(json.dumps(operation))
    monkeypatch.setattr(module, "OP_PATH", operation_path)
    monkeypatch.setattr(module, "ACTION_STATE", tmp_path / "state.json")
    monkeypatch.setattr(module, "ACTION_LOCK", tmp_path / "state.lock")
    monkeypatch.setattr(module, "ACTION_AUDIT_ROOT", tmp_path / "audit")
    monkeypatch.setattr(module, "load_module", lambda path, name: fake_meta)


def active_campaign(campaign_id="1", budget="3000", number="09", *, status="ACTIVE"):
    return {
        "id": campaign_id,
        "name": f"{number} - 20-08 - Garagem Brasil",
        "status": status,
        "configured_status": status,
        "effective_status": status,
        "daily_budget": budget,
        "updated_time": "2026-08-20T08:00:00-0300",
    }


def scale_row(campaign_id="1", budget_usd=30.0):
    return {
        "number": "09",
        "campaign_id": campaign_id,
        "name": "09 - 20-08 - Garagem Brasil",
        "budget_usd": budget_usd,
        "sb_roi": 27.0,
        "matched_adgroups": 1,
        "recommendation": "ESCALAR +10%",
    }


def meta_account():
    return {
        "id": "act_1046241194533786",
        "currency": "USD",
        "timezone_name": "America/Sao_Paulo",
        "account_status": 1,
        "disable_reason": 0,
    }


def source_context(*, delay=60, current_date="2026-08-20"):
    return {"delay": {"totalMinutes": delay}, "current_date": current_date}


def run_actions(module, rows, campaigns, decision_at, *, anomaly=False, source=None):
    return module.execute_intraday_actions(
        rows,
        meta_account(),
        campaigns,
        source or source_context(),
        {"anomaly": anomaly, "spend_diff": 0.1},
        "2026-08-20",
        decision_at,
    )


def test_reporting_layouts_are_report_specific_and_no_id_rec():
    module = load_reports_module()
    assert module.recommendation(1, 27, 88, 8) == "ESCALAR +10%"
    assert module.recommendation(3, -11, -5, 12) == "CORTE APÓS GATE"
    assert module.daily_signal(1) == "🟢"
    assert module.daily_signal(-5) == "🟡"
    assert module.daily_signal(-10) == "🔴"
    assert "aligned_table" in inspect.getsource(module.build_daily)
    daily_source = inspect.getsource(module.build_daily)
    assert '"Lance"' in daily_source
    assert '"Budget"' in daily_source
    assert '"Custo"' in daily_source
    intraday_source = inspect.getsource(module.build_intraday)
    assert "table_pages" in intraday_source
    assert '"Lance"' in intraday_source
    assert '"Custo"' in intraday_source
    assert '"ROAS"' in intraday_source
    assert '["Sinal", "Camp"' in intraday_source
    assert "ID REC" not in SCRIPT.read_text()


def test_bid_strategy_labels_use_live_campaign_and_adset_fields():
    module = load_reports_module()
    assert module.bid_strategy_label(
        {"bid_strategy": "COST_CAP"},
        [{"bid_amount": 50}],
    ) == "CPA 0,50"
    assert module.bid_strategy_label(
        {"bid_strategy": "LOWEST_COST_WITHOUT_CAP"},
        [{}],
    ) == "MAXVOL"
    assert module.bid_strategy_label(
        {"bid_strategy": "LOWEST_COST_WITHOUT_CAP"},
        [{"bid_constraints": {"roas_average_floor": 10000}}],
    ) == "ROAS"


def test_intraday_report_cadence_and_action_checkpoint_are_separate():
    module = load_reports_module()
    expected_report_hours = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23}
    assert module.INTRADAY_REPORT_HOURS == expected_report_hours
    for hour in range(24):
        assert module.intraday_gate_due(hour, actions_only=False) is (hour in expected_report_hours)
        assert module.intraday_gate_due(hour, actions_only=True) is (hour == 8)


def test_campaign_column_is_compact_and_includes_date():
    module = load_reports_module()
    assert module.compact_campaign_label("07", "07 - 20-08 - Garagem Brasil") == "C07-20/08"
    assert module.compact_campaign_label("09", "09 - Garagem Brasil", "2026-08-20") == "C09-20/08"


def test_report_scope_discovers_new_live_campaigns_without_expanding_write_allowlist():
    module = load_reports_module()
    campaigns = [
        {"id": "7", "name": "07 - 20-08 - Garagem Brasil - (b01fb13c07) event_Subscribe", "status": "ACTIVE"},
        {"id": "12", "name": "12 - 21-08 - Garagem Brasil - (b01fb13c12) event_Subscribe - MAXVOL", "status": "ACTIVE"},
        {"id": "13", "name": "13 - 21-08 - Garagem Brasil - (b01fb13c13) event_Subscribe - MAXVOL", "status": "PAUSED"},
        {"id": "50", "name": "50 - old - (b01fb13c50) event_Subscribe", "status": "ARCHIVED"},
        {"id": "other", "name": "Unrelated account campaign", "status": "ACTIVE"},
    ]
    assert module.report_campaign_ids(campaigns) == ["7", "12", "13"]
    assert module.report_campaign_ids(campaigns, {"50": {"spend": 1}}, {}) == ["7", "12", "13", "50"]
    assert module.AUTONOMOUS_WRITE_NUMBERS == {"07", "08", "09", "10", "11"}


def test_new_campaign_cycle_date_comes_from_operational_name():
    module = load_reports_module()
    campaign = {
        "id": "12",
        "name": "12 - 21-08 - Garagem Brasil - (b01fb13c12) event_Subscribe - MAXVOL",
        "start_time": "2026-08-20T23:25:41-0300",
    }
    assert module.campaign_cycle_start_date(campaign, {}, datetime(2026, 8, 21).date()) == "2026-08-21"


def test_report_tables_paginate_instead_of_hiding_new_campaigns():
    module = load_reports_module()
    pages = module.table_pages(["Camp"], [[f"C{number:02d}"] for number in range(1, 15)], page_size=7)
    assert len(pages) == 2
    assert "C01" in pages[0]
    assert "C14" in pages[1]


def test_aligned_table_accounts_for_wide_emoji_cells():
    module = load_reports_module()
    rendered = module.aligned_table(
        ["Sinal", "Indicador"],
        [["⚪", "Spend Meta"], ["🔴", "Receita aquisição"]],
    )
    lines = rendered.splitlines()
    spend_line = next(line for line in lines if "Spend Meta" in line)
    revenue_line = next(line for line in lines if "Receita aquisição" in line)

    def visual_width(text):
        import unicodedata

        return sum(2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1 for char in text)

    assert visual_width(spend_line.split("Spend Meta")[0]) == visual_width(
        revenue_line.split("Receita aquisição")[0]
    )


def test_decision_boundaries_are_explicit():
    module = load_reports_module()
    assert module.recommendation(1, 19.999, None, 8) == "OBSERVAR D1/D2"
    assert module.recommendation(1, 20.0, None, 8) == "ESCALAR +10%"
    assert module.recommendation(1, 30.0, None, 8) == "ESCALAR +10%"
    assert module.recommendation(1, 30.001, None, 8) == "ESCALAR +20%"
    assert module.recommendation(1, 40.0, None, 8) == "ESCALAR +20%"
    assert module.recommendation(1, 40.001, None, 8) == "ESCALAR +30%"
    assert module.recommendation(3, -10.0, -1.0, 12) == "CORTE APÓS GATE"
    assert module.recommendation(3, -10.0, 1.0, 12) == "HOLD ESTIMADO"


def test_meta_cost_and_roas_use_omni_purchase():
    module = load_reports_module()
    aggregated = module.aggregate_meta(
        [
            {
                "campaign_id": "1",
                "campaign_name": "09 - Teste",
                "spend": "10.00",
                "actions": [{"action_type": "omni_purchase", "value": "20"}],
                "purchase_roas": [{"action_type": "omni_purchase", "value": "1.50"}],
            }
        ]
    )["1"]
    assert aggregated["cost_per_purchase"] == 0.5
    assert aggregated["purchase_roas"] == 1.5


def test_scale_is_single_attempt_written_once_and_verified(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    first, first_audit = run_actions(module, [scale_row()], [campaign], decision_at)
    assert first[0]["status"] == "executed"
    assert first[0]["verified"] is True
    assert fake_meta.campaigns["1"]["daily_budget"] == "3300"
    assert fake_meta.posts == [("1", {"daily_budget": "3300"})]
    assert Path(first_audit).exists()

    changed_tier = scale_row()
    changed_tier["recommendation"] = "ESCALAR +20%"
    second, second_audit = run_actions(module, [changed_tier], [campaign], decision_at)
    assert second[0]["status"] == "already_applied"
    assert fake_meta.posts == [("1", {"daily_budget": "3300"})]
    assert Path(second_audit).exists()


def test_scale_blocks_whole_batch_when_account_cap_would_be_exceeded(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    other = active_campaign(campaign_id="2", budget="27000", number="99")
    other["effective_status"] = "IN_PROCESS"
    fake_meta = FakeMeta([campaign, other])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta, account_cap=300)
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = run_actions(module, [scale_row()], [campaign, other], decision_at)
    assert results[0]["status"] == "blocked"
    assert results[0]["reason"] == "batch_account_operational_cap_exceeded"
    assert fake_meta.posts == []


def test_scale_blocks_outside_checkpoint_window(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    decision_at = datetime(2026, 8, 20, 8, 11, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = run_actions(module, [scale_row()], [campaign], decision_at)
    assert results[0]["reason"] == "outside_scale_checkpoint_window"
    assert fake_meta.posts == []


def test_scale_blocks_stale_smart_bidding_source(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = run_actions(module, [scale_row()], [campaign], decision_at, source=source_context(delay=121))
    assert results[0]["reason"] == "smart_bidding_source_stale_or_unknown"
    assert fake_meta.posts == []


def test_scale_blocks_campaign_number_collision(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    duplicate = active_campaign(campaign_id="2", number="09", status="PAUSED")
    fake_meta = FakeMeta([campaign, duplicate])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = run_actions(module, [scale_row()], [campaign, duplicate], decision_at)
    assert results[0]["reason"] == "campaign_number_collision_or_drift"
    assert fake_meta.posts == []


def test_scale_blocks_inactive_child_hierarchy(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    monkeypatch.setattr(
        module,
        "campaign_hierarchy_snapshot",
        lambda *args: (False, {"active_adsets": 1, "active_ads": 2}),
    )
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = run_actions(module, [scale_row()], [campaign], decision_at)
    assert results[0]["reason"] == "campaign_hierarchy_not_1x1x3_active"
    assert fake_meta.posts == []


def test_malformed_active_budget_fails_closed(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign(budget="NaN")
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    try:
        run_actions(module, [scale_row()], [campaign], decision_at)
    except RuntimeError as exc:
        assert "invalid daily_budget" in str(exc)
    else:
        raise AssertionError("malformed active budget must fail closed")
    assert fake_meta.posts == []


def test_historical_date_issues_zero_posts(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    try:
        run_actions(module, [scale_row()], [campaign], decision_at, source=source_context(current_date="2026-08-21"))
    except RuntimeError as exc:
        assert "historical or mismatched date" in str(exc)
    else:
        raise AssertionError("historical action must fail closed")
    assert fake_meta.posts == []


def test_cut_blocks_on_reconciliation_anomaly(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    row = scale_row()
    row["recommendation"] = "CORTE APÓS GATE"
    decision_at = datetime(2026, 8, 20, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = run_actions(module, [row], [campaign], decision_at, anomaly=True)
    assert results[0]["status"] == "blocked"
    assert results[0]["reason"] == "reconciliation_anomaly_gate"
    assert fake_meta.posts == []


def test_in_flight_scale_recovers_by_get_without_second_post(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign(budget="3300")
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    key = module._action_key("2026-08-20", 8, scale_row(), "ESCALAR +10%")
    module.atomic_write_json(
        module.ACTION_STATE,
        {
            "schema_version": "1.0",
            "applied": {
                key: {
                    "status": "in_flight",
                    "action_type": "scale_budget",
                    "expected_minor": 3000,
                    "requested_minor": 3300,
                }
            },
        },
    )

    results, _ = run_actions(module, [scale_row()], [campaign], decision_at)
    assert results[0]["status"] == "recovered_verified"
    assert fake_meta.posts == []


def test_report_delivery_is_idempotent_per_slot(monkeypatch, tmp_path):
    module = load_reports_module()
    monkeypatch.setattr(module, "DELIVERY_STATE", tmp_path / "delivery.json")
    monkeypatch.setattr(module, "DELIVERY_LOCK", tmp_path / "delivery.lock")
    posted = []
    text = "relatório curto"
    content_hash = hashlib.sha256(text.encode()).hexdigest()

    def fake_post(thread_id, body):
        posted.append((thread_id, body))
        return ["m1"]

    def fake_readback(thread_id, message_ids, expected_text=None):
        return {
            "ok": True,
            "messages": [
                {
                    "message_id": "m1",
                    "channel_id": str(thread_id),
                    "http_status": 200,
                    "content_length": len(text),
                    "content_sha256": content_hash,
                    "verified": True,
                }
            ],
        }

    monkeypatch.setattr(module, "post_discord", fake_post)
    monkeypatch.setattr(module, "readback_discord_messages", fake_readback)
    first = module.deliver_report_once("intraday:2026-08-20:12", "thread", text)
    second = module.deliver_report_once("intraday:2026-08-20:12", "thread", text)
    assert first[2] is False
    assert second[2] is True
    assert posted == [("thread", text)]


def test_approved_report_schedule_and_action_checkpoint():
    module = load_reports_module()
    assert module.DAILY_REPORT_HOURS == {7, 8, 11, 14, 20}
    assert module.intraday_gate_due(11, actions_only=False)
    assert module.intraday_gate_due(7, actions_only=False)
    assert module.intraday_gate_due(13, actions_only=False)
    assert not module.intraday_gate_due(14, actions_only=False)
    assert not module.intraday_gate_due(20, actions_only=False)
    assert module.intraday_gate_due(8, actions_only=True)
    assert not module.intraday_gate_due(11, actions_only=True)


def test_daily_period_is_previous_day_only_at_07_and_current_day_afterward():
    module = load_reports_module()
    sp = ZoneInfo("America/Sao_Paulo")
    assert module.daily_target_date(datetime(2026, 8, 20, 7, 0, tzinfo=sp)) == "2026-08-19"
    for hour in (8, 11, 14, 20):
        assert module.daily_target_date(datetime(2026, 8, 20, hour, 0, tzinfo=sp)) == "2026-08-20"
    assert module.daily_target_date(
        datetime(2026, 8, 20, 7, 0, tzinfo=sp),
        "2026-08-01",
    ) == "2026-08-01"


def test_snapshot_thread_history_scope_is_exact():
    module = load_reports_module()
    assert module.THREAD_HISTORY_SCOPE == {
        "creation": "1539826050765299872",
        "daily": "1539831487719800872",
        "intraday": "1539832402744975450",
    }


def test_snapshot_gate_is_daily_not_72_hourly(monkeypatch, tmp_path):
    module = load_reports_module()
    state = tmp_path / "snapshot-gate.json"
    monkeypatch.setattr(module, "SNAPSHOT_STATE", state)
    now_sp = datetime(2026, 8, 20, 3, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert module.snapshot_due(now_sp)
    state.write_text(json.dumps({"last_snapshot_sp": now_sp.isoformat()}))
    assert not module.snapshot_due(now_sp.replace(hour=4))
    assert module.snapshot_due(now_sp.replace(day=21))
