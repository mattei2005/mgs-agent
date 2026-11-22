"""Distinct RAW exports require source-bound proof and identical clean bytes."""
import copy,hashlib,json,os,subprocess,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_autonomous_intake as a
class DuplicateExportTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']);p=Path(cls.tmp.name);raw=p/'raw.mp4';clean=p/'clean.mp4'
  subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=red:s=32x32:d=0.1','-metadata','title=RAW export','-y',str(raw)],check=True)
  subprocess.run([str(a.bridge.BASE/'scripts/clean-creative-metadata.sh'),'clean',str(raw),'--out',str(clean),'--agent','ares'],capture_output=True,check=True)
  cls.data=raw.read_bytes();cls.sha=hashlib.sha256(cls.data).hexdigest();cls.clean=hashlib.sha256(clean.read_bytes()).hexdigest()
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):
  self.source={'source_id':'duplicateOffline1','name':'RAW.mp4','size':str(len(self.data)),'md5':hashlib.md5(self.data).hexdigest(),'sha256':self.sha}
  self.hashes={'sha256':self.sha,'md5':self.source['md5'],'size':self.source['size']}
  link={'source_drive_id':self.source['source_id'],'original_filename':self.source['name'],'canonical_filename':'FINAL.mp4','original_checksum':self.sha,'clean_checksum':self.clean}
  self.row={'source_drive_id':'primaryOffline1','canonical_filename':'FINAL.mp4','clean_checksum':self.clean,'duplicate_source_drive_ids':[self.source['source_id']],'duplicate_sources':[link]}
  self.d=Mock();self.d.raw.return_value=self.data
 def test_exact_source_bound_equivalence(self):self.assertTrue(a.verify_duplicate_export(self.d,self.source,self.row,self.hashes))
 def test_unbound_id_rejected(self):
  self.row['duplicate_source_drive_ids']=[]
  with self.assertRaises(a.IntakeError):a.verify_duplicate_export(self.d,self.source,self.row,self.hashes)
 def test_duplicate_link_rejected(self):
  self.row['duplicate_sources']*=2
  with self.assertRaises(a.IntakeError):a.verify_duplicate_export(self.d,self.source,self.row,self.hashes)
 def test_wrong_raw_hash_rejected(self):
  self.row['duplicate_sources'][0]['original_checksum']='a'*64
  with self.assertRaises(a.IntakeError):a.verify_duplicate_export(self.d,self.source,self.row,self.hashes)
 def test_wrong_name_rejected(self):
  self.row['duplicate_sources'][0]['original_filename']='other.mp4'
  with self.assertRaises(a.IntakeError):a.verify_duplicate_export(self.d,self.source,self.row,self.hashes)
 def test_wrong_clean_rejected_after_real_sanitize(self):
  self.row['clean_checksum']='b'*64;self.row['duplicate_sources'][0]['clean_checksum']='b'*64
  with self.assertRaises(a.IntakeError):a.verify_duplicate_export(self.d,self.source,self.row,self.hashes)
 def test_content_changed_during_read_rejected(self):
  self.d.raw.return_value=b'changed'
  with self.assertRaises(a.IntakeError):a.verify_duplicate_export(self.d,self.source,self.row,self.hashes)
 def test_primary_id_not_duplicate(self):
  self.row['source_drive_id']=self.source['source_id']
  with self.assertRaises(a.IntakeError):a.verify_duplicate_export(self.d,self.source,self.row,self.hashes)
if __name__=='__main__':unittest.main()
