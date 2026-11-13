#!/usr/bin/env python3
"""Synthetic, no external calls: H source/authority and native search bounds."""
import ast,copy,importlib.util,json,pathlib,tempfile,unittest
S=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pub',S/'publish_pay_now.py');pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
class SourceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch');self.addCleanup(self.tmp.cleanup);b=pathlib.Path(self.tmp.name);(b/'pixel.png').write_bytes(b'not-an-image-synthetic-existence-fixture');(b/'text.txt').write_text('Synthetic account ID: 10000000 Active Credit line $12.34\n')
  self.target={'account_id':'10000000','name':'Synthetic account'};self.c={'business_id':'155263197283282','authorization_messages':['1570815017794674749'],'h_source':'accounts_list_outstanding_balance'}
  self.r={'account_id':'10000000','business_id':self.c['business_id'],'payments_executed':0,'status':'accounts_list_outstanding_balance_read','name':'Synthetic account','amount':'12.34','read_at':'2026-11-13T00:00:00-05:00','screenshot':str(b/'pixel.png'),'text_path':str(b/'text.txt')}
  self.v={'accounts_list_checks':{'10000000':{'valid_billing_list':True,'business_id':self.c['business_id'],'row_account_id':'10000000','name':'Synthetic account','balance_usd':'12.34','balance_label':'Outstanding balance','authority_message_id':'1570815017794674749'}}}
 def call(self):return pub.verified_entry(self.r,self.target,self.c,self.v,'synthetic-fixture-only')
 def test_source(self):self.assertEqual(self.call()['source'],'accounts_list_outstanding_balance')
 def test_authority(self):
  self.c['authorization_messages']=[]
  with self.assertRaises(AssertionError):self.call()
 def test_policy(self):
  self.c['h_source']='accounts_list_current_balance'
  with self.assertRaises(AssertionError):self.call()
 def test_label(self):
  self.v['accounts_list_checks']['10000000']['balance_label']='Current balance'
  with self.assertRaises(AssertionError):self.call()
 def test_visual_authority(self):
  self.v['accounts_list_checks']['10000000']['authority_message_id']='old'
  with self.assertRaises(AssertionError):self.call()
 def test_amount(self):
  self.v['accounts_list_checks']['10000000']['balance_usd']='12.35'
  with self.assertRaises(AssertionError):self.call()
 def test_name(self):
  self.v['accounts_list_checks']['10000000']['name']='Other'
  with self.assertRaises(AssertionError):self.call()
 def test_id(self):
  self.v['accounts_list_checks']['10000000']['row_account_id']='99999999'
  with self.assertRaises(AssertionError):self.call()
 def test_native_coordinates_ignore_estimated_scale(self):
  tree=ast.parse((S/'read_pc1_accounts_list.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='search_pixel_point');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<synthetic-extract>','exec'),ns)
  f=ns['search_pixel_point'];self.assertEqual(f({'bounds':[448,378,1967,20]},{'width':2558,'height':1390,'bounds_scale':1.5}),[628,388])
  with self.assertRaises(AssertionError):f({'bounds':[448,2000,1967,20]},{'width':2558,'height':1390,'bounds_scale':1.5})
if __name__=='__main__':unittest.main()
