import importlib.util
import json
import stat
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

SCRIPT = Path('/root/mgs-agent/scripts/monitor-sb-messenger-token-invalid.py')
FIXTURE = Path('/root/mgs-agent/tests/fixtures/sb-messenger-token-invalid.json')
spec = importlib.util.spec_from_file_location('sb_token_monitor', SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


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
