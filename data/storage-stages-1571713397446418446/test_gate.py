"""Read-only negative tests for stage scope, providers, consumers and authorization."""
import pathlib,importlib.util,json,copy,sys,subprocess,os
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent
s=importlib.util.spec_from_file_location('stage_gate',OUT/'retire.py');assert s and s.loader;g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
m,rows=g.rec.load();results=[]
def reject(name,fn):
 try:fn()
 except AssertionError:results.append(dict(name=name,status='PASS',expected_block=True))
 else:raise RuntimeError('Unexpected acceptance: '+name)
a=copy.deepcopy(m);a['files']+=1;reject('reduced_or_increased_count',lambda:g.rec.scope(a,rows))
a=copy.deepcopy(m);a['allowed_roots']=['/root/mgs-agent/scripts'];reject('allowed_roots_replaced',lambda:g.rec.scope(a,rows))
b=copy.deepcopy(rows);b[0]['source']['path']='/root/mgs-agent/scripts/engine.py';reject('installed_program_outside_scope',lambda:g.rec.scope(m,b))
b=copy.deepcopy(rows);b[0]=b[1];reject('duplicate_target',lambda:g.rec.scope(m,b))
b=copy.deepcopy(rows);i=next(i for i,x in enumerate(b)if x['retained']['kind']=='file');b[i]['retained']['path']=b[0]['source']['path'];reject('retained_source_is_target',lambda:g.rec.scope(m,b))
b=copy.deepcopy(rows);b[0]['source']['mtime_ns']+=1;reject('source_fingerprint_drift',lambda:g.verify(m,b))
q=next(x['retained']for x in rows if x['retained']['kind']=='file');tip=subprocess.check_output(['git','-C',str(g.ROOT),'rev-parse','origin/main'],text=True).strip();reject('retained_payload_digest_mismatch',lambda:g.rec.provider_bytes(q,'0'*64,tip))
q=copy.deepcopy(next(x['retained']for x in rows if x['retained']['kind']=='git'));q['git_blob_oid']='0'*40;reject('Git_member_binding_drift',lambda:g.rec.git_binding(q['repository'],q['commit'],q['member'],q['git_blob_oid']))
scan=json.load(open(OUT/'consumers.json'));bad=copy.deepcopy(scan);bad['literal_prefix_hits'].append(dict(path='/root/mgs-agent/scripts/unclassified_consumer.py',prefixes=[m['allowed_roots'][0]]));reject('unclassified_consumer',lambda:g.rec.classify(m,bad))
a=copy.deepcopy(m);key=next(k for k,v in a['allowed_reference_evidence'].items()if v['kind']=='fixture_ast');a['allowed_reference_evidence'][key]['ast_sha256']='0'*64;reject('fixture_changed_semantics',lambda:g.rec.classify(a,scan))
fixture=dict(owner_id=g.OWNER,thread_id=g.THREAD,native_readback_verified=False,scope_expansion_authorized=False);assert g.envelope('fixture_start',fixture)['thread_id']==g.THREAD;assert g.envelope('fixture_completion',fixture)['owner_id']==g.OWNER
reject('audit_thread_conflict',lambda:g.envelope('fixture',dict(fixture,thread_id='wrong')));reject('missing_verified_approval',lambda:g.approval(fixture))
assert not any((OUT/name).exists()for name in ['approval.json','retirement-start.json','retirement-journal.jsonl','retirement-filesystem-result.json']);assert all(os.path.lexists(x['source']['path'])for x in rows)
print(json.dumps(dict(status='PASS',negative_tests=len(results),audit_schema_start_completion_positive='PASS',source_files_removed=0,synthetic_fixture_not_authorization=True,tests=results)))
