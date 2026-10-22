import contextlib,copy,hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_monitor_projection as p
import ares_archive_efficiency_rollout as fast
import mgs_backup_automation as a
class EfficiencyRegression(unittest.TestCase):
 def health(self,rows):return {'status':'blocked','owner_worker_status':'runtime_budget_paused','blocked':rows,'worker_ready':False}
 def test_rotating_known_retryable_receipts_do_not_realert_same_pause(self):
  one=self.health([{'job_id':'one','reason':'OWNER_BLOCKED:'+p.READ}]);two=self.health([{'job_id':'two','reason':'OWNER_BLOCKED:'+p.CREATE}]);self.assertEqual(p.stable_incident(one,{'one'}),p.stable_incident(two,{'two'}));self.assertEqual(one['blocked'][0]['job_id'],'one')
 def test_unknown_permission_or_integrity_failure_is_never_suppressed(self):
  x=self.health([{'job_id':'one','reason':'PERMISSION_DENIED'}]);self.assertEqual(p.stable_incident(x,{'one'})['blocked'],x['blocked'])
 def test_unproven_or_exhausted_provider_error_still_alerts(self):
  x=self.health([{'job_id':'one','reason':'OWNER_BLOCKED:'+p.READ}]);self.assertEqual(p.stable_incident(x)['blocked'],x['blocked'])
 def test_resumed_worker_leaves_provider_errors_visible(self):
  x=self.health([{'job_id':'one','reason':'OWNER_BLOCKED:'+p.READ}]);x['owner_worker_status']='ok';self.assertEqual(p.stable_incident(x,{'one'}),x)
 def test_native_retryability_requires_real_publisher_and_remaining_attempts(self):
  d=Mock();d.one.return_value={'id':'receipt'};d.meta.return_value={'parents':['receipts'],'properties':{'mgsArchiveKey':'receipt:one'}};x=self.health([{'job_id':'one','reason':'OWNER_BLOCKED:'+p.READ}]);body={'jobId':'one','status':'blocked','reason':p.READ,'attempts':1,'retryAfter':'2026-10-22T15:34:31.754Z'}
  with patch.object(a.b,'require_publisher') as verify:
   d.raw.return_value=json.dumps(body).encode();self.assertEqual(p.native_retryable_jobs(d,{'receipts_folder_id':'receipts'},x),{'one'});verify.assert_called_once()
   body.update(attempts=5,retryAfter=None);d.raw.return_value=json.dumps(body).encode();self.assertEqual(p.native_retryable_jobs(d,{'receipts_folder_id':'receipts'},x),set())
 def test_composer_requires_exact_previously_accepted_source(self):
  with self.assertRaisesRegex(a.b.ArchiveError,'BASE_CHANGED'):fast.build(b'changed',b'')
 def accept_fixture(self,versioned):
  s={'worker_sha256':'e'*64,'plan_sha256':'f'*64,'heartbeat_samples':[{'executedAt':'first'},{'executedAt':'second'}],'owner_accepted':False}
  if versioned:s['efficiency_revision']={'backup_activation_key_versioned':True}
  plan={'bindingSha256':'d'*64};hb={'executedAt':'second','triggerUid':'trigger','workerSha256':s['worker_sha256']}
  with patch.object(a,'load',return_value=(plan,s)),patch.object(a,'heartbeat',return_value=hb),patch.object(a,'owner_ready',return_value=True),patch.object(a.b,'Drive',return_value=Mock()),patch.object(a.b,'config_load',return_value={'worker_sha256':s['worker_sha256'],'requests_folder_id':'requests'}),patch.object(a.b,'queue_lock',contextlib.nullcontext),patch.object(a.b,'atomic_json'),patch.object(a.b,'read_json',return_value={}),patch.object(a.m,'accept_owner') as accept,patch.object(a,'immutable',return_value='activation') as publish:
   result=a.resume_acceptance();self.assertEqual(result['status'],'accepted_backup_future_archive');accept.assert_called_once();self.assertTrue(s['owner_accepted']);args=publish.call_args.args;self.assertFalse(args[4]['archiveTrashEnabled']);self.assertFalse(args[4]['deleteSource']);return args[2]
 def test_new_activation_is_versioned_content_bound_and_fits_drive_property_limit(self):
  key=self.accept_fixture(True);expected='backup-activation-v2:'+hashlib.sha256(('f'*64+'|'+'e'*64).encode()).hexdigest();self.assertEqual(key,expected);self.assertLessEqual(len(('mgsArchiveKey'+key).encode()),124)
 def test_old_activation_contract_is_preserved(self):self.assertEqual(self.accept_fixture(False),'backup-activation:'+'f'*64)
if __name__=='__main__':unittest.main()
