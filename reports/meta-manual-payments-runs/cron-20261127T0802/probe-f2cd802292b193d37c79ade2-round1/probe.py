"""Same-occurrence read-only desktop probe. Only local evidence and lease state."""
import os, sys, json, shutil, subprocess, sqlite3, fcntl, contextlib, hashlib
from pathlib import Path
from datetime import datetime, timezone
os.umask(0o077)
sys.dont_write_bytecode = True
ROOT = Path('/root/mgs-agent')
B = Path(__file__).parent
KEY = 'f2cd802292b193d37c79ade2'
def load(p):
    return json.loads(Path(p).read_text())
def save(name, value):
    with (B / name).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
def now():
    return datetime.now(timezone.utc).isoformat()
sys.path.insert(0, str(ROOT / 'scripts'))
from mgs_automation_continuity import native_contract_hash
q = sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro', uri=True)
q.row_factory = sqlite3.Row
row = dict(q.execute('select * from requests where key=?', (KEY,)).fetchone())
source = json.loads(row['source'])
assert row['state'] == 'running'
os.kill(int(row['owner'].split(':')[1]), 0)
c = load(ROOT / 'data/meta-manual-payments/digital-trust-workbook-contract.json')
j = next(x for x in load('/root/.hermes/profiles/zeus/cron/jobs.json')['jobs'] if x['id'] == source['job_id'])
assert j['enabled'] and j['state'] == 'scheduled' and not j.get('fire_claim')
assert native_contract_hash(j) == source['contract_hash']
assert source['scheduled_at'] == j['last_dispatch']['scheduled_at'] == '2026-11-27T08:02:00-05:00'
assert c['recurring_scope']['mode'] == 'active_tab_only' and c['sheet_id'] == 794137639
assert not c['balance_views']['enabled']
assert set(source['pending_account_ids']) <= set(c['account_ids'])
assert set(source['pending_H_account_ids']) == set(c['pay_now_account_ids'])
auth = load(ROOT / 'data/authorized-users.json')['agents']['zeus']
assert '344196393512075265' in auth['authorized_user_discord_ids']
sdb = sqlite3.connect('file:/root/.hermes/profiles/zeus/state.db?mode=ro', uri=True)
sdb.row_factory = sqlite3.Row
authorities = []
for mid in ['1563960055504838767', '1563960345826037821', '1575022093777637377', '1569193434189668453', '1575252034100138135']:
    a = sdb.execute('select m.id,m.session_id,m.role,m.content,m.platform_message_id,s.source,s.user_id,s.thread_id from messages m join sessions s on s.id=m.session_id where m.platform_message_id=? and m.role=? order by m.id limit 1', (mid, 'user')).fetchone()
    expected = '1569185140502954077' if mid == '1569193434189668453' else source['thread_id']
    if a is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location('readonly_resolver', ROOT/'scripts/alerts-infra-failed-alert-resolver.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        status, data = m.discord_api(m.load_token(), 'GET', f'/channels/{expected}/messages/{mid}')
        assert status == 200 and data['id'] == mid and data['channel_id'] == expected
        assert data['author']['id'] == '344196393512075265'
        a = {'platform_message_id':mid, 'thread_id':expected, 'user_id':data['author']['id'], 'source':'discord', 'content':data['content'], 'http_status':status}
    else:
        a = dict(a)
        assert a['source'] == 'discord' and a['user_id'] == '344196393512075265'
        assert a['thread_id'] == expected
    authorities.append(a)
save('authority-readback.json', {'registry_authorized': True, 'messages': authorities})
workers = []
names = ['refresh_workbook.py','refresh_september_invoices.py','regroup_funding.py','publish_pay_now.py','record_pc1_proof.py','read_pc1_accounts_list.py','read_pc1_billing_history.py']
for p in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        args = p.read_bytes().split(b'\0')
    except OSError:
        continue
    for name in names:
        if any(a.endswith(('/' + name).encode()) for a in args):
            workers.append({'pid': int(p.parts[2]), 'worker': name})
            break
assert not workers, 'financial worker active'
with (ROOT / 'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(f, fcntl.LOCK_UN)
pre = load(source['checkpoint'])
ledger_paths = ['pc1-pay-now-ledger.json','pc1-card-ledger.json','last-refresh.json']
ledger_info = {}
for n in ledger_paths:
    p = ROOT / 'data/meta-manual-payments' / n
    ledger_info[n] = {'mtime': datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
newer = []
cutoff = Path(source['checkpoint']).stat().st_mtime
for p in (ROOT / 'reports/meta-manual-payments-runs').glob('*/receipt.json'):
    if p.stat().st_mtime > cutoff:
        newer.append({'path': str(p), 'mtime': datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()})
rec = {'at': now(), 'operation_key': KEY, 'source_key': row['source_key'], 'source': source, 'owner': row['owner'], 'owner_alive': True, 'native_fire_claim': j.get('fire_claim'), 'native_hash_matches': True, 'next_run_at': j['next_run_at'], 'workers': workers, 'writer_lock_free': True, 'active_ids': c['account_ids'], 'ledger_info': ledger_info, 'last_refresh': load(ROOT/'data/meta-manual-payments/last-refresh.json'), 'closure_status': pre['status'], 'newer_top_level_receipts': newer, 'prior_occurrences': [dict(r) for r in q.execute('select key,state,owner,updated from requests where key in (%s)' % ','.join('?' for _ in source['prior_occurrence_keys']), source['prior_occurrence_keys'])]}
save('reconciliation.json', rec)
lock = ROOT / 'scripts/mgs-pc1-computer-use-lock.py'
lease_path = Path('/root/.hermes/shared/locks/pc1-computer-use.json')
if lease_path.exists():
    existing = load(lease_path)
    if datetime.fromisoformat(existing['expires_at'].replace('Z','+00:00')) > datetime.now(timezone.utc):
        save('probe-receipt.json', {'operation_key': KEY, 'mode': 'probe_only', 'status': 'waiting_resource', 'auth_ready': False, 'lease_owner': existing.get('session_id'), 'at': now()})
        print('Pendente: PC1 ocupado.', flush=True)
        sys.exit(0)
R = Path(shutil.which('hermes')).resolve().parents[2]
sys.path.insert(0, str(R))
with (B/'runtime.log').open('a') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
    from pm.environments import activate_dependencies
    activate_dependencies(R)
    os.environ['HERMES_CUA_DRIVER_CMD'] = str(ROOT/'scripts/mgs-pc1-cua-driver-ssh.sh')
    from tools.computer_use_tool import handle_computer_use, release_computer_use_session
    from tools.computer_use import cua_backend
    cua_backend._computer_use_max_image_dimension = lambda: 3200
session = os.environ.get('HERMES_SESSION_ID') or ('probe-' + KEY)
os.environ['MGS_CONTINUITY_OPERATION_KEY'] = KEY
lease = subprocess.run([sys.executable,str(lock),'acquire','--agent','zeus','--session-id',session,'--thread-id',source['thread_id'],'--ttl','180'],capture_output=True,text=True)
save('lease-acquire.json', {'exit_code': lease.returncode, 'result': json.loads(lease.stdout)})
if lease.returncode:
    print('Pendente: PC1 ocupado.', flush=True)
    sys.exit(0)
try:
    discoveries = []
    for i in range(2):
        p = subprocess.run([str(ROOT/'scripts/mgs-pc1-cua-driver-ssh.sh'),'call','list_windows'],capture_output=True,text=True,timeout=55)
        assert p.returncode == 0, 'desktop discovery failed'
        ws = json.loads(p.stdout)['windows']
        discoveries.append([{k:w.get(k) for k in ['pid','window_id','app_name','is_on_screen','minimized']} for w in ws])
    save('window-discovery.json', discoveries)
    chrome = [w for w in ws if 'chrome' in w.get('app_name','').lower()]
    candidates = chrome + [w for w in ws if w.get('app_name','').lower() == 'lockapp.exe' or 'credential' in w.get('app_name','').lower()]
    captures = []
    for i,w in enumerate(candidates):
        label = 'window-' + str(i)
        item = {k:w.get(k) for k in ['pid','window_id','app_name']}
        for mode in ['ax','vision']:
            with (B/'runtime.log').open('a') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                raw = handle_computer_use({'action':'capture','mode':mode,'pid':w['pid'],'window_id':w['window_id']},session_id=session)
            d = json.loads(raw) if isinstance(raw,str) else raw
            save(label+'-'+mode+'.json',d)
            if d.get('elements_file'):
                shutil.copy2(d['elements_file'],B/(label+'-elements.json'))
            if d.get('screenshot_path'):
                dest = B/(label+'-'+mode+'.png')
                shutil.copy2(d['screenshot_path'],dest)
                item[mode+'_screenshot'] = str(dest)
            item[mode+'_error'] = d.get('error')
            item[mode+'_ok'] = d.get('ok')
        captures.append(item)
    receipt = {'at':now(),'mode':'probe_only','operation_key':KEY,'source_key':row['source_key'],'chrome_windows':len(chrome),'captures':captures,'input_actions':0,'business_writes':0,'tabs_modified':0,'auth_ready':False,'visual_review_pending':True,'pending_H_account_ids':source['pending_H_account_ids'],'pending_recent_D_account_ids':source['pending_recent_D_account_ids'],'completed_financial_layers':source['completed_financial_layers'],'historical_D_source_checkpoint':source['checkpoint'],'next_authorized_step':source['closure_guard']}
    save('probe-receipt.json',receipt)
    print(json.dumps({'authority_verified':True,'active_count':len(c['account_ids']),'H_pending_count':len(source['pending_H_account_ids']),'D_pending_count':len(source['pending_recent_D_account_ids']),'owner':row['owner'],'chrome_windows':len(chrome),'captures':captures,'input_actions':0}),flush=True)
finally:
    with (B/'runtime.log').open('a') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        release_computer_use_session(session)
    release = subprocess.run([sys.executable,str(lock),'release','--agent','zeus','--session-id',session],capture_output=True,text=True)
    status = subprocess.run([sys.executable,str(lock),'status'],capture_output=True,text=True)
    save('lease-release.json',{'release_exit':release.returncode,'release':json.loads(release.stdout),'readback':json.loads(status.stdout)})
