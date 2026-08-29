import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path('/root/mgs-agent/scripts/ares-discord-post-with-thread.py')
spec = importlib.util.spec_from_file_location('ares_discord_poster', MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DiscordPostReadbackTests(unittest.TestCase):
    def test_exact_get_readback_is_required(self):
        calls = []

        def fake_request(method, path, token, body=None):
            calls.append((method, path))
            return 200, {'id': 'm1', 'content': 'conteudo exato'}

        result = mod.verify_message_readbacks(
            'thread1', 'secret-never-printed', [('m1', 'conteudo exato')],
            request=fake_request,
        )
        self.assertTrue(result['ok'])
        self.assertEqual(result['confirmed'], 1)
        self.assertEqual(calls, [('GET', '/channels/thread1/messages/m1')])

    def test_content_mismatch_fails_readback(self):
        def fake_request(method, path, token, body=None):
            return 200, {'id': 'm1', 'content': 'diferente'}

        result = mod.verify_message_readbacks(
            'thread1', 'secret-never-printed', [('m1', 'esperado')],
            request=fake_request,
        )
        self.assertFalse(result['ok'])
        self.assertEqual(result['confirmed'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
