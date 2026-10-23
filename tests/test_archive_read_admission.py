"""Offline control flow: a read releases/reacquires mutation lease, never writes."""
import sys,contextlib,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_archive_read_admission as r
class ReadAdmission(unittest.TestCase):
 def test_backup_releases_only_during_stream(self):
  events=[];lease=object()
  def flock(fd,mode):self.assertIs(fd,lease);events.append(mode)
  def hashes(fid):events.append('read');return {'verified':'offline'}
  with patch.object(r,'binary_read_slot',contextlib.nullcontext),patch.object(r.fcntl,'flock',side_effect=flock):result=r.backup_read_hashes(hashes,lease)('file')
  self.assertEqual(events,[r.fcntl.LOCK_UN,'read',r.fcntl.LOCK_EX]);self.assertEqual(result,{'verified':'offline'})
 def test_exception_still_reacquires_lease(self):
  events=[]
  def fail(fid):raise RuntimeError('OFFLINE_READ_FAILURE')
  with patch.object(r,'binary_read_slot',contextlib.nullcontext),patch.object(r.fcntl,'flock',side_effect=lambda fd,mode:events.append(mode)):
   with self.assertRaises(RuntimeError):r.backup_read_hashes(fail,object())('file')
  self.assertEqual(events,[r.fcntl.LOCK_UN,r.fcntl.LOCK_EX])
if __name__=='__main__':unittest.main()
