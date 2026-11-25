"""Same-operation reconciliation and read-only PC1 surface evidence."""
import os, sys, json, shutil, subprocess, importlib.util, fcntl, sqlite3, re
from pathlib import Path
from datetime import datetime, timezone
B=Path(__file__).parent
B.chmod(0o700)
ROOT=Path('/root/mgs-agent')
R=Path(shutil.which('hermes')).resolve().parents[2]
sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,str(ROOT/'scripts'))
from mgs_automation_continuity import native_contract_hash

def save(n,d):
 p=B/n
 assert not p.exists(), 'immutable artifact exists'
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)

spec=importlib.util.spec_from_file_location('resolver',ROOT/'scripts/alerts-infra-failed-alert-resolver.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
token=m.load_token()
a=[]
for channel,mid in [('1563926766286803004','1563960055504838767'),('1563926766286803004','1563960345826037821'),('1563926766286803004','1575022093777637377'),('1569185140502954077','1569193434189668453')]:
 status,d=m.discord_api(token,'GET',f'/channels/{channel}/messages/{mid}')
 assert status==200 and d['id']==mid and d['channel_id']==channel and d['author']['id']=='344196393512075265', 'authority readback failed'
 a.append({'id':mid,'channel_id':channel,'author_id':d['author']['id'],'status':status,'content':d['content']})
reg=json.loads((ROOT/'data/authorized-users.json').read_text())
assert '344196393512075265' in reg['agents']['zeus']['authorized_user_discord_ids']
save('authority-readback.json',{'messages':a,'current_registry_rodolfo_authorized':True})
c=json.loads((ROOT/'data/meta-manual-payments/digital-trust-workbook-contract.json').read_text())
jobs=json.loads(Path('/root/.hermes/profiles/zeus/cron/jobs.json').read_text())
j=next(x for x in (jobs if isinstance(jobs,list) else jobs['jobs']) if x['id']=='2ee720363d7d')
assert native_contract_hash(j)=='2524af68edce24fe67783c7856030c1c2bd4b4e850df1cb6dc1d31c6cf8c6386'
assert j['enabled'] and not j.get('fire_claim') and j['last_dispatch']['scheduled_at']=='2026-11-25T08:02:00-05:00'
assert c['recurring_scope']['mode']=='active_tab_only' and c['sheet_id']==794137639 and not c['balance_views']['enabled']
pending=c['pending_new_account_fields']['D_account_ids']
assert set(pending)==set(['1034081997659047','1492168699397108','1542257646409395','1663268201836138','1754588462350629']) and set(pending)<=set(c['account_ids'])
ledger=json.loads((ROOT/'data/meta-manual-payments/pc1-card-ledger.json').read_text())['accounts']
with (ROOT/'data/meta-manual-payments/writer.lock').open('r') as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
workers=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try: cmd=(p/'cmdline').read_bytes().decode(errors='replace').split('\x00')
 except OSError:continue
 for arg in cmd:
  if Path(arg).name in ['refresh_workbook.py','regroup_funding.py','refresh_september_invoices.py','record_pc1_proof.py','read_pc1_billing_history.py','read_pc1_accounts_list.py','publish_pay_now.py']:
   workers.append({'pid':int(p.name),'worker':Path(arg).name});break
assert not workers,'financial worker active'
q=sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro',uri=True);q.row_factory=sqlite3.Row
row=dict(q.execute('select * from requests where key=?',('79cd082a20c22a736307765f',)).fetchone())
owner=int(row['owner'].split(':')[1]);os.kill(owner,0)
hb=json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0])
rec={'observed_at':datetime.now(timezone.utc).isoformat(),'native_contract_hash':native_contract_hash(j),'job_enabled':j['enabled'],'job_state':j['state'],'fire_claim':j.get('fire_claim'),'last_dispatch_scheduled_at':j['last_dispatch']['scheduled_at'],'next_run_at':j['next_run_at'],'later_native_tick_observed':False,'writer_lock_free':True,'financial_worker_processes_found':workers,'pending_ledger_entries':{k:ledger.get(k) for k in pending},'pending_account_ids':pending,'pending_H_account_ids':c['pending_new_account_fields']['H_account_ids'],'active_account_count':len(c['account_ids']),'last_refresh':json.loads((ROOT/'data/meta-manual-payments/last-refresh.json').read_text()),'queue':{k:row[k] for k in ['state','owner','attempts','failures','due','lease_until']},'consumer_heartbeat':hb,'queue_owner_alive':True}
save('reconciliation.json',rec)
print(json.dumps({'authority_verified':True,'reconciliation_file':str(B/'reconciliation.json'),'pending_ids':pending,'ledger_entries_present':[k for k in pending if ledger.get(k)]}))
os.environ['HERMES_CUA_DRIVER_CMD']=str(ROOT/'scripts/mgs-pc1-cua-driver-ssh.sh')
from tools.computer_use_tool import handle_computer_use, release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400
cua_backend._computer_use_max_image_dimension=lambda:3200
session=os.environ.get('HERMES_SESSION_ID') or 'recovery-79cd082a-round17'
lock=ROOT/'scripts/mgs-pc1-computer-use-lock.py'
lease=subprocess.run([sys.executable,str(lock),'acquire','--agent','zeus','--session-id',session,'--thread-id','1563926766286803004','--ttl','300'],capture_output=True,text=True)
if lease.returncode:
 save('probe-receipt.json',{'status':'waiting_resource','cause':'pc1_lease_busy','lease':json.loads(lease.stdout)})
 print(json.dumps({'status':'waiting_resource','cause':'pc1_lease_busy'}));sys.exit(0)
def call(d):
 raw=handle_computer_use(d,session_id=session)
 return json.loads(raw) if isinstance(raw,str) else raw
try:
 raw=subprocess.run([str(ROOT/'scripts/mgs-pc1-cua-driver-ssh.sh'),'call','list_windows'],capture_output=True,text=True,timeout=50)
 assert raw.returncode==0,'window discovery transport failure'
 windows=json.loads(raw.stdout)['windows']
 bind=json.loads((ROOT/'data/meta-manual-payments/pc1-browser-surface.json').read_text())
 approved=[w for w in windows if w['pid']==bind['pid'] and w['window_id']==bind['window_id']]
 assert len(approved)==1,'approved handle not live'
 dialogs=[w for w in windows if re.search(r'Save As|Salvar como',str(w.get('title','')),re.I)]
 save('window-discovery.json',[{'pid':w['pid'],'window_id':w['window_id'],'minimized':w.get('minimized'),'approved':w in approved,'save_as_dialog':w in dialogs} for w in windows])
 captures={}
 for label,w in [('approved',approved[0])]+[(f'save-dialog-{i}',w)for i,w in enumerate(dialogs)]:
  d=call({'action':'capture','mode':'ax','pid':w['pid'],'window_id':w['window_id']})
  assert not d.get('error'),'AX capture failed'
  full=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d
  save(label+'-elements.json',full)
  v=call({'action':'capture','mode':'vision','pid':w['pid'],'window_id':w['window_id']})
  assert not v.get('error') and v.get('screenshot_path'),'pixel capture failed'
  dest=B/(label+'.png');shutil.copy2(v['screenshot_path'],dest);dest.chmod(0o600)
  captures[label]={'pid':w['pid'],'window_id':w['window_id'],'screenshot':str(dest),'elements':str(B/(label+'-elements.json')),'width':v.get('width'),'height':v.get('height')}
 result={'observed_at':datetime.now(timezone.utc).isoformat(),'captures':captures,'save_dialog_count':len(dialogs),'input_actions':0,'tabs_created':0,'tabs_closed':0}
 save('probe-receipt.json',result);print(json.dumps(result))
finally:
 release_computer_use_session(session)
 rel=subprocess.run([sys.executable,str(lock),'release','--agent','zeus','--session-id',session],capture_output=True,text=True)
 status=subprocess.run([sys.executable,str(lock),'status'],capture_output=True,text=True)
 save('lease-release.json',{'release_exit':rel.returncode,'release':json.loads(rel.stdout),'readback':json.loads(status.stdout)})
