"""Storage-only review of the frozen326 files; no finance execution or DB startup."""
import ast,collections,datetime,gzip,json,os,pathlib,re,shlex,stat,subprocess,time
from typing import Any
if (pathlib.Path(__file__).parent/'review-final.json').exists():
 raise SystemExit('SEALED_PROPOSAL_READONLY: use active-lot gate; do not rerun collection')
R=pathlib.Path('/root/mgs-agent');A=R/'apps/finance-system';O=pathlib.Path(__file__).parent;P=pathlib.Path('/root/.hermes/secure-backups/storage-finance-archives-1572257170626580601');P.mkdir(mode=0o700,exist_ok=True)
OLD=pathlib.Path('/root/.hermes/secure-backups/storage-reaudit-1571983565292441731/finance-archive-hashes.jsonl')
def save(path,obj):
 assert not path.exists(),f'Immutable observation exists: {path}'
 path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n');path.chmod(0o600)
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def meta(p):
 s=os.lstat(p);assert stat.S_ISREG(s.st_mode) and not pathlib.Path(p).is_symlink()
 return dict(dev=s.st_dev,ino=s.st_ino,size=s.st_size,blocks=s.st_blocks,nlink=s.st_nlink,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)
def role(p):
 if p.suffix=='.sql':return 'schema_migration_or_historical_SQL_preserve_for_consumer_review'
 if p.suffix=='.dump':return 'database_rollback_dump_preserve_pending_individual_recovery'
 if p.name.startswith('verified-db-backup-')and p.suffix=='.tar':return 'generated_API_restore_test_archive_preserve_pending_review'
 if p.name.startswith('node-')or p.name.endswith('.tgz'):return 'historical_distribution_archive_preserve_pending_review'
 if 'canary'in p.name:return 'disaster_recovery_canary_archive_preserve_pending_review'
 return 'historical_code_or_release_archive_preserve_pending_review'
start=time.monotonic();old=[json.loads(x)for x in OLD.read_text().splitlines()];assert len(old)==len({x['path']for x in old})==326
before={x['path']:meta(x['path'])for x in old};hashes={};paths=sorted(before)
for offset in range(0,len(paths),40):
 proc=subprocess.run(['sha256sum','--zero','--',*paths[offset:offset+40]],capture_output=True,check=True)
 for line in proc.stdout.split(b'\0'):
  if line:hashes[os.fsdecode(line[66:])]=line[:64].decode()
assert len(hashes)==326
rows=[]
for x in old:
 p=x['path'];m=meta(p);assert m==before[p],'Concurrent archive mutation';assert hashes[p]==x['sha256'],'Historical content drift; preserve'
 rows.append(dict(path=p,role=role(pathlib.Path(p)),metadata=m,sha256=hashes[p],allocated_bytes=m['blocks']*512,disposal='preserve_pending_role_specific_consumer_and_recovery_proof'))
with gzip.open(P/'reviewed326.json.gz','wt',compresslevel=6)as f:json.dump(rows,f,separators=(',',':'))
roles=collections.defaultdict(lambda:dict(files=0,allocated_bytes=0))
for row in rows:roles[row['role']]['files']+=1;roles[row['role']]['allocated_bytes']+=row['allocated_bytes']
save(O/'role-summary.json',dict(reviewed_files=326,hashes_match_prior_326=True,allocated_bytes=sum(r['allocated_bytes']for r in rows),roles=dict(roles),classification_is_not_disposal=True,private_ledger=str(P/'reviewed326.json.gz'),private_ledger_sha256=sha(P/'reviewed326.json.gz')))
# Only read run receipts; no financial rows/amounts emitted or modified.
base=A/'private/gam-email-runs';all_local=sorted(base.glob('*/mgs_finance-before.dump'));new=[p for p in all_local if str(p)not in before];assert len(new)==1 and new[0].parent.name=='20261117T080318-0500'
selected_names=['20261113T080319-0500','20261114T080318-0500','20261115T080318-0500','20261116T080318-0500'];latest=new[0];assert latest.parent.name>max(selected_names)
lineage=[]
for p in [base/n/'mgs_finance-before.dump'for n in selected_names]+[latest]:
 d=json.loads((p.parent/'result.json').read_text());plan=json.loads((p.parent/'plan.json').read_text());assert d['pass']is True and d['status']=='applied'and not d['blockers']and plan['partial']is False and d['verify']['pass']is True and d['verify']['cutoff']==d['date']
 b=d['backup'];remote=b['remote_root']+'/mgs_finance-before.dump';local=b['files']['local_copy'];assert b['verified']is True and local['path']==str(p)and local['sha256']==b['files'][remote]['sha256']and local['bytes']==p.stat().st_size
 digest=sha(p);assert digest==local['sha256'];lineage.append(dict(path=str(p),metadata=meta(p),sha256=digest,remote_path=remote,date=d['date'],source_bundle_sha256=d['source_bundle_sha256'],result_path=str(p.parent/'result.json'),result_sha256=sha(p.parent/'result.json'),plan_path=str(p.parent/'plan.json'),plan_sha256=sha(p.parent/'plan.json'),complete_verified_import=True,retained_newest=p==latest))
save(O/'dump-lineage.json',lineage)
# Reuse only inspected read-only helper definitions, never import/execute application entrypoints.
gate=R/'data/storage-local-tests-1571996311308214363/target-consumer-census-v2/gate.py';tree=ast.parse(gate.read_text());needed={'need','canon','sha','health','runtime_refs','full_code_inventory'};ns:dict[str,Any]={'ROOT':R}
nodes:list[ast.stmt]=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))or isinstance(n,ast.FunctionDef)and n.name in needed or isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in {'SERVICES','CODE'}for t in n.targets)];exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(gate),'exec'),ns)
targets=[r['path']for r in lineage if not r['retained_newest']];assert len(targets)==4;assert not ns['runtime_refs'](targets);health=ns['health']();inventory=ns['full_code_inventory']();hits=[];family=[]
for p in inventory:
 data=pathlib.Path(p).read_bytes()
 for target in targets:
  run=pathlib.Path(target).parent.name;needles=[target.encode(),str(pathlib.Path(target).relative_to(A)).encode(),run.encode()]
  if any(n in data for n in needles):hits.append(dict(source=p,target=target,source_sha256=sha(p)))
 if p.startswith(str(A)+'/')and b'mgs_finance-before.dump'in data:family.append(dict(source=p,sha256=sha(p)))
save(O/'code-consumer-census.json',dict(source_count=len(inventory),exact_target_or_run_hits=hits,family_sources=family,current_process_hits=[],health=health,source_scope='Inherited inspected code/config/job inventory; code and scheduler references, not binary DB pages or financial payloads.'))
# The canonical transport reads only exact remote files. Extract native functions unchanged.
helper=A/'deploy/runcloud_ops.py';ht=ast.parse(helper.read_text());hn:list[ast.stmt]=[n for n in ht.body if isinstance(n,(ast.Import,ast.ImportFrom))or isinstance(n,ast.FunctionDef)and n.name in {'op','secret'}or isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='VAULT'for t in n.targets)];hns:dict[str,Any]={};exec(compile(ast.fix_missing_locations(ast.Module(body=hn,type_ignores=[])),str(helper),'exec'),hns)
producer=A/'finance_gam_revenue_sync.py';pt=ast.parse(producer.read_text());sshnode=next(n for n in pt.body if isinstance(n,ast.FunctionDef)and n.name=='ssh');transport:dict[str,Any]={'os':os,'subprocess':subprocess,'runcloud_secret':hns['secret'],'_RUN_CLOUD_PASSWORD':None};exec(compile(ast.fix_missing_locations(ast.Module(body=[sshnode],type_ignores=[])),str(producer),'exec'),transport)
remote_observations=[]
for row in lineage:
 rp=row['remote_path'];assert re.fullmatch(r'/home/zeus/mgs-finance-backups/gam-email/\d{4}-\d{2}-\d{2}-[0-9a-f]{12}-complete-[0-9a-f]{12}/mgs_finance-before\.dump',rp)
 q=shlex.quote(rp);command='sha256sum -- '+q+' && stat -c %s -- '+q+' && env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/pg_restore --list '+q+' >/dev/null && printf CATALOGUE_OK'
 out=transport['ssh'](command,timeout=180).splitlines();assert len(out)==3 and out[0].split()[0]==row['sha256']and int(out[1])==row['metadata']['size']and out[2]=='CATALOGUE_OK'
 remote_observations.append(dict(local_path=row['path'],remote_path=rp,sha256=row['sha256'],size=row['metadata']['size'],catalogue_rc=0,retained_newest=row['retained_newest'],catalogue_only_not_materialized_restore=True,checked_at=datetime.datetime.now().astimezone().isoformat()))
save(O/'remote-recovery-readback.json',remote_observations)
# Preserve the three partial-run local dumps and newest local fallback.
preserved=[dict(path=str(p),metadata=meta(p),sha256=sha(p),reason='newest_complete_local_fallback'if p==latest else'prior_partial_receipt_or_recovery_ambiguity_not_reopened_by_storage_review')for p in all_local if str(p)not in targets];assert len(preserved)==4
assert not hits,'Unclassified target/run executable references: preserve and inspect'
assert ns['health']()==health and not ns['runtime_refs'](targets)
for p,m in before.items():assert meta(p)==m
save(O/'candidate-four-local-copies.json',dict(status='remote_copy_and_local_preservation_proven_gate_not_yet_frozen',targets=[r for r in lineage if not r['retained_newest']],retained_local=preserved,all_original326_metadata_unchanged=True,all_original326_hashes_verified=True,newly_observed_file_excluded_from_disposal=str(latest),new_file_retained_SHA256_verified=True,source_files_deleted=0,DB_started_or_SQL=False,remote_readonly=True,new_payload_copies=False,elapsed_seconds=round(time.monotonic()-start,2)))
print(json.dumps(dict(status='PASS',files326_verified=len(rows),roles=dict(roles),proven_remote_counterparts=len(remote_observations),candidate_files=4,retained_local_files=len(preserved),new_files_outside_original326_preserved=1,candidate_allocated_bytes=sum(x['metadata']['blocks']*512 for x in lineage if not x['retained_newest']),code_sources=len(inventory),exact_code_hits=len(hits),source_files_deleted=0,elapsed_seconds=round(time.monotonic()-start,2))))
