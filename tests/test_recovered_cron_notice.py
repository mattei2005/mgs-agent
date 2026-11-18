"""Canonical recovery notices are not failures, even with 'failed' in filenames."""
import copy
import importlib.util
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'scripts'))
import mgs_automation_supervisor as supervisor
from mgs_automation_continuity import Queue

spec = importlib.util.spec_from_file_location('recovery_notice_resolver', BASE / 'scripts/alerts-infra-failed-alert-resolver.py')
assert spec and spec.loader
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


def notice():
    return {'id': '1572623689839542407', 'channel_id': resolver.CHANNEL_ID,
            'timestamp': '2026-11-18T14:45:05.593000+00:00', 'content': '',
            'author': {'id': resolver.ZEUS_BOT_ID, 'bot': True},
            'embeds': [{'title': 'Cron recuperado', 'color': 3066993,
                        'description': '`alerts-infra-failed-alert-resolver.py` voltou a ter o sinal monitorado saudável (log/execução/entrega).'}]}


def health():
    return {'producer:alerts-infra-failed-alert-resolver.py': {
        'status': 'OK', 'verified': True, 'target': 'producer:alerts-infra-failed-alert-resolver.py',
        'receipt': 'monitor-predicate:age=1min threshold=20min', 'at': 1795015200}}


def test_canonical_notice_not_failure_despite_failed_filename():
    assert resolver.FAILURE_RE.search(resolver.extract_message_text(notice()))
    assert resolver.recovered_cron_script(notice()) == 'alerts-infra-failed-alert-resolver.py'
    assert not resolver.is_candidate(notice())


def test_real_failure_and_mixed_embeds_still_actionable():
    m = notice()
    m['embeds'][0]['color'] = 15158332
    assert resolver.is_candidate(m)
    m = notice()
    m['embeds'].append({'title': 'Falha nova', 'color': 15158332})
    assert resolver.is_candidate(m)
    m = notice()
    m['embeds'][0]['description'] += ' Erro ainda presente.'
    assert resolver.is_candidate(m)


def test_untrusted_or_wrong_channel_not_recovery():
    for changes in [{'channel_id': 'other'}, {'author': {'id': 'other', 'bot': True}}, {'webhook_id': 'other'}]:
        m = notice()
        m.update(changes)
        assert resolver.recovered_cron_script(m) is None


def test_exact_alert_observation_requires_fresh_same_producer():
    m = notice()
    obs = supervisor.recovered_notice_observation(m, health(), resolver)
    assert obs['target'] == 'alert:' + m['id']
    assert obs['receipt']['message_id'] == m['id']
    assert supervisor.recovered_notice_observation(m, {}, resolver) is None
    h = health()
    row = next(iter(h.values()))
    for changes in [{'status': 'ERROR'}, {'verified': False}, {'at': 1}]:
        other = copy.deepcopy(h)
        next(iter(other.values())).update(changes)
        assert supervisor.recovered_notice_observation(m, other, resolver) is None


def test_queue_closes_same_notice_without_replay_but_preserves_owner_and_gate(tmp_path):
    m = notice()
    obs = supervisor.recovered_notice_observation(m, health(), resolver)
    q = Queue(tmp_path / 'queue.sqlite3')
    try:
        row = q.enqueue(obs['target'], {'kind': 'alert', 'profile': 'zeus'}, 'alert_unresolved', now=1795014434)
        calls = []
        def run(*args):
            calls.append(args)
            return 'Pendente: fixture'
        supervisor.drive(q, {obs['target']: obs}, run, lambda: False, lambda s: True, lambda *a: None, now=1795015300)
        assert q.get(row['key'])['state'] == 'waiting_resource'
        q.defer(row['key'], 'blocked_decision', 'fixture_gate', now=1795015300, delay=1)
        supervisor.drive(q, {obs['target']: obs}, run, lambda: False, lambda s: False, lambda *a: None, now=1795015310)
        assert q.get(row['key'])['state'] == 'blocked_decision'
        q.defer(row['key'], 'verifying', 'fixture_verify', now=1795015310, delay=1)
        supervisor.drive(q, {obs['target']: obs}, run, lambda: False, lambda s: False, lambda *a: None, now=1795015320)
        assert q.get(row['key'])['state'] == 'completed_validated'
        assert not calls
    finally:
        q.close()


def test_natural_entrypoint_reconciles_existing_notice_after_candidate_skip(tmp_path, monkeypatch):
    q = Queue(tmp_path / 'queue.sqlite3')
    m = notice()
    key = 'alert:' + m['id']
    row = q.enqueue(key, {'kind': 'alert', 'profile': 'zeus', 'alert_id': m['id'],
                          'alert_channel': resolver.CHANNEL_ID}, 'alert_unresolved', now=1795014434)
    q.defer(row['key'], 'verifying', 'await_readback', now=1795014434, delay=1)
    legacy = {'last_seen_id': m['id'], 'processed': {
        m['id']: {'status': 'continuity_owned', 'continuity_key': row['key']}}}
    monkeypatch.setattr(supervisor, 'Queue', lambda: q)
    monkeypatch.setattr(supervisor, 'collect', lambda: (health(), []))
    monkeypatch.setattr(supervisor, 'original_active', lambda s: False)
    monkeypatch.setattr(supervisor, 'pc1_busy', lambda: False)
    def no_worker(*args):
        raise AssertionError('Healthy notice must not dispatch a worker')
    monkeypatch.setattr(supervisor, 'run_worker', no_worker)
    notices = []
    monkeypatch.setattr(supervisor, 'notify_result', lambda *args: notices.append(args))
    monkeypatch.setattr(resolver, 'load_token', lambda: 'offline-fixture')
    monkeypatch.setattr(resolver, 'load_state', lambda: legacy)
    monkeypatch.setattr(resolver, 'save_state', lambda s: None)
    monkeypatch.setattr(resolver, 'fetch_messages', lambda *a, **k: [m])
    monkeypatch.setattr(sys, 'argv', ['offline-fixture'])
    assert supervisor.main(resolver) == 0
    check = Queue(tmp_path / 'queue.sqlite3')
    try:
        assert check.get(row['key'])['state'] == 'completed_validated'
        assert legacy['processed'][m['id']]['status'] == 'done'
        assert notices
    finally:
        check.close()
