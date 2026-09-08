"""Read-only Google Ads MCC inventory; credentials stay on Zeus, only IDs in the app."""
import sys,json,re,urllib.request,urllib.error,pathlib,datetime
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env,service_account_access_token,load_service_account
from zoneinfo import ZoneInfo
MCC='8137016595';VERSION='v25'
def customer_id(value):
 if not isinstance(value,str) or not re.fullmatch(r'\d{10}|\d{3}-\d{3}-\d{4}',value):raise ValueError('Google customer ID format invalid')
 return value.replace('-','')
def inventory():
 load_env();sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent/'deploy'));from runcloud_ops import op
 item=op(['item','get','Google Ads API - MGS','--vault','MGS Conteúdo','--format','json']);fields={f.get('label',f.get('id')):f.get('value') for f in item.get('fields',[])}
 if customer_id(fields.get('login_customer_id'))!=MCC or not fields.get('developer_token'):raise RuntimeError('Google Ads MCC/item configuration mismatch')
 sa=load_service_account()
 if sa.get('project_id')!='mgs-core-prod' or sa.get('client_email')!='mgsagent@mgs-core-prod.iam.gserviceaccount.com':raise RuntimeError('Noncanonical Google identity')
 token=service_account_access_token('https://www.googleapis.com/auth/adwords');headers={'Authorization':'Bearer '+token,'developer-token':fields['developer_token'],'login-customer-id':MCC,'Content-Type':'application/json'}
 query='SELECT customer_client.id, customer_client.descriptive_name, customer_client.currency_code, customer_client.time_zone, customer_client.manager, customer_client.level, customer_client.status FROM customer_client'
 params={'query':query};accounts={};seen=set();pages=0;root_verified=False
 while True:
  req=urllib.request.Request('https://googleads.googleapis.com/'+VERSION+'/customers/'+MCC+'/googleAds:search',data=json.dumps(params).encode(),headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=45) as response:data=json.load(response)
  except urllib.error.HTTPError as e:
   err=json.load(e).get('error',{});codes=[str(x.get('errorCode')) for dt in err.get('details',[]) for x in dt.get('errors',[])];reasons=[dt.get('reason') for dt in err.get('details',[]) if dt.get('reason')]
   raise RuntimeError('Google Ads HTTP '+str(e.code)+' '+str(reasons+codes)) from None
  pages+=1
  for row in data.get('results',[]):
   c=row['customerClient'];cid=customer_id(c['id'])
   if cid==MCC:
    if not c.get('manager') or c.get('descriptiveName')!='MARKETING DIGITAL ADS LTDA':raise RuntimeError('MCC identity mismatch')
    root_verified=True
   if c.get('manager'):continue
   timezone=c.get('timeZone');ZoneInfo(timezone)
   a={'account_id':cid,'display_id':cid[:3]+'-'+cid[3:6]+'-'+cid[6:],'name':c.get('descriptiveName',''),'currency':c['currencyCode'],'timezone':timezone,'business_id':MCC,'platform':'google','status':c.get('status','UNKNOWN'),'level':int(c.get('level',0))}
   if cid in accounts and accounts[cid]!=a:raise RuntimeError('Conflicting Google account metadata')
   accounts[cid]=a
  next_page=data.get('nextPageToken')
  if not next_page:break
  if next_page in seen or pages>=100:raise RuntimeError('Incomplete Google pagination')
  seen.add(next_page);params['pageToken']=next_page
 if not root_verified:raise RuntimeError('MCC root not returned; inventory incomplete')
 return accounts,pages
if __name__=='__main__':
 rows,pages=inventory();out={'pass':True,'mcc':MCC,'pages':pages,'count':len(rows),'accounts':list(rows.values()),'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'google_mutations':0};target=pathlib.Path(__file__).resolve().parent/'private/google-square-1546702931384991834/google-inventory.json';target.write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='accounts'}))
