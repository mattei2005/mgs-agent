"""OFFLINE ONLY. Real 3-slot media evidence; synthetic GET supplement explicitly
marked in setUp until owner provides a fuller real adset snapshot. No API writes.
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
 supplement=M/'owner-supplement.json'
 if supplement.exists():s['adsets']=[rec.load(supplement)]
 else:
  # FIXTURE ONLY, not real GET evidence. Tests for absent fields reject the
  # original snapshot; production always requires a new full readback.
  for k,v in PAYLOAD['campaigns'][0]['adset_create'].items():s['adsets'][0].setdefault(k,copy.deepcopy(v))
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
  self.patches=[patch.object(rec,'local',side_effect=lambda *a:(self.g,self.cfg,self.q,self.payload)),patch.object(rec.continuation,'admission',admission),patch.object(rec,'fetch_video',side_effect=lambda vid:Path(next(x['path'] for x in PROOF['downloads'] if x['video_id']==vid)).read_bytes()),patch.object(rec,'inspect_bytes',side_effect=lambda raw,d:{'video_id':d['video_id'],'sha256':rec.sha(raw)})]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def run_recovery(self):return rec.recover(self.path,SimpleNamespace(),G['original_approved_digest'],G['approval_message_id'],runtime_factory=self.runtime)
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

if __name__=='__main__':
 with patch.object(socket.socket,'connect',side_effect=AssertionError('offline network forbidden')):unittest.main()
