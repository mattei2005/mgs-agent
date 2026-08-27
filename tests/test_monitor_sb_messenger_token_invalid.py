import importlib.util
import json
import os
import stat
import tempfile
import unittest
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

    def test_filter_and_exact_page_count(self):
        data = self.fixture()
        alerts = mod.normalize_alerts(data['notifications'], data['pages'])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['notification_id'], 100)
        self.assertEqual(alerts[0]['pages'], 2)
        self.assertEqual(alerts[0]['page_count_scope'], 'company-domain-user')
        self.assertEqual(alerts[0]['source'], 'canary')

    def test_payload_has_no_mentions_and_canary_label(self):
        data = self.fixture()
        alert = mod.normalize_alerts(data['notifications'], data['pages'])[0]
        payload = mod.build_payloads([alert], canary=True)[0]
        self.assertEqual(payload['content'], '')
        self.assertEqual(payload['allowed_mentions'], {'parse': []})
        embed = payload['embeds'][0]
        self.assertEqual(embed['title'], 'CANÁRIO — FINANCEADX — Token Messenger inválido')
        self.assertNotIn('description', embed)
        self.assertEqual([field['name'] for field in embed['fields']], ['User', 'Segurador', 'Páginas'])
        self.assertEqual(embed['fields'][2]['value'], '2')

    def test_chunking_is_bounded_to_ten_embeds(self):
        data = self.fixture()
        alert = mod.normalize_alerts(data['notifications'], data['pages'])[0]
        rows = []
        for index in range(23):
            row = dict(alert)
            row['notification_id'] = 1000 + index
            row['user_id'] = str(index)
            rows.append(row)
        payloads = mod.build_payloads(rows)
        self.assertEqual([len(payload['embeds']) for payload in payloads], [10, 10, 3])

    def test_atomic_state_mode_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            state = mod.initial_state()
            mod.save_state(path, state)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(mod.load_state(path)['last_seen_id'], 0)

    def test_post_readback_validates_zero_mentions(self):
        calls = []
        payload = {'content': '', 'allowed_mentions': {'parse': []}, 'embeds': [{'title': 'Teste'}]}
        def fake_request(method, path, body=None, allow_404=False):
            calls.append((method, path))
            if method == 'POST':
                return 200, {'id': '555'}
            return 200, {'id': '555', 'channel_id': '123', 'content': '', 'mentions': [], 'embeds': [{'title': 'Teste'}]}
        original = mod.discord_request
        setattr(mod, 'discord_request', fake_request)
        try:
            self.assertEqual(mod.post_and_verify('123', payload), '555')
        finally:
            setattr(mod, 'discord_request', original)
        self.assertEqual([method for method, _ in calls], ['POST', 'GET'])

    def test_malformed_body_fails_closed(self):
        data = self.fixture()
        data['notifications'][0]['BODY'] = '{bad json'
        with self.assertRaises(RuntimeError):
            mod.normalize_alerts(data['notifications'], data['pages'])


if __name__ == '__main__':
    unittest.main()
