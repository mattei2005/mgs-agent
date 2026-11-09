"""DTR audit: durable per-user collection and idempotent verified delivery.
No credentials or DTR/SB writes. Reuses the original renderer and state contract.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

ROOT=Path('/root/.hermes/shared/automation-continuity')


def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex)
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,sort_keys=True);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


class Progress:
    def __init__(self,root,users,now=None):
        now=time.time() if now is None else now
        self.users=sorted(users)
        scope=hashlib.sha256(json.dumps(self.users).encode()).hexdigest()
        self.root=Path(root)/scope
        self.manifest=self.root/'current.json'
        old=json.loads(self.manifest.read_text()) if self.manifest.exists() else None
        if old and old['state']=='collecting' and 0<=now-old['created']<=7200:
            self.meta=old
        else:
            self.meta={'generation':uuid.uuid4().hex,'created':now,'state':'collecting','users':self.users}
            atomic(self.manifest,self.meta)
        self.directory=self.root/self.meta['generation']

    def path(self,user):
        if user not in self.users:raise ValueError('user outside frozen scope')
        return self.directory/(hashlib.sha256(user.encode()).hexdigest()+'.json')

    def read(self,user,now=None):
        now=time.time() if now is None else now
        p=self.path(user)
        if not p.exists():return None
        data=json.loads(p.read_text())
        if not 0<=now-data['at']<=7200:return None
        return data['scan']

    def save(self,user,scan,now=None):
        now=time.time() if now is None else now
        if not scan.get('login_ok') or scan.get('errors') or any(a.get('errors') for a in scan.get('accounts',[])):return
        atomic(self.path(user),{'at':now,'scan':scan})

    def complete(self):
        self.meta['state']='collected';self.meta['completed']=time.time();atomic(self.manifest,self.meta)


def validate_snapshot(data):
    summary=data['summary'];scans=data['dtr_scans']
    n=summary['dtr_users_scanned']
    if not n or len(scans)!=n or summary['dtr_login_ok']!=n:raise ValueError('DTR incomplete login coverage')
    if any(summary.get(k) for k in ('errors','op_errors','missing_1p_users')):raise ValueError('DTR incomplete source')
    if len({s['username'] for s in scans})!=n:raise ValueError('DTR duplicate user')
    if any(not s.get('login_ok') or s.get('errors') or any(a.get('errors') for a in s.get('accounts',[])) for s in scans):raise ValueError('DTR nested collection error')
    if sum(len(s.get('pages',[])) for s in scans)!=summary['dtr_pages_raw']:raise ValueError('DTR page coverage mismatch')
    return True


def deliver(snapshot,outdir,module,post):
    snapshot=Path(snapshot);outdir=Path(outdir);manifest=outdir/'manifest.json'
    supplied=json.loads(snapshot.read_text());validate_snapshot(supplied)
    if manifest.exists():
        state=json.loads(manifest.read_text())
        # A delivery retry must use its frozen original snapshot/payload, never
        # create a second report because a later collection got another hash.
        original=Path(state['snapshot']);raw=original.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=state['sha256']:raise ValueError('frozen snapshot drift')
        data=json.loads(raw);validate_snapshot(data)
    else:
        data=supplied;raw=snapshot.read_bytes()
        state={'snapshot':str(snapshot),'sha256':hashlib.sha256(raw).hexdigest(),'status':'PENDING','parts':[],'payloads':[]}
        keys={f"{r['type']}|{r['fb']}|{r['pg_dtr'] or r['pg_sb']}|{r['login_dtr'] or r['login_sb']}|{r['problem'].replace('+',',')}" for r in data['issues']}
        old=set(module.load_state().get('last_issue_keys') or [])
        summary=dict(data['summary']);summary.update(new_issues=len(keys-old),resolved_since_last=len(old-keys) if old else 0)
        text=module.build_report(summary,data['status_counts'],data['restriction_counts'],data['issues'],keys-old,len(old-keys) if old else 0)
        state.update(issue_keys=sorted(keys),summary=summary)
        for index,chunk in enumerate(module.chunk_discord(text)):
            state['payloads'].append({'content':'```\n'+chunk+'\n```','embeds':[],'allowed_mentions':{'parse':[],'users':[],'roles':[],'replied_user':False},'nonce':state['sha256'][:18]+str(index),'enforce_nonce':True})
            state['parts'].append({'part':index,'message_id':None,'verified':False})
        atomic(manifest,state)
    for part,body in zip(state['parts'],state['payloads']):
        # Re-read an accepted ID; never POST again after an ambiguous GET.
        def accepted(mid):part['message_id']=mid;atomic(manifest,state)
        mid=post(body,channel='1524631647151198218',prior_id=part['message_id'],on_created=accepted)
        part.update(message_id=mid,verified=True);atomic(manifest,state)
    if not all(p['verified'] for p in state['parts']):raise ValueError('DTR delivery incomplete')
    # Preserve the canonical issue-key and summary representation exactly.
    module.save_state(set(state['issue_keys']),state['summary'])
    state.update(status='GET_VERIFIED',verified_at=time.time());atomic(manifest,state)
    return state


def latest_snapshot(base=Path('/root/mgs-agent'),now=None):
    now=time.time() if now is None else now
    paths=sorted((base/'reports').glob('dtr-sb-daily-match-audit-*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    for p in paths[:8]:
        try:
            d=json.loads(p.read_text());stamp=datetime.fromisoformat(d['summary']['started_at_et']).timestamp()
            validate_snapshot(d)
            if 0<=now-stamp<=7200:return p,d
        except (ValueError,KeyError,TypeError):continue
    return None,None


def resume_delivery(base=Path('/root/mgs-agent')):
    import fcntl
    import importlib.util
    from mgs_alert_transport import post_verified
    with open('/var/lock/dtr_sb_daily_match_audit.lock','a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return 'Pendente: outra sessão executa a auditoria DTR; nenhuma duplicação.'
        path,data=latest_snapshot(base)
        if path is None:raise ValueError('fresh complete DTR snapshot unavailable; collector must resume first')
        spec=importlib.util.spec_from_file_location('dtr_daily_renderer',base/'scripts/dtr-sb-daily-match-audit.py');assert spec and spec.loader
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        day=str(data['summary']['started_at_et'])[:10]
        result=deliver(path,ROOT/'dtr-delivery'/day,module,post_verified)
        return f"Resolvido: auditoria DTR completa, {data['summary']['dtr_users_scanned']} usuários; {len(result['parts'])} partes com GET verificado; somente entrega faltante retomada."
