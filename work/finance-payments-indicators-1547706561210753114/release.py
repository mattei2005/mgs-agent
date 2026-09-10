import sys,json,hashlib,shlex,pathlib,os
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy');from runcloud_ops import ssh
AUTH='1547706561210753114';ROOT=pathlib.Path('/root/mgs-agent');APP=ROOT/'apps/finance-system';STATE=ROOT/('work/finance-payments-indicators-'+AUTH);TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/'+AUTH
FILES=['finance-ops.mjs','public/operations.js','public/history-operations.js','public/app.js','public/history-dashboard.js'];phase=sys.argv[1]
new={f:hashlib.sha256((APP/f).read_bytes()).hexdigest() for f in FILES};env='env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';psql='sudo -n -u mgs_pg '+env+'/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -d mgs_finance -At '
manifest_sql="""SELECT json_build_object('scenarios',(SELECT json_agg(json_build_object('id',id,'revision',revision,'state',state,'overrides',md5(overrides::text),'additions',md5(additions::text),'result',md5(result::text)) ORDER BY id) FROM scenarios),'ledger',(SELECT json_build_object('count',count(*),'hash',md5(coalesce(string_agg(md5(row_to_json(x)::text),'' ORDER BY id),''))) FROM finance_ledger x),'history',(SELECT json_build_object('count',count(*),'hash',md5(coalesce(string_agg(md5(payload::text),'' ORDER BY period,book),''))) FROM finance_history),'users',(SELECT json_build_object('count',count(*),'hash',md5(coalesce(string_agg(md5(row_to_json(x)::text),'' ORDER BY username),''))) FROM finance_users x));"""
def remote_hashes():return {f:ssh('sudo -n -u mgsfinance sha256sum '+shlex.quote(TARGET+'/'+f)).split()[0] for f in FILES}
def db_manifest():return json.loads(ssh(psql+'-c '+shlex.quote(manifest_sql),timeout=180).strip())
def services():return ssh('systemctl is-active mgs-postgresql18 mgs-finance-dash mgs-finance-dash.socket').split()
def save(name,obj):(STATE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def load(name):return json.loads((STATE/name).read_text())
if phase=='prepare':
 assert services()==['active']*3;assert not ssh('if test -e '+shlex.quote(BACKUP)+'; then echo yes; fi').strip();ssh('sudo -n mkdir -p '+shlex.quote(BACKUP)+' && sudo -n chown zeus:zeus '+shlex.quote(BACKUP)+' && chmod 700 '+shlex.quote(BACKUP));before=remote_hashes();db=db_manifest()
 ssh('sudo -n tar -czf '+shlex.quote(BACKUP+'/code-before.tar.gz')+' -C '+shlex.quote(TARGET)+' '+' '.join(shlex.quote(f) for f in FILES)+' && sudo -n chown zeus:zeus '+shlex.quote(BACKUP+'/code-before.tar.gz')+' && chmod 600 '+shlex.quote(BACKUP+'/code-before.tar.gz'))
 tarhash=ssh('sha256sum '+shlex.quote(BACKUP+'/code-before.tar.gz')).split()[0]
 for f in FILES:
  pending=TARGET+'/'+f+'.pending-'+AUTH;assert not ssh('if sudo -n -u mgsfinance test -e '+shlex.quote(pending)+'; then echo yes; fi').strip();data=(APP/f).read_bytes();ssh('sudo -n -u mgsfinance tee '+shlex.quote(pending)+' >/dev/null',data);ssh('sudo -n -u mgsfinance chmod 600 '+shlex.quote(pending));assert ssh('sudo -n -u mgsfinance sha256sum '+shlex.quote(pending)).split()[0]==new[f]
 out={'pass':True,'authorization':AUTH,'before_hashes':before,'new_hashes':new,'database_manifest':db,'backup':BACKUP+'/code-before.tar.gz','backup_sha256':tarhash,'services':services(),'production_writes':0};save('prepared.json',out);print(json.dumps({'pass':True,'files':len(FILES),'backup_sha256':tarhash,'scenarios':len(db['scenarios']),'services':out['services']}))
elif phase=='publish':
 pre=load('prepared.json');assert pre['pass'] and remote_hashes()==pre['before_hashes'];assert db_manifest()==pre['database_manifest'];assert services()==['active']*3
 for f in FILES:
  pending=TARGET+'/'+f+'.pending-'+AUTH
  if not ssh('if sudo -n -u mgsfinance test -e '+shlex.quote(pending)+'; then echo yes; fi').strip():ssh('sudo -n -u mgsfinance tee '+shlex.quote(pending)+' >/dev/null',(APP/f).read_bytes());ssh('sudo -n -u mgsfinance chmod 600 '+shlex.quote(pending))
  assert ssh('sudo -n -u mgsfinance sha256sum '+shlex.quote(pending)).split()[0]==new[f]
 try:
  ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service')
  for f in FILES:
   code="import os;os.replace("+repr(TARGET+'/'+f+'.pending-'+AUTH)+","+repr(TARGET+'/'+f)+")";ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code))
  ssh('sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service');assert services()==['active']*3;assert remote_hashes()==new
  probe=ssh("a=$(sudo -n -u runcloud-www curl -sS --unix-socket /run/mgs-finance-dash.sock -H 'Host: dash.mgsdigitalcorp.com' -H 'X-Forwarded-Proto: https' -o /dev/null -w '%{http_code}' http://localhost/login); b=$(sudo -n -u runcloud-www curl -sS --unix-socket /run/mgs-finance-dash.sock -H 'Host: dash.mgsdigitalcorp.com' -H 'X-Forwarded-Proto: https' -o /dev/null -w '%{http_code}' http://localhost/api/scenarios); printf '%s|%s' \"$a\" \"$b\"").strip();assert probe=='200|401'
 except Exception:
  ssh('sudo -n tar -xzf '+shlex.quote(pre['backup'])+' -C '+shlex.quote(TARGET)+' && sudo -n chown -R mgsfinance:mgsfinance '+shlex.quote(TARGET)+' && sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service');assert remote_hashes()==pre['before_hashes'] and services()==['active']*3;save('rollback.json',{'pass':True,'reason':'publish_exception','restored_hashes':pre['before_hashes'],'services':services()});raise
 out={'pass':True,'authorization':AUTH,'files':new,'services':services(),'login_http':200,'unauth_api':401,'database_manifest_unchanged':db_manifest()==pre['database_manifest'],'rollback_available':pre['backup']};assert out['database_manifest_unchanged'];save('published.json',out);print(json.dumps({'pass':True,'files':len(new),'services':out['services'],'login_http':200,'unauth_api':401,'database_unchanged':True}))
elif phase=='verify':
 pre=load('prepared.json');pub=load('published.json');assert pub['pass'] and remote_hashes()==new and services()==['active']*3 and db_manifest()==pre['database_manifest'];out={'pass':True,'authorization':AUTH,'hashes':new,'services':services(),'database_manifest_unchanged':True,'backup':pre['backup'],'backup_sha256':pre['backup_sha256']};save('deploy-readback.json',out);print(json.dumps({'pass':True,'files':len(new),'services':out['services'],'database_unchanged':True,'backup_sha256':out['backup_sha256']}))
elif phase=='rollback':
 pre=load('prepared.json');ssh('sudo -n systemctl stop mgs-finance-dash.socket mgs-finance-dash.service && sudo -n tar -xzf '+shlex.quote(pre['backup'])+' -C '+shlex.quote(TARGET)+' && sudo -n chown -R mgsfinance:mgsfinance '+shlex.quote(TARGET)+' && sudo -n systemctl start mgs-finance-dash.socket mgs-finance-dash.service');assert remote_hashes()==pre['before_hashes'] and services()==['active']*3;out={'pass':True,'hashes':remote_hashes(),'services':services()};save('rollback.json',out);print(json.dumps(out))
else:raise ValueError('phase')
