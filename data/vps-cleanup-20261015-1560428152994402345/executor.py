#!/usr/bin/env python3
"""Exact-target verifier/executor. Default mode is read-only verification.
Deletion requires the owner's second confirmation after the frozen hash.
"""
import argparse,collections,hashlib,json,os,pathlib,stat,subprocess,time
HERE=pathlib.Path(__file__).resolve().parent
M=HERE/'manifest.json'
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
def fingerprint(p):
 p=pathlib.Path(p);device=p.stat().st_dev;nodes=[]
 assert not p.is_symlink() and not os.path.ismount(p)
 if p.is_dir():
  for dr,ds,fs in os.walk(p,followlinks=False):
   nodes += [pathlib.Path(dr)]+[pathlib.Path(dr)/f for f in fs]+[pathlib.Path(dr)/f for f in ds if (pathlib.Path(dr)/f).is_symlink()]
 else:nodes=[p]
 h=hashlib.sha256();c=collections.Counter()
 for n in sorted(nodes,key=lambda x:str(x.relative_to(p))):
  s=n.lstat();assert s.st_dev==device
  typ='dir' if stat.S_ISDIR(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode) else 'symlink' if stat.S_ISLNK(s.st_mode) else 'other';assert typ!='other'
  v=[str(n.relative_to(p)),typ,s.st_mode,s.st_uid,s.st_gid,s.st_size,s.st_blocks,s.st_mtime_ns,s.st_dev,s.st_ino,s.st_nlink,os.readlink(n) if typ=='symlink' else '']
  h.update(json.dumps(v,separators=(',',':')).encode()+b'\n');c[typ+'s']+=1;c['logical_bytes']+=s.st_size;c['allocated_bytes']+=s.st_blocks*512
 return h.hexdigest(),dict(c)
def verify(m):
 assert str(pathlib.Path('/root/.local/bin/hermes').resolve())==m['active_launcher'],'runtime drift'
 assert not subprocess.run(['systemctl','--failed','--no-legend','--plain'],capture_output=True,text=True,check=True).stdout.strip(),'failed units'
 for name in ['zeus-gateway','atena-gateway','ares-gateway']:
  assert subprocess.run(['systemctl','is-active',name],capture_output=True,text=True).stdout.strip()=='active'
 for r in m['protected_file_hashes']:assert sha(r['path'])==r['sha256'],'protected file drift: '+r['path']
 for p in m['retained_latest_hermes_recovery']:assert pathlib.Path(p).exists(),'retained recovery missing'
 for r in m['targets']:
  p=pathlib.Path(r['path']);assert p.exists() and not p.is_symlink();assert p.is_dir()==(r['action']=='delete_tree')
  h,c=fingerprint(p);assert h==r['fingerprint_sha256'],'target drift: '+str(p)
  for k,v in c.items():assert r[k]==v,'count drift: '+str(p)
 refs=[];targets=[r['path'] for r in m['targets']]
 for pid in pathlib.Path('/proc').iterdir():
  if not pid.name.isdigit() or int(pid.name)==os.getpid():continue
  try:
   cmd=(pid/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');links=[]
   for q in [pid/'cwd',pid/'exe']:
    try:links.append(os.readlink(q))
    except OSError:pass
   try:
    for q in (pid/'fd').iterdir():
     try:links.append(os.readlink(q))
     except OSError:pass
   except OSError:pass
   for t in targets:
    if t in cmd or any(x==t or x.startswith(t+'/') for x in links):refs.append({'pid':pid.name,'path':t})
  except OSError:pass
 assert not refs,refs
 return {'status':'preflight_pass_no_deletion','targets':len(m['targets']),'protected_files':len(m['protected_file_hashes']),'time':time.time(),'process_refs':0}
def main():
 a=argparse.ArgumentParser();a.add_argument('--expected-manifest-sha256',required=True);a.add_argument('--execute',action='store_true');a.add_argument('--confirmation-message-id');args=a.parse_args()
 assert sha(M)==args.expected_manifest_sha256,'manifest checksum mismatch';m=json.loads(M.read_text())
 preflight=verify(m);(HERE/'preflight-result.json').write_text(json.dumps(preflight,indent=2))
 if not args.execute:print(json.dumps(preflight));return
 # Keep a separate explicit admission marker to prevent accidental execution from a generic tool invocation.
 assert args.confirmation_message_id and args.confirmation_message_id.isdigit()
 approval=HERE/'owner-critical-confirmation.json';assert approval.exists(),'owner confirmation receipt required'
 approved=json.loads(approval.read_text());assert approved['message_id']==args.confirmation_message_id and approved['manifest_sha256']==args.expected_manifest_sha256
 assert approved['executor_sha256']==sha(__file__),'executor checksum mismatch'
 assert not (HERE/'deletion-result.json').exists(),'execution already has a result; reconcile, never replay'
 import shutil
 audit=pathlib.Path('/root/mgs-agent/logs/events-audit.jsonl')
 def event(kind,**more):
  with audit.open('a') as f:f.write(json.dumps({'ts':time.time(),'event':kind,'actor':'zeus','thread_id':m['thread_id'],'confirmation_message_id':args.confirmation_message_id,'manifest_sha256':args.expected_manifest_sha256,**more})+'\n')
 fs=os.statvfs('/');before=fs.f_bavail*fs.f_frsize;removed=[]
 event('vps_exact_cleanup_started',target_count=len(m['targets']))
 try:
  for r in m['targets']:
   p=pathlib.Path(r['path']);assert p.exists() and not p.is_symlink() and not os.path.ismount(p)
   if r['action']=='delete_tree':assert p.is_dir();shutil.rmtree(p)
   else:assert p.is_file();p.unlink()
   removed.append(str(p))
   with (HERE/'deletion-journal.jsonl').open('a') as f:f.write(json.dumps({'path':str(p),'removed_at':time.time()})+'\n')
  assert all(not pathlib.Path(r['path']).exists() for r in m['targets'])
  fs=os.statvfs('/');result={'status':'filesystem_removed_pending_full_acceptance','removed':removed,'available_delta_bytes':fs.f_bavail*fs.f_frsize-before,'time':time.time()}
  (HERE/'deletion-result.json').write_text(json.dumps(result,indent=2));event('vps_exact_cleanup_filesystem_completed',removed=len(removed),available_delta_bytes=result['available_delta_bytes'])
 except Exception as e:
  result={'status':'partial_failure','removed':removed,'error':str(e),'time':time.time()};(HERE/'deletion-result.json').write_text(json.dumps(result,indent=2));event('vps_exact_cleanup_partial_failure',removed=len(removed),error=str(e));raise
 print(json.dumps({k:v for k,v in result.items() if k!='removed'}))
if __name__=='__main__':main()
