#!/usr/bin/env python3
"""Exact isolated Node executable patch; no app/DB/config writes."""
import os,sys,json,subprocess,time,hashlib,pathlib,shutil,fcntl,socket,stat
from pathlib import Path
B=Path('/root/zeus-finance-node-1562899188658864140')
R=Path('/home/mgsfinance/releases/pg-auth-1545934831664242748')
LIVE=Path('/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node')
CANDIDATE=Path('/home/mgsfinance/runtime/.node-security-1562899188658864140/node')
OLD_SHA='3517c2df0b2f8cd7f422b4b8450ef81c6889f08eb03e281d6de9079b15e6a327'
NEW_SHA='94efd062ed066c1a0b332e18249859c905e920eeada5df55d24c99b919629a90'
AUTH='1562896598286078085';EXCEPTION='1562899188658864140'
UNIT='mgs-finance-dash.service'
PROTECTED=['mgs-finance-dash.socket','mgs-postgresql18.service','mariadb.service','nginx-rc.service','php83rc-fpm.service','bitninja.service']
PGROOT='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/'
PGENV=['sudo','-n','-u','mgs_pg','env','LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu']
TABLES=['acceptance_runs','audit_events','entity_versions','finance_approvals','finance_history','finance_ledger','imports','scenarios','source_cells']
def run(a,t=90,**kw):return subprocess.run(a,capture_output=True,text=True,timeout=t,**kw)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(n,obj):
 B.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(B,0o700);p=B/(n+'.json');p.write_text(json.dumps(obj,indent=2));os.chmod(p,0o600);return obj
def unit(n):
 p=run(['systemctl','show',n,'-p','MainPID','-p','ActiveState','-p','ExecMainStartTimestamp']);return dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
def code_hashes():
 result={}
 for p in R.iterdir():
  if p.is_file() and p.suffix in ['.mjs','.py','.json','.sql']:result[str(p.relative_to(R))]=sha(p)
 for p in (R/'public').rglob('*'):
  if p.is_file():result[str(p.relative_to(R))]=sha(p)
 return result
def deps_hashes():return {str(p.relative_to(R)):sha(p) for p in (R/'node_modules').rglob('*') if p.is_file() and not p.is_symlink()}
def config_hashes():
 paths=[Path('/etc/systemd/system')/(n) for n in [UNIT,'mgs-finance-dash.socket','mgs-postgresql18.service']]
 paths+=list(Path('/etc/nginx-rc/conf.d/mgs-finance-dash.d').glob('*.conf'))+list(Path('/etc/nginx-rc/extra.d').glob('mgs-finance-dash*'))
 paths+=list(Path('/etc/php83rc/fpm.d').glob('mgs-finance-dash.conf'))
 return {str(p):sha(p) for p in paths if p.is_file()}
def financial_fingerprint():
 statements=['BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;','SET LOCAL statement_timeout=60000;']
 for name in TABLES:
  statements.append("SELECT '"+name+"',count(*),md5(coalesce(string_agg(h,'' ORDER BY h),'')) FROM (SELECT md5(row_to_json(t)::text) AS h FROM public."+name+' t) q;')
 statements.append('COMMIT;')
 p=run(PGENV+[PGROOT+'psql','-X','-qAt','-F','|','-h','/run/mgs-postgresql18','-d','mgs_finance','-v','ON_ERROR_STOP=1','-c',''.join(statements)],t=150);assert p.returncode==0,'read-only fingerprint failed'
 rows=[l.split('|') for l in p.stdout.splitlines() if l];assert len(rows)==len(TABLES)
 return {row[0]:{'rows':int(row[1]),'aggregate_row_md5':row[2]} for row in rows}
def http():
 paths=['/login','/api/scenarios','/api/health','/'];out=[]
 for path in paths:
  for origin in [False,True]:
   cmd=['curl','--silent','--show-error','--max-time','20','--output','/dev/null','--write-out','%{http_code}']
   if origin:cmd+=['--unix-socket','/run/mgs-finance-dash.sock','-H','Host: dash.mgsdigitalcorp.com'];url='http://localhost'+path
   else:url='https://dash.mgsdigitalcorp.com'+path
   p=run(cmd+[url],t=25);out.append({'path':path,'private_socket':origin,'exit':p.returncode,'status':int(p.stdout) if p.stdout.isdigit() else 0})
 return out
def running_live_consumers():
 out=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   exe=os.readlink(p/'exe')
   if exe.removesuffix(' (deleted)')==str(LIVE):out.append({'pid':int(p.name),'exe':exe,'version':run([str(p/'exe'),'--version']).stdout.strip()})
  except OSError:pass
 return out
def preflight():
 assert socket.gethostname()=='MatteiInc01' and sha(LIVE)==OLD_SHA and sha(CANDIDATE)==NEW_SHA,'runtime identity drift'
 assert not (B/'cutover-start.json').exists(),'cutover already attempted: reconcile'
 d={'authorization':AUTH,'model_exception':EXCEPTION,'time':time.time(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'app':unit(UNIT),'protected':{n:unit(n) for n in PROTECTED},'code':code_hashes(),'dependencies':deps_hashes(),'config':config_hashes(),'node_stat':{'uid':LIVE.stat().st_uid,'gid':LIVE.stat().st_gid,'mode':stat.S_IMODE(LIVE.stat().st_mode)},'node_before_sha256':sha(LIVE),'node_after_sha256':sha(CANDIDATE),'http':http(),'financial':financial_fingerprint()}
 assert d['app']['ActiveState']=='active' and all(v['ActiveState']=='active' for v in d['protected'].values()),'service baseline failed'
 assert run([str(LIVE),'--version']).stdout.strip()=='v22.23.2';assert run([str(CANDIDATE),'--version']).stdout.strip()=='v22.23.4'
 assert all(x['exit']==0 and x['status']==({'/login':200,'/api/scenarios':401,'/api/health':401,'/':303}[x['path']]) for x in d['http']),'baseline HTTP failed'
 backup=B/'node-22.23.2-before';assert not backup.exists(),'backup already exists: reconcile';shutil.copy2(LIVE,backup);assert sha(backup)==OLD_SHA
 dump=B/'mgs-finance-before-node.dump'
 with dump.open('wb') as f:
  p=subprocess.run(PGENV+[PGROOT+'pg_dump','-h','/run/mgs-postgresql18','-U','mgs_pg','-Fc','mgs_finance'],stdout=f,stderr=subprocess.PIPE,timeout=180)
 assert p.returncode==0,'database dump failed';assert run(['env','LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu',PGROOT+'pg_restore','--list',str(dump)],t=60).returncode==0,'dump catalog invalid'
 archive=B/'code-and-units-before.tar.gz';targets=[str(R/p).lstrip('/') for p in d['code']]+[p.lstrip('/') for p in d['config']]
 p=run(['tar','-czf',str(archive),'-C','/']+targets,t=120);assert p.returncode==0 and run(['tar','-tzf',str(archive)]).returncode==0,'code/config backup invalid'
 save('preflight',d);paths=[backup,dump,archive,B/'preflight.json'];p=run(['sha256sum']+[str(x) for x in paths]);assert p.returncode==0;(B/'rollback.sha256').write_text(p.stdout);assert run(['sha256sum','-c',str(B/'rollback.sha256')]).returncode==0
 return {'preflight_ok':True,'code_files':len(d['code']),'dependency_files':len(d['dependencies']),'fingerprint_tables':len(d['financial']),'http_checks':len(d['http']),'backup':str(B),'dump_bytes':dump.stat().st_size,'node_backup_sha256':sha(backup)}
def apply():
 before=json.loads((B/'preflight.json').read_text());assert before['authorization']==AUTH and before['model_exception']==EXCEPTION
 assert not (B/'cutover-start.json').exists(),'existing cutover: reconcile rather than replay'
 lock=(R/'private/release-control/files.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
 try:
  assert sha(LIVE)==OLD_SHA and sha(CANDIDATE)==NEW_SHA,'binary drift';assert code_hashes()==before['code'] and deps_hashes()==before['dependencies'] and config_hashes()==before['config'],'source/config/dependency drift'
  assert run(['sha256sum','-c',str(B/'rollback.sha256')]).returncode==0,'rollback damaged'
  consumers=running_live_consumers();assert len(consumers)==1 and consumers[0]['pid']==int(unit(UNIT)['MainPID']),'other active Node consumers: wait for their approved jobs'
  fingerprint=financial_fingerprint();save('cutover-financial-before',fingerprint)
  save('cutover-start',{'authorization':AUTH,'model_exception':EXCEPTION,'time':time.time(),'before_sha256':OLD_SHA,'after_sha256':NEW_SHA,'active_pid':unit(UNIT)['MainPID'],'scope':'only existing Node executable;legacy prefix kept,no app/config/DB changes'})
  temp=LIVE.parent/('.node-security-'+EXCEPTION);assert not temp.exists(),'staged destination already exists';shutil.copy2(CANDIDATE,temp);os.chown(temp,before['node_stat']['uid'],before['node_stat']['gid']);temp.chmod(before['node_stat']['mode']);assert sha(temp)==NEW_SHA
  os.replace(temp,LIVE);os.sync();save('binary-installed',{'time':time.time(),'sha256':sha(LIVE)})
  p=run(['systemctl','restart',UNIT],t=70);save('restart',{'exit':p.returncode,'time':time.time()});assert p.returncode==0,'service restart failed'
  after=validate(before,fingerprint);save('completion',after);return after
 except Exception as e:
  save('cutover-failure',{'type':type(e).__name__,'message':str(e),'time':time.time(),'live_sha256':sha(LIVE)})
  # Restore only our exact Node replacement, never code, data, config or a third-party binary.
  if sha(LIVE)==NEW_SHA:
   original=B/'node-22.23.2-before';assert sha(original)==OLD_SHA,'rollback file damaged';temp=LIVE.parent/('.node-rollback-'+EXCEPTION);assert not temp.exists();shutil.copy2(original,temp);os.chown(temp,before['node_stat']['uid'],before['node_stat']['gid']);temp.chmod(before['node_stat']['mode']);os.replace(temp,LIVE);p=run(['systemctl','restart',UNIT],t=70);save('rollback-result',{'exit':p.returncode,'sha256':sha(LIVE),'time':time.time(),'app':unit(UNIT),'http':http()})
  raise
 finally:lock.close()
def validate(before=None,fingerprint=None):
 if before is None:before=json.loads((B/'preflight.json').read_text())
 if fingerprint is None:fingerprint=json.loads((B/'cutover-financial-before.json').read_text())
 readiness=[];deadline=time.monotonic()+20
 while True:
  app=unit(UNIT);pid=app.get('MainPID','0');exe=None
  try:exe=os.readlink('/proc/'+pid+'/exe') if pid!='0' else None
  except OSError:pass
  version=run(['/proc/'+pid+'/exe','--version']).stdout.strip() if exe==str(LIVE) else None
  readiness.append({'time':time.time(),'pid':pid,'state':app.get('ActiveState'),'exe':exe,'version':version});save('latest-runtime-readiness',readiness)
  if app.get('ActiveState')=='active' and exe==str(LIVE) and version=='v22.23.4':break
  assert time.monotonic()<deadline,'new app executable/version did not converge';time.sleep(.1)
 assert app['MainPID']!=before['app']['MainPID'],'new app process not replaced'
 assert code_hashes()==before['code'] and deps_hashes()==before['dependencies'] and config_hashes()==before['config'],'unapproved source/dependency/config change'
 protected={n:unit(n) for n in PROTECTED}
 for n,v in protected.items():assert v['ActiveState']=='active' and v.get('MainPID')==before['protected'][n].get('MainPID'),'unapproved protected-service restart '+n
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==before['boot_id'],'unplanned reboot'
 checks=http();assert all(x['exit']==0 and x['status']==({'/login':200,'/api/scenarios':401,'/api/health':401,'/':303}[x['path']]) for x in checks),'postcutover HTTP regression'
 after=financial_fingerprint();assert after==fingerprint,'financial fingerprint changed while admission held'
 assert all(x['version']=='v22.23.4' and not x['exe'].endswith(' (deleted)') for x in running_live_consumers()),'old scoped Node process survives'
 assert run(['sha256sum','-c',str(B/'rollback.sha256')]).returncode==0,'rollback integrity failed'
 return {'authorization':AUTH,'model_exception':EXCEPTION,'time':time.time(),'status':'dashboard_node22_security_patch_completed','version':'v22.23.4','binary_path':str(LIVE),'historical_prefix_retained_for_existing_unit_and_cli_compatibility':True,'binary_sha256':sha(LIVE),'app_pid':int(app['MainPID']),'previous_app_pid':int(before['app']['MainPID']),'code_files_unchanged':len(before['code']),'dependency_files_unchanged':len(before['dependencies']),'config_unchanged':True,'financial_tables_fingerprint_unchanged':len(after),'financial_writes':0,'protected_service_pids_unchanged':True,'boot_unchanged':True,'http_checks':checks,'rollback_verified':True,'backup':str(B)}
if __name__=='__main__':
 try:print(json.dumps({'ok':True,'result':{'preflight':preflight,'apply':apply,'validate':validate}[sys.argv[1]]()}))
 except Exception as e:save('failure-'+sys.argv[1],{'type':type(e).__name__,'error':str(e),'time':time.time()});print(json.dumps({'ok':False,'type':type(e).__name__,'error':str(e)}));raise SystemExit(1)
