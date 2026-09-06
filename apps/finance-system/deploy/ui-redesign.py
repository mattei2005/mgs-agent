"""Bounded finance UI deploy. Existing authenticated service only; no system config writes."""
import sys,pathlib,json,tarfile,io,hashlib,shlex
ROOT=pathlib.Path('/root/mgs-agent/apps/finance-system');sys.path.insert(0,str(ROOT/'deploy'))
from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env()
AUTH='1546005809845243944';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';BACKUP='/home/zeus/mgs-finance-backups/'+AUTH
FILES=['server.mjs','worker.py','ui_model.py','workspace.mjs','apply-live-quotes.mjs','public/index.html','public/app.js','public/app.css','public/refinements.css','private/ui-model.json','private/live-quotes.json']
OLD=['server.mjs','worker.py','public/index.html','public/app.js','public/app.css']
local_backup=ROOT/'private/ui-redesign-1546005809845243944/before'
expected={f:hashlib.sha256((local_backup/f).read_bytes()).hexdigest() for f in OLD}
remote_check="import hashlib,json,pathlib; p=pathlib.Path("+repr(TARGET)+"); print(json.dumps({k:hashlib.sha256((p/k).read_bytes()).hexdigest() for k in "+repr(OLD)+"}))"
actual=json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(remote_check)))
if actual!=expected:raise SystemExit('Preflight blocked: live code differs from authorized baseline; reconcile before deployment.')
print('preflight_code_hashes_match')
if '--publish' not in sys.argv:raise SystemExit(0)
# Snapshot code and a consistent full DB dump. No pruning or in-place DB restore.
cmd='sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP+' && sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+ ' '.join(OLD)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before.tar.gz && sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && chmod 600 '+BACKUP+'/* && sha256sum '+BACKUP+'/*'
print(ssh(cmd,timeout=180))
# Stage complete files before any replacement.
archive=io.BytesIO()
with tarfile.open(fileobj=archive,mode='w:gz') as t:
 for f in FILES:t.add(ROOT/f,arcname=f)
stage=TARGET+'/private/stage-ui-'+AUTH
print(ssh('sudo -n -u mgsfinance mkdir -p '+stage+' && sudo -n -u mgsfinance tar -xzf - -C '+stage,archive.getvalue(),timeout=90))
backend=[f for f in FILES if not f.startswith('public/')];frontend=[f for f in FILES if f.startswith('public/')]
def replace(files):
 code='import os,pathlib; target=pathlib.Path('+repr(TARGET)+'); stage=pathlib.Path('+repr(stage)+'); files='+repr(files)+'; [(os.chmod(stage/f,0o600),os.replace(stage/f,target/f)) for f in files]; print("installed",len(files))'
 return ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code))
print(replace(backend))
print(ssh('sudo -n systemctl restart mgs-finance-dash.service && systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18',timeout=90))
print(replace(frontend))
code='import pathlib,hashlib,json; p=pathlib.Path('+repr(TARGET)+'); print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(FILES)+'}))'
readback=json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code)))
local={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
if readback!=local:raise SystemExit('Deployment readback hash mismatch')
artifact=ROOT/'private/ui-redesign-1546005809845243944/deploy-evidence.json';artifact.write_text(json.dumps({'pass':True,'target':TARGET,'backup':BACKUP,'files':readback,'system_config_writes':0,'credential_changes':0},indent=2))
print(json.dumps({'deployed_files':len(FILES),'hash_readback':True,'backup':BACKUP,'target':TARGET}))
