"""Unit fixtures for the detached handoff gate; no restart or Discord API calls."""
import importlib.util
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def closure(monkeypatch):
    path = '/root/mgs-agent/data/discord-thread-suffix-activation-1557017992934727691.py'
    spec = importlib.util.spec_from_file_location('suffix_closure_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'transport', MagicMock())
    monkeypatch.setattr(module, 'audit', MagicMock())
    return module


@pytest.mark.parametrize('author', ['344196393512075265', '1496296175014252634'])
def test_missing_or_wrong_handoff_never_starts_restart(closure, monkeypatch, author):
    message = dict(id=str(int(closure.ACTIVATION_AUTH) + 1), author={'id': author},
                   content='**Ativação segura agendada.**' if author != '1496296175014252634' else 'Ainda investigando')
    monkeypatch.setattr(closure, 'api', MagicMock(return_value=[message]))
    monkeypatch.setattr(closure.time, 'monotonic', MagicMock(side_effect=[0, 181]))
    run = MagicMock()
    monkeypatch.setattr(closure.subprocess, 'run', run)
    with pytest.raises(RuntimeError, match='handoff_answer_not_observed_no_restart_executed'):
        closure.activate(SimpleNamespace(finalizer='fixture-finalizer', log='fixture-log'))
    run.assert_not_called()


def test_delivered_handoff_precedes_canonical_finalizer(closure, monkeypatch):
    message = dict(id=str(int(closure.ACTIVATION_AUTH) + 1),
                   author={'id': '1496296175014252634'}, content='**Ativação segura agendada.**')
    monkeypatch.setattr(closure, 'api', MagicMock(return_value=[message]))
    run = MagicMock(side_effect=RuntimeError('fixture_stop_before_any_real_restart'))
    monkeypatch.setattr(closure.subprocess, 'run', run)
    with pytest.raises(RuntimeError, match='fixture_stop_before_any_real_restart'):
        closure.activate(SimpleNamespace(finalizer='fixture-finalizer', log='fixture-log'))
    assert closure.audit.call_args.args[0] == 'discord_thread_suffix_handoff_confirmed'
    assert run.call_args.args[0] == ['bash', 'fixture-finalizer']


def test_report_is_updated_in_place_and_read_back(closure, monkeypatch):
    stored = {'id': 'fixture', 'channel_id': closure.REPORT_CHANNEL, 'content': '',
              'embeds': [{'fields': [{'name': 'Evidência', 'value': 'Pending'}]}]}
    calls = []

    def api(method, route, payload=None):
        calls.append((method, route))
        if method == 'PATCH':
            assert payload['content'] == ''
            assert payload['allowed_mentions'] == {'parse': []}
            stored.update({k: payload[k] for k in ('content', 'embeds')})
        return stored

    monkeypatch.setattr(closure, 'api', api)
    closure.update_report('fixture', 'Validated fixture evidence')
    assert [method for method, _ in calls] == ['GET', 'PATCH', 'GET']
    assert len({route for _, route in calls}) == 1
