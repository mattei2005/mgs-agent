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


 def exception(self):return dict(id='joe-october-10pct-1575202919324844063',authority='1575202919324844063',period='2026-10',manager='joe',rate='0.10')
 def exceptional(self,profit,period='2026-10',activity='ATIVO'):
  rows=self.rows();changes=[dict(kind='expense',id='personnel|148',payroll_rule='monthly-v1',activity=activity,commission_exception=self.exception())]
  return apply_payroll_policy(rows,changes,[dict(manager='joe',row=12,profit=D(profit)/5)],D(5),period=period)[0]
 def test_exception_joe_october_company_cost_once(self):
  r=self.exceptional('98787.11');self.assertEqual(r['brl'],D('-9878.71'));self.assertEqual(r['commission_exception']['normal_brl'],D('6915.10'));self.assertEqual(r['commission_exception']['complement_brl'],D('2963.61'));self.assertEqual(r['commission_base_brl'],D('98787.11'));self.assertEqual(r['commission_rate'],D('.10'))
 def test_exception_preserves_floor_high_band_and_inactive(self):
  self.assertEqual(self.exceptional('1000')['brl'],D('-3000'));self.assertEqual(self.exceptional('1000')['commission_exception']['complement_brl'],0)
  self.assertEqual(self.exceptional('120000')['brl'],D('-12000'));self.assertEqual(self.exceptional('120000')['commission_exception']['complement_brl'],0)
  self.assertEqual(self.exceptional('98787.11',activity='INATIVO')['brl'],0)
 def test_exception_rejects_wrong_month_identity_rate_or_authority(self):
  for period in [None,'2026-09','2026-11','2027-10']:
   with self.subTest(period=period),self.assertRaises(ValueError):self.exceptional('98787.11',period)
  for field,bad in [('authority','other'),('manager','kelly'),('period','2026-11'),('rate','0.11'),('id','other')]:
   ex=self.exception();ex[field]=bad
   with self.subTest(field=field),self.assertRaises(ValueError):apply_payroll_policy(self.rows(),[dict(kind='expense',id='personnel|148',payroll_rule='monthly-v1',commission_exception=ex)],[dict(manager='joe',row=12,profit=100)],D(5),period='2026-10')
  rows=self.rows();rows[0]['manager']='kelly'
  with self.assertRaises(ValueError):apply_payroll_policy(rows,[dict(kind='expense',id='personnel|148',payroll_rule='monthly-v1',commission_exception=self.exception())],[dict(manager='kelly',row=12,profit=100)],D(5),period='2026-10')
 def test_exception_rejects_duplicate_and_keeps_inputs_immutable(self):
  from copy import deepcopy
  rows=self.rows();changes=[dict(kind='expense',id='personnel|148',payroll_rule='monthly-v1',commission_exception=self.exception())];original=deepcopy((rows,changes));args=(rows,changes,[dict(manager='joe',row=12,profit=D('98787.11')/5)],D(5));a=apply_payroll_policy(*args,period='2026-10');b=apply_payroll_policy(*args,period='2026-10');self.assertEqual(a,b);self.assertEqual((rows,changes),original)
  with self.assertRaises(ValueError):apply_payroll_policy(rows,changes+changes,[],D(5),period='2026-10')

if __name__=='__main__':unittest.main()
