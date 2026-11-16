"""Physical-write quota estimate and new-adset-only clock for scoped replacement."""
import copy,importlib.util,json,sys,tempfile,time,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import patch
sys.path[:0]=['/root/mgs-agent/scripts','/root/mgs-agent/tests']
ENGINE=Path('/root/mgs-agent/scripts/ares_campaign_v3/engine.py')
SAME=Path('/root/mgs-agent/scripts/ares_campaign_v3/eggbev_same_account_replacement.py')
def module(name,path):
 s=importlib.util.spec_from_file_location('ares_campaign_v3.'+name,path);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);return m
class WindowAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.e=module('window_engine_candidate',ENGINE);self.m=module('window_same_candidate',SAME)
  self.tmp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def test_two_campaigns_fit_unchanged60_by_physical_write_estimate(self):
  from test_eggbev_target_page_clone import specimen
  from ares_campaign_v3.schema import CampaignSpec
  from ares_campaign_v3.target_page_clone import stages
  from ares_campaign_v3.quota import LaneQuotaStore,QuotaBlocked
  raw=specimen();raw['account_id']=self.m.TARGET;raw['ads']=raw['ads']*3
  c=CampaignSpec.from_dict(raw);bundle=SimpleNamespace(account_id=self.m.TARGET,campaigns=(c,c))
  cap={'enabled':True,'account_id':self.m.TARGET,'quota_basis':'planned_writes_x2_with_readback_margin','quota_points_per_campaign':30}
  cfg={'audit_root':str(self.root/'audit'),'points_per_mode':{self.m.MODE:60},'accounts':{self.m.TARGET:{'operation':self.m.OP,'target_page_replacement':cap}}}
  engine=self.e.CampaignEngine(cfg,transport_factory=lambda a:None,read_only=True)
  write_ops=sum(len(s.operations) for s in stages((c,c)))
  self.assertEqual(write_ops,30);self.assertEqual(engine._points(bundle),2*write_ops)
  quota=LaneQuotaStore(self.root/'quota');lane=('test-app',self.m.TARGET);quota.seed_access_tier(lane,'development_access',source='offline-fixture')
  admitted=quota.reserve(lane,engine._points(bundle),request_id='offline-window');self.assertEqual(admitted['hard_score'],60)
  with self.assertRaises(QuotaBlocked):quota.reserve(lane,1,request_id='offline-overflow')
  del cfg['accounts'][self.m.TARGET]['target_page_replacement']['quota_basis'];self.assertEqual(engine._points(bundle),120)
 def test_real_engine_development_three_waves_and_journaled_starts(self):
  from ares_campaign_v3 import eggbev_same_account_replacement as lane
  from ares_campaign_v3.engine import CampaignEngine
  from ares_campaign_v3.schema import Manifest
  from eggbev_target_fake import TargetFakeMeta
  R=Path('/root/mgs-agent');rid='eggbev03-c212-replacement-1571894746719330377';home=R/'data/ares/meta-ads/audit/eggbev/same-account'/rid/'execution'
  payload=json.loads((home/'effective-manifest.json').read_text());cfg=json.loads((R/'data/ares/meta-ads/engine-v3/config.json').read_text())
  cfg['state_root']=str(self.root/'state');cfg['audit_root']=str(self.root/'audit')
  # This regression exercises the original clock/quota route, not a credential cutover.
  cfg['accounts'][lane.TARGET]['app_key']=payload['campaigns'][0]['app_key']
  cfg['accounts'][lane.TARGET]['marketing_api_access_tier']='development_access'
  cap=cfg['accounts'][lane.TARGET]['target_page_replacement'];cap.update(quota_basis='planned_writes_x2_with_readback_margin',quota_points_per_campaign=30)
  class Fake(TargetFakeMeta):
   def new(self,value):
    if value.get('_kind')=='campaign':value={**value,'account_id':lane.TARGET}
    return super().new(value)
  fake=Fake();engine=CampaignEngine(cfg,transport_factory=lambda a:fake)
  proof={'request_id':rid,'approved_digest':json.loads((home/'summary.json').read_text())['digest'],'approval_message_id':'1571940565040234679','verified_at_monotonic':time.monotonic(),'elapsed_campaign_digests':[lane.digest(c) for c in payload['campaigns']]}
  proof['admitted_manifest_sha256']=lane.digest(payload)
  marker=lane.CURRENT.set(proof)
  try:
   self.assertTrue(lane.allows_elapsed_manifest(payload));self.assertFalse(lane.allows_elapsed_manifest({**payload,'request_id':'forged-request'}))
   manifest=Manifest.from_dict(payload);proof['digest']=manifest.digest;lane.CURRENT.set(proof)
   for expected in [2,4,5]:
    proof['verified_at_monotonic']=time.monotonic();lane.CURRENT.set(proof);result=engine.execute(manifest)
    self.assertEqual(len(result['campaign_ids']),expected)
    self.assertEqual(len([v for v in fake.objects.values() if v.get('_kind')=='campaign']),expected)
    self.assertTrue(all(datetime.fromisoformat(v['start_time'])>datetime.now(timezone.utc) for v in fake.objects.values() if v.get('_kind')=='adset'))
    if expected<5:
     self.assertEqual(result['status'],'PARTIAL_DEFERRED_QUOTA')
     qp=engine.quota._path((cfg['accounts'][lane.TARGET]['app_key'],lane.TARGET));state=json.loads(qp.read_text())
     for event in state['events']:event['at']=time.time()-301
     qp.write_text(json.dumps(state))
   self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE');self.assertEqual(len([v for v in fake.objects.values() if v.get('_kind')=='ad']),30)
   before=len(fake.calls);self.assertTrue(engine.execute(manifest)['idempotent_replay']);self.assertEqual(len(fake.calls),before)
  finally:lane.CURRENT.reset(marker)
 def clock_fixture(self):
  rid='offline-same-immediate';q={'request_id':rid,'account_id':self.m.TARGET};p=self.root/'data/ares/meta-ads/requests'/(rid+'.json');p.parent.mkdir(parents=True);p.write_text(json.dumps(q))
  c=SimpleNamespace(account_id=self.m.TARGET,mode=self.m.MODE,idempotency_key=rid+'-1',start_time=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())
  proof={'request_id':rid,'approved_digest':'a'*64,'approval_message_id':'1571940565040234679','verified_at_monotonic':time.monotonic()}
  engine=SimpleNamespace(_same_account_execution_authority=proof,config={'accounts':{self.m.TARGET:{'campaign_policy':{'immediate_start_request_ids':[rid]}}}})
  return c,engine
 def test_new_adset_clock_is_journaled_once_and_tamper_rejected(self):
  c,engine=self.clock_fixture();record={}
  with patch.object(self.m,'ROOT',self.root),patch.object(self.m,'admit',return_value=({},{})):
   start=self.m.new_adset_start(engine,c,record,1);again=self.m.new_adset_start(engine,c,record,1)
  self.assertEqual(start,again);self.assertGreater(datetime.fromisoformat(start),datetime.now(timezone.utc));self.assertEqual(self.m.expected_start(c,record,1),start)
  record['same_immediate_starts']['1']['effective_start_time']=c.start_time
  with self.assertRaises(ValueError):self.m.expected_start(c,record,1)
 def test_existing_adset_cannot_receive_new_clock(self):
  c,engine=self.clock_fixture()
  with patch.object(self.m,'ROOT',self.root),patch.object(self.m,'admit',return_value=({},{})),self.assertRaisesRegex(ValueError,'existing'):
   self.m.new_adset_start(engine,c,{'target_clone_ids':{'adset_id_1':'999'}},1)
if __name__=='__main__':unittest.main()
