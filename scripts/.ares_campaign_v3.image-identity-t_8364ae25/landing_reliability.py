"""PC1-only hard retry gates and receipt-backed technical recovery."""
from __future__ import annotations
import json
from . import landing_followup as core


def policy():
    try:p=json.loads((core.BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text()).get('pc1_execution_policy') or {}
    except (OSError,ValueError):return {}
    return p if p.get('enabled') is True else {}


def technical_errors(q,key,idx):
    count=0
    for r in q.db.execute("SELECT kind,detail FROM events WHERE job=? AND kind IN ('observation_result','technical_repair_approved','worker_expired') ORDER BY seq DESC",(key,)):
        d=json.loads(r['detail'])
        if d.get('idx')!=idx:continue
        if r['kind']=='worker_expired':count+=1;continue
        if r['kind']=='technical_repair_approved' or d.get('result')!='ERROR':break
        count+=1
    return count


def needs_repair(q,key,idx):
    p=policy()
    if not p:return False
    if technical_errors(q,key,idx)>=int(p.get('technical_error_limit',3)):return True
    for r in q.db.execute("SELECT kind,detail FROM events WHERE job=? AND kind IN ('technical_repair_required','technical_repair_approved') ORDER BY seq DESC",(key,)):
        if json.loads(r['detail']).get('idx')==idx:return r['kind']=='technical_repair_required'
    return False


def technical_delay():
    return int(policy().get('technical_retry_delay_seconds',60))


def no_ad_delay():
    try:p=json.loads((core.BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text())
    except (OSError,ValueError):return 60
    return int((p.get('no_ad_retry_policy') or {}).get('retry_after_seconds',p.get('retry_after_seconds',60)))


def run_directory(q,owner,key,idx,attempt):
    root=q.root/'runs'/owner
    return root/key[:16]/f'{idx}-{attempt}' if policy() else root


def reclaim_retry(q,key,owner,idx):
    with q.tx():
        if not policy() or no_ad_delay()!=0:raise ValueError('immediate retry not enabled')
        if q.db.execute("SELECT 1 FROM jobs WHERE state IN ('RUNNING','RECONCILING','REPAIRING','NEEDS_RECONCILIATION','WAITING_HUMAN_UNCLOSED')").fetchone():raise ValueError('active or uncertain desktop attempt exists')
        j=q.job(key);link=j['links'][idx]
        if j['state']!='READY' or link['state']!='WAIT_RETRY' or link['due']>q.now() or needs_repair(q,key,idx):raise ValueError('exact retry is not safely due')
        last=q.db.execute("SELECT detail FROM events WHERE job=? AND kind='observation_result' ORDER BY seq DESC LIMIT 1",(key,)).fetchone()
        d=json.loads(last['detail']) if last else {}
        if d.get('idx')!=idx or d.get('result')!='NO_AD':raise ValueError('only a confirmed closed no-ad observation can immediately repeat')
        q.db.execute("UPDATE jobs SET state='RUNNING',owner=?,lease_until=? WHERE key=?",(owner,q.now()+600,key))
        q.event(key,'claimed',{'owner':owner,'same_process_immediate_no_ad_retry':True,'idx':idx})
        return q.job(key)


def approve_repair(q,key,owner,idx,probe):
    """Accept only a real probe receipt persisted by the bounded probe runner."""
    with q.tx():
        j=q.job(key)
        if j['state']!='REPAIRING' or j['owner']!=owner or j['lease_until']<q.now():raise ValueError('active technical-repair owner required')
        row=q.db.execute("SELECT seq,at,detail FROM events WHERE job=? AND kind='technical_probe_verified' ORDER BY seq DESC LIMIT 1",(key,)).fetchone()
        if not row:raise ValueError('actual verified probe receipt required')
        receipt=json.loads(row['detail'])
        if receipt.get('owner')!=owner or receipt.get('idx')!=idx or receipt.get('probe_file')!=probe:
            raise ValueError('technical probe receipt belongs to another attempt')
        latest=q.db.execute("SELECT at FROM events WHERE job=? AND kind='observation_result' ORDER BY seq DESC LIMIT 1",(key,)).fetchone()
        if latest and row['at']<latest['at']:raise ValueError('technical probe predates latest error')
        q.event(key,'technical_repair_approved',{'idx':idx,'owner':owner,'probe_event_seq':row['seq'],'no_ad_history_preserved':True,'observation_success':False})
        q.db.execute("UPDATE links SET state='WAIT_RETRY',due=? WHERE job=? AND idx=? AND state='TECHNICAL_REPAIR'",(q.now(),key,idx))
        from .landing_retry_policy import refresh
        refresh(q,key)


def latest_probe_for_cleanup(q,key,idx):
    opened=0
    for row in q.db.execute("SELECT seq,detail FROM events WHERE job=? AND kind='open_intent' ORDER BY seq DESC",(key,)):
        if json.loads(row['detail']).get('idx')==idx:opened=row['seq'];break
    for row in q.db.execute("SELECT seq,detail FROM events WHERE job=? AND kind='technical_probe_intent' ORDER BY seq DESC",(key,)):
        d=json.loads(row['detail'])
        if d.get('idx')==idx:return d.get('probe_file') if row['seq']>opened else None
    return None
