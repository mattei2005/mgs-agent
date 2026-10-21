#!/usr/bin/env python3
import os,json,subprocess,time,re,hashlib,socket
from pathlib import Path
B=Path('/root/zeus-php-security-20261021-1562585423589412987/reboot-1562596910748139551')
TARGET='5.15.0-198-generic';AUTH='1562596910748139551'
UNITS=['nginx-rc.service','php83rc-fpm.service','apache2-rc.service','mariadb.service','cron.service']
if socket.gethostname()=='MatteiInc01':UNITS+=['mgs-finance-dash.service','mgs-finance-dash.socket','mgs-postgresql18.service']
def run(a,t=60):return subprocess.run(a,capture_output=True,text=True,timeout=t)
def unit(n):
 r=run(['systemctl','show',n,'-p','ActiveState','-p','MainPID','-p','UnitFileState','-p','SubState']);return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
def save(n,d):
 B.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(B,0o700);p=B/(n+'.json');p.write_text(json.dumps(d,indent=2));os.chmod(p,0o600)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def preflight():
 assert not (B/'dispatch.json').exists(),'existing reboot dispatch; reconcile rather than repeat'
 d={'host':socket.gethostname(),'auth':AUTH,'boot_id':boot(),'kernel':os.uname().release,'reboot_marker':Path('/var/run/reboot-required').exists(),'units':{n:unit(n) for n in UNITS},'tmp':{'mode':oct(Path('/tmp').stat().st_mode&0o7777),'uid':Path('/tmp').stat().st_uid,'gid':Path('/tmp').stat().st_gid},'free_bytes':os.statvfs('/').f_bavail*os.statvfs('/').f_frsize,'time':time.time()}
 for n,s in d['units'].items():assert s.get('ActiveState')=='active',n+' not active';assert s.get('UnitFileState') in ['enabled','enabled-runtime','static','indirect'],n+' startup not enabled'
 r=run(['dpkg-query','-W','-f=${Status} ${Version}','linux-image-'+TARGET]);assert r.returncode==0 and 'install ok installed' in r.stdout,'target kernel not installed'
 for n in ['vmlinuz-','initrd.img-']:assert (Path('/boot')/(n+TARGET)).is_file(),'missing boot artifact'
 grub=Path('/boot/grub/grub.cfg').read_text(errors='replace');first=re.search(r'^\s*linux\s+([^\s]+)',grub,re.M);assert first and TARGET in first.group(1),'default first GRUB kernel differs'
 env=run(['grub-editenv','/boot/grub/grubenv','list']);d['grub_environment']=[x for x in env.stdout.splitlines() if x.startswith(('saved_entry=','next_entry='))];assert not any('next_entry=' in x for x in d['grub_environment']),'one-shot GRUB override present'
 assert not run(['dpkg','--audit']).stdout.strip(),'dpkg audit not clean'
 d['failed_units']=run(['systemctl','--failed','--no-legend','--no-pager']).stdout.splitlines();assert not d['failed_units'],'preexisting failed units require attribution'
 d['kernel_image_sha256']=sha('/boot/vmlinuz-'+TARGET);d['initrd_sha256']=sha('/boot/initrd.img-'+TARGET)
 save('preflight',d)
 archive=B/'config-before-reboot.tar.gz'
 if not archive.exists():
  paths=['etc/php83rc','etc/nginx-rc']
  if socket.gethostname()=='MatteiInc01':paths+=['etc/systemd/system/mgs-finance-dash.service','etc/systemd/system/mgs-finance-dash.socket','etc/systemd/system/mgs-postgresql18.service']
  r=run(['tar','-czf',str(archive),'-C','/']+paths,90);assert r.returncode==0,'preboot backup failed'
 assert run(['tar','-tzf',str(archive)]).returncode==0
 mf=B/'backup.sha256';mf.write_text(sha(archive)+'  '+str(archive)+'\n');assert run(['sha256sum','-c',str(mf)]).returncode==0
 save('backup',{'archive':str(archive),'bytes':archive.stat().st_size,'verified':True})
 print(json.dumps({'ok':True,'phase':'preflight','data':d,'backup':str(B)}))
def dispatch():
 pre=json.loads((B/'preflight.json').read_text());assert pre['boot_id']==boot(),'boot already changed; do not replay'
 assert not (B/'dispatch.json').exists(),'reboot already dispatched'
 assert Path('/var/run/reboot-required').exists(),'reboot need changed'
 assert run(['sha256sum','-c',str(B/'backup.sha256')]).returncode==0
 for n in UNITS:assert unit(n)['ActiveState']=='active','service drift'
 assert sha('/boot/vmlinuz-'+TARGET)==pre['kernel_image_sha256'] and sha('/boot/initrd.img-'+TARGET)==pre['initrd_sha256'],'boot image drift'
 save('dispatch',{'auth':AUTH,'time':time.time(),'previous_boot':boot(),'target_kernel':TARGET})
 os.sync();r=run(['systemctl','reboot','--no-block'],30);save('dispatch-result',{'exit':r.returncode,'time':time.time()});assert r.returncode==0,'reboot dispatch failed'
 print(json.dumps({'ok':True,'phase':'dispatch','exit':r.returncode}))
def postboot():
 pre=json.loads((B/'preflight.json').read_text());d={'host':socket.gethostname(),'auth':AUTH,'boot_id':boot(),'kernel':os.uname().release,'reboot_marker':Path('/var/run/reboot-required').exists(),'units':{n:unit(n) for n in UNITS},'time':time.time()}
 save('postboot-observation',d)
 assert d['boot_id']!=pre['boot_id'],'old boot still active'
 assert d['kernel']==TARGET,'unexpected running kernel'
 assert not d['reboot_marker'],'reboot marker remains'
 for n,s in d['units'].items():assert s['ActiveState']=='active',n+' not active'
 d['failed_units']=run(['systemctl','--failed','--no-legend','--no-pager']).stdout.splitlines()
 d['boot_critical_journal']=run(['journalctl','-b','-p','0..3','--no-pager','-o','cat']).stdout.splitlines()
 d['dpkg_audit_clean']=not run(['dpkg','--audit']).stdout.strip()
 d['tmp_correct']=Path('/tmp').stat().st_uid==0 and Path('/tmp').stat().st_gid==0 and (Path('/tmp').stat().st_mode&0o7777)==0o1777
 d['backup_verified']=run(['sha256sum','-c',str(B/'backup.sha256')]).returncode==0
 save('postboot',d)
 print(json.dumps({'ok':True,'phase':'postboot','data':d}))
if __name__=='__main__':
 import sys
 try:
  {'preflight':preflight,'dispatch':dispatch,'postboot':postboot}[sys.argv[1]]()
 except Exception as e:
  save('failure-'+sys.argv[1],{'time':time.time(),'type':type(e).__name__,'error':str(e)});print(json.dumps({'ok':False,'type':type(e).__name__,'error':str(e)}));raise SystemExit(1)
