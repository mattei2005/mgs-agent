import sys,json,tempfile,unittest,copy,concurrent.futures,importlib.util
from pathlib import Path
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3 import eggbev_creation_naming as n
from ares_campaign_v3.eggbev_create import build_eggbev_from_zero_manifest
from ares_campaign_v3.media_registry import MediaRegistry
class NamingTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch');self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)/'numbers.json';self.policy=n.load_policy();self.policy['ledger_path']=str(self.path);self.ids=self.policy['account_ids'];self.snap={aid:{'complete':True,'account':{'id':'act_'+aid},'campaigns':[],'read_at':datetime.now(timezone.utc).isoformat()} for aid in self.ids};self.identity={'page_token':'pg_23156','page_id':'1364201870103565','page_name':'Georgina Whitford'}
 def reserve(self,request,account=None,count=1,identity=None):return n.reserve(request,account or self.ids[0],identity or self.identity,count,self.snap,policy=self.policy,ledger_path=self.path)
 def test_exact_example(self):self.assertEqual(n.format_name(300,'Georgina Whitford','pg_23156',1),'300 - Georgina Whitford - ENG - US - (pg_23156) - C01')
 def test_three_accounts_share_one_sequence(self):
  results=[self.reserve('r'+str(i),a) for i,a in enumerate(self.ids)];self.assertEqual([x['global_numbers'][0] for x in results],[300,301,302]);self.assertEqual([x['page_sequences'][0] for x in results],[1,2,3])
 def test_332_then_other_account_333(self):
  self.snap[self.ids[0]]['campaigns']=[{'id':'12345','name':'332 - Georgina Whitford - ENG - US - (pg_23156) - C01','status':'ACTIVE'}];self.assertEqual(self.reserve('next',self.ids[1])['global_numbers'],[333])
 def test_batch_sequential_names(self):
  row=self.reserve('batch',count=3);self.assertEqual(row['global_numbers'],[300,301,302]);self.assertEqual(row['page_sequences'],[1,2,3]);self.assertTrue(row['names'][2].endswith('- C03'))
 def test_page_counter_cross_account_historical_C001(self):
  self.snap[self.ids[2]]['campaigns']=[{'id':'1','name':'219 - Georgina Whitford - ENG - US - (pg_23156) C017','status':'ACTIVE'}];row=self.reserve('next');self.assertEqual(row['global_numbers'],[300]);self.assertEqual(row['page_sequences'],[18])
 def test_replay_idempotent(self):self.assertEqual(self.reserve('same'),self.reserve('same'));self.assertEqual(len(json.loads(self.path.read_text())['allocations']),1)
 def test_replay_different_count_rejected(self):
  self.reserve('same')
  with self.assertRaises(n.NamingError):self.reserve('same',count=2)
 def test_no_account_expansion(self):
  with self.assertRaises(n.NamingError):self.reserve('bad',account='999999999')
 def test_three_histories_mandatory(self):
  self.snap.pop(self.ids[1])
  with self.assertRaises(n.NamingError):self.reserve('bad')
  self.assertFalse(self.path.exists())
 def test_stale_history_rejected(self):
  self.snap[self.ids[2]]['read_at']=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
  with self.assertRaises(n.NamingError):self.reserve('bad')
 def test_identity_lookup(self):
  row={'UTM_CAMPAIGN':'pg_23156','FB_PAGE_ID':'1364201870103565','PAGE_NAME':'Georgina Whitford'};self.assertEqual(n.reconcile_page([row],{'id':row['FB_PAGE_ID'],'name':row['PAGE_NAME']},'pg_23156'),self.identity)
 def test_name_or_id_mismatch_rejected(self):
  row={'UTM_CAMPAIGN':'pg_23156','FB_PAGE_ID':'1364201870103565','PAGE_NAME':'Georgina Whitford'}
  for page in [{'id':'99999','name':'Georgina Whitford'},{'id':'1364201870103565','name':'Other Page'}]:
   with self.subTest(page=page),self.assertRaises(n.NamingError):n.reconcile_page([row],page,'pg_23156')
 def test_ambiguous_pg_rejected(self):
  row={'UTM_CAMPAIGN':'pg_23156','FB_PAGE_ID':'1364201870103565','PAGE_NAME':'Georgina Whitford'}
  with self.assertRaises(n.NamingError):n.reconcile_page([row,row],{'id':row['FB_PAGE_ID'],'name':row['PAGE_NAME']},'pg_23156')
 def test_parallel_unique_allocation(self):
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(lambda i:self.reserve('parallel-'+str(i),self.ids[i%3]),range(18)))
  self.assertEqual(sorted(x['global_numbers'][0] for x in rows),list(range(300,318)));self.assertEqual(len(json.loads(self.path.read_text())['allocations']),18)
 def test_no_live_number_consumed_by_preview(self):
  self.assertEqual(n.plan_numbers('pg_23156',1,self.snap,{},policy=self.policy),([300],[1]));self.assertFalse(self.path.exists())
 def test_historical_requests_keep_old_contract(self):self.assertFalse(n.applies('2026-08-01T00:00:00Z',self.ids[0],self.policy))
 def test_live_collision_before_write(self):
  self.reserve('reserved');self.snap[self.ids[1]]['campaigns']=[{'id':'1','name':'300 - Other Page - ENG - US - (pg_99999) - C01','status':'ACTIVE'}]
  with self.assertRaises(n.NamingError):n.verify_live_reservation('reserved',self.snap,self.policy)
 def manifest(self):
  row=self.reserve('manifest');payload={'object_story_spec':{'page_id':self.identity['page_id']},'url_tags':'utm_campaign=pg_23156'};c=SimpleNamespace(mode='from_zero_prestaged',account_id=self.ids[0],name=row['names'][0],adset_name='ADGROUP 01',adset_create={'promoted_object':{'page_id':self.identity['page_id']}},ads=[SimpleNamespace(creative_payload=payload)]);return SimpleNamespace(request_id='manifest',created_at=datetime.now(timezone.utc).isoformat(),campaigns=[c])
 def test_validator_exact_identity(self):n.validate_manifest(self.manifest(),self.policy)
 def test_validator_wrong_utm(self):
  m=self.manifest();m.campaigns[0].ads[0].creative_payload['url_tags']='utm_campaign=pg_99999'
  with self.assertRaises(n.NamingError):n.validate_manifest(m,self.policy)
 def test_validator_wrong_adgroup(self):
  m=self.manifest();m.campaigns[0].adset_name='AdG1'
  with self.assertRaises(n.NamingError):n.validate_manifest(m,self.policy)
 def test_live_reader_only_three_direct_accounts(self):
  paths=[]
  class Reader:
   def graph_get(inner,path,token,params):
    paths.append(path)
    if path.endswith('/campaigns'):return 200,{'data':[]},{}
    return 200,{'id':path},{}
  got=n.collect_history(Reader(),'synthetic-token',self.policy);self.assertEqual(set(got),set(self.ids));self.assertEqual(len(paths),6);self.assertTrue(all(x.split('/')[0] in ['act_'+a for a in self.ids] for x in paths))
 def test_materializer_new_names_and_adgroup(self):
  registry=MediaRegistry(Path(self.temp.name)/'media.json');refs=[]
  for i in range(6):
   aid='synthetic-'+str(i);checksum=('%064x'%i);registry.register(account_id=self.ids[0],asset_id=aid,checksum=checksum,vertical_video_id=str(10000+i),square_video_id=str(20000+i),ready=True,source='offline-test-only',upload_edge='ad_account_advideos',association_verified=True);refs.append({'asset_id':aid,'checksum':checksum})
  built=build_eggbev_from_zero_manifest(registry=registry,request_id='offline-only',page_id=self.identity['page_id'],instagram_user_id='1234567',page_name=self.identity['page_name'],page_token=self.identity['page_token'],page_sequence=300,campaign_sequences=[1,2],daily_budgets_minor=[3000,3000],start_time=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),asset_refs=refs,ad_names=['AD '+str(i) for i in range(6)],campaign_numbers=[300,301],adset_name='ADGROUP 01');self.assertEqual([x['name'] for x in built['campaigns']],[n.format_name(300,'Georgina Whitford','pg_23156',1),n.format_name(301,'Georgina Whitford','pg_23156',2)]);self.assertTrue(all(x['adset_name']=='ADGROUP 01' for x in built['campaigns']))
if __name__=='__main__':unittest.main()
