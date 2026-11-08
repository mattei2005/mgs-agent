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
class LegacyUnmappedCosts(unittest.TestCase):
 def fact(self,**kw):
  return dict({'id':'zuout-principal|US|1','site':'Zuout','country':'US','date':'2026-10-01','manager':'NÃO MAPEADO','spend':'-47.75'},**kw)
 def site(self,**kw):
  return dict({'name':'Zuout','manager':'Nicolas','native_account_managers':True},**kw)
 def test_legacy_unmapped_cost_reaches_named_owner_once(self):
  facts=[self.fact()];before=[dict(x) for x in facts]
  r=native_manager_costs([], [self.site()], Quotes(), facts)
  self.assertEqual(len(r),1);self.assertEqual(r[0]['manager'],'nicolas');self.assertEqual(r[0]['profit'],Decimal('-47.75'));self.assertTrue(r[0]['legacy_source_spend']);self.assertEqual(facts,before)
 def test_disabled_flag_and_unknown_owner_preserved(self):
  for site in [self.site(native_account_managers=False),self.site(manager='SEM_COMISSAO'),self.site(manager='COMPARTILHADO')]:
   self.assertEqual(native_manager_costs([], [site], Quotes(), [self.fact()]),[])
 def test_already_mapped_legacy_cost_not_debited_again(self):
  self.assertEqual(native_manager_costs([], [self.site()], Quotes(), [self.fact(manager='Nicolas')]),[])
 def test_native_facts_are_not_legacy_costs(self):
  for flag in ['native_addition','native_placeholder']:
   self.assertEqual(native_manager_costs([], [self.site()], Quotes(), [self.fact(**{flag:True})]),[])
 def test_native_part_subtracted_from_legacy_aggregate(self):
  row={'kind':'account_spend','site':'Zuout','account_id':'123456','fact_id':'zuout-principal|US|1','date':'2026-10-01','manager_key':'nicolas','currency':'USD','amount':'10'}
  r=native_manager_costs([row],[self.site()],Quotes(),[self.fact(spend='-57.75')]);self.assertEqual(len(r),2);self.assertEqual(sum(x['profit'] for x in r),Decimal('-57.75'));self.assertEqual(r[-1]['profit'],Decimal('-47.75'))
 def test_zero_cost_has_no_synthetic_manager_charge(self):
  self.assertEqual(native_manager_costs([], [self.site()], Quotes(), [self.fact(spend='0')]),[])
 def test_positive_spend_rejected_not_abs_reclassified(self):
  with self.assertRaises(ValueError):native_manager_costs([], [self.site()], Quotes(), [self.fact(spend='1')])
 def test_explicit_mgs_native_part_never_moves_to_owner(self):
  row={'kind':'account_spend','site':'Zuout','account_id':'123456','fact_id':'zuout-principal|US|1','date':'2026-10-01','manager_key':'SEM_COMISSAO','currency':'USD','amount':'10'}
  r=native_manager_costs([row],[self.site()],Quotes(),[self.fact(spend='-57.75')]);self.assertEqual(len(r),1);self.assertEqual(r[0]['profit'],Decimal('-47.75'))
if __name__=='__main__':unittest.main()
