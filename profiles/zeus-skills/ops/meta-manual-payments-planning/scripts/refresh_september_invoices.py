#!/usr/bin/env python3
"""Read BM invoices, join exact account IDs and publish September outstanding balances only."""
import argparse,copy,fcntl,json,os,re,sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from urllib.parse import quote
import requests
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
H=Path('/root/mgs-agent/data/meta-manual-payments');ROOT=Path('/root/mgs-agent')
INV='Invoice';SEP='Setembro — saldo em aberto'
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2));os.chmod(tmp,0o600);os.replace(tmp,p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--insert-columns-if-needed',action='store_true');ap.add_argument('--run-dir');a=ap.parse_args();c=json.loads((H/'digital-trust-workbook-contract.json').read_text());assert c['payments_authorized']is False
 g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']);sa=g.load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['project_id']=='mgs-core-prod';gt=g.service_account_access_token();obj=g._op_item_json(c['meta_token_item_id'],'MGS Conteúdo');mt=next(f['value']for label in ['credential','token']for f in obj.get('fields',[])if f.get('value')and(f.get('id','').lower()==label or f.get('label','').lower()==label));sess=requests.Session()
 def graph(path,params):
  try:res=sess.get('https://graph.facebook.com/v26.0/'+path,params={**params,'access_token':mt},timeout=60)
  except requests.RequestException as exc:raise RuntimeError('meta_transport_'+type(exc).__name__)from None
  d=res.json();assert res.status_code==200 and'error'not in d,'meta_http_'+str(res.status_code)+'_code_'+str(d.get('error',{}).get('code'));return d
 def api(method,url,payload=None):
  status,d=g.api_json(method,url,gt,payload,quota_project='mgs-core-prod');assert status==200,'google_http_'+str(status);return d
 assert graph('me',{'fields':'id'})['id']==c['meta_actor_id'];params={'fields':'id,invoice_id,ad_account_ids,currency,amount,amount_due,payment_status,invoice_date,billing_period,due_date','limit':100};invoices=[];pages=0
 while True:
  data=graph(c['business_id']+'/business_invoices',params);invoices.extend(data.get('data',[]));pages+=1
  if not data.get('paging',{}).get('next'):break
  params['after']=data['paging']['cursors']['after'];assert pages<100,'pagination_limit'
 assert len(invoices)==len({x['id']for x in invoices}),'duplicate_invoice';september=[x for x in invoices if x.get('billing_period')=='2026-09-01'];by={};open_all=[]
 for x in september:
  assert x['currency']=='USD'and x['amount_due']['currency']=='USD';assert len(x['ad_account_ids'])==1,'shared_invoice_needs_exact_allocation';aid=x['ad_account_ids'][0];assert aid not in by,'multiple_september_invoices_same_account';assert re.fullmatch(r'\d+',x['invoice_id']);due=Decimal(x['amount_due']['amount_in_hundredths'])/100;assert due>=0
  if x['payment_status']=='Paid':assert due==0,'paid_invoice_has_nonzero_due'
  by[aid]={'invoice':x['invoice_id'],'due':str(due),'original':str(Decimal(x['amount'])/100),'status':x['payment_status'],'due_date':x['due_date'],'billing_period':x['billing_period']}
  if due>0:open_all.append(aid)
 B=Path(a.run_dir)if a.run_dir else ROOT/'reports/meta-manual-payments-runs'/('september-'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));B.mkdir(parents=True,exist_ok=True);stamp=datetime.now().astimezone().isoformat();outside=[aid for aid in open_all if aid not in c['account_ids']];outside_info=[]
 for aid in outside:
  act=graph('act_'+aid,{'fields':'account_id,name,currency,business'});assert act['account_id']==aid and act['business']['id']==c['business_id']and act['currency']=='USD';outside_info.append({'account_id':aid,'name':act['name'],**by[aid]})
 bm_total=sum((Decimal(by[aid]['due'])for aid in open_all),Decimal(0));tab_total=sum((Decimal(v['due'])for aid,v in by.items()if aid in c['account_ids']),Decimal(0));summary={'collected_at':stamp,'all_bm_invoices':len(invoices),'pages':pages,'september_invoices':len(september),'unpaid_bm':len(open_all),'unpaid_in_current_tab':sum(aid in c['account_ids']for aid in open_all),'bm_total_usd':str(bm_total),'tab_total_usd':str(tab_total),'outside_current_tab':outside_info,'by_account':by};save(B/'invoice-collection.json',summary)
 root='https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id'];sid=c['sheet_id'];url=root+'?includeGridData=true&ranges='+quote("'"+c['sheet_title']+"'!A:K",safe='')+'&fields=sheets(properties,basicFilter,bandedRanges,data(rowData(values(userEnteredValue,userEnteredFormat,note))))';caps=api('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=trashed,capabilities(canEdit)');assert not caps.get('trashed')and caps['capabilities']['canEdit'];before=api('GET',url);assert before['sheets'][0]['properties']['sheetId']==sid;rows=before['sheets'][0]['data'][0]['rowData'];ids=[re.search(r'^ID da conta: (\d+)\b',r['values'][0].get('note',''))[1]for r in rows if r.get('values')and re.search(r'^ID da conta: (\d+)\b',r['values'][0].get('note',''))];assert len(ids)==len(set(ids))and set(ids)==set(c['account_ids']);heads=[x.get('userEnteredValue',{}).get('stringValue','')for x in rows[0]['values']];existing=heads[4:6]==[INV,SEP];assert existing or(len(heads)==8 and heads[4].startswith('Média diária')),'unexpected_schema'
 if not a.apply:print(json.dumps({'status':'invoice_plan_pass','run_dir':str(B),'columns_insert_required':not existing,**{k:summary[k]for k in ['unpaid_bm','unpaid_in_current_tab','bm_total_usd','tab_total_usd','outside_current_tab']}},ensure_ascii=False));return
 with (H/'writer.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);assert api('GET',url)==before,'concurrent_sheet_edit';save(B/'before.json',before);meta=api('GET',root+'?fields=sheets.properties');save(B/'sheet-properties-before.json',meta)
  if not existing:
   assert a.insert_columns_if_needed,'insertion_flag_required';save(B/'insertion-intent.json',{'sheet_id':sid,'start':4,'end':6,'old_headers':heads,'source_message':'1564022485366734969'})
   api('POST',root+':batchUpdate',{'requests':[{'insertDimension':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':4,'endIndex':6},'inheritFromBefore':True}}]});inserted=api('GET',url);save(B/'post-insert.json',inserted);newrows=inserted['sheets'][0]['data'][0]['rowData']
   for i,row in enumerate(rows):
    for col,cell in enumerate(row.get('values',[])):
     exp=copy.deepcopy(cell);uv=exp.get('userEnteredValue',{})
     if 'formulaValue'in uv:uv['formulaValue']=re.sub(r'(?<![A-Za-z])([E-Z])(?=\d)',lambda m:chr(ord(m[1])+2),uv['formulaValue'])
     ncol=col if col<4 else col+2;actual=newrows[i].get('values',[]);assert exp==(actual[ncol]if ncol<len(actual)else{}),'prior_cell_not_preserved_'+str((i,col))
   before=inserted;rows=newrows
  expected=copy.deepcopy(before);erows=expected['sheets'][0]['data'][0]['rowData'];req=[]
  for i,row in enumerate(erows):
   cells=row.setdefault('values',[])
   while len(cells)<10:cells.append({})
   label=cells[0].get('userEnteredValue',{}).get('stringValue','');match=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''));ic=copy.deepcopy(cells[6]);sc=copy.deepcopy(cells[6]);ic.pop('userEnteredValue',None);sc.pop('userEnteredValue',None);ic.pop('note',None);sc.pop('note',None);ic.setdefault('userEnteredFormat',{})['numberFormat']={'type':'TEXT'}
   if label=='Nome da conta'and cells[1].get('userEnteredValue',{}).get('stringValue')=='Forma de pagamento':
    ic['userEnteredValue']={'stringValue':INV};sc['userEnteredValue']={'stringValue':SEP};ic['note']='Número da invoice de competência setembro/2026, vinculado ao ID exato da conta. Paid continua identificado para referência; status/valor original/vencimento na nota. Fonte Meta business_invoices.';sc['note']='Saldo ainda em aberto das invoices de setembro/2026, não gasto de setembro nem valor original de invoice já paga. Consulta '+stamp+'. Aba: '+str(summary['unpaid_in_current_tab'])+' invoices abertas, USD '+str(tab_total)+'. BM inteira: '+str(len(open_all))+' abertas, USD '+str(bm_total)+'. '+str(len(outside))+' contas com invoice aberta fora do recorte atual de47 contas; não foram reinseridas sem nova autorização.'
   elif match:
    aid=match[1];iv=by.get(aid);method=cells[1]['userEnteredValue']['stringValue']
    if iv:
     ic['userEnteredValue']={'stringValue':iv['invoice']};sc['userEnteredValue']={'numberValue':float(Decimal(iv['due']))};note='Invoice '+iv['invoice']+'; setembro/2026; status '+iv['status']+'; valor original USD '+iv['original']+'; saldo em aberto USD '+iv['due']+'; vencimento '+iv['due_date']+'. Conta '+aid+'. Consulta Meta Graph business_invoices: '+stamp+'. Não é Pay now/current balance. Fonte '+str(B/'invoice-collection.json');ic['note']=note;sc['note']=note
    elif method=='Linha de crédito':
     sc['userEnteredValue']={'numberValue':0};ic['note']='Nenhuma invoice de setembro/2026 vinculada a esta conta na enumeração completa da BM em '+stamp;sc['note']=ic['note']+'. Nenhum saldo de invoice de setembro localizado; não é gasto mensal nem current balance.'
    else:ic['note']='Sem invoice de setembro vinculada a esta conta na BM; pagamento padrão por cartão.';sc['note']=ic['note']
   elif label.startswith('TOTAL LINHA')or label.startswith('TOTAL GERAL')or(label.startswith('TOTAL CARTÃO')and any(r.get('values')and r['values'][0].get('note','').startswith('ID da conta: ')and r['values'][1].get('userEnteredValue',{}).get('stringValue')=='Cartão de crédito'and'numberValue'in r['values'][5].get('userEnteredValue',{})for r in erows)):
    fv=cells[6]['userEnteredValue']['formulaValue'];sc['userEnteredValue']={'formulaValue':re.sub(r'(?<![A-Za-z])G(?=\d)','F',fv)};sc['note']='Total de saldos em aberto de setembro apenas das contas existentes nesta aba; exclui '+str(len(outside))+' contas fora do recorte. Consulta '+stamp
   if c.get('september_owner_payment_report')and(label=='Nome da conta'or(match and Decimal(by.get(match[1],{}).get('due','0'))>0)):
    sc['note']=sc.get('note','')+' Pagamento informado por Rodolfo na mensagem1564115318887161857: invoices de setembro pagas na quinta-feira; baixa ainda pendente de confirmação da Meta quando amount_due permanece maior que zero. Nenhum novo pagamento autorizado.'
   cells[4:6]=[ic,sc];req.append({'updateCells':{'start':{'sheetId':sid,'rowIndex':i,'columnIndex':4},'rows':[{'values':[ic,sc]}],'fields':'userEnteredValue,userEnteredFormat,note'}})
  api('POST',root+':batchUpdate',{'requests':req});after=api('GET',url)
  def normalize(book):
   v=copy.deepcopy(book)
   for sh in v['sheets']:
    for data in sh.get('data',[]):
     for row in data.get('rowData',[]):
      cells=row.get('values',[])
      while cells and cells[-1]=={}:cells.pop()
      if not cells:row.pop('values',None)
   return v
  assert normalize(after)==normalize(expected),'invoice_full_grid_readback_mismatch';am=api('GET',root+'?fields=sheets.properties');bm={x['properties']['sheetId']:x['properties']for x in meta['sheets']};nm={x['properties']['sheetId']:x['properties']for x in am['sheets']};assert set(bm)==set(nm)
  for k in bm:
   exp=copy.deepcopy(bm[k])
   if k==sid and not existing:exp['gridProperties']['columnCount']+=2
   assert exp==nm[k],'other_sheet_properties_changed'
  if not existing:api('POST',root+':batchUpdate',{'requests':[{'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':4,'endIndex':5},'properties':{'pixelSize':125},'fields':'pixelSize'}},{'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':5,'endIndex':6},'properties':{'pixelSize':190},'fields':'pixelSize'}}]})
  save(H/'september-invoice-ledger.json',summary);receipt={'status':'september_invoices_updated_validated','accounts':len(ids),'new_columns':'E Invoice; F Setembro — saldo em aberto','unpaid_in_tab':summary['unpaid_in_current_tab'],'tab_due_usd':str(tab_total),'unpaid_bm':len(open_all),'bm_due_usd':str(bm_total),'outside_accounts':outside_info,'full_grid_readback':True,'prior_cells_preserved':True,'payments_executed':0,'run_dir':str(B)};save(B/'receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'blocked','error':str(e)[:220],'payments_executed':0}));sys.exit(2)
