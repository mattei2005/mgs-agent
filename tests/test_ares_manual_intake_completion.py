"""Offline manual-intake closure tests; no Google, scheduler or production writes."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_autonomous_intake as intake

class ManualCompletionTests(unittest.TestCase):
 def setUp(self):
  import ares_manual_intake_completion as m
  self.m=m
  self.thread='1565379383017873569'
  self.item={'id':'rawOffline001','name':'original.jpg','raw_sha256':'a'*64,'md5Checksum':'c'*32,'size':'101','mimeType':'image/jpeg','createdTime':'2026-10-29T14:00:00Z','parents':['uploadOffline001'],'final_name':'SHEIN_US_EN_IMG_TEST_NV_001.jpg','asset_id':'asset_offline','clean_sha256':'b'*64,'clean_size':99}
  self.plan={'schema':'mgs.manual.intake.plan.v1','thread_id':self.thread,'operation':'SHEIN_US_EN','manager':'Kelly','source_parent':'uploadOffline001','expected_count':1,'items':[self.item]}
  self.execution={'phase':'complete','items':{'rawOffline001':{'dest_id':'cleanOffline001','destination_verified':True,'inventory_verified':True,'legacy_verified':True}}}
  self.audit={'status':'complete','received_sources':1,'new_ready_assets':1,'pending_scoped':0,'all_metadata_clean':True,'all_reservations_preserved':True,'proofs':[{'source_id':'rawOffline001','dest_id':'cleanOffline001'}]}
  self.source=copy.deepcopy(self.item)
  self.proofs=[{'source_id':'rawOffline001','clean_source_id':'cleanOffline001','raw_sha256':'a'*64,'clean_sha256':'b'*64,'source_parent_verified':True,'clean_verified':True,'inventory_verified':True,'reservation_preserved':True}]
 def batch(self):return self.m.make_manual_batch(self.plan,[self.source],self.execution,self.audit,'1291113428982693940')
 def test_build_exact_stable_manual_batch(self):
  b=self.batch();self.assertEqual(b,self.batch());self.assertEqual(b['scope_type'],'explicit_manual_request');self.assertEqual(b['sources'][0]['source_id'],self.item['id']);self.assertEqual(b['manager_code'],'g005')
 def test_missing_audit_rejected(self):
  self.audit['status']='pending'
  with self.assertRaises(self.m.CompletionError):self.batch()
 def test_waiting_archive_not_completed(self):
  self.execution['phase']='treated_waiting_archive'
  with self.assertRaises(self.m.CompletionError):self.batch()
 def test_missing_final_audit_source_rejected(self):
  self.audit['proofs']=[]
  with self.assertRaises(self.m.CompletionError):self.batch()
 def test_changed_source_hash_rejected(self):
  self.source['raw_sha256']='d'*64
  with self.assertRaises(self.m.CompletionError):self.batch()
 def test_source_set_cannot_shrink(self):
  with self.assertRaises(self.m.CompletionError):self.m.make_manual_batch(self.plan,[],self.execution,self.audit,'1291113428982693940')
 def test_duplicate_sources_rejected(self):
  self.plan['items'].append(copy.deepcopy(self.item));self.plan['expected_count']=2
  with self.assertRaises(self.m.CompletionError):self.batch()
 def test_unknown_manager_rejected(self):
  self.plan['manager']='Unknown'
  with self.assertRaises(self.m.CompletionError):self.batch()
 def test_malformed_requester_rejected(self):
  with self.assertRaises(self.m.CompletionError):self.m.make_manual_batch(self.plan,[self.source],self.execution,self.audit,'bad')
 def test_incomplete_item_state_rejected(self):
  self.execution['items']['rawOffline001']['legacy_verified']=False
  with self.assertRaises(self.m.CompletionError):self.batch()
 def test_commit_records_real_completion_and_all_binary_ids(self):
  state={'claims':{},'completed':{}};batch=self.batch()
  entry=self.m.record_completion(state,batch,self.proofs,'evidence-sha','data/execution/final-audit.json')
  self.assertEqual(entry['status'],'complete');self.assertEqual(state['completed']['rawOffline001'],batch['batch_id']);self.assertEqual(entry['archive_source_ids'],['rawOffline001','cleanOffline001'])
 def test_replay_preserves_original_timestamps(self):
  s={'claims':{},'completed':{}};b=self.batch();first=copy.deepcopy(self.m.record_completion(s,b,self.proofs,'same','audit.json'))
  again=self.m.record_completion(s,b,self.proofs,'same','audit.json');self.assertEqual(first,again);self.assertEqual(len(s['claims']),1)
 def test_replay_changed_evidence_rejected(self):
  s={'claims':{},'completed':{}};b=self.batch();self.m.record_completion(s,b,self.proofs,'one','audit.json')
  with self.assertRaises(self.m.CompletionError):self.m.record_completion(s,b,self.proofs,'two','audit.json')
 def test_conflicting_active_claim_rejected(self):
  s={'claims':{'other':{'owner':'cron','status':'claimed','batch':{'batch_id':'other','sources':[{'source_id':'rawOffline001'}]}}},'completed':{}}
  with self.assertRaises(self.m.CompletionError):self.m.record_completion(s,self.batch(),self.proofs,'same','audit.json')
 def test_second_completed_claim_rejected(self):
  s={'claims':{'other':{'owner':'other','status':'complete','batch':{'batch_id':'other','sources':[{'source_id':'rawOffline001'}]}}},'completed':{}}
  with self.assertRaises(self.m.CompletionError):self.m.record_completion(s,self.batch(),self.proofs,'same','audit.json')
 def test_incomplete_proofs_do_not_mutate_state(self):
  s={'claims':{},'completed':{}};before=copy.deepcopy(s)
  with self.assertRaises((self.m.CompletionError,intake.IntakeError)):self.m.record_completion(s,self.batch(),[],'same','audit.json')
  self.assertEqual(s,before)
 def test_duplicate_or_mismatched_clean_proof_rejected(self):
  s={'claims':{},'completed':{}};self.proofs[0]['clean_source_id']='rawOffline001'
  with self.assertRaises(self.m.CompletionError):self.m.record_completion(s,self.batch(),self.proofs,'same','audit.json')
 def test_failed_proof_flag_does_not_mutate_state(self):
  s={'claims':{},'completed':{}};self.proofs[0]['clean_verified']=False
  with self.assertRaises((self.m.CompletionError,intake.IntakeError)):self.m.record_completion(s,self.batch(),self.proofs,'same','audit.json')
  self.assertEqual(s,{'claims':{},'completed':{}})
 def test_local_manifest_path_cannot_escape_execution_root(self):
  with self.assertRaises(self.m.CompletionError):self.m.resolve_execution('/etc')
 def test_release_does_not_change_cleanup_policy(self):
  s={'claims':{},'completed':{}};b=self.batch()
  with patch.object(intake.bridge,'atomic_json',side_effect=AssertionError('production write forbidden')):
   self.m.record_completion(s,b,self.proofs,'same','audit.json')
  self.assertNotIn('delete_source',s)
if __name__=='__main__':unittest.main()
