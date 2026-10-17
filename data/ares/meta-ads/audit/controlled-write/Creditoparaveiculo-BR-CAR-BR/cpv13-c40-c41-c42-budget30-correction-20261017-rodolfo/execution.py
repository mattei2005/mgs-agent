import copy
import importlib.util
import json
import time
from datetime import datetime
from pathlib import Path
spec=importlib.util.spec_from_file_location('r','/root/.hermes/profiles/ares/scripts/cpv13-d1-restart-20261018-19.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
REQUEST='cpv13-c40-c41-c42-budget30-correction-20261017-rodolfo'
AUDIT=r.BASE/'data/ares/meta-ads/audit/controlled-write/Creditoparaveiculo-BR-CAR-BR'/REQUEST
STATE=AUDIT/'request.json'
def save(s):
 s['updated_at_sp']=datetime.now(r.a.SP).isoformat();r.a.atomic_json(STATE,s)
lock=r.a.acquire_lane_lock(wait_seconds=20)
try:
 cfgs=r.a.load_json(r.CONFIG)['batches'];c=r.a.load_common();ac=r.a.load_json(r.a.ACCOUNT_PATH)['accounts'][0];token,_=c.get_token_from_1password(ac['token_1password_item']);account=r.a.account_preflight(c,token)
 s=r.a.load_json(STATE) if STATE.exists() else {'request_id':REQUEST,'authorized_by':'Rodolfo Mattei','authorization_source':r.a.AUTHORIZATION_SOURCE,'desired_budget_minor':3000,'schedule_write':False,'status':'INTAKE','scope':'C40/C41/C42 USD30 per day; C32 correction to C42 recorded, duplicate-date intent awaits operator confirmation'}
 snapshots={};states={}
 for batch,cfg in cfgs.items():
  states[batch]=r.a.load_json(r.paths(cfg)[0]);snapshots[batch]=r.live(cfg,c,token)
  if not s.get('before'):r.validate(cfg,snapshots[batch],states[batch]['prepared'])
  if any(r.a.configured(x)!='PAUSED' for x in snapshots[batch].values()):raise r.a.ActionError('campaign_not_paused')
 if 'before' not in s:s['before']=snapshots;s['account_readback']=account;save(s)
 for batch,cfg in cfgs.items():
  r.p.IDS={n:t['campaign_id'] for n,t in cfg['targets'].items()}
  for n,row in snapshots[batch].items():
   prior=s['before'][batch][n];want=copy.deepcopy(prior);want['daily_budget']='3000'
   if r.p.invariant(row) not in [r.p.invariant(prior),r.p.invariant(want)]:raise r.a.ActionError('unexpected_material_drift_'+n)
   if int(row['daily_budget'])==3000:
    if s.get('writes',{}).get(n):
     s['writes'][n].update(stage='confirmed_by_recovery_get',after=row,post_replayed=False);save(s)
    continue
   if s.get('writes',{}).get(n):raise r.a.ActionError('prior_attempt_requires_explicit_reconciled_retry_'+n)
   s.setdefault('writes',{})[n]={'stage':'in_flight','before':row,'desired_daily_budget_minor':3000};s['status']='BUDGET_IN_FLIGHT';save(s)
   http,payload,_=c.graph_post_once(row['id'],token,{'daily_budget':3000})
   after=r.p.get(c,token,n)
   if int(after.get('daily_budget',0))!=3000 or r.a.configured(after)!='PAUSED' or r.p.invariant(after)!=r.p.invariant(want):raise r.a.ActionError('budget_readback_pending_'+n)
   s['writes'][n].update(stage='confirmed',post_http=http,after=after);save(s)
 final={}
 for batch,cfg in cfgs.items():
  stable=None
  for _ in range(4):
   first=r.live(cfg,c,token);time.sleep(3);second=r.live(cfg,c,token)
   if all(r.p.invariant(first[n])==r.p.invariant(second[n]) and first[n]['updated_time']==second[n]['updated_time'] for n in first):stable=second;break
  if stable is None:raise r.a.ActionError('settling_readback_pending')
  for n,row in stable.items():
   want=copy.deepcopy(s['before'][batch][n]);want['daily_budget']='3000'
   if r.p.invariant(row)!=r.p.invariant(want) or r.a.configured(row)!='PAUSED':raise r.a.ActionError('final_drift_'+n)
  st=states[batch]
  if st.get('budget_amendment_request')!=REQUEST:
   st.setdefault('preparation_amendments',[]).append({'request_id':REQUEST,'prior_prepared':copy.deepcopy(st['prepared']),'authorized_by':'Rodolfo Mattei','reason':'explicit USD30 daily budget request'})
  st.update(prepared=stable,budget_amendment_request=REQUEST)
  r.save(cfg,st);r.commit(cfg,st)
  final.update(stable)
 config=r.a.load_json(r.CONFIG)
 config['pending_c32'].update(state='CORRECTED_TO_C42_SCHEDULE_NEEDS_CONFIRMATION',corrected_campaign_number='42',next_step='Rodolfo to confirm whether C42 stays 18-10 and restarts D1 again 19-10, or moves to 19-10; preserve existing schedules until answer')
 config['budget_amendment']={'request_id':REQUEST,'budget_minor_each':3000,'campaign_numbers':['40','41','42'],'authorized_by':'Rodolfo Mattei','status':'COMPLETE_VERIFIED','audit':str(STATE),'schedules_unchanged':True}
 r.a.atomic_json(r.CONFIG,config)
 s.update(status='COMPLETE_VERIFIED',final_readback=final,schedules_unchanged=True);save(s)
 print(json.dumps({'status':s['status'],'budget_usd_daily':{n:int(row['daily_budget'])/100 for n,row in final.items()},'statuses':{n:r.a.configured(row) for n,row in final.items()},'schedules_changed':False,'C42_schedule_decision_pending':True}))
finally:lock.close()
