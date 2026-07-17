#!/usr/bin/env python3
# MGS_GOOGLE_AUTH_RETIRED_GUARD
raise SystemExit("RETIRED: personal Google authentication was removed. Rebuild this one-off utility on /root/mgs-agent/scripts/mgs_google_workspace_auth.py before any reuse.")
import json, pathlib, urllib.parse, urllib.request, urllib.error, time, datetime, re, csv, io, copy, sys
from collections import Counter, defaultdict

TOKEN_FILE = pathlib.Path('/root/mgs-agent/.secrets/ares-google-drive-oauth-client.json')
BASE = pathlib.Path('/root/mgs-agent/work/finance-month-rollover-audit')
RUN_ID = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
OUT = BASE / f'rollover-july-2026-{RUN_ID}'
OUT.mkdir(parents=True, exist_ok=True)

SHEETS = {
    'principal_2026': {'id':'16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak', 'title':'MGS - Receita dos Sites 2026'},
    'kelly': {'id':'1huhZFlFVEKmY11fR5DxgCWE2TNC3gvw_eXlW2jylVfs', 'title':'Kelly - MGS - Receita dos Sites'},
    'isliago': {'id':'1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c', 'title':'Isliago - MGS - Receita dos Sites'},
    'george': {'id':'1cFPIlC2NxRG6GQiF4VmbNqRz09ZWkZXWUzP7nINK9vU', 'title':'George - MGS - Receita dos Sites'},
    'nicolas': {'id':'128fEDdXayhgGGKMdLPf-FTWyJRW8-v6JgHzmUSrsOMU', 'title':'Nicolas - MGS - Receita dos Sites'},
    'joe': {'id':'1syOKCRi-2wpHQNY5fHMcOzjj73EXmFIUbTF1sTIARvQ', 'title':'Joe - MGS - Receita dos Sites'},
}
SOURCE_TAB = 'Junho 2026'
TARGET_TAB = 'Julho 2026'
MONTH_NUM = 7
YEAR = 2026

# Areas to clear after duplication. Based on formula/value scan: preserve formulas, clear manual constants in daily input regions only.
# For main sheet we clear non-formula numeric/text constants in monthly daily area excluding structural cells and labels.
# For manager sheets we clear non-formula constants in monthly tab data area excluding imported formulas/labels.
DAILY_MAX_ROW = 120


def col(n:int)->str:
    out=''
    while n:
        n -= 1
        out = chr(65+n%26)+out
        n //= 26
    return out

def a1(row:int, coln:int)->str:
    return f'{col(coln)}{row}'

def token():
    c=json.loads(TOKEN_FILE.read_text())
    body=urllib.parse.urlencode({'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':c['refresh_token'],'grant_type':'refresh_token'}).encode()
    req=urllib.request.Request('https://oauth2.googleapis.com/token',data=body,headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)['access_token']
ACCESS=token()

def api(method,url,data=None):
    body=None; headers={'Authorization':'Bearer '+ACCESS}
    if data is not None:
        body=json.dumps(data).encode(); headers['Content-Type']='application/json; charset=UTF-8'
    last=None
    for attempt in range(8):
        req=urllib.request.Request(url,method=method,headers=headers,data=body)
        try:
            with urllib.request.urlopen(req,timeout=240) as r:
                raw=r.read(); return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw=e.read().decode(errors='ignore')[:1500]
            last=f'HTTP {e.code}: {raw}'
            if e.code in (429,500,502,503,504) and attempt<7:
                time.sleep(min(90,15*(attempt+1))); continue
            raise RuntimeError(last)
    raise RuntimeError(last or 'api failure')

def q(s): return urllib.parse.quote(s, safe='')

def get_meta(sid):
    return api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{sid}?fields=properties(title),sheets(properties(sheetId,title,index,gridProperties(rowCount,columnCount)))')

def get_values(sid, rng, render='FORMULA'):
    return api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{q(rng)}?valueRenderOption={render}').get('values',[])

def batch_get(sid, ranges, render='FORMULA'):
    params=urllib.parse.urlencode([('ranges',r) for r in ranges]+[('valueRenderOption',render)])
    return api('GET', f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values:batchGet?{params}').get('valueRanges',[])

def batch_update(sid, requests):
    if not requests: return {}
    return api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{sid}:batchUpdate', {'requests':requests})

def values_batch_update(sid, data, input_option='USER_ENTERED'):
    if not data: return {}
    return api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values:batchUpdate', {'valueInputOption':input_option,'data':data})

def values_clear(sid, ranges):
    if not ranges: return {}
    return api('POST', f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values:batchClear', {'ranges':ranges})

def backup_sheet(key, sid, title, max_rows, max_cols):
    rng=f"'{title}'!A1:{col(max_cols)}{max_rows}"
    formulas=get_values(sid,rng,'FORMULA')
    formatted=get_values(sid,rng,'FORMATTED_VALUE')
    path=OUT / f'backup-{key}-{title.replace(" ","_")}.json'
    path.write_text(json.dumps({'spreadsheet_key':key,'spreadsheet_id':sid,'tab':title,'range':rng,'formulas':formulas,'formatted':formatted},ensure_ascii=False),encoding='utf-8')
    return str(path)

def duplicate_tab(sid, source_sheet_id, new_name, insert_index=None):
    req={'duplicateSheet': {'sourceSheetId': source_sheet_id, 'newSheetName': new_name}}
    if insert_index is not None: req['duplicateSheet']['insertSheetIndex']=insert_index
    res=batch_update(sid,[req])
    return res['replies'][0]['duplicateSheet']['properties']['sheetId']

def delete_tab(sid, sheet_id):
    return batch_update(sid,[{'deleteSheet': {'sheetId': sheet_id}}])

def find_cells_to_clear(formulas, formatted, is_main):
    # Clear constants that look like monthly inputs. Avoid formulas, dates/labels in col B, structural rows <=4, totals rows >=121.
    ranges=[]; cells=[]
    max_r=max(len(formulas),len(formatted))
    for r in range(1, min(max_r, DAILY_MAX_ROW)+1):
        frow=formulas[r-1] if r-1<len(formulas) else []
        vrow=formatted[r-1] if r-1<len(formatted) else []
        max_c=max(len(frow),len(vrow))
        for c in range(1,max_c+1):
            f=frow[c-1] if c-1<len(frow) else ''
            v=vrow[c-1] if c-1<len(vrow) else ''
            if not v: continue
            if isinstance(f,str) and f.startswith('='): continue
            # preserve structural and label/date cells
            if r <= 4: continue
            if c <= 2: continue
            txt=str(v).strip()
            if not txt: continue
            # do not clear obvious headers/status labels
            if txt.upper() in {'ATIVO','INATIVO','TOTAL','BM - $','GOOGLE ADS - R$','DATA','GESTOR','GASTO','RECEITA','LUCRO','MARGEM'}:
                continue
            # Clear numeric/currency/percentage constants in daily data area. Also clear short manual notes only in main? conservative: numeric-like only.
            numeric_like=bool(re.search(r'[-+]?\$?\s*\d', txt))
            if numeric_like:
                cells.append((r,c))
    # compress cells into row ranges where adjacent
    by_row=defaultdict(list)
    for r,c in cells: by_row[r].append(c)
    for r,cols in by_row.items():
        cols=sorted(set(cols)); start=prev=cols[0]
        for cc in cols[1:]:
            if cc==prev+1: prev=cc
            else:
                ranges.append(f"'{TARGET_TAB}'!{col(start)}{r}:{col(prev)}{r}")
                start=prev=cc
        ranges.append(f"'{TARGET_TAB}'!{col(start)}{r}:{col(prev)}{r}")
    return ranges, cells

def formula_error_scan(sid, tab, max_rows, max_cols):
    vals=get_values(sid, f"'{tab}'!A1:{col(max_cols)}{max_rows}", 'FORMATTED_VALUE')
    errors=[]
    for r,row in enumerate(vals,1):
        for c,v in enumerate(row,1):
            if isinstance(v,str) and v.startswith('#'):
                errors.append({'cell':a1(r,c),'value':v})
    return errors

def scan_bad_june_refs(sid, tab, max_rows, max_cols):
    vals=get_values(sid, f"'{tab}'!A1:{col(max_cols)}{max_rows}", 'FORMULA')
    hits=[]
    for r,row in enumerate(vals,1):
        for c,v in enumerate(row,1):
            if isinstance(v,str) and v.startswith('=') and 'Junho 2026' in v:
                hits.append({'cell':a1(r,c),'formula':v[:300]})
    return hits

def ensure_caixa_july_principal(sid, caixa_props):
    # Copy June column H to July column I on CAIXA SINTETICO where I is blank, replacing Junho->Julho and H refs where explicit.
    title='CAIXA SINTETICO'; max_rows=min(caixa_props.get('gridProperties',{}).get('rowCount',200),500)
    vals=batch_get(sid,[f"'{title}'!H1:H{max_rows}", f"'{title}'!I1:I{max_rows}"], 'FORMULA')
    h=vals[0].get('values',[]) if vals else []
    i=vals[1].get('values',[]) if len(vals)>1 else []
    updates=[]
    for idx in range(max_rows):
        hv=h[idx][0] if idx<len(h) and h[idx] else ''
        iv=i[idx][0] if idx<len(i) and i[idx] else ''
        if hv and (not iv):
            nv=hv
            if isinstance(nv,str) and nv.startswith('='):
                nv=nv.replace('Junho 2026','Julho 2026').replace('Junho','Julho')
            updates.append({'range': f"'{title}'!I{idx+1}", 'values': [[nv]]})
    if updates:
        values_batch_update(sid, updates, 'USER_ENTERED')
    return len(updates)

def set_main_july_dates_and_month(sid):
    # A3 numeric month; B4 year appears in formulas; column B dates rows 5:35 (31 days), label as actual dates.
    data=[
        {'range': f"'{TARGET_TAB}'!A3", 'values': [[MONTH_NUM]]},
        {'range': f"'{TARGET_TAB}'!B4", 'values': [[YEAR]]},
    ]
    dates=[]
    for day in range(1,32):
        dates.append([f'{YEAR}-07-{day:02d}'])
    data.append({'range': f"'{TARGET_TAB}'!B5:B35", 'values': dates})
    values_batch_update(sid,data,'USER_ENTERED')
    # format B5:B35 as date
    meta=get_meta(sid); target=next(s['properties'] for s in meta['sheets'] if s['properties']['title']==TARGET_TAB)
    batch_update(sid,[{'repeatCell': {'range': {'sheetId':target['sheetId'],'startRowIndex':4,'endRowIndex':35,'startColumnIndex':1,'endColumnIndex':2}, 'cell': {'userEnteredFormat': {'numberFormat': {'type':'DATE','pattern':'dd/mm/yyyy'}}}, 'fields':'userEnteredFormat.numberFormat'}}])

def main():
    log={'run_id':RUN_ID,'out_dir':str(OUT),'started':datetime.datetime.now().isoformat(timespec='seconds'),'actions':[],'backups':[],'validations':{},'warnings':[]}
    metas={}
    # Preflight + backups
    for key,info in SHEETS.items():
        sid=info['id']; meta=get_meta(sid); metas[key]=meta
        sheets={s['properties']['title']:s['properties'] for s in meta['sheets']}
        if SOURCE_TAB not in sheets: raise RuntimeError(f'{key}: source tab {SOURCE_TAB} not found')
        if TARGET_TAB in sheets:
            raise RuntimeError(f'{key}: target tab {TARGET_TAB} already exists; refusing to overwrite')
        src=sheets[SOURCE_TAB]
        b=backup_sheet(key,sid,SOURCE_TAB,min(src.get('gridProperties',{}).get('rowCount',1000),2500),min(src.get('gridProperties',{}).get('columnCount',26),900))
        log['backups'].append(b)
        if key=='principal_2026' and 'CAIXA SINTETICO' in sheets:
            cp=sheets['CAIXA SINTETICO']
            log['backups'].append(backup_sheet(key,sid,'CAIXA SINTETICO',min(cp.get('gridProperties',{}).get('rowCount',500),1000),min(cp.get('gridProperties',{}).get('columnCount',26),100)))
    # Duplicate tabs
    created={}
    try:
        for key,info in SHEETS.items():
            sid=info['id']; meta=metas[key]
            sheets={s['properties']['title']:s['properties'] for s in meta['sheets']}
            src=sheets[SOURCE_TAB]
            new_id=duplicate_tab(sid, src['sheetId'], TARGET_TAB, src.get('index',0)+1)
            created[key]=new_id
            log['actions'].append({'key':key,'action':'duplicate','from':SOURCE_TAB,'to':TARGET_TAB,'new_sheet_id':new_id})
        # Refresh, structural updates
        main_sid=SHEETS['principal_2026']['id']
        set_main_july_dates_and_month(main_sid)
        log['actions'].append({'key':'principal_2026','action':'set','cells':['A3=7','B4=2026','B5:B35=2026-07-01..31']})
        # CAIXA Sintetico July column
        meta=get_meta(main_sid); sheets={s['properties']['title']:s['properties'] for s in meta['sheets']}
        if 'CAIXA SINTETICO' in sheets:
            n=ensure_caixa_july_principal(main_sid,sheets['CAIXA SINTETICO'])
            log['actions'].append({'key':'principal_2026','action':'caixa_sintetico_fill_july_col_I_blank_cells','updated_cells':n})
        # Clear constants in duplicated July tabs conservatively
        for key,info in SHEETS.items():
            sid=info['id']; meta=get_meta(sid); sheets={s['properties']['title']:s['properties'] for s in meta['sheets']}; t=sheets[TARGET_TAB]
            max_rows=min(t.get('gridProperties',{}).get('rowCount',1000),2500); max_cols=min(t.get('gridProperties',{}).get('columnCount',26),900)
            rng=f"'{TARGET_TAB}'!A1:{col(max_cols)}{max_rows}"
            formulas=get_values(sid,rng,'FORMULA'); formatted=get_values(sid,rng,'FORMATTED_VALUE')
            clear_ranges,cells=find_cells_to_clear(formulas,formatted,key=='principal_2026')
            if clear_ranges:
                values_clear(sid,clear_ranges)
            log['actions'].append({'key':key,'action':'clear_constant_input_like_cells','range_count':len(clear_ranges),'cell_count':len(cells),'sample_ranges':clear_ranges[:20]})
        # Validation
        for key,info in SHEETS.items():
            sid=info['id']; meta=get_meta(sid); sheets={s['properties']['title']:s['properties'] for s in meta['sheets']}; t=sheets[TARGET_TAB]
            max_rows=min(t.get('gridProperties',{}).get('rowCount',1000),2500); max_cols=min(t.get('gridProperties',{}).get('columnCount',26),900)
            errors=formula_error_scan(sid,TARGET_TAB,max_rows,max_cols)
            june_refs=scan_bad_june_refs(sid,TARGET_TAB,max_rows,max_cols)
            vals=batch_get(sid,[f"'{TARGET_TAB}'!A3",f"'{TARGET_TAB}'!B5:B35"],'FORMATTED_VALUE') if key=='principal_2026' else []
            log['validations'][key]={'target_exists':True,'formula_errors':errors[:50],'formula_error_count':len(errors),'literal_junho_refs_count':len(june_refs),'literal_junho_refs_sample':june_refs[:20]}
            if key=='principal_2026':
                log['validations'][key]['A3']=vals[0].get('values',[['']])[0][0] if vals else None
                log['validations'][key]['date_rows_B5_B35_count']=len(vals[1].get('values',[])) if len(vals)>1 else None
        log['finished']=datetime.datetime.now().isoformat(timespec='seconds')
        log_path=OUT/'rollover-log.json'; log_path.write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'ok':True,'run_dir':str(OUT),'log':str(log_path),'validations':log['validations'],'actions':log['actions']},ensure_ascii=False,indent=2))
    except Exception as e:
        log['error']=str(e); log['created']=created
        # best effort rollback: delete created July tabs if any
        rb=[]
        for key,new_id in list(created.items())[::-1]:
            try:
                delete_tab(SHEETS[key]['id'], new_id); rb.append({'key':key,'deleted_sheet_id':new_id})
            except Exception as de:
                rb.append({'key':key,'delete_failed':str(de)})
        log['rollback']=rb; log['finished']=datetime.datetime.now().isoformat(timespec='seconds')
        path=OUT/'rollover-error-log.json'; path.write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'ok':False,'error':str(e),'rollback':rb,'log':str(path)},ensure_ascii=False,indent=2))
        sys.exit(1)

if __name__=='__main__':
    main()
