#!/usr/bin/env python3
"""Record independently visually verified PC1 card evidence; update only D."""
import argparse,copy,fcntl,json,os,re,shutil,sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from urllib.parse import quote
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
H=Path('/root/mgs-agent/data/meta-manual-payments')
def main():
 p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--verified-account-id',required=True);p.add_argument('--verified-business-id',required=True);p.add_argument('--visual-account-verified',action='store_true',required=True);a=p.parse_args()
 contract=json.loads((H/'digital-trust-workbook-contract.json').read_text());rp=Path(a.receipt);rec=json.loads(rp.read_text());aid=a.verified_account_id
 assert a.visual_account_verified and aid==rec['account_requested']and aid in contract['account_ids']and a.verified_business_id==contract['business_id'];assert rec['status']=='read'and Path(rec['screenshot']).is_file()
 # The caller must actually inspect the screenshot; flags never replace that step.
 text=Path(rec['text_path']).read_text();marker='\nDate\nPayment method\nAmount\nStatus\n';events=[]
 if marker in text:
  ls=[x.strip()for x in text.split(marker,1)[1].split('\nView all activity',1)[0].splitlines()if x.strip()]
  for i in range(0,len(ls)-3,4):
   dt,method,amount,status=ls[i:i+4]
   if not re.fullmatch(r'[A-Za-z]{3} \d{1,2}, \d{4}',dt):break
   datetime.strptime(dt,'%b %d, %Y');events.append({'date':dt,'method':method,'amount':str(Decimal(amount.replace('$','').replace(',',''))),'status':status})
 cards=[e for e in events if e['status']=='Paid'and re.fullmatch(r'(MasterCard|Mastercard|American Express|Visa|Discover)\s+·+\s+\d{4}',e['method'])]
 if not cards and events:raise RuntimeError('no_card_in_visible_history_use_View_all_activity_before_recording')
 if not events:assert rec.get('no_recent_spending_message')or 'You have no recent spending.'in text,'no_verified_empty_history_state'
 latest=cards[0]if cards else None
 evidence=rp.parent/('verified-'+aid+'.png');shutil.copy2(rec['screenshot'],evidence);os.chmod(evidence,0o600)
 entry={'account_id':aid,'business_id':a.verified_business_id,'ui_url_account_id_verified':True,'read_at':rec.get('read_at')or datetime.fromtimestamp(rp.stat().st_mtime).astimezone().isoformat(),'screenshot':str(evidence),'receipt':str(rp),'rows':events,'latest_card':latest,'status':'verified_card'if latest else'no_charge_located','no_recent_spending_message':not bool(events)}
 g.load_env();assert all(os.getenv(k)=='service_account'for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']);sa=g.load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'and sa['project_id']=='mgs-core-prod';tok=g.service_account_access_token()
 root='https://sheets.googleapis.com/v4/spreadsheets/'+contract['spreadsheet_id'];rng="'"+contract['sheet_title']+"'!A:H";url=root+'?includeGridData=true&ranges='+quote(rng,safe='')+'&fields=sheets(properties,basicFilter,bandedRanges,data(rowData(values(userEnteredValue,userEnteredFormat,note))))'
 def api(m,u,d=None):
  s,b=g.api_json(m,u,tok,d,quota_project='mgs-core-prod');assert s==200;return b
 with (H/'writer.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);before=api('GET',url);expected=copy.deepcopy(before);rows=expected['sheets'][0]['data'][0]['rowData'];matches=[]
  for i,r in enumerate(rows):
   c=r.get('values',[])
   if c and re.search(r'^ID da conta: '+re.escape(aid)+r'\b',c[0].get('note','')):matches.append(i)
  assert len(matches)==1;i=matches[0];c=rows[i]['values'][3];c['userEnteredFormat'].pop('backgroundColor',None);c['userEnteredFormat'].pop('backgroundColorStyle',None)
  if latest:c['userEnteredValue']={'numberValue':float(Decimal(latest['amount']))};c['note']=f"Última cobrança no cartão: USD {latest['amount']}; {latest['method']}; {latest['date']}; Paid. Leitura PC1 autenticada em {entry['read_at']}; URL/BM/conta verificadas visualmente. Advertising credit e falhas excluídos. Fonte: {rp}. Instrumento histórico não é necessariamente o default atual."
  else:c.pop('userEnteredValue',None);c['note']='Sem cobrança localizada na leitura PC1 de '+entry['read_at']+'. UI sem gastos recentes; não é prova de inexistência universal de histórico. Fonte '+str(rp)
  api('POST',root+':batchUpdate',{'requests':[{'updateCells':{'start':{'sheetId':contract['sheet_id'],'rowIndex':i,'columnIndex':3},'rows':[{'values':[c]}],'fields':'userEnteredValue,userEnteredFormat,note'}}]});assert api('GET',url)==expected
  ledger=json.loads((H/'pc1-card-ledger.json').read_text());ledger['accounts'][aid]=entry;tmp=H/'pc1-card-ledger.next';tmp.write_text(json.dumps(ledger,ensure_ascii=False,indent=2));os.chmod(tmp,0o600);os.replace(tmp,H/'pc1-card-ledger.json');assert json.loads((H/'pc1-card-ledger.json').read_text())['accounts'][aid]==entry
 print(json.dumps({'status':'pc1_proof_recorded_and_sheet_readback_pass','account_id':aid,'latest_card':latest,'meta_writes':0,'payments_executed':0},ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'blocked','error':str(e)[:200]},ensure_ascii=False));sys.exit(2)
