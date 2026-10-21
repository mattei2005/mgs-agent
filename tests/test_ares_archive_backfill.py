"""Offline exact-manifest backfill tests; never call providers."""
import unittest,sys,importlib.util,copy,json,tempfile,os
from unittest.mock import patch,Mock
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
class BackfillTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  s=importlib.util.spec_from_file_location('backfill_offline',ROOT/'scripts/ares_archive_backfill.py');assert s and s.loader;cls.m=importlib.util.module_from_spec(s);s.loader.exec_module(cls.m)
 def setUp(self):
  b=self.m.b;self.c={'account':b.ACCOUNT,'source_drive_id':b.SOURCE_DRIVE,'source_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT};self.stage={'manifest_file_id':'manifestOffline001','manifest_sha256':'a'*64,'migration_id':'1562256530454220851'};self.asset={'sourceId':'sourceOffline001','sourceParentId':'parentOffline001','role':'historical','name':'old.txt','mimeType':'text/plain','size':'0','md5':'b'*32,'sha256':'c'*64,'version':'1','relativeParent':['CAR_BR_BR','IMG','99_LEGACY'],'sourceCreatedTime':'2026-01-01T00:00:00Z'}
 def test_job_is_deterministic_and_copy_only(self):
  one=self.m.make_job([self.asset],self.c,self.stage);two=self.m.make_job([self.asset],self.c,self.stage);self.assertEqual(one['jobId'],two['jobId']);self.assertFalse(one['deleteSource']);self.assertEqual(one['kind'],'backfill')
 def test_primary_ids_not_replaced_or_new_candidates_created(self):
  before=copy.deepcopy(self.asset);self.m.make_job([self.asset],self.c,self.stage);self.assertEqual(self.asset,before)
 def test_batch_budget_is_bounded(self):
  with self.assertRaises(self.m.BackfillError):self.m.make_job([{**self.asset,'sourceId':'offline'+str(i)} for i in range(9)],self.c,self.stage)
 def test_duplicate_source_rejected(self):
  with self.assertRaises(self.m.BackfillError):self.m.make_job([self.asset,self.asset],self.c,self.stage)
 def test_zero_byte_auxiliary_not_dropped(self):self.assertEqual(self.m.make_job([self.asset],self.c,self.stage)['assets'][0]['size'],'0')
 def test_shared_drive_acl_uses_paginated_permissions_not_files_get(self):
  d=Mock();d.api.side_effect=[{'permissions':[{'emailAddress':'first@example.com'}],'nextPageToken':'next'},{'permissions':[{'emailAddress':'second@example.com'}]}]
  result=self.m.permissions(d,'offlineSource001');self.assertEqual(len(result),2);self.assertEqual(d.api.call_args.args[1],'files/offlineSource001/permissions');self.assertEqual(d.api.call_args.args[2]['pageToken'],'next')
 def test_new_owner_heartbeat_is_a_real_separate_gate(self):
  with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as td:
   p=Path(td);d=Mock();d.one.return_value={'id':'heartbeatOffline001'};d.raw.return_value=json.dumps({'workerSha256':'d'*64,'triggerUid':'offlineClock','status':'ok','blocked':[],'executedAt':self.m.b.now_iso()}).encode()
   manifest={'assets':[self.asset]};stage={**self.stage,'worker_sha256':'d'*64}
   with patch.object(self.m,'manifest_load',return_value=(manifest,stage)),patch.object(self.m,'location',return_value=p),patch.object(self.m.b,'require_publisher'):
    result=self.m.cycle_locked(d,{'control_folder_id':'offlineControl001'},False)
   self.assertTrue(result['owner_ready']);self.assertEqual(result['verified_files'],0);self.assertFalse(result['historical_cleanup_enabled']);d.api.assert_not_called()
 def test_old_owner_digest_cannot_activate_historical_processing(self):
  with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as td:
   d=Mock();d.one.return_value={'id':'heartbeatOffline001'};d.raw.return_value=json.dumps({'workerSha256':'e'*64}).encode()
   with patch.object(self.m,'manifest_load',return_value=({'assets':[self.asset]},{'worker_sha256':'d'*64})),patch.object(self.m,'location',return_value=Path(td)),patch.object(self.m.b,'require_publisher'):
    result=self.m.cycle_locked(d,{'control_folder_id':'offlineControl001'},False)
   self.assertEqual(result['status'],'awaiting_owner_repin');self.assertFalse(result['owner_ready']);d.api.assert_not_called()
if __name__=='__main__':unittest.main()
