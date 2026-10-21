#!/usr/bin/env python3
import subprocess,json,os,re,shlex,urllib.request,hashlib,time
from pathlib import Path
B=Path('/root/.hermes/secure-backups/vps-maintenance/php-security-20261021-1562585423589412987')
N=['php8.3-cli','php8.3-common','php8.3-opcache','php8.3-readline'];OLD='8.3.6-0ubuntu0.24.04.12';NEW='8.3.6-0ubuntu0.24.04.13'
def run(a,t=90,cwd=None,env=None):return subprocess.run(a,capture_output=True,text=True,timeout=t,cwd=cwd,env=env)
def pkgs():
 r=run(['dpkg-query','-W','-f=${Package} ${Version}\n']+N);assert r.returncode==0;return dict(x.split() for x in r.stdout.splitlines())
def states():
 out={}
 for n in ['zeus','atena','ares']:
  r=run(['systemctl','show',n+'-gateway.service','-p','MainPID','-p','ActiveState']);out[n]=dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
 return out
def save(n,d):
 p=B/(n+'.json');p.write_text(json.dumps(d,indent=2));os.chmod(p,0o600)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
os.umask(0o077);B.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(B,0o700)
try:
 before=pkgs();assert set(before.values()).issubset({OLD,NEW}),'local prestate changed'
 gs=states();mods=run(['php','-m']);assert mods.returncode==0
 save('preflight',{'packages':before,'gateways':gs,'modules':mods.stdout,'authorization':'1562585423589412987','reboot_marker':Path('/var/run/reboot-required').exists(),'time':time.time()})
 targets=[n+'='+NEW for n in N]
 r=run(['apt-get','-s','install','--only-upgrade','--no-install-recommends']+targets)
 assert r.returncode==0,'local simulation failed'
 rows=[s for s in r.stdout.splitlines() if s.startswith(('Inst ','Remv '))]
 for s in rows:
  m=re.match(r'Inst (\S+) (?:\[([^]]+)\] )?\((\S+)',s);assert m and m.group(1) in N and m.group(3)==NEW,'local transaction scope drift'
 save('simulation',{'transaction':rows})
 debs=[]
 for n,v in before.items():
  if v!=OLD:continue
  r=run(['apt-get','--print-uris','download',n+'='+NEW]);assert r.returncode==0
  urls=[shlex.split(x)[0] for x in r.stdout.splitlines() if x.startswith("'")];assert len(urls)==1
  url=urls[0];assert NEW in url and url.startswith(('http://archive.ubuntu.com/','http://security.ubuntu.com/','https://archive.ubuntu.com/','https://security.ubuntu.com/')),'unexpected repository URI'
  prior=url.replace(NEW,OLD);p=B/(n+'_'+OLD+'_amd64.deb')
  if not p.exists():
   with urllib.request.urlopen(prior,timeout=45) as h:p.write_bytes(h.read())
  assert run(['dpkg-deb','-f',str(p),'Package']).stdout.strip()==n
  assert run(['dpkg-deb','-f',str(p),'Version']).stdout.strip()==OLD
  debs.append(p)
 arc=B/'php-config-before.tar.gz'
 if not arc.exists():assert run(['tar','-czf',str(arc),'-C','/','etc/php/8.3']).returncode==0
 assert run(['tar','-tzf',str(arc)]).returncode==0
 paths=debs+[arc];mf=B/'rollback.sha256';mf.write_text(''.join(sha(p)+'  '+str(p)+'\n' for p in paths));assert run(['sha256sum','-c',str(mf)]).returncode==0
 save('backup',{'old_debs':len(debs),'config_archive':str(arc),'checksums_valid':True})
 assert pkgs()==before and states()==gs,'concurrent local drift'
 if rows:
  save('apply-start',{'time':time.time(),'authorization':'1562585423589412987','targets':targets})
  env=os.environ.copy();env.update({'DEBIAN_FRONTEND':'noninteractive','NEEDRESTART_MODE':'l','UCF_FORCE_CONFFOLD':'1'})
  r=run(['apt-get','-y','install','--only-upgrade','--no-install-recommends','-o','Dpkg::Options::=--force-confold']+targets,240,env=env)
  (B/'install.log').write_text(r.stdout+r.stderr);save('apply-result',{'exit':r.returncode,'time':time.time()});assert r.returncode==0,'local installation failed'
 after=pkgs();assert set(after.values())=={NEW};assert states()==gs,'gateway changed during CLI update'
 assert not run(['dpkg','--audit']).stdout.strip(),'dpkg not clean'
 postmods=run(['php','-m']);assert postmods.returncode==0 and postmods.stdout==mods.stdout and not postmods.stderr,'PHP modules changed or startup warning'
 smoke=run(['php','-r','echo PHP_VERSION," ",PHP_SAPI,"\n";']);assert smoke.returncode==0 and '8.3.6 cli' in smoke.stdout
 changelog=run(['zgrep','-E','CVE-2026-109618|CVE-2026-109619','/usr/share/doc/php8.3-cli/changelog.Debian.gz']);assert 'CVE-2026-109618' in changelog.stdout and 'CVE-2026-109619' in changelog.stdout,'installed CVE changelog missing'
 out={'before':before,'after':after,'gateways_unchanged':True,'gateways':gs,'modules_unchanged':True,'php_smoke':smoke.stdout.strip(),'fixed_cves':['CVE-2026-109618','CVE-2026-109619'],'backup':str(B),'backup_validated':True,'dpkg_clean':True,'reboot_marker':Path('/var/run/reboot-required').exists(),'time':time.time()};save('validation',out);print(json.dumps({'ok':True,'result':out}))
except Exception as e:
 save('failure',{'type':type(e).__name__,'error':str(e),'time':time.time()});print(json.dumps({'ok':False,'type':type(e).__name__,'error':str(e)}));raise SystemExit(1)
