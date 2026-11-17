import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mgs_autopush_continuity as target


class AutopushContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base / 'data').mkdir()
        self.receipt = {'operation_key': target.KEY, 'alert_id': target.ALERT,
                        'authority_message_id': '1569193434189668453',
                        'status': 'recovered_waiting_supervisor_validation',
                        'validated_artifact_hashes': {str(i): 'hash' for i in range(5)},
                        'recovery_not_before': 100}
        self.state = {'last_check': '1970-01-01T00:02:00Z',
                      'consecutive_failures': 0, 'last_failure_details': []}
        self.save()

    def save(self):
        (self.base / 'recovery-evidence.json').write_text(json.dumps(self.receipt))
        (self.base / 'data/auto-push-monitor.json').write_text(json.dumps(self.state))

    def observe(self, reader=None, db=None):
        return target.observation(self.base, self.base, db,
                                  reader or (lambda *args: {'live': True}), now=150)

    def test_exact_occurrence(self):
        result = self.observe()
        self.assertTrue(result['verified'])
        self.assertEqual(result['target'], target.SOURCE_KEY)

    def test_wrong_occurrence(self):
        self.receipt['alert_id'] = 'other'; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_uncertified_receipt(self):
        self.receipt['status'] = 'validated_waiting_native_batch'; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_historic_healthy_monitor_not_enough(self):
        self.receipt['recovery_not_before'] = 130; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_failure_remains_pending(self):
        self.state['consecutive_failures'] = 1; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_live_failure_remains_pending(self):
        def fail(*args):
            raise ValueError('Remote drift')
        self.assertFalse(self.observe(fail)['verified'])

    def test_concurrent_change_not_green(self):
        def mutate(*args):
            self.state['consecutive_failures'] = 1; self.save()
            return {'live': True}
        self.assertFalse(self.observe(mutate)['verified'])

    def test_closed_request_does_not_probe(self):
        path = self.base / 'queue.db'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE requests(key TEXT,source_key TEXT,state TEXT)')
            db.execute('INSERT INTO requests VALUES(?,?,?)', (target.KEY, target.SOURCE_KEY, 'completed_validated'))
        self.assertIsNone(self.observe(lambda *args: self.fail('closed probe'), path))

    def test_independent_closure_no_business_replay(self):
        from mgs_automation_continuity import Queue
        from mgs_automation_supervisor import drive
        q = Queue(self.base / 'queue.db'); self.addCleanup(q.close)
        row = q.enqueue(target.SOURCE_KEY, {'kind': 'alert'}, 'alert_unresolved', now=90)
        calls = []
        drive(q, {target.SOURCE_KEY: self.observe()}, lambda *args: self.fail('replay'),
              lambda: False, lambda source: False, lambda *args: calls.append(args), now=150, max_jobs=0)
        self.assertEqual(q.get(row['key'])['state'], 'completed_validated')
        self.assertEqual(len(calls), 1)

    def test_owner_blocks_closure(self):
        from mgs_automation_continuity import Queue
        from mgs_automation_supervisor import drive
        q = Queue(self.base / 'queue.db'); self.addCleanup(q.close)
        row = q.enqueue(target.SOURCE_KEY, {'kind': 'alert'}, 'alert_unresolved', now=90)
        drive(q, {target.SOURCE_KEY: self.observe()}, lambda *args: self.fail('replay'),
              lambda: False, lambda source: True, lambda *args: self.fail('notice'), now=150, max_jobs=0)
        self.assertNotEqual(q.get(row['key'])['state'], 'completed_validated')


if __name__ == '__main__':
    unittest.main()
