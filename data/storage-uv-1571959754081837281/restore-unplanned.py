"""Restore only the 45 unplanned UV-cache nodes; never rerun prune."""
import pathlib,json,gzip,os,stat,subprocess,fcntl,datetime,collections
ROOT=pathlib.Path('/root/mgs-agent');OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-uv-1571959754081837281');CACHE=pathlib.Path('/root/.cache/uv')
diff=json.load(open(OUT/'postcheck-path-difference.json'));missing=set(diff['missing']);rows={r['relative']:r for r in (json.loads(x)for x in gzip.open(PRIVATE/'metadata-second.jsonl.gz','rt'))};expected=json.load(gzip.open(PRIVATE/'retained-payloads.json.gz','rt'));first=json.load(open(OUT/'unplanned-provider-first-pass.json'));wheels=json.load(open(OUT/'unplanned-wheels-reconstructed.json'));assert wheels['status']=='PASS'and wheels['files']==3
providers={p:matches[0]for p,matches in first['found'].items()};providers.update({x['target']:x['provider']for x in wheels['results']});assert len(providers)==30
assert dict(collections.Counter(rows[x]['kind']for x in missing))=={'directory':12,'file':30,'link':3}
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def audit(action,extra):
 row=dict(at=datetime.datetime.now().astimezone().isoformat(),agent='zeus',owner_id='344196393512075265',thread_id='1569928464033783862',confirmation_message_id='1571969258986938601',action=action,**extra)
 with open(ROOT/'logs/events-audit.jsonl','a')as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
assert not(OUT/'cache-restoration-result.json').exists()
stage=PRIVATE/'unplanned-restoration-payloads';stage.mkdir(mode=0o700,exist_ok=False);staged={}
for i,(target,provider)in enumerate(sorted(providers.items())):
 assert target==str(CACHE/os.path.relpath(target,CACHE))and not os.path.lexists(target)
 assert sha(provider)==expected[target]
 dest=stage/str(i);dest.write_bytes(pathlib.Path(provider).read_bytes());os.chmod(dest,0o600);assert sha(dest)==expected[target];staged[target]=str(dest)
# Reject an active native cache writer or a process consuming the repair roots.
roots=sorted({str(CACHE/pathlib.PurePosixPath(x).parts[0]/pathlib.PurePosixPath(x).parts[1])if x.startswith('archive-v0/')else str((CACHE/x).parents[0])for x in missing if rows[x]['kind']=='file'})
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  executable=os.readlink(proc/'exe');assert pathlib.Path(executable).name not in {'uv','uvx'},'UV writer is active'
  surfaces=[executable,os.readlink(proc/'cwd'),(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'),(proc/'maps').read_text(errors='replace')]
  for fd in(proc/'fd').iterdir():
   try:surfaces.append(os.readlink(fd))
   except (FileNotFoundError,ProcessLookupError):pass
  assert not any(root in text for root in roots for text in surfaces),'Repair root has active consumer'
 except (FileNotFoundError,ProcessLookupError):pass
parents=set()
for rel in missing:
 p=pathlib.PurePosixPath(rel).parent
 while str(p)!='.':
  if str(p)not in missing:parents.add(str(p))
  p=p.parent
approved=json.load(open(OUT/'prune-manifest.json'))['targets'];approved_ancestors={'.'}
for target in approved:
 p=pathlib.PurePosixPath(os.path.relpath(target,CACHE)).parent
 while str(p)!='.':approved_ancestors.add(str(p));p=p.parent
lock=os.open(CACHE/'.lock',os.O_RDONLY)
try:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert all(not os.path.lexists(CACHE/r)for r in missing)
 audit('UV_native_prune_scope_deviation_restoration_start',dict(unplanned_nodes=45,unplanned_regular_files=30,reason='CLI uv_distribution::prune stage was omitted from original source-derived model; native operation succeeded; no retry. All 30 exact byte providers verified before restoration.'))
 for rel in sorted(missing,key=lambda x:len(pathlib.PurePosixPath(x).parts)):
  row=rows[rel];p=CACHE/rel
  if row['kind']=='directory':p.mkdir(mode=row['mode'])
 for rel in sorted(missing):
  row=rows[rel];p=CACHE/rel
  if row['kind']=='file':
   fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,row['mode'])
   with os.fdopen(fd,'wb')as f:f.write(pathlib.Path(staged[str(p)]).read_bytes());f.flush();os.fsync(f.fileno())
   os.chown(p,row['uid'],row['gid']);os.chmod(p,row['mode']);os.utime(p,ns=(row['mtime_ns'],row['mtime_ns']));assert sha(p)==expected[str(p)]
  elif row['kind']=='link':os.symlink(row['target'],p);os.chown(p,row['uid'],row['gid'],follow_symlinks=False);os.utime(p,ns=(row['mtime_ns'],row['mtime_ns']),follow_symlinks=False)
  with open(OUT/'cache-restoration-journal.jsonl','a')as f:f.write(json.dumps(dict(relative=rel,kind=row['kind'],restored=True))+'\n');f.flush();os.fsync(f.fileno())
 for rel in sorted(missing,key=lambda x:len(pathlib.PurePosixPath(x).parts),reverse=True):
  row=rows[rel];p=CACHE/rel
  if row['kind']=='directory':os.chown(p,row['uid'],row['gid']);os.chmod(p,row['mode']);os.utime(p,ns=(row['mtime_ns'],row['mtime_ns']))
 for rel in parents-approved_ancestors:
  row=rows[rel];p=CACHE/rel;assert p.is_dir();os.utime(p,ns=(row['mtime_ns'],row['mtime_ns']))
 validation=[]
 for rel in sorted(missing):
  p=CACHE/rel;row=rows[rel];s=os.lstat(p);kind='file'if stat.S_ISREG(s.st_mode)else'directory'if stat.S_ISDIR(s.st_mode)else'link'if stat.S_ISLNK(s.st_mode)else'other'
  assert kind==row['kind']and(stat.S_IMODE(s.st_mode),s.st_uid,s.st_gid,s.st_mtime_ns)==(row['mode'],row['uid'],row['gid'],row['mtime_ns'])
  if kind=='file':assert s.st_size==row['size']and sha(p)==expected[str(p)]
  if kind=='link':assert os.readlink(p)==row['target']
  validation.append(dict(relative=rel,kind=kind,exact_bytes_or_link_and_restorable_metadata_verified=True,inode_or_ctime_may_differ=True))
 assert all(not os.path.lexists(t)for t in approved)
 result=dict(status='PASS',restored_nodes=45,restored_regular_files=30,restored_directories=12,restored_symlinks=3,all_original_regular_SHA256_matched=True,wheels_reconstructed_and_original_SHA256_matched=3,restorable_metadata_verified=True,physical_inode_ctime_not_claimed_restored=True,original_approved_targets_still_absent=193,no_prune_retry=True,global_cache_exclusive_flock_used=True,validation=validation,at=datetime.datetime.now().astimezone().isoformat())
 (OUT/'cache-restoration-result.json').write_text(json.dumps(result,indent=2)+'\n');audit('UV_native_prune_scope_deviation_cache_restored',dict(restored_nodes=45,restored_regular_files=30,all_original_regular_SHA256_matched=True,approved_targets_absent=193,no_prune_retry=True))
 print(json.dumps({k:v for k,v in result.items()if k!='validation'}))
finally:
 fcntl.flock(lock,fcntl.LOCK_UN);os.close(lock)
