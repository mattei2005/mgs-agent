"""Offline regression of exact archived-child recovery and cron launchers."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path('/root/.hermes/profiles/ares/scripts')

def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

D = module('shein-daily-report')

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        D.save(self.root / 'adsets.json', [{'id': 's1', 'campaign_id': '1'}])
        D.save(self.root / 'ads.json', [{'id': 'a1', 'campaign_id': '1', 'account_id': '9'}])
        self.runner = D.Runner.__new__(D.Runner)
        def paged(path, params):
            cid, edge = path.split('/')
            self.assertEqual(json.loads(params['effective_status']), ['ARCHIVED'])
            return [{'id': edge + cid, 'campaign_id': cid, **({'account_id': '9'} if edge == 'ads' else {})}]
        self.runner.paged = Mock(side_effect=paged)
        self.cm = {'1': {'status': 'ACTIVE'}, '2': {'status': 'ARCHIVED'}, '3': {'status': 'ARCHIVED'}}

    def recover(self):
        self.runner.recover_archived_configuration(self.root, '9', ['1', '2'], self.cm)

    def test_exact_missing_only_and_financial_selection_preserved(self):
        self.recover()
        self.assertEqual([c.args[0] for c in self.runner.paged.call_args_list], ['2/adsets', '2/ads'])
        self.assertEqual(len(D.load(self.root / 'adsets.json')), 2)
        self.assertEqual(D.load(self.root / 'ads-archived-recovery.json')['campaign_ids'], ['2'])
        self.recover()
        self.assertEqual(self.runner.paged.call_count, 2)

    def test_active_missing_not_replaced_by_archive(self):
        self.cm['2']['status'] = 'ACTIVE'
        self.recover()
        self.runner.paged.assert_not_called()
        self.assertEqual(len(D.load(self.root / 'adsets.json')), 1)

    def test_wrong_campaign_fails_without_write(self):
        self.runner.paged.side_effect = None
        self.runner.paged.return_value = [{'id': 'bad', 'campaign_id': '3'}]
        with self.assertRaises(AssertionError): self.recover()
        self.assertEqual(len(D.load(self.root / 'adsets.json')), 1)

    def test_wrong_account_ads_fail(self):
        self.runner.paged.side_effect = lambda path, params: ([{'id': 's2', 'campaign_id': '2'}] if path.endswith('/adsets') else [{'id': 'a2', 'campaign_id': '2', 'account_id': '8'}])
        with self.assertRaises(AssertionError): self.recover()
        self.assertEqual(len(D.load(self.root / 'ads.json')), 1)

    def test_duplicate_child_fails(self):
        self.runner.paged.side_effect = None
        self.runner.paged.return_value = [{'id': 's2', 'campaign_id': '2'}] * 2
        with self.assertRaises(AssertionError): self.recover()

    def test_empty_archive_is_not_fabricated(self):
        self.runner.paged.side_effect = None
        self.runner.paged.return_value = []
        self.recover()
        self.assertEqual(len(D.load(self.root / 'adsets.json')), 1)
        self.assertFalse((self.root / 'adsets-archived-recovery.json').exists())

    def test_intraday_wrapper_uses_python_not_shell_and_forwards(self):
        cron = module('shein-intraday-cron')
        with patch.object(cron.os, 'execv') as execute, patch.object(sys, 'argv', ['cron', '--slot', '14:11', '--scheduled']):
            cron.main()
        interpreter, argv = execute.call_args.args
        self.assertTrue(Path(interpreter).name.startswith('python'))
        self.assertEqual(argv[2:], ['--slot', '14:11', '--scheduled'])

    def test_daily_wrapper_runtime_and_result_journal(self):
        cron = module('shein-daily-cron')
        actual = subprocess.run
        commands = []
        def run(command, **kwargs):
            if len(command) > 1 and command[1].endswith('/shein-daily-report.py'):
                commands.append(command)
                return subprocess.CompletedProcess(command, 0, '{"status":"COMPLETE_GET_VERIFIED"}', '')
            return actual(command, **kwargs)
        with patch.object(cron, 'STATE', self.root), patch.object(cron.subprocess, 'run', side_effect=run): cron.run()
        self.assertTrue(Path(commands[0][0]).name.startswith('python'))
        self.assertEqual(D.load(self.root / 'last-cron-result.json')['returncode'], 0)

if __name__ == '__main__': unittest.main()
