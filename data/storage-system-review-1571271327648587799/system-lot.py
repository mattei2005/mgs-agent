"""Read-only by default. Exact package retirement/file deletion needs new owner approval."""
import pathlib,json,os,stat,subprocess,hashlib,gzip,argparse,datetime,sys
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent');SEC=pathlib.Path('/root/.hermes/secure-backups/storage-system-review-1571271327648587799')
EXPECTED_PACKAGES={'linux-headers-6.8.0-138','linux-headers-6.8.0-138-generic','linux-image-6.8.0-138-generic','linux-modules-6.8.0-138-generic','linux-headers-6.8.0-142','linux-headers-6.8.0-142-generic','linux-image-6.8.0-142-generic','linux-modules-6.8.0-142-generic'}
GO_ARCHIVE='/root/.local/share/mgs-router-toolchain/go1.27.1.linux-amd64.tar.gz'
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def metadata(p):
 s=os.lstat(p);r={'path':str(p),'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid,'size':s.st_size,'allocated':s.st_blocks*512,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'dev':s.st_dev,'ino':s.st_ino,'nlink':s.st_nlink}
 if stat.S_ISLNK(s.st_mode):r['target']=os.readlink(p)
 return r
def fingerprint(rows):
 h=hashlib.sha256()
 for r in sorted(rows,key=lambda x:x['path']):h.update(json.dumps(r,sort_keys=True,separators=(',',':')).encode()+b'\n')
 return h.hexdigest()
def installed_package(name):
 p=subprocess.run(['dpkg-query','-W','-f=${db:Status-Abbrev}\t${Version}',name],capture_output=True,text=True);return p.stdout.strip()if p.returncode==0 else None
def simulate(packages):
 p=subprocess.run(['apt-get','-s','-y','purge','--',*[r['name']for r in packages]],capture_output=True,text=True,timeout=60);assert p.returncode==0,'purge simulation failed';actions=[]
 for line in p.stdout.splitlines():
  if line.startswith(('Remv ','Purg ','Inst ')):
   parts=line.split();assert parts[0]=='Purg','unapproved native transaction';actions.append(parts[1])
 assert set(actions)==EXPECTED_PACKAGES and len(actions)==8,'native transaction drift'
 return actions
def consumers(m):
 ancestors=set();pid=os.getpid()
 while pid>1:
  ancestors.add(pid)
  try:pid=int(pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
  except OSError:break
 prefixes=m['kernel_payload_roots']+[r['path']for r in m['file_targets']];hits=[]
 for proc in pathlib.Path('/proc').iterdir():
  if not proc.name.isdigit()or int(proc.name)in ancestors:continue
  try:
   args=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');comm=(proc/'comm').read_text().strip()
   if comm in ['apt','apt-get','dpkg','unattended-upgr']and not('unattended-upgrade-shutdown'in args and '--wait-for-signal'in args):hits.append({'pid':int(proc.name),'reason':'package_writer'})
   if any(p in args for p in prefixes):hits.append({'pid':int(proc.name),'reason':'target_command_reference'})
   for p in [proc/'cwd',proc/'exe',*(proc/'fd').iterdir()]:
    try:target=os.readlink(p)
    except OSError:continue
    if any(target==r or target.startswith(r+'/')for r in prefixes):hits.append({'pid':int(proc.name),'reason':'target_open_reference'})
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 return hits
def verify(m,post=False):
 assert m['preparation_authority']=='1571271327648587799'and m['owner_id']=='344196393512075265'
 assert len(m['packages'])==8 and {p['name']for p in m['packages']}==EXPECTED_PACKAGES,'package scope drift'
 assert len(m['file_targets'])==29 and len({r['path']for r in m['file_targets']})==29,'file scope drift'
 for row in m['file_targets']:
  p=pathlib.Path(row['path']);assert str(p)==GO_ARCHIVE or(p.parent==pathlib.Path('/var/cache/apt/archives')and p.suffix=='.deb'),'path scope drift'
 assert m['executor_sha256']==sha(__file__),'executor drift'
 allowed_generated={'modules.dep','modules.dep.bin','modules.alias','modules.alias.bin','modules.symbols','modules.symbols.bin','modules.softdep','modules.devname','modules.builtin.bin','modules.builtin.alias.bin'}
 assert len(m['generated_kernel_metadata'])==20
 for path in m['generated_kernel_metadata']:
  p=pathlib.Path(path);assert p.name in allowed_generated and str(p.parent)in ['/lib/modules/6.8.0-138-generic','/lib/modules/6.8.0-142-generic']
 assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==m['boot_id'],'unexpected reboot'
 assert subprocess.check_output(['uname','-r'],text=True).strip()==m['running_kernel']
 for name,version in m['protected_package_versions'].items():assert installed_package(name)=='ii \t'+version,'protected kernel package changed: '+name
 for row in m['protected_hashes']:assert sha(row['path'])==row['sha256'],'protected content changed: '+row['path']
 for row in m['rollback_packages']:
  assert sha(row['path'])==row['sha256'],'rollback checksum failure'
  assert subprocess.check_output(['dpkg-deb','-f',row['path'],'Package'],text=True).strip()==row['package']
  assert subprocess.check_output(['dpkg-deb','-f',row['path'],'Version'],text=True).strip()==row['version']
 for profile,pid in m['gateway_pids'].items():
  assert int(subprocess.check_output(['systemctl','show',profile+'-gateway.service','-p','MainPID','--value'],text=True).strip())==pid
  assert subprocess.run(['systemctl','is-active','--quiet',profile+'-gateway.service']).returncode==0
 assert not subprocess.check_output(['systemctl','--failed','--no-legend','--plain'],text=True).strip(),'failed service'
 if post:
  assert all(not os.path.lexists(r['path'])for r in m['file_targets'])
  assert all(not(installed_package(r['name'])or'').startswith('ii')for r in m['packages'])
  assert all(not os.path.lexists(r['path'])for r in json.load(gzip.open(m['kernel_metadata'],'rt'))),'old kernel payload remains'
  grub=pathlib.Path('/boot/grub/grub.cfg').read_text()
  assert all(v not in grub for v in m['retired_kernel_versions'])
  assert all(v in grub for v in m['retained_kernel_versions'])
  assert not subprocess.check_output(['dpkg','--audit'],text=True).strip(),'dpkg audit findings'
 else:
  assert not consumers(m),'active package/target consumer'
  assert not set(subprocess.check_output(['apt-mark','showhold'],text=True).splitlines())&EXPECTED_PACKAGES,'held package'
  for row in m['packages']:assert installed_package(row['name'])=='ii \t'+row['version'],'package identity drift'
  for row in m['file_targets']:
   assert metadata(row['path'])==row['metadata'],'cached file metadata drift';assert sha(row['path'])==row['sha256']
  expected=json.load(gzip.open(m['kernel_metadata'],'rt'));expected_paths={r['path']for r in expected};observed=set()
  for root in m['kernel_payload_roots']:
   assert not os.path.ismount(root),'target unexpectedly mounted'
   p=pathlib.Path(root)
   if p.is_dir():
    assert not p.is_symlink(),'kernel tree is a symlink'
    for directory,dirs,files in os.walk(p,followlinks=False):
     for name in list(dirs):
      q=pathlib.Path(directory,name)
      if q.is_symlink():observed.add(str(q));dirs.remove(name)
     observed.update(str(pathlib.Path(directory,name))for name in files)
   else:observed.add(root)
  assert observed<=expected_paths,'unclassified new payload in kernel tree'
  actual=[metadata(r['path'])for r in expected];assert fingerprint(actual)==m['kernel_fingerprint'],'kernel metadata drift'
  assert len(actual)==m['kernel_payload_count'],'kernel count drift'
  simulate(m['packages'])
 return {'status':'PASS','mode':'post'if post else'preflight','packages':8,'download_files':29,'kernel_payload_nodes':m['kernel_payload_count'],'deletions_by_verifier':0}
def audit(event):
 event.update(at=datetime.datetime.now().astimezone().isoformat(),agent='zeus',thread_id='1569928464033783862')
 with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def execute(m):
 approval=OUT/'system-approval.json'
 if not approval.exists():raise RuntimeError('missing_owner_critical_confirmation_no_mutation')
 a=json.loads(approval.read_text());assert a['owner_id']=='344196393512075265'and a['channel_id']=='1569928464033783862'and a['native_readback_verified']is True
 assert a['confirmation_message_id']!=m['preparation_authority']and a['manifest_sha256']==sha(OUT/'system-lot.json')and a['executor_sha256']==sha(__file__)
 verify(m);marker=OUT/'system-execution-start.json';fd=os.open(marker,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w')as f:json.dump({'confirmation':a['confirmation_message_id'],'manifest_sha256':a['manifest_sha256']},f);f.flush();os.fsync(f.fileno())
 audit({'action':'system_retirement_exact_lot_start','confirmation_message_id':a['confirmation_message_id'],'manifest_sha256':a['manifest_sha256'],'packages':[r['name']for r in m['packages']],'files':[r['path']for r in m['file_targets']]})
 try:
  env=dict(os.environ,DEBIAN_FRONTEND='noninteractive',NEEDRESTART_MODE='l');p=subprocess.run(['apt-get','-y','-o','Dpkg::Options::=--force-confold','purge','--',*[r['name']for r in m['packages']]],capture_output=True,text=True,timeout=360,env=env);(SEC/'kernel-purge.stdout').write_text(p.stdout);(SEC/'kernel-purge.stderr').write_text(p.stderr);assert p.returncode==0,'native purge failed; inspect persisted output before any retry'
  # Native hooks may leave generated metadata, not packaged/user payloads.
  for path in m['generated_kernel_metadata']:
   if os.path.lexists(path):
    s=os.lstat(path);assert stat.S_ISREG(s.st_mode)or stat.S_ISLNK(s.st_mode);os.unlink(path)
  for version in m['retired_kernel_versions']:
   assert version in ['6.8.0-138-generic','6.8.0-142-generic'];p=pathlib.Path('/lib/modules')/version
   if p.exists():
    assert p.is_dir()and not p.is_symlink()and not any(p.iterdir()),'unexpected nonempty module residue';p.rmdir()
  for row in m['file_targets']:
   p=pathlib.Path(row['path']);assert p.parent==pathlib.Path('/var/cache/apt/archives')or str(p)==GO_ARCHIVE
   assert metadata(p)==row['metadata']and sha(p)==row['sha256'],'cache drift after native transaction; do not expand scope';os.unlink(p)
   with (OUT/'system-file-journal.jsonl').open('a')as f:f.write(json.dumps({'path':str(p),'absent':not os.path.lexists(p)})+'\n');f.flush();os.fsync(f.fileno())
  result=verify(m,post=True);(OUT/'system-filesystem-result.json').write_text(json.dumps(result,indent=2)+'\n');audit({'action':'system_retirement_exact_lot_filesystem_completed','confirmation_message_id':a['confirmation_message_id'],'manifest_sha256':a['manifest_sha256']});print(json.dumps(result))
 except Exception as exc:
  audit({'action':'system_retirement_exact_lot_partial_failure','confirmation_message_id':a['confirmation_message_id'],'error_type':type(exc).__name__,'absent_download_files':[r['path']for r in m['file_targets']if not os.path.lexists(r['path'])]});raise
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--post',action='store_true');args=parser.parse_args()
 try:
  path=OUT/'system-lot.json';assert sha(path)==(OUT/'system-lot.sha256').read_text().split()[0];manifest=json.loads(path.read_text());execute(manifest)if args.execute else print(json.dumps(verify(manifest,args.post)))
 except Exception as exc:print('BLOCKED: '+str(exc),file=sys.stderr);raise SystemExit(1)
