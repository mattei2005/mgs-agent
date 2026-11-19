import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shein_single_clone as d

ACCOUNT = '1663268201836138'
TEST = '120251924617890087'

def profile():
    return {'account_id': ACCOUNT, 'channel_id': '1548150155184701440',
            'campaign_numbering_exclusions': {
                'account_id': ACCOUNT, 'source_channel_id': '1548150155184701440',
                'source_thread_id': '1570857869790945455', 'source_message_id': '1572787993763385456',
                'authorized_by': '1055570806945620030',
                'campaigns': [{'campaign_id': TEST, 'number': '888'}]}}

class NumberingExclusions(unittest.TestCase):
    def setUp(self):
        self.marker = d.CURRENT_PROFILE.set(profile())
        self.rows = [{'id': '120251924491990087', 'name': '050 - NORMAL', 'account_id': ACCOUNT},
                     {'id': TEST, 'name': '888 - TEST', 'account_id': ACCOUNT}]
    def tearDown(self):
        d.CURRENT_PROFILE.reset(self.marker)
    def test_exact_test_ignored_without_mutating_inventory(self):
        original = copy.deepcopy(self.rows)
        self.assertEqual(d.reconcile_number({}, self.rows, None, None), 51)
        self.assertEqual(self.rows, original)
        self.assertEqual(len(d.numbering_inventory(self.rows)), 1)
    def test_other_888_is_not_ignored(self):
        self.rows.append({'id': '120251924617890088', 'name': '888 - OTHER', 'account_id': ACCOUNT})
        self.assertEqual(d.reconcile_number({}, self.rows, None, None), 889)
    def test_other_real_high_number_retained(self):
        self.rows.append({'id': '120251924617890089', 'name': '060 - NORMAL', 'account_id': ACCOUNT})
        self.assertEqual(d.reconcile_number({}, self.rows, None, None), 61)
    def test_same_id_number_drift_rejected(self):
        self.rows[1]['name'] = '889 - CHANGED'
        with self.assertRaises(d.RouteBlocked): d.numbering_inventory(self.rows)
    def test_same_id_account_drift_rejected(self):
        self.rows[1]['account_id'] = '123456789'
        with self.assertRaises(d.RouteBlocked): d.numbering_inventory(self.rows)
    def test_no_policy_keeps_legacy_behavior(self):
        d.CURRENT_PROFILE.set({'account_id': ACCOUNT})
        self.assertEqual(d.reconcile_number({}, self.rows, None, None), 889)
    def test_policy_bound_to_exact_account_and_channel(self):
        for field in ['account_id', 'source_channel_id']:
            p = profile(); p['campaign_numbering_exclusions'][field] = '123456789'
            d.CURRENT_PROFILE.set(p)
            with self.assertRaises(d.RouteBlocked): d.numbering_inventory(self.rows)
    def test_authority_and_duplicate_validation(self):
        for key in ['authorized_by', 'source_message_id', 'source_thread_id']:
            p = profile(); p['campaign_numbering_exclusions'][key] = ''
            d.CURRENT_PROFILE.set(p)
            with self.assertRaises(d.RouteBlocked): d.numbering_inventory(self.rows)
        p = profile(); p['campaign_numbering_exclusions']['campaigns'] *= 2
        d.CURRENT_PROFILE.set(p)
        with self.assertRaises(d.RouteBlocked): d.numbering_inventory(self.rows)
    def test_no_cross_account_reference_change(self):
        d.CURRENT_PROFILE.set({})
        self.assertEqual(d.reconcile_number({'source_account': '123456'}, [], None, None), 1)
    def test_renamed_number_not_excluded_by_prefix_alone(self):
        self.rows[1]['id'] = '120251924617890090'
        self.assertEqual(d.reconcile_number({}, self.rows, None, None), 889)

if __name__ == '__main__': unittest.main()
