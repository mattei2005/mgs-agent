#!/usr/bin/env python3
"""Confirmed Hestia PHP patch only; never reboots or changes credentials."""
import os,sys,json,re,time,subprocess,hashlib,socket,glob,stat,tarfile,concurrent.futures
from pathlib import Path
BASE=Path('/root/zeus-hestia-php-security-1562888441400664176')
AUTH='1562888441400664176'
CORE=['php8.3','php8.3-bcmath','php8.3-bz2','php8.3-cli','php8.3-common','php8.3-curl','php8.3-fpm','php8.3-gd','php8.3-imap','php8.3-intl','php8.3-ldap','php8.3-mbstring','php8.3-mysql','php8.3-opcache','php8.3-pspell','php8.3-readline','php8.3-soap','php8.3-xml','php8.3-zip']
NEW={n:'8.3.36-1+ubuntu24.04.1+deb.sury.org+1' for n in CORE};NEW['hestia-php']='8.5.12-1+ubuntu24.04'
OLD={n:'8.3.31-3+ubuntu24.04.1+deb.sury.org+1' for n in CORE};OLD['hestia-php']='8.5.9-1+ubuntu24.04'
UNITS=['php8.3-fpm.service','hestia.service','nginx.service','exim4.service','dovecot.service','mariadb.service','cron.service']
def run(a,timeout=90,cwd=None,env=None):return subprocess.run(a,capture_output=True,text=True,timeout=timeout,cwd=cwd,env=env)
def save(n,d):
 BASE.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(BASE,0o700)
 p=BASE/(n+'.json');p.write_text(json.dumps(d,indent=2));os.chmod(p,0o600);return d
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def packages():
 p=run(['dpkg-query','-W','-f=${Package}\t${Version}\t${Status}\n']+list(NEW));assert p.returncode==0,'dpkg query failed'
 return {a.split('\t')[0]:a.split('\t')[1] for a in p.stdout.splitlines() if 'install ok installed' in a}
def service(n):
 p=run(['systemctl','show',n,'-p','MainPID','-p','ActiveState','-p','UnitFileState','-p','ExecMainStartTimestamp'])
 return dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
def processes():
 out=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   exe=os.readlink(p/'exe');cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace').strip()
   if Path(exe.removesuffix(' (deleted)')).name in ['php-fpm8.3','hestia-php']:out.append({'pid':int(p.name),'exe':exe,'cmd':cmd})
  except OSError:pass
 return out
def config_files():
 out=set()
 for root in ['/etc/php/8.3','/usr/local/hestia/php/etc','/etc/nginx','/etc/roundcube','/etc/hestiacp','/usr/local/hestia/conf']:
  p=Path(root)
  if p.exists():out.update(str(f) for f in p.rglob('*') if f.is_file() and not f.is_symlink())
 for root in Path('/home').glob('*/conf'):
  out.update(str(f) for f in root.rglob('*') if f.is_file() and not f.is_symlink())
 return sorted(out)
def config_hashes():return {p:sha(p) for p in config_files()}
def domains():
 out=set()
 for f in Path('/etc/nginx/conf.d/domains').glob('*.conf'):
  text=f.read_text(errors='replace')
  for line in re.findall(r'^\s*server_name\s+([^;]+);',text,re.M):
   for h in line.split():
    if re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}',h) and not h.startswith('www.'):out.add(h)
 return sorted(out)
def probe(arg):
 host,origin,panel=arg;port=8083 if panel else 443;url='https://'+host+(':'+str(port) if panel else '')+('/login/' if panel else '/?mgs_php_patch='+str(time.time_ns()))
 cmd=['curl','--silent','--show-error','--location','--max-redirs','4','--connect-timeout','6','--max-time','22','--max-filesize','3145728','--user-agent','MGS-PHP-Security-Validation/1.0','--write-out','\nMGSSTATUS:%{http_code}']
 if origin:cmd+=['--insecure','--resolve',host+':'+str(port)+':188.34.183.6']
 p=run(cmd+[url],timeout=28);body,_,code=p.stdout.rpartition('\nMGSSTATUS:')
 return {'host':host,'origin':origin,'panel':panel,'exit':p.returncode,'status':int(code) if code.isdigit() else 0,'bytes':len(body),'php_fatal':bool(re.search('PHP Fatal error|Fatal error:|Parse error:',body)),'roundcube':bool(re.search('Roundcube Webmail|name="_user"',body,re.I)),'hestia_login':bool(re.search('name="user"|name="username"|id="username"|Hestia Control Panel',body,re.I))}
def probes():
 jobs=[(h,o,False) for h in domains() for o in [False,True]]+ [('server.boostingecon.com',o,True) for o in [False,True]]
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:return list(ex.map(probe,jobs))
def socket_gate():
 listeners=run(['ss','-lxp']).stdout;conf=[]
 for root in ['/etc/php/8.3/fpm/pool.d','/usr/local/hestia/php/etc']:
  for f in Path(root).rglob('*.conf'):
   for path in re.findall(r'^\s*listen\s*=\s*([^;\s]+)',f.read_text(errors='replace'),re.M):
    if path.startswith('/'):
     path=os.path.realpath(path);conf.append({'file':str(f),'socket':path})
 sockets=[r['socket'] for r in conf];assert len(sockets)==len(set(sockets)),'duplicate configured PHP socket'
 for row in conf:
  hits=[l for l in listeners.splitlines() if row['socket'] in l or row['socket'].replace('/run/','/var/run/',1) in l]
  assert all('php-fpm8.3' in l or 'hestia-php' in l for l in hits),'PHP socket collides with other application'
 return conf
def collect(with_http=True):
 sv={n:service(n) for n in UNITS};ps=processes();versions={e:run([e,'-v']).stdout.splitlines()[0] for e in sorted(set(p['exe'] for p in ps)) if not e.endswith(' (deleted)')}
 v=run(['/usr/bin/php8.3','-m']);fp=run(['/usr/sbin/php-fpm8.3','-t']);hp=run(['/usr/local/hestia/php/sbin/hestia-php','-t']);ng=run(['/usr/sbin/nginx','-t'])
 return {'time':time.time(),'host':socket.gethostname(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'kernel':os.uname().release,'packages':packages(),'services':sv,'processes':ps,'versions':versions,'modules':v.stdout.splitlines(),'config_hashes':config_hashes(),'config_ok':{'web_php':fp.returncode==0,'panel_php':hp.returncode==0,'nginx':ng.returncode==0},'socket_gate':socket_gate(),'dpkg_audit':run(['dpkg','--audit']).stdout,'failed_units':run(['systemctl','--failed','--no-legend','--plain']).stdout,'http':probes() if with_http else [],'available_bytes':os.statvfs('/').f_bavail*os.statvfs('/').f_frsize,'reboot_required':Path('/var/run/reboot-required').exists()}
def simulate():
 p=run(['apt-get','-s','install','--only-upgrade','--no-install-recommends']+[n+'='+v for n,v in NEW.items()]);assert p.returncode==0,'APT simulation failed'
 rows=[l for l in p.stdout.splitlines() if l.startswith(('Inst ','Remv '))];seen={}
 for l in rows:
  assert l.startswith('Inst '),'unexpected removal'
  m=re.match(r'Inst (\S+) (?:\[([^]]+)\] )?\((\S+)',l);assert m,'unparsed transaction';seen[m[1]]=m[3]
 assert seen==NEW,'transaction scope drift'
 return rows
def preflight():
 assert not (BASE/'apply-start.json').exists(),'apply already attempted: reconcile receipt'
 u=run(['apt-get','update'],timeout=150);assert u.returncode==0 and not re.search(r'^(W:|E:|Err:)',u.stdout+'\n'+u.stderr,re.M),'repository refresh failed'
 d=collect();assert d['packages']==OLD,'installed version drift';d['simulation']=simulate();assert not d['dpkg_audit'] and not d['failed_units'],'unhealthy baseline';assert all(d['config_ok'].values()),'invalid configuration';assert d['available_bytes']>1500000000,'backup headroom insufficient'
 assert all(s['ActiveState']=='active' for s in d['services'].values()),'inactive baseline service'
 save('preflight',d);return {'preflight_ok':True,'packages':len(NEW),'http_checks':len(d['http']),'domains':domains(),'http_issues':[r for r in d['http'] if r['exit'] or r['status']>=400],'available_bytes':d['available_bytes']}
def backup():
 b=json.loads((BASE/'preflight.json').read_text());assert packages()==OLD and config_hashes()==b['config_hashes'],'prestate changed'
 paths=set(config_files());missing=[]
 for n in NEW:
  p=run(['dpkg-query','-L',n]);assert p.returncode==0,'payload enumeration failed'
  for l in p.stdout.splitlines():
   if not l.startswith('/'):
    assert re.match(r'^(?:locally )?diverted (?:by .+ )?to:',l),'unrecognized dpkg list row';continue
   if l in ['/','/.']:continue
   f=Path(l)
   if f.is_symlink() or f.is_file():paths.add(l)
   elif not f.exists():missing.append(l)
  paths.update(str(p) for p in Path('/var/lib/dpkg/info').glob(n+'.*') if p.is_file() or p.is_symlink())
 manifest=[]
 for name in sorted(paths):
  f=Path(name);s=f.lstat();assert not stat.S_ISDIR(s.st_mode),'directory in payload allowlist'
  manifest.append({'path':name,'symlink':os.readlink(f) if f.is_symlink() else None,'sha256':sha(f) if not f.is_symlink() else None,'size':s.st_size})
 logical=sum(x['size'] for x in manifest);assert logical<700000000 and b['available_bytes']>logical*3+500000000,'backup size gate'
 save('payload-manifest',manifest);lst=BASE/'payload-paths.null';lst.write_bytes(b''.join(x['path'].lstrip('/').encode()+b'\0' for x in manifest));archive=BASE/'installed-payload-and-config-before.tar.gz';assert not archive.exists(),'backup already exists: reconcile'
 p=run(['tar','--no-recursion','--null','-czf',str(archive),'-C','/','-T',str(lst)],timeout=150);assert p.returncode==0,'strict payload archive failed'
 with tarfile.open(archive,'r:gz') as tf:
  members=tf.getmembers();assert len(members)==len(manifest),'archive count mismatch';assert {m.name for m in members}=={x['path'].lstrip('/') for x in manifest},'archive membership mismatch'
  bypath={x['path'].lstrip('/'):x for x in manifest}
  for m in members:
   x=bypath[m.name]
   if m.issym():assert m.linkname==x['symlink'],'symlink mismatch'
   elif m.isfile():
    h=hashlib.sha256();f=tf.extractfile(m)
    for z in iter(lambda:f.read(1048576),b''):h.update(z)
    assert h.hexdigest()==x['sha256'],'archive payload mismatch'
   elif m.islnk():assert m.linkname in bypath,'unknown hardlink target'
   else:raise AssertionError('unexpected archive entry')
 p=run(['sha256sum',str(archive),str(BASE/'payload-manifest.json'),str(BASE/'preflight.json')]);assert p.returncode==0;(BASE/'rollback.sha256').write_text(p.stdout);assert run(['sha256sum','-c',str(BASE/'rollback.sha256')]).returncode==0
 newdir=BASE/'new-debs';newdir.mkdir(mode=0o700,exist_ok=True)
 p=run(['apt-get','download']+[n+'='+v for n,v in NEW.items()],timeout=180,cwd=newdir);(BASE/'download.log').write_text(p.stdout+p.stderr);assert p.returncode==0,'new package download failed'
 seen={};scripts=[]
 for deb in newdir.glob('*.deb'):
  n=run(['dpkg-deb','-f',str(deb),'Package']).stdout.strip();v=run(['dpkg-deb','-f',str(deb),'Version']).stdout.strip();assert NEW.get(n)==v,'download package mismatch';seen[n]=v
  scripts.append({'package':n,'bytes':deb.stat().st_size,'sha256':sha(deb)})
 assert seen==NEW,'download coverage mismatch';save('new-packages',scripts)
 return save('backup',{'authorization':AUTH,'rollback_type':'strict installed payload/config plus dpkg package-info archive; not original vendor DEBs','archive':str(archive),'archive_bytes':archive.stat().st_size,'members':len(manifest),'logical_bytes':logical,'missing_package_paths':missing,'hashes_and_archive_payload_validated':True,'new_package_count':len(seen)})
def apply():
 assert not (BASE/'apply-start.json').exists(),'non-idempotent apply already attempted: reconcile'
 b=json.loads((BASE/'preflight.json').read_text());back=json.loads((BASE/'backup.json').read_text());assert back['hashes_and_archive_payload_validated'];assert run(['sha256sum','-c',str(BASE/'rollback.sha256')]).returncode==0
 assert packages()==OLD and config_hashes()==b['config_hashes'],'state changed after confirmation';simulate();socket_gate()
 assert run(['sha256sum','-c',str(BASE/'reconstructed-rollback.sha256')]).returncode==0,'reconstructed DEB rollback damaged'
 assert len(json.loads((BASE/'reconstructed-rollback.json').read_text()))==len(NEW),'rollback coverage incomplete'
 for x in json.loads((BASE/'new-packages.json').read_text()):
  matches=[f for f in (BASE/'new-debs').glob('*.deb') if sha(f)==x['sha256']];assert len(matches)==1,'candidate artifact damaged'
 start=time.time();save('apply-start',{'authorization':AUTH,'time':start,'targets':NEW})
 env=os.environ.copy();env.update({'DEBIAN_FRONTEND':'noninteractive','NEEDRESTART_MODE':'l','UCF_FORCE_CONFFOLD':'1'})
 p=run(['apt-get','-y','install','--only-upgrade','--no-install-recommends','-o','Dpkg::Options::=--force-confold']+[n+'='+v for n,v in NEW.items()],timeout=270,env=env);(BASE/'install.log').write_text(p.stdout+p.stderr);save('install-result',{'exit':p.returncode,'time':time.time(),'packages':packages()});assert p.returncode==0,'install failed; preserve receipt'
 assert packages()==NEW,'postinstall version mismatch';assert run(['/usr/sbin/php-fpm8.3','-t']).returncode==0 and run(['/usr/local/hestia/php/sbin/hestia-php','-t']).returncode==0,'postinstall config test failed';socket_gate()
 restarts={}
 for n in ['php8.3-fpm.service','hestia.service']:
  p=run(['systemctl','restart',n],timeout=65);restarts[n]=p.returncode;save('restart-results',restarts);assert p.returncode==0,'service restart failed'
 return {'installed':True,'package_count':len(NEW),'restarts':restarts,'started':start}
def validate():
 b=json.loads((BASE/'preflight.json').read_text());a=collect();save('postcheck',a)
 assert a['packages']==NEW,'wrong packages';assert all(a['config_ok'].values()),'configuration invalid';assert not a['dpkg_audit'] and not a['failed_units'],'dpkg/systemd unhealthy'
 assert a['modules']==b['modules'],'PHP module set changed';assert a['boot_id']==b['boot_id'],'unplanned reboot'
 for n,s in a['services'].items():
  assert s['ActiveState']=='active','inactive service '+n
  if n not in ['php8.3-fpm.service','hestia.service']:assert s['MainPID']==b['services'][n]['MainPID'],'unapproved service restart '+n
 assert a['services']['php8.3-fpm.service']['MainPID']!=b['services']['php8.3-fpm.service']['MainPID'],'FPM not replaced'
 assert not any(p['exe'].endswith(' (deleted)') for p in a['processes']),'old deleted PHP process';assert all('8.3.36' in v if 'php-fpm8.3' in e else '8.5.12' in v for e,v in a['versions'].items()),'runtime version wrong'
 before={(r['host'],r['origin'],r['panel']):r for r in b['http']};reg=[]
 for r in a['http']:
  old=before[(r['host'],r['origin'],r['panel'])]
  if old['exit']==0 and old['status']<500 and (r['exit']!=0 or r['status']>=500 or r['php_fatal']):reg.append({'before':old,'after':r})
  if old['roundcube'] and not r['roundcube']:reg.append({'lost_roundcube':r})
 drift=[p for p in set(b['config_hashes'])|set(a['config_hashes']) if b['config_hashes'].get(p)!=a['config_hashes'].get(p)]
 assert not reg,'HTTP regression';assert not drift,'unexpected configuration drift';assert run(['sha256sum','-c',str(BASE/'rollback.sha256')]).returncode==0,'rollback damaged'
 pending=run(['apt-get','-s','install','--only-upgrade','--no-install-recommends']+[n+'='+v for n,v in NEW.items()]);assert pending.returncode==0 and not any(l.startswith(('Inst ','Remv ')) for l in pending.stdout.splitlines()),'selected transaction not settled'
 start=json.loads((BASE/'apply-start.json').read_text())['time'];journal=run(['journalctl','--since','@'+str(int(start)),'-p','0..3','--no-pager','-o','short-iso'])
 errors=[l for l in journal.stdout.splitlines() if l and not l.startswith('--')];save('post-journal',{'errors':errors})
 result={'authorization':AUTH,'status':'php_patched_validated','time':time.time(),'versions':a['versions'],'packages':a['packages'],'http_checks':len(a['http']),'http_issues':[r for r in a['http'] if r['exit'] or r['status']>=400],'regressions':reg,'configuration_drift':drift,'protected_service_pids_unchanged':True,'old_php_processes':0,'rollback_validated':True,'journal_error_count':len(errors),'reboot_required':a['reboot_required'],'backup':str(BASE)}
 save('validation',result);return result
if __name__=='__main__':
 try:
  phase=sys.argv[1];result={'preflight':preflight,'backup':backup,'apply':apply,'validate':validate}[phase]();print(json.dumps({'ok':True,'result':result}))
 except Exception as e:
  save('failure-'+(sys.argv[1] if len(sys.argv)>1 else 'unknown'),{'type':type(e).__name__,'message':str(e),'time':time.time()});raise
