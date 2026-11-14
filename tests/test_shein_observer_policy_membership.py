"""Policy-derived coverage must not regress after authorized account enrollment."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

spec = importlib.util.spec_from_file_location('membership_health', Path(__file__).resolve().parents[1]/'scripts/mgs_report_scheduler_health.py')
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PolicyMembershipTests(unittest.TestCase):
    def fixture(self, root, directory, count):
        policies = root/'policies'
        policies.mkdir()
        policy = {'enabled': True, 'authorized_by_discord_id': '344196393512075265',
                  'expected_reports': count, 'account_ids': [str(1000+i) for i in range(count)],
                  'thread_ids': [str(2000+i) for i in range(count)]}
        path = policies/(directory+'.json')
        path.write_text(json.dumps(policy))
        home = root/directory
        home.mkdir()
        stamp = datetime.now(timezone.utc)
        payload = {'status': 'COMPLETE_GET_VERIFIED', 'accounts': count, 'completed_at': stamp.isoformat()}
        if directory == 'shein-daily-report':
            payload = {'returncode': 0, 'at': stamp.isoformat(), 'stdout': json.dumps(payload)}
        (home/'last-cron-result.json').write_text(json.dumps(payload))
        return path, policy, stamp.timestamp()

    def test_enrolled_counts_without_fixed_24_assumption(self):
        for directory, count in [('shein-daily-report', 24), ('shein-daily-report', 25), ('shein-intraday-report', 26)]:
            with self.subTest(directory=directory, count=count), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, _, now = self.fixture(root, directory, count)
                result = m.report_health('ares/'+directory.replace('-report', '-cron.py'), now, root=root, policy_root=root/'policies')
                self.assertEqual(result[0], 'OK', result)
                self.assertIn('accounts='+str(count), result[1])

    def test_invalid_or_missing_policy_never_uses_receipt_as_expected(self):
        changes = [None, [], {'enabled': False}, {'expected_reports': 24},
                   {'expected_reports': True}, {'authorized_by_discord_id': 'other'},
                   {'account_ids': ['1000']*25}, {'thread_ids': ['2000']*25},
                   {'thread_ids': [None]*25}]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path, policy, now = self.fixture(root, 'shein-daily-report', 25)
                data = dict(policy, **change) if isinstance(change, dict) else change
                path.write_text(json.dumps(data))
                self.assertEqual(m.report_health('ares/shein-daily-cron.py', now, root=root, policy_root=root/'policies')[0], 'ERROR')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, _, now = self.fixture(root, 'shein-daily-report', 25)
            self.assertEqual(m.report_health('ares/shein-daily-cron.py', now, root=root, policy_root=root/'missing')[0], 'ERROR')

    def test_partial_receipt_stays_red_after_scope_extension(self):
        for directory, count in [('shein-daily-report', 25), ('shein-intraday-report', 26)]:
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _, _, now = self.fixture(root, directory, count)
                home = root/directory
                path = home/'last-cron-result.json'
                data = json.loads(path.read_text())
                if 'stdout' in data:
                    payload = json.loads(data['stdout'])
                    payload['accounts'] = 24
                    data['stdout'] = json.dumps(payload)
                else:
                    data['accounts'] = 24
                path.write_text(json.dumps(data))
                script = 'ares/'+directory.replace('-report', '-cron.py')
                self.assertEqual(m.report_health(script, now, root=root, policy_root=root/'policies')[0], 'ERROR')


if __name__ == '__main__':
    unittest.main()
