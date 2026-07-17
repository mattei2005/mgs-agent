#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import json, pathlib, urllib.parse, urllib.request, urllib.error, time, datetime, math, re
from collections import defaultdict
import pandas as pd

SID='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
TAB='Julho 2026'
TOKEN=pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
OUT=pathlib.Path('/root/mgs-agent/work/july-2026-fill-7')
LONG=OUT/'Long.csv'
PREV_LONG=pathlib.Path('/root/mgs-agent/work/july-2026-fill-1-6/Long.csv')
BACKUP=OUT/f"backup-before-master-fill-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
AUDIT=OUT/f"master-fill-audit-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
DATE_FROM='2026-07-07'
DATE_TO='2026-07-07'

REV_COL={
 ('conectageral.com','us'): 'D',
 ('cliquet.com','us'): 'JU',
 ('creditoparaveiculo.com','br'): 'ABK',
 ('de.newsoun.com','de'): 'MQ',
 ('ducapes.com','us'): 'SL',
 ('eggbev.com','us'): 'IJ',
 ('finance.ducapes.com','us'): 'TA',
 ('finance.topfeed.fun','us'): 'AW', ('finance.topfeed.fun','gb'): 'BD', ('finance.topfeed.fun','br'): 'AW',
 ('finance.wantabrand.com','gb'): 'CO',
 ('financeadx.com','us'): 'QP', ('financeadx.com','ca'): 'QX', ('financeadx.com','mx'): 'RF', ('financeadx.com','ar'): 'RN', ('financeadx.com','za'): 'RV',
 ('finanzas.cliquet.com','us'): 'KQ',
 ('finanzas.eggbev.com','us'): 'JF',
 ('finanzas.lyzmo.com','us'): 'HU',
 ('finanzas.newsoun.com','us'): 'MB',
 ('finanzas.openzed.com','us'): 'OB', ('finanzas.openzed.com','es'): 'OI',
 ('finanzas.topfeed.fun','us'): 'BS',
 ('finanzas.zuout.com','us'): 'GJ',
 ('finanzas.zytiva.com','us'): 'PT', ('finanzas.zytiva.com','es'): 'QA',
 ('fincgriffin.com','us'): 'TP',
 ('gamezonead.com','br'): 'AAV',
 ('gamingadx.com','us'): 'AAG',
 ('helixenit.com','de'): 'US', ('helixenit.com','us'): 'VA', ('helixenit.com','mx'): 'VI',
 ('infinitynexx.com','us'): 'YK', ('infinitynexx.com','mx'): 'YS',
 ('lyzmo.com','us'): 'GY', ('lyzmo.com','gb'): 'HF',
 ('marevelx.com','de'): 'VY', ('marevelx.com','us'): 'WG', ('marevelx.com','mx'): 'WO',
 ('newsoun.com','us'): 'LF', ('newsoun.com','gb'): 'LM',
 ('openzed.com','us'): 'NF', ('openzed.com','gb'): 'NM',
 ('portalrelevante.com','us'): 'S',
 ('seuprimeiroempregoam.com','us'): 'DS',
 ('vizioid.com','us'): 'ZI', ('vizioid.com','mx'): 'ZQ',
 ('wantabrand.com','us'): 'DD',
 ('xyvlov.com','de'): 'XE', ('xyvlov.com','us'): 'XM', ('xyvlov.com','mx'): 'XU',
 ('zuout.com','us'): 'FN', ('zuout.com','gb'): 'FU',
 ('zytiva.com','us'): 'OX', ('zytiva.com','gb'): 'PE',
}
ICARO_REV_COL={('openzed.com','us','g001-d'): 'NF', ('openzed.com','gb','g001-d'): 'NM'}
# Spend columns validated from live monthly sheet patterns. Google Ads BRL writes only into R$ input columns.
SPEND_COL={
 'creditoparaveiculo.com':'ABK',
 'gamezonead.com':'AAW',
 'gamingadx.com':'AAH',
 'helixenit.com':'VM',
 'eggbev.com':'IJ',
 'finance.topfeed.fun':'AW',
 'infinitynexx.com':'ZA',
}
MANAGERS=[f'g00{i}-d' for i in range(1,7)]

def token():
    c=json.loads(TOKEN.read_text())
    body=urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
    req=urllib.request.Request('https://oauth2.googleapis.com/token',data=body,headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)['access_token']
ACCESS=token()

def api(method,url,data=None,timeout=180):
    h={'Authorization':'Bearer '+ACCESS}; body=None
    if data is not None:
        body=json.dumps(data).encode(); h['Content-Type']='application/json; charset=UTF-8'
    last=None
    for attempt in range(6):
        try:
            req=urllib.request.Request(url,method=method,headers=h,data=body)
            with urllib.request.urlopen(req,timeout=timeout) as r:
                raw=r.read(); return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw=e.read().decode(errors='ignore')[:1000]
            last=f'HTTP {e.code}: {raw}'
            if e.code in (429,500,502,503,504) and attempt<5:
                time.sleep(5*(attempt+1)); continue
            raise RuntimeError(last)

def q(s): return urllib.parse.quote(s,safe='')
def get(rng, render='FORMATTED_VALUE'):
    return api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/{q(rng)}?valueRenderOption={render}').get('values',[])
def batch_get(ranges, render='FORMATTED_VALUE'):
    params=urllib.parse.urlencode([('ranges',r) for r in ranges]+[('valueRenderOption',render)])
    return api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values:batchGet?{params}').get('valueRanges',[])
def batch_update(data):
    return api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values:batchUpdate', {'valueInputOption':'USER_ENTERED', 'data': data})

def col_to_num(c):
    n=0
    for ch in c:
        n=n*26+ord(ch.upper())-64
    return n
def num_to_col(n):
    s=''
    while n:
        n-=1; s=chr(65+n%26)+s; n//=26
    return s
def country(vertical):
    v=str(vertical).lower()
    return v.split('-')[0] if '-' in v else v

def date_to_rows(d):
    day=pd.Timestamp(d).day
    return 4+day, 45+day, 104+day, 145+day

def load_long(path):
    df=pd.read_csv(path)
    df['Data']=pd.to_datetime(df['Data']).dt.date.astype(str)
    return df

long=load_long(LONG)
long=long[(long['Data']>=DATE_FROM) & (long['Data']<=DATE_TO)].copy()
combined=long.copy()
if PREV_LONG.exists():
    prev=load_long(PREV_LONG)
    prev=prev[(prev['Data']>='2026-07-01') & (prev['Data']<=DATE_TO)].copy()
    combined=pd.concat([prev,long], ignore_index=True)

revenue_cells=defaultdict(float)
spend_cells=defaultdict(float)
unmapped=[]

for _,r in long.iterrows():
    site=str(r['Site']); cc=country(r['Vertical']); gestor=str(r['Gestor'])
    receita=float(r['Receita'] or 0); gasto=float(r['Gasto'] or 0)
    rev_row, spend_row, icaro_row, lower_spend_row = date_to_rows(r['Data'])
    if abs(receita)>1e-12:
        if site=='openzed.com' and gestor=='g001-d':
            col=ICARO_REV_COL.get((site,cc,gestor))
            if not col: unmapped.append({'type':'revenue-icaro','row':r.to_dict()})
            else: revenue_cells[f"'{TAB}'!{col}{icaro_row}"] += receita
        else:
            key=(site, cc)
            col=REV_COL.get(key)
            if not col: unmapped.append({'type':'revenue','key':key,'row':r.to_dict()})
            else: revenue_cells[f"'{TAB}'!{col}{rev_row}"] += receita
    if abs(gasto)>1e-12:
        col=SPEND_COL.get(site)
        if not col: unmapped.append({'type':'spend','site':site,'row':r.to_dict()})
        else: spend_cells[f"'{TAB}'!{col}{spend_row}"] += gasto

if unmapped:
    raise SystemExit(json.dumps({'ok':False,'reason':'unmapped source rows','unmapped':unmapped[:80]},ensure_ascii=False,indent=2))

# Rebuild Fincgriffin detail table for 1..7 so prior days are preserved and day 7 is appended deterministically.
finc_src=combined[(combined['Site']=='fincgriffin.com') & (combined['Data']>='2026-07-01') & (combined['Data']<=DATE_TO)]
finc_by=defaultdict(lambda:{'gasto':0.0,'receita':0.0})
for _,r in finc_src.iterrows():
    finc_by[(r['Data'],r['Gestor'])]['gasto'] += float(r['Gasto'] or 0)
    finc_by[(r['Data'],r['Gestor'])]['receita'] += float(r['Receita'] or 0)
finc_rows=[]
for (date,gestor),v in sorted(finc_by.items()):
    idx=112+len(finc_rows)
    lucro=v['receita']-v['gasto']
    finc_rows.append([date,gestor,round(v['gasto'],10),round(v['receita'],10),round(lucro,10),f'=IFERROR(TU{idx}/TS{idx},"")'])

# Rebuild Creditoparaveiculo lower table for 1..7.
cp_src=combined[(combined['Site']=='creditoparaveiculo.com') & (combined['Data']>='2026-07-01') & (combined['Data']<=DATE_TO)]
cp_by=defaultdict(lambda:{'gasto':0.0,'receita':0.0})
for _,r in cp_src.iterrows():
    cp_by[(r['Data'],r['Gestor'])]['gasto'] += float(r['Gasto'] or 0)
    cp_by[(r['Data'],r['Gestor'])]['receita'] += float(r['Receita'] or 0)
cp_rows=[]
for (date,gestor),v in sorted(cp_by.items()):
    idx=112+len(cp_rows)
    lucro=v['receita']-v['gasto']
    cp_rows.append([date,gestor,round(v['gasto'],10),round(v['receita'],10),round(lucro,10),f'=IFERROR(ABP{idx}/ABN{idx},"")'])

rev_cols=set(REV_COL.values()) | {'NF','NM'}
spend_cols=set(SPEND_COL.values())
updates=[]
# Clear/write only day 7 rows. Do not clear formula conversion columns in spend rows unless they are actual input columns.
for c in sorted(rev_cols, key=col_to_num):
    updates.append({'range':f"'{TAB}'!{c}11", 'values':[['']]})
for c in sorted(spend_cols, key=col_to_num):
    updates.append({'range':f"'{TAB}'!{c}52", 'values':[['']]})
# Lower Openzed/Icaro day 7 revenue + spend input rows.
for c in ['NF','NM']:
    updates.append({'range':f"'{TAB}'!{c}111", 'values':[['']]})
for c in ['NF','NH','NJ','NL','NN','NP','NR','NT','NV']:
    updates.append({'range':f"'{TAB}'!{c}152", 'values':[['']]})
# Rebuild Finc and CP lower tables (clear sufficient detail regions first).
updates.append({'range':f"'{TAB}'!TQ103:TQ108", 'values':[[m] for m in MANAGERS]})
updates.append({'range':f"'{TAB}'!TQ112:TV275", 'values':[['','','','','',''] for _ in range(164)]})
if finc_rows:
    updates.append({'range':f"'{TAB}'!TQ112:TV{111+len(finc_rows)}", 'values':finc_rows})
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

for rng,val in sorted(revenue_cells.items()):
    updates.append({'range':rng,'values':[[round(val,10)]]})
for rng,val in sorted(spend_cells.items()):
    updates.append({'range':rng,'values':[[round(val,10)]]})

backup_ranges=[f"'{TAB}'!A1:AIH180", f"'{TAB}'!TQ100:TV275", f"'{TAB}'!ABL100:ABQ180"]
backup={'created_at':datetime.datetime.now().isoformat(timespec='seconds'), 'ranges':backup_ranges,
        'formatted': batch_get(backup_ranges,'FORMATTED_VALUE'), 'formulas': batch_get(backup_ranges,'FORMULA'),
        'intended_updates': len(updates), 'expected_revenue_cells': dict(revenue_cells), 'expected_spend_cells': dict(spend_cells), 'finc_rows':finc_rows, 'cp_rows':cp_rows}
BACKUP.write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding='utf-8')

resp=batch_update(updates)

expected={}
expected.update({k:round(v,2) for k,v in revenue_cells.items()})
expected.update({k:round(v,2) for k,v in spend_cells.items()})
read_ranges=list(expected.keys()) + [f"'{TAB}'!AAG52", f"'{TAB}'!AAV52", f"'{TAB}'!TQ112:TV{111+len(finc_rows)}", f"'{TAB}'!ABL112:ABQ{111+len(cp_rows)}"]
read=batch_get(read_ranges,'UNFORMATTED_VALUE')
read_map={vr['range']:vr.get('values',[]) for vr in read}
mismatches=[]
for rng,exp in expected.items():
    vals=read_map.get(rng,[])
    got=vals[0][0] if vals and vals[0] else 0
    try: got_num=round(float(got or 0),2)
    except Exception: got_num=got
    if got_num!=exp:
        mismatches.append({'range':rng,'expected':exp,'got':got})
# Formula error scan.
vals=get(f"'{TAB}'!A1:AIH275",'FORMATTED_VALUE')
formula_errors=[]
for ri,row in enumerate(vals,1):
    for ci,v in enumerate(row,1):
        if isinstance(v,str) and v.startswith('#'):
            formula_errors.append({'cell':f'{num_to_col(ci)}{ri}','value':v})
# Ensure BRL neighboring USD conversion formulas survived.
forms=batch_get([f"'{TAB}'!AAG52", f"'{TAB}'!AAV52"], 'FORMULA')
formula_checks={vr['range']: (vr.get('values',[[None]])[0][0] if vr.get('values') and vr.get('values')[0] else '') for vr in forms}
missing_conversion=[rng for rng,val in formula_checks.items() if not (isinstance(val,str) and val.startswith('='))]
# Source totals vs mapped totals.
source_rev=round(float(long['Receita'].sum()),2); source_spend=round(float(long['Gasto'].sum()),2)
mapped_rev=round(sum(float(v) for v in revenue_cells.values()),2); mapped_spend=round(sum(float(v) for v in spend_cells.values()),2)
# Detail table reconciliations.
cp_detail_rev=round(sum(v['receita'] for v in cp_by.values()),2); cp_detail_spend=round(sum(v['gasto'] for v in cp_by.values()),2)
finc_detail_rev=round(sum(v['receita'] for v in finc_by.values()),2); finc_detail_spend=round(sum(v['gasto'] for v in finc_by.values()),2)
audit={
    'ok': not mismatches and not formula_errors and not missing_conversion and source_rev==mapped_rev and source_spend==mapped_spend,
    'backup':str(BACKUP),'batch_response':resp,
    'source_rev':source_rev,'mapped_rev':mapped_rev,'source_spend':source_spend,'mapped_spend':mapped_spend,
    'revenue_cells':len(revenue_cells),'spend_cells':len(spend_cells),'updates_sent':len(updates),
    'mismatches':mismatches,'formula_errors':formula_errors[:50],'formula_error_count':len(formula_errors),
    'conversion_formula_checks':formula_checks,'missing_conversion_formulas':missing_conversion,
    'finc_rows':len(finc_rows),'finc_detail_rev_1_7':finc_detail_rev,'finc_detail_spend_1_7':finc_detail_spend,
    'cp_rows':len(cp_rows),'cp_detail_rev_1_7':cp_detail_rev,'cp_detail_spend_1_7':cp_detail_spend,
    'expected_revenue_cells':dict(revenue_cells),'expected_spend_cells':dict(spend_cells),
}
AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:audit[k] for k in ['ok','backup','source_rev','mapped_rev','source_spend','mapped_spend','revenue_cells','spend_cells','updates_sent','formula_error_count','mismatches','missing_conversion_formulas','finc_rows','cp_rows']},ensure_ascii=False,indent=2))
print('audit',AUDIT)
