import importlib.util,json,copy,contextlib,io
from pathlib import Path
from datetime import datetime,timedelta
from unittest.mock import patch
sp=importlib.util.spec_from_file_location('subject','/root/.hermes/profiles/ares/scripts/shein-status-1572388562752770230.py');x=importlib.util.module_from_spec(sp);sp.loader.exec_module(x)
u=x.u;m=x.m;s=json.loads(x.PATH.read_text());at=datetime.fromisoformat(s['activate_at']);r=x.ROOT
fixture=Path('/root/.hermes/profiles/ares/cache/scratch/status-fixture-1572388562752770230.json')
checks=[]
def ok(name):checks.append(name)
def forbidden(*a,**kw):raise AssertionError('forbidden external side effect')
def save(v):u.save(fixture,copy.deepcopy(v))
# Every invariant is exercised for every selected campaign.
u.validate(s['prepared'],s,s['prepared']);ok('baseline')
for n,base in s['prepared'].items():
 for kind in ['budget','name','creative','tracking','child','schedule','bid','parent','hierarchy']:
  row=copy.deepcopy(base)
  if kind=='budget':row['daily_budget']='99999999'
  elif kind=='name':row['name']+=' changed'
  elif kind=='creative':row['ads']['data'][0]['creative']['id']='changed'
  elif kind=='tracking':
   ad=next(v for v in row['ads']['data'] if 'tracking_specs' in v or 'conversion_specs' in v)
   k='tracking_specs' if 'tracking_specs' in ad else 'conversion_specs';ad[k]=[{'changed':True}]
  elif kind=='child':row['ads']['data'][0]['configured_status']='PAUSED' if row['ads']['data'][0]['configured_status']=='ACTIVE' else 'ACTIVE'
  elif kind=='schedule':row['adsets']['data'][0]['start_time']='2027-01-01T00:00:00-0500'
  elif kind=='bid':row['adsets']['data'][0]['bid_amount']=999999
  elif kind=='parent':row['account_id']='other'
  else:row['ads']['data']=[]
  try:u.validate({n:row},s,s['prepared'])
  except u.GateError:ok(n+':reject_'+kind)
  else:raise AssertionError('accepted drift '+kind)
for delta in [-1,901]:
 try:u.time_gate(s,at+timedelta(seconds=delta))
 except u.GateError:ok('time_gate_'+str(delta))
 else:raise AssertionError('time guard')
# True public entrypoint early block and physical waiting; no lane/credential/API.
save(s)
with patch.object(u,'load_common',forbidden),patch.object(m.fcntl,'flock',forbidden),patch.object(x.w,'notify',forbidden),patch.object(x.subprocess,'run',forbidden):
 try:x.main('activate',fixture,now=at-timedelta(seconds=1),allow_wait=False)
 except u.GateError:ok('public_early_no_effects')
 else:raise AssertionError('early bypass')
 inv=json.loads((r/'global-inventory-pre.json').read_text());physical=datetime.fromisoformat(inv['physical_start']);wait=(at-physical).total_seconds();seen=[]
 class WaitStop(Exception):pass
 def no_sleep(v):seen.append(v);raise WaitStop()
 with patch.object(m.time,'sleep',no_sleep):
  try:x.main('activate',fixture,now=physical)
  except WaitStop:pass
  else:raise AssertionError('wait not exercised')
 assert seen==[wait] and 0<=wait<=600;ok('physical_wait_'+str(wait))
 replay=copy.deepcopy(s);replay.update(status='COMPLETE_ACTIVATED',full_cohort_verified=True,notification_status='DELIVERED');save(replay)
 x.main('activate',fixture,now=at-timedelta(days=1));ok('public_replay_no_effects')
# Simulate public activation including terminal callbacks and integral exact coverage.
class SimDateTime(datetime):
 @classmethod
 def now(cls,tz=None):return at.astimezone(tz) if tz else at.astimezone()
class DummyFile:
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def fileno(self):return 99999
class Lease:
 def __init__(self,*a):pass
 def claim(self,*a,**kw):pass
 def release(self,*a,**kw):pass
 def mark(self,*a,**kw):raise AssertionError('recovery during simulation')
original_open=Path.open
for blocked_case in [False,True]:
 case=copy.deepcopy(s);case['status']='SCHEDULED';case['activation']={};case.pop('full_cohort_verified',None);case.pop('notification_status',None)
 if blocked_case:
  n=next(iter(case['campaign_ids']));case['campaign_ids'].pop(n);snap=case['prepared'].pop(n);case['activation_blocked']={n:{'snapshot':snap,'reason':'synthetic blocked path'}}
 allrows=copy.deepcopy(s['prepared']);posts=[];batches=[];notices=[];checkpoints=[]
 class Common:
  def get_token_from_1password(self,*a):return ('SENTINEL','field')
  def graph_batch_get(self,tok,queries):
   assert tok=='SENTINEL';batches.append([q['path'] for q in queries]);return 200,[{'name':q['name'],'code':200,'body':copy.deepcopy(allrows[q['name']])} for q in queries],{}
  def graph_post_once(self,cid,tok,payload):
   assert tok=='SENTINEL' and payload=={'status':'ACTIVE'}
   n=next(n for n,v in case['campaign_ids'].items() if v==cid);posts.append(cid);allrows[n].update(status='ACTIVE',configured_status='ACTIVE',effective_status='ACTIVE');return 200,{'success':True},{}
 c=Common()
 def fakeget(common,tok,cid,fields):return copy.deepcopy(next(v for v in allrows.values() if v['id']==cid))
 def fakeopen(path,*a,**kw):
  return DummyFile() if path.name=='account-'+s['account_id']+'.lock' else original_open(path,*a,**kw)
 def notice(state,content,*a):
  assert state['full_cohort_verified'] and set(state['full_cohort_readback'])==set(case['requested_campaign_ids'])
  assert str(len(case['campaign_ids']))+' de 29' in content and 'Mavroa Conta 06' in content
  if blocked_case:assert 'Permanecem pausadas: '+next(iter(case['activation_blocked'])) in content
  notices.append(content)
 def run(args,*a,**kw):
  if 'checkpoint-upsert' in args:
   state=json.loads(fixture.read_text());assert state.get('full_cohort_verified');assert '--thread-id' in args and s['source_thread_id'] in args
   assert '1572388562752770230' in ' '.join(args);checkpoints.append(args)
  else:raise AssertionError('unexpected subprocess')
 save(case)
 with patch.object(u,'datetime',SimDateTime),patch.object(u,'load_common',lambda:c),patch.object(u,'preflight',lambda *a:None),patch.object(u,'get',fakeget),patch.object(u,'AccountWriterLeaseStore',Lease),patch.object(m.fcntl,'flock',lambda *a:None),patch.object(Path,'open',fakeopen),patch.object(x.subprocess,'run',run),patch.object(x.w,'notify',notice):
  x.main('activate',fixture,now=at)
 result=json.loads(fixture.read_text());assert set(posts)==set(case['campaign_ids'].values()) and len(posts)==len(case['campaign_ids'])
 assert set(batches[-1])==set(case['requested_campaign_ids'].values()) and len(batches[-1])==29
 assert len(notices)==1 and len(checkpoints)==1 and result['full_cohort_verified']
 if blocked_case:
  n=next(iter(case['activation_blocked']));assert allrows[n]['status']=='PAUSED' and result['full_cohort_readback'][n]['status']=='PAUSED'
 ok('public_full_activation_'+('blocked_exception' if blocked_case else 'all_ready'))
fixture.unlink(missing_ok=True)
# Clock restored before durable test receipt.
u.save(r/'safety-tests.json',{'tests_passed':len(checks),'checks':checks,'meta_calls':0,'meta_writes':0,'simulated_target':at.isoformat(),'real_receipt_time':datetime.now().astimezone().isoformat()})
print(json.dumps({'tests_passed':len(checks),'meta_calls':0,'meta_writes':0,'coverage':len(s['requested_campaign_ids'])}))
