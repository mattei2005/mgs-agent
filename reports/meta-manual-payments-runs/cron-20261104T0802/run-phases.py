import sys,os,json,subprocess
from pathlib import Path
R=Path('/root/.hermes/hermes-agent-port-main-29a61cb7-mgs-20261103');sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
B=Path(__file__).parent;H=Path('/root/mgs-agent/data/meta-manual-payments');S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
c=json.loads((H/'digital-trust-workbook-contract.json').read_text());assert len(c['account_ids'])==47 and len(set(c['account_ids']))==47
assert c['month_since']=='2026-11-01' and c['month_until']=='2026-11-30' and not c['payments_authorized']
g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod'and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['private_key']
t=g.service_account_access_token()
status,drive=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,name,capabilities,trashed',t,quota_project='mgs-core-prod');assert status==200 and drive['capabilities']['canEdit'] and not drive.get('trashed');save(B/'drive.json',drive)
status,baseline=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200
assert not (B/'baseline.json').exists();save(B/'baseline.json',baseline);save(B/'contract-before.json',c)
print(json.dumps({'preflight':'canonical_sa_drive_edit_sheets_200','baseline_saved':True}),flush=True)
phases={}
for name,args in [('regroup_funding',['--apply']),('refresh_september_invoices',['--apply']),('refresh_workbook',['--apply','--allow-history-pending']),('publish_pay_now',['--prepare'])]:
 bootstrap="import sys,runpy;from pathlib import Path;R=Path("+repr(str(R))+");sys.path.insert(0,str(R));from pm.environments import activate_dependencies;activate_dependencies(R);sys.argv="+repr([str(S/(name+'.py'))]+args)+";runpy.run_path(sys.argv[0],run_name='__main__')"
 done=subprocess.run([sys.executable,'-c',bootstrap],capture_output=True,text=True,timeout=420)
 (B/(name+'-output.txt')).write_text(done.stdout+'\n'+done.stderr)
 print(name,done.returncode,done.stdout[-10000:],flush=True)
 assert done.returncode==0,'phase_failed_'+name
 result=json.loads(done.stdout.strip().splitlines()[-1]);assert result.get('status')!='blocked';phases[name]=result;save(B/'phases.json',phases)
