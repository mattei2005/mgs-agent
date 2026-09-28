#!/usr/bin/env python3
"""Bounded, journaled code/rule cutover. Catalog prerequisites are read-only.
No SQL mutations, arbitrary hooks, credential/system-unit changes or file deletion.
"""
from __future__ import annotations
import argparse, base64, contextlib, hashlib, json, os, pathlib, re, shlex, subprocess, sys, tempfile, time
from finance_release_guard import lease, release_state, SAFE_STATES
ROOT = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path('/root/mgs-agent')
TARGET = '/home/mgsfinance/releases/pg-auth-1545934831664242748'
SERVICES = ['mgs-finance-dash.socket', 'mgs-finance-dash.service', 'mgs-postgresql18']

class ReleaseError(RuntimeError): pass

def sha(data): return hashlib.sha256(data).hexdigest()

def relative(value):
    p=pathlib.PurePosixPath(value)
    if not isinstance(value,str) or not value or p.is_absolute() or '..' in p.parts or str(p)!=value:
        raise ReleaseError('invalid_relative_path')
    return p

def atomic(path,data,mode=0o600,owner=None):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,name=tempfile.mkstemp(prefix=path.name+'.release-',dir=path.parent)
    with os.fdopen(fd,'wb') as f:
        f.write(data);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),mode)
        if owner is not None:os.fchown(f.fileno(),*owner)
    os.replace(name,path)
    fd=os.open(path.parent,os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def record(root,state):
    raw=(json.dumps(state,indent=2,sort_keys=True)+'\n').encode()
    atomic(pathlib.Path(root)/'private/release-current.json',raw)
    atomic(pathlib.Path(root)/'private/releases'/state['release_id']/'journal.json',raw)

class LocalFiles:
    def __init__(self,root):self.root=pathlib.Path(root).resolve()
    def target(self,name):
        p=self.root/relative(name)
        if not p.is_file() or p.is_symlink() or p.resolve()!=p or not p.resolve().is_relative_to(self.root):
            raise ReleaseError('target_missing_or_symlink')
        return p
    def read(self,name):return self.target(name).read_bytes()
    def write(self,name,data,expected):
        p=self.target(name)
        if sha(p.read_bytes())!=expected:raise ReleaseError('target_drift')
        s=p.stat();atomic(p,data,s.st_mode&0o777,(s.st_uid,s.st_gid))
        if p.read_bytes()!=data:raise ReleaseError('write_readback')

REMOTE_SCRIPT = r'''
import sys,json,pathlib,hashlib,base64,os,tempfile,fcntl,re
ctl=pathlib.Path('/home/mgsfinance/releases/pg-auth-1545934831664242748/private/release-control');ctl.mkdir(exist_ok=True,mode=0o700);lock=(ctl/'files.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
v=json.load(sys.stdin);root=pathlib.Path('/home/mgsfinance/releases/pg-auth-1545934831664242748');name=v['path'];r=pathlib.PurePosixPath(name)
assert not r.is_absolute() and '..' not in r.parts and str(r)==name
p=root/r;assert p.is_file() and not p.is_symlink() and p.resolve()==p and p.resolve().is_relative_to(root)
old=p.read_bytes();h=hashlib.sha256(old).hexdigest()
if v['action']=='read':print(json.dumps({'data':base64.b64encode(old).decode(),'sha256':h}))
elif v['action']=='write':
 assert re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}',v['release_id']);fence=json.loads((ctl/(v['release_id']+'.json')).read_text());assert fence['phase']==v['phase'] and v['phase'] in ['applying','rolling_back']
 assert h==v['expected'];data=base64.b64decode(v['data'],validate=True);assert hashlib.sha256(data).hexdigest()==v['sha256'];s=p.stat();fd,n=tempfile.mkstemp(prefix=p.name+'.release-',dir=p.parent)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno());os.fchmod(f.fileno(),s.st_mode&0o777);os.fchown(f.fileno(),s.st_uid,s.st_gid)
 os.replace(n,p);fd=os.open(p.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd);assert p.read_bytes()==data;print(json.dumps({'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
else:raise ValueError('action')
'''

def remote(command,input_data=None,timeout=45):
    # Stable canonical transport; do not import a runner being replaced.
    sys.path.insert(0,str(ROOT/'deploy'))
    # Resolve canonical environment without exposing any credential value.
    sys.path.insert(0,str(REPO/'scripts'))
    from mgs_google_workspace_auth import load_env
    load_env()
    from runcloud_ops import ssh
    return ssh(command,input_data,timeout=timeout)

REMOTE_FENCE_SCRIPT = r'''
import sys,pathlib,json,os,fcntl,re,tempfile
v=json.load(sys.stdin);assert re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}',v['release_id']);assert v['phase'] in ['applying','rolling_back','rolled_back','committed']
p=pathlib.Path('/home/mgsfinance/releases/pg-auth-1545934831664242748/private/release-control');p.mkdir(exist_ok=True,mode=0o700);lock=(p/'files.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX);target=p/(v['release_id']+'.json');old=json.loads(target.read_text()) if target.exists() else None
if old:
 allowed={'applying':[], 'rolling_back':['applying','rolling_back','committed','rolled_back'], 'rolled_back':['rolling_back','rolled_back'], 'committed':['applying','committed']}
 assert old['phase'] in allowed[v['phase']]
else:assert v['phase'] in ['applying','rolling_back']
fd,name=tempfile.mkstemp(dir=p,prefix='fence-')
with os.fdopen(fd,'w') as f:json.dump(v,f);f.flush();os.fsync(f.fileno())
os.replace(name,target);fd=os.open(p,os.O_DIRECTORY);os.fsync(fd);os.close(fd);assert json.loads(target.read_text())==v;print(json.dumps({'phase':v['phase']}))
'''

class RemoteFiles:
    def phase(self,release_id,phase):
        v={'release_id':release_id,'phase':phase}
        r=json.loads(remote('sudo -n python3 -c '+shlex.quote(REMOTE_FENCE_SCRIPT),json.dumps(v).encode()))
        if r.get('phase')!=phase:raise ReleaseError('remote_fence_readback')
        self.release_id=release_id;self.release_phase=phase
    def call(self,data):return json.loads(remote('sudo -n python3 -c '+shlex.quote(REMOTE_SCRIPT),json.dumps(data).encode()))
    def read(self,name):
        relative(name);r=self.call({'action':'read','path':name});raw=base64.b64decode(r['data'],validate=True)
        if sha(raw)!=r['sha256']:raise ReleaseError('remote_read_hash')
        return raw
    def write(self,name,data,expected):
        relative(name);r=self.call({'action':'write','path':name,'expected':expected,'data':base64.b64encode(data).decode(),'sha256':sha(data),'release_id':self.release_id,'phase':self.release_phase})
        if r['sha256']!=sha(data):raise ReleaseError('remote_write_hash')

def adapters_default(root):
    if pathlib.Path(root).resolve()!=REPO/'apps/finance-system':raise ReleaseError('noncanonical_recovery_target')
    return {'local':LocalFiles(REPO),'remote':RemoteFiles()}

@contextlib.contextmanager
def legacy_locks(root,timeout):
    import fcntl
    start=time.monotonic()
    with contextlib.ExitStack() as stack:
        for name in ['gam-revenue-sync.lock','media-spend-sync.lock','quote-sync.lock','history-refresh.lock']:
            handle=stack.enter_context((pathlib.Path(root)/'private'/name).open('a'))
            while True:
                try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic()-start>=timeout:raise TimeoutError('existing_finance_job_busy_no_changes')
                    time.sleep(.05)
        yield

def validate_plan(plan,candidate):
    if plan.get('schema')!=1 or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}',plan.get('release_id','')) or not re.fullmatch(r'\d{17,20}',plan.get('authority','')):
        raise ReleaseError('release_identity')
    files=plan.get('files',[])
    if not files or len(files)>40:raise ReleaseError('bounded_file_set_required')
    seen=set();payloads=[]
    for item in files:
        relative(item['path']);relative(item['source']);key=(item['host'],item['path'])
        if key in seen or item['host'] not in ['local','remote']:raise ReleaseError('duplicate_or_unknown_target')
        seen.add(key)
        p=pathlib.Path(candidate)/item['source']
        if p.is_symlink() or not p.resolve().is_relative_to(pathlib.Path(candidate).resolve()):raise ReleaseError('candidate_symlink_or_escape')
        raw=p.read_bytes()
        if not re.fullmatch('[a-f0-9]{64}',item.get('before','')) or sha(raw)!=item.get('after'):raise ReleaseError('candidate_hash')
        payloads.append(raw)
    return payloads

def restart_app(state):
    if state.get('restart_worker'):
        subprocess.run(['systemctl','restart','mgs-finance-meta-lookup.service'],check=True,capture_output=True,timeout=35)
        r=subprocess.run(['systemctl','is-active','mgs-finance-meta-lookup.service'],check=True,capture_output=True,text=True,timeout=10)
        if r.stdout.strip()!='active':raise ReleaseError('lookup_worker_health')
    if state.get('restart_app'):
        remote('sudo -n systemctl restart mgs-finance-dash.service',timeout=60)
    if state.get('remote_health'):
        statuses=remote('sudo -n systemctl is-active '+' '.join(SERVICES)).split()
        if statuses!=['active']*len(SERVICES):raise ReleaseError('production_service_health')
        status=remote("sudo -n curl --silent --show-error --unix-socket /run/mgs-finance-dash.sock -o /dev/null -w '%{http_code}' -H 'Host: dash.mgsdigitalcorp.com' http://localhost/login").strip()
        if status!='200':raise ReleaseError('production_login_health')

def restore_locked(root,state,adapters):
    # Fence late remote writes before inspecting any rollback target (ABA safe).
    for host in {x['host'] for x in state['files']}:
        if hasattr(adapters[host],'phase'):adapters[host].phase(state['release_id'],'rolling_back')
    # Inspect ALL targets first, never overwrite an unexplained third version.
    current=[];backups=[]
    for item in state['files']:
        raw=adapters[item['host']].read(item['path']);h=sha(raw)
        if h not in [item['before'],item['after']]:raise ReleaseError('rollback_unknown_concurrent_content')
        backup=pathlib.Path(root)/'private/releases'/state['release_id']/item['backup']
        old=backup.read_bytes()
        if sha(old)!=item['before']:raise ReleaseError('rollback_backup_hash')
        current.append(h);backups.append(old)
    for item,h,raw in zip(state['files'],current,backups):
        if h!=item['before']:adapters[item['host']].write(item['path'],raw,h)
    for item in state['files']:
        if sha(adapters[item['host']].read(item['path']))!=item['before']:raise ReleaseError('rollback_readback')
    restart_app(state)
    for host in {x['host'] for x in state['files']}:
        if hasattr(adapters[host],'phase'):adapters[host].phase(state['release_id'],'rolled_back')
    state['state']='rolled_back';record(root,state);return state

def recover(root,adapters=None):
    root=pathlib.Path(root);adapters=adapters or adapters_default(root)
    with lease(root,exclusive=True,timeout=120,recover_pending=False),legacy_locks(root,120):
        state=release_state(root)
        if not state or state.get('state') in SAFE_STATES:return state or {'state':'prepared'}
        return restore_locked(root,state,adapters)

def publish(root,candidate,plan,adapters,*,preflight,verify,lock_timeout=120,cutover_seconds=120):
    root=pathlib.Path(root);payloads=validate_plan(plan,candidate)
    preflight() # expensive work must happen without admission/operation locks
    with lease(root,exclusive=True,timeout=lock_timeout,recover_pending=False),legacy_locks(root,lock_timeout):
        admitted=time.monotonic()
        def budget():
            if time.monotonic()-admitted>cutover_seconds:raise ReleaseError('cutover_deadline')
        pending=release_state(root)
        if pending and pending.get('state') not in SAFE_STATES:raise ReleaseError('recover_previous_release_first')
        directory=root/'private/releases'/plan['release_id']
        if directory.exists():raise ReleaseError('release_id_already_used')
        # Check again after acquiring admission: no stale catalog or candidate.
        payloads=validate_plan(plan,candidate);preflight();budget()
        old=[]
        for item in plan['files']:
            raw=adapters[item['host']].read(item['path'])
            if sha(raw)!=item['before']:raise ReleaseError('baseline_drift_no_changes')
            old.append(raw);budget()
        directory.mkdir(parents=True,mode=0o700)
        state={k:plan[k] for k in ['release_id','authority']}
        state.update(schema=1,state='prepared',restart_app=bool(plan.get('restart_app')),restart_worker=bool(plan.get('restart_worker')),remote_health=bool(plan.get('remote_health')),files=[])
        for i,(item,raw) in enumerate(zip(plan['files'],old)):
            name=f'{i:03d}.before';atomic(directory/name,raw);state['files'].append({**item,'backup':name})
        record(root,state)
        state['state']='applying';record(root,state);started=admitted
        try:
            for host in {x['host'] for x in state['files']}:
                if hasattr(adapters[host],'phase'):adapters[host].phase(state['release_id'],'applying')
            for item,raw in zip(plan['files'],payloads):
                if time.monotonic()-started>cutover_seconds:raise ReleaseError('cutover_deadline')
                if item['before']!=item['after']:adapters[item['host']].write(item['path'],raw,item['before'])
            budget();restart_app(state)
            for item in plan['files']:
                budget()
                if sha(adapters[item['host']].read(item['path']))!=item['after']:raise ReleaseError('release_readback')
            verify()
            if time.monotonic()-started>cutover_seconds:raise ReleaseError('cutover_deadline')
            for host in {x['host'] for x in state['files']}:
                if hasattr(adapters[host],'phase'):adapters[host].phase(state['release_id'],'committed')
            state.update(state='committed',cutover_seconds=round(time.monotonic()-started,3));record(root,state)
            return state
        except Exception:
            restore_locked(root,state,adapters)
            raise

def production_policy(plan,candidate):
    """Code/rules only; no private data, secrets, system paths or control self-update."""
    protected={'finance_release.py','finance_release_guard.py','meta-lookup-worker.py'}
    for item in plan['files']:
        p=pathlib.PurePosixPath(item['path'])
        if item['host']=='local':
            if str(p)=='data/finance-gam-revenue-rules.json':continue
            prefix=pathlib.PurePosixPath('apps/finance-system')
            if not p.is_relative_to(prefix):raise ReleaseError('local_target_scope')
            p=p.relative_to(prefix)
        if p.name in protected or 'private' in p.parts or 'deploy' in p.parts or p.suffix not in {'.py','.mjs','.json','.js','.css','.html'} or (len(p.parts)>1 and p.parts[0] not in {'public','tests'}):raise ReleaseError('protected_target_scope')
    if any(x['host']=='local' and x['before']!=x['after'] and pathlib.PurePosixPath(x['path']).suffix=='.py' for x in plan['files']) and not plan.get('restart_worker'):raise ReleaseError('local_python_change_requires_worker_reload')
    if any(x['path']=='data/finance-gam-revenue-rules.json' and x['before']!=x['after'] for x in plan['files']) and not plan.get('catalog_required'):raise ReleaseError('rule_change_requires_catalog_prerequisites')
    # Both full gates must attest to this exact candidate code, not old manifests.
    sys.path.insert(0,str(candidate))
    import importlib.util
    spec=importlib.util.spec_from_file_location('_candidate_gate',pathlib.Path(candidate)/'release_gate.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    code=gate.code_manifest()
    for phase in ['node','python']:
        proof=json.loads((pathlib.Path(candidate)/relative(plan['gates'])/(phase+'-result.json')).read_text())
        if proof.get('pass') is not True or proof.get('code')!=code or not proof.get('results') or any(not r.get('pass') for r in proof['results']):raise ReleaseError('missing_current_release_gate')
    # Rules outside the application code manifest must be covered explicitly by
    # the readonly rehearsal proof, as must approved catalogue prerequisites.
    proof=json.loads((pathlib.Path(candidate)/relative(plan['stage_proof'])).read_text())
    expected={x['host']+':'+x['path']:x['after'] for x in plan['files']}
    if proof.get('pass') is not True or proof.get('files')!=expected or proof.get('financial_writes')!=0 or proof.get('authority')!=plan['authority'] or proof.get('catalog_required')!=plan.get('catalog_required',[]):raise ReleaseError('stage_proof_mismatch')
    # Any changed runtime code on the remote host requires a process reload;
    # remote-only cli changes are safe with this same conservative restart.
    if any(x['host']=='remote' and x['before']!=x['after'] for x in plan['files']) and not plan.get('restart_app'):raise ReleaseError('remote_change_requires_reload')

def catalog_check(plan):
    required=plan.get('catalog_required',[])
    if not required:return
    for x in required:
        if set(x)!={'period','site_id'} or not re.fullmatch(r'\d{4}-\d{2}',x['period']) or not re.fullmatch(r'[a-zA-Z0-9_-]+',x['site_id']):raise ReleaseError('catalog_requirement_shape')
    # Fixed, read-only query; no caller-supplied SQL or financial mutation.
    script="import pg from 'pg';const p=new pg.Pool({host:'/run/mgs-postgresql18',user:'mgsfinance',database:'mgs_finance'});try{await p.query('BEGIN READ ONLY');const rows=(await p.query(\"SELECT id, result->'domain'->'site_catalog' AS sites FROM scenarios WHERE id LIKE 'workspace-%'\")).rows;console.log(JSON.stringify(rows.map(r=>({period:r.id.slice(10),sites:(r.sites||[]).map(s=>s.id)}))));await p.query('ROLLBACK')}finally{await p.end()}"
    command='cd '+shlex.quote(TARGET)+' && /home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node --input-type=module -e '+shlex.quote(script)
    rows=json.loads(remote('sudo -n -u mgsfinance /bin/sh -c '+shlex.quote(command)))
    known={r['period']:set(r['sites']) for r in rows}
    if any(x['site_id'] not in known.get(x['period'],set()) for x in required):raise ReleaseError('catalog_prerequisite_missing_old_version_retained')

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['check','publish','recover']);p.add_argument('--manifest',type=pathlib.Path);p.add_argument('--candidate',type=pathlib.Path);a=p.parse_args()
    if ROOT!=REPO/'apps/finance-system':raise ReleaseError('production_cli_requires_canonical_root')
    if a.action=='recover':out=recover(ROOT)
    else:
        if not a.manifest or not a.candidate:raise ReleaseError('manifest_and_candidate_required')
        candidate=a.candidate.resolve()
        if not candidate.is_relative_to(ROOT/'private') or candidate==ROOT/'private':raise ReleaseError('isolated_candidate_required')
        plan=json.loads(a.manifest.read_text());validate_plan(plan,candidate)
        def preflight():production_policy(plan,candidate);catalog_check(plan)
        if a.action=='check':preflight();out={'state':'validated','financial_writes':0}
        else:out=publish(ROOT,candidate,plan,adapters_default(ROOT),preflight=preflight,verify=lambda:catalog_check(plan))
    print(json.dumps({'pass':True,'state':out['state'],'financial_writes':0,'release_id':out.get('release_id')}))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Transport diagnostics may contain private values; retain only type/code.
        print(json.dumps({'pass':False,'error':str(exc) if isinstance(exc,(ReleaseError,TimeoutError)) else type(exc).__name__,'financial_writes':0}));sys.exit(1)
