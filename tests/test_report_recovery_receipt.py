"""Exact-period observer regression; all business journals are isolated fixtures."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

spec = importlib.util.spec_from_file_location('recovery_health', Path(__file__).resolve().parents[1] / 'scripts/mgs_report_scheduler_health.py')
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
report_health = module.report_health


class DailyRecoveryTests(unittest.TestCase):
    def fixture(self, root):
        self.now = datetime(2026, 11, 11, 14, 0, tzinfo=timezone.utc).timestamp()
        self.stamp = '2026-11-11T08:48:30-05:00'
        home = root / 'shein-daily-report'
        self.day = home / '2026-11-10'
        self.day.mkdir(parents=True)
        self.wrapper = home / 'last-cron-result.json'
        self.save(self.wrapper, {'returncode': 1, 'at': '2026-11-11T08:12:27-05:00', 'stderr': 'original failure'})
        bindings, deliveries = [], []
        for i in range(24):
            aid, tid, mid = str(1000+i), str(2000+i), str(3000+i)
            bindings.append({'account_id': aid, 'thread_id': tid})
            account = self.day / aid
            account.mkdir()
            text = 'Frozen report '+aid
            self.save(account / 'report.parts.json', [text])
            (account / 'report.md').write_text(text)
            self.save(account / 'delivery-intent-0.json', {'message_id': mid, 'thread_id': tid, 'part': 0, 'status': 'GET_VERIFIED', 'sha256': hashlib.sha256(text.encode()).hexdigest()})
            delivery = {'account_id': aid, 'thread_id': tid, 'status': 'COMPLETE_GET_VERIFIED', 'parts': [{'id': mid, 'part': 0, 'verified': True}]}
            self.save(account / 'delivery.json', delivery)
            deliveries.append(delivery)
        self.save(self.day / 'request.json', {'date': '2026-11-10', 'bindings': bindings})
        self.completion = {'date': '2026-11-10', 'status': 'COMPLETE_GET_VERIFIED', 'accounts': 24, 'published_parts': 24, 'completed_at': self.stamp, 'deliveries': deliveries}
        self.save(self.day / 'completion.json', self.completion)

    @staticmethod
    def save(path, data):
        path.write_text(json.dumps(data))

    def observe(self, root, now=None, log_mtime=0):
        return report_health('ares/shein-daily-cron.py', self.now if now is None else now, log_mtime, root=root)

    def test_recovered_exact_period_preserves_failed_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            before = self.wrapper.read_bytes()
            self.assertEqual(self.observe(root)[0], 'OK')
            self.assertEqual(before, self.wrapper.read_bytes())
            self.assertEqual(self.observe(root, self.now+37*3600)[0], 'STALE')
            self.assertIsNone(self.observe(root, log_mtime=(self.day/'completion.json').stat().st_mtime+60))

    def test_invalid_completion_never_certifies_recovery(self):
        changes = [
            {'date': '2026-11-09'}, {'accounts': 23}, {'published_parts': 25},
            {'status': 'PARTIAL'}, {'deliveries': []},
            {'completed_at': '2026-11-11T08:00:00-05:00'},
            {'completed_at': '2026-11-12T08:00:00-05:00'},
            {'completed_at': '2026-11-11T08:48:30'},
        ]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.fixture(root)
                data = copy.deepcopy(self.completion)
                data.update(change)
                self.save(self.day/'completion.json', data)
                self.assertEqual(self.observe(root)[0], 'ERROR')

    def test_other_period_cannot_clear_new_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            self.save(self.wrapper, {'returncode': 1, 'at': '2026-11-12T08:12:27-05:00'})
            self.assertEqual(self.observe(root, self.now+86400)[0], 'ERROR')

    def test_journal_mismatches_fail_closed(self):
        cases = [
            ('delivery-intent-0.json', 'status', 'POST_RETURNED'),
            ('delivery-intent-0.json', 'sha256', 'bad'),
            ('delivery-intent-0.json', 'message_id', '9999'),
            ('delivery-intent-0.json', 'thread_id', '9999'),
            ('delivery.json', 'status', 'PARTIAL'),
            ('report.parts.json', None, ['Changed report']),
        ]
        for filename, key, value in cases:
            with self.subTest(file=filename, key=key), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.fixture(root)
                path = self.day/'1000'/filename
                data = json.loads(path.read_text())
                if key is None:
                    data = value
                else:
                    data[key] = value
                self.save(path, data)
                self.assertEqual(self.observe(root)[0], 'ERROR')

    def test_utc_boundary_uses_new_york_delivery_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            self.save(self.wrapper, {'returncode': 1, 'at': '2026-11-12T00:12:27+00:00'})
            data = copy.deepcopy(self.completion)
            data['completed_at'] = '2026-11-12T00:48:30+00:00'
            self.save(self.day/'completion.json', data)
            self.assertEqual(self.observe(root, datetime(2026, 11, 12, 1, tzinfo=timezone.utc).timestamp())[0], 'OK')


if __name__ == '__main__':
    unittest.main()
