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