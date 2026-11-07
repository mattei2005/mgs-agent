"""Offline safety verification for the frozen 33-campaign one-shot."""
import copy
import importlib.util
import json
from datetime import datetime,timedelta
from pathlib import Path

ROOT=Path('/root/mgs-agent/data/ares/meta-ads/state/status-1568410965559476336')
spec=importlib.util.spec_from_file_location('new_status_wrapper','/root/.hermes/profiles/ares/scripts/shein-status-1568410965559476336.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
u=w.u;m=w.m;s=json.loads(w.PATH.read_text());at=datetime.fromisoformat(s['activate_at']);count=0
u.validate(s['prepared'],s,s['prepared']);count+=1
for n,base in s['prepared'].items():
    for field in ['budget','name','bid','schedule','creative','tracking','child','parent','hierarchy','targeting']:
        row=copy.deepcopy(base)
        if field=='budget':row['daily_budget']=str(int(row.get('daily_budget') or 0)+1)
        elif field=='name':row['name']+=' drift'
        elif field=='bid':row['adsets']['data'][0]['bid_amount']=9999999
        elif field=='schedule':row['adsets']['data'][0]['start_time']='2027-01-01T00:00:00-0500'
        elif field=='creative':row['ads']['data'][0]['creative']['id']='drift'
        elif field=='tracking':row['ads']['data'][0]['tracking_specs']=[{'drift':True}]
        elif field=='child':row['ads']['data'][0]['configured_status']='PAUSED' if u.configured(row['ads']['data'][0])=='ACTIVE' else 'ACTIVE'
        elif field=='parent':row['ads']['data'][0]['adset_id']='drift'
        elif field=='targeting':row['adsets']['data'][0]['targeting']={'drift':True}
        else:row['ads']['data']=[]
        try:u.validate({n:row},s,s['prepared'])
        except u.GateError:count+=1
        else:raise AssertionError('accepted drift '+n+' '+field)
for stamp in [at-timedelta(seconds=1),at+timedelta(minutes=16)]:
    try:u.time_gate(s,stamp)
    except u.GateError:count+=1
    else:raise AssertionError('time gate')
u.time_gate(s,at);count+=1
fixture=ROOT/'offline-fixture.json';old_loader=u.load_common;old_sleep=m.time.sleep;old_notify=w.notify
calls=[]
def forbidden(*a,**k):raise AssertionError('external effect reached')
class WaitProved(Exception):pass
def wait_sentinel(seconds):calls.append(seconds);raise WaitProved()
u.load_common=forbidden;w.notify=forbidden
try:
    u.save(fixture,copy.deepcopy(s))
    try:w.main('activate',state_path=fixture,now=at-timedelta(seconds=1),allow_wait=False)
    except u.GateError:count+=1
    else:raise AssertionError('public wrapper allowed early API')
    m.time.sleep=wait_sentinel
    physical=datetime.fromisoformat('2026-11-06T23:53:15-05:00')
    try:w.main('activate',state_path=fixture,now=physical)
    except WaitProved:assert calls==[405.0];count+=1
    else:raise AssertionError('wrapper wait missing')
    replay=copy.deepcopy(s);replay.update(status='COMPLETE_ACTIVATED',notification_status='DELIVERED');u.save(fixture,replay)
    w.main('activate',state_path=fixture,now=at-timedelta(days=1));count+=1
finally:u.load_common=old_loader;m.time.sleep=old_sleep;w.notify=old_notify
# Simulated entire activation entrypoint: no real credentials, HTTP or delivery.
fixture=ROOT/'offline-activation.json';fake=copy.deepcopy(s);fake['status']='SCHEDULED';u.save(fixture,fake);rows=copy.deepcopy(s['prepared']);by_id={cid:n for n,cid in s['campaign_ids'].items()};writes=[];checkpoints=[];notices=[]
class Clock(datetime):
    @classmethod
    def now(cls,tz=None):return at if tz is None else at.astimezone(tz)
class Client:
    def get_token_from_1password(self,item):return ('OFFLINE_SENTINEL','OFFLINE')
    def graph_post_once(self,cid,token,payload):
        assert cid in by_id and payload=={'status':'ACTIVE'} and token=='OFFLINE_SENTINEL'
        n=by_id[cid];rows[n].update(status='ACTIVE',configured_status='ACTIVE',effective_status='ACTIVE');writes.append(cid)
        return 200,{'success':True},{}
client=Client();old={k:getattr(u,k) for k in ['load_common','preflight','fetch','get','finish_checkpoint','datetime']};old_check=w.checkpoint;old_mcheck=m.checkpoint;old_notify=w.notify
try:
    u.load_common=lambda:client;u.preflight=lambda *a:None
    u.fetch=lambda c,t,state:copy.deepcopy(rows)
    u.get=lambda c,t,cid,fields:copy.deepcopy(rows[by_id[cid]])
    u.finish_checkpoint=lambda state,desc,nxt:checkpoints.append((state['source_thread_id'],len(state['campaign_ids']),desc))
    w.checkpoint=lambda state,desc,nxt:checkpoints.append((state['source_thread_id'],len(state['campaign_ids']),desc));m.checkpoint=w.checkpoint
    w.notify=lambda state,content,kind='success':notices.append((state['source_thread_id'],content,kind))
    u.datetime=Clock
    w.main('activate',state_path=fixture,now=at)
finally:
    for k,v in old.items():setattr(u,k,v)
    w.checkpoint=old_check;m.checkpoint=old_mcheck;w.notify=old_notify
finished=json.loads(fixture.read_text());assert finished['status']=='COMPLETE_ACTIVATED';assert len(writes)==len(s['campaign_ids']) and len(set(writes))==len(writes);assert finished['confirmed_count']==len(s['campaign_ids']);assert all(x[0]==s['source_thread_id'] and x[1]==len(s['campaign_ids']) for x in checkpoints);assert len(notices)==1 and notices[0][0]==s['source_thread_id'] and str(len(s['campaign_ids'])) in notices[0][1] and '07/11/2026' in notices[0][1] and 'G002' not in notices[0][1] and '28 campanhas' not in notices[0][1];count+=5
result={'checks_passed':count,'campaign_count':len(s['campaign_ids']),'meta_calls':0,'real_meta_writes':0,'offline_simulated_status_writes':len(writes),'full_entrypoint_early_block':True,'full_entrypoint_replay_no_calls':True,'physical_wait_seconds':405,'completion_content_scope_verified':True}
u.save(ROOT/'safety-tests.json',result);print(json.dumps(result))
