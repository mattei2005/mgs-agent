"""Offline denial tests for exact approved source ancestry label corrections."""
import sys,copy,hashlib,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_bridge as b
import mgs_archive_source_names as names
class SourceNamesTests(unittest.TestCase):
 def fixture(self):
  asset={'sourceId':'fixture-source','relativeParent':['SHEIN_US_ES','IMG','01_READY'],'size':'10','md5':'a'*32,'sha256':'b'*64};job={'jobId':'fixture-job','assets':[asset]};meta={'id':'fixture-source','parents':['leaf']};chain=[{'id':'leaf','name':'01_READY','parents':['format']},{'id':'format','name':'IMG','parents':['operation']},{'id':'operation','name':'SHEIN_US_ES 2','parents':['root']}]
  rec={'source_id':asset['sourceId'],'source_parent':'leaf','root_id':'root','expected_path':asset['relativeParent'],'current_path':['SHEIN_US_ES 2','IMG','01_READY'],'chain':chain,'job_id':job['jobId'],'job_sha256':names.sha(job),'asset_sha256':names.sha(asset),'full_source_archive_streams_verified':True,'hashes':{k:asset[k] for k in ['size','md5','sha256']}}
  proof={'records':{asset['sourceId']:rec}};binding={'proof_file_id':'native-proof','control_folder_id':'control'};d=Mock()
  folders={r['id']:{**r,'mimeType':b.FOLDER,'trashed':False,'owners':[{'emailAddress':b.ACCOUNT}],'permissions':[]} for r in chain}
  folders['native-proof']={'lastModifyingUser':{'permissionId':b.PUBLISHER_PERMISSION_IDS[b.CANONICAL_SA]},'properties':{'mgsArchiveType':'lineage_map'}}
  d.meta.side_effect=lambda fid:folders[fid];d.raw.side_effect=lambda fid:b.canonical(proof)
  return d,meta,asset,job,proof,binding,folders
 def call(self,mutate=None):
  d,m,a,j,p,c,folders=self.fixture()
  if mutate:mutate(m,a,j,p,c,folders)
  with patch.object(names,'load',return_value=(p,c)),patch.object(b,'control_object_scope',return_value=True):return names.verify(d,m,a,j,{'processing_destination_id':'root'})
 def test_exact_only_name_drift_is_accepted(self):self.assertTrue(self.call())
 def test_unregistered_source_returns_false(self):self.assertFalse(self.call(lambda m,a,j,p,c,f:p['records'].clear()))
 def test_changed_folder_id_parent_name_or_public_access_rejected(self):
  for key,value in [('id','wrong'),('parents',['wrong']),('name','another'),('permissions',[{'type':'anyone'}])]:
   with self.subTest(key=key),self.assertRaises(b.ArchiveError):self.call(lambda m,a,j,p,c,f:f['operation'].__setitem__(key,value))
 def test_changed_source_job_bytes_or_root_rejected(self):
  mutators=[lambda m,a,j,p,c,f:m.__setitem__('parents',['wrong']),lambda m,a,j,p,c,f:j.__setitem__('jobId','wrong'),lambda m,a,j,p,c,f:a.__setitem__('sha256','c'*64),lambda m,a,j,p,c,f:p['records'][a['sourceId']].__setitem__('root_id','other')]
  for change in mutators:
   with self.assertRaises(b.ArchiveError):self.call(change)
 def test_missing_full_stream_acceptance_rejected(self):
  with self.assertRaises(b.ArchiveError):self.call(lambda m,a,j,p,c,f:p['records'][a['sourceId']].__setitem__('full_source_archive_streams_verified',False))
if __name__=='__main__':unittest.main()
