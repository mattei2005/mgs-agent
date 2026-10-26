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
def verified_entry(r,t,c,v,receipt_path):
 aid=t['account_id']
 assert r['account_id']==aid and r['business_id']==c['business_id']and r['payments_executed']==0
 if r['status']=='accounts_list_read':
  assert '1564382301155098717'in c.get('authorization_messages',[]),'accounts_list_publication_not_authorized'
  proof=v.get('accounts_list_checks',{}).get(aid,{})
  assert proof.get('valid_billing_list')is True and proof.get('business_id')==c['business_id']and proof.get('row_account_id')==aid,'accounts_list_visual_identity_missing'
  assert proof.get('name')==t['name']and r['name']==t['name'],'accounts_list_exact_name_mismatch'
  dec=Decimal(r['amount']);assert dec>=0 and Decimal(proof['balance_usd'])==dec,'accounts_list_visual_balance_mismatch'
  assert Path(r['screenshot']).is_file();ls=Path(r['text_path']).read_text().splitlines();prefix=t['name']+' ID: '+aid+' ';matches=[l for l in ls if l.startswith(prefix)and re.search(r'\$[0-9,]+\.\d{2}',l)];assert len(matches)==1,'accounts_list_exact_row_not_unique'
  amount=re.search(r'\$([0-9,]+\.\d{2})',matches[0])[1];assert Decimal(amount.replace(',',''))==dec,'accounts_list_ax_balance_mismatch'
  source='accounts_list_current_balance';period='Current balance da linha Accounts; leitura autorizada1564382301155098717; não é valor de modal';screenshot=r['screenshot']
 elif r['status']=='current_balance_pay_now_unavailable':
  proof=v.get('disabled_balance_checks',{}).get(aid,{})
  assert proof.get('pay_now_visually_disabled')is True and proof.get('valid_billing_page')is True,'disabled_button_visual_proof_missing'
  assert proof.get('business_id')==c['business_id']and proof.get('asset_id')==aid,'disabled_identity_mismatch'
  dec=Decimal(r['amount']);assert dec>=0 and Decimal(proof['balance_usd'])==dec,'disabled_balance_visual_mismatch'
  assert r['pay_now_ax_button_count']==0 and Path(r['page']['screenshot']).is_file()
  ls=Path(r['page']['text_path']).read_text().splitlines();ai=ls.index('+ any applicable fees');amount=ls[ai-1]
  assert re.fullmatch(r'\$[0-9,]+\.\d{2}',amount)and Decimal(amount.replace('$','').replace(',',''))==dec,'disabled_balance_ax_mismatch'
  assert not re.search(r'You.re Temporarily Blocked|temporarily blocked|going too fast|Enter the 6-digit code', '\n'.join(ls),re.I),'provider_gate_not_financial_disable'
  source='current_balance_pay_now_unavailable';period=r['period'];screenshot=r['page']['screenshot']
 else:
  assert r['status']=='modal_read'and Path(r['modal']['screenshot']).is_file()
  ls=r['modal_labels'];assert 'Amount you can pay now'in ls and 'Make a payment'in ls
  amount=ls[ls.index('Amount')+1];assert re.fullmatch(r'\$[0-9,]+\.\d{2}',amount),'amount_not_explicit';dec=Decimal(amount.replace('$','').replace(',',''));assert dec>=0
  source='pay_now_modal';period=next(s for s in ls if s.startswith('Spending from '));screenshot=r['modal']['screenshot']
 return {'account_id':aid,'name':t['name'],'amount':str(dec),'currency':'USD','source':source,'period_label':period,'read_at':r['read_at'],'receipt':str(receipt_path),'screenshot':screenshot,'visual_account_verified':True}

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir');p.add_argument('--prepare',action='store_true');p.add_argument('--apply',action='store_true');p.add_argument('--verified-only',action='store_true',help='Publish only independently verified receipts; preserve every missing account value/note');p.add_argument('--insert-column-if-needed',action='store_true');a=p.parse_args();assert not(a.prepare and a.apply)
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
  assert len(allids)==len(set(allids))and set(allids)==set(c['account_ids']),'account_scope_drift';assert {x['account_id']for x in ts}==set(c['pay_now_account_ids']),'credit_line_scope_drift';return rows,ts
 B=Path(a.run_dir)if a.run_dir else REPORTS/'meta-manual-payments-runs'/('pay-now-'+datetime.now().strftime('%Y%m%dT%H%M%S%f'));B.mkdir(parents=True,exist_ok=True)
 before=api('GET',url);rows,targets=scope(before)
 if a.prepare:
  assert not(B/'targets.json').exists(),'targets_already_frozen';save(B/'targets.json',targets);save(B/'prepare-snapshot.json',before)
  surf=H/'pc1-browser-surface.json'
  if surf.exists():save(B/'pc1-surface.json',json.loads(surf.read_text()))
  print(json.dumps({'status':'prepared','run_dir':str(B),'credit_line_accounts':len(targets),'sheet_writes':0}));return
 frozen=json.loads((B/'targets.json').read_text());assert {x['account_id']:x['name']for x in frozen}=={x['account_id']:x['name']for x in targets},'credit_line_target_identity_drift';v=json.loads((B/'visual-verification.json').read_text());verified=set(v['verified_account_ids']);targetids={t['account_id']for t in targets};assert verified and verified<=targetids and len(verified)==len(v['verified_account_ids']),'visual_identity_verification_invalid';assert a.verified_only or verified==targetids,'visual_identity_verification_incomplete';entries={}
 for t in targets:
  if t['account_id']not in verified:continue
  aid=t['account_id'];rp=B/(aid+'-receipt.json');r=json.loads(rp.read_text());entries[aid]=verified_entry(r,t,c,v,rp)
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
    cell['userEnteredValue']={'stringValue':HEADER};cell['note']='Fonte H nas '+str(len(targets))+' contas de linha; '+str(len(entries))+' verificadas nesta publicação, '+str(len(targets)-len(entries))+' preservadas com timestamp anterior: Current balance da lista Accounts autorizado1564382301155098717; modal ou balance topo quando explicitamente registrados na nota. Cada nota distingue fonte e hora da leitura real. Não é limite do cartão. Nenhum pagamento executado.'
   else:
    mt=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''));label=cells[0].get('userEnteredValue',{}).get('stringValue','')
    if mt and mt[1]in entries:
     e=entries[mt[1]];cell['userEnteredValue']={'numberValue':float(Decimal(e['amount']))}
     if e['source']=='accounts_list_current_balance':
      detail='Current balance da linha Accounts: USD '+e['amount']+'. Método aprovado por Rodolfo1564382301155098717 para concluir H; nome e ID exatos da linha conferidos. Não é leitura de modal nem prova de Pay now desabilitado.'
     elif e['source']=='current_balance_pay_now_unavailable':
      detail='Current balance do topo: USD '+e['amount']+'. Pay now comprovadamente desabilitado na página válida. Usado como saldo a pagar de outubro ainda aberto conforme Rodolfo1564373157727576245; não é leitura de modal.'
     else:detail='Amount you can pay now: USD '+e['amount']+'. '+e['period_label']+'. Valor literal permitido no modal.'
     cell['note']=detail+' Fonte '+e['source']+'. Leitura PC1 autenticada: '+e['read_at']+'. Conta '+e['account_id']+'; BM '+c['business_id']+'; BM/conta e valor verificados visualmente. Não é limite do cartão. Nenhum pagamento realizado. Evidência: '+e['receipt']
    elif label.startswith('TOTAL LINHA')or label.startswith('TOTAL GERAL'):
     fv=cells[balancecol]['userEnteredValue']['formulaValue'];cell['userEnteredValue']={'formulaValue':re.sub(r'(?<![A-Za-z])'+chr(65+balancecol)+r'(?=\d)',chr(65+paycol),fv)};cell['note']='Soma H das '+str(len(targets))+' contas de linha; '+str(len(entries))+' atualizadas, '+str(len(targets)-len(entries))+' históricas preservadas: Current balance da Accounts list por1564382301155098717, ou outra fonte explicitada individualmente. Leituras sequenciais com fonte/hora individual; não é limite de cartão nem promessa de liquidação simultânea.'
    elif mt and mt[1]in targetids:
     # Partial recovery must preserve missing values AND their historical notes.
     continue
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
  if a.verified_only:
   previous=json.loads((H/'pc1-pay-now-ledger.json').read_text());save(B/'prior-pay-now-ledger.json',previous)
   allentries={**previous['accounts'],**entries}
  else:allentries=entries
  ledger_total=sum((Decimal(e['amount'])for e in allentries.values()),Decimal(0))
  save(H/'pc1-pay-now-ledger.json',{'business_id':c['business_id'],'column':HEADER,'accounts':allentries,'total_usd':str(ledger_total),'fresh_account_ids':sorted(entries),'preserved_account_ids':sorted(targetids-set(entries)),'run_dir':str(B),'published_at':datetime.now().astimezone().isoformat(),'payments_executed':0})
  receipt={'status':'pay_now_partial_updated_validated'if verified!=targetids else'pay_now_updated_validated','accounts':len(entries),'target_accounts':len(targets),'preserved_accounts':len(targetids-verified),'sum_usd':str(total),'inserted_column':not existing,'full_grid_readback':True,'other_sheet_properties_unchanged':True,'payments_executed':0,'run_dir':str(B),'completed_at':datetime.now().astimezone().isoformat()};save(B/('publication-receipt-'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json'),receipt);print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'blocked','reason':str(e)[:220],'payments_executed':0}));sys.exit(2)
