"""Fake-only continuation across issuer routing; source seals and existing IDs stay fixed."""
import copy,json,sys,tempfile,time,unittest,hashlib
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
R=Path('/root/mgs-agent');S=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(S/'scripts'),str(S/'tests')]
from ares_campaign_v3 import eggbev_same_account_replacement as same,credential_routing as route
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.prevalidation import validate_account_policy
from eggbev_target_fake import TargetFakeMeta
RID='eggbev03-c212-replacement-1571894746719330377';AID='1481815942722118'
class RoutingContinuationTests(unittest.TestCase):
 def fixture(self):
  self.temp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch');self.addCleanup(self.temp.cleanup);root=Path(self.temp.name)
  from ares_campaign_v3 import media_materialization
  media_root=patch.object(media_materialization,'ROOT',root);media_root.start();self.addCleanup(media_root.stop)
  home=R/'data/ares/meta-ads/audit/eggbev/same-account'/RID/'execution'
  baseline=R/'data/ares/meta-ads/audit/maintenance/eggbev03-route-cutover-1571996433999990885/baseline'
  payload=json.loads((home/'effective-manifest.json').read_text());cp=json.loads((baseline/'data/ares/meta-ads/engine-v3/state/checkpoints'/f'{RID}-{AID}.json').read_text());record=cp['bundles'][0]
  cfg=json.loads((S/'data/ares/meta-ads/engine-v3/config.json').read_text());cfg['state_root']=str(root/'state');cfg['audit_root']=str(root/'audit')
  q=json.loads((R/'data/ares/meta-ads/requests'/(RID+'.json')).read_text());q['resume_authority_message_id']='1571996433999990885'
  qp=root/'data/ares/meta-ads/requests'/(RID+'.json');qp.parent.mkdir(parents=True);qp.write_text(json.dumps(q))
  rel=Path('data/ares/meta-ads/audit/eggbev/same-account')/RID/'execution/app-route-migration/receipt.json';rp=root/rel;rp.parent.mkdir(parents=True)
  receipt=json.loads((S/rel).read_text());rp.write_text(json.dumps(receipt))
  pol=root/'data/ares/meta-ads/policies/eggbev03-same-account-replacement.json';pol.parent.mkdir(parents=True);pol.write_bytes((S/'data/ares/meta-ads/policies/eggbev03-same-account-replacement.json').read_bytes())
  cpath=root/'state/checkpoints'/f'{RID}-{AID}.json';cpath.parent.mkdir(parents=True);cpath.write_text(json.dumps(cp))
  ap=root/'audit'/f'{RID}.json';ap.parent.mkdir();ap.write_bytes((R/'data/ares/meta-ads/engine-v3/audit'/f'{RID}.json').read_bytes())
  class Fake(TargetFakeMeta):
   def new(self,value):
    if value.get('_kind')=='campaign':value={**value,'account_id':AID}
    return super().new(value)
  fake=Fake();ids=record['target_clone_ids']
  for ci,c in enumerate(payload['campaigns'][:2],1):
   cid=ids[f'campaign_id_{ci}'];sid=ids[f'adset_id_{ci}']
   fake.objects[cid]={'id':cid,'_kind':'campaign','account_id':AID,'name':c['name'],'status':'PAUSED',**copy.deepcopy(c['campaign_create'])}
   fake.objects[sid]={'id':sid,'_kind':'adset','name':c['adset_name'],'campaign_id':cid,'status':'ACTIVE','start_time':record['same_immediate_starts'][str(ci)]['effective_start_time'],**copy.deepcopy(c['adset_create'])}
   for ai,ad in enumerate(c['ads'],1):
    crid=ids[f'creative_id_{ci}_{ai}'];fake.objects[crid]={'id':crid,'_kind':'creative',**copy.deepcopy(ad['creative_payload'])}
  return root,home,payload,record,cfg,q,fake,rp
 def test_current_absence_is_scoped_and_does_not_relabel_original_outcome(self):
  root,home,payload,rec,cfg,q,fake,rp=self.fixture();receipt=json.loads(rp.read_text());receipt.update(receipt_path=str(rp),receipt_sha256=hashlib.sha256(rp.read_bytes()).hexdigest())
  from ares_campaign_v3.transport import BatchOperation,BatchResult
  from ares_campaign_v3.target_page_clone import stages
  proof={'request_id':RID,'route_receipt':receipt,'verified_at_monotonic':time.monotonic()}
  class Engine:
   _same_account_execution_authority=proof
   def _batch(self,bundle,transport,ops,stage):return [BatchResult(o.name,200,{'id':o.relative_url.split('?')[0],'account_id':AID,'status':'PAUSED'}) for o in ops]
  marker=same.CURRENT.set(proof)
  try:
   with patch.object(route,'ROOT',root):
    op=next(o for st in stages(tuple(type('C',(),{**c,'ads':[type('Ad',(),a)() for a in c['ads']]})() for c in payload['campaigns'][:2])) for o in st.operations if o.name=='target_seed_create_1_1')
    ids=rec['target_clone_ids'];body={'name':op.body['name'],'adset_id':ids['adset_id_1'],'creative':{'creative_id':ids['creative_id_1_1']},'status':'PAUSED'};op=BatchOperation(op.name,op.method,op.relative_url,body,kind='ad_create')
    bundle=type('B',(),{'account_id':AID})()
    self.assertFalse(route.allow_missing_paused_seed(Engine(),bundle,fake,op,rec,[{'id':'visible'}]))
    self.assertTrue(route.allow_missing_paused_seed(Engine(),bundle,fake,op,rec,[]));self.assertEqual(rec['write_journal'][-1]['confirmed'],[])
    rec['write_journal'].append(copy.deepcopy(rec['write_journal'][-1]));self.assertFalse(route.allow_missing_paused_seed(Engine(),bundle,fake,op,rec,[]))
  finally:same.CURRENT.reset(marker)
 def test_full_fake_continuation_reuses_parents_creatives_and_original_seal(self):
  root,home,payload,record,cfg,q,fake,rp=self.fixture();original=copy.deepcopy(payload)
  with patch.object(route,'ROOT',root),patch.object(same,'ROOT',root):
   receipt=route.receipt_for(q,payload,cfg)
   proof={'request_id':RID,'approved_digest':'5ff905263c0d0218f78bf22974191ca95bc5e6865a9229f35cf83acd3ad44e48','approval_message_id':'1571940565040234679','verified_at_monotonic':time.monotonic(),'route_receipt':receipt,'elapsed_campaign_digests':[same.digest(c) for c in payload['campaigns']],'admitted_manifest_sha256':same.digest(payload)}
   marker=same.CURRENT.set(proof)
   try:
    manifest=Manifest.from_dict(payload);proof['digest']=manifest.digest;same.CURRENT.set(proof);validate_account_policy(manifest,cfg)
    engine=CampaignEngine(cfg,transport_factory=lambda a:fake);result=engine.execute(manifest)
    self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE');self.assertEqual(len(result['campaign_ids']),5)
    self.assertEqual(len([v for v in fake.objects.values() if v.get('_kind')=='campaign']),5)
    writes=[x for x in fake.calls if x[2]=='POST'];self.assertEqual(len([x for x in writes if x[0]=='campaign_create']),3)
    self.assertEqual(len([x for x in writes if x[0]=='creative_create']),9)
    self.assertEqual(payload,original);self.assertEqual(manifest.digest,record['sealed_manifest_digest'])
    self.assertTrue(any(x[0]=='target_seed_create' for x in writes));self.assertEqual(len([v for v in fake.objects.values() if v.get('_kind')=='ad']),30)
    count=len(fake.calls);self.assertTrue(engine.execute(manifest)['idempotent_replay']);self.assertEqual(len(fake.calls),count)
   finally:same.CURRENT.reset(marker)
 def _repair_fixture(self, refuse=False):
  root,home,payload,record,cfg,q,fake,rp=self.fixture()
  record['error']={'stage':'target_seed_create','type':'BatchTransportError','detail':{'children':[{'name':f'target_seed_create_{ci}_{ai}','code':400,'error':{'code':200,'error_subcode':3858756,'is_transient':False}} for ci in (1,2) for ai in (1,2,3)]}}
  cp=root/'state/checkpoints'/f'{RID}-{AID}.json';body=json.loads(cp.read_text());body['bundles'][0]=record;cp.write_text(json.dumps(body))
  old=fake.execute
  def execute(ops,stage):
   if refuse and stage=='post_actor_seed_repair':
    fake.calls.extend((stage,o.name,o.method,o.relative_url) for o in ops)
    raise RuntimeError('synthetic fresh-post refusal; stop after first slot')
   return old(ops,stage)
  fake.execute=execute
  return root,payload,record,cfg,q,fake,rp
 def test_repair_preserves_all_old_ids_and_completes_exact_children(self):
  root,payload,record,cfg,q,fake,rp=self._repair_fixture();original_ids=copy.deepcopy(record['target_clone_ids'])
  with patch.object(route,'ROOT',root),patch.object(same,'ROOT',root):
   receipt=route.receipt_for(q,payload,cfg);proof={'request_id':RID,'approved_digest':'5ff905263c0d0218f78bf22974191ca95bc5e6865a9229f35cf83acd3ad44e48','approval_message_id':'1571940565040234679','verified_at_monotonic':time.monotonic(),'route_receipt':receipt,'elapsed_campaign_digests':[same.digest(c) for c in payload['campaigns']],'admitted_manifest_sha256':same.digest(payload)};marker=same.CURRENT.set(proof)
   try:
    manifest=Manifest.from_dict(payload);proof['digest']=manifest.digest;engine=CampaignEngine(cfg,transport_factory=lambda a:fake);result=engine.execute(manifest);self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE')
    saved=json.loads((root/'state/checkpoints'/f'{RID}-{AID}.json').read_text())['bundles'][0];self.assertEqual(saved['post_actor_repair']['status'],'REPAIRED_VERIFIED')
    self.assertEqual(len(saved['post_actor_repair']['slots']),6);self.assertEqual(saved['campaign_ids'],record['campaign_ids']);self.assertEqual(saved['adset_ids'],record['adset_ids'])
    for k,v in original_ids.items():
     if k.startswith('creative_id_'):self.assertIn(v,fake.objects)
    self.assertEqual(len([v for v in fake.objects.values() if v.get('_kind')=='ad']),30)
   finally:same.CURRENT.reset(marker)
 def test_media_receipt_changes_only_physical_ids_and_preserves_sealed_original(self):
  root,payload,record,cfg,q,fake,rp=self._repair_fixture()
  rel=Path('data/ares/meta-ads/audit/eggbev/same-account')/RID/'execution/media-visibility-repair/materialization-receipt.json';p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((R/rel).read_bytes());before=copy.deepcopy(payload)
  with patch.object(route,'ROOT',root),patch.object(same,'ROOT',root):
   receipt=route.receipt_for(q,payload,cfg);proof={'request_id':RID,'approved_digest':'5ff905263c0d0218f78bf22974191ca95bc5e6865a9229f35cf83acd3ad44e48','approval_message_id':'1571940565040234679','verified_at_monotonic':time.monotonic(),'route_receipt':receipt,'elapsed_campaign_digests':[same.digest(c) for c in payload['campaigns']],'admitted_manifest_sha256':same.digest(payload)};marker=same.CURRENT.set(proof)
   try:
    proof['media_materialization_authorized']=str(rel)
    manifest=Manifest.from_dict(payload);proof['digest']=manifest.digest;engine=CampaignEngine(cfg,transport_factory=lambda a:fake);result=engine.execute(manifest);self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE');self.assertEqual(payload,before)
    data=json.loads(p.read_text());saved=json.loads((root/'state/checkpoints'/f'{RID}-{AID}.json').read_text())['bundles'][0];self.assertEqual(saved['sealed_manifest_digest'],manifest.digest)
    for slot in saved['post_actor_repair']['slots'].values():
     actual=fake.objects[slot['new_creative_id']]['asset_feed_spec']['videos'];self.assertTrue(all(v['video_id'] in data['mapping'].values() for v in actual))
    from ares_campaign_v3.media_materialization import materialize
    bad=copy.deepcopy(saved);bad['media_materialization_receipt']['sha256']='wrong'
    with self.assertRaisesRegex(ValueError,'receipt drift'):materialize(type('B',(),{'campaigns':manifest.campaigns})(),bad)
   finally:same.CURRENT.reset(marker)
 def test_repair_stops_at_first_fresh_post_refusal(self):
  root,payload,record,cfg,q,fake,rp=self._repair_fixture(refuse=True)
  with patch.object(route,'ROOT',root),patch.object(same,'ROOT',root):
   receipt=route.receipt_for(q,payload,cfg);proof={'request_id':RID,'approved_digest':'5ff905263c0d0218f78bf22974191ca95bc5e6865a9229f35cf83acd3ad44e48','approval_message_id':'1571940565040234679','verified_at_monotonic':time.monotonic(),'route_receipt':receipt,'elapsed_campaign_digests':[same.digest(c) for c in payload['campaigns']],'admitted_manifest_sha256':same.digest(payload)};marker=same.CURRENT.set(proof)
   try:
    manifest=Manifest.from_dict(payload);proof['digest']=manifest.digest;engine=CampaignEngine(cfg,transport_factory=lambda a:fake)
    with self.assertRaisesRegex(RuntimeError,'synthetic fresh-post refusal'):engine.execute(manifest)
    self.assertEqual(len([x for x in fake.calls if x[0]=='post_actor_creative_repair']),1);self.assertEqual(len([v for v in fake.objects.values() if v.get('_kind')=='ad']),0)
    count=len([x for x in fake.calls if x[2]=='POST'])
    with self.assertRaisesRegex(ValueError,'fresh post still refused or uncertain'):engine.execute(manifest)
    self.assertEqual(count,len([x for x in fake.calls if x[2]=='POST']))
   finally:same.CURRENT.reset(marker)
if __name__=='__main__':unittest.main()
