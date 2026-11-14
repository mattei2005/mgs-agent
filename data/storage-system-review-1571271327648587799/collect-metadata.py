"""Metadata-only persistent filesystem audit; no payloads opened or deleted."""
import os,stat,json,gzip,collections,heapq,datetime,pathlib,subprocess,time
os.umask(0o077)
ID='1571271327648587799';OUT=pathlib.Path('/root/mgs-agent/data/storage-system-review-'+ID);WORK=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch/storage-system-review-'+ID);OUT.mkdir(exist_ok=True);WORK.mkdir(mode=0o700,exist_ok=True)
MOUNTS=json.loads(subprocess.check_output(['findmnt','-J','-o','TARGET,FSTYPE,SOURCE'],text=True));mountpoints=[]
def flatten(rows):
 for row in rows:
  mountpoints.append(row['target']);flatten(row.get('children',[]))
flatten(MOUNTS['filesystems']);prune=set(x.rstrip('/')for x in mountpoints if x not in ['/','/boot','/boot/efi']);prune|={'/proc','/sys','/dev','/run',str(WORK)}
ACTIVE=[str(p)for p in pathlib.Path('/root/.hermes').glob('hermes-agent*')if p.is_dir()]
def inside(p,r):return p==r or p.startswith(r+'/')
def category(p):
 if inside(p,'/root/mgs-agent/.git'):return '08_institutional_git'
 if inside(p,'/root/mgs-agent/data')or inside(p,'/root/mgs-agent/reports'):return '06_mgs_data_reports'
 if inside(p,'/root/.hermes/secure-backups')or inside(p,'/var/backups'):return '03_recovery_sets'
 if any(inside(p,r)for r in ACTIVE):return '04_retained_hermes_runtimes'
 if inside(p,'/root/.hermes/profiles'):
  if '/cache/'in p or p.endswith('/cache'):return '07_profile_caches'
  return '02_profiles_and_work'
 if inside(p,'/root/.cache')or inside(p,'/root/.npm')or inside(p,'/root/.local/share/uv')or inside(p,'/root/.local/share/pnpm'):return '07_package_tool_caches_and_stores'
 if inside(p,'/tmp')or inside(p,'/var/tmp'):return '05_system_temporaries'
 if inside(p,'/var/cache'):return '05_system_package_caches'
 if inside(p,'/var/log'):return '05_system_logs'
 if inside(p,'/var/lib/systemd/coredump'):return '05_system_coredumps'
 if inside(p,'/usr')or inside(p,'/etc')or inside(p,'/boot')or inside(p,'/var')or p in ['/swapfile']:return '05_system_and_services'
 if inside(p,'/root/mgs-agent'):return '06_mgs_controlplane_sources'
 return '05_other_roots_need_classification'
def group(p):
 parts=p.strip('/').split('/',2)
 return '/'+('/'.join(parts[:2]))if len(parts)>1 else p
shared={};catbytes=collections.Counter();groups=collections.Counter();summary=[];big=[];errors=[];excluded=[];start=time.monotonic()
for base in ['/','/boot','/boot/efi']:
 if not os.path.isdir(base):continue
 dev=os.lstat(base).st_dev;counts=collections.Counter();logical=0;ledger=WORK/('root'if base=='/'else base.strip('/').replace('/','-'));ledger=ledger.with_suffix('.jsonl.gz');stack=[base]
 with gzip.open(ledger,'wt',compresslevel=1)as f:
  while stack:
   p=stack.pop()
   if p!=base and(p.rstrip('/')in prune or p in ['/boot','/boot/efi']):excluded.append({'path':p,'reason':'technical_mount_or_analysis_workspace'});continue
   try:s=os.lstat(p)
   except OSError as exc:errors.append({'path':p,'reason':type(exc).__name__});continue
   if s.st_dev!=dev:excluded.append({'path':p,'reason':'different_device'});continue
   kind='file'if stat.S_ISREG(s.st_mode)else'dir'if stat.S_ISDIR(s.st_mode)else'link'if stat.S_ISLNK(s.st_mode)else'other';counts[kind]+=1;logical+=s.st_size if kind=='file'else 0
   c=category(p);g=group(p);allocated=s.st_blocks*512
   row=[p,s.st_mode,s.st_uid,s.st_gid,s.st_size,s.st_mtime_ns,s.st_ctime_ns,allocated,s.st_dev,s.st_ino,s.st_nlink,c]
   if kind=='link':
    try:row.append(os.readlink(p))
    except OSError:row.append(None)
   f.write(json.dumps(row,separators=(',',':'),ensure_ascii=True)+'\n')
   if kind=='dir'or s.st_nlink==1:catbytes[c]+=allocated;groups[g]+=allocated
   else:
    key=(s.st_dev,s.st_ino);old=shared.get(key)
    if old is None:shared[key]=[c,g,allocated,1,s.st_nlink];catbytes[c]+=allocated;groups[g]+=allocated
    else:
     old[3]+=1
     if old[0]!=c and old[0]!='shared_hardlinks':catbytes[old[0]]-=allocated;catbytes['shared_hardlinks']+=allocated;old[0]='shared_hardlinks'
     if old[1]!=g and old[1]!='shared_hardlinks':groups[old[1]]-=allocated;groups['shared_hardlinks']+=allocated;old[1]='shared_hardlinks'
   if kind=='file'and s.st_size>=32*1024*1024:
    item=(allocated,p,s.st_size,s.st_nlink,c,s.st_mtime_ns)
    if len(big)<300:heapq.heappush(big,item)
    elif item>big[0]:heapq.heapreplace(big,item)
   if kind=='dir':
    try:
     with os.scandir(p)as es:stack.extend(e.path for e in es)
    except OSError as exc:errors.append({'path':p,'reason':type(exc).__name__})
 summary.append({'filesystem_root':base,'device':dev,'counts':dict(counts),'logical_regular_bytes':logical,'ledger':str(ledger),'ledger_sha256':subprocess.check_output(['sha256sum',str(ledger)],text=True).split()[0]})
fs=os.statvfs('/');payload={'status':'metadata_inventory_completed','authority_message_id':ID,'schema':['path','mode','uid','gid','size','mtime_ns','ctime_ns','allocated','dev','ino','nlink','category','optional_link_target'],'filesystems':summary,'scan_errors':errors,'technical_exclusions':excluded,'categories_inode_unique_allocated':dict(catbytes),'groups_inode_unique_allocated':dict(groups.most_common()),'largest_regular_files':[{'allocated':r[0],'path':r[1],'logical':r[2],'nlink':r[3],'category':r[4],'mtime_ns':r[5]}for r in sorted(big,reverse=True)],'multilink_inode_count':len(shared),'scanned_allocated_bytes':sum(catbytes.values()),'root_df_used_bytes':(fs.f_blocks-fs.f_bfree)*fs.f_frsize,'root_df_available_bytes':fs.f_bavail*fs.f_frsize,'ledger_workspace_is_analysis_created_and_excluded':str(WORK),'elapsed_seconds':round(time.monotonic()-start,1),'observed_at':datetime.datetime.now().astimezone().isoformat()};(OUT/'metadata-inventory.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'filesystems':summary,'error_count':len(errors),'errors_sample':errors[:5],'categories_gib':{k:round(v/2**30,3)for k,v in catbytes.items()},'top_nonoverlapping_groups_gib':[(k,round(v/2**30,3))for k,v in groups.most_common(22)],'elapsed_seconds':payload['elapsed_seconds']},ensure_ascii=False))
