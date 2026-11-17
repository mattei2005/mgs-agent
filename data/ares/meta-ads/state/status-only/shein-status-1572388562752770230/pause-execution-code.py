import sys,os,json,re,importlib.util,fcntl,time,subprocess
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3 import shein_channel_authority as auth
from ares_campaign_v3.coordination import AccountWriterLeaseStore
B=Path('/root/mgs-agent');R=B/'data/ares/meta-ads/state/status-only/shein-status-1572388562752770230';P=R/'activation.json'
spec=importlib.util.spec_from_file_location('u','/root/.hermes/profiles/ares/scripts/shein-status-once.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
A='937846586033361';T='1558134703565967394';M='1572388562752770230';WHO='1055570806945620030'
N=['201','175','204','221','212','189','202','196','194','197','184','207','216','195','214','191','177','200','209','211','182','210','213','172','181','198','208','217','219']
assert len(N)==len(set(N))
assert re.findall(r'^\s*(\d+)\s*\|','00:00 18/11/2026\n001 | CP22 v3 | -3,22%\n201 | X | +1,2%',re.M)==['001','201']
cfg=json.loads((B/'data/ares/meta-ads/engine-v3/config.json').read_text());profile=cfg['accounts'][A]['shein_profile']
os.environ['ARES_META_GRAPH_VERSION']=cfg['graph_version'];c=u.load_common()
msg=auth._get('/channels/'+T+'/messages/'+M)
assert msg['author']['id']==WHO and msg['channel_id']==T
assert re.findall(r'^\s*(\d+)\s*\|',msg['content'],re.M)==N
s=json.loads(P.read_text()) if P.exists() else {'request_id':'shein-status-'+M,'authorized_by':WHO,'source_channel_id':'1548150155184701440','source_thread_id':T,'source_message_id':M,'original_message':msg['content'],'message_timestamp':msg['timestamp'],'edited_timestamp':msg.get('edited_timestamp'),'account_id':A,'profile':profile,'requested_numbers':N,'initial':{},'pause':{}}
assert s['original_message']==msg['content']
s['authority_proof']=auth.verify(s,profile,force=True)
subprocess.run(['python3',str(B/'scripts/mgs-ares-asset-scope.py'),'check-account',A,'--json'],capture_output=True,check=True)
token,_=c.get_token_from_1password(cfg['accounts'][A]['token_item'])
account=u.get(c,token,'act_'+A,'id,account_id,name,currency,timezone_name,account_status,user_tasks')
assert account['id'] in {A,'act_'+A} and account['account_id']==A and account['account_status']==1 and 'ADVERTISE' in account['user_tasks']
assert account['name']==cfg['accounts'][A]['alias']
s['account_readback']=account
z=ZoneInfo(account['timezone_name']);d=datetime.fromisoformat(msg['timestamp']).astimezone(z);at=d.replace(hour=0,minute=0,second=0,microsecond=0)
if at<=d:at+=timedelta(days=1)
s.setdefault('activate_at',at.isoformat())
if not s.get('campaign_ids'):
 rows=[];params={'fields':u.CF,'limit':100}
 for page in range(30):
  h,p,_=c.graph_get('act_'+A+'/campaigns',token,params)
  assert h==200 and 'error' not in p
  rows.extend(p['data']);paging=p.get('paging',{})
  if not paging.get('next'):break
  params['after']=paging['cursors']['after']
 else:raise RuntimeError('pagination_bound')
 chosen={}
 for n in N:
  matches=[r for r in rows if re.match(r'^\s*'+re.escape(n)+r'\s*[-|]',r['name']) and u.configured(r) not in {'DELETED','ARCHIVED'}]
  assert len(matches)==1,(n,'nonterminal_match_count',len(matches))
  chosen[n]=matches[0]['id']
 assert len(set(chosen.values()))==len(N)
 s.update(campaign_ids=chosen,requested_campaign_ids=chosen.copy(),pause_campaign_ids=chosen.copy(),status='PAUSE_PENDING')
 u.save(P,s)
 subprocess.run(['python3',str(B/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','SHEIN-STATUS-'+M,'--agent','ares','--thread-id',T,'--objective','Mavroa06: pausa nominal e reativacao unica 00h no fuso da conta','--state','PAUSE_PENDING','--next-step','Confirmar pausa e preparar ativacao dos mesmos IDs','--source',str(P)],capture_output=True,check=True)
lockpath=B/'data/ares/meta-ads/state/shein-campaigns/single-clone'/('account-'+A+'.lock');lockpath.parent.mkdir(parents=True,exist_ok=True)
with lockpath.open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);lease=AccountWriterLeaseStore(cfg['state_root']);lease.claim(A,s['request_id'])
 s['authority_proof']=auth.verify(s,profile,force=True)
 for n,cid in s['campaign_ids'].items():
  row=u.get(c,token,cid,u.CF);assert row['account_id']==A and row['id']==cid
  s['initial'].setdefault(n,row);attempt=s['pause'].get(n)
  if u.configured(row)!='PAUSED':
   assert u.configured(row)=='ACTIVE'
   if attempt and attempt.get('stage')!='post_rejected':raise RuntimeError('reconcile_prior_attempt_'+n)
   s['pause'][n]={'stage':'IN_FLIGHT','before':row,'payload':{'status':'PAUSED'}};u.save(P,s)
   h,p,_=c.graph_post_once(cid,token,{'status':'PAUSED'})
   s['pause'][n].update(post_http=h,post_success=bool(isinstance(p,dict) and p.get('success')));u.save(P,s)
   for delay in [0,1,2,4,8]:
    if delay:time.sleep(delay)
    row=u.get(c,token,cid,u.CF)
    if all(row.get(k)=='PAUSED' for k in ['status','configured_status','effective_status']):break
   assert all(row.get(k)=='PAUSED' for k in ['status','configured_status','effective_status']),n
  else:s['pause'].setdefault(n,{'no_op':True})
  for k in ['id','account_id','name','daily_budget','lifetime_budget','bid_strategy','objective','start_time','stop_time']:assert row.get(k)==s['initial'][n].get(k),(n,k)
  s['pause'][n].update(stage='confirmed',after=row);u.save(P,s)
 h,rows,_=c.graph_batch_get(token,[{'name':n,'path':cid,'params':{'fields':u.CF}} for n,cid in s['campaign_ids'].items()]);assert h==200 and len(rows)==len(N)
 out={r['name']:r['body'] for r in rows if r['code']==200};assert set(out)==set(N)
 for n,row in out.items():
  assert row['id']==s['campaign_ids'][n] and all(row.get(k)=='PAUSED' for k in ['status','configured_status','effective_status'])
  for k in ['id','account_id','name','daily_budget','lifetime_budget','bid_strategy','objective','start_time','stop_time']:assert row.get(k)==s['initial'][n].get(k),(n,k)
 s.update(status='PAUSED_CONFIRMED',pause_readback=out,pause_confirmed_count=len(out),pause_write_count=sum(not v.get('no_op',False) for v in s['pause'].values()),pause_confirmed_at=datetime.now().astimezone().isoformat());u.save(P,s);lease.release(A,s['request_id'])
print(json.dumps({'status':s['status'],'count':len(out),'writes':s['pause_write_count'],'activate_at':s['activate_at'],'account':account['name'],'timezone':account['timezone_name']}))
