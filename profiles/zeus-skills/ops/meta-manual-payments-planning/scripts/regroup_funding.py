#!/usr/bin/env python3
"""Read-only live funding; presentation-only regroup under explicit workbook authority."""
import argparse,copy,fcntl,json,os,re,sys
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
import requests
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
H=Path('/root/mgs-agent/data/meta-manual-payments')
AUTH='1564115318887161857'
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2));os.chmod(p,0o600)
def normal(b):
 b=copy.deepcopy(b)
 for s in b['sheets']:
  for data in s.get('data',[]):
   for row in data.get('rowData',[]):
    cs=row.get('values',[])
    while cs and cs[-1]=={}:cs.pop()
    if not cs:row.pop('values',None)
 return b

def build(before,funding):
 b=copy.deepcopy(before);s=b['sheets'][0];rows=s['data'][0]['rowData'];assert not s.get('merges'),'merged_grid_not_supported'
 def label(r):return r.get('values',[{}])[0].get('userEnteredValue',{}).get('stringValue','')
 def aid(r):
  cs=r.get('values',[]);m=re.search(r'^ID da conta: (\d+)\b',cs[0].get('note',''))if cs else None
  return m[1]if m else None
 accounts=[r for r in rows if aid(r)];assert {aid(r)for r in accounts}==set(funding)
 headers=[r for r in rows if label(r)=='Nome da conta'];assert len(headers)==2 and len(headers[0]['values'])==10
 template={label(r).split(' — ')[0]:r for r in rows if label(r).startswith(('CARTÃO','LINHA','TOTAL'))}
 groups={'Cartão de crédito':[],'Linha de crédito':[]};changes=[]
 for r in accounts:
  i=aid(r);cs=r['values'];live=funding[i];old=cs[1]['userEnteredValue']['stringValue'];method=live['method'];assert live['name']==label(r),'account_name_drift'
  if old!=method:
   assert old=='Linha de crédito'and method=='Cartão de crédito','unapproved_reverse_or_unknown_transition'
   assert not cs[5].get('userEnteredValue',{}).get('numberValue',0),'nonzero_invoice_requires_card_subtotal_design'
   changes.append({'id':i,'name':live['name'],'from':old,'to':method})
   cs[1]['userEnteredValue']={'stringValue':method};cs[2]['userEnteredValue']={'stringValue':live['default']}
   cs[7].pop('userEnteredValue',None);cs[7]['note']='Fora do recorte Pay now: funding padrão atual é cartão; valor anterior preservado no backup. Nenhum billing alterado.'
   cs[5].pop('userEnteredValue',None)
  groups[method].append(r)
 if not changes:return b,changes,groups
 # Preserve every pre-existing relative order; insert newly-card accounts by exact name.
 moved={x['id']for x in changes};cards=[r for r in groups['Cartão de crédito']if aid(r)not in moved]
 for r in [r for r in groups['Cartão de crédito']if aid(r)in moved]:
  pos=next((j for j,x in enumerate(cards)if label(x)>label(r)),len(cards));cards.insert(pos,r)
 groups['Cartão de crédito']=cards
 out=[headers[0]];positions={};subpos={}
 for method,title,total in [('Cartão de crédito','CARTÃO DE CRÉDITO','TOTAL CARTÃO DE CRÉDITO'),('Linha de crédito','LINHA DE CRÉDITO','TOTAL LINHA DE CRÉDITO')]:
  title_row=copy.deepcopy(template[title]);title_row['values'][0]['userEnteredValue']={'stringValue':title+' — '+str(len(groups[method]))+' contas'};out.append(title_row)
  if method=='Linha de crédito':out.append(headers[1])
  start=len(out)+1;out.extend(groups[method]);end=len(out);positions[method]=(start,end)
  sub=copy.deepcopy(template[total]);cs=sub['values'];cols=[6,8,9]if method=='Cartão de crédito'else[5,6,7,8,9]
  for col in cols:
   letter=chr(65+col);cs[col]['userEnteredValue']={'formulaValue':f'=ROUND(SUM({letter}{start}:{letter}{end}),2)'}
  subpos[method]=len(out)+1;out.append(sub)
 out.append(copy.deepcopy(rows[53]));grand=copy.deepcopy(template['TOTAL GERAL']);
 for col in [5,6,7,8,9]:
  letter=chr(65+col);grand['values'][col]['userEnteredValue']={'formulaValue':f'=ROUND(SUM({letter}{subpos["Cartão de crédito"]},{letter}{subpos["Linha de crédito"]}),2)'}
 out.append(grand)
 assert len(out)==55
 out.extend(copy.deepcopy(rows[55:]));s['data'][0]['rowData']=out
 assert {aid(r)for r in out if aid(r)}==set(funding)and len([r for r in out if aid(r)])==len(funding)
 return b,changes,groups

def main():
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args();c=json.loads((H/'digital-trust-workbook-contract.json').read_text());assert AUTH in c['authorization_messages'],'regroup_authority_missing'
 g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']);sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod'and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com';t=g.service_account_access_token()
 def api(m,u,d=None):
  status,data=g.api_json(m,u,t,d,quota_project='mgs-core-prod');assert status==200,'google_http_'+str(status);return data
 root='https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id'];url=root+'?includeGridData=true&ranges='+quote("'"+c['sheet_title']+"'!A:K",safe='')+'&fields=sheets(properties,merges,basicFilter,bandedRanges,data(rowData(values(userEnteredValue,userEnteredFormat,note))))'
 caps=api('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=trashed,capabilities(canEdit)');assert not caps.get('trashed')and caps['capabilities']['canEdit']
 obj=g._op_item_json(c['meta_token_item_id'],'MGS Conteúdo');token=next(f['value']for key in ['credential','token']for f in obj.get('fields',[])if (f.get('id','').lower()==key or f.get('label','').lower()==key)and f.get('value'))
 sess=requests.Session()
 def graph(path,params):
  r=sess.get('https://graph.facebook.com/v26.0/'+path,params={**params,'access_token':token},timeout=60);d=r.json();assert r.status_code==200 and'error'not in d,'meta_read_failed_code_'+str(d.get('error',{}).get('code'));return d
 assert graph('me',{'fields':'id'})['id']==c['meta_actor_id'];funding={}
 for start in range(0,len(c['account_ids']),40):
  ids=c['account_ids'][start:start+40];r=sess.post('https://graph.facebook.com/v26.0/',data={'access_token':token,'batch':json.dumps([{'method':'GET','relative_url':'act_'+i+'?fields=account_id,name,currency,business,funding_source_details'}for i in ids])},timeout=150);ds=r.json();assert r.status_code==200 and isinstance(ds,list)and len(ds)==len(ids)
  for i,child in zip(ids,ds):
   d=json.loads(child['body']);assert child['code']==200 and d['account_id']==i and d['business']['id']==c['business_id']and d['currency']=='USD'
   f=d.get('funding_source_details')or{};typ=f.get('type');assert typ in [1,4],'unknown_funding';method='Cartão de crédito'if typ==1 else'Linha de crédito';display=f.get('display_string','')
   if typ==1:assert not display or re.fullmatch(r'(American Express|Mastercard|MasterCard|Visa|Discover) \*\d{4}',display),'unrecognized_card_display'
   else:assert display=='monthly invoicing'
   funding[i]={'name':d['name'],'method':method,'default':display.replace(' *',' •••• ')if display and typ==1 else'Não identificado pela Meta'if typ==1 else'Não se aplica'}
 before=api('GET',url);assert before['sheets'][0]['properties']['sheetId']==c['sheet_id'];expected,changes,groups=build(before,funding)
 run=Path('/root/mgs-agent/reports/meta-manual-payments-runs')/('regroup-'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));save(run/'before.json',before);save(run/'plan.json',{'funding':funding,'changes':changes,'expected':expected})
 if a.apply:
  with(H/'writer.lock').open('a')as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);assert api('GET',url)==before,'concurrent_sheet_change'
   if changes:
    api('POST',root+':batchUpdate',{'requests':[{'updateCells':{'range':{'sheetId':c['sheet_id'],'startRowIndex':0,'endRowIndex':55,'startColumnIndex':0,'endColumnIndex':10},'rows':expected['sheets'][0]['data'][0]['rowData'][:55],'fields':'userEnteredValue,userEnteredFormat,note'}}]});assert normal(api('GET',url))==normal(expected),'regroup_readback_mismatch'
   fresh=json.loads((H/'digital-trust-workbook-contract.json').read_text());assert fresh==c,'contract_concurrent_change';save(run/'contract-before.json',c)
   c['pay_now_account_ids']=[i for i,x in funding.items()if x['method']=='Linha de crédito'];c['general_refresh_blocker']=None;c['pending_sheet_reclassification']=None;c['native_schedule_state']='enabled_dynamic_live_funding_regroup';c['last_regroup_report']=str(run);save(H/'digital-trust-workbook-contract.json',c)
 result={'status':'regroup_validated'if a.apply else'regroup_plan','accounts':len(funding),'groups':{k:len(v)for k,v in groups.items()},'changes':changes,'run_dir':str(run),'meta_writes':0,'payments_executed':0};save(run/'receipt.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'blocked','reason':str(e)[:200]}));sys.exit(2)
