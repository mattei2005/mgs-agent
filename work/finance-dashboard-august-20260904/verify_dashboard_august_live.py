#!/usr/bin/env python3
import hashlib, importlib.util, json, math, sys, time, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE=Path('/root/mgs-agent'); WORK=BASE/'work/finance-dashboard-august-20260904'
SHEET_ID='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
spec=importlib.util.spec_from_file_location('mgs_google_workspace_auth',BASE/'scripts/mgs_google_workspace_auth.py')
if not spec or not spec.loader: raise RuntimeError('helper unavailable')
google=importlib.util.module_from_spec(spec);sys.modules[spec.name]=google;spec.loader.exec_module(google)
token=google.service_account_access_token([google.SHEETS_SCOPE]);project=google.service_account_project_id()

def api(method,url,payload=None):
 status,data=google.api_json(method,url,token,payload,quota_project=project)
 if status!=200: raise RuntimeError(f'api http {status}')
 return data
def get(a1,render):
 enc=urllib.parse.quote(a1,safe='');return api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{enc}?majorDimension=ROWS&valueRenderOption={render}').get('values') or []
def put(a1,value):
 enc=urllib.parse.quote(a1,safe='');return api('PUT',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{enc}?valueInputOption=RAW',{'range':a1,'majorDimension':'ROWS','values':[[value]]})
def c(g,r,col=1): return g[r-1][col-1] if r<=len(g) and col<=len(g[r-1]) else ''
def close(a,b): return isinstance(a,(int,float)) and isinstance(b,(int,float)) and math.isclose(float(a),float(b),rel_tol=1e-7,abs_tol=1e-7)
def fhash(g): return hashlib.sha256(json.dumps(g,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

ver=json.loads((WORK/'dashboard-august-final-verification.json').read_text())
meta=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?includeGridData=false&fields=spreadsheetId,sheets(properties,charts,basicFilter)')
sheets={s['properties']['title']:s for s in meta.get('sheets') or []}
checks={
 'base_id':sheets.get('BASE_DASH',{}).get('properties',{}).get('sheetId')==ver['created_sheets']['BASE_DASH'],
 'dash_id':sheets.get('DASH EXECUTIVO',{}).get('properties',{}).get('sheetId')==ver['created_sheets']['DASH EXECUTIVO'],
 'charts_4':len(sheets.get('DASH EXECUTIVO',{}).get('charts') or [])==4,
 'base_filter':bool(sheets.get('BASE_DASH',{}).get('basicFilter')),
}
base_formula=get("'BASE_DASH'!A1:V154",'FORMULA');base_fmt=get("'BASE_DASH'!A1:V154",'FORMATTED_VALUE')
dash_formula=get("'DASH EXECUTIVO'!A1:M90",'FORMULA');dash_u=get("'DASH EXECUTIVO'!A1:M90",'UNFORMATTED_VALUE');dash_fmt=get("'DASH EXECUTIVO'!A1:M90",'FORMATTED_VALUE')
caixa=get("'CAIXA SINTETICO'!J2:J81",'UNFORMATTED_VALUE'); j=lambda r:c(caixa,r-1)
checks.update({
 'base_rows_154':len(base_formula)==154,
 'base_header':c(base_formula,1,1)=='Mês' and c(base_formula,1,22)=='Fonte',
 'dash_title':c(dash_formula,1,1)=='MGS | DASHBOARD FINANCEIRO',
 'gross':close(c(dash_u,5,1),j(58)),
 'net':close(c(dash_u,5,4),j(64)),
 'spend':close(c(dash_u,5,7),-float(j(75))),
 'profit':close(c(dash_u,5,10),j(77)),
 'roi':close(c(dash_u,8,1),j(79)),
 'top_table':c(dash_fmt,16,1)=='Site' and c(dash_fmt,17,1)!='',
 'daily_31':c(dash_fmt,32,1)=='Data' and len([r for r in dash_fmt[32:64] if r])>=31,
 'partner_table':c(dash_fmt,66,1)=='Parceiro',
 'country_table':c(dash_fmt,75,1)=='País',
})
errors=[]
for name,grid in [('BASE_DASH',base_fmt),('DASH EXECUTIVO',dash_fmt)]:
 for r,row in enumerate(grid,1):
  for col,value in enumerate(row,1):
   if isinstance(value,str) and value.startswith('#'): errors.append(f'{name}!{r},{col}:{value}')
checks['zero_errors']=not errors
# Source FORMULA-mode scope preservation.
aug_formula=get("'Agosto 2026'!A1:APE338",'FORMULA'); caixa_formula=get("'CAIXA SINTETICO'!A1:R85",'FORMULA')
candidate=json.loads((WORK/'dashboard-august-build-candidate.json').read_text())
checks['august_source_unchanged']=fhash(aug_formula)==candidate['source_formula_hashes']['Agosto 2026']
checks['caixa_source_unchanged']=fhash(caixa_formula)==candidate['source_formula_hashes']['CAIXA SINTETICO']
# Exercise one dropdown and prove query reaction, then restore exact original.
filter_cell="'DASH EXECUTIVO'!B13"; original=c(get(filter_cell,'UNFORMATTED_VALUE'),1,1)
if original!='TODOS': raise RuntimeError(f'unexpected original filter {original!r}')
filter_live=False; filter_restored=False
try:
 put(filter_cell,'ActiveView'); time.sleep(2)
 if c(get(filter_cell,'UNFORMATTED_VALUE'),1,1)!='ActiveView': raise RuntimeError('filter write readback failed')
 partner_active=get("'DASH EXECUTIVO'!A66:D72",'FORMATTED_VALUE')
 data_labels=[row[0] for row in partner_active[1:] if row and row[0] not in ('',None)]
 filter_live=(data_labels==['ActiveView'])
finally:
 put(filter_cell,original); time.sleep(2)
 filter_restored=c(get(filter_cell,'UNFORMATTED_VALUE'),1,1)==original
partner_restored=get("'DASH EXECUTIVO'!A66:D72",'FORMATTED_VALUE')
restored_labels=[row[0] for row in partner_restored[1:] if row and row[0] not in ('',None)]
checks['filter_activeview_live']=filter_live
checks['filter_restored_todos']=filter_restored
checks['partner_table_restored']=len(restored_labels)>=4 and 'ActiveView' in restored_labels and 'JBF' in restored_labels
status='pass' if all(checks.values()) else 'fail'
result={'status':status,'verified_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'errors':errors,'filter_probe':{'original':'TODOS','probe':'ActiveView','probe_rows':data_labels,'restored_rows':restored_labels},'dashboard_values':{'gross':j(58),'net_after_invalid':j(64),'spend_positive':-float(j(75)),'profit':j(77),'roi_net':j(79),'active_sites':c(dash_u,8,7),'profitable_sites':c(dash_u,8,10)},'sheet_ids':ver['created_sheets'],'chart_count':4}
raw=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n';path=WORK/'dashboard-august-independent-live-verification.json';path.write_text(raw,encoding='utf-8');sha=hashlib.sha256(raw.encode()).hexdigest()
print(json.dumps({'status':status,'checks':sum(checks.values()),'total_checks':len(checks),'errors':len(errors),'filter_probe':filter_live,'filter_restored':filter_restored,'chart_count':4,'verification_path':str(path),'sha256':sha},ensure_ascii=False,separators=(',',':')))
if status!='pass': raise SystemExit(2)
