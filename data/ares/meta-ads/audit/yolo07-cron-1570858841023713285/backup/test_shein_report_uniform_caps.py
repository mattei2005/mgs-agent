"""Offline unit fixtures: display-only ceilings and one fixed YOLO grid."""
import copy
import importlib.util
from decimal import Decimal
import unittest
from unittest.mock import patch
import test_shein_report_status_column as fixtures

spec = importlib.util.spec_from_file_location('uniform_caps_layout', '/root/.hermes/profiles/ares/scripts/shein-report-layout.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
PROFILE = 'YOLO_UNIFORM_G001_CAPS_V1'


class UniformCapsTests(unittest.TestCase):
    def model(self):
        m = fixtures.StatusColumnTests().model()
        m['explicit_sort_request']['format_profile_id'] = PROFILE
        return m

    def test_caps_signs_zero_negative_missing_and_grouping(self):
        for value, limit, suffix, expected in [('10500', '999.99', '%', '999,99%'), ('999.99', '999.99', '%', '999,99%'), ('103.58', '999.99', '%', '103,58%'), ('-100', '999.99', '%', '-100,00%'), ('0', '999.99', '%', '0,00%'), ('125', '9.99', 'x', '9,99x'), (None, '9.99', 'x', 'n/d')]:
            self.assertEqual(layout.capped_display(value, limit, suffix), expected)
        self.assertEqual(layout.capped_display('15000', '9999.99', grouped=True), '9.999,99')
        self.assertEqual(layout.capped_display('1234.56', '9999.99', grouped=True), '1.234,56')

    def test_fixed_columns_separators_157_and_model_preservation(self):
        m = self.model()
        before = copy.deepcopy(m)
        out = layout.render_model(m)
        positions = set()
        for part in out['main_parts']:
            for line in part.splitlines()[2:-1]:
                self.assertEqual(layout.visual_width(line), 157)
                self.assertEqual(line.count('|'), 16)
                positions.add(tuple(layout.bar_positions(line)))
        self.assertEqual(len(positions), 1)
        self.assertEqual(m, before)
        layout.validate_report(m, out['text'])
        self.assertIn('Tetos visuais', out['text'])

    def test_capping_does_not_change_raw_order_history_or_totals(self):
        m = self.model()
        for i, revenue in [(0, '1.06'), (1, '0.30')]:
            row = m['rows'][i]
            row['spend'] = '0.01'
            row['net_revenue'] = revenue
            row['estimated_revenue'] = revenue
            row['roi'] = str(layout.roi(revenue, '0.01'))
            row['estimated_roi'] = row['roi']
            row['roas'] = '125'
            row['history'][-1].update(spend='0.01', net_revenue=revenue, roi=row['roi'])
        before = copy.deepcopy(m)
        capped = layout.render_model(m)
        old_m = copy.deepcopy(m)
        old_m['explicit_sort_request'].pop('format_profile_id')
        normal = layout.render_model(old_m)
        self.assertEqual(capped['campaign_ids'], normal['campaign_ids'])
        self.assertEqual(capped['history_parts'], normal['history_parts'])
        self.assertEqual(m, before)
        self.assertIn('999,99%', capped['text'])
        self.assertIn('9,99x', capped['text'])
        self.assertEqual(Decimal(m['rows'][0]['roi']), Decimal('10500'))
        self.assertEqual(m['rows'][0]['roas'], '125')

    def test_overflow_fails_before_publish_no_implicit_widening(self):
        m = self.model()
        m['rows'][0]['rps'] = '12345678.90'
        with self.assertRaisesRegex(layout.LayoutError, 'exceeds the authorized fixed column width'):
            layout.render_model(m)

    def test_profile_identity_and_configuration_guard(self):
        m = self.model()
        m['explicit_sort_request']['format_profile_id'] = 'unknown_profile'
        with self.assertRaises(layout.LayoutError):
            layout.render_model(m)
        m = self.model()
        cfg = layout.policy()
        cfg['format_profiles'][PROFILE]['line_visual_width'] = 158
        with patch.object(layout, 'policy', return_value=cfg):
            with self.assertRaisesRegex(layout.LayoutError, 'grid width mismatch'):
                layout.render_model(m)

    def test_all_36_defaults_share_exact_same_profile(self):
        cfg = layout.policy()
        rules = cfg['account_report_overrides']
        self.assertEqual(len(rules), 36)
        ids = {rule['options']['format_profile_id'] for rule in rules.values()}
        self.assertEqual(len(ids), 1)
        profile = cfg['format_profiles'][next(iter(ids))]
        self.assertEqual(set(profile['account_ids']), set(rules))
        self.assertEqual(profile['column_widths']['Nº'], 13)
        self.assertEqual(sum(profile['column_widths'].values()) + sum(map(len, profile['column_joiners'])), 157)

    def test_original_profile_without_override_unchanged(self):
        m = self.model()
        m['explicit_sort_request'].pop('format_profile_id')
        out = layout.render_model(m)
        self.assertNotIn('Tetos visuais nas linhas principais', out['text'])

    def test_exact_message_capacity_and_balanced_fences(self):
        out = layout.render_model(self.model())
        self.assertTrue(all(layout.discord_length(part) <= 2000 and part.count('```') % 2 == 0 for part in out['parts']))


if __name__ == '__main__':
    unittest.main()
