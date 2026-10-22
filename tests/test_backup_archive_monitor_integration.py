"""Offline integration tests for the existing profile monitor; no live tick."""
import contextlib,importlib.util,io,json,sys,unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts')
spec=importlib.util.spec_from_file_location('backup_profile_monitor','/root/.hermes/profiles/zeus/scripts/ares-archive-automation-monitor.py')
assert spec is not None and spec.loader is not None
monitor=importlib.util.module_from_spec(spec);spec.loader.exec_module(monitor)
class MonitorIntegration(unittest.TestCase):
 def run_case(self,blocked):
  result={'status':'ok','reconciliation':{'blocked':[]},'production':{'blocked':[]},'retirement':{'blocked':[]},'historical_backfill':{},'queue_enabled':False,'worker_ready':True,'delete_source':False,'worker_trigger_uid':'fixture-trigger','owner_worker_status':'ok','owner_worker_sha256':'fixture-worker'}
  output=io.StringIO()
  with patch.object(monitor.time,'sleep'),patch.object(monitor.backup_archive,'cycle',return_value={'status':'owner_repin_required_backup_archive','blocked':blocked,'archive_trash_enabled':False}) as cycle,patch.object(monitor.whole_drive,'resume_acceptance',return_value={'status':'not_applicable'}),patch.object(monitor.automation,'run_cycle',return_value=result),contextlib.redirect_stdout(output):
   self.assertEqual(monitor.main(),0);cycle.assert_called_once_with(apply=True)
  return json.loads(output.getvalue())
 def test_pending_owner_stage_is_explicit_without_fake_activation(self):
  out=self.run_case([]);self.assertEqual(out['backup_archive_status'],'owner_repin_required_backup_archive');self.assertFalse(out['backup_archive_trash_enabled']);self.assertEqual(out['blocked'],[])
 def test_backup_native_blocker_propagates_into_same_monitor(self):
  failure={'component':'backup_owner','reason':'OFFLINE_FIXTURE_BLOCKER'};out=self.run_case([failure]);self.assertEqual(out['status'],'blocked');self.assertIn(failure,out['blocked'])
if __name__=='__main__':unittest.main()
