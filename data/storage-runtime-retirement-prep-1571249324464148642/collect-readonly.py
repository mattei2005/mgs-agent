import os,stat,json,gzip,subprocess,pathlib,datetime,collections,ast
os.umask(0o077)
ID='1571249324464148642'
BASE=pathlib.Path('/root/mgs-agent')
OUT=BASE/('data/storage-runtime-retirement-prep-'+ID);OUT.mkdir(exist_ok=True)
SEC=pathlib.Path('/root/.hermes/secure-backups/runtime-retirement/'+ID);SEC.mkdir(mode=0o700,parents=True,exist_ok=True)
TARGETS=[pathlib.Path('/root/.hermes/hermes-agent-port-main-'+s+'-mgs') for s in ['46904a3b','ad2d4822']]
ENV=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],env=ENV)
def save(name,d):
 p=OUT/name;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');return str(p)
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
protected=[]
for p in [BASE/'scripts/meta-digital-trust-hourly40-run.py',BASE/'scripts/meta-digital-trust-pc1-create-one.py',*BASE.glob('data/meta-digital-trust-*-state.json')]:
 protected.append({'path':str(p),'sha256':sha(p),'size':p.stat().st_size})
for profile in ['zeus','ares','atena']:
 for n in ['config.yaml','SOUL.md']:
  p=pathlib.Path('/root/.hermes/profiles')/profile/n
  if p.is_file():protected.append({'path':str(p),'sha256':sha(p),'size':p.stat().st_size})
services={}
for profile in ['zeus','ares','atena']:
 v=subprocess.check_output(['systemctl','show',profile+'-gateway.service','-p','MainPID','-p','ActiveState','-p','ExecStart'],text=True)
 pid=int(next(x.split('=',1)[1] for x in v.splitlines() if x.startswith('MainPID=')))
 cmd=pathlib.Path('/proc',str(pid),'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
 services[profile]={'pid':pid,'active': 'ActiveState=active' in v,'runtime_paths':[str(r) for r in pathlib.Path('/root/.hermes').glob('hermes-agent*') if str(r).encode() in cmd.encode()],'executable':os.path.realpath('/proc/'+str(pid)+'/exe')}
save('protected-before.json',{'files':protected,'services':services,'launchers':{str(p):{'symlink':p.is_symlink(),'target':os.readlink(p) if p.is_symlink() else None,'sha256':sha(p) if p.is_file() else None} for p in pathlib.Path('/root/.local/bin').glob('hermes*') if p.is_file() or p.is_symlink()}})
rows=[];inodes={};errors=[]
for root in TARGETS:
 head=git(root,'rev-parse','HEAD').decode().strip();modified=git(root,'diff','--name-only','HEAD','-z').decode().split('\0');modified=[p for p in modified if p]
 untracked=[p for p in git(root,'ls-files','--others','--exclude-standard','-z').decode().split('\0') if p]
 ignored=[p for p in git(root,'ls-files','--others','--ignored','--exclude-standard','-z').decode().split('\0') if p]
 refs=git(root,'for-each-ref','--format=%(refname) %(objectname)').decode().splitlines()
 counts=collections.Counter();top=collections.Counter();clusters=[];db_files=[];maxmtime=0;dev=root.stat().st_dev
 ledger=SEC/(root.name+'-metadata.jsonl.gz')
 with gzip.open(ledger,'wt') as f:
  stack=[str(root)]
  while stack:
   p=stack.pop()
   try:
    st=os.lstat(p)
    if st.st_dev!=dev:errors.append({'path':p,'reason':'different_device'});continue
    rel=os.path.relpath(p,root);kind='file' if stat.S_ISREG(st.st_mode) else 'dir' if stat.S_ISDIR(st.st_mode) else 'link' if stat.S_ISLNK(st.st_mode) else 'other'
    counts[kind]+=1;maxmtime=max(maxmtime,st.st_mtime_ns)
    row={'path':rel,'kind':kind,'mode':st.st_mode,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'allocated':st.st_blocks*512,'dev':st.st_dev,'ino':st.st_ino,'nlink':st.st_nlink}
    if kind=='link':row['target']=os.readlink(p)
    f.write(json.dumps(row,separators=(',',':'))+'\n')
    key=(st.st_dev,st.st_ino);record=inodes.setdefault(key,{'bytes':st.st_blocks*512,'nlink':st.st_nlink,'kind':kind,'counts':collections.Counter()});record['counts'][str(root)]+=1
    top[rel.split('/')[0]]+=st.st_blocks*512
    if os.path.basename(p)=='PG_VERSION' and pathlib.Path(p).with_name('base').is_dir() and pathlib.Path(p).with_name('global').is_dir():clusters.append(os.path.dirname(p))
    if kind=='file' and (p.endswith(('.db','.sqlite','.sqlite3')) or p.endswith(('.db-wal','.db-shm'))):db_files.append({'path':rel,'bytes':st.st_size,'allocated':st.st_blocks*512})
    if kind=='dir':
     with os.scandir(p) as es:stack.extend(e.path for e in es)
   except OSError as e:errors.append({'path':p,'reason':type(e).__name__})
 ignored_classes=collections.Counter(p.split('/')[0] for p in ignored)
 gitstate={'root':str(root),'head':head,'modified_paths':modified,'untracked_paths':untracked,'ignored_paths':ignored,'ignored_classes':dict(ignored_classes),'refs':refs,'git_common_dir':git(root,'rev-parse','--path-format=absolute','--git-common-dir').decode().strip(),'worktrees':git(root,'worktree','list','--porcelain').decode().splitlines()}
 save(root.name+'-git-state.json',gitstate)
 rows.append({'root':str(root),'head':head,'counts':dict(counts),'top_naive_allocations':dict(top.most_common(12)),'ignored_classes':dict(ignored_classes),'modified_files':len(modified),'untracked_files':len(untracked),'postgres_clusters':clusters,'sqlite_like_files':db_files,'newest_mtime_ns':maxmtime,'metadata_ledger':str(ledger),'metadata_ledger_sha256':sha(ledger)})
for row in rows:
 r=row['root'];row['inode_unique_occupied_bytes']=sum(v['bytes'] for v in inodes.values() if r in v['counts'])
 row['exclusive_reclaim_if_all_other_gates_pass']=sum(v['bytes'] for v in inodes.values() if r in v['counts'] and len(v['counts'])==1 and (v['kind']=='dir' or v['nlink']==v['counts'][r]))
save('metadata-result.json',{'roots':rows,'scan_errors':errors,'shared_within_target_set_bytes':sum(v['bytes'] for v in inodes.values() if len(v['counts'])>1),'combined_reclaim_if_all_other_gates_pass':sum(v['bytes']for v in inodes.values()if v['kind']=='dir' or sum(v['counts'].values())==v['nlink'])})
# Literal and token references: code/control-plane and schedulers; never emit line contents.
needles=[str(x) for x in TARGETS]+['46904a3b','ad2d4822','meta-digital-trust-hourly40-run.py','meta-digital-trust-pc1-create-one.py']
files=set()
for directory in [BASE/'scripts',BASE/'config',pathlib.Path('/etc/systemd/system'),pathlib.Path('/etc/cron.d'),pathlib.Path('/var/spool/cron/crontabs'),pathlib.Path('/root/.local/bin')]:
 if directory.exists():
  for p in directory.rglob('*'):
   if p.is_file() and not p.name.endswith(('.pyc','.lock')):files.add(p)
for p in pathlib.Path('/etc').glob('crontab'):files.add(p)
for profile in ['zeus','ares','atena']:
 home=pathlib.Path('/root/.hermes/profiles')/profile
 files.add(home/'config.yaml')
 if (home/'cron').exists():files.update((home/'cron').glob('*.json'))
 if (home/'crons').exists():files.update((home/'crons').glob('*.json'))
references=[];source_errors=[]
for p in sorted(files):
 try:
  if p.is_symlink():
   link=os.readlink(p);hits=[n for n in needles if n in link]
   if hits:references.append({'file':str(p),'type':'symlink','needles':hits,'target':link})
  if not p.is_file() or p.stat().st_size>8*1024*1024:continue
  data=p.read_bytes()
  if b'\0' in data:continue
  hits=[]
  for lineno,line in enumerate(data.decode(errors='replace').splitlines(),1):
   found=[n for n in needles if n in line]
   if found:hits.append({'line':lineno,'needles':found,'comment_only':line.lstrip().startswith('#')})
  if hits:references.append({'file':str(p),'type':'content','hits':hits})
 except OSError as e:source_errors.append({'path':str(p),'error':type(e).__name__})
anc=set();pid=os.getpid()
while pid>1:
 anc.add(pid)
 try:pid=int(pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
 except OSError:break
proc_refs=[]
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdigit() or int(proc.name)in anc:continue
 try:
  cmd=(proc/'cmdline').read_bytes();cmdhits=[str(x)for x in TARGETS if str(x).encode()in cmd]
  if cmdhits:proc_refs.append({'pid':int(proc.name),'kind':'cmdline','roots':cmdhits})
  for f in [proc/'cwd',proc/'exe',*(proc/'fd').iterdir()]:
   try:target=os.readlink(f)
   except OSError:continue
   hits=[str(x) for x in TARGETS if target==str(x)or target.startswith(str(x)+'/')]
   if hits:proc_refs.append({'pid':int(proc.name),'kind':f.name if f.name in ['cwd','exe']else 'fd','roots':hits})
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
alternates=[]
for root in sorted(pathlib.Path('/root/.hermes').glob('hermes-agent*')):
 if not root.is_dir():continue
 common=git(root,'rev-parse','--path-format=absolute','--git-common-dir').decode().strip();alt=pathlib.Path(common)/'objects/info/alternates'
 if alt.exists():alternates.append({'root':str(root),'common':common,'alternates':alt.read_text().splitlines()})
trusted_states=[]
for p in BASE.glob('data/meta-digital-trust-*-state.json'):
 d=json.load(open(p));trusted_states.append({'path':str(p),**{k:(len(v)if isinstance(v,list)else v) for k,v in d.items() if k in ['request_id','status','target','completed','execution_backend','updated_at','next_due_at','blocked_reason']}})
save('dependencies.json',{'reference_source_count':len(files),'references':references,'source_errors':source_errors,'process_references':proc_refs,'auditor_ancestors_excluded':sorted(anc),'alternates':alternates,'digital_trust_states':trusted_states,'pc1_meta_campaign_actions':0})
print(json.dumps({'metadata':[{'root':r['root'],'counts':r['counts'],'occupied_gib':round(r['inode_unique_occupied_bytes']/2**30,3),'hypothetical_reclaim_gib':round(r['exclusive_reclaim_if_all_other_gates_pass']/2**30,3),'modified':r['modified_files'],'untracked':r['untracked_files'],'ignored_classes':r['ignored_classes'],'postgres_clusters':len(r['postgres_clusters']),'sqlite_files':r['sqlite_like_files']}for r in rows],'metadata_errors':len(errors),'references':references,'process_hits':proc_refs,'source_errors':source_errors,'evidence':str(OUT)},ensure_ascii=False))
