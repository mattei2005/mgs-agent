"""Offline regression for the account-scoped SHEIN single-clone adapter."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3 import shein_single_clone as route

ACCOUNT = '7840111366055613'
PAGE = '1187478564456307'


def fixture():
    request = {'request_id': 'unit-single-01', 'account': 'Yolokfx-US-SHEIN-EN-01-G002',
               'source_number': 110, 'budget_usd': '30', 'start_time': '2030-10-08T00:00:00-04:00',
               'status': 'PAUSED', 'authorized_by': '344196393512075265',
               'source_thread_id': '1557274000680288307'}
    source = {'campaign': {'id': '11001', 'account_id': ACCOUNT,
                          'name': '110 - TURBO BLOWER [LP NORMAL] 07/10 - US-EN (b01fb01c110) event_add_to_wishlist',
                          'daily_budget': '4000', 'bid_strategy': 'LOWEST_COST_WITHOUT_CAP', 'objective': 'OUTCOME_SALES'},
              'adset': {'id': '11002', 'name': '01 - ADGROUP - VIDEOS (b01fb01c110g01)',
                        'optimization_goal': 'OFFSITE_CONVERSIONS', 'billing_event': 'IMPRESSIONS',
                        'is_dynamic_creative': False, 'attribution_spec': [{'event_type': 'CLICK_THROUGH', 'window_days': 7}],
                        'promoted_object': {'pixel_id': '1049581090103163', 'custom_event_type': 'ADD_TO_WISHLIST'},
                        'targeting': {'age_min': 18, 'age_max': 65, 'age_range': [18, 65],
                                      'user_age_unknown': True, 'geo_locations': {'countries': ['US']},
                                      'targeting_automation': {'advantage_audience': 1, 'individual_setting': {'age': 1, 'gender': 1}}}},
              'ads': [{'id': '11003', 'name': 'AD - 1', 'adset_id': '11002', 'status': 'ACTIVE',
                       'creative': {'id': '11004', 'effective_object_story_id': PAGE + '_123',
                                    'object_story_spec': {'page_id': PAGE, 'video_data': {'video_id': '11005',
                                        'message': 'FREE TURBO BLOWER', 'call_to_action': {'type': 'GET_OFFER_VIEW', 'value': {
                                            'link': 'https://yolokfx.com/quiz/us/sh2-g002/?utm_source=facebook&utm_medium=g002-s&utm_campaign=b01fb01c110&utm_adgroup=b01fb01c110g01'}}}}}}]}
    cfg = {'alias': request['account'], 'app_key': 'mgs-meta-app-1299247318762949', 'operation': 'SHEIN-US-DIRECT',
           'timezone': 'America/New_York', 'supported_modes': ['pure_clone'], 'token_user_id': '122095869861482193'}
    return request, source, cfg


def live_fixture(manifest, source):
    c = manifest['campaigns'][0]
    adset = copy.deepcopy(source['adset'])
    adset.update(id='target-set', name=c['adset_name'], status='PAUSED', start_time=c['start_time'])
    return {'campaign': {'id': 'target-campaign', 'account_id': ACCOUNT, 'name': c['name'], 'status': 'PAUSED',
                         'effective_status': 'PAUSED', 'start_time': c['start_time'], **c['campaign_updates']},
            'adsets': {'data': [adset]},
            'ads': {'data': [{'id': 'target-ad', 'adset_id': 'target-set', 'name': c['ads'][0]['name'], 'status': 'PAUSED',
                              'source_ad_id': c['ads'][0]['source_ad_id'], 'creative': {
                                  'object_story_id': c['ads'][0]['creative_payload']['object_story_id'],
                                  'effective_object_story_id': c['ads'][0]['creative_payload']['object_story_id'],
                                  'url_tags': c['ads'][0]['creative_payload']['url_tags']}}]}}


class SingleCloneTests(unittest.TestCase):
    def test_budget_exact_cents(self):
        self.assertEqual(route.budget_minor('30'), 3000)
        self.assertEqual(route.budget_minor('30.01'), 3001)
        for value in ['30.001', '-1', '0', 'nan', 'inf']:
            with self.assertRaises(ValueError): route.budget_minor(value)

    def test_one_mode_correct_account_names_and_tracking(self):
        r, s, cfg = fixture()
        p = route.build_manifest(r, s, 114, cfg)
        c = p['campaigns'][0]
        self.assertEqual(c['account_id'], ACCOUNT)
        self.assertEqual(c['name'], '114 - TURBO BLOWER [LP NORMAL] - US-EN (b01fb01c114) 08/10 event_add_to_wishlist COPY C110')
        self.assertNotIn('adset_updates', c)
        self.assertNotIn('media', c['ads'][0])
        self.assertEqual(c['status'], 'PAUSED')
        self.assertEqual(c['campaign_updates']['daily_budget'], '3000')
        self.assertIn('utm_medium=g002-s', c['ads'][0]['creative_payload']['url_tags'])
        self.assertIn('utm_campaign=b01fb01c114', c['ads'][0]['creative_payload']['url_tags'])
        self.assertNotIn('c110', c['ads'][0]['creative_payload']['url_tags'])
        self.assertEqual(c['ads'][0]['source_ad_id'], s['ads'][0]['id'])
        self.assertEqual(c['ads'][0]['creative_payload']['object_story_id'], PAGE + '_123')

    def test_source_date_after_token(self):
        r, s, cfg = fixture()
        s['campaign']['name'] = '110 - HAIRBRUSH audio new [LP NORMAL] - US-EN (b01fb01c110) 22/09 event_add_to_wishlist'
        name = route.build_manifest(r, s, 114, cfg)['campaigns'][0]['name']
        self.assertIn('(b01fb01c114) 08/10', name)
        self.assertNotIn('22/09', name)

    def test_copied_source_replaces_previous_lineage_marker(self):
        r, s, cfg = fixture()
        s['campaign']['name'] += ' COPY C108'
        name = route.build_manifest(r, s, 114, cfg)['campaigns'][0]['name']
        self.assertTrue(name.endswith('COPY C110'))
        self.assertEqual(name.count('COPY C'), 1)

    def test_request_scope_and_authority_fail_closed(self):
        for key, value in [('account', 'other-account'), ('status', 'ACTIVE'), ('authorized_by', 'other-user'),
                           ('request_id', '../escape'), ('start_time', '2030-10-08T00:00:00')]:
            r, s, cfg = fixture(); r[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): route.build_manifest(r, s, 114, cfg)

    def test_wrong_event_account_tracking_and_destination_rejected(self):
        for change in ['event', 'account', 'url', 'tracking', 'post']:
            r, s, cfg = fixture()
            if change == 'event': s['adset']['promoted_object']['custom_event_type'] = 'PURCHASE'
            if change == 'account': s['campaign']['account_id'] = 'wrong'
            if change == 'url': s['ads'][0]['creative']['object_story_spec']['video_data']['call_to_action']['value']['link'] = 'https://example.test/'
            if change == 'tracking': s['campaign']['name'] = s['campaign']['name'].replace('b01fb01c110', 'b01fb03c110')
            if change == 'post': s['ads'][0]['creative']['effective_object_story_id'] = 'another-page_123'
            with self.subTest(change=change), self.assertRaises(ValueError): route.build_manifest(r, s, 114, cfg)

    def test_readback_exact(self):
        r, s, cfg = fixture(); p = route.build_manifest(r, s, 114, cfg)
        self.assertEqual(route.verify_readback(p, s, live_fixture(p, s)), [])

    def test_known_optional_flag_difference_is_reported_not_written(self):
        r, s, cfg = fixture(); p = route.build_manifest(r, s, 114, cfg); live = live_fixture(p, s)
        live['adsets']['data'][0]['targeting']['targeting_automation'].pop('individual_setting')
        self.assertEqual(len(route.verify_readback(p, s, live)), 1)
        self.assertTrue(live['adsets']['data'][0]['targeting']['user_age_unknown'])

    def test_other_readback_drift_fails(self):
        for change in ['budget', 'status', 'schedule', 'audience', 'post', 'lineage', 'tags', 'count', 'issues']:
            r, s, cfg = fixture(); p = route.build_manifest(r, s, 114, cfg); live = live_fixture(p, s)
            if change == 'budget': live['campaign']['daily_budget'] = '4500'
            if change == 'status': live['campaign']['status'] = 'ACTIVE'
            if change == 'schedule': live['adsets']['data'][0]['start_time'] = '2030-10-08T00:10:00-04:00'
            if change == 'audience': live['adsets']['data'][0]['targeting']['age_min'] = 25
            if change == 'post': live['ads']['data'][0]['creative']['effective_object_story_id'] = PAGE + '_456'
            if change == 'lineage': live['ads']['data'][0]['source_ad_id'] = 'wrong'
            if change == 'tags': live['ads']['data'][0]['creative']['url_tags'] = 'utm_campaign=old'
            if change == 'count': live['ads']['data'].append(copy.deepcopy(live['ads']['data'][0]))
            if change == 'issues': live['ads']['data'][0]['issues_info'] = [{'error': 'test'}]
            with self.subTest(change=change), self.assertRaises(ValueError): route.verify_readback(p, s, live)

    def test_social_uses_page_identity_once_and_never_corporate_post_query(self):
        common = Mock()
        common.graph_get.return_value = (200, {'id': PAGE, 'name': 'Page', 'access_token': 'OFFLINE_PAGE_TOKEN'}, {})
        common.graph_batch_get.return_value = (200, [{'name': 'post-1', 'code': 200, 'body': {
            'id': PAGE + '_123', 'reactions': {'summary': {'total_count': 2}}, 'comments': {'summary': {'total_count': 0}}}}], {})
        out = route.read_social(common, 'OFFLINE_CORPORATE_TOKEN', PAGE, [PAGE + '_123', PAGE + '_123'])
        self.assertEqual(common.graph_get.call_count, 1)
        self.assertEqual(common.graph_batch_get.call_args.args[0], 'OFFLINE_PAGE_TOKEN')
        self.assertIsNone(out[0]['shares'])
        self.assertNotIn('OFFLINE_PAGE_TOKEN', json.dumps(out))

    def test_social_reuses_memory_token_and_rejects_mixed_pages(self):
        common = Mock(); common.graph_batch_get.return_value = (200, [{'name': 'post-1', 'code': 200, 'body': {'id': PAGE + '_123'}}], {})
        route.read_social(common, 'CORPORATE', PAGE, [PAGE + '_123'], page_token='PAGE_TOKEN')
        common.graph_get.assert_not_called()
        with self.assertRaises(ValueError): route.read_social(common, 'CORPORATE', PAGE, ['other_123'])


if __name__ == '__main__':
    unittest.main()
