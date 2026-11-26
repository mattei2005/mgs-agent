"""Evidence-only same-occurrence desktop/authentication probe; no business writes."""
import os, sys, json, shutil, subprocess, sqlite3, fcntl, importlib.util, contextlib
from pathlib import Path
from datetime import datetime, timezone
os.umask(0o077)
sys.dont_write_bytecode=True
ROOT=Path('/root/mgs-agent'); B=Path(__file__).parent; KEY='7471f3223a3e11e7840702b7'
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R));sys.path.insert(0,str(ROOT/'scripts'))
with (B/'runtime.log').open('a') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
    from pm.environments import activate_dependencies
    activate_dependencies(R)

def load(p):return json.loads(Path(p).read_text())
def save(name,value):
    with (B/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
from mgs_automation_continuity import native_contract_hash
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',(KEY,)).fetchone());source=json.loads(row['source'])
assert row['state']=='running';os.kill(int(row['owner'].split(':')[1]),0)
c=load(ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json')
j=next(j for j in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs'] if j['id']==source['job_id'])
assert j['enabled'] and j['state']=='scheduled' and not j.get('fire_claim')
assert native_contract_hash(j)==source['contract_hash']
assert source['scheduled_at']==j['last_dispatch']['scheduled_at']=='2026-11-26T14:02:00-05:00'
assert c['sheet_id']==794137639 and c['recurring_scope']['mode']=='active_tab_only' and not c['balance_views']['enabled']
assert set(source['pending_account_ids'])<=set(c['account_ids'])
assert set(source['pending_H_account_ids'])==set(c['pay_now_account_ids'])
spec=importlib.util.spec_from_file_location('readonly_resolver',ROOT/'scripts/alerts-infra-failed-alert-resolver.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
a=[]; token=m.load_token()
for ch,mid in [('1563926766286803004','1563960055504838767'),('1563926766286803004','1563960345826037821'),('1563926766286803004','1575022093777637377'),('1569185140502954077','1569193434189668453'),('1563926766286803004','1575252034100138135')]:
    status,d=m.discord_api(token,'GET',f'/channels/{ch}/messages/{mid}')
    assert status==200 and d['id']==mid and d['channel_id']==ch and d['author']['id']=='344196393512075265'
    a.append({'id':mid,'channel_id':ch,'author_id':d['author']['id'],'http_status':status,'content':d['content']})
assert '344196393512075265' in load(ROOT/'data/authorized-users.json')['agents']['zeus']['authorized_user_discord_ids']
save('authority-readback.json',{'messages':a,'registry_authorized':True})
workers=[]
for p in Path('/proc').glob('[0-9]*/cmdline'):
    try:args=p.read_bytes().split(b'\0')
    except OSError:continue
    names=['refresh_workbook.py','refresh_september_invoices.py','regroup_funding.py','publish_pay_now.py','record_pc1_proof.py','read_pc1_accounts_list.py','read_pc1_billing_history.py']
    for n in names:
        if any(v.endswith(('/'+n).encode())for v in args):workers.append({'pid':int(p.parts[2]),'worker':n});break
assert not workers
with (ROOT/'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
pre=load(source['checkpoint'])
hl=load(ROOT/'data/meta-manual-payments/pc1-pay-now-ledger.json').get('accounts',{})
dl=load(ROOT/'data/meta-manual-payments/pc1-card-ledger.json').get('accounts',{})
def proof(ledger,ids):return {i:{k:v for k,v in ledger.get(i,{}).items()if k in ['read_at','verified_at','source','amount','receipt']}for i in ids}
save('reconciliation.json',{'at':datetime.now(timezone.utc).isoformat(),'operation_key':KEY,'source_key':row['source_key'],'source':source,'owner':row['owner'],'owner_alive':True,'native_fire_claim':j.get('fire_claim'),'native_hash_matches':True,'next_run_at':j['next_run_at'],'workers':workers,'writer_lock_free':True,'active_ids':c['account_ids'],'pending_H_account_ids':source['pending_H_account_ids'],'pending_recent_D_account_ids':source['pending_recent_D_account_ids'],'H_current_ledger':proof(hl,source['pending_H_account_ids']),'D_current_ledger':proof(dl,source['pending_recent_D_account_ids']),'last_refresh':load(ROOT/'data/meta-manual-payments/last-refresh.json'),'closure_receipt_status':pre['status'],'consumer_heartbeat':json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0]),'other_occurrences':[dict(r)for r in q.execute('select key,state,owner,updated from requests where key in (%s)'%','.join('?'for _ in source['prior_occurrence_keys']),source['prior_occurrence_keys'])]})
print(json.dumps({'authority_verified':True,'active_count':len(c['account_ids']),'H_pending_count':len(source['pending_H_account_ids']),'D_pending_count':len(source['pending_recent_D_account_ids']),'owner':row['owner'],'writer_lock_free':True}),flush=True)
os.environ['MGS_CONTINUITY_OPERATION_KEY']=KEY
os.environ['HERMES_CUA_DRIVER_CMD']=str(ROOT/'scripts/mgs-pc1-cua-driver-ssh.sh')
lock=ROOT/'scripts/mgs-pc1-computer-use-lock.py';session=os.environ.get('HERMES_SESSION_ID')or'probe-7471-20261126T1420'
lease=subprocess.run([sys.executable,str(lock),'acquire','--agent','zeus','--session-id',session,'--thread-id',source['thread_id'],'--ttl','180'],capture_output=True,text=True)
save('lease-acquire.json',{'exit_code':lease.returncode,'result':json.loads(lease.stdout)})
if lease.returncode:print('PC1 ocupado',flush=True);sys.exit(0)
try:
    with (B/'runtime.log').open('a')as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        from tools.computer_use_tool import handle_computer_use,release_computer_use_session
        from tools.computer_use import cua_backend
        cua_backend._computer_use_max_image_dimension=lambda:3200
    discoveries=[]
    for i in range(2):
        p=subprocess.run([str(ROOT/'scripts/mgs-pc1-cua-driver-ssh.sh'),'call','list_windows'],capture_output=True,text=True,timeout=50)
        assert p.returncode==0,'desktop discovery failed'
        ws=json.loads(p.stdout)['windows']
        discoveries.append([{k:w.get(k)for k in ['pid','window_id','app_name','is_on_screen','minimized']}for w in ws])
    save('window-discovery.json',discoveries)
    chrome=[w for w in ws if 'chrome' in w.get('app_name','').lower()]
    candidates=chrome+[w for w in ws if w.get('app_name','').lower()=='lockapp.exe'or'credential' in w.get('app_name','').lower()]
    captures=[]
    for i,w in enumerate(candidates):
        label='window-'+str(i)
        item={k:w.get(k)for k in ['pid','window_id','app_name']}
        for mode in ['ax','vision']:
            with (B/'runtime.log').open('a')as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
                raw=handle_computer_use({'action':'capture','mode':mode,'pid':w['pid'],'window_id':w['window_id']},session_id=session)
            d=json.loads(raw)if isinstance(raw,str)else raw
            save(label+'-'+mode+'.json',d)
            if d.get('elements_file'):shutil.copy2(d['elements_file'],B/(label+'-elements.json'))
            if d.get('screenshot_path'):
                dest=B/(label+'-'+mode+'.png');shutil.copy2(d['screenshot_path'],dest);item[mode+'_screenshot']=str(dest)
            item[mode+'_error']=d.get('error');item[mode+'_ok']=d.get('ok')
        captures.append(item)
    save('probe-receipt.json',{'at':datetime.now(timezone.utc).isoformat(),'mode':'probe_only','operation_key':KEY,'chrome_windows':len(chrome),'captures':captures,'input_actions':0,'business_writes':0,'tabs_modified':0,'auth_ready':False,'visual_review_pending':True})
    print(json.dumps({'chrome_windows':len(chrome),'captures':captures,'input_actions':0}),flush=True)
finally:
    with (B/'runtime.log').open('a')as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        if 'release_computer_use_session'in globals():release_computer_use_session(session)
    release=subprocess.run([sys.executable,str(lock),'release','--agent','zeus','--session-id',session],capture_output=True,text=True)
    status=subprocess.run([sys.executable,str(lock),'status'],capture_output=True,text=True)
    save('lease-release.json',{'release_exit':release.returncode,'release':json.loads(release.stdout),'readback':json.loads(status.stdout)})
