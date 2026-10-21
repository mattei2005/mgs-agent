#!/usr/bin/env python3
import runpy,json,time,socket,sys,datetime,subprocess
from pathlib import Path
ROOT=Path('/root/mgs-agent/reports/php-security-20261021/reboot')
H=runpy.run_path('/root/.hermes/profiles/zeus/cache/scratch/php-security-ssh.py');EXEC=Path('/root/.hermes/profiles/zeus/cache/scratch/mattei-reboot-executor.py').read_text()
name=sys.argv[1];ip=H['TARGETS'][name][0]
def persist(phase,r):
 (ROOT/(name+'-'+phase+'.json')).write_text(json.dumps(r,indent=2))
def call(phase,script,args=(),timeout=150):
 r=H['remote'](name,script,args,timeout=timeout);persist(phase,r);return r
pre=json.loads(json.loads((ROOT/(name+'-preflight.json')).read_text())['stdout'])['data'];assert pre['auth']=='1562596910748139551'
with open('/root/mgs-agent/logs/events-audit.jsonl','a') as f:f.write(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'agent':'zeus','action':'mattei_reboot_start','host':name,'authorization_message_id':'1562596910748139551','previous_boot_id':pre['boot_id'],'target_kernel':'5.15.0-198-generic'})+'\n')
r=call('dispatch',EXEC,['dispatch'],timeout=65);print('dispatch',name,'exit',r['exit'],r['stdout'][:500],r['stderr'][:150],flush=True)
# An SSH disconnect can be the expected effect of the dispatched reboot; never replay it.
assert r['exit'] in (0,255),'dispatch failed unexpectedly'
time.sleep(12);deadline=time.monotonic()+300;observations=[];ready=False
probe="""import json,subprocess\nfrom pathlib import Path\nnames=['nginx-rc.service','php83rc-fpm.service','apache2-rc.service','mariadb.service','cron.service']\nif Path('/etc/systemd/system/mgs-finance-dash.service').exists():names+=['mgs-finance-dash.service','mgs-finance-dash.socket','mgs-postgresql18.service']\ns={n:subprocess.run(['systemctl','is-active',n],capture_output=True,text=True).stdout.strip() for n in names}\nprint(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'units':s}))\n"""
while time.monotonic()<deadline:
 # Authenticate a real read-only SSH command; a bare TCP open/close creates
 # misleading sshd kex errors in the new boot's journal.
 r=H['remote'](name,probe,timeout=50)
 if r['exit']==0:
  d=json.loads(r['stdout']);observations.append(d)
  if d['boot_id']!=pre['boot_id'] and all(v=='active' for v in d['units'].values()):ready=True;break
 time.sleep(8)
persist('readiness',{'ready':ready,'observations':observations});assert ready,'host did not reach new-boot readiness in bounded window'
r=call('postboot',EXEC,['postboot'],timeout=100);assert r['exit']==0,r['stdout'];d=json.loads(r['stdout'])['data'];print('postboot',name,json.dumps(d),flush=True)
assert not d['failed_units'],'postboot failed units require diagnosis'
# Preserve the strict journal predicate independently of reboot and application
# completion. Any entries remain an explicit health residual for diagnosis.
d['journal_gate_clear']=not d['boot_critical_journal']
assert d['dpkg_audit_clean'] and d['tmp_correct'] and d['backup_verified'],'postboot package/tmp/backup health failed'
base=Path('/root/.hermes/profiles/zeus/cache/scratch/php-security-remote-executor.py').read_text();apps=Path('/root/.hermes/profiles/zeus/cache/scratch/mattei-postboot-apps.py').read_text();script='__name__="probe_definitions"\n'+base+'\n'+apps
r=call('app-validation',script,timeout=240);print('applications',name,'exit',r['exit'],r['stdout'][:5000],r['stderr'][:300],flush=True);assert r['exit']==0,'application verification failed'
result={'reboot_completed':True,'application_validation_passed':True,'overall_health_gate_clear':d['journal_gate_clear'],'authorization':'1562596910748139551','host':name,'before_boot_id':pre['boot_id'],'postboot':d,'apps':json.loads(r['stdout'])['data'],'time':time.time()};persist('completed',result)
print('HOST_REBOOT_COMPLETED',name,flush=True)
