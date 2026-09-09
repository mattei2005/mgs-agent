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

    def test_git_metrics_prompt_explains_distinct_bases(self):
        result = subprocess.CompletedProcess(['hermes'], 0, stdout=COMPLETE, stderr='')
        with mock.patch.object(MODULE.subprocess, 'run', return_value=result) as run_mock:
            MODULE.explain('Novos desde o último alerta: 5093; pendentes: 2082')
        prompt = run_mock.call_args.args[0][-1]
        self.assertIn('novos no main desde o último alerta', prompt)
        self.assertIn('main pós-release', prompt)
        self.assertIn('Nunca trate commits do main pós-release como atraso do runtime', prompt)

    def test_monitor_alert_recognizes_all_current_titles_and_future_field_contract(self):
        for title in MODULE.HERMES_MONITOR_TITLES:
            message = {'embeds': [{'title': title, 'fields': []}]}
            self.assertTrue(MODULE.is_hermes_monitor_alert(message), title)
        future = {
            'embeds': [{
                'title': 'Hermes Agent — novo estado de release',
                'fields': [{'name': 'Atualização estável', 'value': 'Nenhuma'}],
            }],
        }
        self.assertTrue(MODULE.is_hermes_monitor_alert(future))

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