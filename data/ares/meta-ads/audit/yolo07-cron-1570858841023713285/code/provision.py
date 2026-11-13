"""Provisioning-only: one approved account, one existing System User, ANALYZE."""
import pathlib,json,subprocess,urllib.request,urllib.error,os,datetime,time,sys,importlib.util,hashlib
ROOT=pathlib.Path('/root/mgs-agent/data/ares/meta-ads/audit/yolo07-cron-1570858841023713285')
ACCOUNT='1492168699397108';BUSINESS='155263197283282';SYSTEM_USER='122095869861482193';ADMIN='10233237854144701';ITEM='4c2p3bon37smfbklfhuej5ywkm'
MODE=sys.argv[1];assert MODE in ('preflight','apply')
def save(name,obj):
 p=ROOT/name;p.write_text(json.dumps(obj,ensure_ascii=False,indent=2));p.chmod(0o600)
s=importlib.util.spec_from_file_location('approval_daily','/root/.hermes/profiles/ares/scripts/shein-daily-report.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
dc=d.Discord();approval=dc.call('GET','/channels/1570801075621986305/messages/1570860329947103396');proof=json.loads((ROOT/'critical-approval-readback.json').read_text());prompt=dc.call('GET','/channels/1570801075621986305/messages/'+proof['prompt']['id'])
assert approval['author']['id']=='344196393512075265' and approval['content'].strip().casefold()=='sim' and prompt['content']==proof['prompt']['content']
assert proof['authorized_delta']=={'account_id':ACCOUNT,'system_user_id':SYSTEM_USER,'business_id':BUSINESS,'tasks_to_add':['ANALYZE'],'preserve_existing_tasks':True,'credential_changes':False}
# This existing administrative User credential is used only for assignment.
# Never expose/cache it or substitute it into the Campaign Ops transport.
r=subprocess.run(['bash','-lc',"set -a; . /root/mgs-agent/.env; set +a; op item get "+ITEM+" --vault 'MGS Conteúdo' --format json --reveal"],capture_output=True,text=True,timeout=45);assert r.returncode==0;item=json.loads(r.stdout);token=next(f['value'] for f in item['fields'] if f['id']=='credential');del item,r
from urllib.parse import urlencode,urlsplit,parse_qs
allowed={'me','me/permissions', 'act_'+ACCOUNT, 'act_'+ACCOUNT+'/assigned_users'}
def api(method,path,params):
 assert path in allowed and method in ('GET','POST')
 if method=='POST':assert path=='act_'+ACCOUNT+'/assigned_users' and params['user']==SYSTEM_USER and params['business']==BUSINESS and isinstance(params['tasks'],str)
 url='https://graph.facebook.com/v26.0/'+path;data=None
 if method=='GET':url+='?'+urlencode(params)
 else:data=urlencode(params).encode()
 req=urllib.request.Request(url,data=data,method=method,headers={'Authorization':'Bearer '+token,'User-Agent':'MGS-Ares-Provisioning-Only/1.0'})
 try:
  with urllib.request.urlopen(req,timeout=60) as res:return res.status,json.load(res)
 except urllib.error.HTTPError as exc:
  b=json.loads(exc.read());return exc.code,{'error':{k:b.get('error',{}).get(k) for k in ['code','error_subcode','type','message']}}
def assignments():
 rows=[];after=None;seen=set()
 for _ in range(30):
  params={'business':BUSINESS,'fields':'id,tasks','limit':100}
  if after:params['after']=after
  st,b=api('GET','act_'+ACCOUNT+'/assigned_users',params)
  if st!=200:return st,b,None
  rows.extend(b.get('data',[]))
  if not b.get('paging',{}).get('next'):return 200,rows,True
  after=b.get('paging',{}).get('cursors',{}).get('after');assert after and after not in seen;seen.add(after)
 raise RuntimeError('assignment pagination incomplete')
st,admin=api('GET','me',{'fields':'id,name'});save('admin-identity-readback.json',{'http':st,'identity':admin,'credential_item_id':ITEM,'purpose':'provisioning only'})
assert st==200 and admin['id']==ADMIN,'Approved administrative identity not available'
st,permissions=api('GET','me/permissions',{'fields':'permission,status'});granted={x['permission'] for x in permissions.get('data',[]) if x.get('status')=='granted'};save('admin-permissions-readback.json',{'http':st,'business_management_granted':'business_management' in granted});assert st==200 and 'business_management' in granted,'Provisioning scope not granted'
st,account=api('GET','act_'+ACCOUNT,{'fields':'id,name,business,currency,timezone_name,account_status'});save('admin-account-readback.json',{'http':st,'account':account})
assert st==200 and account['id'].removeprefix('act_')==ACCOUNT and account.get('business',{}).get('id')==BUSINESS,'Target ownership not proven'
st,rows,complete=assignments()
if st!=200:
 save('assignment-preflight.json',{'http':st,'error':rows,'complete':False});print(json.dumps({'status':'ADMIN_ASSIGNMENT_READ_BLOCKED','http':st,'error':rows},ensure_ascii=False));sys.exit(2)
target=[x for x in rows if x['id']==SYSTEM_USER];assert len(target)<=1;existing=set(target[0].get('tasks',[]) if target else []);desired=sorted(existing|{'ANALYZE'});other={x['id']:sorted(x.get('tasks',[])) for x in rows if x['id']!=SYSTEM_USER}
before={'status':'PREFLIGHT_VERIFIED','authority_message_id':'1570860329947103396','account_id':ACCOUNT,'business_id':BUSINESS,'system_user_id':SYSTEM_USER,'existing_tasks':sorted(existing),'desired_tasks':desired,'pagination_complete':complete,'other_assignments_digest':hashlib.sha256(json.dumps(other,sort_keys=True).encode()).hexdigest(),'account':{k:account[k] for k in ['id','name','currency','timezone_name']},'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
save('assignment-preflight.json',before)
if MODE=='preflight':print(json.dumps(before,ensure_ascii=False));sys.exit()
journal=ROOT/'permission-journal.json'
if journal.exists():
 old=json.loads(journal.read_text());assert old['account_id']==ACCOUNT and old['system_user_id']==SYSTEM_USER
 if old.get('status') in ('IN_FLIGHT','POST_RETURNED','VERIFIED') and 'ANALYZE' not in existing:raise RuntimeError('Prior assignment uncertain; manual reconciliation required, no blind POST')
else:old={**before,'permission_writes':0,'credential_changes':False,'campaign_writes':0}
if 'ANALYZE' not in existing:
 old.update(status='IN_FLIGHT');save('permission-journal.json',old)
 st,result=api('POST','act_'+ACCOUNT+'/assigned_users',{'user':SYSTEM_USER,'business':BUSINESS,'tasks':json.dumps(desired)})
 old.update(status='POST_RETURNED',post_http=st,post_result=result,permission_writes=1);save('permission-journal.json',old)
# Read back regardless of successful/ambiguous POST; never retry the write.
for attempt in range(4):
 st,afterrows,complete=assignments()
 if st==200:
  final=[x for x in afterrows if x['id']==SYSTEM_USER]
  if len(final)==1 and set(final[0]['tasks'])>=set(desired):break
 time.sleep(2**attempt)
else:raise RuntimeError('Assignment write not verified')
afterother={x['id']:sorted(x.get('tasks',[])) for x in afterrows if x['id']!=SYSTEM_USER};assert other==afterother
old.update(status='VERIFIED',final_tasks=sorted(final[0]['tasks']),assignment_get_verified=True,other_assignments_preserved=True,ownership_preserved=True,verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat());save('permission-journal.json',old)
print(json.dumps({k:old[k] for k in ['status','account_id','system_user_id','existing_tasks','desired_tasks','final_tasks','permission_writes','assignment_get_verified','other_assignments_preserved']},ensure_ascii=False))
