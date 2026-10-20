"""Google metadata version drift is not a payload revision; preserve exact SHA scope."""
import unittest,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('archive_version_bridge',ROOT/'scripts/ares_archive_bridge.py');assert spec is not None and spec.loader is not None
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class VersionProofTests(unittest.TestCase):
 def setUp(self):
  self.c={'source_drive_id':b.SOURCE_DRIVE};self.a={'sourceId':'sourceOffline','sourceParentId':'parentOffline','name':'raw.png','mimeType':'image/png','size':'226','md5':'a'*32,'sha256':'b'*64,'version':'1','sourceCreatedTime':'2026-10-20T17:00:00Z'}
  self.m={'id':'sourceOffline','parents':['parentOffline'],'driveId':b.SOURCE_DRIVE,'name':'raw.png','mimeType':'image/png','size':'226','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'version':'2','trashed':False,'createdTime':'2026-10-20T17:00:00Z'}
 def test_metadata_version_advance_requires_exact_native_content_sha(self):self.assertIs(b.validate_source_metadata(self.m,self.a,self.c),True)
 def test_changed_version_without_native_sha_stays_blocked(self):
  del self.m['sha256Checksum']
  with self.assertRaises(b.ArchiveError):b.validate_source_metadata(self.m,self.a,self.c)
 def test_wrong_sha_blocks_even_with_original_version(self):
  self.m.update(version='1',sha256Checksum='c'*64)
  with self.assertRaises(b.ArchiveError):b.validate_source_metadata(self.m,self.a,self.c)
 def test_backward_version_blocked(self):
  self.m['version']='0'
  with self.assertRaises(b.ArchiveError):b.validate_source_metadata(self.m,self.a,self.c)
 def test_changed_name_not_a_metadata_only_acceptance(self):
  self.m['name']='other.png'
  with self.assertRaises(b.ArchiveError):b.validate_source_metadata(self.m,self.a,self.c)
 def test_changed_mime_still_blocked(self):
  self.m['mimeType']='video/mp4'
  with self.assertRaises(b.ArchiveError):b.validate_source_metadata(self.m,self.a,self.c)
 def test_changed_created_time_still_blocked(self):
  self.m['createdTime']='2026-10-20T18:00:00Z'
  with self.assertRaises(b.ArchiveError):b.validate_source_metadata(self.m,self.a,self.c)
if __name__=='__main__':unittest.main()
