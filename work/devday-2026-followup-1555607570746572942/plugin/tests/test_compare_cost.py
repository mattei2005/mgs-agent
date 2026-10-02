import importlib.util
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).parents[1] / 'skills/compare-credit-cost/scripts/compare_cost.py'
spec = importlib.util.spec_from_file_location('compare_cost', SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CompareCostTests(unittest.TestCase):
    def payload(self):
        return {'currency':'BRL', 'amount_received':'1000.00', 'offers':[
            {'label':'A', 'installments':12, 'installment_amount':'100.00', 'upfront_fees':'0.00'},
            {'label':'B', 'installments':10, 'installment_amount':'115.00', 'upfront_fees':'30.00'}]}
    def test_total_and_order(self):
        r=module.compare(self.payload()); self.assertEqual(r['offers'][0]['label'],'B')
        self.assertEqual(r['offers'][0]['total_paid'],'1180.00'); self.assertEqual(r['offers'][0]['cost_above_received'],'180.00')
    def test_decimal_precision(self):
        p=self.payload(); p['offers'][0].update(installments=3, installment_amount='0.10'); self.assertEqual(module.compare(p)['offers'][0]['total_paid'],'0.30')
    def test_zero_fees(self):
        self.assertEqual(module.compare(self.payload())['offers'][1]['total_paid'],'1200.00')
    def test_tie_stable(self):
        p=self.payload(); p['offers'][1].update(installments=12, installment_amount='100.00',upfront_fees='0.00'); self.assertEqual([x['label'] for x in module.compare(p)['offers']],['A','B'])
    def test_other_currency(self):
        p=self.payload(); p['currency']='USD'; self.assertEqual(module.compare(p)['currency'],'USD')
    def test_one_offer_rejected(self):
        p=self.payload(); p['offers']=p['offers'][:1]; self.assertRaises(ValueError,module.compare,p)
    def test_missing_input_rejected(self):
        p=self.payload(); del p['offers'][0]['upfront_fees']; self.assertRaises(ValueError,module.compare,p)
    def test_extra_personal_fields_rejected(self):
        p=self.payload(); p['cpf']='synthetic'; self.assertRaises(ValueError,module.compare,p)
    def test_extra_offer_fields_rejected(self):
        p=self.payload(); p['offers'][0]['token']='synthetic'; self.assertRaises(ValueError,module.compare,p)
    def test_nan_rejected(self):
        p=self.payload(); p['amount_received']='NaN'; self.assertRaises(ValueError,module.compare,p)
    def test_infinity_rejected(self):
        p=self.payload(); p['offers'][0]['installment_amount']='Infinity'; self.assertRaises(ValueError,module.compare,p)
    def test_negative_rejected(self):
        p=self.payload(); p['offers'][0]['upfront_fees']='-1.00'; self.assertRaises(ValueError,module.compare,p)
    def test_bool_count_rejected(self):
        p=self.payload(); p['offers'][0]['installments']=True; self.assertRaises(ValueError,module.compare,p)
    def test_zero_received_rejected(self):
        p=self.payload(); p['amount_received']='0.00'; self.assertRaises(ValueError,module.compare,p)
    def test_fractional_cent_rejected(self):
        p=self.payload(); p['amount_received']='1000.001'; self.assertRaises(ValueError,module.compare,p)
    def test_duplicate_labels_rejected(self):
        p=self.payload(); p['offers'][1]['label']='A'; self.assertRaises(ValueError,module.compare,p)
    def test_floating_input_rejected(self):
        p=self.payload(); p['amount_received']=1000.0; self.assertRaises(ValueError,module.compare,p)
    def test_bad_currency_rejected(self):
        p=self.payload(); p['currency']='BRL/USD'; self.assertRaises(ValueError,module.compare,p)

if __name__=='__main__': unittest.main()
