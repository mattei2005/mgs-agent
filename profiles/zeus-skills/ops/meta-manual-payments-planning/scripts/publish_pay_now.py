#!/usr/bin/env python3
"""Prepare/readback or narrowly publish independently verified PC1 Pay now evidence."""
import argparse,copy,fcntl,json,os,re,sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from urllib.parse import quote
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
H=Path('/root/mgs-agent/data/meta-manual-payments');REPORTS=Path('/root/mgs-agent/reports');HEADER='Disponível para pagar no cartão (Pay now)'
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.next');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2));os.chmod(tmp,0o600);os.replace(tmp,p)
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir');p.add_argument('--prepare',action='store_true');p.add_argument('--apply',action='store_true');p.add_argument('--insert-column-if-needed',action='store_true');a=p.parse_args();assert not(a.prepare and a.apply)
 c=json.loads((H/'digital-trust-workbook-contract.json').read_text());assert c['business_id']=='155263197283282'and c['payments_authorized']is False
 g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']);sa=g.load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['project_id']=='mgs-core-prod';tok=g.service_account_access_token()
 def api(m,u,d=None):
  status,data=g.api_json(m,u,tok,d,quota_project='mgs-core-prod');assert status==200,'google_http_'+str(status);return data
 root='https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id'];sid=c['sheet_id'];rng="'"+c['sheet_title']+"'!A:K";url=root+'?includeGridData=true&ranges='+quote(rng,safe='')+'&fields=sheets(properties,basicFilter,bandedRanges,data(rowData(values(userEnteredValue,userEnteredFormat,note))))'
 drive=api('GET','https://www.googleapis.com/drive/v3/files/'+c['spreadsheet_id']+'?supportsAllDrives=true&fields=trashed,capabilities(canEdit)');assert not drive.get('trashed')and drive['capabilities']['canEdit']
 def scope(book):
  sh=book['sheets'][0];assert sh['properties']['sheetId']==sid;rows=sh['data'][0]['rowData'];allids=[];ts=[]
  for i,r in enumerate(rows):
   cells=r.get('values',[])
   if cells and(mt:=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''))):
    allids.append(mt[1])
    if cells[1]['userEnteredValue']['stringValue']=='Linha de crédito':ts.append({'account_id':mt[1],'name':cells[0]['userEnteredValue']['stringValue'],'row_index':i})
  assert len(allids)==len(set(allids))and set(allids)==set(c['account_ids']),'account_scope_drift';assert len(ts)==39,'credit_line_scope_drift';return rows,ts
 B=Path(a.run_dir)if a.run_dir else REPORTS/'meta-manual-payments-runs'/('pay-now-'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));B.mkdir(parents=True,exist_ok=True)
 before=api('GET',url);rows,targets=scope(before)
 if a.prepare:
  assert not(B/'targets.json').exists(),'targets_already_frozen';save(B/'targets.json',targets);save(B/'prepare-snapshot.json',before)
  surf=H/'pc1-browser-surface.json'
  if surf.exists():save(B/'pc1-surface.json',json.loads(surf.read_text()))
  print(json.dumps({'status':'prepared','run_dir':str(B),'credit_line_accounts':len(targets),'sheet_writes':0}));return
 frozen=json.loads((B/'targets.json').read_text());assert {x['account_id']:x['name']for x in frozen}=={x['account_id']:x['name']for x in targets},'credit_line_target_identity_drift';v=json.loads((B/'visual-verification.json').read_text());assert set(v['verified_account_ids'])=={t['account_id']for t in targets}and len(v['verified_account_ids'])==len(targets),'visual_identity_verification_incomplete';entries={}
 for t in targets:
  aid=t['account_id'];r=json.loads((B/(aid+'-receipt.json')).read_text());assert r['status']=='modal_read'and r['account_id']==aid and r['business_id']==c['business_id']and r['payments_executed']==0;assert Path(r['modal']['screenshot']).is_file();ls=r['modal_labels'];assert 'Amount you can pay now'in ls and 'Make a payment'in ls;amount=ls[ls.index('Amount')+1];assert re.fullmatch(r'\$[0-9,]+\.\d{2}',amount),'amount_not_explicit';dec=Decimal(amount.replace('$','').replace(',',''));assert dec>=0;period=next(s for s in ls if s.startswith('Spending from '));entries[aid]={'account_id':aid,'name':t['name'],'amount':str(dec),'currency':'USD','period_label':period,'read_at':r['read_at'],'receipt':str(B/(aid+'-receipt.json')),'screenshot':r['modal']['screenshot'],'visual_account_verified':True}
 total=sum((Decimal(x['amount'])for x in entries.values()),Decimal(0));heads=[x.get('userEnteredValue',{}).get('stringValue','')for x in rows[0]['values']];existing=HEADER in heads;paycol=heads.index(HEADER)if existing else 5;balancecol=heads.index('Saldo a pagar');width=len(heads)
 assert existing or heads[5:7]==['Saldo a pagar','Total já gasto em outubro'],'unexpected_schema'
 if not a.apply:print(json.dumps({'status':'pay_now_plan_pass','accounts':len(entries),'sum_usd':str(total),'insert_required':not existing,'sheet_writes':0}));return
 with (H/'writer.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);assert api('GET',url)==before,'concurrent_sheet_change';backup=B/('pre-write-'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json');save(backup,before);meta=api('GET',root+'?fields=sheets.properties');save(B/('sheet-properties-'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json'),meta)
  if not existing:
   assert a.insert_column_if_needed and '1563981039230255186'in c.get('authorization_messages',[]),'column_insertion_not_authorized'
   api('POST',root+':batchUpdate',{'requests':[{'insertDimension':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':5,'endIndex':6},'inheritFromBefore':True}}]})
   inserted=api('GET',url);irows,_=scope(inserted);save(B/'post-insert-before-values.json',inserted)
   # Sheet auto-adjusts old F/G formulas. Prove every existing value/note/format preserved by mapping.
   def shifted(cell):
    out=copy.deepcopy(cell);uv=out.get('userEnteredValue',{})
    if 'formulaValue'in uv:uv['formulaValue']=re.sub(r'(?<![A-Za-z])([FG])(?=\d)',lambda m:chr(ord(m[1])+1),uv['formulaValue'])
    return out
   for i,r in enumerate(rows):
    for col,cell in enumerate(r.get('values',[])):
     nc=col if col<5 else col+1;actual=irows[i].get('values',[]);assert shifted(cell)==(actual[nc]if nc<len(actual)else{}),'existing_cell_not_preserved_after_insert_'+str((i,col))
   before=inserted;rows=irows;width+=1;balancecol+=1
  expected=copy.deepcopy(before);erows=expected['sheets'][0]['data'][0]['rowData'];req=[]
  for i,r in enumerate(erows):
   cells=r.setdefault('values',[])
   while len(cells)<width:cells.append({})
   cell=copy.deepcopy(cells[balancecol]);cell.pop('userEnteredValue',None);cell.pop('note',None)
   if i==0 or(cells[0].get('userEnteredValue',{}).get('stringValue')=='Nome da conta'and cells[1].get('userEnteredValue',{}).get('stringValue')=='Forma de pagamento'):
    cell['userEnteredValue']={'stringValue':HEADER};cell['note']='Fonte: modal Make a payment > Amount you can pay now, no PC1; somente as 39 contas de linha de crédito. Cada nota informa período e hora da leitura real. Não é current balance, invoice fechada ou limite disponível no emissor do cartão. Nenhum pagamento executado.'
   else:
    mt=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''));label=cells[0].get('userEnteredValue',{}).get('stringValue','')
    if mt and mt[1]in entries:
     e=entries[mt[1]];cell['userEnteredValue']={'numberValue':float(Decimal(e['amount']))};cell['note']='Amount you can pay now: USD '+e['amount']+'. '+e['period_label']+'. Leitura PC1 autenticada: '+e['read_at']+'. Conta '+e['account_id']+'; BM '+c['business_id']+'; URL/conta e valor verificados visualmente. É o valor permitido neste modal, não current balance nem limite do cartão. Nenhum pagamento realizado. Fonte: '+e['receipt']
    elif label.startswith('TOTAL LINHA')or label.startswith('TOTAL GERAL'):
     fv=cells[balancecol]['userEnteredValue']['formulaValue'];cell['userEnteredValue']={'formulaValue':re.sub(r'(?<![A-Za-z])'+chr(65+balancecol)+r'(?=\d)',chr(65+paycol),fv)};cell['note']='Soma dos valores literalmente exibidos no Pay now das 39 contas de linha de crédito. Leituras sequenciais com horário individual nas notas; não é limite de cartão nem promessa de liquidação simultânea.'
    elif mt:cell['note']='Não coletado: esta coluna foi solicitada somente para as contas cuja forma de pagamento é linha de crédito. Vazio não significa zero.'
   cells[paycol]=cell;req.append({'updateCells':{'start':{'sheetId':sid,'rowIndex':i,'columnIndex':paycol},'rows':[{'values':[cell]}],'fields':'userEnteredValue,userEnteredFormat,note'}})
  # Structural width is explicit; only the authorized column changes.
  api('POST',root+':batchUpdate',{'requests':req});after=api('GET',url)
  def normalized(book):
   book=copy.deepcopy(book)
   for sheet in book.get('sheets',[]):
    for data in sheet.get('data',[]):
     for row in data.get('rowData',[]):
      cells=row.get('values',[])
      while cells and cells[-1]=={}:cells.pop()
      if not cells:row.pop('values',None)
   return book
  assert normalized(after)==normalized(expected),'pay_now_full_grid_readback_mismatch'
  if not existing:api('POST',root+':batchUpdate',{'requests':[{'updateDimensionProperties':{'range':{'sheetId':sid,'dimension':'COLUMNS','startIndex':5,'endIndex':6},'properties':{'pixelSize':300},'fields':'pixelSize'}}]})
  am=api('GET',root+'?fields=sheets.properties');bm={s['properties']['sheetId']:s['properties']for s in meta['sheets']};nm={s['properties']['sheetId']:s['properties']for s in am['sheets']};assert set(bm)==set(nm)
  for k in bm:
   exp=copy.deepcopy(bm[k])
   if k==sid and not existing:exp['gridProperties']['columnCount']+=1
   assert exp==nm[k],'sheet_properties_changed_unexpectedly'
  save(H/'pc1-pay-now-ledger.json',{'business_id':c['business_id'],'column':HEADER,'accounts':entries,'total_usd':str(total),'run_dir':str(B),'published_at':datetime.now().astimezone().isoformat(),'payments_executed':0})
  receipt={'status':'pay_now_updated_validated','accounts':len(entries),'sum_usd':str(total),'inserted_column':not existing,'full_grid_readback':True,'other_sheet_properties_unchanged':True,'payments_executed':0,'run_dir':str(B),'completed_at':datetime.now().astimezone().isoformat()};save(B/('publication-receipt-'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json'),receipt);print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'blocked','reason':str(e)[:220],'payments_executed':0}));sys.exit(2)
