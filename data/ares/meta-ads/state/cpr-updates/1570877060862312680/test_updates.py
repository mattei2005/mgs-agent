import importlib.util,json,tempfile
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timedelta
P=Path('/root/.hermes/profiles/ares/scripts/shein-g004-mavroa-cpr-updates-20261113.py')
spec=importlib.util.spec_from_file_location('test09',P);assert spec and spec.loader;n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n);m=n
checks=[]
def check(label,value):
 assert value,label;checks.append(label)
def c(cid='1',created=None,account=None):
 return {'id':cid,'account_id':account or m.AID,'name':cid.zfill(3)+' - 13/11 - X','created_time':created or m.CUTOFF.isoformat(),'status':'ACTIVE'}
at=m.CUTOFF+timedelta(hours=1)
check('exact cutoff admitted',set(m.candidates([c()],at))=={'1'})
check('after cutoff excluded',not m.candidates([c(created=(m.CUTOFF+timedelta(microseconds=1)).isoformat())],at))
check('old day excluded',not m.candidates([c(created='2026-11-12T23:59:59-05:00')],at))
check('next day excluded',not m.candidates([c(created='2026-11-14T00:00:00-05:00')],at))
try:m.candidates([c(account='999')],at)
except AssertionError:check('other account blocked',True)
else:raise AssertionError('account leak')
metric=lambda spend,qty:m.metric({'spend':spend,'actions':[{'action_type':m.w.ACTION,'value':qty}]})
check('low CPR retained',metric('0.10','2')['cpr']=='0.05')
check('zero results undefined',metric('5','0')['cpr'] is None)
check('missing action undefined',m.metric({'spend':'5'})['cpr'] is None)
check('wrong alias excluded',m.metric({'spend':'5','actions':[{'action_type':'omni_add_to_wishlist','value':'20'}]})['cpr'] is None)
snap={'observed_at':at.isoformat(),'rows':{'1':{'number':'001','status':'ACTIVE','pending':None,**metric('0.10','2')}}}
render='\n'.join(m.text(snap));check('low CPR visible','US$ 0,05/resultado' in render)
check('request labels and no future promise','13/11' in render and 'Mavroa' in render and '14:04 EST' in render and 'Novas campanhas' not in render)
check('large report splits',len(m.text(dict(snap,rows={str(i):dict(snap['rows']['1'],number=str(i)) for i in range(100)})))>1)
d,delivery=m.helpers();check('effective transport target',delivery.TID==m.TID and delivery.USER==m.USER)
class Runner:
 cs=[];ss=[];ins=[];calls=[]
 def __init__(self,*args):self.meta=self;self.token='TEST'
 def graph_batch_get(self,token,requests):
  assert token=='TEST';self.calls.append(('batch',requests));ids=[x['path'] for x in requests];assert ids
  return 200,[{'code':200,'body':next(x for x in self.cs if x['id']==cid)} for cid in ids],{}
 def source(self,run,name,fn):
  result=fn();m.save(run/(name+'-observed-at.json'),{'observed_at':at.isoformat()});return result
 def graph(self,path,params):return {'id':m.AID,'name':'Mavroa-US-SHEIN-ES-04-G004','currency':'USD','timezone_name':'America/New_York'}
 def paged(self,path,params):
  self.calls.append((path,params));ids=json.loads(params['filtering'])[0]['value'];assert ids
  if path.endswith('/campaigns'):
   return [x for x in self.cs if x['id'] in ids]
  if path.endswith('/adsets'):return self.ss
  return self.ins
ss=lambda cid:{'id':'s'+cid,'account_id':m.AID,'campaign_id':cid,'optimization_goal':'OFFSITE_CONVERSIONS','promoted_object':{'custom_event_type':'ADD_TO_WISHLIST'}}
with tempfile.TemporaryDirectory(dir=str(m.HOME/'cache/scratch')) as tmp:
 root=Path(tmp);manifest=m.load(m.ROOT/'manifest.json');manifest.update(cohort_frozen=True,campaigns=list(m.candidates([c()],at).values()))
 def collect(label):
  run=root/label;run.mkdir();Runner.calls=[];return m.collect(SimpleNamespace(Runner=Runner),manifest,run,{})
 Runner.cs=[c(),c('2')];Runner.ss=[ss('1')];Runner.ins=[]
 result=collect('frozen');check('frozen cohort excludes second eligible',set(result['rows'])=={'1'})
 check('query frozen IDs only',Runner.calls[0][0]=='batch' and [x['path'] for x in Runner.calls[0][1]]==['1'])
 manifest['campaigns']=[];result=collect('empty');check('frozen empty no campaigns adsets insights',not result['rows'] and not Runner.calls)
 manifest['campaigns']=list(m.candidates([c(),c('2')],at).values());Runner.cs=[c(),c('2')];Runner.ss=[ss('2')]
 result=collect('pending');check('pending isolated',result['rows']['1']['pending'] and not result['rows']['2']['pending'])
 Runner.ss=[ss('1'),ss('2')];result=collect('recovery');check('pending recovers',not result['pending'])
 Runner.ss[0]['promoted_object']={};result=collect('event-lost');check('lost event isolated',result['rows']['1']['pending'] and not result['rows']['2']['pending'])
 Runner.ss=[ss('1'),ss('2')];Runner.ins=[{'campaign_id':'1','date_start':m.DAY,'date_stop':m.DAY,'spend':'5','actions':[{'action_type':m.w.ACTION,'value':'2'}],'cost_per_action_type':[{'action_type':m.w.ACTION,'value':'9'}]}]
 result=collect('badmetric');check('inconsistent metric isolated',result['rows']['1']['pending'] and not result['rows']['2']['pending'])
 # Live timezone wins over stale catalog in manifest preparation.
 check('manifest timezone derives live',manifest['timezone_name']==n._account['timezone_name'] and m.DAY==m.CUTOFF.date().isoformat())
 orig_root,orig_scope=m.ROOT,m.scope;m.ROOT=root;m.save(root/'manifest.json',manifest)
 def forbidden(*args,**kwargs):raise AssertionError('scope API unexpectedly called')
 m.scope=forbidden;args=SimpleNamespace(initial=False,dry_run=False)
 check('expiry before API',m.execute(args,datetime.fromisoformat(manifest['expires_at']))['status']=='EXPIRED')
 manifest['slots']=[m.CUTOFF.replace(hour=15,minute=13,second=0,microsecond=0).isoformat()];m.save(root/'manifest.json',manifest)
 check('outside slot no API',m.execute(args,m.CUTOFF)['status']=='NOT_DUE')
 run=root/'runs/1513';run.mkdir(parents=True);m.save(run/'complete.json',{'status':'PERSISTED'})
 check('full executor replay no API',m.execute(args,datetime.fromisoformat(manifest['slots'][0]))['status']=='PERSISTED')
 posts=[];messages={}
 class DC:
  def verify(self,bindings):assert bindings==[{'thread_id':m.TID,'channel_id':manifest['parent_id']}]
  def call(self,method,path,payload=None):
   if method=='POST':
    assert payload is not None
    assert path=='/channels/'+m.TID+'/messages';posts.append(payload);messages['123']={'id':'123','content':payload['content'],'channel_id':m.TID,'author':{'id':'BOT'}};return messages['123']
   assert path.endswith('/123');return messages['123']
 run=root/'delivery';run.mkdir()
 for _ in range(2):delivery.deliver(SimpleNamespace(Discord=DC,BOT_ID='BOT'),manifest,run,['test'])
 check('nonce readback replay one POST',len(posts)==1 and posts[0]['enforce_nonce'])
 # Decimal/type failures remain isolated to the inconsistent campaign.
 Runner.ins=[{'campaign_id':'1','date_start':m.DAY,'date_stop':m.DAY,'spend':'invalid'}]
 result=collect('invalid-decimal');check('invalid decimal isolated',result['rows']['1']['pending'] and not result['rows']['2']['pending'])
 Runner.ins=[{'campaign_id':'1','date_start':m.DAY,'date_stop':m.DAY,'spend':'5','actions':[{'action_type':m.w.ACTION,'value':None}]}]
 result=collect('invalid-type');check('invalid action isolated',result['rows']['1']['pending'] and not result['rows']['2']['pending'])
 # Empty OS run-parts is a verified no-op, never an assumed exemption.
 import subprocess
 rp=root/'hourly';rp.mkdir()
 check('empty run-parts verified',not subprocess.check_output(['run-parts','--test',str(rp)],text=True).strip())
 task=rp/'workload';task.write_text('#!/bin/sh\nexit 0\n');task.chmod(0o700)
 check('nonempty run-parts detected',str(task) in subprocess.check_output(['run-parts','--test',str(rp)],text=True))
 m.ROOT,m.scope=orig_root,orig_scope
import re
sample=subprocess.check_output(['systemd-analyze','calendar','--iterations=3','--base-time=2026-11-13T00:00:00-05:00','*-*-* *:00/10:00'],text=True)
regex=r'(?:Next elapse|Iteration #\d+|Iter\. #\d+):[^\n]*?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
check('systemd all iterations parsed',len(re.findall(regex,sample))==3)
check('systemd times ordered',re.findall(regex,sample)==['2026-11-13 00:10:00','2026-11-13 00:20:00','2026-11-13 00:30:00'])
result={'status':'PASS','tests':len(checks),'checks':checks,'external_calls':0};m.save(m.ROOT/'tests.json',result);print(json.dumps(result,ensure_ascii=False))
