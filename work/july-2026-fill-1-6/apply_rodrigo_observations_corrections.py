#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import json,pathlib,urllib.parse,urllib.request,urllib.error,datetime,time
from collections import defaultdict
import pandas as pd
SID='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
TAB='Julho 2026'
TOKEN=pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
OUT=pathlib.Path('/root/mgs-agent/work/july-2026-fill-1-6')
LONG=OUT/'Long.csv'
PREV_BACKUP=OUT/'backup-before-master-fill-20260707-121130.json'
BACKUP=OUT/f"backup-before-observation-fixes-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
AUDIT=OUT/f"observation-fixes-audit-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
MANAGERS=[f'g00{i}-d' for i in range(1,7)]

def token():
 c=json.loads(TOKEN.read_text()); data=urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
 return json.load(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',data=data,headers={'Content-Type':'application/x-www-form-urlencoded'}),timeout=30))['access_token']
ACCESS=token()
def api(method,url,data=None,timeout=180):
 h={'Authorization':'Bearer '+ACCESS}; body=None
 if data is not None:
  body=json.dumps(data).encode(); h['Content-Type']='application/json; charset=UTF-8'
 for attempt in range(6):
  try:
   req=urllib.request.Request(url,method=method,headers=h,data=body)
   with urllib.request.urlopen(req,timeout=timeout) as r:
    raw=r.read(); return json.loads(raw) if raw else {}
  except urllib.error.HTTPError as e:
   if e.code in (429,500,502,503,504) and attempt<5:
    time.sleep(5*(attempt+1)); continue
   raise

def q(s): return urllib.parse.quote(s,safe='')
def batch_get(ranges,render='FORMULA'):
 params=urllib.parse.urlencode([('ranges',r) for r in ranges]+[('valueRenderOption',render)])
 return api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values:batchGet?{params}').get('valueRanges',[])
def batch_update(data):
 return api('POST',f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values:batchUpdate',{'valueInputOption':'USER_ENTERED','data':data})
def get(rng,render='FORMATTED_VALUE'):
 return api('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/{q(rng)}?valueRenderOption={render}').get('values',[])

def col_to_num(c):
 n=0
 for ch in c: n=n*26+ord(ch)-64
 return n
def num_to_col(n):
 s=''
 while n: n-=1; s=chr(65+n%26)+s; n//=26
 return s

def backup_cell(c,r):
 b=json.loads(PREV_BACKUP.read_text()); vals=b['formulas'][0].get('values',[]); ci=col_to_num(c)
 return vals[r-1][ci-1] if r-1<len(vals) and ci-1<len(vals[r-1]) else ''

def country(vertical):
 v=str(vertical).lower()
 return v.split('-')[0] if '-' in v else v

# Build Creditoparaveiculo detail rows from source Long.
long=pd.read_csv(LONG)
long['Data']=pd.to_datetime(long['Data']).dt.date.astype(str)
cp=long[(long['Site']=='creditoparaveiculo.com') & (long['Data']>='2026-07-01') & (long['Data']<='2026-07-06')]
by=defaultdict(lambda:{'gasto':0.0,'receita':0.0})
for _,r in cp.iterrows():
 by[(r['Data'],r['Gestor'])]['gasto'] += float(r['Gasto'] or 0)
 by[(r['Data'],r['Gestor'])]['receita'] += float(r['Receita'] or 0)
cp_rows=[]
for (date,gestor),v in sorted(by.items()):
 lucro=v['receita']-v['gasto']
 cp_rows.append([date,gestor,round(v['gasto'],10),round(v['receita'],10),round(lucro,10),f'=IFERROR(ABP{112+len(cp_rows)}/ABN{112+len(cp_rows)},"")'])

# Backup current touched ranges.
touched=[f"'{TAB}'!AAG46:AAG51",f"'{TAB}'!AAV46:AAV51",f"'{TAB}'!TV112:TV140",f"'{TAB}'!ABL100:ABQ180",f"'{TAB}'!AAG46:AAL51",f"'{TAB}'!AAV46:ABA51"]
backup={'created_at':datetime.datetime.now().isoformat(timespec='seconds'),'ranges':touched,'formula':batch_get(touched,'FORMULA'),'formatted':batch_get(touched,'FORMATTED_VALUE')}
BACKUP.write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding='utf-8')

updates=[]
# Restore USD formula columns for Google Ads BRL spend that were accidentally blanked.
for col in ['AAG','AAV']:
 for r in range(46,52):
  f=backup_cell(col,r)
  if f:
   updates.append({'range':f"'{TAB}'!{col}{r}", 'values':[[f]]})
# Fincgriffin ROI/margin detail formulas in TV112:TV140.
for r in range(112,141):
 updates.append({'range':f"'{TAB}'!TV{r}", 'values':[[f'=IFERROR(TU{r}/TS{r},"")']]})
# Creditoparaveiculo lower table ABL100:ABQ.
updates.extend([
 {'range':f"'{TAB}'!ABL100:ABQ180", 'values':[['','','','','',''] for _ in range(81)]},
 {'range':f"'{TAB}'!ABL100", 'values':[['POR MES']]},
 {'range':f"'{TAB}'!ABL102:ABP102", 'values':[['Gestor','Gasto','Receita','Lucro','Margem']]},
 {'range':f"'{TAB}'!ABL103:ABL108", 'values':[[m] for m in MANAGERS]},
])
for i,m in enumerate(MANAGERS,103):
 updates += [
  {'range':f"'{TAB}'!ABM{i}", 'values':[[f'=SUMIF($ABM$112:$ABM$180,ABL{i},$ABN$112:$ABN$180)']]},
  {'range':f"'{TAB}'!ABN{i}", 'values':[[f'=SUMIF($ABM$112:$ABM$180,ABL{i},$ABO$112:$ABO$180)']]},
  {'range':f"'{TAB}'!ABO{i}", 'values':[[f'=ABN{i}-ABM{i}']]},
  {'range':f"'{TAB}'!ABP{i}", 'values':[[f'=IFERROR(ABO{i}/ABM{i},"")']]},
 ]
updates.append({'range':f"'{TAB}'!ABL111:ABQ111", 'values':[['Data','Gestor','Gasto','Receita','Lucro','Margem']]})
if cp_rows:
 updates.append({'range':f"'{TAB}'!ABL112:ABQ{111+len(cp_rows)}", 'values':cp_rows})
resp=batch_update(updates)

# Validate.
read_ranges=[f"'{TAB}'!AAG46:AAG51",f"'{TAB}'!AAV46:AAV51",f"'{TAB}'!TV112:TV140",f"'{TAB}'!ABL100:ABQ{111+len(cp_rows)}"]
forms=batch_get(read_ranges,'FORMULA')
fmt=batch_get(read_ranges,'FORMATTED_VALUE')
# formula errors full sheet
vals=get(f"'{TAB}'!A1:AIH275",'FORMATTED_VALUE')
errs=[]
for ri,row in enumerate(vals,1):
 for ci,v in enumerate(row,1):
  if isinstance(v,str) and v.startswith('#'):
   errs.append({'cell':f'{num_to_col(ci)}{ri}','value':v})
# confirm restored formulas exist in AAG/AAV.
restore_missing=[]
for col in ['AAG','AAV']:
 for r in range(46,52):
  rng=f"'{TAB}'!{col}{r}"
  val=batch_get([rng],'FORMULA')[0].get('values',[[None]])[0][0]
  if not (isinstance(val,str) and val.startswith('=')):
   restore_missing.append(rng)
# numeric reconciliation for CP lower table.
cp_source_rev=round(float(cp['Receita'].sum()),2); cp_source_spend=round(float(cp['Gasto'].sum()),2)
# read unformatted summary rows ABM103:ABN108
summary=batch_get([f"'{TAB}'!ABM103:ABN108"],'UNFORMATTED_VALUE')[0].get('values',[])
cp_sum_spend=round(sum(float((row+[0,0])[0] or 0) for row in summary),2)
cp_sum_rev=round(sum(float((row+[0,0])[1] or 0) for row in summary),2)
audit={'ok': not errs and not restore_missing and cp_source_rev==cp_sum_rev and cp_source_spend==cp_sum_spend,
       'backup':str(BACKUP),'batch_response':resp,'formula_errors':errs[:50],'formula_error_count':len(errs),
       'restored_formula_missing':restore_missing,'cp_rows':len(cp_rows),'cp_source_rev':cp_source_rev,'cp_summary_rev':cp_sum_rev,'cp_source_spend':cp_source_spend,'cp_summary_spend':cp_sum_spend,
       'forms':forms,'formatted_samples':fmt}
AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:audit[k] for k in ['ok','backup','formula_error_count','restored_formula_missing','cp_rows','cp_source_rev','cp_summary_rev','cp_source_spend','cp_summary_spend']},ensure_ascii=False,indent=2))
print('audit',AUDIT)
