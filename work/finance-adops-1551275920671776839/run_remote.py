import sys,json,shlex,base64,hashlib
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env;load_env()
sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy');from runcloud_ops import ssh
W=Path(__file__).parent;R='/home/mgsfinance/backups/adops-1551275920671776839';PG='env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/'
phase=sys.argv[1]
if phase=='prepare':
 ssh('sudo -n install -d -m 700 -o mgsfinance -g mgsfinance '+R)
 for name in ['plan.json','apply.mjs']:
  ssh('sudo -u mgsfinance tee '+R+'/'+name+' >/dev/null',input_data=(W/name).read_bytes())
  remote=ssh('sudo -u mgsfinance sha256sum '+R+'/'+name).split()[0];assert remote==hashlib.sha256((W/name).read_bytes()).hexdigest()
 print('Remote payload hashes PASS')
elif phase=='backup':
 ssh('sudo -n bash -c '+shlex.quote('sudo -u mgs_pg '+PG+'pg_dump -h /run/mgs-postgresql18 -d mgs_finance -Fc > '+R+'/before.dump && chown mgsfinance:mgsfinance '+R+'/before.dump && chmod 600 '+R+'/before.dump'),timeout=180)
 listing=ssh('sudo -u mgsfinance '+PG+'pg_restore -l '+R+'/before.dump');assert 'scenarios' in listing and 'audit_events' in listing
 encoded=ssh('sudo -u mgsfinance base64 -w0 '+R+'/before.dump',timeout=180);raw=base64.b64decode(encoded,validate=True);local=W/'before.dump';local.write_bytes(raw);local.chmod(0o600)
 h=hashlib.sha256(raw).hexdigest();remote=ssh('sudo -u mgsfinance sha256sum '+R+'/before.dump').split()[0];assert h==remote
 # Materialize isolated restore, never delete/reuse an existing database.
 db='mgs_finance_adops_1551275920671776839'
 ssh('sudo -u mgs_pg '+PG+'createdb -h /run/mgs-postgresql18 '+db)
 ssh('sudo -u mgsfinance /bin/cat '+R+'/before.dump | sudo -u mgs_pg '+PG+'pg_restore -h /run/mgs-postgresql18 --exit-on-error -d '+db,timeout=180)
 query="SELECT json_build_object('scenarios',(SELECT count(*) FROM scenarios),'source_cells',(SELECT count(*) FROM source_cells),'revision',(SELECT revision FROM scenarios WHERE id='workspace-2026-08'))"
 check=json.loads(ssh('sudo -u mgs_pg '+PG+'psql -h /run/mgs-postgresql18 -d '+db+' -At -c '+shlex.quote(query)))
 assert check['revision']==391 and check['source_cells']==85868
 out={'pass':True,'sha256':h,'remote':R+'/before.dump','local':str(local),'restore_database':db,'restore_check':check}
 (W/'backup-readback.json').write_text(json.dumps(out));print(json.dumps(out))
else:
 assert phase in ['rehearse','apply','verify'];out=ssh('sudo -u mgsfinance /home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node '+R+'/apply.mjs '+phase,timeout=240);(W/(phase+'-out.json')).write_text(out);print(out)
