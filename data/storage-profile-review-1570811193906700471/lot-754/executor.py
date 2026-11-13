#!/usr/bin/env python3
"""Read-only validation by default. Exact media files only; never directories."""
import argparse,copy,json,os,stat,subprocess,time
from pathlib import Path
H=Path(__file__).resolve().parent
ROOT=Path('/root/.hermes/profiles/ares/artifacts/meta-library')
GROUPS={'POUPLIX_LIBRARY_REF_2026-09-17','POUPLIX_RECHECK_2026-09-19T1906Z'}
SERVICES=['zeus-gateway.service','atena-gateway.service','ares-gateway.service']
def require(v,why):
 if not v:raise RuntimeError(why)
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def metadata(p):
 s=Path(p).lstat();return {'mode':s.st_mode,'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'blocks':s.st_blocks,'mtime_ns':s.st_mtime_ns,'nlink':s.st_nlink}
def health():
 d={n:subprocess.check_output(['systemctl','show',n,'-p','MainPID','-p','ActiveState'],text=True).strip() for n in SERVICES};require(all('ActiveState=active' in x and 'MainPID=0' not in x for x in d.values()),'GATEWAY_HEALTH');return d
def process_references(paths):
 excluded=set();pid=os.getpid()
 while pid>1 and pid not in excluded:
  excluded.add(pid)
  try:pid=int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[1])
  except OSError:break
 hits=[];targets=set(paths)
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name) in excluded:continue
  try:vals=(p/'cmdline').read_bytes().decode(errors='replace').split('\0')
  except OSError:continue
  for rel in ['cwd','exe']:
   try:vals.append(os.readlink(p/rel))
   except OSError:pass
  try:
   for fd in (p/'fd').iterdir():
    try:vals.append(os.readlink(fd))
    except OSError:pass
  except OSError:pass
  for v in vals:
   if v in targets:hits.append({'pid':p.name,'target':v})
 return hits
def validate(p):
 require(p['status']=='frozen_waiting_exact_critical_confirmation' and p['request_message_id']=='1570811193906700471','PLAN_SCOPE')
 require(len(p['targets'])==754 and len({r['path'] for r in p['targets']})==754,'COUNT')
 require(sha(__file__)==p['executor_sha256'],'EXECUTOR_DRIFT')
 for r in p['targets']:
  x=Path(r['path']);require(x.is_relative_to(ROOT) and x.relative_to(ROOT).parts[0] in GROUPS and x.resolve()==x and not x.is_symlink() and x.is_file() and not os.path.ismount(x),'FILE_SCOPE')
  require(metadata(x)==r['metadata'] and x.stat().st_nlink==1,'METADATA_DRIFT')
  require(sha(x)==r['sha256'],'CONTENT_DRIFT')
 for r in p['retained_evidence']:require(Path(r['path']).is_file() and sha(r['path'])==r['sha256'],'RETAINED_EVIDENCE')
 require(os.path.realpath('/root/.local/bin/hermes')==p['protected_launcher'],'LAUNCHER_DRIFT')
 require(not process_references([r['path'] for r in p['targets']]),'LIVE_PROCESS_REFERENCE')
 return health()
def approval(a,m,e):
 require(a.get('author_id')=='344196393512075265' and a.get('native_message_readback_verified') is True and a.get('manifest_sha256')==m and a.get('executor_sha256')==e and a.get('confirmation_message_id') not in [None,'','1570811193906700471'],'NEW_EXACT_OWNER_CONFIRMATION')
def event(name,data):
 with Path('/root/mgs-agent/logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'ts':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'event':name,'actor':'zeus','request_message_id':'1570811193906700471',**data})+'\n');f.flush();os.fsync(f.fileno())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--self-test',action='store_true');a=ap.parse_args();mf=H/'manifest.json';m=(H/'manifest.sha256').read_text().split()[0];require(sha(mf)==m,'MANIFEST_HASH');p=json.loads(mf.read_text());before=validate(p)
 if a.self_test:
  tests=[]
  for name in ['count','scope','metadata']:
   q=copy.deepcopy(p)
   if name=='count':q['targets']=q['targets'][:-1]
   elif name=='scope':q['targets'][0]['path']='/root/NOT_AUTHORIZED'
   else:q['targets'][0]['metadata']['size']+=1
   try:validate(q)
   except RuntimeError:tests.append(name)
  try:approval({},m,p['executor_sha256'])
  except RuntimeError:tests.append('missing_approval')
  require(len(tests)==4,'NEGATIVE_TEST');print(json.dumps({'preflight':'PASS','negative_tests':tests,'deletions':0}));return
 if not a.apply:print(json.dumps({'preflight':'PASS','targets':754,'manifest_sha256':m,'deletions':0}));return
 approval(json.loads((H/'approval.json').read_text()),m,p['executor_sha256'])
 g=json.loads((H/'fresh-external-preflight.json').read_text());require(g.get('manifest_sha256')==m and g.get('native_archive_readback_pass') is True and g.get('historical_evidence_mapping_retained') is True and g.get('profile_and_browser_preservation_baseline') is True and g.get('executable_and_scheduler_scan_pass') is True and time.time()-g.get('checked_at_epoch',0)<300,'FRESH_EXTERNAL_GATES')
 require(not (H/'filesystem-result.json').exists(),'ALREADY_EXECUTED_RECONCILE');before=validate(p);v=os.statvfs('/');free=v.f_bavail*v.f_frsize;deleted=[];event('profile_media_exact_start',{'manifest_sha256':m,'targets':754})
 try:
  for r in p['targets']:
   x=Path(r['path']);require(not x.is_symlink() and x.is_file() and x.lstat().st_ino==r['metadata']['ino'],'IDENTITY');x.unlink();deleted.append(str(x))
  require(all(not Path(r['path']).exists() for r in p['targets']),'ABSENCE');require(before==health(),'GATEWAY_PID_DRIFT')
  for r in p['retained_evidence']:require(sha(r['path'])==r['sha256'],'HISTORY_EVIDENCE_POST')
 except BaseException as e:event('profile_media_partial',{'manifest_sha256':m,'deleted':deleted,'error':str(e)});raise
 v=os.statvfs('/');r={'status':'filesystem_validated_external_postchecks_pending','manifest_sha256':m,'deleted':deleted,'observed_free_delta':v.f_bavail*v.f_frsize-free,'gateway_pids_unchanged':True};(H/'filesystem-result.json').write_text(json.dumps(r,indent=2));event('profile_media_filesystem_finished',{'manifest_sha256':m,'deleted':len(deleted),'observed_free_delta':r['observed_free_delta']});print(json.dumps({'deleted':len(deleted),'observed_free_delta':r['observed_free_delta'],'external_postchecks_pending':True}))
if __name__=='__main__':main()
