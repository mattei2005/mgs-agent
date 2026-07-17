#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import json, pathlib, urllib.parse, urllib.request, urllib.error, time, datetime, math, re
from collections import defaultdict
import pandas as pd

SID='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
TAB='Julho 2026'
TOKEN=pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
OUT=pathlib.Path('/root/mgs-agent/work/july-2026-fill-1-6')
LONG=OUT/'Long.csv'
BACKUP=OUT/f"backup-before-master-fill-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
AUDIT=OUT/f"master-fill-audit-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

# Manual mapping validated from the live Julho 2026 sheet headers and MGS finance skills.
CAD_SITES={'financeadx.com','helixenit.com','infinitynexx.com','marevelx.com','vizioid.com','xyvlov.com'}
REV_COL={
 ('conectageral.com','us'): 'D',
 ('cliquet.com','us'): 'JU',
 ('creditoparaveiculo.com','br'): 'ABK',
 ('de.newsoun.com','de'): 'MQ',
 ('ducapes.com','us'): 'SL',
 ('eggbev.com','us'): 'IJ',
 ('finance.ducapes.com','us'): 'TA',
 ('finance.topfeed.fun','us'): 'AW', ('finance.topfeed.fun','gb'): 'BD',
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
# Special lower Openzed/Icaro block: row 105..135, same day offset, columns NF/NM there.
ICARO_REV_COL={('openzed.com','us','g001-d'): 'NF', ('openzed.com','gb','g001-d'): 'NM'}
SPEND_COL={
 'creditoparaveiculo.com':'ABK',
 'gamezonead.com':'AAW',
 'gamingadx.com':'AAH',
 # Only one Helixenit MX spend account in this report; first MX BM-$ input under Helixenit block.
 'helixenit.com':'VM',
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
    return api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values:batchUpdate', {
        'valueInputOption':'USER_ENTERED', 'data': data
    })

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
    if '-' in v: return v.split('-')[0]
    return v

def date_to_rows(d):
    day=pd.Timestamp(d).day
    return 4+day, 45+day, 104+day, 145+day

def add_value(cells, rng, val):
    cells[rng]=float(cells.get(rng,0) or 0)+float(val)

long=pd.read_csv(LONG)
long['Data']=pd.to_datetime(long['Data']).dt.date.astype(str)
long=long[(long['Data']>='2026-07-01') & (long['Data']<='2026-07-06')].copy()

revenue_cells=defaultdict(float)
spend_cells=defaultdict(float)
finc_details=[]
unmapped=[]

for _,r in long.iterrows():
    site=str(r['Site']); cc=country(r['Vertical']); gestor=str(r['Gestor'])
    receita=float(r['Receita'] or 0); gasto=float(r['Gasto'] or 0)
    rev_row, spend_row, icaro_row, _ = date_to_rows(r['Data'])
    if abs(receita)>1e-12:
        if site=='openzed.com' and gestor=='g001-d':
            col=ICARO_REV_COL.get((site,cc,gestor))
            if not col: unmapped.append({'type':'revenue-icaro','row':r.to_dict()})
            else: revenue_cells[f"'{TAB}'!{col}{icaro_row}"] += receita
        else:
            # Aggregate creditoparaveiculo and fincgriffin by day/site; gestor splits handled only in finc lower table.
            key=(site, cc)
            col=REV_COL.get(key)
            if not col: unmapped.append({'type':'revenue','key':key,'row':r.to_dict()})
            else: revenue_cells[f"'{TAB}'!{col}{rev_row}"] += receita
        if site=='fincgriffin.com':
            finc_details.append({'date':r['Data'],'gestor':gestor,'gasto':0.0,'receita':receita})
    if abs(gasto)>1e-12:
        col=SPEND_COL.get(site)
        if not col: unmapped.append({'type':'spend','site':site,'row':r.to_dict()})
        else: spend_cells[f"'{TAB}'!{col}{spend_row}"] += gasto
        if site=='fincgriffin.com':
            finc_details.append({'date':r['Data'],'gestor':gestor,'gasto':gasto,'receita':0.0})

if unmapped:
    raise SystemExit(json.dumps({'ok':False,'reason':'unmapped source rows','unmapped':unmapped[:50]},ensure_ascii=False,indent=2))

# Merge Finc details by date+gestor.
finc_by=defaultdict(lambda:{'gasto':0.0,'receita':0.0})
for d in finc_details:
    k=(d['date'],d['gestor'])
    finc_by[k]['gasto']+=d['gasto']; finc_by[k]['receita']+=d['receita']
finc_rows=[]
for (date,gestor),v in sorted(finc_by.items()):
    lucro=v['receita']-v['gasto']
    margem='' if abs(v['gasto'])<1e-12 else lucro/v['gasto']
    finc_rows.append([date, gestor, round(v['gasto'],10), round(v['receita'],10), round(lucro,10), margem])

# Clear all input cells in touched 1..6 day rows for every known mapping column, then write computed values.
clear_cols=set(REV_COL.values()) | set(SPEND_COL.values()) | {'NF','NM'}
updates=[]
for c in sorted(clear_cols, key=col_to_num):
    updates.append({'range':f"'{TAB}'!{c}5:{c}10", 'values':[[''] for _ in range(6)]})
    updates.append({'range':f"'{TAB}'!{c}46:{c}51", 'values':[[''] for _ in range(6)]})
# lower Openzed/Icaro revenue/spend input columns for days 1..6
for c in ['NF','NM','NI','NP']:
    updates.append({'range':f"'{TAB}'!{c}105:{c}110", 'values':[[''] for _ in range(6)]})
for c in ['NF','NH','NJ','NL','NN','NP','NR','NT']:
    updates.append({'range':f"'{TAB}'!{c}146:{c}151", 'values':[[''] for _ in range(6)]})
# Finc summary labels and detail table cleanup/fill.
updates.append({'range':f"'{TAB}'!TQ103:TQ108", 'values':[[m] for m in MANAGERS]})
updates.append({'range':f"'{TAB}'!TQ112:TV275", 'values':[['','','','','',''] for _ in range(164)]})
if finc_rows:
    updates.append({'range':f"'{TAB}'!TQ112:TV{111+len(finc_rows)}", 'values':finc_rows})
# Write revenue/spend cells. Group by contiguous rows? Simpler one-cell updates; still one batchUpdate request.
for rng,val in sorted(revenue_cells.items()):
    updates.append({'range':rng,'values':[[round(val,10)]]})
for rng,val in sorted(spend_cells.items()):
    updates.append({'range':rng,'values':[[round(val,10)]]})

backup_ranges=[f"'{TAB}'!A1:AIH180", f"'{TAB}'!TQ100:TV275"]
backup={'created_at':datetime.datetime.now().isoformat(timespec='seconds'), 'ranges':backup_ranges,
        'formatted': batch_get(backup_ranges,'FORMATTED_VALUE'), 'formulas': batch_get(backup_ranges,'FORMULA'),
        'intended_updates': len(updates), 'expected_revenue_cells': dict(revenue_cells), 'expected_spend_cells': dict(spend_cells), 'finc_rows':finc_rows}
BACKUP.write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding='utf-8')

resp=batch_update(updates)

# Verify by readback cells only and formula errors in full used grid.
expected={}
expected.update({k:round(v,2) for k,v in revenue_cells.items()})
expected.update({k:round(v,2) for k,v in spend_cells.items()})
# add finc detail expected for validation in TQ:TV
read_ranges=list(expected.keys())
if finc_rows:
    read_ranges.append(f"'{TAB}'!TQ112:TV{111+len(finc_rows)}")
read_vals=batch_get(read_ranges,'UNFORMATTED_VALUE') if read_ranges else []
values_by_range={vr['range']:vr.get('values',[]) for vr in read_vals}

def coerce(x):
    if x is None or x=='': return 0.0
    try: return float(x)
    except Exception:
        s=str(x).replace('$','').replace('R$','').replace(',','').strip()
        return float(s) if s else 0.0
mismatches=[]
for rng, exp in expected.items():
    got_vals=values_by_range.get(rng,[])
    got=coerce(got_vals[0][0] if got_vals and got_vals[0] else 0)
    if round(got,2)!=round(exp,2):
        mismatches.append({'range':rng,'expected':round(exp,2),'got':round(got,2)})
# formula errors scan
all_vals=get(f"'{TAB}'!A1:AIH275",'FORMATTED_VALUE')
errors=[]
for ri,row in enumerate(all_vals,1):
    for ci,v in enumerate(row,1):
        if isinstance(v,str) and v.startswith('#'):
            errors.append({'cell':f'{num_to_col(ci)}{ri}','value':v})

# Reconcile mapped totals by source totals.
source_rev=round(float(long['Receita'].sum()),2); source_spend=round(float(long['Gasto'].sum()),2)
mapped_rev=round(sum(revenue_cells.values()),2); mapped_spend=round(sum(spend_cells.values()),2)
# Finc detail readback check
finc_mismatches=[]
if finc_rows:
    key=f"'{TAB}'!TQ112:TV{111+len(finc_rows)}"
    got=values_by_range.get(key,[])
    for i,exp_row in enumerate(finc_rows):
        row=got[i] if i < len(got) else []
        # compare date, gestor, gasto, receita, lucro (ignore formatted margin precision)
        for j,name in enumerate(['date','gestor','gasto','receita','lucro']):
            exp=exp_row[j]
            gv=row[j] if j < len(row) else ''
            if j>=2:
                ok=round(coerce(gv),2)==round(float(exp),2)
            else:
                ok=str(gv)==str(exp)
            if not ok: finc_mismatches.append({'row':112+i,'col':name,'expected':exp,'got':gv})

audit={'ok': not mismatches and not errors and not finc_mismatches and source_rev==mapped_rev and source_spend==mapped_spend,
       'backup':str(BACKUP),'batch_response':resp,
       'source_rev':source_rev,'mapped_rev':mapped_rev,'source_spend':source_spend,'mapped_spend':mapped_spend,
       'revenue_cells':len(revenue_cells),'spend_cells':len(spend_cells),'finc_detail_rows':len(finc_rows),
       'updates_sent':len(updates),'mismatches':mismatches,'formula_errors':errors[:50],'formula_error_count':len(errors),'finc_mismatches':finc_mismatches,
       'ambiguous_pages_file':str(OUT/'Paginas_ambiguas.csv')}
AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':audit['ok'],'audit':str(AUDIT),'backup':str(BACKUP),'source_rev':source_rev,'mapped_rev':mapped_rev,'source_spend':source_spend,'mapped_spend':mapped_spend,'revenue_cells':len(revenue_cells),'spend_cells':len(spend_cells),'finc_detail_rows':len(finc_rows),'mismatches':len(mismatches),'formula_errors':len(errors),'finc_mismatches':len(finc_mismatches)},ensure_ascii=False,indent=2))
