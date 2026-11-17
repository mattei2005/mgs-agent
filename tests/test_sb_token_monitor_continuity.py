import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mgs_sb_token_monitor_continuity as target


class TokenMonitorContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'reports/automation-recovery' / target.KEY
        self.root.mkdir(parents=True)
        (self.base / 'data').mkdir()
        (self.base / 'scripts').mkdir()
        self.script = self.base / 'scripts/monitor-sb-messenger-token-invalid.py'
        self.script.write_text('# fixture\n')
        self.receipt = {'operation_key': target.KEY, 'alert_id': target.ALERT,
                        'authority_message_ids': ['1569193434189668453', '1545180305961386055'],
                        'status': 'business_recovered_waiting_supervisor_closure',
                        'initial_pending': None, 'apply_exit': 0, 'apply_mode': 'noop',
                        'preserved_cursor': 755062, 'natural_tick_not_before': 1794951720,
                        'canonical_script_sha256': hashlib.sha256(self.script.read_bytes()).hexdigest()}
        self.state = {'last_check': '2026-11-17T16:42:10-05:00', 'last_seen_id': 755062,
                      'consecutive_failures': 0, 'last_error': None, 'pending': None}
        self.live = {'ok': True, 'mode': 'noop', 'new_alerts': 0,
                     'last_seen_id': 755062, 'alerts_seen': 577}
        self.save()

    def save(self):
        (self.root / 'checkpoint.json').write_text(json.dumps(self.receipt))
        (self.base / 'data/sb-messenger-token-invalid-monitor.json').write_text(json.dumps(self.state))

    def observe(self, reader=None, queue_path=None):
        return target.observation(self.base, reader or (lambda base: self.live),
                                  now=1794951900, queue_path=queue_path)

    def test_exact_fresh_occurrence(self):
        r = self.observe()
        self.assertTrue(r['verified'])
        self.assertEqual(r['target'], target.SOURCE_KEY)
        self.assertFalse(r['evidence']['new_business_delivery_required'])

    def test_other_occurrence_not_green(self):
        self.receipt['alert_id'] = 'other'; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_prior_manual_success_not_natural_tick(self):
        self.state['last_check'] = '2026-11-17T16:38:01-05:00'; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_subsequent_failure_not_green(self):
        self.state['consecutive_failures'] = 1; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_pending_not_green(self):
        self.state['pending'] = {'message_ids': ['accepted']}; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_later_cursor_not_this_noop(self):
        self.state['last_seen_id'] += 1; self.save()
        self.assertFalse(self.observe()['verified'])

    def test_probe_failure_keeps_pending(self):
        def fail(base):
            raise TimeoutError()
        self.assertFalse(self.observe(fail)['verified'])

    def test_new_live_notification_not_green(self):
        self.live['new_alerts'] = 1
        self.assertFalse(self.observe()['verified'])

    def test_changed_consumer_not_green(self):
        self.script.write_text('# changed\n')
        self.assertFalse(self.observe()['verified'])

    def test_closed_queue_does_not_probe(self):
        dbpath = self.base / 'queue.sqlite3'
        with sqlite3.connect(dbpath) as db:
            db.execute('CREATE TABLE requests(key TEXT,source_key TEXT,state TEXT)')
            db.execute('INSERT INTO requests VALUES(?,?,?)', (target.KEY,target.SOURCE_KEY,'completed_validated'))
        def fail(base):
            self.fail('closed request probed')
        self.assertIsNone(self.observe(fail, queue_path=dbpath))

    def test_concurrent_state_mutation_not_green(self):
        def mutate(base):
            self.state['last_seen_id'] += 1; self.save()
            return self.live
        self.assertFalse(self.observe(mutate)['verified'])

    def test_live_probe_uses_only_canonical_dry_run(self):
        with patch.object(target.subprocess, 'run') as run:
            run.return_value = target.subprocess.CompletedProcess([], 0, json.dumps(self.live), '')
            self.assertEqual(target.probe(self.base), self.live)
            args = run.call_args.args[0]
            self.assertEqual(args[-1], '--dry-run')
            self.assertNotIn('--apply', args)
            self.assertEqual(args[:3], ['flock', '-n', '/var/lock/monitor_sb_messenger_token_invalid.lock'])

    def test_supervisor_closes_exact_alert_without_business_replay(self):
        from mgs_automation_continuity import Queue
        from mgs_automation_supervisor import drive
        q = Queue(self.base / 'isolated.sqlite3')
        self.addCleanup(q.close)
        row = q.enqueue(target.SOURCE_KEY, {'kind':'alert','profile':'zeus'}, 'alert_unresolved', now=1794951000)
        calls = []
        drive(q, {target.SOURCE_KEY:self.observe()}, lambda *args:self.fail('business replay'),
              lambda:False, lambda source:False, lambda *args:calls.append(args),
              now=1794951900, max_jobs=1)
        self.assertEqual(q.get(row['key'])['state'], 'completed_validated')
        self.assertEqual(len(calls), 1)

    def test_active_owner_prevents_supervisor_completion(self):
        from mgs_automation_continuity import Queue
        from mgs_automation_supervisor import drive
        q = Queue(self.base / 'isolated.sqlite3')
        self.addCleanup(q.close)
        row = q.enqueue(target.SOURCE_KEY, {'kind':'alert','profile':'zeus'}, 'alert_unresolved', now=1794951000)
        drive(q, {target.SOURCE_KEY:self.observe()}, lambda *args:self.fail('business replay'),
              lambda:False, lambda source:True, lambda *args:self.fail('premature notice'),
              now=1794951900, max_jobs=0)
        self.assertNotEqual(q.get(row['key'])['state'], 'completed_validated')

    def test_decision_gate_not_overridden_by_green_probe(self):
        from mgs_automation_continuity import Queue
        from mgs_automation_supervisor import drive
        q = Queue(self.base / 'isolated.sqlite3')
        self.addCleanup(q.close)
        row = q.enqueue(target.SOURCE_KEY, {'kind':'alert','profile':'zeus'}, 'alert_unresolved', now=1794951000)
        q.defer(row['key'], 'blocked_decision', 'scope_changed', now=1794951100)
        drive(q, {target.SOURCE_KEY:self.observe()}, lambda *args:self.fail('business replay'),
              lambda:False, lambda source:False, lambda *args:self.fail('premature notice'),
              now=1794951900, max_jobs=0)
        self.assertEqual(q.get(row['key'])['state'], 'blocked_decision')


if __name__ == '__main__':
    unittest.main()
