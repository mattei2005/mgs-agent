"""Read-only rejection tests; never removes real source files."""
import pathlib,json,copy,importlib.util,subprocess,os,sys
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('npx_tests',OUT/'npx-gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
m,rows=g.load();before=g.tree(g.TARGET);results=[]
def reject(name,fn):
    try:fn()
    except (AssertionError,FileNotFoundError):results.append(dict(name=name,status='PASS',expected_block=True))
    else:raise RuntimeError('Unexpected acceptance '+name)
x=copy.deepcopy(m);x['target']=g.KEEP;reject('retained_root_as_target',lambda:g.scope(x,rows))
x=copy.deepcopy(m);x['files']-=1;reject('count_changed',lambda:g.scope(x,rows))
x=copy.deepcopy(m);x['symlinks']+=1;reject('link_count_changed',lambda:g.scope(x,rows))
x=copy.deepcopy(m);x['directories_including_root']-=1;reject('directory_count_changed',lambda:g.scope(x,rows))
x=copy.deepcopy(m);x['allocated_reclaim_bytes']+=4096;reject('reclaim_changed',lambda:g.scope(x,rows))
r=copy.deepcopy(rows);r[0]['relative']='../escape';reject('relative_path_escape',lambda:g.scope(m,r))
r=copy.deepcopy(rows);i=next(i for i,x in enumerate(r)if x['source']['kind']=='file');r[i]['provider']['path']=str(pathlib.Path(g.TARGET)/r[i]['relative']);reject('original_is_recovery_provider',lambda:g.scope(m,r))
r=copy.deepcopy(rows);r[0]['source']['mtime_ns']+=1;reject('target_fingerprint_changed',lambda:g.verify(m,r))
x=copy.deepcopy(m);key=next(iter(x['protected_helpers']));x['protected_helpers'][key]='0'*64;reject('Security_wrapper_drift',lambda:g.verify(x,rows))
a=dict(owner_id=g.OWNER,thread_id=g.THREAD,native_readback_verified=False,scope_expansion_authorized=False);reject('unverified_approval',lambda:g.approval(a))
assert g.envelope('fixture_start',a)['owner_id']==g.OWNER and g.envelope('fixture_completed',a)['thread_id']==g.THREAD
reject('audit_reserved_field_conflict',lambda:g.envelope('fixture',dict(a,thread_id='wrong')))
r=copy.deepcopy(rows);i=next(i for i,x in enumerate(r)if x['source']['kind']=='file');r[i]['provider']['metadata']['mtime_ns']+=1;reject('retained_provider_drift',lambda:g.recover(m,r))
r=copy.deepcopy(rows);r[i]['sha256']='0'*64;reject('retained_payload_corrupt',lambda:g.recover(m,r))
reject('missing_approval_file_execute',lambda:g.execute(m,rows))
assert before==g.tree(g.TARGET)and not any((OUT/n).exists()for n in ['npx-approval.json','npx-start.json','npx-journal.jsonl','npx-filesystem-result.json'])
result=dict(status='PASS',negative_tests=len(results),tests=results,original_tree_unchanged=True,source_files_removed=0,real_approval_or_execution_markers_created=False)
(OUT/'npx-negative-tests.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
