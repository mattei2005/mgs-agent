import importlib.machinery
import importlib.util
import json
import pathlib
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

SCRIPT = pathlib.Path('/root/mgs-agent/scripts/monitor-gpt55-oauth-cost.sh')
LOADER = importlib.machinery.SourceFileLoader('monitor_gpt56_oauth_usage', str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(MODULE)


def create_profile(root: pathlib.Path, profile: str, rows: list[dict]) -> None:
    directory = root / profile
    directory.mkdir(parents=True)
    (directory / 'config.yaml').write_text(
        'model:\n  default: gpt-5.6-sol\n  provider: openai-codex\n',
        encoding='utf-8',
    )
    conn = sqlite3.connect(directory / 'state.db')
    conn.executescript(
        '''
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL
        );
        CREATE TABLE session_model_usage (
            session_id TEXT NOT NULL,
            model TEXT NOT NULL,
            billing_provider TEXT NOT NULL,
            billing_mode TEXT NOT NULL,
            api_call_count INTEGER NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            cache_read_tokens INTEGER NOT NULL,
            cache_write_tokens INTEGER NOT NULL,
            reasoning_tokens INTEGER NOT NULL,
            actual_cost_usd REAL NOT NULL,
            first_seen REAL,
            last_seen REAL
        );
        '''
    )
    for index, row in enumerate(rows, 1):
        session_id = f'session-{index}'
        conn.execute('INSERT INTO sessions(id, source) VALUES (?, ?)', (session_id, row['source']))
        conn.execute(
            '''INSERT INTO session_model_usage(
                   session_id, model, billing_provider, billing_mode,
                   api_call_count, input_tokens, output_tokens,
                   cache_read_tokens, cache_write_tokens, reasoning_tokens,
                   actual_cost_usd, first_seen, last_seen
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                session_id,
                row.get('model', 'gpt-5.6-sol'),
                row.get('provider', 'openai-codex'),
                row.get('billing_mode', 'subscription_included'),
                row['api_calls'],
                row['input_tokens'],
                row['output_tokens'],
                row.get('cache_read_tokens', 0),
                row.get('cache_write_tokens', 0),
                row.get('reasoning_tokens', 0),
                row.get('actual_cost_usd', 0.0),
                row['first_seen'],
                row['last_seen'],
            ),
        )
    conn.commit()
    conn.close()


class _CaptureHandler(BaseHTTPRequestHandler):
    body = None
    authorization = None

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        type(self).body = json.loads(self.rfile.read(length))
        type(self).authorization = self.headers.get('Authorization')
        response = json.dumps({'id': 'mock-message', 'channel_id': 'mock-channel'}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        return


class GPT56OAuthUsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.now = datetime(2026, 7, 19, 16, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def test_counts_cli_and_discord_from_sqlite_with_real_tokens(self):
        inside = self.now - timedelta(hours=2)
        create_profile(self.root, 'zeus', [
            {
                'source': 'cli', 'api_calls': 20, 'input_tokens': 181924,
                'output_tokens': 7338, 'cache_read_tokens': 1987072,
                'first_seen': inside.timestamp(), 'last_seen': inside.timestamp(),
            },
            {
                'source': 'discord', 'api_calls': 4, 'input_tokens': 79794,
                'output_tokens': 1144, 'cache_read_tokens': 25088,
                'first_seen': inside.timestamp(), 'last_seen': inside.timestamp(),
            },
        ])
        with mock.patch.object(MODULE, 'PROFILES', ('zeus',)), mock.patch.object(MODULE, 'PROFILES_ROOT', self.root):
            payload, summary = MODULE.build_report(self.now)
        self.assertEqual(summary['total_calls'], 24)
        self.assertEqual(summary['total_sessions'], 2)
        self.assertEqual(summary['input_tokens'], 261718)
        self.assertEqual(summary['output_tokens'], 8482)
        self.assertEqual(summary['sources'], {'cli': 20, 'discord': 4})
        self.assertEqual(summary['coverage'], 'exata')
        self.assertIn('uso real', payload['embeds'][0]['title'])
        self.assertIn('state.db/session_model_usage', payload['embeds'][0]['footer']['text'])

    def test_flags_session_that_crosses_window_boundary(self):
        create_profile(self.root, 'zeus', [{
            'source': 'discord', 'api_calls': 10, 'input_tokens': 1000,
            'output_tokens': 100, 'first_seen': (self.now - timedelta(hours=25)).timestamp(),
            'last_seen': (self.now - timedelta(hours=1)).timestamp(),
        }])
        with mock.patch.object(MODULE, 'PROFILES', ('zeus',)), mock.patch.object(MODULE, 'PROFILES_ROOT', self.root):
            _, summary = MODULE.build_report(self.now)
        self.assertEqual(summary['boundary_sessions'], 1)
        self.assertIn('cruzam o início', summary['coverage'])

    def test_mock_discord_delivery_has_empty_content_and_no_secret_in_payload(self):
        server = HTTPServer(('127.0.0.1', 0), _CaptureHandler)
        thread = threading.Thread(target=server.handle_request)
        thread.start()
        try:
            payload = {'content': '', 'embeds': [{'title': 'teste'}]}
            result = MODULE.post_discord(payload, {
                'MGS_DISCORD_API_URL_OVERRIDE': f'http://127.0.0.1:{server.server_port}/messages',
                'MGS_DISCORD_CHANNEL_ID_OVERRIDE': 'mock-channel',
                'MGS_DISCORD_BOT_TOKEN_OVERRIDE': 'fixture-token',
            })
        finally:
            thread.join(timeout=5)
            server.server_close()
        self.assertEqual(result['id'], 'mock-message')
        captured = _CaptureHandler.body
        self.assertIsInstance(captured, dict)
        assert isinstance(captured, dict)
        self.assertEqual(captured, payload)
        self.assertEqual(captured['content'], '')
        self.assertNotIn('fixture-token', json.dumps(captured))
        self.assertEqual(_CaptureHandler.authorization, 'Bot fixture-token')


if __name__ == '__main__':
    unittest.main()
