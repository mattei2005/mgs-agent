import importlib.util,json,unittest
from pathlib import Path
R=Path(__file__).parent
s=importlib.util.spec_from_file_location('current_intraday',R/'intraday.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
l=a.d.module('summary_layout',a.H/'scripts/shein-report-layout.py')
def model(rows):return {'account':{'name':'Fixture G006','timezone_name':'America/New_York'},'rows':rows,'date':'2026-11-17','source_timestamps':{'financial':'2026-11-17T10:00:00-05:00'}}
def row(sp,net,est):return {'spend':sp,'net_revenue':net,'estimated_revenue':est,'meta_spend':'999'}
class SummaryTests(unittest.TestCase):
 def test_empty(self):
  t=a.summary(model([]),l)
  for text in ['Gasto: **US$ 0,00**','Receita líquida: **n/d**','Saldo: **n/d**','ROI real: **n/d**','ROI estimado: **n/d**']:self.assertIn(text,t)
 def test_explicit_zero(self):
  t=a.summary(model([row('0','0','0')]),l)
  for text in ['Gasto: **US$ 0,00**','Receita líquida: **US$ 0,00**','Saldo: **US$ 0,00**','ROI real: **n/d**','ROI estimado: **n/d**']:self.assertIn(text,t)
 def test_missing_revenues_independent(self):
  t=a.summary(model([row('10',None,'12'),row('20','25',None)]),l)
  for text in ['Gasto: **US$ 30,00**','Receita líquida: **n/d**','Saldo: **n/d**','ROI real: **n/d**','ROI estimado: **n/d**','receita líquida SB','receita estimada SB']:self.assertIn(text,t)
  self.assertNotIn('investimento SB;',t)
 def test_missing_investment_preserves_revenue(self):
  t=a.summary(model([row('10','12','14'),row(None,'25','30')]),l)
  for text in ['Gasto: **n/d**','Receita líquida: **US$ 37,00**','Saldo: **n/d**','ROI real: **n/d**','ROI estimado: **n/d**','Cobertura incompleta de investimento SB;']:self.assertIn(text,t)
  self.assertNotIn('receita incompleta',t);self.assertNotIn('999',t)
 def test_weighted_roi(self):
  t=a.summary(model([row('10','20','30'),row('90','90','90')]),l)
  for text in ['Gasto: **US$ 100,00**','Receita líquida: **US$ 110,00**','Saldo: **+US$ 10,00**','ROI real: **10,00%**','ROI estimado: **20,00%**']:self.assertIn(text,t)
  positions=[t.index(x) for x in ['• Gasto:','• Receita líquida:','• Saldo:','• ROI real:','• ROI estimado:']];self.assertEqual(positions,sorted(positions));self.assertNotIn('ROI real: **50,00%',t)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SummaryTests))
 p=R/'test-results.json';d=json.loads(p.read_text());d['summary_fixtures']={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()};p.write_text(json.dumps(d,ensure_ascii=False,indent=2));raise SystemExit(0 if result.wasSuccessful() else 1)
