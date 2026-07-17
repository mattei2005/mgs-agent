#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import json,pathlib,urllib.parse,urllib.request,urllib.error,re,datetime,time
TOKEN=pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
RUN_DIR=pathlib.Path('/root/mgs-agent/work/finance-month-rollover-audit/rollover-july-2026-20260703-185408')
c=json.loads(TOKEN.read_text())
body=urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
req=urllib.request.Request('https://oauth2.googleapis.com/token',data=body,headers={'Content-Type':'application/x-www-form-urlencoded'})
with urllib.request.urlopen(req,timeout=30) as r: access=json.load(r)['access_token']
def api(method,url,data=None,timeout=180):
 body=None; h={'Authorization':'Bearer '+access}
 if data is not None:
  body=json.dumps(data).encode(); h['Content-Type']='application/json; charset=UTF-8'
 last=None
 for attempt in range(5):
  try:
   req=urllib.request.Request(url,method=method,headers=h,data=body)
   with urllib.request.urlopen(req,timeout=timeout) as r:
    raw=r.read(); return json.loads(raw) if raw else {}
  except (urllib.error.HTTPError, TimeoutError) as e:
   if isinstance(e, urllib.error.HTTPError):
    raw=e.read().decode(errors='ignore')[:500]; last=f'HTTP {e.code}: {raw}'
    retry=e.code in (429,500,502,503,504)
   else:
    last='Timeout'; retry=True
   if retry and attempt<4:
    time.sleep(10*(attempt+1)); continue
   raise RuntimeError(last)
def q(s): return urllib.parse.quote(s,safe='')
def col(n):
 out=''
 while n:
  n-=1; out=chr(65+n%26)+out; n//=26
 return out
SHEETS={
 'principal_2026':'16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak',
 'kelly':'1huhZFlFVEKmY11fR5DxgCWE2TNC3gvw_eXlW2jylVfs',
 'isliago':'1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c',
 'george':'1cFPIlC2NxRG6GQiF4VmbNqRz09ZWkZXWUzP7nINK9vU',
 'nicolas':'128fEDdXayhgGGKMdLPf-FTWyJRW8-v6JgHzmUSrsOMU',
 'joe':'1syOKCRi-2wpHQNY5fHMcOzjj73EXmFIUbTF1sTIARvQ',
}

def scan_values(sid, tab, rows, cols, render):
 errors=[]; june=[]; formula_count=0
 # chunks to avoid large response timeout
 for start in range(1, cols+1, 120):
  end=min(cols,start+119)
  rng=f"'{tab}'!{col(start)}1:{col(end)}{rows}"
  vals=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{q(rng)}?valueRenderOption={render}',timeout=120).get('values',[])
  for r,row in enumerate(vals,1):
   for off,v in enumerate(row):
    c=start+off
    if render=='FORMATTED_VALUE':
     if isinstance(v,str) and v.startswith('#'): errors.append(f'{col(c)}{r}:{v}')
    else:
     if isinstance(v,str) and v.startswith('='):
      formula_count+=1
      if 'Junho 2026' in v: june.append(f'{col(c)}{r}')
 return errors,june,formula_count
report={}
for key,sid in SHEETS.items():
 meta=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}?fields=properties(title),sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))')
 sheets={s['properties']['title']:s['properties'] for s in meta['sheets']}
 t=sheets.get('Julho 2026')
 if not t:
  report[key]={'target_exists':False}; continue
 rows=min(t.get('gridProperties',{}).get('rowCount',1000),2500); cols=min(t.get('gridProperties',{}).get('columnCount',26),900)
 errors,_,_=scan_values(sid,'Julho 2026',rows,cols,'FORMATTED_VALUE')
 _,june,formula_count=scan_values(sid,'Julho 2026',rows,cols,'FORMULA')
 rep={'target_exists':True,'formula_count':formula_count,'formula_error_count':len(errors),'errors':errors[:30],'literal_junho_ref_count':len(june),'literal_junho_refs':june[:30]}
 if key=='principal_2026':
  main_range = "'Julho 2026'!A3:B35"
  vals=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{q(main_range)}?valueRenderOption=FORMATTED_VALUE').get('values',[])
  rep['A3']=vals[0][0] if vals and vals[0] else None
  # Above range starts at A3, so dates B5:B35 are rows index 2..32, col index 1
  rep['B5_B35_nonblank']=sum(1 for row in vals[2:] if len(row)>1 and row[1])
  caixa_range = "'CAIXA SINTETICO'!I1:I120"
  cvals=api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{q(caixa_range)}?valueRenderOption=FORMULA').get('values',[])
  rep['caixa_col_I_nonblank']=sum(1 for row in cvals if row and row[0])
 report[key]=rep
out=RUN_DIR/'final-validation.json'
out.write_text(json.dumps({'validated_at':datetime.datetime.now().isoformat(timespec='seconds'),'report':report},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'validation_file':str(out),'report':report},ensure_ascii=False,indent=2))
