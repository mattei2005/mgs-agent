"""Offline folder-phase proof: cache paths, not files; revalidate before ACK."""
import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_backfill as h
class FolderPhase(unittest.TestCase):
 def fake(self):
  class Drive:
   def __init__(self):self.calls=[];self.rows={'folder':{'id':'folder','name':'READY','parents':['root'],'mimeType':h.b.FOLDER,'trashed':False,'version':'1'},'file':{'id':'file','name':'clip.mp4','mimeType':'video/mp4','parents':['folder']}}
   def meta(self,fid):self.calls.append(fid);return copy.deepcopy(self.rows[fid])
  return Drive()
 def test_file_reads_are_never_cached(self):
  d=self.fake();scope=h.FolderReadScope(d);scope.meta('file');scope.meta('file');self.assertEqual(d.calls,['file','file'])
 def test_paths_reused_then_all_folders_refetched(self):
  d=self.fake();scope=h.FolderReadScope(d)
  self.assertEqual(scope.relative_parent('folder','root'),['READY']);scope.relative_parent('folder','root');self.assertEqual(d.calls,['folder']);scope.validate_folders();self.assertEqual(d.calls,['folder','folder'])
 def test_mid_phase_parent_rename_move_or_version_change_blocks(self):
  for field,value in [('parents',['foreign']),('name','USED'),('version','2')]:
   d=self.fake();scope=h.FolderReadScope(d);scope.relative_parent('folder','root');d.rows['folder'][field]=value
   with self.subTest(field=field),self.assertRaises(h.b.ArchiveError):scope.validate_folders()
if __name__=='__main__':unittest.main()
