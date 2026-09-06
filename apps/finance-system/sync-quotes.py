#!/usr/bin/env python3
"""Read Google formula quotes via canonical SA; send only quotes to isolated finance app."""
import sys,json,pathlib,datetime,math,os,fcntl
from urllib.parse import urlencode
BASE=pathlib.Path('/root/mgs-agent');ROOT=BASE/'apps/finance-system'
sys.path.insert(0,str(BASE/'scripts'))
from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
SHEET='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748'
EXPECTED={'principal|CAIXA SINTETICO|J2':'=GOOGLEFINANCE("USDBRL")*99%','principal|Agosto 2026|H1':'=GOOGLEFINANCE("USDCAD")'}

def collect():
 load_env()
 for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']:
  if os.environ.get(k)!='service_account':raise RuntimeError('canonical_auth_selector_conflict')
 sa=load_service_account()
 if sa.get('client_email')!='mgsagent@mgs-core-prod.iam.gserviceaccount.com' or sa.get('project_id')!='mgs-core-prod':raise RuntimeError('canonical_identity_mismatch')
 token=service_account_access_token();project='mgs-core-prod'
 status,drive=api_json('GET','https://www.googleapis.com/drive/v3/files/'+SHEET+'?'+urlencode({'supportsAllDrives':'true','fields':'id,trashed'}),token,quota_project=project)
 if status!=200 or drive.get('trashed'):raise RuntimeError('drive_preflight_failed_'+str(status))
 params=[('ranges',"'Agosto 2026'!A1:L1"),('ranges',"'CAIXA SINTETICO'!J2"),('includeGridData','true'),('fields','spreadsheetId,sheets(properties(title),data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue))))')]
 status,response=api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+SHEET+'?'+urlencode(params),token,quota_project=project)
 if status!=200:raise RuntimeError('sheets_read_failed_'+str(status))
 cells={}
 for sheet in response['sheets']:
  title=sheet['properties']['title']
  for block in sheet.get('data',[]):
   for ri,row in enumerate(block.get('rowData',[]),start=block.get('startRow',0)+1):
    for ci,cell in enumerate(row.get('values',[]),start=block.get('startColumn',0)+1):
     col='';v=ci
     while v:v,r=divmod(v-1,26);col=chr(65+r)+col
     cells['principal|'+title+'|'+col+str(ri)]=cell
 if cells.get('principal|Agosto 2026|F1',{}).get('userEnteredValue',{}).get('formulaValue')!="=SUM('CAIXA SINTETICO'!J2)":raise RuntimeError('quote_formula_changed_F1')
 values={}
 for key,formula in EXPECTED.items():
  cell=cells.get(key,{})
  if cell.get('userEnteredValue',{}).get('formulaValue')!=formula:raise RuntimeError('quote_formula_changed_'+key.split('|')[-1])
  value=cell.get('effectiveValue',{}).get('numberValue')
  if not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<value<10000:raise RuntimeError('invalid_quote_value')
  values[key]=value
 return {'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'Google Sheets / GOOGLEFINANCE','spreadsheet_id':SHEET,'values':values,'formulas':EXPECTED,'google_writes':0}

def publish(payload):
 sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
 code="import sys,json,pathlib,os; p=pathlib.Path('"+TARGET+"/private/live-quotes.json'); d=json.load(sys.stdin); assert len(d['values'])==2; t=p.with_suffix('.pending'); t.write_text(json.dumps(d)); t.chmod(0o600); os.replace(t,p); print(json.dumps({'readback':json.loads(p.read_text())==d}))"
 import shlex
 out=ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code),json.dumps(payload).encode());assert json.loads(out)['readback']
 out=ssh('sudo -n -u mgsfinance env FINANCE_DATABASE=postgres /home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node '+TARGET+'/apply-live-quotes.mjs',timeout=180)
 return json.loads(out)

def main():
 state=ROOT/'private/quote-sync-state.json';lock=ROOT/'private/quote-sync.lock'
 with lock.open('a') as handle:
  try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  try:
   payload=collect();result=publish(payload) if '--publish' in sys.argv else {'read_only':True}
   if '--publish' not in sys.argv:(ROOT/'private/live-quotes.json').write_text(json.dumps(payload))
   state.write_text(json.dumps({'ok':True,'consecutive_failures':0,'updated_at':payload['updated_at'],'result':result}))
   if '--quiet' not in sys.argv:print(json.dumps({'ok':True,'quotes':len(payload['values']),'google_writes':0,**result}))
  except Exception as e:
   old=json.loads(state.read_text()) if state.exists() else {};count=old.get('consecutive_failures',0)+1
   # Known diagnostic codes only; never raw SSH/1Password exceptions.
   safe=str(e) if str(e).startswith(('canonical_','drive_preflight_','sheets_read_','quote_formula_','invalid_quote_')) else type(e).__name__
   state.write_text(json.dumps({'ok':False,'consecutive_failures':count,'error':safe,'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}))
   print('Câmbio da dash: sincronização falhou; último valor preservado. Diagnóstico: '+safe+'. Falhas consecutivas: '+str(count)+'.'+(' Zeus: intervenção necessária.' if count>=3 else ''))
   raise SystemExit(1)
if __name__=='__main__':main()
