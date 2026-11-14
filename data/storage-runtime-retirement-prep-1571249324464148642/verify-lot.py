"""Exact lot validator. Never runs Git in a deletion target or mutates a source."""
import pathlib,os,stat,json,hashlib,subprocess,importlib.util,argparse
OUT=pathlib.Path(__file__).parent
EXPECTED={'/root/.hermes/hermes-agent-port-main-46904a3b-mgs':'delete_tree','/root/.hermes/hermes-agent-port-main-ad2d4822-mgs':'native_git_worktree_remove','/root/.local/bin/hermes-main-ad2d4822-mgs':'delete_symlink','/root/.hermes/hermes-agent-port-main-59004a62-mgs/.git/worktrees':'native_worktree_admin_cleanup'}
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def collect(path,ledger=None):
 root=str(path);dev=os.lstat(root).st_dev;stack=[root];counts={'files':0,'directories':0,'symlinks':0};h=hashlib.sha256();nodes=[]
 while stack:
  p=stack.pop();s=os.lstat(p);assert s.st_dev==dev,'mount boundary';kind='file'if stat.S_ISREG(s.st_mode)else'directory'if stat.S_ISDIR(s.st_mode)else'symlink'if stat.S_ISLNK(s.st_mode)else'other';assert kind!='other'
  r={'path':os.path.relpath(p,root),'kind':kind,'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid,'size':s.st_size,'allocated':s.st_blocks*512,'dev':s.st_dev,'ino':s.st_ino,'nlink':s.st_nlink,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
  if kind=='symlink':r['target']=os.readlink(p)
  b=json.dumps(r,sort_keys=True,separators=(',',':')).encode();h.update(b+b'\n');nodes.append(r)
  counts[{'file':'files','directory':'directories','symlink':'symlinks'}[kind]]+=1
  if kind=='directory':
   with os.scandir(p)as es:children=sorted([e.path for e in es],reverse=True)
   stack.extend(children)
 if ledger:
  import gzip
  with gzip.open(ledger,'wt')as f:
   for r in nodes:f.write(json.dumps(r,separators=(',',':'))+'\n')
 return {'fingerprint':h.hexdigest(),'counts':counts,'root_identity':{k:nodes[0][k]for k in ['dev','ino','mode']},'nodes':nodes}
def process_references(roots):
 ancestors=set();pid=os.getpid()
 while pid>1:
  ancestors.add(pid)
  try:pid=int(pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
  except OSError:break
 hits=[]
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit()or int(p.name)in ancestors:continue
  try:
   cmd=(p/'cmdline').read_bytes();found=[r for r in roots if r.encode()in cmd]
   if found:hits.append({'pid':int(p.name),'source':'cmdline','roots':found})
   for ref in [p/'cwd',p/'exe',*(p/'fd').iterdir()]:
    try:target=os.readlink(ref)
    except OSError:continue
    found=[r for r in roots if target==r or target.startswith(r+'/')]
    if found:hits.append({'pid':int(p.name),'source':'path','roots':found})
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 return hits
def consumer_references():
 roots=[p for p,a in EXPECTED.items()if a in ['delete_tree','native_git_worktree_remove']];hits=[];files=set()
 for directory in ['/root/mgs-agent/scripts','/etc/systemd/system','/etc/systemd/user','/root/.config/systemd/user','/etc/cron.d','/var/spool/cron/crontabs','/root/.local/bin']:
  d=pathlib.Path(directory)
  if d.exists():files.update(p for p in d.rglob('*')if p.is_file()and not p.name.endswith(('.pyc','.lock')))
 files.add(pathlib.Path('/etc/crontab'))
 for profile in ['zeus','ares','atena']:
  home=pathlib.Path('/root/.hermes/profiles')/profile;files.add(home/'config.yaml');files.update((home/'cron').glob('*.json'))
 for p in files:
  if str(p)=='/root/.local/bin/hermes-main-ad2d4822-mgs':continue
  if not p.is_file()or p.stat().st_size>8*1024*1024:continue
  data=p.read_bytes()
  if b'\0'in data:continue
  if any(root.encode()in data for root in roots):hits.append(str(p))
 return sorted(hits)
def check_scope(m):
 assert len(m['targets'])==4 and {r['path']:r['action']for r in m['targets']}==EXPECTED,'scope drift'
 assert m['authority']['owner_id']=='344196393512075265'and m['authority']['preparation_message_id']=='1571249324464148642'
 assert m['full_old_python_environment_rebuilt']is False
 assert m['no_deletion_authorization']is True
 for helper,digest in m['helper_sha256'].items():assert sha(OUT/helper)==digest,'helper drift'
def verify(m,post=False,recovery=True):
 check_scope(m)
 if post:
  assert all(not os.path.lexists(r['path'])for r in m['targets']),'target remains'
 else:
  totals={'files':0,'directories':0,'symlinks':0}
  for row in m['targets']:
   assert not os.path.ismount(row['path']);actual=collect(row['path']);assert actual['fingerprint']==row['fingerprint'],'metadata drift: '+row['path'];assert actual['counts']==row['counts'],'count drift'
   for k,v in actual['counts'].items():totals[k]+=v
  assert totals==m['counts'],'total count drift'
  admin=pathlib.Path('/root/.hermes/hermes-agent-port-main-59004a62-mgs/.git/worktrees');assert sorted(p.name for p in admin.iterdir())==['hermes-agent-port-main-ad2d4822-mgs'],'new linked worktree'
  assert not process_references(list(EXPECTED)),'active consumer'
  assert not consumer_references(),'new executable reference'
 for p in m['retained_paths']:assert pathlib.Path(p).exists(),'retained path missing: '+p
 for row in m['retained_hashes']:assert sha(row['path'])==row['sha256'],'protected hash drift: '+row['path']
 assert str(pathlib.Path('/root/.local/bin/hermes').resolve())==m['live_launcher_target']
 for profile,pid in m['gateway_pids'].items():
  assert int(subprocess.check_output(['systemctl','show',profile+'-gateway.service','-p','MainPID','--value'],text=True).strip())==pid
  assert subprocess.run(['systemctl','is-active','--quiet',profile+'-gateway.service']).returncode==0
 failed=subprocess.check_output(['systemctl','--failed','--no-legend','--plain'],text=True);assert not failed.strip(),'failed systemd units'
 proof=None
 if recovery:
  spec=importlib.util.spec_from_file_location('retained_recovery',OUT/'recover-retained.py');assert spec and spec.loader;mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);proof=mod.verify_recovery()
 return {'status':'PASS','mode':'post'if post else'preflight','target_paths':4,'counts':m['counts'],'recovery':proof,'deletions_by_validator':0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--post',action='store_true');a=p.parse_args();manifest=OUT/'deletion-manifest.json';assert sha(manifest)==(OUT/'deletion-manifest.sha256').read_text().split()[0];print(json.dumps(verify(json.loads(manifest.read_text()),a.post)))
