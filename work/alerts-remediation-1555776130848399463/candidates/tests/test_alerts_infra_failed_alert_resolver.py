from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "alerts-infra-failed-alert-resolver.py"
SPEC = importlib.util.spec_from_file_location("alerts_infra_failed_alert_resolver", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_zeus_monitor_failure_embed_is_candidate() -> None:
    message = {
        "id": "1",
        "author": {"id": MODULE.ZEUS_BOT_ID, "username": "Zeus", "bot": True},
        "content": "<@344196393512075265> alerta de auto-push",
        "embeds": [{
            "title": "Auto-push falhando",
            "fields": [
                {"name": "Falhas consecutivas", "value": "3"},
                {"name": "Último erro", "value": "auto-commit bloqueado"},
            ],
        }],
    }
    assert MODULE.is_candidate(message) is True


def test_resolver_feedback_from_zeus_is_not_candidate() -> None:
    message = {
        "id": "2",
        "author": {"id": MODULE.ZEUS_BOT_ID, "username": "Zeus", "bot": True},
        "content": "",
        "embeds": [{
            "title": "✅ ALERTA CORRIGIDO",
            "description": "Falha corrigida e validada.",
            "footer": {"text": "Zeus · retorno automático do alerta"},
        }],
    }
    assert MODULE.is_candidate(message) is False


def test_report_infra_from_zeus_is_not_candidate() -> None:
    message = {
        "id": "3",
        "author": {"id": MODULE.ZEUS_BOT_ID, "username": "Zeus", "bot": True},
        "content": "",
        "embeds": [{"title": "REPORT-INFRA", "description": "script modificado"}],
    }
    assert MODULE.is_candidate(message) is False


def test_plain_human_message_is_not_candidate() -> None:
    message = {
        "id": "4",
        "author": {"id": "123", "username": "human", "bot": False},
        "content": "estou com um erro",
        "embeds": [],
    }
    assert MODULE.is_candidate(message) is False


def test_resolved_reply_pushes_rodolfo_when_original_alert_pushed_him() -> None:
    source = {
        "id": "5",
        "channel_id": MODULE.CHANNEL_ID,
        "content": f"<@{MODULE.RODOLFO_ID}>",
        "mentions": [{"id": MODULE.RODOLFO_ID}],
    }
    payload = MODULE.build_feedback_payload(source, "Resolvido e validado por readback.")
    assert payload["content"] == f"<@{MODULE.RODOLFO_ID}>"
    assert payload["allowed_mentions"] == {
        "parse": [],
        "users": [MODULE.RODOLFO_ID],
        "roles": [],
        "replied_user": False,
    }
    assert payload["message_reference"]["message_id"] == source["id"]
    assert payload["embeds"][0]["title"] == "✅ ALERTA CORRIGIDO"


def test_resolution_without_original_push_remains_silent() -> None:
    source = {"id": "6", "channel_id": MODULE.CHANNEL_ID, "content": "", "mentions": []}
    payload = MODULE.build_feedback_payload(source, "Corrigido e validado.")
    assert payload["content"] == ""
    assert payload["allowed_mentions"]["users"] == []


def test_investigation_does_not_push_even_when_original_alert_pushed() -> None:
    source = {
        "id": "7",
        "channel_id": MODULE.CHANNEL_ID,
        "content": f"<@{MODULE.RODOLFO_ID}>",
        "mentions": [{"id": MODULE.RODOLFO_ID}],
    }
    payload = MODULE.build_feedback_payload(source, "Investigado; decisão ainda necessária.")
    assert payload["content"] == ""
    assert payload["allowed_mentions"]["users"] == []
    assert payload["embeds"][0]["title"] == "🔎 ALERTA INVESTIGADO"