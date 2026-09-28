import json,unittest,copy
from pathlib import Path
from decimal import Decimal as D
from worker import run
from gross_pairs import total,index
ROOT=Path(__file__).resolve().parents[1]
class GrossPairs(unittest.TestCase):
 def test_decimal_and_invalid_scope(self):
  self.assertEqual(total({'cad':'10','usd':'2'},'1.4'),D(10)/D('1.4')+D(2))
  self.assertEqual(total({'cad':'0.004317552897398294','usd':'13.91'},'1.4'),D('0.004317552897398294')/D('1.4')+D('13.91'))
  with self.assertRaises(ValueError):index([{'kind':'gross_pair','period':'2026-08','target_type':'input','target':'x','cad':'1','usd':'2'}],'2026-09')
 def test_legacy_pair_all_months_and_manager_propagation(self):
  for period in ['2026-08','2026-09','2027-02']:
   base={'period':period,'overrides':{'principal|Agosto 2026|H1':'1.4'},'additions':[]};saved=copy.deepcopy(base);before=run(base)
   pair={'kind':'gross_pair','id':'test-pair','period':period,'target_type':'input','target':'principal|Agosto 2026|KU22','cad':'10','usd':'2'}
   after=run({**base,'additions':[pair]});self.assertEqual(base,saved);self.assertEqual(after['summary']['counts'].get('error',0),0)
   b=next(f for f in before['domain']['facts'] if f['site']=='Eggbev' and f['country']=='US' and f['date']==period+'-18');a=next(f for f in after['domain']['facts'] if f['id']==b['id']);expected=D(10)/D('1.4')+D(2)
   self.assertLess(abs(D(a['gross'])-expected),D('1e-20'));self.assertEqual(a['gross_origins'],{'CAD':D(10),'USD':D(2)})
   self.assertEqual(after['domain']['cash']['spend'],before['domain']['cash']['spend'])
   self.assertLess(abs(D(after['domain']['cash']['gross'])-D(before['domain']['cash']['gross'])-(expected-D(b['gross'] or 0))),D('1e-18'))
   old=next(m for m in before['domain']['managers'] if m['manager']=='nicolas' and m['row']==12);new=next(m for m in after['domain']['managers'] if m['manager']=='nicolas' and m['row']==12)
   self.assertLess(abs(D(new['profit'])-D(old['profit'])-(D(a['profit'])-D(b['profit']))),D('1e-18'))
 def test_native_pair_not_duplicate(self):
  addition={'id':'synthetic-native','date':'2026-09-18','site':'Synthetic fixture','country':'US','manager':'nicolas','partner':'AV','currency':'USD','gross':'2','spend':'3','quotes':{'USDCAD':'1.4','USDBRL':'5','GBPUSD':'1.2'},'invalid_rate':'0','share_rate':'0','tax_rate':'0'}
  p={'period':'2026-09','overrides':{'principal|Agosto 2026|H1':'1.4'},'additions':[addition]};b=run(p);pair={'kind':'gross_pair','id':'test-native-pair','period':'2026-09','target_type':'entry','target':addition['id'],'cad':'10','usd':'2'};a=run({**p,'additions':[addition,pair]})
  self.assertEqual(len(a['domain']['facts']),len(b['domain']['facts']));self.assertEqual(a['domain']['cash']['spend'],b['domain']['cash']['spend']);f=next(f for f in a['domain']['facts'] if f['id']==addition['id']);self.assertEqual(f['gross_origins'],{'CAD':D(10),'USD':D(2)});self.assertLess(abs(D(f['gross'])-(D(10)/D('1.4')+D(2))),D('1e-20'))
if __name__=='__main__':unittest.main()
