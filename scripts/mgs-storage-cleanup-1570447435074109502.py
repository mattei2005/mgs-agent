#!/usr/bin/env python3
"""Exact storage lot. Default read-only; apply requires a separate owner approval."""
import argparse, hashlib, json, os, stat, subprocess, sys, time
from pathlib import Path
ROOT=Path('/root/mgs-agent')
HOME=ROOT/'data/storage-reorganization-1570447435074109502'
PREFIX=ROOT/'apps/finance-system/private/gam-email-runs'
AUDIT=ROOT/'logs/events-audit.jsonl'
REQUEST='1570447435074109502'
SERVICES=('zeus-gateway','ares-gateway','atena-gateway')
def require(ok,code):
 if not ok:raise RuntimeError(code)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def metadata(p):
 p=Path(p);s=p.lstat()
 return {'path':str(p),'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'blocks':s.st_blocks,'mtime_ns':s.st_mtime_ns,'nlink':s.st_nlink,'mode':stat.S_IMODE(s.st_mode)}
def identities():
 return {s:subprocess.check_output(['systemctl','show',s,'-p','MainPID','-p','ActiveState'],text=True).strip() for s in SERVICES}
def process_references(paths):
 targets=set(paths);hits=[];excluded=set();pid=os.getpid()
 while pid>1 and pid not in excluded:
  excluded.add(pid)
  try:pid=int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[1])
  except OSError:break
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name) in excluded:continue
  values=[]
  try:values+= (p/'cmdline').read_bytes().decode(errors='replace').split('\0')
  except OSError:continue
  for rel in ['cwd','exe']:
   try:values.append(os.readlink(p/rel))
   except OSError:pass
  try:
   for fd in (p/'fd').iterdir():
    try:values.append(os.readlink(fd))
    except OSError:pass
  except OSError:pass
  for path in targets:
   if path in values:hits.append({'pid':p.name,'path':path})
 return hits

def code_references(paths):
 needles={str(Path(p).parent):p for p in paths};hits=[]
 roots=[ROOT/'scripts',ROOT/'apps/finance-system/deploy',Path('/etc/systemd/system'),Path('/etc/cron.d')]
 files=list((ROOT/'apps/finance-system').glob('*.py'))
 for profile in ['zeus','ares','atena']:
  roots.append(Path('/root/.hermes/profiles')/profile/'scripts')
 for root in roots:
  if root.exists():
   for dp,dn,fn in os.walk(root):
    dn[:]=[n for n in dn if n not in {'.git','__pycache__','node_modules','private','deprecated'}]
    files.extend(Path(dp)/n for n in fn)
 for p in files:
  if p.is_symlink() or not p.is_file() or p.stat().st_size>2*1024*1024:continue
  try:text=p.read_text()
  except (UnicodeError,OSError):continue
  for needle,target in needles.items():
   if needle in text:hits.append({'file':str(p),'target':target})
 cron=subprocess.run(['crontab','-l'],capture_output=True,text=True)
 for needle,target in needles.items():
  if needle in cron.stdout:hits.append({'file':'root crontab','target':target})
 return hits

def validate(plan):
 require(plan.get('request_message_id')==REQUEST and plan.get('status')=='frozen_awaiting_critical_confirmation','PLAN_SCOPE')
 targets=plan['targets'];require(len(targets)==28 and len({r['path'] for r in targets})==28,'EXACT_28_TARGETS')
 for row in targets:
  p=Path(row['path'])
  require(p.parent.parent==PREFIX and p.name=='mgs_finance-before.dump' and p.resolve()==p and p.is_file() and not p.is_symlink(),'EXACT_ALLOWED_REGULAR_FILE')
  require(metadata(p)==row['metadata'] and p.stat().st_nlink==1,'TARGET_METADATA_DRIFT')
  require(digest(p)==row['sha256'],'TARGET_CONTENT_DRIFT')
 for row in plan['retained_local']:
  require(Path(row['path']).is_file() and digest(row['path'])==row['sha256'],'RETAINED_LOCAL_CONTENT')
 require(all(r.get('verified') and r.get('pg_restore_list_exit')==0 for r in plan['remote_readbacks']),'REMOTE_RECOVERY_RECEIPTS')
 refs=process_references([r['path'] for r in targets]);require(not refs,'PROCESS_REFERENCES:'+json.dumps(refs))
 refs=code_references([r['path'] for r in targets]);require(not refs,'EXECUTABLE_REFERENCES:'+json.dumps(refs))
 require(os.path.realpath('/root/.local/bin/hermes')==plan['protected_launcher'],'ACTIVE_LAUNCHER_DRIFT')
 states=identities();require(all('ActiveState=active' in v and 'MainPID=0' not in v for v in states.values()),'GATEWAY_HEALTH')
 return states

def audit(event,payload):
 row={'ts':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'event':event,'actor':'zeus','request_message_id':REQUEST,**payload}
 with AUDIT.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 manifest=HOME/'finance-duplicate-lot.json';raw=manifest.read_bytes();plan=json.loads(raw)
 expected=(HOME/'finance-duplicate-lot.sha256').read_text().split()[0]
 require(hashlib.sha256(raw).hexdigest()==expected,'MANIFEST_SHA256')
 require(digest(Path(__file__).resolve())==plan['executor_sha256'],'EXECUTOR_DRIFT')
 before=validate(plan)
 if not args.apply:
  print(json.dumps({'status':'read_only_preflight_passed','targets':len(plan['targets']),'reclaim_bytes':sum(r['allocated'] for r in plan['targets']),'manifest_sha256':expected,'deletions':0}));return
 approval=json.loads((HOME/'critical-approval.json').read_text())
 require(approval.get('author_id')=='344196393512075265' and approval.get('manifest_sha256')==expected and approval.get('request_message_id')==REQUEST and approval.get('confirmation_message_id') not in {None,'',REQUEST},'EXPLICIT_NEW_OWNER_CONFIRMATION')
 require(approval.get('executor_sha256')==plan['executor_sha256'],'APPROVED_EXECUTOR')
 require(approval.get('native_message_readback_verified') is True,'NATIVE_CONFIRMATION_READBACK')
 deleted=[];audit('storage_cleanup_exact_start',{'manifest_sha256':expected,'confirmation_message_id':approval['confirmation_message_id'],'targets':28})
 try:
  for row in plan['targets']:
   p=Path(row['path']);require(p.is_file() and not p.is_symlink() and p.lstat().st_ino==row['metadata']['ino'],'IDENTITY_CHANGED_DURING_APPLY')
   p.unlink();deleted.append(str(p))
  require(all(not Path(r['path']).exists() for r in plan['targets']),'TARGETS_NOT_ABSENT')
  require(before==identities(),'GATEWAY_PID_DRIFT')
  require(all(digest(r['path'])==r['sha256'] for r in plan['retained_local']),'RETAINED_CONTENT_POSTCHECK')
 except BaseException as e:
  audit('storage_cleanup_exact_partial_failure',{'manifest_sha256':expected,'deleted':deleted,'remaining':[r['path'] for r in plan['targets'] if r['path'] not in deleted],'error_type':type(e).__name__});raise
 audit('storage_cleanup_exact_finished',{'manifest_sha256':expected,'deleted':deleted,'retained_local':9,'gateway_pids_unchanged':True})
 print(json.dumps({'status':'deleted_validated','deleted':len(deleted),'manifest_sha256':expected,'governance_and_external_postchecks_pending':True}))
if __name__=='__main__':main()
