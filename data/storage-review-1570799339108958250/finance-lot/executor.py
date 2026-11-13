#!/usr/bin/env python3
"""Frozen 27-file finance lot. Read-only unless exact approval is present."""
import argparse,copy,json,os,stat,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
PREFIX=Path('/root/mgs-agent/apps/finance-system/private/gam-email-runs')
SERVICES=['zeus-gateway.service','ares-gateway.service','atena-gateway.service']
def require(ok,reason):
 if not ok:raise RuntimeError(reason)
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def meta(p):
 s=Path(p).lstat();return {'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'blocks':s.st_blocks,'nlink':s.st_nlink,'mtime_ns':s.st_mtime_ns,'mode':s.st_mode}
def services():
 return {x:subprocess.check_output(['systemctl','show',x,'-p','MainPID','-p','ActiveState'],text=True).strip() for x in SERVICES}
def process_hits(paths):
 hits=[];excluded=set();pid=os.getpid()
 while pid>1 and pid not in excluded:
  excluded.add(pid)
  try:pid=int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[1])
  except OSError:break
 for dp in Path('/proc').iterdir():
  if not dp.name.isdigit() or int(dp.name) in excluded:continue
  try:values=(dp/'cmdline').read_bytes().decode(errors='replace').split('\0')
  except OSError:continue
  for rel in ['cwd','exe']:
   try:values.append(os.readlink(dp/rel))
   except OSError:pass
  try:
   for fd in (dp/'fd').iterdir():
    try:values.append(os.readlink(fd))
    except OSError:pass
  except OSError:pass
  for p in paths:
   if any(v==p or v.startswith(p+'/') for v in values):hits.append({'pid':dp.name,'target':p})
 return hits
def validate(p):
 require(p['status']=='frozen_waiting_exact_critical_confirmation','STATUS')
 require(p['request_message_id']=='1570807018380599409','REQUEST')
 rows=p['targets']; require(len(rows)==27 and len({r['path'] for r in rows})==27,'COUNT')
 require(sha(__file__)==p['executor_sha256'],'EXECUTOR_DRIFT')
 for r in rows:
  x=Path(r['path']);require(x.parent.parent==PREFIX and x.name=='mgs_finance-before.dump' and x.resolve()==x and not x.is_symlink() and x.is_file(),'SCOPE')
  require(meta(x)==r['metadata'] and x.stat().st_nlink==1,'METADATA_DRIFT')
  require(sha(x)==r['sha256'],'CONTENT_DRIFT')
 for r in p['retained_local']:require(Path(r['path']).is_file() and sha(r['path'])==r['sha256'],'RETAINED_LOCAL')
 require(os.path.realpath('/root/.local/bin/hermes')==p['protected_launcher'],'LAUNCHER')
 require(not process_hits([r['path'] for r in rows]),'PROCESS_REFERENCE')
 state=services(); require(all('ActiveState=active' in v and 'MainPID=0' not in v for v in state.values()),'SERVICE_HEALTH')
 return state
def approval_check(a,expected,executor):
 require(a.get('author_id')=='344196393512075265' and a.get('native_message_readback_verified') is True and a.get('manifest_sha256')==expected and a.get('executor_sha256')==executor and a.get('confirmation_message_id') not in [None,'','1570807018380599409'],'NEW_EXACT_APPROVAL')
def audit(event,data):
 with Path('/root/mgs-agent/logs/events-audit.jsonl').open('a') as f:
  f.write(json.dumps({'ts':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'event':event,'actor':'zeus','request_message_id':'1570807018380599409',**data})+'\n');f.flush();os.fsync(f.fileno())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--self-test',action='store_true');args=ap.parse_args()
 mf=HERE/'manifest.json';expected=(HERE/'manifest.sha256').read_text().split()[0];require(sha(mf)==expected,'MANIFEST_HASH');p=json.loads(mf.read_text())
 before=validate(p)
 if args.self_test:
  tested=[]
  for kind in ['count','scope','metadata']:
   c=copy.deepcopy(p)
   if kind=='count':c['targets']=c['targets'][:-1]
   elif kind=='scope':c['targets'][0]['path']='/root/NOT_AUTHORIZED'
   else:c['targets'][0]['metadata']['size']+=1
   try:validate(c)
   except RuntimeError:tested.append(kind)
  try:approval_check({},expected,p['executor_sha256'])
  except RuntimeError:tested.append('missing_approval')
  require(len(tested)==4,'SELF_TEST_FAILURE');print(json.dumps({'read_only_preflight':'PASS','negative_tests':tested,'deletions':0}));return
 if not args.apply:print(json.dumps({'read_only_preflight':'PASS','targets':27,'manifest_sha256':expected,'deletions':0}));return
 approval=json.loads((HERE/'approval.json').read_text());approval_check(approval,expected,p['executor_sha256'])
 require((HERE/'fresh-external-preflight.json').is_file(),'EXTERNAL_PRESERVATION_GATE')
 ext=json.loads((HERE/'fresh-external-preflight.json').read_text());require(ext.get('manifest_sha256')==expected and ext.get('remote_recovery_verified') is True and ext.get('finance_preservation_baseline_ready') is True and ext.get('executable_and_scheduler_scan_pass') is True and time.time()-ext.get('checked_at_epoch',0)<300,'FRESH_EXTERNAL_GATES')
 before=validate(p);v=os.statvfs('/');free_before=v.f_bavail*v.f_frsize;deleted=[]
 audit('finance_local_dump_cleanup_start',{'manifest_sha256':expected,'confirmation_message_id':approval['confirmation_message_id'],'targets':27})
 try:
  for r in p['targets']:
   x=Path(r['path']);require(x.is_file() and not x.is_symlink() and x.lstat().st_ino==r['metadata']['ino'],'IDENTITY');x.unlink();deleted.append(str(x))
  require(all(not Path(r['path']).exists() for r in p['targets']),'TARGET_ABSENCE')
  require(before==services(),'SERVICE_PID_DRIFT')
  for r in p['retained_local']:require(sha(r['path'])==r['sha256'],'RETAINED_POST')
 except BaseException as e:
  audit('finance_local_dump_cleanup_partial',{'deleted':deleted,'error':str(e)});raise
 v=os.statvfs('/');result={'status':'filesystem_deleted_validated_external_postchecks_pending','manifest_sha256':expected,'deleted':deleted,'observed_free_delta':v.f_bavail*v.f_frsize-free_before,'gateway_pids_unchanged':True};(HERE/'filesystem-result.json').write_text(json.dumps(result,indent=2));audit('finance_local_dump_cleanup_filesystem_finished',{'manifest_sha256':expected,'deleted_count':len(deleted),'observed_free_delta':result['observed_free_delta']});print(json.dumps({'deleted':len(deleted),'observed_free_delta':result['observed_free_delta'],'external_postchecks_pending':True}))
if __name__=='__main__':main()
