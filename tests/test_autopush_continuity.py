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


class IndexLockContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base / 'data').mkdir()
        self.receipt = {'operation_key': target.INDEX_KEY, 'alert_id': target.INDEX_ALERT,
                        'authority_message_id': '1569193434189668453',
                        'status': 'recovered_waiting_supervisor_validation',
                        'recovery_not_before': 100}
        self.state = {'last_check': '1970-01-01T00:02:00Z',
                      'consecutive_failures': 0, 'last_failure_details': []}
        self.save()

    def save(self):
        (self.base / 'recovery-evidence.json').write_text(json.dumps(self.receipt))
        (self.base / 'data/auto-push-monitor.json').write_text(json.dumps(self.state))

    def observe(self, reader=None, db=None):
        return target.index_lock_observation(self.base, self.base, db,
                                            reader or (lambda *args: {'live': True}), now=150)

    def test_exact_occurrence(self):
        self.assertTrue(self.observe()['verified'])
        self.assertEqual(self.observe()['target'], 'alert:' + target.INDEX_ALERT)

    def test_wrong_alert_not_green(self):
        self.receipt['alert_id'] = target.ALERT; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_partial_receipt_not_green(self):
        self.receipt['status'] = 'waiting_native_retry'; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_old_monitor_not_green(self):
        self.receipt['recovery_not_before'] = 130; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_failure_not_green(self):
        self.state['consecutive_failures'] = 1; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_readback_failure_not_green(self):
        def fail(*args):
            raise ValueError('GET failed')
        self.assertFalse(self.observe(fail)['verified'])

    def test_concurrent_mutation_not_green(self):
        def mutate(*args):
            self.state['consecutive_failures'] = 1; self.save()
            return {'live': True}
        self.assertFalse(self.observe(mutate)['verified'])

    def test_closed_does_not_probe(self):
        path = self.base / 'queue.db'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE requests(key TEXT,source_key TEXT,state TEXT)')
            db.execute('INSERT INTO requests VALUES(?,?,?)', (target.INDEX_KEY, 'alert:' + target.INDEX_ALERT, 'completed_validated'))
        self.assertIsNone(self.observe(lambda *args: self.fail('closed probe'), path))

    def test_owner_and_decision_gates_preserved(self):
        from mgs_automation_continuity import Queue
        from mgs_automation_supervisor import drive
        q = Queue(self.base / 'queue.db'); self.addCleanup(q.close)
        row = q.enqueue('alert:' + target.INDEX_ALERT, {'kind': 'alert'}, 'alert_unresolved', now=90)
        def drive_once(active=False):
            drive(q, {row['source_key']: self.observe()}, lambda *args: self.fail('replay'),
                  lambda: False, lambda source: active, lambda *args: None, now=150, max_jobs=0)
        drive_once(True)
        self.assertNotEqual(q.get(row['key'])['state'], 'completed_validated')
        q.defer(row['key'], 'blocked_decision', 'decision', now=150)
        drive_once()
        self.assertEqual(q.get(row['key'])['state'], 'blocked_decision')

    def test_independent_closure_without_replay(self):
        from mgs_automation_continuity import Queue
        from mgs_automation_supervisor import drive
        q = Queue(self.base / 'queue.db'); self.addCleanup(q.close)
        row = q.enqueue('alert:' + target.INDEX_ALERT, {'kind': 'alert'}, 'alert_unresolved', now=90)
        drive(q, {row['source_key']: self.observe()}, lambda *args: self.fail('replay'),
              lambda: False, lambda source: False, lambda *args: None, now=150, max_jobs=0)
        self.assertEqual(q.get(row['key'])['state'], 'completed_validated')


class RepeatedIndexLockContinuityTests(IndexLockContinuityTests):
    def observe(self, reader=None, db=None):
        key = '5372f4df6089c7f3c6810be5'
        alert = '1573981654010036305'
        # Reuse all failure/owner fixtures without treating an older receipt as
        # proof of the new occurrence. Only the fixture's original identity moves.
        receipt = dict(self.receipt)
        if receipt['operation_key'] == target.INDEX_KEY:
            receipt['operation_key'] = key
        if receipt['alert_id'] == target.INDEX_ALERT:
            receipt['alert_id'] = alert
        (self.base / 'recovery-evidence.json').write_text(json.dumps(receipt))
        return target.index_lock_observation(
            self.base, self.base, db, reader or (lambda *args: {'live': True}),
            now=150, key=key, alert=alert)

    def test_exact_occurrence(self):
        result = self.observe()
        self.assertTrue(result['verified'])
        self.assertEqual(result['target'], 'alert:1573981654010036305')

    def test_closed_does_not_probe(self):
        path = self.base / 'queue.db'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE requests(key TEXT,source_key TEXT,state TEXT)')
            db.execute('INSERT INTO requests VALUES(?,?,?)', (
                '5372f4df6089c7f3c6810be5', 'alert:1573981654010036305', 'completed_validated'))
        self.assertIsNone(self.observe(lambda *args: self.fail('closed probe'), path))

    def test_prior_receipt_cannot_certify_new_occurrence(self):
        result = target.index_lock_observation(
            self.base, self.base, None, lambda *args: self.fail('old receipt probe'),
            now=150, key='5372f4df6089c7f3c6810be5', alert='1573981654010036305')
        self.assertFalse(result['verified'])

    def test_unregistered_pair_not_probed(self):
        self.assertIsNone(target.index_lock_observation(
            self.base, self.base, None, lambda *args: self.fail('unregistered probe'),
            now=150, key='5372f4df6089c7f3c6810be5', alert=target.INDEX_ALERT))

    def test_independent_closure_without_replay(self):
        from mgs_automation_continuity import Queue
        from mgs_automation_supervisor import drive
        q = Queue(self.base / 'queue.db'); self.addCleanup(q.close)
        row = q.enqueue('alert:1573981654010036305', {'kind': 'alert'}, 'alert_unresolved', now=90)
        drive(q, {row['source_key']: self.observe()}, lambda *args: self.fail('replay'),
              lambda: False, lambda source: False, lambda *args: None, now=150, max_jobs=0)
        self.assertEqual(q.get(row['key'])['state'], 'completed_validated')

    def test_owner_and_decision_gates_preserved(self):
        from mgs_automation_continuity import Queue
        from mgs_automation_supervisor import drive
        q = Queue(self.base / 'queue.db'); self.addCleanup(q.close)
        row = q.enqueue('alert:1573981654010036305', {'kind': 'alert'}, 'alert_unresolved', now=90)
        def check(active):
            drive(q, {row['source_key']: self.observe()}, lambda *args: self.fail('replay'),
                  lambda: False, lambda source: active, lambda *args: None, now=150, max_jobs=0)
        check(True)
        self.assertNotEqual(q.get(row['key'])['state'], 'completed_validated')
        q.defer(row['key'], 'blocked_decision', 'decision', now=150)
        check(False)
        self.assertEqual(q.get(row['key'])['state'], 'blocked_decision')

    def test_live_read_uses_exact_new_alert(self):
        from unittest.mock import patch
        commit = 'a' * 40
        (self.base / 'logs').mkdir()
        (self.base / 'logs/auto-commit-watcher.log').write_text(
            "Unable to create '/root/mgs-agent/.git/index.lock': File exists.\n"
            f'[main {commit[:10]}]\n')
        (self.base / 'logs/auto-push.log').write_text(
            f'[1970-01-01T00:02:00+00:00] auto-push OK commit={commit[:10]} branch=main\n')
        source = {'id': '1573981654010036305', 'author': {'id': '1496296175014252634'},
                  'content': '', 'timestamp': '1970-01-01T00:01:30Z', 'embeds': [{
                      'title': 'Auto-push falhando', 'color': 15158332, 'fields': [{
                          'name': 'Último erro',
                          'value': 'auto-commit falhou [commit/push não iniciou; consultar auto-commit-watcher.log]'}]}]}
        notice = {'id': 'notice', 'author': {'id': '1496296175014252634'},
                  'content': '', 'timestamp': '1970-01-01T00:02:10Z', 'embeds': [{
                      'title': 'Auto-push restabelecido', 'color': 3066993, 'fields': [{
                          'name': 'Último commit OK', 'value': commit[:10]}]}]}
        receipt = dict(self.receipt, alert_id=source['id'], native_retry_commit=commit,
                       recovery_notice_id='notice')
        with patch.object(target.subprocess, 'check_output', side_effect=[b'active', commit.encode()]), \
             patch.object(target.subprocess, 'run'), \
             patch('mgs_alert_transport.request', side_effect=[source, notice]) as get:
            result = target.index_lock_live_check(self.base, receipt)
        self.assertEqual(result['native_retry_commit'], commit)
        self.assertTrue(get.call_args_list[0].args[1].endswith('/1573981654010036305'))
        source['id'] = target.INDEX_ALERT
        with patch.object(target.subprocess, 'check_output', side_effect=[b'active', commit.encode()]), \
             patch.object(target.subprocess, 'run'), \
             patch('mgs_alert_transport.request', return_value=source):
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                target.index_lock_live_check(self.base, receipt)


if __name__ == '__main__':
    unittest.main()
