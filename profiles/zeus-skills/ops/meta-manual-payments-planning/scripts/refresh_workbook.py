#!/usr/bin/env python3
"""Refresh approved Meta workbook through read-only Meta + narrow Sheets writes.
D is never inferred from generic API events: new payments require PC1 proof.
"""
import argparse,copy,fcntl,json,os,re,subprocess,sys
from pathlib import Path
from datetime import datetime,timedelta,date
from decimal import Decimal,ROUND_HALF_UP
from urllib.parse import quote,urlencode
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
import requests
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
ROOT=Path('/root/mgs-agent');HOME=ROOT/'data/meta-manual-payments'

def zone(name):
 try:return ZoneInfo(name)
 except ZoneInfoNotFoundError:
  links={p[2]:p[1] for l in Path('/usr/share/zoneinfo/tzdata.zi').read_text().splitlines() if len(p:=l.split())>=3 and p[0]in ['L','Link']}
  seen=set()
  while name in links and name not in seen:seen.add(name);name=links[name]
  return ZoneInfo(name)

def save(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.next');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));os.chmod(tmp,0o600);os.replace(tmp,path)

def main():
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
 contract=json.loads((HOME/'digital-trust-workbook-contract.json').read_text());ledger=json.loads((HOME/'pc1-card-ledger.json').read_text());g.load_env()
 assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
 sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod'and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com';gt=g.service_account_access_token()
 def google(method,url,payload=None):
  s,d=g.api_json(method,url,gt,payload,quota_project='mgs-core-prod')
  if s!=200:raise RuntimeError('google_http_'+str(s)+':'+str(d.get('error',{}).get('status')))
  return d
 sheet=contract['spreadsheet_id'];sid=contract['sheet_id'];bm=contract['business_id'];apiroot='https://sheets.googleapis.com/v4/spreadsheets/'+sheet;rng="'"+contract['sheet_title']+"'!A:J"
 gridurl=apiroot+'?includeGridData=true&ranges='+quote(rng,safe='')+'&fields=sheets(properties,basicFilter,bandedRanges,data(rowData(values(userEnteredValue,userEnteredFormat,note))))'
 before=google('GET',gridurl);rows=before['sheets'][0]['data'][0]['rowData'];assert before['sheets'][0]['properties']['sheetId']==sid
 headers=[c.get('userEnteredValue',{}).get('stringValue','')for c in rows[0]['values']]
 def column(prefix):
  matches=[i for i,h in enumerate(headers)if h.startswith(prefix)];assert len(matches)==1,'header_not_unique_'+prefix;return matches[0]
 avgcol=column('Média diária');balancecol=column('Saldo a pagar');monthcol=column('Total já gasto');financial=[(avgcol,'average_daily'),(balancecol,'balance'),(monthcol,'month_spend')]
 assert (avgcol,balancecol,monthcol)in [(4,5,6),(4,6,7),(6,8,9)],'unapproved_financial_schema'
 targets=[]
 for ri,r in enumerate(rows):
  c=r.get('values',[])
  if c and (m:=re.search(r'^ID da conta: (\d+)\b',c[0].get('note',''))):targets.append({'id':m[1],'row':ri,'cells':c})
 assert set(t['id']for t in targets)==set(contract['account_ids'])and len(targets)==len(contract['account_ids'])
 obj=g._op_item_json(contract['meta_token_item_id'],'MGS Conteúdo');mt=None
 for label in ['credential','token']:
  for f in obj.get('fields',[]):
   if not mt and (f.get('id','').lower()==label or f.get('label','').lower()==label)and f.get('value'):mt=f['value']
 assert mt
 sess=requests.Session()
 def graph(path,params=None):
  r=sess.get('https://graph.facebook.com/v26.0/'+path,params={**(params or {}),'access_token':mt},timeout=60);d=r.json()
  if r.status_code!=200 or'error'in d:
   e=d.get('error',{});raise RuntimeError('meta_http_'+str(r.status_code)+'_code_'+str(e.get('code'))+'_subcode_'+str(e.get('error_subcode')))
  return d
 def batch(paths):
  out=[]
  for start in range(0,len(paths),40):
   part=paths[start:start+40];r=sess.post('https://graph.facebook.com/v26.0/',data={'access_token':mt,'batch':json.dumps([{'method':'GET','relative_url':x}for x in part])},timeout=150);data=r.json();assert r.status_code==200 and isinstance(data,list)and len(data)==len(part)
   for child in data:
    d=json.loads(child['body']);assert child['code']==200 and'error'not in d,{'meta_code':d.get('error',{}).get('code')};out.append(d)
  return out
 assert graph('me',{'fields':'id'})['id']==contract['meta_actor_id']
 fields='account_id,name,currency,timezone_name,business,funding_source_details,user_tasks,balance'
 accounts=batch(['act_'+t['id']+'?fields='+fields for t in targets]);plans=[];requests_meta=[]
 for t,a in zip(targets,accounts):
  assert a['account_id']==t['id']and a['business']['id']==bm and a['currency']=='USD'
  now=datetime.now(zone(a['timezone_name']));today=now.date();period={'since':contract['month_since'],'until':min(today,date.fromisoformat(contract['month_until'])).isoformat()};avg={'since':(today-timedelta(days=3)).isoformat(),'until':(today-timedelta(days=1)).isoformat()}
  plans.append({'target':t,'account':a,'month':period,'average':avg})
  for tr,inc in [(period,1),(period,'all_days'),(avg,1),(avg,'all_days')]:requests_meta.append('act_'+t['id']+'/insights?'+urlencode({'level':'account','fields':'account_id,account_currency,spend,date_start,date_stop','time_range':json.dumps(tr),'time_increment':inc,'limit':100}))
 insights=batch(requests_meta);pending=[];planned=[];nowstamp=datetime.now().astimezone().isoformat()
 for i,plan in enumerate(plans):
  t=plan['target'];a=plan['account'];bodies=insights[i*4:i*4+4]
  for d in bodies:
   assert not d.get('paging',{}).get('next')
   for x in d.get('data',[]):assert x['account_id']==t['id']and x['account_currency']=='USD'
  totals=[sum((Decimal(x['spend'])for x in b.get('data',[])),Decimal(0))for b in bodies]
  assert abs(totals[0]-totals[1])<=Decimal('.01')and abs(totals[2]-totals[3])<=Decimal('.01'),'insights_daily_aggregate_mismatch'
  funding=a.get('funding_source_details')or{};typ=funding.get('type');method='Cartão de crédito'if typ==1 else'Linha de crédito'if typ==4 and funding.get('display_string')=='monthly invoicing'else'Não identificado pela Meta'
  # Stop structural drift rather than silently moving or dropping authorized accounts.
  assert t['cells'][1]['userEnteredValue']['stringValue']==method,'funding_group_changed_requires_skill_regroup:account='+t['id']+';sheet='+t['cells'][1]['userEnteredValue']['stringValue']+';live='+method
  default=funding.get('display_string','')if method=='Cartão de crédito'else'Não se aplica'if method=='Linha de crédito'else'Não disponível'
  if method=='Cartão de crédito':
   if default:assert re.fullmatch(r'(American Express|Mastercard|MasterCard|Visa|Discover) \*\d{4}',default)
   default=default.replace(' *',' •••• ')if default else'Não identificado pela Meta'
   proof=ledger['accounts'].get(t['id']);assert proof
   since=datetime.fromisoformat(proof['read_at']);params={'business_id':bm,'category':'BUDGET','since':int(since.timestamp()),'until':int(datetime.now().timestamp()),'fields':'event_time,event_type,extra_data','limit':100};has_new=False
   while True:
    ev=graph('act_'+t['id']+'/activities',params)
    for e in ev.get('data',[]):
     if e.get('event_type')=='ad_account_billing_charge'and datetime.fromisoformat(e['event_time'])>since:has_new=True
    if not ev.get('paging',{}).get('next'):break
    params['after']=ev['paging']['cursors']['after']
   if has_new:pending.append({'account_id':t['id'],'name':a['name'],'reason':'new_generic_payment_since_pc1_proof'})
  balance=Decimal(a['balance'])/100;average=(totals[3]/3).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
  planned.append({'id':t['id'],'name':a['name'],'row':t['row'],'method':method,'default':default,'balance':str(balance),'month_spend':str(totals[1]),'average_daily':str(average),'average_period':plan['average'],'month_period':plan['month'],'timezone':a['timezone_name']})
 run=ROOT/'reports/meta-manual-payments-runs'/datetime.now().strftime('%Y%m%dT%H%M%S%f');run.mkdir(parents=True)
 save(run/'plan.json',{'contract':contract,'before':before,'planned':planned,'pending_ui':pending,'collected_at':nowstamp})
 if pending:
  print(json.dumps({'status':'needs_pc1_payment_history','run_dir':str(run),'pending_ui_accounts':pending,'sheet_writes':0},ensure_ascii=False));return 3
 if not args.apply:
  print(json.dumps({'status':'dry_run_pass','run_dir':str(run),'accounts':len(planned),'pending_ui_accounts':[],'sheet_writes':0},ensure_ascii=False));return 0
 with (HOME/'writer.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);assert google('GET',gridurl)==before,'concurrent_sheet_change'
  expected=copy.deepcopy(before);erows=expected['sheets'][0]['data'][0]['rowData'];req=[]
  for p in planned:
   ri=p['row'];cells=erows[ri]['values'];cells[2]['userEnteredValue']={'stringValue':p['default']}
   req.append({'updateCells':{'start':{'sheetId':sid,'rowIndex':ri,'columnIndex':2},'rows':[{'values':[cells[2]]}],'fields':'userEnteredValue'}})
   for col,key in financial:
    cells[col]['userEnteredValue']={'numberValue':float(Decimal(p[key]))};oldnote=cells[col].get('note','')
    note='Atualizado '+nowstamp+'. Fonte Meta Graph v26.0; moeda USD; conta '+p['id']+'; fuso '+p['timezone']+'. '
    if col==avgcol:note+='Média de '+p['average_period']['since']+' a '+p['average_period']['until']+' (3 dias completos, zeros incluídos), diário/agregado reconciliados.'
    elif col==balancecol:note+='Current balance; não é invoice vencida nem Amount you can pay now.'
    else:note+='Gasto de '+p['month_period']['since']+' a '+p['month_period']['until']+'; dia aberto parcial quando aplicável; diário/agregado reconciliados.'
    if p['id']=='2633813727134360'and col==balancecol and 'Conciliação de outubro'in oldnote:note+=' Histórico da conciliação anterior: '+oldnote[oldnote.find('Conciliação de outubro'):]
    cells[col]['note']=note
    req.append({'updateCells':{'start':{'sheetId':sid,'rowIndex':ri,'columnIndex':col},'rows':[{'values':[cells[col]]}],'fields':'userEnteredValue,note'}})
  for col,_ in financial:erows[0]['values'][col]['note']='Atualização automática 3x/dia America/New_York. Última coleta: '+nowstamp+'. Média: três dias completos anteriores, nos fusos das contas. Gasto mensal fixado em outubro/2026 conforme contrato. Fonte Meta; nenhuma cobrança executada.';req.append({'updateCells':{'start':{'sheetId':sid,'rowIndex':0,'columnIndex':col},'rows':[{'values':[erows[0]['values'][col]]}],'fields':'note'}})
  google('POST',apiroot+':batchUpdate',{'requests':req});after=google('GET',gridurl);assert after==expected,'sheet_full_readback_mismatch'
  save(run/'receipt.json',{'status':'updated_validated','accounts':len(planned),'collected_at':nowstamp,'completed_at':datetime.now().astimezone().isoformat(),'pending_ui':[],'meta_writes':0,'payment_actions':0,'full_grid_exact_readback':True})
  save(HOME/'last-refresh.json',{'status':'updated_validated','run_dir':str(run),'collected_at':nowstamp,'accounts':len(planned)})
 print(json.dumps({'status':'updated_validated','accounts':len(planned),'run_dir':str(run),'meta_writes':0,'payments_executed':0,'snapshot_at':nowstamp},ensure_ascii=False));return 0

if __name__=='__main__':
 try:sys.exit(main())
 except Exception as exc:
  print(json.dumps({'status':'blocked','error':str(exc)[:220],'payments_executed':0},ensure_ascii=False));sys.exit(2)
