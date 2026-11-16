"""Infrastructure-only review of local state directories. No DB startup, SQL, mutation or payload copies."""
import pathlib,os,json,gzip,stat,subprocess,datetime,re,collections,time
OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-local-tests-1571996311308214363');PRIVATE.mkdir(mode=0o700,exist_ok=False);REPO=pathlib.Path('/root/mgs-agent');APP=REPO/'apps/finance-system';prior=json.load(open(REPO/'data/storage-reaudit-1571983565292441731/postgres-clusters.json'));TARGETS=[r['path']for r in prior];assert len(set(TARGETS))==34
protected=json.load(open(REPO/'data/storage-reorganization-1570447435074109502/generated-tests-1570473727043436596/manifest.json'))['protected_prior_roots'];START=time.time()
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def under(p,r):return p==r or p.startswith(r+'/')
def kind(s):return'file'if stat.S_ISREG(s.st_mode)else'directory'if stat.S_ISDIR(s.st_mode)else'link'if stat.S_ISLNK(s.st_mode)else'other'
# Revalidate current counts without opening database pages.
metadata=[];errors=[]
for root in TARGETS:
 assert pathlib.Path(root).is_dir()and not pathlib.Path(root).is_symlink();assert(pathlib.Path(root)/'PG_VERSION').is_file()and(pathlib.Path(root)/'base').is_dir()and(pathlib.Path(root)/'global').is_dir();rows=[];counts=collections.Counter();inodes={}
 def onerror(e):errors.append(dict(path=e.filename,errno=e.errno,phase='cluster_metadata'))
 for d,ds,fs in os.walk(root,followlinks=False,onerror=onerror):
  for name in ['.']+fs+[x for x in ds if pathlib.Path(d,x).is_symlink()]:
   p=pathlib.Path(d)if name=='.'else pathlib.Path(d)/name;s=os.lstat(p);k=kind(s);counts[k]+=1;inodes[(s.st_dev,s.st_ino)]=s.st_blocks*512;row=dict(path=str(p),kind=k,dev=s.st_dev,ino=s.st_ino,size=s.st_size,allocated=s.st_blocks*512,nlink=s.st_nlink,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns)
   if k=='link':row['target']=os.readlink(p)
   rows.append(row)
 pidfile=pathlib.Path(root)/'postmaster.pid';sentinel=None
 if pidfile.is_file():
  first=pidfile.open().readline().strip();sentinel=int(first)if re.fullmatch(r'-?\d+',first)else'non_numeric'
 metadata.append(dict(path=root,counts=dict(counts),allocated_bytes=sum(inodes.values()),protected_by_prior_explicit_set=root in protected,postmaster_pid_marker=sentinel,rows=rows))
with gzip.open(PRIVATE/'cluster-metadata.json.gz','wt',compresslevel=1)as f:json.dump(metadata,f)
# Runtime references: ignore only auditor-ancestor cmdline literals, never real open-file references.
ancestors=set();pid=os.getpid()
while pid>1:
 ancestors.add(pid)
 try:pid=int(pathlib.Path('/proc',str(pid),'stat').read_text().split(') ',1)[1].split()[1])
 except (OSError,ValueError,IndexError):break
runtime=[];processes=0;proc_errors=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  surfaces={}
  for key in ['cwd','exe']:
   try:surfaces[key]=os.readlink(p/key)
   except FileNotFoundError:pass
  if int(p.name)not in ancestors:surfaces['cmdline']=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  surfaces['maps']=(p/'maps').read_text(errors='replace');fd=[]
  for x in(p/'fd').iterdir():
   try:fd.append(os.readlink(x))
   except (FileNotFoundError,ProcessLookupError):pass
  surfaces['fd']='\n'.join(fd);processes+=1
  for root in TARGETS:
   matched=[surface for surface,text in surfaces.items()if re.search(re.escape(root)+r'(?=/|\s|$|[\x00\"\'])',text)]
   if matched:runtime.append(dict(path=root,pid=int(p.name),comm=(p/'comm').read_text().strip(),surfaces=matched))
 except (FileNotFoundError,ProcessLookupError):pass
 except PermissionError as e:proc_errors.append(dict(pid=p.name,errno=e.errno))
dump(OUT/'runtime-reference-review.json',dict(processes=processes,references=runtime,errors=proc_errors,ancestor_cmdline_exclusions=sorted(ancestors),maps_and_open_files_included=True))
# Search all declared uncompressed reference surfaces, excluding database pages/dependencies and own storage audit bodies.
roots=[REPO,pathlib.Path('/etc/systemd/system'),pathlib.Path('/etc/cron.d')]
for home in pathlib.Path('/root/.hermes/profiles').iterdir():
 if home.is_dir():
  roots.extend(p for p in [home/'scripts',home/'cron',home/'config.yaml',home/'.env']if p.exists())
roots.extend(p for p in [pathlib.Path('/etc/crontab'),pathlib.Path('/var/spool/cron/crontabs/root')]if p.exists())
SUFFIX={'.py','.sh','.mjs','.cjs','.js','.ts','.tsx','.jsx','.json','.jsonl','.md','.txt','.conf','.service','.timer','.toml','.yaml','.yml','.html','.sql','.env'}
SKIPDIR={'.git','node_modules','site-packages','__pycache__','.venv','venv','venv-next','cache','browser-profiles'}
source_files=[];excluded=collections.Counter();seen=set();walk_errors=[];unlisted_clusters=[]
def own_audit(p):return any(x in p for x in ['/data/storage-','/work/storage-','/reports/storage-','/context/storage-','/scripts/storage-'])
for base in roots:
 if base.is_file():candidates=[str(base)]
 else:
  candidates=[]
  for d,ds,fs in os.walk(base,topdown=True,followlinks=False,onerror=lambda e:walk_errors.append(dict(path=e.filename,errno=e.errno))):
   if'PG_VERSION'in fs and'base'in ds and'global'in ds:
    if d not in TARGETS:unlisted_clusters.append(d)
    ds[:]=[];excluded['postgres_root']+=1;continue
   ds[:]=[x for x in ds if x not in SKIPDIR and not pathlib.Path(d,x).is_symlink()and not own_audit(str(pathlib.Path(d,x)))]
   for n in fs:
    p=str(pathlib.Path(d,n))
    if own_audit(p):excluded['own_storage_audit_file']+=1;continue
    if pathlib.Path(p).suffix not in SUFFIX and n not in {'.env','crontab','root'}:continue
    if n.endswith(('.key','.pem'))or n in {'auth.json','credentials.json','service-account.json'}:excluded['credential_container']+=1;continue
    candidates.append(p)
 for p in candidates:
  if p in seen:continue
  seen.add(p)
  try:
   s=os.lstat(p)
   if not stat.S_ISREG(s.st_mode):excluded['nonregular_source']+=1;continue
   source_files.append(p)
  except FileNotFoundError:walk_errors.append(dict(path=p,kind='source_disappeared'))
dump(PRIVATE/'reference-source-index.json',source_files)
unique_leaf={root:pathlib.Path(root).name for root in TARGETS if re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-',pathlib.Path(root).name)}
strong={};composite={};family={};families=['test-pg-','ui-test-','ui-browser-','catalog-test-','TEST-payroll-','TEST-periods-','sync-browser-','stage-db','stage-baseline','stage-candidate','isolated-pglite','pgdata']
for root in TARGETS:
 needles=[root.encode(),str(pathlib.Path(root).relative_to(APP)).encode()]
 if root in unique_leaf:needles.append(unique_leaf[root].encode())
 strong[root]=needles
 # Weak/composite matches require the owning run ID and leaf name in the same source file.
 ids=re.findall(r'\d{17,20}',root)
 if ids:composite[root]=(ids[-1].encode(),pathlib.Path(root).name.encode())
def classify_source(p):
 if'/cron/'in p or p.startswith('/etc/')or p.startswith('/var/spool/cron/')or pathlib.Path(p).name in {'.env','config.yaml'}:return'scheduler_or_live_configuration'
 if p.startswith(str(APP)+'/')and'/private/'not in p and pathlib.Path(p).suffix in {'.py','.mjs','.js','.sh','.ts','.sql'}:return'primary_application_code_or_tests'
 if p.startswith(str(REPO/'scripts')+'/')or'/profiles/'in p and'/scripts/'in p:return'operational_helper_code'
 if pathlib.Path(p).suffix in {'.py','.mjs','.js','.sh','.ts'}:return'historical_or_candidate_executable_code'
 return'evidence_or_documentation'
hits=[];family_hits=[];read_errors=[];totalbytes=0;credential_scans=[]
with open(PRIVATE/'reference-hits.jsonl','a')as ledger:
 for index,p in enumerate(source_files):
  exact=set();a=set();b=set();foundfam=set();linebase=1;locations={};tail=b''
  try:
   with open(p,'rb')as f:
    while True:
     chunk=f.read(1024*1024)
     if not chunk:break
     totalbytes+=len(chunk);data=tail+chunk
     for root,needles in strong.items():
      if root in exact:continue
      offsets=[(data.find(n),n)for n in needles];positive=[pos for pos,n in offsets if pos>=0]
      if positive:exact.add(root);locations[root]=linebase+data[:min(positive)].count(b'\n')
     for root,(run,leaf)in composite.items():
      if run in data:a.add(root)
      if leaf in data:b.add(root)
     for fam in families:
      if fam.encode()in data:foundfam.add(fam)
     linebase+=chunk.count(b'\n');tail=data[-1024:]
   category=classify_source(p)
   for target in sorted(exact|(a&b)):
    hit=dict(source=p,target=target,category=category,match='exact_path_or_unique_leaf'if target in exact else'owning_run_id_and_leaf_same_source',line=locations.get(target));hits.append(hit);ledger.write(json.dumps(hit)+'\n')
   if foundfam:family_hits.append(dict(source=p,category=category,families=sorted(foundfam)))
   if pathlib.Path(p).name=='.env':credential_scans.append(dict(path=p,only_target_reference_flags_persisted=True))
  except (OSError,MemoryError)as e:read_errors.append(dict(path=p,error=type(e).__name__))
  if index%1000==0:
   ledger.flush();dump(OUT/'reference-scan-progress.json',dict(files_considered=index+1,files_total=len(source_files),bytes_read=totalbytes,hits=len(hits),errors=read_errors,at=datetime.datetime.now().astimezone().isoformat()))
 ledger.flush();os.fsync(ledger.fileno())
with gzip.open(PRIVATE/'family-reference-index.json.gz','wt',compresslevel=1)as f:json.dump(family_hits,f)
cp=json.load(open(REPO/'data/agent-checkpoints.json'))['checkpoints'];bytarget=[]
for item in metadata:
 root=item['path'];refs=[h for h in hits if h['target']==root];ids=re.findall(r'\d{17,20}',root);owners=[{k:r.get(k)for k in ['id','state','objective','next_step','source']}for r in cp if any(i in str(r.get('id',''))for i in ids)]
 bytarget.append(dict(path=root,counts=item['counts'],allocated_bytes=item['allocated_bytes'],protected_by_prior_explicit_set=item['protected_by_prior_explicit_set'],pid_marker=item['postmaster_pid_marker'],runtime_refs=[r for r in runtime if r['path']==root],exact_or_composite_reference_count=len(refs),reference_categories=dict(collections.Counter(r['category']for r in refs)),reference_sources=sorted({r['source']for r in refs}),owner_checkpoints=owners,status='pending_manual_reference_and_family_review'))
dump(OUT/'cluster-reference-matrix.json',bytarget)
summary=dict(status='reference_collection_complete',authority_message_id='1571996311308214363',infrastructure_scope_only=True,financial_semantics_evaluated=False,clusters=34,current_allocated_bytes=sum(x['allocated_bytes']for x in metadata),explicit_previously_retained_roots=protected,processes=processes,runtime_reference_count=len(runtime),source_files_scanned=len(source_files),source_bytes_read=totalbytes,reference_count=len(hits),family_reference_files=len(family_hits),metadata_errors=errors,process_errors=proc_errors,walk_errors=walk_errors,read_errors=read_errors,unlisted_clusters=unlisted_clusters,database_binaries_excluded=True,archive_contents_not_expanded=True,credentials_or_source_line_contents_persisted=False,own_audit_surfaces_excluded=True,excluded_counts=dict(excluded),databases_opened_or_started=0,files_deleted=0,new_backups_created=False,elapsed_seconds=round(time.time()-START,2))
dump(OUT/'collection-summary.json',summary);print(json.dumps(summary,ensure_ascii=False));print('CLUSTER_MATRIX_REDUCED')
for r in bytarget:print(json.dumps({k:r[k]for k in ['path','allocated_bytes','protected_by_prior_explicit_set','reference_categories','exact_or_composite_reference_count']},ensure_ascii=False))
