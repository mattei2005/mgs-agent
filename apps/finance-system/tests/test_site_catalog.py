import unittest,json,pathlib
from decimal import Decimal as D
import worker
class CatalogTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.base=worker.run({})
 def test_active_native_allocation_and_extra_propagation(self):
  from site_catalog import catalog
  cat=catalog(self.base['domain']['segments'],[]);egg=next(s for s in cat if s['name']=='Eggbev')
  after=worker.run({'additions':[{'kind':'site','id':egg['id'],'name':egg['name'],'status':'INATIVO'}]})
  self.assertEqual(sum(s['units'] for s in after['domain']['site_catalog'] if s['status']=='ATIVO'),29)
  self.assertEqual(next(s['expenses'] for s in after['domain']['segments'] if s['site']=='Eggbev'),D(0))
  e=worker.run({'additions':[{'kind':'expense','id':'TEST-company','category':'company','label':'TEST only','amount':'30','currency':'USD','status':'A conferir'}]})
  self.assertAlmostEqual(float(sum(s['expenses'] for s in e['domain']['segments'])-sum(s['expenses'] for s in self.base['domain']['segments'])),-30,places=7)
  def nic(x):return next(m['profit'] for m in x['domain']['managers'] if m['manager']=='nicolas' and m['row']==12)
  self.assertNotEqual(nic(self.base),nic(e))
 def test_new_site_adds_one_unit_and_inactive_keeps_history(self):
  new={'kind':'site','id':'newsite-TEST','name':'TEST new finance site','status':'ATIVO','new':True,'countries':['US'],'manager':'nicolas','partner':'JBF','currency':'USD','invalid_source':'L1'}
  a=worker.run({'additions':[new]});self.assertEqual(sum(s['units'] for s in a['domain']['site_catalog'] if s['status']=='ATIVO'),31)
  f=[f for f in a['domain']['facts'] if f['site']==new['name']];self.assertEqual(len(f),31)
  self.assertAlmostEqual(float(sum(s['expenses'] for s in a['domain']['segments'])),float(a['domain']['cash']['company_expenses']),places=7)
  row={'id':'TEST-entry','site':new['name'],'partner':'JBF','manager':'nicolas','country':'US','date':'2026-08-01','currency':'USD','gross':'100','spend':'1','invalid_rate':'0','share_rate':'0.1','tax_rate':'0.05','quotes':{'USDBRL':'5','USDCAD':'1.3','GBPUSD':'1.2'}}
  b=worker.run({'additions':[{**new,'status':'INATIVO'},row]});self.assertEqual(sum(float(f['gross'] or 0) for f in b['domain']['facts'] if f['site']==new['name']),100)
  self.assertEqual(next(s['expenses'] for s in b['domain']['segments'] if s['site']==new['name']),0)
 def test_baseline_no_native_mutations_remains_parity(self):self.assertEqual(self.base['summary']['status'],'PARITY_PASS')
 def test_native_spend_before_and_after_revenue(self):
  site={'kind':'site','id':'newsite-TEST-spend','name':'TEST native spend','status':'INATIVO','new':True,'countries':['US'],'manager':'SEM_COMISSAO','partner':'JBF','currency':'USD','invalid_source':'L1'}
  spend={'kind':'account_spend','id':'account|123|newsite-TEST-spend|US|25','fact_id':'newsite-TEST-spend|US|25','account_id':'123','currency':'USD','amount':'52.4','date':'2026-09-25','site':site['name'],'manager_key':'SEM_COMISSAO'}
  cutoff={'kind':'data_cutoff','id':'data-cutoff-2026-09','date':'2026-09-24','source':'test'}
  payload={'period':'2026-09','additions':[site,spend,cutoff]}
  before=worker.run(payload);facts=[f for f in before['domain']['facts'] if f['site']==site['name'] and f['date']==spend['date']]
  self.assertEqual(len(facts),1);self.assertEqual(facts[0]['spend'],D('-52.4'));self.assertEqual(facts[0]['gross'],'');self.assertEqual(before['domain']['realized']['cutoff_date'],'2026-09-24')
  revenue={'id':'TEST-native-revenue','site':site['name'],'partner':'JBF','manager':'SEM_COMISSAO','country':'US','date':spend['date'],'currency':'USD','gross':'100','spend':'0','invalid_rate':'0','share_rate':'0.1','tax_rate':'0.05','quotes':{'USDBRL':'5','USDCAD':'1.3','GBPUSD':'1.2'}}
  after=worker.run({**payload,'additions':[site,spend,revenue,{**cutoff,'date':'2026-09-25'}]});facts=[f for f in after['domain']['facts'] if f['site']==site['name'] and f['date']==spend['date']]
  self.assertEqual(len(facts),2);self.assertEqual(sum(D(f['spend'] or 0) for f in facts),D('-52.4'));self.assertEqual(sum(D(f['gross'] or 0) for f in facts),D('100'))
  self.assertEqual(after['domain']['cash']['spend'],before['domain']['cash']['spend']);self.assertEqual(after['domain']['realized']['cutoff_date'],'2026-09-25')
 def test_native_spend_invalid_targets_remain_blocked(self):
  site={'kind':'site','id':'newsite-TEST-spend','name':'TEST native spend','status':'INATIVO','new':True,'countries':['US'],'manager':'SEM_COMISSAO','partner':'JBF','currency':'USD','invalid_source':'L1'}
  spend={'kind':'account_spend','id':'account|123|newsite-TEST-spend|US|25','fact_id':'newsite-TEST-spend|US|25','account_id':'123','currency':'USD','amount':'52.4','date':'2026-09-25','site':site['name']}
  for change in [{'fact_id':'unknown|US|25'},{'date':'2026-09-24'},{'site':'Wrong site'},{'fact_id':'newsite-TEST-spend|BR|25'},{'fact_id':'newsite-TEST-spend|US|31','date':'2026-09-31'}]:
   with self.subTest(change=change),self.assertRaisesRegex(ValueError,'Conta sem vínculo'):worker.run({'period':'2026-09','additions':[site,{**spend,**change}]})
if __name__=='__main__':unittest.main()
