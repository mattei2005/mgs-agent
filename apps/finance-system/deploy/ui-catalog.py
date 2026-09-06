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
AUTH='1546169687346249728';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748'
STATE=ROOT/('private/ui-catalog-'+AUTH);BACKUP='/home/zeus/mgs-finance-backups/'+AUTH
FILES=['server.mjs','worker.py','workspace.mjs','site_catalog.py','public/index.html','public/app.js','public/refinements.css']
OLD=[f for f in FILES if f!='site_catalog.py']
MANIFEST=ROOT/'private/ui-redesign-1546005809845243944/deploy-evidence.json'
manifest=json.loads(MANIFEST.read_text());expected={f:manifest['files'].get(f) for f in FILES}
def hashes():
 code='import pathlib,hashlib,json; p=pathlib.Path('+repr(TARGET)+'); print(json.dumps({f:(hashlib.sha256((p/f).read_bytes()).hexdigest() if (p/f).exists() else None) for f in '+repr(FILES)+'}))'
 return json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code)))
assert hashes()==expected,'Remote code changed: reconcile origin before writing'
(STATE/'preflight.json').write_text(json.dumps({'pass':True,'files':expected},indent=2))
print('preflight hashes PASS',flush=True)
if not args.publish:raise SystemExit(0)
assert json.loads((STATE/'local-browser-evidence.json').read_text())['pass']
assert json.loads((STATE/'catalog-api-evidence.json').read_text())['pass']
assert '# pass 19' in (STATE/'node-tests.log').read_text() and '# fail 0' in (STATE/'node-tests.log').read_text()
assert 'Ran 23 tests' in (STATE/'python-tests.log').read_text()
# Guard against overwriting earlier backup/staging state on reruns.
ssh('test ! -e '+BACKUP+' && sudo -n install -d -o zeus -g zeus -m 700 '+BACKUP)
pg_env='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu '
bin='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin/'
pg=pg_env+bin+'psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
check="SELECT count(*) FROM source_cells; SELECT md5(result::text) FROM scenarios WHERE id='baseline';"
baseline=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip()
ssh('sudo -n tar -czf '+BACKUP+'/code-before.tar.gz -C '+TARGET+' '+' '.join(OLD)+' && sudo -n chown zeus:zeus '+BACKUP+'/code-before.tar.gz && '+pg_env+bin+'pg_dump -h /run/mgs-postgresql18 -U mgs_pg -Fc mgs_finance > '+BACKUP+'/finance-before.dump && chmod 600 '+BACKUP+'/*',timeout=180)
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
DB='mgs_finance_catalog_'+AUTH
ssh(pg_env+bin+'createdb -h /run/mgs-postgresql18 -U mgs_pg '+DB)
ssh('cat '+BACKUP+'/finance-before.dump | '+pg_env+bin+'pg_restore -h /run/mgs-postgresql18 -U mgs_pg --exit-on-error -d '+DB,timeout=180)
assert ssh(pg+'-d '+DB+' -c '+shlex.quote(check)).strip()==baseline
sql="""BEGIN; SET LOCAL ROLE mgsfinance;
INSERT INTO scenarios(id,import_id,name,state,result,additions)
SELECT 'TEST-catalog-1546169687346249728',import_id,'TEST isolated conference date','draft',result,'[{"kind":"expense","id":"TEST-review","category":"company","label":"TEST isolated only","amount":"0","currency":"USD","status":"Conferido","checked_on":"2026-09-08"}]'::jsonb FROM scenarios WHERE id='baseline';
DO $test$ DECLARE blocked boolean:=false; BEGIN BEGIN UPDATE scenarios SET revision=revision+1 WHERE id='baseline'; EXCEPTION WHEN OTHERS THEN blocked:=true; END; IF NOT blocked THEN RAISE EXCEPTION 'baseline writable'; END IF; END $test$;
COMMIT;"""
ssh(pg+'-d '+DB,sql.encode(),timeout=90)
readback=ssh(pg+'-d '+DB+' -c '+shlex.quote("SELECT additions->0->>'checked_on' FROM scenarios WHERE id='TEST-catalog-1546169687346249728';")).strip()
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
# Run new worker on an isolated staging copy before replacing production code.
ssh('sudo -n -u mgsfinance mkdir -p '+stage+'/private && sudo -n -u mgsfinance cp '+TARGET+'/calc.py '+TARGET+'/domain.py '+TARGET+'/expenses.py '+TARGET+'/ui_model.py '+stage+'/ && sudo -n -u mgsfinance ln -s '+TARGET+'/private/source.json '+stage+'/private/source.json && sudo -n -u mgsfinance ln -s '+TARGET+'/private/ui-model.json '+stage+'/private/ui-model.json')
canary_payload={'additions':[{'kind':'site','id':'newsite-TEST-staged','name':'TEST isolated staging only','new':True,'status':'ATIVO','countries':['US'],'manager':'nicolas','partner':'JBF','currency':'USD','invalid_source':'L1'},{'kind':'expense','id':'TEST-extra-staged','category':'company','label':'TEST isolated staging extra','amount':'30','currency':'USD','status':'A conferir'}]}
code='import sys,json,pathlib;sys.path.insert(0,'+repr(stage)+');import worker;from calc import json_default; r=worker.run(json.load(sys.stdin));d=r["domain"]; assert d["allocation"]["active_units"]==31; assert abs(sum(s["expenses"] for s in d["segments"])-d["cash"]["company_expenses"])<0.000001; pathlib.Path('+repr(stage+'/private/canary-result.json')+').write_text(json.dumps(r,default=json_default));print(json.dumps({"pass":True,"active_units":31,"allocation_reconciles":True,"production_writes":0}))'
canary=json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code),json.dumps(canary_payload).encode(),timeout=180));assert canary['pass'];(STATE/'remote-canary-evidence.json').write_text(json.dumps(canary,indent=2))
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
 assert all(hashes()[f]==expected[f] for f in OLD),'Rollback code hash mismatch'
 (STATE/'rollback.json').write_text(json.dumps({'restored':True,'files':expected}))
 raise
manifest['files'].update(local);MANIFEST.write_text(json.dumps(manifest,indent=2))
result={'pass':True,'target':TARGET,'backup':BACKUP,'files':local,'services':services,'baseline_preserved':True,'sheets_writes':0,'system_config_writes':0,'credential_changes':0}
(STATE/'deploy-evidence.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
