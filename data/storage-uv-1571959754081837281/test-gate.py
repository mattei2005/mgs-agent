"""Read-only native-prune gate negatives; no real deletion or prune call."""
import pathlib,json,copy,importlib.util,sys,os
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('uv_gate_tests',OUT/'prune-gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
m,rows=g.load();tests=[]
def reject(name,fn):
    try:fn()
    except (AssertionError,FileNotFoundError):tests.append(dict(name=name,status='PASS',expected_block=True))
    else:raise RuntimeError('Unexpected acceptance '+name)
for name,key,value in [('reduced_scope','top_level_targets',192),('target_count_changed','expected_orphan_archives',189),('whole_cache_as_target','cache_root','/root/.cache'),('claim_exact_historical_restore','exact_old_environment_restore_proven',True),('remove_retirement_disclosure','historical_cached_state_retirement',False)]:
    x=copy.deepcopy(m);x[key]=value;reject(name,lambda x=x:g.scope(x,rows))
x=copy.deepcopy(m);x['targets']=x['targets'][:-1];reject('reduced_path_list',lambda:g.scope(x,rows))
x=copy.deepcopy(m);x['targets'][0]='/root/.hermes';reject('profile_root_outside_cache',lambda:g.scope(x,rows))
x=copy.deepcopy(m);x['native_argv'].append('--force');reject('force_flag_forbidden',lambda:g.scope(x,rows))
x=copy.deepcopy(m);x['native_argv'].append('--ci');reject('ci_scope_expansion_forbidden',lambda:g.scope(x,rows))
x=copy.deepcopy(m);x['target_node_counts']['file']+=1;reject('descendant_file_count_changed',lambda:g.scope(x,rows))
x=copy.deepcopy(m);x['protected_helpers'][g.UV]='0'*64;reject('native_binary_drift',lambda:g.verify(x,rows,check_consumers=False,check_payload=False))
a=dict(owner_id=g.OWNER,thread_id=g.THREAD,native_readback_verified=False,scope_expansion_authorized=False);reject('missing_native_confirmation',lambda:g.approval(a));assert g.envelope('fixture_start',a)['owner_id']==g.OWNER and g.envelope('fixture_completed',a)['thread_id']==g.THREAD
reject('audit_reserved_field_conflict',lambda:g.envelope('fixture',dict(a,thread_id='wrong')))
reject('missing_approval_file_execute',lambda:g.execute(m,rows))
reject('postcondition_rejects_present_cache_targets',lambda:g.verify(m,rows,post=True,check_consumers=False,check_payload=False))
assert not any((OUT/n).exists()for n in ['prune-approval.json','prune-start.json','prune-native-result.json','prune-post.json'])
assert g.c.snapshot(None)[1]['normalized_plain_sha256']==m['cache_normalized_sha256']
result=dict(status='PASS',negative_tests=len(tests),tests=tests,audit_schema_start_completion_positive=True,cache_fingerprint_unchanged=True,actual_native_prune_calls=0,source_files_deleted=0)
(OUT/'negative-tests.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='tests'}))
