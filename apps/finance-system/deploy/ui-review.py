"""Publish bounded finance review changes with code/DB backup and hash gates.
No Sheets, credentials, grants, system config or gateways are changed.
"""
import sys,pathlib,json,hashlib,shlex,tarfile,io,argparse
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'deploy'))
from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
p=argparse.ArgumentParser();p.add_argument('--publish',action='store_true');args=p.parse_args()
AUTH='1546147880559968286';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748'
STATE=ROOT/('private/ui-review-'+AUTH);BACKUP='/home/zeus/mgs-finance-backups/'+AUTH
FILES=['workspace.mjs','ui_model.py','public/index.html','public/app.js','public/refinements.css']
MANIFEST=ROOT/'private/ui-redesign-1546005809845243944/deploy-evidence.json'
manifest=json.loads(MANIFEST.read_text());expected={f:manifest['files'][f] for f in FILES}
def hashes():
 code='import pathlib,hashlib,json; p=pathlib.Path('+repr(TARGET)+'); print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(FILES)+'}))'
 return json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code)))
assert hashes()==expected,'Remote code changed: reconcile origin before writing'
(STATE/'preflight.json').write_text(json.dumps({'pass':True,'files':expected},indent=2))
print('preflight hashes PASS',flush=True)
if not args.publish:raise SystemExit(0)
assert json.loads((STATE/'local-browser-evidence.json').read_text())['pass']
# Guard against overwriting earlier backup/staging state on reruns.
ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP)
pg_env='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu '
bin='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/'
pg=pg_env+bin+'psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
check="SELECT count(*) FROM source_cells; SELECT md5(result::text) FROM scenarios WHERE id='baseline';"
baseline=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()
ssh('sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(FILES)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before.tar.gz && '+pg_env+bin+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && chmod 600 '+BACKUP+'/*',timeout=180)
# Second local copy of the consistent dump and code, with binary hash equality.
backup_hashes={}
for name in ['finance-before.dump','code-before.tar.gz']:
 # runcloud helper is text-oriented; transport binary as shell-generated base64.
 import base64
 encoded=ssh('base64 -w0 '+BACKUP+'/'+name,timeout=180)
 data=base64.b64decode(encoded,validate=True);dest=STATE/name;dest.write_bytes(data);dest.chmod(0o600)
 h=hashlib.sha256(data).hexdigest();assert ssh('sha256sum '+BACKUP+'/'+name).split()[0]==h
 backup_hashes[name]=h
# Restore into an isolated database without changing HBA or app grants.
DB='mgs_finance_review_'+AUTH
ssh(pg_env+bin+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB)
ssh('cat '+BACKUP+'/finance-before.dump | '+pg_env+bin+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB,timeout=180)
assert ssh(pg+'-d '+DB+' -c '+shlex.quote(check)).strip()==baseline
sql="""BEGIN; SET LOCAL ROLE mgsfinance;
INSERT INTO scenarios(id,import_id,name,state,result,additions)
SELECT 'TEST-review-1546147880559968286',import_id,'TEST isolated conference date','draft',result,'[{"kind":"expense","id":"TEST-review","category":"company","label":"TEST isolated only","amount":"0","currency":"USD","status":"Conferido","checked_on":"2026-09-08"}]'::jsonb FROM scenarios WHERE id='baseline';
DO $test$ DECLARE blocked boolean:=false; BEGIN BEGIN UPDATE scenarios SET revision=revision+1 WHERE id='baseline'; EXCEPTION WHEN OTHERS THEN blocked:=true; END; IF NOT blocked THEN RAISE EXCEPTION 'baseline writable'; END IF; END $test$;
COMMIT;"""
ssh(pg+'-d '+DB,sql.encode(),timeout=90)
readback=ssh(pg+'-d '+DB+' -c '+shlex.quote("SELECT additions->0->>'checked_on' FROM scenarios WHERE id='TEST-review-1546147880559968286';")).strip()
assert readback=='2026-09-08'
(STATE/'pg-restore-evidence.json').write_text(json.dumps({'pass':True,'isolated_database':DB,'baseline_hash_match':True,'baseline_write_rejected':True,'date_persisted':True,'production_test_financial_writes':0,'backup_hashes':backup_hashes},indent=2))
# Stage and validate all hashes before the bounded service-only cutover.
stage=TARGET+'/private/stage-review-'+AUTH
archive=io.BytesIO()
with tarfile.open(fileobj=archive,mode='w:gz') as t:
 for f in FILES:t.add(ROOT/f,arcname=f)
ssh('sudo -n -u mgsfinance mkdir '+stage+' && sudo -n -u mgsfinance tar -xzf - -C '+stage,archive.getvalue(),timeout=90)
local={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
code='import pathlib,hashlib; p=pathlib.Path('+repr(stage)+'); expected='+repr(local)+'; assert all(hashlib.sha256((p/f).read_bytes()).hexdigest()==h for f,h in expected.items())'
ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code))
assert hashes()==expected,'Concurrent change during staging; no publication'
try:
 ssh('sudo -n systemctl stop mgs-finance-dash.service',timeout=90)
 code='import os,pathlib; t=pathlib.Path('+repr(TARGET)+'); s=pathlib.Path('+repr(stage)+'); files='+repr(FILES)+'; [(os.chmod(s/f,0o600),os.replace(s/f,t/f)) for f in files]'
 ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code))
 ssh('sudo -n systemctl start mgs-finance-dash.service',timeout=90)
 assert hashes()==local
 services=ssh('systemctl is-active mgs-finance-dash.service mgs-finance-dash.socket mgs-postgresql18').split()
 assert services==['active']*3
 assert ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()==baseline
except Exception:
 ssh('sudo -n tar -xzf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' && sudo -n systemctl restart mgs-finance-dash.service',timeout=90)
 assert hashes()==expected,'Rollback code hash mismatch'
 (STATE/'rollback.json').write_text(json.dumps({'restored':True,'files':expected}))
 raise
manifest['files'].update(local);MANIFEST.write_text(json.dumps(manifest,indent=2))
result={'pass':True,'target':TARGET,'backup':BACKUP,'files':local,'services':services,'baseline_preserved':True,'sheets_writes':0,'system_config_writes':0,'credential_changes':0}
(STATE/'deploy-evidence.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
