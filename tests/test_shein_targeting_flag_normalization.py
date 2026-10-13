"""Offline-only readback tests for preserved device suggestions.

Fixtures are synthetic; no network, credentials or campaign writes.
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_shein_single_clone_route import fixture, live_fixture
from ares_campaign_v3 import shein_single_clone as route


class TargetingFlagNormalizationTests(unittest.TestCase):
    def setup_case(self, source_flags, target_flags):
        request, source, config = fixture()
        source['adset']['targeting']['targeting_automation']['individual_setting'] = source_flags
        manifest = route.build_manifest(request, source, 114, config)
        live = live_fixture(manifest, source)
        automation = live['adsets']['data'][0]['targeting']['targeting_automation']
        if target_flags is None:
            automation.pop('individual_setting', None)
        else:
            automation['individual_setting'] = target_flags
        return manifest, source, live

    def test_device_preserved_age_gender_omitted_reports_warning_without_mutation(self):
        manifest, source, live = self.setup_case(
            {'age': 1, 'gender': 1, 'device': 1}, {'device': 1})
        before = copy.deepcopy((manifest, source, live))
        warnings = route.verify_readback(manifest, source, live)
        self.assertEqual(len(warnings), 1)
        self.assertIn('not literally identical', warnings[0])
        self.assertEqual((manifest, source, live), before)

    def test_original_known_omission_is_still_accepted(self):
        manifest, source, live = self.setup_case({'age': 1, 'gender': 1}, None)
        self.assertEqual(len(route.verify_readback(manifest, source, live)), 1)

    def test_unchanged_device_flags_need_no_warning(self):
        flags = {'age': 1, 'gender': 1, 'device': 1}
        manifest, source, live = self.setup_case(flags, flags.copy())
        self.assertEqual(route.verify_readback(manifest, source, live), [])

    def test_missing_or_changed_device_and_other_flag_changes_are_rejected(self):
        cases = [
            ({'age': 1, 'gender': 1, 'device': 1}, None),
            ({'age': 1, 'gender': 1, 'device': 1}, {'device': 0}),
            ({'age': 1, 'gender': 1, 'device': 1}, {'device': 1, 'age': 0}),
            ({'age': 1, 'gender': 1, 'device': 1}, {'device': 1, 'gender': 0}),
            ({'age': 0, 'gender': 1, 'device': 1}, {'device': 1}),
            ({'age': 1, 'gender': 1, 'other': 1}, {'other': 1}),
            ({'age': 1, 'gender': 1}, {'device': 1}),
        ]
        for source_flags, target_flags in cases:
            with self.subTest(source=source_flags, target=target_flags):
                manifest, source, live = self.setup_case(source_flags, target_flags)
                with self.assertRaisesRegex(route.RouteBlocked, 'targeting divergence'):
                    route.verify_readback(manifest, source, live)

    def test_other_targeting_drift_is_not_hidden_by_known_flag_omission(self):
        for field, value in [('age_min', 25), ('user_age_unknown', False),
                             ('geo_locations', {'countries': ['CA']})]:
            with self.subTest(field=field):
                manifest, source, live = self.setup_case(
                    {'age': 1, 'gender': 1, 'device': 1}, {'device': 1})
                live['adsets']['data'][0]['targeting'][field] = value
                with self.assertRaisesRegex(route.RouteBlocked, 'targeting divergence'):
                    route.verify_readback(manifest, source, live)

    def test_budget_cap_schedule_and_children_guards_are_not_bypassed(self):
        for change in ['budget', 'cap', 'schedule', 'empty_sets', 'empty_ads']:
            with self.subTest(change=change):
                manifest, source, live = self.setup_case(
                    {'age': 1, 'gender': 1, 'device': 1}, {'device': 1})
                if change == 'budget': live['campaign']['daily_budget'] = '1'
                if change == 'cap':
                    manifest['campaigns'][0]['bid_override'] = True
                    manifest['campaigns'][0]['adset_updates'] = {'bid_amount': '75', 'bid_constraints': {}}
                    live['adsets']['data'][0]['bid_amount'] = 76
                if change == 'schedule': live['adsets']['data'][0]['start_time'] = '2030-10-08T00:10:00-04:00'
                if change == 'empty_sets': live['adsets']['data'] = []
                if change == 'empty_ads': live['ads']['data'] = []
                with self.assertRaises(route.RouteBlocked):
                    route.verify_readback(manifest, source, live)


if __name__ == '__main__':
    unittest.main()
