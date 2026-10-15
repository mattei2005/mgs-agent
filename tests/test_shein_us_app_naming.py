"""Offline prospective US-SHEIN marker, source parsing and policy coverage."""
import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ares_campaign_v3.shein_naming import campaign_name, product_label
from ares_campaign_v3 import shein_general
from test_shein_general_runtime import case

POLICY = {'enabled': True, 'route_regex': r'^/quiz/us/sh([123])-g[0-9]{3}/$',
          'layout_version_map': {'1': 'v1', '2': 'v2', '3': 'v3'}}


class UsAppNamingTests(unittest.TestCase):
    def name(self, source=None, bid='LOWEST_COST_WITHOUT_CAP'):
        return campaign_name(7, '2030-10-15T00:00:00-04:00', 'America/New_York',
                             'https://example.invalid/quiz/us/sh2-g002/', 'PRODUCT',
                             bid, 'b01fb02c007', POLICY, copy_source_number=source)

    def test_copy_marker_position_exact(self):
        self.assertEqual(self.name(6), '007 - 15/10 - v2 - PRODUCT - MAXVOL - '
                         '(b01fb02c007) - COPY C6 - (US_APP) - event_add_to_wishlist')

    def test_no_copy_marker_position_exact(self):
        self.assertEqual(self.name(), '007 - 15/10 - v2 - PRODUCT - MAXVOL - '
                         '(b01fb02c007) - (US_APP) - event_add_to_wishlist')

    def test_all_bids(self):
        for strategy, alias in [('LOWEST_COST_WITHOUT_CAP', 'MAXVOL'),
                                ('COST_CAP', 'COCAP'), ('LOWEST_COST_WITH_BID_CAP', 'BIDCAP')]:
            with self.subTest(strategy=strategy):
                name = self.name(6, strategy)
                self.assertIn(' - ' + alias + ' - (b01fb02c007)', name)
                self.assertEqual(name.count('(US_APP)'), 1)

    def test_new_and_old_sources_parse_without_marker_in_product(self):
        for source in [None, 6]:
            name = self.name(source)
            self.assertEqual(product_label(name), 'PRODUCT')
            self.assertEqual(product_label(name.replace(' - (US_APP)', '')), 'PRODUCT')

    def test_all_modes_compile_marker_without_mutating_source_or_tracking(self):
        for mode in ['pure_clone', 'clone_prestaged', 'from_zero_prestaged']:
            with self.subTest(mode=mode):
                request, source, account, _ = case(1, mode=mode)
                account['shein_naming'] = copy.deepcopy(POLICY)
                original = copy.deepcopy(source)
                result = shein_general.build(request, source, 7, account)
                name = result['campaigns'][0]['name']
                expected = (' - COPY C110' if mode != 'from_zero_prestaged' else '')
                self.assertTrue(name.endswith(expected + ' - (US_APP) - event_add_to_wishlist'))
                self.assertEqual(name.count('(US_APP)'), 1)
                self.assertEqual(source, original)
                for ad in result['campaigns'][0]['ads']:
                    self.assertNotIn('US_APP', json.dumps({k: v for k, v in ad.items() if k != 'name'}))

    def test_already_marked_source_is_not_duplicated(self):
        request, source, account, _ = case(1)
        account['shein_naming'] = copy.deepcopy(POLICY)
        source['campaign']['name'] = ('110 - 07/10 - v2 - PRODUCT - MAXVOL - '
                                      '(b01fb02c110) - COPY C67 - (US_APP) - event_add_to_wishlist')
        original = copy.deepcopy(source)
        name = shein_general.build(request, source, 120, account)['campaigns'][0]['name']
        self.assertEqual(name, '120 - 08/10 - v2 - PRODUCT - MAXVOL - '
                         '(b01fb02c120) - COPY C110 - (US_APP) - event_add_to_wishlist')
        self.assertEqual(source, original)

    def test_current_us_shein_policies_accept_new_and_sealed_legacy_names(self):
        config = json.loads((ROOT / 'data/ares/meta-ads/engine-v3/config.json').read_text())
        accounts = [a for a in config['accounts'].values() if a.get('operation') == 'SHEIN-US-DIRECT']
        self.assertTrue(accounts)
        for account in accounts:
            with self.subTest(account=account['shein_profile']['account_id']):
                self.assertIn('-US-SHEIN-', account['shein_profile']['account_name'].upper())
                self.assertIs(account['shein_naming']['enabled'], True)
                pattern = account['campaign_policy']['name_regex']
                for source in [None, 6]:
                    name = self.name(source)
                    self.assertIsNotNone(re.fullmatch(pattern, name))
                    self.assertIsNotNone(re.fullmatch(pattern, name.replace(' - (US_APP)', '')))
                self.assertIsNone(re.fullmatch(pattern, self.name(6).replace('COPY C6 - (US_APP)', '(US_APP) - COPY C6')))
                self.assertIsNone(re.fullmatch(pattern, self.name().replace('(US_APP)', '(US_APP) - (US_APP)')))

    def test_canonical_rule_is_prospective(self):
        operation = json.loads((ROOT / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
        policy = operation['campaign_naming_policy']
        self.assertEqual(policy['us_app_marker']['literal'], '(US_APP)')
        self.assertIs(policy['us_app_marker']['prospective_only'], True)
        self.assertIs(policy['us_app_marker']['sealed_manifests_unchanged'], True)
        self.assertIs(policy['existing_campaigns_rename_authorized'], False)


if __name__ == '__main__':
    unittest.main()
