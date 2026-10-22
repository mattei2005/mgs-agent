"""Manual ok plus native bulk pause is one waiting incident, not a new failure."""
import copy,importlib,importlib.util,sys,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
p=importlib.import_module('ares_archive_monitor_projection')
spec=importlib.util.spec_from_file_location('gate','/root/.hermes/profiles/zeus/scripts/ares-archive-notification-gate.py')
assert spec is not None and spec.loader is not None
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class NotificationWaitTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2030,1,1,12,0,tzinfo=timezone.utc)
  self.h={'status':'blocked','blocked':[],'queue_enabled':True,'owner_repin_pending':False,'owner_worker_sha256':'sha','owner_worker_status':'ok'}
  self.native={'workerSha256':'sha','executionMode':'manual_probe_only','status':'ok','canaryAcknowledged':True,'blocked':[],'executedAt':self.now.isoformat(),'runtimeBudget':{'bulk':{'paused':True,'earliestRetryAt':(self.now+timedelta(hours=1)).isoformat()}}}
 def projected(self):
  h=p.native_runtime_context(self.h,self.native,'sha',self.now);h=p.stable_incident(h,{'pending'});h['notification_class']=p.notification_class(h);return h
 def frame(self,h=None):return {'schema':'mgs.archive.notification.health.v1','observed_at':self.now.isoformat(),'health':h or self.projected()}
 def test_manual_ok_bulk_paused_is_classified_without_false_recovery(self):
  h=self.projected();self.assertEqual(h['status'],'blocked');self.assertTrue(h['owner_bulk_runtime_paused']);self.assertEqual(h['notification_class'],'known_runtime_wait')
 def test_known_runtime_wait_does_not_wake_model(self):self.assertFalse(g.evaluate(self.frame(),self.now)['wakeAgent'])
 def test_old_provider_receipt_is_not_new_failure_after_manual_success(self):
  self.h['blocked']=[{'job_id':'pending','reason':'OWNER_BLOCKED:'+p.READ}];h=self.projected();self.assertEqual(h['blocked'],[]);self.assertFalse(g.evaluate(self.frame(h),self.now)['wakeAgent'])
 def test_unknown_or_exhausted_error_still_wakes(self):
  self.h['blocked']=[{'job_id':'exhausted','reason':'OWNER_BLOCKED:'+p.READ}];self.assertTrue(g.evaluate(self.frame(),self.now)['wakeAgent'])
 def test_permission_failure_wakes(self):
  self.h['blocked']=[{'reason':'PERMISSION_DENIED'}];self.assertTrue(g.evaluate(self.frame(),self.now)['wakeAgent'])
 def test_new_owner_action_wakes(self):
  self.h['owner_repin_pending']=True;self.assertTrue(g.evaluate(self.frame(),self.now)['wakeAgent'])
 def test_queue_pause_is_not_suppressed(self):
  self.h['queue_enabled']=False;self.assertTrue(g.evaluate(self.frame(),self.now)['wakeAgent'])
 def test_wrong_native_digest_is_not_suppressed(self):
  self.native['workerSha256']='other';self.assertTrue(g.evaluate(self.frame(),self.now)['wakeAgent'])
 def test_native_blocked_components_are_not_suppressed(self):
  self.native.update(status='blocked',blocked=[{'reason':'ROOT_CHANGED'}]);self.assertTrue(g.evaluate(self.frame(),self.now)['wakeAgent'])
 def test_missing_or_invalid_deadline_is_not_suppressed(self):
  self.native['runtimeBudget']['bulk']['earliestRetryAt']='bad';self.assertTrue(g.evaluate(self.frame(),self.now)['wakeAgent'])
 def test_wait_window_does_not_hide_stopped_scheduler_forever(self):
  self.native['executedAt']=(self.now-timedelta(hours=3)).isoformat();self.native['runtimeBudget']['bulk']['earliestRetryAt']=(self.now-timedelta(minutes=21)).isoformat();self.assertTrue(g.evaluate(self.frame(),self.now)['wakeAgent'])
 def test_stale_frame_does_not_suppress(self):self.assertTrue(g.evaluate(self.frame(),self.now+timedelta(seconds=181))['wakeAgent'])
 def test_missing_frame_and_unknown_schema_wake(self):
  self.assertTrue(g.evaluate({},self.now)['wakeAgent']);f=self.frame();f['schema']='other';self.assertTrue(g.evaluate(f,self.now)['wakeAgent'])
 def test_actual_recovery_is_not_classified_as_known_wait(self):
  self.h.update(status='ok');self.native['runtimeBudget']['bulk']['paused']=False;self.assertTrue(g.evaluate(self.frame(),self.now)['wakeAgent'])
if __name__=='__main__':unittest.main()
