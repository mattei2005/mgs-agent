import pathlib,os,json,stat,hashlib,collections,subprocess,datetime
O=pathlib.Path(__file__).parent;R=pathlib.Path('/root/mgs-agent/apps/finance-system');P=R/'private';targets=json.loads((O/'proposed-primary.json').read_text());retained=json.loads((O/'retained-primary.json').read_text());seen=collections.defaultdict(list);stats=[];errors=[];symlinks=[]
for target in targets:
 root=pathlib.Path(target['path']);assert root.parent==P and not root.is_symlink();paths=[root]
 if root.is_dir():
  for base,dirs,files in os.walk(root,followlinks=False):
   for name in dirs+files:paths.append(pathlib.Path(base)/name)
 digest=hashlib.sha256();count=0;logical=allocated=0;oldest=float('inf');newest=0
 for path in sorted(paths):
  try:s=path.lstat()
  except OSError as e:errors.append({'path':str(path),'error':type(e).__name__});continue
  assert s.st_dev==P.stat().st_dev,'foreign mount';logical+=s.st_size;allocated+=s.st_blocks*512;oldest=min(oldest,s.st_mtime);newest=max(newest,s.st_mtime)
  if stat.S_ISREG(s.st_mode):count+=1;seen[(s.st_dev,s.st_ino)].append({'path':str(path),'nlink':s.st_nlink,'allocated':s.st_blocks*512})
  if stat.S_ISLNK(s.st_mode):symlinks.append({'path':str(path),'target':os.readlink(path)})
  digest.update(json.dumps([str(path.relative_to(root)),s.st_mode,s.st_dev,s.st_ino,s.st_nlink,s.st_size,s.st_blocks,s.st_mtime_ns]).encode())
 stats.append({**target,'file_count':count,'entry_count':len(paths),'logical_bytes':logical,'allocated_bytes':allocated,'oldest_mtime':oldest,'newest_mtime':newest,'metadata_sha256':digest.hexdigest()})
assert not errors and not symlinks
naive=sum(x['allocated_bytes'] for x in stats);file_naive=sum(v['allocated'] for items in seen.values() for v in items);file_reclaim=sum(items[0]['allocated'] for items in seen.values() if len(items)==items[0]['nlink']);reclaim=naive-file_naive+file_reclaim
roots=[x['path'] for x in stats];in_scope=lambda p:any(p==root or p.startswith(root+'/') for root in roots);refs=[]
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  for kind in ['cwd','exe']:
   try:
    link=os.readlink(proc/kind)
    if in_scope(link):refs.append({'pid':proc.name,'type':kind,'target':link})
   except OSError:pass
  for f in (proc/'fd').iterdir():
   try:
    link=os.readlink(f)
    if in_scope(link):refs.append({'pid':proc.name,'type':'fd','target':link})
   except OSError:pass
  cmd=(proc/'cmdline').read_bytes().decode(errors='replace')
  for root in roots:
   if root in cmd:refs.append({'pid':proc.name,'type':'cmdline','target':root})
  for line in (proc/'maps').read_text(errors='replace').splitlines():
   path=line.split(maxsplit=5)[-1]
   if in_scope(path):refs.append({'pid':proc.name,'type':'mmap','target':path})
 except (OSError,PermissionError):pass
assert not refs,refs
archives=[]
for x in retained:
 p=pathlib.Path(x['path'])
 if p.suffix=='.tar':
  r=subprocess.run(['tar','-tf',str(p)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=120);assert r.returncode==0,r.stderr
  h=hashlib.sha256()
  with p.open('rb') as f:
   while b:=f.read(4*1024*1024):h.update(b)
  archives.append({'path':str(p),'tar_listing_pass':True,'sha256':h.hexdigest()})
fs=os.statvfs('/');total=fs.f_blocks*fs.f_frsize;used=(fs.f_blocks-fs.f_bfree)*fs.f_frsize;available=fs.f_bavail*fs.f_frsize
families=collections.defaultdict(lambda:{'targets':0,'files':0,'allocated_bytes':0})
for s in stats:
 f=families[s['family']];f['targets']+=1;f['files']+=s['file_count'];f['allocated_bytes']+=s['allocated_bytes']
result={'status':'analysis_only_no_deletion','authority':'1552356639850373301','root':str(P),'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target_count':len(stats),'file_count':sum(s['file_count'] for s in stats),'naive_allocated_bytes':naive,'inode_aware_reclaim_bytes':reclaim,'external_hardlinks':sum(len(x)!=x[0]['nlink'] for x in seen.values()),'symlinks':symlinks,'errors':errors,'process_references':refs,'families':dict(families),'retained_archives_validation':archives,'disk':{'total':total,'used':used,'available':available,'use_percent':100*used/(used+available),'projected_use_percent':100*(used-reclaim)/(used+available)},'targets':stats,'retained':retained}
(O/'analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['targets','retained','retained_archives_validation']},indent=2));print('analysis_sha256',hashlib.sha256((O/'analysis.json').read_bytes()).hexdigest())
