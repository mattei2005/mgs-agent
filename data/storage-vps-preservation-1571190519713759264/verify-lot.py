#!/usr/bin/env python3
"""Non-mutating exact-lot verifier; this file never deletes anything."""
import argparse,json,pathlib,os,stat,subprocess,hashlib

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,default=pathlib.Path(__file__).with_name('deletion-manifest.json'));p.add_argument('--post',action='store_true');p.add_argument('--require-approval',action='store_true');a=p.parse_args();m=json.loads(a.manifest.read_text());root=pathlib.Path(m['source_root'])
 assert m['deletion_authorized'] is False or m['approval_message_id'],'Missing native deletion approval'
 if a.require_approval:assert m['deletion_authorized'] and m['approval_message_id'],'No deletion approval exists'
 assert root==pathlib.Path('/root/.hermes/secure-backups/vps-maintenance') and not root.is_symlink()
 assert len(m['targets'])==m['target_count']==36,'Target count drift'
 assert sorted(x['path'] for x in m['targets'])==sorted(str(root/x) for x in m['top_entries']),'Scope drift'
 source_manifest=pathlib.Path(m['source_manifest']);h=subprocess.run(['sha256sum',str(source_manifest)],capture_output=True,text=True,check=True).stdout.split()[0];assert h==m['source_manifest_sha256']
 rows=json.loads(source_manifest.read_text())['files'];expected={r['relative_path']:r for r in rows if r['relative_path']!='.'}
 assert sum(stat.S_ISREG(r['mode']) for r in expected.values())==m['regular_files']==2675
 assert sum(stat.S_ISDIR(r['mode']) for r in expected.values())==m['directories']==352
 assert sum(stat.S_ISLNK(r['mode']) for r in expected.values())==m['symlinks']==16
 for x in m['targets']:
  q=pathlib.Path(x['path']);assert q.parent==root and not q.is_symlink() and not os.path.ismount(q)
 if a.post:
  assert all(not os.path.lexists(t['path']) for t in m['targets']),'Targets remain'
 else:
  assert sorted(os.listdir(root))==sorted(m['top_entries']),'Unexpected root entry or missing target'
  for rel,r in expected.items():
   q=root/rel;s=os.lstat(q)
   assert tuple(getattr(s,k) for k in ['st_mode','st_size','st_mtime_ns','st_ctime_ns','st_dev','st_ino','st_nlink','st_blocks'])==tuple(r[k] for k in ['mode','size','mtime_ns','ctime_ns','dev','ino','nlink'])+(r['allocated']//512,),'Source metadata drift'
   if stat.S_ISLNK(s.st_mode):assert os.readlink(q)==r['link_target']
  paths=[str(root/rel) for rel,r in expected.items() if stat.S_ISREG(r['mode'])]
  result=subprocess.run(['xargs','-0','sha256sum','--zero'],input=b'\0'.join(os.fsencode(v) for v in paths)+b'\0',capture_output=True,check=True).stdout
  for z in result.split(b'\0'):
   if not z:continue
   rel=str(pathlib.Path(os.fsdecode(z[66:])).relative_to(root));assert z[:64].decode()==expected[rel]['sha256'],'Source payload drift'
 # No process may reference one of the exact targets. Exclude only this auditor and its ancestors.
 excluded=set();pid=os.getpid()
 while pid>1 and pid not in excluded:
  excluded.add(pid)
  try:pid=int(pathlib.Path('/proc',str(pid),'status').read_text().split('PPid:')[1].splitlines()[0].strip())
  except (OSError,IndexError,ValueError):break
 refs=[]
 for pid in os.listdir('/proc'):
  if not pid.isdigit() or int(pid) in excluded:continue
  candidates=[]
  try:candidates+=pathlib.Path('/proc',pid,'cmdline').read_bytes().decode(errors='replace').split('\0')
  except OSError:pass
  for leaf in ['cwd','exe']:
   try:candidates.append(os.readlink(f'/proc/{pid}/{leaf}'))
   except OSError:pass
  try:
   for fd in os.listdir(f'/proc/{pid}/fd'):
    try:candidates.append(os.readlink(f'/proc/{pid}/fd/{fd}'))
    except OSError:pass
  except OSError:pass
  for t in m['targets']:
   if any(c==t['path'] or c.startswith(t['path']+'/') for c in candidates):refs.append({'pid':pid,'path':t['path']})
 assert not refs,'Process consumer exists'
 # Historical units must stay disabled/inactive with no trigger; no system configuration is changed.
 for u in m['historical_units']:
  raw=subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','UnitFileState','-p','TriggeredBy'],capture_output=True,text=True,check=True).stdout
  state=dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
  assert state.get('ActiveState')=='inactive' and state.get('UnitFileState')=='disabled' and state.get('TriggeredBy')=='','Historical consumer became active'
 for profile,pid in m['gateway_pids'].items():
  now=subprocess.run(['systemctl','show',profile+'-gateway.service','-p','MainPID','--value'],capture_output=True,text=True,check=True).stdout.strip();assert now==str(pid),'Gateway PID drift'
 launcher=os.path.realpath('/root/.local/bin/hermes');assert launcher==m['launcher'],'Launcher drift'
 r=subprocess.run(['python3',m['recover_tool']],capture_output=True,text=True);assert r.returncode==0,'Retained recovery validation failed'
 print(json.dumps({'status':'PASS','mode':'post' if a.post else 'preflight','targets':36,'files':2675,'directories':352,'symlinks':16,'source_originals_checked':not a.post,'retained_recovery_verified':True,'process_refs':0,'deletions':0}))
if __name__=='__main__':main()
