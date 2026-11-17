"""Frozen four-file local-copy gate. No SQL, DB startup or mutation without exact approval."""
import argparse,ast,collections,datetime,fcntl,gzip,hashlib,json,os,pathlib,re,shlex,stat,subprocess,time
from typing import Any
ROOT=pathlib.Path('/root/mgs-agent');APP=ROOT/'apps/finance-system';OUT=pathlib.Path(__file__).parent;BASE=APP/'private/gam-email-runs'
RUNS={'20261113T080319-0500','20261114T080318-0500','20261115T080318-0500','20261116T080318-0500'}
SERVICES=('zeus-gateway','atena-gateway','ares-gateway')
CODE={'.py','.mjs','.cjs','.js','.ts','.tsx','.jsx','.sh','.conf','.service','.timer','.yaml','.yml','.toml'}
def need(value,reason):
 if not value:raise RuntimeError(reason)
def canon(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def meta(p):
 s=os.lstat(p);need(stat.S_ISREG(s.st_mode)and not pathlib.Path(p).is_symlink(),'REGULAR_FILE_REQUIRED')
 return dict(dev=s.st_dev,ino=s.st_ino,size=s.st_size,blocks=s.st_blocks,nlink=s.st_nlink,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)
def health():
 r={s:subprocess.check_output(['systemctl','show',s,'-p','ActiveState','-p','MainPID'],text=True).strip()for s in SERVICES};need(all('ActiveState=active'in v and'MainPID=0'not in v for v in r.values()),'GATEWAY_HEALTH');need(not subprocess.check_output(['systemctl','--failed','--no-legend','--plain'],text=True).strip(),'FAILED_UNITS');return r
# Inspected read-only full-code and /proc collectors are embedded below during preparation.
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
     if p.suffix in CODE or n=='.env'or p.parent==APP and p.suffix=='.json':candidates.append(str(p))
  for p in candidates:
   if not pathlib.Path(p).is_file()or pathlib.Path(p).is_symlink():continue
   files[p]=sha(p)
 return files

def shape(m):
 need(m['request_message_id']=='1572257170626580601'and m['status']=='frozen_awaiting_exact_critical_confirmation','REQUEST_OR_STATUS')
 targets=m['targets'];expected={str(BASE/r/'mgs_finance-before.dump')for r in RUNS}
 need(len(targets)==4 and {x['path']for x in targets}==expected,'EXACT_FOUR_PATHS')
 need(m['file_count']==4 and m['directory_count']==0,'COUNTS')
 need(m['reclaim_bytes']==sum(x['metadata']['blocks']*512 for x in targets),'RECLAIM_SUM')
 need(len({(x['metadata']['dev'],x['metadata']['ino'])for x in targets})==4 and all(x['metadata']['nlink']==1 for x in targets),'HARDLINK_SCOPE')
 need(len(m['retained_local_dumps'])==4 and not({x['path']for x in m['retained_local_dumps']}&expected),'RETAINED_DUMP_SET')
 need(any('/20261117T080318-0500/'in x['path']for x in m['retained_local_dumps']),'NEWEST_LOCAL_FALLBACK')
 need(len(m['retained_reviewed_files'])==322 and not({x['path']for x in m['retained_reviewed_files']}&expected),'RETAINED_322')
 need(len(m['remote_recovery'])==5 and {x['local_path']for x in m['remote_recovery']}==expected|{str(BASE/'20261117T080318-0500/mgs_finance-before.dump')},'REMOTE_RECOVERY_SCOPE')
 expected_rows={x['path']:x for x in m['targets']+m['retained_local_dumps']}
 for x in m['remote_recovery']:
  need(x['sha256']==expected_rows[x['local_path']]['sha256'] and x['size']==expected_rows[x['local_path']]['metadata']['size'],'REMOTE_LOCAL_BINDING')
  need(bool(re.fullmatch(r'/home/zeus/mgs-finance-backups/gam-email/\d{4}-\d{2}-\d{2}-[0-9a-f]{12}-complete-[0-9a-f]{12}/mgs_finance-before\.dump',x['remote_path'])),'REMOTE_PATH')
 return True

def select_target(data,p,targets):
 return any(path.encode()in data or str(pathlib.Path(path).relative_to(APP)).encode()in data or pathlib.Path(path).parent.name.encode()in data for path in targets)
def census(targets):
 index={};full=full_code_inventory();markers=[b'finance-system',b'pglite',b'pg_version',b'mgs_finance-before.dump',b'gam-email-runs',b'pg_restore']
 for p in full:
  data=pathlib.Path(p).read_bytes();need(not select_target(data,p,targets),'NEW_TARGET_EXECUTABLE_OR_JOB_REFERENCE')
  if p.endswith('/cron/jobs.json'):
   raw=json.loads(data);jobs=raw.get('jobs',[])if isinstance(raw,dict)else raw;jobs=list(jobs.values())if isinstance(jobs,dict)else jobs
   for job in jobs:
    row={k:job[k]for k in ['id','prompt','skills','skill','script','no_agent','monitor_script','monitor_url','context_from','schedule','enabled','model','provider','base_url','workdir','deliver','origin','enabled_toolsets','failure_deliver']if k in job};body=canon(row)
    if any(x in body.lower()for x in markers):need(bool(job.get('id')),'JOB_ID');index[p+'::job::'+job['id']]=hashlib.sha256(body).hexdigest()
  elif p.startswith(str(APP)+'/')or any(x in data.lower()for x in markers):index[p]=sha(p)
 return index

def remote(m):
 for p,h in m['transport_source_hashes'].items():need(sha(p)==h,'TRANSPORT_HELPER_DRIFT')
 helper=APP/'deploy/runcloud_ops.py';tree=ast.parse(helper.read_text());nodes:list[ast.stmt]=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))or isinstance(n,ast.FunctionDef)and n.name in {'op','secret'}or isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='VAULT'for t in n.targets)]
 auth=ROOT/'scripts/mgs_google_workspace_auth.py';load=next(n for n in ast.parse(auth.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='load_env');env={'BASE':ROOT,'Path':pathlib.Path,'os':os};exec(compile(ast.fix_missing_locations(ast.Module(body=[load],type_ignores=[])),str(auth),'exec'),env);env['load_env']();need(bool(os.environ.get('OP_SERVICE_ACCOUNT_TOKEN')),'CANONICAL_SERVICE_ENV_REQUIRED')
 hns:dict[str,Any]={};exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(helper),'exec'),hns)
 prod=APP/'finance_gam_revenue_sync.py';node=next(n for n in ast.parse(prod.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='ssh');ns:dict[str,Any]={'os':os,'subprocess':subprocess,'runcloud_secret':hns['secret'],'_RUN_CLOUD_PASSWORD':None};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(prod),'exec'),ns)
 checked=[]
 for x in m['remote_recovery']:
  q=shlex.quote(x['remote_path']);command='sha256sum -- '+q+' && stat -c %s -- '+q+' && env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/pg_restore --list '+q+' >/dev/null && printf CATALOGUE_OK'
  result=ns['ssh'](command,timeout=180).splitlines();need(len(result)==3 and result[0].split()[0]==x['sha256']and int(result[1])==x['size']and result[2]=='CATALOGUE_OK','REMOTE_EXACT_CONTENT_OR_CATALOGUE')
  checked.append(x['remote_path'])
 return len(checked)

def validate(m,post=False):
 shape(m);need(sha(__file__)==m['gate_sha256'],'FROZEN_GATE_HASH');paths=[x['path']for x in m['targets']]
 for row in m['targets']:
  p=pathlib.Path(row['path']);need(p.resolve()==p and not p.is_symlink()and not os.path.ismount(p),'TARGET_PATH')
  if post:need(not os.path.lexists(p),'TARGET_STILL_PRESENT')
  else:need(meta(p)==row['metadata']and sha(p)==row['sha256'],'TARGET_CONTENT_OR_METADATA_DRIFT')
 need(not runtime_refs(paths),'PROCESS_REFERENCE');need(os.path.realpath('/root/.local/bin/hermes')==m['launcher'],'LAUNCHER_DRIFT');need(health()==m['runtime'],'RUNTIME_DRIFT')
 for row in m['retained_reviewed_files']+m['retained_local_dumps']:
  need(meta(row['path'])==row['metadata']and sha(row['path'])==row['sha256'],'RETAINED_METADATA_OR_PAYLOAD_DRIFT')
 for p,h in m['retained_evidence'].items():need(sha(p)==h,'SOURCE_RECEIPT_DRIFT')
 need(sha(m['source_census_path'])==m['source_census_sha256'],'CENSUS_INDEX_DRIFT');expected=json.load(gzip.open(m['source_census_path'],'rt'));need(census(paths)==expected,'RELEVANT_CODE_OR_JOB_DRIFT')
 checked=remote(m)
 return dict(status='PASS',post=post,targets=4,retained_reviewed=322,retained_local=4,remote_counterparts=checked,source_files_deleted=0 if not post else 4,SQL=False,DB_started=False)

def approval(a,digest,gate):
 need(a.get('author_id')=='344196393512075265'and a.get('thread_id')=='1569928464033783862'and a.get('native_message_readback_verified')is True and a.get('manifest_sha256')==digest and a.get('gate_sha256')==gate and a.get('confirmation_message_id')not in [None,'','1572257170626580601'],'NEW_EXACT_NATIVE_OWNER_APPROVAL_REQUIRED')
def audit(event,extra):
 row={'at':datetime.datetime.now().astimezone().isoformat(),'agent':'zeus','event':event,'request_message_id':'1572257170626580601',**extra}
 with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
def apply(m,digest,a):
 approval(a,digest,m['gate_sha256']);need(not(OUT/'execution-start.json').exists(),'REPLAY_BLOCKED');validate(m)
 fd=os.open(OUT/'execution-start.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w')as f:json.dump({'manifest_sha256':digest,'confirmation_message_id':a['confirmation_message_id']},f);f.flush();os.fsync(f.fileno())
 audit('four_local_remote_mirrored_dump_retirement_start',{'manifest_sha256':digest,'confirmation_message_id':a['confirmation_message_id']});deleted=[];v=os.statvfs('/');free=v.f_bavail*v.f_frsize
 try:
  for row in m['targets']:
   need(meta(row['path'])==row['metadata'],'FINAL_IDENTITY_DRIFT');os.unlink(row['path']);deleted.append(row['path'])
   with (OUT/'deletion-journal.jsonl').open('a')as f:f.write(json.dumps({'path':row['path'],'kind':'file'})+'\n');f.flush();os.fsync(f.fileno())
  v=os.statvfs('/');delta=v.f_bavail*v.f_frsize-free;post=validate(m,post=True);need(len(deleted)==4 and set(deleted)=={x['path']for x in m['targets']},'EXACT_DELETE_JOURNAL')
  result={'status':'four_paths_removed_and_retained_recovery_validated','manifest_sha256':digest,'deleted':deleted,'observed_available_delta_bytes':delta,'post_validation':post,'governance_closure_pending':True};(OUT/'filesystem-result.json').write_text(json.dumps(result,indent=2)+'\n');audit('four_local_remote_mirrored_dump_retirement_complete',{'manifest_sha256':digest,'deleted_count':4,'observed_available_delta_bytes':delta});return result
 except BaseException as e:audit('four_local_remote_mirrored_dump_retirement_partial',{'deleted':deleted,'error_type':type(e).__name__});raise

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();mf=OUT/'manifest.json';digest=(OUT/'manifest.sha256').read_text().split()[0];need(sha(mf)==digest,'MANIFEST_HASH');m=json.loads(mf.read_text())
 if args.apply:
  need((OUT/'critical-approval.json').is_file(),'NEW_EXACT_NATIVE_OWNER_APPROVAL_REQUIRED');a=json.loads((OUT/'critical-approval.json').read_text());approval(a,digest,m['gate_sha256'])
  with (OUT/'execution.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);print(json.dumps(apply(m,digest,a)))
 else:print(json.dumps(validate(m)))
if __name__=='__main__':main()
