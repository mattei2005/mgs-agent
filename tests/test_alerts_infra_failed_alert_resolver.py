import importlib.util
import pathlib
import subprocess
import unittest
from unittest import mock

SCRIPT = pathlib.Path('/root/mgs-agent/scripts/alerts-infra-failed-alert-resolver.py')
SPEC = importlib.util.spec_from_file_location('alerts_infra_failed_alert_resolver', SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FailedAlertResolverTests(unittest.TestCase):
    def test_delivers_final_stdout_when_oneshot_aborts_after_response(self):
        completed = subprocess.CompletedProcess(
            ['hermes'],
            -6,
            stdout='Resolvido. Readback real concluído.',
            stderr='native abort after shutdown',
        )
        with mock.patch.object(MODULE.subprocess, 'run', return_value=completed):
            result = MODULE.run_hermes_resolution('alerta de cron error', 'https://discord.invalid/message')
        self.assertEqual(result, 'Resolvido. Readback real concluído.')

    def test_rejects_nonzero_exit_without_final_stdout(self):
        completed = subprocess.CompletedProcess(['hermes'], -6, stdout='', stderr='native abort')
        with mock.patch.object(MODULE.subprocess, 'run', return_value=completed):
            with self.assertRaisesRegex(RuntimeError, 'rc=-6 sem resposta final'):
                MODULE.run_hermes_resolution('alerta de cron error', 'https://discord.invalid/message')

    def test_feedback_is_reply_embed_without_mentions(self):
        message = {'id': '123', 'channel_id': MODULE.CHANNEL_ID}
        payload = MODULE.build_feedback_payload(message, 'Resolvido com readback real.')
        self.assertEqual(payload['content'], '')
        self.assertEqual(payload['allowed_mentions'], {'parse': []})
        self.assertEqual(payload['message_reference']['message_id'], '123')
        self.assertEqual(payload['embeds'][0]['color'], MODULE.RESOLVED_COLOR)


if __name__ == '__main__':
    unittest.main()
