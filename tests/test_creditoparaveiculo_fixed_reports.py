from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

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
        if path == "act_1046241194533786":
            return 200, meta_account(), {}
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
    monkeypatch.setattr(module, "GUARDRAIL_STATE", tmp_path / "guardrail.json")
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
    assert module.recommendation(1, 20, 88, 8) == "MANTER SEM ESCALA"
    assert module.recommendation(3, -11, -5, 8, d3_negative_estimated_streak=True) == "PARAR D3 ESTIMADO"
    assert module.recommendation(2, -1, -2, 16, scaled_at_08=True) == "PAUSAR 16H TEMPORÁRIO"
    assert module.recommendation(4, -1, -2, 16, scaled_at_08=True, prior_16h_failures=2) == "PARAR RECORRÊNCIA"
    assert module.recommendation(2, -1, 2, 16, scaled_at_08=True) == "MANTER ESTIMADO POSITIVO"
    assert module.daily_signal(1) == "🟢"
    assert module.daily_signal(-5) == "🟡"
    assert module.daily_signal(-10) == "🔴"
    assert "aligned_table" in inspect.getsource(module.build_daily)
    daily_source = inspect.getsource(module.build_daily)
    assert '"Lance"' in daily_source
    assert '"Budget"' in daily_source
    assert '"Custo"' in daily_source
    assert "daily_mobile_card" in daily_source
    assert "campaign_mobile_cards" in daily_source
    assert "Tabela consolidada — visão desktop" in daily_source
    intraday_source = inspect.getsource(module.build_intraday)
    assert "intraday_mobile_card" in intraday_source
    assert "INTRADAY_CARD_DIVIDER" in intraday_source
    assert "desktop_table_rows" in intraday_source
    assert "table_pages" in intraday_source
    assert "Tabela consolidada — visão desktop" in intraday_source
    assert "Histórico ROI SB — visão desktop" in intraday_source
    assert "fetch_sb_roi_history" in intraday_source
    assert "ID REC" not in SCRIPT.read_text()


def test_intraday_mobile_card_matches_approved_discord_layout():
    module = load_reports_module()
    row = {
        "campaign_label": "C08-20/08",
        "lance": "MAXVOL",
        "cycle_day": 2,
        "status": "ACTIVE",
        "budget_usd": 39.0,
        "meta_spend": 11.77,
        "meta_cost": 0.08,
        "meta_roas": 1.64,
        "sb_roi": 45.4,
        "estimated_roi": 81.9,
        "roi_history": [
            {"date_label": "19/08", "roi": None, "partial": False},
            {"date_label": "20/08", "roi": -17.7, "partial": False},
            {"date_label": "21/08", "roi": 45.4, "partial": True},
        ],
    }
    assert module.INTRADAY_CARD_DIVIDER == "━" * 34
    assert module.intraday_mobile_card(row, "OBSERVAR D1/D2", "🟡") == (
        "🟡 **C08-20/08 · MAXVOL · D2 · ATIVA**\n"
        "👁️ **OBSERVAR · D1/D2**\n"
        "```text\n"
        "Budget $39,00    Spend $11,77\n"
        "Custo  $0,08     ROAS  1,64\n"
        "ROI real +45,4%  ROI est +81,9%\n"
        "\n"
        "ROI 19/08 n/d\n"
        "ROI 20/08 -17,7%\n"
        "ROI 21/08 +45,4% parcial\n"
        "```"
    )


def test_roi_history_aggregates_by_campaign_date_and_marks_current_partial():
    module = load_reports_module()
    rows = [
        {"CAMPAIGN_ID": "8", "DATE": "2026-08-20", "INVESTIMENT": 10, "NET_REVENUE": 8},
        {"CAMPAIGN_ID": "8", "DATE": "2026-08-20", "INVESTIMENT": 5, "NET_REVENUE": 7},
        {"CAMPAIGN_ID": "8", "DATE": "2026-08-19", "INVESTIMENT": 0, "NET_REVENUE": 0},
        {"CAMPAIGN_ID": "9", "DATE": "invalid", "INVESTIMENT": 1, "NET_REVENUE": 2},
    ]
    aggregated = module.aggregate_sb_daily_roi(rows)
    assert aggregated["8"]["2026-08-20"] == 0.0
    assert aggregated["8"]["2026-08-19"] is None
    history = module.campaign_roi_history(
        "8",
        "2026-08-21",
        30.3,
        aggregated,
        current_is_partial=True,
    )
    assert [item["date_label"] for item in history] == ["19/08", "20/08", "21/08"]
    assert [item["roi"] for item in history] == [None, 0.0, 30.3]
    assert [item["partial"] for item in history] == [False, False, True]


def test_roi_history_rejects_nonpositive_window():
    module = load_reports_module()
    with pytest.raises(ValueError, match="positive"):
        module.campaign_roi_history("8", "2026-08-21", None, {}, current_is_partial=False, days=0)


def test_daily_mobile_card_matches_approved_hybrid_layout():
    module = load_reports_module()
    row = {
        "campaign_label": "C07-20/08",
        "lance": "CPA 0,50",
        "status": "ACTIVE",
        "budget_usd": 30.0,
        "meta_spend": 11.93,
        "meta_cost": 0.12,
        "meta_roas": 1.08,
        "sb_roi": -5.9,
    }
    assert module.daily_mobile_card(row) == (
        "🟡 **C07-20/08 · CPA 0,50 · ATIVA**\n"
        "```text\n"
        "Budget $30,00    Spend $11,93\n"
        "Custo  $0,12     ROAS  1,08\n"
        "ROI SB  -5,9%\n"
        "```"
    )


def test_discord_chunking_keeps_mobile_cards_and_desktop_table_atomic():
    module = load_reports_module()
    base_row = {
        "campaign_label": "C08-20/08",
        "lance": "MAXVOL",
        "cycle_day": 2,
        "status": "ACTIVE",
        "budget_usd": 39.0,
        "meta_spend": 11.77,
        "meta_cost": 0.08,
        "meta_roas": 1.64,
        "sb_roi": 45.4,
        "estimated_roi": 81.9,
    }
    cards = []
    for number in range(7, 14):
        row = {**base_row, "campaign_label": f"C{number:02d}-20/08"}
        cards.append(module.intraday_mobile_card(row, "OBSERVAR D1/D2", "🟡"))
    table = module.aligned_table(
        ["Camp", "Spend", "Ação"],
        [[f"C{number:02d}-20/08", "$11,77", "OBSERVAR D1/D2"] for number in range(7, 14)],
    )
    history_table = module.aligned_table(
        ["Camp", "19/08", "20/08", "21/08"],
        [[f"C{number:02d}-20/08", "n/d", "-17,7%", "+45,4%*"] for number in range(7, 14)],
    )
    text = "\n\n".join([
        "Resumo",
        *cards,
        "Tabela consolidada — visão desktop",
        table,
        "Histórico ROI SB — visão desktop",
        history_table,
        "Spend monitorado: $82,39",
    ])
    chunks = module.split_message(text, limit=500)
    assert len(chunks) > 1
    assert all(chunk.count("```") % 2 == 0 for chunk in chunks)
    for atomic_section in [*cards, table, history_table]:
        assert sum(atomic_section in chunk for chunk in chunks) == 1
    discord_contents = module.discord_message_contents(text)
    assert all(len(content) <= 1900 for content in discord_contents)
    assert all(content.count("```") % 2 == 0 for content in discord_contents)


def test_chunking_preserves_blank_lines_inside_mobile_card_fences():
    module = load_reports_module()
    row = {
        "campaign_label": "C08-20/08",
        "lance": "MAXVOL",
        "cycle_day": 2,
        "status": "ACTIVE",
        "budget_usd": 39.0,
        "meta_spend": 11.77,
        "meta_cost": 0.08,
        "meta_roas": 1.64,
        "sb_roi": 45.4,
        "estimated_roi": 81.9,
        "roi_history": [
            {"date_label": "19/08", "roi": None, "partial": False},
            {"date_label": "20/08", "roi": -17.7, "partial": False},
            {"date_label": "21/08", "roi": 45.4, "partial": True},
        ],
    }
    card = module.intraday_mobile_card(row, "OBSERVAR D1/D2", "🟡")
    text = "\n\n".join(["Resumo", card, "Spend monitorado: $11,77"])
    sections = module.report_atomic_sections(text)
    assert card in sections
    contents, retried = module.discord_message_plan(text)
    assert retried is False
    assert all(content.count("```") % 2 == 0 for content in contents)


def test_oversized_fenced_table_gets_one_bounded_safe_retry():
    module = load_reports_module()
    table = module.aligned_table(
        ["Camp", "Spend", "Ação"],
        [[f"C{number:03d}-20/08", "$123,45", "OBSERVAR D1/D2 com detalhe operacional"] for number in range(1, 90)],
    )
    with pytest.raises(module.DiscordReportChunkingError, match="exceeds safe chunk"):
        module.split_message(table, limit=1875)
    contents, retried = module.discord_message_plan(table)
    assert retried is True
    assert len(contents) > 1
    assert all(len(content) <= 1900 for content in contents)
    assert all(content.count("```") % 2 == 0 for content in contents)
    assert all("Camp" in content and "Spend" in content and "Ação" in content for content in contents)


def test_malformed_fence_still_fails_closed_after_retry():
    module = load_reports_module()
    with pytest.raises(module.DiscordReportChunkingError, match="unbalanced fenced block"):
        module.discord_message_plan("Resumo\n\n```text\nlinha sem fechamento")


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
        assert module.intraday_gate_due(hour, actions_only=True) is (hour in {8, 16})


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
    zero_only_meta = {
        "28": {"name": "28 - Garagem Brasil - (b01fb13c28) event_Subscribe", "spend": 0},
    }
    zero_only_sb = {
        "34": {
            "name": "34 - Garagem Brasil - (b01fb13c34) event_Subscribe",
            "investment": 0,
            "net_revenue": 0,
            "utm_adgroups": ["b01fb13c34g01"],
        }
    }
    assert module.report_campaign_ids(campaigns, zero_only_meta, zero_only_sb) == ["7", "12", "13"]
    assert module.AUTONOMOUS_WRITE_NUMBERS == {"07", "08", "09", "10", "11", "12", "13"}


def test_metric_bearing_deleted_campaign_is_hydrated_by_id_and_snapshot(monkeypatch, tmp_path):
    module = load_reports_module()
    deleted = {
        "id": "old-11",
        "name": "11 - 20-08 - Garagem Brasil - (b01fb13c11) event_Subscribe",
        "status": "DELETED",
        "configured_status": "DELETED",
        "effective_status": "DELETED",
        "daily_budget": "3000",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
    }

    class HistoricalMeta(FakeMeta):
        def graph_get(self, path, token, params=None):
            if str(path) == "old-11/adsets":
                return 200, {"data": []}, {}
            return super().graph_get(path, token, params)

    fake_meta = HistoricalMeta([deleted])
    snapshot_root = tmp_path / "snapshots"
    snapshot_root.mkdir()
    (snapshot_root / "snapshot-20260821T060006Z.json").write_text(
        json.dumps(
            {
                "meta_adsets": [
                    {
                        "id": "old-11-adset",
                        "campaign_id": "old-11",
                        "bid_constraints": {"roas_average_floor": 10000},
                    }
                ]
            }
        )
    )
    monkeypatch.setattr(module, "SNAPSHOT_ROOT", snapshot_root)
    monkeypatch.setattr(module, "load_module", lambda path, name: fake_meta)

    campaigns, adsets, audit = module.hydrate_missing_report_campaigns([], [], ["old-11"])

    assert campaigns[0]["configured_status"] == "DELETED"
    assert campaigns[0]["daily_budget"] == "3000"
    assert module.bid_strategy_label(campaigns[0], adsets) == "ROAS"
    assert audit[0]["status"] == "DELETED"
    assert audit[0]["daily_budget_usd"] == 30.0
    assert audit[0]["adset_source"] == "continuity_snapshot"
    assert audit[0]["adset_count"] == 1
    assert audit[0]["credential"]["token_len"] == len("sanitized-test-token")


def test_metric_bearing_campaign_fails_closed_when_direct_readback_is_unavailable(monkeypatch):
    module = load_reports_module()
    fake_meta = FakeMeta([])
    monkeypatch.setattr(module, "load_module", lambda path, name: fake_meta)
    monkeypatch.setattr(module, "SNAPSHOT_ROOT", Path("/nonexistent"))

    with pytest.raises(RuntimeError, match="historical campaign readback failed"):
        module.hydrate_missing_report_campaigns([], [], ["missing-id"])


def test_new_campaign_cycle_date_comes_from_operational_name():
    module = load_reports_module()
    campaign = {
        "id": "12",
        "name": "12 - 21-08 - Garagem Brasil - (b01fb13c12) event_Subscribe - MAXVOL",
        "start_time": "2026-08-20T23:25:41-0300",
    }
    assert module.campaign_cycle_start_date(campaign, {}, datetime(2026, 8, 21).date()) == "2026-08-21"


def test_dynamic_v3_campaign_enters_autonomous_allowlist_only_with_readback_provenance(monkeypatch):
    module = load_reports_module()
    monkeypatch.setattr(module, "AUTONOMOUS_WRITE_NUMBERS", {"13"})
    operation = {
        "management_scope": {
            "autonomous_action_scope": {
                "allowed_campaigns": {
                    "13": {"campaign_id": "id-13", "cycle_start_date": "2026-08-21"},
                    "14": {
                        "campaign_id": "id-14",
                        "cycle_start_date": "2026-08-22",
                        "source": "campaign_engine_v3_daily_readback",
                        "request_id": "cpv-daily-20260821",
                    },
                }
            }
        }
    }
    assert set(module.validated_allowed_campaigns(operation)) == {"13", "14"}
    operation["management_scope"]["autonomous_action_scope"]["allowed_campaigns"]["14"].pop("request_id")
    with pytest.raises(RuntimeError, match="provenance"):
        module.validated_allowed_campaigns(operation)


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
    assert module.recommendation(1, None, None, 3) == "OBSERVAR D1/D2"
    assert module.recommendation(2, None, None, 3) == "OBSERVAR D1/D2"
    assert module.recommendation(3, None, None, 3) == "OBSERVAR"
    assert module.recommendation(1, 10.0, None, 8) == "OBSERVAR D1/D2"
    assert module.recommendation(1, 10.001, None, 8) == "MANTER SEM ESCALA"
    assert module.recommendation(1, 20.0, None, 8) == "MANTER SEM ESCALA"
    assert module.recommendation(1, 20.001, None, 8) == "ESCALAR +10%"
    assert module.recommendation(1, 30.0, None, 8) == "ESCALAR +10%"
    assert module.recommendation(1, 30.001, None, 8) == "ESCALAR +20%"
    assert module.recommendation(1, 40.0, None, 8) == "ESCALAR +20%"
    assert module.recommendation(1, 40.001, None, 8) == "ESCALAR +30%"
    assert module.recommendation(3, -10.0, -1.0, 12) == "OBSERVAR"
    assert module.recommendation(3, -10.0, -1.0, 8, d3_negative_estimated_streak=True) == "PARAR D3 ESTIMADO"


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


def test_d3_three_negative_estimated_mornings_pause_terminal(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    module.atomic_write_json(
        module.GUARDRAIL_STATE,
        {
            "schema_version": "1.0",
            "campaigns": {
                "1": {
                    "campaign_id": "1",
                    "campaign_number": "09",
                    "cycle_start_date": "2026-08-18",
                    "morning_estimated_roi": {
                        "2026-08-18": {"cycle_day": 1, "estimated_roi": -1.0},
                        "2026-08-19": {"cycle_day": 2, "estimated_roi": -2.0},
                    },
                    "consecutive_16h_failures": 0,
                }
            },
        },
    )
    row = {**scale_row(), "cycle_day": 3, "cycle_start_date": "2026-08-18", "estimated_roi": -0.1,
           "recommendation": "PARAR D3 ESTIMADO", "autonomous_write_eligible": True}
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = run_actions(module, [row], [campaign], decision_at)
    assert results[0]["status"] == "executed"
    assert fake_meta.posts == [("1", {"status": "PAUSED"})]
    state = json.loads(module.GUARDRAIL_STATE.read_text())
    assert state["campaigns"]["1"]["terminal"] is True
    assert "pending_reactivation" not in state["campaigns"]["1"]


def test_16h_first_negative_post_scale_pause_schedules_00_30(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    scale_key = module._action_key("2026-08-20", 8, scale_row(), "ESCALAR +10%")
    module.atomic_write_json(module.ACTION_STATE, {"schema_version": "1.0", "applied": {scale_key: {"status": "executed"}}})
    row = {**scale_row(), "cycle_day": 1, "cycle_start_date": "2026-08-20", "sb_roi": -1.0,
           "estimated_roi": -0.1, "recommendation": "PAUSAR 16H TEMPORÁRIO", "autonomous_write_eligible": True}
    decision_at = datetime(2026, 8, 20, 16, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = run_actions(module, [row], [campaign], decision_at)
    assert results[0]["status"] == "executed"
    state = json.loads(module.GUARDRAIL_STATE.read_text())["campaigns"]["1"]
    assert state["consecutive_16h_failures"] == 1
    assert state["pending_reactivation"]["due_date"] == "2026-08-21"
    assert state["pending_reactivation"]["due_time"] == "00:30"
    assert state["terminal"] is False


def test_16h_third_consecutive_failure_is_terminal(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    scale_key = module._action_key("2026-08-20", 8, scale_row(), "ESCALAR +10%")
    module.atomic_write_json(module.ACTION_STATE, {"schema_version": "1.0", "applied": {scale_key: {"status": "executed"}}})
    module.atomic_write_json(module.GUARDRAIL_STATE, {"schema_version": "1.0", "campaigns": {"1": {
        "campaign_id": "1", "campaign_number": "09", "cycle_start_date": "2026-08-20",
        "morning_estimated_roi": {}, "consecutive_16h_failures": 2}}})
    row = {**scale_row(), "cycle_day": 3, "cycle_start_date": "2026-08-20", "sb_roi": -1.0,
           "estimated_roi": -0.1, "recommendation": "PARAR RECORRÊNCIA", "autonomous_write_eligible": True}
    decision_at = datetime(2026, 8, 20, 16, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = run_actions(module, [row], [campaign], decision_at)
    assert results[0]["status"] == "executed"
    state = json.loads(module.GUARDRAIL_STATE.read_text())["campaigns"]["1"]
    assert state["terminal"] is True
    assert state["consecutive_16h_failures"] >= 3
    assert "pending_reactivation" not in state


def test_00_30_reactivates_only_verified_temporary_pause(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign(status="PAUSED")
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    module.atomic_write_json(module.GUARDRAIL_STATE, {"schema_version": "1.0", "campaigns": {"1": {
        "campaign_id": "1", "campaign_number": "09", "cycle_start_date": "2026-08-20",
        "morning_estimated_roi": {}, "consecutive_16h_failures": 1, "terminal": False,
        "pending_reactivation": {"provenance": "post_scale_16h", "due_date": "2026-08-21", "due_time": "00:30", "status": "pending"}}}})
    now_sp = datetime(2026, 8, 21, 0, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = module.execute_guardrail_reactivations(now_sp)
    assert results[0]["status"] == "executed"
    assert fake_meta.posts == [("1", {"status": "ACTIVE"})]
    state = json.loads(module.GUARDRAIL_STATE.read_text())["campaigns"]["1"]
    assert state["pending_reactivation"]["status"] == "completed"
    assert state["last_reactivation"]["status"] == "ACTIVE"


def test_00_30_reactivates_verified_first_delivery_pause_once(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign(status="PAUSED")
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    module.atomic_write_json(module.GUARDRAIL_STATE, {"schema_version": "1.0", "campaigns": {"1": {
        "campaign_id": "1", "campaign_number": "09", "cycle_start_date": "2026-08-21",
        "morning_estimated_roi": {}, "consecutive_16h_failures": 0, "terminal": False,
        "pending_reactivation": {"provenance": "first_delivery_guardrail", "one_shot": True,
                                 "due_date": "2026-08-21", "due_time": "00:30", "status": "pending"}}}})
    now_sp = datetime(2026, 8, 21, 0, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = module.execute_guardrail_reactivations(now_sp)
    assert results[0]["status"] == "executed"
    assert fake_meta.posts == [("1", {"status": "ACTIVE"})]
    state = json.loads(module.GUARDRAIL_STATE.read_text())["campaigns"]["1"]
    assert state["pending_reactivation"]["status"] == "completed"


def test_00_30_blocks_pending_reactivation_without_known_provenance(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign(status="PAUSED")
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    module.atomic_write_json(module.GUARDRAIL_STATE, {"schema_version": "1.0", "campaigns": {"1": {
        "campaign_id": "1", "campaign_number": "09", "cycle_start_date": "2026-08-21",
        "morning_estimated_roi": {}, "consecutive_16h_failures": 0, "terminal": False,
        "pending_reactivation": {"due_date": "2026-08-21", "due_time": "00:30", "status": "pending"}}}})
    now_sp = datetime(2026, 8, 21, 0, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, audit = module.execute_guardrail_reactivations(now_sp)
    assert results == []
    assert audit is None
    assert fake_meta.posts == []


def test_00_30_never_reactivates_terminal_pause(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign(status="PAUSED")
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    module.atomic_write_json(module.GUARDRAIL_STATE, {"schema_version": "1.0", "campaigns": {"1": {
        "campaign_id": "1", "campaign_number": "09", "cycle_start_date": "2026-08-20",
        "morning_estimated_roi": {}, "consecutive_16h_failures": 3, "terminal": True,
        "pending_reactivation": {"provenance": "post_scale_16h", "due_date": "2026-08-21", "due_time": "00:30", "status": "pending"}}}})
    now_sp = datetime(2026, 8, 21, 0, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, audit = module.execute_guardrail_reactivations(now_sp)
    assert results == []
    assert audit is None
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
    assert module.DAILY_REPORT_HOURS == {7, 8, 12, 14, 16, 20}
    assert module.intraday_gate_due(11, actions_only=False)
    assert module.intraday_gate_due(7, actions_only=False)
    assert module.intraday_gate_due(13, actions_only=False)
    assert not module.intraday_gate_due(14, actions_only=False)
    assert not module.intraday_gate_due(20, actions_only=False)
    assert module.intraday_gate_due(8, actions_only=True)
    assert module.intraday_gate_due(16, actions_only=True)
    assert not module.intraday_gate_due(11, actions_only=True)


def test_daily_period_is_previous_day_only_at_07_and_current_day_afterward():
    module = load_reports_module()
    sp = ZoneInfo("America/Sao_Paulo")
    assert module.daily_target_date(datetime(2026, 8, 20, 7, 0, tzinfo=sp)) == "2026-08-19"
    for hour in (8, 12, 14, 16, 20):
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
