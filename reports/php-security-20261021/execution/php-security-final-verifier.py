#!/usr/bin/env python3
# Invoked after the shared probe definitions, not standalone.
import copy
before=json.loads((BASE/'preflight.json').read_text());after=collect(True)
expected_apps=copy.deepcopy(before['apps']);expected_hashes=dict(before['config_hashes'])
recovery=BASE/'socket-recovery-1562594110655828149/result.json'
if recovery.exists():
 rec=json.loads(recovery.read_text());assert rec['authorization']=='1562594110655828149'
 for app in expected_apps:
  if app['name']=='mgs-finance-dash':app['socket']='/var/run/mgs-finance-dash-php.sock'
 expected_hashes.update(rec['hashes_after'])
assert after['apps']==expected_apps,'unapproved app map drift'
assert after['config_hashes']==expected_hashes,'unapproved config drift'
assert set(after['packages'].values())=={NEW},'wrong installed package revision'
assert '8.3.36' in after['php_version'] and after['nginx_config_ok'] and after['fpm_config_ok'] and not after['dpkg_audit'],'package/config validation failed'
assert after['php_modules']==before['php_modules'],'module mismatch'
for unit in after['services']:
 assert after['services'][unit]['ActiveState']=='active','inactive service '+unit
 if unit!='php83rc-fpm.service':assert after['services'][unit]['MainPID']==before['services'][unit]['MainPID'],'unexpected protected service restart '+unit
hprev={(x['app'],x['origin']):x for x in before['probes']['http']};fprev={x['app']:x for x in before['probes']['fcgi']};reg=[]
for x in after['probes']['http']:
 old=hprev[(x['app'],x['origin'])]
 if old.get('exit')==0 and old.get('status',0)<500 and (x.get('exit')!=0 or x.get('status',0)>=500):reg.append({'type':'http','before':old,'after':x})
for x in after['probes']['fcgi']:
 old=fprev[x['app']]
 if old.get('complete') and not old.get('fatal') and old.get('status',0)<500 and (not x.get('complete') or x.get('fatal') or x.get('status',0)>=500):reg.append({'type':'fcgi','before':old,'after':x})
old_workers=[]
for p in P('/proc').iterdir():
 if p.name.isdigit():
  try:
   exe=os.readlink(p/'exe')
   if 'php83rc' in exe and exe.endswith(' (deleted)'):old_workers.append(int(p.name))
  except OSError:pass
rollback=run(['sha256sum','-c',str(BASE/'rollback.sha256')]);assert rollback.returncode==0,'original rollback damaged'
rows=sim();assert not rows,'approved package revision not settled'
checks={'time':time.time(),'host':socket.gethostname(),'packages':after['packages'],'apps':len(after['apps']),'http_checks':len(after['probes']['http']),'fcgi_completed':sum(bool(x.get('complete')) for x in after['probes']['fcgi']),'fcgi_skipped':[x for x in after['probes']['fcgi'] if x.get('skipped')],'regressions':reg,'old_deleted_workers':old_workers,'all_modules_preserved':True,'config_changes_exactly_approved':True,'protected_service_pids_unchanged':True,'rollback_validated':True,'current_http_issues':[x for x in after['probes']['http'] if x.get('exit') or x.get('status',0)>=400],'current_fcgi_issues':[x for x in after['probes']['fcgi'] if x.get('error') or x.get('fatal') or x.get('status',0)>=400]}
save('final-postcheck',after);save('final-validation',checks)
assert not reg and not old_workers,'validation regression or stale PHP process'
print(json.dumps({'ok':True,'result':checks}))
