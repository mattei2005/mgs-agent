"""Consolidated gate tests. Every destructive OS/audit/write call is mocked; RPC fixtures are synthetic."""
import pathlib,json,copy,importlib.util,unittest,subprocess,io,contextlib,os,stat,time,hashlib
from unittest.mock import patch
O=pathlib.Path(__file__).parent;spec=importlib.util.spec_from_file_location('g',O/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);M,DIGEST=g.load_manifest();rspec=importlib.util.spec_from_file_location('r',O/'retained-reader.py');assert rspec and rspec.loader;r=importlib.util.module_from_spec(rspec);rspec.loader.exec_module(r)
class Sink(io.StringIO):
 def fileno(self):return 9007
 def __exit__(self,*args)->None:return None
class GateTests(unittest.TestCase):
 def changed(self,fn):
  m=copy.deepcopy(M);fn(m)
  with self.assertRaises(RuntimeError):g.shape(m)
 def test_shape(self):self.assertTrue(g.shape(M))
 def test_reduced_scope(self):self.changed(lambda m:m['targets'].pop())
 def test_extra_scope(self):self.changed(lambda m:m['targets'].append(m['targets'][0]))
 def test_duplicate(self):self.changed(lambda m:m['targets'].__setitem__(0,m['targets'][1]))
 def test_path_drift(self):self.changed(lambda m:m['targets'][0].update(path='/root/NOT_APPROVED'))
 def test_kind_drift(self):self.changed(lambda m:m['targets'][0].update(kind='UNAPPROVED'))
 def test_reclaim(self):self.changed(lambda m:m.update(reclaim_bytes=m['reclaim_bytes']+4096))
 def test_hardlink(self):self.changed(lambda m:m['targets'][0]['metadata'].update(nlink=2))
 def test_inode_overlap(self):self.changed(lambda m:m['targets'][0].update(metadata=m['targets'][1]['metadata']))
 def test_wrong_request(self):self.changed(lambda m:m.update(request_message_id='1572270579850153987'))
 def test_wrong_thread(self):self.changed(lambda m:m.update(thread_id='OTHER'))
 def test_wrong_status(self):self.changed(lambda m:m.update(status='APPROVED_BY_INFERENCE'))
 def test_parent_scope(self):self.changed(lambda m:m['parent_directories'].pop(next(iter(m['parent_directories']))))
 def test_local_provider_count(self):self.changed(lambda m:m['local_providers'].pop(next(iter(m['local_providers']))))
 def test_media_provider_count(self):self.changed(lambda m:m['media_expected'].pop(next(iter(m['media_expected']))))
 def test_local_provider_digest(self):
  key=next(iter(M['local_providers']));self.changed(lambda m:m['local_providers'][key].update(sha256='0'*64))
 def test_media_provider_digest(self):
  sid=next(r['source_id']for r in M['targets']if r['kind']=='archived_media');self.changed(lambda m:m['media_expected'][sid].update(sha256='0'*64))
 def test_missing_approval(self):
  with self.assertRaises(RuntimeError):g.approval({},DIGEST,M)
 def test_previous_lot_approval_rejected(self):
  a=json.loads((O.parent/'storage-rollback-dumps-1572270579850153987/critical-approval.json').read_text())
  with self.assertRaises(RuntimeError):g.approval(a,DIGEST,M)
 def test_continue_is_not_exact_confirmation(self):
  a=dict(author_id=g.ACTOR,thread_id=g.THREAD,native_message_readback_verified=True,manifest_sha256=DIGEST,gate_sha256=M['gate_sha256'],question_message_id=g.REQUEST,confirmation_message_id=g.REQUEST)
  with self.assertRaises(RuntimeError):g.approval(a,DIGEST,M)
 def test_wrong_actor(self):
  with self.assertRaises(RuntimeError):g.approval(dict(author_id='OTHER'),DIGEST,M)
 def test_new_exact_reader_blocks(self):
  with patch.object(g,'source_inventory',return_value={'/x/new.py':'fixture'}),patch.object(pathlib.Path,'read_bytes',return_value=M['targets'][0]['path'].encode()):
   with self.assertRaisesRegex(RuntimeError,'NEW_OR_CHANGED_EXACT_TARGET_READER'):g.census(M)
 def job_index(self,next_run,enabled=True):
  body=json.dumps({'jobs':[{'id':'SYNTHETIC','prompt':'Read finance-system metadata','enabled':enabled,'next_run_at':next_run}]}).encode()
  with patch.object(g,'source_inventory',return_value={'/synthetic/cron/jobs.json':'fixture'}),patch.object(pathlib.Path,'read_bytes',return_value=body):return g.census(M)[0]
 def test_job_runtime_counter_ignored(self):self.assertEqual(self.job_index('A'),self.job_index('B'))
 def test_job_definition_change_detected(self):self.assertNotEqual(self.job_index('A',True),self.job_index('A',False))
 def test_unrelated_code_not_hard_bound(self):
  with patch.object(g,'source_inventory',return_value={'/unrelated/a.py':'fixture'}),patch.object(pathlib.Path,'read_bytes',return_value=b'print(1)'):self.assertEqual(g.census(M)[0],{})
 def test_apply_blocks_before_validation(self):
  with patch.object(g,'validate_local')as v,patch.object(g.os,'unlink')as u:
   with self.assertRaises(RuntimeError):g.apply(M,DIGEST,{})
   v.assert_not_called();u.assert_not_called()
 def test_completed_replay_guard_precedes_validation(self):
  with patch.object(g,'approval'),patch.object(pathlib.Path,'exists',return_value=True),patch.object(g,'validate_local')as v,patch.object(g.os,'unlink')as u:
   with self.assertRaisesRegex(RuntimeError,'REPLAY_BLOCKED'):g.apply(M,DIGEST,{'confirmation_message_id':'SYNTHETIC'})
   v.assert_not_called();u.assert_not_called()
 def test_missing_remote_proof(self):
  with patch.object(pathlib.Path,'is_file',return_value=False):
   with self.assertRaisesRegex(RuntimeError,'BOUNDED_NATIVE_REMOTE_PREFLIGHT_REQUIRED'):g.remote_proof(M,DIGEST,'prepare')
 def test_short_remote_proof(self):
  with patch.object(pathlib.Path,'is_file',return_value=True),patch.object(pathlib.Path,'read_text',return_value=''):
   with self.assertRaisesRegex(RuntimeError,'REMOTE_SCOPE'):g.remote_proof(M,DIGEST,'prepare')
 def simulation(self,fail=False):
  with contextlib.ExitStack()as s:
   s.enter_context(patch.object(g,'approval'));s.enter_context(patch.object(g,'remote_proof',return_value=248));s.enter_context(patch.object(g,'validate_local',return_value={'status':'MOCKED_PASS'}));a=s.enter_context(patch.object(g,'audit'));s.enter_context(patch.object(g.os,'open',return_value=9007));s.enter_context(patch.object(g.os,'fdopen',side_effect=lambda *a,**k:Sink()));s.enter_context(patch.object(g.os,'fsync'));s.enter_context(patch.object(pathlib.Path,'open',side_effect=lambda *a,**k:Sink()));s.enter_context(patch.object(pathlib.Path,'write_text',return_value=0));u=s.enter_context(patch.object(g.os,'unlink',side_effect=[None,RuntimeError('INJECTED')]if fail else None))
   if fail:
    with self.assertRaisesRegex(RuntimeError,'INJECTED'):g.apply(M,DIGEST,{'confirmation_message_id':'SYNTHETIC'})
    self.assertEqual(u.call_count,2);self.assertEqual(a.call_args.args[0],'storage_consolidated_exact_file_retirement_partial');self.assertEqual(len(a.call_args.args[1]['deleted_paths']),1)
   else:
    result=g.apply(M,DIGEST,{'confirmation_message_id':'SYNTHETIC'});self.assertEqual(u.call_count,643);self.assertEqual([x.args[0]for x in u.call_args_list],[x['path']for x in M['targets']]);self.assertEqual(result['deleted_directories'],0);self.assertEqual(result['status'],'files_removed_post_acceptance_pending')
 def test_mocked_exact_unlink_set(self):self.simulation()
 def test_mocked_partial_failure_no_replay(self):self.simulation(True)
class SyntheticRAMTests(unittest.TestCase):
 def setUp(self):
  self.data=b'MGS_SYNTHETIC_RETAINED_ONLY_FIXTURE';self.h=subprocess.run(['sha256sum'],input=self.data,capture_output=True,check=True).stdout.split()[0].decode();self.row={'metadata':dict(size=len(self.data),uid=os.getuid(),gid=os.getgid(),mode=stat.S_IFREG|0o600,mtime_ns=1700000000123456789),'sha256':self.h}
 def test_real_memfd(self):self.assertEqual(r.recover(self.row,self.data),self.h)
 def test_corruption(self):
  with self.assertRaises(AssertionError):r.recover(self.row,b'X'*len(self.data))
 def test_wrong_size(self):
  with self.assertRaises(AssertionError):r.recover(self.row,b'X')
before={r['path']:g.meta(r['path'])for r in M['targets']};suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(GateTests),unittest.defaultTestLoader.loadTestsFromTestCase(SyntheticRAMTests)]);result=unittest.TextTestRunner(verbosity=1).run(suite);assert result.wasSuccessful();assert before=={p:g.meta(p)for p in before};assert not(O/'execution-start.json').exists()and not(O/'deletion-journal.jsonl').exists();child=subprocess.run(['python3','-B',str(O/'gate.py'),'--apply'],capture_output=True,text=True);assert child.returncode!=0 and'NEW_NATIVE_EXACT_APPROVAL_REQUIRED'in child.stderr;assert not(O/'execution-start.json').exists();receipt=dict(status='PASS',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),real_source_files_deleted=0,all_destructive_OS_and_audit_calls_in_simulation_mocked=True,native_apply_without_new_exact_approval_blocked=True,all643_source_metadata_unchanged=True,synthetic_RPC_or_RAM_fixtures_not_remote_acceptance=True);p=O/'gate-tests.json'
if p.exists():assert json.loads(p.read_text())==receipt
else:p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
