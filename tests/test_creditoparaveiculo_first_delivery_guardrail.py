from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

SCRIPT = Path("/root/.hermes/profiles/ares/scripts/creditoparaveiculo-first-delivery-guardrail.py")
WRAPPER = Path("/root/.hermes/profiles/ares/scripts/creditoparaveiculo-first-delivery-guardrail.sh")
OPERATION = Path("/root/mgs-agent/data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json")


def load_module():
    spec = importlib.util.spec_from_file_location("cpv_first_delivery_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_canonical_rename_changes_only_operational_date():
    module = load_module()
    before = "14 - 22-08 - Garagem Brasil - (b01fb13c14) event_Subscribe - MAXVOL"
    after = module.rename_for_operational_date(before, "2026-08-23")
    assert after == "14 - 23-08 - Garagem Brasil - (b01fb13c14) event_Subscribe - MAXVOL"
    assert "b01fb13c14" in after
    assert "MAXVOL" in after


def test_noncanonical_name_fails_closed():
    module = load_module()
    with pytest.raises(RuntimeError, match="canonical operational date"):
        module.rename_for_operational_date("campaign without date", "2026-08-23")


def test_operation_contract_auto_enrolls_with_00_30_to_02_00_grace():
    operation = json.loads(OPERATION.read_text())
    policy = operation["first_delivery_guardrail"]
    assert policy["enabled"] is True
    assert policy["watch_interval_minutes"] == 15
    assert policy["automatic_enrollment"] == "every validated new production campaign after Campaign Engine v3 readback"
    assert policy["grace_window"] == "00:30 through 02:00 inclusive America/Sao_Paulo"
    assert policy["trigger"] == "first_observed_spend_after_02_00_grace_window"
    assert policy["reactivation_time"] == "00:30 America/Sao_Paulo next day"
    assert policy["one_shot"] is True
    assert policy["repeat_after_safe_release_or_verified_reactivation"] is False
    assert policy["provenance_required_for_reactivation"] == "first_delivery_guardrail"


def test_first_spend_grace_window_is_inclusive_at_00_30_and_02_00():
    module = load_module()
    sp = ZoneInfo("America/Sao_Paulo")
    target = {"cycle_start_date": "2026-08-23"}
    assert not module.in_first_spend_grace_window(target, datetime(2026, 8, 23, 0, 29, tzinfo=sp))
    assert module.in_first_spend_grace_window(target, datetime(2026, 8, 23, 0, 30, tzinfo=sp))
    assert module.in_first_spend_grace_window(target, datetime(2026, 8, 23, 1, 59, tzinfo=sp))
    assert module.in_first_spend_grace_window(target, datetime(2026, 8, 23, 2, 0, 59, tzinfo=sp))
    assert not module.in_first_spend_grace_window(target, datetime(2026, 8, 23, 2, 1, tzinfo=sp))
    assert not module.in_first_spend_grace_window(target, datetime(2026, 8, 24, 1, 0, tzinfo=sp))


def test_wrapper_is_script_only_quiet_watch():
    text = WRAPPER.read_text()
    assert "--watch --quiet" in text
    assert "source /root/mgs-agent/.env" in text
    assert "--arm" not in text


def test_auto_arm_adds_new_v3_campaign_without_meta_write(monkeypatch, tmp_path):
    module = load_module()
    now_sp = datetime.now(ZoneInfo("America/Sao_Paulo"))
    operational_date = (now_sp.date() + timedelta(days=1)).isoformat()
    label = (now_sp.date() + timedelta(days=1)).strftime("%d-%m")
    campaign_id = "new-campaign-17"
    campaign = {
        "id": campaign_id,
        "name": f"17 - {label} - Garagem Brasil - (b01fb13c17) event_Subscribe - MAXVOL",
        "status": "ACTIVE",
        "configured_status": "ACTIVE",
        "effective_status": "ACTIVE",
        "daily_budget": "3000",
    }

    class FakeMeta:
        def get_token_from_1password(self, item, force_refresh=False):
            return "test-token", "token"

        def graph_get(self, path, token, params=None):
            if path == "act_1046241194533786/insights":
                return 200, {"data": []}, {}
            if path == campaign_id:
                return 200, dict(campaign), {}
            raise AssertionError(path)

    operation_path = tmp_path / "operation.json"
    operation_path.write_text(json.dumps({
        "operation_id": "Creditoparaveiculo-BR-CAR-BR",
        "first_delivery_guardrail": {
            "enabled": True,
            "trigger": "first_observed_spend_after_02_00_grace_window",
            "reactivation_time": "00:30 America/Sao_Paulo next day",
            "automatic_enrollment": "every validated new production campaign after Campaign Engine v3 readback",
            "grace_window": "00:30 through 02:00 inclusive America/Sao_Paulo",
        },
        "management_scope": {"autonomous_action_scope": {"allowed_campaigns": {
            "17": {"campaign_id": campaign_id, "cycle_start_date": operational_date,
                   "source": "campaign_engine_v3_daily_readback", "request_id": "request-17"}
        }}},
    }))
    performance = tmp_path / "performance.json"

    def atomic(path, payload):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload))

    fixed = SimpleNamespace(
        OP_PATH=operation_path,
        META_COMMON=Path("common.py"),
        META_ITEM="item",
        ACCOUNT_ACT="act_1046241194533786",
        ACTION_LOCK=tmp_path / "action.lock",
        GUARDRAIL_STATE=performance,
        load_module=lambda path, name: FakeMeta(),
        validated_allowed_campaigns=lambda operation: operation["management_scope"]["autonomous_action_scope"]["allowed_campaigns"],
        as_float=lambda value: float(value or 0),
        load_guardrail_state=lambda: json.loads(performance.read_text()) if performance.exists() else {"schema_version": "1.0", "campaigns": {}},
        atomic_write_json=atomic,
    )
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "first-delivery.json")
    monkeypatch.setattr(module, "STATE_LOCK", tmp_path / "first-delivery.lock")
    monkeypatch.setattr(module, "AUDIT_ROOT", tmp_path / "audit")

    result = module.auto_arm_created(fixed, [campaign_id], operational_date, "request-17")

    assert result["status"] == "AUTO_ARMED"
    assert result["armed_count"] == 1
    assert result["meta_writes"] == 0
    target = json.loads(module.STATE_PATH.read_text())["targets"][campaign_id]
    assert target["status"] == "armed"
    assert target["enrollment_source"] == "campaign_engine_v3_postprocess"
    assert target["request_id"] == "request-17"
    assert target["cycle_start_date"] == operational_date


def test_first_spend_pauses_once_and_queues_next_0030(monkeypatch, tmp_path):
    module = load_module()

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = datetime(2026, 8, 23, 3, 0, tzinfo=module.SP)
            return value if tz is None else value.astimezone(tz)

    monkeypatch.setattr(module, "datetime", FixedDatetime)
    campaign_id = "campaign-7"
    campaign = {
        "id": campaign_id,
        "name": "07 - 23-08 - Garagem Brasil - (b01fb13c07) event_Subscribe - MAXVOL",
        "status": "ACTIVE",
        "configured_status": "ACTIVE",
        "effective_status": "ACTIVE",
        "daily_budget": "3000",
        "updated_time": "2026-08-22T14:00:00-0300",
    }

    class FakeMeta:
        def __init__(self):
            self.posts = []

        def get_token_from_1password(self, item, force_refresh=False):
            return "test-token", "token"

        def graph_get(self, path, token, params=None):
            if path == "act_1046241194533786/insights":
                return 200, {"data": [{"campaign_id": campaign_id, "spend": "0.25", "impressions": "10"}]}, {}
            if path == "act_1046241194533786":
                return 200, {
                    "id": "act_1046241194533786", "currency": "USD",
                    "timezone_name": "America/Sao_Paulo", "account_status": 1, "disable_reason": 0,
                }, {}
            if path == campaign_id:
                return 200, dict(campaign), {}
            raise AssertionError(path)

        def graph_post_once(self, path, token, params=None):
            payload = dict(params or {})
            self.posts.append((path, payload))
            if "status" in payload:
                campaign["status"] = payload["status"]
                campaign["configured_status"] = payload["status"]
                campaign["effective_status"] = payload["status"]
            if "name" in payload:
                campaign["name"] = payload["name"]
            return 200, {"success": True}, {}

    fake_meta = FakeMeta()
    operation_path = tmp_path / "operation.json"
    operation_path.write_text(json.dumps({
        "operation_id": "Creditoparaveiculo-BR-CAR-BR",
        "first_delivery_guardrail": {
            "enabled": True,
            "trigger": "first_observed_spend_after_02_00_grace_window",
            "reactivation_time": "00:30 America/Sao_Paulo next day",
            "automatic_enrollment": "every validated new production campaign after Campaign Engine v3 readback",
            "grace_window": "00:30 through 02:00 inclusive America/Sao_Paulo",
        },
        "management_scope": {
            "manual_holds": [],
            "autonomous_action_scope": {"allowed_campaigns": {
                "07": {"campaign_id": campaign_id, "cycle_start_date": "2026-08-23"}
            }},
        },
    }))
    action_lock = tmp_path / "action.lock"
    guardrail_state = tmp_path / "performance.json"

    def atomic(path, payload):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload))

    fixed = SimpleNamespace(
        OP_PATH=operation_path,
        META_COMMON=Path("common.py"),
        META_ITEM="item",
        ACCOUNT_ACT="act_1046241194533786",
        ACCOUNT_ID="1046241194533786",
        ACTION_LOCK=action_lock,
        GUARDRAIL_STATE=guardrail_state,
        THREAD_INTRADAY="thread",
        load_module=lambda path, name: fake_meta,
        validated_allowed_campaigns=lambda operation: operation["management_scope"]["autonomous_action_scope"]["allowed_campaigns"],
        as_float=lambda value: float(value or 0),
        campaign_hierarchy_snapshot=lambda meta, token, cid: (True, {"active_adsets": 1, "active_ads": 3}),
        bounded_campaign_readback=lambda meta, token, cid, desired_status=None: (
            campaign["status"] == desired_status, 200, dict(campaign)
        ),
        _safe_error=lambda meta, payload: {"safe": True},
        load_guardrail_state=lambda: json.loads(guardrail_state.read_text()) if guardrail_state.exists() else {"schema_version": "1.0", "campaigns": {}},
        atomic_write_json=atomic,
        post_discord=lambda thread, text: ["message-1"],
        readback_discord_messages=lambda thread, ids, expected_text=None: {"ok": True, "messages": [{"verified": True}]},
    )
    monkeypatch.setattr(module, "STATE_PATH", tmp_path / "first-delivery.json")
    monkeypatch.setattr(module, "STATE_LOCK", tmp_path / "first-delivery.lock")
    monkeypatch.setattr(module, "OP_LOCK", tmp_path / "operation.lock")
    monkeypatch.setattr(module, "AUDIT_ROOT", tmp_path / "audit")
    module.atomic_json(module.STATE_PATH, {
        "schema_version": "1.0",
        "targets": {campaign_id: {
            "campaign_id": campaign_id,
            "campaign_number": "07",
            "after_name": campaign["name"],
            "status": "armed",
            "watch_since_date": "2026-08-22",
            "cycle_start_date": "2026-08-23",
        }},
    })

    result = module.watch_once(fixed)

    assert result["status"] == "PAUSED_AND_QUEUED"
    assert fake_meta.posts[0] == (campaign_id, {"status": "PAUSED"})
    assert result["results"][0]["verified"] is True
    due = (FixedDatetime.now(ZoneInfo("America/Sao_Paulo")).date() + timedelta(days=1)).isoformat()
    performance = json.loads(guardrail_state.read_text())["campaigns"][campaign_id]
    assert performance["pending_reactivation"]["provenance"] == "first_delivery_guardrail"
    assert performance["pending_reactivation"]["due_date"] == due
    assert performance["pending_reactivation"]["due_time"] == "00:30"
    assert performance["pending_reactivation"]["one_shot"] is True
