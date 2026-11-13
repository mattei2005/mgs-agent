"""Offline fixtures only: SHEIN active/paused status blocks, no API or publishing."""
import copy
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch
import test_shein_report_budget_used_all36 as fixtures

layout = fixtures.layout


class StatusBlocksTests(unittest.TestCase):
    def model(self, binding=None):
        helper = fixtures.All36BudgetUsedTests()
        binding = binding or helper.bindings()[0]
        m = helper.model_for(binding)
        since = datetime.fromisoformat(layout.policy()['campaign_status_blocks']['effective_from_financial_snapshot']) + timedelta(seconds=1)
        m['source_timestamps'] = {k: since.isoformat() for k in ('insights', 'sb', 'configuration', 'status')}
        m['rps_source']['observed_at'] = since.isoformat()
        base = m['rows'][0]
        m['rows'] = []
        for i, status in enumerate(('PAUSED', 'ACTIVE', 'ARCHIVED', 'ACTIVE', 'DELETED')):
            r = copy.deepcopy(base)
            r.update(id=str(990000 + i), name=f'{i+1:03d} - offline unit fixture', number=f'{i+1:03d}', campaign_status=status, campaign_effective_status='PAUSED' if status == 'ACTIVE' else 'ACTIVE')
            m['rows'].append(r)
        return m

    def cells(self, parts):
        result = {}
        for part in parts:
            lines = part.splitlines()
            headers = [v.strip() for v in lines[2].split('|')]
            for line in lines[3:-1]:
                cells = dict(zip(headers, (v.strip() for v in line.split('|'))))
                result[cells['Nº']] = cells
        return result

    def test_all36_separate_configured_status_keep_cells_totals_grid_and_model(self):
        for b in fixtures.All36BudgetUsedTests().bindings():
            with self.subTest(account=b['account_id']):
                m = self.model(b)
                before = copy.deepcopy(m)
                out = layout.render_model(m)
                layout.validate_report(m, out['text'], b['thread_id'])
                self.assertEqual(out['campaign_ids'], ['990001', '990003', '990000', '990002', '990004'])
                self.assertEqual(out['history_campaign_ids'], out['campaign_ids'])
                self.assertIn('Campanhas ativas (2)', out['main_parts'][0])
                self.assertIn('Campanhas pausadas (1)', out['main_parts'][1])
                self.assertIn('Campanhas arquivadas (1)', out['main_parts'][2])
                self.assertIn('Campanhas deletadas (1)', out['main_parts'][-1])
                oldcfg = copy.deepcopy(layout.policy()); oldcfg.pop('campaign_status_blocks')
                with patch.object(layout, 'policy', return_value=oldcfg):
                    old = layout.render_model(m)
                self.assertEqual(self.cells(out['main_parts']), self.cells(old['main_parts']))
                self.assertEqual(self.cells(out['history_parts']), self.cells(old['history_parts']))
                self.assertEqual(out['main_rows'], len(m['rows']))
                self.assertEqual(m, before)
                summary = lambda text: next(line for line in text.splitlines() if line.startswith('Gasto **'))
                self.assertEqual(summary(out['text']), summary(old['text']))
                positions = set()
                for part in out['main_parts']:
                    for line in part.splitlines()[2:-1]:
                        self.assertEqual(layout.visual_width(line), 157)
                        positions.add(tuple(layout.bar_positions(line)))
                self.assertEqual(len(positions), 1)

    def test_sort_stable_inside_blocks_not_global_roi_ranking(self):
        m = self.model()
        m['rows'] = m['rows'][:4]
        for row, revenue in zip(m['rows'], ('0.9', '0.2', '0.5', '0.8')):
            row['estimated_revenue'] = revenue
            row['estimated_roi'] = str(layout.roi(revenue, row['spend']))
        out = layout.render_model(m)
        self.assertEqual(out['campaign_ids'], ['990003', '990001', '990000', '990002'])
        self.assertEqual(out['history_campaign_ids'], ['990001', '990003', '990000', '990002'])

    def test_snapshot_before_cutoff_keeps_previous_render(self):
        m = self.model()
        since = datetime.fromisoformat(layout.policy()['campaign_status_blocks']['effective_from_financial_snapshot'])
        m['source_timestamps']['insights'] = (since - timedelta(seconds=1)).isoformat()
        self.assertIsNone(layout.render_model(m)['status_blocks_policy_id'])
        self.assertNotIn('Campanhas ativas', layout.render_model(m)['text'])

    def test_no_inferred_status_or_missing_timestamp(self):
        for missing in ('campaign_status', 'timestamp'):
            m = self.model()
            if missing == 'timestamp': m['source_timestamps'].pop('status')
            else: m['rows'][0].pop('campaign_status')
            with self.assertRaises(layout.LayoutError): layout.render_model(m)

    def test_empty_and_active_only_keep_both_headers_without_fictitious_rows(self):
        for count in (0, 1):
            m = self.model(); m['rows'] = [m['rows'][1]] if count else []
            out = layout.render_model(m)
            self.assertIn(f'Campanhas ativas ({count})', out['text'])
            self.assertIn('Campanhas pausadas (0)', out['text'])
            self.assertEqual(out['main_rows'], count)
            self.assertEqual(out['history_rows'], count)
            self.assertEqual(len(self.cells(out['main_parts'])), count)

    def test_long_blocks_exact_pagination_and_tamper_rejection(self):
        m = self.model(); base = copy.deepcopy(m['rows'][0]); m['rows'] = []
        for i in range(120):
            row = copy.deepcopy(base)
            row.update(id=str(980000+i), number=f'{i+1:03d}', name=f'{i+1:03d} - offline pagination fixture', campaign_status='ACTIVE' if i % 2 else 'PAUSED')
            m['rows'].append(row)
        out = layout.render_model(m)
        self.assertEqual(len(set(out['campaign_ids'])), 120)
        self.assertEqual(len(self.cells(out['main_parts'])), 120)
        self.assertEqual(len(self.cells(out['history_parts'])), 120)
        self.assertTrue(all(layout.discord_length(p) <= 2000 and p.count('```') % 2 == 0 for p in out['parts']))
        layout.validate_report(m, out['text'])
        with self.assertRaises(layout.LayoutError): layout.validate_report(m, out['text'].replace('Campanhas ativas', 'Misturadas', 1))


if __name__ == '__main__':
    unittest.main()
