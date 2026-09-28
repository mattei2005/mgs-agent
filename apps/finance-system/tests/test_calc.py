"""Regression first: no cached formula values may enter calculation."""
import unittest
from calc import Workbook, CalculationError

class CalculationTests(unittest.TestCase):
 def book(self, cells):return Workbook({'cells':cells,'as_of':'2026-09-05','sources':{}})
 def test_recursive_not_cached(self):
  w=self.book([{'book':'b','sheet':'s','cell':'A1','input':3,'expected':3},{'book':'b','sheet':'s','cell':'B1','formula':'=A1*2','expected':900},{'book':'b','sheet':'s','cell':'C1','formula':'=B1+1','expected':999}])
  self.assertEqual(w.get('b','s','C1'),7)
 def test_overrides_flow(self):
  w=self.book([{'book':'b','sheet':'s','cell':'A1','input':3},{'book':'b','sheet':'s','cell':'B1','formula':'=A1*2'}]); w.overrides={'b|s|A1':5}
  self.assertEqual(w.get('b','s','B1'),10)
 def test_cycle_fails(self):
  w=self.book([{'book':'b','sheet':'s','cell':'A1','formula':'=B1'},{'book':'b','sheet':'s','cell':'B1','formula':'=A1'}])
  with self.assertRaises(CalculationError):w.get('b','s','A1')
 def test_unresolved_not_cached(self):
  w=self.book([{'book':'b','sheet':'s','cell':'A1','formula':'=UNKNOWN(3)','expected':6}])
  with self.assertRaises(CalculationError):w.get('b','s','A1')
class CoordinateCacheTests(unittest.TestCase):
 def test_coordinates_cached_not_financial_values(self):
  from calc import address
  address.cache_clear();self.assertEqual(address('AZ19'),(19,52));self.assertEqual(address('AZ19'),(19,52));self.assertEqual(address.cache_info().hits,1)
 def test_reference_cache_is_per_workbook_and_immutable_to_caller(self):
  def book(last):return Workbook({'cells':[{'book':'b','sheet':'s','cell':'A'+str(last),'input':last}],'as_of':'2026-09-05','sources':{}})
  a,b=book(1),book(9);self.assertEqual(a.ref('A:A','b','s').r2,1);self.assertEqual(b.ref('A:A','b','s').r2,9)
  ref=a.ref('A:A','b','s');ref.r2=99;self.assertEqual(a.ref('A:A','b','s').r2,1);self.assertTrue(a._refcoords)
class AugustRede2ClosingTests(unittest.TestCase):
 def row(self):return {'kind':'monthly_gross_adjustment','period':'2026-08','date':'2026-08','authority':'1554177164872519692','id':'august-rede2-1554177164872519692-cpv','site':'CreditoParaVeiculo','target_monthly_gross':'71824.15','manager':'SEM_COMISSAO','country':'BR','partner':'SB Rede2','source_network':'SB Rede2','currency':'USD','gross':'8.250550586970137850','spend':'0'}
 def test_exact_authorized_targets(self):
  from worker import validate_monthly_adjustment
  a=self.row();validate_monthly_adjustment(a,'2026-08');b={**a,'id':'august-rede2-1554177164872519692-gamezone','site':'GameZoneAd','target_monthly_gross':'13653.88','gross':'1.611454584938138847'};validate_monthly_adjustment(b,'2026-08')
 def test_other_month_and_invented_day_rejected(self):
  from worker import validate_monthly_adjustment
  with self.assertRaises(ValueError):validate_monthly_adjustment(self.row(),'2026-09')
  with self.assertRaises(ValueError):validate_monthly_adjustment({**self.row(),'date':'2026-08-31'},'2026-08')
 def test_other_financial_scopes_rejected(self):
  from worker import validate_monthly_adjustment
  for key,value in [('site','Fincgriffin'),('manager','nicolas'),('country','US'),('partner','AV'),('currency','CAD'),('source_network','AV'),('spend','1'),('gross','451.60'),('authority','unapproved'),('target_monthly_gross','71825')]:
   with self.subTest(key=key),self.assertRaises(ValueError):validate_monthly_adjustment({**self.row(),key:value},'2026-08')
 def test_previous_closing_authority_preserved(self):
  from worker import validate_monthly_adjustment
  validate_monthly_adjustment({'period':'2026-08','date':'2026-08','authority':'1551358728870035530'},'2026-08')
if __name__=='__main__':unittest.main()
