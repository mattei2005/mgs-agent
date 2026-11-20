"""Exact incident verification and supervisor closure without business replay."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mgs_autopush_rollback_continuity as mod


class RollbackObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        (self.base / 'data').mkdir()
        self.state = {'last_check': '2026-11-20T20:06:00Z', 'consecutive_failures': 0, 'last_failure_details': []}
        self.receipt = {'operation_key': mod.KEY, 'alert_id': mod.ALERT,
                        'authority_message_id': '1569193434189668453',
                        'status': 'recovered_waiting_supervisor_validation',
                        'recovery_not_before': 1795205000,
                        'validated_artifact_hashes': {p: 'fixture' for p in mod.ARTIFACTS}}
        self.now = 1795205200
        self.save()

    def save(self):
        (self.base / 'data/auto-push-monitor.json').write_text(json.dumps(self.state))
        (self.base / 'recovery-evidence.json').write_text(json.dumps(self.receipt))

    def observe(self, reader=None):
        return mod.observation(base=self.base, root=self.base, queue_path=None,
                               now=self.now, reader=reader or (lambda b, r: {'GET': True}))

    def test_exact_occurrence_verified(self):
        self.assertTrue(self.observe()['verified'])
        self.assertEqual(self.observe()['target'], 'alert:' + mod.ALERT)

    def test_wrong_scope_and_incomplete_artifacts(self):
        for key, value in [('operation_key', 'other'), ('alert_id', 'other'),
                           ('authority_message_id', 'other'), ('validated_artifact_hashes', {})]:
            with self.subTest(key=key):
                old = self.receipt[key]
                self.receipt[key] = value
                self.save()
                self.assertFalse(self.observe()['verified'])
                self.receipt[key] = old

    def test_stale_failed_future_monitor(self):
        for stamp, failures in [('2026-11-20T19:56:01Z', 0), ('2026-11-20T20:06:00Z', 1), ('2026-11-21T20:06:00Z', 0)]:
            self.state.update(last_check=stamp, consecutive_failures=failures)
            self.save()
            self.assertFalse(self.observe()['verified'])

    def test_get_failure_and_concurrent_monitor(self):
        def failed(b, r):
            raise ValueError('GET unavailable')
        self.assertFalse(self.observe(failed)['verified'])
        def mutate(b, r):
            self.state['consecutive_failures'] = 1
            self.save()
            return {}
        self.assertFalse(self.observe(mutate)['verified'])

    def test_queue_scope_terminal_and_decision_gates(self):
        import sqlite3
        dbpath = self.base / 'queue.sqlite3'
        with sqlite3.connect(dbpath) as db:
            db.execute('CREATE TABLE requests (key TEXT, source_key TEXT, state TEXT)')
            db.execute('INSERT INTO requests VALUES (?,?,?)', (mod.KEY, 'alert:' + mod.ALERT, 'verifying'))
        for state in ['completed_validated', 'cancelled_owner', 'blocked_decision']:
            with sqlite3.connect(dbpath) as db:
                db.execute('UPDATE requests SET state=?', (state,))
            self.assertIsNone(mod.observation(base=self.base, root=self.base, queue_path=dbpath))

    def test_supervisor_closes_exact_key_without_runner(self):
        from mgs_automation_continuity import Queue
        from mgs_automation_supervisor import drive
        q = Queue(self.base / 'isolated.sqlite3')
        self.addCleanup(q.db.close)
        source = {'kind': 'alert', 'profile': 'zeus', 'alert_id': mod.ALERT}
        row = q.enqueue('alert:' + mod.ALERT, source, 'alert_unresolved', now=self.now - 1)
        called = []
        def no_runner(*args):
            self.fail('Business replay forbidden')
        drive(q, {'alert:' + mod.ALERT: self.observe()}, no_runner, lambda: False,
              lambda s: False, lambda r, t: called.append(r['key']), now=self.now, max_jobs=0)
        self.assertEqual(q.get(row['key'])['state'], 'completed_validated')
        self.assertEqual(called, [row['key']])


if __name__ == '__main__':
    unittest.main()
