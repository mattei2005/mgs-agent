"""Read-only live workbook reconciliation and resource-gate checkpoint."""
import os,sys,json,re,shutil,sqlite3,subprocess,hashlib,runpy,contextlib,fcntl
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
os.umask(0o077)
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');KEY='ce11800d217d22dba6a58dcc'
launcher=shutil.which('hermes');assert launcher
R=Path(launcher).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,str(ROOT/'scripts'))
import mgs_google_workspace_auth as g
from mgs_automation_continuity import native_contract_hash

def load(p):return json.loads(Path(p).read_text())
def save(n,v):
    with (B/n).open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2)
def mapping(s):
    out={}
    for grid in s.get('data',[]):
        for row in grid.get('rowData',[]):
            cs=row.get('values',[])
            m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))if cs else None
            if m:assert m[1]not in out;out[m[1]]=cs
    return out
def uv(c):return c.get('userEnteredValue',{})
def authored_row(cs):return [{k:v for k,v in c.items()if k in ('userEnteredValue','note','userEnteredFormat','textFormatRuns')}for c in cs]
rec=load(B/'reconciliation.json');probe=load(B/'probe-receipt.json');lease=load(B/'lease-release.json')
assert probe['dialog_count']==1 and probe['input_actions']==0
assert lease['release_exit']==0 and not lease['readback']['locked']
c=load(ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json');source=rec['source']
assert c['account_ids']==rec['active_ids'] and c['pay_now_account_ids']==rec['h_targets']
g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
sa=g.load_service_account();assert(sa['client_email'],sa['project_id'])==('mgsagent@mgs-core-prod.iam.gserviceaccount.com','mgs-core-prod')
with(ROOT/'data/meta-manual-payments/writer.lock').open('r')as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    token=g.service_account_access_token()
    st,meta=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=trashed,capabilities(canEdit)',token,quota_project='mgs-core-prod');assert st==200 and not meta.get('trashed')and meta['capabilities']['canEdit']
    st,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',token,quota_project='mgs-core-prod');assert st==200;save('workbook-live.json',book)
    aa={s['properties']['sheetId']:s for s in book['sheets']}
    adddir=ROOT/'reports/meta-manual-payments-runs/add1-1575252034100138135';addafter=load(adddir/'workbook-after.json');ab={s['properties']['sheetId']:s for s in addafter['sheets']}
    assert set(aa)==set(ab)
    am=mapping(aa[c['sheet_id']]);assert set(am)==set(c['account_ids']) and len(am)==len(c['account_ids'])
    whole_after_inclusion={str(k):aa[k]==ab[k]for k in aa};assert all(whole_after_inclusion.values()),'live diverges from inclusion receipt; preserve snapshot, no write'
    original=load(B.parent/'final-workbook-readback.json');orig={s['properties']['sheetId']:s for s in original['sheets']};bm=mapping(orig[c['sheet_id']])
    assert set(am)-set(bm)=={'1770569568407466'} and not set(bm)-set(am)
    assert all(authored_row(am[k])==authored_row(bm[k])for k in bm),'original cells changed beyond row insertion'
    frozen={str(k):aa[k]==orig[k]for k in aa if k!=c['sheet_id']};assert all(frozen.values())
    plan=load(Path(source['completed_financial_layers']['C_G_I_J'])/'plan.json');assert set(p['id']for p in plan['planned'])==set(bm)
    iv=load(Path(source['completed_financial_layers']['E_F'])/'invoice-collection.json')
    hl=load(ROOT/'data/meta-manual-payments/pc1-pay-now-ledger.json')['accounts'];dl=load(ROOT/'data/meta-manual-payments/pc1-card-ledger.json')['accounts']
    for p in plan['planned']:
        aid=p['id'];cs=am[aid];assert uv(cs[2])=={'stringValue':p['default']}
        for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(uv(cs[col])['numberValue']))==Decimal(p[key])and plan['collected_at']in cs[col]['note']
        inv=iv['by_account'].get(aid)
        if inv:
            expected=inv['invoice']if Decimal(inv['due'])>0 and inv['status']!='Paid'else None
            assert uv(cs[4]).get('stringValue')==expected and Decimal(str(uv(cs[5])['numberValue']))==Decimal(inv['due'])
        else:assert not uv(cs[4])and uv(cs[5])==({'numberValue':0}if p['method']=='Linha de crédito'else{})
        if aid in c['pay_now_account_ids']:
            h=hl[aid];assert Decimal(str(uv(cs[7])['numberValue']))==Decimal(h['amount'])and h['read_at']in cs[7]['note']
        d=dl.get(aid)
        if d:
            card=d.get('latest_card')
            if card:assert Decimal(str(uv(cs[3])['numberValue']))==Decimal(card['amount'])and d['read_at']in cs[3]['note']and card['method']in cs[3]['note']
            else:assert not uv(cs[3])and d['status']=='no_charge_located'
    script=ROOT.parent/'.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts/validate_workbook_readonly.py'
    sys.argv=[str(script),'--spreadsheet-id',c['spreadsheet_id'],'--sheet-id',str(c['sheet_id']),'--business-id',c['business_id']]
    with(B/'structural-readonly.log').open('x')as out,contextlib.redirect_stdout(out):runpy.run_path(str(script),run_name='__main__')
    structural=[json.loads(l)for l in(B/'structural-readonly.log').read_text().splitlines()if l.startswith('{')][-1];assert structural['status']=='snapshot_readback_pass'
    fcntl.flock(f,fcntl.LOCK_UN)
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',(KEY,)).fetchone());assert row['owner']==rec['queue_owner']and row['state']=='running';os.kill(int(row['owner'].split(':')[1]),0)
assert json.loads(row['source'])==source
jobs=load('/root/.hermes/profiles/zeus/cron/jobs.json');j=next(x for x in jobs['jobs']if x['id']==source['job_id']);assert native_contract_hash(j)==source['contract_hash']and not j.get('fire_claim')and j['enabled']
lease_now=json.loads(subprocess.run([sys.executable,str(ROOT/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert not lease_now['locked']
cron=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True);consumers=[l for l in cron.stdout.splitlines()if not l.lstrip().startswith('#')and'alerts-infra-failed-alert-resolver'in l];assert len(consumers)==1
validation={'status':'readonly_live_scope_and_preservation_validated','live_account_ids':sorted(am),'account_count':len(am),'original_accounts_preserved_by_id':sorted(bm),'new_account_preserved_not_adopted':list(set(am)-set(bm)),'all_sheets_equal_to_post_inclusion_snapshot':whole_after_inclusion,'frozen_sheets_equal_to_original_occurrence':frozen,'original_C_G_I_J_exact':True,'original_E_F_exact':True,'existing_H_ledger_exact':True,'existing_D_ledger_exact':True,'structural':structural,'google_write_calls':0,'meta_calls':0,'business_writes':0}
save('live-validation.json',validation)
e={'observed_at':datetime.now(timezone.utc).isoformat(),'operation_key':KEY,'source_key':row['source_key'],'mode':'resume_safe','status':'waiting_resource','cause':'pc1_native_save_as_dialog_still_open','authority_receipt':str(B/'authority-readback.json'),'reconciliation':str(B/'reconciliation.json'),'live_validation':str(B/'live-validation.json'),'native_contract_hash':source['contract_hash'],'pending_H_account_ids':source['pending_H_account_ids'],'pending_recent_D_account_ids':source['pending_recent_D_account_ids'],'historical_D_separate_request':source['historical_D_request_key'],'completed_financial_layers_preserved':source['completed_financial_layers'],'h_prepare':source['h_prepare'],'surface':{'business_id_pixels':'155263197283282','page':'Accounts','header':'Outstanding balance','profile_Rodolfo_in_AX':'Rodolfo'in(B/'approved-elements.json').read_text(),'save_as_open_pixels':True,'dialog_origin_unproved':True,'dialog_preserved':True,'authentication_gate_proved':False,'screenshots_inspected':[str(B/'approved.png'),str(B/'native-dialog-0.png')]},'lease_free_readback':True,'queue_owner':row['owner'],'owner_alive':True,'consumer_heartbeat':json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0]),'consumer_schedule':' '.join(consumers[0].split()[:5]),'queue_transition_owner':'existing supervisor, no direct queue mutation','input_actions':0,'tabs_created':0,'tabs_closed':0,'business_writes':0,'payments':0,'billing_changes':0,'cron_changes':0,'infrastructure_changes':0,'gateway_restarts':0,'completed_layers_replayed':False,'native_scope_amendment_reconciled':True,'next_step':'Existing supervisor preserves resource backoff and same occurrence. Recheck dialog/current ownership; only after resource available collect missing original H35/D2, preserve newer proofs and separate historical D owner, then canonical API final reconcile max2/event and independent validation/delivery. No duplicate report.'}
save('recovery-evidence.json',e)
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in B.iterdir()if p.is_file()and not p.name.endswith('.log')};save('evidence-sha256.json',manifest)
assert all(hashlib.sha256((B/n).read_bytes()).hexdigest()==h for n,h in load(B/'evidence-sha256.json').items())
print(json.dumps({'status':e['status'],'checkpoint':str(B/'recovery-evidence.json'),'hashes_verified':True,'accounts':len(am),'original_accounts_preserved':len(bm),'h_pending':len(source['pending_H_account_ids']),'d_pending':len(source['pending_recent_D_account_ids']),'lease_free':True,'business_writes':0}))
