"""Negative gates plus a fully mocked deletion-order unit test. No real unlink/rmdir."""
import pathlib,json,copy,subprocess,importlib.util,io,types,stat
from unittest.mock import patch,mock_open
OUT=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('gate_tested',OUT/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);m=json.load(open(OUT/'manifest.json'));passed=[]
def deny(name,change,fn):
 n=copy.deepcopy(m);change(n)
 try:fn(n)
 except(RuntimeError,FileNotFoundError):passed.append(name)
 else:raise AssertionError('Gate accepted '+name)
deny('wrong_request',lambda n:n.update(request_message_id='wrong'),g.shape)
deny('wrong_status',lambda n:n.update(status='approved'),g.shape)
deny('scope_reduction',lambda n:n['targets'].pop(),g.shape)
deny('scope_expansion',lambda n:n['targets'].append(copy.deepcopy(n['targets'][0])),g.shape)
deny('wrong_parent',lambda n:n['targets'][0].update(path='/etc/'+pathlib.Path(n['targets'][0]['path']).name),g.shape)
deny('count_tamper',lambda n:n['counts'].update(file=n['counts']['file']+1),g.shape)
deny('retained_set_reduction',lambda n:n['retained_roots'].pop(),g.shape)
deny('retained_duplicate',lambda n:n['retained_roots'].__setitem__(0,copy.deepcopy(n['retained_roots'][1])),g.shape)
deny('gate_hash_tamper',lambda n:n.update(gate_sha256='0'*64),g.check)
deny('runtime_drift',lambda n:n.update(runtime={}),g.check)
deny('launcher_drift',lambda n:n.update(launcher='/nonexistent'),g.check)
deny('target_metadata_drift',lambda n:n['targets'][0]['metadata'].update(fingerprint_sha256='0'*64),g.check)
deny('retained_metadata_drift',lambda n:n['retained_roots'][0]['metadata'].update(fingerprint_sha256='0'*64),g.check)
deny('protected_index_hash_drift',lambda n:n.update(payload_index_sha256='0'*64),g.check)
# Native apply with no approval must stop before an execution marker or any source deletion.
r=subprocess.run(['python3','-B',str(OUT/'gate.py'),'--apply'],capture_output=True,text=True);assert r.returncode!=0 and'NEW_NATIVE_OWNER_CONFIRMATION_REQUIRED'in(r.stdout+r.stderr);assert not(OUT/'execution-start.json').exists();passed.append('native_apply_denied_without_new_owner_confirmation')
# Explicitly synthetic OS call unit test; every destructive call and result write is mocked in memory.
synthetic=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch/synthetic-local-test-gate-no-real-files');fake=copy.deepcopy(m);fake['targets']=[];fake['retained_roots']=[];nodes={};stats={};wanted=[]
for i in range(6):
 root=str(synthetic/str(i));fake['targets'].append(dict(path=root));rows=[['.','directory',1,100+i*2,4096,8,1,2,448,0,0],['data.bin','file',1,101+i*2,3,8,1,1,384,0,0]];nodes[root]=rows
 for row in rows:stats[str(pathlib.Path(root)/row[0])]=types.SimpleNamespace(st_mode=stat.S_IFDIR|448 if row[1]=='directory'else stat.S_IFREG|384,st_dev=row[2],st_ino=row[3],st_size=row[4],st_mtime_ns=row[6])
 wanted.extend([('file',str(pathlib.Path(root)/'data.bin')),('directory',root)])
class SyntheticBuffer(io.StringIO):
 def fileno(self):return 1234
calls=[]
with patch.object(g,'OUT',synthetic),patch.object(g,'approval',return_value={'confirmation_message_id':'SYNTHETIC_TEST_NOT_APPROVAL'}),patch.object(g,'check',return_value={'status':'UNIT_TEST_ONLY'}),patch.object(g,'sha',return_value=fake['target_node_index_sha256']),patch.object(g.gzip,'open',side_effect=[io.StringIO(json.dumps(nodes)),io.StringIO('{}')]),patch.object(g.os,'open',return_value=1234),patch.object(g.os,'fdopen',return_value=SyntheticBuffer()),patch.object(g.os,'fsync'),patch.object(g,'audit'),patch.object(g,'open',mock_open(),create=True),patch.object(g.os,'lstat',side_effect=lambda p:stats[str(p)]),patch.object(g.os,'unlink',side_effect=lambda p:calls.append(('file',str(p)))),patch.object(g.os,'rmdir',side_effect=lambda p:calls.append(('directory',str(p)))),patch.object(g.os.path,'lexists',return_value=False),patch.object(g,'health',return_value=fake['runtime']),patch.object(pathlib.Path,'write_text',return_value=0):
 result=g.apply(fake,'SYNTHETIC_ONLY');assert result['deleted_nodes']==12
assert calls==wanted;assert all(pathlib.Path(r['path']).is_dir()for r in m['targets']);assert not(OUT/'execution-start.json').exists();passed.append('fully_mocked_exact_nodes_and_order_no_actual_delete')
summary=dict(status='PASS',tests=len(passed),passed=passed,real_source_files_deleted=0,real_execution_markers_created=0,synthetic_apply_only_all_destructive_OS_calls_mocked=True)
(OUT/'gate-tests.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
