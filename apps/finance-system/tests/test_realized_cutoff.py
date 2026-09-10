import unittest,pathlib,sys
from decimal import Decimal as D
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]));import worker
class CutoffTests(unittest.TestCase):
 def row(self,day,gross):return {'id':'TEST-cutoff-'+str(day),'site':'TEST cutoff','partner':'SB Rede1','manager':'SEM_COMISSAO','country':'US','date':f'2026-09-{day:02d}','currency':'USD','gross':str(gross),'spend':'0','invalid_rate':'0','share_rate':'0','tax_rate':'0','quotes':{'USDBRL':'5','USDCAD':'1.4','GBPUSD':'1.3'}}
 def test_realized_stops_at_explicit_complete_day_and_projection_subtracts_fixed_once(self):
  additions=[self.row(1,100),self.row(10,1000),{'kind':'data_cutoff','id':'data-cutoff-2026-09','date':'2026-09-09','source':'TEST'}];r=worker.run({'period':'2026-09','as_of':'2026-09-10','additions':additions});z=r['domain']['realized'];self.assertEqual(z['cutoff_date'],'2026-09-09');self.assertEqual(z['elapsed_days'],9);self.assertEqual(D(z['gross']),D(100));self.assertEqual(D(z['company_expenses']),D(r['domain']['cash']['company_expenses'])*D(9)/D(30));self.assertEqual(D(z['personnel']),D(r['domain']['cash']['personnel'])*D(9)/D(30));p=r['domain']['projection'];expected=(D(100)*D(30)/D(9)+D(r['domain']['cash']['company_expenses'])+D(r['domain']['cash']['personnel']))/2;self.assertEqual(D(p['half_usd']),expected);wrong=(D(1100)*D(30)/D(9)+D(r['domain']['cash']['company_expenses'])+D(r['domain']['cash']['personnel']))/2;self.assertNotEqual(D(p['half_usd']),wrong)
 def test_cutoff_rejects_current_or_future_day(self):
  with self.assertRaisesRegex(ValueError,'dia completo'):worker.run({'period':'2026-09','as_of':'2026-09-10','additions':[{'kind':'data_cutoff','id':'data-cutoff-2026-09','date':'2026-09-10','source':'TEST'}]})
if __name__=='__main__':unittest.main()
