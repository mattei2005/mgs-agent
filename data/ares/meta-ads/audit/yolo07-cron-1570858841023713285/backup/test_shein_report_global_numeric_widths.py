"""Offline tests only: Rodolfo's global SHEIN numeric presentation approval."""
import copy
from datetime import datetime,timedelta
import unittest
from unittest.mock import patch
import test_shein_report_status_blocks as fixtures

layout=fixtures.layout

class GlobalNumericWidthsTests(unittest.TestCase):
    def model(self,b=None):
        m=fixtures.StatusBlocksTests().model(b)
        since=datetime.fromisoformat(layout.policy()['numeric_width_standard']['effective_from_financial_snapshot'])+timedelta(seconds=1)
        m['source_timestamps']={k:since.isoformat() for k in ('insights','sb','configuration','status')}
        m['rps_source']['observed_at']=since.isoformat()
        return m

    def test_36_bindings_global_minimum160_cells_model_history_totals_preserved(self):
        for b in fixtures.fixtures.All36BudgetUsedTests().bindings():
            with self.subTest(account=b['account_id']):
                m=self.model(b);before=copy.deepcopy(m)
                out=layout.render_model(m);layout.validate_report(m,out['text'],b['thread_id'])
                cfg=copy.deepcopy(layout.policy());cfg.pop('numeric_width_standard')
                profile=cfg['format_profiles']['SHEIN_ALL36_UNIFORM_G001_CAPS_V1']
                profile['column_widths'].update({'Gasto':6,'B.R.%':7,'Saldo':7});profile['line_visual_width']=160
                with patch.object(layout,'policy',return_value=cfg):old=layout.render_model(m)
                self.assertEqual(out['main_parts'],old['main_parts'])
                self.assertEqual(out['history_parts'],old['history_parts'])
                self.assertEqual(out['campaign_ids'],old['campaign_ids'])
                self.assertEqual(m,before)
                self.assertEqual(out['numeric_width_policy_id'],'ARES-SHEIN-ALL36-NUMERIC-WIDTHS-20261019')
                for p in out['main_parts']:
                    self.assertTrue(all(layout.visual_width(line)==160 for line in p.splitlines()[2:-1]))
                self.assertTrue(all(layout.discord_length(p)<=2000 for p in out['parts']))

    def test_bigger_numbers_grow_only_three_columns_keep_full_signs_and_decimals(self):
        m=self.model();r=m['rows'][0]
        r.update(spend='12345.67',net_revenue='20000.00',estimated_revenue='20000.00',daily_budget='50')
        r['roi']=str(layout.roi(r['net_revenue'],r['spend']));r['estimated_roi']=r['roi']
        r['history'][-1].update(spend=r['spend'],net_revenue=r['net_revenue'],roi=r['roi'])
        before=copy.deepcopy(m);out=layout.render_model(m)
        for cell in ('12345,67','24691,34%','+7654,33'):self.assertIn(cell,out['text'])
        self.assertEqual(set(out['width_expansions']),{'Gasto','B.U.%','Saldo'})
        self.assertEqual(m,before)
        positions={tuple(layout.bar_positions(line)) for p in out['main_parts'] for line in p.splitlines()[2:-1]}
        self.assertEqual(len(positions),1)
        layout.validate_report(m,out['text'])

    def test_prior_snapshot_unchanged_but_explicit_preserved_application_allowed(self):
        m=fixtures.StatusBlocksTests().model();self.assertIsNone(layout.render_model(m)['numeric_width_policy_id'])
        original=copy.deepcopy(m)
        m['numeric_width_policy_id']=layout.policy()['numeric_width_standard']['policy_id']
        m['source_timestamps']['presentation']=layout.policy()['numeric_width_standard']['effective_from_financial_snapshot']
        out=layout.render_model(m)
        self.assertIsNotNone(out['numeric_width_policy_id'])
        self.assertEqual(m['rows'],original['rows'])
        self.assertEqual(m['source_timestamps']['insights'],original['source_timestamps']['insights'])

    def test_bad_authority_column_binding_or_fake_application_rejected(self):
        for key,value in [('authorized_by_discord_id','321263240782807040'),('columns',['RPS']),('mode','truncate')]:
            cfg=copy.deepcopy(layout.policy());cfg['numeric_width_standard'][key]=value
            with self.subTest(key=key),patch.object(layout,'policy',return_value=cfg):
                with self.assertRaises(layout.LayoutError):layout.render_model(self.model())
        m=self.model();m['numeric_width_policy_id']='fake'
        with self.assertRaises(layout.LayoutError):layout.render_model(m)

    def test_unapproved_columns_still_fail_and_budget_formula_not_remaining(self):
        m=self.model();m['rows'][0]['rps']='12345678.90'
        with self.assertRaises(layout.LayoutError):layout.render_model(m)
        self.assertEqual(layout.budget_used_percent('108.86','100'),layout.number('108.86'))
        self.assertIsNone(layout.budget_used_percent('10',0))

if __name__=='__main__':unittest.main()
