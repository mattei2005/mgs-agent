import sys,os,json,subprocess,shutil,sqlite3
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent;B.chmod(0o700)
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
H=Path('/root/mgs-agent/data/meta-manual-payments');S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
def save(p,d):
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
mode=sys.argv[1]
if mode=='preflight':
 c=json.loads((H/'digital-trust-workbook-contract.json').read_text())
 assert c['business_id']=='155263197283282' and len(set(c['account_ids']))==47 and c['month_since']=='2026-11-01' and c['month_until']=='2026-11-30' and c['payments_authorized'] is False
 con=sqlite3.connect('file:/root/.hermes/profiles/zeus/cron/executions.db?mode=ro',uri=True);con.row_factory=sqlite3.Row
 active=[dict(x)for x in con.execute("select * from executions where job_id='2ee720363d7d' and status in ('claimed','running')")]
 assert len(active)==1 and active[0]['id']=='32681e68c7ab4a37841b51ce3a733410' and active[0]['scheduled_instant']=='2026-11-12T02:02:00+00:00','concurrent_scheduled_writer'
 save(B/'active-execution.json',active)
 q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
 queues=[dict(x)for x in q.execute("select key,state,owner,cause,evidence,observation from requests where source_key like '%2ee720363d7d%' or observation like '%2ee720363d7d%'")]
 save(B/'continuity-before.json',queues)
 assert not any(x['owner'] and x['state'] in ['running','claimed','verifying'] for x in queues),'continuity_writer_active'
 sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
 g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
 sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['private_key'];t=g.service_account_access_token()
 status,d=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,capabilities',t,quota_project='mgs-core-prod');assert status==200 and d['capabilities']['canEdit']
 status,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',t,quota_project='mgs-core-prod');assert status==200
 assert not(B/'baseline.json').exists();save(B/'baseline.json',book)
 save(B/'contract-before.json',c)
 print(json.dumps({'status':'preflight_pass','active_executions':len(active),'other_tabs_baseline':len(book['sheets'])-1,'continuity_states':[x['state']for x in queues]}))
elif mode=='transport':
 ts=json.loads(subprocess.check_output(['tailscale','status','--json'],text=True));peer=next(x for x in ts['Peer'].values()if '100.85.69.58'in x.get('TailscaleIPs',[]))
 r=subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,timeout=65)
 d={'checked_at':datetime.now().astimezone().isoformat(),'tailscale_backend':ts['BackendState'],'pc1_online':peer.get('Online'),'pc1_last_seen':peer.get('LastSeen'),'ssh_exit':r.returncode,'ssh_timeout': 'Connection timed out'in r.stderr,'no_gui_input':True}
 if r.returncode==0:
  raw=json.loads(r.stdout);save(B/'pc1-windows-private.json',raw)
  d['windows']=[{'pid':x.get('pid'),'window_id':x.get('window_id'),'chrome': 'chrome'in x.get('app_name','').lower(),'minimized':x.get('minimized')}for x in raw.get('windows',[])]
 else:d['ssh_error']='connection_timeout' if 'Connection timed out'in r.stderr else 'transport_failed_see_private_diagnostic'
 p=B/'transport-diagnostic.json'
 if p.exists():save(B/('transport-diagnostic-'+datetime.now().strftime('%H%M%S')+'.json'),json.loads(p.read_text()))
 save(p,d);print(json.dumps(d))
else:
 args=sys.argv[2:];r=subprocess.run([sys.executable,str(S/(mode+'.py')),*args],capture_output=True,text=True,timeout=540)
 for suffix,text in [('stdout',r.stdout),('stderr',r.stderr)]:
  p=B/(mode+'-'+suffix+'.txt');p.write_text(text);p.chmod(0o600)
 try:d=json.loads(r.stdout)
 except Exception:print(json.dumps({'worker':mode,'exit_code':r.returncode,'output_parse_error':True}));raise SystemExit(2)
 p=B/'phases.json';ph=json.loads(p.read_text())if p.exists()else{};ph[mode]=d;save(p,ph)
 print(json.dumps({'worker':mode,'exit_code':r.returncode,'result':d},ensure_ascii=False));raise SystemExit(r.returncode)
