"""Reconcile this occurrence and capture desktop without input."""
import os, sys, json, shutil, subprocess, importlib.util, sqlite3, fcntl, re, hashlib
from pathlib import Path
from datetime import datetime, timezone
os.umask(0o077)
B=Path(__file__).parent; B.chmod(0o700)
ROOT=Path('/root/mgs-agent'); KEY='ce11800d217d22dba6a58dcc'
R=Path(shutil.which('hermes')).resolve().parents[2]; sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,str(ROOT/'scripts'))
from mgs_automation_continuity import native_contract_hash
os.environ['MGS_CONTINUITY_OPERATION_KEY']=KEY

def save(name,obj):
    with (B/name).open('x') as f: json.dump(obj,f,ensure_ascii=False,indent=2)

spec=importlib.util.spec_from_file_location('resolver',ROOT/'scripts/alerts-infra-failed-alert-resolver.py')
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
token=m.load_token(); authorities=[]
for ch,mid in [('1563926766286803004','1563960055504838767'),('1563926766286803004','1563960345826037821'),('1563926766286803004','1575022093777637377'),('1569185140502954077','1569193434189668453')]:
    status,d=m.discord_api(token,'GET',f'/channels/{ch}/messages/{mid}')
    assert status==200 and d['id']==mid and d['channel_id']==ch and d['author']['id']=='344196393512075265','authority mismatch'
    authorities.append({'id':mid,'channel_id':ch,'author_id':d['author']['id'],'status':status,'content':d['content']})
reg=json.loads((ROOT/'data/authorized-users.json').read_text())
assert '344196393512075265' in reg['agents']['zeus']['authorized_user_discord_ids']
save('authority-readback.json',{'messages':authorities,'registry_authorized':True})
c=json.loads((ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json').read_text())
jobs=json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text()); j=next(x for x in (jobs if isinstance(jobs,list)else jobs['jobs'])if x['id']=='2ee720363d7d')
assert native_contract_hash(j)=='2524af68edce24fe67783c7856030c1c2bd4b4e850df1cb6dc1d31c6cf8c6386'
assert j['enabled'] and j['state']=='scheduled' and not j.get('fire_claim')
assert c['recurring_scope']['mode']=='active_tab_only' and c['sheet_id']==794137639 and not c['balance_views']['enabled']
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True); q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',(KEY,)).fetchone()); source=json.loads(row['source'])
assert row['state']=='running'; os.kill(int(row['owner'].split(':')[1]),0)
assert source['scheduled_at']==j['last_dispatch']['scheduled_at']=='2026-11-25T14:02:00-05:00'
assert set(source['pending_account_ids'])<=set(c['account_ids'])
workers=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name)==os.getpid(): continue
    try: args=(p/'cmdline').read_bytes().decode(errors='replace').split('\0')
    except OSError: continue
    for arg in args:
        if Path(arg).name in ['refresh_workbook.py','regroup_funding.py','refresh_september_invoices.py','record_pc1_proof.py','read_pc1_billing_history.py','read_pc1_accounts_list.py','read_pc1_accounts_uia.py','publish_pay_now.py']:
            workers.append({'pid':int(p.name),'worker':Path(arg).name}); break
assert not workers,'concurrent financial worker'
with (ROOT/'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); fcntl.flock(f,fcntl.LOCK_UN)
closure=json.loads((B.parent/'closure-receipt.json').read_text())
ledger_path=ROOT/'data/meta-manual-payments/pc1-card-ledger.json'; ledger=json.loads(ledger_path.read_text())
related=[dict(r)for r in q.execute('select key,state,owner,due,attempts,failures from requests where key=?',('79cd082a20c22a736307765f',))]
hb=json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
rec={'observed_at':datetime.now(timezone.utc).isoformat(),'operation_key':KEY,'source_key':row['source_key'],'native_contract_hash':native_contract_hash(j),'job_enabled':j['enabled'],'fire_claim':j.get('fire_claim'),'scheduled_at':source['scheduled_at'],'next_run_at':j['next_run_at'],'writer_lock_free':True,'financial_workers':workers,'queue_owner':row['owner'],'owner_alive':True,'queue_state':row['state'],'consumer_heartbeat':hb,'related_historical_D_queue':related,'pending_H_account_ids':source['pending_H_account_ids'],'pending_recent_D_account_ids':source['pending_recent_D_account_ids'],'historical_D_not_adopted':c['pending_new_account_fields']['D_account_ids'],'ledger_sha256':hashlib.sha256(ledger_path.read_bytes()).hexdigest(),'card_ledger_active_proof_times':{k:{z:v for z,v in ledger.get('accounts',{}).get(k,{}).items()if z in ['read_at','verified_at','receipt','source']}for k in source['pending_recent_D_account_ids']},'completed_layers':source['completed_financial_layers'],'h_prepare':source['h_prepare'],'current_receipt_status':closure['status'],'active_ids':c['account_ids'],'live_h_targets':c['pay_now_account_ids'],'business_writes':0}
save('reconciliation.json',rec)
print(json.dumps({'authority':authorities,'reconciled':True,'pending_H':len(rec['pending_H_account_ids']),'pending_D':rec['pending_recent_D_account_ids']},ensure_ascii=False),flush=True)
os.environ['HERMES_CUA_DRIVER_CMD']=str(ROOT/'scripts/mgs-pc1-cua-driver-ssh.sh')
from tools.computer_use_tool import handle_computer_use, release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400
cua_backend._computer_use_max_image_dimension=lambda:3200
session=os.environ.get('HERMES_SESSION_ID')or 'recovery-ce11800-round1'; lock=ROOT/'scripts/mgs-pc1-computer-use-lock.py'
lease=subprocess.run([sys.executable,str(lock),'acquire','--agent','zeus','--session-id',session,'--thread-id',c['thread_id'],'--ttl','300'],capture_output=True,text=True)
if lease.returncode:
    save('probe-receipt.json',{'status':'waiting_resource','cause':'pc1_lease_busy','input_actions':0}); print('PC1 busy'); sys.exit(0)
def call(d):
    r=handle_computer_use(d,session_id=session); return json.loads(r)if isinstance(r,str)else r
try:
    raw=subprocess.run([str(ROOT/'scripts/mgs-pc1-cua-driver-ssh.sh'),'call','list_windows'],capture_output=True,text=True,timeout=50); assert raw.returncode==0
    ws=json.loads(raw.stdout)['windows']; bind=json.loads((ROOT/'data/meta-manual-payments/pc1-browser-surface.json').read_text())
    approved=[w for w in ws if w['pid']==bind['pid']and w['window_id']==bind['window_id']]; assert len(approved)==1,'approved handle unavailable'
    dialogs=[w for w in ws if re.search(r'Save As|Salvar como',str(w.get('title','')),re.I)]
    save('window-discovery.json',[{'pid':w['pid'],'window_id':w['window_id'],'approved':w in approved,'save_as_dialog':w in dialogs,'minimized':w.get('minimized')}for w in ws])
    captures={}
    for label,w in [('approved',approved[0])]+[(f'save-dialog-{i}',w)for i,w in enumerate(dialogs)]:
        d=call({'action':'capture','mode':'ax','pid':w['pid'],'window_id':w['window_id']}); assert not d.get('error'),'AX capture failed'
        full=json.loads(Path(d['elements_file']).read_text())if d.get('elements_file')else d; save(label+'-elements.json',full)
        v=call({'action':'capture','mode':'vision','pid':w['pid'],'window_id':w['window_id']}); assert not v.get('error')and v.get('screenshot_path'),'pixels failed'
        dest=B/(label+'.png'); shutil.copy2(v['screenshot_path'],dest)
        captures[label]={'pid':w['pid'],'window_id':w['window_id'],'screenshot':str(dest),'elements':str(B/(label+'-elements.json')),'width':v.get('width'),'height':v.get('height')}
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'captures':captures,'save_dialog_count':len(dialogs),'input_actions':0,'tabs_created':0,'tabs_closed':0}
    save('probe-receipt.json',result); print(json.dumps(result),flush=True)
finally:
    release_computer_use_session(session)
    rel=subprocess.run([sys.executable,str(lock),'release','--agent','zeus','--session-id',session],capture_output=True,text=True)
    st=subprocess.run([sys.executable,str(lock),'status'],capture_output=True,text=True)
    save('lease-release.json',{'release_exit':rel.returncode,'release':json.loads(rel.stdout),'readback':json.loads(st.stdout)})
