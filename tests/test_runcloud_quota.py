"""Quota/backoff regressions. All HTTP responses are isolated fixtures."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from email.message import Message

SPEC = importlib.util.spec_from_file_location('monitor_runcloud_quota', '/root/mgs-agent/scripts/monitor-runcloud.py')
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def rejected(monthly=True, headers=None):
    message = 'Monthly API quota limit exceeded.' if monthly else 'Too Many Attempts.'
    hdrs = Message()
    for key, value in (headers or {}).items(): hdrs[key] = value
    return HTTPError('http://fixture.invalid/servers/1', 429, 'fixture', hdrs, io.BytesIO(json.dumps({'message': message}).encode()))


def fail_http(monthly=True, headers=None):
    def request(*args, **kwargs): raise rejected(monthly, headers)
    return request


class Response:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return b'{"online":true,"connected":true}'


class QuotaTests(unittest.TestCase):
    def setUp(self):
        self.control = {}
        self.api = M.API('fixture-not-a-real-token')
        self.api.control = self.control
        self.clock = patch.object(M.time, 'time', return_value=1000)
        self.clock.start()
        self.sleep = patch.object(M.time, 'sleep')
        self.sleep.start()
        self.addCleanup(self.clock.stop)
        self.addCleanup(self.sleep.stop)

    def monthly(self, **headers):
        with patch.object(M.urllib.request, 'urlopen', side_effect=fail_http(headers=headers)) as http:
            with self.assertRaises(M.APIError): self.api.get('/servers/1')
        return http

    def test_monthly_429_makes_one_request_not_two(self):
        self.assertEqual(self.monthly(**{'Retry-After': '2000'}).call_count, 1)

    def test_monthly_retry_after_is_not_capped_to_30_seconds(self):
        self.monthly(**{'Retry-After': '2000000'})
        self.assertEqual(self.control.get('retry_at'), 2001000)
        self.assertEqual(self.control.get('kind'), 'monthly_quota')

    def test_later_reset_header_is_honored(self):
        self.monthly(**{'Retry-After': '60', 'X-RateLimit-Reset': '9000', 'X-RateLimit-Limit': '10000', 'X-RateLimit-Remaining': '0'})
        self.assertEqual(self.control.get('retry_at'), 9000)
        self.assertEqual(self.control.get('remaining'), 0)
        self.assertEqual(self.control.get('limit'), 10000)

    def test_monthly_missing_headers_uses_bounded_daily_probe(self):
        self.monthly()
        self.assertEqual(self.control.get('retry_at'), 87400)

    def test_transient_429_has_its_own_backoff(self):
        with patch.object(M.urllib.request, 'urlopen', side_effect=fail_http(False, {'Retry-After': '120'})) as http:
            with self.assertRaises(M.APIError): self.api.get('/servers/1')
        self.assertEqual(http.call_count, 1)
        self.assertEqual(self.control.get('retry_at'), 1120)
        self.assertEqual(self.control.get('kind'), 'rate_limit')

    def test_http_date_retry_after(self):
        self.monthly(**{'Retry-After': 'Thu, 01 Jan 1970 00:33:20 GMT'})
        self.assertEqual(self.control.get('retry_at'), 2000)

    def test_invalid_infinite_deadline_uses_safe_fallback(self):
        self.monthly(**{'Retry-After': 'inf', 'X-RateLimit-Reset': 'nan'})
        self.assertEqual(self.control.get('retry_at'), 87400)

    def test_quota_diagnostic_does_not_store_raw_body_or_token(self):
        self.monthly(**{'Retry-After': '2000'})
        saved = json.dumps(self.control)
        self.assertNotIn('fixture-not-a-real-token', saved)
        self.assertNotIn('message', self.control)

    def test_monthly_block_repeated_in_new_process_has_no_requests(self):
        self.monthly(**{'Retry-After': '2000'})
        state = json.loads(json.dumps(self.control))
        another = M.API('fixture-not-a-real-token')
        another.control = state
        with patch.object(M.urllib.request, 'urlopen', return_value=Response()) as http:
            with self.assertRaises(M.APIError): another.get('/servers/2')
        self.assertEqual(http.call_count, 0)

    def test_active_cooldown_does_not_open_network(self):
        self.control.update(kind='monthly_quota', retry_at=5000, observed_at=900)
        with patch.object(M.urllib.request, 'urlopen', return_value=Response()) as http:
            with self.assertRaises(M.APIError): self.api.get('/servers/1')
        self.assertEqual(http.call_count, 0)
        self.assertEqual(self.api.calls, 0)

    def test_expired_cooldown_requires_real_success(self):
        self.control.update(kind='monthly_quota', retry_at=999, observed_at=900)
        with patch.object(M.urllib.request, 'urlopen', return_value=Response()) as http:
            value = self.api.get('/servers/1')
        self.assertTrue(value['online'])
        self.assertEqual(http.call_count, 1)
        self.assertNotIn('retry_at', self.control)

    def test_503_after_deadline_does_not_claim_quota_recovered(self):
        self.control.update(kind='monthly_quota', retry_at=999, observed_at=900)
        def failure(*a, **k): raise HTTPError('http://fixture.invalid', 503, 'fixture', Message(), io.BytesIO(b'{}'))
        with patch.object(M.urllib.request, 'urlopen', side_effect=failure):
            with self.assertRaises(M.APIError): self.api.get('/servers/1')
        self.assertEqual(self.control.get('kind'), 'monthly_quota')

    def test_collect_stops_all_endpoints_after_first_quota_response(self):
        state = M.fresh_state()
        state['api_control'] = self.control
        cfg = {'servers': [{'id': str(i), 'name': 'Inc', 'services': []} for i in range(3)], 'webapp_servers': {}, 'backup_max_age_hours': 36}
        with patch.object(M.urllib.request, 'urlopen', side_effect=fail_http(headers={'Retry-After': '9000'})) as http:
            obs, summary = M.collect(self.api, cfg, state, 1000, True)
        self.assertEqual(http.call_count, 1)
        self.assertEqual(summary['api_calls'], 1)
        self.assertEqual(summary.get('status'), 'deferred_quota')
        self.assertEqual(obs['monitor:api']['severity'], 2)
        self.assertEqual(state.get('last_backup_check', 0), 0)

    def test_unknown_servers_never_recover_during_block(self):
        state = M.fresh_state()
        state['incidents'] = {'1:connection': {'published': 2, 'candidate': 2, 'count': 1}}
        state['api_control'] = self.control
        self.control.update(kind='monthly_quota', retry_at=5000, observed_at=900)
        cfg = {'servers': [{'id': '1', 'name': 'Inc', 'services': []}], 'webapp_servers': {}, 'backup_max_age_hours': 36}
        with patch.object(M.urllib.request, 'urlopen', return_value=Response()) as http:
            obs, _ = M.collect(self.api, cfg, state, 1000)
        events = M.transitions(state, obs, 1000)
        self.assertEqual(http.call_count, 0)
        self.assertEqual(state['incidents']['1:connection']['published'], 2)
        self.assertFalse(any(e['key'] == '1:connection' for e in events))

    def test_blocked_dry_run_skips_credentials_and_state_write(self):
        root = Path(tempfile.mkdtemp(prefix='runcloud-quota-test-', dir=os.environ['TMPDIR']))
        state = M.fresh_state()
        state['api_control'] = {'kind': 'monthly_quota', 'retry_at': 9000, 'observed_at': 900}
        cfg = {'servers': [], 'webapp_servers': {}, 'backup_max_age_hours': 36, 'channel_id': 'fixture'}
        sp = root/'state.json'; cp = root/'config.json'
        sp.write_text(json.dumps(state)); cp.write_text(json.dumps(cfg)); before = sp.read_bytes()
        with patch.object(M.sys, 'argv', ['monitor', '--dry-run', '--state', str(sp), '--config', str(cp)]), patch.object(M, 'load_env'), patch.object(M.subprocess, 'run') as proc, patch.object(M.urllib.request, 'urlopen') as http, contextlib.redirect_stdout(io.StringIO()) as output:
            M.main()
        self.assertEqual(proc.call_count, 0)
        self.assertEqual(http.call_count, 0)
        self.assertEqual(sp.read_bytes(), before)
        self.assertEqual(json.loads(output.getvalue())['summary']['api_calls'], 0)

    def test_blocked_collect_preserves_backup_summary(self):
        state = M.fresh_state()
        state['last_backup_summary'] = {'active': 93, 'checked': 93}
        state['api_control'] = self.control
        self.control.update(kind='monthly_quota', retry_at=5000, observed_at=900)
        before = copy.deepcopy(state['last_backup_summary'])
        cfg = {'servers': [], 'webapp_servers': {}, 'backup_max_age_hours': 36}
        with patch.object(M.urllib.request, 'urlopen') as http:
            M.collect(self.api, cfg, state, 1000, True)
        self.assertEqual(state['last_backup_summary'], before)
        self.assertEqual(http.call_count, 0)


if __name__ == '__main__': unittest.main(verbosity=2)
