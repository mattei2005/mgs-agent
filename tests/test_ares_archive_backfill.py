"""Offline exact-manifest backfill tests; never call providers."""
import unittest,sys,importlib.util,copy
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
if __name__=='__main__':unittest.main()
