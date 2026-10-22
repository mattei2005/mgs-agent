"""Offline 0s policy tests: confirmation selects retention, never skips safety gates."""
import sys,unittest,copy
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_retirement as r
from tests import test_ares_archive_retirement as fixture_tests
class ImmediateRetention(unittest.TestCase):
 def setUp(self):
  fixture_tests.RetirementTests.setUpClass();self.f=fixture_tests.RetirementTests();self.f.setUp();self.b=r.b
  self.auth={'schema':'mgs.archive.retirement.authorization.v1','confirmation_message_id':r.IMMEDIATE_CONFIRMATION,'confirmation_user_id':'344196393512075265','confirmation_thread_id':'1562078493498540042','source_drive_id':self.b.SOURCE_DRIVE,'source_root_id':self.b.SOURCE_ROOT,'archive_root_id':self.b.ARCHIVE_ROOT,'archive_owner':self.b.ACCOUNT,'retention_seconds':0,'max_pairs_per_run':2,'include_historical':False,'exclude_validation_jobs':True,'permanent_source_deletion':True,'supersedes_confirmation_message_id':r.CONFIRMATION,'all_integrity_access_consumer_gates_preserved':True,'effective_after':self.f.c['effective_after']}
  self.c={**self.f.c,'delete_source':True,'source_cleanup_confirmation_message_id':r.IMMEDIATE_CONFIRMATION,'source_cleanup_authorization_sha256':r.digest(self.auth),'retirements_folder_id':'retirementOffline001'}
 def fake_read(self,path,default=None):
  if Path(path)==self.b.CONFIG:return self.c
  if Path(path).name=='retirement-authorization-'+r.IMMEDIATE_CONFIRMATION+'.json':return self.auth
  raise AssertionError('Unexpected fixture read:'+str(path))
 def call_ready(self,now='2026-10-20T16:00:01Z'):
  with patch.object(self.b,'read_json',side_effect=self.fake_read):return r.candidate_ready(self.f.job,self.f.index,[self.f.row],self.f.state,self.c,now,'2026-10-20T16:00:00Z')
 def test_confirmed_zero_retention_accepts_one_second_after_ack_release(self):self.assertEqual(self.call_ready()['row']['asset_id'],self.f.row['asset_id'])
 def test_unknown_confirmation_rejected(self):
  with self.assertRaisesRegex(r.RetirementError,'UNKNOWN_CONFIRMATION'):r.authorization('not-approved')
 def test_zero_without_exact_pinned_digest_rejected(self):
  self.c['source_cleanup_authorization_sha256']='0'*64
  with self.assertRaises(r.RetirementError):self.call_ready()
 def test_scope_cannot_expand_to_history_by_changing_auth(self):
  self.auth['include_historical']=True
  with self.assertRaises(r.RetirementError):self.call_ready()
 def test_safety_gate_binding_required(self):
  self.auth['all_integrity_access_consumer_gates_preserved']=False
  with self.assertRaises(r.RetirementError):self.call_ready()
 def test_unreleased_batch_still_blocks(self):
  self.f.state['claims']['batchOffline001']['status']='treated_waiting_archive'
  with self.assertRaisesRegex(r.NotReady,'INTAKE_NOT_RELEASED'):self.call_ready()
 def test_missing_alias_still_blocks(self):
  self.f.index['mappings']['cleanOffline001'].pop('stockShortcutId')
  with self.assertRaisesRegex(r.NotReady,'ALIAS_NOT_READY'):self.call_ready()
 def test_future_release_or_ack_blocks_zero_retention(self):
  with self.assertRaisesRegex(r.NotReady,'IN_FUTURE'):self.call_ready('2026-10-20T15:59:59Z')
 def test_technical_fixture_remains_ineligible(self):
  self.f.job['validationOnly']=True
  with self.assertRaises(r.RetirementError):self.call_ready()
 def test_checksum_drift_still_blocks(self):
  self.f.row['clean_checksum']='0'*64
  with self.assertRaises(r.RetirementError):self.call_ready()
 def test_raw_active_claim_still_blocks(self):
  self.f.state['claims']['active']={'status':'claimed','batch':{'sources':[{'source_id':'rawOffline001'}]}}
  with self.assertRaisesRegex(r.NotReady,'ACTIVE_SOURCE_CLAIM'):self.call_ready()
 def test_default_auth_reads_raw_config_without_recursive_validation(self):
  with patch.object(self.b,'read_json',side_effect=self.fake_read),patch.object(self.b,'config_load',side_effect=AssertionError('RECURSIVE_CONFIG_LOAD')):self.assertEqual(r.authorization()['retention_seconds'],0)
if __name__=='__main__':unittest.main()
