"""Finite, authority-scoped 3+1 no-ad policy. No browser or platform writes."""
from __future__ import annotations
import json
from . import landing_followup as core


def policy():
    try:
        p=json.loads((core.BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text()).get('no_ad_retry_policy') or {}
    except (OSError,ValueError):return {}
    if p.get('enabled') is not True:return {}
    if (p.get('initial_no_ad_attempts'),p.get('final_no_ad_attempts'))!=(3,1):
        raise ValueError('approved finite no-ad policy must be exactly 3+1')
    if not p.get('generation') or p.get('authority_thread_id')!=core.INCIDENT_THREAD:
        raise ValueError('explicit finite retry authority required')
    return p


def final_start(q,key,idx):
    for r in q.db.execute("SELECT seq,detail FROM events WHERE job=? AND kind='finite_final_started' ORDER BY seq DESC",(key,)):
        if json.loads(r['detail']).get('idx')==idx:return r['seq']
    return None


def limit(q,key,idx):
    p=policy()
    return (1 if final_start(q,key,idx) else 3) if p else 2


def count(q,key,idx):
    cutoff=final_start(q,key,idx)
    if cutoff is None:return None  # core retains earlier priority-cycle history
    attempts=set()
    for r in q.db.execute("SELECT seq,detail FROM events WHERE job=? AND seq>? AND kind IN ('observation_result','reconciled_no_ad')",(key,cutoff)):
        d=json.loads(r['detail'])
        if d.get('idx')==idx and d.get('result')=='NO_AD':attempts.add(d.get('attempt',r['seq']))
    return len(attempts)


def exhausted_state(q,key,idx):
    return 'REVIEW_REQUIRED' if final_start(q,key,idx) else 'DEFERRED_NO_AD'


def refresh(q,key):
    states={r['state'] for r in q.db.execute('SELECT state FROM links WHERE job=?',(key,))}
    if states=={'PASSED'}:state='OBSERVED'
    elif 'OPEN_INTENT' in states:state='NEEDS_RECONCILIATION'
    elif states.intersection({'READY','WAIT_RETRY'}):state='READY'
    elif 'ATTENTION' in states:state='ATTENTION'
    elif 'TECHNICAL_REPAIR' in states:state='TECHNICAL_REPAIR'
    elif 'DEFERRED_NO_AD' in states:state='DEFERRED_NO_AD'
    elif 'REVIEW_REQUIRED' in states:state='WAITING_HUMAN'
    else:raise ValueError('unrecognized finite retry state')
    q.db.execute('UPDATE jobs SET state=?,owner=NULL,lease_until=NULL WHERE key=?',(state,key))
    return state


def closed_latest(q,key,link):
    try:
        e=json.loads(link['evidence'] or '{}');core.validate_closure(e)
        opened=[r['at'] for r in q.db.execute("SELECT at,detail FROM events WHERE job=? AND kind='open_intent' ORDER BY seq",(key,)) if json.loads(r['detail']).get('idx')==link['idx']]
        if not opened:return False
        return core.file_evidence(e['closed_screenshot'])['captured_at']>=opened[-1]
    except (ValueError,KeyError,TypeError,OSError):return False


def maintain(q):
    """Run under dispatcher flock. Never mutate a live/uncertain browser attempt."""
    p=policy()
    if not p:return {'state':'LEGACY_POLICY'}
    with q.tx():
        if q.db.execute("SELECT 1 FROM jobs WHERE state IN ('RUNNING','RECONCILING','NEEDS_RECONCILIATION','WAITING_HUMAN_UNCLOSED')").fetchone():
            return {'state':'WAITING_SAFE_BOUNDARY'}
        changed=[]
        # Migrate previously exhausted two-attempt links without resetting history.
        for job in q.db.execute("SELECT key FROM jobs WHERE state IN ('ATTENTION','READY','DEFERRED_NO_AD') ORDER BY created,key").fetchall():
            key=job['key'];touched=False
            for link in q.db.execute("SELECT * FROM links WHERE job=? AND state='ATTENTION'",(key,)).fetchall():
                n=q.no_ad_count(key,link['idx'])
                if not n or not closed_latest(q,key,link):continue
                state='WAIT_RETRY' if n<limit(q,key,link['idx']) else exhausted_state(q,key,link['idx'])
                from .landing_reliability import no_ad_delay
                q.db.execute('UPDATE links SET state=?,due=? WHERE job=? AND idx=?',(state,q.now()+no_ad_delay() if state=='WAIT_RETRY' else 0,key,link['idx']))
                q.event(key,'finite_retry_migrated',{'idx':link['idx'],'previous_no_ads':n,'state':state,'generation':p['generation'],'history_preserved':True})
                touched=True;changed.append([key,link['idx'],state])
            if touched:refresh(q,key)
        # The final pass only begins after all normal observations (including
        # future-due retries) are settled. OBSERVED/COMPLETE need no new visits.
        # Freeze peers at the first deferral: later intake cannot postpone the
        # final return forever. One cohort is drained before opening another.
        batch=None
        for r in q.db.execute("SELECT seq,detail FROM events WHERE kind='finite_cohort_started' ORDER BY seq DESC"):
            detail=json.loads(r['detail'])
            if detail.get('generation')!=p['generation']:continue
            done=any(json.loads(x['detail']).get('batch_seq')==r['seq'] for x in q.db.execute("SELECT detail FROM events WHERE kind='finite_cohort_completed'"))
            if not done:batch=(r['seq'],detail['jobs'])
            break
        if batch is None and q.db.execute("SELECT 1 FROM links WHERE state='DEFERRED_NO_AD'").fetchone():
            peers=[r['key'] for r in q.db.execute("SELECT key FROM jobs WHERE reply_id IS NOT NULL AND state IN ('READY','ATTENTION','DEFERRED_NO_AD') ORDER BY created,key")]
            q.event(None,'finite_cohort_started',{'generation':p['generation'],'jobs':peers})
            batch=(q.db.execute('SELECT max(seq) FROM events').fetchone()[0],peers)
        peers=set(batch[1]) if batch else None
        initial=[r for r in q.db.execute("SELECT l.job,l.idx FROM links l JOIN jobs j ON j.key=l.job WHERE j.reply_id IS NOT NULL AND j.state NOT IN ('WAITING_HUMAN','WAITING_HUMAN_UNCLOSED') AND l.state IN ('READY','WAIT_RETRY','OPEN_INTENT')") if peers is None or r['job'] in peers]
        if initial:return {'state':'INITIAL_OR_FINAL_IN_PROGRESS','changed':changed}
        candidate=next((r for r in q.db.execute("SELECT l.* FROM links l JOIN jobs j ON j.key=l.job WHERE l.state='DEFERRED_NO_AD' AND j.state='DEFERRED_NO_AD' ORDER BY j.created,j.key,l.idx") if peers is None or r['job'] in peers),None)
        if candidate:
            key=candidate['job'];idx=candidate['idx']
            if not closed_latest(q,key,candidate):
                q.db.execute("UPDATE links SET state='ATTENTION' WHERE job=? AND idx=?",(key,idx));refresh(q,key)
                q.event(key,'finite_final_needs_closure',{'idx':idx});return {'state':'CLEANUP_REQUIRED'}
            if final_start(q,key,idx):raise ValueError('finite final pass cannot repeat')
            q.event(key,'finite_final_started',{'idx':idx,'generation':p['generation'],'initial_no_ads':q.no_ad_count(key,idx),'maximum_no_ad_attempts':1,'new_visit_not_yet_started':True})
            from .landing_reliability import no_ad_delay
            q.db.execute("UPDATE links SET state='WAIT_RETRY',due=? WHERE job=? AND idx=?",(q.now()+no_ad_delay(),key,idx));refresh(q,key)
            return {'state':'FINAL_RETRY_SCHEDULED','job':key,'idx':idx,'changed':changed}
        # One immutable final report per failed combination, only when the
        # entire retry pass is over. Outbox + exact GET, never a synthetic PASS.
        for link in q.db.execute("SELECT l.*,j.payload FROM links l JOIN jobs j ON j.key=l.job WHERE l.state='REVIEW_REQUIRED' ORDER BY j.created,j.key,l.idx").fetchall():
            key=link['job'];idx=link['idx'];payload=json.loads(link['payload']);e=json.loads(link['evidence'] or '{}')
            if peers is not None and key not in peers:continue
            url=e.get('observed_url') or payload['links'][idx].get('landing_url') or payload['links'][idx]['effective_campaign_url']
            core.scope(url)
            message_key='landing-final-review:'+p['generation']+':'+key+':'+str(idx)
            if q.db.execute('SELECT 1 FROM messages WHERE key=?',(message_key,)).fetchone():continue
            utm=dict(core.urllib.parse.parse_qsl(core.urllib.parse.urlsplit(url).query)).get('utm_campaign','')
            content=('**Landing pendente — revisão de Rodolfo**\n'
                f"Pedido: {payload['request_id']} · conta: {payload['account_id']} · campanha: {utm}\n"
                'Sem anúncio visível em 3 tentativas iniciais e em 1 tentativa final, após os demais links.\n'
                f'{url}\nAção solicitada: revisar a exibição de anúncios deste link. Não validado; sem nova repetição automática.')
            q.prepare_message(message_key,core.INCIDENT_THREAD,content)
            q.event(key,'finite_review_report_authorized',{'idx':idx,'notification_key':message_key,'generation':p['generation'],'authority_thread_id':p['authority_thread_id']})
        if batch:q.event(None,'finite_cohort_completed',{'batch_seq':batch[0],'generation':p['generation'],'validation_success_not_implied':True})
        return {'state':'FINITE_PASS_SETTLED','changed':changed}
