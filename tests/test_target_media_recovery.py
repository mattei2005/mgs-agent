"""OFFLINE ONLY. Real 3-slot snapshots plus owner GET-only supplement.
Every positive fixture field comes from stored Graph GETs, never manifest values.
No API writes; transport/crash simulations remain explicitly test doubles.
"""
import copy,hashlib,importlib.util,json,os,socket,sys,tempfile,unittest
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_53c187db'
sys.path[:0]=[str(R/'scripts')]
import ares_campaign_v3
if 'ares_campaign_v3.target_media_recovery' not in sys.modules:
 p=R/'scripts/ares_campaign_v3/target_media_recovery.py'
 if not p.exists():p=M/'target_media_recovery.py'
 spec=importlib.util.spec_from_file_location('ares_campaign_v3.target_media_recovery',p);rec=importlib.util.module_from_spec(spec);sys.modules[spec.name]=rec;spec.loader.exec_module(rec)
else:rec=sys.modules['ares_campaign_v3.target_media_recovery']
G=rec.load(rec.GRANT_PATH);H=Path(G['request_path']).parent
PAYLOAD=rec.load(H/'manifest.json');SELECTED=rec.load(H/'selected-assets.json');SNAP=rec.load(H/'owner-attempt5-live-readback.json');PROOF=rec.load(G['proof_path'])
def runner_load():
 p=R/'scripts/ares-eggbev-target-clone.py'
 if os.environ.get('TARGET_MEDIA_CANDIDATE')=='1':p=M/'ares-eggbev-target-clone.py'
 spec=importlib.util.spec_from_file_location('recovery_test_runner',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

def full_fixture():
 s=copy.deepcopy(SNAP)
 supplement=rec.load(H/'origin-supplemental-live-readback-20261115T063608Z.json')
 assert supplement['request_id']==G['request_id'] and supplement['meta_writes']==0
 for section,target in [('campaign',s['campaign']),('adset',s['adsets'][0])]:
  row=supplement[section];assert row['http_status']==200 and target['id']==row['body']['id']
  for k,v in row['body'].items():
   if k in target:
    if k=='start_time':assert datetime.fromisoformat(target[k])==datetime.fromisoformat(v)
    else:assert target[k]==v,(k,target[k],v)
   else:target[k]=copy.deepcopy(v)
 return s

class MediaTests(unittest.TestCase):
 def setUp(self):
  self.p=copy.deepcopy(PAYLOAD);self.s=full_fixture();self.g=copy.deepcopy(G);self.a=copy.deepcopy(SELECTED)
 def check(self,state='PAUSED'):
  return rec.semantic(self.p,self.g['ids'],self.a,self.s,self.g['pairs'],state)
 def test_01_three_real_slots_six_pairs_no_raw_mutation(self):
  before=copy.deepcopy(self.s);p=self.check();self.assertEqual(6,len(p));self.assertEqual(before,self.s);rec.rendered(self.g,self.g['ids'],p)
 def test_02_original_comparator_active_expectations_only(self):
  self.s['campaign']['status']='ACTIVE';self.assertEqual(6,len(self.check('ACTIVE')))
 def test_03_original_snapshot_rejects_missing_live_fields(self):
  self.s=copy.deepcopy(SNAP)
  with self.assertRaises(ValueError):self.check()
 def test_04_local_real_original_grant_journal(self):
  runner=runner_load();g,cfg,q,p=rec.local(H/'request.json',runner,G['original_approved_digest'],G['approval_message_id']);self.assertEqual(11,len(g['ids']))
 def test_05_wrong_approval(self):
  with self.assertRaises(ValueError):rec.grant_load(H/'request.json',G['original_approved_digest'],'1')
 def test_06_wrong_digest(self):
  with self.assertRaises(ValueError):rec.grant_load(H/'request.json','0'*64,G['approval_message_id'])
 def test_07_other_path(self):
  with self.assertRaises(ValueError):rec.grant_load(H/'other.json',G['original_approved_digest'],G['approval_message_id'])
 def test_08_expired_clock(self):
  for dt in [-601,1]:
   now=datetime.now(timezone.utc)
   with self.assertRaises(ValueError):rec.fresh((now+timedelta(seconds=dt)).isoformat(),now)
 def test_09_naive_clock(self):
  with self.assertRaises(ValueError):rec.fresh('2026-11-15T00:00:00')
 def test_10_ready_metadata_all_twelve(self):
  ps=self.check()
  for p in ps:
   for vid in [p['expected_video_id'],p['observed_video_id']]:
    d=next(x for x in PROOF['downloads'] if x['video_id']==vid)
    v={k:d[k] for k in ['title','length','status']} if 'status' in d else {'title':d['title'],'length':d['length'],'status':{'video_status':'ready',**{k:{'status':'complete'} for k in ['uploading_phase','processing_phase','publishing_phase']}}}
    v['id']=vid;self.assertEqual(d,rec.validate_video(v,p,PROOF))
 def test_11_all_twelve_real_downloads_and_36_decoded_frames(self):
  for d in PROOF['downloads']:rec.inspect_bytes(Path(d['path']).read_bytes(),d)
 def test_12_bad_bytes(self):
  d=PROOF['downloads'][0]
  with self.assertRaises(ValueError):rec.inspect_bytes(Path(d['path']).read_bytes()+b'X',d)
 def test_13_bad_frame_hash(self):
  d=copy.deepcopy(PROOF['downloads'][0]);d['frames'][0]['sha256']='0'*64
  with self.assertRaises(ValueError):rec.inspect_bytes(Path(d['path']).read_bytes(),d)
 def test_14_bad_dimensions(self):
  d=copy.deepcopy(PROOF['downloads'][0]);d['width']=1
  with self.assertRaises(ValueError):rec.inspect_bytes(Path(d['path']).read_bytes(),d)
 def test_15_wrong_title(self):
  p=self.check()[0];d=PROOF['downloads'][0];v={'id':d['video_id'],'title':'wrong','length':d['length'],'status':{}}
  with self.assertRaises(ValueError):rec.validate_video(v,p,PROOF)
 def test_16_not_ready(self):
  p=self.check()[0];d=PROOF['downloads'][0];v={'id':d['video_id'],'title':d['title'],'length':d['length'],'status':{'video_status':'processing'}}
  with self.assertRaises(ValueError):rec.validate_video(v,p,PROOF)
 def test_17_rendered_missing(self):
  with patch.object(rec,'load',return_value={'verified':True,'rendered_media':[]}):
   with self.assertRaises(ValueError):rec.rendered(self.g,self.g['ids'],self.check())
 def test_18_url_ssrf_and_redirect_shape(self):
  for u in ['http://localhost/a.mp4','https://127.0.0.1/a.mp4','https://scontent-a.xx.fbcdn.net:443/a.mp4','https://evil.test/a.mp4','https://scontent-a.xx.fbcdn.net/a.html']:
   with self.assertRaises(ValueError):rec.fetch_video(u)
 def test_19_inventory_actual_vertical_and_lineage(self):
  ps=self.check();a=rec.assignments_for(ps,self.s,self.a,self.g['ids']);self.assertEqual(3,len(a))
  for row in a:self.assertNotEqual(next(p['expected_video_id'] for p in ps if p['asset_id']==row['asset_id'] and p['variant']=='vertical'),row['video_id']);self.assertEqual(2,len(row['media_lineage']))
 def test_20_immutable_receipt_collision(self):
  with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as d:
   p=Path(d)/'r.json';rec.missing(p,{'x':1});rec.missing(p,{'x':1})
   with self.assertRaises(ValueError):rec.missing(p,{'x':2})
 def test_21_link_missing_only_and_backup(self):
  with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as d:
   p=Path(d)/'r.json';b=Path(d)/'b.json';rec.atomic(p,{'error':'preserved'});rec.cas_link(p,'link',{'id':1},b);rec.cas_link(p,'link',{'id':1},b);self.assertEqual({'error':'preserved'},rec.load(b))
   with self.assertRaises(ValueError):rec.cas_link(p,'link',{'id':2},b)

def mutation_test(name,mutate):
 def test(self):
  mutate(self)
  with self.assertRaises((ValueError,KeyError,StopIteration)):self.check()
 test.__name__='test_negative_'+name;setattr(MediaTests,test.__name__,test)
first=lambda x:next(a for a in x.s['ads'] if a['id']==x.g['ids']['copied_ad_id_1_1'])
mutations={
 'missinglabel':lambda x:first(x)['creative']['asset_feed_spec']['videos'][0].pop('adlabels'),
 'tamperedvideoid':lambda x:first(x)['creative']['asset_feed_spec']['videos'][0].update(video_id='123'),
 'wrongcreativeid':lambda x:first(x)['creative'].update(id='123'),
 'wrongassetid':lambda x:x.a[0].update(asset_id='other'),
 'missingpair':lambda x:x.g['pairs'].pop(),
 'duplicatepair':lambda x:x.g['pairs'].__setitem__(1,copy.deepcopy(x.g['pairs'][0])),
 'extraad':lambda x:x.s['ads'].append(copy.deepcopy(x.s['ads'][0])),
 'missingseed':lambda x:x.s['ads'].pop(),
 'parentactive':lambda x:x.s['campaign'].update(status='ACTIVE'),
 'parentbudget':lambda x:x.s['campaign'].update(daily_budget='9999'),
 'parentaccount':lambda x:x.s['campaign'].update(account_id='123'),
 'event':lambda x:x.s['adsets'][0]['promoted_object'].update(custom_event_str='wrong'),
 'targeting':lambda x:x.s['adsets'][0]['targeting'].update(age_min=25),
 'schedule':lambda x:x.s['adsets'][0].update(start_time='2026-11-15T01:00:00-05:00'),
 'adsetstatus':lambda x:x.s['adsets'][0].update(status='PAUSED'),
 'copy':lambda x:first(x)['creative']['asset_feed_spec']['bodies'][0].update(text='different'),
 'cta':lambda x:first(x)['creative']['asset_feed_spec'].update(call_to_action_types=['LEARN_MORE']),
 'json':lambda x:first(x)['creative']['asset_feed_spec']['additional_data'].update(page_welcome_message='{}'),
 'jsoninvalid':lambda x:first(x)['creative']['asset_feed_spec']['additional_data'].update(page_welcome_message='{'),
 'page':lambda x:first(x)['creative']['object_story_spec'].update(page_id='123'),
 'pbia':lambda x:first(x)['creative']['object_story_spec'].update(instagram_user_id='123'),
 'utm':lambda x:first(x)['creative'].update(url_tags='other'),
 'rules':lambda x:first(x)['creative']['asset_feed_spec'].update(asset_customization_rules=[]),
 'seedactive':lambda x:next(a for a in x.s['ads'] if a['id']==x.g['ids']['seed_ad_id_1_1']).update(status='ACTIVE'),
 'seedcreative':lambda x:next(a for a in x.s['ads'] if a['id']==x.g['ids']['seed_ad_id_1_1'])['creative'].update(id='123'),
 'seedlineage':lambda x:next(a for a in x.s['ads'] if a['id']==x.g['ids']['seed_ad_id_1_1']).update(source_ad_id='123'),
 'objective':lambda x:x.s['campaign'].update(objective='OUTCOME_TRAFFIC'),
 'buyingtype':lambda x:x.s['campaign'].update(buying_type='RESERVED'),
 'specialcategory':lambda x:x.s['campaign'].update(special_ad_categories=[]),
 'specialcountry':lambda x:x.s['campaign'].update(special_ad_category_country=['BR']),
 'feature_extra_optin':lambda x:first(x)['creative']['degrees_of_freedom_spec']['creative_features_spec'].update(unapproved_feature={'enroll_status':'OPT_IN'}),
 'lineage':lambda x:first(x).update(source_ad_id='123'),
}
for n,f in mutations.items():mutation_test(n,f)

class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']);self.root=Path(self.temp.name);self.h=self.root/'request';self.h.mkdir();self.path=self.h/'request.json'
  self.g=copy.deepcopy(G);self.g['request_path']=str(self.path);self.g['checkpoint_path']=str(self.root/'checkpoint.json');self.g['audit_path']=str(self.root/'audit.json')
  self.q=rec.load(H/'request.json');self.payload=copy.deepcopy(PAYLOAD);self.cfg={'state_root':str(self.root/'state')}
  for n in ['request.json','selected-assets.json','manifest.json']:(self.h/n).write_bytes((H/n).read_bytes())
  for p in [Path(self.g['checkpoint_path']),Path(self.g['audit_path']),self.h/'engine-result.json']:p.write_text(json.dumps({'status':'FAILED','error':'original failure'}))
  self.g['pins']={str(self.path):rec.file_sha(self.path),str(self.h/'manifest.json'):rec.file_sha(self.h/'manifest.json')}
  self.s=full_fixture();self.calls=[];self.activate_count=0;self.crash=False
  outer=self
  class FakeRuntime:
   meta=object();token='offline'
   def __init__(self,*args):pass
   def authority(self):outer.calls.append('authority')
   def source_page(self):outer.calls.append('source_page')
   def read(self):outer.calls.append('GET');return copy.deepcopy(outer.s)
   def video(self,vid):
    d=next(x for x in PROOF['downloads'] if x['video_id']==vid)
    return {'id':vid,'title':d['title'],'length':d['length'],'status':{'video_status':'ready',**{k:{'status':'complete'} for k in ['uploading_phase','processing_phase','publishing_phase']}},'source':vid}
   def activate(self):
    outer.calls.append('POST_PARENT_ACTIVE');outer.activate_count+=1;outer.s['campaign']['status']='ACTIVE'
    if outer.crash:raise RuntimeError('offline crash after status success')
  self.runtime=FakeRuntime
  @contextmanager
  def admission(*args,**kwargs):yield None
  self.patches=[patch.object(rec,'local',side_effect=lambda *a:(self.g,self.cfg,self.q,self.payload)),patch.object(rec.continuation,'admission',admission),patch.object(rec,'fetch_video',side_effect=lambda vid:Path(next(x['path'] for x in PROOF['downloads'] if x['video_id']==vid)).read_bytes()),patch.object(rec,'inspect_bytes',side_effect=lambda raw,d:{'video_id':d['video_id'],'sha256':rec.sha(raw),'bytes':len(raw),'frames':[f['sha256'] for f in d['frames']],'dimensions':[d['width'],d['height']]})]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def run_recovery(self):return rec.recover(self.path,getattr(self,'runner',SimpleNamespace()),G['original_approved_digest'],G['approval_message_id'],runtime_factory=self.runtime)
 def test_recover_allslots_statusonly_receipt_and_retry(self):
  result=self.run_recovery();self.assertEqual('POSTPROCESS_PENDING',result['phase']);self.assertEqual(1,self.activate_count)
  self.run_recovery();self.assertEqual(1,self.activate_count)
  for p in [self.g['checkpoint_path'],self.g['audit_path'],self.h/'engine-result.json']:
   v=rec.load(p);self.assertEqual('FAILED',v['status']);self.assertEqual('original failure',v['error']);self.assertIn('independent_media_recovery',v)
 def test_crash_after_post_does_not_repeat_post(self):
  self.crash=True
  with self.assertRaises(RuntimeError):self.run_recovery()
  self.crash=False;self.run_recovery();self.assertEqual(1,self.activate_count)
 def test_active_without_intent_no_replay(self):
  self.s['campaign']['status']='ACTIVE'
  with self.assertRaises(ValueError):self.run_recovery()
  self.assertEqual(0,self.activate_count)
 def test_uncertain_incomplete_no_mutation(self):
  self.s['ads'].pop()
  with self.assertRaises(ValueError):self.run_recovery()
  self.assertEqual(0,self.activate_count)
 def test_json_failure_no_mutation(self):
  next(a for a in self.s['ads'] if a['id']==G['ids']['copied_ad_id_1_1'])['creative']['asset_feed_spec']['additional_data']['page_welcome_message']='{}'
  with self.assertRaises(ValueError):self.run_recovery()
  self.assertEqual(0,self.activate_count)
 def test_receipt_tamper(self):
  r=self.run_recovery();p=Path(r['recovery_receipt']['path']);v=rec.load(p);v['request_id']='other';rec.atomic(p,v)
  with self.assertRaises(ValueError):rec.validate_receipt(r['recovery_receipt'],self.g,self.payload,self.path)
 def test_receipt_other_manifest(self):
  r=self.run_recovery();p=copy.deepcopy(self.payload);p['request_id']='other'
  with self.assertRaises(ValueError):rec.validate_receipt(r['recovery_receipt'],self.g,p,self.path)
 def test_receipt_missing_download(self):
  r=self.run_recovery();v=rec.load(r['recovery_receipt']['path']);v['downloads'].pop();p=self.h/'media-recovery'/('receipt-'+rec.digest(v)+'.json');rec.atomic(p,v)
  with self.assertRaises(ValueError):rec.validate_receipt({'path':str(p),'sha256':rec.file_sha(p)},self.g,self.payload,self.path)

class FinalizeTests(PipelineTests):
 def setUp(self):
  super().setUp()
  import ares_manager_storage_standard as standard
  self.standard=standard;self.inv=self.root/'data/ares/creative-ops/inventory/assets.jsonl';self.inv.parent.mkdir(parents=True)
  rows=copy.deepcopy(SELECTED)
  for r in rows:r.update(used_by='ARES_IN_FLIGHT',reservation_request_id=self.q['request_id'])
  self.inv.write_text(''.join(json.dumps(r)+'\n' for r in rows));self.stock=self.root/'stock';self.stock.mkdir()
  self.ledger=self.root/'ledger.json';rec.atomic(self.ledger,{'allocations':{self.q['request_id']:{'account_id':self.q['account_id'],'names':[PAYLOAD['campaigns'][0]['name']],'status':'RESERVED'}}})
  self.runner=SimpleNamespace(INVENTORY=self.inv,R=self.root,naming=SimpleNamespace(load_policy=lambda:{'ledger_path':'ledger.json'}))
  self.stock_calls=[];self.fail_slot=None;self.failed=False;self.moved=set()
  def controller(asset_id,rid,apply=False):
   self.stock_calls.append(asset_id)
   if self.fail_slot==asset_id and not self.failed:self.failed=True;raise RuntimeError('offline stock partial failure')
   rows=[json.loads(s) for s in self.inv.read_text().splitlines()];row=next(r for r in rows if r['asset_id']==asset_id)
   p=self.stock/('use-'+rec.sha(standard.b.canonical([rid,row['asset_drive_id']]))+'.json')
   v={'schema':'mgs.manager.standard.use.v1','status':'verified','request_id':rid,'asset_id':asset_id,'logical_id':row['asset_drive_id'],'stock_file_id':'stock_'+asset_id,'sha256':row['clean_checksum'],'folder_id':'used_folder','assignment':{'campaign_id':row['used_by'],'adset_id':row['meta_adset_id'],'ad_id':row['meta_ad_id'],'creative_id':row['meta_creative_id']}}
   if p.exists():self.assertEqual(v,rec.load(p))
   else:rec.atomic(p,v);self.moved.add(asset_id)
   row.update(manager_media_folder_id='used_folder',manager_storage_state='used',manager_use_request_id=rid);self.inv.write_text(''.join(json.dumps(r)+'\n' for r in rows))
   return {'status':'verified','asset_id':asset_id,'destination':'used_folder','same_ids':True}
  self.extra=[patch.object(standard,'HOME',self.stock),patch.object(standard,'confirm_usage',controller),patch.object(rec,'repair_partial_stock',return_value=None)]
  for p in self.extra:p.start()
 def tearDown(self):
  for p in reversed(self.extra):p.stop()
  super().tearDown()
 def finish(self):return rec.finalize(self.path,self.runner,G['original_approved_digest'],G['approval_message_id'],runtime_factory=self.runtime)
 def test_finalize_real_ids_usados_then_ledger_and_retry(self):
  self.run_recovery();f=self.finish();self.assertEqual('COMPLETE',f['phase']);self.assertEqual(3,len(self.moved));self.assertEqual(f,self.finish());self.assertEqual(1,self.activate_count)
  rows=[json.loads(s) for s in self.inv.read_text().splitlines()]
  for row in rows:self.assertEqual(next(p['observed_video_id'] for p in G['pairs'] if p['asset_id']==row['asset_id'] and p['labels'][0].endswith('_vertical')),row['meta_video_id'])
  self.assertEqual('COMMITTED',rec.load(self.ledger)['allocations'][self.q['request_id']]['status'])
  self.assertFalse(rec.load(Path(self.cfg['state_root'])/'writer-leases'/f"{self.q['account_id']}.json")['blocks_readers'])
 def test_partial_stock_retry_missing_only_keeps_ledger_uncommitted(self):
  self.run_recovery();self.fail_slot=SELECTED[1]['asset_id']
  with self.assertRaises(RuntimeError):self.finish()
  self.assertEqual({SELECTED[0]['asset_id']},self.moved);self.assertEqual('RESERVED',rec.load(self.ledger)['allocations'][self.q['request_id']]['status'])
  self.finish();self.assertEqual(3,len(self.moved));self.assertEqual(1,self.activate_count)
 def test_no_receipt_no_finalize(self):
  with self.assertRaises(ValueError):self.finish()
  self.assertFalse(self.stock_calls)
 def test_fake_stock_receipt_does_not_commit(self):
  self.run_recovery()
  with patch.object(self.standard,'confirm_usage',return_value={'status':'verified','asset_id':SELECTED[0]['asset_id'],'same_ids':True,'destination':'used_folder'}):
   with self.assertRaises(FileNotFoundError):self.finish()
  self.assertEqual('RESERVED',rec.load(self.ledger)['allocations'][self.q['request_id']]['status'])
 def test_final_get_drift_blocks_finalize(self):
  self.run_recovery();self.s['adsets'][0]['targeting']['age_min']=30
  with self.assertRaises(ValueError):self.finish()
  self.assertFalse(self.stock_calls)
 def test_recover_terminal_then_finalize_no_post(self):
  self.run_recovery();f=self.finish();self.run_recovery();self.assertEqual(f,self.finish());self.assertEqual(1,self.activate_count)
  self.assertFalse(rec.load(Path(self.cfg['state_root'])/'writer-leases'/f"{self.q['account_id']}.json")['blocks_readers'])
 def test_terminal_finalize_is_readonly_no_lease_reopen(self):
  self.run_recovery();f=self.finish()
  lease=Path(self.cfg['state_root'])/'writer-leases'/f"{self.q['account_id']}.json"
  before={p:p.read_bytes() for p in [self.inv,self.ledger,lease]}
  with patch.object(rec,'write_assignments',side_effect=AssertionError('terminal write forbidden')):
   self.assertEqual(f,self.finish())
  self.assertEqual(before,{p:p.read_bytes() for p in before})
 def test_crash_after_final_before_links_repaired_by_finalize(self):
  self.run_recovery();real=rec.cas_link
  def crash(p,k,v,b):
   if k=='independent_media_finalization':raise RuntimeError('offline crash before links')
   return real(p,k,v,b)
  with patch.object(rec,'cas_link',side_effect=crash):
   with self.assertRaises(RuntimeError):self.finish()
  self.assertTrue((self.h/'final.json').exists());self.assertEqual(3,len(self.moved))
  f=self.finish();self.assertEqual('COMPLETE',f['phase']);self.assertEqual(1,self.activate_count)
 def test_independent_source_proof_requires_all_stock_receipts(self):
  self.run_recovery();self.finish();cp=rec.load(self.g['checkpoint_path'])
  fp=rec.independent_completion(cp,{},self.q['request_id'],self.q['account_id'],self.g['ids'],audit_root=self.h);self.assertEqual(self.h/'final.json',fp)
  proof=Path(rec.load(fp)['manager_stock_readbacks'][0]['path']);v=rec.load(proof);v['stock_file_id']='wrong';rec.atomic(proof,v)
  with self.assertRaises(ValueError):rec.independent_completion(cp,{},self.q['request_id'],self.q['account_id'],self.g['ids'],audit_root=self.h)

class AdapterTests(unittest.TestCase):
 def test_status_transport_only_existing_parent_exact_body(self):
  from unittest.mock import Mock
  r=rec.Runtime.__new__(rec.Runtime);r.g=G;r.lane=('app','account');r.reserve=Mock();r.quota=Mock();r.transport=Mock();r.transport.last_outer_headers={}
  r.transport.execute.return_value=[SimpleNamespace(code=200,body={'success':True})];r.activate()
  ops,stage=r.transport.execute.call_args.args;self.assertEqual(1,len(ops));self.assertEqual('POST',ops[0].method);self.assertEqual(G['ids']['campaign_id_1'],ops[0].relative_url);self.assertEqual({'status':'ACTIVE'},ops[0].body);r.reserve.assert_called_once_with(3)
 def test_uncertain_status_response_requires_get_no_second_post(self):
  from unittest.mock import Mock
  r=rec.Runtime.__new__(rec.Runtime);r.g=G;r.lane=('app','account');r.reserve=Mock();r.quota=Mock();r.transport=Mock();r.transport.last_outer_headers={};r.transport.execute.return_value=[SimpleNamespace(code=200,body={})]
  with self.assertRaises(ValueError):r.activate()
  self.assertEqual(1,r.transport.execute.call_count)
 def test_quota_blocks_before_status_post(self):
  from unittest.mock import Mock
  r=rec.Runtime.__new__(rec.Runtime);r.reserve=Mock(side_effect=RuntimeError('quota'));r.transport=Mock()
  with self.assertRaises(RuntimeError):r.activate()
  r.transport.execute.assert_not_called()
 def test_extra_required_fields_are_requested_readonly(self):
  from unittest.mock import Mock
  r=rec.Runtime.__new__(rec.Runtime);r.g=G;r.payload=PAYLOAD;r.lane=('app','account');r.reserve=Mock();r.quota=Mock();r.transport=Mock();r.transport.last_outer_headers={}
  r.transport.execute.return_value=[SimpleNamespace(name='readback_campaign_1',code=200,body=SNAP['campaign']),SimpleNamespace(name='readback_adsets_1',code=200,body={'data':SNAP['adsets']}),SimpleNamespace(name='readback_ads_1',code=200,body={'data':SNAP['ads']})];r.read()
  ops,_=r.transport.execute.call_args.args;self.assertTrue(all(op.method=='GET' for op in ops))
  for k in PAYLOAD['campaigns'][0]['adset_create']:self.assertIn(k,ops[1].relative_url)
 def test_partial_remote_move_reuses_original_source_and_stock_id(self):
  import ares_manager_storage_standard as standard
  import ares_archive_storage as storage
  from unittest.mock import Mock
  @contextmanager
  def queue():yield
  with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as td:
   root=Path(td);inv=root/'data/ares/creative-ops/inventory/assets.jsonl';inv.parent.mkdir(parents=True);home=root/'receipts';home.mkdir()
   asset=copy.deepcopy(SELECTED[0]);asset['manager_media_folder_id']='exclusive';row=copy.deepcopy(asset);row.update(manager_storage_state='exclusive',reservation_request_id=G['request_id']);inv.write_text(json.dumps(row)+'\n')
   a={'campaign_id':'11','adset_id':'22','ad_id':'33','creative_id':'44'};q={'request_id':G['request_id']};key=rec.sha(standard.b.canonical([q['request_id'],asset['asset_drive_id']]))
   old={'status':'intent','stock_file_id':'stock1','assignment':a,'request_id':q['request_id']};rec.atomic(home/('use-'+key+'.json'),old)
   record={'parents':['used'],'stock_file_id':'stock1','sha256Checksum':asset['clean_checksum'],'md5Checksum':asset['clean_md5']}
   result={'folder_id':'used','manager_code':'g006','request_id':q['request_id']};used=Mock(return_value=result)
   with patch.object(standard.b,'BASE',root),patch.object(standard,'HOME',home),patch.object(standard.b,'queue_lock',queue),patch.object(standard.b,'Drive',return_value=SimpleNamespace(token='offline')),patch.object(storage,'resolve_media',return_value=record),patch.object(standard,'find_slot',return_value=({'used_id':'used'},'exclusive')),patch.object(standard,'mark_used',used),patch.object(standard,'apply_use_result',side_effect=lambda r,v:r.update(manager_storage_state='used',manager_media_folder_id=v['folder_id'])):
    rec.repair_partial_stock(standard,asset,a,q)
   used.assert_called_once();self.assertEqual('exclusive',used.call_args.args[2]['ready_parent_id']);self.assertEqual('used',json.loads(inv.read_text())['manager_storage_state'])
 def test_failed_transport_still_observes_quota_headers(self):
  from unittest.mock import Mock
  for method in ['activate','read']:
   r=rec.Runtime.__new__(rec.Runtime);r.g=G;r.payload=PAYLOAD;r.lane=('app','account');r.reserve=Mock();r.quota=Mock();r.transport=Mock();r.transport.last_outer_headers={'x-app-usage':'{}'};r.transport.execute.side_effect=RuntimeError('offline failure')
   with self.assertRaises(RuntimeError):getattr(r,method)()
   r.quota.observe_headers.assert_called_once_with(r.lane,r.transport.last_outer_headers)
 def test_receipt_content_hash_cannot_replace_proven_media(self):
  v={'x':1};self.assertNotEqual(rec.digest(v),rec.digest({'x':2}))

if __name__=='__main__':
 with patch.object(socket.socket,'connect',side_effect=AssertionError('offline network forbidden')):unittest.main()
