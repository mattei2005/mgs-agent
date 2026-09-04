#!/usr/bin/env python3
import importlib.util, json, math, sys, urllib.parse
from pathlib import Path

BASE = Path('/root/mgs-agent')
WORK = BASE / 'work/finance-dashboard-august-20260904'
SHEET_ID = '16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
spec = importlib.util.spec_from_file_location('mgs_google_workspace_auth', BASE/'scripts/mgs_google_workspace_auth.py')
if not spec or not spec.loader: raise RuntimeError('helper unavailable')
google = importlib.util.module_from_spec(spec); sys.modules[spec.name]=google; spec.loader.exec_module(google)
token = google.service_account_access_token([google.SHEETS_SCOPE]); project=google.service_account_project_id()

def get(a1, render):
    enc=urllib.parse.quote(a1,safe='')
    status,data=google.api_json('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{enc}?majorDimension=ROWS&valueRenderOption={render}',token,quota_project=project)
    if status!=200: raise RuntimeError(f'read http {status}')
    return data.get('values') or []
def c(g,r,col=1):
    return g[r-1][col-1] if r<=len(g) and col<=len(g[r-1]) else ''
def close(a,b): return isinstance(a,(int,float)) and isinstance(b,(int,float)) and math.isclose(float(a),float(b),rel_tol=1e-7,abs_tol=1e-7)

cand=json.loads((WORK/'caixa-j59-j75-write-candidate.json').read_text())
f=get("'CAIXA SINTETICO'!J2:J81",'FORMULA'); u=get("'CAIXA SINTETICO'!J2:J81",'UNFORMATTED_VALUE'); fmt=get("'CAIXA SINTETICO'!J2:J81",'FORMATTED_VALUE')
su=get("'Agosto 2026'!O145:Q178",'UNFORMATTED_VALUE')
apb=get("'Agosto 2026'!APB36",'UNFORMATTED_VALUE')
# Local row index for J2:J81 is sheet row - 1.
formula_mismatches=[]
for target,expected in cand['formulas'].items():
    row=int(target[1:]); actual=c(f,row-1)
    if actual!=expected: formula_mismatches.append({'cell':target,'actual':actual})
source_expected={
 'J59': c(su,31,2), # P175 within O145:Q178
 'J60': c(su,32,2),
 'J61': c(su,33,2),
 'J62': c(su,34,2),
 'J72': c(su,1,1),
 'J73': c(su,17,1),
 'J75': c(apb,1,1),
}
value_mismatches=[]
for target,expected in source_expected.items():
    row=int(target[1:]); actual=c(u,row-1)
    if not close(actual,expected): value_mismatches.append({'cell':target,'expected':expected,'actual':actual})
errors=[]
for idx,row in enumerate(fmt,2):
    v=row[0] if row else ''
    if isinstance(v,str) and v.startswith('#'): errors.append(f'J{idx}:{v}')
preserved={k:v for k,v in cand['preserved_summary_formulas'].items() if c(f,int(k[1:])-1)!=v}
spacers=[f'J{r}' for r in cand['preserved_spacer_rows'] if c(f,r-1) not in ('',None)]
result={
 'status':'pass' if not (formula_mismatches or value_mismatches or errors or preserved or spacers) else 'fail',
 'formula_mismatches':formula_mismatches,
 'value_mismatches':value_mismatches,
 'displayed_errors':errors,
 'preserved_formula_mismatches':preserved,
 'spacer_changes':spacers,
 'J58':c(u,57),'J64':c(u,63),'J77':c(u,76),'J79':c(u,78),'J80':c(u,79),'J81':c(u,80),
}
print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
if result['status']!='pass': raise SystemExit(2)
