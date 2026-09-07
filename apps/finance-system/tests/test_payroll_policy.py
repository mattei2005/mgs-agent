"""Explicit TEST-only cases for policy authorized by 1546380179654451281."""
import unittest
from decimal import Decimal as D
from expenses import apply_payroll_policy

class PayrollPolicyTests(unittest.TestCase):
 def rows(self):
  return [dict(id='personnel|148',category='personnel',manager='joe',mode='COMMISSION_FLOOR',usd=D('-1'),brl=D('-5')),dict(id='personnel|159',category='personnel',manager=None,mode='BRL',usd=D('-600'),brl=D('-3000'))]
 def calculate(self,profit,activity='ATIVO'):
  rows=self.rows();changes=[dict(kind='expense',id='personnel|148',payroll_rule='monthly-v1',activity=activity)]
  return apply_payroll_policy(rows,changes,[dict(manager='joe',row=12,profit=D(profit)/5)],D(5))[0]
 def test_threshold_inclusive_and_floor(self):
  for profit,expected in [('0','3000'),('-100','3000'),('42857.15','3000.00'),('60000','4200'),('99999.99','7000.00'),('100000','10000'),('100000.01','10000.00'),('120000','12000')]:
   with self.subTest(profit=profit):self.assertEqual(self.calculate(profit)['brl'],-D(expected))
 def test_inactive_zero(self):self.assertEqual(self.calculate('120000','INATIVO')['usd'],0)
 def test_fixed_and_manager_separate(self):
  rows=self.rows();changes=[dict(kind='expense',id=x['id'],payroll_rule='monthly-v1',activity='ATIVO') for x in rows]
  out=apply_payroll_policy(rows,changes,[dict(manager='joe',row=12,profit=0)],D(5))
  self.assertEqual([x['brl'] for x in out],[-D(3000),-D(3000)])
 def test_baseline_no_policy_unchanged(self):
  rows=self.rows();self.assertEqual(apply_payroll_policy(rows,[],[],D(5)),rows)
 def test_inactive_fixed_and_archived(self):
  for field in ['activity','archived']:
   rows=self.rows();changes=[dict(kind='expense',id='personnel|159',payroll_rule='monthly-v1',activity='INATIVO' if field=='activity' else 'ATIVO')]
   if field=='archived':rows[1]['archived']=True
   self.assertEqual(apply_payroll_policy(rows,changes,[],D(5))[1]['brl'],0)
 def test_active_manager_missing_mapping_fails_closed(self):
  with self.assertRaises(ValueError):apply_payroll_policy(self.rows(),[dict(kind='expense',id='personnel|148',payroll_rule='monthly-v1',activity='ATIVO')],[],D(5))

if __name__=='__main__':unittest.main()
