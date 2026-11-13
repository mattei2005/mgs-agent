"""Offline unit fixtures: prospective global Budget Used across exact 36 bindings."""
import copy
import json
from datetime import datetime, timedelta, date
from pathlib import Path
import unittest
from unittest.mock import patch
import test_shein_report_uniform_caps as fixtures

layout = fixtures.layout
ROOT = Path('/root/mgs-agent')


class All36BudgetUsedTests(unittest.TestCase):
    def bindings(self):
        b = json.loads((ROOT / 'data/ares/discord/shein-intraday-report-bindings.json').read_text())['bindings']
        return list(b.values()) if isinstance(b, dict) else b

    def model_for(self, binding):
        # Explicitly offline test-only adaptation of the established real fixture.
        m = fixtures.UniformCapsTests().model()
        m.pop('explicit_sort_request', None)
        cfg = layout.policy()
        after = datetime.fromisoformat(cfg['budget_used_standard']['effective_from_financial_snapshot']) + timedelta(seconds=1)
        target = after.date()
        m['account'].update(id='act_' + binding['account_id'], name=binding['account_name'], currency='USD')
        m['date'] = target.isoformat()
        m['history_dates'] = [(target - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        m['source_timestamps'] = {k: after.isoformat() for k in ('insights', 'sb', 'configuration', 'status')}
        m['rps_source'].update(data_date=m['date'], observed_at=after.isoformat())
        for row in m['rows']:
            for item, dt in zip(row['history'], m['history_dates']):
                item['date'] = dt
                item['partial'] = dt == m['date']
        return m

    def cell_maps(self, result):
        headers = [x.strip() for x in result['main_parts'][0].splitlines()[2].split('|')]
        return [dict(zip(headers, [x.strip() for x in line.split('|')])) for part in result['main_parts'] for line in part.splitlines()[3:-1]]

    def test_all36_render_validate_only_budget_cells_change(self):
        bindings = self.bindings()
        self.assertEqual(len(bindings), 36)
        self.assertEqual(len({b['account_id'] for b in bindings}), 36)
        self.assertEqual(len({b['thread_id'] for b in bindings}), 36)
        for binding in bindings:
            with self.subTest(account=binding['account_id']):
                model = self.model_for(binding)
                before = copy.deepcopy(model)
                current = layout.render_model(model)
                layout.validate_report(model, current['text'], thread_id=binding['thread_id'])
                oldcfg = copy.deepcopy(layout.policy())
                oldcfg.pop('account_budget_display_overrides', None)
                with patch.object(layout, 'policy', return_value=oldcfg):
                    old = layout.render_model(model)
                self.assertEqual(current['campaign_ids'], old['campaign_ids'])
                self.assertEqual(current['history_parts'], old['history_parts'])
                self.assertEqual(model, before)
                self.assertIn('B.U.%', current['main_parts'][0])
                self.assertNotIn('B.R.%', current['text'])
                for newrow, oldrow in zip(self.cell_maps(current), self.cell_maps(old)):
                    newrow.pop('B.U.%'); oldrow.pop('B.R.%')
                    self.assertEqual(newrow, oldrow)
                for part in current['main_parts']:
                    for line in part.splitlines()[2:-1]:
                        self.assertEqual(layout.visual_width(line), 157)

    def test_prospective_cutoff_keeps_old_account_semantics(self):
        cfg = layout.policy()
        for binding in self.bindings():
            model = self.model_for(binding)
            self.assertTrue(layout.account_budget_used(model, cfg))
            since = datetime.fromisoformat(cfg['budget_used_standard']['effective_from_financial_snapshot'])
            model['source_timestamps']['insights'] = (since - timedelta(seconds=1)).isoformat()
            self.assertEqual(layout.account_budget_used(model, cfg), binding['account_id'] == '7840111366055613')

    def test_exact_coverage_policy_authority_and_no_side_effects(self):
        cfg = layout.policy()
        bindings = self.bindings()
        rules = cfg['account_budget_display_overrides']
        self.assertEqual(set(rules), {b['account_id'] for b in bindings})
        for b in bindings:
            r = rules[b['account_id']]
            self.assertEqual(r['authorized_by_discord_id'], '344196393512075265')
            self.assertEqual(r['source_thread_id'], b['thread_id'])
            self.assertEqual(r['account_name'], b['account_name'])
            self.assertEqual(r['display_header'], 'B.U.%')
            self.assertEqual(r['metric'], 'daily_spend_over_daily_budget_percent')
        self.assertTrue(cfg['budget_used_standard']['no_Meta_write'])
        self.assertTrue(cfg['budget_used_standard']['no_schedule_change'])
        self.assertTrue(cfg['budget_used_standard']['no_republication'])


if __name__ == '__main__':
    unittest.main()
