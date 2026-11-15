"""Ana/m6 maintenance regressions. Synthetic data stays in isolated scratch."""
import copy,hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
S=Path(__file__).resolve().parents[1]/'scripts';sys.path.insert(0,str(S))
from ares_campaign_v3.coordination import AccountWriterLeaseStore,reader_block_reason,WriterLeaseConflict
from ares_campaign_v3 import operator_suspension as suspension

def module(name,filename):
 spec=importlib.util.spec_from_file_location(name,S/filename);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class IntegrationTests(unittest.TestCase):
 def test_build_derives_exact_account_app_and_missing_binding_fails(self):
  m=module('ana_build','ares-eggbev-target-clone.py');source={'campaign':{k:[] for k in ['objective','buying_type','bid_strategy','special_ad_categories','special_ad_category_country']},'adset':{'id':'100','promoted_object':{'page_id':'200'}},'ads':[]}
  source['campaign']['id']='12345'
  q={'daily_budget_usd':'35','request_id':'offline-ana-build','operation':'Eggbev-US-CC-EN-BOT','start_time':'2099-01-01T00:02:00-05:00'}
  for key in ['mgs-meta-app-953171080682697','test-different-app']:
   with patch.object(m,'load',return_value={'accounts':{m.ACCOUNT:{'app_key':key}}}):
    self.assertEqual(m.build(q,source,{'id':'300'},[],None,{'names':['offline']})['campaigns'][0]['app_key'],key)
  with patch.object(m,'load',return_value={'accounts':{m.ACCOUNT:{}}}):
   with self.assertRaises(KeyError):m.build(q,source,{'id':'300'},[],None,{'names':['offline']})
 def test_new_app_manifest_plan_without_prepare(self):
  from test_eggbev_target_page_clone import specimen
  from ares_campaign_v3.eggbev_create import messenger_welcome_message
  from ares_campaign_v3.media_registry import MediaRegistry
  from ares_campaign_v3.prevalidation import prevalidate_payload,validate_account_policy
  from ares_campaign_v3.schema import Manifest
  from ares_campaign_v3.engine import CampaignEngine
  from datetime import datetime,timezone
  cfg_path=Path(__file__).resolve().parents[2]/'staged/data/ares/meta-ads/engine-v3/config.json'
  if not cfg_path.exists():cfg_path=Path('/root/mgs-agent/data/ares/meta-ads/engine-v3/config.json')
  cfg=json.loads(cfg_path.read_text());c=specimen();c['app_key']=cfg['accounts'][suspension.ACCOUNT]['app_key'];self.assertEqual(c['app_key'],'mgs-meta-app-953171080682697')
  c['ads'][0]['creative_payload']['asset_feed_spec']['additional_data']={'page_welcome_message':messenger_welcome_message()}
  with tempfile.TemporaryDirectory() as t:
   cfg=copy.deepcopy(cfg);cfg['state_root']=str(Path(t)/'state');cfg['audit_root']=str(Path(t)/'audit')
   registry=MediaRegistry(Path(t)/'registry.json');media=c['ads'][0]['media']
   registry.register(account_id=suspension.ACCOUNT,asset_id=media['asset_id'],checksum=media['checksum'],vertical_video_id=media['vertical_video_id'],square_video_id=media['square_video_id'],ready=True,upload_edge='ad_account_advideos',association_verified=True,source='offline-test-only')
   draft={'schema_version':3,'request_id':'offline-ana-dry-run','operation':'Eggbev-US-CC-EN-BOT','graph_version':'v26.0','created_at':datetime.now(timezone.utc).isoformat(),'campaigns':[c]}
   manifest=Manifest.from_dict(prevalidate_payload(draft,registry))
   from ares_campaign_v3 import eggbev_creation_naming as naming
   synthetic={'count':1,'account_id':suspension.ACCOUNT,'names':[c['name']],'page_id':'82001','page_token':'pg_23186'}
   with patch.object(naming,'allocation',return_value=synthetic):
    validate_account_policy(manifest,cfg)
    plan=CampaignEngine(cfg,transport_factory=lambda account:None).dry_run(manifest)
   self.assertTrue(plan)
   wrong=copy.deepcopy(cfg);wrong['accounts'][suspension.ACCOUNT]['app_key']='mgs-meta-app-1299247318762949'
   with self.assertRaises(Exception):validate_account_policy(manifest,wrong)
 def test_cache_account_opt_in_and_item_mismatch_never_reuses(self):
  m=module('ana_cache','ares-meta-common.py');old=m.TOKEN_CACHE_PATH
  m.configure_account_cache({});self.assertEqual(m.TOKEN_CACHE_PATH,old)
  m.configure_account_cache({'token_cache_path':'/root/.cache/mgs/ares-meta-token-eggbev01-ana-m6.json'})
  self.assertEqual(m.TOKEN_CACHE_LOCK_PATH,Path(str(m.TOKEN_CACHE_PATH)+'.lock'))
  with self.assertRaises(ValueError):m.configure_account_cache({'token_cache_path':'/other/unsafe.json'})
  with tempfile.TemporaryDirectory() as t:
   m.TOKEN_CACHE_PATH=Path(t)/'cache.json';m.TOKEN_CACHE_PATH.write_text(json.dumps({'item':'old-profile','token':'synthetic-only','cached_at':__import__('time').time()}));m.TOKEN_CACHE_PATH.chmod(0o600)
   self.assertIsNone(m._read_token_cache('new-profile'))
 def make(self,root):
  pins={}
  for name in ['checkpoints/preserved.json','target-continuations/preserved.json','historical-audit/preserved.json']:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{"historical_ids":["123"]}');pins[name]=hashlib.sha256(p.read_bytes()).hexdigest()
  receipt={'account_id':suspension.ACCOUNT,'request_id':suspension.REQUEST,'status':suspension.STATUS,'authority_message_ids':['1570338387380936737','1570343663307989043'],'campaign_qa_complete':False,'meta_writes':0,'reservation_release':False,'recorded_at':'offline','record_pins':pins}
  p=suspension.path(root,suspension.ACCOUNT,suspension.REQUEST);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(receipt))
  store=AccountWriterLeaseStore(root);lp=store.path(suspension.ACCOUNT);lp.write_text(json.dumps({'account_id':suspension.ACCOUNT,'request_id':suspension.REQUEST,'status':'RECOVERY_PENDING','blocks_readers':True,'historical':'preserved'}))
  return store,hashlib.sha256(lp.read_bytes()).hexdigest()
 def test_suspend_cas_receipt_and_new_reader_admission_no_qa(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);store,sha=self.make(root)
   with self.assertRaises(WriterLeaseConflict):store.suspend_operator(suspension.ACCOUNT,suspension.REQUEST,expected_sha256='0'*64)
   result=store.suspend_operator(suspension.ACCOUNT,suspension.REQUEST,expected_sha256=sha)
   self.assertEqual(result['status'],suspension.STATUS);self.assertFalse(result['campaign_qa_complete']);self.assertEqual(result['historical'],'preserved')
   self.assertIsNone(reader_block_reason(suspension.ACCOUNT,root))
   with self.assertRaises(ValueError):store.claim(suspension.ACCOUNT,suspension.REQUEST)
   store.claim(suspension.ACCOUNT,'offline-new-ana-request');self.assertEqual(reader_block_reason(suspension.ACCOUNT,root)['request_id'],'offline-new-ana-request')
   with self.assertRaises(ValueError):store.claim(suspension.ACCOUNT,suspension.REQUEST)
 def test_corrupt_receipt_blocks_reader_and_new_claim(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);store,sha=self.make(root);store.suspend_operator(suspension.ACCOUNT,suspension.REQUEST,expected_sha256=sha)
   suspension.path(root,suspension.ACCOUNT,suspension.REQUEST).write_text('{}')
   self.assertEqual(reader_block_reason(suspension.ACCOUNT,root)['source'],'operator_suspension_invalid')
   with self.assertRaises(WriterLeaseConflict):store.claim(suspension.ACCOUNT,'offline-new-ana-request')
   with self.assertRaises(ValueError):suspension.deny_replay(root,suspension.ACCOUNT,suspension.REQUEST)
 def test_other_account_unaffected(self):
  with tempfile.TemporaryDirectory() as t:
   store=AccountWriterLeaseStore(t);self.make(Path(t));self.assertEqual(store.claim('1001115192056600','offline-other-account')['status'],'IN_PROGRESS')

if __name__=='__main__':unittest.main()
