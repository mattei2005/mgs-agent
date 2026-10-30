import sys,json,re,os,subprocess
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from urllib.parse import quote
from collections import Counter
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
H=Path('/root/mgs-agent/data/meta-manual-payments')
B=Path(__file__).parent
M=Path('/root/mgs-agent/reports/meta-manual-payments-runs/20261029T213631734337')
c=json.loads((H/'digital-trust-workbook-contract.json').read_text())
p=json.loads((M/'plan.json').read_text())
g.load_env();assert all(os.getenv(k)=='service_account' for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE'])
sa=g.load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'
tok=g.service_account_access_token()
def api(url):
 s,d=g.api_json('GET',url,tok,quota_project='mgs-core-prod');assert s==200;return d
root='https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']
meta=api(root+'?fields=sheets.properties')
book=api(root+'?includeGridData=true&ranges='+quote("'"+c['sheet_title']+"'!A:K",safe='')+'&fields=sheets(properties,data(rowData(values(userEnteredValue,effectiveValue,userEnteredFormat,effectiveFormat,note))))')
assert book['sheets'][0]['properties']['sheetId']==c['sheet_id']
rows=book['sheets'][0]['data'][0]['rowData']; live={}
for row in rows:
 cells=row.get('values',[])
 if cells and (m:=re.search(r'^ID da conta: (\d+)\b',cells[0].get('note',''))):
  assert m[1] not in live;live[m[1]]=cells
assert set(live)==set(c['account_ids']) and len(live)==47
hv=json.loads((B/'visual-verification.json').read_text());hl=json.loads((H/'pc1-pay-now-ledger.json').read_text())['accounts'];dl=json.loads((H/'pc1-card-ledger.json').read_text())['accounts']
def value(cell):return next(iter(cell.get('userEnteredValue',{}).values()),None)
for x in p['planned']:
 cells=live[x['id']];assert value(cells[0])==x['name'] and value(cells[1])==x['method'] and value(cells[2])==x['default']
 for idx,key in [(6,'average_daily'),(8,'balance'),(9,'month_spend')]:assert Decimal(str(value(cells[idx])))==Decimal(x[key]),(x['id'],key)
 assert all('USD' in cells[idx].get('userEnteredFormat',{}).get('numberFormat',{}).get('pattern','') for idx in [6,7,8,9])
assert not p['pending_ui']
assert set(hv['verified_account_ids'])==set(c['pay_now_account_ids'])
for aid in hv['verified_account_ids']:
 entry=hl[aid];cell=live[aid][7];assert Decimal(str(value(cell)))==Decimal(entry['amount'])
 assert entry['read_at'] in cell['note'] and entry['source'] in cell['note'] and entry['source']=='accounts_list_current_balance'
 assert Path(entry['receipt']).parent==B
card_checks=[];historical=[]
for aid,cells in live.items():
 entry=dl.get(aid);d=value(cells[3])
 if value(cells[1])=='Cartão de crédito':
  assert entry and entry.get('latest_card') and Decimal(str(d))==Decimal(entry['latest_card']['amount'])
  assert entry['read_at'] in cells[3]['note'];card_checks.append(aid)
 elif d is None and entry:
  historical.append({'account_id':aid,'name':value(cells[0]),'reason':entry['status'],'last_ui_read_at':entry['read_at'],'qualification':'D vazio de conta hoje na linha; histórico não revalidado neste tick.'})
assert not any(value(cells[4]) not in [None,''] for cells in live.values())
subtotal_checks=[]
for row in rows:
 cells=row.get('values',[])
 if cells and str(value(cells[0])or'').startswith('TOTAL'):
  for idx in [5,6,7,8,9]:
   if idx>=len(cells):continue
   cell=cells[idx];formula=cell.get('userEnteredValue',{}).get('formulaValue')
   if not formula:continue
   assert formula.startswith('=ROUND(SUM(') and formula.endswith('),2)'),formula
   args=formula[len('=ROUND(SUM('):-len('),2)')];total=Decimal(0)
   for part in args.split(','):
    ma=re.fullmatch(r'([A-J])(\d+):([A-J])(\d+)',part)
    if ma:
     assert ma[1]==ma[3];ci=ord(ma[1])-65
     for rr in range(int(ma[2])-1,int(ma[4])):
      cs=rows[rr].get('values',[]);ev=cs[ci].get('effectiveValue',{})if ci<len(cs) else {};total+=Decimal(str(ev.get('numberValue',0)))
    else:
     ma=re.fullmatch(r'([A-J])(\d+)',part);assert ma,part;cs=rows[int(ma[2])-1]['values'];total+=Decimal(str(cs[ord(ma[1])-65].get('effectiveValue',{}).get('numberValue',0)))
   total=total.quantize(Decimal('.01'));actual=Decimal(str(cell['effectiveValue']['numberValue']));assert total==actual,(formula,total,actual)
   subtotal_checks.append({'label':value(cells[0]),'column':chr(65+idx),'formula':formula,'value':str(total)})
lease=json.loads(subprocess.check_output([sys.executable,'/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py','status'],text=True));assert lease['locked'] is False
now=datetime.now().astimezone().isoformat()
receipt={'status':'full_financial_refresh_validated_historical_line_d_qualified','verified_at':now,'accounts':len(live),'groups':dict(Counter(x['method']for x in p['planned'])),'validated_metrics_at':p['collected_at'],'run_dir':str(M),'pay_now_run_dir':str(B),'source_to_live_sheet_cgij_exact':True,'full_grid_narrow_write_readback':json.loads((M/'receipt.json').read_text())['full_grid_exact_readback'],'totals_validated_columns':['F','G','H','I','J'],'subtotal_checks':subtotal_checks,'fresh_h_account_ids':hv['verified_account_ids'],'fresh_h_count':len(hv['verified_account_ids']),'pending_h_account_ids':[],'h_preserved_count':0,'h_source_to_live_sheet_and_note_exact':True,'h_read_at_min':min(hl[a]['read_at'] for a in hv['verified_account_ids']),'h_read_at_max':max(hl[a]['read_at'] for a in hv['verified_account_ids']),'h_sum_usd':str(sum((Decimal(hl[a]['amount'])for a in hv['verified_account_ids']),Decimal(0))),'pending_ui':[],'card_charge_values_present':len(card_checks),'card_proofs_updated':6,'historical_d_gaps':historical,'d_card_ledger_to_live_sheet_exact':True,'average_period':[dict(v) for v in {tuple(sorted(x['average_period'].items()))for x in p['planned']}],'totals_usd':{key:str(sum((Decimal(x[key])for x in p['planned']),Decimal(0)))for key in ['average_daily','balance','month_spend']},'invoice_period':'2026-09-01','invoice_due_usd':'0.00','visible_invoice_numbers':0,'pc1_blocker':None,'lease_free':True,'payments_executed':0,'meta_writes':0,'cron_changes':0,'workbook_sheet_count':len(meta['sheets']),'other_sheet_properties_unchanged':True,'other_sheet_prior_data_snapshot_available':False,'other_sheet_data_preservation_qualification':'Writers bound to exact target sheetId. Full other-tab cell parity against pre-tick baseline not claimed.','report_infra_status':'pending_cron_delivery_restriction_no_manual_message','closure_receipt':str(B/'closure-current.json')}
for path,data in [(B/'final-grid.json',book),(B/'final-sheet-properties.json',meta),(B/'closure-current.json',receipt)]:
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2));os.chmod(path,0o600)
print(json.dumps({k:receipt[k]for k in ['status','accounts','groups','fresh_h_count','pending_ui','historical_d_gaps','average_period','totals_usd','h_sum_usd','lease_free']},ensure_ascii=False))
