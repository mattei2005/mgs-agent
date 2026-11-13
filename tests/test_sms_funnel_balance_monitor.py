"""Offline regression tests: explicit fixtures and local HTTP only."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import unittest
from unittest.mock import patch
from typing import Any

SCRIPT = Path('/root/mgs-agent/scripts/monitor-sms-funnel-balance.py')
spec = importlib.util.spec_from_file_location('sms_balance', SCRIPT)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
LEGACY = dict(total_contracted=3074000, total_sent=2852054, total_reserved=0,
              credits=0, total_calculated_broadcasts=6708, daily_average_3d=15000)
WALLET: dict[str, Any] = dict(currency='BRL', balance_micros=17083760000,
              available_micros=17083760000, held_micros=0)
PRICES = {'products': [dict(service='sms', unit='message', unit_price_micros=80000, blocked=False)]}


def metrics(wallet=None, prices=None):
    return m.wallet_metrics(m.validate_metrics(LEGACY), wallet or WALLET, prices or PRICES)


class WalletContract(unittest.TestCase):
    def test_real_world_regression_legacy_zero_wallet_positive(self):
        x = metrics()
        self.assertEqual(x['credits'], 0)
        self.assertEqual(m.alert_capacity(x), 213547)
        self.assertEqual(m.balance_level(m.alert_capacity(x)), 'normal')
        self.assertEqual(m.fmt_money(x['available_micros']), 'R$ 17.083,76')
        p = m.burn_projection({}, x, 1)
        self.assertGreater(p['hours_left'], 0)
        fields = m.metric_fields(x, p)
        self.assertEqual(fields[0]['value'], '**R$ 17.083,76**')
        self.assertNotIn('Conciliação', [f['name'] for f in fields])
        self.assertIn('outros canais', fields[-1]['value'])
        self.assertNotIn('Ação necessária', [f['name'] for f in m.friday_payload(x, p)['embeds'][0]['fields']])

    def test_approved_threshold_uses_live_price(self):
        for amount, level in [(0, 'emergency'), (560000000, 'emergency'), (560080000, 'normal')]:
            w = dict(WALLET, balance_micros=amount, available_micros=amount)
            self.assertEqual(m.balance_level(m.alert_capacity(metrics(w))), level)
        other_price = copy.deepcopy(PRICES)
        other_price['products'][0]['unit_price_micros'] = 160000
        self.assertEqual(m.alert_capacity(metrics(prices=other_price)), 106773)

    def test_money_reserves_and_rounding(self):
        w = dict(WALLET, held_micros=1000000, available_micros=WALLET['balance_micros']-1000000)
        self.assertEqual(metrics(w)['held_micros'], 1000000)
        self.assertEqual(m.fmt_money(80000), 'R$ 0,08')
        self.assertEqual(m.fmt_money(0), 'R$ 0,00')

    def test_invalid_wallet_never_becomes_zero(self):
        for key, value in [('available_micros', None), ('held_micros', -1), ('currency', 'USD'), ('balance_micros', True)]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                metrics(dict(WALLET, **{key: value}))
        with self.assertRaises(RuntimeError):
            metrics(dict(WALLET, held_micros=1))
        with self.assertRaises(RuntimeError):
            m.validate_metrics({})

    def test_unknown_invalid_or_blocked_price_is_unknown(self):
        for price in [None, 0, -1, True, '80000']:
            p = copy.deepcopy(PRICES)
            p['products'][0]['unit_price_micros'] = price
            with self.subTest(price=price), self.assertRaises(RuntimeError):
                metrics(prices=p)
        for p in [{'products': []}, {'products': PRICES['products']*2},
                  {'products': [dict(PRICES['products'][0], blocked=True)]}]:
            with self.assertRaises(RuntimeError): metrics(prices=p)

    def test_no_false_recharge_on_migration_hold_release_or_price_change(self):
        x = metrics()
        self.assertFalse(m.increased_balance(LEGACY, x))
        held = dict(x, held_micros=1000000, available_micros=x['available_micros']-1000000)
        self.assertFalse(m.increased_balance(held, x))
        self.assertFalse(m.increased_balance(x, dict(x, sms_equivalent=999999)))
        self.assertTrue(m.increased_balance(x, dict(x, balance_micros=x['balance_micros']+1)))
        self.assertTrue(m.increased_balance(dict(LEGACY, credits=0), dict(LEGACY, credits=100)))

    def test_no_wallet_projection_from_frozen_legacy_totals(self):
        x = dict(metrics(), daily_average_3d=0)
        state = {'samples': [{'ts': 1, 'total_sent': 1}, {'ts': 250000, 'total_sent': 99999}]}
        self.assertIsNone(m.burn_projection(state, x, 260000)['hours_left'])
        self.assertEqual(m.completed_three_day_average({'data': [1, 120, 150, 180, 999999]}), 150)

    def test_probe_selects_wallet_and_fails_closed(self):
        replies = {m.LOGIN_URL: {'access_token': 'fixture-only'}, m.CREDITS_URL: LEGACY,
                   m.WALLET_BILLING_URL: {'sms': 'wallet'}, m.WALLET_BALANCE_URL: WALLET,
                   m.WALLET_PRICES_URL: PRICES, m.DAILY_SENTS_URL: {'data': [1,120,150,180,999]}}
        calls = []
        def fake(url, **kwargs):
            calls.append(url)
            return 200, replies[url]
        with patch.object(m, 'read_credential', return_value=('fixture','fixture')), patch.object(m, 'http_json', side_effect=fake):
            x = m.probe_live({})
            self.assertEqual(x['available_micros'], WALLET['available_micros'])
            self.assertEqual(x['daily_average_3d'], 150)
            self.assertNotIn(m.CREDITS_URL, calls)
            replies[m.WALLET_BILLING_URL] = {}
            with self.assertRaises(RuntimeError): m.probe_live({})
            replies[m.WALLET_BILLING_URL] = {'sms': 'wallet'}
            replies[m.WALLET_BALANCE_URL] = {}
            with self.assertRaises(RuntimeError): m.probe_live({})


class ConsumerLocalHTTP(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR', '/root/.hermes/profiles/zeus/cache/scratch'))
        self.root = Path(self.tmp.name)
        self.state = self.root/'state.json'
        self.fixture = self.root/'fixture.json'
        self.requests = []
        self.fail_post = False
        outer = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                outer.requests.append({'auth': self.headers.get('Authorization'), 'path': self.path, 'body': body})
                self.send_response(500 if outer.fail_post else 200)
                self.send_header('Content-Type', 'application/json'); self.end_headers()
                self.wfile.write(json.dumps({'id': str(len(outer.requests)), 'channel_id': 'fixture-channel'}).encode())
        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.api = 'http://127.0.0.1:'+str(self.server.server_port)
        self.put_fixture()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.tmp.cleanup()

    def put_fixture(self, wallet=None, error=None):
        data = {'error': error} if error else {'legacy': LEGACY, 'wallet': wallet or WALLET, 'prices': PRICES}
        self.fixture.write_text(json.dumps(data))

    def run_consumer(self, *extra):
        argv = ['monitor', '--state-file', str(self.state), '--fixture', str(self.fixture),
                '--channel-id', 'fixture-channel', '--discord-api-base', self.api, *extra]
        output = io.StringIO()
        with patch('sys.argv', argv), patch.object(m, 'runtime_env', return_value={'DISCORD_BOT_TOKEN':'local-test-only'}), contextlib.redirect_stdout(output):
            result = m.main()
        return result, output.getvalue()

    def test_manual_publish_state_and_silent_repeat(self):
        self.assertEqual(self.run_consumer('--current-report')[0], 0)
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request['auth'], 'Bot local-test-only')
        self.assertEqual(request['path'], '/channels/fixture-channel/messages')
        payload = request['body']
        self.assertEqual(payload['allowed_mentions'], {'parse': []})
        self.assertIn('correção', payload['embeds'][0]['title'])
        self.assertEqual(json.loads(self.state.read_text())['level'], 'normal')
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.run_consumer()[0], 0)
        self.assertEqual(len(self.requests), 1)

    def test_dry_run_no_state_write_no_delivery(self):
        self.assertEqual(self.run_consumer('--dry-run')[0], 0)
        self.assertFalse(self.state.exists()); self.assertEqual(self.requests, [])

    def test_threshold_antispam_recovery_and_mentions(self):
        self.run_consumer('--current-report')
        self.put_fixture(dict(WALLET, balance_micros=560000000, available_micros=560000000))
        self.assertEqual(self.run_consumer()[0], 0)
        self.assertEqual(len(self.requests), 2)
        payload = self.requests[-1]['body']
        self.assertEqual(payload['allowed_mentions'], {'users': [m.MENTION_USER_ID]})
        self.assertIn('emergência', payload['embeds'][0]['title'])
        self.run_consumer(); self.assertEqual(len(self.requests), 2)
        self.put_fixture(); self.run_consumer()
        self.assertEqual(len(self.requests), 3)
        self.assertIn('Aumento de saldo', self.requests[-1]['body']['embeds'][0]['title'])
        self.assertEqual(json.loads(self.state.read_text())['level'], 'normal')

    def test_migration_is_one_correction_not_recharge(self):
        state = m.default_state('fixture-channel')
        state.update(last_metrics=LEGACY, level='emergency')
        m.save_state(self.state, state)
        self.run_consumer()
        self.assertEqual(len(self.requests), 1)
        self.assertIn('correção', self.requests[0]['body']['embeds'][0]['title'])

    def test_delivery_failure_does_not_consume_transition(self):
        self.fail_post = True
        self.assertEqual(self.run_consumer('--current-report')[0], 1)
        self.assertEqual(json.loads(self.state.read_text())['last_metrics'], {})
        self.fail_post = False
        self.assertEqual(self.run_consumer('--current-report')[0], 0)
        self.assertEqual(json.loads(self.state.read_text())['last_metrics']['balance_basis'], 'wallet')

    def test_probe_failure_unknown_preserves_balance_and_recovers_once(self):
        self.run_consumer('--current-report')
        prior = json.loads(self.state.read_text())['last_metrics']
        self.put_fixture(error='fixture outage')
        self.assertEqual(self.run_consumer()[0], 1)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.run_consumer()[0], 1)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(json.loads(self.state.read_text())['last_metrics'], prior)
        self.put_fixture()
        self.run_consumer()
        self.assertEqual(len(self.requests), 3)
        self.assertIn('restabelecido', self.requests[-1]['body']['embeds'][0]['title'])

    def test_friday_window_dedup_and_wallet_zero_legacy(self):
        self.run_consumer('--friday-report', '--now-brazil', '2026-11-13T14:00:00-03:00')
        self.assertEqual(self.requests, [])
        self.run_consumer('--friday-report', '--now-brazil', '2026-11-13T15:00:00-03:00')
        self.assertEqual(len(self.requests), 1)
        fields = self.requests[0]['body']['embeds'][0]['fields']
        self.assertNotIn('Ação necessária', [f['name'] for f in fields])
        self.run_consumer('--friday-report', '--now-brazil', '2026-11-13T15:30:00-03:00')
        self.assertEqual(len(self.requests), 1)

    def test_shared_lock_skips_without_mutation(self):
        with self.state.with_suffix('.run.lock').open('a') as lock:
            m.fcntl.flock(lock.fileno(), m.fcntl.LOCK_EX | m.fcntl.LOCK_NB)
            code, out = self.run_consumer('--current-report')
            self.assertEqual(code, 0); self.assertIn('already_running', out)
            self.assertEqual(self.requests, []); self.assertFalse(self.state.exists())


if __name__ == '__main__':
    unittest.main()
