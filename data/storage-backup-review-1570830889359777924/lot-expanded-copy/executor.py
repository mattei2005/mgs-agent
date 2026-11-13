#!/usr/bin/env python3
"""Frozen expanded-backup retirement. Read-only unless exact approval exists."""
import argparse,copy,hashlib,json,os,shutil,stat,subprocess,time
from pathlib import Path
H=Path(__file__).resolve().parent
TARGET=Path('/root/.hermes/secure-backups/hermes-update/20261103-phase4-1567354570823172209/control-plane')
SERVICES=['zeus-gateway.service','ares-gateway.service','atena-gateway.service']
def require(v,why):
 if not v:raise RuntimeError(why)
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def fingerprint(root):
 root=Path(root);require(root==TARGET and root.is_dir() and not root.is_symlink() and not os.path.ismount(root),'EXACT_TREE_SCOPE');dev=root.lstat().st_dev;rows=[];stack=[root];files=dirs=links=0
 while stack:
  p=stack.pop();s=p.lstat();require(s.st_dev==dev and not os.path.ismount(p),'MOUNT_CROSSING');kind='directory' if stat.S_ISDIR(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode) else 'symlink' if stat.S_ISLNK(s.st_mode) else 'forbidden';require(kind!='forbidden','SPECIAL_FILE')
  rows.append([str(p.relative_to(root)) or '.',kind,s.st_mode,s.st_dev,s.st_ino,s.st_size,s.st_blocks,s.st_mtime_ns,s.st_nlink,os.readlink(p) if kind=='symlink' else None])
  if kind=='directory':
   dirs+=1
   with os.scandir(p) as entries:stack.extend(Path(x.path) for x in entries)
  elif kind=='file':files+=1
  else:links+=1
 rows.sort(key=lambda r:r[0]);raw=json.dumps(rows,sort_keys=True,separators=(',',':')).encode();return {'sha256':hashlib.sha256(raw).hexdigest(),'files':files,'directories':dirs,'symlinks':links,'entries':len(rows),'allocated_bytes':sum(r[6]*512 for r in rows),'root_inode':root.lstat().st_ino,'device':dev}
def health():
 r={x:subprocess.check_output(['systemctl','show',x,'-p','MainPID','-p','ActiveState'],text=True).strip() for x in SERVICES};require(all('ActiveState=active' in v and 'MainPID=0' not in v for v in r.values()),'SERVICE_HEALTH');return r
def process_refs():
 excluded=set();pid=os.getpid()
 while pid>1 and pid not in excluded:
  excluded.add(pid)
  try:pid=int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[1])
  except OSError:break
 hits=[];target=str(TARGET)
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name) in excluded:continue
  try:vals=(p/'cmdline').read_bytes().decode(errors='replace').split('\0')
  except OSError:continue
  for n in ['cwd','exe']:
   try:vals.append(os.readlink(p/n))
   except OSError:pass
  try:
   for fd in (p/'fd').iterdir():
    try:vals.append(os.readlink(fd))
    except OSError:pass
  except OSError:pass
  if any(v==target or v.startswith(target+'/') for v in vals):hits.append(p.name)
 return hits
def validate(p):
 require(p['status']=='frozen_waiting_exact_critical_confirmation' and p['request_message_id']=='1570830889359777924','PLAN_STATUS');require(p['target']==str(TARGET) and p['action']=='delete_tree','PLAN_SCOPE');require(sha(__file__)==p['executor_sha256'],'EXECUTOR_DRIFT');require(fingerprint(TARGET)==p['fingerprint'],'TREE_METADATA_DRIFT')
 for r in p['retained_files']:
  q=Path(r['path']);require(not q.is_relative_to(TARGET) and q.is_file() and sha(q)==r['sha256'],'RETAINED_RECOVERY_CHANGED')
 require(os.path.realpath('/root/.local/bin/hermes')==p['protected_launcher'],'LAUNCHER_DRIFT');require(not process_refs(),'ACTIVE_TARGET_REFERENCE');return health()
def approval(a,m,e):require(a.get('author_id')=='344196393512075265' and a.get('native_message_readback_verified') is True and a.get('manifest_sha256')==m and a.get('executor_sha256')==e and a.get('confirmation_message_id') not in [None,'','1570830889359777924'],'POST_MANIFEST_OWNER_CONFIRMATION')
def event(name,data):
 with Path('/root/mgs-agent/logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'ts':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'event':name,'actor':'zeus','request_message_id':'1570830889359777924',**data})+'\n');f.flush();os.fsync(f.fileno())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--self-test',action='store_true');a=ap.parse_args();mf=H/'manifest.json';mh=(H/'manifest.sha256').read_text().split()[0];require(sha(mf)==mh,'MANIFEST_HASH');p=json.loads(mf.read_text());before=validate(p)
 if a.self_test:
  passed=[]
  for name in ['scope','metadata','count']:
   q=copy.deepcopy(p)
   if name=='scope':q['target']='/root/NOT_AUTHORIZED'
   elif name=='metadata':q['fingerprint']['sha256']='INVALID_TEST_DIGEST'
   else:q['fingerprint']['files']+=1
   try:validate(q)
   except RuntimeError:passed.append(name)
  try:approval({},mh,p['executor_sha256'])
  except RuntimeError:passed.append('missing_approval')
  require(len(passed)==4,'NEGATIVE_TEST');print(json.dumps({'preflight':'PASS','negative_tests':passed,'deletions':0}));return
 if not a.apply:print(json.dumps({'preflight':'PASS','target':str(TARGET),'manifest_sha256':mh,'files':p['fingerprint']['files'],'deletions':0}));return
 apv=json.loads((H/'approval.json').read_text());approval(apv,mh,p['executor_sha256']);require(not (H/'filesystem-result.json').exists(),'ALREADY_EXECUTED_RECONCILE')
 g=json.loads((H/'fresh-external-preflight.json').read_text());require(g.get('manifest_sha256')==mh and g.get('retained_archives_and_snapshots_validated') is True and g.get('live_profile_and_browser_preservation_baseline') is True and g.get('executable_scheduler_and_inbound_reference_scan_pass') is True and g.get('git_target_tracking_checked') is True and time.time()-g.get('checked_at_epoch',0)<300,'FRESH_EXTERNAL_GATES')
 before=validate(p);v=os.statvfs('/');free=v.f_bavail*v.f_frsize;event('expanded_backup_cleanup_exact_start',{'manifest_sha256':mh,'confirmation_message_id':apv['confirmation_message_id'],'target':str(TARGET)})
 try:
  require(TARGET.lstat().st_ino==p['fingerprint']['root_inode'] and not TARGET.is_symlink(),'FINAL_IDENTITY');shutil.rmtree(TARGET);require(not TARGET.exists(),'TARGET_REMAINS');require(health()==before,'GATEWAY_PID_DRIFT')
  for r in p['retained_files']:require(sha(r['path'])==r['sha256'],'RETAINED_RECOVERY_POST')
 except BaseException as e:event('expanded_backup_cleanup_partial',{'manifest_sha256':mh,'root_still_exists':TARGET.exists(),'error':str(e)});raise
 v=os.statvfs('/');r={'status':'filesystem_validated_external_postchecks_pending','manifest_sha256':mh,'target_absent':True,'observed_free_delta':v.f_bavail*v.f_frsize-free,'gateway_pids_unchanged':True};(H/'filesystem-result.json').write_text(json.dumps(r,indent=2));event('expanded_backup_cleanup_filesystem_finished',r);print(json.dumps(r))
if __name__=='__main__':main()
