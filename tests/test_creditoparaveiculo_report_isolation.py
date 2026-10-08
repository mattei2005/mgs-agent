"""Regression: CPV reporting must not inherit a campaign recovery hold."""
import importlib.util
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path('/root/.hermes/profiles/ares/scripts')


def load_module():
    spec = importlib.util.spec_from_file_location('cpv_report_isolation_test', ROOT / 'creditoparaveiculo-fixed-reports.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def reports(monkeypatch, tmp_path):
    m = load_module()
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 8, 13, 6, tzinfo=m.SP)
    monkeypatch.setattr(m, 'datetime', Clock)
    monkeypatch.setattr(m, 'build_intraday', Mock(return_value=('report', {'kind': 'intraday'})))
    monkeypatch.setattr(m, 'build_daily', Mock(return_value=('report', {'kind': 'daily'})))
    monkeypatch.setattr(m, 'save_report', Mock(return_value=tmp_path / 'report.json'))
    monkeypatch.setattr(m, 'deliver_report_once', Mock(return_value=(['id'], {'ok': True}, False)))
    return m


def test_automatic_report_only_does_not_execute_actions_or_force_repost(reports, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['reports', '--mode', 'intraday', '--report-only', '--gate'])
    assert reports.main() == 0
    assert reports.build_intraday.call_args.kwargs['execute_actions'] is False
    assert reports.deliver_report_once.call_args.kwargs['force'] is False


def test_manual_report_only_can_reissue_explicitly(reports, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['reports', '--mode', 'intraday', '--report-only'])
    assert reports.main() == 0
    assert reports.deliver_report_once.call_args.kwargs['force'] is True
    assert reports.build_intraday.call_args.kwargs['execute_actions'] is False


def test_unverified_delivery_is_not_success(reports, monkeypatch):
    reports.deliver_report_once.return_value = (['id'], {'ok': False, 'deferred': True}, True)
    monkeypatch.setattr(sys, 'argv', ['reports', '--mode', 'intraday', '--report-only', '--gate'])
    assert reports.main() == 74


def test_busy_notice_does_not_read_meta_or_change_campaigns(reports, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['reports', '--mode', 'intraday', '--report-only', '--gate', '--report-unavailable', 'account_busy'])
    assert reports.main() == 75
    reports.build_intraday.assert_not_called()
    reports.build_daily.assert_not_called()
    assert reports.deliver_report_once.call_args.args[1] == reports.THREAD_INTRADAY
    assert reports.deliver_report_once.call_args.kwargs['force'] is False
    payload = reports.save_report.call_args.args[1]
    assert payload['status'] == 'unavailable'
    assert payload['meta_writes'] == 0


def test_busy_notice_rejects_actions_mode(reports, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['reports', '--mode', 'intraday', '--actions-only', '--report-unavailable', 'account_busy'])
    with pytest.raises(SystemExit) as exc:
        reports.main()
    assert exc.value.code == 2
    reports.deliver_report_once.assert_not_called()


@pytest.mark.parametrize('name,hour,expected', [
    ('creditoparaveiculo-intraday.sh', '09', 'report'),
    ('creditoparaveiculo-intraday.sh', '11', 'report'),
    ('creditoparaveiculo-intraday.sh', '13', 'report'),
    ('creditoparaveiculo-daily.sh', '12', 'report'),
    ('creditoparaveiculo-intraday.sh', '08', 'blocked_action'),
    ('creditoparaveiculo-intraday.sh', '12', 'blocked_action'),
    ('creditoparaveiculo-intraday.sh', '16', 'blocked_action'),
    ('creditoparaveiculo-intraday.sh', '10', 'none'),
    ('creditoparaveiculo-daily.sh', '11', 'none'),
])
def test_wrappers_report_despite_persisted_writer_lease(tmp_path, name, hour, expected):
    # Stubs are strictly offline and never load a real credential or call an API.
    body = (ROOT / name).read_text().replace('source /root/mgs-agent/.env', ':')
    wrapper = tmp_path / name
    wrapper.write_text(body)
    log = tmp_path / 'calls'
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    scripts = {
        'date': '#!/bin/sh\nprintf "%s\\n" "$TEST_HOUR"\n',
        'python3': '#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\ncase "$*" in *ares-cpv-meta-reader-gate.py*) exit 75;; esac\nexit 0\n',
        'flock': '#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\nexit "${TEST_FLOCK_RC:-0}"\n',
    }
    for key, value in scripts.items():
        p = bindir / key
        p.write_text(value)
        p.chmod(0o700)
    env = dict(os.environ, PATH=f'{bindir}:/usr/bin:/bin', TEST_HOUR=hour, TEST_LOG=str(log))
    result = subprocess.run(['/bin/bash', str(wrapper)], env=env, capture_output=True, text=True)
    calls = log.read_text() if log.exists() else ''
    assert result.returncode == 0
    if expected == 'report':
        assert '--report-only --gate' in calls
        assert '--actions-only' not in calls
        assert 'ares-cpv-meta-reader-gate.py' not in calls
        assert '-w 45' in calls
    elif expected == 'blocked_action':
        assert 'ares-cpv-meta-reader-gate.py' in calls
        assert 'flock' not in calls
        assert 'fixed-reports.py' not in calls
    else:
        assert calls == ''


@pytest.mark.parametrize('name,hour', [('creditoparaveiculo-intraday.sh', '13'), ('creditoparaveiculo-daily.sh', '12')])
def test_physical_writer_lock_timeout_requests_notice_and_fails(tmp_path, name, hour):
    body = (ROOT / name).read_text().replace('source /root/mgs-agent/.env', ':')
    wrapper = tmp_path / name
    wrapper.write_text(body)
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    log = tmp_path / 'calls'
    for key, text in {
        'date': '#!/bin/sh\nprintf "%s\\n" "$TEST_HOUR"\n',
        'flock': '#!/bin/sh\nexit 75\n',
        'python3': '#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\nexit 75\n',
    }.items():
        p = bindir / key
        p.write_text(text)
        p.chmod(0o700)
    result = subprocess.run(['/bin/bash', str(wrapper)], env=dict(os.environ, PATH=f'{bindir}:/usr/bin:/bin', TEST_HOUR=hour, TEST_LOG=str(log)), capture_output=True, text=True)
    assert result.returncode == 75
    assert '--report-unavailable account_busy' in log.read_text()
    assert 'indisponível' in result.stderr
