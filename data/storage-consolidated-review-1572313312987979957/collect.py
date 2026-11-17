"""Whole-host metadata inventory. No cleanup, imports of apps, DB access or service changes."""
import os,stat,pathlib,json,gzip,subprocess,datetime,collections,heapq,time
OUT=pathlib.Path(__file__).parent
if (OUT/'audit-final.sha256').exists():raise SystemExit('SEALED_AUDIT: use a new observation directory')
PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-reaudit-1572313312987979957')
PRIVATE.mkdir(mode=0o700,exist_ok=False)
START=time.time();OWN=[str(OUT),str(PRIVATE)];ERRORS=[];MOUNTS=[];CLUSTERS=[];VENV=[];GIT=[];LARGE=[]
def under(p,r):return p==r or p.startswith(r+'/')
def now():return datetime.datetime.now().astimezone().isoformat()
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def cmd(args):return subprocess.check_output(args,text=True,timeout=45)
def df(p):
 s=os.statvfs(p);used=(s.f_blocks-s.f_bfree)*s.f_frsize;available=s.f_bavail*s.f_frsize
 return dict(total=s.f_blocks*s.f_frsize,used=used,available=available,reserved_free=(s.f_bfree-s.f_bavail)*s.f_frsize,used_percent=round(100*used/(used+available),2))
def flatten(nodes):
 for n in nodes:
  MOUNTS.append(n);flatten(list(n.get('children',[])))
flatten(json.loads(cmd(['findmnt','-J','-o','TARGET,SOURCE,FSTYPE,OPTIONS']))['filesystems'])
PERSIST=[n for n in MOUNTS if n['fstype']in {'ext4','ext3','ext2','xfs','btrfs','vfat','zfs'}and n.get('source','').startswith('/dev/')]
assert {x['target']for x in PERSIST}=={'/','/boot','/boot/efi'},'New persistent scope needs explicit collector support'
MOUNTPOINTS={n['target']for n in MOUNTS};mounts_safe=[{k:n[k]for k in ('target','source','fstype')}for n in MOUNTS];dump(OUT/'mounts.json',mounts_safe)
PREFIX='/root/mgs-agent';HP='/root/.hermes'
def classify(p,cluster=None):
 parts=p.strip('/').split('/')
 if cluster:return ('postgres_clusters_pending_role',cluster)
 if under(p,PREFIX+'/.git'):return('institutional_git',PREFIX+'/.git')
 if under(p,HP+'/secure-backups'):
  a=p[len(HP+'/secure-backups'):].strip('/').split('/');return('operational_recovery',HP+'/secure-backups/'+ '/'.join(a[:2]))
 if under(p,HP+'/profiles'):
  a=p[len(HP+'/profiles/'):].split('/');name=a[0];tail=a[1:];base=HP+'/profiles/'+name
  if tail and tail[0]=='cache':return('cache_paused_owner_choice',base+'/cache')
  if tail and tail[0]=='browser-profiles':return('persistent_browser_state',base+'/browser-profiles')
  if tail and tail[0]in {'checkpoints','sessions','logs','artifacts','workspaces'}:return('agent_'+tail[0],base+'/'+tail[0])
  return('agent_profile_state',base)
 if under(p,HP+'/cache')or under(p,'/root/.cache')or under(p,'/root/.npm')or under(p,'/var/cache'):return('cache_paused_owner_choice','/'+ '/'.join(parts[:min(4 if under(p,HP+'/cache')else 3,len(parts))]))
 if under(p,PREFIX):
  tail=p[len(PREFIX):].strip('/').split('/');kind=tail[0]
  if kind in {'apps','data','work','reports','logs'}:return('mgs_'+kind,PREFIX+'/'+ '/'.join(tail[:2]))
  return('institutional_code_or_configuration',PREFIX+'/'+kind)
 if under(p,HP):
  a=p[len(HP):].strip('/').split('/');first=a[0]
  if first.startswith('hermes-agent'):return('hermes_code_or_environment',HP+'/'+first)
  if first in {'installs','bin','runtimes','venvs','python'}:return('hermes_managed_installation',HP+'/'+ '/'.join(a[:2]))
  return('other_hermes_state',HP+'/'+first)
 if under(p,'/var/log'):return('system_logs','/'+ '/'.join(parts[:3]))
 if under(p,'/var/lib'):return('system_service_state','/'+ '/'.join(parts[:3]))
 if under(p,'/usr')or under(p,'/lib')or under(p,'/lib64')or under(p,'/bin')or under(p,'/sbin'):return('operating_system_or_installed_tools','/'+parts[0])
 if under(p,'/boot'):return('boot_system','/boot/efi'if under(p,'/boot/efi')else'/boot')
 if under(p,'/etc'):return('system_configuration','/etc')
 if under(p,'/root')or under(p,'/home')or under(p,'/opt')or under(p,'/srv'):return('other_local_data_pending_role','/'+ '/'.join(parts[:3]if under(p,'/home')else parts[:2]))
 if under(p,'/tmp')or under(p,'/var/tmp'):return('temporary_noncache_pending_role','/var/tmp'if under(p,'/var/tmp')else'/tmp')
 return('other_filesystem_data','/'+parts[0]if parts[0]else'/')
# Every inode is credited once. Cross-category hardlinks are reassigned to one shared bucket.
INODES={};UNITS={};FS=[]
shared='shared_hardlinks_between_classes'
def accum(p,s,k,fsroot,cluster=None):
 cat,unit=classify(p,cluster);alloc=s.st_blocks*512;key=(s.st_dev,s.st_ino)
 entry=INODES.get(key)
 if entry is None:INODES[key]=[alloc,s.st_nlink,1,cat,unit,k,fsroot]
 else:
  entry[2]+=1
  if entry[3]!=cat:entry[3]=shared
  if entry[4]!=unit:entry[4]='[shared_between_operational_units]'
 u=UNITS.setdefault(unit,dict(path=unit,category=cat,file=0,directory=0,link=0,other=0,logical_bytes=0,naive_allocated_bytes=0,latest_mtime_ns=0));u[k]+=1;u['logical_bytes']+=s.st_size if k=='file'else 0;u['naive_allocated_bytes']+=alloc;u['latest_mtime_ns']=max(u['latest_mtime_ns'],s.st_mtime_ns)
 row=dict(p=p,k=k,d=s.st_dev,i=s.st_ino,s=s.st_size,b=alloc,n=s.st_nlink,m=stat.S_IMODE(s.st_mode),u=s.st_uid,g=s.st_gid,t=s.st_mtime_ns,c=cat,unit=unit)
 if k=='link':row['target']=os.readlink(p)
 if k=='file'and alloc>=8*1024**2:
  item=(alloc,p,s.st_size)
  if len(LARGE)<100:heapq.heappush(LARGE,item)
  elif item>LARGE[0]:heapq.heapreplace(LARGE,item)
 return row
for mount in PERSIST:
 fr=mount['target'];dev=os.lstat(fr).st_dev;counts=collections.Counter();before=df(fr);excluded=[];contexts: dict[str, str | None] = {fr: None};ledger=PRIVATE/('metadata-root.jsonl.gz'if fr=='/'else'metadata-'+fr.strip('/').replace('/','-')+'.jsonl.gz')
 def error(e):ERRORS.append(dict(filesystem=fr,path=e.filename,errno=e.errno,kind=type(e).__name__))
 with gzip.open(ledger,'wt',compresslevel=1)as w:
  for current,dirs,files in os.walk(fr,topdown=True,followlinks=False,onerror=error):
   cluster=contexts.pop(current,None)
   if 'PG_VERSION'in files and 'base'in dirs and 'global'in dirs:
    cluster=current
    try:version=(pathlib.Path(current)/'PG_VERSION').read_text().strip();version=version if version.isdigit()else'unknown'
    except OSError:version='unreadable'
    CLUSTERS.append(dict(path=current,version=version))
   if 'pyvenv.cfg'in files:VENV.append(current)
   if '.git'in dirs or '.git'in files:GIT.append(current)
   try:
    s=os.lstat(current);row=accum(current,s,'directory',fr,cluster);w.write(json.dumps(row,separators=(',',':'))+'\n');counts['directory']+=1
   except OSError as e:error(e);dirs[:]=[];continue
   keep=[]
   for name in dirs:
    p=os.path.join(current,name)
    try:
     s=os.lstat(p)
     if stat.S_ISLNK(s.st_mode):w.write(json.dumps(accum(p,s,'link',fr,cluster),separators=(',',':'))+'\n');counts['link']+=1;continue
     if p in MOUNTPOINTS or s.st_dev!=dev or any(under(p,r)for r in OWN):excluded.append(p);continue
     keep.append(name);contexts[p]=cluster
    except OSError as e:error(e)
   dirs[:]=keep
   for name in files:
    p=os.path.join(current,name)
    try:
     s=os.lstat(p);k='file'if stat.S_ISREG(s.st_mode)else'link'if stat.S_ISLNK(s.st_mode)else'other';w.write(json.dumps(accum(p,s,k,fr,cluster),separators=(',',':'))+'\n');counts[k]+=1
    except OSError as e:error(e)
 fs=dict(root=fr,source=mount['source'],fstype=mount['fstype'],counts=dict(counts),before=before,after=df(fr),excluded=excluded,ledger=str(ledger));FS.append(fs);dump(OUT/'scan-progress.json',dict(completed_filesystems=FS,errors=ERRORS,at=now()))
CATS=collections.Counter();FSTOTAL=collections.Counter();UNITUNIQUE=collections.Counter();linksout=collections.Counter()
for alloc,nlink,seen,cat,unit,kind,fsroot in INODES.values():
 CATS[cat]+=alloc;FSTOTAL[fsroot]+=alloc;UNITUNIQUE[unit]+=alloc
 if kind=='file'and nlink>seen:linksout[fsroot]+=alloc
for unit,u in UNITS.items():u['unique_allocated_bytes']=UNITUNIQUE[unit]
for fs in FS:fs['unique_allocated_bytes']=FSTOTAL[fs['root']];fs['inodes_with_links_outside_scanned_persistent_names_bytes']=linksout[fs['root']];fs['df_used_minus_named_allocated_bytes']=fs['after']['used']-fs['unique_allocated_bytes']
assert sum(CATS.values())==sum(FSTOTAL.values())==sum(UNITUNIQUE.values())
units=sorted(UNITS.values(),key=lambda x:x['unique_allocated_bytes'],reverse=True)
# Shared-unit bytes are intentionally not charged to any named operational unit.
shared_units=UNITUNIQUE['[shared_between_operational_units]'];dump(OUT/'operational-units.json',dict(units=units,shared_between_units_bytes=shared_units))
pg=[]
for c in CLUSTERS:
 u=UNITS.get(c['path'],{});pg.append(dict(**c,metadata=u,role='pending_producer_and_consumer_proof'))
dump(OUT/'postgres-clusters.json',pg);dump(OUT/'environment-and-git-roots.json',dict(virtualenvs=VENV,git_roots=GIT));dump(OUT/'large-files.json',[dict(allocated_bytes=a,path=p,logical_bytes=s)for a,p,s in sorted(LARGE,reverse=True)])
summary=dict(status='metadata_scan_complete'if not ERRORS else'metadata_scan_complete_with_errors',authority_message_id='1572313312987979957',host=cmd(['hostname']).strip(),started_at=datetime.datetime.fromtimestamp(START).astimezone().isoformat(),finished_at=now(),elapsed_seconds=round(time.time()-START,2),filesystems=FS,category_unique_allocated_bytes=dict(sorted(CATS.items(),key=lambda x:-x[1])),shared_between_units_bytes=shared_units,unique_inode_count=len(INODES),metadata_counts=dict(sum((collections.Counter(x['counts'])for x in FS),collections.Counter())),operational_units=len(units),postgres_cluster_roots=len(CLUSTERS),virtualenv_roots=len(VENV),git_roots=len(GIT),errors=ERRORS,scan_is_live_not_atomic=True,source_file_contents_read=False,postgres_version_markers_only=True,deleted_files=0,application_or_service_changes=False,caches_measured_not_cleanup_candidates=True,own_analysis_excluded=OWN,read_only_mounts_excluded=[n['target']for n in MOUNTS if n['fstype']=='squashfs'])
dump(OUT/'metadata-summary.json',summary)
print(json.dumps(dict(status=summary['status'],elapsed_seconds=summary['elapsed_seconds'],metadata_counts=summary['metadata_counts'],filesystems=[dict(root=f['root'],used_percent=f['after']['used_percent'],named_allocated_GiB=round(f['unique_allocated_bytes']/1024**3,3),unreconciled_df_minus_names_GiB=round(f['df_used_minus_named_allocated_bytes']/1024**3,3))for f in FS],categories_GiB={k:round(v/1024**3,3)for k,v in CATS.most_common()},pg_clusters=len(CLUSTERS),venvs=len(VENV),git_roots=len(GIT),errors=ERRORS),ensure_ascii=False))
