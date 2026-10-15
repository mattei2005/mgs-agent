"""Read-only ad account discovery and exact account/day spend; no ad or Sheet writes."""
import pathlib,sys,json,importlib.util,datetime,re,urllib.request,urllib.error,time
from decimal import Decimal
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'deploy'));sys.path.insert(0,'/root/mgs-agent/scripts')
from runcloud_ops import op
from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token
class SourceError(Exception):pass
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def google_headers():
 item=op(['item','get','Google Ads API - MGS','--vault','MGS Conteúdo','--format','json']);f={x.get('label',x.get('id')):x.get('value') for x in item['fields']};assert f['login_customer_id'].replace('-','')=='8137016595';sa=load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['project_id']=='mgs-core-prod'
 return {'Authorization':'Bearer '+service_account_access_token('https://www.googleapis.com/auth/adwords'),'developer-token':f['developer_token'],'login-customer-id':'8137016595','Content-Type':'application/json'}
def google_search(cid,query,headers):
 rows=[];params={'query':query};seen=set()
 while True:
  req=urllib.request.Request('https://googleads.googleapis.com/v25/customers/'+cid+'/googleAds:search',data=json.dumps(params).encode(),headers=headers,method='POST')
  try:
   with urllib.request.urlopen(req,timeout=45) as r:d=json.load(r)
  except urllib.error.HTTPError as e:
   err=json.load(e).get('error',{});codes=[str(x.get('errorCode')) for dt in err.get('details',[]) for x in dt.get('errors',[])];raise SourceError('Google HTTP '+str(e.code)+' '+str(codes)) from None
  rows.extend(d.get('results',[]));p=d.get('nextPageToken')
  if not p:return rows
  if p in seen or len(seen)>=100:raise SourceError('Google incomplete pagination')
  seen.add(p);params['pageToken']=p
def dates(start,end):
 a=datetime.date.fromisoformat(start);b=datetime.date.fromisoformat(end);assert a<=b and a.strftime('%Y-%m')==b.strftime('%Y-%m') and a>=datetime.date(2026,9,1)
 return [(a+datetime.timedelta(days=n)).isoformat() for n in range((b-a).days+1)]
def meta_reconciliation_tolerance(daily_rows):
 assert isinstance(daily_rows,int) and 0<=daily_rows<=31
 return Decimal('.005')*(daily_rows+1)
def collect_account(a,start,end,meta,token,headers):
 platform=a.get('platform','meta');out={'id':a['id'],'name':a['name'],'platform':platform,'since':start,'until':end,'queried_at':now(),'status':'error'}
 try:
  def get(edge,params):
   status,d,_=meta.graph_get(edge,token,params)
   if status!=200:raise SourceError('Meta HTTP '+str(status)+' code '+str(d.get('error',{}).get('code'))+' subcode '+str(d.get('error',{}).get('error_subcode')))
   return d
  if platform=='meta':
   assert re.fullmatch(r'\d{5,30}',a['id']);m=get('act_'+a['id'],{'fields':'account_id,name,currency,timezone_name'});assert m['account_id']==a['id'];currency=m['currency'];tz=m['timezone_name']
   def insights(increment):
    params={'fields':'account_id,account_currency,date_start,date_stop,spend','level':'account','time_range':json.dumps({'since':start,'until':end}),'time_increment':increment,'limit':100};rows=[];seen=set()
    while True:
     d=get('act_'+a['id']+'/insights',params);rows.extend(d.get('data',[]))
     if not d.get('paging',{}).get('next'):return rows
     p=d.get('paging',{}).get('cursors',{}).get('after')
     if not p or p in seen or len(seen)>=100:raise SourceError('Meta incomplete pagination')
     seen.add(p);params['after']=p
   source=insights(1);aggregate=insights('all_days');daily=[]
   for r in source:
    assert r['account_id']==a['id'] and r['account_currency']==currency and r['date_start']==r['date_stop'] and start<=r['date_start']<=end;daily.append({'date':r['date_start'],'amount':r['spend']})
   assert len(aggregate)<=1
   if aggregate:assert aggregate[0]['account_id']==a['id'] and aggregate[0]['account_currency']==currency and aggregate[0]['date_start']==start and aggregate[0]['date_stop']==end
   total=Decimal(aggregate[0]['spend']) if aggregate else Decimal(0)
  elif platform=='google':
   assert re.fullmatch(r'\d{10}',a['id']);identity=google_search(a['id'],'SELECT customer.id, customer.descriptive_name, customer.currency_code, customer.time_zone FROM customer',headers);assert len(identity)==1;m=identity[0]['customer'];assert m['id']==a['id'];currency=m['currencyCode'];tz=m['timeZone'];where=" WHERE segments.date BETWEEN '"+start+"' AND '"+end+"'"
   source=google_search(a['id'],'SELECT customer.id, segments.date, metrics.cost_micros FROM customer'+where,headers);aggregate=google_search(a['id'],'SELECT customer.id, metrics.cost_micros FROM customer'+where,headers);daily=[]
   for r in source:
    assert r['customer']['id']==a['id'] and start<=r['segments']['date']<=end;micros=str(r['metrics']['costMicros']);daily.append({'date':r['segments']['date'],'amount':str(Decimal(micros)/1000000),'cost_micros':micros})
   assert len(aggregate)<=1;total=Decimal(aggregate[0]['metrics'].get('costMicros','0'))/1000000 if aggregate else Decimal(0)
  else:raise SourceError('Unsupported platform')
  assert currency==a['currency'] and tz==a['timezone'];assert datetime.date.fromisoformat(end)<datetime.datetime.now(ZoneInfo(tz)).date();assert len({r['date'] for r in daily})==len(daily)
  for r in daily:assert Decimal(r['amount']).is_finite() and Decimal(r['amount'])>=0
  summed=sum((Decimal(r['amount']) for r in daily),Decimal(0));tolerance=meta_reconciliation_tolerance(len(daily)) if platform=='meta' else Decimal(0);assert abs(summed-total)<=tolerance;observed={r['date']:r for r in daily}
  complete=[{**observed[d],'source_row':True} if d in observed else {'date':d,'amount':'0','source_row':False,'evidence':'complete_daily_and_aggregate_query_no_spend_row'} for d in dates(start,end)]
  out.update(status='ok',currency=currency,timezone=tz,daily=complete,aggregate_total=str(total),sum_daily=str(summed),reconciliation_difference=str(summed-total),reconciliation_tolerance=str(tolerance),pagination_complete=True)
 except Exception as e:out['error']=str(e) if isinstance(e,SourceError) else type(e).__name__
 return out
READ_RETRY_SECONDS=300
READ_RETRY_AUTHORITY='1560288130085560351'
def retryable_read_error(error):
 """Read-only transient candidates; never retry credentials/billing/permissions."""
 text=str(error or '')
 if text in {'AssertionError','TimeoutError','URLError','ConnectionResetError','ConnectionError','RemoteDisconnected','IncompleteRead'}:return True
 if re.search(r'(?:Meta|Google) HTTP (?:429|5\d\d)\b',text):return True
 match=re.search(r'Meta HTTP \d+ code (\d+)\b',text)
 return bool(match and int(match[1]) in {1,2,4,17,32,613,80004})

def retry_failed_batch(rows,read_one,*,status_key='status',error_key='error',history_key='collection_attempts',evidence_path=None):
 """One delayed read-only round, only failed rows, bounded shared wait."""
 rows=[dict(row) for row in rows];pending=[];streak=0;stopped=False
 for index,row in enumerate(rows):
  status=row[status_key];row[history_key]=[{'attempt':1,'status':status,'error':row.get(error_key)}]
  if status=='not_checked':stopped=True
  streak=streak+1 if status not in {'ok','unavailable_status'} else 0
  if streak>=5:stopped=True
  if status=='error' and retryable_read_error(row.get(error_key)):pending.append(index)
 if not pending or stopped:return rows
 proof={'authority':READ_RETRY_AUTHORITY,'status':'waiting','delay_seconds':READ_RETRY_SECONDS,'scheduled_at':now(),'accounts':[rows[i].get('id',rows[i].get('account_id')) for i in pending]}
 def save_proof():
  if evidence_path is not None:
   p=pathlib.Path(evidence_path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(proof));p.chmod(0o600)
 save_proof();time.sleep(READ_RETRY_SECONDS)
 proof.update(status='retrying',started_at=now());save_proof()
 with ThreadPoolExecutor(max_workers=3) as ex:
  retried=list(ex.map(read_one,[rows[i] for i in pending]))
 for index,new in zip(pending,retried):
  previous=rows[index];new=dict(new);new[history_key]=previous[history_key]+[{'attempt':2,'status':new[status_key],'error':new.get(error_key),'delay_seconds':READ_RETRY_SECONDS}]
  if new[status_key]=='ok':new['automatic_recovery']={'attempts':2,'first_error':previous.get(error_key),'delay_seconds':READ_RETRY_SECONDS,'authority':READ_RETRY_AUTHORITY}
  rows[index]=new
 proof.update(status='completed',completed_at=now(),recovered=sum(rows[i][status_key]=='ok' for i in pending),remaining=sum(rows[i][status_key]!='ok' for i in pending));save_proof()
 return rows

def collect_account_with_retry(a,start,end,meta,token,headers,attempts=2):
 assert isinstance(attempts,int) and 1<=attempts<=2
 row=collect_account(a,start,end,meta,token,headers)
 if attempts==2:row=retry_failed_batch([row],lambda _:collect_account(a,start,end,meta,token,headers))[0]
 return row,row.get('collection_attempts',[{'attempt':1,'status':row['status'],'error':row.get('error')}])
def missing_spend_account(a,start,end,meta,token,headers):
 """Read spend for an accessible unregistered account; never create it."""
 out={**a,'spend_status':'error','spend_since':start,'spend_until':end,'spend_queried_at':now()}
 if a['platform']=='google' and a.get('status') in ('CANCELED','CLOSED'):return {**out,'spend_status':'unavailable_status','spend_error':'Google account canceled; not treated as zero'}
 try:
  if a['platform']=='meta':
   status,data,_=meta.graph_get('act_'+a['account_id']+'/insights',token,{'fields':'account_id,account_currency,date_start,date_stop,spend','level':'account','time_range':json.dumps({'since':start,'until':end}),'time_increment':'all_days','limit':2})
   if status!=200:raise SourceError('Meta HTTP '+str(status)+' code '+str(data.get('error',{}).get('code')))
   rows=data.get('data',[]);assert len(rows)<=1 and not data.get('paging',{}).get('next')
   if rows:assert rows[0]['account_id']==a['account_id'] and rows[0]['date_start']==start and rows[0]['date_stop']==end and rows[0]['account_currency']==a['currency']
   amount=Decimal(rows[0]['spend']) if rows else Decimal(0)
  else:
   rows=google_search(a['account_id'],"SELECT customer.id, customer.currency_code, metrics.cost_micros FROM customer WHERE segments.date BETWEEN '"+start+"' AND '"+end+"'",headers);assert len(rows)<=1
   if rows:assert rows[0]['customer']['id']==a['account_id'] and rows[0]['customer']['currencyCode']==a['currency']
   amount=Decimal(rows[0]['metrics'].get('costMicros','0'))/1000000 if rows else Decimal(0)
  assert amount.is_finite() and amount>=0;out.update(spend_status='ok',spend_amount=str(amount))
 except Exception as e:out['spend_error']=str(e) if isinstance(e,SourceError) else type(e).__name__
 return out

def collect(registry,start,end,directory):
 dates(start,end);load_env();directory.mkdir(parents=True,exist_ok=True,mode=0o700);accounts=registry['accounts'];assert len({(a.get('platform','meta'),a['id']) for a in accounts})==len(accounts)
 spec=importlib.util.spec_from_file_location('finance_worker',ROOT/'meta-lookup-worker.py');worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker);token,_=worker.meta.get_token_from_1password('APP NOVO 02/09 Token Meta API - Contas de Anuncio Meta - Roosevelt Mattei');headers=google_headers();discovery_errors=[];discovered=[]
 for platform in ['meta','google']:
  try:
   if platform=='meta':inv,pages=worker.inventory()
   else:
    from google_ads_inventory import inventory
    inv,pages=inventory()
   discovered.extend({**v,'platform':platform} for v in inv.values())
  except Exception as e:discovery_errors.append({'platform':platform,'error':type(e).__name__})
 known={(a.get('platform','meta'),a['id']) for a in accounts};missing=[a for a in discovered if (a['platform'],a['account_id']) not in known]
 checked=[]
 with ThreadPoolExecutor(max_workers=3) as ex:
  for platform in ['meta','google']:
   group=[a for a in missing if a['platform']==platform];streak=0
   for offset in range(0,len(group),3):
    if streak>=5:
     checked.extend({**a,'spend_status':'not_checked','spend_error':'scan_stopped_after_repeated_errors'} for a in group[offset:]);break
    batch=list(ex.map(lambda a:missing_spend_account(a,start,end,worker.meta,token,headers),group[offset:offset+3]));checked.extend(batch)
    for row in batch:streak=0 if row['spend_status'] in ['ok','unavailable_status'] else streak+1
 missing=checked;(directory/'missing-spend.json').write_text(json.dumps(missing))
 def run(a):
  row=collect_account(a,start,end,worker.meta,token,headers);p=directory/(row['platform']+'-'+row['id']+'.json');p.write_text(json.dumps(row));p.chmod(0o600);return row
 with ThreadPoolExecutor(max_workers=3) as ex:rows=list(ex.map(run,accounts))
 out={'authority':'1546991137171181578','since':start,'until':end,'period':start[:7],'queried_at':now(),'registry_revision':registry['revision'],'expected_accounts':len(accounts),'accounts':rows,'discovered_count':len(discovered),'missing_accounts':missing,'discovery_errors':discovery_errors,'source_scope':{'meta_bm':'155263197283282','google_mcc':'8137016595'},'ad_writes':0,'sheet_writes':0};assert len(rows)==len(accounts);(directory/'collection.json').write_text(json.dumps(out));return out

def collect_api_first(start,end,directory):
 """Discover and inspect all API-visible accounts before reading the Dash registry."""
 dates(start,end);load_env();directory.mkdir(parents=True,exist_ok=True,mode=0o700)
 spec=importlib.util.spec_from_file_location('finance_api_worker',ROOT/'meta-lookup-worker.py');worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker);token,_=worker.meta.get_token_from_1password('APP NOVO 02/09 Token Meta API - Contas de Anuncio Meta - Roosevelt Mattei');headers=google_headers();discovered=[];errors=[]
 for platform in ['meta','google']:
  try:
   if platform=='meta':inventory,_=worker.inventory()
   else:
    from google_ads_inventory import inventory as google_inventory
    inventory,_=google_inventory()
   discovered.extend({**a,'platform':platform} for a in inventory.values())
  except Exception as e:errors.append({'platform':platform,'error':type(e).__name__})
 assert discovered and len({(a['platform'],a['account_id']) for a in discovered})==len(discovered)
 scans=[]
 with ThreadPoolExecutor(max_workers=3) as ex:
  for platform in ['meta','google']:
   group=[a for a in discovered if a['platform']==platform];streak=0
   for offset in range(0,len(group),3):
    if streak>=5:
     scans.extend({**a,'spend_status':'not_checked','spend_error':'scan_stopped_after_repeated_errors'} for a in group[offset:]);break
    batch=list(ex.map(lambda a:missing_spend_account(a,start,end,worker.meta,token,headers),group[offset:offset+3]));scans.extend(batch)
    for a in batch:streak=0 if a['spend_status'] in ['ok','unavailable_status'] else streak+1
    (directory/'api-account-scan.json').write_text(json.dumps(scans))
 positive=[a for a in scans if a['spend_status']=='ok' and Decimal(a['spend_amount'])>0]
 scan_inputs={(a['platform'],a['account_id']):a for a in discovered}
 def run(a):
  row=collect_account({**a,'id':a['account_id']},start,end,worker.meta,token,headers);row['verified_api_identity']=row['status']=='ok';row['business_id']=a.get('business_id');return row
 with ThreadPoolExecutor(max_workers=3) as ex:rows=list(ex.map(run,positive))
 # Save first observations before a shared five-minute recovery round. Both
 # phases share one wait so the existing900s standalone cron budget is retained.
 for row in rows:(directory/(row['platform']+'-'+row['id']+'.json')).write_text(json.dumps(row))
 tasks=[{'id':a['account_id'],'platform':a['platform'],'phase':'scan','status':a['spend_status'],'error':a.get('spend_error'),'value':a} for a in scans]
 tasks.extend({'id':a['id'],'platform':a['platform'],'phase':'detail','status':a['status'],'error':a.get('error'),'value':a} for a in rows)
 def reread(task):
  identity=scan_inputs[(task['platform'],task['id'])]
  if task['phase']=='scan':
   value=missing_spend_account(identity,start,end,worker.meta,token,headers)
   out={**task,'status':value['spend_status'],'error':value.get('spend_error'),'value':value}
   # A newly recovered positive account still needs the same exact detail gates.
   if value['spend_status']=='ok' and Decimal(value['spend_amount'])>0:
    detail=run(value);detail['collection_attempts']=[{'attempt':1,'status':detail['status'],'error':detail.get('error')}];detail['discovered_after_delayed_retry']=True;out['new_detail']=detail
   return out
  value=run(identity);return {**task,'status':value['status'],'error':value.get('error'),'value':value}
 tasks=retry_failed_batch(tasks,reread,evidence_path=directory/'source-retry.json')
 scans=[];rows=[]
 for task in tasks:
  value=dict(task['value']);key='scan_attempts' if task['phase']=='scan' else 'collection_attempts';value[key]=task['collection_attempts']
  if task.get('automatic_recovery'):value['automatic_recovery']=task['automatic_recovery']
  if task['phase']=='scan':
   scans.append(value)
   if task.get('new_detail'):rows.append(task['new_detail'])
  else:rows.append(value)
 positive=[a for a in scans if a['spend_status']=='ok' and Decimal(a['spend_amount'])>0]
 (directory/'api-account-scan.json').write_text(json.dumps(scans))
 for row in rows:(directory/(row['platform']+'-'+row['id']+'.json')).write_text(json.dumps(row))
 out={'schema':'api-first-1','authority':'1547015219325444107','since':start,'until':end,'period':start[:7],'queried_at':now(),'expected_accounts':len(rows),'accounts':rows,'api_scan':scans,'discovered_count':len(scans),'positive_accounts':len(positive),'discovery_errors':errors,'source_scope':{'meta_bm':'155263197283282','google_mcc':'8137016595'},'ad_writes':0,'sheet_writes':0};assert len(scans)==len(discovered) and len(rows)==len(positive);(directory/'collection.json').write_text(json.dumps(out));return out
