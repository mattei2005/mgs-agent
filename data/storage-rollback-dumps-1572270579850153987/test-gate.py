"""Gate regressions and explicitly synthetic RAM-reader tests. No real unlink or remote business calls."""
import contextlib,copy,hashlib,importlib.util,io,json,os,pathlib,stat,subprocess,unittest
from unittest.mock import patch
O=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('g',O/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
spec2=importlib.util.spec_from_file_location('ram_reader',O/'retained-ram-reader.py');assert spec2 and spec2.loader;r=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(r)
M=json.loads((O/'manifest.json').read_text());DIGEST=(O/'manifest.sha256').read_text().split()[0]
class Sink(io.StringIO):
 def fileno(self):return 9007
 def __exit__(self,*args)->None:return None
class GateTests(unittest.TestCase):
 def changed(self,fn):
  m=copy.deepcopy(M);fn(m)
  with self.assertRaises(RuntimeError):g.shape(m)
 def test_shape_positive(self):self.assertTrue(g.shape(M))
 def test_reduced_count(self):self.changed(lambda m:m['targets'].pop())
 def test_scope(self):self.changed(lambda m:m['targets'][0].update(path='/root/NOT_IN_SCOPE'))
 def test_duplicate(self):self.changed(lambda m:m['targets'].__setitem__(0,m['targets'][1]))
 def test_old_request(self):self.changed(lambda m:m.update(request_message_id='1572257170626580601'))
 def test_reclaim(self):self.changed(lambda m:m.update(reclaim_bytes=m['reclaim_bytes']+4096))
 def test_hardlink(self):self.changed(lambda m:m['targets'][0]['metadata'].update(nlink=2))
 def test_lost_newest(self):self.changed(lambda m:m['retained_local_dumps'][-1].update(path='/root/no_latest'))
 def test_reduced_retained(self):self.changed(lambda m:m['retained_reviewed_files'].pop())
 def test_remote_scope(self):self.changed(lambda m:m['remote_recovery'][0].update(remote_path='/tmp/NOT_ALLOWED.dump'))
 def test_remote_digest_binding(self):self.changed(lambda m:m['remote_recovery'][0].update(sha256='0'*64))
 def test_remote_traversal(self):self.changed(lambda m:m['remote_recovery'][0].update(remote_path='/home/zeus/mgs-finance-backups/../escape.dump'))
 def test_missing_approval(self):
  with self.assertRaises(RuntimeError):g.approval({},DIGEST,M['gate_sha256'])
 def test_previous_four_file_approval_does_not_authorize_new_lot(self):
  a=json.loads((O.parent/'storage-finance-archives-1572257170626580601/critical-approval.json').read_text())
  with self.assertRaises(RuntimeError):g.approval(a,DIGEST,M['gate_sha256'])
 def test_request_not_confirmation(self):
  a=dict(author_id='344196393512075265',thread_id='1569928464033783862',native_message_readback_verified=True,manifest_sha256=DIGEST,gate_sha256=M['gate_sha256'],confirmation_message_id='1572270579850153987')
  with self.assertRaises(RuntimeError):g.approval(a,DIGEST,M['gate_sha256'])
 def test_new_reader_detected(self):
  with patch.object(g,'full_code_inventory',return_value={'reader.py':'fixture'}),patch.object(pathlib.Path,'read_bytes',return_value=M['targets'][0]['path'].encode()):
   with self.assertRaisesRegex(RuntimeError,'NEW_OR_CHANGED_TARGET_REFERENCE'):g.census([x['path']for x in M['targets']])
 def test_generic_filename_not_an_exact_owner_selector(self):self.assertFalse(g.select_target(b'finance-before.dump','reader.py',[x['path']for x in M['targets']]))
 def test_owner_local_filename_selector_detected(self):
  t=M['targets'][0];self.assertTrue(g.select_target(pathlib.Path(t['path']).name.encode(),str(pathlib.Path(t['path']).parent/'reader.py'),[t['path']]))
 def test_json_dumps_is_not_dump_filename(self):self.assertFalse(g.select_target(b'json.dumps(state)',str(pathlib.Path(M['targets'][0]['path']).parent/'reader.py'),[M['targets'][0]['path']]))
 def test_apply_without_approval_blocks_before_validate(self):
  with patch.object(g,'validate')as v,patch.object(g.os,'unlink')as u:
   with self.assertRaises(RuntimeError):g.apply(M,DIGEST,{})
   v.assert_not_called();u.assert_not_called()
 def simulation(self,fail_second=False):
  with contextlib.ExitStack()as s:
   s.enter_context(patch.object(g,'approval'));v=s.enter_context(patch.object(g,'validate',return_value={'status':'MOCKED_PASS'}));audit=s.enter_context(patch.object(g,'audit'));s.enter_context(patch.object(g.os,'open',return_value=9007));s.enter_context(patch.object(g.os,'fdopen',side_effect=lambda *a,**k:Sink()));s.enter_context(patch.object(g.os,'fsync'));s.enter_context(patch.object(pathlib.Path,'open',side_effect=lambda *a,**k:Sink()));s.enter_context(patch.object(pathlib.Path,'write_text',return_value=0));u=s.enter_context(patch.object(g.os,'unlink',side_effect=[None,RuntimeError('INJECTED')]if fail_second else None))
   if fail_second:
    with self.assertRaisesRegex(RuntimeError,'INJECTED'):g.apply(M,DIGEST,{'confirmation_message_id':'SYNTHETIC_ONLY'})
    self.assertEqual(u.call_count,2);self.assertEqual(audit.call_args.args[0],'historical_rollback_local_dump_retirement_partial');self.assertEqual(len(audit.call_args.args[1]['deleted']),1)
   else:
    out=g.apply(M,DIGEST,{'confirmation_message_id':'SYNTHETIC_ONLY'});self.assertEqual(out['deleted'],[x['path']for x in M['targets']]);self.assertEqual(u.call_count,29);self.assertEqual(v.call_count,2)
 def test_mocked_exact29_unlink_order(self):self.simulation()
 def test_mocked_partial_failure_no_blind_replay(self):self.simulation(True)
class SyntheticReaderTests(unittest.TestCase):
 def setUp(self):
  self.payload=b'MGS_SYNTHETIC_RAM_FIXTURE';self.digest=subprocess.run(['sha256sum'],input=self.payload,capture_output=True,check=True).stdout.split()[0].decode();self.row={'path':'/synthetic/fixture.dump','remote_candidates':['/home/zeus/mgs-finance-backups/SYNTHETIC_FIXTURE/fixture.dump'],'sha256':self.digest,'metadata':dict(size=len(self.payload),uid=os.getuid(),gid=os.getgid(),mode=stat.S_IFREG|0o600,mtime_ns=1700000000123456789)}
 def transport(self,command,**kwargs):
  if'cat -- 'in command:return self.payload
  return(self.digest+'  SYNTHETIC\n'+str(len(self.payload))+'\nCATALOGUE_OK').encode()
 def test_real_RAM_file_synthetic_fixture(self):
  proof=r.recover(self.row,self.transport);self.assertEqual(proof['actual_recovered_sha256'],self.digest);self.assertEqual(proof['source_payload_reads'],0);self.assertTrue(proof['mode_owner_nanosecond_mtime_restored'])
 def test_corrupt_payload(self):
  def corrupt(command,**kwargs):return b'X'*len(self.payload)if'cat -- 'in command else self.transport(command)
  with self.assertRaisesRegex(RuntimeError,'MATERIALIZED_RAM_PAYLOAD_SHA256'):r.recover(self.row,corrupt)
 def test_wrong_length(self):
  def short(command,**kwargs):return b'X'if'cat -- 'in command else self.transport(command)
  with self.assertRaisesRegex(RuntimeError,'FULL_BINARY_TRANSFER'):r.recover(self.row,short)
 def test_bad_remote_catalogue(self):
  with self.assertRaisesRegex(RuntimeError,'REMOTE_HASH_SIZE_OR_CATALOGUE'):r.recover(self.row,lambda *a,**k:b'BROKEN')
 def test_unsafe_remote_path(self):
  self.row['remote_candidates']=['/home/zeus/mgs-finance-backups/../unsafe.dump']
  with self.assertRaisesRegex(RuntimeError,'REMOTE_EXACT_ALLOWLIST'):r.recover(self.row,self.transport)
 def test_headroom(self):
  with patch.object(pathlib.Path,'read_text',return_value='MemAvailable: 1024 kB\n'):
   with self.assertRaisesRegex(RuntimeError,'MEMORY_HEADROOM'):r.recover(self.row,self.transport)
 def test_sudo_read_only_for_exact_original_privileged_route(self):
  self.row['remote_candidates']=['/home/zeus/mgs-finance-backups/month-prune-1556898264878419969/finance-before.dump'];calls=[]
  def captured(command,**kwargs):calls.append(command);return self.transport(command)
  r.recover(self.row,captured);self.assertEqual(len(calls),2);self.assertTrue(all(c.startswith('sudo -n ')for c in calls));self.assertFalse(any(word in' '.join(calls)for word in ['chmod','chown','mkdir','createdb','pg_dump']))
before={x['path']:g.meta(x['path'])for x in M['targets']};suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(GateTests),unittest.defaultTestLoader.loadTestsFromTestCase(SyntheticReaderTests)]);result=unittest.TextTestRunner(verbosity=1).run(suite);assert result.wasSuccessful();assert before=={p:g.meta(p)for p in before};assert not(O/'execution-start.json').exists()and not(O/'deletion-journal.jsonl').exists()
child=subprocess.run(['python3','-B',str(O/'gate.py'),'--apply'],capture_output=True,text=True);assert child.returncode!=0 and'NEW_EXACT_NATIVE_OWNER_APPROVAL_REQUIRED'in child.stderr;assert not(O/'execution-start.json').exists()
receipt=dict(status='PASS',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),all_destructive_OS_calls_in_simulation_mocked=True,native_apply_without_new_approval_blocked=True,all29_real_targets_metadata_unchanged=True,real_source_files_deleted=0,synthetic_RAM_tests_not_remote_acceptance=True)
f=O/'gate-tests.json'
if f.exists():assert json.loads(f.read_text())==receipt
else:f.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
