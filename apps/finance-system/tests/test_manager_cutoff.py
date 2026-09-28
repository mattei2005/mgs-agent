import copy,json,pathlib,sys,unittest
from decimal import Decimal as D
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import worker

class ManagerCutoffTests(unittest.TestCase):
 def payload(self,as_of='2026-09-22'):
  return {'period':'2026-09','as_of':as_of,'additions':[{'id':'TEST-cutoff','kind':'data_cutoff','date':'2026-09-20','source':'TEST'}]}
 def managers(self,r):return r['domain']['managers']
 def test_midnight_does_not_accrue_beyond_complete_cutoff(self):
  fixture=json.loads((worker.root/'private/simple-review-1551798771661275147/september.json').read_text())
  p={k:fixture[k] for k in ('overrides','additions')};p['period']='2026-09'
  a=worker.run({**p,'as_of':'2026-09-21'});b=worker.run({**p,'as_of':'2026-09-22'})
  self.assertEqual(self.managers(a),self.managers(b))
  self.assertEqual(a['domain']['expenses'],b['domain']['expenses'])
  self.assertEqual(b['summary']['as_of'],'2026-09-22')
 def test_partial_native_revenue_preserved_but_not_in_manager_payroll(self):
  p=self.payload();base=worker.run(p)
  p['additions'].append({'id':'TEST-native-partial','site':'Ducapes','partner':'SB Rede1','manager':'george','country':'US','date':'2026-09-21','currency':'USD','gross':'1234.56','spend':'0','invalid_rate':'0','share_rate':'0','tax_rate':'0','quotes':{'USDBRL':'5','USDCAD':'1.4','GBPUSD':'1.3'}})
  original=copy.deepcopy(p);r=worker.run(p)
  self.assertEqual(self.managers(base),self.managers(r))
  self.assertTrue(any(f['id']=='TEST-native-partial' and D(f['gross'])>0 for f in r['domain']['facts']))
  self.assertEqual(p,original)
 def test_partial_legacy_revenue_preserved_but_not_in_manager_total(self):
  p=self.payload();base=worker.run(p)
  model=json.loads((worker.root/'private/ui-model.json').read_text())
  key=next(k for ident,f in model['facts'].items() if ident.endswith('|21') for k in f['gross'] if 'george' in model['inputs'][k].get('managers',[]))
  p['overrides']={key:'1234.56'};r=worker.run(p)
  self.assertEqual(self.managers(base),self.managers(r))
  self.assertGreater(sum(D(f['gross'] or 0) for f in r['domain']['facts']),sum(D(f['gross'] or 0) for f in base['domain']['facts']))
 def test_null_cutoff_keeps_all_managers_at_zero(self):
  p=self.payload();p['additions'][0]['date']=None;r=worker.run(p)
  for m in self.managers(r):
   if m['row']==12:self.assertEqual(D(m['profit']),D(0))
  self.assertEqual(r['domain']['realized']['elapsed_days'],0)

if __name__=='__main__':unittest.main()
