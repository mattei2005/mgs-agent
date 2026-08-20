from __future__ import annotations

import importlib.util
import hashlib
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
        row = self.campaigns.get(str(path))
        if row is None:
            return 404, {"error": {"message": "not found"}}, {}
        return 200, dict(row), {}

    def graph_post(self, path, token, params=None):
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
    operation = {
        "operation_id": "Creditoparaveiculo-BR-CAR-BR",
        "management_scope": {
            "write_enabled": True,
            "reporting_mode": "autonomous_guarded",
            "manual_holds": [],
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


def active_campaign(campaign_id="1", budget="3000"):
    return {
        "id": campaign_id,
        "name": "09 - 20-08 - Garagem Brasil",
        "status": "ACTIVE",
        "configured_status": "ACTIVE",
        "effective_status": "ACTIVE",
        "daily_budget": budget,
        "updated_time": "2026-08-20T08:00:00-0300",
    }


def scale_row(campaign_id="1", budget_usd=30.0):
    return {
        "number": "09",
        "campaign_id": campaign_id,
        "name": "09 - 20-08 - Garagem Brasil",
        "budget_usd": budget_usd,
        "recommendation": "ESCALAR +10%",
    }


def test_reporting_signals_and_no_wide_table_or_id_rec():
    module = load_reports_module()
    assert module.recommendation(1, 27, 88, 8) == "ESCALAR +10%"
    assert module.recommendation(3, -11, -5, 12) == "CORTE APÓS GATE"
    assert module.daily_signal(1) == "🟢"
    assert module.daily_signal(-5) == "🟡"
    assert module.daily_signal(-10) == "🔴"
    source = SCRIPT.read_text()
    assert "aligned_table" not in source
    assert "ID REC" not in source


def test_scale_is_written_once_and_verified(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    first, first_audit = module.execute_intraday_actions(
        [scale_row()], [campaign], {"anomaly": False, "spend_diff": 0.1}, "2026-08-20", decision_at
    )
    assert first[0]["status"] == "executed"
    assert first[0]["verified"] is True
    assert fake_meta.campaigns["1"]["daily_budget"] == "3300"
    assert fake_meta.posts == [("1", {"daily_budget": "3300"})]
    assert Path(first_audit).exists()

    changed_tier = scale_row()
    changed_tier["recommendation"] = "ESCALAR +20%"
    second, second_audit = module.execute_intraday_actions(
        [changed_tier], [campaign], {"anomaly": False, "spend_diff": 0.1}, "2026-08-20", decision_at
    )
    assert second[0]["status"] == "already_applied"
    assert fake_meta.posts == [("1", {"daily_budget": "3300"})]
    assert Path(second_audit).exists()


def test_scale_blocks_account_cap(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    other = active_campaign(campaign_id="2", budget="27000")
    other["effective_status"] = "IN_PROCESS"
    fake_meta = FakeMeta([campaign, other])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta, account_cap=300)
    decision_at = datetime(2026, 8, 20, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = module.execute_intraday_actions(
        [scale_row()], [campaign, other], {"anomaly": False}, "2026-08-20", decision_at
    )
    assert results[0]["status"] == "blocked"
    assert results[0]["reason"] == "account_operational_cap_exceeded"
    assert fake_meta.posts == []


def test_cut_blocks_on_reconciliation_anomaly(monkeypatch, tmp_path):
    module = load_reports_module()
    campaign = active_campaign()
    fake_meta = FakeMeta([campaign])
    configure_runtime(monkeypatch, tmp_path, module, fake_meta)
    row = scale_row()
    row["recommendation"] = "CORTE APÓS GATE"
    decision_at = datetime(2026, 8, 20, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))

    results, _ = module.execute_intraday_actions(
        [row], [campaign], {"anomaly": True, "spend_diff": 2.0}, "2026-08-20", decision_at
    )
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

    results, _ = module.execute_intraday_actions(
        [scale_row()], [campaign], {"anomaly": False}, "2026-08-20", decision_at
    )
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
