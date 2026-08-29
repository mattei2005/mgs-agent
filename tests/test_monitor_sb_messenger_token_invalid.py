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
        self.assertEqual(embed['fields'][2]['value'], '2')

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

    def test_atomic_state_mode_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            state = mod.initial_state()
            mod.save_state(path, state)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            loaded = mod.load_state(path)
            self.assertEqual(loaded['last_seen_id'], 0)
            self.assertEqual(loaded['_meta']['reminder_hours'], 3)

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

    def test_unresolved_incident_counts_repeats_and_open_age(self):
        alert = self.alerts()[0]
        state = mod.initial_state()
        mod.register_incidents(state, [alert], ['111'], at='2026-08-26T10:00:00-04:00')
        posted = {}
        post_order = []
        def fake_request(method, path, body=None, allow_404=False):
            if method == 'POST':
                message_id = str(222 + 111 * len(post_order))
                posted[message_id] = body
                post_order.append(message_id)
                return 200, {'id': message_id}
            message_id = path.rsplit('/', 1)[-1]
            if message_id == '111':
                return 200, {'id': '111', 'channel_id': '123', 'reactions': []}
            payload = posted[message_id]
            return 200, {
                'id': message_id,
                'channel_id': '123',
                'content': payload['content'],
                'mentions': [],
                'mention_roles': mod.TEAM_ROLE_IDS,
                'embeds': payload['embeds'],
                'reactions': [],
            }
        original = mod.discord_request
        setattr(mod, 'discord_request', fake_request)
        try:
            first = mod.process_incident_reminders(
                state,
                '123',
                False,
                now_value=datetime.fromisoformat('2026-08-26T13:00:01-04:00'),
            )
            second = mod.process_incident_reminders(
                state,
                '123',
                False,
                now_value=datetime.fromisoformat('2026-08-26T16:00:02-04:00'),
            )
        finally:
            setattr(mod, 'discord_request', original)
        self.assertEqual(first['reminded'], 1)
        self.assertEqual(second['reminded'], 1)
        incident = next(iter(state['incidents'].values()))
        self.assertEqual(incident['message_ids'], ['111', '222', '333'])
        self.assertEqual(incident['repeat_count'], 2)
        self.assertEqual(posted['222']['embeds'][0]['title'], 'LEMBRETE #1 — FINANCEADX — Token Messenger inválido')
        self.assertEqual(posted['222']['embeds'][0]['footer']['text'], 'Aberto há 3h · repetido 1x · SB #100')
        self.assertEqual(posted['333']['embeds'][0]['title'], 'LEMBRETE #2 — FINANCEADX — Token Messenger inválido')
        self.assertEqual(posted['333']['embeds'][0]['footer']['text'], 'Aberto há 6h · repetido 2x · SB #100')

    def test_new_source_alert_for_active_incident_is_counted_as_repeat(self):
        alert = self.alerts()[0]
        state = mod.initial_state()
        mod.register_incidents(state, [alert], ['111'], at='2026-08-26T10:00:00-04:00')
        newer = dict(alert)
        newer['notification_id'] = 101
        specs = mod.selected_delivery_specs(
            state,
            [newer],
            now_value=datetime.fromisoformat('2026-08-26T11:00:00-04:00'),
        )
        payload = mod.build_payloads_from_specs([newer], specs)[0]
        self.assertEqual(specs[0]['repeat_count'], 1)
        self.assertEqual(payload['embeds'][0]['title'], 'LEMBRETE #1 — FINANCEADX — Token Messenger inválido')
        self.assertEqual(payload['embeds'][0]['footer']['text'], 'Aberto há 1h · repetido 1x · SB #101')

    def test_checkmark_resolves_incident_and_stops_reminder(self):
        alert = self.alerts()[0]
        state = mod.initial_state()
        mod.register_incidents(state, [alert], ['111'], at='2026-08-26T10:00:00-04:00')
        def fake_request(method, path, body=None, allow_404=False):
            return 200, {
                'id': '111',
                'channel_id': '123',
                'reactions': [{'emoji': {'name': '✅'}, 'count': 1}],
            }
        original = mod.discord_request
        setattr(mod, 'discord_request', fake_request)
        try:
            stats = mod.process_incident_reminders(
                state,
                '123',
                False,
                now_value=datetime.fromisoformat('2026-08-26T13:00:01-04:00'),
            )
        finally:
            setattr(mod, 'discord_request', original)
        self.assertEqual(stats['resolved'], 1)
        incident = next(iter(state['incidents'].values()))
        self.assertEqual(incident['status'], 'resolved')
        newer = dict(alert)
        newer['notification_id'] = 101
        mod.register_incidents(state, [newer], ['222'], at='2026-08-26T18:00:00-04:00')
        reopened = next(iter(state['incidents'].values()))
        self.assertEqual(reopened['status'], 'active')
        self.assertEqual(reopened['repeat_count'], 0)
        self.assertEqual(reopened['opened_at'], '2026-08-26T18:00:00-04:00')
        self.assertEqual(reopened['message_ids'], ['222'])
        self.assertEqual(reopened['notification_ids'], [101])

    def test_malformed_body_fails_closed(self):
        data = self.fixture()
        data['notifications'][0]['BODY'] = '{bad json'
        with self.assertRaises(RuntimeError):
            mod.normalize_alerts(data['notifications'], data['users'], data['pages'])


if __name__ == '__main__':
    unittest.main()
