"""Exact gate regressions. All unlink/write/audit calls in apply simulation are mocked."""
import contextlib,copy,importlib.util,io,json,pathlib,subprocess,unittest
from unittest.mock import patch
O=pathlib.Path(__file__).parent;spec=importlib.util.spec_from_file_location('g',O/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);M=json.loads((O/'manifest.json').read_text());DIGEST=(O/'manifest.sha256').read_text().split()[0]
class Sink(io.StringIO):
 def fileno(self):return 9007
 def __exit__(self,*args)->None:return None
class Tests(unittest.TestCase):
 def changed(self,fn):
  m=copy.deepcopy(M);fn(m)
  with self.assertRaises(RuntimeError):g.shape(m)
 def test_shape_positive(self):self.assertTrue(g.shape(M))
 def test_reduced_count(self):self.changed(lambda m:m['targets'].pop())
 def test_scope(self):self.changed(lambda m:m['targets'][0].update(path='/root/NOT_IN_SCOPE'))
 def test_duplicate(self):self.changed(lambda m:m['targets'].__setitem__(0,m['targets'][1]))
 def test_old_request(self):self.changed(lambda m:m.update(request_message_id='1570807018380599409'))
 def test_reclaim(self):self.changed(lambda m:m.update(reclaim_bytes=m['reclaim_bytes']+4096))
 def test_hardlink(self):self.changed(lambda m:m['targets'][0]['metadata'].update(nlink=2))
 def test_lost_newest(self):self.changed(lambda m:m['retained_local_dumps'][-1].update(path='/root/no_latest'))
 def test_reduced_retained(self):self.changed(lambda m:m['retained_reviewed_files'].pop())
 def test_remote_scope(self):self.changed(lambda m:m['remote_recovery'][0].update(remote_path='/tmp/not_authorized.dump'))
 def test_remote_digest_binding(self):self.changed(lambda m:m['remote_recovery'][0].update(sha256='0'*64))
 def test_missing_approval(self):
  with self.assertRaises(RuntimeError):g.approval({},DIGEST,M['gate_sha256'])
 def test_request_not_confirmation(self):
  a={'author_id':'344196393512075265','thread_id':'1569928464033783862','native_message_readback_verified':True,'manifest_sha256':DIGEST,'gate_sha256':M['gate_sha256'],'confirmation_message_id':'1572257170626580601'}
  with self.assertRaises(RuntimeError):g.approval(a,DIGEST,M['gate_sha256'])
 def test_new_reader_detected(self):
  with patch.object(g,'full_code_inventory',return_value={'reader.py':'fixture'}),patch.object(pathlib.Path,'read_bytes',return_value=M['targets'][0]['path'].encode()):
   with self.assertRaisesRegex(RuntimeError,'NEW_TARGET'):g.census([r['path']for r in M['targets']])
 def test_path_boundary_sibling_not_literal(self):
  # A generic filename is a family signal, not an exact four-run path reference.
  self.assertFalse(g.select_target(b'mgs_finance-before.dump','reader.py',[x['path']for x in M['targets']]))
 def test_apply_without_approval_blocks_before_validate(self):
  with patch.object(g,'validate')as v,patch.object(g.os,'unlink')as u:
   with self.assertRaises(RuntimeError):g.apply(M,DIGEST,{})
   v.assert_not_called();u.assert_not_called()
 def simulation(self,fail_second=False):
  with contextlib.ExitStack()as stack:
   stack.enter_context(patch.object(g,'approval'));v=stack.enter_context(patch.object(g,'validate',return_value={'status':'MOCKED_PASS'}));audit=stack.enter_context(patch.object(g,'audit'));stack.enter_context(patch.object(g.os,'open',return_value=9007));stack.enter_context(patch.object(g.os,'fdopen',side_effect=lambda *a,**k:Sink()));stack.enter_context(patch.object(g.os,'fsync'));stack.enter_context(patch.object(pathlib.Path,'open',side_effect=lambda *a,**k:Sink()));stack.enter_context(patch.object(pathlib.Path,'write_text',return_value=0));u=stack.enter_context(patch.object(g.os,'unlink',side_effect=[None,RuntimeError('INJECTED')]if fail_second else None))
   if fail_second:
    with self.assertRaisesRegex(RuntimeError,'INJECTED'):g.apply(M,DIGEST,{'confirmation_message_id':'SYNTHETIC_ONLY'})
    self.assertEqual(u.call_count,2);self.assertEqual(audit.call_args.args[0],'four_local_remote_mirrored_dump_retirement_partial');self.assertEqual(len(audit.call_args.args[1]['deleted']),1)
   else:
    out=g.apply(M,DIGEST,{'confirmation_message_id':'SYNTHETIC_ONLY'});self.assertEqual(out['deleted'],[x['path']for x in M['targets']]);self.assertEqual(u.call_count,4);self.assertEqual(v.call_count,2)
 def test_mocked_exact_four_unlink_order(self):self.simulation()
 def test_mocked_partial_failure_no_blind_replay(self):self.simulation(True)
before={r['path']:g.meta(r['path'])for r in M['targets']};suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);result=unittest.TextTestRunner(verbosity=1).run(suite);assert result.wasSuccessful();assert before=={p:g.meta(p)for p in before};assert not(O/'execution-start.json').exists()and not(O/'deletion-journal.jsonl').exists()
p=subprocess.run(['python3','-B',str(O/'gate.py'),'--apply'],capture_output=True,text=True);assert p.returncode!=0 and'NEW_EXACT_NATIVE_OWNER_APPROVAL_REQUIRED'in p.stderr;assert not(O/'execution-start.json').exists()
receipt={'status':'PASS','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'all_destructive_OS_calls_in_simulation_mocked':True,'native_apply_without_new_approval_blocked':True,'all_four_real_files_metadata_unchanged':True,'real_source_files_deleted':0}
if (O/'gate-tests.json').exists():assert json.loads((O/'gate-tests.json').read_text())==receipt
else:(O/'gate-tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
