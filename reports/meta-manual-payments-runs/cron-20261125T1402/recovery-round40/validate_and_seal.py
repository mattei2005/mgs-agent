"""Read-only latest-layer validation; never replay superseded H or metrics."""
import os,sys,json,re,shutil,sqlite3,subprocess,hashlib,runpy,contextlib,fcntl
from pathlib import Path
from datetime import datetime,timezone,timedelta,date
from decimal import Decimal
from zoneinfo import ZoneInfo
os.umask(0o077)
B=Path(__file__).parent;ROOT=Path('/root/mgs-agent');KEY='ce11800d217d22dba6a58dcc'
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,str(ROOT/'scripts'))
import mgs_google_workspace_auth as g
from mgs_automation_continuity import native_contract_hash

def load(p):return json.loads(Path(p).read_text())
def save(n,v):
    with (B/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def mapping(s):
    out={}
    for grid in s.get('data',[]):
        for row in grid.get('rowData',[]):
            cs=row.get('values',[])
            m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note','')) if cs else None
            if m:assert m[1] not in out;out[m[1]]=cs
    return out
def uv(c):return c.get('userEnteredValue',{})
rec=load(B/'reconciliation.json');source=rec['source'];later=load(B/'newer-native-receipt.json')
visual=load(B/'visual-verification.json');assert visual['native_dialog']['open_pixels'] and not visual['approved_surface']['authentication_gate_visible']
assert visual['approved_surface']['business_id_pixels']=='155263197283282'
assert 'Rodolfo' in (B/'approved-elements.json').read_text()
probe=load(B/'probe-receipt.json');lease=load(B/'lease-release.json')
assert probe['dialog_count']==1 and probe['input_actions']==0 and not lease['readback']['locked']
c=load(ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json')
assert c['account_ids']==rec['active_ids'] and c['pay_now_account_ids']==rec['h_targets']
g.load_env();assert all(os.getenv(k)=='service_account' for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
sa=g.load_service_account();assert (sa['client_email'],sa['project_id'])==('mgsagent@mgs-core-prod.iam.gserviceaccount.com','mgs-core-prod')
with (ROOT/'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    token=g.service_account_access_token()
    st,meta=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=trashed,capabilities(canEdit)',token,quota_project='mgs-core-prod');assert st==200 and not meta.get('trashed') and meta['capabilities']['canEdit']
    st,book=g.api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']+'?includeGridData=true',token,quota_project='mgs-core-prod');assert st==200;save('workbook-live.json',book)
    aa={s['properties']['sheetId']:s for s in book['sheets']}
    nb=ROOT/'reports/meta-manual-payments-runs/cron-20261125T2102'
    expected=load(nb/'final-workbook-readback.json');bb={s['properties']['sheetId']:s for s in expected['sheets']}
    assert set(aa)==set(bb) and all(aa[k]==bb[k] for k in aa),'live divergence from newer native readback'
    orig=load(B.parent/'final-workbook-readback.json');oo={s['properties']['sheetId']:s for s in orig['sheets']}
    frozen={str(k):aa[k]==oo[k] for k in aa if k!=c['sheet_id']};assert all(frozen.values())
    am=mapping(aa[c['sheet_id']]);assert set(am)==set(c['account_ids'])
    plan=load(Path(later['api_run_dir'])/'plan.json');assert set(p['id'] for p in plan['planned'])==set(am)
    iv=load(Path(later['invoices']['source_run_dir'])/'invoice-collection.json');assert iv==load(ROOT/'data/meta-manual-payments/september-invoice-ledger.json')
    hl=load(ROOT/'data/meta-manual-payments/pc1-pay-now-ledger.json');dl=load(ROOT/'data/meta-manual-payments/pc1-card-ledger.json')['accounts']
    hd=Path(later['h_run_dir']);vm=load(hd/'visual-verification.json');assert set(vm['verified_account_ids'])==set(c['pay_now_account_ids'])
    reconciled_h={}
    for p in plan['planned']:
        aid=p['id'];cs=am[aid];assert uv(cs[2])=={'stringValue':p['default']}
        for col,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(uv(cs[col])['numberValue']))==Decimal(p[key]) and plan['collected_at'] in cs[col]['note']
        today=datetime.fromisoformat(plan['collected_at']).astimezone(ZoneInfo(p['timezone'])).date()
        assert p['month_period']=={'since':c['month_since'],'until':min(today,date.fromisoformat(c['month_until'])).isoformat()}
        assert p['average_period']=={'since':(today-timedelta(days=3)).isoformat(),'until':(today-timedelta(days=1)).isoformat()}
        inv=iv['by_account'].get(aid)
        if inv:
            ev=inv['invoice'] if Decimal(inv['due'])>0 and inv['status']!='Paid' else None
            assert uv(cs[4]).get('stringValue')==ev and Decimal(str(uv(cs[5])['numberValue']))==Decimal(inv['due'])
        else:assert not uv(cs[4]) and uv(cs[5])==({'numberValue':0} if p['method']=='Linha de crédito' else {})
        if aid in c['pay_now_account_ids']:
            h=hl['accounts'][aid];rr=load(hd/(aid+'-receipt.json'));check=vm['accounts_list_checks'][aid]
            assert h['read_at']==rr['read_at']==later['h_read_times'][aid]
            assert datetime.fromisoformat(h['read_at'])>datetime.fromisoformat(source['scheduled_at'])
            assert rr['account_id']==aid and rr['business_id']==c['business_id']
            assert check['row_account_id']==aid and check['business_id']==c['business_id'] and check['valid_billing_list']
            assert check['balance_label']=='Outstanding balance' and check['authority_message_id']=='1570815017794674749'
            assert h['source']==rr['source']=='accounts_list_outstanding_balance'
            assert Decimal(h['amount'])==Decimal(rr['amount'])==Decimal(check['balance_usd'])==Decimal(str(uv(cs[7])['numberValue'])) and h['read_at'] in cs[7]['note']
            assert Path(rr['screenshot']).is_file() and Path(rr['text_path']).is_file()
            reconciled_h[aid]={'read_at':h['read_at'],'amount':h['amount'],'receipt':str(hd/(aid+'-receipt.json')),'source':h['source']}
        d=dl.get(aid)
        if d:
            card=d.get('latest_card')
            if card:assert Decimal(str(uv(cs[3])['numberValue']))==Decimal(card['amount']) and d['read_at'] in cs[3]['note'] and card['method'] in cs[3]['note']
            else:assert not uv(cs[3]) and d['status']=='no_charge_located'
    script=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts/validate_workbook_readonly.py')
    sys.argv=[str(script),'--spreadsheet-id',c['spreadsheet_id'],'--sheet-id',str(c['sheet_id']),'--business-id',c['business_id']]
    with (B/'structural-readonly.log').open('x') as out,contextlib.redirect_stdout(out):runpy.run_path(str(script),run_name='__main__')
    structural=[json.loads(l) for l in (B/'structural-readonly.log').read_text().splitlines() if l.startswith('{')][-1];assert structural['status']=='snapshot_readback_pass'
    fcntl.flock(f,fcntl.LOCK_UN)
assert set(reconciled_h)==set(source['pending_H_account_ids'])
current_pending={p['account_id'] for p in load(ROOT/'data/meta-manual-payments/last-refresh.json')['pending_ui']}
assert set(source['pending_recent_D_account_ids'])<=current_pending
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',(KEY,)).fetchone());assert row['owner']==rec['queue_owner'] and row['state']=='running' and json.loads(row['source'])==source;os.kill(int(row['owner'].split(':')[1]),0)
j=next(x for x in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs'] if x['id']==source['job_id']);assert native_contract_hash(j)==source['contract_hash'] and j['enabled'] and not j.get('fire_claim')
lease_now=json.loads(subprocess.run([sys.executable,str(ROOT/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,check=True).stdout);assert not lease_now['locked']
cron=subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True);consumers=[l for l in cron.stdout.splitlines() if not l.lstrip().startswith('#') and 'alerts-infra-failed-alert-resolver' in l];assert len(consumers)==1
queues=[{k:r[k] for k in ['key','source_key','state','owner','due','failures']} for r in q.execute('select * from requests where key in (?,?,?)',(KEY,source['historical_D_request_key'],later['continuity_key']))]
validation={'status':'readonly_newer_native_layers_live_validated','account_count':len(am),'live_ids':sorted(am),'all_sheets_equal_newer_native_snapshot':True,'frozen_sheets_equal_original_occurrence':frozen,'latest_C_G_I_J_exact':True,'latest_E_F_exact':True,'existing_D_ledger_exact':True,'H35_superseded_by_newer_native_proofs':reconciled_h,'pending_recent_D_original_ids':source['pending_recent_D_account_ids'],'later_tick_pending_ids_separate':sorted(current_pending-set(source['pending_recent_D_account_ids'])),'structural':structural,'business_writes':0}
save('live-validation.json',validation)
e={'observed_at':datetime.now(timezone.utc).isoformat(),'operation_key':KEY,'source_key':row['source_key'],'mode':'resume_safe','status':'waiting_resource','cause':'pc1_native_save_as_dialog_still_open','authority_receipt':str(B/'authority-readback.json'),'reconciliation':str(B/'reconciliation.json'),'live_validation':str(B/'live-validation.json'),'native_contract_hash':source['contract_hash'],'original_H_targets_preserved':source['pending_H_account_ids'],'pending_H_account_ids':[],'H_covered_by_newer_native_occurrence':later['continuity_source_key'],'H_newer_receipts_verified':len(reconciled_h),'pending_recent_D_account_ids':source['pending_recent_D_account_ids'],'historical_D_separate_request':source['historical_D_request_key'],'latest_native_source_readback':str(B/'newer-native-receipt.json'),'surface':visual,'lease_free_readback':True,'queue_owner':row['owner'],'owner_alive':True,'consumer_heartbeat':json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0]),'consumer_schedule':' '.join(consumers[0].split()[:5]),'queue_records':queues,'queue_transition_owner':'existing supervisor; no direct queue mutation','input_actions':0,'tabs_created':0,'tabs_closed':0,'business_writes':0,'payments':0,'billing_changes':0,'cron_changes':0,'infrastructure_changes':0,'completed_layers_replayed':False,'business_complete':False,'delivery_complete':False,'next_step':'Preserve same occurrence and supervisor resource backoff. H35 is already covered by exact newer 21:02 proofs and live GET: do not recollect or overwrite. Only original D2 remains in this occurrence, reconcile later D owner before UI navigation after Save As no longer blocks. Preserve separate historical D and new account. Canonical final API reconcile max2/event, independent full validation, canonical occurrence delivery with GET only after genuine recovery.'}
save('recovery-evidence.json',e)
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in B.iterdir() if p.is_file()};save('evidence-sha256.json',manifest)
assert all(hashlib.sha256((B/n).read_bytes()).hexdigest()==h for n,h in manifest.items())
print(json.dumps({'status':e['status'],'accounts':len(am),'H_newer_proofs_reconciled':len(reconciled_h),'H_pending':0,'original_D_pending':len(source['pending_recent_D_account_ids']),'hashes_verified':True,'lease_free':True,'checkpoint':str(B/'recovery-evidence.json'),'business_writes':0}))
