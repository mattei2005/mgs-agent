import json,sys,os,subprocess,shutil,sqlite3
from pathlib import Path
B=Path(__file__).parent;B.chmod(0o700);H=Path('/root/mgs-agent/data/meta-manual-payments')
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
c=json.loads((H/'digital-trust-workbook-contract.json').read_text());g.load_env()
assert c['month_since']=='2026-11-01' and len(set(c['account_ids']))==47 and c['payments_authorized'] is False
assert all(os.getenv(k)=='service_account' for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
con=sqlite3.connect('file:/root/.hermes/profiles/zeus/cron/executions.db?mode=ro',uri=True);con.row_factory=sqlite3.Row
active=[dict(x)for x in con.execute("select * from executions where job_id='2ee720363d7d' and status in ('claimed','running')")];assert len(active)==1 and active[0]['scheduled_instant']=='2026-11-11T13:02:00+00:00','concurrent_scheduled_writer';(B/'active-execution.json').write_text(json.dumps(active))
sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['private_key'];t=g.service_account_access_token()
s,d=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,capabilities',t,quota_project='mgs-core-prod');assert s==200 and d['capabilities']['canEdit']
s,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert s==200
assert not (B/'baseline.json').exists();(B/'baseline.json').write_text(json.dumps(book,ensure_ascii=False));(B/'baseline.json').chmod(0o600)
print(json.dumps({'status':'google_baseline_pass','active_scheduled_writers':len(active),'baseline':str(B/'baseline.json')}))
