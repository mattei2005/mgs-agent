#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import datetime, json, pathlib, re, urllib.parse, urllib.request
AUDIT_PATH=pathlib.Path('/root/mgs-agent/work/july-2026-fill-8-12/master-fill-audit-20260713-181957.json')
OUT=AUDIT_PATH.parent
SID='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'; TAB='Julho 2026'
TOKEN=pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
audit=json.loads(AUDIT_PATH.read_text()); backup=json.loads(pathlib.Path(audit['backup']).read_text())
c=json.loads(TOKEN.read_text()); body=urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
a=json.load(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',data=body,headers={'Content-Type':'application/x-www-form-urlencoded'}),timeout=30))['access_token']
def api(url): return json.load(urllib.request.urlopen(urllib.request.Request(url,headers={'Authorization':'Bearer '+a}),timeout=180))
def q(s): return urllib.parse.quote(s,safe='')
def get(rng,render): return api(f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/{q(rng)}?valueRenderOption={render}').get('values',[])
def batch(ranges,render):
 p=urllib.parse.urlencode([('ranges',r) for r in ranges]+[('valueRenderOption',render)])
 return api(f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values:batchGet?{p}').get('valueRanges',[])
def cnum(c):
 n=0
 for ch in c:n=n*26+ord(ch.upper())-64
 return n
def col(n):
 s=''
 while n:n-=1;s=chr(65+n%26)+s;n//=26
 return s
def parse_range(rng):
 part=rng.split('!',1)[1]; a1,b1=(part.split(':')+[part])[:2]
 m1=re.match(r'([A-Z]+)(\d+)',a1); m2=re.match(r'([A-Z]+)(\d+)',b1)
 return cnum(m1.group(1)),int(m1.group(2)),cnum(m2.group(1)),int(m2.group(2))
def matrix_map(rng,vals):
 c1,r1,_,_=parse_range(rng); out={}
 for i,row in enumerate(vals):
  for j,v in enumerate(row):
   if v!='': out[(r1+i,c1+j)]=v
 return out
def allowed(row,c):
 if 12<=row<=16: return True
 if 53<=row<=57: return True
 if 112<=row<=275 and cnum('TQ')<=c<=cnum('TV'): return True
 if 112<=row<=180 and cnum('ABL')<=c<=cnum('ABQ'): return True
 if 112<=row<=116 and c in (cnum('NF'),cnum('NM')): return True
 if 153<=row<=157 and c in [cnum(x) for x in ['NF','NH','NJ','NL','NN','NP','NR','NT','NV']]: return True
 return False
# Compare full FORMULA-render snapshots to detect changes outside requested bands.
current_formula=batch(backup['ranges'],'FORMULA')
cur_by={v['range']:v.get('values',[]) for v in current_formula}
backup_by={v['range']:v.get('values',[]) for v in backup['formulas']}
changes_out=[]; changes_total=0
for rng,bvals in backup_by.items():
 cvals=cur_by.get(rng,[]); bm=matrix_map(rng,bvals); cm=matrix_map(rng,cvals)
 for pos in set(bm)|set(cm):
  if bm.get(pos,'')!=cm.get(pos,''):
   changes_total+=1
   if not allowed(*pos): changes_out.append({'cell':f'{col(pos[1])}{pos[0]}','before':bm.get(pos,''),'after':cm.get(pos,'')})
# Independent expected-cell readback.
expected={**audit['expected_revenue_cells'],**audit['expected_spend_cells']}
reads=batch(list(expected),'UNFORMATTED_VALUE'); rb={v['range']:v.get('values',[]) for v in reads}; mism=[]
for rng,exp in expected.items():
 vals=rb.get(rng,[]); got=vals[0][0] if vals and vals[0] else 0
 try: ok=round(float(got or 0),2)==round(float(exp),2)
 except Exception: ok=False
 if not ok:mism.append({'range':rng,'expected':exp,'got':got})
# Formula integrity and formula errors.
allv=get(f"'{TAB}'!A1:AIH275",'FORMATTED_VALUE'); errors=[]
for ri,row in enumerate(allv,1):
 for ci,v in enumerate(row,1):
  if isinstance(v,str) and v.startswith('#'):errors.append({'cell':f'{col(ci)}{ri}','value':v})
formula_ranges=[f"'{TAB}'!AAG{r}" for r in range(53,58)]+[f"'{TAB}'!AAV{r}" for r in range(53,58)]+[f"'{TAB}'!TV{r}" for r in range(112,112+audit['finc_rows'])]+[f"'{TAB}'!ABQ{r}" for r in range(112,112+audit['cp_rows'])]
fr=batch(formula_ranges,'FORMULA'); missing=[]
for v in fr:
 val=(v.get('values') or [[]])[0]
 x=val[0] if val else ''
 if not(isinstance(x,str) and x.startswith('=')):missing.append(v['range'])
result={'ok':not changes_out and not mism and not errors and not missing,'audit_source':str(AUDIT_PATH),'changes_total_in_formula_render':changes_total,'changes_outside_allowed':changes_out,'expected_cells':len(expected),'cell_mismatches':mism,'formula_errors':errors,'formula_checks':len(formula_ranges),'missing_formulas':missing,'checked_at':datetime.datetime.now().isoformat(timespec='seconds')}
p=OUT/f'independent-validation-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.json'; p.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2)); print('validation',p)
raise SystemExit(0 if result['ok'] else 2)
