"""Offline tests of the authorized, scheduled SHEIN name-only replacement."""
import copy
import importlib.util
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'scripts/ares-shein-name-replacement-20261015.py'
spec = importlib.util.spec_from_file_location('rename', PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class FakeCommon:
    def __init__(self, name='007 - PRODUCT - US-EN (tracking)'):
        self.campaign = {'id': '7', 'account_id': '123', 'name': name, 'status': 'ACTIVE',
                         'daily_budget': '3000', 'bid_strategy': 'COST_CAP',
                         'start_time': '2030-01-01T00:00:00-04:00',
                         'adsets': {'data': [{'id': '8', 'name': 'set', 'status': 'ACTIVE',
                                             'ads': {'data': [{'id': '9', 'name': 'ad',
                                                              'status': 'ACTIVE', 'creative': {'id': '10'}}]}}]}}
        self.writes = []
        self.events = []
        self.fail_after_apply = False

    def graph_get(self, path, token, params):
        self.events.append('GET')
        return 200, copy.deepcopy(self.campaign), {}

    def graph_post_once(self, path, token, params):
        self.events.append('POST')
        self.writes.append((path, copy.deepcopy(params)))
        self.campaign['name'] = params['name']
        if self.fail_after_apply:
            raise TimeoutError('simulated response loss')
        return 200, {'success': True}, {}


class RenameTests(unittest.TestCase):
    def target(self, common):
        return {'id': '7', 'account_id': '123', 'discovery_name': common.campaign['name']}

    def run_one(self, common, target):
        with patch.object(runner, 'save'):
            runner.reconcile_one(common, 'NOT_A_CREDENTIAL', target, {'targets': [target]})

    def test_literal_replacement_preserves_full_name(self):
        name = '007 - 15/10 - v2 - PRODUCT - COCAP - (tracking) - COPY C5 - US-EN - event_add_to_wishlist'
        self.assertEqual(runner.desired_name(name), name.replace('US-EN', '(US_APP)'))
        self.assertEqual(runner.desired_name('us-en US–EN US_EN'), 'us-en US–EN US_EN')

    def test_exact_eighteen_account_scope(self):
        accounts = runner.scope()
        self.assertEqual(len(accounts), 18)
        self.assertEqual({a['name'].split('-')[0] for a in accounts}, runner.BRANDS)
        self.assertFalse(any('Yolokfx' in a['name'] for a in accounts))

    def test_no_early_execution(self):
        with self.assertRaisesRegex(ValueError, 'too_early'):
            runner.timing_guard(runner.AT - timedelta(seconds=1))
        runner.timing_guard(runner.AT)

    def test_late_start_blocked(self):
        with self.assertRaisesRegex(ValueError, 'late_start'):
            runner.timing_guard(runner.AT + timedelta(minutes=31))

    def test_only_name_payload_and_children_unchanged(self):
        common = FakeCommon()
        before = copy.deepcopy(common.campaign)
        target = self.target(common)
        self.run_one(common, target)
        self.assertEqual(common.writes, [('7', {'name': runner.desired_name(before['name'])})])
        self.assertEqual(target['state'], 'VERIFIED')
        self.assertEqual(runner.invariant(target['before']), runner.invariant(target['after']))
        self.assertEqual(common.campaign['adsets'], before['adsets'])
        self.assertEqual(common.events, ['GET', 'POST', 'GET'])

    def test_response_loss_reconciles_success_without_second_write(self):
        common = FakeCommon()
        common.fail_after_apply = True
        target = self.target(common)
        self.run_one(common, target)
        self.run_one(common, target)
        self.assertEqual(len(common.writes), 1)
        self.assertEqual(target['state'], 'VERIFIED')

    def test_external_name_drift_is_not_overwritten(self):
        common = FakeCommon()
        target = self.target(common)
        common.campaign['name'] += ' external edit'
        with self.assertRaisesRegex(ValueError, 'external_drift'):
            self.run_one(common, target)
        self.assertFalse(common.writes)

    def test_external_budget_drift_blocks_recovery(self):
        common = FakeCommon()
        target = self.target(common)
        with patch.object(runner, 'save'):
            target['before'] = runner.snapshot(common, '', '7')
        target['desired_name'] = runner.desired_name(target['before']['name'])
        common.campaign['daily_budget'] = '9999'
        with self.assertRaisesRegex(ValueError, 'invariant_drift'):
            self.run_one(common, target)
        self.assertFalse(common.writes)

    def test_terminal_campaign_never_written(self):
        for status in ['ARCHIVED', 'DELETED']:
            common = FakeCommon()
            common.campaign['status'] = status
            target = self.target(common)
            self.run_one(common, target)
            self.assertEqual(target['state'], 'SKIPPED_TERMINAL')
            self.assertFalse(common.writes)

    def test_child_pagination_fails_closed(self):
        common = FakeCommon()
        common.campaign['adsets']['paging'] = {'next': 'not a credential'}
        with self.assertRaisesRegex(ValueError, 'child_pagination'):
            self.run_one(common, self.target(common))
        self.assertFalse(common.writes)


if __name__ == '__main__':
    unittest.main()
