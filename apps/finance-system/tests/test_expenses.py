import unittest
from decimal import Decimal as D
from expenses import compensation
from ui_model import apply_expense_changes
class PayrollTests(unittest.TestCase):
 def test_floor_negative_profit(self):self.assertEqual(compensation(-100,5),-600)
 def test_low_rate(self):self.assertEqual(compensation(10000,5),-700)
 def test_high_boundary(self):self.assertEqual(compensation(20000,5),-2000)
 def test_floor_boundary(self):
  profit=D(3000)/D('.07')/5
  self.assertAlmostEqual(compensation(profit,5),D(-600),places=20)
class CompanyCreditTests(unittest.TestCase):
 def setUp(self):self.rows=[{'id':'company|122','category':'company','label':'Ferramenta ver artigos:','mode':'BRL','usd':D('-19.4'),'brl':D('-97')}]
 def test_credit_is_positive_and_preserves_original_currency(self):
  out=apply_expense_changes(self.rows,[{'kind':'expense','id':'company|122','target':'company|122','category':'company','label':'Crédito/estorno SPYFLIX','amount':'2522','currency':'BRL','direction':'credit'}],D('5.11'))[0]
  self.assertEqual(out['brl'],D('2522'));self.assertEqual(out['usd'],D('2522')/D('5.11'));self.assertEqual(out['direction'],'credit')
 def test_legacy_expense_remains_debit(self):
  out=apply_expense_changes(self.rows,[{'kind':'expense','id':'company|122','target':'company|122','category':'company','amount':'97','currency':'BRL'}],D('5'))[0]
  self.assertEqual(out['brl'],D('-97'));self.assertEqual(out['direction'],'debit')
 def test_personnel_credit_fails_closed(self):
  with self.assertRaisesRegex(ValueError,'direction'):
   apply_expense_changes([], [{'kind':'expense','id':'personnel-test','category':'personnel','amount':'1','currency':'BRL','direction':'credit'}],D('5'))
if __name__=='__main__':unittest.main()
