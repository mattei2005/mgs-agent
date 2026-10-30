"""Prepared, serial PC1 batches. Queue/mapping only; no browser or platform writes."""
from __future__ import annotations
import json,urllib.parse
from . import landing_followup as core
from . import landing_retry_policy as finite
from .landing_lean import observation_url,tracking_query_matches

PENDING={'READY','WAIT_RETRY','DEFERRED_NO_AD','COOLDOWN_NO_AD'}

def policy():
    try:p=json.loads((core.BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text()).get('continuous_execution') or {}
    except (OSError,ValueError):return {}
    if p.get('enabled') is not True:return {}
    budget=p.get('maximum_run_seconds',10800)
    if type(budget) is not int or not 600<=budget<=10800:raise ValueError('bounded continuous-worker budget required')
    return p


def freeze_scope(q,key,owner):
    first=q.owned(key,owner);eligible=[]
    # A return phase uses its frozen peers, not an unbounded stream of new intake.
    peer_filter=None;prior_report_jobs=None
    for row in q.db.execute("SELECT detail FROM events WHERE kind='continuous_batch_started' ORDER BY seq DESC"):
        prior=json.loads(row['detail'])
        if key in prior.get('jobs',[]):
            prior_report_jobs=prior.get('report_jobs') or prior['jobs'];peer_filter=set(prior_report_jobs);break
    returning=any(finite.final_start(q,key,l['idx']) or finite.recovery_start(q,key,l['idx']) for l in first['links'] if l['state'] in PENDING)
    if returning:
        for r in q.db.execute("SELECT detail FROM events WHERE kind='finite_cohort_started' ORDER BY seq DESC"):
            peers=json.loads(r['detail']).get('jobs',[])
            if key in peers:peer_filter=set(peers);break
    for row in q.db.execute("SELECT key FROM jobs WHERE state='READY' OR key=? ORDER BY created,key",(key,)):
        j=q.job(row['key'])
        if peer_filter is not None and j['key'] not in peer_filter:continue
        if any(l['state'] in PENDING for l in j['links']):eligible.append({'key':j['key'],'payload_digest':j['digest']})
    if not any(x['key']==key for x in eligible):raise ValueError('selected job not in prepared batch')
    report_jobs=prior_report_jobs or list(dict.fromkeys(peer for x in eligible for peer in q.success_group(x['key'])[0]))
    scope={'schema':1,'first_job':key,'owner':owner,'jobs':eligible,'report_jobs':report_jobs,'created_at':q.now()}
    scope['id']=core.digest([eligible,owner]);return scope


def validate_scope(q,scope,owner):
    if scope.get('schema')!=1 or scope.get('owner')!=owner or not scope.get('jobs'):raise ValueError('exact batch scope/owner required')
    if scope.get('id')!=core.digest([scope['jobs'],owner]):raise ValueError('frozen batch scope changed')
    keys=[x['key'] for x in scope['jobs']]
    if len(keys)!=len(set(keys)) or scope.get('first_job') not in keys:raise ValueError('duplicate/invalid batch jobs')
    for x in scope['jobs']:
        j=q.job(x['key'])
        if x['payload_digest']!=j['digest']:raise ValueError('immutable batch request changed')
    return keys


def required(q,scope):
    return {(x['key'],l['idx']) for x in scope['jobs'] for l in q.job(x['key'])['links'] if l['state'] in PENDING}


def ensure_cache(q):
    q.db.execute('CREATE TABLE IF NOT EXISTS prepared_landing_links(job TEXT NOT NULL,idx INTEGER NOT NULL,payload_digest TEXT NOT NULL,mapping TEXT NOT NULL,PRIMARY KEY(job,idx))')


def validate_mapping(q,item,check_scope=None):
    key=item.get('job');idx=item.get('index')
    if not isinstance(key,str) or type(idx) is not int:raise ValueError('literal job/index required')
    j=q.job(key)
    if idx<0 or idx>=len(j['links']):raise ValueError('mapping index outside request')
    link=j['payload']['links'][idx];url=item.get('url') or '';source=urllib.parse.urlsplit(link['effective_campaign_url']);dest=urllib.parse.urlsplit(url)
    if not item.get('mapping_source') or item.get('destination_count',1)!=1:raise ValueError('complete unambiguous mapping source required; distinct A/B destinations need their own coverage')
    (check_scope or core.scope)(url)
    if dest.scheme!='https' or source.hostname!=dest.hostname or not tracking_query_matches(dest.query,source.query) or core.re.search(r'/(quiz|chat)(/|$)',dest.path,core.re.I):raise ValueError('prepared landing/query differs from exact request')
    if link.get('landing_url') and url not in [link['landing_url'],observation_url(link['landing_url'])]:raise ValueError('canonical mapped destination changed')
    return {'job':key,'index':idx,'url':url,'mapping_source':item['mapping_source'],'destination_count':1,'payload_digest':j['digest']}


def store_manifest(q,scope,manifest,owner,check_scope=None):
    keys=validate_scope(q,scope,owner);items=manifest.get('items')
    if not isinstance(items,list):raise ValueError('prepared items required')
    pairs=[(x.get('job'),x.get('index')) for x in items]
    if len(pairs)!=len(set(pairs)) or set(pairs)!=required(q,scope):raise ValueError('prepare ALL pending batch links before the first visit')
    clean=[validate_mapping(q,x,check_scope) for x in items]
    if any(x['job'] not in keys for x in clean):raise ValueError('foreign mapping in batch')
    ensure_cache(q)
    with q.tx():
        for item in clean:
            old=q.db.execute('SELECT mapping FROM prepared_landing_links WHERE job=? AND idx=?',(item['job'],item['index'])).fetchone()
            if old and json.loads(old['mapping'])!=item:q.event(item['job'],'prepared_mapping_superseded',{'idx':item['index'],'previous':json.loads(old['mapping']),'new':item})
            q.db.execute('INSERT INTO prepared_landing_links VALUES(?,?,?,?) ON CONFLICT(job,idx) DO UPDATE SET payload_digest=excluded.payload_digest,mapping=excluded.mapping',(item['job'],item['index'],item['payload_digest'],json.dumps(item,ensure_ascii=False)))
        q.event(None,'continuous_batch_prepared',{'scope_id':scope['id'],'jobs':keys,'items':len(clean),'meta_writes':0})
    return clean


def cached_manifest(q,scope,owner):
    validate_scope(q,scope,owner);ensure_cache(q);out=[];missing=[]
    for key,idx in sorted(required(q,scope)):
        row=q.db.execute('SELECT * FROM prepared_landing_links WHERE job=? AND idx=?',(key,idx)).fetchone();j=q.job(key);link=j['payload']['links'][idx]
        if row and row['payload_digest']==j['digest']:out.append(json.loads(row['mapping']))
        elif link.get('landing_url') and link.get('mapping_source'):out.append({'job':key,'index':idx,'url':link['landing_url'],'mapping_source':link['mapping_source'],'destination_count':1})
        else:missing.append({'job':key,'index':idx,'effective_campaign_url':link['effective_campaign_url']})
    return {'items':out,'missing':missing}


def run(q,scope,owner,execute,*,before_attempt=lambda:None,should_stop=lambda:False):
    """Pure queue loop; execute receives one exact item and persists real evidence.

    No model turn, network notification or backend release between URLs. One
    failed/uncertain item yields diagnosis; finite cooldown returns without sleep.
    """
    keys=set(validate_scope(q,scope,owner));prepared=cached_manifest(q,scope,owner)
    if prepared['missing']:return {'state':'MAPPING_REQUIRED','missing':prepared['missing'],'browser_actions':0}
    mappings={(x['job'],x['index']):validate_mapping(q,x) for x in prepared['items']}
    with q.tx():q.event(None,'continuous_batch_started',{'scope_id':scope['id'],'jobs':list(keys),'report_jobs':scope.get('report_jobs',list(keys)),'owner':owner})
    results=[]
    while not should_stop():
        owned=next((q.job(k) for k in keys if q.job(k)['state']=='RUNNING' and q.job(k)['owner']==owner),None)
        if owned is None:
            ready=any(j['state']=='READY' and any(l['state'] in {'READY','WAIT_RETRY'} and l['due']<=q.now() for l in j['links']) for j in (q.job(k) for k in keys))
            if not ready:
                transition=finite.maintain(q)
                ready=any(j['state']=='READY' and any(l['state'] in {'READY','WAIT_RETRY'} and l['due']<=q.now() for l in j['links']) for j in (q.job(k) for k in keys))
                if not ready:return {'state':transition['state'],'transition':transition,'results':results}
            owned=q.claim(owner,ttl=900)
            if not owned:return {'state':'WAITING_QUEUE_BOUNDARY','results':results}
            if owned['key'] not in keys:q.deferred(owned['key'],owner);return {'state':'YIELD_OLDER_DUE_WORK','results':results}
        idx=next((l['idx'] for l in owned['links'] if l['state'] in {'READY','WAIT_RETRY'} and l['due']<=q.now()),None)
        if idx is None:raise ValueError('batch owned job has no due item; reconcile before retry')
        item=mappings[(owned['key'],idx)];before_attempt();q.begin(owned['key'],owner,idx)
        result,evidence=execute(item,q.job(owned['key'])['links'][idx]['attempt'])
        q.result(owned['key'],owner,idx,result,evidence)
        results.append({'job':owned['key'],'idx':idx,'result':result})
        if result=='ERROR':return {'state':'BATCH_TECHNICAL_DIAGNOSIS','results':results,'diagnosis':evidence.get('diagnosis'),'safe_closed':bool(evidence.get('tab_closed_verified') or evidence.get('no_tab_opened'))}
    # Stop only between attempts, never while a landing is kept open.
    for k in keys:
        j=q.job(k)
        if j['state']=='RUNNING' and j['owner']==owner:q.deferred(k,owner)
    return {'state':'PAUSED_AT_SAFE_BOUNDARY','results':results}
