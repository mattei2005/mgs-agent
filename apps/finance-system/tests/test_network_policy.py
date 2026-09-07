"""Network changes: real snapshot in isolated calculation, never production facts."""
import unittest,json,pathlib,copy
from decimal import Decimal as D
from worker import run
ROOT=pathlib.Path(__file__).resolve().parents[1]
class NetworkTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.base=run({})
 def test_site_network_drives_invalid_and_share(self):
  site=next(s for s in self.base['domain']['site_catalog'] if s['name']=='GameZoneAd')
  changes=[{'kind':'site','id':site['id'],'name':site['name'],'new':False,'status':site['status'],'network':'SB Rede2'}]
  result=run({'additions':changes,'overrides':{'network|monthly|SB_REDE2_INVALID':'.02'}})
  facts=[f for f in result['domain']['facts'] if f['site']==site['name']]
  self.assertTrue(facts)
  self.assertTrue(all(f['partner']=='SB Rede2' and D(f['invalid_rate'])==D('.02') for f in facts))
  self.assertTrue(all(abs(D(f['invalid'])+D(f['gross'])*D('.02'))<D('1e-15') for f in facts if f['gross']!=''))
  others=[f for f in result['domain']['facts'] if f['site']=='FinanceAdx']
  self.assertTrue(all(D(f['invalid_rate'])==D('.004104') for f in others))
  self.assertEqual(result['summary']['counts'].get('error',0),0)
 def test_network_change_uses_m2_share_and_preserves_input(self):
  site=next(s for s in self.base['domain']['site_catalog'] if s['name']=='Eggbev')
  row={'kind':'site','id':site['id'],'name':site['name'],'new':False,'status':site['status'],'network':'M2'}
  result=run({'additions':[row]})
  facts=[f for f in result['domain']['facts'] if f['site']=='Eggbev']
  self.assertTrue(all(f['partner']=='M2' and D(f['share_rate'])==D('.05') for f in facts))
  before={f['id']:f['gross'] for f in self.base['domain']['facts']}
  self.assertTrue(all(before[f['id']]==f['gross'] for f in result['domain']['facts']))
 def test_unknown_network_rejected(self):
  site=self.base['domain']['site_catalog'][0]
  with self.assertRaisesRegex(ValueError,'[Rr]ede|[Nn]etwork'):
   run({'additions':[{'kind':'site','id':site['id'],'new':False,'status':site['status'],'network':'UNKNOWN'}]})
if __name__=='__main__':unittest.main()
