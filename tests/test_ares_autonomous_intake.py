"""Offline tests: approved contextual intake without campaign or media writes."""
import unittest,importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('autonomous_intake',ROOT/'scripts/ares_autonomous_intake.py');assert spec and spec.loader
class IntakeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  assert spec is not None and spec.loader is not None
  cls.a=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.a)
 def setUp(self):
  self.slot={'folder_id':'slotOffline001','operation':'SHEIN_US_ES','manager_code':'g006','manager_name':'Nicolas'}
  self.row={'id':'sourceOffline001','name':'different-name.mp4','parents':['slotOffline001'],'mimeType':'video/mp4','size':'100','md5Checksum':'a'*32,'version':'1','createdTime':'2026-10-20T20:00:00Z'}
 def test_context_comes_from_registered_id_not_filename(self):
  d=self.a.describe(self.row,self.slot);self.assertEqual(d['operation'],'SHEIN_US_ES');self.assertEqual(d['manager_code'],'g006');self.assertEqual(d['source_id'],self.row['id'])
 def test_wrong_parent_rejected(self):
  self.row['parents']=['outsideOffline']
  with self.assertRaises(self.a.IntakeError):self.a.describe(self.row,self.slot)
 def test_missing_checksum_is_upload_incomplete(self):
  del self.row['md5Checksum']
  with self.assertRaises(self.a.IntakeError):self.a.describe(self.row,self.slot)
 def test_stability_requires_three_identical_polls_and_40_seconds(self):
  state={};d=[self.a.describe(self.row,self.slot)]
  self.assertFalse(self.a.observe(state,d,100)['stable']);self.assertFalse(self.a.observe(state,d,120)['stable']);self.assertTrue(self.a.observe(state,d,140)['stable'])
 def test_content_change_resets_stability(self):
  state={};d=[self.a.describe(self.row,self.slot)];self.a.observe(state,d,100);self.a.observe(state,d,120);d[0]['size']='101';self.assertFalse(self.a.observe(state,d,140)['stable'])
 def test_batch_is_operation_manager_scoped_and_bounded(self):
  d=self.a.describe(self.row,self.slot);other={**d,'source_id':'sourceOffline002','manager_code':'g005','manager_name':'Kelly'};batch=self.a.make_batch([d,other],set(),limit=4);self.assertEqual(len(batch['sources']),1);self.assertEqual(batch['pending_total'],2)
 def test_inventory_and_completed_ids_are_excluded(self):
  d=self.a.describe(self.row,self.slot);self.assertIsNone(self.a.make_batch([d],{d['source_id']}))
 def test_same_snapshot_batch_id_is_stable(self):
  d=[self.a.describe(self.row,self.slot)];self.assertEqual(self.a.make_batch(d,set())['batch_id'],self.a.make_batch(d,set())['batch_id'])
 def test_claim_blocks_parallel_owner(self):
  b=self.a.make_batch([self.a.describe(self.row,self.slot)],set());s={};self.a.claim(s,b,'cron-owner-one')
  with self.assertRaises(self.a.IntakeError):self.a.claim(s,b,'second-writer')
 def test_claim_replay_reuses_same_batch(self):
  b=self.a.make_batch([self.a.describe(self.row,self.slot)],set());s={};self.assertEqual(self.a.claim(s,b,'same'),self.a.claim(s,b,'same'))
 def test_completed_requires_both_source_and_clean_proofs(self):
  b=self.a.make_batch([self.a.describe(self.row,self.slot)],set());s={};self.a.claim(s,b,'same')
  with self.assertRaises(self.a.IntakeError):self.a.complete(s,b['batch_id'],'same',[])
 def test_descriptor_cannot_change_operation_to_new_scope(self):
  self.slot['operation']='OUTSIDE_INVALID'
  with self.assertRaises(self.a.IntakeError):self.a.describe(self.row,self.slot)
 def test_duplicate_protected_fields_must_remain_identical(self):
  old={'asset_id':'a','ares_eligible':False,'used_by':'existingCampaign','reservation_status':'RESERVADO_PELO_REQUEST','clean_checksum':'a'*64}
  baseline={'a':[self.a.protected_fingerprint(old)]}
  self.assertTrue(self.a.verify_reservation(old,baseline,self.slot))
  changed={**old,'ares_eligible':True}
  with self.assertRaises(self.a.IntakeError):self.a.verify_reservation(changed,baseline,self.slot)
 def test_new_lineage_reservation_requires_exact_manager_and_no_use(self):
  row={'asset_id':'new','source_manager':'Nicolas','ares_eligible':False,'used_by':None,'reservation_status':'RESERVADO_PELO_GESTOR'}
  self.assertTrue(self.a.verify_reservation(row,{},self.slot))
  with self.assertRaises(self.a.IntakeError):self.a.verify_reservation({**row,'source_manager':'Kelly'},{},self.slot)
 def test_selftest_never_accepts_operational_parent_or_unpinned_raw(self):
  config={'schema':'mgs.intake.selftest.v1','validation_only':True,'run_id':'1562188030205362227','raw_source_id':'sourceOffline001','raw_sha256':'a'*64,'upload_parent_id':'uploadOffline001','legacy_parent_id':'legacyOffline001','ready_parent_id':'readyOffline001'}
  raw={'id':'sourceOffline001','parents':['legacyOffline001'],'properties':{'mgsArchiveType':'intake_test_media'}};clean={'id':'cleanOffline001','parents':['readyOffline001'],'properties':{'mgsArchiveType':'intake_test_media'}}
  self.assertTrue(self.a.validate_selftest_identity(config,raw,clean,'a'*64))
  with self.assertRaises(self.a.IntakeError):self.a.validate_selftest_identity(config,raw,{**clean,'parents':['OPERATIONAL']},'a'*64)
  with self.assertRaises(self.a.IntakeError):self.a.validate_selftest_identity(config,raw,clean,'b'*64)
 def test_archive_completion_waits_for_every_verified_alias(self):
  entry={'archive_source_ids':['rawOffline001','cleanOffline001']};index={'mappings':{'rawOffline001':{'verified':True,'stockShortcutId':'a'}}}
  self.assertFalse(self.a.batch_archive_ready(entry,index));index['mappings']['cleanOffline001']={'verified':True,'stockShortcutId':'b'};self.assertTrue(self.a.batch_archive_ready(entry,index))
if __name__=='__main__':unittest.main()
