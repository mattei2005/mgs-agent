import importlib.util,json,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
P=Path('/root/.hermes/profiles/ares/scripts/shein-g004-cpr-updates-20261105.py')
spec=importlib.util.spec_from_file_location('test_target',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
A=m.AID;D=m.DAY;NY=m.NY
at=datetime.fromisoformat('2026-11-05T10:43:28.592-05:00')
checks=[]
def check(label,predicate):
 assert predicate,label;checks.append(label)
def c(cid='1',created='2026-11-05T10:00:00-05:00',account=A):
 return {'id':cid,'account_id':account,'name':cid.zfill(3)+' - 05/11 - X','created_time':created,'status':'ACTIVE'}
check('created today',set(m.candidates([c()],at))=={'1'})
check('future today admitted later',set(m.candidates([c(created='2026-11-05T11:00:00-05:00')],at))==set())
check('future after time advances',set(m.candidates([c(created='2026-11-05T11:00:00-05:00')],at.replace(hour=12)))=={'1'})
check('old day excluded',not m.candidates([c(created='2026-11-04T23:59:59-05:00')],at))
check('next day excluded',not m.candidates([c(created='2026-11-06T00:00:00-05:00')],at))
check('civil timezone conversion',bool(m.candidates([c(created='2026-11-06T04:59:59+00:00')],at.replace(hour=23,minute=59,second=59,microsecond=999999))))
try:m.candidates([c(account='999')],at)
except AssertionError:check('other account rejected',True)
else:raise AssertionError('account leak')
act=m.w.ACTION
metric=lambda amount,qty:m.metric({'spend':amount,'actions':[{'action_type':act,'value':qty}]})
check('low CPR retained',metric('0.10','2')['cpr']=='0.05')
check('zero results undefined',metric('5','0')['cpr'] is None)
check('missing action undefined',m.metric({'spend':'5'})['cpr'] is None)
check('wrong alias excluded',m.metric({'spend':'5','actions':[{'action_type':'omni_add_to_wishlist','value':'20'}]})['cpr'] is None)
snap={'observed_at':at.isoformat(),'rows':{'1':{'number':'001','status':'ACTIVE','pending':None,**metric('0.10','2')}}}
render='\n'.join(m.text(snap));check('low CPR visible','US$ 0,05/resultado' in render)
check('target labels','Yolokfx Conta 04' in render and '05/11' in render and 'Mavroa' not in render)
check('large report splits',len(m.text({'observed_at':at.isoformat(),'rows':{str(i):dict(snap['rows']['1'],number=str(i)) for i in range(100)}}))>1)
d,delivery=m.helpers();check('actual imported transport target',delivery.TID==m.TID and delivery.USER==m.USER)
# Persisted source fake: no live API or credentials in offline collect tests.
class Runner:
 cs=[];ss=[];ins=[];paths=[]
 def __init__(self,*args):self.meta=None
 def source(self,run,name,fn):
  out=fn();m.save(run/(name+'-observed-at.json'),{'observed_at':at.isoformat()});return out
 def graph(self,path,params):
  return {'id':A,'name':'Yolokfx-US-SHEIN-EN-04-G004','currency':'USD','timezone_name':'America/New_York'}
 def paged(self,path,params):
  self.paths.append((path,params))
  if path.endswith('/campaigns'):return self.cs
  ids=json.loads(params['filtering'])[0]['value'];assert ids,'empty filter leaked'
  if path.endswith('/adsets'):return self.ss
  return self.ins
fake=SimpleNamespace(Runner=Runner)
ss=lambda cid:{'id':'s'+cid,'account_id':A,'campaign_id':cid,'optimization_goal':'OFFSITE_CONVERSIONS','promoted_object':{'custom_event_type':'ADD_TO_WISHLIST'}}
with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
 root=Path(tmp);manifest={'date':D,'expires_at':'2026-11-06T00:00:00-05:00','account_name':'Yolokfx-US-SHEIN-EN-04-G004','campaigns':[],'slots':['2026-11-05T11:13:00-05:00']}
 for label,cs,sets in [('empty',[],[]),('pending',[c()],[]),('recovered',[c()],[ss('1')]),('isolated',[c('1'),c('2')],[ss('2')])]:
  Runner.cs=cs;Runner.ss=sets;Runner.paths=[];run=root/label;run.mkdir();result=m.collect(fake,manifest,run,{})
  if label=='empty':check('empty no financial global query',not result['rows'] and len(Runner.paths)==1)
  if label=='pending':check('pending ID preserved',result['campaigns'][0]['id']=='1' and result['rows']['1']['pending'] is not None)
  if label=='recovered':check('pending recovers',result['rows']['1']['pending'] is None)
  if label=='isolated':check('pending does not block valid',result['rows']['1']['pending'] is not None and result['rows']['2']['pending'] is None)
 # Full executor guards before scope/API, and replay.
 orig_root,orig_scope=m.ROOT,m.scope;m.ROOT=root;m.save(root/'manifest.json',manifest)
 def forbidden(*a,**k):raise AssertionError('scope/API invoked')
 m.scope=forbidden;args=SimpleNamespace(initial=False,dry_run=False)
 check('expiry before API',m.execute(args,datetime.fromisoformat(manifest['expires_at']))['status']=='EXPIRED')
 check('outside slot before API',m.execute(args,at)['status']=='NOT_DUE')
 run=root/'runs'/'1113';run.mkdir(parents=True);m.save(run/'complete.json',{'status':'persisted'})
 check('full executor replay before API',m.execute(args,at.replace(hour=11,minute=13))['status']=='persisted')
 # Live transport semantics exercised via fake Discord, GET exact and no replay POST.
 posts=[];messages={}
 class DC:
  def verify(self,bindings):assert bindings==[{'thread_id':m.TID,'channel_id':'1558147066826334309'}]
  def call(self,method,path,payload=None):
   if method=='POST':
    assert path=='/channels/'+m.TID+'/messages';posts.append(payload);messages['123']={'id':'123','content':payload['content'],'channel_id':m.TID,'author':{'id':'BOT'}};return messages['123']
   assert path.endswith('/123');return messages['123']
 fd=SimpleNamespace(Discord=DC,BOT_ID='BOT');run=root/'delivery';run.mkdir()
 for _ in range(2):delivery.deliver(fd,{'request_id':m.REQUEST,'parent_id':'1558147066826334309'},run,['test'])
 check('nonce GET replay no duplicate POST',len(posts)==1 and posts[0]['enforce_nonce'] is True)
 m.ROOT,m.scope=orig_root,orig_scope
print(json.dumps({'status':'PASS','tests':len(checks),'checks':checks,'external_calls':0},ensure_ascii=False))
