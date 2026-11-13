"""Offline tests for prospectively saved YOLO account reporting defaults."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_shein_report_rps_budget_percent as fixtures

spec = importlib.util.spec_from_file_location('yolo_default_layout', '/root/.hermes/profiles/ares/scripts/shein-report-layout.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


class YoloDefaultTests(unittest.TestCase):
    def fixture(self):
        model = fixtures.RpsBudgetTests().model()
        model.pop('explicit_sort_request')
        cfg = layout.policy()
        aid = model['account']['id'].removeprefix('act_')
        cfg['account_report_overrides'][aid]['effective_from_financial_snapshot'] = '1900-01-01T00:00:00+00:00'
        return model, cfg

    def test_future_model_uses_saved_settings_without_request_flags(self):
        model, cfg = self.fixture()
        before = copy.deepcopy(model)
        with patch.object(layout, 'policy', return_value=cfg):
            result = layout.render_model(model)
            layout.validate_report(model, result['text'])
        self.assertEqual(model, before)
        self.assertIn('Padrão salvo nesta conta: ROI E. do maior para o menor', result['text'])
        header = [v.strip() for v in result['main_parts'][0].splitlines()[2].split('|')]
        self.assertEqual(header[5:7], ['RPS', 'Bid'])
        self.assertEqual(header[8], 'B.R.%')
        self.assertEqual(result['history_campaign_ids'], [r['id'] for r in sorted(model['rows'], key=lambda r: (int(r['number']), r['id']))])
        expected = sorted(model['rows'], key=lambda r: (layout.number(r['estimated_roi']) is None, -layout.number(r['estimated_roi']) if layout.number(r['estimated_roi']) is not None else 0, r['first_delivery'] or '9999-12-31', int(r['number']), r['id']))
        self.assertEqual(result['campaign_ids'], [r['id'] for r in expected])

    def test_future_without_visible_rps_cannot_publish(self):
        model, cfg = self.fixture()
        model.pop('rps_source')
        with patch.object(layout, 'policy', return_value=cfg):
            with self.assertRaisesRegex(layout.LayoutError, 'visible SB dashboard RPS provenance'):
                layout.render_model(model)

    def test_old_snapshot_not_retroactively_changed(self):
        model, cfg = self.fixture()
        cfg['account_report_overrides'][model['account']['id'].removeprefix('act_')]['effective_from_financial_snapshot'] = '2999-01-01T00:00:00+00:00'
        model.pop('rps_source')
        with patch.object(layout, 'policy', return_value=cfg):
            result = layout.render_model(model)
        self.assertNotIn('RPS', result['main_parts'][0].splitlines()[2])
        self.assertEqual(len(result['main_parts'][0].splitlines()[2].split('|')), 15)

    def test_unrelated_account_stays_global(self):
        model, cfg = self.fixture()
        model['account'].update(id='act_999999', name='Unit-only other account')
        model.pop('rps_source')
        with patch.object(layout, 'policy', return_value=cfg):
            result = layout.render_model(model)
        self.assertNotIn('RPS', result['main_parts'][0].splitlines()[2])
        self.assertEqual(len(result['main_parts'][0].splitlines()[2].split('|')), 15)

    def test_explicit_sort_delta_preserves_saved_required_columns(self):
        model, cfg = self.fixture()
        model['explicit_sort_request'] = {'mode': 'estimated_roi_asc', 'authorized_by_discord_id': '344196393512075265', 'source_thread_id': '1561752465978818722', 'request_text': 'ranking crescente neste pedido'}
        options = layout.effective_report_options(model, cfg)
        self.assertEqual(options['mode'], 'estimated_roi_asc')
        self.assertTrue(options['include_rps'])
        self.assertEqual(options['history_sort'], 'campaign_number_asc')

    def test_live_contract_includes_six_yolo_and_all_36_bindings(self):
        cfg = layout.policy()
        index = json.loads(Path('/root/mgs-agent/data/ares/discord/shein-intraday-report-bindings.json').read_text())
        bindings = [b for b in index['bindings'] if b['account_name'].startswith('Yolokfx')]
        self.assertEqual(set(cfg['account_report_overrides']), {b['account_id'] for b in index['bindings']})
        self.assertEqual(len(index['bindings']), 36)
        self.assertEqual(len(bindings), 6)
        for b in bindings:
            rule = cfg['account_report_overrides'][b['account_id']]
            self.assertEqual(rule['account_name'], b['account_name'])
            self.assertEqual(rule['thread_id'], b['thread_id'])
            self.assertTrue(rule['options']['include_rps'])
            self.assertEqual(rule['options']['mode'], 'estimated_roi_desc')


if __name__ == '__main__':
    unittest.main()
