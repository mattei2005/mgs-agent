"""Offline retirement safety fixtures; no network or real deletion permitted."""
import unittest,importlib.util,sys,copy
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
class RetirementTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  spec=importlib.util.spec_from_file_location('retirement_offline',ROOT/'scripts/ares_archive_retirement.py');assert spec and spec.loader;cls.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.m)
 def setUp(self):
  b=self.m.b;self.c={'account':b.ACCOUNT,'source_drive_id':b.SOURCE_DRIVE,'source_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'delete_source':False,'include_historical':False,'queue_enabled':True,'prefer_archive_reads':True,'effective_after':'2026-10-20T14:00:00Z'}
  def asset(role,sid,status):return {'role':role,'sourceId':sid,'sourceParentId':'parentOffline001','name':role+'.png','mimeType':'image/png','size':'20','md5':'b'*32,'sha256':'a'*64,'version':'1','relativeParent':['SHEIN_US_ES','IMG',status],'sourceCreatedTime':'2026-10-20T15:00:00Z'}
  self.job={'jobId':'a'*32,'kind':'lineage','lineageId':'assetOffline001','deleteSource':False,'assets':[asset('original','rawOffline001','99_LEGACY'),asset('clean','cleanOffline001','01_READY')]}
  entries=[{**a,'archiveId':'archive'+a['sourceId'],'lineageId':self.job['lineageId'],'jobId':self.job['jobId'],'stockShortcutId':'shortcut'+a['sourceId'],'verified':True,'owner':b.ACCOUNT,'md5':a['md5']} for a in self.job['assets']]
  self.index={'verified_jobs':{self.job['jobId']:{'kind':'lineage','status':'verified','jobId':self.job['jobId'],'assets':entries}},'mappings':{a['sourceId']:a for a in entries}}
  self.row={'asset_id':'assetOffline001','source_drive_id':'rawOffline001','asset_drive_id':'cleanOffline001','original_checksum':'a'*64,'clean_checksum':'a'*64,'metadata_clean':True,'first_seen_at':'2026-10-20T15:00:00Z','operation':'SHEIN_US_ES','format':'IMG'}
  self.state={'claims':{'batchOffline001':{'status':'complete','completed_at':'2026-10-20T16:00:00Z','batch':{'sources':[{'source_id':'rawOffline001'}]}}}}
 def ready(self,now='2026-10-22T16:00:00Z'):
  return self.m.candidate_ready(self.job,self.index,[self.row],self.state,self.c,now,'2026-10-20T16:00:00Z')
 def test_full_new_pair_ready_after_retention(self):self.assertEqual(self.ready()['row']['asset_id'],'assetOffline001')
 def test_retention_never_bypassed_for_operational_now(self):
  with self.assertRaises(self.m.NotReady):self.ready('2026-10-20T17:00:00Z')
 def test_validation_pair_never_eligible(self):
  self.job['validationOnly']=True
  with self.assertRaises(self.m.RetirementError):self.ready()
 def test_historical_never_eligible(self):
  self.row['first_seen_at']='2026-10-19T12:00:00Z'
  with self.assertRaises(self.m.RetirementError):self.ready()
 def test_same_bytes_historical_source_never_eligible(self):
  self.job['assets'][0]['sourceCreatedTime']='2026-10-19T12:00:00Z'
  with self.assertRaises(self.m.RetirementError):self.ready()
 def test_not_a_full_pair_blocked(self):
  self.job['assets'].pop()
  with self.assertRaises(self.m.RetirementError):self.ready()
 def test_folder_or_shortcut_never_deleted(self):
  self.job['assets'][0]['mimeType']='application/vnd.google-apps.shortcut'
  with self.assertRaises(self.m.RetirementError):self.ready()
 def test_manager_and_control_paths_excluded(self):
  self.job['assets'][1]['relativeParent']=['SHEIN_US_ES','IMG','Nicolas']
  with self.assertRaises(self.m.RetirementError):self.ready()
 def test_unreleased_batch_waits(self):
  self.state['claims']['batchOffline001']['status']='treated_waiting_archive'
  with self.assertRaises(self.m.NotReady):self.ready()
 def test_missing_alias_waits(self):
  self.index['mappings']['cleanOffline001'].pop('stockShortcutId')
  with self.assertRaises(self.m.NotReady):self.ready()
 def test_changed_lineage_checksum_blocks(self):
  self.row['clean_checksum']='d'*64
  with self.assertRaises(self.m.RetirementError):self.ready()
 def test_unsafe_config_true_without_pinned_authority_rejected(self):
  with self.assertRaises(self.m.RetirementError):self.m.validate_active_policy({**self.c,'delete_source':True})
 def test_unexplained_404_is_not_a_retirement(self):
  class Missing:
   def meta(_self,_fid):raise self.m.b.ArchiveError('DRIVE_HTTP_404')
  with patch.object(self.m.b,'read_json',return_value={'mappings':{}}):
   with self.assertRaises(self.m.RetirementError):self.m.source_state(Missing(),self.c,self.job,self.job['assets'][0])
 def test_ambiguous_delete_is_never_replayed(self):
  with self.assertRaises(self.m.RetirementError):self.m.assert_delete_phase({'phase':'delete_started'})
 def test_explicit_rejection_is_not_false_success(self):
  with self.assertRaises(self.m.RetirementError):self.m.assert_delete_phase({'phase':'rejected'})
 def test_normal_pair_immutable_readiness_does_not_change_business_rows(self):
  before=copy.deepcopy((self.row,self.job,self.index,self.state));self.ready();self.assertEqual(before,(self.row,self.job,self.index,self.state))
 def offline_delete_case(self,status=204):
  import contextlib,tempfile,json,os
  import ares_archive_storage as storage
  self.c['retirements_folder_id']='retirementsOffline001'
  stack=contextlib.ExitStack();tmp=stack.enter_context(tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR','/root/.hermes/profiles/zeus/cache/scratch')));base=Path(tmp);data=base/'queue';data.mkdir();(base/'data/ares/creative-ops/inventory').mkdir(parents=True)
  (base/'data/ares/creative-ops/inventory/assets.jsonl').write_text(json.dumps(self.row)+'\n');(data/'archive-index.json').write_text(json.dumps(self.index));asset=self.job['assets'][0];source={'id':asset['sourceId'],'name':asset['name'],'mimeType':asset['mimeType'],'size':asset['size'],'md5Checksum':asset['md5'],'sha256Checksum':asset['sha256'],'version':'1','createdTime':asset['sourceCreatedTime'],'parents':[asset['sourceParentId']],'driveId':self.m.b.SOURCE_DRIVE,'trashed':False}
  class FakeDrive:
   token='offline-token-never-network';payload=b''
   def api(_self,*args,**kwargs):return {'capabilities':{'canDelete':True}}
   def hashes(_self,_fid):return {k:asset[k] for k in ['size','md5','sha256']}
   def upload_once(_self,_parent,_name,body,*args):_self.payload=body;return 'intentOffline001'
   def raw(_self,_fid):return _self.payload
   def meta(_self,_fid):return {'lastModifyingUser':{'permissionId':self.m.b.PUBLISHER_PERMISSION_IDS[self.m.b.CANONICAL_SA],'emailAddress':self.m.b.CANONICAL_SA}}
  d=FakeDrive();stack.enter_context(patch.object(self.m.b,'BASE',base));stack.enter_context(patch.object(self.m.b,'DATA',data));stack.enter_context(patch.object(self.m,'validate_active_policy',return_value={}));stack.enter_context(patch.object(self.m,'authorization',return_value={'offline_fixture':True}));stack.enter_context(patch.object(storage,'meta',return_value=source));stack.enter_context(patch.object(self.m,'check_copy',return_value={}));stack.enter_context(patch.object(self.m,'source_optional',return_value=None));stack.enter_context(patch.object(self.m,'source_etag',return_value={'etag':'"offline-etag"','version':'1'}));delete=stack.enter_context(patch.object(self.m,'delete_conditionally',return_value=status));publish=stack.enter_context(patch.object(self.m,'publish_receipt',return_value='receiptOffline001'));stack.enter_context(patch('urllib.request.urlopen',side_effect=AssertionError('OFFLINE_NETWORK_FORBIDDEN')))
  return stack,d,data,asset,delete,publish
 def test_accepted_delete_is_checkpointed_and_not_replayed_on_resume(self):
  stack,d,data,asset,delete,publish=self.offline_delete_case()
  with stack:
   result=self.m.retire_asset(d,self.c,self.job,asset,self.m.digest(self.row));self.assertEqual(result,'receiptOffline001');self.assertEqual(__import__('json').loads((data/'retirements'/('source-'+asset['sourceId']+'.json')).read_text())['phase'],'delete_accepted')
   self.m.retire_asset(d,self.c,self.job,asset,self.m.digest(self.row));delete.assert_called_once();self.assertEqual(publish.call_count,2)
 def test_precondition_rejection_preserved_and_never_retried(self):
  stack,d,data,asset,delete,publish=self.offline_delete_case(412)
  with stack:
   with self.assertRaises(self.m.RetirementError):self.m.retire_asset(d,self.c,self.job,asset,self.m.digest(self.row))
   with self.assertRaises(self.m.RetirementError):self.m.retire_asset(d,self.c,self.job,asset,self.m.digest(self.row))
   delete.assert_called_once();publish.assert_not_called()
 def test_lost_delete_response_blocks_without_success_receipt(self):
  stack,d,data,asset,delete,publish=self.offline_delete_case()
  with stack:
   delete.side_effect=TimeoutError('offline injected timeout')
   with self.assertRaises(self.m.RetirementError):self.m.retire_asset(d,self.c,self.job,asset,self.m.digest(self.row))
   with self.assertRaises(self.m.RetirementError):self.m.retire_asset(d,self.c,self.job,asset,self.m.digest(self.row))
   delete.assert_called_once();publish.assert_not_called()
 def test_known_retirement_routes_through_receipt_proof_not_fake_google_meta(self):
  index={'mappings':{'rawOffline001':{'sourceRetirementReceipt':'receiptOffline001'}}};record={'record_kind':'mgs.source.retirement.v1','source_id':'rawOffline001'}
  with patch.object(self.m.b,'read_json',return_value=index),patch.object(self.m,'verified_receipt',return_value=record) as verify:
   self.assertEqual(self.m.source_state(object(),self.c,self.job,self.job['assets'][0]),record);verify.assert_called_once()
if __name__=='__main__':unittest.main()
