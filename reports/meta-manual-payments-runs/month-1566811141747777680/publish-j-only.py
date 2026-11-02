#!/usr/bin/env python3
"""Publish only approved November J data; never write A:I or another tab."""
import sys,json,re,copy,fcntl
from pathlib import Path
from decimal import Decimal
from datetime import datetime
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
B=Path(__file__).parent
H=Path('/root/mgs-agent/data/meta-manual-payments')
R=Path('/root/mgs-agent/reports/meta-manual-payments-runs/20261102T085003783414')
def load(p):return json.loads(p.read_text())
def save(p,d):
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
c=load(H/'digital-trust-workbook-contract.json');plan=load(R/'plan.json')
assert c['month_since']=='2026-11-01' and c['month_until']=='2026-11-30' and c['month_period_authority_message']=='1566811141747777680'
assert set(x['id']for x in plan['planned'])==set(c['account_ids']) and len(plan['planned'])==47 and not plan['pending_ui']
assert all(x['month_period']['since']=='2026-11-01' and x['month_period']['until']>='2026-11-01' for x in plan['planned'])
g.load_env();sa=g.load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['project_id']=='mgs-core-prod'
t=g.service_account_access_token();base='https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']
def api(method,url,data=None):
 s,d=g.api_json(method,url,t,data,quota_project='mgs-core-prod');assert s==200,('google_http',s);return d
def get():return api('GET',base+'?includeGridData=true')
def sheet(book):return next(x for x in book['sheets']if x['properties']['sheetId']==c['sheet_id'])
def rows(book):return sheet(book)['data'][0]['rowData']
def cell(row,col):return (row.get('values',[])+[{}]*10)[col]
def val(cell):return next(iter(cell.get('userEnteredValue',{}).values()),None)
def ids(book):
 out={}
 for i,row in enumerate(rows(book)):
  m=re.search(r'^ID da conta: (\d+)\b',cell(row,0).get('note',''))
  if m:assert m[1]not in out;out[m[1]]=i
 return out
def authored(book,exclude_j=False):
 result=copy.deepcopy(book)
 for sh in result['sheets']:
  for grid in sh.get('data',[]):
   for row in grid.get('rowData',[]):
    for i,ce in enumerate(row.get('values',[])):
     ce.pop('effectiveValue',None);ce.pop('effectiveFormat',None);ce.pop('formattedValue',None);ce.pop('hyperlink',None)
     if exclude_j and sh['properties']['sheetId']==c['sheet_id'] and i==9:
      ce.pop('userEnteredValue',None);ce.pop('note',None)
 return result
status,drive=g.api_json('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=id,capabilities(canEdit)',t,quota_project='mgs-core-prod');assert status==200 and drive['capabilities']['canEdit']
with (H/'writer.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 before=get();save(B/'before-j-write.json',before);mapping=ids(before);assert set(mapping)==set(c['account_ids'])
 original=load(B/'workbook-before.json');assert authored({'sheets':[sheet(before)]})==authored({'sheets':[sheet(original)]}),'target_changed_during_collection'
 request=[];expected={};stamp=plan['collected_at']
 for p in plan['planned']:
  ri=mapping[p['id']];assert ri==p['row'] and val(cell(rows(before)[ri],0))==p['name']
  amount=Decimal(p['month_spend']);assert amount>=0
  note='Atualizado '+stamp+'. Fonte Meta Graph v26.0; conta '+p['id']+'; moeda USD; fuso '+p['timezone']+'. Gasto de '+p['month_period']['since']+' a '+p['month_period']['until']+'; dia aberto parcial; diário/agregado reconciliados. Competência novembro/2026 autorizada por Rodolfo1566811141747777680.'
  value={'userEnteredValue':{'numberValue':float(amount)},'note':note};expected[ri]=value
  request.append({'updateCells':{'start':{'sheetId':c['sheet_id'],'rowIndex':ri,'columnIndex':9},'rows':[{'values':[value]}],'fields':'userEnteredValue,note'}})
 header={'userEnteredValue':{'stringValue':'Total já gasto — Novembro/2026'},'note':'Gasto corrente novembro/2026 desde01/11, dia aberto parcial no fuso de cada conta. Última coleta '+stamp+'. Atualização3x/dia preservada; E/F são invoices outubro, não gasto novembro. Autoridade1566811141747777680.'};expected[0]=header
 request.append({'updateCells':{'start':{'sheetId':c['sheet_id'],'rowIndex':0,'columnIndex':9},'rows':[{'values':[header]}],'fields':'userEnteredValue,note'}})
 save(B/'j-plan.json',{'source_plan':str(R/'plan.json'),'expected':expected,'requests':request})
 if '--apply'not in sys.argv:print(json.dumps({'status':'j_only_dry_run_pass','accounts':47,'requests':len(request)}));sys.exit(0)
 assert not(B/'mutation-intent.json').exists(),'reconcile_prior_intent_before_retry'
 save(B/'mutation-intent.json',{'at':datetime.now().astimezone().isoformat(),'scope':'J values/notes only, same47IDs','request_count':len(request)})
 api('POST',base+':batchUpdate',{'requests':request[:1]});canary=get();ri=next(iter(expected));actual=cell(rows(canary)[ri],9);assert actual['userEnteredValue']==expected[ri]['userEnteredValue']and actual['note']==expected[ri]['note']
 api('POST',base+':batchUpdate',{'requests':request[1:]});after=get();save(B/'after-j-write.json',after)
 assert authored(before,True)==authored(after,True),'non_J_authored_data_changed'
 for ri,value in expected.items():
  ce=cell(rows(after)[ri],9);assert ce['userEnteredValue']==value['userEnteredValue']and ce['note']==value['note']
 checks=[]
 for ri,row in enumerate(rows(after)):
  label=val(cell(row,0))
  if not isinstance(label,str)or not label.startswith('TOTAL'):continue
  subset=[p for p in plan['planned']if label.startswith('TOTAL GERAL')or('CARTÃO'in label and p['method']=='Cartão de crédito')or('LINHA'in label and p['method']=='Linha de crédito')]
  total=sum((Decimal(p['month_spend'])for p in subset),Decimal(0));ce=cell(row,9);assert ce['userEnteredValue'].get('formulaValue','').startswith('=ROUND(SUM(');assert Decimal(str(ce['effectiveValue']['numberValue']))==total
  checks.append({'row':ri+1,'label':label,'amount':str(total),'formula':ce['userEnteredValue']['formulaValue']})
 assert len(checks)==3
 out={'status':'november_j_updated_validated','authority_message_id':'1566811141747777680','source_plan':str(R/'plan.json'),'accounts':47,'header':header['userEnteredValue']['stringValue'],'collected_at':stamp,'periods':[dict(x)for x in {tuple(sorted(p['month_period'].items()))for p in plan['planned']}],'total_usd':str(sum((Decimal(p['month_spend'])for p in plan['planned']),Decimal(0))),'subtotal_checks':checks,'all47_exact_readback':True,'outside_J_authored_cells_unchanged':True,'other_tabs_authored_unchanged':True,'e_f_october_invoices_preserved':True,'payments':0,'meta_writes':0,'completed_at':datetime.now().astimezone().isoformat()}
 save(B/'receipt.json',out);print(json.dumps(out,ensure_ascii=False))
