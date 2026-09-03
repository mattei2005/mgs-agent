import asyncio
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path('/root/mgs-agent/scripts/monitor-sb-messenger-token-invalid.py')
CRON_CONTROL = Path('/root/mgs-agent/scripts/cron-control-plane.py')
FIXTURE = Path('/root/mgs-agent/tests/fixtures/sb-messenger-token-invalid.json')
spec = importlib.util.spec_from_file_location('sb_token_monitor', SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
cron_spec = importlib.util.spec_from_file_location('cron_control_plane', CRON_CONTROL)
assert cron_spec and cron_spec.loader
cron_mod = importlib.util.module_from_spec(cron_spec)
cron_spec.loader.exec_module(cron_mod)


class TokenMonitorTests(unittest.TestCase):
    def fixture(self):
        return json.loads(FIXTURE.read_text())

    def alerts(self):
        data = self.fixture()
        return mod.normalize_alerts(data['notifications'], data['users'], data['pages'])

    def test_filter_and_mapped_page_count(self):
        alerts = self.alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['notification_id'], 100)
        self.assertEqual(alerts[0]['pages'], 2)
        self.assertEqual(alerts[0]['page_statuses'], {'Broadcast': 1, 'On-hold': 1})
        self.assertEqual(alerts[0]['page_count_scope'], 'mapped-sb-user-id')
        self.assertEqual(alerts[0]['source'], 'canary')

    def test_payload_mentions_both_roles_and_keeps_compact_format(self):
        payload = mod.build_payloads(self.alerts(), canary=True)[0]
        self.assertEqual(payload['content'], f'{mod.TEAM_MENTIONS} · Reaja ✅ quando resolver.')
        self.assertEqual(payload['allowed_mentions'], {'parse': [], 'roles': mod.TEAM_ROLE_IDS})
        embed = payload['embeds'][0]
        self.assertEqual(embed['title'], 'CANÁRIO — FINANCEADX — Token Messenger inválido')
        self.assertNotIn('description', embed)
        self.assertEqual([field['name'] for field in embed['fields']], ['User', 'Segurador', 'Páginas'])
        self.assertEqual(embed['fields'][2]['value'], 'Total 2\n1 Broadcast + 1 On-hold')
        self.assertFalse(embed['fields'][2]['inline'])

    def test_page_summary_uses_operational_status_order(self):
        row = {
            'pages': 390,
            'page_statuses': {
                'Ready': 5,
                'Blocked': 14,
                'On-hold': 101,
                'Broadcast': 270,
            },
        }
        self.assertEqual(
            mod.format_page_summary(row),
            'Total 390\n270 Broadcast + 101 On-hold + 14 Blocked + 5 Ready',
        )

    def test_page_summary_fails_closed_on_total_mismatch(self):
        with self.assertRaisesRegex(RuntimeError, 'does not match'):
            mod.format_page_summary({
                'pages': 3,
                'page_statuses': {'Broadcast': 1, 'On-hold': 1},
            })

    def test_one_discord_message_per_incident(self):
        alert = self.alerts()[0]
        rows = []
        for index in range(23):
            row = dict(alert)
            row['notification_id'] = 1000 + index
            row['user_id'] = str(index)
            rows.append(row)
        payloads = mod.build_payloads(rows)
        self.assertEqual(len(payloads), 23)
        self.assertTrue(all(len(payload['embeds']) == 1 for payload in payloads))

    def test_refresh_active_incident_adds_live_status_breakdown(self):
        live_alert = self.alerts()[0]
        legacy_alert = dict(live_alert)
        legacy_alert.pop('page_statuses')
        key = mod.incident_key(live_alert)
        state = {
            'incidents': {
                key: {
                    'status': 'active',
                    'alert': legacy_alert,
                },
            },
        }
        self.assertEqual(mod.refresh_active_incident_alerts(state, [live_alert]), 1)
        self.assertEqual(
            state['incidents'][key]['alert']['page_statuses'],
            {'Broadcast': 1, 'On-hold': 1},
        )
        self.assertEqual(mod.refresh_active_incident_alerts(state, [live_alert]), 0)

    def test_atomic_state_mode_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            state = mod.initial_state()
            mod.save_state(path, state)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            loaded = mod.load_state(path)
            self.assertEqual(loaded['last_seen_id'], 0)
            self.assertEqual(
                loaded['_meta']['daily_cycle'],
                'no state-only resend; deliver only newly observed live /notification IDs',
            )
            self.assertIn('current live /notification response', loaded['_meta']['delivery_gate'])

    def test_failure_alert_is_sent_only_once_per_failure_streak(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            state = mod.initial_state()
            state['consecutive_failures'] = 2
            deliveries = []

            def fake_post(channel_id, payload):
                deliveries.append((channel_id, payload))
                return 'message-id'

            with patch.object(mod, 'post_and_verify', side_effect=fake_post):
                mod.record_failure(path, state, RuntimeError('upstream unavailable'), dry_run=False)
                mod.record_failure(path, state, RuntimeError('upstream unavailable'), dry_run=False)

            loaded = mod.load_state(path)
            self.assertEqual(len(deliveries), 1)
            self.assertEqual(loaded['consecutive_failures'], 4)
            self.assertEqual(loaded['failure_alert_sent_for'], 3)

    def test_retention_cutoff_keeps_only_previous_day_and_current_day(self):
        cutoff = mod.retention_cutoff(
            datetime.fromisoformat('2026-08-29T00:05:00-04:00')
        )
        self.assertEqual(cutoff.isoformat(), '2026-08-28T00:00:00-04:00')

    def test_retention_targets_only_token_messenger_alert_embeds(self):
        target = {
            'embeds': [{'title': 'LEMBRETE #2 — FINANCEADX — Token Messenger inválido'}]
        }
        unrelated = {
            'embeds': [{'title': 'Monitor SB de token Messenger com falha'}]
        }
        manual = {'content': 'mensagem manual', 'embeds': []}
        self.assertTrue(mod.is_retention_target_message(target))
        self.assertFalse(mod.is_retention_target_message(unrelated))
        self.assertFalse(mod.is_retention_target_message(manual))

    def test_retention_dry_run_does_not_delete(self):
        messages = [
            {'id': '3', 'timestamp': '2026-08-29T01:00:00+00:00', 'embeds': [{'title': 'SITE — Token Messenger inválido'}]},
            {'id': '2', 'timestamp': '2026-08-28T12:00:00+00:00', 'embeds': [{'title': 'SITE — Token Messenger inválido'}]},
            {'id': '1', 'timestamp': '2026-08-27T03:59:59+00:00', 'embeds': [{'title': 'SITE — Token Messenger inválido'}]},
        ]
        calls = []
        def fake_request(method, path, body=None, allow_404=False):
            calls.append((method, path))
            return 200, list(messages)
        original = mod.discord_request
        setattr(mod, 'discord_request', fake_request)
        try:
            result = mod.cleanup_old_messages(
                '123',
                dry_run=True,
                now_value=datetime.fromisoformat('2026-08-29T00:05:00-04:00'),
                sleep_func=lambda _: None,
            )
        finally:
            setattr(mod, 'discord_request', original)
        self.assertEqual(result['eligible'], 1)
        self.assertEqual(result['would_delete'], 1)
        self.assertEqual(result['deleted'], 0)
        self.assertEqual([method for method, _ in calls], ['GET'])

    def test_retention_deletes_old_target_and_preserves_other_messages(self):
        messages = [
            {'id': '4', 'timestamp': '2026-08-29T01:00:00+00:00', 'embeds': [{'title': 'SITE — Token Messenger inválido'}]},
            {'id': '3', 'timestamp': '2026-08-28T12:00:00+00:00', 'embeds': [{'title': 'SITE — Token Messenger inválido'}]},
            {'id': '2', 'timestamp': '2026-08-27T03:59:59+00:00', 'embeds': [{'title': 'SITE — Token Messenger inválido'}]},
            {'id': '1', 'timestamp': '2026-08-26T12:00:00+00:00', 'content': 'mensagem manual', 'embeds': []},
        ]
        calls = []
        def fake_request(method, path, body=None, allow_404=False):
            calls.append((method, path))
            if method == 'DELETE':
                message_id = path.rsplit('/', 1)[-1]
                messages[:] = [row for row in messages if row['id'] != message_id]
                return 204, None
            return 200, list(messages)
        original = mod.discord_request
        setattr(mod, 'discord_request', fake_request)
        try:
            result = mod.cleanup_old_messages(
                '123',
                dry_run=False,
                now_value=datetime.fromisoformat('2026-08-29T00:05:00-04:00'),
                sleep_func=lambda _: None,
            )
        finally:
            setattr(mod, 'discord_request', original)
        self.assertEqual(result['eligible'], 1)
        self.assertEqual(result['deleted'], 1)
        self.assertEqual(result['remaining'], 0)
        self.assertEqual([row['id'] for row in messages], ['4', '3', '1'])
        self.assertEqual([method for method, _ in calls], ['GET', 'DELETE', 'GET'])

    def test_retention_success_is_recorded_without_changing_monitor_failures(self):
        state = mod.initial_state()
        state['consecutive_failures'] = 2
        mod.record_retention_success(
            state,
            {
                'cutoff': '2026-08-28T00:00:00-04:00',
                'scanned': 10,
                'eligible': 3,
                'deleted': 3,
                'already_missing': 0,
                'remaining': 0,
                'message_ids': ['1', '2', '3'],
            },
            at='2026-08-29T00:05:00-04:00',
        )
        self.assertEqual(state['consecutive_failures'], 2)
        self.assertEqual(state['retention']['last_success_date'], '2026-08-29')
        self.assertEqual(state['retention']['consecutive_failures'], 0)
        self.assertEqual(state['retention']['last_result']['deleted'], 3)

    def test_retention_failure_persists_independent_counter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            state = mod.initial_state()
            mod.record_retention_failure(
                path,
                state,
                RuntimeError('discord unavailable'),
                dry_run=False,
                at='2026-08-29T00:05:00-04:00',
            )
            loaded = mod.load_state(path)
        self.assertEqual(loaded['consecutive_failures'], 0)
        self.assertEqual(loaded['retention']['consecutive_failures'], 1)
        self.assertEqual(loaded['retention']['last_error']['type'], 'RuntimeError')

    def test_parse_args_accepts_cleanup_old_messages_mode(self):
        with patch.object(sys, 'argv', ['monitor', '--cleanup-old-messages', '--dry-run']):
            args = mod.parse_args()
        self.assertTrue(args.cleanup_old_messages)
        self.assertTrue(args.dry_run)

    def test_cron_inventory_labels_retention_mode_accurately(self):
        job = cron_mod.parse_cron_line(
            '5 0 * * * flock -n /var/lock/cleanup.lock '
            '/root/.local/share/mgs/sb-venv/bin/python '
            '/root/mgs-agent/scripts/monitor-sb-messenger-token-invalid.py '
            '--cleanup-old-messages --apply >> /root/mgs-agent/logs/monitor.log 2>&1'
        )
        self.assertIn('retenção diária', job['description'])
        self.assertIn('exclusão', job['risk'])

    def test_cron_inventory_labels_live_only_monitor_policy(self):
        job = cron_mod.parse_cron_line(
            '12,27,42,57 * * * * flock -n /var/lock/monitor.lock '
            'xvfb-run -a /root/.local/share/mgs/sb-venv/bin/python '
            '/root/mgs-agent/scripts/monitor-sb-messenger-token-invalid.py --apply'
        )
        self.assertIn('API SB ao vivo', job['description'])
        self.assertIn('nunca origina republicação', job['description'])
        self.assertIn('sem replay', job['risk'])

    def test_discord_request_retries_seven_rate_limits_before_success(self):
        attempts = []
        delays = []
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self):
                return b'{}'
        def fake_urlopen(request, timeout):
            attempts.append(request.full_url)
            if len(attempts) <= 7:
                raise mod.urllib.error.HTTPError(
                    request.full_url,
                    429,
                    'rate limited',
                    {},
                    io.BytesIO(b'{"retry_after":0}'),
                )
            return Response()
        with patch.object(mod, 'load_env'), \
             patch.dict(os.environ, {'DISCORD_BOT_TOKEN': 'test-token'}), \
             patch.object(mod.urllib.request, 'urlopen', fake_urlopen), \
             patch.object(mod.time, 'sleep', delays.append):
            status, body = mod.discord_request('GET', '/test')
        self.assertEqual(status, 200)
        self.assertEqual(body, {})
        self.assertEqual(len(attempts), 8)
        self.assertEqual(delays, [0.25] * 7)

    def test_post_readback_validates_role_mentions(self):
        calls = []
        payload = mod.build_payloads(self.alerts())[0]
        def fake_request(method, path, body=None, allow_404=False):
            calls.append((method, path))
            if method == 'POST':
                return 200, {'id': '555'}
            return 200, {
                'id': '555',
                'channel_id': '123',
                'content': payload['content'],
                'mentions': [],
                'mention_roles': mod.TEAM_ROLE_IDS,
                'embeds': payload['embeds'],
            }
        original = mod.discord_request
        setattr(mod, 'discord_request', fake_request)
        try:
            self.assertEqual(mod.post_and_verify('123', payload), '555')
        finally:
            setattr(mod, 'discord_request', original)
        self.assertEqual([method for method, _ in calls], ['POST', 'GET'])

    def test_active_incident_is_never_replayed_from_state_on_next_day(self):
        alert = self.alerts()[0]
        state = mod.initial_state()
        mod.register_incidents(state, [alert], ['111'], at='2026-08-26T10:00:00-04:00')
        state['daily']['date'] = '2026-08-26'
        posted = {}
        def fake_request(method, path, body=None, allow_404=False):
            message_id = path.rsplit('/', 1)[-1]
            if message_id == '111':
                return 200, {'id': '111', 'channel_id': '123', 'reactions': []}
            raise AssertionError(f'unexpected Discord request {method} {path}')
        original = mod.discord_request
        setattr(mod, 'discord_request', fake_request)
        try:
            same_day = mod.process_daily_incident_cycle(
                state,
                '123',
                False,
                now_value=datetime.fromisoformat('2026-08-26T16:00:01-04:00'),
                sleep_func=lambda _: None,
            )
            next_day = mod.process_daily_incident_cycle(
                state,
                '123',
                False,
                now_value=datetime.fromisoformat('2026-08-27T00:12:00-04:00'),
                sleep_func=lambda _: None,
            )
            again_next_day = mod.process_daily_incident_cycle(
                state,
                '123',
                False,
                now_value=datetime.fromisoformat('2026-08-27T12:00:00-04:00'),
                sleep_func=lambda _: None,
            )
        finally:
            setattr(mod, 'discord_request', original)
        self.assertEqual(same_day['daily_sent'], 0)
        self.assertEqual(next_day['daily_sent'], 0)
        self.assertEqual(again_next_day['daily_sent'], 0)
        self.assertFalse(next_day['state_only_resend'])
        self.assertEqual(next_day['would_send'], 0)
        incident = next(iter(state['incidents'].values()))
        self.assertEqual(incident['message_ids'], ['111'])
        self.assertEqual(incident['repeat_count'], 0)
        self.assertEqual(posted, {})
        self.assertEqual(state['daily']['date'], '2026-08-27')

    def test_legacy_daily_pending_is_discarded_without_delivery(self):
        alert = self.alerts()[0]
        state = mod.initial_state()
        state['daily'] = {
            'date': '2026-08-26',
            'pending': {'alerts': [alert], 'message_ids': []},
            'last_result': None,
        }
        with patch.object(mod, 'post_and_verify') as post:
            stats = mod.process_daily_incident_cycle(
                state,
                '123',
                False,
                now_value=datetime.fromisoformat('2026-08-27T00:12:00-04:00'),
            )
        post.assert_not_called()
        self.assertEqual(stats['discarded_cached_pending'], 1)
        self.assertEqual(stats['daily_sent'], 0)
        self.assertIsNone(state['daily']['pending'])
        self.assertEqual(state['daily']['last_result']['source'], 'new-live-notification-only')

    def test_pending_recovery_rebuilds_payload_from_live_fixture(self):
        live_alert = self.alerts()[0]
        stale_alert = dict(live_alert)
        stale_alert['user_email'] = 'stale@example.invalid'
        captured = []
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'state.json'
            state = mod.initial_state()
            state['last_seen_id'] = 99
            state['daily']['date'] = datetime.now(mod.NY).date().isoformat()
            stamp = mod.now_iso()
            state['pending'] = {
                'created_at': stamp,
                'notification_ids': [100],
                'cursor_ids': [100],
                'alerts': [stale_alert],
                'fingerprint': 'stale',
                'delivery_specs': [{'repeat_count': 0, 'opened_at': stamp, 'rendered_at': stamp}],
                'message_ids': [],
            }
            mod.save_state(state_path, state)
            args = SimpleNamespace(
                cleanup_old_messages=False,
                fixture=str(FIXTURE),
                test_alert=False,
                baseline=False,
                dry_run=False,
                state_path=str(state_path),
                channel_id='123',
            )
            def fake_post(channel_id, payload):
                captured.append(payload)
                return '555'
            with patch.object(mod, 'post_and_verify', side_effect=fake_post):
                result = asyncio.run(mod.run(args))
        self.assertEqual(result, 0)
        self.assertEqual(len(captured), 1)
        fields = {field['name']: field['value'] for field in captured[0]['embeds'][0]['fields']}
        self.assertEqual(fields['User'], live_alert['user_email'])
        self.assertNotEqual(fields['User'], stale_alert['user_email'])

    def test_new_source_alert_for_active_incident_is_suppressed_intraday(self):
        alert = self.alerts()[0]
        state = mod.initial_state()
        mod.register_incidents(state, [alert], ['111'], at='2026-08-26T10:00:00-04:00')
        newer = dict(alert)
        newer['notification_id'] = 101
        def fake_request(method, path, body=None, allow_404=False):
            return 200, {'id': '111', 'channel_id': '123', 'reactions': []}
        original = mod.discord_request
        setattr(mod, 'discord_request', fake_request)
        try:
            deliverable, stats = mod.classify_new_alerts(state, [newer], '123', False)
        finally:
            setattr(mod, 'discord_request', original)
        self.assertEqual(deliverable, [])
        self.assertEqual(stats['suppressed_active'], 1)
        incident = next(iter(state['incidents'].values()))
        self.assertEqual(incident['alert']['notification_id'], 101)
        self.assertEqual(incident['notification_ids'], [100, 101])

    def test_reacted_incident_reopens_only_for_new_source_alert(self):
        alert = self.alerts()[0]
        state = mod.initial_state()
        mod.register_incidents(state, [alert], ['111'], at='2026-08-26T10:00:00-04:00')
        newer = dict(alert)
        newer['notification_id'] = 101
        def fake_request(method, path, body=None, allow_404=False):
            return 200, {
                'id': '111',
                'channel_id': '123',
                'reactions': [{'emoji': {'name': '✅'}, 'count': 1}],
            }
        original = mod.discord_request
        setattr(mod, 'discord_request', fake_request)
        try:
            deliverable, stats = mod.classify_new_alerts(state, [newer], '123', False)
        finally:
            setattr(mod, 'discord_request', original)
        self.assertEqual(stats['resolved'], 1)
        incident = next(iter(state['incidents'].values()))
        self.assertEqual(incident['status'], 'resolved')
        self.assertEqual([row['notification_id'] for row in deliverable], [101])
        mod.register_incidents(state, [newer], ['222'], at='2026-08-26T18:00:00-04:00')
        reopened = next(iter(state['incidents'].values()))
        self.assertEqual(reopened['status'], 'active')
        self.assertEqual(reopened['repeat_count'], 0)
        self.assertEqual(reopened['opened_at'], '2026-08-26T18:00:00-04:00')
        self.assertEqual(reopened['message_ids'], ['222'])
        self.assertEqual(reopened['notification_ids'], [101])

    def test_duplicate_new_source_rows_deliver_only_latest_incident_snapshot(self):
        alert = self.alerts()[0]
        first = dict(alert)
        first['notification_id'] = 101
        second = dict(alert)
        second['notification_id'] = 102
        deliverable, stats = mod.classify_new_alerts(
            mod.initial_state(),
            [first, second],
            '123',
            True,
        )
        self.assertEqual([row['notification_id'] for row in deliverable], [102])
        self.assertEqual(stats['source_rows'], 2)
        self.assertEqual(stats['deduped_incidents'], 1)

    def test_run_suppresses_active_incident_intraday_and_advances_cursor(self):
        alert = self.alerts()[0]
        calls = []
        def fake_request(method, path, body=None, allow_404=False):
            calls.append((method, path))
            return 200, {'id': '111', 'channel_id': '123', 'reactions': []}
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'state.json'
            state = mod.initial_state()
            mod.register_incidents(state, [alert], ['111'], at=mod.now_iso())
            state['last_seen_id'] = 99
            state['daily']['date'] = datetime.now(mod.NY).date().isoformat()
            mod.save_state(state_path, state)
            args = SimpleNamespace(
                cleanup_old_messages=False,
                fixture=str(FIXTURE),
                test_alert=False,
                baseline=False,
                dry_run=False,
                state_path=str(state_path),
                channel_id='123',
            )
            output = io.StringIO()
            original = mod.discord_request
            setattr(mod, 'discord_request', fake_request)
            try:
                with patch('sys.stdout', output):
                    result = asyncio.run(mod.run(args))
            finally:
                setattr(mod, 'discord_request', original)
            loaded = mod.load_state(state_path)
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())['mode'], 'suppressed')
        self.assertEqual(loaded['last_seen_id'], 100)
        self.assertEqual(loaded['last_delivery']['message_ids'], [])
        self.assertEqual([method for method, _ in calls], ['GET'])

    def test_noop_success_resets_failure_alert_streak_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'state.json'
            state = mod.initial_state()
            state['last_seen_id'] = 100
            state['consecutive_failures'] = 6
            state['failure_alert_sent_for'] = 3
            state['last_error'] = {'type': 'RuntimeError', 'message': 'upstream unavailable'}
            state['daily']['date'] = datetime.now(mod.NY).date().isoformat()
            mod.save_state(state_path, state)
            args = SimpleNamespace(
                cleanup_old_messages=False,
                fixture=str(FIXTURE),
                test_alert=False,
                baseline=False,
                dry_run=False,
                state_path=str(state_path),
                channel_id='123',
            )
            output = io.StringIO()
            with patch('sys.stdout', output):
                result = asyncio.run(mod.run(args))
            loaded = mod.load_state(state_path)
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())['mode'], 'noop')
        self.assertEqual(loaded['consecutive_failures'], 0)
        self.assertEqual(loaded['failure_alert_sent_for'], 0)
        self.assertIsNone(loaded['last_error'])

    def test_malformed_body_fails_closed(self):
        data = self.fixture()
        data['notifications'][0]['BODY'] = '{bad json'
        with self.assertRaises(RuntimeError):
            mod.normalize_alerts(data['notifications'], data['users'], data['pages'])


if __name__ == '__main__':
    unittest.main()
