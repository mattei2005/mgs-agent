"""Deploy only reviewed changed files, with baseline CAS and same-ID backup."""
from pathlib import Path
import json,hashlib,os,fcntl,shutil,ast
from datetime import datetime,timezone
R=Path('/root/mgs-agent');H=R/'data/ares/meta-ads/audit/maintenance/t_e524bad0';S=H/'staged'
pins=json.loads((H/'initial-pins.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
changed=[]
for part in ['scripts','tests','data']:
 for p in (S/part).rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts or (part in ['scripts','tests'] and p.suffix!='.py'):continue
  rel=str(p.relative_to(S))
  if sha(p)!=pins.get(rel):changed.append(rel)
assert len(changed)==23,(len(changed),changed)
assert all(not any(x in rel.lower() for x in ['finance-','router-']) for rel in changed)
backup=H/'foreground-before-install';backup.mkdir(exist_ok=True)
with (H/'foreground-install.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 for rel in changed:
  dst=R/rel;candidate=S/rel
  assert sha(dst) in {pins.get(rel),sha(candidate)},'CAS conflict: '+rel
  if candidate.suffix=='.py':ast.parse(candidate.read_text())
  elif candidate.suffix=='.json':json.loads(candidate.read_text())
 # Source and all foreign account configs remain unchanged by this deployment.
 before=json.loads((R/'data/ares/meta-ads/engine-v3/config.json').read_text())
 after=json.loads((S/'data/ares/meta-ads/engine-v3/config.json').read_text())
 assert {k:v for k,v in before['accounts'].items() if k!='1481815942722118'}=={k:v for k,v in after['accounts'].items() if k!='1481815942722118'}
 for rel in sorted(changed,key=lambda x:(x.startswith('data/'),x.endswith('engine-v3/config.json'),x)):
  dst=R/rel;src=S/rel
  if sha(dst)==sha(src):continue
  saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True)
  if dst.exists() and not saved.exists():shutil.copy2(dst,saved)
  dst.parent.mkdir(parents=True,exist_ok=True);tmp=dst.with_name(dst.name+'.foreground-cross.tmp')
  with tmp.open('wb') as out:out.write(src.read_bytes());out.flush();os.fsync(out.fileno())
  os.chmod(tmp,dst.stat().st_mode & 0o777 if dst.exists() else 0o644)
  assert sha(dst)==pins.get(rel),'CAS changed during install: '+rel
  os.replace(tmp,dst)
  assert sha(dst)==sha(src),'installed hash mismatch: '+rel
 receipt={'at':datetime.now(timezone.utc).isoformat(),'authority_message_id':'1571652369467445359','foreground_authority_message_id':'1571658531411595376','files':{rel:{'before':pins.get(rel),'installed':sha(R/rel)} for rel in changed},'foreign_accounts_preserved':True,'campaign_writes':0}
 (H/'foreground-installed-pins.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'installed_files':len(changed),'all_hashes_verified':True,'foreign_accounts_preserved':True,'campaign_writes':0}))
