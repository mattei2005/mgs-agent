import os,sys,json,shutil,re,fcntl,sqlite3,importlib.util,hashlib,subprocess
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
os.umask(0o077)
h=shutil.which('hermes');assert h
R=Path(h).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
from mgs_finance_continuity import authored
from mgs_automation_continuity import native_contract_hash
B=Path(__file__).parent;P=B/'recovery-6373-20261125T214459';H=Path('/root/mgs-agent/data/meta-manual-payments');key='6373afb33275674610c06b6a'
def load(p):return json.loads(p.read_text())
def save(n,d):
 with (P/n).open('x') as f:json.dump(d,f,indent=2,ensure_ascii=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
c=load(H/'digital-trust-workbook-contract.json');old=load(B/'closure-receipt.json');baseline=load(B/'workbook-before.json');published=load(B/'final-workbook-readback.json');q=sqlite3.connect('/root/.hermes/shared/automation-continuity/queue.sqlite3');q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',(key,)).fetchone());source=json.loads(row['source']);assert row['state']=='running' and row['owner']=='supervisor:2464497'
j=next(x for x in load(Path('/root/.hermes/profiles/zeus/cron/jobs.json'))['jobs'] if x['id']=='2ee720363d7d');assert j['enabled'] is True and j['state']=='scheduled' and not j.get('fire_claim');assert native_contract_hash(j)==source['contract_hash']
assert c['account_scope_authority_message']=='1575252034100138135' and c['recurring_scope']['mode']=='active_tab_only' and not c['balance_views']['enabled'] and not c['payments_authorized'];assert not set(c['account_ids'])&set(c['archived_account_ids'])
f=(H/'writer.lock').open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
g.load_env();assert all(os.getenv(x)=='service_account' for x in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']);sa=g.load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['project_id']=='mgs-core-prod';token=g.service_account_access_token()
st,live=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',token,quota_project='mgs-core-prod');assert st==200;save('live-workbook.json',live)
ls={x['properties']['sheetId']:x for x in live['sheets']};bs={x['properties']['sheetId']:x for x in baseline['sheets']};ps={x['properties']['sheetId']:x for x in published['sheets']};assert set(ls)==set(bs)==set(ps)
frozen={str(k):authored(ls[k])==authored(bs[k]) for k in ls if k!=c['sheet_id']};assert all(frozen.values())
assert all(authored(ls[k])==authored(ps[k]) for k in ls),'authored_data_changed_after_previous_validation'
assert ls[c['sheet_id']]==ps[c['sheet_id']],'active_snapshot_changed_after_previous_validation'
accounts={}
for grid in ls[c['sheet_id']].get('data',[]):
 for rowdata in grid.get('rowData',[]):
  cells=rowdata.get('values',[])
  if cells and (m:=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''))):
   assert m[1] not in accounts;accounts[m[1]]=cells
assert set(accounts)==set(c['account_ids'])
hl=load(H/'pc1-pay-now-ledger.json');dl=load(H/'pc1-card-ledger.json');pending=[x['account_id'] for x in old['pending_ui']];assert set(pending)==set(source['pending_account_ids']) and set(pending)<=set(c['account_ids'])
for aid in c['pay_now_account_ids']:
 hr=hl['accounts'][aid];cell=accounts[aid][7]
 assert hr['read_at']==old['h_read_times'][aid] and hr['read_at'] in cell['note'] and hr['source']=='accounts_list_outstanding_balance' and Decimal(str(cell['userEnteredValue']['numberValue']))==Decimal(hr['amount'])
for aid in pending:
 proof=dl['accounts'].get(aid)
 assert not proof or datetime.fromisoformat(proof['read_at'])<datetime.fromisoformat(old['verified_at']),'newer_D_evidence_requires_reconciliation'
lease=json.loads(subprocess.run([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],capture_output=True,text=True,check=True).stdout);assert not lease['locked']
spec=importlib.util.spec_from_file_location('resolver_readonly','/root/mgs-agent/scripts/alerts-infra-failed-alert-resolver.py');resolver=importlib.util.module_from_spec(spec);spec.loader.exec_module(resolver);dt=resolver.load_token();authority=[]
for channel,mid in [('1563926766286803004','1575252034100138135'),('1563926766286803004','1575022093777637377'),('1563926766286803004','1563960345826037821'),('1569185140502954077','1569193434189668453')]:
 status,d=resolver.discord_api(dt,'GET',f'/channels/{channel}/messages/{mid}');assert status==200 and d['author']['id']=='344196393512075265' and d['channel_id']==channel
 authority.append({'id':d['id'],'channel_id':channel,'author_id':d['author']['id'],'content':d.get('content',''),'http_status':status})
save('authority-readback.json',authority)
result={'operation':key,'source_key':row['source_key'],'status':'waiting_resource','business_refresh_complete':False,'verified_at':datetime.now(timezone.utc).isoformat(),'reason':'native_human_save_as_dialog_still_present_navigation_not_safe','probe':str(P/'probe.json'),'visual_review':{'approved_meta_accounts_accessible':True,'approved_business_id':'155263197283282','unrelated_save_dialog_confirmed':True,'authentication_gate_demonstrated':False},'authority_readback':str(P/'authority-readback.json'),'contract_hash':native_contract_hash(j),'current_scope_ids':c['account_ids'],'pending_D_account_ids':pending,'pending_H_account_ids':[],'completed_layers_preserved':source['completed_financial_layers'],'previous_source_to_live_validation_retained':True,'live_all_authored_cells_equal_published_snapshot':True,'live_active_full_snapshot_equal':True,'frozen_sheets_full_authored_equality':frozen,'H35_original_times_ledger_live_exact':True,'D_ledger_newer_proof_found':False,'ledger_sha256':{'D':sha(H/'pc1-card-ledger.json'),'H':sha(H/'pc1-pay-now-ledger.json')},'writer_free':True,'lease_free':True,'supervisor_owner':row['owner'],'input_actions':0,'business_writes':0,'payments_executed':0,'billing_changes':0,'cron_changes':0,'tabs_created':0,'tabs_closed':0,'delivery_sent':False,'next_step':'Existing supervisor retries same D9 only after native dialog is gone and exact browser capture/URL navigation is consistent. Do not close human dialog or replay funding/invoices/H. Then final API (max two per event), full validation, canonical idempotent delivery with GET. Historical D5 remain separate.','evidence_files':['probe.json','windows.json','approved-elements.json','approved.png','save-dialog-elements.json','save-dialog.png','live-workbook.json','authority-readback.json']}
save('recovery-evidence.json',result);print(json.dumps({k:result[k] for k in ['status','reason','pending_D_account_ids','pending_H_account_ids','live_active_full_snapshot_equal','frozen_sheets_full_authored_equality','lease_free']}));print('evidence',P/'recovery-evidence.json')
