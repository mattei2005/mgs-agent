"""Same authorized occurrence, probe_only: no business writes or UI input."""
import os, sys, json, shutil, subprocess, importlib.util, sqlite3, fcntl, re, hashlib
from pathlib import Path
from datetime import datetime, timezone
os.umask(0o077)
B = Path(__file__).parent
ROOT = Path('/root/mgs-agent')
KEY = '6373afb33275674610c06b6a'
R = Path(shutil.which('hermes')).resolve().parents[2]
sys.path.insert(0, str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0, str(ROOT / 'scripts'))
from mgs_automation_continuity import native_contract_hash
os.environ['MGS_CONTINUITY_OPERATION_KEY'] = KEY

def load(p):
    return json.loads(Path(p).read_text())

def save(n, v):
    with (B / n).open('x') as f:
        json.dump(v, f, ensure_ascii=False, indent=2)

q = sqlite3.connect('file:/root/.hermes/shared/automation-continuity/queue.sqlite3?mode=ro', uri=True)
q.row_factory = sqlite3.Row
row = dict(q.execute('select * from requests where key=?', (KEY,)).fetchone())
source = json.loads(row['source'])
assert row['state'] == 'running'
os.kill(int(row['owner'].split(':')[1]), 0)
c = load(ROOT / 'data/meta-manual-payments/digital-trust-workbook-contract.json')
jobs = load('/root/.hermes/profiles/zeus/cron/jobs.json')
j = next(x for x in (jobs if isinstance(jobs, list) else jobs['jobs']) if x['id'] == source['job_id'])
assert j['enabled'] and j['state'] == 'scheduled' and not j.get('fire_claim')
assert native_contract_hash(j) == source['contract_hash']
assert source['scheduled_at'] == j['last_dispatch']['scheduled_at'] == '2026-11-25T21:02:00-05:00'
assert c['sheet_id'] == 794137639 and c['recurring_scope']['mode'] == 'active_tab_only' and not c['balance_views']['enabled']
assert set(source['pending_account_ids']) <= set(c['account_ids'])
assert source['pending_H_account_ids'] == []
assert '344196393512075265' in load(ROOT / 'data/authorized-users.json')['agents']['zeus']['authorized_user_discord_ids']
spec = importlib.util.spec_from_file_location('resolver', ROOT / 'scripts/alerts-infra-failed-alert-resolver.py')
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
token = m.load_token()
authorities = []
for ch, mid in [('1563926766286803004', '1563960055504838767'), ('1563926766286803004', '1563960345826037821'), ('1563926766286803004', '1575022093777637377'), ('1569185140502954077', '1569193434189668453'), ('1563926766286803004', '1575252034100138135')]:
    st, d = m.discord_api(token, 'GET', f'/channels/{ch}/messages/{mid}')
    assert st == 200 and d['id'] == mid and d['channel_id'] == ch and d['author']['id'] == '344196393512075265'
    authorities.append({'id': mid, 'channel_id': ch, 'author_id': d['author']['id'], 'status': st, 'content': d['content']})
save('authority-readback.json', {'messages': authorities, 'registry_authorized': True})
workers = []
names = {'refresh_workbook.py', 'regroup_funding.py', 'refresh_september_invoices.py', 'record_pc1_proof.py', 'read_pc1_billing_history.py', 'read_pc1_accounts_list.py', 'read_pc1_accounts_uia.py', 'read_pc1_history_uia.py', 'publish_pay_now.py'}
for p in Path('/proc').glob('[0-9]*'):
    if int(p.name) == os.getpid():
        continue
    try:
        args = (p / 'cmdline').read_bytes().decode(errors='replace').split('\0')
    except OSError:
        continue
    matches = [Path(arg).name for arg in args if Path(arg).name in names]
    if matches:
        workers.append({'pid': int(p.name), 'worker': matches[0]})
assert not workers, 'concurrent financial worker'
with (ROOT / 'data/meta-manual-payments/writer.lock').open('r') as f:
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(f, fcntl.LOCK_UN)
ledger_paths = {'D': ROOT / 'data/meta-manual-payments/pc1-card-ledger.json', 'H': ROOT / 'data/meta-manual-payments/pc1-pay-now-ledger.json'}
ledgers = {k: load(p) for k, p in ledger_paths.items()}
proof = lambda ledger, ids: {k: {z: v for z, v in ledger.get('accounts', {}).get(k, {}).items() if z in ['amount', 'source', 'read_at', 'verified_at', 'receipt']} for k in ids}
related = [dict(r) for r in q.execute("select key,state,owner,lease_until,due from requests where source like ? and state!='completed_validated'", ('%2ee720363d7d%',))]
assert all(not r['owner'] or r['key'] == KEY for r in related), 'other occurrence owned'
save('reconciliation.json', {'observed_at': datetime.now(timezone.utc).isoformat(), 'mode': 'probe_only', 'operation': KEY, 'source_key': row['source_key'], 'source': source, 'queue_owner': row['owner'], 'related_owners': related, 'consumer_heartbeat': json.loads(q.execute("select value from service where key='heartbeat'").fetchone()[0]), 'native_contract_hash': native_contract_hash(j), 'active_ids': c['account_ids'], 'pending_D_account_ids': source['pending_recent_D_account_ids'], 'pending_H_account_ids': [], 'H_current_proofs': proof(ledgers['H'], c['pay_now_account_ids']), 'D_current_proofs': proof(ledgers['D'], source['pending_recent_D_account_ids']), 'ledger_sha256': {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in ledger_paths.items()}, 'financial_workers': workers, 'writer_free': True, 'job_fire_claim': j.get('fire_claim'), 'next_run_at': j['next_run_at']})
print(json.dumps({'authority_verified': True, 'scope_count': len(c['account_ids']), 'owner': row['owner'], 'reconciled': True}), flush=True)
os.environ['HERMES_CUA_DRIVER_CMD'] = str(ROOT / 'scripts/mgs-pc1-cua-driver-ssh.sh')
from tools.computer_use_tool import handle_computer_use, release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements = lambda: 2400
cua_backend._computer_use_max_image_dimension = lambda: 3200
session = os.environ['HERMES_SESSION_ID']
lock = ROOT / 'scripts/mgs-pc1-computer-use-lock.py'
lease = subprocess.run([sys.executable, str(lock), 'acquire', '--agent', 'zeus', '--session-id', session, '--thread-id', c['thread_id'], '--ttl', '240'], capture_output=True, text=True)
save('lease-acquire.json', json.loads(lease.stdout))
if lease.returncode:
    print(json.dumps({'status': 'waiting_resource', 'evidence': str(B / 'lease-acquire.json')}))
    raise SystemExit(0)
def call(d):
    r = handle_computer_use(d, session_id=session)
    return json.loads(r) if isinstance(r, str) else r
try:
    raw = subprocess.run([str(ROOT / 'scripts/mgs-pc1-cua-driver-ssh.sh'), 'call', 'list_windows'], capture_output=True, text=True, timeout=50)
    assert raw.returncode == 0
    ws = json.loads(raw.stdout)['windows']
    bind = load(ROOT / 'data/meta-manual-payments/pc1-browser-surface.json')
    approved = [w for w in ws if w['pid'] == bind['pid'] and w['window_id'] == bind['window_id']]
    assert len(approved) == 1, 'approved handle unavailable'
    dialogs = [w for w in ws if re.search(r'Save As|Salvar como|Windows Security', str(w.get('title', '')), re.I) or w.get('app_name') == 'CredentialUIBroker.exe']
    save('window-discovery.json', [{'pid': w['pid'], 'window_id': w['window_id'], 'approved': w in approved, 'native_dialog_candidate': w in dialogs, 'minimized': w.get('minimized')} for w in ws])
    captures = {}
    for label, w in [('approved', approved[0])] + [(f'native-dialog-{i}', w) for i, w in enumerate(dialogs)]:
        d = call({'action': 'capture', 'mode': 'ax', 'pid': w['pid'], 'window_id': w['window_id']})
        assert not d.get('error')
        save(label + '-elements.json', load(d['elements_file']) if d.get('elements_file') else d)
        v = call({'action': 'capture', 'mode': 'vision', 'pid': w['pid'], 'window_id': w['window_id']})
        assert not v.get('error') and v.get('screenshot_path')
        dest = B / (label + '.png')
        shutil.copy2(v['screenshot_path'], dest)
        captures[label] = {'pid': w['pid'], 'window_id': w['window_id'], 'screenshot': str(dest), 'elements': str(B / (label + '-elements.json'))}
    result = {'operation': KEY, 'mode': 'probe_only', 'observed_at': datetime.now(timezone.utc).isoformat(), 'captures': captures, 'dialog_count': len(dialogs), 'input_actions': 0, 'business_writes': 0, 'tabs_created': 0, 'tabs_closed': 0}
    save('probe-receipt.json', result)
    print(json.dumps(result), flush=True)
finally:
    release_computer_use_session(session)
    rel = subprocess.run([sys.executable, str(lock), 'release', '--agent', 'zeus', '--session-id', session], capture_output=True, text=True)
    st = subprocess.run([sys.executable, str(lock), 'status'], capture_output=True, text=True)
    save('lease-release.json', {'release_exit': rel.returncode, 'release': json.loads(rel.stdout), 'readback': json.loads(st.stdout)})
