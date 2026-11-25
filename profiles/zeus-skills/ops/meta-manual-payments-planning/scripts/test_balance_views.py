import copy,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('views',Path(__file__).with_name('publish_balance_views.py'));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def row(name):return {'values':[{'userEnteredValue':{'stringValue':name}}]+[{} for _ in range(9)]}
def account(i,method,balance=None):
 r=row('Unit account '+i);r['values'][0]['note']='ID da conta: '+i;r['values'][1]['userEnteredValue']={'stringValue':method}
 if balance is not None:r['values'][8]['effectiveValue']={'numberValue':balance};r['values'][8]['userEnteredValue']={'numberValue':balance}
 return r

def fixture():
 return [row('Nome da conta'),row('CARTÃO DE CRÉDITO — 1 contas'),account('101','Cartão de crédito',0),row('TOTAL CARTÃO DE CRÉDITO'),row('LINHA DE CRÉDITO — 2 contas'),row('Nome da conta'),account('102','Linha de crédito',12.34),account('103','Linha de crédito'),row('TOTAL LINHA DE CRÉDITO'),row('TOTAL GERAL — 3 contas')]

class ViewsTests(unittest.TestCase):
 def test_only_explicit_numeric_zero(self):
  r=account('101','Cartão de crédito',0);self.assertTrue(v.is_zero(r));r['values'][8]['effectiveValue']={'stringValue':'0'};self.assertFalse(v.is_zero(r));r['values'][8]['effectiveValue']={'errorValue':{'type':'N_A'}};self.assertFalse(v.is_zero(r));r['values'][8]['effectiveValue']={'numberValue':False};self.assertFalse(v.is_zero(r))
 def test_negative_retained(self):self.assertFalse(v.is_zero(account('101','Linha de crédito',-3)))
 def test_partition_complete_disjoint(self):
  a,b=v.partition(fixture());self.assertEqual([v.aid(r)for r in a],['102','103']);self.assertEqual([v.aid(r)for r in b],['101'])
 def test_duplicate_rejected(self):
  r=fixture();r.append(copy.deepcopy(r[2]));self.assertRaises(AssertionError,v.partition,r)
 def test_authored_values_notes_links_preserved(self):
  rows=fixture();rows[2]['values'][0]['userEnteredFormat']={'textFormat':{'link':{'uri':'https://example.invalid/test-only'}}};original=copy.deepcopy(rows);a,b=v.partition(rows);out,bounds=v.build_view(rows,b,'UNIT_TEST')
  self.assertEqual(next(x for x in out if v.aid(x)=='101'),v.authored(rows[2]));self.assertEqual(rows,original);self.assertEqual(len(out),len(b)+8)
 def test_empty_view_uses_zero_formula(self):
  out,_=v.build_view(fixture(),[],'UNIT_TEST');self.assertEqual(len(out),8);self.assertFalse(any(v.aid(r)for r in out));self.assertTrue(any(c.get('userEnteredValue',{}).get('formulaValue')=='=ROUND(SUM(0),2)'for r in out for c in r['values']))
 def test_blank_omission_canonical_only(self):
  self.assertEqual(v.canon({'values':[{},{}]}),v.canon({'values':[]}));self.assertNotEqual(v.canon({'values':[{'note':'keep'}]}),v.canon({'values':[]}))
 def test_pending_h_never_zeroed(self):
  rows=fixture();rows[6]['values'][7]['note']='PENDENTE_H_NOVA_CONTA: UNIT_TEST';out,_=v.build_view(rows,[rows[6]],'UNIT_TEST');r=next(x for x in out if v.aid(x)=='102');self.assertNotIn('userEnteredValue',r['values'][7]);self.assertEqual(r['values'][7]['note'],'PENDENTE_H_NOVA_CONTA: UNIT_TEST')

if __name__=='__main__':unittest.main()
