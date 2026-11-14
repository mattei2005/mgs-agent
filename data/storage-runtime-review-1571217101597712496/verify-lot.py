#!/usr/bin/env python3
"""Read-only exact runtime lot validation. No deletion function exists here."""
import pathlib,json,os,stat,hashlib,subprocess,tarfile,gzip,argparse
TARGETS=['/root/.hermes/hermes-agent-stage-main-7cc3fb8c-mgs','/root/.hermes/secure-backups/hermes-update/20261012-1559192694096404537-preport/clean-target-7cc3fb8c']
def snapshot(root):
 root=pathlib.Path(root);assert root.is_dir() and not root.is_symlink() and not os.path.ismount(root);rows=[];stack=[root];dev=root.stat().st_dev
 while stack:
  p=stack.pop();s=p.lstat();assert s.st_dev==dev,'Mount/device boundary';r={'path':str(p.relative_to(root)),'mode':s.st_mode,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'dev':s.st_dev,'ino':s.st_ino,'nlink':s.st_nlink,'allocated':s.st_blocks*512}
  if stat.S_ISLNK(s.st_mode):r['link_target']=os.readlink(p)
  if stat.S_ISDIR(s.st_mode):stack.extend(p.iterdir())
  rows.append(r)
 rows.sort(key=lambda x:x['path']);data=b''.join(json.dumps(x,sort_keys=True,separators=(',',':')).encode()+b'\n' for x in rows)
 return rows,data,hashlib.sha256(data).hexdigest()
def sha(p):return subprocess.run(['sha256sum',str(p)],capture_output=True,text=True,check=True).stdout.split()[0]
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,default=pathlib.Path(__file__).with_name('deletion-manifest.json'));p.add_argument('--post',action='store_true');p.add_argument('--require-approval',action='store_true');a=p.parse_args();m=json.loads(a.manifest.read_text());assert sorted(t['path'] for t in m['targets'])==sorted(TARGETS) and len(m['targets'])==2,'Scope/count drift'
 if a.require_approval:assert m.get('deletion_approval_message_id'),'No native deletion approval'
 for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines():
  mount=line.split()[4].replace('\\040',' ');assert not any(mount==t or mount.startswith(t+'/') for t in TARGETS),'Mount inside target'
 needle='ares-direct-traffic-supervised-repeat.py';texts=[subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True).stdout]
 for base in ['/etc/cron.d','/etc/systemd/system']:
  for q in pathlib.Path(base).rglob('*'):
   if q.is_file() and q.stat().st_size<1000000 and q.suffix in ['','.service','.timer','.conf']:
    try:texts.append(q.read_text(errors='replace'))
    except OSError:pass
 for profile in ['zeus','ares','atena']:
  q=pathlib.Path('/root/.hermes/profiles',profile,'cron/jobs.json')
  if q.is_file():texts.append(q.read_text())
 assert not any(needle in text for text in texts),'Historical reader now has a scheduled consumer'
 counts={'regular_files':0,'directories':0,'symlinks':0}
 for t in m['targets']:
  if a.post:assert not os.path.lexists(t['path']);continue
  rows,data,digest=snapshot(t['path']);assert digest==t['metadata_fingerprint'],'Source metadata drift'
  for row in rows:
   key='regular_files' if stat.S_ISREG(row['mode']) else 'directories' if stat.S_ISDIR(row['mode']) else 'symlinks' if stat.S_ISLNK(row['mode']) else None;assert key;counts[key]+=1
 if not a.post:assert counts==m['counts'],'Target unit totals drift'
 # Every retained preservation artifact is hash-pinned before use.
 for r in m['retained_files']:assert pathlib.Path(r['path']).is_file() and sha(r['path'])==r['sha256'],'Retained artifact drift'
 cap=json.loads(pathlib.Path(m['code_preservation_manifest']).read_text());expected={r['member']:r for r in cap['entries']};seen=set()
 with tarfile.open(m['code_archive'],'r:gz') as tf:
  for mem in tf:
   seen.add(mem.name)
   if mem.name not in expected:assert mem.name in ['stage-working-tree.patch','stage-refs.json'];continue
   r=expected[mem.name]
   if 'sha256' in r:assert hashlib.sha256(tf.extractfile(mem).read()).hexdigest()==r['sha256']
   else:assert mem.issym() and mem.linkname==r['link_target']
 assert seen==set(expected)|{'stage-working-tree.patch','stage-refs.json'}
 for r in m['git_recovery_bases']:
  done=subprocess.run(['git','-C',r['repository'],'archive','--format=tar',r['commit']],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);assert done.returncode==0,'Retained Git tree/blobs unavailable'
 state=json.load(open(m['historical_reader_state']));assert state['round_complete'] and len(state['items'])==33 and all(r['state']=='PASS_LEAN' for r in state['items'].values()),'Historical reader no longer demonstrably complete'
 assert sha(m['historical_reader_script'])==m['historical_reader_script_sha256'],'Historical reader contract drift'
 anc=set();pid=os.getpid()
 while pid>1 and pid not in anc:
  anc.add(pid)
  try:pid=int(pathlib.Path('/proc',str(pid),'status').read_text().split('PPid:')[1].splitlines()[0].strip())
  except (OSError,ValueError,IndexError):break
 refs=[]
 for proc in pathlib.Path('/proc').iterdir():
  if not proc.name.isdigit() or int(proc.name) in anc:continue
  paths=[]
  try:paths+=proc.joinpath('cmdline').read_bytes().decode(errors='replace').split('\0')
  except OSError:pass
  for leaf in ['cwd','exe']:
   try:paths.append(os.readlink(proc/leaf))
   except OSError:pass
  try:
   for fd in (proc/'fd').iterdir():
    try:paths.append(os.readlink(fd))
    except OSError:pass
  except OSError:pass
  for root in TARGETS:
   if any(p==root or p.startswith(root+'/') for p in paths):refs.append({'pid':int(proc.name),'target':root})
 assert not refs,'Live consumer detected'
 for profile,pid in m['gateway_pids'].items():
  raw=subprocess.run(['systemctl','show',profile+'-gateway.service','-p','MainPID','-p','ActiveState'],capture_output=True,text=True,check=True).stdout;d=dict(l.split('=',1) for l in raw.splitlines());assert d['MainPID']==str(pid) and d['ActiveState']=='active','Gateway drift'
 assert os.path.realpath('/root/.local/bin/hermes')==m['active_launcher'],'Active launcher drift'
 print(json.dumps({'status':'PASS','mode':'post' if a.post else 'preflight','targets':2,'counts':m['counts'],'retained_code_capsule_verified':True,'retained_git_base_archives_readable':True,'live_target_consumers':0,'deletions':0}))
if __name__=='__main__':main()
