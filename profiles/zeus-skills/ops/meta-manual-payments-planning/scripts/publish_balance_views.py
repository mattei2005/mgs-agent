#!/usr/bin/env python3
"""Publish balance-based views; retain the full canonical Meta dataset."""
import argparse,copy,fcntl,json,os,re,sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
sys.path.insert(0,'/root/mgs-agent/scripts')
HOME=Path('/root/mgs-agent/data/meta-manual-payments')

def aid(row):
 cells=row.get('values',[])
 match=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note','')) if cells else None
 return match[1] if match else None

def label(row):
 return row.get('values',[{}])[0].get('userEnteredValue',{}).get('stringValue','')

def authored(row):
 return {'values':[{k:copy.deepcopy(v) for k,v in c.items() if k in ['userEnteredValue','userEnteredFormat','note','dataValidation','textFormatRuns']} for c in row.get('values',[])]}

def canon(value):
 if isinstance(value,dict):
  d={k:canon(v) for k,v in value.items() if k not in ['backgroundColorStyle','foregroundColorStyle']}
  if 'values' in d:
   while d['values'] and d['values'][-1]=={}:d['values'].pop()
  return d
 if isinstance(value,list):return [canon(v) for v in value]
 if isinstance(value,float):return round(value,6)
 return value

def is_zero(row):
 cells=row.get('values',[])
 value=cells[8].get('effectiveValue',{}).get('numberValue') if len(cells)>8 else None
 return value is not None and not isinstance(value,bool) and Decimal(str(value))==0

def partition(rows):
 accounts=[r for r in rows if aid(r)]
 assert len({aid(r) for r in accounts})==len(accounts),'duplicate_ids'
 return [r for r in accounts if not is_zero(r)],[r for r in accounts if is_zero(r)]

def build_view(source_rows,accounts,description):
 headers=[authored(r) for r in source_rows if label(r)=='Nome da conta'];assert len(headers)==2
 templates={label(r).split(' — ')[0]:authored(r) for r in source_rows if label(r).startswith(('CARTÃO','LINHA','TOTAL'))}
 groups={'Cartão de crédito':[],'Linha de crédito':[]}
 for row in accounts:
  method=row['values'][1]['userEnteredValue']['stringValue'];assert method in groups
  groups[method].append(authored(row))
 out=[headers[0]];positions={};sub={}
 for method,title,total in [('Cartão de crédito','CARTÃO DE CRÉDITO','TOTAL CARTÃO DE CRÉDITO'),('Linha de crédito','LINHA DE CRÉDITO','TOTAL LINHA DE CRÉDITO')]:
  row=copy.deepcopy(templates[title]);row['values'][0]['userEnteredValue']={'stringValue':title+' — '+str(len(groups[method]))+' contas'};out.append(row)
  if method=='Linha de crédito':out.append(copy.deepcopy(headers[1]))
  start=len(out);out.extend(groups[method]);end=len(out);positions[method]=(start,end)
  row=copy.deepcopy(templates[total]);cols=[6,8,9] if method=='Cartão de crédito' else [5,6,7,8,9]
  if method=='Cartão de crédito' and any('numberValue' in r['values'][5].get('userEnteredValue',{}) for r in groups[method]):cols.insert(0,5)
  for k in [5,6,7,8,9]:
   if k not in cols:row['values'][k].pop('userEnteredValue',None);continue
   formula=f'=ROUND(SUM({chr(65+k)}{start+1}:{chr(65+k)}{end}),2)' if end>start else '=ROUND(SUM(0),2)'
   row['values'][k]['userEnteredValue']={'formulaValue':formula};row['values'][k]['note']='Subtotal somente desta aba. '+description+' Células vazias preservadas; não são zero confirmado.'
  sub[method]=len(out)+1;out.append(row)
 out.append({'values':[{} for _ in range(10)]});row=copy.deepcopy(templates['TOTAL GERAL']);row['values'][0]['userEnteredValue']={'stringValue':'TOTAL GERAL — '+str(len(accounts))+' contas'}
 for k in [5,6,7,8,9]:
  row['values'][k]['userEnteredValue']={'formulaValue':f'=ROUND(SUM({chr(65+k)}{sub["Cartão de crédito"]},{chr(65+k)}{sub["Linha de crédito"]}),2)'};row['values'][k]['note']='Total desta aba. '+description+' H pode ser parcial por ausência de prova própria.'
 out.append(row)
 for i in [0,positions['Linha de crédito'][0]-1]:out[i]['values'][8]['note']=description+' Critério: coluna I — Saldo a pagar; somente zero numérico confirmado vai para a aba de zeros. Em branco/erro/não confirmado permanece na principal. Não é filtro pelo gasto mensal. Fonte: base canônica; horário de cada métrica preservado nas notas.'
 assert len(out)==len(accounts)+8
 return out,positions

def main():
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
 import mgs_google_workspace_auth as g
 g.load_env();assert all(os.getenv(k)=='service_account' for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']);sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com';token=g.service_account_access_token()
 def api(method,url,payload=None):
  code,data=g.api_json(method,url,token,payload,quota_project='mgs-core-prod');assert code==200,'google_http_'+str(code);return data
 with (HOME/'writer.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  path=HOME/'digital-trust-workbook-contract.json';contract=json.loads(path.read_text());cfg=contract['balance_views'];assert cfg['enabled'] and cfg['authority_message_id'] in contract['authorization_messages'];assert cfg['source_sheet_id']==contract['sheet_id']
  root='https://sheets.googleapis.com/v4/spreadsheets/'+contract['spreadsheet_id'];caps=api('GET','https://www.googleapis.com/drive/v3/files/'+contract['spreadsheet_id']+'?supportsAllDrives=true&fields=trashed,capabilities(canEdit)');assert not caps.get('trashed') and caps['capabilities']['canEdit']
  before=api('GET',root+'?includeGridData=true');source=next(s for s in before['sheets'] if s['properties']['sheetId']==contract['sheet_id']);assert source['properties']['title']==contract['sheet_title'];rows=source['data'][0]['rowData'];main_rows,zero_rows=partition(rows);assert {aid(r) for r in main_rows+zero_rows}==set(contract['account_ids'])
  ids=[cfg['main_sheet_id'],cfg['zero_sheet_id']];assert len(set(ids+[cfg['source_sheet_id']]))==3
  views=[]
  for kind,accounts in [('main',main_rows),('zero',zero_rows)]:
   desc='Visualização principal: saldo a pagar diferente de zero ou ainda não confirmado.' if kind=='main' else 'Arquivo operacional: saldo a pagar exatamente zero; contas continuam monitoradas.'
   output,bounds=build_view(rows,accounts,desc);views.append({'kind':kind,'id':cfg[kind+'_sheet_id'],'title':cfg[kind+'_title'],'rows':output,'bounds':bounds,'accounts':accounts})
  run=Path('/root/mgs-agent/reports/meta-manual-payments-runs')/('balance-views-'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));run.mkdir(mode=0o700)
  (run/'before.json').write_text(json.dumps(before,ensure_ascii=False));(run/'plan.json').write_text(json.dumps([{k:v for k,v in x.items() if k!='accounts'} for x in views],ensure_ascii=False))
  if not args.apply:print(json.dumps({'status':'views_plan','run_dir':str(run),'source_accounts':len(contract['account_ids']),'main':len(main_rows),'zero':len(zero_rows),'sheets_write_calls':0}));return
  assert api('GET',root+'?includeGridData=true')==before,'concurrent_workbook_change';requests=[];existing={s['properties']['sheetId']:s for s in before['sheets']}
  for view in views:
   sid=view['id'];count=len(view['rows']);prop={'sheetId':sid,'title':view['title'],'hidden':False,'gridProperties':{'rowCount':max(count+6,existing.get(sid,{}).get('properties',{}).get('gridProperties',{}).get('rowCount',0)),'columnCount':10,'frozenRowCount':1}}
   if sid in existing:
    assert existing[sid]['properties']['title']==view['title'],'view_title_drift'
    # Only the exact previously generated IDs may occur in a managed view.
    oldids={aid(r) for d in existing[sid].get('data',[]) for r in d.get('rowData',[]) if aid(r)};assert oldids<=set(contract['account_ids']),'foreign_account_in_view'
    requests.append({'updateSheetProperties':{'properties':prop,'fields':'gridProperties.rowCount,gridProperties.frozenRowCount,hidden'}})
   else:requests.append({'addSheet':{'properties':prop}})
   # Clear only prior generated view cells, never source or unrelated tabs.
   end=max(count,len(existing.get(sid,{}).get('data',[{}])[0].get('rowData',[])))
   requests.append({'updateCells':{'range':{'sheetId':sid,'startRowIndex':0,'endRowIndex':end,'startColumnIndex':0,'endColumnIndex':10},'rows':view['rows'],'fields':'userEnteredValue,userEnteredFormat,note'}})
   st,en=view['bounds']['Linha de crédito'];requests.append({'setBasicFilter':{'filter':{'range':{'sheetId':sid,'startRowIndex':st-1,'endRowIndex':en,'startColumnIndex':0,'endColumnIndex':10}}}})
   requests.extend([{'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':0,'endIndex':1},'properties':{'pixelSize':360},'fields':'pixelSize'}},{'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':1,'endIndex':10},'properties':{'pixelSize':170},'fields':'pixelSize'}}])
  requests.append({'updateSheetProperties':{'properties':{'sheetId':cfg['source_sheet_id'],'hidden':True},'fields':'hidden'}})
  (run/'write-intent.json').write_text(json.dumps({'requests':requests},ensure_ascii=False));api('POST',root+':batchUpdate',{'requests':requests});after=api('GET',root+'?includeGridData=true');(run/'after.json').write_text(json.dumps(after,ensure_ascii=False))
  actual={s['properties']['sheetId']:s for s in after['sheets']};base=copy.deepcopy(actual[cfg['source_sheet_id']]);base['properties'].pop('hidden',None);old=copy.deepcopy(source);old['properties'].pop('hidden',None);assert base==old,'canonical_source_changed';assert actual[cfg['source_sheet_id']]['properties']['hidden']
  for sid,ss in existing.items():
   if sid not in ids+[cfg['source_sheet_id']]:assert actual[sid]==ss,'unrelated_sheet_changed'
  totals={};all_ids=set()
  for view in views:
   s=actual[view['id']];ar=s['data'][0]['rowData'];expected=view['rows'];assert len(ar)>=len(expected)
   for i,row in enumerate(expected):assert canon(authored(ar[i]))==canon(authored(row)),'view_row_mismatch_'+view['kind']+'_'+str(i+1)
   for row in ar[len(expected):]:assert not any(c.get('userEnteredValue') or c.get('note') for c in row.get('values',[])),'stale_view_tail'
   accounts=[r for r in ar if aid(r)];v_ids={aid(r) for r in accounts};assert len(accounts)==len(v_ids) and v_ids=={aid(r) for r in view['accounts']} and not v_ids&all_ids;all_ids|=v_ids
   for row in ar:
    for cell in row.get('values',[]):assert 'errorValue' not in cell.get('effectiveValue',{}),'view_formula_error'
   grand=next(r for r in ar if label(r).startswith('TOTAL GERAL'));totals[view['kind']]={}
   for k in [5,6,7,8,9]:
    observed=Decimal(str(grand['values'][k]['effectiveValue']['numberValue'])).quantize(Decimal('.01'));expected_total=sum((Decimal(str(r['values'][k].get('effectiveValue',{}).get('numberValue',0))) for r in accounts),Decimal(0)).quantize(Decimal('.01'));assert observed==expected_total,'view_total_mismatch';totals[view['kind']][chr(65+k)]=str(observed)
  assert all_ids==set(contract['account_ids']) and json.loads(path.read_text())==contract
  receipt={'status':'balance_views_published_validated','run_dir':str(run),'authority_message_id':cfg['authority_message_id'],'source_accounts':len(all_ids),'main_accounts':len(main_rows),'zero_accounts':len(zero_rows),'main_sheet_id':cfg['main_sheet_id'],'zero_sheet_id':cfg['zero_sheet_id'],'criterion':'I — Saldo a pagar: only numeric zero, unknown retained in main','source_values_notes_formulas_unchanged':True,'unrelated_sheets_unchanged':True,'all_view_account_rows_exact':True,'all_ids_disjoint_and_complete':True,'totals':totals,'meta_writes':0,'payments_executed':0,'published_at':datetime.now().astimezone().isoformat()};(run/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));latest=HOME/'balance-views-last-publication.json';tmp=latest.with_suffix('.json.next');tmp.write_text(json.dumps(receipt,ensure_ascii=False,indent=2));os.chmod(tmp,0o600);os.replace(tmp,latest);print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':
 try:main()
 except Exception as exc:print(json.dumps({'status':'blocked','reason':str(exc)[:240],'meta_writes':0,'payments_executed':0}));sys.exit(2)
