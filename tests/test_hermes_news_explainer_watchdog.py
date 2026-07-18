import importlib.util
import json
import pathlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

SCRIPT = pathlib.Path('/root/mgs-agent/scripts/hermes-news-explainer-watchdog.py')
SPEC = importlib.util.spec_from_file_location('hermes_news_explainer_watchdog', SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

NOW = datetime(2026, 7, 18, 16, 0, tzinfo=timezone.utc)


def source_message(age_seconds=480, source_id='1529000000000000001'):
    return {
        'id': source_id,
        'type': 0,
        'timestamp': MODULE.iso(NOW - timedelta(seconds=age_seconds)),
        'author': {'id': MODULE.ZEUS_BOT_ID},
        'content': '',
        'embeds': [{
            'title': 'Hermes Agent — update disponível',
            'fields': [
                {'name': 'Upstream', 'value': 'v2026.7.7.2 (abc123)'},
                {'name': 'Versão local', 'value': 'v2026.7.1 (def456)'},
                {'name': 'Atraso', 'value': '4 dias / 715 commits atrás'},
                {'name': 'Resumo', 'value': 'Features 80 | Fixes 424 | Security 78 | Breaking 0'},
                {'name': 'Breaking', 'value': 'nenhum'},
                {'name': 'Antes de atualizar', 'value': 'Verificar conflito com patches locais.'},
            ],
        }],
    }


def explanation(source_id, reply_id='1529000000000000100', content=None):
    return {
        'id': reply_id,
        'type': 19,
        'timestamp': MODULE.iso(NOW),
        'author': {'id': MODULE.ZEUS_BOT_ID},
        'message_reference': {'message_id': source_id, 'channel_id': MODULE.CHANNEL_ID},
        'content': content or (
            '1) O que mudou\n- Atualização detectada.\n\n'
            '2) Impacto para Zeus/Atena/MGS\n- Nenhuma mudança automática.\n\n'
            '3) Exige ação?\n- Sim, revisão controlada antes de atualizar.'
        ),
        'embeds': [],
    }


class FakeDiscord:
    def __init__(self, messages, fail_reply_posts=0):
        self.messages = list(messages)
        self.fail_reply_posts = fail_reply_posts
        self.posts = []
        self.by_id = {str(m['id']): m for m in messages}
        self.next_id = 1529000000000001000

    def __call__(self, token, method, path, body=None):
        if method == 'GET' and path.startswith(f'/channels/{MODULE.CHANNEL_ID}/messages?'):
            return list(reversed(sorted(self.messages, key=lambda m: int(m['id']))))
        if method == 'GET' and f'/channels/{MODULE.CHANNEL_ID}/messages/' in path:
            message_id = path.rsplit('/', 1)[-1]
            if message_id not in self.by_id:
                raise RuntimeError('not found')
            return self.by_id[message_id]
        if method == 'GET' and f'/channels/{MODULE.ALERTS_INFRA_CHANNEL_ID}/messages/' in path:
            message_id = path.rsplit('/', 1)[-1]
            if message_id not in self.by_id:
                raise RuntimeError('not found')
            return self.by_id[message_id]
        if method == 'POST' and path == f'/channels/{MODULE.CHANNEL_ID}/messages':
            if self.fail_reply_posts > 0:
                self.fail_reply_posts -= 1
                raise RuntimeError('simulated reply delivery failure')
            self.next_id += 1
            message_id = str(self.next_id)
            msg = explanation(body['message_reference']['message_id'], message_id, body['content'])
            self.messages.append(msg)
            self.by_id[message_id] = msg
            self.posts.append((path, body, message_id))
            return {'id': message_id}
        if method == 'POST' and path == f'/channels/{MODULE.ALERTS_INFRA_CHANNEL_ID}/messages':
            self.next_id += 1
            message_id = str(self.next_id)
            msg = {
                'id': message_id,
                'type': 0,
                'timestamp': MODULE.iso(NOW),
                'author': {'id': MODULE.ZEUS_BOT_ID},
                'content': body.get('content', ''),
                'embeds': body.get('embeds', []),
            }
            self.by_id[message_id] = msg
            self.posts.append((path, body, message_id))
            return {'id': message_id}
        raise AssertionError((method, path, body))


class WatchdogTests(unittest.TestCase):
    def make_watchdog(self, fake, tmp, generator):
        state = pathlib.Path(tmp) / 'watchdog.json'
        primary = pathlib.Path(tmp) / 'primary.json'
        lock = pathlib.Path(tmp) / 'delivery.lock'
        primary.write_text(json.dumps({'last_seen_id': None, 'processed': {}}, indent=2))
        return MODULE.Watchdog(
            'test-token',
            api_func=fake,
            generator=generator,
            state_file=state,
            primary_state_file=primary,
            delivery_lock=lock,
            now_fn=lambda: NOW,
        ), state, primary

    def test_source_and_reply_classification(self):
        source = source_message()
        reply = explanation(source['id'])
        self.assertTrue(MODULE.is_source_announcement(source))
        self.assertFalse(MODULE.is_source_announcement(reply))
        self.assertEqual(MODULE.referenced_source_id(reply), source['id'])

    def test_deterministic_fallback_has_required_contract_and_confirmed_fields(self):
        text = MODULE.deterministic_fallback(source_message())
        self.assertTrue(MODULE.is_usable_explanation(text))
        self.assertIn('715 commits', text)
        self.assertIn('Nenhuma atualização, configuração ou restart foi aplicado', text)

    def test_existing_reply_reconciles_inconsistent_primary_state_without_posting(self):
        source = source_message()
        reply = explanation(source['id'])
        fake = FakeDiscord([source, reply])
        with tempfile.TemporaryDirectory() as tmp:
            wd, state_path, primary_path = self.make_watchdog(fake, tmp, lambda _: 'unused')
            primary_path.write_text(json.dumps({
                'last_seen_id': source['id'],
                'processed': {source['id']: {'error': 'stale', 'attempts': 3}},
            }))
            self.assertEqual(wd.run(), 0)
            primary = json.loads(primary_path.read_text())
            self.assertEqual(primary['processed'][source['id']]['reply_id'], reply['id'])
            self.assertNotIn('error', primary['processed'][source['id']])
            state = json.loads(state_path.read_text())
            self.assertEqual(state['records'][source['id']]['status'], 'completed')
            self.assertEqual(fake.posts, [])

    def test_orphan_llm_failure_posts_fallback_reads_back_and_alerts_infra(self):
        source = source_message()
        fake = FakeDiscord([source])
        with tempfile.TemporaryDirectory() as tmp:
            def fail_generator(_):
                raise RuntimeError('simulated LLM failure')
            wd, state_path, primary_path = self.make_watchdog(fake, tmp, fail_generator)
            self.assertEqual(wd.run(), 0)
            reply_posts = [p for p in fake.posts if p[0] == f'/channels/{MODULE.CHANNEL_ID}/messages']
            infra_posts = [p for p in fake.posts if p[0] == f'/channels/{MODULE.ALERTS_INFRA_CHANNEL_ID}/messages']
            self.assertEqual(len(reply_posts), 1)
            self.assertEqual(len(infra_posts), 1)
            self.assertEqual(infra_posts[0][1]['content'], '')
            self.assertEqual(infra_posts[0][1]['allowed_mentions'], {'parse': []})
            state = json.loads(state_path.read_text())
            record = state['records'][source['id']]
            self.assertEqual(record['status'], 'completed')
            self.assertTrue(record['fallback_used'])
            self.assertTrue(record['infra_fallback']['message_id'])
            primary = json.loads(primary_path.read_text())
            self.assertEqual(primary['processed'][source['id']]['reply_id'], record['reply_id'])
            self.assertTrue(primary['processed'][source['id']]['recovered_by_watchdog'])

    def test_successful_llm_recovery_does_not_alert_infra(self):
        source = source_message()
        fake = FakeDiscord([source])
        good = explanation(source['id'])['content']
        with tempfile.TemporaryDirectory() as tmp:
            wd, state_path, _ = self.make_watchdog(fake, tmp, lambda _: good)
            wd.run()
            infra_posts = [p for p in fake.posts if p[0] == f'/channels/{MODULE.ALERTS_INFRA_CHANNEL_ID}/messages']
            self.assertEqual(infra_posts, [])
            record = json.loads(state_path.read_text())['records'][source['id']]
            self.assertEqual(record['completion_mode'], 'llm_recovery')
            self.assertFalse(record['fallback_used'])

    def test_delivery_failure_remains_pending_with_backoff_and_no_false_completion(self):
        source = source_message()
        fake = FakeDiscord([source], fail_reply_posts=1)
        good = explanation(source['id'])['content']
        with tempfile.TemporaryDirectory() as tmp:
            wd, state_path, primary_path = self.make_watchdog(fake, tmp, lambda _: good)
            wd.run()
            record = json.loads(state_path.read_text())['records'][source['id']]
            self.assertEqual(record['status'], 'retry_pending')
            self.assertEqual(record['delivery_failures'], 1)
            self.assertTrue(record['next_attempt_at'])
            primary = json.loads(primary_path.read_text())
            self.assertNotIn(source['id'], primary['processed'])

    def test_dry_run_is_state_neutral_and_does_not_post(self):
        source = source_message()
        fake = FakeDiscord([source])
        with tempfile.TemporaryDirectory() as tmp:
            wd, state_path, primary_path = self.make_watchdog(fake, tmp, lambda _: 'unused')
            before = primary_path.read_bytes()
            wd.run(dry_run=True)
            self.assertFalse(state_path.exists())
            self.assertEqual(primary_path.read_bytes(), before)
            self.assertEqual(fake.posts, [])

    def test_waits_until_recovery_window(self):
        source = source_message(age_seconds=300)
        fake = FakeDiscord([source])
        with tempfile.TemporaryDirectory() as tmp:
            wd, state_path, _ = self.make_watchdog(fake, tmp, lambda _: 'unused')
            wd.run()
            state = json.loads(state_path.read_text())
            self.assertEqual(state['last_scan_counts']['waiting'], 1)
            self.assertEqual(fake.posts, [])


if __name__ == '__main__':
    unittest.main()
