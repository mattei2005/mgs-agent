"""Pure Inc01 pre/post-boot collector; never reboots or changes services."""
import datetime,json,os,pathlib,stat,subprocess,re,tarfile
P=pathlib.Path;B=P('/root/mgs-maintenance/1574252891898908684-inc01');R=B/'reboot-1574650660572504115'
SERVICES=['mariadb','nginx-rc','apache2-rc','php83rc-fpm','runcloud-agent','bitninja','mgs-finance-dash','mgs-postgresql18','cron','ssh']
PGBIN='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/';PGLIB='/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(args,timeout=120,check=True):
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=timeout,env={**os.environ,'LC_ALL':'C','NEEDRESTART_MODE':'l','DEBIAN_FRONTEND':'noninteractive'})
 if check and p.returncode:raise RuntimeError(str(args[0])+' rc='+str(p.returncode))
 return p
def unit(name):return dict(x.split('=',1) for x in run(['systemctl','show',name,'-p','Id','-p','MainPID','-p','ActiveState','-p','SubState','-p','UnitFileState','-p','FragmentPath']).stdout.splitlines() if '=' in x)
def sql(q):return run(['mariadb','--batch','--skip-column-names','-e',q],60).stdout
def pg(q):return run(['runuser','-u','mgs_pg','--','env','LD_LIBRARY_PATH='+PGLIB,PGBIN+'psql','-h','/run/mgs-postgresql18','-d','mgs_finance','-At','-c',q],60).stdout

def assess(obs,pre=None):
 checks=dict(obs['checks'])
 if pre is not None:
  checks.update({'new_boot':obs['boot_id']!=pre['boot_id'],'expected_kernel':obs['kernel']==pre['expected_kernel'],'reboot_marker_absent':not obs['reboot_marker'],'runtime_executables_preserved':obs['executables']==pre['executables'],'configurations_preserved':obs['configuration_hashes']==pre['configuration_hashes'],'mariadb_catalog_preserved':obs['mariadb_catalog']==pre['mariadb_catalog'],'postgresql_version_preserved':obs['postgresql_version']==pre['postgresql_version'],'finance_socket_permissions_preserved':obs['finance_socket']==pre['finance_socket'],'bitninja_optional_expected_state':obs['optional_state']==pre['optional_state'],'needrestart_kernel_current':obs['needrestart_fields'].get('NEEDRESTART-KCUR')==obs['needrestart_fields'].get('NEEDRESTART-KEXP')==pre['expected_kernel'] and obs['needrestart_fields'].get('NEEDRESTART-KSTA')=='1','strict_new_boot_journal_no_priority0_3':obs.get('journal_rc')==0 and obs.get('journal_errors')==[]})
 return {'overall':all(checks.values()),'checks':checks,'checks_passed':sum(checks.values()),'checks_total':len(checks)}

def observe(pre=None,refresh=True):
 checks={};o={'at':now(),'checks':checks,'boot_id':P('/proc/sys/kernel/random/boot_id').read_text().strip(),'kernel':os.uname().release,'reboot_marker':P('/var/run/reboot-required').exists()};checks['host_identity']=os.uname().nodename=='MatteiInc01'
 target=json.loads((B/'confirmed-prestate.json').read_text())['packages'];o['packages']={x['package']:run(['dpkg-query','-W','-f=${Version}',x['package']]).stdout.strip() for x in target};checks['exact_approved_packages']=o['packages']=={x['package']:x['target'] for x in target}
 o['services']={n:unit(n) for n in SERVICES};checks['essential_services_active']=all(x['ActiveState']=='active' and int(x['MainPID'])>0 for x in o['services'].values());checks['essential_services_enabled']=all(x['UnitFileState']=='enabled' for x in o['services'].values())
 optional=unit('bitninja-policier');o['optional_state']={k:optional[k] for k in ['ActiveState','UnitFileState']}
 o['executables']={}
 for name in ['nginx-rc','apache2-rc','php83rc-fpm','mgs-finance-dash','mgs-postgresql18']:
  path='/proc/'+o['services'][name]['MainPID']+'/exe';o['executables'][name]={'path':str(P(path).resolve()),'sha256':run(['sha256sum',path]).stdout.split()[0]}
 paths=[]
 if pre is not None:paths=list(pre['configuration_hashes'])
 else:
  with tarfile.open(B/'configuration-and-dpkg.tar.gz','r:gz') as tf:
   for member in tf:
    n=member.name.removeprefix('./')
    if member.isfile() and n.startswith(('etc/mysql/','etc/ssh/','etc/firewalld/','etc/fail2ban/')):paths.append('/'+n)
  paths += [v['FragmentPath'] for v in o['services'].values() if v.get('FragmentPath')]
  paths += ['/boot/grub/grub.cfg','/etc/default/grub','/boot/vmlinuz-5.15.0-204-generic','/boot/initrd.img-5.15.0-204-generic']
  app=P('/home/mgsfinance/releases/pg-auth-1545934831664242748')
  for folder,dirs,files in os.walk(app,followlinks=False):
   dirs[:]=[n for n in dirs if n not in ['private','node_modules','.git','backups','data','reports','cache','artifacts','tests','test','fixtures','work','candidate','stage','evidence','docs','deploy'] and not (P(folder)/n).is_symlink()]
   for name in files:
    p=P(folder)/name
    if p.suffix in ['.mjs','.js','.cjs','.html','.css','.json'] and p.is_file() and not p.is_symlink():paths.append(str(p))
  auth=P('/home/mgsfinance/.config/finance/auth.json')
  if auth.is_file():paths.append(str(auth))
 o['configuration_hashes']={p:run(['sha256sum',p]).stdout.split()[0] for p in sorted(set(paths))}
 checks['mariadb_ping']=run(['mariadb-admin','ping'],30,False).returncode==0;o['mariadb_version']=sql('SELECT VERSION()').strip();checks['mariadb_expected_version']=o['mariadb_version'].startswith('10.11.20-')
 o['mariadb_catalog']=sql("SELECT TABLE_SCHEMA,TABLE_NAME,COALESCE(ENGINE,''),TABLE_TYPE FROM information_schema.TABLES WHERE TABLE_SCHEMA NOT IN ('information_schema','performance_schema') ORDER BY TABLE_SCHEMA,TABLE_NAME")
 o['postgresql_version']=pg("BEGIN READ ONLY; SELECT current_setting('server_version'); ROLLBACK;");checks['postgresql_readonly_query']=o['postgresql_version'].startswith('BEGIN\n18.6 ')
 checks['finance_unix_socket_present']=P('/run/mgs-finance-dash.sock').is_socket();s=P('/run/mgs-finance-dash.sock').stat();o['finance_socket']={'uid':s.st_uid,'gid':s.st_gid,'mode':stat.S_IMODE(s.st_mode)}
 o['http']={}
 for key,url in [('eggbev_public','https://eggbev.com/'),('finance_login','https://dash.mgsdigitalcorp.com/login'),('finance_unauth_api','https://dash.mgsdigitalcorp.com/api/scenarios')]:
  r=run(['curl','-sS','-L','--max-time','30','-o','/dev/null','-w','%{http_code}',url],40,False);o['http'][key]={'rc':r.returncode,'status':r.stdout.strip()}
 r=run(['curl','-k','-sS','--max-time','30','--resolve','eggbev.com:443:127.0.0.1','--resolve','eggbev.com:80:127.0.0.1','-L','-o','/dev/null','-w','%{http_code}','https://eggbev.com/?mgs-reboot='+str(int(datetime.datetime.now().timestamp()))],40,False);o['http']['eggbev_origin']={'rc':r.returncode,'status':r.stdout.strip()}
 r=run(['curl','-sS','--max-time','15','--unix-socket','/run/mgs-finance-dash.sock','-H','Host: dash.mgsdigitalcorp.com','-H','X-Forwarded-Proto: https','-o','/dev/null','-w','%{http_code}','http://localhost/api/scenarios'],25,False);o['http']['finance_socket_unauth_api']={'rc':r.returncode,'status':r.stdout.strip()}
 checks['public_and_origin_canaries']=all(v['rc']==0 and v['status']==('401' if 'unauth' in k else '200') for k,v in o['http'].items())
 checks['nginx_configuration_valid']=run(['/usr/local/sbin/nginx-rc','-t'],60,False).returncode==0;checks['sshd_configuration_valid']=run(['/usr/sbin/sshd','-t'],30,False).returncode==0
 t=P('/tmp').stat();checks['tmp_root_1777']=t.st_uid==t.st_gid==0 and stat.S_IMODE(t.st_mode)==0o1777
 checks['dpkg_clean']=not run(['dpkg','--audit']).stdout.strip();checks['holds_zero']=not run(['apt-mark','showhold']).stdout.strip();o['failed_units']=run(['systemctl','--failed','--no-legend','--no-pager']).stdout.strip();checks['failed_units_zero']=not o['failed_units']
 if refresh:
  r=run(['apt-get','update','-qq'],180,False);checks['apt_refresh_healthy']=r.returncode==0 and not any(x.startswith(('W:','E:')) for x in r.stderr.splitlines())
 o['apt_graph']={}
 for name,args in [('upgrade',['apt-get','-s','upgrade']),('full_upgrade',['apt-get','-s','dist-upgrade'])]:
  r=run(args);rows=[l for l in r.stdout.splitlines() if l.startswith(('Inst ','Remv ')) or re.match(r'^\d+ upgraded',l)];o['apt_graph'][name]=rows;checks[name+'_no_candidates']=not any(x.startswith(('Inst ','Remv ')) for x in rows)
 nr=run(['needrestart','-b','-r','l'],120);o['needrestart_fields']={k:v.strip() for k,v in (l.split(':',1) for l in nr.stdout.splitlines() if ':' in l and l.startswith('NEEDRESTART-'))};o['needrestart_service_rows']=[l for l in nr.stdout.splitlines() if l.startswith('NEEDRESTART-SVC:')]
 checks['package_and_config_recovery_hashes']=run(['sha256sum','-c',str(B/'rollback-and-candidates.sha256')],180,False).returncode==0
 cold=json.loads((B/'cold-backup-result.json').read_text());restore=json.loads((B/'isolated-restore-result.json').read_text());checks['validated_recovery_retained']=cold['overall'] and restore['overall'] and P(cold['archive']).is_file() and P(cold['archive']).stat().st_size==cold['archive_bytes']
 if pre is not None:
  j=run(['journalctl','-b','0','-p','0..3','--no-pager','-o','json'],120,False);o['journal_rc']=j.returncode;o['journal_errors']=[json.loads(x) for x in j.stdout.splitlines() if x] if j.returncode==0 else None
 o['assessment']=assess(o,pre);return o
