import importlib.util,json,copy,contextlib,io
from pathlib import Path
from datetime import datetime,timedelta
sp=importlib.util.spec_from_file_location('w','/root/.hermes/profiles/ares/scripts/shein-status-1569148392355926029.py');w=importlib.util.module_from_spec(sp);sp.loader.exec_module(w)
u=w.u;m=w.m;s=json.loads(w.PATH.read_text());at=datetime.fromisoformat(s['activate_at']);physical=datetime.fromisoformat(json.loads((w.ROOT/'schedule-selection.json').read_text())['physical_start'])
fixture=Path('/root/.hermes/profiles/ares/cache/scratch/status-1569148392355926029-fixture.json');count=0
for n,base in s['prepared'].items():
 for kind in ['daily_budget','name','bid_strategy','tracking','creative','child','schedule','bid','parent','hierarchy']:
  row=copy.deepcopy(base)
  if kind in ['daily_budget','name','bid_strategy']:row[kind]=str(row.get(kind,''))+'X'
  elif kind=='tracking':row['ads']['data'][0]['tracking_specs']=[{'drift':1}]
  elif kind=='creative':row['ads']['data'][0]['creative']['id']='changed'
  elif kind=='child':row['ads']['data'][0]['configured_status']='PAUSED' if row['ads']['data'][0]['configured_status']=='ACTIVE' else 'ACTIVE'
  elif kind=='schedule':row['adsets']['data'][0]['start_time']='2027-01-01T00:00:00-0500'
  elif kind=='bid':row['adsets']['data'][0]['bid_amount']=9999999
  elif kind=='parent':row['account_id']='changed'
  else:row['ads']['data']=[]
  try:u.validate({n:row},s,s['prepared'])
  except u.GateError:count+=1
  else:raise AssertionError('accepted drift '+n+' '+kind)
for stamp in [at-timedelta(seconds=1),at+timedelta(minutes=16)]:
 try:u.time_gate(s,stamp)
 except u.GateError:count+=1
 else:raise AssertionError('clock bypass')
events=[]
def forbidden(*a,**kw):raise AssertionError('unexpected external action')
w.w.notify=forbidden;w.w.checkpoint=forbidden;m.checkpoint=forbidden;u.finish_checkpoint=forbidden;u.load_common=forbidden
u.save(fixture,copy.deepcopy(s))
try:w.main('activate',fixture,now=at-timedelta(minutes=11),allow_wait=True,send_notice=False)
except u.GateError as ex:assert str(ex)=='invoked_too_early';count+=1
else:raise AssertionError('early entry bypass')
class WaitStop(Exception):pass
def wait(seconds):events.append(('wait',seconds));raise WaitStop()
m.time.sleep=wait
try:w.main('activate',fixture,now=physical,allow_wait=True,send_notice=False)
except WaitStop:assert events==[('wait',(at-physical).total_seconds())];count+=1
else:raise AssertionError('physical gate failed')
replay=copy.deepcopy(s);replay['status']='COMPLETE_ACTIVATED';replay['notification_status']='DELIVERED';u.save(fixture,replay);w.main('activate',fixture,now=at-timedelta(days=1));count+=1
# Full public wrapper simulation: no real credentials/API, lease, checkpoint or Discord.
class Clock(datetime):
 @classmethod
 def now(cls,tz=None):return at.astimezone(tz) if tz else at
u.datetime=Clock
class Lease:
 def __init__(self,*a):pass
 def claim(self,*a,**k):events.append(('claim',a))
 def release(self,*a):events.append(('release',a))
 def mark(self,*a):raise AssertionError('unexpected recovery')
u.AccountWriterLeaseStore=Lease
rows={x['id']:copy.deepcopy(x) for x in s['prepared'].values()};posts=[]
class Common:
 def get_token_from_1password(self,item):return 'offline','token'
 def graph_get(self,path,token,params=None):return 200,copy.deepcopy(rows[path]),{}
 def graph_batch_get(self,token,requests):return 200,[{'name':q['name'],'code':200,'body':copy.deepcopy(rows[q['path']])} for q in requests],{}
 def graph_post_once(self,path,token,payload):
  assert path in set(s['campaign_ids'].values()) and payload=={'status':'ACTIVE'}
  posts.append(path);rows[path].update(status='ACTIVE',configured_status='ACTIVE',effective_status='ACTIVE');return 200,{'success':True},{}
u.load_common=lambda:Common();u.preflight=lambda c,t,state:events.append(('preflight',state['account_id']))
checkpoints=[];notices=[]
def checkpoint(state,st,next_step):checkpoints.append({'account':state['account_id'],'source':state['source_message_id'],'thread':state['source_thread_id'],'total':len(state['requested_campaign_ids']),'ready':len(state['campaign_ids'])})
u.finish_checkpoint=checkpoint;w.w.checkpoint=checkpoint;m.checkpoint=checkpoint
w.w.notify=lambda state,text,*args:notices.append({'thread':state['source_thread_id'],'text':text})
sim=copy.deepcopy(s);sim['status']='SCHEDULED';u.save(fixture,sim)
with contextlib.redirect_stdout(io.StringIO()):w.main('activate',fixture,now=at,send_notice=True)
final=json.loads(fixture.read_text());assert final['status']=='COMPLETE_ACTIVATED' and final['confirmed_count']==26
assert set(posts)==set(s['campaign_ids'].values()) and len(posts)==26
assert set(final['final_readback'])==set(s['campaign_ids'])
assert checkpoints and all(x=={'account':'1583000095650153','source':'1569148392355926029','thread':'1558134300325716050','total':27,'ready':26} for x in checkpoints)
assert len(notices)==1 and notices[0]['thread']=='1558134300325716050' and '26 campanhas' in notices[0]['text'] and '9 de novembro de 2026' in notices[0]['text'] and '00h05' in notices[0]['text']
count+=5
fixture.unlink();result={'tests_passed':count,'live_api_calls':0,'live_meta_writes':0,'frozen_requested':27,'prepared':26,'blocked':['376'],'simulated_status_posts':len(posts),'full_entry_early':True,'physical_wait_seconds':(at-physical).total_seconds(),'replay_no_effects':True,'completion_checkpoints':checkpoints,'completion_notices':notices}
u.datetime=datetime;u.save(w.ROOT/'safety-tests.json',result);print(json.dumps(result,ensure_ascii=False))
