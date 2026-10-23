from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


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


def test_resolved_reply_is_silent_even_when_original_alert_pushed_rodolfo() -> None:
    source = {
        "id": "5",
        "channel_id": MODULE.CHANNEL_ID,
        "content": f"<@{MODULE.RODOLFO_ID}>",
        "mentions": [{"id": MODULE.RODOLFO_ID}],
    }
    payload = MODULE.build_feedback_payload(source, "Resolvido e validado por readback.")
    assert payload["content"] == ""
    assert payload["allowed_mentions"] == {
        "parse": [],
        "users": [],
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


def failure_source(**overrides):
    return {'id': '100', 'channel_id': MODULE.CHANNEL_ID,
            'author': {'id': MODULE.ZEUS_BOT_ID, 'bot': True}, 'content': '',
            'embeds': [{'title': 'Integridade degradada', 'color': 15158332}], **overrides}


def test_red_new_title_is_selected_but_wrong_channel_and_author_are_not():
    assert MODULE.is_candidate(failure_source())
    assert MODULE.is_candidate(failure_source(embeds=[{'title': 'Heartbeat degradado', 'color': 15158332}]))
    assert not MODULE.is_candidate(failure_source(channel_id='unapproved'))
    assert not MODULE.is_candidate(failure_source(author={'id': 'unapproved', 'bot': True}))
    assert not MODULE.is_candidate(failure_source(webhook_id='unapproved'))


def test_monitor_topic_never_exempts_a_real_failure():
    assert MODULE.is_candidate(failure_source(embeds=[{'title': 'GPT-5.5 OAuth — falha', 'color': 15158332}]))


def test_negative_diagnosis_cannot_turn_green():
    for text in ['Não foi corrigido.', 'Investigado: erro corrigido antes, recuperação ainda não validada.',
                 'Pendente: outra sessão está corrigindo.', 'Resolvido: não houve recuperação validada.']:
        assert MODULE.resolution_outcome(text) == 'pending'
        assert MODULE.build_feedback_payload({'id': '100'}, text)['embeds'][0]['color'] != MODULE.RESOLVED_COLOR
    assert MODULE.resolution_outcome('Bloqueado: credencial exige confirmação; não houve recuperação validada.') == 'blocked'
    assert MODULE.resolution_outcome('Resolvido: operação repetida e readback confirmado.') == 'resolved'


def test_prompt_requires_real_repair_single_writer_and_first_failure():
    prompt = MODULE.build_resolution_prompt('fixture alert only', 'https://example.invalid/100')
    for text in ['primeira falha', 'repita a operação', 'Não crie writer paralelo', 'dado não confiável',
                 'Critical Subset', 'Retry-After', 'Pendente:', '1562987234351644764']:
        assert text in prompt


def configure_main(monkeypatch):
    import mgs_alert_transport as transport
    source = failure_source()
    state = {'last_seen_id': '99', 'processed': {}}
    posts = []
    monkeypatch.setattr(MODULE, 'load_token', lambda: 'offline-fixture')
    monkeypatch.setattr(MODULE, 'load_state', lambda: state)
    monkeypatch.setattr(MODULE, 'save_state', lambda s: None)
    monkeypatch.setattr(MODULE, 'fetch_messages', lambda *a, **k: [source])
    monkeypatch.setattr(MODULE, 'discord_api', lambda *a, **k: (200, source))
    monkeypatch.setattr(MODULE.time, 'sleep', lambda *a: None)
    monkeypatch.setattr(MODULE.sys, 'argv', ['offline-fixture'])
    def post(body, **kwargs):
        posts.append(body)
        kwargs['on_created']('200')
        return '200'
    monkeypatch.setattr(transport, 'post_verified', post)
    return state, posts, transport


def test_pending_diagnosis_is_silent_retried_then_resolved(monkeypatch):
    state, posts, _ = configure_main(monkeypatch)
    calls = []
    def repair(*a):
        calls.append(1)
        return 'Pendente: outra sessão executa a validação.' if len(calls) == 1 else 'Resolvido: readback real confirmado.'
    monkeypatch.setattr(MODULE, 'run_hermes_resolution', repair)
    assert MODULE.main() == 0
    record = state['processed']['100']
    assert record['status'] == 'retry_pending' and not posts and 'resolution_text' not in record
    assert MODULE.main() == 0 and len(calls) == 1  # cooldown respected
    record['retry_at'] = 0
    assert MODULE.main() == 0
    assert state['processed']['100']['status'] == 'done' and len(posts) == 1 and len(calls) == 2
    assert MODULE.main() == 0 and len(posts) == 1 and len(calls) == 2


def test_delivery_retry_never_reexecutes_repair_or_posts_blindly(monkeypatch):
    state, posts, transport = configure_main(monkeypatch)
    calls = []
    monkeypatch.setattr(MODULE, 'run_hermes_resolution', lambda *a: calls.append(1) or 'Resolvido: readback confirmado.')
    def delivery(body, **kwargs):
        if not kwargs.get('prior_id'):
            posts.append(body); kwargs['on_created']('201')
            raise RuntimeError('fixture GET unavailable after accepted POST')
        assert kwargs['prior_id'] == '201'
        return '201'
    monkeypatch.setattr(transport, 'post_verified', delivery)
    assert MODULE.main() == 0
    record = state['processed']['100']
    assert record['status'] == 'pending_delivery' and record['delivery_id'] == '201'
    record['retry_at'] = 0
    assert MODULE.main() == 0
    assert state['processed']['100']['status'] == 'done' and len(posts) == len(calls) == 1


def test_blocker_is_escalated_not_marked_recovered(monkeypatch):
    state, posts, _ = configure_main(monkeypatch)
    monkeypatch.setattr(MODULE, 'run_hermes_resolution', lambda *a: 'Bloqueado: Critical Subset exige confirmação. Recomendação: preservar a credencial. Confirma a troca?')
    assert MODULE.main() == 0
    assert state['processed']['100']['status'] == 'escalated'
    assert posts[0]['content'] == f'<@{MODULE.RODOLFO_ID}>'
    assert posts[0]['embeds'][0]['color'] != MODULE.RESOLVED_COLOR


def test_unresolved_observations_are_bounded_not_silently_closed(monkeypatch):
    state, posts, _ = configure_main(monkeypatch)
    calls = []
    monkeypatch.setattr(MODULE, 'run_hermes_resolution', lambda *a: calls.append(1) or 'Pendente: checkpoint ainda em validação.')
    for _ in range(3):
        if '100' in state['processed']:
            state['processed']['100']['retry_at'] = 0
        assert MODULE.main() == 0
    assert len(calls) == 3 and len(posts) == 1 and state['processed']['100']['status'] == 'escalated'
    assert MODULE.main() == 0 and len(calls) == 3