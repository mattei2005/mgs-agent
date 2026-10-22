#!/usr/bin/env python3
"""Four explicitly confirmed remote reboots; never touches the agent VPS."""
import os,sys,json,time,socket,subprocess,re,hashlib,stat
from pathlib import Path
AUTH='1562891945536393229'
B=Path('/root/zeus-hetzner-reboot-'+AUTH)
HETZNER_HOSTS={'MatteiInc01':'5.15.0-198-generic','MatteiInc02':'5.15.0-198-generic','MatteiInc03':'5.15.0-198-generic','server.boostingecon.com':'6.8.0-147-generic'}
HOST=socket.gethostname();assert HOST in HETZNER_HOSTS,'out-of-scope host'
TARGET=HETZNER_HOSTS[HOST];RC=HOST!='server.boostingecon.com'
UNIT='zeus-hetzner-reboot-'+AUTH
UNITS=['nginx-rc.service','php83rc-fpm.service','apache2-rc.service','mariadb.service','cron.service'] if RC else ['nginx.service','php8.3-fpm.service','hestia.service','exim4.service','dovecot.service','mariadb.service','cron.service']
if HOST=='MatteiInc01':UNITS+=['mgs-finance-dash.service','mgs-finance-dash.socket','mgs-postgresql18.service']
def run(a,t=70):return subprocess.run(a,capture_output=True,text=True,timeout=t)
def save(n,d):
 B.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(B,0o700);p=B/(n+'.json');p.write_text(json.dumps(d,indent=2));os.chmod(p,0o600);return d
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
def unit(n):
 p=run(['systemctl','show',n,'-p','ActiveState','-p','SubState','-p','MainPID','-p','UnitFileState','-p','Result','-p','LoadState'])
 return dict(l.split('=',1) for l in p.stdout.splitlines() if '=' in l)
def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def packages():
 p=run(['dpkg-query','-W','-f=${Package}\t${Version}\t${Status}\n','php83rc*'] if RC else ['dpkg-query','-W','-f=${Package}\t${Version}\t${Status}\n','php8.3*','hestia-php'])
 return {l.split('\t')[0]:l.split('\t')[1] for l in p.stdout.splitlines() if 'install ok installed' in l}
def journal():return run(['journalctl','-b','-p','0..3','--no-pager','-o','cat']).stdout.splitlines()
def preflight():
 assert not (B/'dispatch.json').exists(),'existing dispatch: reconcile before proceeding'
 p=unit(UNIT+'.timer');assert p.get('LoadState')=='not-found','existing reboot timer'
 d={'authorization':AUTH,'host':HOST,'time':time.time(),'boot_id':boot(),'kernel':os.uname().release,'target_kernel':TARGET,'units':{n:unit(n) for n in UNITS},'packages':packages(),'reboot_marker':Path('/var/run/reboot-required').exists(),'boot_journal_errors':journal()}
 for n,v in d['units'].items():
  assert v.get('ActiveState')=='active',n+' inactive'
  if n=='hestia.service':assert v.get('UnitFileState')=='generated' and list(Path('/etc/rc2.d').glob('S*hestia')),'Hestia SysV boot path missing'
  else:assert v.get('UnitFileState') in ['enabled','enabled-runtime','static','indirect'],n+' not boot-enabled'
 assert not run(['dpkg','--audit']).stdout.strip(),'dpkg audit dirty'
 assert not run(['systemctl','--failed','--no-legend','--plain']).stdout.strip(),'failed baseline units'
 assert run(['dpkg-query','-W','-f=${Status}','linux-image-'+TARGET]).stdout.strip()=='install ok installed','target kernel package missing'
 artifacts=['/boot/vmlinuz-'+TARGET,'/boot/initrd.img-'+TARGET]
 assert all(Path(p).is_file() and Path(p).stat().st_size>1000000 for p in artifacts),'kernel/initrd missing'
 grub=Path('/boot/grub/grub.cfg').read_text(errors='replace');first=re.search(r'^\s*linux\s+\S*vmlinuz-(\S+)',grub,re.M);assert first and first[1]==TARGET,'GRUB kernel drift'
 ge=run(['grub-editenv','/boot/grub/grubenv','list']);assert ge.returncode==0 and not any(l.startswith('next_entry=') for l in ge.stdout.splitlines()),'GRUB override';d['grub_overrides']=[l for l in ge.stdout.splitlines() if l.startswith(('next_entry=','saved_entry='))]
 d['boot_artifacts']={p:sha(p) for p in artifacts};d['fstab_sha256']=sha('/etc/fstab');d['time_synchronized']=run(['timedatectl','show','-p','NTPSynchronized','--value']).stdout.strip();assert d['time_synchronized']=='yes','host clock not synchronized'
 if RC:assert d['packages'].get('php83rc')=='8.3.36-1+ubuntu22.04+1','PHP83 package drift'
 else:
  assert d['packages'].get('php8.3-fpm')=='8.3.36-1+ubuntu24.04.1+deb.sury.org+1' and d['packages'].get('hestia-php')=='8.5.12-1+ubuntu24.04','Hestia PHP drift'
  prev=Path('/root/zeus-hestia-php-security-1562888441400664176');assert run(['sha256sum','-c',str(prev/'rollback.sha256')]).returncode==0 and run(['sha256sum','-c',str(prev/'reconstructed-rollback.sha256')]).returncode==0,'PHP rollback damaged'
 archive=B/'config-before-reboot.tar.gz';B.mkdir(mode=0o700,exist_ok=True)
 if not archive.exists():
  paths=['etc/fstab','etc/default/grub','boot/grub/grub.cfg','etc/php83rc','etc/nginx-rc'] if RC else ['etc/fstab','etc/default/grub','boot/grub/grub.cfg','etc/php/8.3','etc/nginx','usr/local/hestia/php/etc','usr/local/hestia/conf']
  p=run(['tar','-czf',str(archive),'-C','/']+paths,120);assert p.returncode==0,'config backup failed'
 assert run(['tar','-tzf',str(archive)]).returncode==0,'backup archive invalid'
 digest=run(['sha256sum',str(archive)]);assert digest.returncode==0;(B/'backup.sha256').write_text(digest.stdout);assert run(['sha256sum','-c',str(B/'backup.sha256')]).returncode==0,'backup checksum mismatch'
 d['backup_bytes']=archive.stat().st_size;save('preflight',d);return d
def dispatch(epoch):
 pre=json.loads((B/'preflight.json').read_text());assert boot()==pre['boot_id'],'boot already changed'
 assert not (B/'dispatch.json').exists(),'already dispatched'
 assert 12<epoch-time.time()<180,'dispatch target outside safe window'
 assert sha('/etc/fstab')==pre['fstab_sha256'],'fstab drift'
 assert all(sha(p)==v for p,v in pre['boot_artifacts'].items()),'boot image drift'
 assert packages()==pre['packages'],'package drift'
 assert all(unit(n)['ActiveState']=='active' for n in UNITS),'service drift'
 assert run(['sha256sum','-c',str(B/'backup.sha256')]).returncode==0,'backup damaged'
 calendar=time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime(epoch));save('dispatch',{'authorization':AUTH,'time':time.time(),'target_epoch':epoch,'target_utc':calendar,'previous_boot_id':boot(),'timer':UNIT+'.timer','target_kernel':TARGET})
 os.sync();p=run(['systemd-run','--quiet','--unit='+UNIT,'--on-calendar='+calendar,'--timer-property=AccuracySec=1s','--timer-property=RandomizedDelaySec=0','/usr/bin/systemctl','reboot','--no-block'],25);save('dispatch-command',{'exit':p.returncode,'stderr':p.stderr[-1000:]});assert p.returncode==0,'timer creation failed'
 deadline=time.monotonic()+6
 while True:
  v=unit(UNIT+'.timer')
  if v.get('ActiveState')=='active' and v.get('SubState')=='waiting':break
  assert time.monotonic()<deadline,'timer did not become active/waiting';time.sleep(.25)
 detail=run(['systemctl','show',UNIT+'.timer','-p','NextElapseUSecRealtime','-p','Triggers']).stdout
 target=run(['systemctl','show',UNIT+'.service','-p','ExecStart']).stdout;assert '/usr/bin/systemctl reboot --no-block' in target,'wrong timer command'
 return save('dispatch-readback',{'authorization':AUTH,'timer':v,'schedule':detail,'target':target,'target_epoch':epoch})
def quick():return {'host':HOST,'boot_id':boot(),'kernel':os.uname().release,'units':{n:unit(n) for n in UNITS}}
def postboot():
 pre=json.loads((B/'preflight.json').read_text());d=quick();d.update({'authorization':AUTH,'time':time.time(),'packages':packages(),'reboot_marker':Path('/var/run/reboot-required').exists(),'failed_units':run(['systemctl','--failed','--no-legend','--plain']).stdout.splitlines(),'journal_errors':journal(),'dpkg_audit':run(['dpkg','--audit']).stdout.strip(),'tmp':{'uid':Path('/tmp').stat().st_uid,'gid':Path('/tmp').stat().st_gid,'mode':oct(stat.S_IMODE(Path('/tmp').stat().st_mode))},'backup_verified':run(['sha256sum','-c',str(B/'backup.sha256')]).returncode==0})
 save('postboot-observation',d);assert d['boot_id']!=pre['boot_id'],'no new boot';assert d['kernel']==TARGET,'wrong kernel';assert d['packages']==pre['packages'],'package drift';assert not d['reboot_marker'],'reboot marker persists'
 assert all(v['ActiveState']=='active' for v in d['units'].values()),'service inactive';assert not d['failed_units'] and not d['dpkg_audit'],'systemd/dpkg unhealthy';assert d['tmp']=={'uid':0,'gid':0,'mode':'0o1777'},'tmp unhealthy';assert d['backup_verified'],'backup damaged'
 d['journal_gate_clear']=not d['journal_errors'];d['reboot_and_runtime_ready']=True;save('postboot',d);return d
if __name__=='__main__':
 try:
  phase=sys.argv[1];result={'preflight':preflight,'dispatch':lambda:dispatch(int(sys.argv[2])),'quick':quick,'postboot':postboot}[phase]();print(json.dumps({'ok':True,'phase':phase,'result':result}))
 except Exception as e:
  save('failure-'+sys.argv[1],{'time':time.time(),'type':type(e).__name__,'error':str(e)});print(json.dumps({'ok':False,'error':str(e),'type':type(e).__name__}));raise SystemExit(1)
