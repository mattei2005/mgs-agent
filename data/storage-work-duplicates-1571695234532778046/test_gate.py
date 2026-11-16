"""Read-only regression tests; requires the twelve proposed originals present."""
import pathlib,sys,importlib.util,json,copy,os
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('frozen_work_disposal_gate',OUT/'retire.py');assert spec and spec.loader
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
m=json.load(open(OUT/'retirement-manifest.json'));assert all(os.path.lexists(x['source']['path']) for x in m['files'])
tests=[]
def blocked(name,fn):
 try:fn()
 except AssertionError:tests.append(dict(name=name,status='PASS',expected_block=True))
 else:raise RuntimeError('Unexpected acceptance: '+name)
a=copy.deepcopy(m);a['files'][0]['source']['path']=str(g.rec.OLD/'principal.json');blocked('outside_exact_target_set',lambda:g.rec.scoped(a))
a=copy.deepcopy(m);a['files'][0]=a['files'][1];blocked('duplicate_target',lambda:g.rec.scoped(a))
a=copy.deepcopy(m);a['files'][0]['retained']['path']=a['files'][0]['source']['path'];blocked('retained_input_equals_deleted_target',lambda:g.rec.scoped(a))
a=copy.deepcopy(m);a['protected_hashes'][next(iter(a['protected_hashes']))]='0'*64;blocked('protected_dependency_drift',lambda:g.verify(a))
a=copy.deepcopy(m);a['files'][0]['retained']['size']+=1;blocked('retained_identity_drift',lambda:g.verify(a))
a=copy.deepcopy(m);a['files'][0]['source']['mtime_ns']+=1;blocked('original_identity_drift',lambda:g.verify(a))
fixture=dict(owner_id=g.OWNER,thread_id=g.THREAD,native_readback_verified=False,scope_expansion_authorized=False)
assert g.envelope('fixture_start',fixture)['thread_id']==g.THREAD and g.envelope('fixture_completion',fixture)['owner_id']==g.OWNER
blocked('audit_conflicting_thread',lambda:g.envelope('fixture',dict(fixture,thread_id='wrong')))
blocked('no_native_approval',lambda:g.approve(fixture))
assert not any((OUT/n).exists() for n in ['approval.json','retirement-start.json','retirement-journal.jsonl','retirement-filesystem-result.json'])
print(json.dumps(dict(status='PASS',negative_tests=len(tests),audit_start_completion_shape='PASS',sources_intact=True,execution_not_invoked=True,tests=tests)))
