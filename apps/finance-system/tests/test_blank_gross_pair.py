"""Regression: the first CAD/USD entry in a blank, allowed leaf."""
import copy,json,unittest
from decimal import Decimal as D
from pathlib import Path
from worker import run
from calc import Workbook,CalculationError
from ui_model import prepare_inputs
ROOT=Path(__file__).resolve().parents[1]
KEY='principal|Agosto 2026|D5'
class BlankGrossPair(unittest.TestCase):
 def test_first_fill_blank_leaf_periods(self):
  source=json.loads((ROOT/'private/source.json').read_text());model=json.loads((ROOT/'private/ui-model.json').read_text())
  self.assertIn(KEY,model['inputs']);self.assertFalse(any(c['id']==KEY for c in source['cells']))
  for period in ['2026-09','2026-10','2027-02']:
   payload={'period':period,'overrides':{'principal|Agosto 2026|H1':'1.4'},'additions':[{'kind':'gross_pair','id':'blank-test','period':period,'target_type':'input','target':KEY,'cad':'123.45','usd':'2'}]};saved=copy.deepcopy(payload)
   result=run(payload)
   self.assertEqual(payload,saved);self.assertEqual(result['summary']['counts'].get('error',0),0)
   facts=[f for f in result['domain']['facts'] if f.get('gross_origins',{}).get('CAD')==D('123.45')]
   self.assertEqual(len(facts),1);self.assertEqual(facts[0]['date'],period+'-01');self.assertEqual(facts[0]['gross_origins'],{'CAD':D('123.45'),'USD':D('2')})
   self.assertLess(abs(D(facts[0]['gross'])-(D('123.45')/D('1.4')+D('2'))),D('1e-20'))
  self.assertEqual(json.loads((ROOT/'private/source.json').read_text()),source)
 def test_unlisted_blank_and_formula_still_rejected(self):
  source=json.loads((ROOT/'private/source.json').read_text());model=json.loads((ROOT/'private/ui-model.json').read_text());saved=copy.deepcopy(source)
  for key in ['principal|Agosto 2026|ZZZ9999','principal|Agosto 2026|APE38']:
   self.assertNotIn(key,model['inputs']);w=Workbook(prepare_inputs(source,{key:D(1)},model),{key:D(1)})
   with self.assertRaises(CalculationError):w.get(*key.split('|'))
  self.assertEqual(source,saved)
if __name__=='__main__':unittest.main()
