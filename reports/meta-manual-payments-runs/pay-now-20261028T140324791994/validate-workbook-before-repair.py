#!/usr/bin/env python3
"""Read-only schema/source-note/financial readback, supports approved seven/eight columns."""
import argparse,json,os,re,sys
from collections import Counter
from decimal import Decimal
from urllib.parse import quote,urlparse,parse_qs
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g

def money(v):return Decimal(str(v)).quantize(Decimal('.01'))
def numeric(v):return isinstance(v,(int,float))and not isinstance(v,bool)

def main():
 p=argparse.ArgumentParser();p.add_argument('--spreadsheet-id',required=True);p.add_argument('--sheet-id',type=int,required=True);p.add_argument('--business-id',required=True);a=p.parse_args()
 assert re.fullmatch(r'[A-Za-z0-9_-]+',a.spreadsheet_id)and a.sheet_id>=0 and a.business_id.isdigit(),'invalid_target_identifier'
 g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']);sa=g.load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['project_id']=='mgs-core-prod';t=g.service_account_access_token()
 def get(u):
  s,d=g.api_json('GET',u,t,quota_project='mgs-core-prod');assert s==200,'read_http_'+str(s);return d
 caps=get('https://www.googleapis.com/drive/v3/files/'+a.spreadsheet_id+'?supportsAllDrives=true&fields=trashed,capabilities(canEdit)');assert not caps.get('trashed')and caps['capabilities']['canEdit']
 root='https://sheets.googleapis.com/v4/spreadsheets/'+a.spreadsheet_id;meta=get(root+'?fields=sheets.properties');matches=[s['properties']for s in meta['sheets']if s['properties']['sheetId']==a.sheet_id];assert len(matches)==1
 rng="'"+matches[0]['title'].replace("'","''")+"'!A:J";enc=quote(rng,safe='!:');forms=get(root+'/values/'+enc+'?valueRenderOption=FORMULA')['values'];vals=get(root+'/values/'+enc+'?valueRenderOption=UNFORMATTED_VALUE')['values'];grid=get(root+'?includeGridData=true&ranges='+quote(rng,safe='')+'&fields=sheets(data(rowData(values(note,userEnteredFormat(textFormat.link,numberFormat)))))')['sheets'][0]['data'][0]['rowData']
 september=len(forms[0])==10;pay=len(forms[0])in (8,10);expected=['Nome da conta','Forma de pagamento','Cartão usado como default','Última cobrança no cartão','Média diária','Saldo a pagar','Total']
 if pay:expected.insert(5,'Disponível para pagar no cartão')
 if september:
  month_headers=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];assert forms[0][5]in [m+' — saldo em aberto'for m in month_headers],'invoice_period_header_invalid';expected[4:4]=['Invoice',forms[0][5]]
 assert len(forms[0])==len(expected)and all(str(v).startswith(pre)for v,pre in zip(forms[0],expected)),'header_schema_mismatch'
 width=len(expected);paycol=7 if september else 5;metrics=(6 if september else 4,width-2,width-1);special=((paycol,)if pay else())+((5,)if september else());financial=tuple(sorted(metrics+special));assert len(forms)==len(vals)
 accounts=[];ids=set();groups=Counter();totals=[];currencies=set()
 for i,row in enumerate(vals):
  row=row+['']*(width-len(row));assert not any(isinstance(v,str)and v.startswith(('#REF!','#VALUE!','#DIV/0!','#ERROR!','#N/A'))for v in row),'formula_error'
  cells=grid[i].get('values',[])if i<len(grid)else[];note=cells[0].get('note','')if cells else'';m=re.search(r'^ID da conta: (\d+)\b',note)
  if m:
   aid=m[1];assert aid not in ids,'duplicate_account_id';ids.add(aid);link=cells[0].get('userEnteredFormat',{}).get('textFormat',{}).get('link',{}).get('uri','');u=urlparse(link);q=parse_qs(u.query);assert 'billing_hub/accounts/details'in u.path and q.get('asset_id')==[aid]and q.get('business_id')==[a.business_id],'billing_link_mismatch'
   cs=[]
   for c in financial:
    pat=cells[c].get('userEnteredFormat',{}).get('numberFormat',{}).get('pattern','');cm=re.search(r'"([A-Z]{3})"',pat);assert cm,'financial_currency_format_missing';cs.append(cm[1])
   assert len(set(cs))==1,'row_currency_mismatch';currencies.add(cs[0]);assert all(numeric(row[c])for c in metrics),'financial_value_missing'
   if pay:
    if row[1]=='Linha de crédito':
     sn=cells[paycol].get('note','');modal='Amount you can pay now'in sn;disabled=all(x in sn for x in ['current_balance_pay_now_unavailable','1564373157727576245','Pay now comprovadamente desabilitado','Leitura PC1 autenticada:'])
     listing=all(x in sn for x in ['accounts_list_current_balance','1564382301155098717','Current balance da linha Accounts:','Leitura PC1 autenticada:'])
     assert numeric(row[paycol])and(modal or disabled or listing),'credit_line_pay_now_missing_or_no_source_note'
    else:assert row[paycol]=='','pay_now_scope_includes_unrequested_card_account'
   if september:
    if row[1]=='Linha de crédito':assert numeric(row[5]),'september_due_missing'
    if row[4]!='':assert re.fullmatch(r'\d+',str(row[4]))and'invoice'in cells[4].get('note','').lower(),'invoice_identity_or_source_missing'
   accounts.append({'row':i+1,'id':aid,'method':row[1],'values':row});groups[row[1]]+=1
  elif str(row[0]).startswith('TOTAL'):
   for c in financial:
    if c in special and row[0]=='TOTAL CARTÃO DE CRÉDITO'and not(c==5 and september and any(x['method']=='Cartão de crédito'and numeric(x['values'][5])for x in accounts)):assert row[c]=='';continue
    assert len(forms[i])>c and str(forms[i][c]).startswith('=ROUND(SUM('),'total_formula_missing_round_sum'
   totals.append(row)
 assert accounts and totals and len(currencies)==1,'empty_or_mixed_currency_scope'
 grand=[r for r in totals if str(r[0]).startswith('TOTAL GERAL')];assert len(grand)==1
 for c in financial:assert money(grand[0][c])==sum((money(x['values'][c])for x in accounts if x['values'][c]!=''),Decimal(0)),'grand_total_mismatch_'+str(c)
 for group,label in [('Cartão de crédito','TOTAL CARTÃO DE CRÉDITO'),('Linha de crédito','TOTAL LINHA DE CRÉDITO')]:
  if not groups[group]:continue
  sub=[r for r in totals if r[0]==label];assert len(sub)==1,'subtotal_not_unique'
  for c in financial:
   if c in special and group=='Cartão de crédito'and not(c==5 and september and any(x['method']==group and numeric(x['values'][5])for x in accounts)):continue
   assert money(sub[0][c])==sum((money(x['values'][c])for x in accounts if x['method']==group),Decimal(0)),'subtotal_mismatch'
 contract_path='/root/mgs-agent/data/meta-manual-payments/digital-trust-workbook-contract.json'
 from pathlib import Path
 contract=json.loads(Path(contract_path).read_text())
 if a.spreadsheet_id==contract['spreadsheet_id']and a.sheet_id==contract['sheet_id']:assert ids==set(contract['account_ids']),'contract_account_ids_mismatch'
 cards=[x for x in accounts if x['method']=='Cartão de crédito'];print(json.dumps({'status':'snapshot_readback_pass','spreadsheet_id':a.spreadsheet_id,'sheet_id':a.sheet_id,'business_id':a.business_id,'currency':next(iter(currencies)),'accounts':len(accounts),'groups':dict(groups),'card_charge_values_present':sum(numeric(x['values'][3])for x in cards),'card_charge_blank_rows':[x['row']for x in cards if x['values'][3]==''],'totals_validated_columns':[chr(65+c)for c in financial],'pay_now_values_present':sum(numeric(x['values'][paycol])for x in accounts)if pay else 0,'september_due_usd':str(money(grand[0][5]))if september else None,'all_account_billing_links_checked':True,'historical_instrument_not_revalidated_by_this_script':True,'google_write_calls':0,'meta_calls':0,'payments_executed':0},ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'blocked','reason':str(e)[:200],'payments_executed':0}));sys.exit(2)
