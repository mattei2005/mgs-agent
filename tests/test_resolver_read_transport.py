"""Read-only Discord retry budget; no replay of ambiguous writes."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import urllib.error
from unittest.mock import MagicMock

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'scripts'))
import mgs_automation_supervisor as supervisor
from mgs_automation_continuity import Queue

spec = importlib.util.spec_from_file_location('resolver_read_transport', BASE / 'scripts/alerts-infra-failed-alert-resolver.py')
assert spec and spec.loader
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


def response(value):
    result = MagicMock()
    result.__enter__.return_value = result
    result.status = 200
    result.read.return_value = json.dumps(value).encode()
    return result


def setup(monkeypatch, effects):
    calls = []
    waits = []
    pending = iter(effects)
    def open_request(req, timeout):
        calls.append(req.get_method())
        value = next(pending)
        if isinstance(value, Exception):
            raise value
        return response(value)
    monkeypatch.setattr(resolver.urllib.request, 'urlopen', open_request)
    monkeypatch.setattr(resolver.time, 'sleep', waits.append)
    monkeypatch.setattr(resolver, 'FETCH_RETRY_ATTEMPTS', 3)
    monkeypatch.setattr(resolver, 'FETCH_RETRY_BASE_SECONDS', 2)
    return calls, waits


@pytest.mark.parametrize('error', [urllib.error.URLError(ConnectionResetError(104, 'fixture')), ConnectionResetError(104, 'fixture'), TimeoutError('fixture')])
def test_exact_message_get_recovers_transport(monkeypatch, error):
    calls, waits = setup(monkeypatch, [error, {'id': '123'}])
    assert resolver.discord_api('offline', 'GET', '/channels/1/messages/123') == (200, {'id': '123'})
    assert calls == ['GET', 'GET'] and waits == [2]


def test_fetch_page_has_only_one_total_retry_budget(monkeypatch):
    errors = [urllib.error.HTTPError('fixture', 503, 'fixture', {}, io.BytesIO(b'{}')) for _ in range(3)]
    calls, waits = setup(monkeypatch, errors)
    with pytest.raises(RuntimeError, match='HTTP 503'):
        resolver._fetch_page('offline')
    assert len(calls) == 3 and waits == [2, 4]


def test_exhausted_transport_is_not_green(monkeypatch):
    calls, waits = setup(monkeypatch, [TimeoutError('fixture') for _ in range(3)])
    with pytest.raises(TimeoutError):
        resolver.discord_api('offline', 'GET', '/channels/1/messages/123')
    assert len(calls) == 3 and waits == [2, 4]


@pytest.mark.parametrize('method', ['POST', 'PATCH', 'DELETE'])
def test_ambiguous_write_never_replayed(monkeypatch, method):
    calls, waits = setup(monkeypatch, [ConnectionResetError(104, 'fixture')])
    with pytest.raises(ConnectionResetError):
        resolver.discord_api('offline', method, '/channels/1/messages', {'content': ''})
    assert calls == [method] and not waits


@pytest.mark.parametrize('status', [401, 403, 404])
def test_auth_and_missing_message_do_not_retry(monkeypatch, status):
    error = urllib.error.HTTPError('fixture', status, 'fixture', {}, io.BytesIO(b'{}'))
    calls, waits = setup(monkeypatch, [error])
    assert resolver.discord_api('offline', 'GET', '/channels/1/messages/123')[0] == status
    assert len(calls) == 1 and not waits


def test_rate_limit_uses_larger_body_or_header_delay(monkeypatch):
    error = urllib.error.HTTPError('fixture', 429, 'fixture', {'Retry-After': '7'}, io.BytesIO(b'{"retry_after": 3}'))
    calls, waits = setup(monkeypatch, [error, {'id': '123'}])
    assert resolver.discord_api('offline', 'GET', '/channels/1/messages/123')[0] == 200
    assert len(calls) == 2 and waits == [7]


def test_supervisor_legacy_get_reset_continues_to_healthy_tick(tmp_path, monkeypatch, capsys):
    q = Queue(tmp_path / 'queue.sqlite3')
    legacy = {'processed': {'123': {'status': 'continuity_owned'}}, 'last_seen_id': '123'}
    calls, waits = setup(monkeypatch, [urllib.error.URLError(ConnectionResetError(104, 'fixture')), {'id': '123', 'content': '', 'embeds': []}])
    monkeypatch.setattr(supervisor, 'Queue', lambda: q)
    monkeypatch.setattr(supervisor, 'collect', lambda: ({}, []))
    monkeypatch.setattr(supervisor, 'run_worker', lambda *a: pytest.fail('No business replay'))
    monkeypatch.setattr(resolver, 'load_token', lambda: 'offline')
    monkeypatch.setattr(resolver, 'load_state', lambda: legacy)
    monkeypatch.setattr(resolver, 'save_state', lambda *a: None)
    monkeypatch.setattr(resolver, 'fetch_messages', lambda *a, **k: [])
    monkeypatch.setattr(resolver, 'is_candidate', lambda *a: False)
    monkeypatch.setattr(sys, 'argv', ['offline-fixture'])
    assert supervisor.main(resolver) == 0
    lines = capsys.readouterr().out.splitlines()
    final = json.loads(lines[-1])
    assert final['ok'] is True and final['status'] == 'supervisor_tick_complete'
    assert calls == ['GET', 'GET'] and waits == [2]
    assert legacy['processed']['123']['status'] == 'continuity_owned'


def test_real_semantic_monitor_accepts_tick_boundary_after_old_traceback(tmp_path, monkeypatch):
    import os
    import subprocess
    log = tmp_path / 'resolver.log'
    log.write_text('Traceback (most recent call last):\nURLError: old fixture reset\n' +
                   json.dumps({'ok': True, 'status': 'supervisor_tick_complete'}) + '\n')
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    crontab = bin_dir / 'crontab'
    line = f'2-57/5 * * * * /root/mgs-agent/scripts/alerts-infra-failed-alert-resolver.py >> {log} 2>&1\n'
    crontab.write_text('#!/usr/bin/env python3\nprint(' + repr(line) + ', end="")\n')
    crontab.chmod(0o700)
    monkeypatch.setenv('PATH', str(bin_dir) + ':' + os.environ['PATH'])
    monkeypatch.setenv('CRON_STALE_STATE', str(tmp_path / 'state.json'))
    monkeypatch.delenv('MGS_MONITOR_NATIVE', raising=False)
    result = subprocess.run(['bash', str(BASE / 'scripts/monitor-cron-stale-logs.sh'), '--dry-run'],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0
    row = result.stdout.splitlines()[0].split('|')
    assert row[0].strip() == 'alerts-infra-failed-alert-resolver.py'
    assert row[1].strip() == 'OK'
    assert not (tmp_path / 'state.json').exists()
