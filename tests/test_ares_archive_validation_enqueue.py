"""Offline tests for the bounded technical validation-pair exception."""
import unittest,importlib.util,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
def load_module(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'))
 assert spec is not None and spec.loader is not None
 module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
 return module
b=load_module('ares_archive_bridge');api=load_module('ares_archive_automation')
class ValidationEnqueueTests(unittest.TestCase):
 def setUp(self):
  self.c={'account':b.ACCOUNT,'source_drive_id':b.SOURCE_DRIVE,'source_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'delete_source':False,'queue_enabled':False,'effective_after':'2026-10-20T14:23:41Z','control_folder_id':'controlOffline123'}
  self.manifest={'schema':'mgs.archive.validation-pair.v1','run_id':'archive-validation-1562141828449439838','metadata_clean':True,'sources':{'original':{'id':'rawOfflineSource','sha256':'a'*64},'clean':{'id':'cleanOfflineSource','sha256':'b'*64}}}
  self.metas={sid:{'id':sid,'name':'MGS_ARCHIVE_TEST_ONLY_'+role+'.png','parents':[role+'ParentOffline'],'driveId':b.SOURCE_DRIVE,'properties':{'mgsArchiveType':'archive_test_media'},'lastModifyingUser':{'permissionId':'07414359829876449782'}} for role,sid in [('original','rawOfflineSource'),('clean','cleanOfflineSource')]}
  outer=self
  class D:
   def meta(self,fid):return outer.metas[fid]
   def relative_parent(self,parent,root):return ['TEST_INPUTS','PAIR','99_LEGACY' if parent.startswith('original') else '01_READY']
  self.d=D();self.calls=[]
 def snapshot(self,d,c,fid,role):
  return {'sourceId':fid,'sourceParentId':role+'ParentOffline','role':role,'name':'MGS_ARCHIVE_TEST_ONLY_'+role+'.png','mimeType':'image/png','size':'100','md5':'c'*32,'sha256':self.manifest['sources'][role]['sha256'],'version':'1','relativeParent':['00_ARQUIVO_CONTROLE','TEST_INPUTS','PAIR','99_LEGACY' if role=='original' else '01_READY'],'sourceCreatedTime':'2026-10-20T17:00:00Z'}
 def invoke(self,apply=True):
  with patch.object(api.bridge,'asset_snapshot',side_effect=self.snapshot),patch.object(api.bridge,'enqueue',side_effect=lambda d,c,j:(self.calls.append(j) or {'jobId':j['jobId'],'requestFileId':'offlineRequest'})):
   return api.enqueue_validation_pair(self.d,self.c,self.manifest,apply)
 def test_technical_pair_can_be_verified_without_enabling_production(self):
  result=self.invoke();self.assertEqual(len(self.calls),1);self.assertIs(self.calls[0]['validationOnly'],True);self.assertFalse(self.c['queue_enabled'])
 def test_dry_run_does_not_publish(self):
  self.invoke(False);self.assertEqual(self.calls,[])
 def test_arbitrary_test_run_rejected(self):
  self.manifest['run_id']='not-approved'
  with self.assertRaises(b.ArchiveError):self.invoke()
 def test_nontechnical_file_rejected(self):
  self.metas['rawOfflineSource']['properties']['mgsArchiveType']='production'
  with self.assertRaises(b.ArchiveError):self.invoke()
 def test_wrong_native_source_publisher_rejected(self):
  self.metas['rawOfflineSource']['lastModifyingUser']['permissionId']='other'
  with self.assertRaises(b.ArchiveError):self.invoke()
 def test_noncontrol_parent_rejected(self):
  self.d.relative_parent=lambda parent,root:['SHEIN_US_EN','99_LEGACY']
  with self.assertRaises(b.ArchiveError):self.invoke()
 def test_missing_clean_verification_rejected(self):
  self.manifest['metadata_clean']=False
  with self.assertRaises(b.ArchiveError):self.invoke()
if __name__=='__main__':unittest.main()
