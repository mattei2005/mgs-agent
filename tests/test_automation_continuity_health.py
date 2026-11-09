import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timezone

BASE = Path('/root/mgs-agent')
spec = importlib.util.spec_from_file_location('report_health', BASE / 'scripts/mgs_report_scheduler_health.py')
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReceiptTests(unittest.TestCase):
    def setup_receipt(self, root, script, **changes):
        directory, expected, threshold = m.REPORTS[script]
        now = time.time()
        payload = dict(status='COMPLETE_GET_VERIFIED', accounts=expected, completed_at=datetime.fromtimestamp(now, timezone.utc).isoformat())
        payload.update(changes)
        path = root / directory / 'last-cron-result.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(payload))
        return now, path

    def test_intraday_complete_and_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            now, path = self.setup_receipt(root, 'ares/shein-intraday-cron.py')
            self.assertEqual(m.report_health('ares/shein-intraday-cron.py', now, root=root)[0], 'OK')
            self.assertEqual(m.report_health('ares/shein-intraday-cron.py', now+11*3600, root=root)[0], 'OK')
            self.assertEqual(m.report_health('ares/shein-intraday-cron.py', now+13*3600, root=root)[0], 'STALE')

    def test_partial_coverage_and_wrong_status_fail_closed(self):
        for change in ({'accounts':23}, {'status':'PARTIAL'}, {'completed_at':'bad'}, {'completed_at':'2026-11-08T12:00:00'}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                now, path = self.setup_receipt(root, 'ares/shein-intraday-cron.py', **change)
                self.assertEqual(m.report_health('ares/shein-intraday-cron.py', now, root=root)[0], 'ERROR')

    def test_newer_log_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            now, path = self.setup_receipt(root, 'ares/shein-intraday-cron.py')
            self.assertIsNone(m.report_health('ares/shein-intraday-cron.py', now, path.stat().st_mtime+60, root=root))

    def test_daily_wrapper_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            now, path = self.setup_receipt(root, 'ares/shein-daily-cron.py')
            inner = json.loads(path.read_text())
            wrapped = {'returncode':0, 'at':inner['completed_at'], 'stdout':json.dumps(inner)}
            path.write_text(json.dumps(wrapped))
            self.assertEqual(m.report_health('ares/shein-daily-cron.py', now, root=root)[0], 'OK')
            wrapped['returncode']=1
            path.write_text(json.dumps(wrapped))
            self.assertEqual(m.report_health('ares/shein-daily-cron.py', now, root=root)[0], 'ERROR')

    def test_missing_and_corrupt_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(m.report_health('ares/shein-daily-cron.py', time.time(), root=root)[0], 'ERROR')
            now, path = self.setup_receipt(root, 'ares/shein-daily-cron.py')
            path.write_text('{')
            self.assertEqual(m.report_health('ares/shein-daily-cron.py', now, root=root)[0], 'ERROR')

    def test_creation_needs_exact_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / 'shein-campaign-creation-daily' / '2026-11-08'
            home.mkdir(parents=True)
            now = time.time()
            (home/'run.json').write_text(json.dumps({'status':'complete','complete_accounts':36,'completed_at':datetime.fromtimestamp(now,timezone.utc).isoformat()}))
            (home/'delivery.json').write_text(json.dumps({'status':'GET_VERIFIED','complete_accounts':36,'message_id':'123'}))
            self.assertEqual(m.report_health('ares/shein-campaign-creation-cron.py', now, root=root)[0], 'OK')
            (home/'delivery.json').write_text(json.dumps({'status':'PENDING','complete_accounts':36}))
            self.assertEqual(m.report_health('ares/shein-campaign-creation-cron.py', now, root=root)[0], 'ERROR')


class IntegratedTests(unittest.TestCase):
    def test_profile_wrapper_and_nonzero_exit_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bindir = root/'bin'
            bindir.mkdir()
            log = root/'fake.log'
            crontab = bindir/'crontab'
            crontab.write_text('#!/usr/bin/env python3\nprint('+repr('* * * * * /usr/bin/python3 /root/.hermes/profiles/ares/scripts/custom-audit.py >> '+str(log)+' 2>&1')+')\n')
            crontab.chmod(0o755)
            env = dict(os.environ, PATH=str(bindir)+':'+os.environ['PATH'],CRON_STALE_STATE=str(root/'state.json'))
            for line, status in [('START\nEND rc=2\n','ERROR'), ('START\n"execution_complete": false\n','ERROR'), ('START\nEND rc=0\n','OK'), ('START\nEND rc=2\nSTART\nEND rc=0\n','OK')]:
                with self.subTest(line=line):
                    log.write_text(line)
                    result = subprocess.run([str(BASE/'scripts/monitor-cron-stale-logs.sh'),'--dry-run'],env=env,capture_output=True,text=True,timeout=30)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertIn('ares/custom-audit.py',result.stdout)
                    self.assertIn('| '+status.ljust(6)+' |',result.stdout)
            self.assertFalse((root/'state.json').exists())


if __name__ == '__main__':
    unittest.main()
