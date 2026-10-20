"""Offline validation-pair protocol and index isolation tests."""
import unittest,importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('archive_validation_bridge',ROOT/'scripts/ares_archive_bridge.py')
assert spec is not None and spec.loader is not None
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class ValidationTests(unittest.TestCase):
 def setUp(self):
  self.c={'account':b.ACCOUNT,'source_drive_id':b.SOURCE_DRIVE,'source_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'delete_source':False,'effective_after':'2026-10-20T14:23:41Z'}
  self.a={'role':'original','sourceId':'rawOfflineSource','sourceParentId':'parentOffline','name':'MGS_ARCHIVE_TEST_ONLY_raw.png','mimeType':'image/png','size':'100','md5':'a'*32,'sha256':'b'*64,'version':'1','relativeParent':['TEST_INPUTS','99_LEGACY'],'sourceCreatedTime':'2026-10-20T16:00:00Z'}
  self.clean={**self.a,'role':'clean','sourceId':'cleanOfflineSource','relativeParent':['TEST_INPUTS','01_READY']}
  self.entry={'sourceId':'rawOfflineSource','archiveId':'archiveOffline','sha256':'b'*64,'lineageId':'test'}
  self.job:dict={'jobId':'a'*32,'kind':'lineage'};self.result={'status':'verified','jobId':'a'*32,'deleteSource':False,'assets':[self.entry]}
 def test_validation_flag_is_hashed_without_changing_normal_request_contract(self):
  normal=b.make_request(self.c,[self.a,self.clean],kind='lineage',lineage_id='test')
  test=b.make_request(self.c,[self.a,self.clean],kind='lineage',lineage_id='test',validation_only=True)
  self.assertNotIn('validationOnly',normal);self.assertIs(test['validationOnly'],True);self.assertNotEqual(test['jobId'],normal['jobId'])
 def test_nonboolean_validation_flag_rejected(self):
  with self.assertRaises(b.ArchiveError):b.make_request(self.c,[self.a,self.clean],kind='lineage',lineage_id='test',validation_only='true')
 def test_normal_lineage_adds_verified_mapping(self):
  index={'mappings':{},'verified_jobs':{}};b.record_verified_job(index,self.job,self.result);self.assertEqual(index['mappings']['rawOfflineSource']['archiveId'],'archiveOffline')
 def test_validation_lineage_keeps_production_mapping_empty(self):
  self.job['validationOnly']=True;index={'mappings':{},'verified_jobs':{}};b.record_verified_job(index,self.job,self.result);self.assertEqual(index['mappings'],{});self.assertIn('a'*32,index['verified_jobs'])
 def test_validation_string_flag_is_not_a_bypass(self):
  self.job['validationOnly']='true'
  with self.assertRaises(b.ArchiveError):b.record_verified_job({'mappings':{},'verified_jobs':{}},self.job,self.result)
 def test_existing_mapping_conflict_still_rejected(self):
  index={'mappings':{'rawOfflineSource':{**self.entry,'archiveId':'different'}},'verified_jobs':{}}
  with self.assertRaises(b.ArchiveError):b.record_verified_job(index,self.job,self.result)
 def test_unverified_result_never_promoted(self):
  self.result['status']='pending'
  with self.assertRaises(b.ArchiveError):b.record_verified_job({'mappings':{},'verified_jobs':{}},self.job,self.result)
if __name__=='__main__':unittest.main()
