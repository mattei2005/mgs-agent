"""Source-only preparation regression. Synthetic bytes; retain evidence, no cleanup."""
import unittest,pathlib,sys,uuid,hashlib,shutil,os,copy
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'deploy'))
from source_stage import prepare
class SourceStageTests(unittest.TestCase):
 def setUp(self):
  self.root=pathlib.Path(os.environ.get('TMPDIR','/root/.hermes/profiles/zeus/cache/scratch'))/('source-stage-test-'+str(uuid.uuid4()));self.source=self.root/'source';self.source.mkdir(parents=True)
  (self.source/'app.mjs').write_text('export const fixture=true;');(self.source/'private/old-stage').mkdir(parents=True);(self.source/'private/old-stage/residue.txt').write_text('synthetic')
  self.manifest={'authority':'1556332890743115850','producer':'test_source_stage','files':[{'path':'app.mjs','kind':'code','sha256':hashlib.sha256((self.source/'app.mjs').read_bytes()).hexdigest()}]}
 def test_recursive_baseline_and_source_only_green(self):
  shutil.copytree(self.source,self.root/'baseline');self.assertTrue((self.root/'baseline/private/old-stage/residue.txt').exists());r=prepare(self.source,self.root/'green',self.manifest);self.assertEqual(len(r['files']),1);self.assertFalse((self.root/'green/private').exists())
 def test_private_recursion_refused(self):
  self.manifest['files'][0]['path']='private/old-stage/residue.txt'
  with self.assertRaises(ValueError):prepare(self.source,self.root/'rejected',self.manifest)
 def test_hash_drift_refused(self):
  self.manifest['files'][0]['sha256']='0'*64
  with self.assertRaises(ValueError):prepare(self.source,self.root/'rejected',self.manifest)
 def test_output_dirs_red_green(self):
  self.assertFalse((self.root/'green/private/ui-redesign/api-evidence.json').parent.exists())
  self.manifest['test_output_dirs']=['private/ui-redesign']
  prepare(self.source,self.root/'green',self.manifest)
  self.assertTrue((self.root/'green/private/ui-redesign').is_dir())
  self.assertEqual(list((self.root/'green/private/ui-redesign').iterdir()),[])
 def test_output_escape_and_symlink(self):
  from source_stage import output_dirs
  for bad in ['../escape','/escape','private/../escape','private/backups','private/secrets']:
   with self.assertRaises(ValueError):output_dirs(self.root/'new',[bad])
  (self.root/'link').symlink_to(self.source,target_is_directory=True)
  with self.assertRaises(ValueError):output_dirs(self.root/'link',['private/output'])
 def test_approved_public_symlink(self):
  (self.source/'public').mkdir();(self.source/'public/app.js').write_text('void 0;');self.manifest['links']=[{'path':'public','target':str(self.source/'public'),'approved':True,'markers':{'app.js':hashlib.sha256((self.source/'public/app.js').read_bytes()).hexdigest()}}]
  prepare(self.source,self.root/'green',self.manifest);self.assertEqual((self.root/'green/public').resolve(),self.source/'public')
if __name__=='__main__':unittest.main()
