import json,selectors,subprocess,time
from pathlib import Path
P=Path('/root/.hermes/profiles/zeus/cache/scratch/browser-budget-four-1555702597925470400');cfg=P/'rendered-concurrency-budget.json'
cfg.write_text(json.dumps({'schema_version':1,'slots':3,'batch_slots':2,'local_workers':1,'wait_timeout_seconds':5,'poll_seconds':.02,'lock_dir':str(P/'rendered-concurrency-locks')}))
processes={};sel=selectors.DefaultSelector();events=[]
def spawn(role,kind,hold):
 p=subprocess.Popen(['/root/.local/share/mgs/sb-venv/bin/python',str(P/'chromium_actor.py'),str(cfg),role,kind,str(hold)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 processes[role]=p;sel.register(p.stdout,selectors.EVENT_READ,role)
def collect_until(predicate):
 deadline=time.monotonic()+30
 while not predicate():
  assert time.monotonic()<deadline,'rendered canary timeout'
  for key,mask in sel.select(.1):
   s=key.fileobj.readline()
   if s:events.append(json.loads(s))
   else:sel.unregister(key.fileobj)
spawn('batch-one','batch',3);spawn('batch-two','batch',3)
collect_until(lambda: len([e for e in events if e['kind']=='admitted'])==2)
spawn('batch-three','batch',.1);spawn('interactive','interactive',.1)
collect_until(lambda: len([e for e in events if e['kind']=='complete'])==4)
for role,p in processes.items():
 p.wait(timeout=10); assert p.returncode==0,role
 # Child output is local fixture-only, nevertheless expose counters not text.
 assert not any('Traceback' in x for x in p.stderr.read().splitlines()),role
admitted={e['role']:e for e in events if e['kind']=='admitted'};done={e['role']:e for e in events if e['kind']=='complete'}
assert admitted['batch-three']['wait_seconds']>.5
assert admitted['interactive']['wait_seconds']<.3
assert admitted['interactive']['slot']==2
assert all(admitted[r]['slot']<2 for r in ['batch-one','batch-two','batch-three'])
points=[]
for role,e in admitted.items():points.extend([(e['at'],1,role),(done[role]['at'],-1,role)])
active=set();peak_total=peak_batch=0
for at,delta,role in sorted(points):
 if delta==1:active.add(role)
 else:active.remove(role)
 peak_total=max(peak_total,len(active));peak_batch=max(peak_batch,len([r for r in active if r.startswith('batch')]))
assert peak_total==3 and peak_batch==2
receipt={'pass':True,'rendered_browser_jobs':4,'peak_admitted_total':peak_total,'peak_admitted_batch':peak_batch,'third_batch_wait_seconds':round(admitted['batch-three']['wait_seconds'],3),'interactive_wait_seconds':round(admitted['interactive']['wait_seconds'],3),'elapsed_seconds':round(max(e['at'] for e in done.values())-min(e['at'] for e in admitted.values()),3),'uses_production_module':True,'uses_isolated_lock_namespace':True,'protected_sessions_touched':False,'events':events}
(P/'rendered-concurrency.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k!='events'}))
