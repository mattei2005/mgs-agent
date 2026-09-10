import sys,json,hashlib,shlex,pathlib
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy');from runcloud_ops import ssh
AUTH='1547706561210753114';ROOT=pathlib.Path('/root/mgs-agent');STATE=ROOT/('work/finance-payments-indicators-'+AUTH);LOCAL=ROOT/'apps/finance-system/public/app.js';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748/public/app.js';BACKUP='/home/zeus/mgs-finance-backups/'+AUTH+'/app-profit-before.js';PENDING=TARGET+'.profit-pending-'+AUTH;OLD='e58f5d9a259e179bba854cf22069f51927c660b9b24a305c1f83fef95f719b60';NEW=hashlib.sha256(LOCAL.read_bytes()).hexdigest();assert NEW!=OLD;phase=sys.argv[1]
def rh(p,user='mgsfinance'):return ssh('sudo -n -u '+user+' sha256sum '+shlex.quote(p)).split()[0]
def save(name,x):(STATE/name).write_text(json.dumps(x,indent=2)+'\n')
if phase=='apply':
 assert rh(TARGET)==OLD;assert not ssh('if test -e '+shlex.quote(BACKUP)+'; then echo yes; fi').strip();assert not ssh('if sudo -n -u mgsfinance test -e '+shlex.quote(PENDING)+'; then echo yes; fi').strip();ssh('sudo -n cp '+shlex.quote(TARGET)+' '+shlex.quote(BACKUP)+' && sudo -n chown zeus:zeus '+shlex.quote(BACKUP)+' && chmod 600 '+shlex.quote(BACKUP));assert rh(BACKUP,'zeus')==OLD
 data=LOCAL.read_bytes();ssh('sudo -n -u mgsfinance tee '+shlex.quote(PENDING)+' >/dev/null',data);ssh('sudo -n -u mgsfinance chmod 600 '+shlex.quote(PENDING));assert rh(PENDING)==NEW
 try:ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote('import os;os.replace('+repr(PENDING)+','+repr(TARGET)+')'));assert rh(TARGET)==NEW
 except Exception:ssh('sudo -n cp '+shlex.quote(BACKUP)+' '+shlex.quote(TARGET)+' && sudo -n chown mgsfinance:mgsfinance '+shlex.quote(TARGET));assert rh(TARGET)==OLD;raise
 out={'pass':True,'old_sha256':OLD,'new_sha256':NEW,'backup':BACKUP,'backup_sha256':rh(BACKUP,'zeus'),'services':ssh('systemctl is-active mgs-postgresql18 mgs-finance-dash mgs-finance-dash.socket').split(),'finance_service_restarts':0,'database_writes':0};assert out['services']==['active']*3;save('profit-semantic-published.json',out);print(json.dumps(out))
elif phase=='verify':
 out={'pass':rh(TARGET)==NEW,'new_sha256':NEW,'services':ssh('systemctl is-active mgs-postgresql18 mgs-finance-dash mgs-finance-dash.socket').split(),'backup_sha256':rh(BACKUP,'zeus'),'database_writes':0};assert out['pass'] and out['services']==['active']*3 and out['backup_sha256']==OLD;save('profit-semantic-readback.json',out);print(json.dumps(out))
elif phase=='rollback':
 ssh('sudo -n cp '+shlex.quote(BACKUP)+' '+shlex.quote(TARGET)+' && sudo -n chown mgsfinance:mgsfinance '+shlex.quote(TARGET));assert rh(TARGET)==OLD;out={'pass':True,'restored_sha256':OLD,'services':ssh('systemctl is-active mgs-finance-dash mgs-finance-dash.socket').split()};save('profit-semantic-rollback.json',out);print(json.dumps(out))
else:raise ValueError('phase')
