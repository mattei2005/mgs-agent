"""Whole-batch completion: pure proof and missing-only stock retry boundaries."""
import copy,json,unittest
from pathlib import Path
import test_eggbev_cross_account_clone as fixtures

class CompletionTests(unittest.TestCase):
 def setUp(self):
  self.base=fixtures.CrossTests('test_14_real_engine_five_campaigns_fifteen_ads_fifteen_seeds');self.base.setUp();self.addCleanup(self.base.doCleanups)
  b=self.base;fake=b.fake();self.fake=fake;m=b.manifest();engine=b.engine(fake)
  with b.admitted(m):self.result=engine.execute(m)
  self.payload=json.loads((Path(b.cfg['audit_root'])/(m.request_id+'.json')).read_text()).get('manifest')
  from ares_campaign_v3.prevalidation import prevalidate_payload
  self.payload=prevalidate_payload(b.draft(),b.reg)
  self.checkpoint=json.loads((Path(b.cfg['state_root'])/'checkpoints'/(m.request_id+'-'+b.c.TARGET+'.json')).read_text())
  self.records=copy.deepcopy([r for r in self.checkpoint['bundles'] if r.get('status')=='COMPLETE'])
 def prove(self):
  from ares_campaign_v3.eggbev_cross_account_completion import completion_proof
  return completion_proof(self.base.q,self.payload,self.checkpoint,self.records,self.base.assets)
 def test_complete_five_fifteen_and_paused_seeds(self):
  p=self.prove();self.assertEqual(len(p['campaign_ids']),5);self.assertEqual(len(p['assignments']),15);self.assertEqual(len({a['ad_id'] for a in p['assignments']}),15);self.assertEqual(len(p['technical_seed_ids']),15)
 def test_empty_or_partial_is_not_complete(self):
  self.records=[]
  with self.assertRaises(ValueError):self.prove()
 def test_missing_slot_rejected(self):
  self.records[0]['target_clone_ids'].pop('copied_ad_id_1_1')
  with self.assertRaises((ValueError,KeyError)):self.prove()
 def test_postprocessing_never_infers_equivalent_video(self):
  rows=self.records[0]['readback_results'];row=next(x for x in rows if x['name']=='readback_ads_1')
  for a in row['body']['data']:
   if a.get('status')=='ACTIVE':a['creative']['asset_feed_spec']['videos'][0]['video_id']='7777777';break
  with self.assertRaises(ValueError):self.prove()
 def test_hard_issue_keeps_completion_pending(self):
  row=next(x for x in self.records[0]['readback_results'] if x['name']=='readback_ads_1')
  row['body']['data'][0]['issues_info']=[{'error_code':2446386}]
  with self.assertRaises(ValueError):self.prove()
 def test_seed_activation_rejected(self):
  row=next(x for x in self.records[0]['readback_results'] if x['name']=='readback_ads_1')
  for a in row['body']['data']:
   if a.get('status')=='PAUSED':a['status']='ACTIVE';break
  with self.assertRaises(ValueError):self.prove()
 def test_input_and_proofs_immutable(self):
  before=copy.deepcopy((self.payload,self.checkpoint,self.records));self.prove();self.assertEqual(before,(self.payload,self.checkpoint,self.records))
 def finalize_context(self,stock):
  from contextlib import ExitStack
  from unittest.mock import patch,Mock
  from ares_campaign_v3 import eggbev_cross_account_completion as completion,eggbev_creation_naming as naming,transport
  import ares_manager_storage_standard as standard
  b=self.base;home=b.root/'completion';home.mkdir(exist_ok=True)
  inv=home/'inventory.jsonl';inv.write_text(''.join(json.dumps({**a,'reservation_request_id':b.q['request_id']})+'\n' for a in b.assets))
  summary={'names':b.allocation['names'],'start_time':b.start,'digest':self.payload['prevalidation']['content_digest']}
  for name,value in [('summary.json',summary),('engine-result.json',self.result),('source-live.json',b.source),('target-page-live.json',b.page),('selected-assets.json',b.assets)]:b.m.save(home/name,value)
  ledger=home/'ledger.json';b.m.save(ledger,{'allocations':{b.q['request_id']:copy.deepcopy(b.allocation)}})
  cfg=home/'config.json';b.m.save(cfg,b.cfg)
  stack=ExitStack();self.addCleanup(stack.close)
  for obj,key,value in [(b.c,'request_load',lambda p:b.q),(b.c,'home_for',lambda q:home),(b.c,'runtime',lambda r,cfg:(Mock(),Mock(),Mock(),'fake-token')),(b.c,'verify_advertiser',lambda *a:None),(b.c,'live_request',lambda *a:None),(b.c,'final_approval',lambda *a:self.payload),(b.c,'page_read',lambda *a:b.page),(b.m,'CONFIG',cfg),(b.m,'INVENTORY',inv),(naming,'load_policy',lambda:{'ledger_path':str(ledger)}),(transport,'GraphBatchTransport',lambda *a:self.fake),(standard,'confirm_usage',stock)]:stack.enter_context(patch.object(obj,key,value))
  return completion,home,ledger,inv
 def test_finalize_stock_partial_then_missing_only_retry(self):
  calls=[];fail=[True]
  def stock(asset_id,request_id,apply):
   calls.append(asset_id)
   if fail[0] and len(calls)==3:raise ValueError('simulated stock interruption')
   return {'status':'verified','same_ids':True,'asset_id':asset_id}
  module,home,ledger,inv=self.finalize_context(stock)
  before=len([c for c in self.fake.calls if c[2]=='POST'])
  with self.assertRaisesRegex(ValueError,'stock interruption'):module.finalize('unused',self.base.m,'digest','approval')
  self.assertNotEqual(json.loads(ledger.read_text())['allocations'][self.base.q['request_id']].get('status'),'COMMITTED')
  self.assertFalse((home/'final.json').exists());fail[0]=False
  result=module.finalize('unused',self.base.m,'digest','approval')
  self.assertEqual(result['phase'],'COMPLETE');self.assertEqual(len(result['assignments']),15)
  self.assertEqual(json.loads(ledger.read_text())['allocations'][self.base.q['request_id']]['status'],'COMMITTED')
  self.assertEqual(before,len([c for c in self.fake.calls if c[2]=='POST']))
 def test_finalize_refuses_unverified_stock_receipt(self):
  module,home,ledger,inv=self.finalize_context(lambda *a,**k:{'status':'queued'})
  with self.assertRaisesRegex(ValueError,'stock receipt incomplete'):module.finalize('unused',self.base.m,'digest','approval')
  self.assertFalse((home/'final.json').exists())
 def test_source_blank_body_preserved(self):
  self.assertEqual(self.base.c.primary_text({'asset_feed_spec':{'bodies':[{'text':''}]}}),'')

if __name__=='__main__':unittest.main()
