import copy,json,os,sys,tempfile,unittest,fcntl
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3 import shein_external_block_coordination as e,shein_request_queue as q,shein_decision_wait as w,shein_manual_takeover as manual,shein_single_clone as driver,shein_channel_authority as authority

class ExternalCoordinationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR','/root/.hermes/profiles/ares/cache/scratch'));self.base=Path(self.temp.name);self.account='937846586033361';self.oldid='test-old';self.newid='test-new'
  self.request={'request_id':self.newid,'account':self.account,'authorized_by':'1055570806945620030','source_channel_id':'1548150155184701440','source_thread_id':'1558134703565967394','budget_usd':'35','quantity':15,'mode':'clone_prestaged','campaign_groups':[{'files':['new.mp4']}],'start_time':'2026-11-18T00:15:00-05:00'}
  self.old={'request':{**self.request,'request_id':self.oldid},'phase':'POSTPROCESS_PENDING','engine_result':{'status':'COMPLETE_PAUSED','request_id':self.oldid,'campaign_ids':['100']},'manifest':{'campaigns':[{'account_id':self.account,'status':'PAUSED','ads':[{'media':{'video_id':'10'}}]}]},'media_qa':{'100':{'verified':True}}}
  self.live=[{'id':'100','name':'old','daily_budget':'6500','bid_strategy':'COST_CAP','start_time':'2026-11-17T00:05:00-0500','status':'PAUSED','effective_status':'PAUSED','adsets':[{'id':'110','status':'ACTIVE','effective_status':'CAMPAIGN_PAUSED','bid_amount':90,'start_time':'2026-11-17T00:05:00-0500'}],'ads':[{'id':'120','adset_id':'110','creative_id':'130','status':'PAUSED','effective_status':'WITH_ISSUES','issue_codes':[2490468],'ad_review_feedback':{},'primary_media':[['identity','10']]}]}]
  self.selected=[{'asset_id':'new-asset','canonical_filename':'new.mp4','video_id':'20'}]
  self.root=q.root(self.base);self.engine=self.base/'data/ares/meta-ads/engine-v3/state';self.jobdir=self.root/'queue/jobs'
  for rid in [self.oldid,self.newid]:q.atomic(q.job_path(self.base,rid),{'request_id':rid,'request':self.request if rid==self.newid else self.old['request'],'status':'FOREGROUND_OWNED','dispatch_owner':'foreground'})
  q.atomic(self.root/'single-clone'/self.oldid/'state.json',self.old);q.atomic(self.root/'single-clone'/self.oldid/'manifest-sealed.json',self.old['manifest']);q.atomic(self.engine/'checkpoints'/(self.oldid+'-'+self.account+'.json'),{'account_id':self.account,'status':'COMPLETE','campaign_ids':['100'],'manual_reconciliation_required':False})
  q.atomic(self.engine/'writer-leases'/(self.account+'.json'),{'account_id':self.account,'status':'COMPLETE','blocks_readers':False,'released_at_utc':'now'})
  policy={'scope':{'parent_channel_id':self.request['source_channel_id'],'account_ids':[self.account],'approver_ids':['344196393512075265','1055570806945620030']},'receipts':{}}
  q.atomic(self.base/e.POLICY,policy);q.atomic(self.base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json',{'profiles':{self.account:{}}});q.atomic(self.base/'data/ares/meta-ads/engine-v3/config.json',{'state_root':str(self.engine),'accounts':{self.account:{'token_item':'fake'}}})
  inv=self.base/'data/ares/creative-ops/inventory/assets.jsonl';inv.parent.mkdir(parents=True,exist_ok=True);inv.write_text('\n'.join(json.dumps(v) for v in self.selected))
  self.msg={'id':'99999999999999999','author':{'id':'344196393512075265'},'channel_id':self.request['source_thread_id'],'content':'Approved coordination only'}
  self.patches=[patch.object(authority,'_get',return_value=self.msg),patch.object(authority,'verify',return_value={'verified':True}),patch.object(q,'selected',side_effect=lambda *a:copy.deepcopy(self.selected)),patch.object(driver,'_load_common',return_value=Mock(get_token_from_1password=Mock(return_value=('SENTINEL','f')))),patch.object(e,'capture_live',side_effect=lambda *a:copy.deepcopy(self.live))]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def create(self):return e.reconcile(self.base,self.oldid,self.request,self.msg['id'])
 def test_positive_idempotence_no_old_mutation(self):
  before=e.pins(self.base,self.oldid,self.account);first=self.create();second=self.create();self.assertEqual(first,second);self.assertEqual(before,e.pins(self.base,self.oldid,self.account));self.assertFalse(first['qa_certified']);self.assertFalse(first['reservation_release']);self.assertEqual(q.dependencies(self.request,self.account,self.base),[]);self.assertTrue(w.pending(self.base,self.oldid))
 def test_predecessor_replay_fenced_engine_and_runner(self):
  self.create()
  with self.assertRaises(ValueError):manual.deny_replay(self.base,self.oldid)
  with self.assertRaises(ValueError):manual.deny_engine_replay(self.engine,self.oldid)
 def test_unauthorized_approval(self):
  self.msg['author']['id']='666'
  with self.assertRaises(ValueError):self.create()
 def test_permission_missing(self):
  authority.verify.side_effect=ValueError('no permission')
  with self.assertRaises(ValueError):self.create()
 def test_shared_media(self):
  self.selected[0]['video_id']='10'
  with self.assertRaises(ValueError):self.create()
 def test_reserved_media(self):
  self.selected[0]['reservation_request_id']='other'
  with self.assertRaises(ValueError):self.create()
 def test_busy_lease(self):
  q.atomic(self.engine/'writer-leases'/(self.account+'.json'),{'account_id':self.account,'status':'IN_PROGRESS','blocks_readers':True,'request_id':'other'})
  with self.assertRaises(ValueError):self.create()
 def test_account_lock(self):
  p=self.root/'single-clone'/('account-'+self.account+'.lock')
  with p.open('a+') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaises(BlockingIOError):self.create()
 def test_corrupt_receipt_still_fences(self):
  self.create();e.path(self.base,self.oldid).write_text('{}')
  with self.assertRaises(ValueError):e.validate(self.base,self.old,resume_request=self.request)
  with self.assertRaises(ValueError):manual.deny_replay(self.base,self.oldid)
 def test_no_grant(self):
  self.create();policy=e.read(self.base/e.POLICY);policy['receipts']={};q.atomic(self.base/e.POLICY,policy)
  with self.assertRaises(ValueError):e.validate(self.base,self.old,resume_request=self.request)
 def test_pin_changed(self):
  self.create();old=copy.deepcopy(self.old);old['phase']='COMPLETE';q.atomic(self.root/'single-clone'/self.oldid/'state.json',old)
  with self.assertRaises(ValueError):e.validate(self.base,old,resume_request=self.request)
 def test_successor_budget_quantity_time_and_other_id(self):
  self.create()
  for key in ['budget_usd','quantity','start_time','request_id','source_channel_id','account']:
   altered=copy.deepcopy(self.request);altered[key]='changed'
   with self.assertRaises(ValueError):e.validate(self.base,self.old,resume_request=altered)
 def test_internal_preparation_additions_allowed(self):
  self.create();ready=copy.deepcopy(self.request);ready['asset_refs']=['new-asset'];ready['campaign_groups'][0]['asset_refs']=['new-asset'];self.assertTrue(e.validate(self.base,self.old,resume_request=ready))
 def test_live_drift_budget_bid_media_and_terminals(self):
  self.create()
  mutations=[lambda x:x[0].update(daily_budget='1'),lambda x:x[0]['adsets'][0].update(bid_amount=1),lambda x:x[0]['ads'][0].update(primary_media=[['identity','99']]),lambda x:x[0]['ads'][0].update(creative_id='99'),lambda x:x[0].update(status='DELETED')]
  for change in mutations:
   previous=copy.deepcopy(self.live);change(self.live)
   with self.assertRaises(ValueError):e.verify_live(self.base,self.old,resume_request=self.request)
   self.live=previous
 def test_mutable_external_delivery_not_qa(self):
  self.create();self.live[0]['status']='ACTIVE';self.live[0]['ads'][0].update(status='ACTIVE',effective_status='ACTIVE',issue_codes=[]);self.assertTrue(e.verify_live(self.base,self.old,resume_request=self.request));self.assertFalse(e.validate(self.base,self.old)['qa_certified'])
 def test_other_successor_cannot_borrow_grant(self):
  self.create();altered={**self.request,'request_id':'another'};self.assertFalse(w.inert_for(altered,self.old,self.selected,self.base))
 def test_shared_media_after_registration_blocks_dependencies(self):
  self.create();self.selected[0]['video_id']='10';self.assertEqual(q.dependencies(self.request,self.account,self.base),[self.oldid])
 def test_replay_worker_pending_without_subprocess(self):
  self.create();job=e.read(q.job_path(self.base,self.oldid))
  with patch.object(q.subprocess,'run',side_effect=AssertionError('writer reached')):q._tick_locked(job,self.base)

 def next_successor(self,terminal=True):
  self.create()
  q.atomic(self.root/'single-clone'/self.newid/'state.json',{'request':copy.deepcopy(self.request),'phase':'COMPLETE_FUTURE_ACTIVE' if terminal else 'POSTPROCESS_PENDING','summary':{'campaigns':[{'id':'200'}]} if terminal else {}})
  request={**copy.deepcopy(self.request),'request_id':'test-next'}
  q.atomic(q.job_path(self.base,request['request_id']),{'request_id':request['request_id'],'request':request,'status':'FOREGROUND_OWNED','maintenance_hold':True})
  self.msg.update(id='99999999999999998',author={'id':'1055570806945620030'},content='OK separate request coordination')
  return request
 def test_additional_successor_separate_receipt_no_replacement(self):
  request=self.next_successor();original=e.path(self.base,self.oldid).read_bytes();grant=copy.deepcopy(e.read(self.base/e.POLICY)['receipts']);before=e.pins(self.base,self.oldid,self.account)
  first=e.reconcile(self.base,self.oldid,request,self.msg['id']);second=e.reconcile(self.base,self.oldid,request,self.msg['id'])
  self.assertEqual(first,second);self.assertEqual(original,e.path(self.base,self.oldid).read_bytes());self.assertEqual(grant,e.read(self.base/e.POLICY)['receipts']);self.assertEqual(before,e.pins(self.base,self.oldid,self.account));self.assertEqual(q.dependencies(request,self.account,self.base),[])
  self.assertEqual(e.validate(self.base,self.old)['successor_request'],self.request);self.assertEqual(e.validate(self.base,self.old,resume_request=request)['successor_request'],request)
  with self.assertRaises(ValueError):manual.deny_replay(self.base,self.oldid)
 def test_additional_successor_requires_terminal_parent(self):
  request=self.next_successor(terminal=False)
  with self.assertRaisesRegex(ValueError,'previous successor not terminal'):e.reconcile(self.base,self.oldid,request,self.msg['id'])
 def test_additional_successor_cannot_reuse_old_approval(self):
  request=self.next_successor();self.msg['id']='99999999999999999'
  with self.assertRaisesRegex(ValueError,'fresh successor approval'):e.reconcile(self.base,self.oldid,request,self.msg['id'])
 def test_additional_successor_grant_missing_fails_closed(self):
  request=self.next_successor();e.reconcile(self.base,self.oldid,request,self.msg['id']);policy=e.read(self.base/e.POLICY);policy['successor_receipts']={};q.atomic(self.base/e.POLICY,policy)
  with self.assertRaises(ValueError):e.validate(self.base,self.old,resume_request=request)
 def test_additional_successor_digest_and_parent_pins(self):
  request=self.next_successor();e.reconcile(self.base,self.oldid,request,self.msg['id']);p=e.successor_path(self.base,self.oldid,request['request_id']);saved=p.read_bytes();p.write_text('{}')
  with self.assertRaises(ValueError):e.validate(self.base,self.old,resume_request=request)
  p.write_bytes(saved);e.path(self.base,self.oldid).write_text('{}')
  with self.assertRaises(ValueError):e.validate(self.base,self.old,resume_request=request)
 def test_additional_successor_material_change_rejected(self):
  request=self.next_successor();e.reconcile(self.base,self.oldid,request,self.msg['id'])
  for key in ['budget_usd','quantity','start_time','account','source_channel_id']:
   changed={**request,key:'changed'}
   with self.assertRaises(ValueError):e.validate(self.base,self.old,resume_request=changed)
 def test_additional_successor_shared_or_reserved_media(self):
  request=self.next_successor();self.selected[0]['video_id']='10'
  with self.assertRaises(ValueError):e.reconcile(self.base,self.oldid,request,self.msg['id'])
  self.selected[0].update(video_id='20',reservation_request_id='foreign')
  with self.assertRaises(ValueError):e.reconcile(self.base,self.oldid,request,self.msg['id'])
 def test_additional_successor_own_resume_lease(self):
  request=self.next_successor();e.reconcile(self.base,self.oldid,request,self.msg['id'])
  q.atomic(self.root/'single-clone'/request['request_id']/'state.json',{'request':request,'phase':'POSTPROCESS_PENDING'})
  q.atomic(self.engine/'writer-leases'/(self.account+'.json'),{'account_id':self.account,'request_id':request['request_id'],'status':'RECOVERY_PENDING','blocks_readers':True})
  self.assertTrue(e.validate(self.base,self.old,resume_request=request));self.assertTrue(e.verify_live(self.base,self.old,resume_request=request))

if __name__=='__main__':unittest.main()
