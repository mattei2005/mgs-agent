import importlib.util
import pathlib
import subprocess
import unittest
from unittest import mock

SCRIPT = pathlib.Path('/root/mgs-agent/scripts/hermes-news-explainer.py')
SPEC = importlib.util.spec_from_file_location('hermes_news_explainer', SCRIPT)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


COMPLETE = """1) O que mudou
- Houve uma atualização relevante.

2) Impacto para Zeus/Atena/MGS
- A operação ganha estabilidade sem alteração automática de configuração.

3) Exige ação?
- Exige revisão controlada antes da atualização.
"""


class HermesNewsExplainerTests(unittest.TestCase):
    def test_accepts_complete_stdout_when_oneshot_aborts(self):
        result = subprocess.CompletedProcess(['hermes'], -6, stdout=COMPLETE, stderr='')
        with mock.patch.object(MODULE.subprocess, 'run', return_value=result):
            self.assertEqual(MODULE.explain('anúncio'), COMPLETE.strip())

    def test_rejects_incomplete_stdout_when_oneshot_fails(self):
        result = subprocess.CompletedProcess(['hermes'], -6, stdout='parcial', stderr='abortado')
        with mock.patch.object(MODULE.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'rc=-6'):
                MODULE.explain('anúncio')

    def test_failed_messages_are_selected_for_retry(self):
        messages = [{'id': '101'}, {'id': '100'}, {'id': '99'}]
        state = {
            'last_seen_id': '101',
            'processed': {
                '100': {'error': 'temporary failure'},
                '99': {'error': 'permanent failure', 'attempts': MODULE.MAX_PROCESSING_ATTEMPTS},
            },
        }
        self.assertEqual(
            [item['id'] for item in MODULE.select_candidates(messages, state)],
            ['100'],
        )

    def test_successful_messages_are_not_selected_again(self):
        messages = [{'id': '100'}]
        state = {'last_seen_id': '100', 'processed': {'100': {'reply_id': '200'}}}
        self.assertEqual(MODULE.select_candidates(messages, state), [])


if __name__ == '__main__':
    unittest.main()