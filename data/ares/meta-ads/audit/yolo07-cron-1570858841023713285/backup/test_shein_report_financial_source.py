"""Offline regressions for authorized SB financial-source cutover; no API calls."""
import copy,importlib.util,json,sys,unittest
from pathlib import Path
from decimal import Decimal as D
HOME=Path('/root/.hermes/profiles/ares');sys.path.insert(0,str(HOME/'scripts'))
import shein_financial_source as finance
spec=importlib.util.spec_from_file_location('finance_layout',HOME/'scripts/shein-report-layout.py');layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)
BASE=Path('/root/mgs-agent/data/ares/meta-ads/audit/on-demand-intraday-1570794782773612555')
class FinancialTests(unittest.TestCase):
 def fixture(self):
  m=json.loads((BASE/'2323706575049143/model.json').read_text());sb=json.loads((BASE/'2323706575049143/sb.json').read_text())
  for k in ['insights','sb','configuration','budget','status']:m['source_timestamps'][k]='2026-11-13T10:00:00-05:00'
  m['rps_source']['observed_at']='2026-11-13T10:00:00-05:00'
  return m,sb,layout.policy()
 def adjusted(self):
  m,sb,cfg=self.fixture();finance.apply_financial_source(m,sb,cfg);return m,sb,cfg
 def test_same_source_per_campaign(self):
  m,sb,cfg=self.adjusted();self.assertTrue(finance.validate_financial_source(m,cfg))
  for r in m['rows']:
   rs=[x for x in sb if x['CAMPAIGN_ID']==r['id'] and x['DATE']==m['date']]
   self.assertEqual(r['spend'],sum((D(str(x['INVESTIMENT'])) for x in rs),D(0)))
   self.assertEqual(r['roi'],finance.roi(r['net_revenue'],r['spend']))
 def test_new_model_without_source_rejected(self):
  m,sb,cfg=self.fixture()
  with self.assertRaises(layout.LayoutError):layout.render_model(m)
 def test_double_shift_rejected(self):
  m,sb,cfg=self.adjusted();m['financial_source']['additional_timezone_shift']=True
  with self.assertRaises(layout.LayoutError):layout.render_model(m)
 def test_wrong_spend_or_roi_rejected(self):
  m,sb,cfg=self.adjusted();m['rows'][0]['spend']=m['rows'][0]['meta_spend']
  with self.assertRaises(layout.LayoutError):layout.render_model(m)
 def test_current_and_history_same_sb_base(self):
  m,sb,cfg=self.adjusted()
  for row in m['rows']:
   self.assertEqual(row['spend'],row['history'][-1]['spend']);self.assertEqual(row['roi'],row['history'][-1]['roi'])
   self.assertTrue(all(h['spend_source']=='SB_INVESTIMENT_ADJUSTED' for h in row['history']))
 def test_missing_investment_is_nd_not_meta_fallback(self):
  m,sb,cfg=self.fixture();cid=m['rows'][0]['id']
  for x in sb:
   if x['CAMPAIGN_ID']==cid and x['DATE']==m['date']:x.pop('INVESTIMENT',None)
  finance.apply_financial_source(m,sb,cfg);self.assertIsNone(m['rows'][0]['spend']);self.assertIsNone(m['rows'][0]['roi'])
  text=layout.render_model(m)['text'];self.assertIn('Gasto **n/d**',text);self.assertIn('Saldo **n/d**',text)
 def test_zero_investment_is_explicit_zero_roi_nd(self):
  m,sb,cfg=self.fixture()
  for x in sb:
   if x['DATE']==m['date']:x['INVESTIMENT']=0
  finance.apply_financial_source(m,sb,cfg);text=layout.render_model(m)['text'];self.assertIn('Gasto **0,00**',text);self.assertIn('ROI **n/d**',text)
 def test_empty_has_no_invented_revenue(self):
  m,sb,cfg=self.fixture();m['rows']=[];finance.apply_financial_source(m,[],cfg);text=layout.render_model(m)['text']
  self.assertIn('Gasto **0,00**',text);self.assertIn('Rev **n/d**',text);self.assertIn('Saldo **n/d**',text)
 def test_duplicate_source_blocked(self):
  m,sb,cfg=self.fixture()
  with self.assertRaises(finance.FinancialSourceError):finance.apply_financial_source(m,sb+[sb[0]],cfg)
 def test_other_account_source_blocked(self):
  m,sb,cfg=self.fixture();sb[0]['CUSTOMER_ID']='not-the-target'
  with self.assertRaises(finance.FinancialSourceError):finance.apply_financial_source(m,sb,cfg)
 def test_other_date_blocked(self):
  m,sb,cfg=self.fixture();sb[0]['DATE']='2000-01-01'
  with self.assertRaises(finance.FinancialSourceError):finance.apply_financial_source(m,sb,cfg)
 def test_idempotent_apply_preserves_meta(self):
  m,sb,cfg=self.adjusted();before=copy.deepcopy(m);finance.apply_financial_source(m,sb,cfg);self.assertEqual(m,before)
 def test_meta_BU_and_ROAS_not_rebased(self):
  m,sb,cfg=self.fixture();before=copy.deepcopy(m);finance.apply_financial_source(m,sb,cfg);out=layout.render_model(m)['text']
  for a,b in zip(m['rows'],before['rows']):self.assertEqual(a['meta_spend'],b['spend']);self.assertEqual(a['roas'],b['roas'])
  self.assertIn('B.U.% operacional',out);self.assertIn('não usa o Gasto financeiro SB',out)
 def test_historical_replay_exact(self):
  m=json.loads((BASE/'2323706575049143/model.json').read_text());self.assertIsNone(finance.active_rule(m,layout.policy()))
  self.assertEqual(layout.render_model(m)['text'],(BASE/'2323706575049143/report.md').read_text())
 def test_all36_bindings_covered_by_same_rule(self):
  bindings=json.loads(Path('/root/mgs-agent/data/ares/discord/shein-intraday-report-bindings.json').read_text())['bindings']
  self.assertEqual(len(bindings),36)
  for b in bindings:
   m,sb,cfg=self.fixture();m['account'].update(id='act_'+b['account_id'],name=b['account_name'])
   for x in sb:x['CUSTOMER_ID']=b['account_id']
   finance.apply_financial_source(m,sb,cfg);self.assertTrue(finance.validate_financial_source(m,cfg));layout.check_thread_binding(m,b['thread_id'])
 def test_sb_only_campaign_not_lost(self):
  rows=[{'CUSTOMER_ID':'123','DATE':'2026-11-13','CAMPAIGN_ID':'456','INVESTIMENT':1},{'CUSTOMER_ID':'789','DATE':'2026-11-13','CAMPAIGN_ID':'999','INVESTIMENT':9}]
  self.assertEqual(finance.additional_campaign_ids(rows,'123','2026-11-13'),{'456'})
 def test_new_evidence_hash_tampering_rejected(self):
  m,sb,cfg=self.adjusted();m['financial_source']['rows'][0]['INVESTIMENT']=999
  with self.assertRaises(layout.LayoutError):layout.render_model(m)
 def test_cutover_boundary(self):
  m,sb,cfg=self.fixture();at=cfg['financial_source_standard']['effective_from_financial_snapshot']
  m['source_timestamps'].update(insights=at,sb=at);self.assertIsNotNone(finance.active_rule(m,cfg))
if __name__=='__main__':unittest.main()
