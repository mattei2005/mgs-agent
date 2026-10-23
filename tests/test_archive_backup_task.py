"""Offline finite-child supervision; no real child or production health writes."""
import sys,tempfile,json,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_archive_backup_task as t
class BackupTasks(unittest.TestCase):
 def test_live_pinned_pid_is_not_spawned_again(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(t,'HOME',Path(tmp)),patch.object(t,'start_ticks',return_value='PIN'),patch.object(t.a,'cycle') as cycle,patch.object(t.subprocess,'Popen') as spawn:
   (Path(tmp)/'background-task.json').write_text(json.dumps({'pid':123,'start_ticks':'PIN'}));out=t.supervise();self.assertTrue(out['in_progress']);cycle.assert_not_called();spawn.assert_not_called()
 def test_dead_child_without_result_blocks_without_replay(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(t,'HOME',Path(tmp)),patch.object(t,'start_ticks',return_value=None),patch.object(t.a,'cycle') as cycle,patch.object(t.subprocess,'Popen') as spawn:
   (Path(tmp)/'background-task.json').write_text(json.dumps({'pid':123,'start_ticks':'PIN','recovery_attempts':2,'result_path':str(Path(tmp)/'missing.json')}));out=t.supervise();self.assertEqual(out['status'],'blocked');cycle.assert_not_called();spawn.assert_not_called()
 def test_idle_lane_runs_canonical_producer_then_exact_private_child(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(t,'HOME',Path(tmp)),patch.object(t,'start_ticks',return_value='NEW'),patch.object(t.a,'cycle',return_value={'status':'ok','blocked':[]}) as cycle,patch.object(t.subprocess,'run',side_effect=[Mock(returncode=0),Mock(returncode=0,stdout='456\n')]) as spawn:
   out=t.supervise();cycle.assert_called_once_with(apply=True);self.assertTrue(out['in_progress']);args=spawn.call_args_list[0].args[0];self.assertEqual(args[0],'systemd-run');self.assertEqual(args[-3:],[str(t.b.BASE/'scripts/mgs_private_backup_transport.py'),'tick','--apply']);state=json.loads((Path(tmp)/'background-task.json').read_text());self.assertEqual(state['pid'],456);self.assertEqual(state['start_ticks'],'NEW')
if __name__=='__main__':unittest.main()
