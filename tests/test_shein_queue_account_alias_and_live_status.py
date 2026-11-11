"""Scheduling-only regression: no provider calls or campaign writes."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shein_manual_takeover as manual
from ares_campaign_v3 import shein_source_media as media
from ares_campaign_v3 import shein_request_queue as queue


class SchedulingIdentityTests(unittest.TestCase):
    def setUp(self):
        self.baseline = [{'id': 'C', 'status': 'ACTIVE', 'effective_status': 'ACTIVE',
            'daily_budget': '3500', 'bid_strategy': 'COST_CAP', 'start_time': 'T',
            'adsets': [{'id': 'S', 'status': 'ACTIVE', 'effective_status': 'ACTIVE', 'bid_amount': 90}],
            'ads': [{'id': 'A', 'adset_id': 'S', 'creative_id': 'CR', 'status': 'ACTIVE',
                'effective_status': 'ACTIVE', 'issue_codes': [], 'ad_review_feedback': None,
                'primary_media': [['identity', 'HASH']]}]}]

    def test_external_pause_and_review_do_not_change_scheduling_identity(self):
        live = copy.deepcopy(self.baseline)
        live[0].update(status='PAUSED', effective_status='PAUSED')
        live[0]['adsets'][0]['effective_status'] = 'CAMPAIGN_PAUSED'
        live[0]['ads'][0].update(status='PAUSED', effective_status='WITH_ISSUES', issue_codes=[2490468])
        self.assertEqual(manual.scheduling_identity(live), manual.scheduling_identity(self.baseline))
        self.assertEqual(self.baseline[0]['status'], 'ACTIVE')
        self.assertEqual(live[0]['ads'][0]['issue_codes'], [2490468])

    def test_configuration_identity_and_media_remain_strict(self):
        for field, value in [('daily_budget', '9999'), ('bid_strategy', 'OTHER'), ('id', 'OTHER'), ('start_time', 'OTHER')]:
            with self.subTest(field=field):
                live = copy.deepcopy(self.baseline); live[0][field] = value
                self.assertNotEqual(manual.scheduling_identity(live), manual.scheduling_identity(self.baseline))
        for field, value in [('id', 'OTHER'), ('adset_id', 'OTHER'), ('creative_id', 'OTHER'), ('primary_media', [['identity', 'OTHER']])]:
            with self.subTest(field=field):
                live = copy.deepcopy(self.baseline); live[0]['ads'][0][field] = value
                self.assertNotEqual(manual.scheduling_identity(live), manual.scheduling_identity(self.baseline))

    def test_deleted_archived_or_missing_status_rejected(self):
        for value in ['DELETED', 'ARCHIVED', None]:
            for kind in ['campaign', 'adset', 'ad']:
                with self.subTest(value=value, kind=kind):
                    live = copy.deepcopy(self.baseline)
                    target = live[0] if kind == 'campaign' else live[0]['adsets' if kind == 'adset' else 'ads'][0]
                    target['status'] = value
                    with self.assertRaises(ValueError): manual.scheduling_identity(live)

    def test_alias_dependency_resolution_does_not_mutate_input(self):
        request = {'request_id': 'REQUEST', 'account': 'EXACT-CATALOGUE-ALIAS'}
        with patch('ares_campaign_v3.shein_single_clone.lookup_account', return_value={'account_id': '123'}), patch.object(queue, 'state', return_value={'phase': 'COMPLETE', 'summary': {'campaigns': [{'campaign_id': 'C'}]}}):
            self.assertEqual(queue.dependencies(request, '123'), [])
        self.assertEqual(request['account'], 'EXACT-CATALOGUE-ALIAS')

    def test_wrong_alias_binding_rejected(self):
        with patch('ares_campaign_v3.shein_single_clone.lookup_account', return_value={'account_id': '456'}):
            with self.assertRaises(ValueError): queue.dependencies({'request_id': 'R', 'account': 'ALIAS'}, '123')

    def test_resume_alias_identity_exact(self):
        left = {'account': 'ALIAS', 'quantity': 7, 'mode': 'pure_clone'}
        right = {**left, 'account': '123'}
        with patch('ares_campaign_v3.shein_single_clone.lookup_account', return_value={'account_id': '123'}):
            self.assertTrue(media.same_resume_request(Path('.'), left, right))
        with patch('ares_campaign_v3.shein_single_clone.lookup_account', side_effect=[{'account_id': '456'}, {'account_id': '123'}]):
            self.assertFalse(media.same_resume_request(Path('.'), left, right))


if __name__ == '__main__':
    unittest.main()
