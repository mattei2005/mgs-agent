import unittest,sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from account_manager_costs import native_manager_costs
from decimal import Decimal
class Quotes:
 def get(self,book,month,cell):return {'F1':Decimal('5'),'H1':Decimal('1.3'),'I1':Decimal('1.2')}[cell]
class ManagerCosts(unittest.TestCase):
 def row(self,**kw):return dict(kind='account_spend',site='Yolokfx',account_id='1583000095650153',date='2026-09-01',manager_key='nicolas',currency='USD',amount='25.12',**kw)
 def test_opt_in_and_no_legacy_double_debit(self):
  self.assertEqual(native_manager_costs([self.row()],[{'name':'Yolokfx'}],Quotes()),[])
 def test_exact_native_cost_and_original_currency(self):
  row=self.row();row.update(currency='BRL',amount='125.60');result=native_manager_costs([row],[{'name':'Yolokfx','native_account_managers':True}],Quotes());self.assertEqual(result[0]['profit'],Decimal('-25.12'));self.assertEqual(result[0]['amount'],'125.60');self.assertTrue(result[0]['spend_only'])
 def test_mgs_no_commission_manager(self):
  row=self.row();row['manager_key']='SEM_COMISSAO';self.assertEqual(native_manager_costs([row],[{'name':'Yolokfx','native_account_managers':True}],Quotes()),[])
if __name__=='__main__':unittest.main()
