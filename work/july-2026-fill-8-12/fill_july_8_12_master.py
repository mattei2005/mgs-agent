#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import datetime, json, math, pathlib, time, urllib.error, urllib.parse, urllib.request
from collections import defaultdict
import pandas as pd

SID = '16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
TAB = 'Julho 2026'
TOKEN = pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
OUT = pathlib.Path('/root/mgs-agent/work/july-2026-fill-8-12')
LONG = OUT / 'Long.csv'
PRIOR_LONGS = [
    pathlib.Path('/root/mgs-agent/work/july-2026-fill-1-6/Long.csv'),
    pathlib.Path('/root/mgs-agent/work/july-2026-fill-7/Long.csv'),
]
DATE_FROM = '2026-07-08'
DATE_TO = '2026-07-12'
STAMP = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
BACKUP = OUT / f'backup-before-master-fill-{STAMP}.json'
AUDIT = OUT / f'master-fill-audit-{STAMP}.json'

REV_COL = {
 ('conectageral.com','us'): 'D', ('cliquet.com','us'): 'JU',
 ('creditoparaveiculo.com','br'): 'ABK', ('de.newsoun.com','de'): 'MQ',
 ('ducapes.com','us'): 'SL', ('eggbev.com','us'): 'IJ',
 ('finance.ducapes.com','us'): 'TA',
 ('finance.topfeed.fun','us'): 'AW', ('finance.topfeed.fun','gb'): 'BD', ('finance.topfeed.fun','br'): 'AW',
 ('finance.wantabrand.com','gb'): 'CO',
 ('financeadx.com','us'): 'QP', ('financeadx.com','ca'): 'QX', ('financeadx.com','mx'): 'RF', ('financeadx.com','ar'): 'RN', ('financeadx.com','za'): 'RV',
 ('finanzas.cliquet.com','us'): 'KQ', ('finanzas.eggbev.com','us'): 'JF',
 ('finanzas.lyzmo.com','us'): 'HU', ('finanzas.newsoun.com','us'): 'MB',
 ('finanzas.openzed.com','us'): 'OB', ('finanzas.openzed.com','es'): 'OI',
 ('finanzas.topfeed.fun','us'): 'BS', ('finanzas.zuout.com','us'): 'GJ',
 ('finanzas.zytiva.com','us'): 'PT', ('finanzas.zytiva.com','es'): 'QA',
 ('fincgriffin.com','us'): 'TP', ('gamezonead.com','br'): 'AAV',
 ('gamingadx.com','us'): 'AAG',
 ('helixenit.com','de'): 'US', ('helixenit.com','us'): 'VA', ('helixenit.com','mx'): 'VI',
 ('infinitynexx.com','us'): 'YK', ('infinitynexx.com','mx'): 'YS',
 ('lyzmo.com','us'): 'GY', ('lyzmo.com','gb'): 'HF',
 ('marevelx.com','de'): 'VY', ('marevelx.com','us'): 'WG', ('marevelx.com','mx'): 'WO',
 ('newsoun.com','us'): 'LF', ('newsoun.com','gb'): 'LM',
 ('openzed.com','us'): 'NF', ('openzed.com','gb'): 'NM',
 ('portalrelevante.com','us'): 'S', ('seuprimeiroempregoam.com','us'): 'DS',
 ('vizioid.com','us'): 'ZI', ('vizioid.com','mx'): 'ZQ',
 ('wantabrand.com','us'): 'DD',
 ('xyvlov.com','de'): 'XE', ('xyvlov.com','us'): 'XM', ('xyvlov.com','mx'): 'XU',
 ('zuout.com','us'): 'FN', ('zuout.com','gb'): 'FU',
 ('zytiva.com','us'): 'OX', ('zytiva.com','gb'): 'PE',
}
ICARO_REV_COL = {('openzed.com','us','g001-d'): 'NF', ('openzed.com','gb','g001-d'): 'NM'}

# Account-level routing. Existing July assignments from the 1–7 fill are preserved
# for accounts already used there; new accounts use the next manual BM-$ slot.
ACCOUNT_SPEND_COL = {
 'mattei 1 (google ads - brl)': 'AAW',
 'gamingadx-us-01 (google ads - brl)': 'AAH',
 'topfeed-br-car-br-01': 'AW',
 'infinitynexx-mx-cc-es-01': 'ZA',
 'eggbev-us-cc-en-03 (fax-us-02)': 'IJ',
 'eggbev-br-car-br-01': 'IN',
 'helixenit-mx-cc-es-01': 'VM',
 'openzed-us-cc-en-01': 'NF',
 'openzed-br-car-br-01': 'NH',
 'openzedfinanzas-es-cc-es-03': 'ON',
 'topfeedfinanzas-us-cc-es-01': 'BS',
 'wantabrand-us-cc-es-01': 'DD',
 'wantabrand-br-car-br-01': 'DH',
 'newsoun-us-cc-en-02': 'LH',
 'newsoun-br-car-br-01': 'LJ',
 'fincgriffin-us-car-en-01 g005': 'TP',
 'cliquet-br-car-br-01': 'JW',
}
MANAGERS = [f'g00{i}-d' for i in range(1, 7)]

def token():
    c = json.loads(TOKEN.read_text())
    body = urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=body, headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)['access_token']
ACCESS = token()

def api(method, url, data=None, timeout=180):
    headers = {'Authorization':'Bearer ' + ACCESS}; body = None
    if data is not None:
        body = json.dumps(data).encode(); headers['Content-Type'] = 'application/json; charset=UTF-8'
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, method=method, headers=headers, data=body)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(); return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            msg = f'HTTP {e.code}: {e.read().decode(errors="ignore")[:1000]}'
            if e.code in (429,500,502,503,504) and attempt < 5:
                time.sleep(5 * (attempt + 1)); continue
            raise RuntimeError(msg)

def q(s): return urllib.parse.quote(s, safe='')
def get(rng, render='FORMATTED_VALUE'):
    return api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/{q(rng)}?valueRenderOption={render}').get('values', [])
def batch_get(ranges, render='FORMATTED_VALUE'):
    params = urllib.parse.urlencode([('ranges', r) for r in ranges] + [('valueRenderOption', render)])
    return api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values:batchGet?{params}').get('valueRanges', [])
def batch_update(data):
    return api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{SID}/values:batchUpdate', {'valueInputOption':'USER_ENTERED','data':data})
def col_num(c):
    n = 0
    for ch in c: n = n * 26 + ord(ch.upper()) - 64
    return n
def num_col(n):
    s = ''
    while n: n -= 1; s = chr(65 + n % 26) + s; n //= 26
    return s
def country(vertical):
    v = str(vertical).lower(); return v.split('-')[0] if '-' in v else v
def rows_for(date):
    day = pd.Timestamp(date).day
    return 4 + day, 45 + day, 104 + day, 145 + day
def load_long(path):
    df = pd.read_csv(path); df['Data'] = pd.to_datetime(df['Data']).dt.date.astype(str); return df
def norm_account(v): return ' '.join(str(v).strip().lower().split())
def date_serial_to_iso(v):
    if isinstance(v, (int,float)) and not isinstance(v, bool):
        return (datetime.date(1899,12,30) + datetime.timedelta(days=int(v))).isoformat()
    try: return pd.Timestamp(v).date().isoformat()
    except Exception: return str(v)

long = load_long(LONG)
long = long[(long['Data'] >= DATE_FROM) & (long['Data'] <= DATE_TO)].copy()
parts = []
for p in PRIOR_LONGS:
    if p.exists(): parts.append(load_long(p))
parts.append(long)
combined = pd.concat(parts, ignore_index=True)
combined = combined[(combined['Data'] >= '2026-07-01') & (combined['Data'] <= DATE_TO)].copy()

revenue_cells = defaultdict(float); spend_cells = defaultdict(float); unmapped = []
for _, r in long.iterrows():
    site, cc, gestor = str(r['Site']), country(r['Vertical']), str(r['Gestor'])
    receita, gasto = float(r['Receita'] or 0), float(r['Gasto'] or 0)
    rev_row, spend_row, icaro_row, _ = rows_for(r['Data'])
    if abs(receita) > 1e-12:
        if site == 'openzed.com' and gestor == 'g001-d':
            col = ICARO_REV_COL.get((site, cc, gestor)); typ = 'revenue-icaro'
            rownum = icaro_row
        else:
            col = REV_COL.get((site, cc)); typ = 'revenue'; rownum = rev_row
        if not col: unmapped.append({'type':typ,'site':site,'vertical':r['Vertical'],'gestor':gestor,'date':r['Data'],'value':receita})
        else: revenue_cells[f"'{TAB}'!{col}{rownum}"] += receita
    if abs(gasto) > 1e-12:
        acct = norm_account(r['Conta_FB'])
        if site == 'creditoparaveiculo.com': col = 'ABK'
        else: col = ACCOUNT_SPEND_COL.get(acct)
        if not col: unmapped.append({'type':'spend','site':site,'vertical':r['Vertical'],'account':r['Conta_FB'],'date':r['Data'],'value':gasto})
        else: spend_cells[f"'{TAB}'!{col}{spend_row}"] += gasto
if unmapped:
    raise SystemExit(json.dumps({'ok':False,'reason':'unmapped source rows','unmapped':unmapped}, ensure_ascii=False, indent=2))

# Rebuild manager detail tables from the reconciled 1–12 July Long sources.
def manager_rows(site, first_row, profit_col, spend_col):
    src = combined[combined['Site'] == site]
    by = defaultdict(lambda:{'gasto':0.0,'receita':0.0})
    for _, r in src.iterrows():
        by[(r['Data'],r['Gestor'])]['gasto'] += float(r['Gasto'] or 0)
        by[(r['Data'],r['Gestor'])]['receita'] += float(r['Receita'] or 0)
    rows = []
    for (date, gestor), v in sorted(by.items()):
        idx = first_row + len(rows); lucro = v['receita'] - v['gasto']
        rows.append([date,gestor,round(v['gasto'],10),round(v['receita'],10),round(lucro,10),f'=IFERROR({profit_col}{idx}/{spend_col}{idx},"")'])
    return rows, by
finc_rows, finc_by = manager_rows('fincgriffin.com', 112, 'TU', 'TS')
cp_rows, cp_by = manager_rows('creditoparaveiculo.com', 112, 'ABP', 'ABN')
if len(finc_rows) > 164 or len(cp_rows) > 69:
    raise SystemExit('Mini-table capacity exceeded; no write performed')

rev_cols = set(REV_COL.values()) | {'NF','NM'}
spend_cols = set(ACCOUNT_SPEND_COL.values()) | {'ABK'}
updates = []
# Clear only requested dates 8–12, then repopulate from the source report.
for c in sorted(rev_cols, key=col_num):
    updates.append({'range':f"'{TAB}'!{c}12:{c}16",'values':[[''] for _ in range(5)]})
for c in sorted(spend_cols, key=col_num):
    updates.append({'range':f"'{TAB}'!{c}53:{c}57",'values':[[''] for _ in range(5)]})
for c in ['NF','NM']:
    updates.append({'range':f"'{TAB}'!{c}112:{c}116",'values':[[''] for _ in range(5)]})
for c in ['NF','NH','NJ','NL','NN','NP','NR','NT','NV']:
    updates.append({'range':f"'{TAB}'!{c}153:{c}157",'values':[[''] for _ in range(5)]})
# Rebuild Fincgriffin and Creditoparaveiculo lower tables through 12 July.
updates.append({'range':f"'{TAB}'!TQ112:TV275",'values':[['','','','','',''] for _ in range(164)]})
updates.append({'range':f"'{TAB}'!TQ112:TV{111+len(finc_rows)}",'values':finc_rows})
updates.append({'range':f"'{TAB}'!ABL112:ABQ180",'values':[['','','','','',''] for _ in range(69)]})
updates.append({'range':f"'{TAB}'!ABL112:ABQ{111+len(cp_rows)}",'values':cp_rows})
for rng, value in sorted(revenue_cells.items()): updates.append({'range':rng,'values':[[round(value,10)]]})
for rng, value in sorted(spend_cells.items()): updates.append({'range':rng,'values':[[round(value,10)]]})

backup_ranges = [f"'{TAB}'!A1:AIH180",f"'{TAB}'!TQ100:TV275",f"'{TAB}'!ABL100:ABQ180"]
backup = {
 'created_at':datetime.datetime.now().isoformat(timespec='seconds'),'source_period':[DATE_FROM,DATE_TO],
 'ranges':backup_ranges,'formatted':batch_get(backup_ranges,'FORMATTED_VALUE'),'formulas':batch_get(backup_ranges,'FORMULA'),
 'intended_updates':len(updates),'expected_revenue_cells':dict(revenue_cells),'expected_spend_cells':dict(spend_cells),
 'finc_rows':finc_rows,'cp_rows':cp_rows,'account_spend_mapping':ACCOUNT_SPEND_COL,
}
BACKUP.write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding='utf-8')
response = batch_update(updates)

expected = {**{k:round(v,2) for k,v in revenue_cells.items()},**{k:round(v,2) for k,v in spend_cells.items()}}
read_ranges = list(expected) + [f"'{TAB}'!TQ112:TV{111+len(finc_rows)}",f"'{TAB}'!ABL112:ABQ{111+len(cp_rows)}"]
read = batch_get(read_ranges,'UNFORMATTED_VALUE'); read_map = {vr['range']:vr.get('values',[]) for vr in read}
mismatches = []
for rng, exp in expected.items():
    vals = read_map.get(rng,[]); got = vals[0][0] if vals and vals[0] else 0
    try: got_num = round(float(got or 0),2)
    except Exception: got_num = got
    if got_num != exp: mismatches.append({'range':rng,'expected':exp,'got':got})

def compare_detail(rng, expected_rows):
    got_rows = read_map.get(rng,[]); out = []
    for i, erow in enumerate(expected_rows):
        grow = got_rows[i] if i < len(got_rows) else []
        for j, name in enumerate(['date','gestor','gasto','receita','lucro']):
            got = grow[j] if j < len(grow) else ''
            if j == 0: ok = date_serial_to_iso(got) == erow[0]
            elif j == 1: ok = str(got) == str(erow[1])
            else:
                try: ok = round(float(got or 0),2) == round(float(erow[j]),2)
                except Exception: ok = False
            if not ok: out.append({'row':112+i,'field':name,'expected':erow[j],'got':got})
    return out
finc_rng = f"'{TAB}'!TQ112:TV{111+len(finc_rows)}"; cp_rng = f"'{TAB}'!ABL112:ABQ{111+len(cp_rows)}"
finc_mismatches = compare_detail(finc_rng,finc_rows); cp_mismatches = compare_detail(cp_rng,cp_rows)

vals = get(f"'{TAB}'!A1:AIH275",'FORMATTED_VALUE'); formula_errors = []
for ri,row in enumerate(vals,1):
    for ci,v in enumerate(row,1):
        if isinstance(v,str) and v.startswith('#'): formula_errors.append({'cell':f'{num_col(ci)}{ri}','value':v})
conversion_ranges = [f"'{TAB}'!AAG{r}" for r in range(53,58)] + [f"'{TAB}'!AAV{r}" for r in range(53,58)]
forms = batch_get(conversion_ranges,'FORMULA')
formula_checks = {vr['range']:(vr.get('values',[[None]])[0][0] if vr.get('values') and vr.get('values')[0] else '') for vr in forms}
missing_conversion = [rng for rng,val in formula_checks.items() if not (isinstance(val,str) and val.startswith('='))]
summary_ranges = [f"'{TAB}'!TR{r}:TU{r}" for r in range(103,109)] + [f"'{TAB}'!ABM{r}:ABP{r}" for r in range(103,109)]
summary_forms = batch_get(summary_ranges,'FORMULA')
missing_summary = []
for vr in summary_forms:
    row = (vr.get('values') or [[]])[0]
    if len(row) < 4 or any(not (isinstance(v,str) and v.startswith('=')) for v in row[:4]): missing_summary.append(vr['range'])
source_rev, source_spend = round(float(long['Receita'].sum()),2), round(float(long['Gasto'].sum()),2)
mapped_rev, mapped_spend = round(sum(revenue_cells.values()),2), round(sum(spend_cells.values()),2)
per_day_source = long.groupby('Data')[['Receita','Gasto']].sum().round(2).to_dict('index')

audit = {
 'ok':not mismatches and not finc_mismatches and not cp_mismatches and not formula_errors and not missing_conversion and not missing_summary and source_rev==mapped_rev and source_spend==mapped_spend,
 'backup':str(BACKUP),'batch_response':response,'source_period':[DATE_FROM,DATE_TO],
 'source_rev':source_rev,'mapped_rev':mapped_rev,'source_spend':source_spend,'mapped_spend':mapped_spend,
 'per_day_source':per_day_source,'revenue_cells':len(revenue_cells),'spend_cells':len(spend_cells),'updates_sent':len(updates),
 'mismatches':mismatches,'finc_mismatches':finc_mismatches,'cp_mismatches':cp_mismatches,
 'formula_error_count':len(formula_errors),'formula_errors':formula_errors[:100],
 'conversion_formula_checks':formula_checks,'missing_conversion_formulas':missing_conversion,'missing_summary_formulas':missing_summary,
 'finc_rows':len(finc_rows),'cp_rows':len(cp_rows),
 'finc_detail_rev_1_12':round(sum(v['receita'] for v in finc_by.values()),2),'finc_detail_spend_1_12':round(sum(v['gasto'] for v in finc_by.values()),2),
 'cp_detail_rev_1_12':round(sum(v['receita'] for v in cp_by.values()),2),'cp_detail_spend_1_12':round(sum(v['gasto'] for v in cp_by.values()),2),
 'expected_revenue_cells':dict(revenue_cells),'expected_spend_cells':dict(spend_cells),
}
AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:audit[k] for k in ['ok','backup','source_period','source_rev','mapped_rev','source_spend','mapped_spend','per_day_source','revenue_cells','spend_cells','updates_sent','formula_error_count','mismatches','finc_mismatches','cp_mismatches','missing_conversion_formulas','missing_summary_formulas','finc_rows','cp_rows']},ensure_ascii=False,indent=2))
print('audit',AUDIT)
if not audit['ok']:
    raise SystemExit(2)
