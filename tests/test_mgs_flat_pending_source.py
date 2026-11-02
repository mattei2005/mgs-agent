import copy,hashlib,json,unittest
from unittest.mock import patch
import mgs_flat_source_compat as f
import ares_archive_bridge as b

class PendingSourceTests(unittest.TestCase):
 def setUp(self):
  self.asset={'sourceId':'source0001','sourceParentId':'frozen-parent','name':'test.png','mimeType':'image/png','size':'3','md5':'a'*32,'sha256':'b'*64,'sourceCreatedTime':'2026-10-29T00:00:00Z','version':'2','relativeParent':['OP','IMG','01_READY'],'role':'clean'}
  self.job={'jobId':'job0001','assets':[self.asset]}
  self.meta={'id':'source0001','name':'test.png','mimeType':'image/png','size':'3','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'createdTime':self.asset['sourceCreatedTime'],'parents':[f.PENDING_UPLOAD],'driveId':b.SOURCE_DRIVE,'version':'5','trashed':False,'permissions':[]}
  self.proof={'schema':'mgs.flat.pending.sources.proof.v1','redesign_confirmation':'1566814476626563115','access_confirmation':'1566825959645253764','delete_writes':0,'sources':{'source0001':{'asset_sha256':f.sha(self.asset),'job_id':'job0001','job_sha256':f.sha(self.job),'metadata_after':self.meta.copy(),'full_source_archive_streams_verified':True}}}
  raw=b.canonical(self.proof)
  self.state={'schema':'mgs.flat.pending.sources.binding.v1','status':'verified','proof_file_id':'proof0001','proof_sha256':hashlib.sha256(raw).hexdigest(),'source_ids':['source0001'],'control_folder_id':'control0001'}
  outer=self
  class Drive:
   def raw(self,fid):return b.canonical(outer.proof)
   def meta(self,fid):
    if fid==f.PENDING_UPLOAD:return {'id':fid,'mimeType':b.FOLDER,'driveId':b.SOURCE_DRIVE,'trashed':False}
    return {'id':fid,'properties':{'mgsArchiveType':'stock_layout_snapshot'}}
  self.d=Drive()
  self.read=patch.object(b,'read_json',return_value=self.state);self.read.start();self.addCleanup(self.read.stop)
  self.pub=patch.object(b,'require_publisher');self.pub.start();self.addCleanup(self.pub.stop)
  self.scope=patch.object(b,'control_object_scope',return_value=True);self.scope.start();self.addCleanup(self.scope.stop)
 def refresh(self):self.state['proof_sha256']=hashlib.sha256(b.canonical(self.proof)).hexdigest()
 def verify(self):return f.verify_pending(self.d,self.meta,self.asset,self.job)
 def test_exact_pending_source(self):self.assertTrue(self.verify())
 def test_unlisted_source_falls_through(self):self.asset['sourceId']='other0001';self.assertFalse(self.verify())
 def test_wrong_parent(self):self.meta['parents']=['other'];self.assertRaises(f.FlatSourceError,self.verify)
 def test_changed_bytes(self):self.meta['sha256Checksum']='c'*64;self.assertRaises(f.FlatSourceError,self.verify)
 def test_changed_job(self):self.job['extra']=True;self.assertRaises(f.FlatSourceError,self.verify)
 def test_changed_asset(self):self.asset['name']='changed';self.assertRaises(f.FlatSourceError,self.verify)
 def test_digest(self):self.proof['extra']=True;self.assertRaises(f.FlatSourceError,self.verify)
 def test_wrong_authority(self):self.proof['access_confirmation']='wrong';self.refresh();self.assertRaises(f.FlatSourceError,self.verify)
 def test_public(self):self.meta['permissions']=[{'type':'anyone'}];self.assertRaises(f.FlatSourceError,self.verify)
 def test_trashed(self):self.meta['trashed']=True;self.assertRaises(f.FlatSourceError,self.verify)
 def test_wrong_drive(self):self.meta['driveId']='wrong';self.assertRaises(f.FlatSourceError,self.verify)
 def test_proof_streams_required(self):self.proof['sources']['source0001']['full_source_archive_streams_verified']=False;self.refresh();self.assertRaises(f.FlatSourceError,self.verify)
 def test_version_regression(self):self.meta['version']='1';self.assertRaises(f.FlatSourceError,self.verify)
 def test_scope(self):
  with patch.object(b,'control_object_scope',return_value=False):self.assertRaises(f.FlatSourceError,self.verify)
 def test_native_publisher(self):
  with patch.object(b,'require_publisher',side_effect=b.ArchiveError('publisher')):self.assertRaises(b.ArchiveError,self.verify)
 def test_missing_state(self):self.state.clear();self.assertFalse(self.verify())
 def test_retirement_unchanged(self):
  import ares_archive_retirement as retirement
  self.assertNotIn('verify_pending',retirement.source_state.__code__.co_names)
if __name__=='__main__':unittest.main()
