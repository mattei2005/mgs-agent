#!/usr/bin/env python3
"""Exact retirement of isolated generated finance tests; read-only by default."""
import argparse,collections,fcntl,hashlib,json,os,re,shutil,stat,subprocess,time
from pathlib import Path
ROOT=Path('/root/mgs-agent');BASE=ROOT/'apps/finance-system/private'
HOME=ROOT/'data/storage-reorganization-1570447435074109502/generated-tests-1570473727043436596'
UUID=r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
CLUSTER=re.compile(r'(?:test-pg|catalog-test|ui-test)-'+UUID)
ARCHIVE=re.compile(r'verified-db-backup-'+UUID+r'\.tar')
SERVICES=('zeus-gateway','atena-gateway','ares-gateway')
def require(v,why):
 if not v:raise RuntimeError(why)
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def health():
 values={s:subprocess.check_output(['systemctl','show',s,'-p','MainPID','-p','ActiveState'],text=True).strip() for s in SERVICES}
 require(all('ActiveState=active' in x and 'MainPID=0' not in x for x in values.values()),'GATEWAY_HEALTH')
 return values
def fingerprint(path):
 path=Path(path);dev=BASE.stat().st_dev;entries=[];inodes={};files=dirs=0;stack=[path]
 while stack:
  p=stack.pop();s=p.lstat();require(s.st_dev==dev and not stat.S_ISLNK(s.st_mode),'MOUNT_OR_SYMLINK')
  require(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode),'SPECIAL_FILE')
  entries.append([str(p.relative_to(path)) or '.',s.st_mode,s.st_dev,s.st_ino,s.st_size,s.st_blocks,s.st_mtime_ns,s.st_nlink])
  if stat.S_ISDIR(s.st_mode):
   dirs+=1
   with os.scandir(p) as it:stack.extend(Path(e.path) for e in it)
  else:
   files+=1;require(s.st_nlink==1,'SHARED_FILE_HARDLINK');inodes[(s.st_dev,s.st_ino)]=s.st_blocks*512
 entries.sort(key=lambda x:x[0]);allocated=sum(v[5]*512 for v in entries if stat.S_ISDIR(v[1]))+sum(inodes.values())
 return {'fingerprint_sha256':hashlib.sha256(canon(entries)).hexdigest(),'files':files,'dirs':dirs,'allocated_bytes':allocated,'inode':path.lstat().st_ino,'device':dev}
def references(paths):
 hits=[];excluded=set();pid=os.getpid()
 while pid>1 and pid not in excluded:
  excluded.add(pid)
  try:pid=int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[1])
  except OSError:break
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit() or int(proc.name) in excluded:continue
  vals=[]
  try:vals+=(proc/'cmdline').read_bytes().decode(errors='replace').split('\0')
  except OSError:continue
  for rel in ['cwd','exe']:
   try:vals.append(os.readlink(proc/rel))
   except OSError:pass
  try:
   for fd in (proc/'fd').iterdir():
    try:vals.append(os.readlink(fd))
    except OSError:pass
  except OSError:pass
  for target in paths:
   if any(v==target or v.startswith(target+'/') for v in vals):hits.append({'pid':proc.name,'path':target})
 return hits

def executable_references(paths):
 needles={Path(p).name for p in paths};hits=[]
 scan=[ROOT/'scripts',ROOT/'apps/finance-system/deploy',ROOT/'apps/finance-system/tests',Path('/etc/systemd/system'),Path('/etc/cron.d')]
 files=[p for p in (ROOT/'apps/finance-system').iterdir() if p.is_file() and p.suffix in ['.py','.mjs','.js','.json']]
 for name in ['zeus','atena','ares']:scan.append(Path('/root/.hermes/profiles')/name/'scripts')
 for base in scan:
  if not base.exists():continue
  for dp,dn,fn in os.walk(base):
   dn[:]=[x for x in dn if x not in ['private','.git','node_modules','__pycache__','deprecated']]
   files.extend(Path(dp)/n for n in fn)
 for p in files:
  if not p.is_file() or p.is_symlink() or p.stat().st_size>2*1048576:continue
  try:text=p.read_text()
  except (UnicodeError,OSError):continue
  for needle in needles:
   if needle in text:hits.append({'consumer':str(p),'target_basename':needle})
 cron=subprocess.run(['crontab','-l'],capture_output=True,text=True)
 for needle in needles:
  if needle in cron.stdout:hits.append({'consumer':'root_crontab','target_basename':needle})
 return hits

def validate(plan):
 require(plan['request_message_id']=='1570473727043436596' and plan['status']=='frozen_awaiting_critical_test_state_retirement','PLAN_SCOPE')
 targets=plan['targets'];require(len(targets)==81 and len({r['path'] for r in targets})==81,'EXACT_TARGET_SET')
 require(sum(x['action']=='delete_tree' for x in targets)==60 and sum(x['action']=='delete_file' for x in targets)==21,'EXACT_CLASSES')
 for r in targets:
  p=Path(r['path']);require(p.is_relative_to(BASE) and p.resolve()==p and str(p) not in plan['protected_prior_roots'],'PATH_SCOPE')
  if r['action']=='delete_tree':require(CLUSTER.fullmatch(p.name) and (p/'PG_VERSION').is_file() and (p/'base').is_dir() and (p/'global').is_dir(),'GENERATED_CLUSTER')
  else:require(ARCHIVE.fullmatch(p.name) and p.is_file(),'GENERATED_ARCHIVE')
  require(fingerprint(p)==r['metadata'],'METADATA_DRIFT:'+str(p))
 for row in plan['retained_generator_files']:require(sha(row['path'])==row['sha256'],'GENERATOR_DRIFT')
 for path in plan['protected_prior_roots']:require(Path(path).is_dir(),'RETAINED_TEST_ROOT_MISSING')
 for path in plan['retained_input_paths']:require(Path(path).exists(),'RETAINED_INPUT_MISSING')
 require(os.path.realpath('/root/.local/bin/hermes')==plan['protected_launcher'],'LAUNCHER_DRIFT')
 require(not references([x['path'] for x in targets]),'PROCESS_REFERENCE')
 require(not executable_references([x['path'] for x in targets]),'EXECUTABLE_REFERENCE')
 return health()
def audit(event,data):
 row={'ts':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'event':event,'actor':'zeus','request_message_id':'1570473727043436596',**data}
 with (ROOT/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 raw=(HOME/'manifest.json').read_bytes();plan=json.loads(raw);digest=hashlib.sha256(raw).hexdigest();require(digest==(HOME/'manifest.sha256').read_text().split()[0],'MANIFEST_DIGEST');require(sha(__file__)==plan['executor_sha256'],'EXECUTOR_DRIFT')
 with (HOME/'execution.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);before=validate(plan)
  if not args.apply:
   print(json.dumps({'status':'read_only_preflight_passed','targets':len(plan['targets']),'files':sum(r['metadata']['files'] for r in plan['targets']),'allocated_bytes':sum(r['metadata']['allocated_bytes'] for r in plan['targets']),'manifest_sha256':digest,'deletions':0}));return
  a=json.loads((HOME/'critical-approval.json').read_text());require(a.get('author_id')=='344196393512075265' and a.get('manifest_sha256')==digest and a.get('executor_sha256')==plan['executor_sha256'] and a.get('native_message_readback_verified') is True and a.get('explicit_test_state_retirement') is True and a.get('confirmation_message_id') not in [None,'','1570473727043436596'],'NEW_OWNER_CRITICAL_CONFIRMATION')
  deleted=[];audit('generated_test_retirement_exact_start',{'manifest_sha256':digest,'confirmation_message_id':a['confirmation_message_id'],'targets':len(plan['targets'])})
  try:
   for r in plan['targets']:
    p=Path(r['path']);require(not p.is_symlink() and p.lstat().st_ino==r['metadata']['inode'],'IDENTITY_DRIFT_DURING_APPLY')
    if r['action']=='delete_tree':shutil.rmtree(p)
    else:p.unlink()
    deleted.append(str(p));audit('generated_test_retirement_target_deleted',{'manifest_sha256':digest,'path':str(p)})
   require(all(not Path(r['path']).exists() for r in plan['targets']),'TARGETS_REMAIN');require(health()==before,'GATEWAY_PID_DRIFT')
  except BaseException as exc:
   audit('generated_test_retirement_partial_failure',{'manifest_sha256':digest,'deleted':deleted,'error_type':type(exc).__name__});raise
  audit('generated_test_retirement_exact_finished',{'manifest_sha256':digest,'deleted':deleted,'external_postchecks_pending':True})
  print(json.dumps({'status':'deleted_pending_external_validation','deleted_targets':len(deleted),'manifest_sha256':digest}))
if __name__=='__main__':main()
