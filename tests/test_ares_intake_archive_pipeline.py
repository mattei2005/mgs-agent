"""Offline deterministic continuation; every native/owner surface mocked."""
import copy, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_bridge as b
import ares_autonomous_intake as intake
import ares_intake_archive_pipeline as pipeline

class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
  self.entry={'owner':'native-owner','batch':{'batch_id':'syntheticbatch','sources':[{'source_id':'rawOffline001'}]},'status':'treated_waiting_archive','archive_source_ids':['rawOffline001','cleanOffline001']}
  original_read=b.read_json
  fixture_read=lambda path,default=None: original_read(path,default) if Path(path).parent==self.home else {'verified_jobs':{'syntheticjob':{}},'mappings':{}}
  self.patches=[patch.object(pipeline,'HOME',self.home),patch.object(pipeline,'enabled',return_value=True),patch.object(pipeline,'scoped_rows',return_value=[{'asset_id':'syntheticAsset'}]),patch.object(pipeline,'publish',return_value={'queued':[]}),patch.object(pipeline,'jobs_for',return_value=['syntheticjob']),patch.object(pipeline,'repair_aliases'),patch.object(pipeline,'verify_ready',return_value=[{'provider_id':'syntheticProvider','native_ack_verified':True}]),patch.object(pipeline,'child',return_value={'status':'ok','blocked':[]}),patch.object(b,'read_json',side_effect=fixture_read)]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def test_ready_batch_finishes_mechanically_without_model_or_owner_copy(self):
  with patch.object(pipeline,'progress',return_value={'mapped':2,'aliases':2,'transferred':2}),patch.object(intake,'batch_archive_ready',return_value=True):
   self.assertTrue(pipeline.advance(self.entry));pipeline.child.assert_not_called()
   receipt=json.loads((self.home/'batch-syntheticbatch.json').read_text());self.assertEqual(receipt['status'],'verified');self.assertEqual(len(receipt['records']),1)
 def test_two_rounds_keep_native_two_job_bound(self):
  pipeline.jobs_for.return_value=['notyetverified'];pipeline.publish.return_value={'queued':['one']}
  with patch.object(pipeline,'progress',side_effect=[{'mapped':0},{'mapped':2},{'mapped':2},{'mapped':4}]),patch.object(intake,'batch_archive_ready',side_effect=[False,True]):self.assertTrue(pipeline.advance(self.entry))
  self.assertEqual(pipeline.child.call_count,2)
  for call in pipeline.child.call_args_list:self.assertEqual(call.args[1],['tick','--apply','--max-jobs','2','--max-seconds','100','--origin','foreground'])
 def test_no_progress_does_not_spin(self):
  with patch.object(pipeline,'progress',return_value={'mapped':0}),patch.object(intake,'batch_archive_ready',return_value=False):self.assertFalse(pipeline.advance(self.entry))
  self.assertEqual(pipeline.publish.call_count,1)
 def test_blocked_component_preserves_blocked_receipt(self):
  pipeline.publish.side_effect=b.ArchiveError('synthetic-block')
  with patch.object(pipeline,'progress',return_value={'mapped':0}):
   with self.assertRaises(b.ArchiveError):pipeline.advance(self.entry)
  receipt=json.loads((self.home/'batch-syntheticbatch.json').read_text());self.assertEqual(receipt['status'],'blocked')
 def test_round_bounds(self):
  for rounds in [0,5,True]:
   with self.assertRaises(b.ArchiveError):pipeline.advance(self.entry,rounds)
 def test_existing_complete_preserves_first_times_and_proofs(self):
  entry={**self.entry,'status':'complete','treated_at':'first-treated','completed_at':'first-complete','proofs':[{'real':'frozen'}]};state={'claims':{'syntheticbatch':entry}}
  with patch.object(intake,'verify_completed',side_effect=AssertionError('do not re-treat')),patch.object(b,'Drive',side_effect=AssertionError('no native IO on replay')),patch('ares_archive_automation.run_cycle',side_effect=AssertionError('no replay cycle')):
   before=copy.deepcopy(entry);self.assertEqual(intake.finish_with_archive(state,entry['batch'],'native-owner'),before);self.assertEqual(entry,before)
 def test_owner_mismatch_stays_blocked_even_on_replay(self):
  entry={**self.entry,'status':'complete'}
  with self.assertRaises(intake.IntakeError):intake.finish_with_archive({'claims':{'syntheticbatch':entry}},entry['batch'],'other-owner')
 def test_child_unknown_or_blocked_never_succeeds(self):
  self.patches[-2].stop()
  with patch.object(pipeline.subprocess,'run',return_value=Mock(stdout='{"status":"blocked","blocked":["exact"]}',returncode=2)):
   with self.assertRaises(b.ArchiveError):pipeline.child('synthetic.py',[])
 def test_no_owner_grant_loaded_into_agent_process(self):
  text=Path(pipeline.__file__).read_text();self.assertNotIn('OwnerDrive()',text);self.assertNotIn('auth.json',text)
 def test_completed_flat_delivery_replay_preserves_first_receipt(self):
  import ares_flat_intake as flat
  batch={'flat_request_id':'syntheticRequest','batch_id':'syntheticbatch'}
  prior={'verified_at':'first-delivery','deliveries':[{'asset_id':'syntheticAsset','status':'common_ready_preserving_inventory_eligibility'}]}
  registry={'requests':{'syntheticRequest':{'completed_batches':{'syntheticbatch':prior}}}}
  state={'claims':{'syntheticbatch':{'status':'complete'}}}
  with patch.object(flat,'validate_batch_identity'),patch.object(b,'read_json',side_effect=[registry,state]),patch.object(b,'atomic_json',side_effect=AssertionError('no replay write')):
   result=flat.finalize_batch(batch)
  self.assertTrue(result['replay']);self.assertEqual(result['deliveries'],prior['deliveries']);self.assertEqual(prior['verified_at'],'first-delivery')
 def test_wrong_owner_mode_never_publishes(self):
  self.patches[3].stop()
  import contextlib
  @contextlib.contextmanager
  def lease():yield True
  with patch.object(b,'queue_lock',lease),patch.object(b,'config_load',return_value={'owner_executor_mode':'unsupported'}),patch.object(b,'Drive',side_effect=AssertionError('no identity fallback')):
   with self.assertRaises(b.ArchiveError):pipeline.publish([])
 def test_enabled_requires_exact_authority_and_boolean(self):
  self.patches[1].stop()
  for cfg in [{'archive_pipeline_enabled':True,'archive_pipeline_authority_message_id':'wrong'},{'archive_pipeline_enabled':'true','archive_pipeline_authority_message_id':pipeline.AUTHORITY}]:
   with patch.object(b,'read_json',return_value=cfg):self.assertFalse(pipeline.enabled())

if __name__=='__main__':unittest.main()
