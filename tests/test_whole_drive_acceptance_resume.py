"""Offline control tests. They do not establish Google acceptance."""
import contextlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_whole_drive_migration as m
SHA='bf9801376e8b0479271c41f7608661a21ae6edba47a6c9e7d32282466f9d3108'
class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.stage={'worker_sha256':SHA,'corporate_grants_applied':True}
        self.corp={'worker_sha256':SHA,'owner_setup_verified':True,'owner_setup_receipt_missing':False,'production_moves_enabled':False}
        self.config={'worker_sha256':'a'*64,'control_folder_id':'controlFolder123'}
        self.proof={}
        self.hb={'workerSha256':SHA,'triggerUid':'2456112746912022528','status':'runtime_budget_paused','blocked':[],'canaryAcknowledged':True,'deleteSource':False,'executionMode':'scheduled_bulk','executedAt':m.b.now_iso()}
        self.drive=Mock();self.drive.one.return_value={'id':'heartbeat123'}
        self.drive.meta.return_value={'parents':['controlFolder123'],'driveId':m.b.SOURCE_DRIVE,'trashed':False}
        self.promote=Mock(return_value={'status':'owner_probe_verified'})
        self.publisher=Mock()
    def run_resume(self):
        def read(path,default=None):
            return {'stage.json':self.stage,'corporate-stage.json':self.corp,'owner-acceptance.json':self.proof}.get(Path(path).name,default)
        self.drive.raw.return_value=json.dumps(self.hb).encode()
        with patch.object(m.b,'read_json',side_effect=read),patch.object(m.b,'config_load',return_value=self.config),patch.object(m.b,'Drive',return_value=self.drive),patch.object(m.b,'queue_lock',side_effect=contextlib.nullcontext),patch.object(m.b,'require_publisher',self.publisher),patch.object(m,'accept_owner',self.promote):
            return m.resume_acceptance()
    def test_paused_native_run_never_promotes_or_rewrites_configuration(self):
        self.assertEqual(self.run_resume()['status'],'awaiting_bulk_budget_recovery');self.promote.assert_not_called();self.publisher.assert_called_once()
    def test_healthy_native_run_promotes_once_without_production_activation(self):
        self.hb['status']='ok';r=self.run_resume();self.assertEqual(r['status'],'accepted');self.assertFalse(r['production_activation_performed']);self.assertFalse(r['migration_completion_asserted']);self.promote.assert_called_once_with()
    def test_unknown_future_pin_is_not_automatically_accepted(self):
        self.stage['worker_sha256']='b'*64;self.assertEqual(self.run_resume()['status'],'not_applicable');self.promote.assert_not_called();self.drive.one.assert_not_called()
    def test_missing_owner_setup_waits(self):
        self.corp['owner_setup_verified']=False;self.assertEqual(self.run_resume()['status'],'awaiting_corporate_setup');self.promote.assert_not_called()
    def test_missing_receipt_flag_remains_a_gate(self):
        self.corp['owner_setup_receipt_missing']=True;self.assertEqual(self.run_resume()['status'],'awaiting_corporate_setup');self.promote.assert_not_called()
    def test_wrong_worker_heartbeat_does_not_promote(self):
        self.hb['workerSha256']='c'*64;self.assertEqual(self.run_resume()['status'],'awaiting_expected_owner_schedule');self.promote.assert_not_called()
    def test_manual_execution_does_not_prove_schedule(self):
        self.hb['triggerUid']=None;self.assertEqual(self.run_resume()['status'],'awaiting_expected_owner_schedule');self.promote.assert_not_called()
    def test_wrong_trigger_is_not_accepted(self):
        self.hb['triggerUid']='different';self.assertEqual(self.run_resume()['status'],'awaiting_expected_owner_schedule');self.promote.assert_not_called()
    def test_stale_healthy_run_is_not_promoted(self):
        self.hb.update(status='ok',executedAt='2026-01-01T00:00:00Z');self.assertEqual(self.run_resume()['status'],'awaiting_fresh_owner_schedule');self.promote.assert_not_called()
    def test_nonempty_block_list_is_not_success(self):
        self.hb.update(status='ok',blocked=[{'reason':'PROBE_BLOCKED'}]);self.assertEqual(self.run_resume()['status'],'awaiting_healthy_owner_schedule');self.promote.assert_not_called()
    def test_owner_delete_false_is_required(self):
        self.hb['deleteSource']=True
        with self.assertRaisesRegex(m.b.ArchiveError,'HEARTBEAT_BINDING'):self.run_resume()
        self.promote.assert_not_called()
    def test_native_publisher_error_stops(self):
        self.publisher.side_effect=m.b.ArchiveError('PUBLISHER')
        with self.assertRaisesRegex(m.b.ArchiveError,'PUBLISHER'):self.run_resume()
        self.promote.assert_not_called()
    def test_missing_heartbeat_does_not_create_anything(self):
        self.drive.one.return_value=None;self.assertEqual(self.run_resume()['status'],'awaiting_expected_owner_schedule');self.promote.assert_not_called()
    def test_repeated_accepted_state_is_idempotent(self):
        self.config['worker_sha256']=SHA;self.proof={'status':'owner_probe_verified','scheduled_heartbeat':{'workerSha256':SHA}}
        self.assertEqual(self.run_resume()['status'],'accepted');self.promote.assert_not_called();self.drive.one.assert_not_called()
    def test_active_pin_without_independent_acceptance_proof_is_blocked(self):
        self.config['worker_sha256']=SHA
        with self.assertRaisesRegex(m.b.ArchiveError,'ACCEPTANCE_PROOF_MISSING'):self.run_resume()
        self.promote.assert_not_called()
if __name__=='__main__':unittest.main()
