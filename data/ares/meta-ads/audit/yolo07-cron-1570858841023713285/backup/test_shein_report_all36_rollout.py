"""Offline coverage tests for the explicitly approved all-36 SHEIN rollout."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
import test_shein_report_status_column as fixtures

spec = importlib.util.spec_from_file_location('all36_layout', '/root/.hermes/profiles/ares/scripts/shein-report-layout.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
PROFILE = 'SHEIN_ALL36_UNIFORM_G001_CAPS_V1'
INDEX = Path('/root/mgs-agent/data/ares/discord/shein-intraday-report-bindings.json')


class All36RolloutTests(unittest.TestCase):
    def bindings(self):
        return json.loads(INDEX.read_text())['bindings']

    def model(self, binding, empty=False):
        m = fixtures.StatusColumnTests().model()
        m['account'].update(id='act_' + binding['account_id'], name=binding['account_name'])
        m['explicit_sort_request']['format_profile_id'] = PROFILE
        if empty:
            m['rows'] = []
        return m

    def test_exact_36_accounts_threads_six_managers_and_shared_profile(self):
        bindings = self.bindings()
        cfg = layout.policy()
        self.assertEqual(len(bindings), 36)
        self.assertEqual(len({b['account_id'] for b in bindings}), 36)
        self.assertEqual(len({b['thread_id'] for b in bindings}), 36)
        self.assertEqual(len({b['manager_code'] for b in bindings}), 6)
        self.assertEqual(set(cfg['account_report_overrides']), {b['account_id'] for b in bindings})
        self.assertEqual(set(cfg['format_profiles'][PROFILE]['account_ids']), {b['account_id'] for b in bindings})
        for b in bindings:
            rule = cfg['account_report_overrides'][b['account_id']]
            self.assertEqual(rule['account_name'], b['account_name'])
            self.assertEqual(rule['thread_id'], b['thread_id'])
            self.assertEqual(rule['options']['format_profile_id'], PROFILE)

    def test_same_grid_and_complete_identity_validation_all_36(self):
        positions = set()
        for b in self.bindings():
            m = self.model(b)
            out = layout.render_model(m)
            layout.validate_report(m, out['text'], b['thread_id'])
            for part in out['main_parts']:
                for line in part.splitlines()[2:-1]:
                    self.assertEqual(layout.visual_width(line), 157)
                    positions.add(tuple(layout.bar_positions(line)))
        self.assertEqual(len(positions), 1)

    def test_empty_accounts_keep_two_headers_and_no_invented_revenue(self):
        for b in self.bindings():
            m = self.model(b, empty=True)
            out = layout.render_model(m)
            self.assertEqual(out['main_rows'], 0)
            self.assertEqual(out['history_rows'], 0)
            self.assertIn('Sem campanhas com entrega', out['text'])
            self.assertIn('Rev **n/d**', out['text'])
            self.assertIn('Saldo **n/d**', out['text'])
            self.assertIn('Histórico ROI real', out['text'])
            layout.validate_report(m, out['text'], b['thread_id'])

    def test_api_or_local_rps_source_rejected_for_non_yolo(self):
        b = next(b for b in self.bindings() if not b['account_name'].startswith('Yolokfx'))
        for source in ['API', 'SB_FRONTEND_NATIVE', 'LOCAL_FORMULA']:
            m = self.model(b)
            m['rps_source']['source_kind'] = source
            with self.assertRaises(layout.LayoutError):
                layout.render_model(m)

    def test_report_cannot_be_delivered_to_another_bound_account(self):
        a, b = self.bindings()[:2]
        model = self.model(a)
        out = layout.render_model(model)
        with self.assertRaises(layout.LayoutError):
            layout.validate_report(model, out['text'], b['thread_id'])


if __name__ == '__main__':
    unittest.main()
