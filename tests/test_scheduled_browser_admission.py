"""Admission boundary tests: real leases and actual consumer CLI entrypoints."""
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys
import subprocess
import threading
import time

import pytest

BASE = Path(os.environ.get('MGS_ADMISSION_TEST_SCRIPT_ROOT', '/root/mgs-agent/scripts'))
CONSUMERS = ['dtr-sb-page-health-sync.py', 'sync-sb-sms-revenue-daily.py', 'sync-sb-messenger-revenue-sheet.py', 'monitor-sb-messenger-token-invalid.py']


def load_budget():
    spec = importlib.util.spec_from_file_location('mgs_browser_budget', BASE / 'mgs_browser_budget.py')
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def budget():
    mod = load_budget()
    return mod


@pytest.fixture
def config(tmp_path):
    p = tmp_path / 'budget.json'
    p.write_text(json.dumps({'schema_version': 1, 'slots': 3, 'batch_slots': 2, 'local_workers': 1, 'wait_timeout_seconds': .5, 'poll_seconds': .01, 'lock_dir': str(tmp_path / 'leases')}))
    return p


def test_batch_job_never_uses_interactive_reservation(budget, config, capsys):
    assert callable(getattr(budget, 'scheduled_browser_job', None)), 'missing scheduled consumer admission boundary'
    first = budget.Lease(config, batch=True).acquire()
    second = budget.Lease(config, batch=True).acquire()
    called = False
    try:
        with pytest.raises(TimeoutError):
            with budget.scheduled_browser_job('consumer.py', config_path=config, timeout=.03):
                called = True
        assert not called
        interactive = budget.Lease(config).acquire()
        assert interactive.slot == 2
        interactive.release()
    finally:
        first.release(); second.release()
    assert 'timeout' in capsys.readouterr().err.lower()


def test_whole_workflow_stays_admitted_until_exit(budget, config):
    with budget.scheduled_browser_job('consumer.py', config_path=config):
        other = budget.Lease(config, batch=True).acquire()
        try:
            denied = budget.Lease(config, timeout=0, batch=True)
            with pytest.raises(TimeoutError): denied.acquire()
        finally: other.release()
    one = budget.Lease(config, timeout=0, batch=True).acquire()
    two = budget.Lease(config, timeout=0, batch=True).acquire()
    one.release(); two.release()


@pytest.mark.parametrize('exc', [RuntimeError('private-value-do-not-log'), SystemExit(0), SystemExit(2), KeyboardInterrupt()])
def test_release_on_failure_exit_and_interrupt(budget, config, capsys, exc):
    with pytest.raises(type(exc)):
        with budget.scheduled_browser_job('consumer.py', config_path=config): raise exc
    one = budget.Lease(config, timeout=0, batch=True).acquire()
    two = budget.Lease(config, timeout=0, batch=True).acquire()
    one.release(); two.release()
    assert 'private-value-do-not-log' not in capsys.readouterr().err


def test_disabled_mode_never_reads_budget_or_waits(budget, tmp_path, capsys):
    with budget.scheduled_browser_job('fixture.py', enabled=False, config_path=tmp_path / 'missing.json') as lease:
        assert lease is None
    assert capsys.readouterr().err == ''


def test_invalid_config_fails_before_consumer_body(budget, tmp_path):
    p = tmp_path / 'invalid.json'; p.write_text('{}')
    reached = False
    with pytest.raises(RuntimeError):
        with budget.scheduled_browser_job('consumer.py', config_path=p): reached = True
    assert not reached


def test_wait_telemetry_is_stderr_only_and_bounded(budget, config, capsys):
    lease1 = budget.Lease(config, batch=True).acquire()
    lease2 = budget.Lease(config, batch=True).acquire()
    t = threading.Thread(target=lambda: (time.sleep(.08), lease1.release()))
    t.start()
    try:
        with budget.scheduled_browser_job('consumer.py', config_path=config) as lease:
            assert .04 <= lease.wait_seconds < .5
    finally: t.join(); lease2.release()
    output = capsys.readouterr(); assert output.out == ''
    events = [json.loads(s.removeprefix('BROWSER_BUDGET ')) for s in output.err.splitlines()]
    admitted = next(e for e in events if e['event'] == 'admitted')
    assert admitted['consumer'] == 'consumer.py' and admitted['wait_seconds'] >= .04
    assert events[-1]['event'] == 'released'


@pytest.mark.parametrize('consumer', CONSUMERS)
def test_real_consumer_entrypoint_reaches_admission_before_job_body(budget, monkeypatch, consumer):
    class BeforeBody(Exception): pass
    observed = []
    from contextlib import contextmanager
    @contextmanager
    def stop_at_boundary(label, **kwargs):
        observed.append((Path(label).name, kwargs.get('enabled', True)))
        raise BeforeBody()
        yield
    budget.scheduled_browser_job = stop_at_boundary
    monkeypatch.setitem(sys.modules, 'mgs_browser_budget', budget)
    monkeypatch.setattr(sys, 'argv', [str(BASE / consumer)])
    monkeypatch.syspath_prepend(str(BASE))
    with pytest.raises(BeforeBody): runpy.run_path(str(BASE / consumer), run_name='__main__')
    assert observed == [(consumer, True)]


@pytest.mark.parametrize('consumer', CONSUMERS)
def test_help_uses_no_lease_and_preserves_cli(budget, monkeypatch, consumer):
    from contextlib import contextmanager
    observed = []
    @contextmanager
    def no_lease(label, **kwargs):
        observed.append(kwargs.get('enabled', True))
        assert kwargs['enabled'] is False
        yield None
    monkeypatch.setitem(sys.modules, 'mgs_browser_budget', budget)
    budget.scheduled_browser_job = no_lease
    monkeypatch.setattr(sys, 'argv', [str(BASE / consumer), '--help'])
    monkeypatch.syspath_prepend(str(BASE))
    with pytest.raises(SystemExit) as exc: runpy.run_path(str(BASE / consumer), run_name='__main__')
    assert exc.value.code == 0 and observed == [False]
