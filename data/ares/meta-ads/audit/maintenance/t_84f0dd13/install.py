import ast,difflib,hashlib,json,os,sys
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_84f0dd13'
hash=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
target=R/'scripts/ares_campaign_v3/shein_channel_authority.py';before=M/'before/shein_channel_authority.py';candidate=M/'shein_channel_authority.py'
pins=json.loads((M/'candidate-runtime-hashes.json').read_text());assert hash(candidate)==pins[str(target.relative_to(R))]
protected=json.loads((M/'protected-before.json').read_text());drift=[p for p,h in protected.items() if hash(p)!=h];assert not drift,drift
assert hash(target)==hash(before),'CAS helper changed'
for p,h in pins.items():
 if p!=str(target.relative_to(R)):assert hash(R/p)==h,p
nodes=lambda p:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a=nodes(before);b=nodes(candidate);assert [k for k in a if a[k]!=b[k]]==['_get'];assert all(a[k]==b[k] for k in ['verify','effective_permissions'])
for p in Path('/proc').glob('[0-9]*'):
 try:argv=(p/'cmdline').read_bytes().split(b'\0')
 except OSError:continue
 assert not (b'execute' in argv and any(v.endswith(b'ares-eggbev-target-clone.py') for v in argv)),p
(M/'helper.diff').write_text(''.join(difflib.unified_diff(before.read_text().splitlines(True),candidate.read_text().splitlines(True))))
temp=target.with_name(target.name+'.t_84f0dd13');fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL, target.stat().st_mode & 0o777)
with os.fdopen(fd,'wb') as f:f.write(candidate.read_bytes());f.flush();os.fsync(f.fileno())
assert hash(target)==hash(before),'CAS helper changed before replace';os.replace(temp,target)
fd=os.open(target.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
assert hash(target)==hash(candidate)
receipt={'task_id':'t_84f0dd13','execution_owner_task':'t_bdfc754f','target':str(target),'before_sha256':hash(before),'installed_sha256':hash(target),'backup':str(before),'tested_candidate_sha256':hash(candidate),'protected_unchanged':len(protected),'modified_existing_ast':['_get'],'new_functions':sorted(set(b)-set(a)),'permissions_cache_verify_unchanged':True,'engine_meta_drive_calls':0}
(M/'install-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
