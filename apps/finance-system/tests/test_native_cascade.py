import unittest
from decimal import Decimal as D
from worker import run
from expenses import compensation
class NativeCascadeTests(unittest.TestCase):
 def test_new_country_reaches_manager_payroll_and_cash(self):
  base=run({});payload={'id':'test-only-native','site':'TEST ONLY','partner':'TEST','manager':'nicolas','country':'BR','date':'2026-08-01','currency':'USD','gross':'100000','spend':'0','invalid_rate':'0','share_rate':'.1','tax_rate':'.05','quotes':{'USDBRL':'5','USDCAD':'1.4','GBPUSD':'1.3'}}
  changed=run({'additions':[payload]});a=base['domain'];b=changed['domain'];delta=D('100000')*(1-D('.1'))*(1-D('.05'))
  old=next(r for r in a['managers'] if r['manager']=='nicolas' and r['row']==12);new=next(r for r in b['managers'] if r['manager']=='nicolas' and r['row']==12)
  self.assertAlmostEqual(new['profit']-old['profit'],delta,places=18)
  old_salary=next(x for x in a['expenses'] if x['manager']=='nicolas')['usd'];new_salary=next(x for x in b['expenses'] if x['manager']=='nicolas')['usd']
  self.assertLess(new_salary,old_salary)
  self.assertAlmostEqual(b['cash']['profit']-a['cash']['profit'],delta+new_salary-old_salary,places=18)
  self.assertEqual(base['summary']['status'],'PARITY_PASS');self.assertEqual(changed['summary']['status'],'SCENARIO_CHANGED')
if __name__=='__main__':unittest.main()
