#!/usr/bin/env python3
import os,json,subprocess,time,hashlib,re
from pathlib import Path
BASE=Path('/root/zeus-php-security-20261021-1562585423589412987')
D=BASE/'socket-recovery-1562594110655828149'
FILES={'/etc/php83rc/fpm.d/mgs-finance-dash.conf':'645d5b2ff63c4a07677a55355cd763b6a5bd97ca7f1b9d1fa2ab153818c37c2b','/etc/nginx-rc/conf.d/mgs-finance-dash.d/proxy.conf':'abe8ff28cbdf3254de8de90af6a853cc74b7a85833d97246063d76ec05298bc7'}
OLD=b'/var/run/mgs-finance-dash.sock';NEW=b'/var/run/mgs-finance-dash-php.sock'
def run(a,t=60):return subprocess.run(a,capture_output=True,text=True,timeout=t)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def states():
 out={}
 for n in ['php83rc-fpm.service','nginx-rc.service','mgs-finance-dash.service','mgs-finance-dash.socket','mgs-postgresql18.service','mariadb.service','apache2-rc.service']:
  r=run(['systemctl','show',n,'-p','ActiveState','-p','MainPID','-p','Listen']);out[n]=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
 return out
def http():
 r=run(['curl','-sS','-L','--max-redirs','4','--max-time','25','-o','/dev/null','-w','%{http_code}','https://dash.mgsdigitalcorp.com/?php_recovery='+str(time.time_ns())],35)
 return {'exit':r.returncode,'status':int(r.stdout) if r.stdout.isdigit() else 0}
def save(n,d):
 (D/(n+'.json')).write_text(json.dumps(d,indent=2));os.chmod(D/(n+'.json'),0o600)
os.umask(0o077);D.mkdir(mode=0o700,parents=True,exist_ok=True)
try:
 before=states();status=http();now={p:sha(p) for p in FILES}
 save('preflight',{'authorization':'1562594110655828149','states':before,'http':status,'hashes':now,'var_run_realpath':os.path.realpath('/var/run')})
 assert os.path.realpath('/var/run')=='/run'
 allold=all(now[p]==FILES[p] for p in FILES)
 allnew=all(NEW in Path(p).read_bytes() and OLD not in Path(p).read_bytes() for p in FILES)
 assert allold or allnew,'confirmed file fingerprint drift'
 if not allnew:
  for i,p in enumerate(FILES):
   path=Path(p);data=path.read_bytes();assert data.count(OLD)==1 and NEW not in data
   backup=D/('config-'+str(i)+'.before');backup.write_bytes(data);os.chmod(backup,0o600)
  save('mutation-start',{'time':time.time(),'authorization':'1562594110655828149','files':FILES})
  for p in FILES:
   path=Path(p);data=path.read_bytes();path.write_bytes(data.replace(OLD,NEW));assert path.read_bytes()==data.replace(OLD,NEW)
  for cmd in [['/RunCloud/Packages/php83rc/sbin/php-fpm','-t'],['/usr/local/sbin/nginx-rc','-t']]:
   r=run(cmd);assert r.returncode==0,'configuration check failed before restart'
 for cmd in [['systemctl','stop','mgs-finance-dash.service','mgs-finance-dash.socket'],['systemctl','restart','php83rc-fpm.service'],['systemctl','start','mgs-finance-dash.socket','mgs-finance-dash.service'],['systemctl','reload','nginx-rc.service']]:
  r=run(cmd);save('last-command',{'command':cmd,'exit':r.returncode,'time':time.time()});assert r.returncode==0,'service action failed: '+' '.join(cmd)
 after=states();observations=[]
 for i in range(5):
  observations.append(http())
  if observations[-1]=={'exit':0,'status':200}:break
  time.sleep(2)
 assert observations[-1]=={'exit':0,'status':200},'public dashboard not recovered'
 for unit in after:assert after[unit].get('ActiveState')=='active',unit+' inactive'
 for unit in ['mgs-postgresql18.service','mariadb.service','apache2-rc.service','nginx-rc.service']:
  assert before[unit].get('MainPID')==after[unit].get('MainPID'),'unexpected protected service restart: '+unit
 ss=run(['ss','-lxp']).stdout
 relevant=[s for s in ss.splitlines() if '/run/mgs-finance-dash.sock' in s or '/var/run/mgs-finance-dash-php.sock' in s]
 assert any('/var/run/mgs-finance-dash-php.sock' in s and 'php-fpm' in s for s in relevant),'missing isolated FPM listener'
 assert any('/run/mgs-finance-dash.sock' in s and 'node' in s for s in relevant),'missing Node listener'
 assert not any('/var/run/mgs-finance-dash.sock' in s for s in ss.splitlines()),'legacy conflicting listener remains'
 out={'authorization':'1562594110655828149','states':after,'http':observations,'hashes_after':{p:sha(p) for p in FILES},'socket_owners':relevant,'separated_sockets':True,'protected_service_pids_unchanged':True,'financial_writes':0,'time':time.time()};save('result',out);print(json.dumps({'ok':True,'result':out}))
except Exception as e:
 save('failure',{'type':type(e).__name__,'error':str(e),'time':time.time()});print(json.dumps({'ok':False,'type':type(e).__name__,'error':str(e)}));raise SystemExit(1)
