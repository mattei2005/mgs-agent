#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import json,pathlib,urllib.parse,urllib.request,urllib.error,time,re,datetime
TOKEN=pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
OUT=pathlib.Path('/root/mgs-agent/work/finance-month-rollover-audit/rollover-july-2026-20260703-185408')
OUT.mkdir(parents=True, exist_ok=True)
SHEETS={
 'principal_2026':'16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak',
 'kelly':'1huhZFlFVEKmY11fR5DxgCWE2TNC3gvw_eXlW2jylVfs',
 'isliago':'1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c',
 'george':'1cFPIlC2NxRG6GQiF4VmbNqRz09ZWkZXWUzP7nINK9vU',
 'nicolas':'128fEDdXayhgGGKMdLPf-FTWyJRW8-v6JgHzmUSrsOMU',
 'joe':'1syOKCRi-2wpHQNY5fHMcOzjj73EXmFIUbTF1sTIARvQ',
}
MANAGERS={k:v for k,v in SHEETS.items() if k!='principal_2026'}

def col(n):
 out=''
 while n:
  n-=1; out=chr(65+n%26)+out; n//=26
 return out

def token():
 c=json.loads(TOKEN.read_text())
 body=urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
 req=urllib.request.Request('https://oauth2.googleapis.com/token',data=body,headers={'Content-Type':'application/x-www-form-urlencoded'})
 with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)['access_token']
ACCESS=token()
def api(method,url,data=None,timeout=120):
 body=None; h={'Authorization':'Bearer '+ACCESS}
 if data is not None:
  body=json.dumps(data).encode(); h['Content-Type']='application/json; charset=UTF-8'
 last=None
 for attempt in range(6):
  try:
   req=urllib.request.Request(url,method=method,headers=h,data=body)
   with urllib.request.urlopen(req,timeout=timeout) as r:
    raw=r.read(); return json.loads(raw) if raw else {}
  except (urllib.error.HTTPError, TimeoutError) as e:
   if isinstance(e, urllib.error.HTTPError):
    raw=e.read().decode(errors='ignore')[:600]; last=f'HTTP {e.code}: {raw}'; retry=e.code in (429,500,502,503,504)
   else:
    last='Timeout'; retry=True
   if retry and attempt<5:
    time.sleep(10*(attempt+1)); continue
   raise RuntimeError(last)
def q(s): return urllib.parse.quote(s,safe='')
def get(sid,rng,render='FORMATTED_VALUE'):
 return api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{q(rng)}?valueRenderOption={render}').get('values',[])
def batch_get(sid,ranges,render='FORMATTED_VALUE'):
 params=urllib.parse.urlencode([('ranges',r) for r in ranges]+[('valueRenderOption',render)])
 return api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values:batchGet?{params}').get('valueRanges',[])
def meta(sid):
 return api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}?fields=properties(title),sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))')
def scan_tab(sid, tab, rows, cols):
 errors=[]; june_refs=[]; formula_count=0
 for start in range(1,cols+1,150):
  end=min(cols,start+149)
  rng=f"'{tab}'!{col(start)}1:{col(end)}{rows}"
  vals=get(sid,rng,'FORMATTED_VALUE')
  forms=get(sid,rng,'FORMULA')
  for r,row in enumerate(vals,1):
   for off,v in enumerate(row):
    if isinstance(v,str) and v.startswith('#'): errors.append({'cell':f'{col(start+off)}{r}','value':v})
  for r,row in enumerate(forms,1):
   for off,v in enumerate(row):
    if isinstance(v,str) and v.startswith('='):
     formula_count+=1
     if 'Junho 2026' in v: june_refs.append({'cell':f'{col(start+off)}{r}','formula':v[:300]})
 return formula_count, errors, june_refs
report={'validated_at':datetime.datetime.now().isoformat(timespec='seconds'),'sheets':{},'overall_ok':True,'issues':[]}
# principal
sid=SHEETS['principal_2026']; m=meta(sid); sh={s['properties']['title']:s['properties'] for s in m['sheets']}
pt=sh.get('Julho 2026')
if not pt:
 report['overall_ok']=False; report['issues'].append('principal missing Julho 2026')
else:
 rows=min(pt.get('gridProperties',{}).get('rowCount',1000),2500); cols=min(pt.get('gridProperties',{}).get('columnCount',900),900)
 fc,errors,june=scan_tab(sid,'Julho 2026',rows,cols)
 # critical ranges
 vb=batch_get(sid,["'Julho 2026'!A3","'Julho 2026'!E1","'Julho 2026'!B5:B35","'Julho 2026'!B46:B76","'Julho 2026'!B105:B135","'CAIXA SINTETICO'!I2","'Julho 2026'!NF100:NU104","'Julho 2026'!NF105:NF135","'Julho 2026'!NM105:NM135","'Julho 2026'!NF146:NV176"],'FORMATTED_VALUE')
 vf={vr['range']:vr.get('values',[]) for vr in vb}
 ff=batch_get(sid,["'Julho 2026'!E1"],'FORMULA')[0].get('values',[])
 def nonblank_count(vals): return sum(1 for row in vals for v in row if str(v).strip()!='')
 # manual inputs in openzed/ícaro should be blank in selected columns; formula result columns may show R$ - and are not counted here except exact input ranges.
 nf_inputs=nonblank_count(vf.get("'Julho 2026'!NF105:NF135",[]))
 nm_inputs=nonblank_count(vf.get("'Julho 2026'!NM105:NM135",[]))
 # spend input columns are alternating, read formula to ensure input cols blank? use formatted range and count only even offsets corresponding input cols in NF,NH,NJ,NL,NN,NP,NR,NT,NV.
 spend_vals=vf.get("'Julho 2026'!NF146:NV176",[]); spend_input_nonblank=0
 input_offsets=[0,2,4,6,8,10,12,14,16]
 for row in spend_vals:
  for off in input_offsets:
   if off < len(row) and str(row[off]).strip(): spend_input_nonblank+=1
 b_checks={}
 for rng in ["'Julho 2026'!B5:B35","'Julho 2026'!B46:B76","'Julho 2026'!B105:B135"]:
  vals=[row[0] for row in vf.get(rng,[]) if row]
  b_checks[rng]={'count':len(vals),'first':vals[0] if vals else None,'last':vals[-1] if vals else None,'raw_date_format_ok': bool(vals and ',' in vals[0] and vals[-1].endswith('31'))}
 principal={
  'title':m['properties']['title'],'target_exists':True,'formula_count':fc,'formula_error_count':len(errors),'errors':errors[:30],
  'literal_junho_ref_count':len(june),'literal_junho_refs':june[:20],
  'A3':vf.get("'Julho 2026'!A3",[['']])[0][0] if vf.get("'Julho 2026'!A3") else None,
  'E1_formula':ff[0][0] if ff and ff[0] else None,
  'E1_value':vf.get("'Julho 2026'!E1",[['']])[0][0] if vf.get("'Julho 2026'!E1") else None,
  'caixa_I2':vf.get("'CAIXA SINTETICO'!I2",[['']])[0][0] if vf.get("'CAIXA SINTETICO'!I2") else None,
  'B_blocks':b_checks,
  'openzed_icaro_header':vf.get("'Julho 2026'!NF100:NU104",[])[:4],
  'openzed_icaro_revenue_input_nonblank':nf_inputs+nm_inputs,
  'openzed_icaro_spend_input_nonblank':spend_input_nonblank,
 }
 report['sheets']['principal_2026']=principal
 for cond,msg in [(len(errors)==0,'principal formula errors'),(len(june)==0,'principal references Junho'),(principal['A3'] in ('7.00','7'),'principal A3'),('I2' in (principal['E1_formula'] or ''),'principal E1 I2'),(all(x['raw_date_format_ok'] and x['count']==31 for x in b_checks.values()),'principal B format/count'),(nf_inputs+nm_inputs==0,'openzed revenue inputs blank'),(spend_input_nonblank==0,'openzed spend inputs blank')]:
  if not cond:
   report['overall_ok']=False; report['issues'].append(msg)
# managers
for key,sid in MANAGERS.items():
 m=meta(sid); sh={s['properties']['title']:s['properties'] for s in m['sheets']}; t=sh.get('Julho 2026')
 if not t:
  report['overall_ok']=False; report['issues'].append(f'{key} missing Julho 2026'); continue
 rows=min(t.get('gridProperties',{}).get('rowCount',1000),2500); cols=min(t.get('gridProperties',{}).get('columnCount',100),300)
 fc,errors,june=scan_tab(sid,'Julho 2026',rows,cols)
 vals=batch_get(sid,["'Julho 2026'!H1","'Julho 2026'!A21:H21"],'FORMATTED_VALUE')
 forms=batch_get(sid,["'Julho 2026'!H1"],'FORMULA')
 vf={vr['range']:vr.get('values',[]) for vr in vals}
 h1f=forms[0].get('values',[]) if forms else []
 manager={
  'title':m['properties']['title'],'target_exists':True,'formula_count':fc,'formula_error_count':len(errors),'errors':errors[:20],
  'literal_junho_ref_count':len(june),'literal_junho_refs':june[:20],
  'H1_formula':h1f[0][0] if h1f and h1f[0] else None,
  'H1_value':vf.get("'Julho 2026'!H1",[['']])[0][0] if vf.get("'Julho 2026'!H1") else None,
  'A21_H21':vf.get("'Julho 2026'!A21:H21",[]),
 }
 report['sheets'][key]=manager
 for cond,msg in [(len(errors)==0,f'{key} formula errors'),(len(june)==0,f'{key} references Junho'),('I2' in (manager['H1_formula'] or ''),f'{key} H1 I2')]:
  if not cond:
   report['overall_ok']=False; report['issues'].append(msg)
path=OUT/'final-audit-after-corrections.json'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'audit_file':str(path),'overall_ok':report['overall_ok'],'issues':report['issues'],'summary':{k:{'errors':v.get('formula_error_count'),'junho_refs':v.get('literal_junho_ref_count'),'formulas':v.get('formula_count')} for k,v in report['sheets'].items()}},ensure_ascii=False,indent=2))
