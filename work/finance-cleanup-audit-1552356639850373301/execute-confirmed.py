import pathlib,os,json,hashlib,stat,subprocess,datetime,fcntl,shutil,sys,shlex
R=pathlib.Path('/root/mgs-agent');APP=R/'apps/finance-system';P=APP/'private';W=pathlib.Path(__file__).parent
H='c50e6d99faedbc4fa6709397a02c55f6fe28fd4949feb208858697b5f7616621';AUTH='1552362272725401693'
assert sys.argv[1:]==['--execute',H]
M=W/'deletion-manifest-1552361649480933457.json'
assert hashlib.sha256(M.read_bytes()).hexdigest()==H
m=json.loads(M.read_text());targets=m['targets'];assert len(targets)==len({x['path'] for x in targets})==270
assert not (W/'deletion-result.json').exists(),'Existing result requires manual reconciliation, never blind retry'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def audit(action,**kw):
 e={'timestamp':now(),'agent':'zeus','action':action,'confirmation_message_id':AUTH,'manifest_sha256':H,**kw}
 with (R/'logs/events-audit.jsonl').open('a') as f:
  fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps(e)+'\n');f.flush();os.fsync(f.fileno())
def save(name,data):
 with (W/name).open('w') as f:json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())
def tree(root):
 assert root.parent==P and root.exists() and not root.is_symlink()
 paths=[root]
 if root.is_dir():
  def onerror(e):raise e
  for base,dirs,files in os.walk(root,followlinks=False,onerror=onerror):paths.extend(pathlib.Path(base)/n for n in dirs+files)
 digest=hashlib.sha256();count=size=0
 for path in sorted(paths):
  s=path.lstat();assert s.st_dev==P.stat().st_dev and not stat.S_ISLNK(s.st_mode)
  assert stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)
  if stat.S_ISREG(s.st_mode):assert s.st_nlink==1;count+=1
  size+=s.st_blocks*512
  digest.update(json.dumps([str(path.relative_to(root)),s.st_mode,s.st_dev,s.st_ino,s.st_nlink,s.st_size,s.st_blocks,s.st_mtime_ns]).encode())
 return {'metadata_sha256':digest.hexdigest(),'file_count':count,'entry_count':len(paths),'allocated_bytes':size}
def validate(x):
 p=pathlib.Path(x['path']);assert p.resolve()==p and p.parent==P
 assert (x['action']=='delete_file' and p.is_file()) or (x['action']=='delete_tree' and p.is_dir())
 got=tree(p)
 for k in got:assert got[k]==x[k],('drift',x['name'],k)
def references():
 roots=[x['path'] for x in targets];hit=lambda p:any(p==r or p.startswith(r+'/') for r in roots);refs=[]
 for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines():
  mount=line.split()[4];assert not hit(mount),('mount',mount)
 for proc in pathlib.Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:
   cmd=(proc/'cmdline').read_bytes().decode(errors='replace')
   for r in roots:
    if r in cmd:refs.append((proc.name,'cmdline',r))
   for f in [proc/'cwd',proc/'exe']+list((proc/'fd').iterdir()):
    try:
     link=os.readlink(f)
     if hit(link):refs.append((proc.name,'link',link))
    except FileNotFoundError:pass
   for line in (proc/'maps').read_text().splitlines():
    p=line.split(maxsplit=5)[-1]
    if hit(p):refs.append((proc.name,'mmap',p))
  except (FileNotFoundError,ProcessLookupError):pass
 assert not refs,refs
 return refs
def retained():
 result={x['path']:tree(pathlib.Path(x['path'])) for x in m['retained']}
 for x in m['retained_archives_validation']:
  h=hashlib.sha256()
  with open(x['path'],'rb') as f:
   while b:=f.read(4*1024*1024):h.update(b)
  assert h.hexdigest()==x['sha256']
  subprocess.run(['tar','-tf',x['path']],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True,timeout=60)
 return result
def protected():
 paths=list(APP.glob('*.py'))+list(APP.glob('*.mjs'))
 for folder in ['public','tests','deploy']:
  paths.extend(p for p in (APP/folder).rglob('*') if p.is_file() and p.suffix in ['.py','.mjs','.js','.css','.html','.md','.json','.sh','.service'])
 paths.extend(p for p in P.glob('*') if p.is_file() and not p.is_symlink() and (p.name.startswith('source.') or p.name.endswith('fixture.json')))
 paths.append(R/'data/finance-gam-revenue-rules.json')
 return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
def disk():
 s=os.statvfs('/');used=(s.f_blocks-s.f_bfree)*s.f_frsize;avail=s.f_bavail*s.f_frsize
 return {'used':used,'available':avail,'percent':used/(used+avail)*100}
def units():
 s=subprocess.run(['systemctl','--failed','--no-legend','--plain'],capture_output=True,text=True,check=True).stdout
 assert not s.strip(),s
 return subprocess.run(['systemctl','show','hermes-zeus','hermes-atena','hermes-ares','-p','Id','-p','MainPID','-p','ActiveState'],capture_output=True,text=True,check=True).stdout
sys.path.insert(0,str(APP));import finance_gam_revenue_sync as remote
helper_hash=hashlib.sha256((APP/'finance_gam_revenue_sync.py').read_bytes()).hexdigest()
def production():
 sql="SELECT json_build_object('id',id,'hash',md5(ROW(overrides,additions,result,revision,state)::text)) FROM scenarios ORDER BY id"
 out=remote.ssh("systemctl is-active mgs-finance-dash mgs-postgresql18; systemctl show mgs-finance-dash mgs-postgresql18 -p Id -p MainPID -p WorkingDirectory; "+remote.PG+"psql -h "+remote.SOCKET+" -U mgs_pg -d mgs_finance -At -c "+shlex.quote(sql),timeout=90)
 assert out.startswith('active\nactive\n');return out
before_production=production();before_units=units();before_protected=protected();before_retained=retained()
conditional=json.loads((W/'conditional-staging.json').read_text());assert all(pathlib.Path(x['path']).is_dir() for x in conditional)
assert not subprocess.run(['git','-C',str(R),'ls-files','apps/finance-system/private'],capture_output=True,text=True,check=True).stdout.strip()
for x in targets:validate(x)
references();assert hashlib.sha256((APP/'finance_gam_revenue_sync.py').read_bytes()).hexdigest()==helper_hash
before_disk=disk();save('deletion-before.json',{'disk':before_disk,'protected':before_protected,'retained':before_retained,'production':before_production,'units':before_units,'preflight_pass':True})
audit('finance_cleanup_delete_started',target_count=270,files=m['file_count'],allocated_bytes=m['allocated_bytes'],executor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),remote_helper_sha256=helper_hash)
deleted=[];result={'status':'started','confirmation':AUTH,'manifest_sha256':H,'deleted':deleted}
try:
 assert shutil.rmtree.avoids_symlink_attacks
 for x in targets:
  validate(x);p=pathlib.Path(x['path'])
  if x['action']=='delete_tree':shutil.rmtree(p)
  else:p.unlink()
  assert not os.path.lexists(p);deleted.append(x['path'])
  with (W/'deletion-journal.jsonl').open('a') as f:f.write(json.dumps({'path':x['path'],'removed_at':now()})+'\n');f.flush();os.fsync(f.fileno())
 assert len(deleted)==270 and all(not os.path.lexists(x['path']) for x in targets)
 after_protected=protected();assert before_protected==after_protected
 after_retained=retained();assert before_retained==after_retained
 assert all(pathlib.Path(x['path']).is_dir() for x in conditional)
 after_production=production();assert before_production==after_production,'Production state changed; reconcile authorized concurrency'
 assert before_units==units()
 os.sync();after_disk=disk()
 result.update(status='filesystem_completed_validated',deleted_count=len(deleted),files_removed=m['file_count'],allocated_bytes=m['allocated_bytes'],observed_reclaimed_bytes=after_disk['available']-before_disk['available'],before_disk=before_disk,after_disk=after_disk,protected_hash_count=len(before_protected),retained_count=len(before_retained),protected_unchanged=True,production_fingerprint_unchanged=True,services_unchanged=True,conditional_stages_preserved=len(conditional),financial_writes=0,completed_at=now())
 save('deletion-result.json',result);audit('finance_cleanup_delete_completed',deleted_count=len(deleted),observed_reclaimed_bytes=result['observed_reclaimed_bytes'],protected_unchanged=True)
 print(json.dumps({k:v for k,v in result.items() if k!='deleted'},indent=2))
except BaseException as e:
 result.update(status='partial_failure',error_type=type(e).__name__,error=str(e)[:500],remaining=[x['path'] for x in targets if os.path.lexists(x['path'])]);save('deletion-result.json',result);audit('finance_cleanup_delete_partial_failure',deleted=deleted,remaining=result['remaining'],error_type=type(e).__name__);raise
