import ast,difflib,fcntl,hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_53c187db'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
pins=load(M/'candidate-runtime-hashes.json');tests=load(M/'candidate-tests.json')
assert all(x['success'] and not x['skipped'] for x in tests)
assert sum(x['tests'] for x in tests)==637
protected=load(M/'protected-before.json');assert all(sha(p)==s for p,s in protected.items())
before=load(M/'runtime-before.json');assert all(sha(R/p)==s for p,s in before.items())
assert not load(M/'shared-regression.json')['drift']
targets={'scripts/ares-eggbev-target-clone.py':M/'ares-eggbev-target-clone.py','scripts/ares_campaign_v3/target_media_recovery.py':M/'target_media_recovery.py'}
assert all(sha(p)==pins[n] for n,p in targets.items())
for n,s in pins.items():
 if n not in targets:assert sha(R/n)==s,n
runner=R/'scripts/ares-eggbev-target-clone.py';backup=M/'before/ares-eggbev-target-clone.py';assert sha(runner)==sha(backup)
nodes=lambda p:{x.name:ast.dump(x,include_attributes=False) for x in ast.parse(Path(p).read_text()).body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
a=nodes(backup);b=nodes(targets['scripts/ares-eggbev-target-clone.py']);changed=[n for n in a if a[n]!=b[n]]
assert changed==['source_seed_proof','finalize','main'];assert set(a)==set(b)
for p in Path('/proc').glob('[0-9]*'):
 try:argv=(p/'cmdline').read_bytes().split(b'\0')
 except OSError:continue
 assert not (any(x in argv for x in [b'execute',b'prepare',b'recover-media',b'finalize']) and any(x.endswith(b'ares-eggbev-target-clone.py') for x in argv)),str(p)
(M/'runner.diff').write_text(''.join(difflib.unified_diff(backup.read_text().splitlines(True),targets['scripts/ares-eggbev-target-clone.py'].read_text().splitlines(True))))
g=load(M/'media-grant.json');home=Path(g['request_path']).parent
with (home/'target-clone.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 # Install unused new module first, then expose CLI; no runtime invocation.
 for n in reversed(list(targets)):
  candidate=targets[n];p=R/n
  if n.endswith('target_media_recovery.py'):
   assert not p.exists() or sha(p)==pins[n],'new module collision'
   if p.exists():continue
  else:assert sha(p)==sha(backup),'runner pre-replace CAS'
  temp=p.with_name(p.name+'.t_53c187db')
  fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o755 if n.endswith('ares-eggbev-target-clone.py') else 0o644)
  with os.fdopen(fd,'wb') as f:f.write(candidate.read_bytes());f.flush();os.fsync(f.fileno())
  os.replace(temp,p);fd=os.open(p.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
  assert sha(p)==pins[n]
receipt={'task_id':'t_53c187db','installed_at':datetime.now(timezone.utc).isoformat(),'execution_owner_task':'t_bdfc754f','request_id':g['request_id'],'installed':{str(R/n):sha(R/n) for n in targets},'backup':str(backup),'backup_sha256':sha(backup),'existing_ast_modified':changed,'shared_runtime_unchanged':len(before)-1,'protected_unchanged':len(protected),'new_module_first':True,'engine_meta_drive_calls':0,'production_recovery_finalization_executed':False}
(M/'install-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
