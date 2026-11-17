"""Exact six-tree retirement gate. Read-only unless a separately verified native approval exists."""
import pathlib,json,os,stat,hashlib,gzip,subprocess,re,fcntl,time,argparse
ROOT=pathlib.Path('/root/mgs-agent');OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-pending25-1572091759247368262');BASE=ROOT/'apps/finance-system/private/network-month-1552101423754514465'
LEAVES={'stage-db-v6', 'stage-db-v2', 'stage-db-v3', 'stage-db-v4', 'stage-db-v5', 'stage-db'}
SERVICES=('zeus-gateway','atena-gateway','ares-gateway')
def need(v,why):
 if not v:raise RuntimeError(why)
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def health():
 d={s:subprocess.check_output(['systemctl','show',s,'-p','ActiveState','-p','MainPID'],text=True).strip()for s in SERVICES};need(all('ActiveState=active'in x and'MainPID=0'not in x for x in d.values()),'GATEWAY_HEALTH');need(not subprocess.check_output(['systemctl','--failed','--no-legend','--plain'],text=True).strip(),'FAILED_UNIT');return d
def snapshot(root):
 root=pathlib.Path(root);device=BASE.stat().st_dev;rows=[];todo=[root];counts={'file':0,'directory':0};allocated=0
 while todo:
  p=todo.pop();s=os.lstat(p);need(s.st_dev==device and not p.is_symlink()and not os.path.ismount(p),'MOUNT_OR_SYMLINK');k='directory'if stat.S_ISDIR(s.st_mode)else'file'if stat.S_ISREG(s.st_mode)else'other';need(k!='other','SPECIAL_NODE');need(k!='file'or s.st_nlink==1,'EXTERNAL_HARDLINK');counts[k]+=1;allocated+=s.st_blocks*512;rows.append([str(p.relative_to(root)),k,s.st_dev,s.st_ino,s.st_size,s.st_blocks,s.st_mtime_ns,s.st_nlink,stat.S_IMODE(s.st_mode),s.st_uid,s.st_gid])
  if k=='directory':
   with os.scandir(p)as it:todo.extend(pathlib.Path(e.path)for e in it)
 rows.sort(key=lambda r:r[0]);return dict(path=str(root),counts=counts,allocated_bytes=allocated,fingerprint_sha256=hashlib.sha256(canon(rows)).hexdigest()),rows
def runtime_refs(paths):
 ancestors=set();pid=os.getpid()
 while pid>1:
  ancestors.add(pid)
  try:pid=int(pathlib.Path('/proc',str(pid),'stat').read_text().split(') ',1)[1].split()[1])
  except(OSError,ValueError,IndexError):break
 hits=[];errors=[]
 for proc in pathlib.Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:
   texts=[]
   if int(proc.name)not in ancestors:texts.append((proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'))
   for rel in ['cwd','exe']:
    try:texts.append(os.readlink(proc/rel))
    except FileNotFoundError:pass
   texts.append((proc/'maps').read_text(errors='replace'))
   for f in(proc/'fd').iterdir():
    try:texts.append(os.readlink(f))
    except(FileNotFoundError,ProcessLookupError):pass
   for p in paths:
    if any(re.search(re.escape(p)+r'(?=/|\s|$|[\x00\"\'])',t)for t in texts):hits.append(dict(pid=int(proc.name),target=p))
  except(FileNotFoundError,ProcessLookupError):pass
  except PermissionError:errors.append(int(proc.name))
 need(not errors,'PROCESS_SURFACE_UNAVAILABLE');return hits
CODE={'.py','.mjs','.cjs','.js','.ts','.tsx','.jsx','.sh','.conf','.service','.timer','.yaml','.yml','.toml'}
def full_code_inventory():
 roots=[ROOT,pathlib.Path('/etc/systemd/system'),pathlib.Path('/etc/cron.d')];files={};skip={'.git','node_modules','site-packages','__pycache__','.venv','venv','cache','browser-profiles'}
 for home in pathlib.Path('/root/.hermes/profiles').iterdir():
  if home.is_dir():roots.extend(p for p in [home/'scripts',home/'cron/jobs.json',home/'config.yaml',home/'SOUL.md',home/'.env']if p.exists())
 roots.extend(p for p in [pathlib.Path('/etc/crontab'),pathlib.Path('/var/spool/cron/crontabs/root')]if p.exists())
 for base in roots:
  if base.is_file():candidates=[str(base)]
  else:
   candidates=[]
   for d,ds,fs in os.walk(base,followlinks=False,onerror=lambda e:(_ for _ in()).throw(e)):
    if 'PG_VERSION'in fs and'base'in ds and'global'in ds:ds[:]=[];continue
    ds[:]=[x for x in ds if x not in skip and not pathlib.Path(d,x).is_symlink()and not any(v in str(pathlib.Path(d,x))for v in ['/data/storage-','/work/storage-','/reports/storage-'])]
    for n in fs:
     p=pathlib.Path(d)/n
     if p.suffix in CODE or n=='.env'or p.parent==ROOT/'apps/finance-system'and p.suffix=='.json':candidates.append(str(p))
  for p in candidates:
   if not pathlib.Path(p).is_file()or pathlib.Path(p).is_symlink():continue
   if p.endswith('/cron/jobs.json'):
    raw=json.load(open(p));jobs=raw.get('jobs',[])if isinstance(raw,dict)else raw;jobs=list(jobs.values())if isinstance(jobs,dict)else jobs;keep=[]
    for r in jobs:
     row={k:r.get(k)for k in ['id','prompt','skills','skill','script','no_agent','monitor_script','monitor_url','context_from','schedule','enabled','model','provider','base_url','workdir','deliver','origin','enabled_toolsets','failure_deliver']if k in r};repeat=r.get('repeat');row['repeat']={k:v for k,v in repeat.items()if k!='completed'}if isinstance(repeat,dict)else repeat;keep.append(row)
    files[p]=hashlib.sha256(canon(sorted(keep,key=lambda r:str(r.get('id'))))).hexdigest()
   else:files[p]=sha(p)
 return files
def target_selector(data,source):
 for leaf in LEAVES:
  target=BASE/leaf
  needles=[str(target).encode(),str(target.relative_to(ROOT/'apps/finance-system')).encode()]
  if any(re.search(re.escape(n)+rb'(?![a-zA-Z0-9_.-])',data)for n in needles):return True
  context=str(source).startswith(str(BASE)+'/')or b'1552101423754514465'in data
  if context and re.search(rb'(?<![a-zA-Z0-9_.-])'+re.escape(leaf.encode())+rb'(?![a-zA-Z0-9_.-])',data):return True
 return False
def census():
 selected={};markers=[b'finance-system',b'pglite',b'pg_version',b'pgdata',b'openDatabase',b'stage-db',b'api-test-db',b'sync-browser-'];app=str(ROOT/'apps/finance-system')+'/'
 for p in full_code_inventory():
  data=pathlib.Path(p).read_bytes()
  if p.endswith('/cron/jobs.json'):
   raw=json.loads(data);jobs=raw.get('jobs',[])if isinstance(raw,dict)else raw;jobs=list(jobs.values())if isinstance(jobs,dict)else jobs
   for r in jobs:
    row={k:r.get(k)for k in ['id','prompt','skills','skill','script','no_agent','monitor_script','monitor_url','context_from','schedule','enabled','model','provider','base_url','workdir','deliver','origin','enabled_toolsets','failure_deliver']if k in r};repeat=r.get('repeat');row['repeat']={k:v for k,v in repeat.items()if k!='completed'}if isinstance(repeat,dict)else repeat;body=canon(row)
    need(not target_selector(body,p),'NEW_TARGET_CONSUMER')
    if any(x.lower()in body.lower()for x in markers):
     need(isinstance(r.get('id'),str)and bool(r['id']),'SCHEDULER_SELECTOR_ID');selected[p+'::job::'+r['id']]=hashlib.sha256(body).hexdigest()
  else:
   need(not target_selector(data,p),'NEW_TARGET_CONSUMER')
   if p.startswith(app)or any(x.lower()in data.lower()for x in markers):selected[p]=hashlib.sha256(data).hexdigest()
 return selected
def shape(m):
 need(m.get('code_census_policy')=='network-intermediates-v1','CODE_CENSUS_POLICY')
 need(m['request_message_id']=='1572091759247368262'and m['status']=='awaiting_exact_critical_test_state_retirement','PLAN_SCOPE');need(len(m['targets'])==6 and {pathlib.Path(r['path']).name for r in m['targets']}==LEAVES,'EXACT_SIX');need({str(pathlib.Path(r['path']).parent)for r in m['targets']}=={str(BASE)},'ALLOWED_PARENT');need(len(m['retained_roots'])==25 and len({r['path']for r in m['retained_roots']})==25 and not({r['path']for r in m['targets']}&{r['path']for r in m['retained_roots']}),'EXACT_RETAINED_SET')
 for r in m['targets']:need(pathlib.Path(r['path']).resolve()==pathlib.Path(r['path'])and(pathlib.Path(r['path'])/'PG_VERSION').is_file(),'PATH_OR_CLUSTER')
 need(sum(r['metadata']['counts']['file']for r in m['targets'])==m['counts']['file']and sum(r['metadata']['counts']['directory']for r in m['targets'])==m['counts']['directory'],'COUNT_TAMPER')
def check(m):
 shape(m);need(sha(__file__)==m['gate_sha256'],'GATE_DRIFT');need(health()==m['runtime'],'RUNTIME_DRIFT');need(os.path.realpath('/root/.local/bin/hermes')==m['launcher'],'LAUNCHER_DRIFT');need(not runtime_refs([r['path']for r in m['targets']]),'PROCESS_REFERENCE')
 for r in m['targets']:need(snapshot(r['path'])[0]==r['metadata'],'TARGET_METADATA_DRIFT')
 for r in m['retained_roots']:need(snapshot(r['path'])[0]==r['metadata'],'RETAINED_METADATA_DRIFT')
 for p,h in m['retained_inputs'].items():need(sha(p)==h,'INPUT_OR_GENERATOR_DRIFT')
 need(sha(m['payload_index'])==m['payload_index_sha256'],'PROTECTED_INDEX_DRIFT');need(sha(m['source_index'])==m['source_index_sha256'],'SOURCE_INDEX_DRIFT');expected=json.load(gzip.open(m['source_index'],'rt'));need(census()==expected,'CODE_OR_SCHEDULER_CENSUS_DRIFT')
 with gzip.open(m['payload_index'],'rt')as f:payloads=json.load(f)
 for p,h in payloads.items():need(sha(p)==h,'RETAINED_PAYLOAD_DRIFT')
 return dict(status='PASS',targets=6,counts=m['counts'],retained_roots=25,retained_payloads=len(payloads),source_census_files=len(expected),deletion_authorized=False,files_deleted=0)
def approval(m,digest):
 p=OUT/'critical-approval.json';need(p.is_file(),'NEW_NATIVE_OWNER_CONFIRMATION_REQUIRED');a=json.load(open(p));need(a.get('author_id')=='344196393512075265'and a.get('manifest_sha256')==digest and a.get('gate_sha256')==m['gate_sha256']and a.get('native_message_readback_verified')is True and a.get('explicit_test_state_retirement')is True,'APPROVAL_BINDING');need(a.get('confirmation_message_id')not in [None,'','1572091759247368262'],'NEW_CONFIRMATION_REQUIRED');return a
def audit(action,extra):
 row=dict(at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),agent='zeus',action=action,authority_message_id='1572091759247368262',**extra)
 with open(ROOT/'logs/events-audit.jsonl','a')as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
def apply(m,digest):
 a=approval(m,digest);need(not(OUT/'execution-start.json').exists(),'REPLAY_BLOCKED');before=check(m);need(sha(m['target_node_index'])==m['target_node_index_sha256'],'NODE_INDEX_DRIFT');nodes=json.load(gzip.open(m['target_node_index'],'rt'));paths=[r['path']for r in m['targets']];allowed={r['path']for r in m['targets']};need(set(nodes)==allowed,'NODE_SCOPE')
 fd=os.open(OUT/'execution-start.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w')as f:json.dump(dict(manifest_sha256=digest,confirmation_message_id=a['confirmation_message_id'],targets=paths),f);f.flush();os.fsync(f.fileno())
 deleted=0;audit('six_network_intermediate_roots_retirement_start',dict(manifest_sha256=digest,confirmation_message_id=a['confirmation_message_id']))
 try:
  for root,rows in nodes.items():
   # Only frozen regular files first. Never recursively remove unknown entries.
   for r in rows:
    if r[1]!='file':continue
    p=pathlib.Path(root)/r[0];s=os.lstat(p);need(stat.S_ISREG(s.st_mode)and(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(r[2],r[3],r[4],r[6]),'NODE_IDENTITY_DRIFT');os.unlink(p);deleted+=1
    with open(OUT/'deletion-journal.jsonl','a')as f:f.write(json.dumps(dict(path=str(p),kind='file'))+'\n');f.flush();os.fsync(f.fileno())
   for r in sorted((r for r in rows if r[1]=='directory'),key=lambda r:len(pathlib.PurePosixPath(r[0]).parts),reverse=True):
    p=pathlib.Path(root)/r[0];s=os.lstat(p);need(stat.S_ISDIR(s.st_mode)and(s.st_dev,s.st_ino)==(r[2],r[3]),'DIRECTORY_IDENTITY_DRIFT');os.rmdir(p);deleted+=1
    with open(OUT/'deletion-journal.jsonl','a')as f:f.write(json.dumps(dict(path=str(p),kind='directory'))+'\n');f.flush();os.fsync(f.fileno())
  need(all(not os.path.lexists(p)for p in paths),'TARGETS_REMAIN');need(health()==m['runtime'],'RUNTIME_CHANGED_AFTER_RETIREMENT')
  for r in m['retained_roots']:need(snapshot(r['path'])[0]==r['metadata'],'RETAINED_METADATA_POST_DRIFT')
  for p,h in json.load(gzip.open(m['payload_index'],'rt')).items():need(sha(p)==h,'RETAINED_PAYLOAD_POST_DRIFT')
  result=dict(status='retired_pending_independent_external_validation',deleted_nodes=deleted,manifest_sha256=digest,confirmation_message_id=a['confirmation_message_id'],retained_payloads_verified=True);(OUT/'native-retirement-result.json').write_text(json.dumps(result,indent=2)+'\n');audit('six_network_intermediate_roots_retirement_completed',result);return result
 except BaseException as e:
  result=dict(status='partial_failure_do_not_replay',deleted_nodes=deleted,remaining_roots=[p for p in paths if os.path.lexists(p)],error_type=type(e).__name__);(OUT/'partial-failure.json').write_text(json.dumps(result,indent=2)+'\n');audit('six_network_intermediate_roots_retirement_partial_failure',result);raise
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();raw=(OUT/'manifest.json').read_bytes();m=json.loads(raw);digest=hashlib.sha256(raw).hexdigest();need(digest==(OUT/'manifest.sha256').read_text().split()[0],'MANIFEST_DRIFT')
 with open(OUT/'execution.lock','a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);print(json.dumps(apply(m,digest)if args.apply else check(m)))
