"""Exact cross-account capability acceptance. Fake transport only; no provider writes."""
import copy,importlib.util,json,sys,tempfile,unittest
from contextlib import ExitStack,contextmanager
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch,Mock
R=Path('/root/mgs-agent');sys.path[:0]=[str(R/'scripts'),str(R/'tests')]
RID='eggbev03-cross-account-1571623835822858352';REQ=R/'data/ares/meta-ads/requests'/f'{RID}.json'

def runner():
 s=importlib.util.spec_from_file_location('offline_cross_runner',R/'scripts/ares-eggbev-target-clone.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def fixture():
 from test_eggbev_target_page_clone import specimen
 c=specimen();page={'id':'82001','name':'Moorcroft Finances','page_token':'pg_23187','instagram_user_id':'82002','naming_identity':{'page_id':'82001','page_name':'Moorcroft Finances','page_token':'pg_23187'}}
 ads=[]
 for i in range(3):
  a=copy.deepcopy(c['ads'][0]);a['id']=str(81003+i);a['adset_id']='81002';a['status']='ACTIVE'
  a['creative']={'id':str(81100+i),'object_story_spec':{'page_id':'82001','video_data':{'message':'Exact source body '+str(i),'call_to_action':{'type':'APPLY_NOW','value':{'app_destination':'MESSENGER'}}}},'url_tags':'utm_source=fb&utm_campaign=pg_23187&opaque=literal%2Bvalue','degrees_of_freedom_spec':{'creative_features_spec':{'image_background_gen':{'enroll_status':'OPT_IN'},'text_optimizations':{'enroll_status':'OPT_IN','opaque':'preserve'}}},'contextual_multi_ads':{'enroll_status':'OPT_OUT'}}
  ads.append(a)
 source={'campaign':{'id':'81001','account_id':'1034081997659047','name':'303 - Moorcroft Finances - ENG - US - (pg_23187) - C01','status':'ACTIVE',**c['campaign_create']},'adset':{'id':'81002',**c['adset_create']},'ads':ads,'all_ads':copy.deepcopy(ads),'technical_seed_ads':[]}
 source['adset']['bid_amount']='123';source['adset']['bid_constraints']={'roas_average_floor':10}
 return json.loads(REQ.read_text()),source,page

class CrossTests(unittest.TestCase):
 def setUp(self):
  from ares_campaign_v3 import eggbev_cross_account as cross
  self.c=cross;self.m=runner();self.q,self.source,self.page=fixture();self.temp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.cfg=json.loads((R/'data/ares/meta-ads/engine-v3/config.json').read_text());self.cfg['state_root']=str(self.root/'state');self.cfg['audit_root']=str(self.root/'audit');self.cfg['require_prevalidated_manifest']=True
  # Historical cancelled cross-account mode retains its historical issuer fixture.
  self.cfg['accounts'][self.c.TARGET].update(app_key='mgs-meta-app-'+self.c.APP,meta_app_id=self.c.APP,token_user_id=self.c.USER,marketing_api_access_tier='development_access')
  self.m.CONFIG=self.root/'frozen-legacy-config.json';self.m.CONFIG.write_text(json.dumps(self.cfg))
  self.assets=[]
  from ares_campaign_v3.media_registry import MediaRegistry
  self.reg=MediaRegistry(self.root/'registry.json')
  for i,f in enumerate([f for g in self.q['campaigns'] for f in g['media_filenames']]):
   a={'asset_id':'offline-asset-'+str(i),'canonical_filename':f,'clean_checksum':format(i+1,'064x')};self.assets.append(a)
   self.reg.register(account_id=cross.TARGET,asset_id=a['asset_id'],checksum=a['clean_checksum'],vertical_video_id=str(92000+i*2),square_video_id=str(92001+i*2),ready=True,upload_edge='ad_account_advideos',association_verified=True)
  self.allocation={'count':5,'account_id':cross.TARGET,'names':[f'{400+i} - Moorcroft Finances - ENG - US - (pg_23187) - C{2+i:02d}' for i in range(5)],'page_id':'82001','page_token':'pg_23187'}
  self.start=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
 def draft(self):return self.c.build(self.q,self.source,self.page,self.assets,self.reg,self.allocation,self.m,self.start)
 def manifest(self):
  from ares_campaign_v3.prevalidation import prevalidate_payload
  from ares_campaign_v3.schema import Manifest
  return Manifest.from_dict(prevalidate_payload(self.draft(),self.reg))
 @contextmanager
 def admitted(self,m):
  from ares_campaign_v3 import eggbev_creation_naming as naming
  marker=self.c.CURRENT.set({'request_id':RID,'digest':m.digest})
  try:
   with patch.object(naming,'allocation',return_value=self.allocation):yield
  finally:self.c.CURRENT.reset(marker)
 def engine(self,fake):
  from ares_campaign_v3.engine import CampaignEngine
  cfg=copy.deepcopy(self.cfg);cfg['accounts'][self.c.TARGET]['marketing_api_access_tier']='standard_access'
  return CampaignEngine(cfg,transport_factory=lambda a:fake)
 def fake(self,**kw):
  from eggbev_target_fake import TargetFakeMeta
  from ares_campaign_v3.transport import BatchResult
  target=self.c.TARGET
  class CrossFake(TargetFakeMeta):
   def execute(self,operations,stage):
    crash=self.crash_seed and stage=='target_seed_create'
    if crash:self.crash_seed=False
    rows=super().execute(operations,stage)
    if crash:raise KeyboardInterrupt('simulated batch response lost after all seeds were created')
    for obj in self.objects.values():
     if obj.get('_kind')=='campaign':obj['account_id']=target
    return [BatchResult(row.name,row.code,{**row.body,'account_id':target} if row.body.get('_kind')=='campaign' else row.body) for row in rows]
  return CrossFake(**kw)
 def test_01_new_mode_shape_and_five_by_three_order(self):
  d=self.draft();m=self.manifest();self.assertEqual(len(m.campaigns),5);self.assertEqual(sum(len(c.ads) for c in m.campaigns),15)
  self.assertEqual([a.name.split(' - ')[1]+'.mp4' for c in m.campaigns for a in c.ads],[a['canonical_filename'] for a in self.assets]);self.assertTrue(all(c.mode==self.c.MODE and c.account_id==self.c.TARGET and c.cross_account_source['account_id']==self.c.SOURCE for c in m.campaigns));self.assertNotIn('reference',d['campaigns'][0])
 def test_02_preserves_source_and_fields(self):
  before=copy.deepcopy(self.source);d=self.draft();self.assertEqual(before,self.source)
  for c in d['campaigns']:
   for k,v in self.source['adset'].items():
    if k!='id':self.assertEqual(c['adset_create'][k],v)
   for i,a in enumerate(c['ads']):
    p=a['creative_payload'];self.assertEqual(p['asset_feed_spec']['bodies'][0]['text'],'Exact source body '+str(i));self.assertEqual(p['url_tags'],self.source['ads'][i]['creative']['url_tags']);self.assertEqual(p['degrees_of_freedom_spec']['creative_features_spec']['text_optimizations'],{'enroll_status':'OPT_IN','opaque':'preserve'});self.assertEqual(p['degrees_of_freedom_spec']['creative_features_spec']['image_background_gen']['enroll_status'],'OPT_OUT')
 def test_03_all_headlines_description_JSON_CTA(self):
  from ares_campaign_v3.eggbev_create import messenger_welcome_message
  for c in self.draft()['campaigns']:
   for a in c['ads']:
    af=a['creative_payload']['asset_feed_spec'];self.assertEqual([x['text'] for x in af['titles']],self.q['copy']['headlines']);self.assertEqual([x['text'] for x in af['descriptions']],[self.q['copy']['description']]);self.assertEqual(json.loads(af['additional_data']['page_welcome_message']),json.loads(messenger_welcome_message()));self.assertEqual(af['call_to_action_types'],['APPLY_NOW'])
 def test_04_another_source_target_or_Page_rejected(self):
  from ares_campaign_v3.schema import Manifest
  for key,value in [('account_id','1001115192056600'),('source_campaign_id','99999')]:
   d=self.draft();d['campaigns'][0][key]=value
   with self.assertRaises(ValueError):Manifest.from_dict(d)
  d=self.draft();d['campaigns'][0]['cross_account_source']['page_id']='99999'
  with self.assertRaises(ValueError):Manifest.from_dict(d)
 def test_05_another_request_refused(self):
  with self.assertRaises(ValueError):self.c.policy(RID+'-other')
 def test_06_policy_absence_invalid_authority(self):
  p=self.root/'policy.json';p.write_text('{}')
  with self.assertRaises(ValueError):self.c.policy(RID,path=p)
 def test_07_wrong_advertiser_or_app_rejected(self):
  from ares_campaign_v3.prevalidation import validate_account_policy
  m=self.manifest()
  for k,v in [('meta_app_id','1299247318762949'),('token_user_id','1234567890'),('token_identity','retired')]:
   cfg=copy.deepcopy(self.cfg);cfg['accounts'][self.c.TARGET][k]=v
   with self.admitted(m),self.assertRaises(ValueError):validate_account_policy(m,cfg)
 def test_08_validate_plan_no_network_writes_or_state(self):
  from ares_campaign_v3.engine import CampaignEngine
  from ares_campaign_v3.prevalidation import validate_account_policy
  m=self.manifest();before=set(self.root.rglob('*'))
  with self.admitted(m):
   validate_account_policy(m,self.cfg);plan=CampaignEngine(self.cfg,transport_factory=Mock(side_effect=AssertionError),read_only=True).dry_run(m)
  self.assertEqual(before,set(self.root.rglob('*')));self.assertEqual(plan['writes'],0);self.assertEqual(plan['campaign_count'],5);self.assertEqual(plan['network_calls'],0)
 def test_09_prestaged_source_account_never_accepted(self):
  from ares_campaign_v3.media_registry import MediaRegistry
  reg=MediaRegistry(self.root/'wrong-registry.json');a=self.assets[0]
  reg.register(account_id=self.c.SOURCE,asset_id=a['asset_id'],checksum=a['clean_checksum'],vertical_video_id='92000',square_video_id='92001',ready=True,upload_edge='ad_account_advideos',association_verified=True)
  with self.assertRaises(Exception):self.c.build(self.q,self.source,self.page,self.assets,reg,self.allocation,self.m,self.start)
 def test_10_unassociated_video_rejected(self):
  from ares_campaign_v3.prevalidation import prevalidate_payload
  d=self.draft();d['campaigns'][0]['ads'][0]['media']['association_verified']=False
  with self.assertRaises(Exception):prevalidate_payload(d,self.reg)
 def test_11_source_reader_before_any_transport_or_effect(self):
  from ares_campaign_v3.coordination import AccountWriterLeaseStore
  store=AccountWriterLeaseStore(self.cfg['state_root']);store.claim(self.c.SOURCE,'different-source-recovery',status='RECOVERY_PENDING');before=store.path(self.c.SOURCE).read_bytes()
  meta=Mock(side_effect=AssertionError);common=Mock(side_effect=AssertionError)
  with self.assertRaisesRegex(ValueError,'reader excluded'):self.c.source_read(self.q,self.m,common,meta,'synthetic',self.cfg)
  self.assertEqual(before,store.path(self.c.SOURCE).read_bytes());self.assertFalse(common.fetch_all_meta.called);self.assertFalse(meta.graph_get.called)
 def test_12_target_writer_conflict(self):
  from ares_campaign_v3.coordination import AccountWriterLeaseStore,WriterLeaseConflict
  store=AccountWriterLeaseStore(self.cfg['state_root']);store.claim(self.c.TARGET,'different-target')
  with self.assertRaises(WriterLeaseConflict):store.claim(self.c.TARGET,RID)
 def test_13_plan_writes_only_target_shells_and_local_copies(self):
  from ares_campaign_v3.planning import Planner
  plan=Planner().build(self.manifest());bundles=plan.lanes[self.c.TARGET];self.assertEqual([len(b.campaigns) for b in bundles],[2,2,1])
  for b in bundles:
   for stage in b.stages:
    for op in stage.operations:
     if op.kind in {'campaign_create','adset_create','creative_create','ad_create'}:self.assertTrue(op.relative_url.startswith('act_'+self.c.TARGET+'/'))
     if op.kind=='ad_copy_with_creative':self.assertTrue(op.relative_url.startswith('{seed_ad_id_'))
     self.assertNotIn('81001/',op.relative_url);self.assertNotIn('81003/',op.relative_url)
 def test_14_real_engine_five_campaigns_fifteen_ads_fifteen_seeds(self):
  fake=self.fake();m=self.manifest();engine=self.engine(fake)
  with self.admitted(m):result=engine.execute(m)
  self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE');self.assertEqual(len(result['campaign_ids']),5)
  ads=[x for x in fake.objects.values() if x.get('_kind')=='ad'];self.assertEqual(len(ads),30);seeds=[x for x in ads if x['status']=='PAUSED'];finals=[x for x in ads if x['status']=='ACTIVE'];self.assertEqual(len(seeds),15);self.assertEqual(len(finals),15);self.assertTrue(all(a['source_ad_id'] in {s['id'] for s in seeds} for a in finals));self.assertTrue(all(call[2]!='DELETE' for call in fake.calls))
  before=len(fake.calls)
  with self.admitted(m):self.assertTrue(engine.execute(m)['idempotent_replay'])
  self.assertEqual(before,len(fake.calls))
 def test_15_crash_seed_readback_first_missing_only(self):
  fake=self.fake(crash_seed=True);m=self.manifest();engine=self.engine(fake)
  with self.admitted(m),self.assertRaises(KeyboardInterrupt):engine.execute(m)
  before=len(fake.calls)
  with self.admitted(m):result=engine.execute(m)
  self.assertEqual(result['status'],'COMPLETE_FUTURE_ACTIVE');new=fake.calls[before:];self.assertEqual(new[0][2],'GET');self.assertEqual(len([x for x in fake.objects.values() if x.get('_kind')=='campaign']),5);self.assertEqual(len([x for x in fake.objects.values() if x.get('_kind')=='ad']),30)
 def test_16_QA_Page_divergence_holds_parent_PAUSED(self):
  fake=self.fake(wrong_final=True);m=self.manifest()
  with self.admitted(m),self.assertRaises(ValueError):self.engine(fake).execute(m)
  self.assertTrue(all(x['status']=='PAUSED' for x in fake.objects.values() if x.get('_kind')=='campaign'))
 def test_17_final_OK_gate_Engine_cannot_be_bypassed(self):
  fake=self.fake();m=self.manifest()
  with self.assertRaisesRegex(ValueError,'fresh final approval'):
   from ares_campaign_v3 import eggbev_creation_naming as naming
   with patch.object(naming,'allocation',return_value=self.allocation):self.engine(fake).execute(m)
  self.assertFalse(fake.calls)
 def test_18_source_primary_missing_or_ambiguous_rejected(self):
  for cr in [{},{'asset_feed_spec':{'bodies':[{'text':'a'},{'text':'b'}]}},{'asset_feed_spec':{'bodies':[{'text':'a'}]},'object_story_spec':{'video_data':{'message':'b'}}}]:
   with self.assertRaises(ValueError):self.c.primary_text(cr)
 def test_19_order_and_cardinality_rejected(self):
  for assets in [self.assets[:-1],list(reversed(self.assets)),[self.assets[0]]*15]:
   with self.assertRaises(ValueError):self.c.build(self.q,self.source,self.page,assets,self.reg,self.allocation,self.m,self.start)
 def test_20_foreign_mode_cannot_carry_cross_reference(self):
  from ares_campaign_v3.schema import CampaignSpec
  d=self.draft()['campaigns'][0];d['mode']='clone_target_prestaged'
  with self.assertRaisesRegex(ValueError,'another mode'):CampaignSpec.from_dict(d)
 def test_21_real_scope_metadata_grant_self_only(self):
  guard=self.m.module('offline_guard',R/'scripts/mgs-ares-asset-scope.py')
  guard.enforce_credential_metadata('me',{'fields':'id,name'},'GET',self.c.TARGET,'synthetic')
  grant=guard._credential_identity_policy(self.c.TARGET)['technical_identity_validation']
  guard.observe_credential_metadata('debug_token',{'input_token':'synthetic'},{'data':{'is_valid':True,'app_id':grant.get('expected_app_id',self.c.APP),'user_id':self.c.USER,'type':grant.get('expected_token_type','USER')}},self.c.TARGET,'synthetic')
  for path,params,method in [('me/accounts',{'fields':'id'},'GET'),('debug_token',{'input_token':'other'},'GET'),('me',{'fields':'id,name'},'POST')]:
   with self.assertRaises(ValueError):guard.enforce_credential_metadata(path,params,method,self.c.TARGET,'synthetic')
 def test_22_Page_exact_SB_Meta_and_ephemeral_context(self):self.page_case()
 def page_case(self,rows=None,page_id='82001',grant=True,pbia=True):
  from ares_campaign_v3 import eggbev_page_identity as p
  sb=Mock();sb.api_request.return_value=(200,rows if rows is not None else [{'UTM_CAMPAIGN':'pg_23187','FB_PAGE_ID':'82001','PAGE_NAME':'Moorcroft Finances'}],{})
  guard=self.m.module('offline_page_guard',R/'scripts/mgs-ares-asset-scope.py');calls=[]
  class Meta:
   def graph_get(_,path,token,params):
    guard.enforce_meta_path(path,params,'GET');calls.append(path)
    if '/' in path:return 200,{'data':[{'id':'82002'}] if pbia else []},{}
    return (200,{'id':page_id,'name':'Moorcroft Finances',**({'access_token':'synthetic'} if grant else {})},{})
   def graph_post_once(*a):raise AssertionError('no PBIA write')
  try:
   result=p.resolve(Meta(),sb,'synthetic',self.c.TARGET,'pg_23187',authority_path=self.c.POLICY,request_path=REQ)
   self.assertNotIn('access_token',json.dumps(result));self.assertEqual(result['id'],'82001');self.assertEqual(len(calls),2);return result
  finally:self.assertIsNone(p.CURRENT.get())
 def test_23_SB_absence(self):
  with self.assertRaisesRegex(ValueError,'missing or ambiguous'):self.page_case(rows=[])
 def test_24_SB_ambiguity(self):
  row={'UTM_CAMPAIGN':'pg_23187','FB_PAGE_ID':'82001','PAGE_NAME':'Moorcroft Finances'}
  with self.assertRaisesRegex(ValueError,'missing or ambiguous'):self.page_case(rows=[row,row])
 def test_25_Page_mismatch(self):
  with self.assertRaisesRegex(ValueError,'mismatch'):self.page_case(page_id='82099')
 def test_26_Page_grant_absence(self):
  with self.assertRaisesRegex(ValueError,'Access Token'):self.page_case(grant=False)
 def test_27_PBIA_empty_no_initialization(self):
  with self.assertRaisesRegex(ValueError,'PBIA unavailable'):self.page_case(pbia=False)
 def test_28_Page_denylist(self):
  from ares_campaign_v3 import eggbev_page_eligibility as e
  with patch.object(e,'load_denylist',return_value={'pages':{'pg_23187':{'fb_page_id':'82001'}}}),self.assertRaises(Exception):self.page_case()
 def test_29_other_Page_or_initialization_refused_before_SB(self):
  from ares_campaign_v3 import eggbev_page_identity as p
  sb=Mock()
  for pg,ensure in [('pg_23189',False),('pg_23187',True)]:
   with self.assertRaises(ValueError):p.resolve(Mock(),sb,'synthetic',self.c.TARGET,pg,authority_path=self.c.POLICY,request_path=REQ,ensure_pbia=ensure)
  self.assertFalse(sb.api_request.called)
 def test_30_request_mutations_refused(self):
  for k,v in [('target_account_id',self.c.SOURCE),('duplicate_count',4),('budget_usd_per_campaign','40'),('source_mutation_authorized',True)]:
   q=copy.deepcopy(self.q);q[k]=v;p=self.root/'request.json';p.write_text(json.dumps(q))
   with self.assertRaises(ValueError):self.c.request_load(p)
 def test_31_request_raw_unchanged(self):self.assertEqual(self.c.request_load(REQ),self.q)
 def test_32_source_reader_context_not_a_Page_grant(self):
  from ares_campaign_v3.eggbev_page_identity import dependency
  with self.c.reader(self.c.SOURCE,self.cfg):self.assertIsNone(dependency('82001'))
 def test_33_dev_quota_defers_remaining_without_source_lane(self):
  fake=self.fake();m=self.manifest();from ares_campaign_v3.engine import CampaignEngine
  engine=CampaignEngine(self.cfg,transport_factory=lambda a:fake)
  with self.admitted(m):result=engine.execute(m)
  self.assertEqual(result['status'],'PARTIAL_DEFERRED_QUOTA');self.assertEqual(result['deferred_accounts'],[self.c.TARGET]);self.assertEqual(len(result['campaign_ids']),2);self.assertFalse(list((self.root/'state').glob('checkpoints/*'+self.c.SOURCE+'*')))
 def test_34_unscoped_legacy_route_unchanged(self):
  from test_eggbev_target_page_clone import specimen
  from ares_campaign_v3.schema import CampaignSpec
  self.assertEqual(CampaignSpec.from_dict(specimen()).mode,'clone_target_prestaged')
 def test_35_require_source_Page_preserved_build(self):
  page=copy.deepcopy(self.page);page['id']='99999'
  with self.assertRaises(ValueError):self.c.build(self.q,self.source,page,self.assets,self.reg,self.allocation,self.m,self.start)
 def test_36_preparation_blocked_before_runtime(self):
  from ares_campaign_v3.coordination import AccountWriterLeaseStore
  AccountWriterLeaseStore(self.cfg['state_root']).claim(self.c.SOURCE,'source-recovery',status='RECOVERY_PENDING')
  with patch.object(self.c,'load',side_effect=lambda p:self.cfg if p==self.m.CONFIG else json.loads(Path(p).read_text())),patch.object(self.c,'runtime') as rt,self.assertRaisesRegex(ValueError,'reader excluded'):self.c.prepare(REQ,self.m,True)
  self.assertFalse(rt.called)
 def test_37_final_summary_OK_missing_delivery_receipt(self):
  with patch.object(self.c,'home_for',return_value=self.root),self.assertRaises(FileNotFoundError):self.c.final_approval(self.q,{},Mock(),'999999999999999999','a'*64)
 def test_38_installed_account03_modes_have_separate_scoped_authorities(self):
  a=self.cfg['accounts'][self.c.TARGET];self.assertIn(self.c.MODE,a['supported_modes']);self.assertTrue(a['cross_account_clone']['enabled']);self.assertEqual(a['meta_app_id'],self.c.APP)
  extras=set(a['supported_modes'])-{self.c.MODE}
  self.assertLessEqual(extras,{'clone_target_prestaged'})
  if extras:
   cap=a['target_page_replacement'];self.assertTrue(cap['enabled']);self.assertEqual(cap['account_id'],self.c.TARGET);self.assertEqual(cap['authorized_by'],self.c.CEO)
   policy=json.loads((R/cap['policy_source']).read_text());self.assertTrue(policy['request_only']);self.assertFalse(policy['future_requests_authorized'])
   self.assertEqual(set(cap['allowed_request_ids']),set(policy['requests']));self.assertEqual(cap['authority_message_id'],policy['authority_message_id'])
 def test_39_validate_capability_rejects_missing_or_changed_JSON(self):
  from ares_campaign_v3.schema import Manifest
  from ares_campaign_v3.prevalidation import validate_account_policy
  d=self.draft();d['campaigns'][2]['ads'][1]['creative_payload']['asset_feed_spec']['additional_data']['page_welcome_message']='{}';m=Manifest.from_dict(d)
  with self.admitted(m),self.assertRaises(ValueError):validate_account_policy(m,self.cfg)
 def test_40_source_fields_survive_plan(self):
  from ares_campaign_v3.planning import Planner
  m=self.manifest();p=Planner().build(m)
  for b in p.lanes[self.c.TARGET]:
   for c in b.campaigns:self.assertEqual(c.adset_create['bid_constraints'],{'roas_average_floor':10});self.assertEqual(c.adset_create['promoted_object']['custom_event_str'],'eggbev-pv-u')

 def test_41_preserved_real_source_all_fifteen_slots_to_plan(self):
  from ares_campaign_v3.prevalidation import prevalidate_payload,validate_account_policy
  from ares_campaign_v3.schema import Manifest
  from ares_campaign_v3.engine import CampaignEngine
  source=json.loads((R/'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937/source-live.json').read_text());before=copy.deepcopy(source)
  page=copy.deepcopy(self.page);page['id']=source['adset']['promoted_object']['page_id'];allocation={**self.allocation,'page_id':page['id']}
  raw=self.c.build(self.q,source,page,self.assets,self.reg,allocation,self.m,self.start);m=Manifest.from_dict(prevalidate_payload(raw,self.reg))
  from ares_campaign_v3 import eggbev_creation_naming as naming
  with patch.object(naming,'allocation',return_value=allocation):
   validate_account_policy(m,self.cfg);plan=CampaignEngine(self.cfg,transport_factory=Mock(side_effect=AssertionError),read_only=True).dry_run(m)
  self.assertEqual(plan['campaign_count'],5);self.assertEqual(source,before);self.assertEqual(len([a for c in raw['campaigns'] for a in c['ads']]),15)
 def approval_fixture(self):
  import hashlib
  m=self.manifest();payload=m.raw;seal=payload['prevalidation']['content_digest'];summary={'digest':seal,'request_sha256':self.c.digest(self.q),'names':self.allocation['names'],'final_campaigns':5,'final_ads':15,'technical_paused_seeds':15}
  content='\n'.join([seal,*summary['names'],'JSON-AGT / 15 PAUSED seeds / 15 final ads / USD35 each / USD175 total'])
  sent={'id':'1571659999999999000','channel_id':self.q['source_thread_id'],'author':{'id':'1508864261504630925','bot':True},'content':content,'timestamp':'2026-11-16T20:00:00+00:00'}
  ok={'id':'1571659999999999999','channel_id':self.q['source_thread_id'],'author':{'id':self.c.ACTOR,'bot':False},'content':'OK','timestamp':'2026-11-16T20:01:00+00:00','message_reference':{'message_id':sent['id']}}
  self.m.save(self.root/'manifest.json',payload);self.m.save(self.root/'summary-delivery.json',{'request_id':RID,'digest':seal,'message_id':sent['id'],'content_sha256':hashlib.sha256(content.encode()).hexdigest()})
  common=Mock();common.discord_request.side_effect=lambda method,path:(200,copy.deepcopy(ok if path.endswith(ok['id']) else sent))
  return summary,sent,ok,common
 def test_42_fresh_final_OK_exact_summary_accepted(self):
  summary,sent,ok,common=self.approval_fixture()
  with patch.object(self.c,'home_for',return_value=self.root):payload=self.c.final_approval(self.q,summary,common,ok['id'],summary['digest'])
  self.assertEqual(payload['request_id'],RID);self.assertEqual(common.discord_request.call_count,2)
 def test_43_wrong_author_and_bot_OK_denied(self):
  for change in [{'id':'99999999999999999','bot':False},{'id':self.c.ACTOR,'bot':True}]:
   summary,sent,ok,common=self.approval_fixture();ok['author']=change
   with patch.object(self.c,'home_for',return_value=self.root),self.assertRaises(ValueError):self.c.final_approval(self.q,summary,common,ok['id'],summary['digest'])
 def test_44_wrong_digest_and_early_OK_denied(self):
  summary,sent,ok,common=self.approval_fixture()
  with patch.object(self.c,'home_for',return_value=self.root),self.assertRaises(ValueError):self.c.final_approval(self.q,summary,common,ok['id'],'0'*64)
  ok['timestamp']='2026-11-16T19:00:00+00:00'
  with patch.object(self.c,'home_for',return_value=self.root),self.assertRaises(ValueError):self.c.final_approval(self.q,summary,common,ok['id'],summary['digest'])
 def test_45_unreferenced_OR_edited_OK_denied(self):
  for change in [{'message_reference':{}},{'edited_timestamp':'2026-11-16T21:00:00+00:00'}]:
   summary,sent,ok,common=self.approval_fixture();ok.update(change)
   with patch.object(self.c,'home_for',return_value=self.root),self.assertRaises(ValueError):self.c.final_approval(self.q,summary,common,ok['id'],summary['digest'])
 def test_46_provenance_cached_source_Page_exact_context_only(self):
  guard=self.m.module('cross_cache_guard',R/'scripts/mgs-ares-asset-scope.py')
  from ares_campaign_v3 import eggbev_page_identity as p
  row={'source':'scoped_graph_dependency','kind':'page','account_ids':[self.c.SOURCE]};data=guard.load_scope()
  marker=p.CURRENT.set({'account_id':self.c.TARGET,'page_id':'82001','request_id':RID,'page_token':'pg_23187','ensure_pbia':False})
  try:
   with patch.object(guard,'_objects',return_value={'82001':row}):self.assertEqual(guard._dependency_for_node('82001',data)['account_ids'],[self.c.TARGET])
   for wrong in [{'source':'scoped_graph_response','kind':'page','account_ids':[self.c.SOURCE]},{'source':'scoped_graph_dependency','kind':'video','account_ids':[self.c.SOURCE]},{'source':'scoped_graph_dependency','kind':'page','account_ids':['1001115192056600']}]:
    with patch.object(guard,'_objects',return_value={'82001':wrong}),self.assertRaises(ValueError):guard._dependency_for_node('82001',data)
  finally:p.CURRENT.reset(marker)
 def test_47_live_wrong_advertiser_metadata_rejected(self):
  meta=Mock();meta.graph_get_credential_metadata.side_effect=[(200,{'id':'wrong','name':'Ana Cunha'},{}),(200,{'data':{'app_id':self.c.APP,'user_id':self.c.USER,'type':'USER','is_valid':True}}, {})]
  with self.assertRaisesRegex(ValueError,'advertiser/app'):self.c.verify_advertiser(meta,'synthetic')
 def test_48_uncertain_zero_readback_never_POST_replay(self):
  from ares_campaign_v3.target_page_clone import _adopt_uncertain
  from ares_campaign_v3.transport import BatchOperation
  from ares_campaign_v3.planning import Planner
  fake=self.fake();engine=self.engine(fake);b=Planner().build(self.manifest()).lanes[self.c.TARGET][0]
  op=BatchOperation('target_seed_create_1_1','POST','act_'+self.c.TARGET+'/ads',{'name':'missing','adset_id':'none','creative':{'creative_id':'123'}},kind='ad_create')
  with self.assertRaisesRegex(ValueError,'no POST replay'):_adopt_uncertain(engine,b,fake,op,{})
  self.assertTrue(fake.calls);self.assertTrue(all(c[2]=='GET' for c in fake.calls))

class MissingModeRedTests(unittest.TestCase):
 def test_new_mode_is_not_from_zero(self):
  from ares_campaign_v3.schema import CampaignSpec
  from test_eggbev_target_page_clone import specimen
  d=specimen();d['mode']='clone_cross_account_prestaged';d['account_id']='1481815942722118';d['cross_account_source']={'account_id':'1034081997659047','campaign_id':'81001','adset_id':'81002','ad_ids':['81003'],'page_id':'82001','page_token':'pg_23187','access':'READ_ONLY','semantics':'source_derived_shell_local_seed_copy','snapshot_sha256':'a'*64}
  self.assertEqual(CampaignSpec.from_dict(d).mode,'clone_cross_account_prestaged')

if __name__=='__main__':unittest.main()
