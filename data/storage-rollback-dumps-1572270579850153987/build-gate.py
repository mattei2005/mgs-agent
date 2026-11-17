"""Generate a new self-contained gate for29 proven mirrored historical copies; never mutate the previous lot."""
import ast,gzip,json,pathlib,subprocess
R=pathlib.Path('/root/mgs-agent');O=pathlib.Path(__file__).parent;P=pathlib.Path('/root/.hermes/secure-backups/storage-rollback-dumps-1572270579850153987');old=R/'data/storage-finance-archives-1572257170626580601/gate.py'
assert subprocess.check_output(['sha256sum',str(old)],text=True).split()[0]=='46f77b164decb428a6056410328ada68dab42b790c5b50039c621b040ff8921c';assert not(O/'gate.py').exists()
rows=json.load(gzip.open(P/'selected-lineage.json.gz','rt'));paths=sorted(x['path']for x in rows);assert len(paths)==29
code=old.read_text().replace('1572257170626580601','1572270579850153987').replace('Frozen four-file local-copy gate.','Frozen29-file historical local-copy gate.')
lines=code.splitlines();lines=[('TARGET_PATHS='+repr(set(paths)))if line.startswith('RUNS=')else line for line in lines];code='\n'.join(lines)+'\n'
def replace_function(text,name,body):
 n=next(x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef)and x.name==name);s=text.splitlines(keepends=True);return ''.join(s[:n.lineno-1])+body+'\n'+''.join(s[n.end_lineno:])
shape='''def shape(m):
 need(m['request_message_id']=='1572270579850153987'and m['status']=='frozen_awaiting_exact_critical_confirmation','REQUEST_OR_STATUS')
 targets=m['targets'];expected=TARGET_PATHS
 need(len(targets)==29 and {x['path']for x in targets}==expected,'EXACT_29_PATHS');need(m['file_count']==29 and m['directory_count']==0,'COUNTS')
 need(m['reclaim_bytes']==sum(x['metadata']['blocks']*512 for x in targets),'RECLAIM_SUM')
 need(len({(x['metadata']['dev'],x['metadata']['ino'])for x in targets})==29 and all(x['metadata']['nlink']==1 for x in targets),'HARDLINK_SCOPE')
 need(len(m['retained_local_dumps'])==4 and not({x['path']for x in m['retained_local_dumps']}&expected),'RETAINED_DUMP_SET')
 latest=str(APP/'private/gam-email-runs/20261117T080318-0500/mgs_finance-before.dump');need(any(x['path']==latest for x in m['retained_local_dumps']),'NEWEST_LOCAL_FALLBACK')
 need(len(m['retained_reviewed_files'])==293 and not({x['path']for x in m['retained_reviewed_files']}&expected),'RETAINED_293')
 need(len(m['remote_recovery'])==30 and {x['local_path']for x in m['remote_recovery']}==expected|{latest},'REMOTE_RECOVERY_SCOPE')
 expected_rows={x['path']:x for x in targets+m['retained_local_dumps']}
 for x in m['remote_recovery']:
  need(x['sha256']==expected_rows[x['local_path']]['sha256']and x['size']==expected_rows[x['local_path']]['metadata']['size'],'REMOTE_LOCAL_BINDING')
  remote=pathlib.PurePosixPath(x['remote_path']);need(str(remote).startswith('/home/zeus/mgs-finance-backups/')and '..'not in remote.parts and re.fullmatch(r'[A-Za-z0-9_./-]+\\.dump',str(remote)),'REMOTE_PATH')
 return True
'''
selector='''def select_target(data,p,targets):
 for target in targets:
  t=pathlib.Path(target);ids=re.findall(r'\\d{17,20}',str(t));owner=ids[-1]if ids else None
  if t.as_posix().encode()in data or t.relative_to(APP).as_posix().encode()in data:return True
  if owner and(owner in p or owner.encode()in data)and re.search(re.escape(t.name.encode())+rb'(?![A-Za-z0-9_.-])',data):return True
 return False
'''
census='''def census(targets,allowed=None):
 allowed=allowed or {};index={};full=full_code_inventory();markers=[b'finance-system',b'pglite',b'pg_version',b'mgs_finance-before.dump',b'gam-email-runs',b'pg_restore',b'finance-before.dump']
 for p in full:
  data=pathlib.Path(p).read_bytes();digest=hashlib.sha256(data).hexdigest()
  if select_target(data,p,targets):need(allowed.get(p)==digest,'NEW_OR_CHANGED_TARGET_REFERENCE')
  if p.endswith('/cron/jobs.json'):
   raw=json.loads(data);jobs=raw.get('jobs',[])if isinstance(raw,dict)else raw;jobs=list(jobs.values())if isinstance(jobs,dict)else jobs
   for job in jobs:
    row={k:job[k]for k in ['id','prompt','skills','skill','script','no_agent','monitor_script','monitor_url','context_from','schedule','enabled','model','provider','base_url','workdir','deliver','origin','enabled_toolsets','failure_deliver']if k in job};body=canon(row)
    if any(x in body.lower()for x in markers):need(bool(job.get('id')),'JOB_ID');index[p+'::job::'+job['id']]=hashlib.sha256(body).hexdigest()
  elif p.startswith(str(APP)+'/')or any(x in data.lower()for x in markers):index[p]=digest
 return index
'''
remote='''def remote(m):
 import importlib.util
 for p,h in m['transport_source_hashes'].items():need(sha(p)==h,'TRANSPORT_HELPER_DRIFT')
 need(sha(m['ram_reader_path'])==m['ram_reader_sha256'],'RAM_READER_DRIFT')
 for p,h in m['ram_reader_dependency_hashes'].items():need(sha(p)==h,'RAM_READER_DEPENDENCY_DRIFT')
 spec=importlib.util.spec_from_file_location('frozen_retained_reader',m['ram_reader_path']);need(spec is not None and spec.loader is not None,'RAM_READER_IMPORT');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader);transport,_=reader.bootstrap();checked=[]
 for x in m['remote_recovery']:
  prefix='sudo -n 'if x['remote_path']=='/home/zeus/mgs-finance-backups/month-prune-1556898264878419969/finance-before.dump'else'';q=shlex.quote(x['remote_path'])
  command=prefix+'sha256sum -- '+q+' && '+prefix+'stat -c %s -- '+q+' && '+prefix+'env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/pg_restore --list '+q+' >/dev/null && printf CATALOGUE_OK'
  result=transport(command,timeout=180).decode().splitlines();need(len(result)==3 and result[0].split()[0]==x['sha256']and int(result[1])==x['size']and result[2]=='CATALOGUE_OK','REMOTE_EXACT_CONTENT_OR_CATALOGUE');checked.append(x['remote_path'])
 return len(checked)
'''
for name,body in [('shape',shape),('select_target',selector),('census',census),('remote',remote)]:code=replace_function(code,name,body)
old_loop=" for row in m['retained_reviewed_files']+m['retained_local_dumps']:\n  need(meta(row['path'])==row['metadata']and sha(row['path'])==row['sha256'],'RETAINED_METADATA_OR_PAYLOAD_DRIFT')"
new_loop=" union={}\n for row in m['retained_reviewed_files']+m['retained_local_dumps']:\n  if row['path']in union:need(row['metadata']==union[row['path']]['metadata']and row['sha256']==union[row['path']]['sha256'],'RETAINED_BINDING_CONFLICT')\n  union[row['path']]=row\n need(len(union)==294,'RETAINED_UNION_COUNT')\n for row in union.values():need(meta(row['path'])==row['metadata']and sha(row['path'])==row['sha256'],'RETAINED_METADATA_OR_PAYLOAD_DRIFT')"
assert code.count(old_loop)==1;code=code.replace(old_loop,new_loop)
code=code.replace("census(paths)==expected","census(paths,m['allowed_reference_sources'])==expected")
code=code.replace("targets=4,retained_reviewed=322","targets=29,retained_reviewed=293").replace('source_files_deleted=0 if not post else 4','source_files_deleted=0 if not post else 29').replace('len(deleted)==4','len(deleted)==29').replace("'deleted_count':4","'deleted_count':29").replace('four_local_remote_mirrored_dump','historical_rollback_local_dump').replace('four_paths_removed_and_retained_recovery_validated','29_paths_removed_hash_catalogue_validated_post_RAM_replay_pending')
anchor=" checked=remote(m)\n return dict(status='PASS'";repl=" need(sha(m['ram_pre_proof_path'])==m['ram_pre_proof_sha256'],'RAM_PROOF_INDEX_DRIFT')\n proof=[json.loads(line)for line in pathlib.Path(m['ram_pre_proof_path']).read_text().splitlines()];need(len(proof)==29 and {x['path']for x in proof}==set(paths),'RAM_PROOF_SCOPE');expect={r['path']:r for r in m['targets']}\n need(all(x['actual_recovered_sha256']==expect[x['path']]['sha256']and x['size']==expect[x['path']]['metadata']['size']and x['source_payload_reads']==0 and x['real_file_materialized_in_anonymous_RAM']is True for x in proof),'RAM_PROOF_BINDING')\n checked=remote(m)\n return dict(status='PASS'";assert code.count(anchor)==1;code=code.replace(anchor,repl)
compile(code,str(O/'gate.py'),'exec');(O/'gate.py').write_text(code)
print(json.dumps({'new_gate_generated':True,'targets':29,'previous_frozen_gate_unchanged':subprocess.check_output(['sha256sum',str(old)],text=True).split()[0]=='46f77b164decb428a6056410328ada68dab42b790c5b50039c621b040ff8921c'}))
