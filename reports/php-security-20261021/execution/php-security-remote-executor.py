#!/usr/bin/env python3
"""Scoped PHP security executor; readback receipts never include secrets."""
import os, sys, json, subprocess, hashlib, pathlib, re, time, concurrent.futures, socket, struct
P=pathlib.Path
BASE=P('/root/zeus-php-security-20261021-1562585423589412987')
OLD='8.3.33-1+ubuntu22.04+1'; NEW='8.3.36-1+ubuntu22.04+1'
NAMES=['php83rc','php83rc-bcmath','php83rc-common','php83rc-compression','php83rc-curl','php83rc-essentials','php83rc-gd','php83rc-imap','php83rc-intl','php83rc-mbstring','php83rc-mysql','php83rc-mysqli','php83rc-opcache','php83rc-process','php83rc-pspell','php83rc-realpath-turbo','php83rc-soap','php83rc-sodium','php83rc-sqlite','php83rc-tidy','php83rc-xml']
AUTH='1562585423589412987'
def run(cmd,timeout=90,env=None,cwd=None):
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,env=env,cwd=cwd)
 return p

def save(name,obj):
 BASE.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(BASE,0o700)
 p=BASE/(name+'.json');p.write_text(json.dumps(obj,indent=2));os.chmod(p,0o600)
 return obj

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def packages():
 r=run(['dpkg-query','-W','-f=${Package} ${Version} ${Status}\n']+NAMES)
 assert r.returncode==0,'dpkg-query failed'
 d={s.split()[0]:s.split()[1] for s in r.stdout.splitlines() if 'install ok installed' in s}
 assert set(d)==set(NAMES),'package inventory mismatch'
 return d

def service(unit):
 r=run(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','ExecMainStartTimestamp'])
 return dict(s.split('=',1) for s in r.stdout.splitlines() if '=' in s)

def config_hashes():
 d={}
 for root in ['/etc/php83rc','/etc/nginx-rc']:
  for p in P(root).rglob('*'):
   if p.is_file() and p.suffix in ('.conf','.ini'):
    d[str(p)]=sha(p)
 return d

def inventory():
 apps=[]
 for pool in sorted(P('/etc/php83rc/fpm.d').glob('*.conf')):
  text=pool.read_text(errors='replace');sections=re.findall(r'^\s*\[([^]]+)\]\s*$',text,re.M)
  sections=[s for s in sections if s!='global']
  if not sections:continue
  assert len(sections)==1,'multiple pools per file'
  name=sections[0];assert re.fullmatch(r'[A-Za-z0-9_.-]+',name),'invalid pool name'
  sock=re.search(r'^\s*listen\s*=\s*([^;\s]+)',text,re.M)
  domain_dir=P('/etc/nginx-rc/conf.d')/(name+'.domains.d');domains=[]
  for cf in sorted(domain_dir.glob('*.conf')):
   for line in re.findall(r'^\s*server_name\s+([^;]+);',cf.read_text(errors='replace'),re.M):
    for h in line.split():
     if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}',h) and not h.startswith('www.') and h not in domains: domains.append(h)
  main=P('/etc/nginx-rc/conf.d')/(name+'.d/main.conf');root=None
  if main.exists():
   m=re.search(r'^\s*root\s+([^;]+);',main.read_text(errors='replace'),re.M)
   if m:root=m.group(1).strip().strip('"')
  if not root:
   candidates=list(P('/home').glob('*/webapps/'+name))
   if len(candidates)==1:root=str(candidates[0])
  apps.append({'name':name,'domains':domains,'root':root,'socket':sock.group(1) if sock else None,'wordpress':bool(root and (P(root)/'wp-config.php').exists())})
 assert apps,'no application pools'
 return apps

def curl_probe(arg):
 app,origin=arg
 if not app['domains']:return {'app':app['name'],'origin':origin,'error':'no_domain'}
 host=app['domains'][0];url='https://'+host+'/?mgs_php_security_check='+str(time.time_ns())
 cmd=['curl','--silent','--show-error','--location','--max-redirs','4','--connect-timeout','7','--max-time','25','--max-filesize','3145728','--output','/dev/null','--write-out','%{http_code}\t%{url_effective}\t%{content_type}','--user-agent','MGS-PHP-Security-Validation/1.0']
 if origin:cmd+=['--insecure','--resolve',host+':443:127.0.0.1']
 p=run(cmd+[url],timeout=32);bits=p.stdout.split('\t')
 return {'app':app['name'],'domain':host,'origin':origin,'tls_verified':not origin,'exit':p.returncode,'status':int(bits[0]) if bits and bits[0].isdigit() else 0,'final_host':__import__('urllib.parse',fromlist=['urlparse']).urlparse(bits[1]).hostname if len(bits)>1 else None,'content_type':bits[2] if len(bits)>2 else '', 'error_kind':('tls' if p.returncode==60 else 'timeout' if p.returncode==28 else 'transport' if p.returncode else None)}

def fcgi_probe(app):
 if not app.get('root') or not app.get('socket'):return {'app':app['name'],'error':'unmapped_root_or_socket'}
 script=P(app['root'])/'index.php'
 if not script.is_file():return {'app':app['name'],'skipped':'no_index_php'}
 host=app['domains'][0] if app['domains'] else 'localhost'
 def record(kind,data):return struct.pack('!BBHHBB',1,kind,1,len(data),0,0)+data
 def enc_len(n):return bytes([n]) if n<128 else struct.pack('!I',n|0x80000000)
 def nv(k,v):
  a=k.encode();b=v.encode();return enc_len(len(a))+enc_len(len(b))+a+b
 params={'GATEWAY_INTERFACE':'CGI/1.1','REQUEST_METHOD':'GET','SCRIPT_FILENAME':str(script),'SCRIPT_NAME':'/index.php','REQUEST_URI':'/?mgs_php_security_check='+str(time.time_ns()),'QUERY_STRING':'mgs_php_security_check='+str(time.time_ns()),'DOCUMENT_ROOT':str(script.parent),'SERVER_PROTOCOL':'HTTP/1.1','SERVER_SOFTWARE':'MGS-validation','SERVER_NAME':host,'HTTP_HOST':host,'SERVER_ADDR':'127.0.0.1','SERVER_PORT':'443','HTTPS':'on','REMOTE_ADDR':'127.0.0.1','REMOTE_PORT':'54321','HTTP_USER_AGENT':'MGS-PHP-Security-Validation/1.0'}
 s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.settimeout(25)
 out=bytearray();err=bytearray();end=False;app_status=None
 try:
  s.connect(app['socket']);s.sendall(record(1,struct.pack('!HB5x',1,0))+record(4,b''.join(nv(k,v) for k,v in params.items()))+record(4,b'')+record(5,b''))
  def recv(n):
   b=bytearray()
   while len(b)<n:
    x=s.recv(n-len(b))
    if not x:raise RuntimeError('unexpected FastCGI EOF')
    b.extend(x)
   return b
  while not end:
   h=recv(8);ver,kind,rid,length,pad,res=struct.unpack('!BBHHBB',h);assert ver==1 and rid==1
   content=recv(length) if length else b''
   if pad:recv(pad)
   if kind==6:
    if len(out)<4194304:out.extend(content)
   elif kind==7:
    if len(err)<65536:err.extend(content)
   elif kind==3:
    app_status,protocol=struct.unpack('!IB3x',content);end=True
  text=out.decode(errors='replace');header=text.split('\r\n\r\n',1)[0];m=re.search(r'^Status:\s*(\d+)',header,re.M|re.I)
  return {'app':app['name'],'status':int(m.group(1)) if m else 200,'app_status':app_status,'response_bytes':len(out),'fatal':bool(re.search(r'PHP Fatal error|Fatal error:|Parse error:',text+err.decode(errors='replace'))),'stderr_bytes':len(err),'complete':end}
 except Exception as e:return {'app':app['name'],'error':type(e).__name__}
 finally:s.close()

def probes(apps):
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
  http=list(ex.map(curl_probe,[(a,origin) for a in apps for origin in [False,True]]))
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:fcgi=list(ex.map(fcgi_probe,apps))
 return {'http':http,'fcgi':fcgi}

def collect(with_probes=True):
 apps=inventory();p=packages();sv={k:service(k) for k in ['php83rc-fpm.service','nginx-rc.service','mariadb.service','apache2-rc.service']}
 r=run(['/RunCloud/Packages/php83rc/bin/php','-v']);version=r.stdout.splitlines()[0] if r.stdout else ''
 mods=run(['/RunCloud/Packages/php83rc/bin/php','-m'])
 ng=run(['/usr/local/sbin/nginx-rc','-t']);fp=run(['/RunCloud/Packages/php83rc/sbin/php-fpm','-t'])
 pid=sv['php83rc-fpm.service'].get('MainPID','0');exe=os.readlink('/proc/'+pid+'/exe') if pid!='0' else None
 return {'time':time.time(),'host':socket.gethostname(),'auth':AUTH,'packages':p,'services':sv,'php_version':version,'php_modules':mods.stdout.splitlines(),'php_module_stderr_bytes':len(mods.stderr),'nginx_config_ok':ng.returncode==0,'fpm_config_ok':fp.returncode==0,'fpm_executable':exe,'apps':apps,'config_hashes':config_hashes(),'dpkg_audit':run(['dpkg','--audit']).stdout,'disk_available':os.statvfs('/').f_bavail*os.statvfs('/').f_frsize,'probes':probes(apps) if with_probes else None}

def sim():
 r=run(['apt-get','-s','install','--only-upgrade','--no-install-recommends']+[n+'='+NEW for n in NAMES])
 assert r.returncode==0,'APT simulation failed'
 rows=[s for s in r.stdout.splitlines() if s.startswith(('Inst ','Remv '))]
 assert not any(s.startswith('Remv ') for s in rows),'unexpected removal'
 for s in rows:
  m=re.match(r'Inst (\S+) (?:\[([^]]+)\] )?\((\S+)',s);assert m and m.group(1) in NAMES and m.group(3)==NEW,'transaction drift'
 return rows

def backup():
 before=json.loads((BASE/'preflight.json').read_text());assert before['disk_available']>1073741824,'insufficient backup headroom'
 assert packages()==before['packages'],'package drift before backup'
 old=BASE/'old-debs';old.mkdir(mode=0o700,exist_ok=True)
 need=[n for n,v in before['packages'].items() if v==OLD]
 if need:
  r=run(['apt-get','download']+[n+'='+OLD for n in need],timeout=180,cwd=old)
  (BASE/'rollback-download.log').write_text(r.stdout+r.stderr)
  assert r.returncode==0,'old package download failed; preserved partial set'
 debs={}
 for p in old.glob('*.deb'):
  n=run(['dpkg-deb','-f',str(p),'Package']).stdout.strip();v=run(['dpkg-deb','-f',str(p),'Version']).stdout.strip();assert n in need and v==OLD,'rollback artifact mismatch';debs[n]=p
 assert set(debs)==set(need),'rollback package coverage incomplete'
 archive=BASE/'php-nginx-config-before.tar.gz'
 if not archive.exists():
  r=run(['tar','-czf',str(archive),'-C','/','etc/php83rc','etc/nginx-rc'],timeout=120);assert r.returncode==0,'config backup failed'
 assert run(['tar','-tzf',str(archive)]).returncode==0,'config backup integrity failed'
 paths=[archive]+list(debs.values());manifest=''.join(sha(p)+'  '+str(p)+'\n' for p in paths);(BASE/'rollback.sha256').write_text(manifest)
 r=run(['sha256sum','-c',str(BASE/'rollback.sha256')]);assert r.returncode==0,'rollback checksum failed'
 return save('backup',{'auth':AUTH,'old_debs':len(debs),'archive':str(archive),'archive_bytes':archive.stat().st_size,'backup_dir':str(BASE),'sha256_validated':True,'config_hashes':before['config_hashes']})

def apply():
 before=json.loads((BASE/'preflight.json').read_text());b=json.loads((BASE/'backup.json').read_text());assert b['sha256_validated']
 assert run(['sha256sum','-c',str(BASE/'rollback.sha256')]).returncode==0,'rollback damaged'
 current=packages();assert set(current.values()).issubset({OLD,NEW}),'unexpected current version'
 assert config_hashes()==before['config_hashes'],'configuration drift; do not overwrite'
 rows=sim();receipt={'auth':AUTH,'started':time.time(),'before':current,'simulation':rows,'backup':str(BASE)};save('apply-start',receipt)
 if rows:
  env=os.environ.copy();env.update({'DEBIAN_FRONTEND':'noninteractive','NEEDRESTART_MODE':'l','UCF_FORCE_CONFFOLD':'1'})
  r=run(['apt-get','-y','install','--only-upgrade','--no-install-recommends','-o','Dpkg::Options::=--force-confold']+[n+'='+NEW for n in NAMES],timeout=240,env=env)
  (BASE/'install.log').write_text(r.stdout+r.stderr);receipt['install_exit']=r.returncode;save('apply-result',receipt)
  assert r.returncode==0,'package installation failed; inspect preserved receipt'
 else:receipt['install_exit']=0;receipt['already_patched']=True
 assert set(packages().values())=={NEW},'post-install package mismatch'
 assert run(['/RunCloud/Packages/php83rc/sbin/php-fpm','-t']).returncode==0,'post-install FPM config failed'
 r=run(['systemctl','restart','php83rc-fpm.service'],timeout=60);receipt['restart_exit']=r.returncode;save('apply-result',receipt);assert r.returncode==0,'PHP-FPM restart failed'
 receipt['finished']=time.time();receipt['after']=packages();save('apply-result',receipt);return receipt

def compare():
 b=json.loads((BASE/'preflight.json').read_text());a=collect(True);save('postcheck',a)
 assert set(a['packages'].values())=={NEW},'wrong package versions'
 assert a['nginx_config_ok'] and a['fpm_config_ok'] and not a['dpkg_audit'],'config/dpkg validation failed'
 assert a['services']['php83rc-fpm.service']['ActiveState']=='active','FPM inactive'
 assert a['services']['php83rc-fpm.service']['MainPID']!=b['services']['php83rc-fpm.service']['MainPID'],'worker master not replaced'
 assert a['apps']==b['apps'],'app mapping changed'
 assert a['php_modules']==b['php_modules'],'extension/module set changed'
 drift=[p for p in set(b['config_hashes'])|set(a['config_hashes']) if b['config_hashes'].get(p)!=a['config_hashes'].get(p)]
 hbefore={(r['app'],r['origin']):r for r in b['probes']['http']};f_before={r['app']:r for r in b['probes']['fcgi']};reg=[]
 for r in a['probes']['http']:
  prev=hbefore[(r['app'],r['origin'])]
  if prev.get('exit')==0 and prev.get('status',0)<500 and (r.get('exit')!=0 or r.get('status',0)>=500):reg.append({'type':'http','before':prev,'after':r})
 for r in a['probes']['fcgi']:
  prev=f_before[r['app']]
  if prev.get('complete') and not prev.get('fatal') and prev.get('status',0)<500 and (not r.get('complete') or r.get('fatal') or r.get('status',0)>=500):reg.append({'type':'fcgi','before':prev,'after':r})
 workers=[]
 for p in P('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   exe=os.readlink(p/'exe')
   if 'php83rc' in exe and exe.endswith(' (deleted)'):workers.append(int(p.name))
  except OSError:pass
 checks={'all_packages_target':True,'fpm_active_new_master':True,'apps_preserved':True,'modules_preserved':True,'config_changed_paths':drift,'old_deleted_workers':workers,'regressions':reg,'apps':len(a['apps']),'http_checks':len(a['probes']['http']),'fcgi_checks':len(a['probes']['fcgi']),'preexisting_http_issues':[r for r in b['probes']['http'] if r.get('exit') or r.get('status',0)>=400],'preexisting_fcgi_issues':[r for r in b['probes']['fcgi'] if r.get('error') or r.get('fatal') or r.get('status',0)>=400]}
 save('validation',checks)
 assert not drift,'configuration changed; requires diagnosis'
 assert not workers,'old PHP workers remain'
 assert not reg,'application regression detected'
 return checks

def main():
 os.umask(0o077);phase=sys.argv[1]
 if phase=='preflight':
  assert not (BASE/'apply-start.json').exists(),'mutation receipt already exists; reconcile before replay'
  a=collect(True);assert set(a['packages'].values()).issubset({OLD,NEW}),'package prestate drift'
  assert a['nginx_config_ok'] and a['fpm_config_ok'] and not a['dpkg_audit'],'preflight not healthy'
  a['simulation']=sim();save('preflight',a);out={'apps':len(a['apps']),'mapped_domains':sum(bool(x['domains']) for x in a['apps']),'mapped_roots':sum(bool(x['root']) for x in a['apps']),'packages':a['packages'],'services':a['services'],'http_checks':len(a['probes']['http']),'fcgi_checks':len(a['probes']['fcgi']),'http_issues':[r for r in a['probes']['http'] if r.get('exit') or r.get('status',0)>=400],'fcgi_issues':[r for r in a['probes']['fcgi'] if r.get('error') or r.get('fatal') or r.get('status',0)>=400],'backup':str(BASE)}
 elif phase=='backup':out=backup()
 elif phase=='apply':out=apply()
 elif phase=='verify':out=compare()
 elif phase=='collect':out=collect(False)
 else:raise ValueError('unknown phase')
 print(json.dumps({'phase':phase,'ok':True,'data':out}))
if __name__=='__main__':
 try:main()
 except Exception as e:
  save('failure-'+(sys.argv[1] if len(sys.argv)>1 else 'unknown'),{'time':time.time(),'type':type(e).__name__,'error':str(e)});print(json.dumps({'ok':False,'type':type(e).__name__,'error':str(e)}));sys.exit(1)
