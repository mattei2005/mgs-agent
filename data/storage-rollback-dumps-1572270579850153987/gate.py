"""Frozen29-file historical local-copy gate. No SQL, DB startup or mutation without exact approval."""
import argparse,ast,collections,datetime,fcntl,gzip,hashlib,json,os,pathlib,re,shlex,stat,subprocess,time
from typing import Any
ROOT=pathlib.Path('/root/mgs-agent');APP=ROOT/'apps/finance-system';OUT=pathlib.Path(__file__).parent;BASE=APP/'private/gam-email-runs'
TARGET_PATHS={'/root/mgs-agent/apps/finance-system/private/growpowerhub-1554828914424156170/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/br-car-1564993480487342243/catalog-backup/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/sms-dashboard-1557763144762269717/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/annual-1556874856446951425/finance-before.dump', '/root/mgs-agent/apps/finance-system/private/columns-1555702482557075539/finance-before.dump', '/root/mgs-agent/apps/finance-system/private/sb-tech-cad-1547697182948458611/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/composition-1555934054132486275/finance-before.dump', '/root/mgs-agent/apps/finance-system/private/wavesbee-1553019425706217652/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/expense-charges-1553040522287784077/backup/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/noindex-1555943137128751176/finance-before.dump', '/root/mgs-agent/apps/finance-system/private/recovery-1566802212548517990/finance-before.dump', '/root/mgs-agent/apps/finance-system/private/composition-style-1556369322782232598/finance-before.dump', '/root/mgs-agent/apps/finance-system/private/oct01-1555562222023999501/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/gam-close-1551587001629937686/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/proxy-addr-1556897466652037131/finance-before.dump', '/root/mgs-agent/apps/finance-system/private/rate-propagation-1552079131628281897/before.dump', '/root/mgs-agent/apps/finance-system/private/spend-repair-1553386505639165953/backup/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/network-month-1552101423754514465/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/columns-default-1555736746409459743/finance-before.dump', '/root/mgs-agent/apps/finance-system/private/save-perf-1552071425156845749/before.dump', '/root/mgs-agent/apps/finance-system/private/wavesbee-1553019425706217652/expenses-backup/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/quote-fix-1552011536011108493/before.dump', '/root/mgs-agent/apps/finance-system/private/prevention-release-1551755722700624003/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/shein-sites-1557024816031342732/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/spyflix-credit-1553049180434604103/backup/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/sms-residual-1557401256098664584/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/expense-save-1552090743085076510/mgs_finance-before.dump', '/root/mgs-agent/apps/finance-system/private/month-prune-1556898264878419969/finance-before.dump', '/root/mgs-agent/apps/finance-system/private/openzed-icaro-1551714950781866035/mgs_finance-before.dump'}
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
 need(m['request_message_id']=='1572270579850153987'and m['status']=='frozen_awaiting_exact_critical_confirmation','REQUEST_OR_STATUS')
 targets=m['targets'];expected=TARGET_PATHS
 need(len(targets)==29 and {x['path']for x in targets}==expected,'EXACT_29_PATHS');need(m['file_count']==29 and m['directory_count']==0,'COUNTS')
 need(m['reclaim_bytes']==sum(x['metadata']['blocks']*512 for x in targets),'RECLAIM_SUM')
 need(len({(x['metadata']['dev'],x['metadata']['ino'])for x in targets})==29 and all(x['metadata']['nlink']==1 for x in targets),'HARDLINK_SCOPE')
 need(len(m['retained_local_dumps'])==4 and not({x['path']for x in m['retained_local_dumps']}&expected),'RETAINED_DUMP_SET')
 latest=str(APP/'private/gam-email-runs/20261117T080318-0500/mgs_finance-before.dump');need(any(x['path']==latest for x in m['retained_local_dumps']),'NEWEST_LOCAL_FALLBACK')
 need(len(m['retained_reviewed_files'])==293 and not({x['path']for x in m['retained_reviewed_files']}&expected),'RETAINED_293')
 need(len(m['remote_recovery'])==30 and {x['local_path']for x in m['remote_recovery']}==expected|{latest},'REMOTE_RECOVERY_SCOPE')
 expected_rows={x['path']:x for x in targets+m['retained_local_dumps']}
 for x in m['remote_recovery']:
  need(x['sha256']==expected_rows[x['local_path']]['sha256']and x['size']==expected_rows[x['local_path']]['metadata']['size'],'REMOTE_LOCAL_BINDING')
  remote=pathlib.PurePosixPath(x['remote_path']);need(str(remote).startswith('/home/zeus/mgs-finance-backups/')and '..'not in remote.parts and re.fullmatch(r'[A-Za-z0-9_./-]+\.dump',str(remote)),'REMOTE_PATH')
 return True


def select_target(data,p,targets):
 for target in targets:
  t=pathlib.Path(target);ids=re.findall(r'\d{17,20}',str(t));owner=ids[-1]if ids else None
  if t.as_posix().encode()in data or t.relative_to(APP).as_posix().encode()in data:return True
  if owner and(owner in p or owner.encode()in data)and re.search(re.escape(t.name.encode())+rb'(?![A-Za-z0-9_.-])',data):return True
 return False

def census(targets,allowed=None):
 allowed=allowed or {};index={};full=full_code_inventory();markers=[b'finance-system',b'pglite',b'pg_version',b'mgs_finance-before.dump',b'gam-email-runs',b'pg_restore',b'finance-before.dump']
 for p in full:
  data=pathlib.Path(p).read_bytes();digest=hashlib.sha256(data).hexdigest()
  if select_target(data,p,targets):need(allowed.get(p)==digest,'NEW_OR_CHANGED_TARGET_REFERENCE')
  if p.endswith('/cron/jobs.json'):
   raw=json.loads(data);jobs=raw.get('jobs',[])if isinstance(raw,dict)else raw;jobs=list(jobs.values())if isinstance(jobs,dict)else jobs
   for job in jobs:
    row={k:job[k]for k in ['id','prompt','skills','skill','script','no_agent','monitor_script','monitor_url','context_from','schedule','enabled','model','provider','base_url','workdir','deliver','origin','enabled_toolsets','failure_deliver']if k in job};body=canon(row)
    if any(x in body.lower()for x in markers):need(bool(job.get('id')),'JOB_ID');index[p+'::job::'+job['id']]=hashlib.sha256(body).hexdigest()
  elif p.startswith(str(APP)+'/')or any(x in data.lower()for x in markers):index[p]=digest
 return index


def remote(m):
 import importlib.util
 for p,h in m['transport_source_hashes'].items():need(sha(p)==h,'TRANSPORT_HELPER_DRIFT')
 need(sha(m['ram_reader_path'])==m['ram_reader_sha256'],'RAM_READER_DRIFT')
 for p,h in m['ram_reader_dependency_hashes'].items():need(sha(p)==h,'RAM_READER_DEPENDENCY_DRIFT')
 spec=importlib.util.spec_from_file_location('frozen_retained_reader',m['ram_reader_path']);need(spec is not None and spec.loader is not None,'RAM_READER_IMPORT');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader);transport,_=reader.bootstrap();checked=[]
 for x in m['remote_recovery']:
  prefix='sudo -n 'if x['remote_path']=='/home/zeus/mgs-finance-backups/month-prune-1556898264878419969/finance-before.dump'else'';q=shlex.quote(x['remote_path'])
  command=prefix+'sha256sum -- '+q+' && '+prefix+'stat -c %s -- '+q+' && '+prefix+'env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/pg_restore --list '+q+' >/dev/null && printf CATALOGUE_OK'
  result=transport(command,timeout=180).decode().splitlines();need(len(result)==3 and result[0].split()[0]==x['sha256']and int(result[1])==x['size']and result[2]=='CATALOGUE_OK','REMOTE_EXACT_CONTENT_OR_CATALOGUE');checked.append(x['remote_path'])
 return len(checked)


def validate(m,post=False):
 shape(m);need(sha(__file__)==m['gate_sha256'],'FROZEN_GATE_HASH');paths=[x['path']for x in m['targets']]
 for row in m['targets']:
  p=pathlib.Path(row['path']);need(p.resolve()==p and not p.is_symlink()and not os.path.ismount(p),'TARGET_PATH')
  if post:need(not os.path.lexists(p),'TARGET_STILL_PRESENT')
  else:
   need(meta(p)==row['metadata']and sha(p)==row['sha256'],'TARGET_CONTENT_OR_METADATA_DRIFT');need(not os.listxattr(p,follow_symlinks=False),'UNCLASSIFIED_TARGET_XATTR')
 for p,expected in m['retained_parent_directories'].items():
  s=os.lstat(p);need(stat.S_ISDIR(s.st_mode)and not pathlib.Path(p).is_symlink(),'PARENT_DIRECTORY_REQUIRED');need(dict(dev=s.st_dev,ino=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)==expected,'PARENT_DIRECTORY_DRIFT')
 need(not runtime_refs(paths),'PROCESS_REFERENCE');need(os.path.realpath('/root/.local/bin/hermes')==m['launcher'],'LAUNCHER_DRIFT');need(health()==m['runtime'],'RUNTIME_DRIFT')
 union={}
 for row in m['retained_reviewed_files']+m['retained_local_dumps']:
  if row['path']in union:need(row['metadata']==union[row['path']]['metadata']and row['sha256']==union[row['path']]['sha256'],'RETAINED_BINDING_CONFLICT')
  union[row['path']]=row
 need(len(union)==294,'RETAINED_UNION_COUNT')
 for row in union.values():need(meta(row['path'])==row['metadata']and sha(row['path'])==row['sha256'],'RETAINED_METADATA_OR_PAYLOAD_DRIFT')
 for p,h in m['retained_evidence'].items():need(sha(p)==h,'SOURCE_RECEIPT_DRIFT')
 need(sha(m['source_census_path'])==m['source_census_sha256'],'CENSUS_INDEX_DRIFT');expected=json.load(gzip.open(m['source_census_path'],'rt'));need(census(paths,m['allowed_reference_sources'])==expected,'RELEVANT_CODE_OR_JOB_DRIFT')
 need(sha(m['ram_pre_proof_path'])==m['ram_pre_proof_sha256'],'RAM_PROOF_INDEX_DRIFT')
 proof=[json.loads(line)for line in pathlib.Path(m['ram_pre_proof_path']).read_text().splitlines()];need(len(proof)==29 and {x['path']for x in proof}==set(paths),'RAM_PROOF_SCOPE');expect={r['path']:r for r in m['targets']}
 need(all(x['actual_recovered_sha256']==expect[x['path']]['sha256']and x['size']==expect[x['path']]['metadata']['size']and x['source_payload_reads']==0 and x['real_file_materialized_in_anonymous_RAM']is True for x in proof),'RAM_PROOF_BINDING')
 checked=remote(m)
 return dict(status='PASS',post=post,targets=29,retained_reviewed=293,retained_local=4,remote_counterparts=checked,source_files_deleted=0 if not post else 29,SQL=False,DB_started=False)

def approval(a,digest,gate):
 need(a.get('author_id')=='344196393512075265'and a.get('thread_id')=='1569928464033783862'and a.get('native_message_readback_verified')is True and a.get('manifest_sha256')==digest and a.get('gate_sha256')==gate and a.get('confirmation_message_id')not in [None,'','1572270579850153987'],'NEW_EXACT_NATIVE_OWNER_APPROVAL_REQUIRED')
def audit(event,extra):
 row={'at':datetime.datetime.now().astimezone().isoformat(),'agent':'zeus','event':event,'request_message_id':'1572270579850153987',**extra}
 with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
def apply(m,digest,a):
 approval(a,digest,m['gate_sha256']);need(not(OUT/'execution-start.json').exists(),'REPLAY_BLOCKED');validate(m)
 fd=os.open(OUT/'execution-start.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w')as f:json.dump({'manifest_sha256':digest,'confirmation_message_id':a['confirmation_message_id']},f);f.flush();os.fsync(f.fileno())
 audit('historical_rollback_local_dump_retirement_start',{'manifest_sha256':digest,'confirmation_message_id':a['confirmation_message_id']});deleted=[];v=os.statvfs('/');free=v.f_bavail*v.f_frsize
 try:
  for row in m['targets']:
   need(meta(row['path'])==row['metadata'],'FINAL_IDENTITY_DRIFT');os.unlink(row['path']);deleted.append(row['path'])
   with (OUT/'deletion-journal.jsonl').open('a')as f:f.write(json.dumps({'path':row['path'],'kind':'file'})+'\n');f.flush();os.fsync(f.fileno())
  v=os.statvfs('/');delta=v.f_bavail*v.f_frsize-free;post=validate(m,post=True);need(len(deleted)==29 and set(deleted)=={x['path']for x in m['targets']},'EXACT_DELETE_JOURNAL')
  result={'status':'29_paths_removed_hash_catalogue_validated_post_RAM_replay_pending','manifest_sha256':digest,'deleted':deleted,'observed_available_delta_bytes':delta,'post_validation':post,'governance_closure_pending':True};(OUT/'filesystem-result.json').write_text(json.dumps(result,indent=2)+'\n');audit('historical_rollback_local_dump_retirement_complete',{'manifest_sha256':digest,'deleted_count':29,'observed_available_delta_bytes':delta});return result
 except BaseException as e:audit('historical_rollback_local_dump_retirement_partial',{'deleted':deleted,'error_type':type(e).__name__});raise

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();mf=OUT/'manifest.json';digest=(OUT/'manifest.sha256').read_text().split()[0];need(sha(mf)==digest,'MANIFEST_HASH');m=json.loads(mf.read_text())
 if args.apply:
  need((OUT/'critical-approval.json').is_file(),'NEW_EXACT_NATIVE_OWNER_APPROVAL_REQUIRED');a=json.loads((OUT/'critical-approval.json').read_text());approval(a,digest,m['gate_sha256'])
  with (OUT/'execution.lock').open('a')as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);print(json.dumps(apply(m,digest,a)))
 else:print(json.dumps(validate(m)))
if __name__=='__main__':main()
