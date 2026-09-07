import unittest,json,pathlib
from decimal import Decimal as D
from worker import run
from ui_model import apply_expense_changes
ROOT=pathlib.Path(__file__).resolve().parents[1]
class OriginTests(unittest.TestCase):
 def test_live_import_rules_recompute_brl_usd_and_fixed_payroll(self):
  s=json.loads((ROOT/'private/origin-1546618148571058266/production-before.json').read_text())[0]
  for fx in ['5','4']:
   r=run({'period':'2026-08','as_of':'2026-09-07','overrides':{**s['overrides'],'principal|CAIXA SINTETICO|J2':fx},'additions':s['additions']});rows={e['id']:e for e in r['domain']['expenses']}
   for id,amount in [('company|113','100'),('personnel|155','2000'),('personnel|156','7000')]:
    self.assertEqual(D(rows[id]['brl']),-D(amount));self.assertEqual(D(rows[id]['usd']),-D(amount)/D(fx))
   self.assertEqual(D(rows['company|114']['usd']),D('-200'));self.assertEqual(D(rows['company|114']['brl']),D('-200')*D(fx));self.assertEqual(r['summary']['counts'].get('error',0),0)
 def test_native_billing_preserves_cad_and_unit_divisors(self):
  rows=[{'id':'cad','category':'company','mode':'CAD','label':'wire','usd':0,'brl':0},{'id':'units','category':'company','mode':'UNIT_COST_DIVISOR','label':'units','usd':0,'brl':0}]
  changes=[{'kind':'expense','id':'cad','amount':'25','currency':'CAD'},{'kind':'expense','id':'units','amount':'629.28','currency':'UNITS'}]
  out=apply_expense_changes(rows,changes,'5',{'CAD':'1.25','UNITS':'50'})
  self.assertEqual(out[0]['usd'],D('-20'));self.assertEqual(out[0]['edit_amount'],'25');self.assertEqual(out[1]['usd'],D('-12.5856'))
if __name__=='__main__':unittest.main()
