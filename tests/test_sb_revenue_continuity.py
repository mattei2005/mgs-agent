# pyright: reportMissingImports=false
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from typing import Any

BASE = Path('/root/mgs-agent')
sys.path.insert(0, str(BASE / 'scripts'))
import mgs_sb_revenue_continuity as adapter
import mgs_automation_supervisor as supervisor
from mgs_automation_continuity import Queue


class RevenueContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'reports/automation-recovery' / adapter.KEY
        self.root.mkdir(parents=True)
        (self.base / 'data').mkdir()
        original = BASE / 'reports/automation-recovery' / adapter.KEY
        for name in ('checkpoint.json', 'expected-column.json'):
            (self.root / name).write_bytes((original / name).read_bytes())
        self.receipt = json.loads((self.root / 'checkpoint.json').read_text())
        self.state = self.receipt['canonical_state']
        self.save_state()
        expected = json.loads((self.root / 'expected-column.json').read_text())
        self.values: list[list[Any]] = [['RECEITA 3 DIAS']] + [[] for _ in range(expected['row_count'] - 1)]
        for row, value in expected['values'].items():
            self.values[int(row) - 1] = [float(value)]

    def save_state(self):
        (self.base / 'data/sb-messenger-revenue-sheet-sync-state.json').write_text(json.dumps(self.state))

    def save_receipt(self):
        (self.root / 'checkpoint.json').write_text(json.dumps(self.receipt))

    def observe(self):
        return adapter.observation(base=self.base, reader=lambda n: copy.deepcopy(self.values), now=200, queue_path=None)

    def test_exact_live_read_is_verified(self):
        result = self.observe()
        self.assertTrue(result['verified'])
        self.assertEqual(result['target'], 'alert:1572239665250181151')
        self.assertEqual(result['evidence']['written_rows'], 151)
        self.assertEqual(result['evidence']['written_total'], '69984.49')

    def test_live_drift_is_not_green(self):
        row = next(i for i in range(1, len(self.values)) if self.values[i])
        self.values[row][0] += 1
        self.assertFalse(self.observe()['verified'])

    def test_extra_nonempty_row_is_not_green(self):
        row = next(i for i in range(1, len(self.values)) if not self.values[i])
        self.values[row] = [0]
        self.assertFalse(self.observe()['verified'])

    def test_wrong_header_is_not_green(self):
        self.values[0] = ['RECEITA 7 DIAS']
        self.assertFalse(self.observe()['verified'])

    def test_later_period_cannot_certify_original(self):
        self.state['period_end'] = '2026-11-18'
        self.save_state()
        self.assertFalse(self.observe()['verified'])

    def test_changed_original_target_is_not_green(self):
        self.receipt['target']['column'] = 'D'
        self.save_receipt()
        self.assertFalse(self.observe()['verified'])

    def test_mutated_frozen_expected_is_not_green(self):
        p = self.root / 'expected-column.json'
        p.write_text(p.read_text() + '\n')
        self.assertFalse(self.observe()['verified'])

    def test_reader_failure_is_not_green(self):
        def fail(_):
            raise TimeoutError('fixture')
        self.assertFalse(adapter.observation(base=self.base, reader=fail, queue_path=None)['verified'])

    def test_no_receipt_has_no_effect(self):
        self.assertIsNone(adapter.observation(base=self.base / 'missing'))

    def test_closed_request_does_not_read_google_again(self):
        q = Queue(self.base / 'closed.sqlite3')
        self.addCleanup(q.close)
        row = q.enqueue(adapter.SOURCE_KEY, {'kind': 'alert'}, 'fixture', now=1794921732.0845373)
        self.assertEqual(row['key'], adapter.KEY)
        q.complete(row['key'], self.observe(), now=200)
        self.assertIsNone(adapter.observation(base=self.base, queue_path=q.path, reader=lambda n: self.fail('closed operation read Google')))

    def test_boolean_is_not_numeric_revenue(self):
        row = next(i for i in range(1, len(self.values)) if self.values[i])
        self.values[row] = [True]
        self.assertFalse(self.observe()['verified'])

    def test_scope_gate_is_not_cleared(self):
        q = Queue(self.base / 'fixture.sqlite3')
        self.addCleanup(q.close)
        row = q.enqueue(adapter.SOURCE_KEY, {'kind': 'alert', 'profile': 'zeus'}, 'fixture', now=100)
        q.defer(row['key'], 'blocked_decision', 'fixture_scope_gate', now=100)
        supervisor.drive(q, {adapter.SOURCE_KEY: self.observe()}, lambda *a: self.fail('business runner called'), lambda: False, lambda s: False, lambda *a: None, now=200)
        self.assertEqual(q.get(row['key'])['state'], 'blocked_decision')

    def test_independent_supervisor_closes_fixture_without_business_replay(self):
        q = Queue(self.base / 'fixture.sqlite3')
        self.addCleanup(q.close)
        row = q.enqueue(adapter.SOURCE_KEY, {'kind': 'alert', 'profile': 'zeus'}, 'fixture', now=100)
        notices = []
        supervisor.drive(q, {adapter.SOURCE_KEY: self.observe()}, lambda *a: self.fail('business runner called'), lambda: False, lambda s: False, lambda *a: notices.append(a), now=200)
        self.assertEqual(q.get(row['key'])['state'], 'completed_validated')
        self.assertEqual(len(notices), 1)


if __name__ == '__main__':
    unittest.main()
