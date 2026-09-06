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
if __name__=='__main__':unittest.main()
