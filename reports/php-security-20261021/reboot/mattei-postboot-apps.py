#!/usr/bin/env python3
# Runs after definitions from the PHP security probe module.
import copy
before=json.loads((BASE/'preflight.json').read_text());after=collect(True)
expected_apps=copy.deepcopy(before['apps']);expected_hashes=dict(before['config_hashes'])
recovery=BASE/'socket-recovery-1562594110655828149/result.json'
if recovery.exists():
 rec=json.loads(recovery.read_text());assert rec['authorization']=='1562594110655828149'
 for app in expected_apps:
  if app['name']=='mgs-finance-dash':app['socket']='/var/run/mgs-finance-dash-php.sock'
 expected_hashes.update(rec['hashes_after'])
assert after['apps']==expected_apps,'application map changed'
assert after['config_hashes']==expected_hashes,'unapproved configuration drift'
assert set(after['packages'].values())=={NEW},'PHP patch version changed'
assert after['nginx_config_ok'] and after['fpm_config_ok'] and not after['dpkg_audit'],'configuration or dpkg check failed'
assert after['php_modules']==before['php_modules'],'module set changed'
for n,s in after['services'].items():assert s['ActiveState']=='active','service inactive '+n
hprev={(x['app'],x['origin']):x for x in before['probes']['http']};fprev={x['app']:x for x in before['probes']['fcgi']};reg=[]
for x in after['probes']['http']:
 old=hprev[(x['app'],x['origin'])]
 if old.get('exit')==0 and old.get('status',0)<500 and (x.get('exit')!=0 or x.get('status',0)>=500):reg.append({'type':'http','before':old,'after':x})
for x in after['probes']['fcgi']:
 old=fprev[x['app']]
 if old.get('complete') and not old.get('fatal') and old.get('status',0)<500 and (not x.get('complete') or x.get('fatal') or x.get('status',0)>=500):reg.append({'type':'fcgi','before':old,'after':x})
checks={'host':socket.gethostname(),'apps':len(after['apps']),'http_checks':len(after['probes']['http']),'php_executions':sum(bool(x.get('complete')) for x in after['probes']['fcgi']),'php_version':after['php_version'],'regressions':reg,'module_set_preserved':True,'config_and_apps_preserved':True,'time':time.time()}
if recovery.exists():
 ss=run(['ss','-lxp']).stdout
 checks['finance_node_socket']=any('/run/mgs-finance-dash.sock' in s and 'node' in s for s in ss.splitlines())
 checks['finance_php_socket']=any('/var/run/mgs-finance-dash-php.sock' in s and 'php-fpm' in s for s in ss.splitlines())
 assert checks['finance_node_socket'] and checks['finance_php_socket'],'finance socket ownership invalid'
save('reboot-1562596910748139551/app-postcheck',after);save('reboot-1562596910748139551/app-validation',checks)
assert not reg,'application regression after reboot'
print(json.dumps({'ok':True,'data':checks}))
