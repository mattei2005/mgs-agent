import unittest,json,pathlib
from decimal import Decimal
from ui_model import build_model,prepare_inputs,apply_expense_changes
from calc import Workbook
ROOT=pathlib.Path(__file__).resolve().parents[1]
class InterfaceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data=json.loads((ROOT/'private/source.json').read_text());cls.model=build_model(cls.data)
 def test_every_daily_fact_has_input_mapping(self):
  self.assertEqual(len(self.model['facts']),2418)
  self.assertTrue(all(x['gross'] and x['spend'] for x in self.model['facts'].values()))
 def test_empty_inputs_allowed_but_formulas_never(self):
  allowed=self.model['inputs'];self.assertIn('principal|Agosto 2026|D5',allowed)
  self.assertNotIn('principal|Agosto 2026|E5',allowed)
  data=prepare_inputs(self.data,{'principal|Agosto 2026|D5':'12.5'},self.model)
  w=Workbook(data,{'principal|Agosto 2026|D5':12.5});self.assertEqual(w.get('principal','Agosto 2026','D5'),Decimal('12.5'))
 def test_rates_dates_and_text_not_editable(self):
  self.assertNotIn('principal|Agosto 2026|H1',self.model['inputs'])
  self.assertNotIn('principal|Agosto 2026|M100',self.model['inputs'])
 def test_expense_adjustment_and_archive_do_not_double_count(self):
  rows=[{'id':'company|100','category':'company','usd':Decimal('-10'),'brl':Decimal('-50'),'label':'A','mode':'USD','manager':None}]
  out=apply_expense_changes(rows,[{'kind':'expense','id':'x','target':'company|100','category':'company','label':'Edited','status':'Pago','amount':'20','currency':'BRL','archived':False}],Decimal('5'))
  self.assertEqual(out[0]['usd'],Decimal('-4'));self.assertEqual(out[0]['brl'],Decimal('-20'))
  archived=apply_expense_changes(rows,[{'kind':'expense','id':'x','target':'company|100','category':'company','archived':True}],Decimal('5'))
  self.assertEqual(archived[0]['usd'],0);self.assertTrue(archived[0]['archived'])
 def test_payroll_metadata_preserves_calculation(self):
  rows=[{'id':'personnel|148','category':'personnel','usd':Decimal('-600'),'brl':Decimal('-3000'),'label':'Manager','mode':'COMMISSION_FLOOR','manager':'joe'}]
  out=apply_expense_changes(rows,[{'kind':'expense','id':'x','target':'personnel|148','category':'personnel','label':'Joe','status':'Pago','archived':False}],Decimal('5'))
  self.assertEqual(out[0]['usd'],Decimal('-600'));self.assertEqual(out[0]['status'],'Pago')
if __name__=='__main__':unittest.main()
